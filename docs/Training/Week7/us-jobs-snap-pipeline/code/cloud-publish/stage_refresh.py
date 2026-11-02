"""
Stage an accepted cloud Silver refresh in BigQuery.

Purpose:
- Load saved Silver Parquet directly from Cloud Storage.
- Keep each refresh in separate staging tables.
- Validate exact BLS and SNAP business-key coverage.
- Save an accepted staging manifest after validation.

This component does not modify Gold facts or revision history.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from urllib.parse import urlsplit

from google.api_core.exceptions import Conflict, NotFound
from google.cloud import bigquery, storage


PROJECT_ID = "project-4b0f63f3-e441-4289-b42"
LOCATION = "us-central1"
STAGING_DATASET = f"{PROJECT_ID}.jobs_snap_staging"
GOLD_DATASET = f"{PROJECT_ID}.jobs_snap_gold"
MAX_BYTES_BILLED = 104857600


def query_rows(client, sql):
    """Read small validation results with an explicit query-cost limit."""
    config = bigquery.QueryJobConfig(
        maximum_bytes_billed=MAX_BYTES_BILLED,
    )
    return list(
        client.query(
            sql,
            job_config=config,
            location=LOCATION,
        ).result()
    )


def finish_load(client, job_id, start_job):
    """
    Reattach to an existing load when retrying the same logical input.

    Stable job IDs avoid submitting duplicate loads after a lost response.
    A failed saved load raises its error instead of silently replacing data.
    """
    try:
        job = client.get_job(job_id, location=LOCATION)
    except NotFound:
        try:
            job = start_job()
        except Conflict:
            job = client.get_job(job_id, location=LOCATION)

    job.result()
    return job


def load_parquet(client, uri, table_id, job_id):
    """Create a native staging table without overwriting existing rows."""
    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_EMPTY,
    )

    finish_load(
        client,
        job_id,
        lambda: client.load_table_from_uri(
            f"{uri.rstrip('/')}/part-*.parquet",
            table_id,
            job_id=job_id,
            location=LOCATION,
            job_config=config,
        ),
    )


def require_keys(rows, fields, expected, source):
    """Reject missing, extra, duplicate or NULL source business keys."""
    actual = [
        tuple(row[field] for field in fields)
        for row in rows
    ]

    if any(any(value is None for value in key) for key in actual):
        raise ValueError(f"{source}: NULL business key")

    if len(actual) != len(set(actual)):
        raise ValueError(f"{source}: duplicate business keys")

    actual = set(actual)
    if actual != expected:
        raise ValueError(
            f"{source}: {len(expected - actual)} missing keys; "
            f"{len(actual - expected)} unexpected keys"
        )


def stage_refresh(summary_uri, refresh_run_id):
    """Load, validate and record one accepted monthly Silver refresh."""
    parsed = urlsplit(summary_uri)
    if parsed.scheme != "gs" or not parsed.netloc:
        raise ValueError("Silver summary must use a gs:// URI")

    storage_client = storage.Client(project=PROJECT_ID)
    raw = (
        storage_client.bucket(parsed.netloc)
        .blob(parsed.path.lstrip("/"))
        .download_as_bytes()
    )
    summary = json.loads(raw)

    if (
        summary.get("status") != "complete"
        or summary.get("mode") != "monthly_refresh_slice"
    ):
        raise ValueError("Expected a complete monthly Silver slice")

    # Bind staging names to both logical refresh ID and exact summary bytes.
    # Reusing the same inputs produces the same table and load-job names.
    summary_sha256 = hashlib.sha256(raw).hexdigest()
    token = hashlib.sha256(
        f"{refresh_run_id}:{summary_sha256}".encode("utf-8")
    ).hexdigest()[:24]

    bls_table = f"{STAGING_DATASET}.bls_{token}"
    snap_table = f"{STAGING_DATASET}.snap_{token}"
    manifest_table = f"{STAGING_DATASET}.manifest_{token}"

    client = bigquery.Client(
        project=PROJECT_ID,
        location=LOCATION,
    )

    # Both warehouse datasets must match the regional Silver bucket.
    for dataset_id in (STAGING_DATASET, GOLD_DATASET):
        dataset = client.get_dataset(dataset_id)
        if dataset.location.lower() != LOCATION:
            raise ValueError(f"Wrong dataset location: {dataset_id}")

    load_parquet(
        client,
        summary["bls_output"],
        bls_table,
        f"stage_bls_{token}",
    )
    load_parquet(
        client,
        summary["snap_output"],
        snap_table,
        f"stage_snap_{token}",
    )

    # Validate loaded keys, not only whether load jobs succeeded.
    bls_keys = query_rows(
        client,
        f"SELECT series_id, date_key FROM `{bls_table}`",
    )
    snap_keys = query_rows(
        client,
        f"SELECT state_fips, date_key FROM `{snap_table}`",
    )

    expected_bls = {
        (series_id, month)
        for series_id, months
        in summary["bls_refresh_months_by_series"].items()
        for month in months
    }

    states = query_rows(
        client,
        f"SELECT state_key FROM `{GOLD_DATASET}.dim_state`",
    )
    state_keys = {row["state_key"] for row in states}
    if (
        len(states) != 50
        or len(state_keys) != 50
        or None in state_keys
    ):
        raise ValueError("Expected 50 unique configured state keys")

    expected_snap = {
        (state, month)
        for state in state_keys
        for month in summary["snap_target_months"]
    }

    require_keys(
        bls_keys,
        ("series_id", "date_key"),
        expected_bls,
        "BLS",
    )
    require_keys(
        snap_keys,
        ("state_fips", "date_key"),
        expected_snap,
        "SNAP",
    )

    if (
        len(bls_keys) != summary["bls_rows"]
        or len(snap_keys) != summary["snap_rows"]
    ):
        raise ValueError("Loaded counts differ from accepted Silver")

    # This manifest is the handoff to the subsequent Gold merge.
    # It is recorded only after both source tables pass validation.
    manifest = {
        "status": "complete",
        "refresh_run_id": refresh_run_id,
        "silver_summary": summary_uri,
        "silver_summary_sha256": summary_sha256,
        "bls_table": bls_table,
        "snap_table": snap_table,
        "bls_rows": len(bls_keys),
        "snap_rows": len(snap_keys),
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }

    schema = [
        bigquery.SchemaField(name, field_type)
        for name, field_type in [
            ("status", "STRING"),
            ("refresh_run_id", "STRING"),
            ("silver_summary", "STRING"),
            ("silver_summary_sha256", "STRING"),
            ("bls_table", "STRING"),
            ("snap_table", "STRING"),
            ("bls_rows", "INT64"),
            ("snap_rows", "INT64"),
            ("accepted_at", "TIMESTAMP"),
        ]
    ]
    config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_EMPTY,
    )

    finish_load(
        client,
        f"stage_manifest_{token}",
        lambda: client.load_table_from_json(
            [manifest],
            manifest_table,
            job_id=f"stage_manifest_{token}",
            location=LOCATION,
            job_config=config,
        ),
    )

    result = {
        "status": "staged",
        "refresh_run_id": refresh_run_id,
        "manifest_table": manifest_table,
        "bls_table": bls_table,
        "snap_table": snap_table,
        "bls_rows": len(bls_keys),
        "snap_rows": len(snap_keys),
    }
    print(json.dumps(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silver-summary", required=True)
    parser.add_argument("--refresh-run-id", required=True)
    args = parser.parse_args()

    stage_refresh(args.silver_summary, args.refresh_run_id)


if __name__ == "__main__":
    main()