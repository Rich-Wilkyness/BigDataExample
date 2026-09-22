"""Learner file for OP-C02: Python pipeline setup with SQLAlchemy.

The pandas transformation is supplied in op_c02_sales_transform.py. Complete only the runtime
configuration, database setup/load/query, connection lifecycle, and output-publication functions.
"""

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql.elements import TextClause

from .op_c02_sales_transform import build_valid_sales


def read_runtime_config() -> tuple[Path, Path, str]:
    """Return INPUT_FILE, OUTPUT_FILE, and DATABASE_URL supplied by Docker Compose."""
    raise NotImplementedError("Checkpoint 1: read the three runtime environment variables")


def build_report_query() -> TextClause:
    """Return the SQL aggregation used to create the category sales report."""
    raise NotImplementedError("Checkpoint 2: construct REPORT_QUERY with sqlalchemy.text")


def create_database_engine(database_url: str) -> Engine:
    """Create and return SQLAlchemy's connection manager for the configured database."""
    raise NotImplementedError("Checkpoint 3: create the SQLAlchemy engine")


def create_schema_and_table(connection: Connection) -> None:
    """Create the reporting schema and sales_transactions table when absent."""
    raise NotImplementedError("Checkpoint 4: execute idempotent schema and table DDL")


def replace_transactions(connection: Connection, transactions_df: pd.DataFrame) -> None:
    """Full-refresh the reporting table with the supplied transformed DataFrame."""
    raise NotImplementedError("Checkpoint 5: truncate and load reporting.sales_transactions")


def read_report(connection: Connection, report_query: TextClause) -> pd.DataFrame:
    """Execute the report query and return its result as a DataFrame."""
    raise NotImplementedError("Checkpoint 6: execute REPORT_QUERY with pandas")


def write_report(report_df: pd.DataFrame, output_file: Path) -> None:
    """Create the output directory and write the final report CSV."""
    raise NotImplementedError("Checkpoint 6: publish output/sales_report.csv")


def main() -> None:
    """Run the supplied transform inside the learner-configured database lifecycle."""
    input_file, output_file, database_url = read_runtime_config()
    report_query = build_report_query()

    # OP-C02 treats the transformation as an input to the setup exercise.
    valid_sales_df = build_valid_sales(input_file)

    engine = create_database_engine(database_url)
    try:
        # begin() opens one connection and transaction. Success commits; an exception rolls back.
        with engine.begin() as connection:
            create_schema_and_table(connection)
            replace_transactions(connection, valid_sales_df)
            report_df = read_report(connection, report_query)
    finally:
        engine.dispose()

    write_report(report_df, output_file)
    print(f"Loaded {len(valid_sales_df)} rows into reporting.sales_transactions")
    print(f"Report written to {output_file}")


if __name__ == "__main__":
    main()
