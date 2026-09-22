"""Supplied OP-C01 runtime fixture.

The lab does not ask the learner to reimplement these pandas transformations. Its purpose is to
provide a real process for the learner's Docker, Compose, PostgreSQL, mount, and Bash setup to run.
"""

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


INPUT_FILE = Path(os.environ["INPUT_FILE"])
OUTPUT_FILE = Path(os.environ["OUTPUT_FILE"])
DATABASE_URL = os.environ["DATABASE_URL"]

REQUIRED_COLUMNS = [
    "transaction_id",
    "transaction_date",
    "customer",
    "product",
    "category",
    "quantity",
    "unit_price",
]

REPORT_QUERY = text(
    """
    SELECT
        category,
        SUM(quantity) AS total_units,
        SUM(sales_amount) AS total_revenue
    FROM reporting.sales_transactions
    GROUP BY category
    ORDER BY total_revenue DESC, category ASC
    """
)


if not INPUT_FILE.is_file():
    raise FileNotFoundError(f"CSV not found at {INPUT_FILE}")

raw_df = pd.read_csv(INPUT_FILE, usecols=REQUIRED_COLUMNS, dtype="string")

valid_sales_df = raw_df.assign(
    transaction_id=lambda data: data["transaction_id"].str.strip(),
    transaction_date=lambda data: pd.to_datetime(
        data["transaction_date"].str.strip(),
        format="%Y-%m-%d",
        errors="coerce",
    ),
    customer=lambda data: data["customer"].str.strip().str.title(),
    product=lambda data: data["product"].str.strip().str.title(),
    category=lambda data: data["category"].str.strip().str.title(),
    quantity=lambda data: pd.to_numeric(data["quantity"], errors="coerce"),
    unit_price=lambda data: pd.to_numeric(data["unit_price"], errors="coerce"),
)

text_columns = ["transaction_id", "customer", "product", "category"]
valid_sales_df[text_columns] = valid_sales_df[text_columns].replace("", pd.NA)

valid_sales_df = (
    valid_sales_df.dropna(subset=REQUIRED_COLUMNS)
    .loc[
        lambda data: (data["quantity"] > 0)
        & (data["quantity"] % 1 == 0)
        & (data["unit_price"] >= 0)
    ]
    .copy()
)

if valid_sales_df.empty:
    raise ValueError("No valid sales rows remain after cleaning")

duplicate_ids = valid_sales_df["transaction_id"].duplicated(keep=False)
if duplicate_ids.any():
    duplicate_values = sorted(valid_sales_df.loc[duplicate_ids, "transaction_id"].unique())
    raise ValueError(f"Duplicate transaction IDs found: {duplicate_values}")

valid_sales_df["quantity"] = valid_sales_df["quantity"].astype("int64")
valid_sales_df["transaction_date"] = valid_sales_df["transaction_date"].dt.date
valid_sales_df = valid_sales_df.assign(
    unit_price=lambda data: data["unit_price"].round(2),
    sales_amount=lambda data: (data["quantity"] * data["unit_price"]).round(2),
)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS reporting"))
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS reporting.sales_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    transaction_date DATE NOT NULL,
                    customer TEXT NOT NULL,
                    product TEXT NOT NULL,
                    category TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price NUMERIC(12, 2) NOT NULL,
                    sales_amount NUMERIC(14, 2) NOT NULL
                )
                """
            )
        )
        connection.execute(text("TRUNCATE TABLE reporting.sales_transactions"))
        valid_sales_df.to_sql(
            name="sales_transactions",
            schema="reporting",
            con=connection,
            if_exists="append",
            index=False,
            method="multi",
        )
        report_df = pd.read_sql_query(REPORT_QUERY, con=connection)
finally:
    engine.dispose()

report_df["total_revenue"] = pd.to_numeric(report_df["total_revenue"])
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
report_df.to_csv(OUTPUT_FILE, index=False, float_format="%.2f")

print(f"Loaded {len(valid_sales_df)} rows into reporting.sales_transactions")
print(f"Report written to {OUTPUT_FILE}")
