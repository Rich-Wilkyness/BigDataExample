# DataFrames, Spark SQL, Schemas, and Types

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: PySpark / Spark SQL / Batch  
> Data scale: Local fixture; distributed estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A Spark DataFrame is a distributed relation with named, typed columns and a
deferred computation plan. Spark SQL and the DataFrame API use the same structured
execution engine, so the important choice is not syntax preference but whether
the expression preserves a declared schema, grain, and semantics that the planner
can analyze.

Schemas are executable contracts. Inferring them from a convenient sample can
change numeric width, timestamp interpretation, nullability, or corrupt-record
behavior when production data changes. Python type hints do not define Spark SQL
types; the logical schema at the JVM engine boundary does.

## Learning objectives

- Define explicit Spark schemas and explain their limits as data contracts.
- Translate transformations between DataFrame expressions and Spark SQL.
- Reason about `NULL`, three-valued logic, decimals, timestamps, and ANSI behavior.
- Separate driver-side Python objects from distributed Spark columns and rows.
- Validate, quarantine, and reconcile records without silently changing grain.

## Prerequisites

- SQL types and `NULL` from [03 SQL and Analytical Querying](../03-sql-and-analytical-querying/README.md)
- Event contracts and validation from [06 Data Ingestion and Source Integration](../06-data-ingestion-and-source-integration/README.md)
- [Spark architecture](01-spark-architecture-driver-executors-and-clusters.md)

## Mental model and terminology

A DataFrame resembles a Room query builder more than a `List<Row>`: it describes
columns and relational work that an engine validates and plans. The analogy stops
because Spark distributes partitions, may reorder expressions, and applies Spark
SQL coercion and `NULL` rules across a JVM/Python boundary.

| Term | Meaning in this guide |
| --- | --- |
| Schema | Ordered field names, Spark SQL data types, nesting, and nullability metadata |
| Row grain | What one row represents at a named DataFrame boundary |
| Column expression | Declarative computation evaluated by Spark, not a local Python value |
| Analysis | Resolving names, functions, types, and relations before physical execution |
| ANSI mode | SQL behavior that raises errors for specified invalid operations rather than returning permissive results |
| Quarantine | Governed dataset of rejected records plus safe reason codes and provenance |

## Requirements, assumptions, and invariants

The accepted-event boundary has one row per logical `(tenant_id, event_id)`.
Timestamps are producer instants normalized to UTC; `event_date_utc` is derived
from the instant, not parsed from device-local display text. Revenue uses a fixed
decimal contract rather than binary floating point.

- Required keys are non-null and non-blank after normalization.
- Unknown event types are rejected or quarantined, never silently reinterpreted.
- Duplicate event IDs resolve under one documented deterministic rule.
- `NULL`, empty string, zero, absent field, malformed value, and JSON `null` are not conflated.
- Decimal precision/scale and overflow behavior are explicit.
- Invalid rows retain run, source-file, and safe error-code provenance.
- DataFrame/SQL equivalents produce the same rows independent of partition order.

## Explicit schema and validation

```python
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DecimalType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

EVENT_SCHEMA = StructType([
    StructField("tenant_id", StringType(), nullable=False),
    StructField("event_id", StringType(), nullable=False),
    StructField("product_id", StringType(), nullable=True),
    StructField("event_type", StringType(), nullable=False),
    StructField("event_time", TimestampType(), nullable=False),
    StructField("revenue_usd", DecimalType(18, 2), nullable=True),
])

raw = spark.read.schema(EVENT_SCHEMA).json(input_uri)

reason = (
    F.when(F.trim("tenant_id") == "", F.lit("blank_tenant_id"))
     .when(F.trim("event_id") == "", F.lit("blank_event_id"))
     .when(~F.col("event_type").isin("view", "purchase"), F.lit("unknown_event_type"))
     .when((F.col("event_type") == "purchase") & F.col("revenue_usd").isNull(),
           F.lit("purchase_missing_revenue"))
)

classified = raw.withColumn("rejection_reason", reason)
valid = classified.where(F.col("rejection_reason").isNull())
quarantine = classified.where(F.col("rejection_reason").isNotNull())
```

An explicit reader schema prevents sample-dependent inference, but it is not a
complete validator. Reader modes, type coercion, corrupt input, field absence,
and source-format rules need failure fixtures. Spark commonly treats fields read
from files as nullable for compatibility even when a business contract says they
are required; assert the business invariant in data, not only schema metadata.

## DataFrame and SQL equivalence

```python
daily_df = (
    valid.withColumn("event_date_utc", F.to_date("event_time"))
         .groupBy("tenant_id", "product_id", "event_date_utc")
         .agg(
             F.count("event_id").alias("event_count"),
             F.sum(F.when(F.col("event_type") == "purchase", F.lit(1)).otherwise(0))
              .alias("purchase_count"),
             F.sum("revenue_usd").alias("revenue_usd"),
         )
)
```

```sql
-- Spark SQL. Grain: tenant + product + UTC event date.
SELECT tenant_id,
       product_id,
       to_date(event_time) AS event_date_utc,
       COUNT(event_id) AS event_count,
       SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchase_count,
       SUM(revenue_usd) AS revenue_usd
FROM valid_events
GROUP BY tenant_id, product_id, to_date(event_time);
```

Both forms describe a relation. Neither guarantees row order without `ORDER BY`,
and grouping normally creates an exchange. `COUNT(column)` excludes `NULL`, while
`COUNT(*)` counts rows; the choice is part of the metric definition.

## `NULL`, types, and time

| Concern | Unsafe assumption | Required decision/evidence |
| --- | --- | --- |
| Equality | `x == NULL` finds missing values | Use `IS NULL` / `isNull`; test three-valued predicates |
| Join keys | Null keys match each other | Standard equality does not; use null-safe equality only when business semantics require it |
| Aggregation | All-null sum is zero | Decide whether unknown and zero are distinct; use `coalesce` only after that decision |
| Decimal | Python float is money | Use bounded decimal precision/scale and test rounding/overflow |
| Timestamp | Cluster local zones are equivalent | Set/session-test timezone and normalize instants before date derivation |
| Cast | Invalid text becomes harmless null | Prefer ANSI/error behavior or classify invalid values before cast |
| Ordering | DataFrame preserves file/input order | Require explicit complete sort keys only where a consumer contract needs order |

Spark 4.2 documents ANSI mode as enabled by default; pin and assert the setting
rather than relying on a changing default. Tests should cover overflow, division
by zero, invalid casts, daylight-saving transitions, and timestamps at UTC date
boundaries.

## Python and engine boundaries

`F.col("revenue_usd")` is a plan expression; a Python loop over `collect()` results
is driver-local. Built-in functions keep work visible to Catalyst and typically
inside the JVM execution engine. Python UDFs introduce serialization and separate
worker processes and can obscure optimization. DataFrame creation from Python
objects also crosses a boundary and suits small fixtures, not production ingestion.

Avoid:

```python
# Unbounded driver materialization and local business logic.
rows = [normalize(row) for row in raw.collect()]
```

Prefer:

```python
# Declarative expressions remain distributed and analyzable.
normalized = raw.select(
    F.trim("tenant_id").alias("tenant_id"),
    F.trim("event_id").alias("event_id"),
    F.upper("event_type").alias("event_type"),
    "product_id", "event_time", "revenue_usd",
)
```

## Data flow and trust boundaries

| Boundary | Input contract | Authority/owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Raw files → reader | Versioned format and source manifest | Raw owner | Reject unreadable file or declared corrupt-record policy | Untrusted records |
| Parsed → classified | Explicit schema plus semantic rules | Pipeline owner | Split valid/quarantine with counts | Validated shape only |
| Valid → deduplicated | Stable event identity and precedence | Curated owner | Fail ambiguous duplicates | Trusted for aggregation |
| Aggregated → candidate | Metric definition/version | Curated owner | Reconcile before publication | Derived, uncertified |
| Quarantine → operators | Safe reason/provenance schema | Data quality owner | Restricted repair workflow | Sensitive invalid data |

## Failure model and recovery

| Failure | Detection | Containment and recovery | Convergence evidence |
| --- | --- | --- | --- |
| Missing required field | Null/parse classifier | Quarantine or fail input scope | Accepted + rejected = observed |
| Incompatible type | Reader/ANSI error | Reject file/version; do not permissively coerce | Fixture produces expected error |
| Duplicate event | Uniqueness/reconciliation check | Deterministic dedup by stable precedence | Partition/rerun invariant result |
| Ambiguous column after join | Analysis error or wrong selection | Qualify/rename before projection | Schema contract test |
| Time-zone drift | Boundary fixture mismatch | Pin session zone and normalize | Same UTC results across environments |
| Driver materialization | Memory pressure/termination | Replace collect with aggregate/sample/limit budget | Driver memory stays bounded |

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Command/procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Schema contract | Valid/missing/extra/wrong-type JSON fixture / local Spark | Read with explicit schema | Expected fields and classified failures | Pending |
| SQL equivalence | Same fixture | Compare DataFrame and SQL results as unordered sets | Exact equality | Pending |
| Null/type suite | Null, overflow, bad cast, decimal edge rows | Run under pinned ANSI/timezone config | Declared error/value behavior | Pending |
| Partition invariance | Repartition fixture across several counts | Recompute metrics | Same rows and values | Pending |
| Quality reconciliation | Valid + invalid + duplicate fixture | Compare input/accepted/rejected/dedup counts | Declared conservation equations hold | Pending |

## Debugging guide

Start with the schema printed by the failing boundary and the analyzed plan, not
only the Python call site. Capture the exact input manifest, options, session
timezone, ANSI setting, column resolution, error class, safe offending value
category, and row-count reconciliation. A result mismatch with no exception often
comes from `NULL` filtering, implicit cast, duplicate join matches, timestamp date
derivation, or nondeterministic dedup ordering.

## Common pitfalls

### Pitfall: schema inference as a production contract

A small sample may omit nullable fields or fit values into narrower types. Declare
the schema, test compatibility, and preserve raw bytes/provenance for repair.

### Pitfall: Python truth tests on Columns

Python `and`, `or`, and `if column` do not express Spark SQL predicates. Use `&`,
`|`, `~`, parentheses, and Spark functions; test `NULL` cases explicitly.

### Pitfall: deduplicating without a total precedence rule

`dropDuplicates(["tenant_id", "event_id"])` does not select a business winner
from conflicting duplicates. Define immutable arrival/source position or version
precedence and fail ties that remain ambiguous.

## Performance, security, and compatibility

Project needed columns early, apply selective deterministic filters, and use
built-in expressions so scans and plans can optimize. Do not claim pushdown until
the physical plan and scan metrics show it. Restrict raw/quarantine access, hash or
tokenize identifiers only under a governed contract, and never emit sensitive raw
rows to logs or notebook displays.

Schema evolution uses expand/migrate/contract: add compatible fields, dual-read
where necessary, backfill/reconcile historical partitions, migrate consumers, then
retire old fields. Test mixed file/schema/catalog versions and pin behavior across
Spark upgrades.

## Working example

- PySpark source/SQL/tests/data: Planned
- Expected result: explicit parsing, classified invalid rows, deterministic deduplication, and equivalent daily metrics
- Scale represented: none yet; fixture first, then representative files
- Remaining risk: source reader modes, distributed plan, time zones, schema drift, and Python/JVM compatibility

## Knowledge check

1. State the grain of raw, valid, quarantine, deduplicated, and daily metric rows.
2. Predict `COUNT(*)`, `COUNT(revenue_usd)`, and `SUM(revenue_usd)` for all-null values.
3. Rewrite the daily DataFrame expression as Spark SQL and identify the exchange.
4. Design fixtures for bad casts, decimal overflow, and UTC date boundaries.
5. Repair a nondeterministic duplicate winner rule.
6. Explain why a non-nullable schema field is not enough to prove non-null production data.

## Key takeaways

- A DataFrame is a typed relational plan, not an in-memory Python collection.
- Explicit schemas reduce ambiguity but semantic data-quality checks remain necessary.
- Spark SQL and DataFrame APIs share an engine; verify semantic and plan equivalence.
- `NULL`, decimal, timestamp, cast, and ordering behavior belong in the contract.
- Built-in expressions preserve optimizer visibility and avoid unnecessary language-boundary cost.

## Resources

- [Spark SQL, DataFrames, and Datasets guide](https://spark.apache.org/docs/4.2.0/sql-programming-guide.html) (reviewed 2026-09)
- [Spark SQL data types](https://spark.apache.org/docs/4.2.0/sql-ref-datatypes.html) (reviewed 2026-09)
- [Spark SQL null semantics](https://spark.apache.org/docs/4.2.0/sql-ref-null-semantics.html) (reviewed 2026-09)
- [Spark SQL ANSI compliance](https://spark.apache.org/docs/4.2.0/sql-ref-ansi-compliance.html) (reviewed 2026-09)

## Related topics

- [Lazy evaluation, logical plans, and physical plans](03-lazy-evaluation-logical-and-physical-plans.md)
- [Parquet, pushdown, partition pruning, and catalogs](06-parquet-pushdown-partition-pruning-and-catalogs.md)

## Completion checklist

- [x] DataFrame, SQL, schema, type, `NULL`, time, and Python boundaries explained
- [x] Grain, validation, quarantine, deduplication, security, compatibility, and quality addressed
- [ ] Schema, equivalence, null/type, partition-invariance, and reconciliation evidence run

