# Query Plans, Indexes, Statistics, and Optimization

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic data engineering / SQL / Storage / Platform  
> Data scale: Single machine; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

SQL states a logical result; the optimizer chooses a physical plan from the
engine's operators, metadata, statistics, indexes, memory, and cost model.
Optimization is therefore an evidence loop: protect correctness, characterize a
workload, capture an actual plan, locate the dominant resource, change one
assumption, and measure again.

This guide covers scans, join algorithms, cardinality estimation, index tradeoffs,
sorting, spilling, and regression evidence. It does not prescribe a universal
index recipe or claim that a local plan predicts distributed/cloud behavior.

## Learning objectives

After completing this guide, you should be able to:

- Read a plan as a tree of row-producing operators.
- Compare estimated with actual cardinality and trace error propagation.
- Explain scan, nested-loop, hash-join, merge-join, aggregate, and sort tradeoffs.
- Design indexes from workload predicates, joins, ordering, and write cost.
- Build representative, safe benchmarks and performance regression gates.
- Diagnose skew, stale statistics, memory spill, and plan changes.

## Prerequisites

- All preceding guides in this area, especially [joins](03-joins-cardinality-and-missing-matches.md) and [transactions](07-ddl-constraints-transactions-and-concurrent-change.md)

## Mental model

```text
SQL + schema/constraints + statistics + parameters + configuration
                         |
                    optimizer estimate
                         |
                    physical plan
                         |
        actual rows/time/I/O/memory/spill under one workload
```

An Android build plan is a loose analogy: declared dependencies become an
execution graph chosen by tooling. It stops at the cost model—database plans are
often selected using uncertain data distributions and parameter selectivity, and
the same SQL can receive a different plan as statistics or cardinalities change.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Sequential scan | Read qualifying data by scanning the relation/storage range |
| Index scan | Use an auxiliary structure to locate/order candidates, then possibly fetch table rows |
| Selectivity | Fraction of input rows expected to satisfy a predicate |
| Cardinality estimate | Optimizer prediction of rows emitted by an operator |
| Nested loop | Repeatedly find inner matches for outer rows |
| Hash join | Build a hash structure for one side and probe it with the other |
| Merge join | Consume compatibly ordered inputs by join key |
| Spill | Write intermediate state to storage because memory is insufficient |

## Requirements and workload assumptions

The target interaction queries a 35-day, approximately 100M-row `events` table
for one time interval and product/event subset, with 20 concurrent readers and a
500 ms p95 objective. The daily build scans about 3M events and publishes within
15 minutes. These values are hypotheses until measured.

Invariants are:

- Optimized and baseline queries return identical bags or ordered sequences under
  the declared contract.
- Plans are captured with engine/version, schema/indexes, statistics state,
  parameters, cache state, dataset generator/version, and concurrency.
- Representative data preserves key correlations, null rates, skew, time
  clustering, row widths, and match distributions without exposing production data.
- Index benefit is assessed against writes, storage, maintenance, and migrations.
- `EXPLAIN ANALYZE`-style execution is never run casually on destructive or
  unbounded production statements.

## Reading a plan

Read from data-producing leaves toward the root. At each operator ask:

1. What is its input and output grain?
2. What are estimated and actual rows, loops, and row width?
3. Which predicate is an access condition and which is a residual filter?
4. Where are rows multiplied, removed, sorted, aggregated, or materialized?
5. What time, I/O, memory, temporary storage, and network did it consume?

A large estimate error low in a plan can cause an unsuitable join order or
algorithm above it. Faster execution does not repair wrong cardinality caused by
an incomplete join.

## Physical operators and tradeoffs

| Situation | Plausible operator | Strength | Risk/change point |
| --- | --- | --- | --- |
| Large fraction of compact table | Sequential scan | Efficient bulk I/O | Wasteful for selective query |
| Selective range with suitable index | Index scan | Avoids most candidates; may provide order | Random fetches and low selectivity can dominate |
| Small outer plus indexed inner | Nested loop | Excellent targeted lookups | Explodes when outer/inner matches exceed estimate |
| Equality join with build side fitting memory | Hash join | Linear-style probing | Memory, spill, skew, hashable equality required |
| Both inputs ordered on key | Merge join | Streams ordered equality/range work | Sort cost and duplicate groups |
| Many groups | Hash or sort aggregate | Partial/streaming opportunities vary | High cardinality/skew and spill |

The engine makes the choice. Forcing a strategy can stabilize one fixture while
hiding a statistics or workload problem.

## Index design

For the reference range query, a candidate might be:

```sql
CREATE INDEX events_product_time_idx
    ON events (product_id, event_time, event_id);
```

Column order encodes a workload hypothesis: equality on product, then a time
range, then a deterministic tie-breaker. It may not help a time-only daily scan.
Covering/included columns, partial indexes, expression indexes, clustered layout,
and index-only access are engine-specific and depend on visibility and storage
behavior.

Every index consumes storage, write I/O, cache, build time, log/replication
bandwidth, and maintenance effort. Redundant indexes can slow ingestion more than
they help reads. Constraints may create supporting indexes, but exact behavior is
engine-specific.

## Statistics and estimation

Optimizers commonly use row counts, value frequencies, null fractions, ranges,
and distinct-value estimates. Independent-column assumptions fail when attributes
are correlated—for example, an event name may strongly determine whether
`product_id` is null. Skew and newly arrived date ranges also cause errors.

Refresh or improve statistics only after observing estimate error and confirming
the data/change lifecycle. A statistics refresh can change plans across the
workload, so treat it as an operational change with comparison and rollback.

## Data flow, ownership, and trust boundaries

| Artifact | Owner | Contract/failure behavior |
| --- | --- | --- |
| Query/metric definition | Data-product team | Correct result and version independent of chosen plan |
| Schema/index/statistics | Database/platform owner with product input | Managed changes, maintenance, storage, rollback |
| Representative dataset | Test-data owner | Distribution fidelity, privacy review, reproducibility |
| Plan/benchmark record | Performance-test owner | Environment and workload metadata; safe redaction |

Plans may contain literals, object names, partitions, or distribution details.
Restrict and sanitize captures before sharing. Benchmark accounts are read-only
unless the test explicitly owns isolated writes.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Stale/skew-blind statistics | Estimated/actual row divergence | Refresh/improve statistics; rerun whole workload comparison |
| Plan regression after growth/deploy | Latency/I/O gate fails with same result | Roll back change or apply reviewed index/query repair |
| Hash/sort spill | Temp bytes and operator timing | Reduce width/population, adjust design/resources based on evidence |
| Index build blocks or exhausts storage | Lock/disk/replication alerts | Cancel if safe; use engine-supported phased/concurrent method; clean up |
| Fast but semantically changed rewrite | Result/mutation suite fails | Reject optimization and restore correct definition |
| Benchmark warms cache unrealistically | Cold/warm results diverge | Label cache state and test the intended operational mixture |

During overload, apply admission, timeout, cancellation, and workload isolation.
Do not let exploratory queries consume the resources required for ingestion or
publication recovery.

## Evidence-driven optimization loop

1. Freeze the result contract and correctness suite.
2. Define query mix, data shape, cache state, concurrency, and latency/cost budget.
3. Capture baseline result, actual plan, wall/CPU time, rows, I/O, memory, spill,
   storage, and write impact.
4. Identify the dominant operator and the uncertainty causing it.
5. Make one query/schema/statistics/configuration change.
6. Re-run correctness mutations and the entire representative workload.
7. Record benefit, regression, operational cost, rollback, and invalidating conditions.

Median-only measurements hide tail latency and noisy-neighbor effects. Repeat
runs, report distributions, and distinguish compilation/planning from execution
and client transfer.

## Data quality, testing, and evidence

The planned generator must produce deterministic 100K, 1M, and preferably
realistic larger scales with configurable product skew, time clustering, null
rates, duplicate deliveries, and join match rates. Synthetic evidence is not
production evidence.

| Evidence | Expected result | Result |
| --- | --- | --- |
| Correctness before/after | Identical declared result across every optimization | Pending |
| Actual plan baseline | Estimated/actual rows and resource hotspots recorded | Pending |
| Index comparison | Target workload benefit plus write/storage cost measured | Pending |
| Cardinality/skew sweep | Scaling curve and first bottleneck identified | Pending |
| Concurrent mix | p50/p95/p99, throughput, timeouts, and recovery captured | Pending |
| Plan regression gate | Material regression blocks delivery under defined tolerance | Pending |

## Debugging and operations

Correlate query version, plan fingerprint, dataset/statistics version, engine and
configuration version, parameters bucketed by safe selectivity class, runtime,
rows, I/O, spill, waits, timeout/cancel result, and consumer impact. Avoid raw
high-cardinality parameter labels.

When latency rises, confirm the result contract and input freshness first, then
compare current and known-good plans, cardinality estimates, table/index growth,
statistics age, cache, locks, concurrency, storage latency, and resource quotas.
Recovery is complete only when correctness and sustained workload objectives both
pass, not when one query becomes fast again.

## Common pitfalls

### Pitfall: indexing every filter column

Single-column indexes may not fit compound predicates and still tax every write.
Design from query shapes and test the complete workload.

### Pitfall: trusting estimated cost as elapsed time

Cost is an optimizer comparison unit, not a portable duration. Use actual
execution metrics in a controlled environment.

### Pitfall: optimizing a tiny fixture

Algorithm crossovers, spill, skew, and cache pressure often appear only at larger
cardinality. Test a scaling curve with realistic distributions.

### Pitfall: reading only the slowest operator

Find where rows or estimate error first diverge; the expensive parent may be a
symptom of a bad join or missing filter below it.

## Compatibility, migration, and delivery

Engine upgrades, statistics changes, indexes, configuration, and schema growth can
all change plans without query-text changes. Keep a representative suite and
plan/performance history, while gating on outcomes rather than brittle full-plan
text. Build/drop indexes through a rehearsed method with disk, lock, replication,
and rollback budgets. Dual-run rewritten queries against pinned versions and
reconcile before cutover.

## Working example

- SQL/data/tests: planned query suite, deterministic scale generator, plan recorder, and mutation cases
- Try it: pending engine selection and exact repeatable command
- Expected result: correct results plus measured plan/index/cardinality tradeoffs
- Scale represented: none yet; 100M retained rows and concurrency are estimates
- Remaining risk: engine/version changes, production skew, cache, locks, and mixed workload

## Knowledge check

1. Read a plan from leaves to root and state grain at every join/aggregate.
2. Explain how a 10x underestimate can make a nested loop fail at scale.
3. Design one index for product/time lookup and name a query it does not serve well.
4. Build a benchmark matrix across cardinality, skew, cache, and concurrency.
5. Diagnose a regression after statistics refresh without immediately forcing a plan.
6. Propose an index rollout, observation period, and rollback.

## Key takeaways

- Logical correctness is fixed before physical optimization begins.
- Plans are estimates made concrete by one execution under one environment.
- Cardinality error, skew, row width, memory, and I/O explain many plan failures.
- Indexes trade write/storage/operations cost for selected access paths.
- Performance evidence needs realistic distributions, concurrency, and repeatability.

## Resources

- [PostgreSQL documentation: using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html) (reviewed 2026-09)
- [PostgreSQL documentation: indexes](https://www.postgresql.org/docs/current/indexes.html) (reviewed 2026-09)
- [PostgreSQL documentation: planner statistics](https://www.postgresql.org/docs/current/planner-stats.html) (reviewed 2026-09)
- [SQLite documentation: query planner](https://www.sqlite.org/queryplanner.html) (reviewed 2026-09)

## Related topics

- [Joins, cardinality, and missing matches](03-joins-cardinality-and-missing-matches.md)
- [Window functions, time series, and analytical patterns](06-window-functions-time-series-and-analytical-patterns.md)
- [DDL, constraints, transactions, and concurrent change](07-ddl-constraints-transactions-and-concurrent-change.md)

## Completion checklist

- [x] Plans, scans, joins, estimates, indexes, statistics, and optimization loop explained
- [x] Correctness, scale, skew, concurrency, security, operations, and migration addressed
- [x] Workload and evidence matrix stated conservatively
- [ ] Scale generator, plan recorder, index comparison, and concurrency evidence executed
