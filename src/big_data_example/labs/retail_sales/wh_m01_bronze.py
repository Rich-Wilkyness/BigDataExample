"""Bronze-layer loading and Stage 1 checks for WH-M01."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from big_data_example.labs.retail_sales.wh_m01_database import (
    LAB_DATABASE,
    make_engine,
    repository_root,
)
from big_data_example.labs.retail_sales.wh_m01_source import (
    DELIVERY_ID,
    EXPECTED_ROW_COUNT,
    SOURCE_COLUMNS,
    SOURCE_FILENAME,
    source_directory,
    verify_source_delivery,
)


def bronze_sql_path(root: Path | None = None) -> Path:
    project_root = root or repository_root()
    return (
        project_root
        / "sql"
        / "interactive-data-engineering-labs"
        / "retail-sales"
        / "wh-m01-medallion-sales-pipeline"
        / "01-create-bronze.sql"
    )


def create_bronze_schema(root: Path | None = None) -> None:
    """Create only the WH-M01 Bronze schema and raw table."""

    sql = bronze_sql_path(root).read_text(encoding="utf-8")
    engine = make_engine(LAB_DATABASE, root)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(sql)
    finally:
        engine.dispose()


def load_bronze(root: Path | None = None) -> int:
    """Replace one source batch in Bronze and return its loaded row count."""

    batch_directory = source_directory(root)
    verify_source_delivery(batch_directory)
    csv_path = batch_directory / SOURCE_FILENAME
    with csv_path.open(newline="", encoding="utf-8") as source_file:
        source_rows = list(csv.DictReader(source_file))

    rows_to_load = [
        {
            "source_batch_id": DELIVERY_ID,
            "source_file_name": SOURCE_FILENAME,
            "source_row_number": row_number,
            **source_row,
        }
        for row_number, source_row in enumerate(source_rows, start=1)
    ]

    column_names = (
        "source_batch_id",
        "source_file_name",
        "source_row_number",
        *SOURCE_COLUMNS,
    )
    insert_columns = ", ".join(column_names)
    insert_values = ", ".join(f":{column}" for column in column_names)
    insert_sql = text(
        f"INSERT INTO bronze.sales_transactions ({insert_columns}) "
        f"VALUES ({insert_values})"
    )

    engine = make_engine(LAB_DATABASE, root)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "DELETE FROM bronze.sales_transactions "
                    "WHERE source_batch_id = :source_batch_id"
                ),
                {"source_batch_id": DELIVERY_ID},
            )
            connection.execute(insert_sql, rows_to_load)
    finally:
        engine.dispose()
    return len(rows_to_load)


def read_bronze(root: Path | None = None) -> pd.DataFrame:
    """Read Bronze in stable source-row order for notebook inspection."""

    engine = make_engine(LAB_DATABASE, root)
    try:
        return pd.read_sql_query(
            text(
                "SELECT * FROM bronze.sales_transactions "
                "WHERE source_batch_id = :source_batch_id "
                "ORDER BY source_row_number"
            ),
            engine,
            params={"source_batch_id": DELIVERY_ID},
        )
    finally:
        engine.dispose()


def check_stage1(root: Path | None = None) -> dict[str, object]:
    """Validate manifest integrity, Bronze preservation, count, and lineage."""

    manifest = verify_source_delivery(source_directory(root))
    batch_directory = source_directory(root)
    with (batch_directory / SOURCE_FILENAME).open(
        newline="", encoding="utf-8"
    ) as source_file:
        source_rows = list(csv.DictReader(source_file))

    bronze_df = read_bronze(root)
    if bronze_df.shape[0] != EXPECTED_ROW_COUNT:
        raise AssertionError(
            f"Bronze has {bronze_df.shape[0]} rows; expected {EXPECTED_ROW_COUNT}."
        )
    if bronze_df["source_row_number"].nunique() != EXPECTED_ROW_COUNT:
        raise AssertionError("Bronze source_row_number values are not unique.")
    if set(bronze_df["source_batch_id"]) != {DELIVERY_ID}:
        raise AssertionError("Bronze contains an unexpected source_batch_id.")
    if set(bronze_df["source_file_name"]) != {SOURCE_FILENAME}:
        raise AssertionError("Bronze contains an unexpected source_file_name.")

    for zero_based_index, source_row in enumerate(source_rows):
        bronze_row = bronze_df.iloc[zero_based_index]
        for column in SOURCE_COLUMNS:
            if bronze_row[column] != source_row[column]:
                raise AssertionError(
                    f"Bronze changed source row {zero_based_index + 1} column {column}."
                )

    return {
        "status": "PASS",
        "delivery_id": manifest["delivery_id"],
        "source_rows": len(source_rows),
        "bronze_rows": int(bronze_df.shape[0]),
        "bronze_columns": int(bronze_df.shape[1]),
        "sha256": manifest["sha256"],
    }
