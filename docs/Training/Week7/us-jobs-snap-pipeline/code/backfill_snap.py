"""
Capture the historical USDA SNAP archive into local Bronze.

Purpose:
- Find the historical ZIP on USDA's SNAP data-tables page.
- Preserve the original ZIP without changing or extracting its contents.
- Identify FY2015–FY2026 workbooks needed for calendar years 2015–2025.
- Record archive/member checksums for later Silver processing.

This does not parse state measurements, upload files, or create cloud resources.
SNAP downloads do not require the BLS API key.
"""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

# Reuse the small, source-independent helpers already in the BLS script.
from backfill_bls import checksum, get_retry_wait, save_json, utc_now


PROJECT_DIR = Path(__file__).resolve().parent.parent
BRONZE_ROOT = PROJECT_DIR / "data" / "bronze" / "snap"

LANDING_URL = (
    "https://fns-prod.azureedge.us/pd/"
    "supplemental-nutrition-assistance-program-snap"
)

START_YEAR = 2015
END_YEAR = 2025

# SNAP fiscal years run October–September.
# October–December 2025 therefore require the FY2026 workbook.
REQUIRED_FISCAL_YEARS = set(range(START_YEAR, END_YEAR + 2))

MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 90
MAX_DOWNLOAD_BYTES = 100_000_000
MAX_SELECTED_WORKBOOK_BYTES = 200_000_000

RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504}


class LinkCollector(HTMLParser):
    """Collect link URLs and visible labels from the official landing page."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []

    def handle_data(self, data):
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href is not None:
            label = " ".join("".join(self.current_text).split())
            self.links.append((self.current_href, label))
            self.current_href = None
            self.current_text = []


def download(url):
    """Download bounded original bytes; leave retry decisions to the caller."""
    request = Request(
        url,
        headers={"User-Agent": "JobsSnapLearning/1.0"},
    )

    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        raw_bytes = response.read(MAX_DOWNLOAD_BYTES + 1)

    if len(raw_bytes) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Download exceeded the configured size limit")

    return raw_bytes


def discover_archive(landing_bytes):
    """
    Locate the historical archive rather than hard-coding a changing filename.

    Match the FY69-through-current label so we don't accidentally download
    the separate Pandemic EBT archive.
    """
    parser = LinkCollector()
    parser.feed(landing_bytes.decode("utf-8", errors="replace"))

    matches = [
        urljoin(LANDING_URL, href)
        for href, label in parser.links
        if re.search(r"FY\s*69\s+through\s+FY\s*\d+", label, re.I)
        and ".zip" in href.lower()
    ]

    matches = list(dict.fromkeys(matches))

    if len(matches) != 1:
        raise ValueError(
            "Could not identify exactly one historical SNAP archive. "
            "Inspect the landing page or provide --archive-url."
        )

    return matches[0]


def inspect_workbooks(archive_bytes, required_fiscal_years=None):
    """
    Validate required workbook members without extracting arbitrary ZIP paths.

    Reading selected members also checks their ZIP CRCs. This validates archive
    structure, not state/month measurement completeness—that comes in Silver.
    """
    required_fiscal_years = (
        REQUIRED_FISCAL_YEARS
        if required_fiscal_years is None
        else set(required_fiscal_years)
    )
    selected = {}
    total_size = 0

    with ZipFile(BytesIO(archive_bytes)) as archive:
        for member in archive.infolist():
            filename = member.filename.replace("\\", "/").split("/")[-1]
            match = re.fullmatch(r"FY(\d{2}|\d{4})\.(xls|xlsx)", filename, re.I)

            if not match:
                continue

            year_text = match.group(1)
            fiscal_year = int(year_text)

            if len(year_text) == 2:
                fiscal_year += 2000 if fiscal_year < 69 else 1900

            if fiscal_year not in required_fiscal_years:
                continue

            if fiscal_year in selected:
                raise ValueError(
                    f"Multiple candidate workbooks for FY{fiscal_year}"
                )

            total_size += member.file_size
            if total_size > MAX_SELECTED_WORKBOOK_BYTES:
                raise ValueError("Selected workbook sizes exceed the limit")

            member_bytes = archive.read(member)

            selected[fiscal_year] = {
                "fiscal_year": fiscal_year,
                "filename": filename,
                "archive_member": member.filename,
                "byte_size": len(member_bytes),
                "sha256": checksum(member_bytes),
            }

    missing = required_fiscal_years - set(selected)
    if missing:
        raise ValueError(f"Required fiscal-year workbooks missing: {sorted(missing)}")

    return [selected[year] for year in sorted(selected)]


def capture_archive(
    run_dir,
    explicit_archive_url=None,
    *,
    required_fiscal_years=None,
    mode="historical",
    target_start_year=START_YEAR,
    target_end_year=END_YEAR,
):
    """Capture an archive, keeping each failed attempt in its own directory."""
    for attempt_number in range(1, MAX_ATTEMPTS + 1):
        attempt_dir = run_dir / f"attempt_id={attempt_number:03d}"
        attempt_dir.mkdir(exist_ok=False)
        active_url = explicit_archive_url or LANDING_URL

        try:
            if explicit_archive_url:
                archive_url = explicit_archive_url
            else:
                landing_bytes = download(LANDING_URL)

                # Preserve the page used to discover this particular archive.
                with (attempt_dir / "landing.html").open("xb") as file:
                    file.write(landing_bytes)

                archive_url = discover_archive(landing_bytes)

            active_url = archive_url
            archive_bytes = download(archive_url)

        except (HTTPError, URLError, TimeoutError, ConnectionError) as error:
            is_http = isinstance(error, HTTPError)
            status = error.code if is_http else None
            retry_after = (
                error.headers.get("Retry-After")
                if is_http and error.headers
                else None
            )

            try:
                preview = (
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
                    "failed_at": utc_now(),
                    "source": "snap",
                    "url": active_url,
                    "error_type": type(error).__name__,
                    "http_status": status,
                    "reason": str(error),
                    "retry_after": retry_after,
                    "body_preview": preview,
                },
            )

            retryable = (
                status in RETRYABLE_HTTP_CODES if is_http else True
            )
            if not retryable or attempt_number == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Download failed. Inspect {attempt_dir / 'error.json'}"
                ) from None

            delay = get_retry_wait(retry_after, attempt_number)
            print(f"Download failed; waiting {delay:.0f}s before retry.")
            time.sleep(delay)
            continue

        retrieved_at = utc_now()

        # Preserve the original download even if structural checks then fail.
        archive_path = attempt_dir / "archive.zip"
        with archive_path.open("xb") as file:
            file.write(archive_bytes)

        try:
            members = inspect_workbooks(
                archive_bytes,
                required_fiscal_years=required_fiscal_years,
            )
        except (BadZipFile, ValueError, RuntimeError) as error:
            save_json(
                attempt_dir / "error.json",
                {
                    "failed_at": utc_now(),
                    "error_type": "ArchiveValidationError",
                    "reason": str(error),
                    "response_filename": "archive.zip",
                    "sha256": checksum(archive_bytes),
                },
            )
            raise RuntimeError(
                f"Archive validation failed. Inspect {attempt_dir}"
            ) from None

        manifest = {
            "source": "snap",
            "mode": mode,
            "landing_url": LANDING_URL,
            "endpoint": archive_url,
            "retrieval_ts": retrieved_at,
            "ingestion_date": run_dir.parent.name.removeprefix(
                "ingestion_date="
            ),
            "run_id": run_dir.name.removeprefix("run_id="),
            "attempt_id": f"{attempt_number:03d}",
            "target_start_year": target_start_year,
            "target_end_year": target_end_year,
            "response_filename": "archive.zip",
            "byte_size": len(archive_bytes),
            "sha256": checksum(archive_bytes),
            "members": members,
            "validation_scope": "ZIP and required workbook members only",
        }

        manifest_path = attempt_dir / "manifest.json"
        save_json(manifest_path, manifest)
        return manifest_path


def main():
    """Inspect configuration by default; download only with --execute."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--archive-url",
        help="Optional explicit historical ZIP URL from the official page.",
    )
    args = parser.parse_args()

    print(
        "SNAP historical capture: calendar years 2015–2025; "
        "required workbooks FY2015–FY2026."
    )

    if not args.execute:
        print("Dry run only. Add --execute to download the archive.")
        return

    ingestion_date = datetime.now(timezone.utc).date().isoformat()
    run_dir = (
        BRONZE_ROOT
        / f"ingestion_date={ingestion_date}"
        / f"run_id={uuid4().hex}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    print(f"Bronze run: {run_dir}")

    manifest_path = capture_archive(run_dir, args.archive_url)
    print(f"SNAP archive accepted: {manifest_path}")


if __name__ == "__main__":
    main()