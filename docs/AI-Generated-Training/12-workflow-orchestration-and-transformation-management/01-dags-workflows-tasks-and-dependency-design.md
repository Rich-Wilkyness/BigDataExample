# DAGs, Workflows, Tasks, and Dependency Design

> Status: Documentation complete; executable graph evidence planned  
> Level: Beginner to Senior  
> Applies to: Generic orchestration / Batch / SQL transformation / Platform  
> Data scale: Local design fixture; distributed production estimate  
> Example status: Planned  
> Evidence status: Documentation and contract review only  
> Last reviewed: 2026-09

## Overview

A workflow is a repeatable coordination contract. Its directed acyclic graph
(DAG) says which units of work may run only after which durable prerequisites.
The orchestrator records and schedules work; processing engines read and write
the data. A green task state is not itself proof that a complete dataset exists.

This guide designs the graph before selecting Airflow or dbt. It excludes product
installation and streaming record-by-record processing.

## Learning objectives

- Distinguish orchestration, execution, transformation, and publication.
- Choose task boundaries around retryable, observable commits.
- Model control dependencies separately from data dependencies.
- Detect false success, excessive coupling, and unsafe side effects.
- Evaluate coarse and fine-grained graphs using recovery and capacity evidence.

## Prerequisites

- Area 07 incremental pipeline and atomic publication concepts.
- Area 08 retry, idempotency, and distributed task-attempt concepts.
- Area 11 authoritative dataset and snapshot concepts.

## Mental model and terminology

```text
workflow definition --instantiate(interval, code/config)--> workflow run
workflow run         --expands-----------------------------> task instances
task instance        --may retry---------------------------> task attempts
task attempt         --reads committed inputs--------------> candidate output
candidate output     --validate + commit-------------------> dataset version
```

| Term | Meaning in this guide |
| --- | --- |
| DAG | Finite directed graph with no dependency cycle |
| Workflow run | One graph execution for an interval and versioned parameters |
| Task instance | Logical unit of work within one run; attempts are retries of it |
| Control dependency | Ordering required by policy or resource coordination |
| Data dependency | Requirement for a named dataset version or frontier |
| Commit boundary | Point at which a candidate becomes authoritative to consumers |
| Idempotency scope | Identity within which repetition converges to one result |

A DAG resembles a Gradle task graph, but Gradle normally produces local build
artifacts in one invocation. Workflow nodes can run hours apart on different
workers and publish durable shared state. Process completion and data commit are
therefore separate facts.

## Requirements, scale assumptions, and invariants

- One run covers `[interval_start, interval_end)` in UTC and records the input frontier.
- Tasks exchange durable references and small metadata, not multi-gigabyte payloads.
- Every published dataset version identifies interval, code, schema, and inputs.
- A retry or duplicate run either reuses the same valid result or replaces it atomically.
- Consumers see the old complete version or the new complete version, never task staging.
- A downstream task starts from a committed dataset fact, not a worker-local file.
- Cancellation prevents publication or fences a late attempt from winning.
- Estimated daily input is 3 million events/3 GiB; no runtime measurement exists.
- Non-goal: using the orchestrator as a general data-processing engine.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Scheduler | Versioned graph and interval | Platform team; coordination metadata only | Delay run, never invent data readiness | Trusted control plane |
| Landing manifest | Immutable accepted objects and frontier | Ingestion owner | Missing/incomplete remains not ready | Validated but not curated |
| Transform task | Manifest plus model version | Data pipeline owner | Write private candidate; fail closed | Mixed trust |
| Quality gate | Candidate and declared checks | Dataset owner | Block certification and retain diagnostics | Trusted decision logic |
| Publication pointer | Validated generation ID | Dataset owner | Conditional atomic update | Authoritative derived data |
| Consumer | Certified version contract | Consumer owns use and caching | Continue prior version or degrade explicitly | Governed output |

## Designing task boundaries

Prefer a task boundary when work has a distinct owner, resource profile, retry
policy, observable outcome, or durable commit. Keep operations together when
splitting would create an uncommitted intermediate or require large payloads to
pass through orchestration metadata.

```text
Avoid: extract_row -> normalize_row -> enrich_row -> aggregate_row (millions of tasks)
Prefer: acquire_interval -> publish_fact_generation -> build_metric -> certify
```

| Requirement | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Recover expensive stages independently | Durable stage boundary | Retry skips valid prior commits | Intermediate lifecycle costs exceed recovery benefit |
| Pass large datasets | Object/table reference | Bounded control plane | Payload is genuinely small configuration |
| Enforce dataset readiness | Manifest/snapshot dependency | Represents data truth | Producer offers no durable readiness marker |
| Share reusable transform logic | Library or SQL model | Testable outside scheduler | Execution needs distinct isolation/policy |
| Coordinate independent consumers | Fan-out after one commit | Avoids duplicate production | Consumer-specific grains require separate models |

### SQL model

The workflow supplies typed interval parameters; the warehouse performs the set
operation. SQL dialect is illustrative ANSI-style SQL. Event time is non-null
UTC, and the half-open predicate prevents boundary duplication.

```sql
SELECT tenant_id, product_id, CAST(event_time AS DATE) AS metric_date,
       COUNT(*) AS view_count
FROM curated_event_fact
WHERE event_time >= :interval_start
  AND event_time <  :interval_end
  AND event_name = 'product_view'
GROUP BY tenant_id, product_id, CAST(event_time AS DATE);
```

The task writes to a private candidate keyed by publication ID, validates grain,
then conditionally publishes. `ORDER BY` is unnecessary because relation order
is not part of the contract.

### Python boundary model

```python
@dataclass(frozen=True)
class DatasetRef:
    dataset: str
    version: str
    interval_start: datetime
    interval_end: datetime
    checksum: str

def build_metric(source: DatasetRef, publication_id: str) -> DatasetRef:
    """Build a private candidate; do not return until its manifest is durable."""
    ...
```

The return value is small metadata. The process never returns an in-memory table
through the orchestrator, and the caller does not infer correctness from return
code alone.

## Lifecycle, consistency, identity, and time

Definition identity, run identity, task identity, attempt identity, and dataset
identity are distinct. A task retry keeps logical task identity but gets a new
attempt. A repaired backfill can keep the interval while changing code and
publication IDs. The publication ledger must reject two winners for the same
declared replacement policy.

Task dependencies give partial order, not wall-clock order. Parallel branches
may finish in either order. The consumer consistency boundary is the certified
publication pointer, not the completion timestamps of individual tasks.

## Failure model and recovery

| Failure | Detection and containment | Recovery owner and convergence evidence |
| --- | --- | --- |
| Worker dies before candidate commit | Missing candidate manifest; no publish | Executor retries; one valid manifest results |
| Worker dies after commit response is lost | Lookup by idempotency key | Task adopts committed result; no duplicate version |
| Upstream task green but dataset absent | Readiness/manifest check fails | Producer repairs; downstream never starts from absence |
| Quality task skipped by branch | Certification requires explicit gate receipt | Workflow owner fixes graph and re-evaluates interval |
| Concurrent runs target same interval | Conditional publication/fencing rejects loser | Dataset owner selects winner and reconciles |
| Cyclic business dependency | Graph validation or design review | Break cycle with authoritative snapshot or iteration outside DAG |
| Oversized graph overloads scheduler | Parse/schedule latency and task count alert | Coarsen boundaries or bound mapping |

A cleanup task must not be the only leaf whose success makes the whole workflow
appear successful. Certification queries required receipts directly.

## Security, privacy, and governance

Run workers with dataset-specific identities and least privilege. Do not put raw
records, secrets, or access tokens into task metadata, parameters, logs, or graph
names. Record lineage with dataset identifiers and versions. Separate permission
to run a backfill from permission to publish or delete certified data.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Command or procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Graph contract | Tiny declarative graph / local | Parse and assert acyclic required paths | Every certify node depends on data and quality commits | Pending |
| Task idempotency | Six-event fixture / local double | Crash before/after commit and retry | One certified publication | Pending |
| Reconciliation | Candidate metric / SQL engine | Compare source buckets to output totals | Declared exclusions explain difference | Pending |
| Real scheduler | Airflow test deployment | Run, clear, retry, overlap | State and data converge | Pending |
| Capacity | Generated intervals / test deployment | Increase tasks and concurrent runs | Scheduling objective and bounds hold | Pending |

Fixtures cannot prove metadata-database concurrency, worker isolation, executor
loss, warehouse transaction behavior, or distributed scheduling.

## Debugging guide

1. Identify the affected dataset version, interval, consumer, and freshness breach.
2. Trace publication ID backward through quality receipt, model candidate, input manifest, run ID, task instance, and attempt.
3. Compare orchestration state with storage/catalog truth; do not clear tasks first.
4. Inspect task duration, queue time, retries, exit reason, worker logs, query ID, and lineage.
5. Contain by pausing certification or retaining the prior version.
6. Replay with the same interval and a new repair publication ID, then reconcile before closing.

## Common pitfalls

### Pitfall: encode data truth as task completion

A task can finish after writing nothing or before an asynchronous query commits.
Require a durable manifest, snapshot, or quality receipt.

### Pitfall: pass datasets through workflow metadata

Large payloads overload serialization, databases, and UIs. Publish data through a
data system and pass only a versioned reference.

### Pitfall: one giant task or one task per record

The former makes retries expensive and opaque; the latter overwhelms control
planes. Align tasks with bounded, independently recoverable commits.

## Performance, capacity, and cost

Budget scheduler parsing time, queued task count, task-start latency, metadata
rows/connections, worker slots, warehouse concurrency, and retry amplification.
If 35 daily intervals are replayed with five tasks each, the base expansion is
175 task instances before retries or mapping. Measure control-plane capacity and
downstream query load rather than assuming more parallelism is faster.

## Compatibility, migration, backfill, and delivery

Use expand/migrate/contract: deploy readers tolerant of old/new dataset versions,
deploy producing tasks disabled, validate one interval, enable bounded runs,
certify, then remove the old path after retention and rollback windows. Keep task
IDs stable when historical state or operational links depend on them; otherwise
provide an explicit mapping and migration procedure.

## Working example

- Python source: Planned under `src/big_data_example/orchestration/`
- SQL: Planned under `sql/orchestration/`
- Tests: Planned under `tests/orchestration/`
- Data: Reuse the bounded mobile-event fixture when implemented
- Try it: Planned local graph-contract and publication-state commands
- Expected result: Repeat and overlap produce one certified interval version
- Evidence: Planned unit, SQL reconciliation, fault, scheduler, and capacity results
- Scale represented: Documentation plus production estimate only
- Remaining risk: All executable and real-system behavior is unverified

## Knowledge check

1. Explain why `extract >> transform` is weaker than a dependency on a named committed input version.
2. Draw task boundaries for validation, fact publication, metrics, quality, and certification; defend each commit.
3. Diagnose a green run whose consumer table is missing one partition.
4. Design a crash-after-commit experiment and its convergence assertion.
5. Estimate task instances for 35 intervals, two mapped tenants, five base tasks, and two retry attempts.
6. Propose a compatible task split without losing historical traceability.
7. Add a quality gate to the planned graph and specify how its failure blocks publication.

## Key takeaways

- A DAG coordinates durable work; it does not make the work correct.
- Data readiness must be represented by a committed dataset fact.
- Task boundaries should match ownership, retry, observability, and commit boundaries.
- Task success and dataset certification are different states.
- Identity and fencing make retries and overlaps convergent.

## Resources

- [Apache Airflow: DAGs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html) (reviewed 2026-09)
- [Apache Airflow: architecture overview](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html) (reviewed 2026-09)
- [W3C PROV overview](https://www.w3.org/TR/prov-overview/) (reviewed 2026-09)

## Related topics

- [Schedules and data intervals](02-schedules-data-intervals-catchup-and-time-zones.md)
- [Task isolation and retries](04-task-isolation-idempotency-retries-timeouts-and-sensors.md)
- [Metadata and data-aware scheduling](07-metadata-lineage-artifacts-and-data-aware-scheduling.md)

## Completion checklist

- [x] Durable mental model, graph contract, grain, ownership, and trust boundaries defined
- [x] SQL and Python boundary sketches distinguish control metadata from data
- [x] Identity, time, concurrency, partial failure, security, and recovery addressed
- [x] Capacity, migration, delivery, and operational diagnosis covered
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Graph model, fault fixture, scheduler integration, and capacity evidence executed

