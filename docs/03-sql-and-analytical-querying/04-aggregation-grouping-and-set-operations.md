# Aggregation, Grouping, and Set Operations

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / SQL  
> Data scale: Local fixture; production cardinality estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Aggregation changes grain: many input rows become one row per grouping key.
Correct metrics require an explicit population, denominator, duplicate policy,
and null policy. Set operations then combine compatible query results with either
bag-preserving or duplicate-removing semantics.

This guide builds daily product metrics and reconciliation queries. Advanced
time-series windows and multidimensional modeling are handled later.

## Learning objectives

After completing this guide, you should be able to:

- State input grain, grouping grain, and metric definition.
- Predict `COUNT`, conditional aggregate, and `NULL` behavior.
- Avoid double counting after joins and unsafe averaging of averages.
- Choose `UNION ALL`, `UNION`, `INTERSECT`, or `EXCEPT` deliberately.
- Reconcile totals across transformation boundaries.

## Prerequisites

- [Joins, cardinality, and missing matches](03-joins-cardinality-and-missing-matches.md)

## Mental model

```text
input population -> group key -> aggregate state -> one output per group
```

`groupBy` on a Kotlin collection is a useful starting analogy, but SQL engines
may hash, sort, partition, spill, or partially combine aggregate state. Moreover,
SQL nulls and bags define which values contribute. The logical result remains
the contract even when physical aggregation is distributed.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Grouping grain | What one aggregate output row represents |
| Population | Exact input rows eligible for a metric |
| Denominator | Count or weight against which a rate/average is defined |
| Conditional aggregate | Aggregate whose inputs are selected by an explicit condition |
| Additive metric | Metric safe to sum across stated dimensions |
| Set operation | Combination of union-compatible query results with defined duplicate behavior |

## Requirements and invariants

`daily_product_metrics` has one row per UTC `metric_date` and `product_id` for
accepted logical events. Views count unique `event_id`; purchases contribute
non-null, non-negative `revenue_cents`. Orphans are reported separately rather
than assigned to an invented product.

- Eligible event identities are unique before aggregation.
- Every metric names its population, numerator, denominator, time zone, and version.
- `COUNT(*)` and `COUNT(column)` are not substituted for each other.
- Empty population, all-null inputs, and numerical zero remain distinguishable.
- Combining partitions with `UNION ALL` is allowed only when their identity ranges
  are disjoint or downstream deduplication is explicit.
- Input counts reconcile to included and excluded reason buckets.

## Aggregation patterns

```sql
-- Output grain: one UTC date and product_id.
SELECT
    CAST(event_time AT TIME ZONE 'UTC' AS date) AS metric_date,
    product_id,
    COUNT(*) FILTER (WHERE event_name = 'product_view') AS view_count,
    COUNT(*) FILTER (WHERE event_name = 'purchase') AS purchase_count,
    SUM(revenue_cents) FILTER (WHERE event_name = 'purchase') AS revenue_cents
FROM events
WHERE event_time >= :start_utc
  AND event_time < :end_utc
  AND product_id IS NOT NULL
GROUP BY CAST(event_time AT TIME ZONE 'UTC' AS date), product_id;
```

`FILTER` and `AT TIME ZONE` syntax are dialect-specific. A portable conditional
form is usually `SUM(CASE WHEN condition THEN 1 ELSE 0 END)`. The two forms must
be tested for the selected engine and types.

`COUNT(*)` counts rows; `COUNT(product_id)` counts non-null product IDs;
`COUNT(DISTINCT event_id)` counts distinct non-null identities. `SUM` over no
qualifying values commonly returns `NULL`, so a deliberate consumer contract may
use `COALESCE`, but only after absence and zero are proven equivalent.

### Ratios and averages

Compute ratios from additive components and guard zero denominators:

```sql
purchase_count * 1.0 / NULLIF(view_count, 0) AS conversion_rate
```

Do not average daily conversion rates to obtain a weekly rate unless equal daily
weight is the intended definition. Sum purchases and views, then divide.

### Set operations

```sql
-- Preserve every row; caller asserts date partitions do not overlap.
SELECT * FROM events_2026_09_05
UNION ALL
SELECT * FROM events_2026_09_06;
```

`UNION`, `INTERSECT`, and `EXCEPT` remove duplicate result rows unless their
`ALL` variants are used and supported. Inputs must be union-compatible, and
column names generally come from the first query. `UNION` is not a business-key
deduplication rule because it compares projected rows.

## Ownership and trust boundaries

The pipeline owns the accepted-event snapshot; the metric owner owns eligibility
and definitions; finance or product consumers own their decision thresholds. A
semantic/version catalog must expose metric grain, SQL version, input versions,
freshness, and exclusions. Restricted identifiers are omitted from published
aggregates, but small groups can still create re-identification risk and may need
suppression or access controls.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Join explosion precedes grouping | Distinct-ID and sum reconciliation diverge | Repair join, rebuild affected metrics, compare to prior version |
| `COUNT(column)` hides nulls | Null-rate assertion and denominator mismatch | Define null bucket; republish versioned metric |
| Overlapping `UNION ALL` partitions | Duplicate IDs/date overlap check | Correct manifest/ranges and rerun idempotently |
| Empty group becomes zero silently | Missing-row versus zero test | Publish completeness state separately from numeric metric |
| Integer division truncates rate | Boundary fixture | Cast deliberately and backfill affected outputs |
| Late event changes closed date | Freshness/late-arrival monitor | Apply correction window and republish with version lineage |

Atomic publication keeps the previous complete metric version visible until the
new results and reconciliation report commit together.

## Data quality, testing, and evidence

The planned fixture contains duplicate deliveries, event-name categories, null
products, zero revenue, null revenue, an orphan product, an empty day, and events
at UTC boundaries. Mutation cases replace `UNION ALL` with `UNION`, remove a
grouping column, switch count forms, and inject join fan-out.

| Evidence | Expected result | Result |
| --- | --- | --- |
| Hand-calculated aggregate fixture | Exact rows, counts, sums, nulls, and rates | Pending |
| Reconciliation | Input = included + each exclusion; detail totals = aggregate totals | Pending |
| Mutation suite | Each semantic mutation fails at least one assertion | Pending |
| Realistic cardinality | Runtime, memory/spill, group skew, output size recorded | Pending |

## Debugging, performance, and operations

Start with definition/query/dataset versions, then compare eligible rows,
distinct identities, join fan-out, null buckets, exclusion buckets, group counts,
and additive totals. For skew, inspect top group sizes rather than only average
group size. Operational metrics include freshness, input/output rows, distinct
keys, excluded rows by bounded reason, reconciliation delta, duration, spill,
and failed publication.

High-cardinality groups consume aggregate memory and can create skew; duplicate
removal adds hash or sort work. Project only needed columns, filter the intended
population early when semantics allow, and measure plans before pre-aggregating.
Pre-aggregation sacrifices detail and may constrain later metric definitions.

Metric changes use new versioned columns or tables, historical dual computation,
consumer comparison, atomic cutover, and rollback. Never silently redefine an
existing metric in place.

## Common pitfalls

### Pitfall: grouping until the SQL runs

Adding columns to `GROUP BY` may satisfy syntax while changing grain. Define the
output key first, then decide how every selected expression belongs to that grain.

### Pitfall: `COALESCE` everywhere

Turning absent, unknown, incomplete, and not-applicable into zero can make a
dashboard look healthy during failure. Preserve completeness metadata.

### Pitfall: averaging averages

Retain numerator and denominator so higher-level consumers can recompute a
weighted result.

## Working example

- SQL and data: planned daily product metric suite and bounded fixture
- Expected result: hand-reconciled counts, revenue, rates, and exclusion buckets
- Scale represented: local fixture; 3M events/day estimate remains untested
- Remaining risk: numeric precision, time zones, skew, late correction, and dialect syntax

## Knowledge check

1. Predict `COUNT(*)`, `COUNT(product_id)`, and `COUNT(DISTINCT product_id)` with nulls and duplicates.
2. Explain why an empty day is not necessarily a day with zero events.
3. Diagnose doubled revenue after product enrichment.
4. Choose between `UNION` and `UNION ALL` for disjoint daily partitions.
5. Compute a weekly conversion rate from daily numerator/denominator pairs.
6. Design a versioned migration that changes purchase eligibility.

## Key takeaways

- Aggregation changes grain and must name population and denominator.
- Null, zero, empty input, and incomplete input have different meanings.
- Additive components are safer building blocks than precomputed averages.
- Set operations have explicit bag/distinct semantics, not identity-aware magic.
- Reconciliation and versioned publication make metrics operable.

## Resources

- [PostgreSQL documentation: aggregate functions](https://www.postgresql.org/docs/current/functions-aggregate.html) (reviewed 2026-09)
- [PostgreSQL documentation: combining queries](https://www.postgresql.org/docs/current/queries-union.html) (reviewed 2026-09)

## Related topics

- [Window functions, time series, and analytical patterns](06-window-functions-time-series-and-analytical-patterns.md)
- [Joins, cardinality, and missing matches](03-joins-cardinality-and-missing-matches.md)

## Completion checklist

- [x] Grouping grain, aggregate/null rules, set operations, and reconciliation explained
- [x] Failure, security, operations, performance, and metric evolution addressed
- [x] Mutation cases and evidence boundary stated
- [ ] Aggregate fixture, mutations, plan, and scale evidence executed

