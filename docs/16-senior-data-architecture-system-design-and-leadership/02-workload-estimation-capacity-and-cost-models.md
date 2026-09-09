# Workload Estimation, Capacity, and Cost Models

> Status: Documentation complete; measured workload and price evidence planned  
> Level: Senior  
> Applies to: Batch / Streaming / Storage / Warehouses / Platforms  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and arithmetic review only  
> Last reviewed: 2026-09

## Overview

A capacity model translates consumer requirements into demand, service rate,
resources, headroom, recovery time, and cost. Its purpose is not false precision;
it identifies feasibility, dominant variables, breakpoints, and measurements that
could change a decision. Senior engineers expose ranges and uncertainty rather
than laundering guesses into exact-looking infrastructure counts.

This guide models the shared mobile-event platform from source through replay and
consumer queries. It does not size a named vendor service or claim benchmarked performance.

## Learning objectives

- Estimate rows, bytes, files, events, partitions, concurrency, retention, and growth with units.
- Separate average, peak, skewed, failure, replay, and migration workloads.
- Relate throughput, utilization, queues, headroom, and recovery drain time.
- Construct a cost model and sensitivity analysis without hiding uncertainty.
- Define measurements and gates that replace assumptions over time.

## Prerequisites

- [Requirements and context](01-requirements-constraints-system-context-and-non-goals.md).
- [Area 15 performance/capacity](../15-reliability-observability-performance-cost-and-operations/06-performance-profiling-query-plans-and-capacity-modeling.md) and [cost modeling](../15-reliability-observability-performance-cost-and-operations/07-cost-modeling-finops-quotas-and-workload-isolation.md).

## Mental model and terminology

```text
demand envelope -> bottleneck service rate -> utilization/queue -> objective risk
       |                    |                       |
       v                    v                       v
 growth/skew          failure capacity       headroom + admission
       +-------------------- cost per useful outcome ----------------+
```

| Term | Meaning in this guide |
| --- | --- |
| Workload envelope | Named steady, peak, skew, recovery, and growth cases |
| Service demand | Resource time or bytes consumed per useful unit |
| Bottleneck | Resource whose available service rate first constrains throughput |
| Headroom | Capacity reserved for bursts, failures, recovery, and uncertainty |
| Sensitivity | Change in outcome when one uncertain input changes |
| Breakpoint | Input value at which a requirement fails or architecture changes |
| Unit economics | Cost per useful outcome such as accepted million events or certified tenant-day |

This resembles estimating Android request volume, storage, and backend concurrency.
The analogy stops because data systems reread and rewrite history: a 35-day replay,
compaction, dual-run migration, and consumer scans can exceed new-event traffic.

## Requirements, assumptions, and invariants

Starting low/base/high inputs:

| Input | Low | Base | High | Confidence |
| --- | ---: | ---: | ---: | --- |
| Accepted events/day | 1M | 3M | 12M | Low until telemetry review |
| Encoded bytes/event | 0.5 KiB | 1 KiB | 4 KiB | Low; compression excluded |
| Peak/average rate | 3x | 10x | 30x | Low |
| Hot-tenant share | 10% | 35% | 60% | Low |
| Hot replay | 7 days | 35 days | 90 days | Requirement hypothesis |
| Annual growth | 20% | 60% | 150% | Product forecast hypothesis |

Invariants:

- Every number carries units, source, observation date, range/confidence, and owner.
- Logical records, delivered events, compressed bytes, scanned bytes, and billed units stay distinct.
- Model steady, burst, skew, one failure domain lost, retry amplification, replay, maintenance, and dual-run migration.
- Capacity protects current critical work while recovery drains within its objective.
- Cost retains shared/unallocated amounts and includes compute, storage, requests, transfer, telemetry, support, and people-operability where decision-relevant.
- A measured benchmark replaces only the assumptions it actually represents.

## Data flow, ownership, and trust boundaries

| Stage | Demand unit | Primary limit | Owner/evidence |
| --- | --- | --- | --- |
| Ingestion | Delivered/accepted events per second | Validation, broker/network, dedupe state | Ingestion owner/receipts |
| Stream compute | Events, keys, state bytes, windows | Hot partitions, checkpoint, sink commit | Processing owner/task metrics |
| Governed history | Written/stored/read bytes and objects | Throughput, metadata, retention | Storage owner/manifests |
| Daily batch/replay | Scanned/shuffled/output bytes | Slots, skew, deadline | Dataset owner/run receipts |
| BI/API serving | Queries, concurrency, scanned rows/bytes | Queue, cache, warehouse slots | Consumer/platform owner |
| Control plane | Datasets, jobs, policies, lineage edges | Metadata rate/availability | Platform owner |

Producer receipts and provider bills are untrusted observations until reconciled
to platform acceptance and the authoritative invoice. Workload samples must not
cross tenant, privacy, or production-access boundaries merely to improve realism.

## Estimation model

Base arithmetic:

```text
average_events_per_second = events_per_day / 86,400
peak_events_per_second = average_events_per_second * peak_factor
raw_bytes_per_day = accepted_events * encoded_bytes_per_event
retained_bytes = daily_bytes * retention_days * replication_or_copy_factor
partition_peak = total_peak * max(hot_key_share, 1 / partition_count)
```

At 3M events/day, average input is about 34.7 events/second. A 10x peak is
about 347 events/second; the round 500 events/second hypothesis adds uncertainty
headroom. At 1 KiB/event, uncompressed logical input is about 2.86 GiB/day. Do
not use decimal GB and binary GiB interchangeably.

Recovery must include concurrent arrival:

```text
net_drain_rate = recovery_service_rate - concurrent_arrival_rate
drain_time = backlog / net_drain_rate         # only if net_drain_rate > 0
required_service_rate = arrival_rate + backlog / recovery_deadline
```

If six hours create about 750,000 missing events and effective recovery handles
200 events/second while 35/second continue to arrive, first-order drain time is
about 76 minutes. Shared bottlenecks and startup can make the real result worse.

### Python model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Scenario:
    events_per_day: int
    bytes_per_event: int
    peak_factor: float
    retention_days: int

    def average_eps(self) -> float:
        return self.events_per_day / 86_400

    def peak_eps(self) -> float:
        return self.average_eps() * self.peak_factor

    def retained_bytes(self, copy_factor: float = 1.0) -> float:
        return self.events_per_day * self.bytes_per_event * self.retention_days * copy_factor
```

The model intentionally excludes protocol overhead, indexes, metadata, compression,
small files, temporary shuffle, checkpoints, backups, and billing rounding. Add
each explicitly rather than hiding it inside a magic multiplier.

### SQL measurement sketch

```sql
-- Grain: one tenant/hour. Dialect-specific timestamp functions require adaptation.
SELECT tenant_id,
       DATE_TRUNC('hour', accepted_at) AS accepted_hour,
       COUNT(*) AS accepted_events,
       SUM(encoded_bytes) AS encoded_bytes,
       COUNT(DISTINCT event_id) AS logical_events
FROM accepted_event_receipt
WHERE accepted_at >= :start_utc AND accepted_at < :end_utc
GROUP BY tenant_id, DATE_TRUNC('hour', accepted_at);
```

Measure delivered and accepted counts separately; `COUNT(DISTINCT)` can be
expensive or approximate in some engines. Preserve exact reconciliation controls.

## Sensitivity and breakpoint analysis

Vary one uncertain driver across low/base/high while retaining coupled constraints.
Rank variables by their effect on deadline and cost. Typical dominant variables
are bytes/event, peak factor, hot-key share, state retention, scan amplification,
replay days, query concurrency, transfer, and copies.

| Question | Breakpoint evidence |
| --- | --- |
| When does one partition miss five minutes? | Per-key peak and measured per-partition service distribution |
| When can replay no longer catch up? | Recovery rate minus current arrival reaches zero |
| When does daily scan miss deadline? | Representative scan/shuffle throughput under concurrency |
| When does cost exceed budget? | Unit-cost model with billed prices and growth range |
| When is a second architecture justified? | Existing design fails a requirement after safe tuning/admission |

## Lifecycle, consistency, identity, and time

Model versions move from hypothesis to calibrated, decision baseline, observed,
and retired. Bind each to workload interval, data/contract version, environment,
software/config, and prices. Event time drives windows; acceptance time drives
platform backlog; billing time drives invoices. Never silently mix them.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Average hides burst | Per-minute/tenant percentiles | Refit peak/skew envelope |
| Compression assumed before measurement | Stored/logical bytes disagree | Separate factors by format/data distribution |
| Replay shares saturated resource | Net drain non-positive | Reserve/isolate capacity or relax objective |
| Retry storm amplifies traffic | Delivered/accepted ratio rises | Backoff, dedupe, admission, and bounded retry |
| Unit mismatch | Dimensional check fails | Normalize units and rerun model/tests |
| Price/API changes | Estimate no longer reconciles invoice | Version price input and refresh decision |
| Growth exceeds high case | Forecast alert | Revisit capacity wave before breakpoint |

## Security, privacy, and governance

Aggregate workload telemetry and restrict tenant-identifying volumes, query text,
and cost allocation. Models must include encryption/key calls, policy checks,
retention/deletion rewrites, audit, backup, and regional constraints rather than
treating governance as free or optional.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Arithmetic/unit | Boundary and unit tests | Known scenarios and invalid ranges behave correctly | Pending |
| Workload profile | 28+ representative days segmented by tenant/time | Low/base/high calibrated | Pending |
| Micro/prototype | Pinned component and payload distribution | Service demand and bottleneck bounded | Pending |
| Load/skew | Rate, size, partition, concurrency sweep | Saturation and tail behavior measured | Pending |
| Recovery | Current traffic plus staged backlog/failure | Drain objective met without starving current work | Pending |
| Cost | Usage export/invoice reconciliation | Allocated plus shared equals authoritative bill | Pending |

## Debugging guide

Inspect units, grain, interval, percentile, source date, delivered versus accepted
records, logical versus physical bytes, tenant/key distribution, copies, cache,
concurrency, bottleneck saturation, billing rounding, and omitted recovery work.
Recalculate a small case manually before trusting the model.

## Common pitfalls

### Pitfall: precision without confidence

`17.43 workers` is not accuracy. Preserve ranges, assumptions, discrete limits,
and safety factors, then round only at the provisioning boundary.

### Pitfall: multiply average by one peak factor

Traffic, payload size, key skew, queries, and retries may peak together or not.
Model correlated scenarios and validate them from traces/receipts.

### Pitfall: omit the transition

Dual writes, backfills, validation, and retained rollback copies can make migration
the peak workload. Size the change, not only steady state.

## Performance, capacity, and cost

Track throughput and p50/p95/p99 latency, CPU, memory/state, disk/network, files,
requests, shuffle/spill, checkpoints, queue age, retries, copy amplification,
headroom, and unit cost. Optimize the constrained resource while preserving
correctness, recovery, security, operability, and total cost.

## Observability and operations

Publish demand versus model bands, saturation distance, forecast date to breakpoint,
backlog/drain projection, cost actual versus forecast, and model error. Alert on
actionable thresholds with an owner and lead time, not on every forecast fluctuation.

## Compatibility, migration, and delivery

Recalculate for mixed versions, dual paths, historical conversion, temporary
copies, validation queries, rollback retention, and decommissioning. Deliver
instrumentation early so later sizing decisions use observed evidence.

## Engineering tradeoffs

| Choice | Benefit | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Fixed headroom | Predictable burst/recovery | Idle spend | Elastic startup meets objective reliably |
| Elastic capacity | Matches variable demand | Delay, quotas, price, complexity | Baseline dominates or cold start fails |
| Precompute | Stable read latency | Write/storage/freshness cost | Definitions change or reads are rare |
| Approximate result | Lower latency/resource | Error contract and bias | Decision needs exact reconciliation |

## Working example

- Python: Planned typed scenario, drain, growth, and sensitivity model
- SQL: Planned hourly/tenant workload extraction and cost reconciliation
- Tests: Planned unit, dimension, range, no-drain, and allocation cases
- Load: Planned burst, skew, concurrency, failure-loss, and replay experiments
- Expected result: Requirements map to a range, breakpoint, bottleneck, and cost with explicit uncertainty
- Remaining risk: Real distribution, nonlinear queues, service quotas, migration amplification, prices, and production contention

## Knowledge check

1. Estimate average and 20x-peak rate for 12M events/day.
2. Predict recovery when service rate is below concurrent arrival.
3. Diagnose a model that matches row counts but underestimates scanned bytes 10x.
4. Design low/base/high cases for hot-tenant skew and replay.
5. Identify the three inputs most likely to change architecture selection.
6. Add dual-run migration demand to the capacity envelope.
7. Implement one unit-safe sensitivity calculation and test invalid inputs.

## Key takeaways

- Capacity is a range of workload and failure cases, not an average event rate.
- Units, provenance, uncertainty, and sensitivity matter more than decorative precision.
- Recovery and migration can dominate steady-state demand.
- A bottleneck and its saturation curve determine useful parallelism.
- Estimates become trustworthy through calibration and invoice/runtime reconciliation.

## Resources

- [Google SRE Workbook: non-abstract large system design](https://sre.google/workbook/non-abstract-design/) (reviewed 2026-09)
- [Google SRE Workbook: managing load](https://sre.google/workbook/managing-load/) (reviewed 2026-09)
- [AWS Billing: cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html) (reviewed 2026-09; provider-specific)

## Related topics

- [Requirements and system context](01-requirements-constraints-system-context-and-non-goals.md)
- [Architecture alternatives](03-architecture-alternatives-technology-selection-and-tradeoffs.md)
- [Area 15 performance and capacity](../15-reliability-observability-performance-cost-and-operations/06-performance-profiling-query-plans-and-capacity-modeling.md)

## Completion checklist

- [x] Workload, units, growth, skew, recovery, migration, headroom, sensitivity, breakpoints, and cost covered
- [x] Ownership, time, security, failure, observability, and evidence limitations explicit
- [x] SQL/Python models and working example accurately marked Planned
- [ ] Arithmetic, telemetry, load, skew, recovery, cost, distributed, and production evidence executed
