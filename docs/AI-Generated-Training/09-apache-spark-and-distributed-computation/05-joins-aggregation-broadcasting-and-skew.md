# Joins, Aggregation, Broadcasting, and Skew

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: PySpark / Spark SQL / Distributed computation  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Joins and aggregations change cardinality and often redistribute data. Their
correctness begins with grain, key uniqueness, `NULL` policy, effective-time
semantics, and reconciliation—not with a preferred Spark join hint. Their
performance depends on actual side sizes, key distribution, statistics, row
width, partitioning, and executor resources.

Broadcasting sends a sufficiently small relation to executors so the large side
need not shuffle for an eligible join. Skew handling splits or restructures
disproportionate work. Both are conditional physical strategies, not substitutes
for a correct relational contract.

## Learning objectives

- Predict join output cardinality from input grain and key multiplicity.
- Read physical join/aggregate strategies and the exchanges they require.
- Decide when broadcast is safe using serialized size and executor concurrency.
- Detect and repair hot-key skew without duplicating or dropping results.
- Validate adaptive decisions and preserve semantics across strategy changes.

## Prerequisites

- Joins, grouping, and windows from [03 SQL and Analytical Querying](../03-sql-and-analytical-querying/README.md)
- Grain and slowly changing dimensions from [05 Data Modeling and Business Semantics](../05-data-modeling-and-business-semantics/README.md)
- [Partitions, shuffles, parallelism, and output files](04-partitions-shuffles-parallelism-and-output-files.md)

## Mental model and terminology

A Kotlin `Map<Id, Value>` lookup resembles a broadcast hash join: build a small
lookup and apply it while scanning many records. The analogy stops because Spark
serializes and transfers the relation, each executor/task consumes memory, SQL
`NULL` and duplicate-key semantics apply, and the optimizer may choose another
strategy.

| Term | Meaning in this guide |
| --- | --- |
| Build side | Relation materialized into an in-memory join structure |
| Stream/probe side | Relation scanned and matched against the build structure |
| Sort-merge join | Both sides redistributed/sorted as required, then merged by key |
| Broadcast hash join | Small eligible side distributed to executors for local probing |
| Cardinality | Number of rows at a boundary; join multiplicity can expand it |
| Skew | Unequal key/partition distribution causing disproportionate work |
| Salting | Adding controlled subkeys to spread a hot key, with required semantic recombination |
| AQE skew handling | Runtime splitting/coalescing/strategy changes based on observed shuffle statistics |

## Requirements, assumptions, and invariants

The event side has one accepted row per `(tenant_id, event_id)`. The product
dimension must supply exactly one applicable row per event under tenant/product
and effective-time conditions. The current snapshot is estimated below 10 MiB,
but that estimate must be measured in Spark's broadcast representation and may
grow.

- Join keys are normalized to compatible types before joining.
- Dimension uniqueness/effective intervals are validated before enrichment.
- Unknown products follow a declared reject, quarantine, or “unknown member” policy.
- Join output count reconciles to the accepted event count for a mandatory many-to-one enrichment.
- Aggregate partial/final operations preserve metric semantics; averages combine sum/count, not averages.
- Optimization hints never change business results.
- Hot-key repair is deterministic and tested across partition counts.

## Correctness before strategy

```sql
-- Spark SQL: event grain must remain one row per accepted event.
SELECT e.tenant_id,
       e.event_id,
       e.product_id,
       e.event_time,
       p.category,
       e.revenue_usd
FROM valid_events e
LEFT JOIN product_dimension p
  ON e.tenant_id = p.tenant_id
 AND e.product_id = p.product_id
 AND e.event_time >= p.valid_from
 AND e.event_time <  p.valid_to;
```

Before tuning, assert dimension intervals do not overlap for the same key and that
every event produces exactly one result under the missing-dimension policy. A
many-to-many accident can finish quickly and still corrupt all downstream sums.

```python
from pyspark.sql import functions as F

duplicate_keys = (
    products.groupBy("tenant_id", "product_id")
            .count()
            .where(F.col("count") > 1)
)

# For a current-snapshot dimension, fail before relying on a many-to-one join.
if duplicate_keys.limit(1).count() != 0:
    raise ValueError("product dimension violates current-key uniqueness")
```

The action above is deliberate validation but can scan/shuffle the dimension.
Production design may certify uniqueness when publishing the dimension and consume
that evidence here, while still monitoring reconciliation.

## Strategy decision table

| Requirement/evidence | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| One side demonstrably small and eligible | Optimizer-selected or explicit broadcast after measurement | Avoids large-side shuffle | Build memory/transfer/time grows or stats are stale |
| Both sides large, equi-join, sortable keys | Sort-merge join | Scales through partitioned shuffle/sort | Existing compatible partitioning or different distribution wins |
| Shuffled build side fits per partition | Shuffled hash join where supported/chosen | Avoids sorting one strategy path | Memory pressure or key distribution changes |
| Non-equi/cross predicate | Specialized/nested-loop strategy with strict cardinality bound | General equality hash/merge unavailable | Rewrite model or pre-bound candidate pairs |
| Skew appears only at runtime | AQE skew optimization first, then validate | Uses observed shuffle sizes | Hot key still exceeds resource/deadline budget |
| Known semantic hot key | Isolate, pre-aggregate, or carefully salt | Makes distribution explicit | Recombination cost/complexity exceeds benefit |

Spark 4.2's documented automatic broadcast threshold defaults to 10 MiB, but a
default is not a capacity proof. Concurrent broadcasts, executor heap, timeouts,
statistics, relation expansion, and adaptive conversion all matter. Hints express
preference and are not guaranteed for unsupported join types.

## Aggregation and map-side reduction

Counts and sums can be partially aggregated before shuffle, reducing bytes. Exact
distinct counts may require large state/shuffle; approximate algorithms trade an
explicit error bound for resources. Collecting all values per key creates
unbounded per-key state and is usually the wrong shape.

| Metric | Safe distributed state | Unsafe shortcut |
| --- | --- | --- |
| Count | Integer count, then sum partial counts | Counting partitions |
| Sum decimal | Decimal partial sum with overflow contract | Binary float without error budget |
| Average | `(sum, count)`, then divide | Average of partition averages |
| Min/max | Partial min/max | Assuming input order |
| Distinct | Exact set/shuffle or declared approximation | Summing per-partition distinct/duplicates ignored |

## Skew diagnosis and repair

Skew can arise in input files, join keys, group keys, `NULL`/default keys, or
post-filter cardinality. Diagnose using task-level maximum versus median rows,
shuffle bytes, duration, spill, and memory plus a safe heavy-hitter profile.

Repair ladder:

1. Confirm it is distribution skew rather than one corrupt/huge file or slow executor.
2. Filter/project earlier and fix accidental default/null key concentration.
3. Broadcast a truly small side if that removes the skewed exchange safely.
4. Pre-aggregate the high-volume side before joining when semantics permit.
5. Let AQE split skewed partitions and validate its final plan/metrics.
6. Isolate known hot keys into a separate path or salt them, then recombine exactly.
7. Revisit the data model if a many-to-many explosion is being mistaken for skew.

For salting a large-side hot key, replicate the matching small-side row across the
same finite salts, assign each large row deterministically to one salt, join on
key+salt, and remove/recombine salt at the final business grain. Random salt makes
reruns harder to compare; incorrect replication drops matches or multiplies them.

## Failure model and recovery

| Failure | Detection | Containment/recovery | Evidence |
| --- | --- | --- | --- |
| Many-to-many explosion | Join rows far above expected, huge shuffle | Fail cardinality gate; repair dimension/grain | Key multiplicity report |
| Broadcast OOM/timeout | Executor/driver memory or broadcast timeout | Remove hint, fix stats, use scalable join | Representative load run |
| One hot reduce task | Max task bytes/time dominates | AQE, pre-aggregate, isolate, or salt | Before/after task distribution |
| Null/default hot key | Key-frequency and quality checks | Classify missing keys; separate policy | Null/missing reconciliation |
| Stale stats choose bad plan | Estimate vs actual divergence | Refresh stats or avoid brittle hint | Cost/final plan comparison |
| Retry after shuffle loss | Fetch/task retry | Recompute pure partitions | Exact result after injected loss |
| Non-associative aggregate drift | Partition-count result mismatch | Correct state/algorithm or define tolerance | Property/metamorphic test |

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Cardinality contract | Match/missing/duplicate dimension fixture | Run each join type | Exact expected row counts and missing policy | Pending |
| SQL/DataFrame equivalence | Same fixture | Compare unordered results | Exact equality | Pending |
| Strategy plan | Small and oversized dimension fixtures | Inspect initial/final plans | Broadcast only within safe case | Pending |
| Skew benchmark | Uniform vs 35% hot-key datasets | Compare task distribution/runtime/spill | Repair lowers tail without result change | Pending |
| Executor-loss test | Cluster shuffle job | Remove executor during join | Retry converges to exact result | Pending |

## Debugging guide

First compare input and output grain/counts, key multiplicities, unmatched rows,
and `NULL` keys. Then inspect estimated/actual relation sizes, selected strategy,
exchange partitioning, and initial/final adaptive plans. Sort tasks by shuffle
read, output rows, spill, peak memory, GC, and duration. A fast but inflated join
is a correctness incident; a correct straggler is a capacity/availability incident.

## Common pitfalls

### Pitfall: broadcasting because a table has few rows

Wide rows, nested data, and serialization can make “few rows” large. Measure bytes,
account for concurrent tasks/broadcasts, and test executor memory.

### Pitfall: salting every key

Salting increases complexity and can replicate the other side unnecessarily.
Target proven hot keys, preserve deterministic routing, and reconcile after salt
removal.

### Pitfall: fixing a many-to-many bug with more executors

Capacity can hide but not repair wrong multiplicity. Validate dimension uniqueness,
temporal non-overlap, join predicates, and expected cardinality first.

## Security, performance, and operations

Heavy-hitter diagnostics can expose tenant or product identity; aggregate, hash,
limit, and restrict them. A broadcast copies sensitive dimension data across
executors, expanding its exposure footprint. Record join strategy, actual/estimated
rows and bytes, shuffle/spill, skew ratios, unmatched/duplicate counts, runtime,
and cost per run with bounded metric labels.

## Compatibility, migration, and delivery

Join selection and AQE behavior can change with Spark/configuration/statistics.
Treat hints as reviewed code and compare exact results plus final plans during
upgrades. For dimension schema/key changes, expand the dimension, validate
uniqueness and historical effective-time joins, shadow the candidate, reconcile,
then cut consumers over. Preserve the previous certified generation for rollback.

## Working example

- PySpark/SQL fixtures, tests, skew benchmark: Planned
- Expected result: cardinality-safe enrichment and exact aggregate under all strategies
- Scale represented: none yet
- Remaining risk: broadcast representation, executor memory, runtime AQE, shuffle/network, and production key distribution

## Knowledge check

1. Predict output rows for one-to-one, many-to-one, one-to-many, and many-to-many keys.
2. Explain when a 9 MiB dimension still may be unsafe to broadcast.
3. Design a fixture that distinguishes skew from join explosion.
4. Repair an average-of-averages aggregation.
5. Describe deterministic hot-key salting and its final reconciliation.
6. Identify evidence needed before forcing a join hint.

## Key takeaways

- Grain, uniqueness, and cardinality are correctness contracts before performance choices.
- Broadcast is a measured memory/network tradeoff, not a synonym for “dimension.”
- Runtime task distributions reveal skew that averages and plans can hide.
- AQE is useful but must be verified through final plans and metrics.
- Every skew repair must preserve the unsalted business result.

## Resources

- [Spark SQL performance tuning: statistics, joins, and AQE](https://spark.apache.org/docs/4.2.0/sql-performance-tuning.html) (reviewed 2026-09)
- [Spark SQL join syntax](https://spark.apache.org/docs/4.2.0/sql-ref-syntax-qry-select-join.html) (reviewed 2026-09)
- [Spark SQL null semantics](https://spark.apache.org/docs/4.2.0/sql-ref-null-semantics.html) (reviewed 2026-09)

## Related topics

- [Caching, memory, serialization, and Python UDFs](07-caching-memory-serialization-and-python-udfs.md)
- [Testing, tuning, failure diagnosis, and deployment](08-testing-tuning-failure-diagnosis-and-deployment.md)

## Completion checklist

- [x] Cardinality, strategies, broadcasting, aggregation, AQE, and skew repair explained
- [x] Correctness, failure, security, observability, capacity, and migration addressed
- [ ] Cardinality, equivalence, strategy, skew, and executor-loss evidence run

