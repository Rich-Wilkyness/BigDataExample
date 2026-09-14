# 15 Reliability, Observability, Performance, Cost, and Operations

> Area status: Documentation complete; executable operational evidence planned  
> Level: Intermediate to Senior data engineering  
> Applies to: Batch / Streaming / Storage / Warehouses / Data platforms / Operations  
> Reference scenario: Operated mobile-event pipeline with objectives, telemetry, capacity and cost budgets, recovery, and safe delivery  
> Evidence boundary: Documentation and current primary-source review; no fault, load, restore, rollout, or disaster-recovery exercise has run  
> Last reviewed: 2026-09

## Purpose

A data system is useful only while consumers can obtain data that is sufficiently
correct, complete, fresh, available, and affordable. Reliability defines those
consumer-visible outcomes and the conditions under which they hold. Observability
provides evidence about system state. Performance and capacity describe whether
the workload fits within time and resource budgets. Cost makes resource choices
economically explicit. Operations keeps all of those guarantees true through
failures and change.

An Android crash-free-session metric is a useful bridge: it measures an outcome,
while logs and traces help diagnose why it changed. The analogy stops where a data
product has asynchronous publication, historical correction, several record and
interval populations, long-lived derived copies, and consumers who may keep using
an incorrect result after the compute job has recovered.

This area synthesizes earlier correctness, distributed-systems, orchestration,
quality, security, and governance work into an operating model. It stays
vendor-neutral and does not prescribe an on-call tool, observability backend,
query engine, cloud, container orchestrator, infrastructure language, or incident
management framework.

## Prerequisites

- Requirements, scale, and boundaries from [Area 01](../01-big-data-and-data-engineering-foundations/README.md).
- SQL/Python execution and storage behavior from [Area 02](../02-python-for-data-engineering/README.md), [Area 03](../03-sql-and-analytical-querying/README.md), and [Area 04](../04-data-storage-files-and-serialization/README.md).
- Processing, distributed failure, streaming state, and serving from [Area 07](../07-batch-processing-and-etl-elt/README.md) through [Area 11](../11-warehouses-lakes-lakehouses-and-serving-systems/README.md).
- Workflow operations and evidence design from [Area 12](../12-workflow-orchestration-and-transformation-management/README.md) and [Area 13](../13-data-quality-contracts-and-testing/README.md).
- Governance, access, lifecycle, and audit from [Area 14](../14-governance-security-privacy-and-data-lifecycle/README.md).
- No third-party package, service, cloud account, or production access is required for this documentation pass.

## Learning path

1. [Data-system reliability requirements and failure domains](01-data-system-reliability-requirements-and-failure-domains.md) turns consumer harm into guarantees and explicit blast-radius boundaries.
2. [Logs, metrics, traces, lineage, and correlation](02-logs-metrics-traces-lineage-and-correlation.md) designs safe complementary signals across asynchronous data work.
3. [Data SLIs, SLOs, alerts, dashboards, and runbooks](03-data-slis-slos-alerts-dashboards-and-runbooks.md) measures outcomes and connects objective threats to action.
4. [Incident response, data repair, and organizational learning](04-incident-response-data-repair-and-organizational-learning.md) contains harm, repairs durable data, and turns incidents into owned improvements.
5. [Backups, restores, checkpoints, and disaster recovery](05-backups-restores-checkpoints-and-disaster-recovery.md) restores authoritative state and validates dependencies against RPO/RTO.
6. [Performance profiling, query plans, and capacity modeling](06-performance-profiling-query-plans-and-capacity-modeling.md) finds bottlenecks with representative workloads and forecasts limits.
7. [Cost modeling, FinOps, quotas, and workload isolation](07-cost-modeling-finops-quotas-and-workload-isolation.md) attributes cost and protects both budgets and critical work.
8. [Infrastructure, delivery, rollout, rollback, and operations](08-infrastructure-delivery-rollout-rollback-and-operations.md) delivers inspectable infrastructure and data changes with safe lifecycle behavior.

The order is deliberate: state the guarantee before selecting telemetry, alerting,
recovery, tuning, cost, or deployment mechanisms. In practice these activities
form a feedback loop rather than eight independent phases.

## Shared reference scenario

```text
mobile producers -> ingest -> validated events -> daily product metrics -> BI/API
                       |             |                    |
                    stream log    object/table         warehouse
                       |             |                    |
                       +------ run + dataset lineage -----+

control plane: scheduler, catalog, identity, policy, deployment, telemetry
operations: objectives -> alerts -> diagnosis -> containment -> repair -> review
economics: workload demand -> capacity -> allocation -> budget -> optimization
```

| Boundary | Grain and authority | Consumer guarantee | Operational owner |
| --- | --- | --- | --- |
| Accepted event | One logical event per `tenant_id,event_id`; governed event store is authoritative | Valid identity and durable acceptance | Ingestion owner |
| Daily publication | One tenant, UTC date, product, and metric version | Certified completeness/correctness by freshness deadline | Dataset owner |
| Run receipt | One job attempt and one immutable input/output frontier | Outcome and publication association are attributable | Orchestration owner |
| Telemetry event | One observation from a named source/version | Delay and loss are measured; telemetry is not authoritative business data | Observability owner |
| Incident | One coordinated response to a bounded consumer impact | Command, decisions, repairs, and closure are recorded | Incident commander and dataset owner |
| Cost record | One provider charge or allocated usage line for a billing period | Allocation method and unallocated amount remain visible | Platform plus finance owner |

Starting estimates are 3 million events/day (about 3 GiB encoded), 100 tenants,
35 days of hot replay, 100 million retained governed events, 100 scheduled
workflows, 10,000 task instances/day, and 1,000 registered datasets. Assume a
daily publication deadline of 120 minutes after source readiness and a provisional
99.9% availability target only where the guide says so. These figures are teaching
hypotheses, not measurements, commitments, or a production design.

## Durable operating contract

Every operated data product must answer:

- Which consumer decision is harmed, which eligible population is measured, and which invariant or objective protects it?
- Where are authoritative state, derived copies, commit frontiers, checkpoints, backups, and restoration dependencies?
- Which failures share a region, account, cluster, scheduler, catalog, identity, network, or human dependency?
- Which safe signals prove impact, cause, telemetry health, and recovery without exposing data?
- Who can declare, command, communicate, contain, repair, certify, and close an incident?
- Which workload, bottleneck, saturation point, headroom, growth model, and cost allocation justify current capacity?
- Which change artifact, review, rollout unit, compatibility window, migration, rollback, and reconciliation protect delivery?
- Which claims have deterministic, integration, distributed, operational, or production evidence, and which remain assumptions?

Recovery of compute is not recovery of data. A green job after a failure does not
prove previously published data is correct, missed intervals were rebuilt,
downstream extracts refreshed, or consumers stopped using a bad version.

## Evidence ladder and scope

| Evidence | What it demonstrates | What remains unproven |
| --- | --- | --- |
| Contract/tabletop review | Owners, failure domains, decisions, and procedures are explicit | Runtime behavior or realistic timing |
| Deterministic model/fixture | Arithmetic, state transitions, and edge cases for bounded inputs | Real engine, service, contention, or scale |
| Integration fault test | Named components detect and recover from injected failure | Multi-node and regional behavior |
| Representative load/profile | Bottleneck, latency distribution, resource use, and cost for one workload | Future growth and different skew/concurrency |
| Restore/rollout rehearsal | Recovery or delivery procedure converges in a named environment | Undrilled dependencies or disaster scope |
| Distributed game day | Failure-domain isolation and operational coordination under controlled faults | Unmodeled correlated failures |
| Production observation | Actual outcomes, demand, cost, incidents, and recovery for a bounded period | Future workloads and unseen failure modes |

This pass supplies definitions, models, SQL/Python sketches, failure tables,
decision criteria, runbook steps, and precise pending evidence. It does not claim
an achieved SLO, tested recovery point/objective, measured capacity, optimized
cost, safe rollout, distributed resilience, or production readiness.

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] Reliability, telemetry, objectives, incidents, recovery, performance, cost, and delivery connected into one operating model
- [x] Consumer harm, ownership, failure domains, data repair, security, scale, cost, and migration boundaries explicit
- [x] Primary standards and official guidance linked with review dates
- [x] Working examples and executable evidence accurately marked Planned
- [ ] Fault, correlation, SLI/alert, incident, repair, restore, and DR evidence executed
- [ ] Representative profile, query-plan, load, capacity, cost, quota, rollout, rollback, and production evidence executed
