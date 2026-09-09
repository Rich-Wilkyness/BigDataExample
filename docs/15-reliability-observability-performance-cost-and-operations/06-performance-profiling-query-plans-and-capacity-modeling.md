# Performance Profiling, Query Plans, and Capacity Modeling

> Status: Documentation complete; executable performance evidence planned  
> Level: Intermediate to Senior  
> Applies to: Python / SQL / Batch / Streaming / Warehouses / Platforms  
> Data scale: Single-machine fixture and production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Performance is observed behavior for a specified workload and environment.
Profiling attributes resource use, query plans show an engine’s chosen execution
strategy, and capacity models connect demand to resources, limits, headroom, and
growth. Optimization without a workload or budget can make the wrong path faster.

This guide develops workload models, latency/throughput distributions, bottleneck
analysis, plans, skew, benchmarks, forecasts, regression gates, and scale limits.
It does not promise that a local benchmark predicts distributed or production behavior.

## Learning objectives

- Define representative workload, service-level budget, and measurement method.
- Relate throughput, concurrency, latency, utilization, queues, and saturation.
- Read estimated versus actual query plans and challenge cardinality estimates.
- Diagnose CPU, memory, disk, network, shuffle, skew, and coordination bottlenecks.
- Forecast capacity with headroom, recovery demand, sensitivity, and uncertainty.

## Prerequisites

- SQL plans from [Area 03](../03-sql-and-analytical-querying/README.md), partitions/distribution from [Area 08](../08-distributed-systems-foundations/README.md), and engine behavior from [Area 09](../09-apache-spark-and-distributed-computation/README.md).
- [Reliability requirements](01-data-system-reliability-requirements-and-failure-domains.md) and [telemetry](02-logs-metrics-traces-lineage-and-correlation.md).
- A pinned real engine and representative fixture are planned, not yet selected.

## Mental model and terminology

```text
workload: rows + bytes + files + keys + skew + queries + concurrency + growth
                                      |
                                      v
execution path: scan -> filter -> join/shuffle -> aggregate/sort -> write/commit
                                      |
resources: CPU / memory / disk / network / slots / metadata / external limits
                                      |
bottleneck -> queue -> saturation -> latency/error/cost -> measured optimization
```

| Term | Meaning in this guide |
| --- | --- |
| Throughput | Completed useful units per time, with the unit stated |
| Latency | Time for one operation/interval, reported as a distribution |
| Concurrency | Simultaneous admitted or active work |
| Utilization | Fraction of resource capacity busy over a window |
| Saturation | Demand exceeds promptly serviceable capacity, creating queue/rejection |
| Selectivity | Fraction of input rows retained by a predicate |
| Cardinality estimate | Planner’s predicted rows/distinct values at an operator |
| Skew | Uneven key/partition/work distribution that controls tail completion |
| Headroom | Reserved capacity for bursts, failures, recovery, and forecast uncertainty |

Android profiling provides the right discipline—reproduce, trace/profile, change
one cause, compare. The analogy stops when a declarative engine can rewrite the
plan and distributed tail latency is controlled by shuffle, skew, remote storage,
metadata, and the slowest tasks rather than one process.

## Requirements, scale assumptions, and invariants

Record data grain, rows/bytes/files, compression, schema width, key distribution,
selectivity, partitions, query mix, arrival pattern, concurrency, cache state,
software/config/hardware, latency/throughput budget, correctness checks, and cost.
Use the shared 3 million events/day (~3 GiB), 100 tenants with a hypothetical 35%
hot tenant, 100 million retained rows, and 35-day replay. None is measured.

Invariants:

- Every result binds workload/data version, code/query, engine/config, environment, warmup/cache state, repetitions, statistics, and raw measurements.
- Correctness and publication semantics remain fixed while comparing performance.
- Report distributions and sample counts; averages do not replace p95/p99/tail analysis.
- Measure end-to-end consumer/workflow time and operator/resource detail without double-counting parallel CPU as wall time.
- Capacity includes current work, retry/recovery/backfill demand, failure loss, and explicit headroom.
- A query plan is evidence about one planner/environment/data state, not a permanent guarantee.
- Optimization is accepted only when repeated evidence improves the stated budget without unacceptable reliability, cost, or maintainability regression.

## Data flow, ownership, and trust boundaries

| Boundary | Owner/contract | Performance concern |
| --- | --- | --- |
| Workload fixture/generator | Dataset/benchmark owner | Representativeness, privacy, key distribution, determinism |
| Query/job definition | Dataset owner | Semantics, versions, parameter classes |
| Planner/runtime | Engine/platform owner | Statistics, plan, stages, adaptive behavior, resource limits |
| Storage/network | Platform/provider owner | Throughput, latency, locality, throttling, cache |
| Scheduler/concurrency | Platform owner | Queue, admission, fairness, cold start |
| Result store | Evidence owner | Raw samples, environment metadata, comparison method |

## Workload and capacity model

Separate workload classes: current scheduled publication, interactive query,
streaming steady state/burst, repair/backfill, compaction/maintenance, and recovery.
Each has different deadlines and may compete for the same bottleneck.

```text
arrival_rate = input_units / interval
service_rate = measured_completed_units / active_time
backlog_change = arrival_rate - effective_service_rate
drain_time = backlog / (recovery_service_rate - concurrent_arrival_rate)
required_capacity ~= peak_demand / target_utilization * failure_and_growth_factor
```

These are first-order models. Queuing is nonlinear near saturation; external
quotas, parallelism limits, skew, startup, commit, and coordination can dominate.

### SQL model

```sql
-- PostgreSQL example: inspect estimates without executing writes first.
EXPLAIN (FORMAT JSON)
SELECT tenant_id, product_id, COUNT(*) AS view_count
FROM governed_event
WHERE event_time_utc >= :start_utc
  AND event_time_utc < :end_utc
GROUP BY tenant_id, product_id;

-- In an isolated environment, EXPLAIN ANALYZE executes the statement.
-- Use a read-only transaction or disposable target for mutating statements.
```

Inspect scans, filters, estimated versus actual rows, join algorithms/order,
sort/aggregate, loops, memory/spill, buffers/I/O, parallel workers, and total time.
Syntax and available fields are engine/version-specific. Stale statistics or
correlated columns can cause row-estimate errors that cascade through the plan.

### Python model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class DrainEstimate:
    backlog_rows: int
    processing_rows_per_second: float
    arrival_rows_per_second: float

    def seconds(self) -> float:
        net = self.processing_rows_per_second - self.arrival_rows_per_second
        if net <= 0:
            raise ValueError("backlog cannot drain at current effective capacity")
        return self.backlog_rows / net
```

The model assumes stable rates and a shared resource accounting; a benchmark must
test burst, skew, retries, and tail behavior before it supports an operational claim.

## Measurement and optimization loop

1. State consumer/workflow budget, correctness invariant, and workload envelope.
2. Capture reproducible baseline with environment and raw distributions.
3. Locate the constrained resource and queuing point using end-to-end and operator evidence.
4. Form one falsifiable hypothesis: reduce scanned bytes, fix selectivity estimate, repartition skew, bound concurrency, compact files, or remove serialization.
5. Change one dimension; rerun correctness and repeated performance evidence.
6. Test adverse workload classes, cold/warm state, failure/retry, and cost.
7. Add a regression gate with variance-aware threshold and periodically reassess representativeness.

| Symptom | Inspect first | Tempting but unsafe shortcut |
| --- | --- | --- |
| High elapsed, low CPU | Queue, remote I/O, locks, throttles | Add workers blindly |
| Few slow tail tasks | Partition sizes, hot keys, spill, host | Optimize median task |
| Join explosion | Grain/cardinality and actual rows | Increase memory only |
| Many tiny files/tasks | Metadata/listing/startup/commit | Maximize partition count |
| Fast query, missed deadline | Scheduler queue and upstream readiness | Tune SQL alone |
| More concurrency lowers throughput | Shared bottleneck and contention | Raise concurrency again |

## Lifecycle, consistency, identity, and time

Benchmark artifacts progress from proposed fixture to validated workload, baseline,
candidate comparison, accepted result, regression gate, stale/retired. Keep query
digest, plan, dataset snapshot, statistics timestamp, engine/config, machine/cluster,
run IDs, and measurement clock. Do not compare runs across semantic changes or
mixed units. Late/corrected data can change both size and key distribution.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Fixture lacks production skew | Distribution comparison | Regenerate/reweight; invalidate unsupported result |
| Cache makes candidate look fast | Cold/warm separated runs | Clear/identify cache safely and rerun |
| `EXPLAIN ANALYZE` mutates data | Review/read-only/disposable target | Restore target and use safe plan procedure |
| More workers hit storage throttle | Network/storage saturation | Reduce/admit concurrency or increase actual bottleneck |
| Benchmark noise trips gate | Raw samples/variance/environment check | Fix isolation; use robust comparison and rerun |
| Tuning changes result | Differential/reconciliation tests | Reject optimization; restore correct plan |
| Capacity model omits recovery | Game day backlog cannot drain | Reserve/add capacity or revise recovery requirement |

## Security, privacy, and governance

Use synthetic or minimized production-derived workload statistics where possible.
Protect plans, SQL, profiles, samples, resource names, and query parameters; they
can reveal schema, tenant activity, and sensitive predicates. Load tests need
admission, target allowlists, cost limits, cleanup, and approval. Never run an
unbounded benchmark against production merely to improve representativeness.

## Data quality, testing, and evidence

| Evidence | Environment/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Arithmetic/unit | Fixed rate/backlog models | Units and no-drain cases correct | Pending |
| Query correctness | Deterministic fixture/differential | Baseline and optimized results equivalent | Pending |
| Plan | Pinned real SQL engine | Estimates/actuals/operators captured | Pending |
| Profile/benchmark | Repeated representative workload | Bottleneck and distributions reproducible | Pending |
| Skew/load | Hot tenant, small files, concurrency sweep | Tail/saturation point and safe limit measured | Pending |
| Capacity/recovery | Forecast plus staged outage backlog | Headroom/drain meet named objective | Pending |

## Debugging guide

Start with affected workload and deadline, queue delay versus run time, arrival/
completion rates, concurrency, resource saturation, input rows/bytes/files,
partition distribution, plan and estimate/actual differences, spill/shuffle,
external throttles, code/config/dependency changes, and cache/statistics state.
Reproduce with the same parameter class and dataset version. Verify correctness
before and after each change and identify what evidence would falsify the diagnosis.

## Common pitfalls

### Pitfall: optimize an average

Tail latency or slowest partitions determine deadlines. Preserve distributions
and segment by workload/failure domain without creating unbounded telemetry.

### Pitfall: scale out before finding the bottleneck

Extra workers can amplify shuffle, storage throttling, metadata, and cost. Measure
the constrained resource and perform a concurrency sweep.

### Pitfall: treat estimated cost as elapsed time

Planner cost is an internal relative estimate, not milliseconds or currency.
Compare estimates with actual rows/time/I/O in a safe representative environment.

## Performance, capacity, and cost

This entire guide is governed by a performance budget and cost boundary. Track
rows/bytes/files scanned/written, CPU-seconds, memory peak, spill, disk/network,
shuffle, slots, task count, queue, latency percentiles, throughput, concurrency,
and monetary estimate. Report cost per successful publication or useful unit,
not only total cost or faster elapsed time.

## Observability and operations

Monitor demand, queue depth/oldest age, completion throughput, p50/p95/p99,
failures/retries, saturation for every hard resource, partition/skew distribution,
spill/shuffle, external quotas, capacity forecast, and regression history. Profiles
are diagnostic and sampled; objective metrics remain low-cardinality and stable.

## Compatibility, migration, and delivery

Plans can change after engine, statistics, schema, index, partition, configuration,
or data-distribution changes. Pin comparison environments, capture plan digests/
artifacts, canary workloads, gate regressions, and preserve rollback where data
layout permits. Some optimizations—repartitioning or rewritten formats—need dual
read, backfill, validation, cutover, and forward repair.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Scale up | Single-node/local operation is bottleneck | Vertical limit and failure domain | Distribution benefit exceeds overhead |
| Scale out | Work partitions independently enough | Shuffle/coordination/skew cost | Shared storage/serial stage dominates |
| Precompute | Repeated reads have strict latency | Freshness/storage/change complexity | Queries are rare or definitions volatile |
| More headroom | Burst/recovery harm is high | Idle cost | Admission/degradation safely absorbs demand |

## Working example

- Python: Planned rate/drain/capacity models under `src/big_data_example/operations/`
- SQL: Planned query and plan capture under `sql/operations/`
- Tests: Planned units, no-drain, correctness differential, skew, and threshold cases
- Try it: Planned pinned-engine cold/warm plan, benchmark, profile, and concurrency sweep
- Expected result: Bottleneck and saturation are evidenced; optimized result remains correct
- Scale represented: Planned local engine plus production estimate; no measurement yet
- Remaining risk: Fixture representativeness, distributed tail, external throttles, regression variance, recovery load, and cost

## Knowledge check

1. Define a representative workload and performance budget for daily metrics.
2. Predict drain behavior when processing rate equals arrival rate.
3. Diagnose a query whose estimated join rows differ greatly from actual rows.
4. Design a cold/warm, skewed concurrency benchmark with correctness checks.
5. Forecast capacity including one-worker loss and six-hour recovery backlog.
6. Plan a repartitioning rollout with data validation and rollback limits.
7. Add one variance-aware performance regression gate.

## Key takeaways

- Performance claims bind workload, environment, method, distributions, and correctness.
- Query plans are engine decisions driven by estimates, not permanent source-code facts.
- Bottlenecks and queues determine whether added parallelism helps.
- Capacity includes failure, recovery, growth, and uncertainty headroom.
- Optimization is accepted through comparative evidence and total cost/value.

## Resources

- [PostgreSQL current documentation: using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html) (reviewed 2026-09; engine/version-specific)
- [Apache Spark performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html) (reviewed 2026-09; version-specific and not yet executed here)
- [Google SRE Workbook: managing load](https://sre.google/workbook/managing-load/) (reviewed 2026-09)
- [Google SRE Workbook: non-abstract large system design](https://sre.google/workbook/non-abstract-design/) (reviewed 2026-09)

## Related topics

- [Cost modeling, quotas, and workload isolation](07-cost-modeling-finops-quotas-and-workload-isolation.md)
- [Area 09 Spark performance](../09-apache-spark-and-distributed-computation/README.md)
- [Area 03 analytical SQL](../03-sql-and-analytical-querying/README.md)

## Completion checklist

- [x] Workloads, budgets, plans, profiles, bottlenecks, skew, benchmarks, capacity, failure, security, cost, and migration covered
- [x] SQL/Python models and local/distributed evidence limits explicit
- [x] Working example accurately marked Planned
- [ ] Arithmetic, engine-plan, profile, load, skew, concurrency, recovery-capacity, cost, and production evidence executed
