# Shuffles, Skew, Stragglers, and Hot Partitions

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic data engineering / Distributed computation / Storage  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A shuffle redistributes records so a downstream operation has the required
co-location or ordering. It often adds serialization, network transfer, disk
spill, many-to-many block tracking, and a stage barrier. Skew makes that cost
unequal; a few partitions or keys then determine the whole job's completion time.

A straggler is an unusually slow task, not necessarily a failed one. Its cause may
be data volume, key frequency, join fan-out, hardware, throttling, garbage
collection, fetch retries, or another tenant. Mitigation begins with measurement.

## Learning objectives

- Explain why joins, groups, distinct, repartition, and global order may shuffle.
- Measure distribution with tails and largest-key shares rather than averages.
- Distinguish data skew, compute skew, infrastructure stragglers, and hot serving keys.
- Select pre-aggregation, salting, splitting, broadcast, or model changes safely.
- Budget shuffle fan-out, spill, network, and recovery amplification.

## Prerequisites

- [Partitioning, hashing, range routing, and rebalancing](02-partitioning-hashing-range-routing-and-rebalancing.md)
- [MapReduce, DAGs, and data locality](05-mapreduce-dags-and-data-locality.md)

## Mental model and terminology

```text
M map partitions each produce buckets for R reduce partitions

map 0: [r0][r1]...[rR] --\
map 1: [r0][r1]...[rR] ----> network/fetch -> reduce partitions
...                         /
map M: [r0][r1]...[rR] ----/

potential block relationships approach M x R even when many blocks are empty
```

| Term | Meaning in this guide |
| --- | --- |
| Shuffle | Redistribution that establishes downstream partitioning/order |
| Data skew | Unequal records/bytes across keys or partitions |
| Compute skew | Similar bytes require unequal CPU due to values or algorithm paths |
| Straggler | Task whose completion is far behind its peers |
| Hot key | One key dominates storage, compute, or request demand |
| Join fan-out | Multiple matches multiply output cardinality beyond expectation |
| Salt | Added subkey used to spread one logical key across physical groups |

## Requirements, assumptions, and invariants

The reference aggregate may receive 35% of all events from one tenant and an
unknown product can become a default key. The 45-minute budget includes shuffle,
with 15 minutes reserved for recovery. Initial 16-way partitioning is a hypothesis.

- Mitigation preserves final grain and metric semantics.
- No null/default/catch-all key grows without an explicit bound and policy.
- Join cardinality is validated before and after redistribution.
- Partition sizing accounts for uncompressed/in-memory expansion and spill.
- A task attempt reads one coherent shuffle generation.
- Tuning is justified by representative distribution evidence, not average bytes.

## Diagnose before changing partition count

| Observation | Likely cause | Confirm with | Candidate response |
| --- | --- | --- | --- |
| One partition has many more records/bytes | Hot key/range | Key frequency and partition histogram | Split/salt/model/range boundaries |
| Similar bytes, one task CPU-heavy | Compute skew/data values | CPU profile and record classes | Isolate expensive path or algorithm |
| Random host's tasks slow | Infrastructure contention | Host/disk/network/GC metrics | Reschedule, repair host, admission control |
| Join output explodes | Duplicate dimension or many-to-many join | Per-key multiplicities and grain test | Repair model/constraint before tuning |
| All tasks fetch slowly | Network/shuffle service saturation | Fetch wait, throughput, errors | Reduce bytes/fan-out or add measured capacity |

Increasing partition count can reduce ordinary partition size but cannot split one
indivisible hot key under plain hash grouping. It can also increase scheduler and
block metadata overhead.

## Mitigation decision table

| Constraint | Prefer | Correctness condition | Cost/risk |
| --- | --- | --- | --- |
| Associative aggregate with hot key | Partial aggregate before shuffle | Merge state is associative with explicit null semantics | More local memory |
| One hot aggregate key | Deterministic salting plus second combine | Every salt recombines to original key exactly once | Second stage and complexity |
| Small immutable join side | Broadcast/local lookup | Fits every worker and version is identical | Memory multiplication |
| Range imbalance | Sample and choose new boundaries | Sampling captures tails; routing is versioned | Rebalance/migration |
| Very large isolated tenant | Dedicated path/partition class | Outputs reconcile to same contract | Operational branching |
| Random slow attempt | Speculation after diagnosis | Attempt commit is idempotent and fenced | Duplicate resource use |

Skew mitigation is not only a performance change. Salting changes intermediate
identity, broadcast changes memory/failure behavior, and isolated paths need
reconciliation and compatibility ownership.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Consumer behavior |
| --- | --- | --- | --- |
| Partition OOMs repeatedly | Same partition/attempt memory failure | Stop blind retry; split or change algorithm | Prior generation remains |
| Shuffle fetch failures | Block/checksum/host errors | Recompute valid producer attempt | No mixed shuffle generations |
| Local disk fills | Spill/free-space metrics | Stop admission, clean safe orphan data, resize plan | No partial publish |
| Hot default key | Key-frequency quality rule | Quarantine/fix producer or salt with contract | Completeness is explicit |
| Speculative duplicates | Multiple attempts for same partition | Fence commit; clean loser outputs | One partition version |
| Join explosion | Output/input ratio and grain failure | Abort before publish; correct key/model | Prior generation remains |

## Security, privacy, and governance

Key-frequency samples and task diagnostics may expose tenant or product behavior.
Use hashed/safe exemplars, access control, minimum aggregation, retention limits,
and bounded labels. Temporary shuffle data needs encryption and cleanup; broadcast
data multiplies sensitive copies across workers.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Uniform versus skew fixture | Generate known distributions | Histograms and p99/max reveal skew | Pending |
| Hot-key failure demo | Route default key without mitigation | One partition dominates or fails | Pending |
| Mitigation equivalence test | Run baseline and salted/pre-aggregated variants | Identical business output | Pending |
| Join-fan-out test | Inject duplicate dimension keys | Quality gate stops publication | Pending |
| Capacity benchmark | Vary records, partitions, key exponent, memory | Runtime/bytes/spill limits recorded | Pending |

## Common pitfalls

### Pitfall: optimizing average partition size

Jobs finish at the tail. Report p50/p95/p99/max records, bytes, time, and largest
key share, tied to stage and routing version.

### Pitfall: retrying deterministic OOM

The same partition and algorithm will probably fail again while consuming the
recovery budget. Change partitioning, memory behavior, or workload admission.

### Pitfall: broadcast because the row count looks small

Serialized bytes, in-memory expansion, indexes, and concurrent copies determine
fit. Measure worker headroom under concurrent tasks.

## Performance, operations, and compatibility

Track shuffle records/bytes, compression ratio, block count, fetch wait/retries,
spill bytes, peak memory, partition quantiles, largest-key share, join expansion,
straggler ratio, speculation waste, and cleanup age. Roll out mitigation with
versioned intermediate contracts, shadow comparison, representative skew, and a
rollback path that preserves old routing and manifests.

## Working example

- Python/tests/data: planned shuffle simulator, Zipf-like fixture, hot-key failure, salting equivalence, join explosion, and capacity report
- Expected result: skew is observable; repairs preserve exact output and bound tails
- Scale represented: none yet; deterministic local fixture then multi-process benchmark
- Remaining risk: real serialization, disk spill, network, scheduler, and concurrent tenants

## Knowledge check

1. Explain why doubling partitions does not split one hot grouping key.
2. Diagnose equal input bytes but one much slower task.
3. Design salting and recombination for the reference count metric.
4. Prove a broadcast side fits with concurrent tasks and memory expansion.
5. Choose metrics that distinguish join explosion from host contention.

## Key takeaways

- Shuffle establishes a data contract and consumes network, disk, memory, and metadata.
- Tail partitions, not averages, set completion time.
- Skew can be in data, computation, joins, or infrastructure.
- Mitigations must preserve grain and be proven equivalent.
- Blind retries and partition-count tuning do not repair deterministic hotspots.

## Resources

- [MapReduce paper](https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/) (reviewed 2026-09)
- [Apache Spark documentation: performance tuning](https://spark.apache.org/docs/latest/tuning.html) (reviewed 2026-09)

## Related topics

- [MapReduce, DAGs, and data locality](05-mapreduce-dags-and-data-locality.md)
- [Resource scheduling, backpressure, and capacity](08-resource-scheduling-backpressure-and-capacity.md)

## Completion checklist

- [x] Shuffle, fan-out, skew, stragglers, hot partitions, diagnosis, and mitigation explained
- [x] Correctness, security, failure, quality, capacity, operations, and migration addressed
- [ ] Distribution, hot-key, equivalence, fan-out, and capacity evidence run
