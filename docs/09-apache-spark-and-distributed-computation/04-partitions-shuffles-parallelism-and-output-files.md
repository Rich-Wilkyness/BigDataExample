# Partitions, Shuffles, Parallelism, and Output Files

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: PySpark / Spark SQL / Batch / Storage  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A Spark partition is a unit of distributed work at a particular plan boundary.
It is not automatically the same as a source directory partition, Parquet row
group, shuffle partition, output file, or business partition. Confusing these
layers causes idle executors, tiny files, oversized tasks, excess shuffle, and
consumer-unfriendly storage.

A shuffle redistributes records so an operator's required keys are co-located.
It is often necessary for correct grouping, joining, or global ordering. The goal
is to control its keys, bytes, balance, and downstream layout—not to eliminate
every exchange.

## Learning objectives

- Distinguish source, file-scan, DataFrame, shuffle, task, storage, and business partitions.
- Predict when grouping, joining, sorting, and repartitioning cause exchanges.
- Choose `repartition`, keyed repartition, `coalesce`, and no change from evidence.
- Estimate task and output-file counts and diagnose skew or small-file amplification.
- Separate correct dataset publication from individual task/file completion.

## Prerequisites

- [Partitioning, hashing, range routing, and rebalancing](../08-distributed-systems-foundations/02-partitioning-hashing-range-routing-and-rebalancing.md)
- [Shuffles, skew, stragglers, and hot partitions](../08-distributed-systems-foundations/06-shuffles-skew-stragglers-and-hot-partitions.md)
- [Lazy evaluation, logical plans, and physical plans](03-lazy-evaluation-logical-and-physical-plans.md)

## Mental model and terminology

Android resource qualifiers partition files by lookup dimensions, but they do not
determine thread scheduling. Likewise, `event_date=2026-09-07/` is a durable
storage-pruning partition; it does not guarantee Spark's in-memory partitioning
by date. The analogy stops because Spark continuously changes execution
partitioning across scans and exchanges.

| Layer | Meaning | Primary owner |
| --- | --- | --- |
| Business partition | Scope independently processed/published, such as UTC date | Dataset contract owner |
| Storage partition | Directory/table transform used for organization and pruning | Storage/table owner |
| File/row group | Durable physical layout and scan metadata unit | Writer/format |
| Scan partition | Input split assigned to one scan task | Data source + Spark planner |
| DataFrame partition | Current distribution of rows during execution | Spark physical plan |
| Shuffle partition | One post-exchange bucket and downstream task input | Spark SQL/runtime config |
| Output file | Usually one task result per output partition, with commit details | Writer/commit protocol |

## Requirements, estimates, and invariants

For the reference day, estimate 3 GiB compressed input in 16 files. Suppose the
candidate output is only 80 MiB across 2,000 product groups. A target file range
of roughly 128–512 MiB is a storage hypothesis, but the small daily result may
justify one or a few files per tenant/date scope instead. Measure compression and
consumer behavior before standardizing.

- Every accepted record routes to exactly one logical aggregate group.
- Changing execution partition counts cannot change the unordered business result.
- No single ordinary task exceeds memory, spill, or duration budgets under representative distribution.
- Output file count and size are deliberate and decoupled from maximum compute parallelism.
- A failed/retried task cannot expose duplicate committed files to consumers.
- One certified manifest/catalog commit identifies the complete output generation.

## Narrow and wide operations

| Operation | Typical dependency | Reason |
| --- | --- | --- |
| `select`, deterministic `withColumn`, row filter | Narrow | Each output row depends on one input partition row |
| `coalesce(n)` downward | Usually narrow | Combines existing partitions without full redistribution |
| `repartition(n)` | Wide | Redistributes records to new buckets |
| `repartition(n, keys...)` | Wide | Co-locates equal keys under hash partitioning |
| `groupBy(...).agg(...)` | Wide unless requirement already satisfied | All values for each group must meet |
| Most equi-joins | Wide on one/both sides | Equal join keys must meet unless broadcast/co-partitioning applies |
| Global `orderBy` | Wide | Produces range/order distribution |

The actual physical plan is authoritative for a pinned version and configuration.
Optimizer rules can remove, reuse, or insert exchanges.

## Repartitioning and output control

```python
from pyspark.sql import functions as F

metrics = aggregate_events(valid_events)

# Compute distribution and durable table partitioning are separate decisions.
prepared = metrics.repartition(8, "event_date_utc")

(
    prepared.write
            .mode("errorifexists")
            .partitionBy("event_date_utc")
            .parquet(candidate_uri)
)
```

This code requests a shuffle to eight execution partitions before writing and a
directory layout by date. It does not promise exactly eight output files overall:
empty partitions, task retries, writer behavior, multiple date values, and commit
protocol affect artifacts. Never encode a correctness contract as “Spark writes
one named file.” Publish a dataset or partition manifest.

Use `coalesce` when reducing partitions without balanced redistribution is
acceptable. Use `repartition` when balance or exact key distribution justifies a
shuffle. Avoid `coalesce(1)` as a habitual export mechanism: it serializes output
through one task and can create a large straggler. When a true single-file consumer
contract exists, quantify the maximum bytes and publish through an explicit export
stage distinct from the scalable curated dataset.

## Shuffle lifecycle and capacity

```text
upstream task attempts
   | partition records by downstream bucket
   | buffer / sort / spill / write shuffle blocks
   v
shuffle storage and network transfer
   |
   | downstream task fetches blocks from many upstream tasks
   v
aggregate/join/sort task -> candidate output task
```

Estimate shuffle with observed input rows, serialized key/value widths, map-side
aggregation reduction, replication (for broadcast), compression, and skew. A
3 GiB compressed source can expand substantially after decoding and can shuffle
more or less than 3 GiB. Compressed file bytes are not a task-memory estimate.

Useful metrics include records/bytes read and written, remote/local shuffle read,
fetch wait, spill memory/disk bytes, task duration distribution, peak execution
memory, and output bytes/files. Percentiles alone can hide one catastrophic hot
partition; inspect maxima and distribution.

## Output publication boundary

Task commit protocols prevent some duplicate-attempt file conflicts, but a
successful write action is not automatically the desired cross-dataset business
transaction. A robust batch flow writes a run-scoped candidate, validates file
inventory/schema/row counts/keys/metrics, then atomically changes the consumer
reference (catalog snapshot, table transaction, or generation manifest). On
failure, the prior generation remains authoritative and abandoned candidates are
cleaned by a separate retention workflow.

## Failure model and recovery

| Failure | Detection | Containment/recovery | Consumer behavior |
| --- | --- | --- | --- |
| Oversized scan split | Long/failed task, high input bytes | Repair file layout/split settings | Prior generation remains |
| Skewed shuffle bucket | One/few long tasks, disproportionate bytes/spill | Change key/algorithm, AQE/skew strategy, or isolate hot key | No partial publish |
| Lost shuffle block | Fetch failure/retry | Recompute source attempt if lineage/input exists | Delayed completion |
| Executor disk full | Spill/write error | Fail/retry elsewhere; resize/fix partitioning | Candidate not certified |
| Tiny output files | Large file count, metadata/list latency | Separate compute count from write compaction/layout | Correct but costly candidate |
| Duplicate attempt file | Commit conflict/orphan | Supported committer + run isolation + inventory check | Only certified files visible |
| Partial candidate | Missing expected partitions/manifest | Fail quality gate and retain previous generation | Stable previous result |

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Partition invariance | Deterministic fixture / local Spark | Run with 1, 2, 8 shuffle partitions | Same unordered rows/values | Pending |
| Plan evidence | Same fixture | Inspect before/after repartition/group | Exchanges and partition counts explained | Pending |
| Skew fixture | 35% hot tenant plus uniform keys | Record per-task rows/bytes/time/spill | Hot distribution detected | Pending |
| Output layout | Representative compressed data | Count files/sizes and read result | Layout budget and exact result hold | Pending |
| Commit failure | Fault-injected write | Kill attempt/application during candidate write | No partial candidate is published | Pending |

## Debugging guide

Identify the slow stage and its exchange. Sort tasks by duration, input/shuffle
bytes, spill, GC, fetch wait, and peak memory. Compare median with maximum and map
the outlier partition back to keys using safe aggregated diagnostics. For file
problems, inventory source/output file counts and size histograms, scan partition
counts, listing time, and partition-directory cardinality. Preserve the failed
run manifest so reproduction uses the same files.

## Common pitfalls

### Pitfall: one source file means one Spark partition

Sources can combine small files or split large files depending on format and
configuration. Confirm scan partitions and task input bytes from the plan/UI.

### Pitfall: more partitions always means faster

Too few partitions limit parallelism and enlarge tasks; too many add scheduling,
shuffle-block, file, and metadata overhead. Tune against bytes, CPU per row,
memory, executor cores, task duration, and output needs.

### Pitfall: partitioning by a high-cardinality key on storage

Directory partitioning by event or user ID creates enormous metadata and tiny
files. Storage partitions should match common selective predicates with bounded
cardinality; clustering/sorting/table-format features may serve other locality.

## Security, governance, and operations

Storage partition paths can expose dates, regions, or tenants. Do not partition
paths by direct sensitive identifiers unless governance explicitly allows it.
Restrict shuffle/spill/temp directories and candidate prefixes; encrypt and expire
them. Alert on task maximum/median ratio, retry storms, spill, fetch failures,
abnormal scan/output file counts, output-size drift, and incomplete generations.

## Compatibility, backfill, and delivery

Changing shuffle partitions should preserve results but may alter floating-point
aggregation order, file names, layout, and task resource needs. Use decimal or
numerically stable contracts where exactness matters. Backfills need separate
run/generation namespaces and bounded date scopes. Roll out layout changes with
dual reads or a shadow candidate, compare pruning and consumer performance, then
cut over atomically.

## Working example

- PySpark source/tests/representative files: Planned
- Expected result: partition-invariant metrics and certified candidate layout
- Scale represented: none yet
- Remaining risk: real file splitting, network shuffle, skew, task commit, object-store semantics, and consumer read cost

## Knowledge check

1. Distinguish the seven partition/file layers in the terminology table.
2. Predict exchanges for filter, group, keyed repartition, broadcast join, and global sort.
3. Estimate useful initial task count from input bytes and a target bytes-per-task range.
4. Diagnose one task reading 40% of shuffle bytes.
5. Design a single-file export without making the curated dataset single-threaded.
6. Explain why completed task files do not prove a complete published generation.

## Key takeaways

- Execution partitions, storage partitions, and files are related but distinct.
- Shuffles are correctness mechanisms whose movement and balance need budgets.
- Compute parallelism and output layout should be tuned separately.
- Partition-count changes should preserve business results, not necessarily file identity.
- Dataset publication requires certification beyond successful task writes.

## Resources

- [Spark SQL performance tuning](https://spark.apache.org/docs/4.2.0/sql-performance-tuning.html) (reviewed 2026-09)
- [Spark configuration: file and shuffle partition settings](https://spark.apache.org/docs/4.2.0/configuration.html) (reviewed 2026-09)
- [Spark web UI stage and task metrics](https://spark.apache.org/docs/4.2.0/web-ui.html) (reviewed 2026-09)

## Related topics

- [Joins, aggregation, broadcasting, and skew](05-joins-aggregation-broadcasting-and-skew.md)
- [Parquet, pushdown, partition pruning, and catalogs](06-parquet-pushdown-partition-pruning-and-catalogs.md)

## Completion checklist

- [x] Partition layers, shuffle, parallelism, file layout, commit, and publication explained
- [x] Skew, capacity, failure, security, quality, operations, and evolution addressed
- [ ] Partition, plan, skew, layout, and commit-failure evidence run

