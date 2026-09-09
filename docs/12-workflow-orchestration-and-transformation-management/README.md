# 12 Workflow Orchestration and Transformation Management

> Area status: Documentation complete; executable orchestration and transformation evidence planned  
> Level: Beginner to Senior data engineering  
> Applies to: Workflow orchestration / Airflow / SQL transformation / dbt-style projects / Platform operations  
> Reference scenario: Scheduled mobile-event pipeline from validated landing data to certified daily product metrics  
> Evidence boundary: Documentation and contract review; no Airflow, dbt, warehouse, or distributed worker execution yet  
> Last reviewed: 2026-09

## Purpose

This area explains how independently correct data operations become a reliable,
repeatable workflow. Orchestration coordinates *when* bounded work may start,
tracks attempts, limits concurrency, and exposes recovery state. Transformation
management makes SQL models, dependencies, tests, documentation, and deployment
artifacts reviewable as one project. Neither system makes a non-idempotent job,
an ambiguous data interval, or a partial publication correct by itself.

An Airflow DAG is superficially like a Gradle task graph: both describe ordered
work and permit independent nodes to run concurrently. The analogy stops because
a data workflow is instantiated repeatedly for historical intervals, its tasks
may run on different machines, and its outputs remain consumer-visible long after
the process exits. Clearing a task instance is therefore closer to replaying an
externally visible distributed operation than rebuilding a local APK.

## Prerequisites

- Requirements, authority, trust boundaries, and SLOs from [Area 01](../01-big-data-and-data-engineering-foundations/README.md).
- SQL semantics and safe parameterization from [Area 03](../03-sql-and-analytical-querying/README.md).
- Grain, facts, dimensions, and semantic ownership from [Area 05](../05-data-modeling-and-business-semantics/README.md).
- Incremental publication, reruns, backfills, and repair from [Area 07](../07-batch-processing-and-etl-elt/README.md).
- Distributed failure, retries, idempotency, and capacity from [Area 08](../08-distributed-systems-foundations/README.md).
- Spark job and deployment boundaries from [Area 09](../09-apache-spark-and-distributed-computation/README.md).
- Event-time frontiers and replay from [Area 10](../10-messaging-streaming-and-change-data-capture/README.md).
- Governed tables, snapshots, catalogs, and serving consumers from [Area 11](../11-warehouses-lakes-lakehouses-and-serving-systems/README.md).
- No Airflow, dbt, warehouse, or cloud account is required for this documentation pass.

## Learning path

1. [DAGs, workflows, tasks, and dependency design](01-dags-workflows-tasks-and-dependency-design.md) separates coordination from processing and chooses durable task boundaries.
2. [Schedules, data intervals, catchup, and time zones](02-schedules-data-intervals-catchup-and-time-zones.md) makes the interval contract explicit before choosing a calendar.
3. [Airflow architecture, DAGs, and task lifecycle](03-airflow-architecture-dags-and-task-lifecycle.md) maps that contract onto scheduler, processor, metadata, executor, and worker boundaries.
4. [Task isolation, idempotency, retries, timeouts, and sensors](04-task-isolation-idempotency-retries-timeouts-and-sensors.md) makes attempts safe under failure and cancellation.
5. [Backfills, dynamic workflows, and concurrency controls](05-backfills-dynamic-workflows-and-concurrency-controls.md) reprocesses bounded history without harming current production work.
6. [SQL transformation projects, models, tests, and documentation](06-sql-transformation-projects-models-tests-and-documentation.md) manages analytical transformations as a versioned dependency graph.
7. [Metadata, lineage, artifacts, and data-aware scheduling](07-metadata-lineage-artifacts-and-data-aware-scheduling.md) coordinates through durable dataset facts rather than hidden clock assumptions.
8. [Environments, secrets, CI/CD, rollout, and orchestrator operations](08-environments-secrets-ci-cd-rollout-and-orchestrator-operations.md) delivers and operates workflow code safely.

## Shared reference workflow

```text
validated landing generation (authoritative replay input)
                         |
                         v
              [confirm interval ready]
                         |
                         v
               [build event facts]
                         |
              +----------+----------+
              |                     |
              v                     v
     [build product metric]  [build quality facts]
              |                     |
              +----------+----------+
                         v
              [test and reconcile]
                         |
                         v
       [atomically certify publication]
                         |
                         v
              BI and application users
```

| Boundary | Grain and identity | Authority | Commit or readiness fact |
| --- | --- | --- | --- |
| Landing generation | One accepted event per tenant and event ID | Validated landing owner | Immutable manifest and source frontier |
| Workflow run | One workflow definition and half-open data interval | Orchestrator metadata for coordination only | Run ID, interval, code version, state |
| Task attempt | One task/run/map index/attempt tuple | Orchestrator metadata | Attempt state; not proof of dataset correctness |
| Model relation | Declared model grain under a code version | Transformation owner | Warehouse transaction or table snapshot |
| Certified metric | One tenant, product, metric version, and UTC date | Metric owner | Publication ID plus tests and input frontier |

Starting assumptions are 3 million events/day (about 3 GiB encoded), a 02:00 UTC
daily certified publication, a 15-minute freshness objective for operational
metrics, 35 days of hot replay, 20 concurrent BI readers, and 35% of events from
one tenant. They are hypotheses, not measurements.

## Durable orchestration contract

Every workflow in this area must answer:

- Which dataset fact, not merely which task state, makes each dependency ready?
- What exact half-open interval and input frontier does a run cover?
- Which task owns each side effect, commit, retry, timeout, and repair?
- Can any attempt be repeated, overlap another interval, or finish after cancellation?
- How are code, schema, configuration, environment, and dataset versions recorded?
- What bounds catchup, dynamic expansion, queueing, resource use, and downstream load?
- What evidence proves that a successful run produced a correct, complete, visible result?

## Evidence and scope

This pass supplies mental models, SQL/Python sketches, failure tables, operational
procedures, capacity assumptions, migration sequences, and exact pending evidence.
It adds no dependencies or executable services. DAG parsing, real scheduling,
worker isolation, retries, cancellation, metadata recovery, dbt compilation,
warehouse transactions, lineage emission, load, CI, and rolling upgrades remain
unverified.

Product behavior is illustrative. Airflow and dbt interfaces evolve; pin the
orchestrator, providers/adapters, Python, database, and transformation runtime,
then test the exact combination before claiming compatibility.

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] Scheduling, Airflow architecture, task safety, backfills, transformation management, metadata, delivery, and operations covered
- [x] Grain, ownership, time, identity, failure, security, capacity, migration, and recovery addressed
- [x] Current primary Airflow and dbt documentation linked; version-sensitive guarantees bounded
- [x] Examples and executable evidence accurately marked Planned
- [ ] Deterministic scheduler, task-state, and transformation fixtures implemented
- [ ] Real Airflow, dbt/warehouse, fault, concurrency, load, delivery, and recovery evidence executed

