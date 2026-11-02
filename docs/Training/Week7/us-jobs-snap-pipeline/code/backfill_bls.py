"""
Historical BLS backfill: all configured series for January 2015–December 2025.

Purpose:
- Read the operational series inventory.
- Request historical data in registered-API batches.
- Preserve original response bytes and request metadata in local Bronze.
- Stop if the returned series/month coverage is incomplete.

This is a manually executed historical loader, not a scheduler.
It does not transform data, upload files, or create cloud resources.
"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


PROJECT_DIR = Path(__file__).resolve().parent.parent
INVENTORY_PATH = PROJECT_DIR / "config" / "bls-series-inventory.json"
BRONZE_ROOT = PROJECT_DIR / "data" / "bronze" / "bls"

BLS_ENDPOINT = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

START_YEAR = 2015
END_YEAR = 2025
BATCH_SIZE = 50                 # Registered BLS API limit.
MAX_ATTEMPTS = 3               # Three total attempts per batch.
REQUEST_TIMEOUT_SECONDS = 60
MAX_RETRY_WAIT_SECONDS = 60
MAX_RESPONSE_BYTES = 10_000_000

RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504}


def utc_now():
    """Return a timezone-aware timestamp for capture metadata."""
    return datetime.now(timezone.utc).isoformat()


def checksum(raw_bytes):
    """Identify the exact bytes saved, independently of their filename."""
    return hashlib.sha256(raw_bytes).hexdigest()


def save_json(path, value):
    """Create a new JSON artifact; never silently overwrite an existing file."""
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, indent=2)
        file.write("\n")


def redact(text, api_key):
    """Remove the credential if a server error happens to echo it."""
    return str(text).replace(api_key, "[REDACTED]")


def load_series_ids():
    """Load selected IDs from configuration, not historical evidence."""
    inventory_bytes = INVENTORY_PATH.read_bytes()
    inventory = json.loads(inventory_bytes)
    series_ids = [record["series_id"] for record in inventory["series"]]

    if len(series_ids) != 248 or len(set(series_ids)) != 248:
        raise ValueError("Expected 248 unique series in the accepted inventory")

    return series_ids, inventory_bytes


def validate_response(raw_bytes, payload):
    """
    Check source acceptance separately from HTTP success.

    A successful HTTP request can still return an API error, an empty series,
    or truncated history. Missing-value markers remain legitimate source data;
    they are counted here and will become NULL/status-aware values in Silver.
    """
    document = json.loads(raw_bytes)

    if document.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError(
            f"BLS rejected the request: {document.get('status')}"
        )

    results = document.get("Results")
    if not isinstance(results, dict):
        raise ValueError("BLS response has no valid Results object")

    returned = results.get("series", [])
    returned_ids = [series["seriesID"] for series in returned]

    if (
        len(returned_ids) != len(set(returned_ids))
        or set(returned_ids) != set(payload["seriesid"])
    ):
        raise ValueError("Returned series do not match the requested series")

    expected_months = {
        (str(year), f"M{month:02d}")
        for year in range(
            int(payload["startyear"]),
            int(payload["endyear"]) + 1,
        )
        for month in range(1, 13)
    }

    observation_count = 0
    missing_value_count = 0

    for series in returned:
        # M13 is an annual average, not one of our monthly observations.
        observations = [
            row
            for row in series.get("data", [])
            if row.get("period") != "M13"
        ]
        months = [(row["year"], row["period"]) for row in observations]

        if (
            len(months) != len(set(months))
            or set(months) != expected_months
        ):
            raise ValueError(
                f"Incomplete or duplicate monthly history: "
                f"{series['seriesID']}"
            )

        for row in observations:
            value = row.get("value")

            if value == "-":
                missing_value_count += 1
                continue

            try:
                number = Decimal(value)
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError(
                    f"Unexpected measurement in {series['seriesID']}: "
                    f"{row['year']}/{row['period']}"
                )

            if not number.is_finite():
                raise ValueError("Non-finite BLS measurement")

        observation_count += len(observations)

    return {
        "series_count": len(returned),
        "monthly_observations": observation_count,
        "source_missing_values": missing_value_count,
    }


def get_retry_wait(retry_after, attempt_number):
    """
    Respect the server's requested wait when supplied.

    Long or malformed waits stop this manual run instead of retrying early.
    Without a server instruction, wait five seconds, then fifteen seconds.
    """
    fallback = 5 * (3 ** (attempt_number - 1))

    if retry_after is None:
        return fallback

    value = retry_after.strip()

    if value.isascii() and value.isdigit():
        requested_wait = float(value)
    else:
        retry_at = parsedate_to_datetime(value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)

        requested_wait = max(
            0,
            (retry_at - datetime.now(timezone.utc)).total_seconds(),
        )

    delay = max(fallback, requested_wait)

    if delay > MAX_RETRY_WAIT_SECONDS:
        raise RuntimeError(
            "Server requested a longer wait. Stop and inspect the saved error."
        )

    return delay


def capture_batch(
    batch_dir,
    payload,
    api_key,
    run_metadata,
    validator=validate_response,
):
    """
    Capture one batch, preserving each failed attempt separately.

    Only the outgoing copy contains the API key. The payload saved in manifests
    and used for request identity remains credential-free.
    """
    request_id = checksum(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    )

    for attempt_number in range(1, MAX_ATTEMPTS + 1):
        attempt_dir = batch_dir / f"attempt_id={attempt_number:03d}"
        attempt_dir.mkdir(parents=True, exist_ok=False)

        request_payload = {
            **payload,
            "registrationkey": api_key,
        }
        request = Request(
            BLS_ENDPOINT,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "JobsSnapLearning/1.0",
            },
            method="POST",
        )

        started_at = utc_now()

        try:
            with urlopen(
                request,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                raw_bytes = response.read(MAX_RESPONSE_BYTES + 1)

        except (HTTPError, URLError, TimeoutError, ConnectionError) as error:
            is_http = isinstance(error, HTTPError)
            status = error.code if is_http else None
            retry_after = (
                error.headers.get("Retry-After")
                if is_http and error.headers
                else None
            )

            try:
                body_preview = (
                    error.read(2048).decode("utf-8", errors="replace")
                    if is_http
                    else ""
                )
            finally:
                if is_http:
                    error.close()

            save_json(
                attempt_dir / "error.json",
                {
                    **run_metadata,
                    "request_id": request_id,
                    "attempt_id": f"{attempt_number:03d}",
                    "failed_at": utc_now(),
                    "endpoint": BLS_ENDPOINT,
                    "request_params": payload,
                    "error_type": type(error).__name__,
                    "http_status": status,
                    "reason": redact(error, api_key),
                    "retry_after": retry_after,
                    "body_preview": redact(body_preview, api_key),
                },
            )

            retryable = (
                status in RETRYABLE_HTTP_CODES if is_http else True
            )

            if not retryable or attempt_number == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Batch failed. Inspect {attempt_dir / 'error.json'}"
                ) from None

            delay = get_retry_wait(retry_after, attempt_number)
            print(
                f"Attempt {attempt_number} failed; "
                f"waiting {delay:.0f}s before retry."
            )
            time.sleep(delay)
            continue

        retrieved_at = utc_now()

        if len(raw_bytes) > MAX_RESPONSE_BYTES:
            raise ValueError("Response exceeded the configured size limit")

        # Prevent accidental credential persistence if a server echoes the key.
        if api_key.encode("utf-8") in raw_bytes:
            raise ValueError("Response unexpectedly contains the API key")

        response_path = attempt_dir / "response.json"
        with response_path.open("xb") as file:
            file.write(raw_bytes)

        try:
            validation = validator(raw_bytes, payload)
        except (ValueError, KeyError, TypeError) as error:
            save_json(
                attempt_dir / "error.json",
                {
                    "failed_at": utc_now(),
                    "error_type": "SourceValidationError",
                    "reason": redact(error, api_key),
                    "request_id": request_id,
                    "request_params": payload,
                    "response_filename": "response.json",
                },
            )
            raise RuntimeError(
                f"Source checks failed. Inspect {attempt_dir}"
            ) from None

        manifest = {
            **run_metadata,
            "source": "bls",
            "endpoint": BLS_ENDPOINT,
            "request_id": request_id,
            "attempt_id": f"{attempt_number:03d}",
            "request_started_at": started_at,
            "retrieval_ts": retrieved_at,
            "request_params": payload,
            "response_filename": "response.json",
            "byte_size": len(raw_bytes),
            "sha256": checksum(raw_bytes),
            "validation": validation,
        }
        save_json(attempt_dir / "manifest.json", manifest)

        return {
            "manifest": str(attempt_dir / "manifest.json"),
            **validation,
        }


def main():
    """Inspect the plan by default; fetch only when --execute is supplied."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Make live BLS requests and save local Bronze captures.",
    )
    args = parser.parse_args()

    series_ids, inventory_bytes = load_series_ids()
    batches = [
        series_ids[index:index + BATCH_SIZE]
        for index in range(0, len(series_ids), BATCH_SIZE)
    ]

    print(
        f"Historical plan: {len(series_ids)} series, "
        f"{START_YEAR}–{END_YEAR}, {len(batches)} requests."
    )

    if not args.execute:
        print("Dry run only. Add --execute to perform ingestion.")
        return

    api_key = os.environ.get("BLS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("BLS_API_KEY is not configured in this terminal")

    metadata = {
        "ingestion_date": datetime.now(timezone.utc).date().isoformat(),
        "run_id": uuid4().hex,
    }
    run_dir = (
        BRONZE_ROOT
        / f"ingestion_date={metadata['ingestion_date']}"
        / f"run_id={metadata['run_id']}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)

    # Freeze the exact definitions used for this run.
    with (run_dir / "inventory.json").open("xb") as file:
        file.write(inventory_bytes)

    summary = {
        **metadata,
        "source": "bls",
        "mode": "historical",
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "inventory_sha256": checksum(inventory_bytes),
        "status": "in_progress",
        "completed_batches": [],
    }

    print(f"Bronze run: {run_dir}")

    try:
        for batch_number, batch in enumerate(batches, start=1):
            payload = {
                "seriesid": batch,
                "startyear": str(START_YEAR),
                "endyear": str(END_YEAR),
            }

            result = capture_batch(
                run_dir / f"batch_id={batch_number:03d}",
                payload,
                api_key,
                metadata,
            )
            summary["completed_batches"].append(result)
            print(
                f"Batch {batch_number}/{len(batches)} accepted: "
                f"{result['monthly_observations']} monthly observations."
            )

        summary["status"] = "complete"

    except Exception as error:
        summary["status"] = "failed"
        summary["error"] = redact(error, api_key)
        raise

    finally:
        # A failed run still records which batches completed.
        save_json(run_dir / "summary.json", summary)

    print(f"Historical capture complete: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
