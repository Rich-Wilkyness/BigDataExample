# Friday lecture: Snowflake ELT, operations, and the bridge to dbt

> Status: Expanded lecture notes; commands are illustrative and were not executed against Snowflake.
> Level: Beginner moving into practical data engineering.
> Last reviewed: 2026-10-03 against official Snowflake, AWS, PostgreSQL, and dbt documentation.

## Overview and study route

Friday connects the tools from earlier lessons into a small analytical pipeline: extract records, load them into Snowflake, derive useful datasets, and operate those datasets safely. A working transformation also needs quality checks, recoverability, permissions, predictable performance, and cost controls.

Use [Thursday's notes](4_Thur_Snowflake.md) for cloud storage, Snowflake architecture, caches, and the existing PostgreSQL/dbt practice project. Use [Wednesday's foundations](3.4_Wed_Snowflake.md) for the wider ingestion options. This guide concentrates on Friday's sequence and the gaps in the captured commands.

After studying, you should be able to explain what each pipeline step changes, verify a load, distinguish typed data from raw text, explain dynamic-table freshness, choose a recovery mechanism, trace required privileges, and investigate a slow query before increasing compute.

## Mental model: where each step runs

```text
PostgreSQL source
    │ psql client exports records
    ▼
CSV on the client machine
    │ PUT uploads a file
    ▼
Snowflake internal stage
    │ COPY INTO parses and loads rows
    ▼
DE_CLASS.RAW.SALES
    │ SQL transformation / dynamic-table refresh
    ▼
DE_CLASS.SILVER.SALES
    │ business aggregation
    ▼
DE_CLASS.GOLD.<business_dataset>
    │ SELECT
    ▼
Analyst / dashboard
```

- **Database:** `DE_CLASS` is a namespace containing schemas.
- **Schema:** `RAW`, `SILVER`, and `GOLD` organize objects; these layer names are team conventions.
- **Warehouse:** `DE_WH` supplies compute. It is separate from the database and stored tables.
- **Stage:** stores or references files awaiting a load; it is not the destination table.
- **ELT:** extract from PostgreSQL, load into Snowflake RAW, then transform inside Snowflake.
- **Grain:** define what one record represents. The lecture's sales example treats `TRANSACTION_ID` as the deduplication key; verify that assumption before applying it to a dataset with multiple line items per transaction.

The source system owns operational records. The ingestion process owns file delivery and load reconciliation. The transformation owner defines cleaning, rejected-record handling, grain, and business metrics. Snowflake manages execution and storage, but it cannot decide those business rules for you.

## Checkpoint 1: configure Snowflake CLI authentication

Run shell commands on your Mac. The examples assume Snowflake CLI is installed; Thursday has the [installation notes](4_Thur_Snowflake.md#optional-snowflake-cli-installation-on-macos).

```bash
snow --version
snow connection add
```

Use these values when defining a connection:

| Field | What to supply |
| --- | --- |
| Connection name | An author-chosen label, such as `de_class` |
| Account | Your instructor/account administrator's Snowflake account identifier, commonly `organization-account` |
| User | Your Snowflake username |
| Authenticator | The authentication method supported by your account; `externalbrowser` uses browser authentication |
| Role | Your granted class role |
| Warehouse | `DE_WH`, if supplied for class |
| Database / schema | `DE_CLASS` / `RAW`, if they already exist |

An AWS account ID and a Snowflake account identifier identify different systems. Do not substitute one for the other. Browser authentication suits interactive development; automated jobs need an approved unattended authentication method.

```bash
snow connection test -c de_class
snow sql -c de_class -q "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE(), CURRENT_REGION();"
```

- **Expected:** the connection test succeeds and the context query identifies the intended user, role, and objects.
- A successful login establishes identity; it does not prove you can create tables or use a warehouse.
- CLI configuration is separate from dbt's profile. If `~/.snowflake` exists, the default file is `~/.snowflake/config.toml`; otherwise macOS uses `~/Library/Application Support/snowflake/config.toml`. A configuration override can change that location. Keep credentials outside the repository and use appropriate owner-only permissions.
- These examples explicitly select `-c de_class`. A different connection name is fine if used consistently.

Sources: [Snowflake connection configuration](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-connections) and [CLI configuration locations](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-cli).

### REPL, one query, or a SQL file?

```bash
# Interactive SQL prompt; end SQL statements with a semicolon.
snow sql -c de_class

# Run one SQL string.
snow sql -c de_class -q "SHOW WAREHOUSES;"

# Run SQL saved in a local file; substitute its actual path.
snow sql -c de_class -f "path/to/your/script.sql"
```

- **REPL:** Read–Eval–Print Loop. You enter a statement, it executes, and you see the result. `python`, `scala`, and `snow sql` are examples when those tools are installed; there is no universal command named `sql`.
- **TUI:** Terminal User Interface, often with menus or panels. It describes the interface; REPL describes the interaction loop.
- SQL blocks below belong in the Snowflake SQL prompt, a worksheet, or a `.sql` file. Bash blocks belong in your Mac terminal.
- Files avoid complicated shell quoting. In zsh, an unescaped `$` inside double quotes can trigger expansion; SQL functions such as `SYSTEM$CLUSTERING_INFORMATION` are easiest to run from a SQL file or worksheet.
- Each separate `snow sql -q` invocation opens its own session. Do not expect a preceding invocation's `USE ROLE` or `USE DATABASE` to persist. Use connection settings, fully qualified names, or one script/session.

Source: [Executing SQL with Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/sql/execute-sql).

## Cloud IAM: how it relates to Snowflake permissions

**IAM — Identity and Access Management** — covers identities and access to cloud resources. AWS, Azure, and Google Cloud provide their own systems. Snowflake has its own authorization model for warehouses, databases, schemas, tables, and other objects.

- An **AWS account** is the ownership/billing boundary; its account ID comes from the account owner.
- An **IAM user** is an identity in an AWS account. Companies may instead use federated sign-in.
- An **IAM role** can be assumed to obtain temporary credentials. It has a trust policy controlling who may assume it and permission policies controlling what it may do.
- A **permission policy** specifies allowed or denied actions on resources. AWS IAM policy documents use JSON; infrastructure tools may embed them in YAML, but that does not make YAML the IAM policy format.
- An **ARN — Amazon Resource Name** — identifies a resource. S3 bucket ARNs omit region/account fields: `arn:aws:s3:::company-data` identifies the bucket, while `arn:aws:s3:::company-data/*` matches objects within it.

Sources: [IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html) and [IAM policy elements](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html).

### Instructor's policy example, preserved for study

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBucketInspection",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetBucketVersioning"
      ],
      "Resource": "arn:aws:s3:::company-data"
    },
    {
      "Sid": "AllowReadWriteObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::company-data/*"
    },
    {
      "Sid": "ExplicitlyDenyDeletion",
      "Effect": "Deny",
      "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
      "Resource": "arn:aws:s3:::company-data/*"
    },
    {
      "Sid": "ExplicitlyDenyBucketAdministration",
      "Effect": "Deny",
      "Action": [
        "s3:DeleteBucket",
        "s3:PutBucketPolicy",
        "s3:PutBucketVersioning"
      ],
      "Resource": "arn:aws:s3:::company-data"
    }
  ]
}
```

- `Sid` labels a statement; `Version` is the policy language version, not the date the policy was written.
- Bucket inspection uses the bucket ARN; object reads/writes use the object ARN pattern.
- Explicit denial takes precedence over an applicable allow. This policy denies deletion while permitting writes; writes may still overwrite an existing object key. It is not an immutable-storage policy.
- The earlier `example-bucket` policy in the notes illustrated the same bucket/object split; this fuller example includes explicit denies.
- **Data-engineering connection:** an external-stage pipeline may need cloud access to files and Snowflake access to load tables. A Snowflake role granting `SELECT` does not automatically grant S3 access. The internal-stage workflow below does not require you to configure your own S3 bucket or IAM role.

Source: [AWS policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html).

## Checkpoint 2: export PostgreSQL data to a local CSV

The lecture switched between an `ORDERS` demonstration and a `SALES` demonstration. Keep them as separate paths:

| Dataset | Local file | Stage | Destination |
| --- | --- | --- | --- |
| Orders | `orders.csv` | `DE_CLASS.RAW.ORDERS_STAGE` | `DE_CLASS.RAW.ORDERS` |
| Sales | `sales.csv` | `DE_CLASS.RAW.LOAD_STAGE` | `DE_CLASS.RAW.SALES` |

A stage name does not have to match a table name. What matters is that the selected file's columns match the target table's loading contract.

The captured export assumes a PostgreSQL database named `sample_database` and the five listed columns. Confirm them first. The original `sample_data` folder is not supplied with these notes; the following example uses `/tmp/orders.csv` as a local teaching path.

```bash
# On the Mac, using your actual PostgreSQL connection details.
psql -d sample_database
```

Inside psql:

```text
\conninfo
\d public.orders
```

Then run this single line inside psql:

```text
\copy (SELECT order_number, order_date, expected_receiving_date, shipping_date, status FROM public.orders) TO '/tmp/orders.csv' WITH (FORMAT CSV, HEADER TRUE)
```

- `\copy` writes on the machine running the psql client. PostgreSQL SQL `COPY ... TO '/path'` writes from the database server's side instead.
- If psql runs inside Docker, `/tmp/orders.csv` belongs to the container. Run the client on your Mac or copy the exported file to the Mac before using Mac-side `PUT`.
- Explicit column ordering keeps the CSV aligned with the Snowflake table. `CSV HEADER` adds names, but the basic load below maps fields by position rather than rearranging them by header.
- **Checkpoint:** inspect the header, record count, column order, and date representation before loading. CSV fields may contain quoted line breaks, so physical line count is not always record count.

Source: [PostgreSQL psql and client-side copy](https://www.postgresql.org/docs/current/app-psql.html).

## Checkpoint 3: create a table, upload a file, then load rows

Assumptions: `DE_CLASS`, `RAW`, and `DE_WH` exist, your role has the needed privileges, and the exported file matches this schema. Use fresh practice objects or inspect existing ones before creating them. `CREATE OR REPLACE` replaces an object; it is not a harmless existence check.

### Orders path: corrected lecture sequence

Run in Snowflake:

```sql
USE WAREHOUSE DE_WH;

CREATE TABLE DE_CLASS.RAW.ORDERS (
    ORDER_NUMBER INTEGER,
    ORDER_DATE DATE,
    EXPECTED_RECEIVING_DATE DATE,
    SHIPPING_DATE DATE,
    STATUS VARCHAR(20)
);

DESC TABLE DE_CLASS.RAW.ORDERS;
CREATE STAGE DE_CLASS.RAW.ORDERS_STAGE;
```

Upload from your Mac:

```bash
snow sql -c de_class -q "PUT file:///tmp/orders.csv @DE_CLASS.RAW.ORDERS_STAGE AUTO_COMPRESS = TRUE;"
snow sql -c de_class -q "LIST @DE_CLASS.RAW.ORDERS_STAGE;"
```

- `file:///tmp/orders.csv` is an absolute local file URI; the captured `file://tmp/orders.csv` was missing a slash.
- `PUT` is handled by a supporting client such as Snowflake CLI. A browser worksheet cannot read the Mac's `/tmp`. Alternatively, use Snowsight's upload action for the intended internal stage.
- With automatic compression, the staged name commonly becomes `orders.csv.gz`. Inspect the upload result and `LIST` rather than assuming the name.

Source: [PUT](https://docs.snowflake.com/en/sql-reference/sql/put).

Run the load in Snowflake; replace the filename if `LIST` reports another name:

```sql
COPY INTO DE_CLASS.RAW.ORDERS
FROM @DE_CLASS.RAW.ORDERS_STAGE
FILES = ('orders.csv.gz')
FILE_FORMAT = (
    TYPE = CSV
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
)
ON_ERROR = 'ABORT_STATEMENT';

SELECT COUNT(*) FROM DE_CLASS.RAW.ORDERS;
SELECT * FROM DE_CLASS.RAW.ORDERS LIMIT 10;
```

`PUT` uploads bytes; `COPY INTO` parses bytes into table rows; `SELECT` reads the table. Snowflake can also query supported staged files directly, so the original “cannot use SELECT yet” means the destination table has not been populated, not that staged files are never queryable.

### Sales path: the lecture's table contract

```sql
CREATE TABLE DE_CLASS.RAW.SALES (
    TRANSACTION_ID VARCHAR(20),
    TRANSACTION_DATE DATE,
    CUSTOMER_NAME VARCHAR(50),
    PRODUCT VARCHAR(20),
    CATEGORY VARCHAR(20),
    QUANTITY INTEGER,
    UNIT_PRICE DECIMAL(10, 2),
    COUNTRY VARCHAR(20)
);
```

Create `DE_CLASS.RAW.LOAD_STAGE` if needed, upload the actual `sales.csv` there, and use its exact staged filename with `COPY INTO DE_CLASS.RAW.SALES`. Uploading `orders.csv` to this stage does not make it sales data. Do not mix the two schemas.

Source: [COPY INTO table syntax and options](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table).

### Bad dates: successful loading can still lose records

The instructor used `ON_ERROR = 'CONTINUE'` because some source dates were invalid.

| Load behavior | Consequence |
| --- | --- |
| `ABORT_STATEMENT` | An encountered data error aborts the load statement |
| `CONTINUE` | Valid rows can load while erroneous rows are skipped |
| `VALIDATION_MODE = 'RETURN_ERRORS'` | A supported basic load can inspect parsing errors without loading rows |

For example, inspect the sales file before loading:

```sql
COPY INTO DE_CLASS.RAW.SALES
FROM @DE_CLASS.RAW.LOAD_STAGE
FILES = ('sales.csv.gz')
FILE_FORMAT = (
    TYPE = CSV
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
)
VALIDATION_MODE = 'RETURN_ERRORS';
```

Match the filename to `LIST`. The ordinary CSV load above is suitable for this validation pattern; validation mode has restrictions for transformed loads.

- Read the load results: rows parsed, rows loaded, errors, and file status. Reconcile accepted plus rejected records with the input.
- `CONTINUE` does not repair dates or preserve the skipped rows inside a typed RAW table. Retain source files and error evidence for replay.
- If preserving every original field is required, a separate landing design can ingest problematic fields as strings and convert them in Silver. This is a design alternative, not a silent change to the instructor's supplied `DATE` schema.
- A format regex checks appearance, not calendar validity. For a string field, `TRY_TO_DATE(text, 'YYYY-MM-DD')` returns `NULL` when conversion fails. For an already typed `DATE`, validate missing dates and business ranges.

Sources: [COPY error handling and validation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table) and [TRY_TO_DATE](https://docs.snowflake.com/en/sql-reference/functions/try_to_date).

### Reruns and ingestion ownership

Snowflake records file-load metadata to help prevent loading the same files repeatedly. That protection has limits and does not define your business deduplication rules. Renamed files or `FORCE = TRUE` can lead to duplicate source records. Track batch/file identity, preserve source files according to policy, and verify loaded counts before publishing downstream results. Do not “fix” a skipped rerun by forcing a load without investigating why it was skipped.

Source: [Data-loading considerations](https://docs.snowflake.com/en/user-guide/data-load-considerations-load).

## Checkpoint 4: understand the dynamic-table transformation

A **dynamic table** stores the result of a defining query and lets Snowflake manage refreshes as dependencies change. You specify the result you want; Snowflake manages how to keep that result refreshed. It does not reach back into PostgreSQL or upload new CSVs for you.

### Corrected version of the captured lecture SQL

This preserves the lecture transformation rather than adding the homework's missing rules. It assumes the typed RAW sales table exists, `SILVER` exists, and the dynamic-table name is available.

```sql
CREATE DYNAMIC TABLE DE_CLASS.SILVER.SALES
    TARGET_LAG = '1 MINUTE'
    WAREHOUSE = DE_WH
AS
SELECT
    TRANSACTION_ID,
    TRANSACTION_DATE,
    INITCAP(TRIM(CUSTOMER_NAME)) AS CUSTOMER_NAME,
    INITCAP(TRIM(PRODUCT)) AS PRODUCT,
    UPPER(TRIM(CATEGORY)) AS CATEGORY,
    QUANTITY,
    UNIT_PRICE,
    ROUND(QUANTITY * UNIT_PRICE, 2) AS TOTAL_AMOUNT,
    UPPER(TRIM(COUNTRY)) AS COUNTRY
FROM DE_CLASS.RAW.SALES
WHERE QUANTITY > 0
  AND UNIT_PRICE > 0
  AND TRANSACTION_DATE IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY TRANSACTION_ID
    ORDER BY TRANSACTION_DATE DESC
) = 1;
```

- `CREATE DYNAMIC TABLE`: creates a persisted transformation result. The original used `CREATE OR REPLACE`; use replacement only when you intend to rebuild the existing object.
- `AS SELECT`: defines the result. `TRIM` removes surrounding whitespace; `INITCAP` changes word capitalization; `UPPER` standardizes case; `ROUND` calculates a two-decimal line amount.
- `WHERE`: excludes records failing the captured positive quantity/price rule. Refunds, free items, and returns may require different business rules.
- `PARTITION BY TRANSACTION_ID`: groups candidate duplicates for ranking; it does not create storage partitions.
- `ROW_NUMBER`: numbers records within each ID group. `QUALIFY ... = 1` keeps one after window evaluation.

Source: [CREATE DYNAMIC TABLE](https://docs.snowflake.com/en/sql-reference/sql/create-dynamic-table).

Two corrections matter:

- The original semicolon before `QUALIFY` ended the query too early. `QUALIFY` belongs inside the same statement, after `WHERE` and window evaluation.
- `TRANSACTION_DATE` was declared `DATE`. A regex against its string representation is not a reliable raw-date validation strategy; invalid source text already encountered conversion at load time.

Date ordering does **not** prove “latest update wins.” If two records share an ID and date but differ in price, this query has no deterministic winner. Agree on a real ordering field, such as an authoritative update timestamp, only if the dataset supplies one. Also inspect NULL/blank IDs: NULL IDs form one ranking group. These are remaining data-quality decisions, not guarantees supplied by the lecture SQL.

Source: [QUALIFY](https://docs.snowflake.com/en/sql-reference/constructs/qualify).

### Freshness and refresh behavior

- `TARGET_LAG = '1 MINUTE'` is a freshness target relative to the pipeline's base data, not “run exactly every minute” and not an end-to-end guarantee from PostgreSQL.
- Snowflake chooses refresh timing to try to meet the target. Expensive queries or failed refreshes can cause the actual lag to exceed it.
- `WAREHOUSE = DE_WH` identifies refresh compute. Background refreshes consume compute even when nobody is querying the output.

Source: [Dynamic-table target lag](https://docs.snowflake.com/en/user-guide/dynamic-tables/target-lag).

Refresh can process changes incrementally or recompute the full result, depending on mode, query support, and configuration. Inspect the selected mode and refresh history; do not assume every dynamic table is incremental or that a short target lag is inexpensive. Refresh-mode options evolve, so consult the current documentation when changing them.

Source: [Dynamic-table refresh modes](https://docs.snowflake.com/en/user-guide/dynamic-tables/refresh-modes).

```sql
SHOW DYNAMIC TABLES IN SCHEMA DE_CLASS.SILVER;
SELECT COUNT(*) FROM DE_CLASS.SILVER.SALES;
SELECT * FROM DE_CLASS.SILVER.SALES LIMIT 10;
```

**Checkpoint:** verify initialization/refresh status, output types, cleaning results, duplicate handling, and actual freshness. A created object is not sufficient evidence that the data contract holds.

### Regular table, view, or dynamic table?

| Choice | What is stored? | Who updates it? | Typical reason to choose it |
| --- | --- | --- | --- |
| Regular table | Rows | Explicit SQL/job/dbt execution | Controlled batches, audit checkpoints, or custom update logic |
| View | Query definition | Evaluated when queried | Reusable SQL without storing another result |
| Dynamic table | Materialized query result | Snowflake-managed refresh | Declarative dependencies and a freshness target |

Gold introduces a different grain: one row per business grouping, such as country/category or day. Define what `COUNT` counts and what revenue includes before implementing the aggregation. A line-item count and a distinct transaction count can differ. The homework asks you to build that SQL yourself.

## Time Travel and cloning: recover a known state

Thursday explains the [Time Travel and cloning foundations](4_Thur_Snowflake.md#time-travel-read-an-earlier-state). Friday's operational question is: can you identify and validate the exact state before a damaging change?

| Mechanism | What it does |
| --- | --- |
| `AT (TIMESTAMP => ...)` | Reads a state at a specified timestamp |
| `AT (OFFSET => -60)` | Reads a state 60 seconds before the query's current time |
| `BEFORE (STATEMENT => '<query_id>')` | Reads the state immediately before a known statement |
| `UNDROP TABLE ...` | Restores a dropped table when retained history permits |
| Historical `CLONE` | Creates an independent object from a retained historical state |

For a recovery experiment, record the original count, the damage statement's query ID, and the target time before proceeding. Historical reads do not modify the current table. An offset is relative to when you run the query; waiting changes what `-60` refers to.

Retention for standard Snowflake tables:

- Standard Edition supports up to one day; zero disables retention. One day is the usual default, not a guaranteed setting on every object.
- Enterprise and higher allow up to 90 days for permanent objects when configured.
- Temporary/transient tables remain limited to zero or one day. History must actually exist within the requested window.
- Fail-safe is separate from user-accessible Time Travel.

Source: [Snowflake Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel).

Illustrative syntax, with a query ID you must replace:

```sql
SELECT COUNT(*)
FROM DE_CLASS.RAW.RECOVERY_TEST
BEFORE (STATEMENT => '<damage_statement_query_id>');

CREATE TABLE DE_CLASS.RAW.RECOVERY_CANDIDATE
CLONE DE_CLASS.RAW.RECOVERY_TEST
BEFORE (STATEMENT => '<damage_statement_query_id>');
```

A clone initially shares underlying storage; subsequent changes can create additional storage. Validate the candidate's count, keys, and values before choosing a repair/cutover procedure. Matching row counts alone does not prove equal contents. Keep destructive experiments on disposable homework objects.

Source: [Cloning considerations](https://docs.snowflake.com/en/user-guide/object-clone).

`UNDROP` restores a dropped object, not individual rows deleted from a still-existing table. Name conflicts may need resolution. Source: [UNDROP TABLE](https://docs.snowflake.com/en/sql-reference/sql/undrop-table).

Time Travel and declaratively refreshed datasets have counterparts in other platforms. Snowflake's syntax, retention rules, execution model, and managed integration are product-specific; the underlying ideas are broader data-engineering concepts.

## RBAC and dynamic masking

**RBAC — Role-Based Access Control** — assigns privileges to roles and grants roles to users or other roles. It serves a similar purpose to cloud IAM, but Snowflake roles and AWS assumable roles are different mechanisms.

```text
User → active/available roles → object privileges
```

For a basic table query, trace this access path:

```text
USAGE on warehouse
  + USAGE on database
  + USAGE on schema
  + SELECT on table
```

`USAGE` allows use of the containing object; it does not grant all operations on everything inside it. Role inheritance and ownership affect effective access, so test using the actual intended role context rather than an administrative session.

Source: [Snowflake access-control overview](https://docs.snowflake.com/en/user-guide/security-access-control-overview).

### Small privilege example, separate from the homework role matrix

Assuming the role has been created by an authorized administrator:

```sql
GRANT USAGE ON WAREHOUSE DE_WH TO ROLE REPORT_READER;
GRANT USAGE ON DATABASE DE_CLASS TO ROLE REPORT_READER;
GRANT USAGE ON SCHEMA DE_CLASS.GOLD TO ROLE REPORT_READER;
GRANT SELECT ON TABLE DE_CLASS.GOLD.DAILY_REPORT TO ROLE REPORT_READER;
```

`DAILY_REPORT` is an illustrative object, not a supplied homework table. `GRANT ROLE REPORT_READER TO USER <user_name>` assigns the role; replace the placeholder. Grants on existing objects and grants on future objects are separate considerations. Creating a dynamic table also needs appropriate create privileges, access to dependencies, and warehouse access.

Source: [Snowflake privileges](https://docs.snowflake.com/en/user-guide/security-access-control-privileges).

### Dynamic data masking

- A masking policy changes the value returned by a query according to policy logic and execution context.
- An authorized role can see the original value; another role may see a placeholder, partial value, or NULL. Asterisks are one possible policy result, not an automatic universal behavior.
- Masking does not rewrite the stored value, encrypt it, or grant table access. The user still needs authorization to query the object.
- Dynamic Data Masking requires Enterprise Edition or higher. Applying policies and managing access require suitable privileges.
- Verify both allowed and restricted contexts. A screenshot from one role does not prove the policy protects every access path.

Source: [Dynamic Data Masking](https://docs.snowflake.com/en/user-guide/security-column-ddm-intro).

## Performance: pruning first, then compute decisions

Thursday contains the [pruning and cache foundations](4_Thur_Snowflake.md#micro-partitions-pruning-and-clustering). Here the goal is to diagnose the homework's large-table date filter.

- A **micro-partition** is a Snowflake-managed storage unit for standard tables. Data is columnar and compressed; micro-partitions typically represent 50–500 MB of uncompressed data.
- Snowflake maintains metadata such as column value ranges. **Pruning** skips partitions that cannot contain a matching value and avoids unnecessary column reads.
- A January filter can skip a partition containing only June dates. If nearly every partition spans the whole year, date pruning is less effective.
- Query Profile exposes scan statistics, such as partitions scanned versus total; you do not browse or manually manage micro-partition files as directory partitions.

Source: [Micro-partitions and pruning](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions).

### Clustering keys are not Hive/Spark bucketing

| Technique | Main idea |
| --- | --- |
| Hive/Spark directory partitioning | Organize files by partition-column values |
| Hive/Spark bucketing | Assign records to buckets, typically by hashing a key |
| Snowflake clustering key | Improve co-location of related values across micro-partitions for useful filters |

Clustering does not promise a globally sorted result. You still need `ORDER BY` for ordered query output. A date key may help a very large table with repeated selective date filters and poorly clustered data. Small tables, infrequent filters, or already useful natural clustering may not justify maintenance cost.

Source: [Clustering keys](https://docs.snowflake.com/en/user-guide/tables-clustering-keys).

```sql
SELECT SYSTEM$CLUSTERING_INFORMATION(
    'DE_CLASS.RAW.SALES',
    '(TRANSACTION_DATE)'
);
```

The JSON output includes partition counts, average overlap/depth, and a depth histogram for the specified columns. Lower overlap/depth generally indicates better separation; interpret it with your query filters and scan measurements. Supplying columns here diagnoses their clustering; it does not create a clustering key.

Source: [SYSTEM$CLUSTERING_INFORMATION](https://docs.snowflake.com/en/sql-reference/functions/system_clustering_information).

### Investigation sequence

1. Confirm correctness and the amount of data the query should read.
2. Inspect Query Profile: scan volume/pruning, expensive joins, spilling, and queue time.
3. Check whether cached results or warehouse cache explain timing differences; Thursday distinguishes the mechanisms.
4. Improve SQL/filtering and evaluate data layout before adding compute.
5. Compare warehouse sizes using the same workload, declared cache conditions, elapsed time, and credits.

A five-billion-row scenario is a scale estimate, not evidence from this class dataset. Do not infer measured clustering or sizing benefits from a small sample.

## Warehouse sizing and cost controls

### Scale up versus scale out

| Action | What changes | Main problem addressed |
| --- | --- | --- |
| Scale up/down | Warehouse size, such as X-Small → Small | Compute/memory available to a workload |
| Scale out/in | Number of clusters in a multi-cluster warehouse | Concurrent query demand and queueing |

Ordinary warehouse size is configured; Snowflake does not automatically change X-Small to Medium just because a query is slow. Configured multi-cluster Auto-scale can add/remove clusters within bounds. Multi-cluster warehouses require Enterprise or higher and primarily address concurrency; one query does not automatically run across all clusters.

Source: [Multi-cluster warehouses](https://docs.snowflake.com/en/user-guide/warehouses-multicluster).

```sql
SHOW WAREHOUSES;
```

Inspect size, state, auto-suspend/resume, and cluster settings. The homework provides an `ALTER WAREHOUSE` development example; understand your current settings before applying it.

- **Auto-suspend:** stops idle warehouse compute after the configured interval.
- **Auto-resume:** allows work to resume a suspended warehouse.
- Warehouse compute is generally billed per second, with a minimum charge of 60 seconds each time it starts. Frequent suspend/resume cycles can add overhead and lose local cache.
- Suspension preserves tables. Storage and other service costs can continue.
- Dynamic-table refresh work can resume/use its warehouse, so idle interactive sessions do not imply an idle transformation pipeline.

Source: [Warehouse considerations](https://docs.snowflake.com/en/user-guide/warehouses-considerations).

For reasoning about compute cost:

```text
approximate credits = credits/hour × billable runtime in hours
```

Hypothetical comparison, not a benchmark or a quoted warehouse price:

| Run | Assumed rate | Billable duration | Credits |
| --- | --- | --- | --- |
| Smaller compute | 1 credit/hour | 20 minutes | 0.333 |
| Larger compute | 2 credits/hour | 5 minutes | 0.167 |

Doubling the rate can reduce total credits if execution improves enough. If runtime barely improves, cost rises instead. Measure rather than assuming either larger or smaller is always cheaper.

### Resource monitors

A resource monitor tracks credit usage for assigned warehouses or at account level and triggers notification/suspension actions. It is a credit quota mechanism, not a guaranteed cap on every dollar of the account's bill.

```sql
-- Administrative illustration; use a fresh monitor name.
CREATE RESOURCE MONITOR CLASS_COMPUTE_MONITOR
    WITH CREDIT_QUOTA = 10
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
        ON 80 PERCENT DO NOTIFY
        ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE DE_WH
SET RESOURCE_MONITOR = CLASS_COMPUTE_MONITOR;
```

Creating a monitor does not attach it automatically. `CREDIT_QUOTA = 10` means credits, not dollars. Source: [CREATE RESOURCE MONITOR](https://docs.snowflake.com/en/sql-reference/sql/create-resource-monitor).

- Resource monitors are available in Standard Edition; Enterprise is not required.
- Current documentation restricts creation and warehouse assignment to `ACCOUNTADMIN`. A custom role with delegated monitor privileges can inspect or modify aspects of an existing monitor; that is different from creating one.
- `SUSPEND` allows running statements to finish; `SUSPEND_IMMEDIATE` cancels running statements. Threshold detection and ongoing work can allow quota overshoot.
- Resource monitors do not control all serverless services or storage spending. Use the appropriate budgets/usage visibility for those costs.

Source: [Working with resource monitors](https://docs.snowflake.com/en/user-guide/resource-monitors).

## Snowflake, Spark, Snowpark, dbt, and pipelines

| Name | Role in the architecture |
| --- | --- |
| Snowflake | Managed data platform storing and processing analytical data |
| Apache Spark | Distributed processing engine used for batch, streaming, and other workloads |
| Databricks | Managed data/AI platform with Spark capabilities and other services |
| Snowpark | Snowflake developer libraries/APIs, including DataFrame-style transformations |
| dbt | Framework for organizing, executing, testing, and documenting transformations on a supported platform |

Snowpark DataFrames may look familiar after PySpark, but they execute through Snowflake's APIs/engine; Snowpark is not simply a Spark cluster inside Snowflake. Source: [Snowpark overview](https://docs.snowflake.com/en/developer-guide/snowpark/index).

Snowflake SQL can handle transformations that you could also implement in Spark. Decide based on data location, latency, formats, workload, team skills, and operating cost. Spark can run outside Databricks, and choosing Snowflake does not rule out Spark upstream.

You can call the combined technologies a **data stack**. A **pipeline** is the sequence of data movement and transformation implemented with that stack. For example, PostgreSQL + file ingestion + Snowflake + dbt can form a stack; extract → load → clean → aggregate is the pipeline.

## Before Monday: the bridge to dbt

The next question is how to maintain many related transformations as code. Revisit [Thursday's dbt sequence](4_Thur_Snowflake.md#dbt-models-source--bronze--silver--gold) for the already documented setup; Friday does not require another installation walkthrough.

| Concept | Connection to Friday |
| --- | --- |
| Model | A named transformation, usually written as a SQL `SELECT` |
| Source / `source()` | Declare and reference an upstream loaded table such as RAW sales |
| `ref()` | Reference another model and declare a dependency |
| DAG | Directed acyclic graph representing those dependencies |
| Materialization | How a model is implemented or persisted |
| Test | An assertion about keys, missing values, relationships, or other data rules |
| Documentation | Explain columns, grain, rules, ownership, and lineage |
| Jinja | Templating used to resolve references and generate SQL |
| Seed | Small CSV data managed by dbt, often reference data |
| Snapshot | Track historical versions of mutable records; distinct from Snowflake Time Travel |

Four materializations to recognize:

- **View:** save a query definition.
- **Table:** build a stored result; ordinary runs rebuild it.
- **Incremental:** update the relevant subset based on logic you define; late data, duplicates, updates, and deletes still need deliberate handling.
- **Ephemeral:** embed the model in dependent SQL rather than create a standalone database relation.

Source: [dbt materializations](https://docs.getdbt.com/docs/build/materializations).

Dynamic tables manage database-side refresh. dbt manages transformation project structure, dependency execution, tests, and documentation. They can be combined through supported Snowflake adapter features; dbt models are not all automatically dynamic tables. dbt also does not replace the extract/load steps in this lesson.

Source: [Using dynamic tables with dbt](https://docs.snowflake.com/en/user-guide/dynamic-tables/dbt).

## Failure checks and production progression

| Symptom | Boundary to inspect | Next check |
| --- | --- | --- |
| Login works; query fails | Authorization/context | Active role, warehouse, and containing-object privileges |
| `PUT` cannot find a file | Client filesystem | Exact URI and whether the file is on Mac or inside Docker |
| Stage has files; table is empty | Load | `COPY INTO` results, filename, schema, and error evidence |
| Typed RAW has fewer rows than source | Parsing/rejections | Reconcile parsed, loaded, and rejected records |
| Rerun loads no rows or duplicates | Load identity | File-load history, renamed files, forced loads, and business keys |
| Silver is stale | Refresh | Refresh state/history, compute, dependency access, and actual lag |
| Duplicate winner changes | Transformation rule | Grain and deterministic ordering, including ties and NULL IDs |
| Historical read fails | Retention | Object type, configured retention, object creation time, and target time |
| Slow query or rising credits | Workload | Profile, pruning, spilling, queueing, refresh frequency, and billable runtime |

For a production pipeline, keep versioned SQL, a file/batch manifest, rejected-record evidence, quality assertions, refresh/load monitoring, role ownership, and a rehearsed recovery procedure. Preserve RAW evidence according to retention/privacy policy; do not keep every source file forever by default. Promote outputs only after the agreed completeness and correctness checks pass.

## Homework map and knowledge checks

| Homework part | Lecture preparation | Your implementation/decision |
| --- | --- | --- |
| 1: profiling | Grain, load results, typed versus text RAW | Write the profile queries and explain what they reveal |
| 2: Silver | Corrected lecture example and remaining rules | Choose at least five transformations and justify them |
| 3: Gold | Business grain and metric definitions | Write your aggregation and metric SQL |
| 4: recovery | Historical reads and candidate validation | Perform and verify a disposable recovery experiment |
| 5: RBAC | Warehouse/database/schema/table privilege chain | Implement the three-role requirements |
| 6: performance | Pruning, clustering, and query investigation | Explain the large-table scenario using evidence where available |
| 7: cost | Compute sizing, billable runtime, suspension | Inspect/configure class compute and compare the choices |
| 8–10: dbt | Model/reference/materialization vocabulary | Explain how you would organize Friday's transformations |

Before moving on, try explaining these without looking:

- Where is the CSV after `\copy`, after `PUT`, and after `COPY INTO`?
- If `CONTINUE` skips invalid dates, which evidence preserves those source records?
- Why is date-format validation different for a string and a typed `DATE`?
- What can make the lecture's deduplication nondeterministic?
- What does a one-minute target lag promise, and what remains outside it?
- How would you distinguish a pruning problem from a concurrency problem?
- What would prove a recovery restored contents rather than just the count?

## Completion and evidence checklist

- [ ] Confirm CLI identity, role, and context using your actual account.
- [ ] Export/inspect a source file and reconcile its load, including rejected records.
- [ ] Inspect transformation types, grain, duplicate policy, and refresh behavior.
- [ ] Verify recovery, permitted/restricted access, and any configured masking.
- [ ] Record query-profile and cost evidence before making optimization claims.
- [ ] Explain how dbt organizes the transformations before Monday's deeper lesson.

The notes were checked against primary documentation. SQL, authentication, cloud permissions, loading, dynamic refresh, masking, recovery, performance, and billing behavior have not been executed or measured for this Friday guide. Thursday's local PostgreSQL/dbt evidence is documented separately and does not validate these Snowflake examples.

## Video review

Video identities, durations, publisher descriptions, chapter metadata, and English caption-track availability were checked on 2026-10-03. Both Snowflake Developers videos exposed published English captions and auto-generated English captions; the Data Engineering Simplified video exposed auto-generated English captions. Transcript requests returned empty responses, so the summaries below are based on descriptions and chapters, not a full transcript or visual review.

Watch the short overview first, then the architecture walkthrough if you want more detail. The longer pipeline lab is optional enrichment. These supplied links focus on Snowpark; they supplement the [Snowflake/Spark comparison](#snowflake-spark-snowpark-dbt-and-pipelines), rather than covering every Friday topic or replacing Monday's dbt lesson.

### 1. [Snowflake 101: What is Snowpark? — Snowflake Developers](https://www.youtube.com/watch?v=ZzfCsmKoVQY)

This **5-minute, 31-second** introduction defines Snowpark, introduces DataFrame-style development and custom code, and compares Snowpark with the Snowflake Spark Connector. It is the best first pass through the terminology before attempting a longer demo.

**Useful chapters:** 00:29 defines Snowpark; 01:39 introduces DataFrames; 02:44 covers custom code; 04:05 compares Snowpark with the Spark Connector.

**Important takeaway:** a familiar DataFrame API does not mean the same execution engine. Snowpark expresses work for Snowflake; the Spark Connector connects a Spark application to Snowflake and can push supported work into Snowflake. For data engineering, ask where data resides and where each operation executes before choosing the API.

Technical cross-check: [Snowflake Spark Connector overview](https://docs.snowflake.com/en/user-guide/spark-connector-overview).

### 2. [#01 | What is Snowpark in Snowflake — Data Engineering Simplified](https://www.youtube.com/watch?v=-awSPRW9AOY&list=PLba2xJ7yxHB4yPg3pUrobdzeMxk4mP24S)

This **21-minute, 36-second** walkthrough compares pandas, Spark, and Snowpark, introduces the Snowpark API, and follows a small Python example into Snowflake Query History and an architecture explanation. It adds a practical execution-model bridge to the shorter overview. The supplied playlist link is preserved; other playlist episodes were not reviewed.

**Useful chapters:** 05:38 compares the tools; 09:40 discusses what Snowpark is; 14:10 shows the Python example; 16:09 connects execution to Query History; 18:45 discusses architecture.

**Important takeaway:** a Snowpark DataFrame describes a relational computation that is evaluated lazily. Actions trigger execution; `collect()` brings results back to the client. Keep large transformations close to warehouse data and avoid collecting an entire dataset just to perform local processing. Use Query History to inspect the actual work.

Technical cross-check: [Snowpark Python DataFrames](https://docs.snowflake.com/en/developer-guide/snowpark/python/working-with-dataframes). The publisher's description uses “in-memory computing”; that wording should not be read as a guarantee that all data fits in memory or that Snowpark uses Spark's execution architecture.

### 3. [How to Build Python Data Engineering Pipelines with Snowpark — Snowflake Developers](https://www.youtube.com/watch?v=yTUneS1WXao)

This **1-hour, 14-minute, 26-second** hands-on lab extends the overview into a Python pipeline. The published chapters cover loading data, Marketplace data, views and streams, a Python UDF, stored procedures, joins, deployment, orchestration, incremental runs, Query History, and GitHub Actions. It is useful after Friday's RAW → SILVER → GOLD flow is clear, because it shows how a transformation becomes an operated pipeline.

**Useful chapters:** 01:01 introduces Snowpark; 20:38 begins loading; 40:12 builds the first pipeline; 55:35 covers orchestration; 59:30 covers incremental runs; 1:01:39 inspects Query History; 1:06:25 introduces deployment through GitHub Actions.

**Important takeaway:** a transformation function is only one part of a pipeline. Loading, dependency ordering, incremental state, deployment, and observability each need an owner and a verification step. Compare those responsibilities with Friday's dynamic tables and Monday's dbt models; they solve overlapping problems through different mechanisms.

Treat the demonstrated setup, packages, interface, and orchestration choices as version-specific examples. The lab's commands were not reproduced for this guide; completing it is optional and does not establish correctness or cost for the class pipeline.
