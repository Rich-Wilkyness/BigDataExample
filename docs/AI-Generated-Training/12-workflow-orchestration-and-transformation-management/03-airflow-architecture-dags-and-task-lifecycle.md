# Airflow Architecture, DAGs, and Task Lifecycle

> Status: Documentation complete; executable Airflow evidence planned  
> Level: Intermediate to Senior  
> Applies to: Apache Airflow / Distributed workflow orchestration / Platform  
> Data scale: Local metadata fixture; distributed production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Airflow is a control plane for creating DAG runs, deciding when task instances are
eligible, and submitting attempts through an executor. The DAG processor parses
workflow definitions; the metadata database coordinates durable state; workers
perform task code; the API server exposes operations; and a triggerer can manage
deferred waiting. Data still belongs in a warehouse, object store, database, or
broker rather than the metadata database.

This guide maps the durable workflow contract onto Airflow. It does not prescribe
an executor, deployment platform, or cloud provider.

## Learning objectives

- Trace a DAG file from parse through run, queue, attempt, and terminal state.
- Separate metadata authority from dataset authority.
- Explain executor, worker, API server, DAG processor, scheduler, and triggerer failure.
- Design stable DAGs with bounded parsing and small inter-task metadata.
- Diagnose discrepancies between Airflow state and external data truth.

## Prerequisites

- Guides 01 and 02 in this area.
- Area 08 coordination, leases/fencing, retries, and capacity.
- A conceptual understanding of external databases and object/table publication.

## Mental model and terminology

```text
DAG bundle -> DAG processor -> serialized definition -> metadata database
                                                      ^        |
                                                      |        v
API server/UI <----------------------------------- scheduler -> executor
                                                                  |
                                         triggerer <-> deferred   v
                                                               workers
                                                                  |
                                                      external data systems
```

| Component | Owns | Does not prove |
| --- | --- | --- |
| DAG processor | Parsing and serializing definitions from DAG bundles | A task's business output is correct |
| Scheduler | Run creation and task eligibility/submission | A source dataset is complete unless checked |
| Metadata database | Orchestration definitions, instances, states, and coordination | Warehouse/object data durability |
| Executor | How eligible task work is launched | Task-side idempotency |
| Worker | One or more task attempts | Global workflow or dataset truth |
| Triggerer | Asynchronous deferred-trigger execution | External event semantics without validation |
| API server | UI/API operations and visibility | Exclusive operational authority outside RBAC |

This resembles Android WorkManager's persisted scheduling at a very high level.
The analogy stops at multi-component deployment, repeated historical intervals,
distributed worker filesystems, and external analytical commits.

## Requirements, scale assumptions, and invariants

- DAG import/parse is deterministic, bounded, and free of external data mutation.
- DAG and task IDs remain stable or receive an explicit state/history migration.
- Workers assume no shared local filesystem and receive versioned artifact references.
- XCom-like metadata remains small, non-sensitive, and bounded.
- Task success follows durable external commit and validation, never only submission.
- Metadata backups, database capacity, and component health have defined owners.
- Multiple schedulers/workers may act concurrently; external commits use idempotency/fencing.
- Production estimates: 100 DAGs, 10,000 task instances/day, 20 active workers;
  these are hypotheses and must be load-tested.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Git/release to DAG bundle | Reviewed immutable code artifact | Workflow delivery owner | Reject unsigned/unapproved version | Trusted supply chain |
| DAG processor to metadata DB | Parsed serialized definition | Airflow platform | Old definition remains active or DAG unavailable | Trusted control plane |
| Scheduler to executor | Task instance plus execution context | Airflow platform | Remain scheduled/queued or retry submission | Trusted control plane |
| Worker to data system | Scoped credentials, interval, dataset refs | Dataset owner for data commit | Private candidate then fail/commit | Privileged execution |
| Worker to metadata | State, logs, bounded XCom | Airflow for attempt state | State may lag external commit | Operational evidence only |
| API/UI to operator | Authenticated actions | Platform RBAC and audit | Deny unauthorized mutation | Human trust boundary |

## DAG definition and lifecycle

Use a top-level definition that is cheap to import. Do not query the warehouse,
list object storage, or fetch secrets merely to discover graph shape during parse.
External state changes between parses and creates scheduler load or inconsistent
topology.

```python
# Illustrative Airflow-style structure; exact imports must match the pinned version.
@dag(schedule="0 2 * * *", start_date=START, catchup=True, max_active_runs=2)
def daily_product_metrics():
    ready = confirm_input_ready()
    facts = build_event_facts(ready)
    metrics = build_product_metrics(facts)
    checks = validate_and_reconcile(metrics)
    certify(metrics, checks)
```

The DAG factory creates task definitions while parsing. It must not process the
day's events. Tasks pass references such as publication IDs; bulk data remains in
the data plane.

### Task-instance state reasoning

```text
none -> scheduled -> queued -> running -> success
  |         |          |         |
  |         |          |         +-> failed -> up_for_retry -> scheduled
  |         |          +------------> queue timeout / reschedule
  |         +-----------------------> upstream_failed / skipped
  +---------------------------------> deferred -> scheduled (trigger fires)
```

Exact product states and transitions are version-sensitive. The durable lesson is
to distinguish eligibility, submission, execution, waiting, terminal attempt
state, and external commit. Clearing state requests another attempt; it cannot
undo a warehouse commit or external API call.

### Run completion

A DAG-run summary can depend on leaf-task states and trigger rules. Therefore a
cleanup leaf that succeeds regardless of upstream failures can produce misleading
run status. Make certification depend on explicit required task and dataset
receipts, and test failure paths in the graph.

## Metadata, XCom, logs, and data ownership

Store dataset rows in a data system. Use XCom or equivalent metadata only for
small references, counts, hashes, and versions. Remote logs are diagnostic and
may arrive late; they are not publication manifests. Back up and rehearse restore
of the metadata database, but independently back up or reconstruct dataset state.

## Failure model and recovery

| Failure | Observable symptom | Containment and recovery |
| --- | --- | --- |
| DAG parse/import error | Definition absent/stale; import error | Retain prior artifact, fix/test import, redeploy |
| Scheduler heartbeat loss | No new runs/tasks scheduled | Fail over/restart after DB and lock health checks |
| Executor submission ambiguity | Scheduled/queued task not launched or duplicated | Reconcile executor and metadata; task idempotency contains duplicate |
| Worker loss | Heartbeat timeout, missing logs, running task stalls | Retry within deadline; inspect external commit first |
| Metadata DB unavailable | Most control-plane operations stop | Restore service/DB; reconcile task and external data state |
| Triggerer loss | Deferred tasks do not resume promptly | Restore triggerer; triggers must be repeatable |
| API server loss | UI/API unavailable while scheduling may continue | Restore API tier; use audited break-glass procedure if needed |
| Version mismatch | Deserialize/import/runtime failures | Stop rollout, preserve compatible artifact, roll back and reconcile |

## Security, privacy, and governance

Apply RBAC to view, trigger, clear, edit, and administer separately. Workers should
receive short-lived, task-scoped access where the platform supports it. Encrypt
metadata, logs, and remote transport. Keep secrets out of DAG source, rendered
templates, XCom, command lines, and exception text. Audit manual runs, clears,
connection changes, pool changes, and release activation.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Import contract | DAG bundle / pinned local Airflow | Import all DAGs with no network calls | Stable IDs, no errors, bounded parse | Pending |
| Graph structure | Serialized DAG / local | Assert required paths and trigger rules | Certification cannot bypass checks | Pending |
| Attempt fault | Six-event fixture / test deployment | Kill worker before/after commit | Retry converges to one publication | Pending |
| Component fault | Test deployment | Stop scheduler, triggerer, API, metadata DB in turn | Documented degradation/recovery occurs | Pending |
| Capacity | Generated DAG/task load | Measure parse, schedule, queue, DB connections | Budgets hold without starvation | Pending |

Local DAG import cannot prove distributed executor, metadata failover, network,
provider, remote logging, or external data-system behavior.

## Debugging guide

1. Start with consumer, dataset version, interval, and publication truth.
2. Find DAG run, task instance, try number, map index, worker/executor ID, and code version.
3. Separate schedule delay, queued delay, execution duration, and external query time.
4. Check scheduler/DAG-processor/triggerer heartbeats and metadata DB latency/connections.
5. Inspect executor state and external commit by idempotency key before clearing.
6. Reconcile data and orchestration state, then repair the smallest safe boundary.

## Common pitfalls

### Pitfall: heavy work during DAG parsing

Repeated database calls or object listings delay every scheduler parse. Move
runtime discovery into bounded tasks or versioned configuration artifacts.

### Pitfall: worker-local handoff

The next task may run on another machine. Publish a durable artifact and pass its
reference.

### Pitfall: clear means rollback

Clearing only changes orchestration history. Inspect and compensate external
effects before requesting a new attempt.

## Performance, capacity, and cost

Measure DAG parse duration/frequency, serialized size, runnable/queued tasks,
scheduler loop latency, metadata queries/connections, worker start latency,
trigger count, log traffic, and database retention growth. High availability adds
components but does not remove metadata-database capacity and correctness limits.

## Compatibility, migration, backfill, and delivery

Pin Airflow, providers, Python, database, executor images, and DAG artifact. Test
imports and representative tasks against the exact matrix. For upgrades: back up
metadata, review migrations and compatibility, stage, pause risky workflows,
canary, observe mixed-version limits, then roll forward or roll back only where
the metadata schema and release procedure permit.

## Working example

- Infrastructure: Planned pinned Airflow test deployment under `infra/`
- DAGs/source: Planned under `src/big_data_example/orchestration/`
- Tests: Planned import, graph, lifecycle, component-fault, and capacity suites
- Try it: Planned repository script for import and one-interval run
- Expected result: Stable graph; one certified output through retry and restart
- Evidence: Planned Airflow metadata, external manifest, logs, and metrics
- Scale represented: Documentation and estimates only
- Remaining risk: Entire Airflow runtime and deployment matrix is unverified

## Knowledge check

1. Assign authority to each Airflow component and to the external data store.
2. Predict what happens when a worker commits output and dies before reporting success.
3. Diagnose a queued task using scheduler, executor, worker, pool, and DB evidence.
4. Design a graph test that prevents cleanup from hiding failed validation.
5. Estimate metadata and connection pressure for the stated task volume.
6. Propose a provider upgrade with canary and rollback constraints.
7. Implement the planned import test without contacting production services.

## Key takeaways

- Airflow coordinates task state; external systems own data truth.
- Parse-time code defines graphs and must be deterministic and cheap.
- Executor submission, worker execution, and dataset commit are separate stages.
- A task retry requires external idempotency, not faith in scheduler state.
- Operate the metadata database and component version matrix as production dependencies.

## Resources

- [Apache Airflow: architecture overview](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html) (reviewed 2026-09)
- [Apache Airflow: core concepts](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/index.html) (reviewed 2026-09)
- [Apache Airflow: production deployment](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html) (reviewed 2026-09)

## Related topics

- [DAG and dependency design](01-dags-workflows-tasks-and-dependency-design.md)
- [Task isolation and retries](04-task-isolation-idempotency-retries-timeouts-and-sensors.md)
- [Environment and orchestrator operations](08-environments-secrets-ci-cd-rollout-and-orchestrator-operations.md)

## Completion checklist

- [x] Architecture, lifecycle, ownership, trust, metadata, and data boundaries defined
- [x] DAG sketch and state model distinguish orchestration from external commit
- [x] Component, concurrency, security, failure, and recovery behavior addressed
- [x] Capacity, compatibility, deployment, and diagnosis covered
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Pinned Airflow import, fault, integration, capacity, and restore evidence executed

