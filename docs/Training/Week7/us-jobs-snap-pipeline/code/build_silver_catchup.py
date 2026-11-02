"""
Combine the accepted historical Silver baseline with 2026 catch-up data.

Purpose:
- Reuse existing source parsers and explicit schemas.
- Parse BLS January–September 2026 and SNAP January–July 2026.
- Retain different source publication cutoffs.
- Write a new combined Silver version without overwriting earlier outputs.

This initial catch-up adds new months only.
It does not apply older revisions, update Gold, or access cloud services.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pyspark.sql import SparkSession, functions as F

from build_silver import (
    BLS_SCHEMA,
    SNAP_SCHEMA,
    PROJECT_DIR,
    load_bls_rows,
    load_snap_rows,
    read_json,
)
from backfill_bls import save_json


def require_unique(frame, keys, label):
    """Reject overlapping or duplicate source/business keys."""
    duplicates = (
        frame.groupBy(*keys)
        .count()
        .filter(F.col("count") > 1)
    )
    if duplicates.limit(1).count():
        raise ValueError(f"Duplicate keys in {label}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-silver", type=Path, required=True)
    parser.add_argument("--bls-run", type=Path, required=True)
    parser.add_argument("--snap-manifest", type=Path, required=True)
    args = parser.parse_args()

    baseline_dir = args.baseline_silver.resolve()
    bls_run = args.bls_run.resolve()
    snap_manifest = args.snap_manifest.resolve()

    baseline = read_json(baseline_dir / "summary.json")
    catchup = read_json(bls_run / "summary.json")

    if (
        baseline["status"] != "complete"
        or baseline["start_year"] != 2015
        or baseline["end_year"] != 2025
    ):
        raise ValueError("Expected the completed historical Silver baseline")

    if (
        catchup["status"] != "complete"
        or catchup["mode"] != "catchup"
        or catchup["earliest_series_latest_month"] != 202609
        or catchup["latest_series_latest_month"] != 202609
    ):
        raise ValueError("Expected the accepted January–September BLS run")

    # Ensure both captures use exactly the same series definitions.
    baseline_bls_run = Path(baseline["bls_run"])
    if (
        (baseline_bls_run / "inventory.json").read_bytes()
        != (bls_run / "inventory.json").read_bytes()
    ):
        raise ValueError("Baseline and catch-up inventories differ")

    bls_months = {202600 + month for month in range(1, 10)}
    snap_months = {202600 + month for month in range(1, 8)}

    # Parse original capture bytes, checking their recorded hashes.
    bls_rows, definitions = load_bls_rows(
        bls_run, target_months=bls_months
    )
    snap_rows = load_snap_rows(
        snap_manifest,
        definitions,
        target_months=snap_months,
    )

    if len(bls_rows) != 2232 or len(snap_rows) != 350:
        raise ValueError("Unexpected catch-up row counts")

    print(f"Catch-up BLS rows: {len(bls_rows)}")
    print(f"Catch-up SNAP rows: {len(snap_rows)}")

    now = datetime.now(timezone.utc)
    output_dir = (
        PROJECT_DIR / "data" / "silver"
        / f"ingestion_date={now.date().isoformat()}"
        / f"run_id={uuid4().hex}"
    )

    spark = (
        SparkSession.builder
        .master("local[2]")
        .appName("JobsSnapSilverCatchup")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        new_bls = (
            spark.createDataFrame(bls_rows, schema=BLS_SCHEMA)
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
        new_snap = spark.createDataFrame(snap_rows, schema=SNAP_SCHEMA)

        old_bls = spark.read.parquet(
            str(baseline_dir / "bls_observations")
        )
        old_snap = spark.read.parquet(
            str(baseline_dir / "snap_state_month")
        )

        # This catch-up appends previously unprocessed months.
        # unionByName aligns columns by name rather than column position.
        bls = old_bls.unionByName(new_bls).cache()
        snap = old_snap.unionByName(new_snap).cache()

        require_unique(bls, ["series_id", "date_key"], "BLS")
        require_unique(snap, ["state_fips", "date_key"], "SNAP")

        bls_count = bls.count()
        snap_count = snap.count()

        if bls_count != 34968 or snap_count != 6950:
            raise ValueError("Combined Silver counts differ from expectations")

        output_dir.mkdir(parents=True, exist_ok=False)

        bls.write.mode("errorifexists").parquet(
            str(output_dir / "bls_observations")
        )
        snap.write.mode("errorifexists").parquet(
            str(output_dir / "snap_state_month")
        )

        summary = {
            "status": "complete",
            "mode": "historical_plus_initial_catchup",
            "start_year": 2015,
            "end_year": 2026,
            "baseline_silver_run": str(baseline_dir),
            "bls_run": str(bls_run),
            "snap_manifest": str(snap_manifest),
            "bls_latest_month": 202609,
            "snap_latest_month": 202607,
            "bls_rows": bls_count,
            "snap_rows": snap_count,
            "bls_source_missing": (
                bls.filter(F.col("value").isNull()).count()
            ),
            "snap_benefit_review_rows": (
                snap.filter(F.col("benefit_review_required")).count()
            ),
        }
        save_json(output_dir / "summary.json", summary)

        print(f"BLS combined: {bls_count} rows, through September 2026")
        print(f"SNAP combined: {snap_count} rows, through July 2026")
        print(f"Silver catch-up complete: {output_dir}")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()