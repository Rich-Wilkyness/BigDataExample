"""
Capture BLS observations published for 2026 into a new Bronze run.

Purpose:
- Reuse the historical loader's request, retry, and manifest functions.
- Accept a publication year that is not finished.
- Report the latest returned month separately for every series.
- Preserve the completed historical baseline unchanged.

This initial catch-up requests January onward.
The later monthly refresh will process only six reporting months.

This script does not modify Silver, Gold, BigQuery, or cloud resources.
"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from uuid import uuid4

from backfill_bls import (
    BATCH_SIZE,
    BRONZE_ROOT,
    capture_batch,
    checksum,
    load_series_ids,
    save_json,
)


CATCHUP_YEAR = 2026


def validate_available_response(raw_bytes, payload):
    """
    Validate each series through its own latest published month.

    Future months are not expected. However, a missing row inside the
    returned January-to-latest interval requires investigation.

    A published "-" measurement is retained as source missing.
    """
    document = json.loads(raw_bytes)

    if document.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError("BLS did not accept the request")

    results = document.get("Results")
    if not isinstance(results, dict):
        raise ValueError("Missing BLS Results object")

    series = results.get("series", [])
    returned_ids = [item["seriesID"] for item in series]

    if (
        len(returned_ids) != len(set(returned_ids))
        or set(returned_ids) != set(payload["seriesid"])
    ):
        raise ValueError("Returned series differ from the request")

    observations = 0
    missing_values = 0
    latest_by_series = {}
    current_month = int(
        datetime.now(timezone.utc).strftime("%Y%m")
    )

    for item in series:
        series_id = item["seriesID"]
        months = []

        for row in item.get("data", []):
            period = row.get("period")

            # Annual averages do not belong in monthly facts.
            if period == "M13":
                continue

            if period not in {
                f"M{month:02d}" for month in range(1, 13)
            }:
                raise ValueError(f"Unexpected period in {series_id}")

            year = int(row["year"])
            month = int(period[1:])
            date_key = year * 100 + month

            if year != CATCHUP_YEAR or date_key > current_month:
                raise ValueError(f"Unexpected date in {series_id}")

            months.append(month)
            value = row.get("value")

            if value == "-":
                missing_values += 1
                continue

            try:
                number = Decimal(value)
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError(
                    f"Invalid measurement in {series_id}/{date_key}"
                )

            if not number.is_finite():
                raise ValueError("Non-finite BLS measurement")

        if not months:
            raise ValueError(f"No catch-up observations: {series_id}")

        latest_month = max(months)

        if (
            len(months) != len(set(months))
            or set(months) != set(range(1, latest_month + 1))
        ):
            raise ValueError(
                f"Duplicate or missing monthly rows: {series_id}"
            )

        observations += len(months)
        latest_by_series[series_id] = (
            CATCHUP_YEAR * 100 + latest_month
        )

    return {
        "series_count": len(series),
        "monthly_observations": observations,
        "source_missing_values": missing_values,
        "latest_month_by_series": latest_by_series,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    series_ids, inventory_bytes = load_series_ids()
    batches = [
        series_ids[index:index + BATCH_SIZE]
        for index in range(0, len(series_ids), BATCH_SIZE)
    ]

    print(
        f"BLS catch-up: {len(series_ids)} series, "
        f"{CATCHUP_YEAR}, {len(batches)} requests."
    )

    if not args.execute:
        print("Dry run only. No requests made or files written.")
        return

    api_key = os.environ.get("BLS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("BLS_API_KEY is not configured")

    metadata = {
        "ingestion_date": (
            datetime.now(timezone.utc).date().isoformat()
        ),
        "run_id": uuid4().hex,
        "mode": "catchup",
    }

    run_dir = (
        BRONZE_ROOT
        / f"ingestion_date={metadata['ingestion_date']}"
        / f"run_id={metadata['run_id']}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)

    # Freeze the definitions used for this specific capture.
    with (run_dir / "inventory.json").open("xb") as file:
        file.write(inventory_bytes)

    summary = {
        **metadata,
        "source": "bls",
        "start_year": CATCHUP_YEAR,
        "end_year": CATCHUP_YEAR,
        "inventory_sha256": checksum(inventory_bytes),
        "status": "in_progress",
        "completed_batches": [],
    }

    print(f"Bronze run: {run_dir}")

    try:
        for number, batch in enumerate(batches, start=1):
            payload = {
                "seriesid": batch,
                "startyear": str(CATCHUP_YEAR),
                "endyear": str(CATCHUP_YEAR),
            }

            result = capture_batch(
                run_dir / f"batch_id={number:03d}",
                payload,
                api_key,
                metadata,
                validator=validate_available_response,
            )

            summary["completed_batches"].append(result)

            print(
                f"Batch {number}/{len(batches)} accepted: "
                f"{result['monthly_observations']} observations."
            )

        # Keep differing publication cutoffs visible rather than silently
        # discarding newer observations to force a common cutoff.
        latest_by_series = {}
        for batch in summary["completed_batches"]:
            latest_by_series.update(batch["latest_month_by_series"])

        summary["latest_month_by_series"] = latest_by_series
        summary["earliest_series_latest_month"] = min(
            latest_by_series.values()
        )
        summary["latest_series_latest_month"] = max(
            latest_by_series.values()
        )
        summary["status"] = "complete"

    except Exception:
        summary["status"] = "failed"
        raise

    finally:
        # Even failed execution records which batches were accepted.
        save_json(run_dir / "summary.json", summary)

    print(
        "Latest returned month range across series: "
        f"{summary['earliest_series_latest_month']}–"
        f"{summary['latest_series_latest_month']}"
    )
    print(f"Catch-up capture complete: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()