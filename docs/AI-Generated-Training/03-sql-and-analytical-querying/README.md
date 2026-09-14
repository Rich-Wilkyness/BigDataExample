# 03 SQL and Analytical Querying

> Area status: Documentation complete; executable query suite planned  
> Level: Beginner to Intermediate data engineering  
> Dialect baseline: Relational SQL; PostgreSQL behavior is named where the standard leaves choices  
> Reference scenario: Mobile events, sessions, products, and daily product metrics  
> Evidence boundary: Documentation and query-design review; no real-engine execution yet  
> Last reviewed: 2026-09

## Purpose

This area develops SQL as a language for stating data contracts, not merely for
retrieving rows. The central skill is to predict a query's output grain,
cardinality, missing-value behavior, ordering, and cost before running it. Those
properties determine whether an analytical result is correct and whether it can
be operated safely as data volume and concurrency grow.

For a Kotlin engineer, a SQL query can initially resemble a chain of collection
operators. That analogy helps with filtering and projection, but stops at the
database boundary: SQL is declarative, tables are bags unless constrained,
`NULL` uses three-valued logic, and the optimizer may choose a different physical
execution order while preserving relational semantics.

## Prerequisites

- Complete [01 Big Data and Data Engineering Foundations](../01-big-data-and-data-engineering-foundations/README.md), especially grain, identity, authority, and event time.
- Be comfortable reading typed records and tests from [02 Python for Data Engineering](../02-python-for-data-engineering/README.md); no Python implementation is required here.
- A database is not required for the documentation pass. The planned executable suite will name and pin its engine before results are recorded.

## Learning path

1. [Relations, sets, bags, keys, and NULL](01-relations-sets-bags-keys-and-null.md)
   establishes the value model and the difference between declared and observed uniqueness.
2. [SELECT, filter, project, order, and limit](02-select-filter-project-order-and-limit.md)
   builds deterministic single-relation queries and safe input boundaries.
3. [Joins, cardinality, and missing matches](03-joins-cardinality-and-missing-matches.md)
   makes relationship multiplicity and grain changes explicit.
4. [Aggregation, grouping, and set operations](04-aggregation-grouping-and-set-operations.md)
   derives metrics while preserving denominator and distinctness semantics.
5. [Subqueries, common table expressions, and recursion](05-subqueries-common-table-expressions-and-recursion.md)
   composes transformations and navigates bounded hierarchies.
6. [Window functions, time series, and analytical patterns](06-window-functions-time-series-and-analytical-patterns.md)
   adds ranking, frames, sessions, gaps and islands, pivots, and cohorts.
7. [DDL, constraints, transactions, and concurrent change](07-ddl-constraints-transactions-and-concurrent-change.md)
   turns query assumptions into enforced schemas and safe state transitions.
8. [Query plans, indexes, statistics, and optimization](08-query-plans-indexes-statistics-and-optimization.md)
   connects logical correctness to measured physical execution.

## Shared reference contract

The planned suite separates delivered records from accepted business events:

| Relation | Grain and key | Authority | Important semantics |
| --- | --- | --- | --- |
| `event_deliveries` | One received envelope / `delivery_id` | Ingestion | Retries may repeat `event_id`; immutable receipt fact |
| `events` | One accepted logical event / `event_id` | Validation pipeline | UTC `event_time`; nullable `session_id` and `product_id` |
| `products` | One current product / `product_id` | Product system | Missing join is a quality signal, not an automatic row deletion |
| `sessions` | One derived session / `session_id` | Session transformation | Rebuildable from a versioned inactivity rule |
| `daily_product_metrics` | One UTC date and product / `(metric_date, product_id)` | Analytical data product | Versioned definition and atomic publication |

```text
untrusted deliveries -> validated, deduplicated events -> sessions
                                      |                    |
                                      +---- products ------+
                                                |
                                      daily product metrics
```

The examples assume bounded fixtures but reason about production cardinality:
3 million logical events per day, 35-day interactive retention, about 100 million
event rows, 100,000 products, and a 500 ms interactive-query objective. These are
design assumptions, not measurements. A benchmark or production profile can
invalidate them.

## Evidence and scope

Each guide states a PostgreSQL-compatible design sketch and the assertions that
must accompany its future executable form. No query, constraint, transaction,
index, plan, load test, or concurrent-failure case in this area has run yet.
Consequently, the guides distinguish logical predictions from engine evidence.

Stored procedures, vendor-specific warehouse syntax, database administration,
distributed SQL internals, dimensional modeling, and orchestration are deferred
to later areas. This area still introduces their prerequisite reasoning:
contracts, transaction boundaries, plan inspection, migration safety, and
consumer-visible failure.

## Area completion checklist

- [x] Eight inventory guides authored in the planned order
- [x] Grain, keys, bags, `NULL`, ordering, cardinality, and time semantics covered
- [x] Analytical patterns, DDL, concurrency, plans, indexes, and statistics connected
- [x] Security, quality, recovery, operations, migration, and cost boundaries documented
- [x] Evidence limitations recorded without claiming engine verification
- [ ] Reference schema, fixture, and query suite implemented under `sql/`
- [ ] Deterministic result and mutation tests executed against the selected engine
- [ ] Plans, indexes, realistic cardinalities, and concurrent-change evidence collected

