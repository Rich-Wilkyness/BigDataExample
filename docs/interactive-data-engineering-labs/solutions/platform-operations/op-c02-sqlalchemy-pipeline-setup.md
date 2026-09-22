# OP-C02: Python Pipeline Setup with SQLAlchemy — Solution and Explanation

## Outcome

The completed learner module reads runtime configuration from environment variables, defines the report query, creates a SQLAlchemy engine, creates application-owned PostgreSQL objects, replaces the transaction rows inside one transaction, reads the aggregate report, and publishes `sales_report.csv`. The pandas cleaning and transformation remain supplied so this lab isolates the setup and database lifecycle.

## Reference implementation

Replace the checkpoint bodies in [`op_c02_sqlalchemy_pipeline_setup.py`](../../../../src/big_data_example/labs/platform_operations/op_c02_sqlalchemy_pipeline_setup.py) with the following implementations. The supplied `main()` function does not need to change.

```python
def read_runtime_config() -> tuple[Path, Path, str]:
    """Return INPUT_FILE, OUTPUT_FILE, and DATABASE_URL supplied by Docker Compose."""
    return (
        Path(os.environ["INPUT_FILE"]),
        Path(os.environ["OUTPUT_FILE"]),
        os.environ["DATABASE_URL"],
    )


def build_report_query() -> TextClause:
    """Return the SQL aggregation used to create the category sales report."""
    return text(
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


def create_database_engine(database_url: str) -> Engine:
    """Create and return SQLAlchemy's connection manager for the configured database."""
    return create_engine(database_url)


def create_schema_and_table(connection: Connection) -> None:
    """Create the reporting schema and sales_transactions table when absent."""
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


def replace_transactions(connection: Connection, transactions_df: pd.DataFrame) -> None:
    """Full-refresh the reporting table with the supplied transformed DataFrame."""
    connection.execute(text("TRUNCATE TABLE reporting.sales_transactions"))
    transactions_df.to_sql(
        name="sales_transactions",
        schema="reporting",
        con=connection,
        if_exists="append",
        index=False,
        method="multi",
    )


def read_report(connection: Connection, report_query: TextClause) -> pd.DataFrame:
    """Execute the report query and return its result as a DataFrame."""
    return pd.read_sql_query(report_query, con=connection)


def write_report(report_df: pd.DataFrame, output_file: Path) -> None:
    """Create the output directory and write the final report CSV."""
    report_df = report_df.copy()
    report_df["total_revenue"] = pd.to_numeric(report_df["total_revenue"]).astype("float64")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(output_file, index=False, float_format="%.2f")
```

## Why it is correct

`INPUT_FILE` and `OUTPUT_FILE` identify locations inside the pipeline container, while `DATABASE_URL` identifies the PostgreSQL service on the private Compose network. Turning file strings into `Path` objects gives the rest of the program one consistent path API.

The engine is a reusable connection manager, not the database itself. `engine.begin()` in the supplied `main()` opens one connection and transaction. Successful completion commits the schema, table, truncate, and insert work; an exception rolls the transaction back. `engine.dispose()` releases pooled connections after the run.

The DDL is idempotent because both objects use `IF NOT EXISTS`. The table declares one row per transaction, enforces the transaction ID as the primary key, and uses PostgreSQL `DATE`, `INTEGER`, and fixed-precision `NUMERIC` types rather than allowing pandas to invent the durable contract.

The load intentionally uses `TRUNCATE` followed by `to_sql(..., if_exists="append")`. `append` respects the table created by the explicit DDL. Using `if_exists="replace"` would drop and recreate the table, discarding its primary key and carefully selected PostgreSQL types.

The report query computes results from stored rows rather than hard-coding them. It groups by category, sums both units and revenue, and applies deterministic ordering for repeatable output.

## Walkthrough

The execution order is configuration, query definition, supplied transformation, engine construction, transactional database work, engine cleanup, and file publication. Within the transaction, object creation must precede the load, and the load must precede the report query. The output is written only after the transaction block succeeds, so a failed database operation does not publish a new report that appears successful.

## Alternatives and tradeoffs

Configuration could use command-line arguments or a settings library instead of environment variables. Environment variables fit container runtimes because Compose can inject values without baking machine-specific paths or credentials into the image.

Small projects can use idempotent DDL in application code. A migration tool such as Alembic becomes preferable once schemas evolve across deployed versions and changes need ordered upgrades and rollbacks.

`pandas.to_sql` is convenient for this eight-row batch. PostgreSQL `COPY`, staged files, or database-native bulk loaders become more appropriate as volume grows. Incremental loading with upserts is preferable when a full-table refresh is too expensive or downstream readers require uninterrupted snapshots.

## Pitfalls

- Reading `.env` directly in Python confuses host configuration with container configuration. Compose reads `.env` and passes only declared values into the container.
- Using `localhost` in `DATABASE_URL` from the pipeline container points back to the pipeline container. The Compose service name is `postgres`.
- Calling `create_engine()` does not connect immediately or create schemas and tables.
- Calling `to_sql("reporting.sales_transactions")` treats the dotted text as a table name. Pass `name="sales_transactions"` and `schema="reporting"` separately.
- Using `if_exists="replace"` bypasses the explicit table contract by dropping it.
- Opening unrelated connections for DDL, load, and query weakens the all-or-nothing transaction boundary.
- Writing the report inside the transaction can leave a file behind even if a later database error rolls the transaction back.

## Verification evidence

On 2026-09-21, the Python files and all clean notebook code cells parsed, the Compose configuration rendered successfully, Docker's build check found no Dockerfile warnings, both supplied shell scripts passed `bash -n`, the guarded reset refused to delete state without `--force`, and the supplied transform produced the expected eight rows and exact category totals. An isolated behavior check also exercised every reference function with fake database objects and temporary output. The static learner check failed at the intended first boundary because the starter functions still contain `NotImplementedError`.

The runtime checker additionally requires a healthy PostgreSQL service, eight stored transactions, and an independently reconciled category report. That runtime evidence remains pending until the learner implementation is complete and `./run_pipeline.sh` plus the runtime checker have executed.

## Production extension

A production pipeline would retrieve credentials from a secret manager, run versioned database migrations separately, use structured logging and run identifiers, emit row-count and reconciliation metrics, distinguish transient from permanent failures, and choose an incremental publication strategy. Connection-pool sizing, statement timeouts, bulk-loading methods, and a scheduler-owned retry policy would become explicit operational decisions.
