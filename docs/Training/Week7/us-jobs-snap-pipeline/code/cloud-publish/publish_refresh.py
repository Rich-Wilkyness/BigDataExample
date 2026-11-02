"""
Prepare and optionally publish a validated monthly refresh.

Default: preview changes and save candidates in staging.
--publish: commit facts, history, calendar and run ledger atomically.

Reuses monthly_merge.py for measurement revisions and metadata rules.
Every automated Gold publisher must use the shared control version.
"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from urllib.parse import urlsplit
from uuid import uuid4

from google.cloud import bigquery, storage

from monthly_merge import index_rows, merge_records
from stage_refresh import (
    PROJECT_ID,
    LOCATION,
    STAGING_DATASET,
    GOLD_DATASET,
    MAX_BYTES_BILLED,
    require_keys,
)


STATE_KEYS = ["state_key", "date_key"]
INDUSTRY_KEYS = ["state_key", "industry_key", "date_key"]

SNAP_FIELDS = [
    "snap_persons",
    "snap_households",
    "snap_benefit_cost_usd",
    "snap_persons_status",
    "snap_households_status",
    "snap_benefits_status",
    "benefit_review_required",
]


def read(client, sql, parameters=None):
    """Read warehouse rows with an explicit processing limit."""
    config = bigquery.QueryJobConfig(
        maximum_bytes_billed=MAX_BYTES_BILLED,
        query_parameters=parameters or [],
    )
    return [
        dict(row)
        for row in client.query(
            sql,
            location=LOCATION,
            job_config=config,
        ).result()
    ]


def parameter(name, kind, value):
    return bigquery.ScalarQueryParameter(name, kind, value)


def encode_value(value):
    """Preserve decimal precision and timezone-aware timestamps in loads."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def stage_candidates(client, table_id, rows, schema):
    """Create isolated candidates, including an empty history table."""
    client.create_table(bigquery.Table(table_id, schema=schema))

    if rows:
        encoded = json.loads(json.dumps(rows, default=encode_value))
        client.load_table_from_json(
            encoded,
            table_id,
            location=LOCATION,
            job_config=bigquery.LoadJobConfig(
                schema=schema,
                write_disposition=bigquery.WriteDisposition.WRITE_EMPTY,
            ),
        ).result()


def project_sources(bls, snap):
    """Map Silver source columns into their Gold contribution columns."""
    groups = {
        "bls_jobs": [],
        "bls_unemployment": [],
        "bls_industry": [],
        "snap": [],
    }

    for row in bls:
        base = {
            "state_key": row["state_fips"],
            "date_key": row["date_key"],
        }

        if row["measure"] == "unemployment_rate":
            groups["bls_unemployment"].append({
                **base,
                "unemployment_rate_pct": row["value"],
                "unemployment_status": row["value_status"],
                "unemployment_series_id": row["series_id"],
                "unemployment_source_manifest": row["source_manifest"],
            })
        elif (
            row["measure"] == "all_employees"
            and row["industry_code"] == "00000000"
        ):
            groups["bls_jobs"].append({
                **base,
                "total_nonfarm_jobs": row["value"],
                "jobs_status": row["value_status"],
                "jobs_series_id": row["series_id"],
                "jobs_source_manifest": row["source_manifest"],
            })
        elif (
            row["measure"] == "all_employees"
            and row["industry_code"] in {
                "20000000", "30000000", "42000000"
            }
        ):
            groups["bls_industry"].append({
                **base,
                "industry_key": row["industry_code"],
                "industry_nonfarm_jobs": row["value"],
                "jobs_status": row["value_status"],
                "series_id": row["series_id"],
                "source_manifest": row["source_manifest"],
            })
        else:
            raise ValueError("Unexpected BLS measure or category")

    for row in snap:
        groups["snap"].append({
            "state_key": row["state_fips"],
            "date_key": row["date_key"],
            "snap_persons": row["snap_persons"],
            "snap_households": row["snap_households"],
            "snap_benefit_cost_usd": row["snap_benefit_cost_usd"],
            "snap_persons_status": row["persons_status"],
            "snap_households_status": row["households_status"],
            "snap_benefits_status": row["benefits_status"],
            "benefit_review_required": row["benefit_review_required"],
            "snap_source_manifest": row["source_manifest"],
            "snap_source_file": row["source_file"],
            "snap_source_sheet": row["source_sheet"],
            "snap_source_row": row["source_row"],
        })

    return groups


def complete_pending_fields(rows, groups, affected_keys, state_keys):
    """
    Initialize other sources on newly inserted state/month rows.

    A NULL contribution is 'not_yet_published' only when the month is
    later than that state's latest captured month for the source.
    An unexplained older gap fails instead of being disguised.
    """
    cutoffs = {}
    for group in ("bls_jobs", "bls_unemployment", "snap"):
        latest = {}
        for row in groups[group]:
            state = row["state_key"]
            latest[state] = max(
                latest.get(state, 0),
                row["date_key"],
            )

        if set(latest) != state_keys:
            raise ValueError(f"{group}: state coverage differs")
        cutoffs[group] = latest

    mappings = [
        ("total_nonfarm_jobs", "jobs_status", "bls_jobs"),
        (
            "unemployment_rate_pct",
            "unemployment_status",
            "bls_unemployment",
        ),
        ("snap_persons", "snap_persons_status", "snap"),
        ("snap_households", "snap_households_status", "snap"),
        ("snap_benefit_cost_usd", "snap_benefits_status", "snap"),
    ]

    for row in rows:
        key = tuple(row[field] for field in STATE_KEYS)
        if key not in affected_keys:
            continue

        for measure, status, group in mappings:
            if row.get(status) is None:
                if (
                    row.get(measure) is not None
                    or row["date_key"]
                    <= cutoffs[group][row["state_key"]]
                ):
                    raise ValueError(
                        f"Unexplained missing contribution: {key}/{measure}"
                    )
                row[measure] = None
                row[status] = "not_yet_published"

        if row.get("benefit_review_required") is None:
            row["benefit_review_required"] = False


def fact_merge_sql(target, candidate, schema, keys):
    """Generate a MERGE using the actual accepted warehouse schema."""
    columns = [field.name for field in schema]
    join = " AND ".join(f"T.`{key}` = S.`{key}`" for key in keys)
    assignments = ", ".join(
        f"T.`{name}` = S.`{name}`"
        for name in columns if name not in keys
    )
    names = ", ".join(f"`{name}`" for name in columns)
    values = ", ".join(f"S.`{name}`" for name in columns)

    return f"""
    MERGE `{target}` T
    USING `{candidate}` S
    ON {join}
    WHEN MATCHED THEN UPDATE SET {assignments}
    WHEN NOT MATCHED THEN INSERT ({names}) VALUES ({values});
    """


def publish(manifest_table, execute):
    """Prepare changes and optionally commit one logical refresh."""
    expected_prefix = STAGING_DATASET + ".manifest_"
    if (
        not manifest_table.startswith(expected_prefix)
        or not re.fullmatch(
            r"[a-f0-9]{24}",
            manifest_table[len(expected_prefix):],
        )
    ):
        raise ValueError("Unexpected staging manifest table ID")

    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    manifests = read(client, f"SELECT * FROM `{manifest_table}`")
    if len(manifests) != 1 or manifests[0]["status"] != "complete":
        raise ValueError("Expected one accepted staging manifest")
    manifest = manifests[0]

    token = manifest_table[len(expected_prefix):]
    for source in ("bls", "snap"):
        expected = f"{STAGING_DATASET}.{source}_{token}"
        if manifest[f"{source}_table"] != expected:
            raise ValueError("Manifest source table differs")

    run_id = manifest["refresh_run_id"]
    run_parameters = [parameter("run_id", "STRING", run_id)]

    # A completed logical refresh is a successful no-op on retry.
    committed = read(
        client,
        f"""
        SELECT *
        FROM `{GOLD_DATASET}.refresh_publications`
        WHERE refresh_run_id = @run_id
        """,
        run_parameters,
    )
    if committed:
        if (
            len(committed) != 1
            or committed[0]["silver_summary_sha256"]
            != manifest["silver_summary_sha256"]
            or committed[0]["stage_manifest"] != manifest_table
        ):
            raise ValueError("Refresh ID reused with different inputs")

        print(json.dumps({
            "status": "already_published",
            "refresh_run_id": run_id,
        }))
        return

    # Recheck the frozen summary and exact source-key coverage.
    uri = urlsplit(manifest["silver_summary"])
    if uri.scheme != "gs" or not uri.netloc:
        raise ValueError("Invalid Silver summary URI")

    raw = (
        storage.Client(project=PROJECT_ID)
        .bucket(uri.netloc)
        .blob(uri.path.lstrip("/"))
        .download_as_bytes()
    )
    if (
        hashlib.sha256(raw).hexdigest()
        != manifest["silver_summary_sha256"]
    ):
        raise ValueError("Silver summary changed after staging")

    summary = json.loads(raw)
    if summary.get("status") != "complete":
        raise ValueError("Silver is not complete")

    bls = read(client, f"SELECT * FROM `{manifest['bls_table']}`")
    snap = read(client, f"SELECT * FROM `{manifest['snap_table']}`")
    states = read(client, f"SELECT state_key FROM `{GOLD_DATASET}.dim_state`")
    state_keys = {row["state_key"] for row in states}
    if len(states) != 50 or len(state_keys) != 50 or None in state_keys:
        raise ValueError("Invalid state dimension")

    require_keys(
        bls,
        ("series_id", "date_key"),
        {
            (series, month)
            for series, months
            in summary["bls_refresh_months_by_series"].items()
            for month in months
        },
        "BLS",
    )
    require_keys(
        snap,
        ("state_fips", "date_key"),
        {
            (state, month)
            for state in state_keys
            for month in summary["snap_target_months"]
        },
        "SNAP",
    )
    if (
        len(bls) != manifest["bls_rows"]
        or len(snap) != manifest["snap_rows"]
    ):
        raise ValueError("Staging counts changed")

    control = read(
        client,
        f"""
        SELECT version
        FROM `{GOLD_DATASET}.pipeline_control`
        WHERE pipeline = 'jobs_snap_monthly'
        """,
    )
    if len(control) != 1 or control[0]["version"] is None:
        raise ValueError("Invalid publication control row")
    baseline_version = control[0]["version"]

    state_target = f"{GOLD_DATASET}.fact_state_month"
    industry_target = f"{GOLD_DATASET}.fact_state_industry_month"
    history_target = f"{GOLD_DATASET}.fact_measure_history"

    current_state = read(client, f"SELECT * FROM `{state_target}`")
    current_industry = read(client, f"SELECT * FROM `{industry_target}`")
    index_rows(current_state, STATE_KEYS)
    index_rows(current_industry, INDUSTRY_KEYS)

    groups = project_sources(bls, snap)
    now = datetime.now(timezone.utc)
    state = current_state
    events = []
    stats = {}

    # Each group changes only its own fields and source lineage.
    for group, fields in [
        ("bls_jobs", ["total_nonfarm_jobs", "jobs_status"]),
        (
            "bls_unemployment",
            ["unemployment_rate_pct", "unemployment_status"],
        ),
        ("snap", SNAP_FIELDS),
    ]:
        state, changes, stats[group] = merge_records(
            state, groups[group], STATE_KEYS, fields, group, now,
            fact_table="fact_state_month",
            refresh_run_id=run_id,
        )
        events.extend(changes)

    industry, changes, stats["bls_industry"] = merge_records(
        current_industry,
        groups["bls_industry"],
        INDUSTRY_KEYS,
        ["industry_nonfarm_jobs", "jobs_status"],
        "bls_industry",
        now,
        fact_table="fact_state_industry_month",
        refresh_run_id=run_id,
    )
    events.extend(changes)

    affected_state = {
        tuple(row[field] for field in STATE_KEYS)
        for group in ("bls_jobs", "bls_unemployment", "snap")
        for row in groups[group]
    }
    affected_industry = set(
        index_rows(groups["bls_industry"], INDUSTRY_KEYS)
    )
    complete_pending_fields(
        state, groups, affected_state, state_keys
    )

    industry_keys = {
        row["industry_key"]
        for row in read(
            client,
            f"SELECT industry_key FROM `{GOLD_DATASET}.dim_industry`",
        )
    }
    if any(
        row["state_key"] not in state_keys
        or row["industry_key"] not in industry_keys
        for row in industry
    ):
        raise ValueError("Unknown industry fact dimension key")

    if len(events) != len({event["event_id"] for event in events}):
        raise ValueError("Duplicate generated history event IDs")

    # Use warehouse schemas to preserve NUMERIC, JSON and required metadata.
    state_schema = client.get_table(state_target).schema
    industry_schema = client.get_table(industry_target).schema
    history_schema = client.get_table(history_target).schema

    state_candidates = [
        {field.name: row.get(field.name) for field in state_schema}
        for row in state
        if tuple(row[field] for field in STATE_KEYS) in affected_state
    ]
    industry_candidates = [
        {field.name: row.get(field.name) for field in industry_schema}
        for row in industry
        if tuple(row[field] for field in INDUSTRY_KEYS) in affected_industry
    ]
    history_candidates = [
        {field.name: event.get(field.name) for field in history_schema}
        for event in events
    ]

    # Unique preparation IDs keep preview/concurrent candidates isolated.
    attempt = uuid4().hex
    state_table = f"{STAGING_DATASET}.state_candidate_{attempt}"
    industry_table = f"{STAGING_DATASET}.industry_candidate_{attempt}"
    history_table = f"{STAGING_DATASET}.history_candidate_{attempt}"

    for table_id, rows, schema in [
        (state_table, state_candidates, state_schema),
        (industry_table, industry_candidates, industry_schema),
        (history_table, history_candidates, history_schema),
    ]:
        stage_candidates(client, table_id, rows, schema)

    result = {
        "status": "preview",
        "refresh_run_id": run_id,
        "baseline_version": baseline_version,
        "state_rows": len(state),
        "industry_rows": len(industry),
        "history_events": len(events),
        "stats": stats,
    }

    if not execute:
        print(json.dumps(result, indent=2))
        return

    history_columns = ", ".join(
        f"`{field.name}`" for field in history_schema
    )

    # All accepted mutations belong to one transaction.
    # Updating the same guard row makes overlapping publishers conflict.
    sql = f"""
    BEGIN TRANSACTION;

    ASSERT (
      SELECT COUNT(*)
      FROM `{GOLD_DATASET}.pipeline_control`
      WHERE pipeline = 'jobs_snap_monthly'
    ) = 1 AS 'Invalid control row';

    UPDATE `{GOLD_DATASET}.pipeline_control`
    SET version = version + 1, updated_at = CURRENT_TIMESTAMP()
    WHERE pipeline = 'jobs_snap_monthly'
      AND version = @baseline_version;

    ASSERT @@row_count = 1
      AS 'Baseline changed; recompute the refresh before publishing';

    ASSERT (
      SELECT COUNT(*)
      FROM `{GOLD_DATASET}.refresh_publications`
      WHERE refresh_run_id = @run_id
    ) = 0 AS 'Refresh already committed; check publication ledger';

    MERGE `{GOLD_DATASET}.dim_date` T
    USING (
      SELECT
        date_key,
        EXTRACT(YEAR FROM month_date) AS year,
        EXTRACT(QUARTER FROM month_date) AS quarter,
        EXTRACT(MONTH FROM month_date) AS month_number,
        FORMAT_DATE('%B', month_date) AS month_name
      FROM (
        SELECT
          date_key,
          PARSE_DATE('%Y%m', CAST(date_key AS STRING)) AS month_date
        FROM (
          SELECT date_key FROM `{state_table}`
          UNION DISTINCT
          SELECT date_key FROM `{industry_table}`
        )
      )
    ) S
    ON T.date_key = S.date_key
    WHEN NOT MATCHED THEN INSERT
      (date_key, year, quarter, month_number, month_name)
    VALUES
      (S.date_key, S.year, S.quarter, S.month_number, S.month_name);

    {fact_merge_sql(
        state_target, state_table, state_schema, STATE_KEYS
    )}

    {fact_merge_sql(
        industry_target, industry_table, industry_schema, INDUSTRY_KEYS
    )}

    IF @history_events > 0 THEN
      INSERT INTO `{history_target}` ({history_columns})
      SELECT {history_columns} FROM `{history_table}`;
    END IF;

    ASSERT (
      SELECT COUNT(*) FROM `{state_target}`
    ) = @state_rows AS 'Unexpected state fact count';

    ASSERT (
      SELECT COUNT(*) FROM `{industry_target}`
    ) = @industry_rows AS 'Unexpected industry fact count';

    INSERT INTO `{GOLD_DATASET}.refresh_publications`
      (
        refresh_run_id, stage_manifest, silver_summary_sha256,
        published_at, state_rows, industry_rows, history_events, stats
      )
    VALUES
      (
        @run_id, @manifest, @summary_sha256,
        CURRENT_TIMESTAMP(), @state_rows, @industry_rows,
        @history_events, PARSE_JSON(@stats_json)
      );

    COMMIT TRANSACTION;
    """

    read(
        client,
        sql,
        [
            parameter("run_id", "STRING", run_id),
            parameter("manifest", "STRING", manifest_table),
            parameter(
                "summary_sha256", "STRING",
                manifest["silver_summary_sha256"],
            ),
            parameter("baseline_version", "INT64", baseline_version),
            parameter("state_rows", "INT64", len(state)),
            parameter("industry_rows", "INT64", len(industry)),
            parameter("history_events", "INT64", len(events)),
            parameter("stats_json", "STRING", json.dumps(stats)),
        ],
    )

    result["status"] = "published"
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-table", required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    publish(args.manifest_table, args.publish)


if __name__ == "__main__":
    main()