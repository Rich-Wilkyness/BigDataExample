"""
Build monthly Silver refresh slices from accepted cloud Bronze captures.

Purpose:
- Read saved BLS/SNAP summaries without requesting source data again.
- Verify and parse Bronze using the existing shared functions.
- Select six reporting months independently for each source/series.
- Normalize payroll measurements into jobs.
- Preserve source values, missing statuses, quality flags and lineage.
- Write versioned Parquet and publish a completion summary last.

This does not merge historical Silver or update BigQuery/Gold.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from uuid import uuid4

from google.cloud import storage
from pyspark.sql import SparkSession, functions as F

from build_silver import (
    BLS_SCHEMA,
    SNAP_SCHEMA,
    load_bls_rows,
    load_snap_rows,
)


def utc_now():
    """Use UTC consistently for capture and processing timestamps."""
    return datetime.now(timezone.utc).isoformat()


def split_gs_uri(uri):
    """Separate a Cloud Storage URI into bucket and object name."""
    parsed = urlsplit(uri)

    if (
        parsed.scheme != "gs"
        or not parsed.netloc
        or not parsed.path.strip("/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Expected a gs://bucket/object URI: {uri}")

    return parsed.netloc, parsed.path.lstrip("/")


def get_blob(client, uri):
    """Use the workload service account through default credentials."""
    bucket, name = split_gs_uri(uri)
    return client.bucket(bucket).blob(name)


def stage_capture(client, summary_uri, directory, expected_source):
    """
    Download listed artifacts into a temporary driver directory.

    Only local copies of summary references are adapted. Cloud Bronze
    objects and their original manifests remain unchanged.
    """
    summary = json.loads(
        get_blob(client, summary_uri).download_as_bytes()
    )

    if (
        summary.get("status") != "complete"
        or summary.get("source") != expected_source
    ):
        raise ValueError(f"Unaccepted {expected_source} capture")

    bucket, summary_name = split_gs_uri(summary_uri)
    prefix = summary_name.rsplit("/", 1)[0] + "/"
    directory.mkdir(parents=True, exist_ok=False)
    local_paths = {}

    for uri in summary["objects"]:
        object_bucket, object_name = split_gs_uri(uri)

        if object_bucket != bucket or not object_name.startswith(prefix):
            raise ValueError("Artifact is outside its capture directory")

        relative = PurePosixPath(object_name[len(prefix):])
        if (
            not relative.parts
            or ".." in relative.parts
            or relative.is_absolute()
            or uri in local_paths
        ):
            raise ValueError("Invalid or duplicate artifact reference")

        destination = directory.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError("Multiple artifacts map to the same file")

        get_blob(client, uri).download_to_filename(str(destination))
        local_paths[uri] = destination.resolve()

    return summary, local_paths


def check_window(months, latest):
    """Require exactly six consecutive calendar months ending at latest."""
    months = list(months)

    if any(
        not isinstance(key, int) or not 1 <= key % 100 <= 12
        for key in months
    ):
        raise ValueError("Invalid YYYYMM reporting month")

    serial_months = sorted(
        (key // 100) * 12 + key % 100 - 1
        for key in months
    )
    latest_serial = (latest // 100) * 12 + latest % 100 - 1

    if serial_months != list(range(latest_serial - 5, latest_serial + 1)):
        raise ValueError("Expected six months ending at the source cutoff")


def restore_lineage(rows, local_paths):
    """Replace temporary driver filenames with original manifest URIs."""
    original_uris = {
        str(path): uri
        for uri, path in local_paths.items()
    }

    for row in rows:
        row["source_manifest"] = original_uris[row["source_manifest"]]


def prepare_rows(client, bls_uri, snap_uri, temporary_root):
    """Reuse shared parsing and checksum checks before starting Spark."""
    bls_dir = temporary_root / "bls"
    bls_summary, bls_paths = stage_capture(
        client, bls_uri, bls_dir, "bls"
    )

    windows = bls_summary["refresh_months_by_series"]
    latest_by_series = bls_summary["latest_month_by_series"]

    if set(windows) != set(latest_by_series):
        raise ValueError("BLS cutoffs differ from its selected series")

    for series_id, months in windows.items():
        check_window(months, latest_by_series[series_id])

    # The shared parser expects local paths in its summary.
    # Create a local adapter copy without modifying cloud metadata.
    local_summary = {
        **bls_summary,
        "completed_batches": [
            {
                **batch,
                "manifest": str(bls_paths[batch["manifest"]]),
            }
            for batch in bls_summary["completed_batches"]
        ],
    }
    (bls_dir / "summary.json").write_text(
        json.dumps(local_summary),
        encoding="utf-8",
    )

    bls_rows, definitions = load_bls_rows(
        bls_dir.resolve(),
        months_by_series=windows,
        filter_outside=True,
    )
    restore_lineage(bls_rows, bls_paths)

    snap_summary, snap_paths = stage_capture(
        client, snap_uri, temporary_root / "snap", "snap"
    )
    check_window(
        snap_summary["target_months"],
        snap_summary["latest_month"],
    )

    snap_rows = load_snap_rows(
        snap_paths[snap_summary["manifest"]],
        definitions,
        target_months=snap_summary["target_months"],
    )
    restore_lineage(snap_rows, snap_paths)

    return bls_rows, snap_rows, bls_summary, snap_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bls-summary", required=True)
    parser.add_argument("--snap-summary", required=True)
    parser.add_argument("--silver-bucket", required=True)
    parser.add_argument("--run-id", default=uuid4().hex)
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        raise ValueError("Invalid output run ID")

    client = storage.Client()
    started_at = utc_now()
    ingestion_date = started_at[:10]

    output_uri = (
        f"gs://{args.silver_bucket}/silver"
        f"/ingestion_date={ingestion_date}"
        f"/run_id={args.run_id}"
    )

    # Reserve this output directory before writing.
    # An existing reservation requires a new output run ID.
    get_blob(client, f"{output_uri}/started.json").upload_from_string(
        json.dumps({
            "status": "started",
            "started_at": started_at,
            "run_id": args.run_id,
            "bls_summary": args.bls_summary,
            "snap_summary": args.snap_summary,
        }, indent=2),
        content_type="application/json",
        if_generation_match=0,
    )

    with TemporaryDirectory(prefix="jobs-snap-silver-") as temporary:
        bls_rows, snap_rows, bls_capture, snap_capture = prepare_rows(
            client,
            args.bls_summary,
            args.snap_summary,
            Path(temporary),
        )

    print(json.dumps({
        "parsed_bls_rows": len(bls_rows),
        "parsed_snap_rows": len(snap_rows),
    }))

    # No local master: managed Spark supplies driver and executors.
    spark = (
        SparkSession.builder
        .appName("JobsSnapMonthlySilver")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        bls = spark.createDataFrame(bls_rows, schema=BLS_SCHEMA)

        # CES publishes thousands of jobs; LAUS publishes percentages.
        bls = (
            bls
            .withColumn(
                "value",
                F.when(
                    F.col("measure") == "all_employees",
                    F.col("source_numeric") * F.lit(1000),
                )
                .otherwise(F.col("source_numeric"))
                .cast("decimal(24,6)"),
            )
            .withColumn(
                "value_units",
                F.when(
                    F.col("measure") == "all_employees",
                    F.lit("jobs"),
                ).otherwise(F.lit("percent")),
            )
        )
        snap = spark.createDataFrame(snap_rows, schema=SNAP_SCHEMA)

        invalid_bls = bls.filter(
            (
                (F.col("measure") == "all_employees")
                & (F.col("value") < 0)
            )
            | (
                (F.col("measure") == "unemployment_rate")
                & (
                    (F.col("value") < 0)
                    | (F.col("value") > 100)
                )
            )
        )
        if invalid_bls.limit(1).count():
            raise ValueError("BLS measurement outside its valid range")

        bls_output = f"{output_uri}/bls_observations"
        snap_output = f"{output_uri}/snap_state_month"

        bls.write.mode("errorifexists").parquet(bls_output)
        snap.write.mode("errorifexists").parquet(snap_output)

        summary = {
            "status": "complete",
            "mode": "monthly_refresh_slice",
            "run_id": args.run_id,
            "started_at": started_at,
            "finished_at": utc_now(),
            "bls_summary": args.bls_summary,
            "snap_summary": args.snap_summary,
            "bls_rows": len(bls_rows),
            "snap_rows": len(snap_rows),
            "bls_output": bls_output,
            "snap_output": snap_output,
            "bls_latest_month_by_series":
                bls_capture["latest_month_by_series"],
            "bls_refresh_months_by_series":
                bls_capture["refresh_months_by_series"],
            "snap_latest_month": snap_capture["latest_month"],
            "snap_target_months": snap_capture["target_months"],
            "bls_source_missing": sum(
                row["value_status"] == "source_missing"
                for row in bls_rows
            ),
            "snap_benefit_review_rows": sum(
                row["benefit_review_required"]
                for row in snap_rows
            ),
        }

        # Consumers must require this complete summary.
        # Partial output from a failed run is never accepted.
        summary_uri = f"{output_uri}/summary.json"
        get_blob(client, summary_uri).upload_from_string(
            json.dumps(summary, indent=2),
            content_type="application/json",
            if_generation_match=0,
        )

        print(json.dumps({
            "status": "complete",
            "bls_rows": len(bls_rows),
            "snap_rows": len(snap_rows),
            "summary": summary_uri,
        }))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()