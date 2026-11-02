"""
Build the historical Gold model from a completed local Silver run.

Outputs:
- dim_state: one row per state.
- dim_date: one row per calendar month.
- dim_industry: one row per selected industry.
- fact_state_month: state-level jobs, unemployment, and SNAP.
- fact_state_industry_month: industry jobs by state/month.
- report_jobs_snap: complete 50-state jobs/participation comparisons.
- report_industry_month: all three industries across 48 common states.

This is an initial historical load. Revision metadata is initialized here;
incremental updates and old/new revision history are separate future work.

No API requests, uploads, or cloud resources are created.
"""

import argparse
import calendar
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from pyspark.sql import SparkSession, functions as F


PROJECT_DIR = Path(__file__).resolve().parent.parent

# Stable source codes serve as dimension keys. Strings preserve leading zeros.
STATE_ABBREVIATIONS = dict(
    pair.split(":")
    for pair in """
    01:AL 02:AK 04:AZ 05:AR 06:CA 08:CO 09:CT 10:DE 12:FL
    13:GA 15:HI 16:ID 17:IL 18:IN 19:IA 20:KS 21:KY 22:LA
    23:ME 24:MD 25:MA 26:MI 27:MN 28:MS 29:MO 30:MT 31:NE
    32:NV 33:NH 34:NJ 35:NM 36:NY 37:NC 38:ND 39:OH 40:OK
    41:OR 42:PA 44:RI 45:SC 46:SD 47:TN 48:TX 49:UT 50:VT
    51:VA 53:WA 54:WV 55:WI 56:WY
    """.split()
)

INDUSTRIES = [
    ("20000000", "Construction"),
    ("30000000", "Manufacturing"),
    ("42000000", "Retail trade"),
]


def read_json(path):
    """Read a local configuration or execution summary."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_keys(frame, keys, label):
    """Reject NULL or duplicate business keys before joining."""
    null_condition = F.lit(False)
    for key in keys:
        null_condition = null_condition | F.col(key).isNull()

    if frame.filter(null_condition).limit(1).count():
        raise ValueError(f"{label}: NULL key")

    if (
        frame.groupBy(*keys)
        .count()
        .filter(F.col("count") > 1)
        .limit(1)
        .count()
    ):
        raise ValueError(f"{label}: duplicate keys")


def require_same_keys(expected, actual, keys, label):
    """
    Check row coverage separately from measurement availability.

    A source row with a documented NULL value is legitimate.
    An absent or unexpected source row fails this historical build.
    """
    require_keys(actual, keys, label)

    expected_keys = expected.select(*keys)
    actual_keys = actual.select(*keys)

    missing = expected_keys.join(actual_keys, keys, "left_anti")
    unexpected = actual_keys.join(expected_keys, keys, "left_anti")

    if missing.limit(1).count() or unexpected.limit(1).count():
        raise ValueError(f"{label}: source keys differ from expected scope")


def add_initial_revision_metadata(frame, loaded_at):
    """Mark this output as a first load, using one timestamp for the run."""
    return (
        frame
        .withColumn("first_loaded_at", F.lit(loaded_at))
        .withColumn("last_changed_at", F.lit(loaded_at))
        .withColumn("revision_count", F.lit(0))
    )


def complete_months(frame, required_rows):
    """
    Keep only months containing every required reporting combination.

    The caller first selects valid measurements and the intended scope.
    """
    months = (
        frame.groupBy("date_key")
        .count()
        .filter(F.col("count") == required_rows)
        .select("date_key")
    )
    return frame.join(months, "date_key", "inner")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silver-run", type=Path, required=True)
    args = parser.parse_args()

    silver_dir = args.silver_run.resolve()
    silver_summary = read_json(silver_dir / "summary.json")

    if (
        silver_summary["status"] != "complete"
        or silver_summary["start_year"] != 2015
        or silver_summary["end_year"] != 2025
    ):
        raise ValueError("Expected a completed 2015–2025 Silver run")

    # Use the inventory frozen with this Bronze capture, rather than a
    # configuration file that might have changed since ingestion.
    inventory_path = Path(silver_summary["bls_run"]) / "inventory.json"
    definitions = read_json(inventory_path)["series"]

    states = {}
    memberships = set()

    for series in definitions:
        fips = series["state_fips"]
        name = series["state_name"]

        if fips in states and states[fips] != name:
            raise ValueError(f"Inconsistent state name for {fips}")
        states[fips] = name

        if (
            series["measure"] == "all_employees"
            and series["industry_code"] in dict(INDUSTRIES)
        ):
            memberships.add((fips, series["industry_code"]))

    if set(states) != set(STATE_ABBREVIATIONS):
        raise ValueError("Inventory does not contain the expected 50 states")

    # Manufacturing/retail cover 50 states; construction excludes DE/HI.
    expected_memberships = {
        (fips, code)
        for fips in states
        for code, _ in INDUSTRIES
        if not (code == "20000000" and fips in {"10", "15"})
    }
    if memberships != expected_memberships:
        raise ValueError("Unexpected state/industry membership")

    loaded_at = datetime.now(timezone.utc)
    output_dir = (
        PROJECT_DIR / "data" / "gold"
        / f"ingestion_date={loaded_at.date().isoformat()}"
        / f"run_id={uuid4().hex}"
    )

    spark = (
        SparkSession.builder
        .master("local[2]")
        .appName("JobsSnapHistoricalGold")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        bls = spark.read.parquet(str(silver_dir / "bls_observations"))
        snap = spark.read.parquet(str(silver_dir / "snap_state_month"))

        # Dimensions provide stable labels and reusable join keys.
        dim_state = spark.createDataFrame(
            [
                (fips, fips, STATE_ABBREVIATIONS[fips], states[fips])
                for fips in sorted(states)
            ],
            """
            state_key string, state_fips string,
            state_abbreviation string, state_name string
            """,
        )

        # Exactly the five agreed fields, with monthly grain.
        dim_date = spark.createDataFrame(
            [
                (
                    year * 100 + month,
                    year,
                    (month - 1) // 3 + 1,
                    month,
                    calendar.month_name[month],
                )
                for year in range(2015, 2026)
                for month in range(1, 13)
            ],
            """
            date_key int, year int, quarter int,
            month_number int, month_name string
            """,
        )

        dim_industry = spark.createDataFrame(
            [(code, code, name) for code, name in INDUSTRIES],
            """
            industry_key string, ces_industry_code string,
            industry_name string
            """,
        )

        membership = spark.createDataFrame(
            sorted(memberships),
            "state_key string, industry_key string",
        )

        # Expected grids establish the full scope before measurements join.
        state_grid = (
            dim_state.select("state_key")
            .crossJoin(dim_date.select("date_key"))
        )
        industry_grid = membership.crossJoin(dim_date.select("date_key"))

        jobs = (
            bls.filter(
                (F.col("measure") == "all_employees")
                & (F.col("industry_code") == "00000000")
            )
            .select(
                F.col("state_fips").alias("state_key"),
                "date_key",
                F.col("value").alias("total_nonfarm_jobs"),
                F.col("value_status").alias("jobs_status"),
                F.col("series_id").alias("jobs_series_id"),
                F.col("source_manifest").alias("jobs_source_manifest"),
            )
        )

        unemployment = (
            bls.filter(F.col("measure") == "unemployment_rate")
            .select(
                F.col("state_fips").alias("state_key"),
                "date_key",
                F.col("value").alias("unemployment_rate_pct"),
                F.col("value_status").alias("unemployment_status"),
                F.col("series_id").alias("unemployment_series_id"),
                F.col("source_manifest").alias(
                    "unemployment_source_manifest"
                ),
            )
        )

        snap_values = snap.select(
            F.col("state_fips").alias("state_key"),
            "date_key",
            "snap_persons",
            "snap_households",
            "snap_benefit_cost_usd",
            F.col("persons_status").alias("snap_persons_status"),
            F.col("households_status").alias("snap_households_status"),
            F.col("benefits_status").alias("snap_benefits_status"),
            "benefit_review_required",
            F.col("source_manifest").alias("snap_source_manifest"),
            F.col("source_file").alias("snap_source_file"),
            F.col("source_sheet").alias("snap_source_sheet"),
            F.col("source_row").alias("snap_source_row"),
        )

        industry_jobs = (
            bls.filter(
                (F.col("measure") == "all_employees")
                & F.col("industry_code").isin(
                    [code for code, _ in INDUSTRIES]
                )
            )
            .select(
                F.col("state_fips").alias("state_key"),
                F.col("industry_code").alias("industry_key"),
                "date_key",
                F.col("value").alias("industry_nonfarm_jobs"),
                F.col("value_status").alias("jobs_status"),
                "series_id",
                "source_manifest",
            )
        )

        state_keys = ["state_key", "date_key"]
        industry_keys = ["state_key", "industry_key", "date_key"]

        for label, frame in (
            ("Total jobs", jobs),
            ("Unemployment", unemployment),
            ("SNAP", snap_values),
        ):
            require_same_keys(state_grid, frame, state_keys, label)

        require_same_keys(
            industry_grid, industry_jobs, industry_keys, "Industry jobs"
        )

        # Left joins retain legitimate partial measurements as NULL.
        fact_state_month = (
            state_grid
            .join(jobs, state_keys, "left")
            .join(unemployment, state_keys, "left")
            .join(snap_values, state_keys, "left")
        )
        fact_state_month = add_initial_revision_metadata(
            fact_state_month, loaded_at
        ).cache()

        fact_state_industry_month = add_initial_revision_metadata(
            industry_grid.join(industry_jobs, industry_keys, "left"),
            loaded_at,
        ).cache()

        require_keys(fact_state_month, state_keys, "State fact")
        require_keys(
            fact_state_industry_month, industry_keys, "Industry fact"
        )

        # This comparison needs jobs and SNAP participants, not unemployment
        # or benefit dollars. Therefore their exceptions do not remove a
        # valid jobs/participation comparison.
        valid_jobs_snap = fact_state_month.filter(
            (F.col("jobs_status") == "available")
            & (F.col("snap_persons_status") == "available")
            & F.col("total_nonfarm_jobs").isNotNull()
            & F.col("snap_persons").isNotNull()
        ).select(
            "state_key", "date_key", "total_nonfarm_jobs", "snap_persons"
        )
        report_jobs_snap = complete_months(valid_jobs_snap, 50)

        # An all-three-industry comparison uses the common 48-state scope.
        common_states = (
            membership.groupBy("state_key")
            .count()
            .filter(F.col("count") == 3)
            .select("state_key")
        )
        valid_industry = (
            fact_state_industry_month
            .join(common_states, "state_key", "inner")
            .filter(
                (F.col("jobs_status") == "available")
                & F.col("industry_nonfarm_jobs").isNotNull()
            )
            .select(
                "state_key", "industry_key", "date_key",
                "industry_nonfarm_jobs",
            )
        )
        report_industry_month = complete_months(valid_industry, 48 * 3)

        tables = {
            "dim_state": dim_state,
            "dim_date": dim_date,
            "dim_industry": dim_industry,
            "fact_state_month": fact_state_month,
            "fact_state_industry_month": fact_state_industry_month,
            "report_jobs_snap": report_jobs_snap,
            "report_industry_month": report_industry_month,
        }

        expected_counts = {
            "dim_state": 50,
            "dim_date": 132,
            "dim_industry": 3,
            "fact_state_month": 6600,
            "fact_state_industry_month": 19536,
        }
        counts = {name: frame.count() for name, frame in tables.items()}

        for name, expected in expected_counts.items():
            if counts[name] != expected:
                raise ValueError(
                    f"{name}: expected {expected}, found {counts[name]}"
                )

        # These outputs are small. One part file per table makes the first
        # manual BigQuery load straightforward. Larger pipelines should
        # choose partitions based on their actual data volumes.
        output_dir.mkdir(parents=True, exist_ok=False)
        load_files = {}

        for name, frame in tables.items():
            table_dir = output_dir / name
            frame.coalesce(1).write.mode("errorifexists").parquet(
                str(table_dir)
            )

            parts = list(table_dir.glob("part-*.parquet"))
            if len(parts) != 1:
                raise ValueError(f"Expected one Parquet part for {name}")

            load_files[name] = str(parts[0])
            print(f"{name}: {counts[name]} rows")

        summary = {
            "status": "complete",
            "mode": "historical_initial_load",
            "start_year": 2015,
            "end_year": 2025,
            "silver_run": str(silver_dir),
            "loaded_at": loaded_at.isoformat(),
            "row_counts": counts,
            "load_files": load_files,
            "report_scope": {
                "report_jobs_snap": "50 states; jobs and SNAP persons",
                "report_industry_month": "48 states; all three industries",
            },
            "revision_history": "Pending incremental implementation",
        }

        # Only mark the version complete after every output is written.
        with (output_dir / "summary.json").open(
            "x", encoding="utf-8"
        ) as file:
            json.dump(summary, file, indent=2)

        print(f"Gold complete: {output_dir}")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
