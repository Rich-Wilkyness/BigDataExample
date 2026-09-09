# Resource Scheduling, Backpressure, and Capacity

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic data engineering / Distributed computation / Platform  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A distributed system is stable only when admitted work can complete within its
resource and deadline budgets. Schedulers map tasks to finite CPU, memory, disk,
network, and service quotas. Backpressure carries downstream saturation toward
producers so queues remain bounded and the system sheds, delays, or reduces work
deliberately rather than failing chaotically.

Adding workers helps only when the bottleneck scales too. Storage, shuffle, metadata,
hot keys, dependency quotas, and coordination can cap useful parallelism.

## Learning objectives

- Translate a workload into CPU, memory, disk, network, slot, and time budgets.
- Explain admission, queueing, fairness, priority, preemption, and backpressure.
- Distinguish throughput, concurrency, parallelism, utilization, and saturation.
- Diagnose overload using queues and tail latency before failure counts.
- Produce a capacity and recovery-headroom plan with explicit assumptions.

## Prerequisites

- [Shuffles, skew, stragglers, and hot partitions](06-shuffles-skew-stragglers-and-hot-partitions.md)
- [Retries, idempotency, speculation, and fault recovery](07-retries-idempotency-speculation-and-fault-recovery.md)

## Mental model and terminology

Coroutine dispatchers limit concurrent work but do not automatically bound every
upstream queue or remote dependency. A cluster scheduler similarly assigns compute;
end-to-end stability still needs bounded inputs, memory, retries, and sink capacity.

```text
arrivals -> admission queue -> runnable tasks -> CPU/memory
                         |             |
                         |             +-> disk/network/dependency queues
                         |                         |
                         <----- backpressure ------+
             delay / reduce / reject / spill within policy
```

| Term | Meaning in this guide |
| --- | --- |
| Throughput | Completed useful work per unit time |
| Concurrency | Work admitted/in progress at once |
| Parallelism | Work executing simultaneously |
| Saturation | A resource has insufficient service capacity for offered demand |
| Backpressure | Signal/control that bounds upstream production or admission |
| Headroom | Reserved capacity for bursts, failures, retries, and recovery |
| Fairness | Rule dividing constrained resources among tenants/workloads |

## Requirements, scale assumptions, and invariants

The reference job estimates 3 million 1 KiB compressed events/day (about 3 GiB
before format overhead), 16 input and aggregate partitions, a 45-minute normal
budget, and a 15-minute recovery reserve. One tenant may contribute 35% of load.
All figures are estimates pending executable measurement.

- Queues and retries are bounded by count, bytes, age, and deadline.
- Memory admission includes task working set, runtime overhead, broadcast/cache,
  shuffle buffers, and concurrent attempts.
- Recovery capacity is not consumed by steady-state target utilization.
- Priority and preemption preserve already committed work and tenant policy.
- Overload behavior is explicit: delay, reduce, reject, spill, or degrade.
- Capacity claims use tail distributions and representative skew/failures.

## Capacity model

Start with useful lower-bound rates, then add measured overhead and headroom:

```text
required event throughput = events / processing-window seconds
required byte throughput  = input bytes / processing-window seconds
effective capacity        = min(CPU, memory, disk, network, metadata, dependency limits)
recovery demand           = normal backlog + replay/retry work within recovery window
```

Three million events over 45 minutes is about 1,112 events/second on average; this
does not include shuffle records, skew, retries, expansion, or output. A credible
plan measures per-stage service rates, p95/p99 partition size, and the slowest
shared boundary. Little's Law (`in-flight = arrival rate x average time in system`)
can sanity-check stable averages, but bursty tails and priority classes still need
explicit modeling.

## Scheduling and overload decisions

| Requirement/condition | Control | Tradeoff |
| --- | --- | --- |
| Protect interactive/critical workload | Reservations, quotas, priority | Idle reserved capacity or policy complexity |
| Prevent memory oversubscription | Resource-aware admission | Lower apparent utilization, fewer OOMs |
| Bound dependency load | Token bucket/concurrency limit | Queue delay or rejection |
| Absorb short burst | Bounded durable queue | Freshness delay and storage cost |
| Stop runaway retries | Global retry/deadline budget | Earlier explicit failure |
| Reclaim lower-priority capacity | Cooperative preemption/checkpoint | Wasted work and recovery overhead |
| Isolate dominant tenant | Per-tenant quota/pool | Fragmentation and fairness policy |

Backpressure must reach the component capable of reducing creation or admission.
An unbounded queue merely moves the out-of-memory point and increases data age.
Batch sources can pause partition admission; streaming sources may pause consumption,
reduce fetch size, spill durably, or reject at an explicit boundary.

## Failure model and recovery

| Failure | Early signal | Containment and recovery | Consumer behavior |
| --- | --- | --- | --- |
| Queue grows continuously | Arrival exceeds completion; age rises | Throttle/admit less, add relevant capacity, drain | Freshness warning before deadline miss |
| Worker OOM | Memory pressure/spill/GC tails | Reduce concurrency/working set; retry changed plan | Prior generation remains |
| Disk/shuffle saturation | Queue, throughput, latency, free-space trend | Reduce shuffle/admission; expand measured bottleneck | No unsafe cleanup/publish |
| Retry storm | Attempts and dependency calls amplify | Circuit/budget, jitter, stop deterministic retries | Explicit degraded/unavailable state |
| Metadata bottleneck | Proposal/queue latency rises | Batch safe metadata, reduce clients/payloads | Data-plane work may wait safely |
| Tenant starvation | Queue age/share by class | Enforce reservation/fair scheduling | SLO breach visible by tenant/class |
| Node/zone loss | Available capacity drops | Invoke reserved headroom, prioritize recovery | Declared recovery objective |

## Security, privacy, and governance

Admission and priority are authorization decisions: tenants must not raise their
class, allocate unbounded resources, or infer other tenants through detailed
metrics. Validate resource requests, enforce quotas at trustworthy boundaries,
protect scheduler APIs, cap labels, and audit overrides/preemption. Spill and queue
storage inherit payload classification and lifecycle.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Deterministic scheduler model | Submit priority/tenant/resource fixtures | Policy and bounds hold without starvation | Pending |
| Backpressure test | Raise arrival above sink capacity | Queue remains bounded; declared shedding occurs | Pending |
| Resource benchmark | Vary records, bytes, partitions, concurrency | Bottleneck and service curve measured | Pending |
| Skew/retry load test | Add hot tenant and transient failures | Budgets prevent collapse | Pending |
| Failure-headroom test | Remove worker capacity during backlog | Recovery objective met or honest limit recorded | Pending |

## Common pitfalls

### Pitfall: maximize utilization

Running every resource near 100% removes burst and recovery capacity and inflates
tail latency. Optimize for SLO, useful throughput, and cost with explicit headroom.

### Pitfall: count records but ignore bytes and expansion

Records vary in size and may expand during deserialization, joins, or aggregation.
Measure bytes and peak working set by partition.

### Pitfall: autoscale on CPU alone

The true limit may be disk, shuffle network, metadata, dependency quota, or one hot
key. Scale the measured bottleneck and confirm useful completion improves.

### Pitfall: backpressure after an unbounded buffer

The buffer consumes memory/disk and increases age before the signal acts. Bound
every queue from the first admission point.

## Observability, operations, and compatibility

Track arrival/completion rates, queue count/bytes/age, admitted/running tasks,
resource requests versus usage, CPU, memory/GC, spill, disk/network throughput,
dependency quotas, retry amplification, preemption, utilization, saturation,
freshness, deadline budget, and cost per successful dataset generation. Use bounded
tenant/workload classes, not raw IDs, as labels.

Scheduler-policy and resource-profile changes alter completion order and failure
behavior. Shadow or canary representative workloads, compare fairness and tails,
drain/checkpoint incompatible tasks, preserve prior configuration, and rehearse
rollback under load rather than only at idle.

## Working example

- Python/tests/data: planned discrete scheduler/backpressure model, workload fixtures, resource benchmark, and node-loss scenario
- Expected result: queues remain bounded, priority/fairness policy holds, and recovery headroom is measured
- Scale represented: none yet; deterministic model followed by multi-process capacity test
- Remaining risk: real scheduler, noisy neighbors, autoscaling delay, cloud quotas, and monetary cost

## Knowledge check

1. Estimate the lower-bound event and byte rate for the reference job.
2. Explain concurrency versus parallelism and utilization versus saturation.
3. Diagnose rising queue age with low CPU but saturated shuffle disks.
4. Design overload behavior for a noncritical backfill competing with daily publication.
5. Propose a node-loss test that validates the 15-minute recovery reserve.
6. Identify the first metrics needed before recommending more workers.

## Key takeaways

- Stable systems bound admission, queues, retries, and memory from end to end.
- Effective capacity is set by the slowest constrained boundary.
- High utilization can destroy tail latency and recovery headroom.
- Backpressure must reach a component that can reduce offered demand.
- Capacity claims require representative skew, faults, tails, and cost evidence.

## Resources

- [The Tail at Scale](https://research.google/pubs/the-tail-at-scale/) (reviewed 2026-09)
- [Kubernetes documentation: resource management for pods and containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) (reviewed 2026-09)

## Related topics

- [Shuffles, skew, stragglers, and hot partitions](06-shuffles-skew-stragglers-and-hot-partitions.md)
- [Planned Reliability, Observability, Performance, Cost, and Operations area](../COVERAGE.md#15-reliability-observability-performance-cost-and-operations)

## Completion checklist

- [x] Scheduling, queues, fairness, backpressure, resources, overload, capacity, and headroom explained
- [x] Failure, security, observability, cost, compatibility, and operational behavior addressed
- [ ] Scheduler, backpressure, benchmark, skew/retry, and headroom evidence run
