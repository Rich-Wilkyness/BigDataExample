# MapReduce, DAGs, and Data Locality

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / Batch / Distributed computation  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Distributed analytical engines split a logical transformation into stages and
partition tasks. MapReduce supplies a durable foundation: map independently,
redistribute records by key, then reduce each key group. Modern engines express
larger directed acyclic graphs (DAGs), pipeline compatible operations, and insert
materialization boundaries where data must move or recovery needs stable state.

This guide focuses on execution semantics rather than an engine API. A declarative
SQL query or DataFrame call does not imply one machine, one pass, or source-code
order.

## Learning objectives

- Translate a grouped data transformation into map, shuffle, and reduce contracts.
- Distinguish logical plans, physical stages, tasks, partitions, and attempts.
- Identify narrow and wide dependencies and their recovery implications.
- Explain data, cache, and compute locality without assuming it is always possible.
- Read a DAG for movement, materialization, failure, and capacity risk.

## Prerequisites

- [Partitioning, hashing, range routing, and rebalancing](02-partitioning-hashing-range-routing-and-rebalancing.md)
- Set-based transformation and plans from [03 SQL and Analytical Querying](../03-sql-and-analytical-querying/README.md)

## Mental model and terminology

A Gradle task graph helps visualize dependencies and parallel branches. It stops
where one logical operator becomes thousands of partition tasks, a shuffle moves
intermediate records over the network, and failed work is recomputed from lineage.

```text
input partitions
  | map: validate/project (narrow, partition-local)
  | combine: optional partial aggregate
  | shuffle by (tenant, product, UTC date)
  v
reduce partitions
  | aggregate/finalize (all values for one key together)
  v
candidate output partitions -> quality -> generation manifest
```

| Term | Meaning in this guide |
| --- | --- |
| Logical plan | Engine-independent relational/transformation intent |
| Physical plan | Selected operators, exchanges, algorithms, and partitioning |
| Stage | Tasks executable without an intervening global data exchange |
| Task | Work for one stage partition; may have multiple attempts |
| Narrow dependency | Each output partition depends on a small known input subset |
| Wide dependency | Output partitions depend on many input partitions, usually through shuffle |
| Lineage | Derivation information used for audit and possibly recomputation |

## Requirements, scale assumptions, and invariants

The daily reference job reads 3 million immutable events from 16 input partitions
and emits daily product metrics. Estimated compressed input is about 3 GiB before
format/metadata overhead. The final business grain is one tenant, product, and UTC
date; an optional combiner may reduce bytes but cannot change that result.

- Every accepted logical event contributes exactly according to the metric contract.
- All values for one final group reach one reduce partition under one routing version.
- Map/reduce logic is deterministic for pinned inputs, code, configuration, and schema.
- Task-attempt output stays private until the engine selects a winner.
- Dataset publication occurs only after all required partitions and quality checks pass.
- Re-execution cannot mix old and new intermediate/output versions.

## From logical transformation to physical DAG

```sql
-- Grain: one tenant, product, and UTC event date.
-- Dialect-neutral model; event_id is deduplicated at the accepted boundary.
SELECT tenant_id,
       product_id,
       event_date_utc,
       COUNT(*) AS event_count
FROM accepted_product_events
GROUP BY tenant_id, product_id, event_date_utc;
```

The group-by normally requires redistribution unless the input already satisfies
the exact partitioning contract. Projection and validation can run within input
partitions. A partial aggregate is safe for associative operations such as count
or sum, but an average must combine `(sum, count)`, not average partial averages.
Order-sensitive and non-associative metrics need a different contract.

| Operator/dependency | Movement/materialization | Recovery unit | Main risk |
| --- | --- | --- | --- |
| Filter/project map | Usually partition-local | Input partition task | CPU/input corruption |
| Local combine | In-memory/spill within task | Recompute map attempt | Memory and semantic safety |
| Repartition/group | Network/disk shuffle | Map block or reduce task | Skew, fan-out, lost intermediates |
| Reduce aggregate | Reads many map outputs | Reduce partition task | Hot key/straggler |
| Output publication | Durable storage + manifest | Dataset generation | Partial/mixed visibility |

## Data locality and materialization

Prefer moving compute toward large data when storage exposes locality and the
scheduler can use it. In object storage, rack-local disk may not exist; connection
reuse, region locality, cache locality, file sizing, and scan pruning become more
important. Waiting too long for locality can waste available capacity, so schedulers
balance locality delay against queue and deadline budgets.

Persist an intermediate when it creates a valuable recovery boundary, is reused,
or prevents expensive recomputation. Each materialization also adds serialization,
I/O, storage lifecycle, compatibility, encryption, and cleanup obligations.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Consumer behavior |
| --- | --- | --- | --- |
| Map task fails | Attempt state/error | Retry partition from immutable input | No candidate publish |
| Shuffle block lost | Fetch/checksum failure | Recompute producing map attempt | Reduce waits/retries within budget |
| Reduce task fails | Attempt state/error | Retry reduce from valid shuffle inputs | No partial generation |
| Driver/coordinator loss | Missing control progress | Restore DAG/run state or restart pinned run | Prior generation remains |
| Invalid record | Validation rule and safe location | Quarantine or fail declared scope | Completeness flag follows contract |
| Output task wins twice | Conflicting attempt commit | Fenced attempt protocol chooses one | One partition version visible |

## Security, privacy, and governance

Intermediate data inherits source classification. Encrypt transport and spill,
restrict worker/storage identities, sanitize diagnostics, isolate tenants where
required, and delete shuffle/caches by policy. Plans and lineage may expose column,
path, and tenant names and need controlled access.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Deterministic local model | Map/combine/shuffle/reduce fixture | Result matches direct reference aggregate | Pending |
| Partition property test | Randomize input and partition count | Same business result | Pending |
| Failure test | Remove map/shuffle/reduce attempt | Recompute converges without duplicate output | Pending |
| Plan review | Inspect stage/exchange boundaries | All wide dependencies and materializations explained | Pending |
| Byte accounting | Record input, shuffle, spill, and output bytes | Capacity estimate reconciles | Pending |

## Common pitfalls

### Pitfall: reading the API chain as execution order

Optimizers may reorder, fuse, prune, or exchange operations. Inspect the physical
plan and validate semantics at data boundaries.

### Pitfall: assuming a combiner always runs

An optimization cannot be required for correctness. Map output and reduce logic
must remain correct if combination runs zero, one, or many times.

### Pitfall: persisting every stage

Extra checkpoints may dominate runtime and lifecycle cost. Persist only when reuse,
recovery value, or recomputation risk justifies measured I/O.

## Performance, operations, and compatibility

Observe plan version, stage/task/attempt counts, input locality, bytes and records,
shuffle read/write, fetch wait, spill, serialization, cache hit, task percentiles,
and candidate/publish state. Compare estimates to p95/p99 partitions, not averages.
Plan changes after engine, schema, statistics, or configuration upgrades require
representative explain/plan capture and result/performance regression tests.

## Working example

- Python/tests/data: planned local MapReduce simulator, partition-invariance tests, fault injection, and byte accounting
- Expected result: direct and distributed models agree; lost intermediates recompute safely
- Scale represented: none yet; bounded local fixture followed by multi-process tasks
- Remaining risk: real engine optimizer, shuffle service, executor memory, and object-store locality

## Knowledge check

1. Draw the physical stages for the reference group-by.
2. Predict whether filter, join, group-by, and sort create narrow or wide dependencies.
3. Explain why averaging partition averages is usually incorrect.
4. Decide whether to persist an expensive shared intermediate.
5. Design recovery after a shuffle block disappears.

## Key takeaways

- Logical transformations become stages, partition tasks, attempts, and exchanges.
- A shuffle is a correctness boundary and a major movement cost.
- Optimizations such as combiners cannot be required for correctness.
- Locality depends on the storage architecture and competes with wait time.
- Publication, not task completion, defines consumer-visible success.

## Resources

- [MapReduce: Simplified Data Processing on Large Clusters](https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/) (reviewed 2026-09)
- [Dryad: Distributed Data-Parallel Programs from Sequential Building Blocks](https://www.microsoft.com/en-us/research/publication/dryad-distributed-data-parallel-programs-from-sequential-building-blocks/) (reviewed 2026-09)

## Related topics

- [Shuffles, skew, stragglers, and hot partitions](06-shuffles-skew-stragglers-and-hot-partitions.md)
- [Planned Apache Spark and Distributed Computation area](../COVERAGE.md#09-apache-spark-and-distributed-computation)

## Completion checklist

- [x] Map, combine, shuffle, reduce, DAG, stage, task, lineage, locality, and materialization explained
- [x] Grain, ownership, failure, security, quality, capacity, compatibility, and publication addressed
- [ ] Local-model, partition-property, failure, plan, and byte-accounting evidence run
