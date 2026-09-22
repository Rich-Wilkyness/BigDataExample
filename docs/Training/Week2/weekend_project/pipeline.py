import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

# Compose creates these environment variables when it starts the pipeline container. INPUT_FILE and
# OUTPUT_FILE are container paths; their bind mounts point back to files/directories on the host.
INPUT_FILE = Path(os.environ["INPUT_FILE"])
OUTPUT_FILE = Path(os.environ.get(
    "OUTPUT_FILE",
    "/app/output/sales_report.csv"
    )
)

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"CSV not found at {INPUT_FILE}")

DATABASE_URL = os.environ["DATABASE_URL"]

# This is SQL executed by PostgreSQL after pandas loads the cleaned transaction rows. Pandas only
# receives the aggregated result; GROUP BY, SUM, and ORDER BY run inside the database.
REPORT_QUERY = text(
    """
    SELECT
        category,
        SUM(quantity) AS total_units,
        SUM(sales_amount) AS total_revenue
    FROM silver.sales_transactions
    GROUP BY category
    ORDER BY total_revenue DESC
    """
)

REQUIRED_COLUMNS = [
    "transaction_id",
    "transaction_date",
    "customer",
    "product",
    "category",
    "quantity",
    "unit_price"
]

df = pd.read_csv(
    INPUT_FILE,
    usecols=REQUIRED_COLUMNS,
    dtype="string",
)

print("DataFrame shape:", df.shape)
print("Types:", df.dtypes)

# transaction_id,transaction_date,customer,product,category,quantity,unit_price
# T001,2026-09-01,Alice,Laptop,Electronics,1,1200


# Clean/validate and Transform the data
valid_sales = df.assign(
    # EX: T001 str
    transaction_id = lambda data: (
        data["transaction_id"]
        .str.strip()
    ),
    # 2026-09-01 data
    transaction_date = lambda data: pd.to_datetime(
        data["transaction_date"].str.strip(),
        format="%Y-%m-%d",
        errors="coerce"
    ),
    # Alice str
    customer = lambda data: (
        data["customer"]
        .str.strip()
        .str.title()
    ),
    # Laptop str
    product = lambda data: (
        data["product"]
        .str.strip()
        .str.title()
    ),
    # Electronics str
    category = lambda data: (
        data["category"]
        .str.strip()
        .str.title()
    ),
    # 1 int64
    quantity = lambda data: pd.to_numeric(
        data["quantity"], errors="coerce"
    ),
    # 1200 float64
    unit_price = lambda data: pd.to_numeric(
        data["unit_price"], errors="coerce"
    )
)

# blank strings
text_columns = [
    "transaction_id",
    "customer",
    "product",
    "category",
]

valid_sales[text_columns] = (
    valid_sales[text_columns]
    .replace("", pd.NA)
)

valid_sales = (
    valid_sales
    .dropna(subset=REQUIRED_COLUMNS)
    .loc[
        lambda data:
            (data["quantity"] > 0) # greater than 0
            & (data["quantity"] % 1 == 0) # whole number
            & (data["unit_price"] >= 0)
    ]
    .copy()
)

# convert to int
valid_sales["quantity"] = valid_sales["quantity"].astype("int64")

# convert to date
valid_sales["transaction_date"] = valid_sales["transaction_date"].dt.date

# create sales_amount and round our numbers
valid_sales = (
    valid_sales.assign(
        unit_price = lambda data: data["unit_price"].round(2),
        sales_amount = lambda data: (
            data["quantity"] * data["unit_price"]
        ).round(2),
    )
)

# other options:
# 1. check if we have data after cleaning and removing
# 2. check if duplicate transaction_id exist


# LOAD STAGE: create/verify database objects, replace the table's rows, and generate the report.

# An Engine is SQLAlchemy's database connection manager. It does not create PostgreSQL or the sales
# database; Compose already did that. It stores the connection URL and opens connections as needed.
engine = create_engine(DATABASE_URL)

try:
    # engine.begin() opens one connection and one transaction. Leaving this block successfully
    # commits every CREATE/TRUNCATE/INSERT operation; an exception rolls the transaction back.
    with engine.begin() as connection:
        # IF NOT EXISTS makes setup repeatable: the first run creates the schema/table, and later
        # runs reuse them from PostgreSQL's persistent volume.
        connection.execute(
            text(
                """
                CREATE SCHEMA IF NOT EXISTS silver
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS silver.sales_transactions(
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

        connection.execute(
            # TRUNCATE makes this a full-refresh pipeline: remove the prior run's rows, then load
            # the current CSV below. The table definition itself remains in PostgreSQL.
            text("TRUNCATE TABLE silver.sales_transactions")
        )

        # to_sql is a DataFrame method. "append" inserts valid_sales into the existing table;
        # schema and name are separate arguments because silver is PostgreSQL's schema namespace.
        valid_sales.to_sql(
            name="sales_transactions",
            schema="silver",
            con=connection,
            if_exists="append",
            index=False,
            method="multi"
        )

        # Use the same transaction/connection so the SQL report can see the rows just inserted.
        report = pd.read_sql_query(
            REPORT_QUERY,
            con=connection
        )

    print(f"Loaded {len(valid_sales)} rows into silver.sales_transactions")

    report["total_revenue"] = pd.to_numeric(
        report["total_revenue"]
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # /app/output is a bind mount, so writing here also creates/updates output/sales_report.csv on
    # the host. This report is an ordinary file and is separate from the PostgreSQL named volume.
    report.to_csv(
        OUTPUT_FILE,
        index=False,
        float_format="%.2f"
    )

    print(report)
    print(f"Report written to {OUTPUT_FILE}")

finally:
    # Release SQLAlchemy's pooled database connections when the one-run pipeline is finished.
    engine.dispose()
