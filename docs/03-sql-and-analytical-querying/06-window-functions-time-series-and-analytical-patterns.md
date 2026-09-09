# Window Functions, Time Series, and Analytical Patterns

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Generic data engineering / SQL / Batch  
> Data scale: Local fixture; production cardinality estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Window functions calculate across related rows while retaining the input row
grain. That makes them the foundation for ranking, deduplication, running values,
lag comparisons, sessions, gaps and islands, and cohorts. Correctness depends on
partition identity, total ordering, frame boundaries, and time semantics.

This guide focuses on bounded batch analysis. Unbounded streaming windows,
watermarks, incremental state, and continuously revised results belong to the
streaming area.

## Learning objectives

After completing this guide, you should be able to:

- Distinguish window partitioning, ordering, and framing from grouping.
- Build deterministic ranking and running-value queries.
- Explain `ROWS` versus peer-sensitive default/range frames.
- Sessionize events under a versioned inactivity rule.
- Design gaps/islands, pivot, and cohort results at explicit grains.
- Test ties, nulls, boundaries, late data, and time zones.

## Prerequisites

- [Aggregation, grouping, and set operations](04-aggregation-grouping-and-set-operations.md)
- [Subqueries, common table expressions, and recursion](05-subqueries-common-table-expressions-and-recursion.md)

## Mental model

`GROUP BY` collapses rows. A window function annotates each row using a logical
neighborhood:

```text
PARTITION BY chooses an independent population
ORDER BY defines sequence and peers inside it
frame chooses which neighboring rows feed this calculation
```

Kotlin's `runningFold` helps explain cumulative state over an already ordered
list. The analogy stops because table order is absent until declared, ties create
peers, frames have SQL-specific semantics, and an engine may sort or redistribute
large partitions.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Window partition | Independent set of rows over which a window expression operates |
| Peer | Row sharing the same window ordering values |
| Frame | Subset relative to the current row used by frame-sensitive functions |
| Sessionization | Deriving visit groups from ordered events and an inactivity threshold |
| Gap and island | Missing interval and contiguous run, respectively |
| Cohort | Population sharing a defined starting attribute or period |
| Pivot | Turning category values into columns, usually with conditional aggregation |

## Requirements, identity, and time invariants

Events use UTC instants. Sessionization partitions by a pseudonymous scoped
`installation_id`, orders by `(event_time, event_id)`, and starts a new session
when the gap from the preceding event is at least 30 minutes. The rule version
and cutoff are part of the derived dataset identity.

- Every order-sensitive window has a unique final tie-breaker.
- `PARTITION BY` matches the entity scope; cross-tenant partitions are forbidden.
- Frame units and both boundaries are explicit for cumulative metrics.
- Event time drives sessions/cohorts; receipt cutoff defines completeness.
- Late accepted events may revise sessions and downstream metrics inside the
  documented correction horizon.
- Null time or identity is rejected or routed before windowing, never arbitrarily ordered.

## Core window patterns

### Deterministic ranking and deduplication

```sql
WITH ranked AS (
    SELECT d.*,
           ROW_NUMBER() OVER (
               PARTITION BY event_id
               ORDER BY receipt_time, delivery_id
           ) AS delivery_rank
    FROM event_deliveries AS d
)
SELECT *
FROM ranked
WHERE delivery_rank = 1;
```

The winner rule is stable only if `delivery_id` makes ties total. `RANK` leaves
gaps after peers; `DENSE_RANK` does not; `ROW_NUMBER` assigns one position per row.

### Running values and frames

```sql
SELECT
    product_id,
    event_time,
    event_id,
    revenue_cents,
    SUM(revenue_cents) OVER (
        PARTITION BY product_id
        ORDER BY event_time, event_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_revenue_cents
FROM events
WHERE event_name = 'purchase';
```

Explicit `ROWS` makes the frame advance one physical ordered row at a time.
Default frames can include all peers sharing the ordering value, so tied
timestamps may make a running total jump across several rows at once.

### Sessionization

```sql
WITH ordered AS (
    SELECT event_id, installation_id, event_time,
           LAG(event_time) OVER (
               PARTITION BY installation_id
               ORDER BY event_time, event_id
           ) AS previous_event_time
    FROM events
), boundaries AS (
    SELECT *,
           CASE WHEN previous_event_time IS NULL
                  OR event_time - previous_event_time >= INTERVAL '30 minutes'
                THEN 1 ELSE 0 END AS starts_session
    FROM ordered
), numbered AS (
    SELECT *,
           SUM(starts_session) OVER (
               PARTITION BY installation_id
               ORDER BY event_time, event_id
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS session_number
    FROM boundaries
)
SELECT installation_id, session_number,
       MIN(event_time) AS session_start,
       MAX(event_time) AS session_end,
       COUNT(*) AS event_count
FROM numbered
GROUP BY installation_id, session_number;
```

Interval arithmetic is dialect-specific. A production session ID should derive
from stable scoped identity, rule version, and a deterministic boundary event,
not from an unstable row number alone.

## Time-series, gaps/islands, pivots, and cohorts

A date spine makes missing periods explicit. Left join aggregates onto the spine,
then retain both completeness state and numeric value; absence is not always zero.
Gaps/islands typically compare each ordered value with `LAG`, mark boundaries,
and cumulatively number runs. The exact adjacency rule belongs to the business
contract.

Portable pivots use conditional aggregation:

```sql
SELECT metric_date,
       SUM(view_count) FILTER (WHERE category = 'books') AS books_views,
       SUM(view_count) FILTER (WHERE category = 'games') AS games_views
FROM daily_category_metrics
GROUP BY metric_date;
```

Dynamic categories are usually better left as rows because generated columns
change the schema and can create unsafe dynamic SQL.

A cohort requires a stable entry rule, such as the UTC month of first qualifying
purchase. Retention denominators must preserve original cohort size and distinguish
late-arriving activity from a definition change.

## Data flow, ownership, and privacy

| Boundary | Owner and contract | Failure behavior | Trust |
| --- | --- | --- | --- |
| Accepted events | Pipeline; event-time snapshot and cutoff | Incomplete cutoff blocks final publication | Restricted |
| Session transform | Analytics owner; inactivity/rule version | Late data triggers bounded recomputation | Highly restricted derived |
| Daily/cohort output | Data-product owner; explicit grain/denominator | Completeness and revision status published | Purpose-limited |

Session paths can reveal behavior even after direct IDs are removed. Restrict
access, use scoped pseudonyms, suppress small cohorts when policy requires it,
bound retention, and propagate deletion through derived sessions and metrics.
Never put raw identifiers into plan captures, logs, or example fixtures.

## Failure model and recovery

| Failure | Symptom and detection | Recovery |
| --- | --- | --- |
| Tied order lacks event ID | Winner/session varies across runs | Add stable tie-breaker; rebuild and compare identities |
| Default frame includes peers | Running value jumps unexpectedly | State explicit frame and regression-test ties |
| Late event bridges two sessions | Historical session IDs/counts change | Recompute affected entity/horizon; version and reconcile outputs |
| Wrong partition key | Cross-user/tenant contamination | Stop publication, assess exposure, fix scope, delete bad derived data |
| DST/local conversion shifts day | Boundary-day mismatch | Store instants, define reporting zone, backfill affected intervals |
| One huge partition | Spill, timeout, worker imbalance | Measure skew; split only with semantics-preserving state design |

Publication is staged. A failed or cancelled calculation exposes neither partial
session tables nor partially refreshed cohorts.

## Data quality, testing, and evidence

The planned fixture covers empty and singleton partitions, equal timestamps,
gaps just below/equal/above 30 minutes, midnight, leap day, DST boundaries,
late bridge events, nulls, duplicates, a high-skew identity, and deleted identity.

| Evidence | Expected result | Result |
| --- | --- | --- |
| Ranking/frame truth table | Exact positions and cumulative values under ties | Pending |
| Session boundary suite | Hand-calculated session IDs and counts | Pending |
| Late-data replay | Affected horizon converges; unaffected rows unchanged | Pending |
| Scale/plan run | Sort, spill, partition skew, duration, and output size captured | Pending |

## Debugging, performance, and operations

For wrong outputs, inspect partition keys, total order, peer groups, frame text,
input duplicates, cutoff, time zone, and rule version. Compare a single safe
entity trace before and after each CTE. For slow output, inspect sort keys,
partition sizes, estimated/actual rows, memory, disk spill, and whether compatible
windows share a sort.

Window work often requires sorting `N` rows and holding partition/frame state.
Large skewed partitions dominate average behavior. Observe freshness, late-event
rate, revised sessions, largest partition, spill bytes, duration, cancelled
queries, and reconciliation deltas. Indexes may help input ordering/filtering but
do not guarantee the optimizer can avoid a sort.

Rule changes require new session/metric versions, bounded historical backfill,
old/new reconciliation, consumer cutover, and rollback. Stable external IDs must
not be tied to engine-specific row numbering.

## Common pitfalls

### Pitfall: window `ORDER BY` as final display order

Window ordering defines calculation only. Add an outer `ORDER BY` for deterministic
result delivery.

### Pitfall: unspecified frame

Defaults vary by function/context and peers matter. Declare `ROWS BETWEEN ...`
when rowwise cumulative behavior is intended.

### Pitfall: treating batch sessionization as final forever

Late data can revise boundaries. Publish cutoff, correction policy, and version.

## Working example

- SQL/tests: planned ranking, running revenue, session, gap/island, pivot, and cohort suite
- Expected result: deterministic hand-calculated outputs plus late-data correction
- Scale represented: bounded fixture; skewed 100M-row plan pending
- Remaining risk: time-zone/dialect behavior, memory/spill, privacy, and late revisions

## Knowledge check

1. Contrast `GROUP BY` with `SUM(...) OVER (...)` in output grain.
2. Predict `ROW_NUMBER`, `RANK`, and `DENSE_RANK` for tied values.
3. Explain how `ROWS` and a peer-sensitive frame differ at tied timestamps.
4. Sessionize gaps of 29:59, 30:00, and 30:01 under the stated rule.
5. Diagnose a late event that merges two published sessions.
6. Design a safe change from a 30- to 20-minute session rule.

## Key takeaways

- Windows retain row grain while adding neighborhood calculations.
- Partition, total order, and frame are independent correctness choices.
- Time-series analysis needs explicit clocks, zones, cutoff, and revision policy.
- Session and cohort outputs are sensitive derived data with lifecycle duties.
- Ties, late data, and skew belong in evidence, not footnotes.

## Resources

- [PostgreSQL documentation: window functions](https://www.postgresql.org/docs/current/functions-window.html) (reviewed 2026-09)
- [PostgreSQL tutorial: window functions](https://www.postgresql.org/docs/current/tutorial-window.html) (reviewed 2026-09)

## Related topics

- [Aggregation, grouping, and set operations](04-aggregation-grouping-and-set-operations.md)
- [Query plans, indexes, statistics, and optimization](08-query-plans-indexes-statistics-and-optimization.md)

## Completion checklist

- [x] Ranking, frames, running values, sessions, gaps/islands, pivots, and cohorts covered
- [x] Identity, time, privacy, late data, skew, recovery, and migration addressed
- [x] Deterministic and adversarial evidence designed
- [ ] Fixture, replay, plan, and realistic-scale evidence executed

