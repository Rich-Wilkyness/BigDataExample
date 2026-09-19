"""Deterministic source delivery for the WH-M01 medallion lab."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from big_data_example.labs.retail_sales.wh_m01_database import repository_root


LAB_ID = "WH-M01"
DELIVERY_ID = "retail-sales-batch-001"
SCHEMA_VERSION = 1
GENERATOR_SEED = 20260917
SOURCE_FILENAME = "sales-transactions.csv"
MANIFEST_FILENAME = "manifest.json"
EXPECTED_ROW_COUNT = 40
SOURCE_COLUMNS = (
    "transaction_id",
    "transaction_date",
    "product_number",
    "product_name",
    "category",
    "customer_number",
    "customer_name",
    "customer_city",
    "quantity",
    "unit_price",
    "currency",
)

PRODUCTS = (
    ("P100", "Laptop Stand", "Office Accessories", Decimal("45.00")),
    ("P200", "Mechanical Keyboard", "Electronics", Decimal("120.00")),
    ("P300", "Monitor", "Electronics", Decimal("300.00")),
    ("P400", "Standing Desk", "Furniture", Decimal("550.00")),
    ("P500", "Webcam", "Electronics", Decimal("80.00")),
)
CUSTOMERS = (
    ("C100", "Ana Rivera", "Boise"),
    ("C200", "Marcus Lee", "Denver"),
    ("C300", "Priya Shah", "Chicago"),
    ("C400", "Jordan Kim", "Seattle"),
    ("C500", "Maya Patel", "Boston"),
)
INTENTIONAL_QUALITY_CASES = {
    "leading_and_trailing_whitespace": [3, 20],
    "inconsistent_capitalization": [5],
    "invalid_date": [7],
    "missing_date": [8],
    "missing_price": [9],
    "nonnumeric_price": [10],
    "zero_quantity": [11],
    "negative_quantity": [12],
    "duplicated_transaction_id": [13, 14],
    "unsupported_currency": [15],
    "missing_product_number": [16],
    "missing_customer_number": [17],
    "missing_transaction_id": [18],
    "customer_city_change": [1, 31],
}


def source_directory(root: Path | None = None) -> Path:
    """Return the tracked batch directory for this lab's source delivery."""

    project_root = root or repository_root()
    return (
        project_root
        / "data"
        / "samples"
        / "interactive-data-engineering-labs"
        / "retail-sales"
        / "wh-m01-medallion-sales-pipeline"
        / "source"
        / "batch-001"
    )


def build_source_records() -> list[dict[str, str]]:
    """Build the same 40 source-oriented transaction records on every run."""

    generator = random.Random(GENERATOR_SEED)
    first_date = date(2024, 1, 15)
    records: list[dict[str, str]] = []

    for index in range(EXPECTED_ROW_COUNT):
        product_number, product_name, category, unit_price = generator.choice(PRODUCTS)
        customer_number, customer_name, customer_city = generator.choice(CUSTOMERS)
        transaction_date = first_date + timedelta(days=index * 23)
        if customer_number == "C100" and transaction_date >= date(2025, 12, 1):
            customer_city = "Meridian"
        records.append(
            {
                "transaction_id": f"TXN-{1001 + index}",
                "transaction_date": transaction_date.isoformat(),
                "product_number": product_number,
                "product_name": product_name,
                "category": category,
                "customer_number": customer_number,
                "customer_name": customer_name,
                "customer_city": customer_city,
                "quantity": str(generator.randint(1, 5)),
                "unit_price": f"{unit_price:.2f}",
                "currency": "USD",
            }
        )

    records[0].update(
        transaction_date="2024-01-15",
        customer_number="C100",
        customer_name="Ana Rivera",
        customer_city="Boise",
    )
    records[30].update(
        transaction_date="2025-12-01",
        customer_number="C100",
        customer_name="Ana Rivera",
        customer_city="Meridian",
    )

    records[2]["product_number"] = f" {records[2]['product_number']} "
    records[2]["category"] = f" {records[2]['category']} "
    records[4]["product_name"] = records[4]["product_name"].upper()
    records[4]["category"] = records[4]["category"].lower()
    records[4]["currency"] = "usd"
    records[6]["transaction_date"] = "2025-13-40"
    records[7]["transaction_date"] = ""
    records[8]["unit_price"] = ""
    records[9]["unit_price"] = "not-a-price"
    records[10]["quantity"] = "0"
    records[11]["quantity"] = "-2"
    records[13]["transaction_id"] = records[12]["transaction_id"]
    records[14]["currency"] = "EUR"
    records[15]["product_number"] = ""
    records[16]["customer_number"] = ""
    records[17]["transaction_id"] = ""
    records[19]["customer_city"] = f" {records[19]['customer_city']} "

    return records


def build_csv_bytes() -> bytes:
    """Serialize source records with stable column order and line endings."""

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=SOURCE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(build_source_records())
    return buffer.getvalue().encode("utf-8")


def build_manifest(csv_bytes: bytes | None = None) -> dict[str, object]:
    """Build the integrity and learning contract for the source delivery."""

    content = csv_bytes if csv_bytes is not None else build_csv_bytes()
    return {
        "lab_id": LAB_ID,
        "delivery_id": DELIVERY_ID,
        "schema_version": SCHEMA_VERSION,
        "generator_seed": GENERATOR_SEED,
        "source_file": SOURCE_FILENAME,
        "row_count": EXPECTED_ROW_COUNT,
        "sha256": hashlib.sha256(content).hexdigest(),
        "columns": list(SOURCE_COLUMNS),
        "intentional_quality_cases": INTENTIONAL_QUALITY_CASES,
    }


def verify_source_delivery(directory: Path | None = None) -> dict[str, object]:
    """Verify files against both their manifest and deterministic generator."""

    batch_directory = directory or source_directory()
    csv_path = batch_directory / SOURCE_FILENAME
    manifest_path = batch_directory / MANIFEST_FILENAME
    if not csv_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError(
            f"Source delivery is incomplete in {batch_directory}; run generate-source.py."
        )

    actual_bytes = csv_path.read_bytes()
    actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_bytes = build_csv_bytes()
    expected_manifest = build_manifest(expected_bytes)

    if actual_bytes != expected_bytes:
        raise ValueError(
            "Source CSV differs from the deterministic WH-M01 delivery. "
            "Regenerate it with generate-source.py --force."
        )
    if actual_manifest != expected_manifest:
        raise ValueError(
            "Source manifest differs from the deterministic WH-M01 contract. "
            "Regenerate it with generate-source.py --force."
        )

    with csv_path.open(newline="", encoding="utf-8") as source_file:
        reader = csv.DictReader(source_file)
        rows = list(reader)
    if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
        raise ValueError("Source CSV columns do not match the WH-M01 source contract.")
    if len(rows) != EXPECTED_ROW_COUNT:
        raise ValueError(
            f"Source CSV has {len(rows)} rows; expected {EXPECTED_ROW_COUNT}."
        )

    return actual_manifest


def write_source_delivery(
    directory: Path | None = None,
    *,
    force: bool = False,
) -> tuple[Path, Path]:
    """Write or restore the deterministic delivery without silent overwrites."""

    batch_directory = directory or source_directory()
    csv_path = batch_directory / SOURCE_FILENAME
    manifest_path = batch_directory / MANIFEST_FILENAME

    if csv_path.exists() or manifest_path.exists():
        if not force:
            verify_source_delivery(batch_directory)
            return csv_path, manifest_path

    batch_directory.mkdir(parents=True, exist_ok=True)
    csv_bytes = build_csv_bytes()
    manifest = build_manifest(csv_bytes)
    csv_path.write_bytes(csv_bytes)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    verify_source_delivery(batch_directory)
    return csv_path, manifest_path
