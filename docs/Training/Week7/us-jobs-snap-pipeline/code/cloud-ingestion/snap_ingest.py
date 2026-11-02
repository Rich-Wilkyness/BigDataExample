"""
Capture the current SNAP archive from Cloud Run into cloud Bronze.

Reuses existing download discovery, archive checks, and retry functions.
Discovers the reporting cutoff from the preserved USDA landing page.

The archive remains intact. Only the workbook members required for the
latest six reporting months are indexed in the capture manifest.

State-level parsing and Silver/Gold publication happen afterward.
"""

from datetime import datetime, timezone
from html import unescape
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from google.cloud import storage

from backfill_bls import save_json
from backfill_snap import LANDING_URL, capture_archive, download
from plan_monthly_refresh import reporting_months


MONTHS = {
    name: number
    for number, name in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}


def discover_latest_month(landing_bytes):
    """
    Read publication metadata, not placeholder rows in a workbook.

    Conflicting or missing metadata requires investigation.
    Actual state measurements are validated during Silver processing.
    """
    html = landing_bytes.decode("utf-8", errors="replace")
    text = unescape(re.sub(r"<[^>]+>", " ", html))
    text = " ".join(text.split())

    matches = re.findall(
        r"Latest\s+Available\s+Month\s*[:\-–]\s*"
        r"([A-Za-z]+)\s+(20\d{2})",
        text,
        re.I,
    )
    dates = {
        int(year) * 100 + MONTHS[month[:3].lower()]
        for month, year in matches
    }

    if len(dates) != 1:
        raise ValueError("Missing or conflicting SNAP publication cutoff")

    latest = dates.pop()
    current_month = int(datetime.now(timezone.utc).strftime("%Y%m"))
    if latest > current_month:
        raise ValueError("SNAP publication cutoff is in the future")

    return latest


def main():
    execution = os.environ.get("CLOUD_RUN_EXECUTION")
    if not execution:
        raise RuntimeError("Run this entry point as a Cloud Run Job")

    project_id = os.environ["PROJECT_ID"]
    bucket_name = os.environ["BRONZE_BUCKET"]

    now = datetime.now(timezone.utc)
    ingestion_date = now.date().isoformat()
    prefix = f"snap/ingestion_date={ingestion_date}/run_id={execution}"

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)

    summary = {
        "source": "snap",
        "mode": "monthly_capture",
        "ingestion_date": ingestion_date,
        "run_id": execution,
        "refresh_run_id": os.environ.get("REFRESH_RUN_ID", execution),
        "status": "in_progress",
    }

    with TemporaryDirectory() as temporary:
        # Preserve the directory labels expected by the shared helper.
        run_dir = (
            Path(temporary)
            / f"ingestion_date={ingestion_date}"
            / f"run_id={execution}"
        )
        run_dir.mkdir(parents=True)

        try:
            landing_bytes = download(LANDING_URL)
            (run_dir / "landing.html").write_bytes(landing_bytes)

            latest = discover_latest_month(landing_bytes)
            months = reporting_months(latest)

            fiscal_years = {
                month // 100 + (1 if month % 100 >= 10 else 0)
                for month in months
            }

            # Reuse archive discovery against the exact preserved page.
            from backfill_snap import discover_archive

            archive_url = discover_archive(landing_bytes)

            manifest_path = capture_archive(
                run_dir,
                archive_url,
                required_fiscal_years=fiscal_years,
                mode="monthly_capture",
                target_start_year=months[0] // 100,
                target_end_year=months[-1] // 100,
            )

            relative_manifest = (
                manifest_path.relative_to(run_dir).as_posix()
            )
            summary.update({
                "latest_month": latest,
                "cutoff_origin": "USDA landing-page metadata",
                "target_months": months,
                "required_fiscal_years": sorted(fiscal_years),
                "expected_state_months": 50 * len(months),
                "manifest": (
                    f"gs://{bucket_name}/{prefix}/{relative_manifest}"
                ),
                "validation_scope": (
                    "Archive/workbook structure and checksums; "
                    "state measurements pending Silver validation"
                ),
                "status": "complete",
            })

        except Exception as error:
            summary["status"] = "failed"
            summary["error_type"] = type(error).__name__

            save_json(run_dir / "capture_error.json", {
                "error_type": type(error).__name__,
                "reason": str(error),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            })
            raise

        finally:
            objects = []

            # Preserve original bytes and failed-attempt artifacts.
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

            # Publish completion only after artifact uploads finish.
            summary_uri = f"gs://{bucket_name}/{prefix}/summary.json"
            bucket.blob(f"{prefix}/summary.json").upload_from_string(
                json.dumps(summary, indent=2),
                content_type="application/json",
                if_generation_match=0,
                timeout=120,
            )

            print(json.dumps({
                "status": summary["status"],
                "latest_month": summary.get("latest_month"),
                "target_months": summary.get("target_months"),
                "summary": summary_uri,
            }), flush=True)


if __name__ == "__main__":
    main()
