"""
Capture BLS data from Cloud Run into immutable Cloud Storage Bronze.

Reuses:
- backfill_bls: requests, retries, error records, manifests, inventory.
- plan_monthly_refresh: six-reporting-month window calculation.

BLS requests use calendar years. Requesting the previous/current years
provides enough history across January boundaries. Original responses are
preserved, but the accepted refresh window is six months per series.

This job does not update Silver, Gold, or BigQuery.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from google.cloud import storage

from backfill_bls import (
    BATCH_SIZE,
    capture_batch,
    checksum,
    load_series_ids,
)
from plan_monthly_refresh import reporting_months


def validate_recent_response(raw_bytes, payload):
    """Validate each series's latest six monthly observations."""
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

    current_month = int(datetime.now(timezone.utc).strftime("%Y%m"))
    latest_by_series = {}
    missing_values = 0
    raw_observations = 0

    for item in series:
        series_id = item["seriesID"]
        observations = {}

        for row in item.get("data", []):
            period = row.get("period")
            if period == "M13":
                continue

            if period not in {
                f"M{month:02d}" for month in range(1, 13)
            }:
                raise ValueError(f"Unexpected period: {series_id}")

            year = int(row["year"])
            date_key = year * 100 + int(period[1:])

            if (
                not int(payload["startyear"]) <= year
                <= int(payload["endyear"])
                or date_key > current_month
            ):
                raise ValueError(f"Unexpected reporting month: {series_id}")

            if date_key in observations:
                raise ValueError(f"Duplicate month: {series_id}/{date_key}")

            observations[date_key] = row

        if not observations:
            raise ValueError(f"No monthly observations: {series_id}")

        latest = max(observations)
        selected_months = reporting_months(latest)

        if not set(selected_months).issubset(observations):
            raise ValueError(f"Missing rows inside refresh window: {series_id}")

        # Validate selected measurements; retain published missing markers.
        for date_key in selected_months:
            value = observations[date_key].get("value")

            if value == "-":
                missing_values += 1
                continue

            try:
                parsed = Decimal(value)
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError(
                    f"Invalid measurement: {series_id}/{date_key}"
                )

            if not parsed.is_finite():
                raise ValueError("Non-finite BLS measurement")

        latest_by_series[series_id] = latest
        raw_observations += len(observations)

    return {
        "series_count": len(series),
        "monthly_observations": len(series) * 6,
        "raw_monthly_observations": raw_observations,
        "source_missing_values": missing_values,
        "latest_month_by_series": latest_by_series,
    }


def main():
    """Capture batches, preserve artifacts, and publish the run summary last."""
    execution = os.environ.get("CLOUD_RUN_EXECUTION")
    if not execution:
        raise RuntimeError("Run this entry point as a Cloud Run Job")

    api_key = os.environ.get("BLS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("BLS_API_KEY was not injected")

    project_id = os.environ["PROJECT_ID"]
    bucket_name = os.environ["BRONZE_BUCKET"]

    now = datetime.now(timezone.utc)
    ingestion_date = now.date().isoformat()

    # One capture per Cloud Run execution. Workflows will later provide a
    # logical refresh ID linking source captures and publication.
    run_id = execution
    refresh_run_id = os.environ.get("REFRESH_RUN_ID", execution)

    prefix = f"bls/ingestion_date={ingestion_date}/run_id={run_id}"
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)

    series_ids, inventory_bytes = load_series_ids()
    batches = [
        series_ids[index:index + BATCH_SIZE]
        for index in range(0, len(series_ids), BATCH_SIZE)
    ]

    metadata = {
        "source": "bls",
        "mode": "monthly_capture",
        "ingestion_date": ingestion_date,
        "run_id": run_id,
        "refresh_run_id": refresh_run_id,
    }
    summary = {
        **metadata,
        "status": "in_progress",
        "start_year": now.year - 1,
        "end_year": now.year,
        "inventory_sha256": checksum(inventory_bytes),
        "validation_scope": "latest six reporting months per series",
        "completed_batches": [],
    }

    with TemporaryDirectory() as temporary:
        run_dir = Path(temporary)
        (run_dir / "inventory.json").write_bytes(inventory_bytes)

        try:
            for number, batch in enumerate(batches, start=1):
                payload = {
                    "seriesid": batch,
                    "startyear": str(now.year - 1),
                    "endyear": str(now.year),
                }

                result = capture_batch(
                    run_dir / f"batch_id={number:03d}",
                    payload,
                    api_key,
                    metadata,
                    validator=validate_recent_response,
                )

                # Cloud descriptors use portable object URIs.
                relative_manifest = (
                    Path(result["manifest"]).relative_to(run_dir).as_posix()
                )
                result["manifest"] = (
                    f"gs://{bucket_name}/{prefix}/{relative_manifest}"
                )
                summary["completed_batches"].append(result)

                print(
                    f"Batch {number}/{len(batches)} accepted: "
                    f"{result['monthly_observations']} "
                    "six-month observations.",
                    flush=True,
                )

            latest = {}
            for batch in summary["completed_batches"]:
                latest.update(batch["latest_month_by_series"])

            summary["latest_month_by_series"] = latest
            summary["refresh_months_by_series"] = {
                series_id: reporting_months(month)
                for series_id, month in latest.items()
            }
            summary["earliest_series_latest_month"] = min(latest.values())
            summary["latest_series_latest_month"] = max(latest.values())
            summary["status"] = "complete"

        except Exception as error:
            summary["status"] = "failed"
            summary["error_type"] = type(error).__name__
            raise

        finally:
            # Preserve failed attempts as well as successful responses.
            # Original response bytes and existing manifests are unchanged.
            objects = []
            for path in sorted(run_dir.rglob("*")):
                if not path.is_file():
                    continue

                relative = path.relative_to(run_dir).as_posix()
                object_name = f"{prefix}/{relative}"

                bucket.blob(object_name).upload_from_filename(
                    str(path),
                    if_generation_match=0,
                    timeout=120,
                )
                objects.append(f"gs://{bucket_name}/{object_name}")

            summary["objects"] = objects
            summary["finished_at"] = datetime.now(timezone.utc).isoformat()

            # Publish the summary only after artifact uploads finish.
            summary_uri = f"gs://{bucket_name}/{prefix}/summary.json"
            bucket.blob(f"{prefix}/summary.json").upload_from_string(
                json.dumps(summary, indent=2),
                content_type="application/json",
                if_generation_match=0,
                timeout=120,
            )

            print(json.dumps({
                "status": summary["status"],
                "summary": summary_uri,
            }), flush=True)


if __name__ == "__main__":
    main()