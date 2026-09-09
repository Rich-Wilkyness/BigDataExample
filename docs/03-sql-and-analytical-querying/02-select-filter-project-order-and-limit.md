# SELECT, Filter, Project, Order, and Limit

> Status: Documentation complete; executable evidence planned  
> Level: Beginner  
> Applies to: Generic data engineering / SQL  
> Data scale: Local fixture; production cardinality estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A single-table query already contains the core analytical contract: choose a
snapshot, filter rows, derive values, order results when order matters, and bound
delivery without changing meaning accidentally. SQL's written order is not its
logical evaluation order, and physical evaluation is chosen by the optimizer.

This guide covers deterministic reads, expression semantics, pagination, and
parameter boundaries. Joins and aggregations follow in later guides.

## Learning objectives

After completing this guide, you should be able to:

- Derive the logical processing order of a `SELECT` query.
- State whether filtering and projection preserve grain.
- Produce deterministic top-N and paginated results.
- Keep `NULL`, time-zone, and type-conversion behavior explicit.
- Separate values from SQL structure to prevent injection.
- Use result assertions and plans to diagnose correctness and cost.

## Prerequisites

- [Relations, sets, bags, keys, and NULL](01-relations-sets-bags-keys-and-null.md)
- Planned engine and fixture described in the [area README](README.md)

## Mental model

For a basic query, reason in this logical order:

```text
FROM snapshot -> WHERE -> SELECT expressions -> DISTINCT -> ORDER BY -> LIMIT/OFFSET
```

The optimizer may scan an index, push a filter earlier, or evaluate expressions
differently if semantics allow. This differs from a Kotlin collection chain,
whose operator order is directly encoded. SQL states a result; the engine chooses
a valid physical plan.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Selection | Retaining rows that satisfy a predicate (`WHERE`) |
| Projection | Choosing or deriving result columns (`SELECT`) |
| Deterministic order | A total order that gives every possible tie a stable position |
| Sargable predicate | A predicate shaped so an engine can potentially use an access path such as an index range |
| Parameter | A separately bound value, not SQL syntax assembled from untrusted text |
| Snapshot | The database state visible to a statement or transaction under its isolation contract |

## Requirements and invariants

The reference query returns accepted product-view events for a half-open UTC
interval `[start, end)`, newest first, with stable paging. Its grain remains one
logical event per row. It must not expose restricted installation identifiers.

Invariants are:

- Time bounds are typed parameters and use `>= start AND < end`.
- An ordered result includes a unique final tie-breaker.
- `LIMIT` without `ORDER BY` is never presented as a reproducible sample or top-N.
- Dynamic values are bound; dynamic identifiers come only from an allowlist.
- A conversion failure or unexpected `NULL` is visible, not silently coerced.
- The selected snapshot/version is traceable for reproducibility.

## Query construction

### Filter and project

```sql
-- PostgreSQL-compatible design sketch.
-- Input and output grain: one logical event per event_id.
SELECT
    event_id,
    product_id,
    event_time,
    revenue_cents,
    revenue_cents / 100.0 AS revenue_amount
FROM events
WHERE event_name = :event_name
  AND event_time >= :start_utc
  AND event_time < :end_utc
  AND product_id IS NOT NULL;
```

Aliases created in `SELECT` generally are not available to `WHERE`, because
filtering is logically earlier. Division, overflow, collation, implicit casts,
and timestamp conversion are dialect-sensitive; production code pins types and
tests boundary values.

### Order and limit

```sql
SELECT event_id, product_id, event_time
FROM events
WHERE event_name = :event_name
ORDER BY event_time DESC, event_id DESC
LIMIT :page_size;
```

`event_id` completes the order when timestamps tie. Without it, either tied row
may occupy the page boundary. `NULLS FIRST` or `NULLS LAST` should be explicit
when the sort key is nullable and the dialect supports that syntax.

For deep or changing result sets, keyset pagination is usually more stable than
large offsets:

```sql
SELECT event_id, product_id, event_time
FROM events
WHERE event_name = :event_name
  AND (event_time, event_id) < (:cursor_time, :cursor_event_id)
ORDER BY event_time DESC, event_id DESC
LIMIT :page_size;
```

Tuple comparison is dialect-specific. The cursor must correspond to the exact
filter, ordering, authorization, and snapshot contract. Even keyset pagination
does not freeze data unless isolation or a versioned dataset does so.

### Safe parameters

```python
# DB-API placeholder style varies by driver. Values stay separate from SQL text.
cursor.execute(
    "SELECT event_id FROM events WHERE event_time >= %s AND event_time < %s",
    (start_utc, end_utc),
)
```

Parameters represent values. They cannot safely choose a column, direction, or
table name in most APIs. If consumers may select those, map a small external
enum to hard-coded SQL fragments. Do not use string interpolation as an escape
mechanism.

## Data flow, ownership, and trust boundaries

| Boundary | Contract and owner | Failure behavior | Trust |
| --- | --- | --- | --- |
| API/report request | Typed interval, page size, allowed sort | Reject invalid bounds and oversized pages | Untrusted |
| Query module | Fixed SQL shape and bound values | Timeout/cancel without treating partial rows as complete | Application-controlled |
| Versioned `events` snapshot | Accepted event grain | Query version and snapshot ID accompany results | Governed internal |
| Consumer result | Only purpose-approved columns | Empty result differs from failed or stale result | Purpose-limited |

The query module owns translation from request to SQL. The data-product owner
owns column meaning; the database owns statement execution and isolation.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Missing tie-breaker changes top-N | Repeat with tied timestamps and compare result IDs | Add total order; invalidate inconsistent cached pages |
| Inclusive end double-counts midnight | Adjacent-window reconciliation | Use half-open intervals and backfill affected partitions |
| `NULL` predicate drops records | True/false/unknown bucket counts | Repair predicate and republish complete result |
| User text changes SQL structure | Security test or anomalous query/error logs | Bind values; allowlist identifiers; rotate exposed credentials if needed |
| Timeout returns partial client buffer | Statement status and row-count mismatch | Treat as failure, cancel/drain connection, retry only at owned boundary |
| Concurrent writes shift offset pages | Duplicate/missing IDs across pages | Use keyset plus stable snapshot/version, or document live-feed semantics |

Recovery is a rerun against an identified snapshot and query version. Partial
client iteration is not a published dataset.

## Data quality, security, and evidence

Tests must include empty input, exact lower and upper time bounds, tied ordering
keys, null sort values, Unicode text, numeric extremes, invalid parameters, and
an injection-shaped value. Reconcile returned IDs against an independently
specified expected set.

| Evidence | Environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Boundary fixture | Real local engine | Query adjacent half-open intervals | No gaps or overlaps | Pending |
| Deterministic top-N | Real local engine | Repeat with timestamp ties | Same ordered IDs | Pending |
| Parameter boundary | Driver plus real engine | Bind hostile strings and invalid types | Data treated as value or rejected; SQL shape unchanged | Pending |
| Plan inspection | Realistic-cardinality dataset | Explain range query and deep page | Access path and cost recorded | Pending |

Logs record query name/version, duration, rows, timeout class, dataset version,
and a privacy-safe request ID. They do not record raw parameter payloads.

## Debugging guide and common pitfalls

For missing rows, first check snapshot, time zone, half-open bounds, `NULL`
buckets, and authorization filters. For unstable rows, inspect the full
`ORDER BY` and concurrency model. For latency, capture the actual plan with safe
parameters representative of selectivity; query text alone is insufficient.

### Pitfall: `LIMIT` as a sample

Without a defined sampling method and stable snapshot, `LIMIT 100` is merely an
arbitrary prefix chosen by the plan. Use it for exploration only and label that
boundary.

### Pitfall: wrapping an indexed column blindly

`WHERE CAST(event_time AS date) = :day` may prevent an efficient range access
path and can introduce time-zone ambiguity. Prefer typed UTC range bounds unless
measurement and engine features justify another form.

### Pitfall: interpolating a sort field

Binding APIs usually cannot parameterize identifiers. Translate an allowed sort
enum to reviewed SQL; reject everything else.

## Performance, operations, compatibility, and delivery

Selectivity, projected row width, sort volume, page depth, concurrency, cache
state, and result-transfer bytes determine cost. The initial objective is a 500
ms interactive query at representative cardinality, not yet measured. Cap page
size and statement duration; observe p50/p95/p99 latency, rows scanned/returned,
timeouts, spills, and cancellation success without high-cardinality labels.

Dialect migrations must test placeholder syntax, timestamp types, collation,
integer division, tuple comparison, null ordering, and limit semantics. During a
query change, dual-run old and new definitions against the same snapshots,
compare ordered IDs and aggregates, then switch consumers with a rollback path.

## Working example

- SQL: planned under `sql/03-sql-and-analytical-querying/`
- Tests: planned deterministic-result and injection-boundary cases
- Try it: pending engine/driver selection
- Expected result: stable event pages with exact time-boundary behavior
- Scale represented: bounded fixture initially; realistic cardinality pending
- Remaining risk: concurrency, dialect, collation, plan stability, and client cancellation

## Knowledge check

1. Write the logical processing order for a query using every clause in this guide.
2. Predict which events at `start`, just before `end`, and exactly `end` are retained.
3. Diagnose duplicates between two offset-based pages while writes continue.
4. Design an allowlisted user-selectable sort without interpolating raw input.
5. Estimate bytes returned for 20 columns versus four columns at one million rows.
6. Modify the top-N query to handle nullable event time with an explicit policy.

## Key takeaways

- Filtering and projection require explicit grain, null, type, and time semantics.
- Only `ORDER BY` promises order; a unique tie-breaker makes it total.
- `LIMIT` bounds rows, not work, stability, or sampling bias.
- Bound values and allowlisted structure are separate security responsibilities.
- Correctness and performance evidence must use named snapshots and realistic predicates.

## Resources

- [PostgreSQL documentation: SELECT](https://www.postgresql.org/docs/current/sql-select.html) (reviewed 2026-09)
- [PostgreSQL documentation: sorting rows](https://www.postgresql.org/docs/current/queries-order.html) (reviewed 2026-09)
- [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) (reviewed 2026-09)

## Related topics

- [Relations, sets, bags, keys, and NULL](01-relations-sets-bags-keys-and-null.md)
- [Joins, cardinality, and missing matches](03-joins-cardinality-and-missing-matches.md)
- [Query plans, indexes, statistics, and optimization](08-query-plans-indexes-statistics-and-optimization.md)

## Completion checklist

- [x] Logical processing, deterministic ordering, and parameter boundaries explained
- [x] Grain, ownership, `NULL`, time, security, failure, and operations addressed
- [x] Pagination and performance tradeoffs tied to requirements
- [x] Planned evidence distinguished from engine results
- [ ] Fixture, driver boundary, result assertions, and plans executed
- [ ] Concurrency and realistic-cardinality behavior measured
