"""Supplied pandas transformation for OP-C02.

Learners use the returned DataFrame but do not reimplement this transformation in OP-C02.
"""

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "transaction_id",
    "transaction_date",
    "customer",
    "product",
    "category",
    "quantity",
    "unit_price",
]


def build_valid_sales(input_file: Path) -> pd.DataFrame:
    """Read the fixed source CSV and return validated transactions with sales_amount."""
    if not input_file.is_file():
        raise FileNotFoundError(f"CSV not found at {input_file}")

    raw_df = pd.read_csv(input_file, usecols=REQUIRED_COLUMNS, dtype="string")
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
    return valid_sales_df.assign(
        unit_price=lambda data: data["unit_price"].round(2),
        sales_amount=lambda data: (data["quantity"] * data["unit_price"]).round(2),
    )
