# Volume, Velocity, Variety, and When Data Becomes Big

> Status: Documentation complete  
> Level: Beginner  
> Applies to: Generic data engineering / Batch / Streaming / Storage / Platform  
> Data scale: Single machine through production estimate  
> Example status: Complete estimation exercise  
> Evidence status: Capacity model  
> Last reviewed: 2026-09

## Overview

Data is “big” when its workload no longer fits the required time, correctness,
reliability, or cost envelope with the simplest acceptable design. Volume,
velocity, and variety are useful prompts, not a product checklist. Variability,
retention, query shape, concurrency, failure recovery, governance, and team
capacity can dominate raw byte count.

This guide turns requirements into estimates and identifies the constraint that
would justify a more complex design. It does not define a universal threshold or
recommend a distributed engine.

## Learning objectives

After completing this guide, you should be able to:

- Estimate events, bytes, files, storage growth, rates, bursts, and replay time.
- Distinguish payload volume from physical storage and processing work.
- Explain how variety becomes schema and semantic complexity.
- Identify the first likely bottleneck using measurements and sensitivity analysis.
- Decide when vertical scaling, partitioning, or distribution is justified.

## Prerequisites

Read the first two guides in this area. A calculator is sufficient; no runtime is
required.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Volume | Amount of data stored or processed over a stated interval |
| Velocity | Arrival or required processing rate, including burst shape |
| Variety | Structural, semantic, source, encoding, and evolution differences |
| Cardinality | Count of distinct values, often important for grouping, indexing, and telemetry |
| Throughput | Work completed per unit time |
| Headroom | Capacity reserved above expected demand for bursts, recovery, and growth |
| Sensitivity analysis | Recalculating a model as uncertain assumptions vary |

## Requirements, scale assumptions, and invariants

Baseline estimates for `screen_viewed`:

| Input | Assumption |
| --- | ---: |
| Daily active installations | 100,000 |
| Events per active installation/day | 30 average; 300 high case |
| Serialized raw event | 1 KiB average; 4 KiB high case |
| Peak-to-average arrival ratio | 10x |
| Raw retention | 30 days |
| Annual traffic growth | 100% estimate |
| Daily batch window | 60 minutes |

Invariants are stable identity, complete accounting of accepted inputs, bounded
memory per worker, an explicit publication cutoff, and enough retained input to
repair within policy. The model is invalidated by measured distributions outside
its ranges, a new low-latency consumer, different retention, or changed privacy
constraints.

## Mental model

Start with a workload envelope:

```text
producers x events/producer x bytes/event x retention
                    |
                    +-- rate and burst shape
                    +-- transformations and shuffle amplification
                    +-- copies, indexes, metadata, and replication
                    +-- consumers, query scans, and concurrency
                    +-- replay, backfill, failure, and growth headroom
```

Android APK size is a limited analogy: bytes matter, but startup time also
depends on device, I/O pattern, initialization, and user path. Likewise, dataset
bytes alone do not predict whether a data workload meets its objective. The
analogy stops when distributed skew and cross-machine coordination dominate.

## Estimation walkthrough

### Baseline volume

```text
events/day = 100,000 x 30 = 3,000,000
raw payload/day = 3,000,000 x 1 KiB ~= 2.86 GiB
30-day payload = 85.8 GiB
average rate = 3,000,000 / 86,400 ~= 35 events/s
estimated peak = 35 x 10 ~= 350 events/s
batch minimum average = 3,000,000 / 3,600 ~= 833 events/s
```

The batch rate excludes parsing, validation, reads, writes, grouping, retries,
and headroom. Physical storage includes file/container overhead, replicas or
erasure coding, staging, quarantine, derived tables, indexes, backups, and
metadata. Compression can reduce bytes but consumes CPU and must be measured on
representative data.

### High case and sensitivity

At 300 events and 4 KiB each, the same population generates 30 million events
and about 114 GiB/day—40 times the baseline byte estimate. At 10x peak, arrival
is about 3,500 events/s. One changed assumption can dominate several small
optimizations, so retain formulas and ranges rather than only a final number.

### Variety

Variety includes multiple schema versions, optional fields, different clocks,
encodings, producer platforms, units, identifiers, and interpretations. Ten
small incompatible sources can be harder to operate than one much larger,
uniform source. Normalize only when the target semantics are owned and raw
information remains available for repair.

## Data flow, ownership, and trust boundaries

| Boundary | Capacity concern | Owner | Failure behavior | Evidence needed |
| --- | --- | --- | --- | --- |
| Device buffer/collector | Offline backlog, payload cap, burst rate | Mobile and ingestion | Bound queue; explicit drop/retry policy | Payload/rate distributions |
| Collector/raw storage | Writes, files, partitions, retention | Ingestion/storage | Backpressure before uncontrolled exhaustion | Load plus fault test |
| Raw/batch transform | Scan bytes, CPU, memory, skew, window | Pipeline/platform | Bounded tasks; retry from committed input | Profile and task timeline |
| Curated/consumers | Query scans and concurrency | Dataset/serving owner | Quotas, caches, or workload isolation | Query plans and concurrency test |

Capacity telemetry may reveal sensitive usage patterns; restrict access and
avoid identifiers as metric labels.

## When to scale up, out, or differently

| Observed constraint | First response | Add distribution when | Warning |
| --- | --- | --- | --- |
| Batch misses window | Profile, reduce scanned data, improve layout, scale one host | Parallel work is partitionable and one host remains insufficient | Coordination and shuffle add cost |
| Memory exhaustion | Stream/chunk, project fields, bound grouping | Required state genuinely exceeds practical host memory | More workers do not fix unbounded per-key state |
| Ingestion overload | Batch/compress, apply backpressure, scale service | Sustained/peak demand exceeds one failure domain | A queue moves pressure; it does not remove it |
| Query latency | Prune, index, precompute, separate workloads | Concurrency/data require parallel scans | Precomputation trades freshness and storage |
| Availability need | Backup/restore, redundancy, tested failover | Required failure domains exceed one machine/site | Replication adds consistency decisions |

Choose the simplest design with measured headroom that satisfies recovery as
well as steady-state demand.

## Consistency, ordering, identity, and time

Rates must specify event time or arrival time and averaging interval. A daily
average hides minute bursts. Late events shift work into later runs; duplicates
increase input work even if output deduplication preserves counts. Per-key skew
can leave one partition overloaded while cluster averages look healthy.

## Failure model and recovery

| Failure | Symptom | Containment/recovery | Capacity implication |
| --- | --- | --- | --- |
| Producer retry storm | Sudden duplicate-heavy rate | Rate limit, stable IDs, backpressure | Size for safe degradation, not unlimited intake |
| Worker outage | Backlog and freshness loss | Redistribute/restart committed work | Reserve recovery headroom |
| Bad partition key | One hot task or shard | Redesign/salt only with correct merge | Average utilization is misleading |
| Historical backfill | Competes with daily run | Isolate quota and bounded dates | Model combined workloads |
| Small-file growth | Slow listings/planning | Compact with atomic publication | Object count is a capacity dimension |
| Retention cleanup stalls | Storage rises unexpectedly | Repair lifecycle job; enforce safe quota | Monitor age and bytes, not just writes |

Recovery capacity matters: a system at 95% steady-state utilization may never
catch up after an outage.

## Security, privacy, and governance

Minimization can be the best scale optimization: do not collect unused fields,
reduce precision where valid, and expire data on policy. Capacity pressure does
not authorize skipping validation, encryption, access controls, or deletion.
Synthetic or de-identified fixtures are preferred for benchmarks, but their
distributions must resemble the production properties being tested.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Baseline arithmetic | Stated assumptions | Recalculate events, bytes, rates, retention | Units and formulas are consistent | Passed; documented above |
| Sensitivity case | Stated high estimates | Increase event count and size | Identifies 40x byte range | Passed as estimate |
| Local/engine benchmark | Representative generated fixture | Measure parse, transform, publish, memory, and file count | Meets window with headroom | Pending |
| Production validation | Authorized telemetry | Compare percentile distributions and growth | Replace estimates with observations | Pending |

Paper arithmetic catches order-of-magnitude errors. It does not predict engine
overhead, network behavior, skew, compression, contention, or monetary price.

## Debugging guide

For missed objectives, graph input/output events and bytes per interval, backlog,
oldest event age, CPU, memory, disk, network, partition sizes, task duration,
spill, retries, file counts, and consumer concurrency. Compare percentiles and
the largest keys, not only averages. Reproduce with the same record widths,
cardinality, skew, and query shape. After mitigation, drain backlog and reconcile
counts before declaring recovery.

## Common pitfalls

### Pitfall: defining big data by a product

Using Spark does not make a workload big, and a single-machine process is not
automatically small. State the constraint and evidence that selected the design.

### Pitfall: multiplying averages only

Average size times average rate hides correlated peaks, tail payloads, hot keys,
and retry bursts. Record distributions and sensitivity ranges.

### Pitfall: sizing only steady state

Backfills, compaction, reprocessing, failover, and backlog drain compete with
normal work. Reserve capacity or isolate workloads.

## Performance, capacity, cost, and operations

Define budgets for event acceptance latency, daily freshness, storage growth,
replay duration, query concurrency, and cost per day or per million events.
Monitor both demand and service: rates, bytes, cardinality, skew, queue age,
utilization, saturation, errors, latency percentiles, and spend attribution.
Alert on consumer impact and exhaustion forecasts rather than raw utilization
alone.

## Compatibility, migration, backfill, and delivery

Schema expansion can increase width; identity changes can increase cardinality;
retention changes multiply storage. Run capacity checks before rollout. Shadow or
canary representative traffic, isolate historical backfills, compare totals and
resource use, and keep a rollback path. A migration is incomplete until old data
and peak traffic remain readable within objectives.

## Working example

The reproducible formulas and sensitivity case are the working conceptual
example. Executable benchmarks remain planned for the processing and storage
areas.

## Knowledge check

1. Recalculate baseline daily bytes if payload p95 is 2.5 KiB and explain why
   multiplying p95 values does not produce a p95 daily total.
2. Predict the effect of 100x one key's frequency on a hash-partitioned group-by.
3. Diagnose a batch whose CPU is low while one task runs far longer than others.
4. Design capacity evidence for a seven-day outage followed by backlog recovery.
5. Identify the first measurement you need before choosing a distributed engine.

## Key takeaways

- Data becomes big relative to an explicit workload and objective.
- Bytes, records, rates, bursts, cardinality, skew, files, retention, and replay all matter.
- Variety is as much semantic and evolutionary as structural.
- Size recovery and concurrent workloads, not only the happy-path average.
- Distribution is justified by measured constraints and adds new failure modes.

## Resources

- [Google SRE: Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Apache Parquet documentation](https://parquet.apache.org/docs/)
- [NIST Guide for Conducting Risk Assessments](https://csrc.nist.gov/pubs/sp/800/30/r1/final)

## Related topics

- [Correctness, freshness, latency, throughput, and cost](06-correctness-freshness-latency-throughput-and-cost.md)
- [Data architecture patterns and trust boundaries](07-data-architecture-patterns-and-trust-boundaries.md)
- [First end-to-end data pipeline](08-first-end-to-end-data-pipeline.md)

## Completion checklist

- [x] Workload dimensions and tool-independent definition explained
- [x] Assumptions, units, formulas, high case, and invalidation evidence stated
- [x] Capacity boundaries, overload, recovery, security, and cost addressed
- [x] Scale estimates distinguished from benchmarks and production observations
- [ ] Representative local, distributed, and production measurements recorded

