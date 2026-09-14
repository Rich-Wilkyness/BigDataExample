# Backfills, Dynamic Workflows, and Concurrency Controls

> Status: Documentation complete; executable backfill evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic orchestration / Airflow / Batch / Platform capacity  
> Data scale: Local expansion model; distributed production estimate  
> Example status: Planned  
> Evidence status: Documentation and contract review only  
> Last reviewed: 2026-09

## Overview

A backfill intentionally recomputes historical intervals. Dynamic workflows
expand work from runtime cardinality. Both multiply load, metadata, retries, and
side effects, so correctness requires a preflight manifest and bounded admission.
Concurrency controls protect shared systems; they do not fix skew, non-idempotent
tasks, or incorrect interval selection.

## Learning objectives

- Plan backfills as versioned migrations with dry-run and reconciliation.
- Distinguish parse-time graph generation from bounded runtime mapping.
- Calculate expansion and retry amplification before admission.
- Apply run, task, pool, queue, priority, and downstream quotas coherently.
- Protect current production work and stop safely under overload.

## Prerequisites

- Interval and catchup semantics from guide 02.
- Attempt safety from guide 04.
- Area 08 scheduling/backpressure and Area 11 workload isolation.

## Mental model and terminology

```text
request -> enumerate immutable work manifest -> preflight -> admit bounded waves
       -> build private candidates -> reconcile -> certify/cut over -> clean up
```

| Term | Meaning in this guide |
| --- | --- |
| Backfill | Controlled historical recomputation for stated intervals/version |
| Dynamic mapping | Runtime creation of task instances from bounded input metadata |
| Pool | Named capacity budget shared by tasks using a constrained resource |
| Active run limit | Bound on concurrent runs of one workflow |
| Overlap policy | Rule for two runs that may target the same data/output |
| Work manifest | Immutable list of intervals/partitions, inputs, versions, and estimates |
| Current-work reserve | Capacity withheld so routine freshness is protected |

Dynamic mapping resembles launching coroutines from a collection, but a scheduler
must persist each mapped instance and may retain its history for months. Millions
of tiny mappings can overwhelm metadata long before worker CPU is saturated.

## Requirements, scale assumptions, and invariants

- Every backfill has owner, reason, bounded range, code/schema version, dry run,
  cost estimate, priority, cancellation rule, and success/reconciliation criteria.
- The work manifest is immutable after approval; changes create a new request/version.
- Current daily work retains at least 50% of the starting warehouse quota.
- A mapped collection has a configured maximum and stable element identity/order.
- Concurrent attempts cannot publish two winners for the same dataset interval/version.
- Partial completion is restartable from committed receipts, not from task timestamps.
- Retention and privacy checks precede historical reads and candidate cleanup.
- Starting case: 35 daily intervals, up to 100 tenant partitions, five base tasks,
  and two attempts; all capacity figures remain unmeasured.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Operator request | Range, reason, release, priority | Incident/change owner | Reject missing or excessive request | Human input |
| Enumerator | Catalog/manifest snapshots | Backfill controller | Produce immutable bounded manifest | Trusted control logic |
| Scheduler/pools | Work manifest and quotas | Platform | Queue or stop admission | Control plane |
| Workers/data systems | One item, fence, resource class | Pipeline/dataset owners | Private candidates only | Privileged execution |
| Certification | Receipts and reconciliation | Dataset owner | Partial range stays uncertified | Authoritative decision |
| Consumers | Replacement publication notice | Product/analytics owners | Retain prior version until cutover | Governed output |

## Preflight and expansion arithmetic

```python
def estimate_instances(intervals: int, mapped_items: int,
                       fixed_tasks: int, mapped_tasks: int,
                       max_attempts: int) -> int:
    logical = intervals * (fixed_tasks + mapped_items * mapped_tasks)
    return logical * max_attempts
```

For 35 intervals, 100 tenants, three fixed tasks, two mapped tasks, and two
attempts, the worst planned count is `35 * (3 + 100 * 2) * 2 = 14,210` task
attempts. That is not a throughput promise; it is an admission warning.

Preflight also estimates bytes scanned/written, query concurrency, object
requests, API quota, metadata rows, staging storage, and downstream refresh load.

## Dynamic graph design

Use parse-time generation only from small, version-controlled configuration.
Use runtime mapping when the items are discovered from a committed manifest and
each item is independently retryable. Prefer engine-native partition processing
when mapping would create tiny tasks or require a global shuffle.

```text
Avoid: list every raw object during DAG import, then create one task per object
Prefer: read one committed manifest at runtime, validate count/size, map bounded
        partitions or submit one engine job that owns internal parallelism
```

Stable mapped identity should be a tenant/partition key, not collection position,
because retries or reordered discovery must refer to the same logical effect.

## Concurrency and admission controls

| Control | Protects | Does not protect |
| --- | --- | --- |
| Max active runs | One workflow from excessive interval overlap | Shared warehouse across other workflows |
| Task concurrency | One task family/key | Other expensive tasks |
| Pool slots | Named shared resource budget | Resources omitted or misweighted |
| Executor/queue limit | Worker launch capacity | Downstream database/API capacity |
| Warehouse workload group | Engine queries and memory | Orchestrator metadata DB |
| Priority | Ordering under contention | Correctness or guaranteed immediate start |

Set all layers from the narrowest real bottleneck and reserve repair/current work.
A task that consumes four times the warehouse capacity should consume weighted
pool capacity where supported rather than counting as one cheap slot.

## Backfill lifecycle and cutover

1. Freeze semantic/code/schema versions and enumerate the input frontier.
2. Dry-run interval/item counts, permissions, retention, capacity, and conflicts.
3. Run one representative interval into an isolated namespace.
4. Reconcile identities, totals, checksums, distributions, and consumer queries.
5. Admit bounded waves, newest-first only if that matches recovery goals.
6. Stop admission on freshness/cost/error thresholds; allow or cancel in-flight work safely.
7. Certify atomically by interval or whole range according to the declared contract.
8. Notify consumers, observe, retain rollback versions, and clean candidates later.

## Failure model and recovery

| Failure | Detection/containment | Recovery and convergence |
| --- | --- | --- |
| Expansion exceeds cap | Preflight/runtime count guard | Split manifest or use engine-native work |
| Current run misses SLO | Freshness/queue alerts | Pause backfill admission; current reserve drains queue |
| Hot tenant straggles | Per-key duration/bytes skew | Isolate/split with equivalent recombination test |
| Partial range succeeds | Receipt ledger shows gaps | Resume only missing/invalid work items |
| Wrong code/version selected | Canary reconciliation fails | Stop, fence candidates, issue corrected request |
| Operator cancels | Admission stops; tasks receive cancellation | Fence late commits, reconcile, retain resumable receipts |
| Metadata DB overloaded | Scheduler/DB latency and connection alerts | Halt expansion, reduce mapping, archive per policy |
| Input expired mid-run | Manifest validation/read failure | Restore governed archive or declare bounded gap |

## Security, privacy, and governance

Historical access can violate current retention or purpose limits. Preflight
authorization per dataset, tenant, time range, and destination. Use isolated
schemas/buckets and distinct publish privilege. Avoid embedding tenant IDs or
sensitive values in task IDs and metrics. Audit requester, approver, manifest,
release, overrides, cancellation, publication, and cleanup.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Expansion model | Synthetic manifests / local | Boundary/property tests against cap | Exact stable item set and estimate | Pending |
| Resume | Faulted 35-interval fixture / local | Stop after arbitrary receipts then resume | Only missing/invalid items rerun | Pending |
| Overlap | Two requests for same intervals | Race candidates/publication | Fence selects one declared winner | Pending |
| Isolation | Test orchestrator/warehouse | Run current plus backfill load | Current freshness budget holds | Pending |
| Cutover | Consumer query suite | Compare old/new and atomic switch | No mixed certified range | Pending |

## Debugging guide

1. Locate request ID, immutable manifest, release, interval/item, task attempt, and publication receipt.
2. Compare planned versus actual task counts, bytes, retries, queue delay, and cost.
3. Identify the saturated layer: scheduler DB, executor, worker, warehouse, API, storage, or consumer.
4. Stop new admission first; fence/cancel only when attempt semantics are known.
5. Reconcile completed items and current-work health before resuming smaller waves.
6. Close only after certified coverage and orphan cleanup are proven.

## Common pitfalls

### Pitfall: unlimited parallelism shortens a backfill

Contention, throttling, retry storms, and metadata load can make it slower while
harming current data. Sweep concurrency under a fixed current-work reserve.

### Pitfall: derive dynamic tasks from mutable external state

Retries may see a different list. Snapshot an immutable manifest and map stable
identities.

### Pitfall: successful tasks imply complete historical range

Reconcile requested items and certified receipts; missing instances may never
have been created.

## Performance, capacity, and cost

Record tasks/attempts, scheduler rows, parse/schedule latency, pool utilization,
queue age, bytes scanned/written, query slots, spill, object requests, staging
growth, and currency cost per interval. Increase one concurrency layer at a time
and stop when throughput plateaus or current-work latency approaches its budget.

## Compatibility, migration, backfill, and delivery

Backfill code is a historical data migration. Preserve the exact artifact and
adapter/provider versions for reproducibility. If old schema cannot be read by
new code, add a normalization boundary rather than silently skipping history.
Canary, dual-calculate, reconcile, atomic cut over, retain old publications, and
document rollback limitations when downstream state is irreversible.

## Working example

- Python source: Planned work-manifest and admission model under `src/big_data_example/orchestration/`
- Tests: Planned expansion, resume, overlap, and capacity tests
- Data: Planned 35-interval/100-tenant synthetic manifest
- Infrastructure: Planned Airflow and warehouse integration
- Try it: Planned dry-run and bounded-wave commands
- Expected result: Exact resumable coverage without current-publication SLO breach
- Evidence: Planned receipts, reconciliation, queue/resource metrics, and cost report
- Scale represented: Arithmetic estimate only
- Remaining risk: Scheduler, warehouse, consumer, and cancellation behavior unverified

## Knowledge check

1. Distinguish catchup, repair rerun, and versioned backfill.
2. Calculate attempts for the stated 35-interval mapping scenario.
3. Diagnose why throughput falls after pool size doubles.
4. Design stable mapped identity and a maximum-expansion guard.
5. Allocate capacity while reserving half for current work.
6. Plan an atomic cutover and rollback for a new metric definition.
7. Implement the estimator and a property that it rejects unbounded requests.

## Key takeaways

- A backfill is a governed data migration, not merely old runs started again.
- Immutable work manifests make expansion reproducible and resumable.
- Concurrency is an end-to-end capacity budget across control and data planes.
- Stable identity, receipts, and fencing make overlap safe.
- Current production freshness receives explicit reserved capacity.

## Resources

- [Apache Airflow: backfill](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html) (reviewed 2026-09)
- [Apache Airflow: dynamic task mapping](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html) (reviewed 2026-09)
- [Apache Airflow: pools](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html) (reviewed 2026-09)

## Related topics

- [Schedules and catchup](02-schedules-data-intervals-catchup-and-time-zones.md)
- [Task isolation and retries](04-task-isolation-idempotency-retries-timeouts-and-sensors.md)
- [Area 08 resource scheduling](../08-distributed-systems-foundations/08-resource-scheduling-backpressure-and-capacity.md)

## Completion checklist

- [x] Backfill, manifest, mapping, overlap, admission, pool, and priority contracts defined
- [x] Expansion arithmetic and decision boundaries included
- [x] Failure, security, cancellation, recovery, and current-work protection addressed
- [x] Capacity, cost, migration, cutover, and operational diagnosis covered
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Expansion model, Airflow/warehouse integration, load, fault, and cutover evidence executed
