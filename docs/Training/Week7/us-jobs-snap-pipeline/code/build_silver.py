"""
Build historical Silver tables from saved BLS and SNAP Bronze captures.

Purpose:
- Verify that Bronze bytes still match their manifests.
- Parse source-specific records without modifying the originals.
- Normalize BLS payroll measurements from thousands of jobs to jobs.
- Preserve missing measurements, source footnotes, and capture lineage.
- Parse SNAP's regional state sections, excluding non-state totals.
- Write new, versioned Parquet outputs using local PySpark.

The baseline is January 2015–December 2025.
This script does not build Gold, upload data, or create cloud resources.
"""

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from uuid import uuid4
from zipfile import ZipFile

import openpyxl
import xlrd
from pyspark.sql import SparkSession, functions as F


PROJECT_DIR = Path(__file__).resolve().parent.parent

START_YEAR = 2015
END_YEAR = 2025

REGIONAL_SHEETS = ("NERO", "MARO", "SERO", "MWRO", "SWRO", "MPRO", "WRO")

MONTH_NUMBERS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

MISSING_MARKERS = {"", "-", "--", "n/a", "na", "...", "…"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_bytes(path, manifest):
    """Reject changed or damaged Bronze files before parsing them."""
    raw = Path(path).read_bytes()

    if (
        len(raw) != manifest["byte_size"]
        or sha256(raw) != manifest["sha256"]
    ):
        raise ValueError(f"Bronze checksum/size mismatch: {path}")

    return raw


def expected_month_keys():
    """Return monthly YYYYMM keys, not a daily calendar."""
    return {
        year * 100 + month
        for year in range(START_YEAR, END_YEAR + 1)
        for month in range(1, 13)
    }


def number(value):
    """
    Parse source numbers without replacing missing measurements with zero.

    Unrecognized nonnumeric text fails rather than becoming an unexplained NULL.
    """
    if value is None:
        return None

    text = str(value).strip()
    if text.lower() in MISSING_MARKERS:
        return None

    try:
        result = Decimal(text.replace(",", "").replace("$", ""))
    except InvalidOperation:
        raise ValueError(f"Unrecognized numeric source value: {value!r}")

    if not result.is_finite():
        raise ValueError(f"Non-finite source value: {value!r}")

    return result


def whole_count(value):
    """SNAP household/person counts are unscaled whole numbers."""
    result = number(value)

    if result is None:
        return None

    if result < 0 or result != result.to_integral_value():
        raise ValueError(f"Invalid household/person count: {value!r}")

    return int(result)


def load_bls_rows(
    bls_run,
    target_months=None,
    *,
    months_by_series=None,
    filter_outside=False,
):
    """Read accepted Bronze batches for an explicitly selected month range."""
    summary = read_json(bls_run / "summary.json")

    # Existing callers retain the original historical baseline defaults.
    requested_months = (
        expected_month_keys()
        if target_months is None
        else set(target_months)
    )
    if not requested_months:
        raise ValueError("No BLS target months selected")

    # Historical callers require an exact year match.
    # Monthly callers may select a smaller window from a wider capture.
    if summary["status"] != "complete":
        raise ValueError("BLS capture is incomplete")

    selected_months = (
        set().union(*(set(months) for months in months_by_series.values()))
        if months_by_series is not None
        else requested_months
    )
    if not selected_months:
        raise ValueError("No BLS target months selected")

    selected_start = min(selected_months) // 100
    selected_end = max(selected_months) // 100

    if filter_outside:
        years_match = (
            summary["start_year"] <= selected_start
            and summary["end_year"] >= selected_end
        )
    else:
        years_match = (
            summary["start_year"] == selected_start
            and summary["end_year"] == selected_end
        )

    if not years_match:
        raise ValueError("BLS capture does not cover the selected years")

    inventory_raw = (bls_run / "inventory.json").read_bytes()
    if sha256(inventory_raw) != summary["inventory_sha256"]:
        raise ValueError("Frozen BLS inventory checksum differs")

    inventory = json.loads(inventory_raw)
    definitions = {
        record["series_id"]: record
        for record in inventory["series"]
    }
    # Each series can have its own latest published month.
    # Require an explicit window for every configured series.
    if months_by_series is None:
        series_months = {
            series_id: requested_months
            for series_id in definitions
        }
    else:
        if set(months_by_series) != set(definitions):
            raise ValueError("BLS month windows differ from the inventory")

        series_months = {
            series_id: set(months)
            for series_id, months in months_by_series.items()
        }
        if any(not months for months in series_months.values()):
            raise ValueError("A BLS series has no target months")

    rows = []
    seen = set()

    for batch in summary["completed_batches"]:
        manifest_path = Path(batch["manifest"]).resolve()

        if not manifest_path.is_relative_to(bls_run):
            raise ValueError("BLS manifest is outside the selected run")

        manifest = read_json(manifest_path)
        raw = checked_bytes(
            manifest_path.parent / manifest["response_filename"],
            manifest,
        )
        document = json.loads(raw)

        if document.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError("Previously accepted BLS response is unsuccessful")

        for series in document["Results"]["series"]:
            series_id = series["seriesID"]

            if series_id not in definitions:
                raise ValueError(f"Unexpected BLS series: {series_id}")

            definition = definitions[series_id]

            for observation in series["data"]:
                period = observation["period"]
                if period == "M13":
                    continue

                month = int(period.removeprefix("M"))
                date_key = int(observation["year"]) * 100 + month

                # Preserve the full Bronze response, but select only this series' window.
                if date_key not in series_months[series_id]:
                    if filter_outside:
                        continue
                    raise ValueError("BLS observation is outside the selected window")

                key = (series_id, date_key)
                if key in seen:
                    raise ValueError(f"Duplicate BLS observation: {key}")
                seen.add(key)

                parsed_value = number(observation["value"])

                rows.append({
                    "series_id": series_id,
                    "state_fips": definition["state_fips"],
                    "state_name": definition["state_name"],
                    "date_key": date_key,
                    "measure": definition["measure"],
                    "industry_code": definition["industry_code"],
                    "industry_name": definition["industry_name"],
                    "source_value": observation["value"],
                    "source_numeric": parsed_value,
                    "source_units": definition["units"],
                    "value_status": (
                        "available"
                        if parsed_value is not None
                        else "source_missing"
                    ),
                    "footnotes": json.dumps(
                        observation.get("footnotes", [])
                    ),
                    "source_manifest": str(manifest_path),
                    "capture_sha256": manifest["sha256"],
                    "retrieval_ts": manifest["retrieval_ts"],
                })

    expected = {
        (series_id, date_key)
        for series_id, months in series_months.items()
        for date_key in months
    }

    if seen != expected:
        raise ValueError(
            f"BLS key coverage differs: "
            f"{len(expected - seen)} missing, {len(seen - expected)} extra"
        )

    return rows, definitions


def workbook_sheets(raw, filename):
    """
    Read regional sheets from XLS or XLSX bytes.

    data_only=True reads Excel's stored values, not formula expressions.
    The original workbook remains untouched inside its Bronze archive.
    """
    if filename.lower().endswith(".xlsx"):
        book = openpyxl.load_workbook(
            BytesIO(raw),
            read_only=True,
            data_only=True,
        )
        try:
            for sheet_name in REGIONAL_SHEETS:
                if sheet_name not in book.sheetnames:
                    raise ValueError(f"Regional sheet missing: {sheet_name}")

                sheet = book[sheet_name]
                rows = list(
                    sheet.iter_rows(
                        min_col=1,
                        max_col=6,
                        values_only=True,
                    )
                )
                yield sheet_name, rows
        finally:
            book.close()

    else:
        book = xlrd.open_workbook(file_contents=raw)
        try:
            for sheet_name in REGIONAL_SHEETS:
                sheet = book.sheet_by_name(sheet_name)
                rows = []

                for row_number in range(sheet.nrows):
                    values = sheet.row_values(row_number)
                    values = (values + [None] * 6)[:6]
                    rows.append(values)

                yield sheet_name, rows
        finally:
            book.release_resources()


def normalized_label(value):
    """Normalize state-section labels, including simple footnote suffixes."""
    return " ".join(
        re.sub(r"[^a-z ]", " ", str(value).lower()).split()
    )


def parse_month_label(value):
    """Parse labels such as 'Jan 2015' or 'Jan 2015 2/'."""
    if isinstance(value, (datetime, date)):
        return value.year, value.month

    match = re.match(r"^\s*([A-Za-z]+)\s+(\d{4})", str(value))
    if not match:
        return None

    month = MONTH_NUMBERS.get(match.group(1)[:3].lower())
    if month is None:
        return None

    return int(match.group(2)), month


def load_snap_rows(manifest_path, definitions, target_months=None):
    """
    Parse state sections on regional sheets, never the national summary.

    State membership comes from the accepted 50-state BLS inventory.
    We preserve negative benefit dollars as published and flag them for review.
    """
    manifest = read_json(manifest_path)
    archive_raw = checked_bytes(
        manifest_path.parent / manifest["response_filename"],
        manifest,
    )

    state_lookup = {
        normalized_label(record["state_name"]): (
            record["state_fips"],
            record["state_name"],
        )
        for record in definitions.values()
    }

    if len(state_lookup) != 50:
        raise ValueError("Expected exactly 50 configured states")

    rows = []
    seen = set()
    target_months = (
        expected_month_keys()
        if target_months is None
        else set(target_months)
)
    with ZipFile(BytesIO(archive_raw)) as archive:
        for member in manifest["members"]:
            raw = archive.read(member["archive_member"])

            if (
                sha256(raw) != member["sha256"]
                or len(raw) != member["byte_size"]
            ):
                raise ValueError("SNAP workbook checksum/size mismatch")

            for sheet_name, sheet_rows in workbook_sheets(
                raw, member["filename"]
            ):
                # Check meaning before using positional columns A–F.
                header = " ".join(
                    str(value or "")
                    for row in sheet_rows[:7]
                    for value in row
                ).lower()

                if not all(
                    word in header
                    for word in ("household", "persons", "cost", "month")
                ):
                    raise ValueError(
                        f"Unexpected SNAP header: "
                        f"{member['filename']}/{sheet_name}"
                    )

                # Preserve explanatory notes alongside row-level lineage.
                notes = [
                    str(row[0]).strip()
                    for row in sheet_rows
                    if row[0] and len(str(row[0])) > 65
                ]
                source_notes = json.dumps(notes)
                report_date = str(sheet_rows[0][5])

                current_state = None

                for row_number, values in enumerate(sheet_rows, start=1):
                    label = values[0]
                    normalized = normalized_label(label)

                    if normalized in state_lookup:
                        current_state = state_lookup[normalized]
                        continue

                    parsed_month = parse_month_label(label)

                    # An unrecognized section heading, such as DC or a
                    # territory, must not inherit the preceding state's name.
                    if (
                        parsed_month is None
                        and str(label or "").strip()
                        and all(
                            value is None or str(value).strip() == ""
                            for value in values[1:6]
                        )
                    ):
                        current_state = None
                        continue

                    if parsed_month is None or current_state is None:
                        continue

                    year, month = parsed_month
                    date_key = year * 100 + month

                    if date_key not in target_months:
                        continue

                    expected_fiscal_year = year + (1 if month >= 10 else 0)
                    if expected_fiscal_year != member["fiscal_year"]:
                        raise ValueError("SNAP month is in the wrong FY member")

                    state_fips, state_name = current_state
                    key = (state_fips, date_key)

                    if key in seen:
                        raise ValueError(f"Duplicate SNAP state/month: {key}")
                    seen.add(key)

                    households = whole_count(values[1])
                    persons = whole_count(values[2])
                    benefits = number(values[3])

                    rows.append({
                        "state_fips": state_fips,
                        "state_name": state_name,
                        "date_key": date_key,
                        "snap_households": households,
                        "snap_persons": persons,
                        "snap_benefit_cost_usd": benefits,
                        "households_status": (
                            "available" if households is not None
                            else "source_missing"
                        ),
                        "persons_status": (
                            "available" if persons is not None
                            else "source_missing"
                        ),
                        "benefits_status": (
                            "source_missing" if benefits is None
                            else "review_required" if benefits < 0
                            else "available"
                        ),
                        "benefit_review_required": (
                            benefits is not None and benefits < 0
                        ),
                        "source_households": str(values[1]),
                        "source_persons": str(values[2]),
                        "source_benefits": str(values[3]),
                        "source_cost_per_household": str(values[4]),
                        "source_cost_per_person": str(values[5]),
                        "source_file": member["filename"],
                        "source_sheet": sheet_name,
                        "source_row": row_number,
                        "source_report_date": report_date,
                        "source_notes": source_notes,
                        "source_manifest": str(manifest_path),
                        "capture_sha256": manifest["sha256"],
                        "workbook_sha256": member["sha256"],
                        "retrieval_ts": manifest["retrieval_ts"],
                    })

    expected = {
        (state_fips, date_key)
        for state_fips, _ in state_lookup.values()
        for date_key in target_months
    }

    if seen != expected:
        raise ValueError(
            f"SNAP key coverage differs: "
            f"{len(expected - seen)} missing, {len(seen - expected)} extra"
        )

    return rows


BLS_SCHEMA = """
    series_id string, state_fips string, state_name string, date_key int,
    measure string, industry_code string, industry_name string,
    source_value string, source_numeric decimal(24,6),
    source_units string, value_status string, footnotes string,
    source_manifest string, capture_sha256 string, retrieval_ts string
"""

SNAP_SCHEMA = """
    state_fips string, state_name string, date_key int,
    snap_households long, snap_persons long,
    snap_benefit_cost_usd decimal(24,2),
    households_status string, persons_status string, benefits_status string,
    benefit_review_required boolean,
    source_households string, source_persons string, source_benefits string,
    source_cost_per_household string, source_cost_per_person string,
    source_file string, source_sheet string, source_row int,
    source_report_date string, source_notes string, source_manifest string,
    capture_sha256 string, workbook_sha256 string, retrieval_ts string
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bls-run", type=Path, required=True)
    parser.add_argument("--snap-manifest", type=Path, required=True)
    args = parser.parse_args()

    bls_run = args.bls_run.resolve()
    snap_manifest = args.snap_manifest.resolve()

    # Parse and check source contracts before starting Spark.
    bls_rows, definitions = load_bls_rows(bls_run)
    snap_rows = load_snap_rows(snap_manifest, definitions)

    print(f"Parsed BLS rows: {len(bls_rows)}")
    print(f"Parsed SNAP rows: {len(snap_rows)}")

    stamp = datetime.now(timezone.utc).date().isoformat()
    output_dir = (
        PROJECT_DIR / "data" / "silver"
        / f"ingestion_date={stamp}"
        / f"run_id={uuid4().hex}"
    )

    spark = (
        SparkSession.builder
        .master("local[2]")
        .appName("JobsSnapHistoricalSilver")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        bls = spark.createDataFrame(bls_rows, schema=BLS_SCHEMA)

        # CES publishes thousands of jobs; LAUS publishes percentages.
        # Normalize intentionally while retaining the original value and unit.
        bls = (
            bls
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

        snap = spark.createDataFrame(snap_rows, schema=SNAP_SCHEMA)

        bls_count = bls.count()
        snap_count = snap.count()
        missing_count = bls.filter(F.col("value").isNull()).count()
        review_count = snap.filter("benefit_review_required").count()

        if bls_count != 32736 or snap_count != 6600:
            raise ValueError("Unexpected historical Silver row counts")

        if bls.filter(
            (F.col("measure") == "unemployment_rate")
            & ((F.col("value") < 0) | (F.col("value") > 100))
        ).count():
            raise ValueError("Unemployment rate outside 0–100 percent")

        if bls.filter(
            (F.col("measure") == "all_employees")
            & (F.col("value") < 0)
        ).count():
            raise ValueError("Negative payroll employment")

        # New output path per run; Bronze files and earlier Silver stay intact.
        output_dir.mkdir(parents=True, exist_ok=False)
        bls.write.mode("errorifexists").parquet(
            str(output_dir / "bls_observations")
        )
        snap.write.mode("errorifexists").parquet(
            str(output_dir / "snap_state_month")
        )

        summary = {
            "status": "complete",
            "start_year": START_YEAR,
            "end_year": END_YEAR,
            "bls_run": str(bls_run),
            "snap_manifest": str(snap_manifest),
            "bls_rows": bls_count,
            "snap_rows": snap_count,
            "bls_source_missing": missing_count,
            "snap_benefit_review_rows": review_count,
        }

        # A complete summary is written only after both outputs succeed.
        with (output_dir / "summary.json").open("x", encoding="utf-8") as file:
            json.dump(summary, file, indent=2)

        print(json.dumps(summary, indent=2))
        print(f"Silver complete: {output_dir}")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()