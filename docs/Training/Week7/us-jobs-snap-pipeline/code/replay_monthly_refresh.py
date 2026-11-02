
"""
Rehearse the monthly merge using accepted Silver and Gold snapshots.

The replay:
- Selects only each source's six reporting months.
- Projects Silver columns into their corresponding Gold fields.
- Checks exact business-key coverage.
- Runs the shared merge.
- Requires zero inserts, zero revisions, and unchanged final facts.

No source requests, file writes, BigQuery updates, or cloud operations occur.
PyArrow is already installed from the earlier processing steps.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pyarrow.parquet as pq

from monthly_merge import index_rows, merge_records
from plan_monthly_refresh import build_replay_plan
from check_monthly_merge import verify_merge_contract


STATE_KEYS = ["state_key", "date_key"]
INDUSTRY_KEYS = ["state_key", "industry_key", "date_key"]

SNAP_CONTENT = [
    "snap_persons",
    "snap_households",
    "snap_benefit_cost_usd",
    "snap_persons_status",
    "snap_households_status",
    "snap_benefits_status",
    "benefit_review_required",
]


def read_rows(directory):
    """Read actual Parquet parts without interpreting parent folder names."""
    parts = sorted(Path(directory).glob("part-*.parquet"))
    if not parts:
        raise ValueError(f"No Parquet parts: {directory}")

    rows = []
    for part in parts:
        rows.extend(pq.ParquetFile(part).read().to_pylist())
    return rows


def replay_group(current, incoming, keys, fields, source, months, now):
    """Require all expected keys before invoking the merge."""
    expected = {
        key
        for key, row in index_rows(current, keys).items()
        if row["date_key"] in months
    }
    actual = set(index_rows(incoming, keys))

    if actual != expected:
        raise ValueError(
            f"{source}: {len(expected - actual)} missing keys; "
            f"{len(actual - expected)} unexpected keys"
        )

    updated, revisions, stats = merge_records(
        current,
        incoming,
        keys,
        fields,
        source,
        now,
        fact_table=(
            "fact_state_industry_month"
            if "industry_key" in keys
            else "fact_state_month"
        ),
        refresh_run_id="replay-" + now.isoformat(),
    )

    if revisions or stats["inserted"] or stats["revised"]:
        raise ValueError(f"Replay unexpectedly changed {source}")

    print(f"{source}: {stats}")
    return updated, stats["unchanged"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-run", type=Path, required=True)
    args = parser.parse_args()

    verify_merge_contract()
    print("Merge contract checks passed.")

    gold_dir = args.gold_run.resolve()
    plan = build_replay_plan(gold_dir)
    silver_dir = Path(plan["silver_run"])

    bls_months = set(plan["sources"]["bls"]["months"])
    snap_months = set(plan["sources"]["snap"]["months"])

    bls = [
        row for row in read_rows(silver_dir / "bls_observations")
        if row["date_key"] in bls_months
    ]
    snap = [
        row for row in read_rows(silver_dir / "snap_state_month")
        if row["date_key"] in snap_months
    ]

    if (
        len(bls) != plan["sources"]["bls"]["expected_source_keys"]
        or len(snap) != plan["sources"]["snap"]["expected_source_keys"]
    ):
        raise ValueError("Source-window record counts differ from the plan")

    original_state = read_rows(gold_dir / "fact_state_month")
    original_industry = read_rows(gold_dir / "fact_state_industry_month")

    jobs = []
    unemployment = []
    industry = []

    for row in bls:
        base = {
            "state_key": row["state_fips"],
            "date_key": row["date_key"],
        }

        if row["measure"] == "unemployment_rate":
            unemployment.append({
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
            jobs.append({
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
            industry.append({
                **base,
                "industry_key": row["industry_code"],
                "industry_nonfarm_jobs": row["value"],
                "jobs_status": row["value_status"],
                "series_id": row["series_id"],
                "source_manifest": row["source_manifest"],
            })
        else:
            raise ValueError("Unexpected BLS measure/category")

    snap_updates = []
    for row in snap:
        snap_updates.append({
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

    now = datetime.now(timezone.utc)
    state = original_state
    unchanged = 0

    # Each source changes only its own measurements, statuses, and lineage.
    for name, updates, fields, months in [
        (
            "bls_jobs", jobs,
            ["total_nonfarm_jobs", "jobs_status"], bls_months,
        ),
        (
            "bls_unemployment", unemployment,
            ["unemployment_rate_pct", "unemployment_status"], bls_months,
        ),
        ("snap", snap_updates, SNAP_CONTENT, snap_months),
    ]:
        state, count = replay_group(
            state, updates, STATE_KEYS, fields, name, months, now
        )
        unchanged += count

    industry_result, count = replay_group(
        original_industry,
        industry,
        INDUSTRY_KEYS,
        ["industry_nonfarm_jobs", "jobs_status"],
        "bls_industry",
        bls_months,
        now,
    )
    unchanged += count

    # Compare whole rows, including first-load/change timestamps and counters.
    if (
        index_rows(state, STATE_KEYS)
        != index_rows(original_state, STATE_KEYS)
        or index_rows(industry_result, INDUSTRY_KEYS)
        != index_rows(original_industry, INDUSTRY_KEYS)
    ):
        raise ValueError("Replay altered accepted facts or their metadata")

    print(json.dumps({
        "status": "passed",
        "mode": "replay",
        "unchanged_source_contributions": unchanged,
        "inserted": 0,
        "revisions": 0,
        "state_fact_rows": len(state),
        "industry_fact_rows": len(industry_result),
        "revision_metadata_preserved": True,
        "outputs_written": False,
    }, indent=2))


if __name__ == "__main__":
    main()
