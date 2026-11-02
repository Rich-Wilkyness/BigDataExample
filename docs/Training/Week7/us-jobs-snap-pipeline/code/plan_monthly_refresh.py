"""
Plan a six-reporting-month refresh for each source.

Replay mode uses cutoffs from an already accepted Gold snapshot.
It makes no API calls and changes no data.

A future live run must discover current publication cutoffs first.
"""

import argparse
import json
from pathlib import Path


def reporting_months(latest_month, count=6):
    """Return consecutive YYYYMM keys, including across year boundaries."""
    year, month = divmod(latest_month, 100)

    if year < 1 or not 1 <= month <= 12 or count < 1:
        raise ValueError("Invalid reporting month or window length")

    # Convert to a continuous month index so January boundaries work.
    latest_index = year * 12 + month - 1
    first_index = latest_index - count + 1

    if first_index < 12:
        raise ValueError("Window extends before year 1")

    months = []
    for index in range(first_index, latest_index + 1):
        month_year, zero_based_month = divmod(index, 12)
        months.append(month_year * 100 + zero_based_month + 1)

    return months


def build_replay_plan(gold_run):
    """Use accepted cutoffs to rehearse a bounded, unchanged-data refresh."""
    gold_run = Path(gold_run).resolve()
    summary = json.loads(
        (gold_run / "summary.json").read_text(encoding="utf-8")
    )

    if summary["status"] != "complete":
        raise ValueError("Gold snapshot is not complete")

    bls_months = reporting_months(summary["bls_latest_month"])
    snap_months = reporting_months(summary["snap_latest_month"])

    return {
        "mode": "replay",
        "accepted_gold_run": str(gold_run),
        "silver_run": summary["silver_run"],
        "sources": {
            "bls": {
                "months": bls_months,
                "expected_source_keys": 248 * len(bls_months),
            },
            "snap": {
                "months": snap_months,
                "expected_source_keys": 50 * len(snap_months),
            },
        },
        "expected_inserts": 0,
        "expected_revisions": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-run", type=Path, required=True)
    args = parser.parse_args()

    plan = build_replay_plan(args.gold_run)
    print(json.dumps(plan, indent=2))