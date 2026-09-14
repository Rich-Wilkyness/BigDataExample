# Metadata, Lineage, Artifacts, and Data-Aware Scheduling

> Status: Documentation complete; executable metadata evidence planned  
> Level: Intermediate to Senior  
> Applies to: Orchestration / Transformation metadata / Catalogs / Lineage / Data-aware scheduling  
> Data scale: Local metadata fixture; cross-system production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Operational metadata explains what was planned, attempted, built, tested, and
published. Lineage connects versioned datasets and transformations. Data-aware
scheduling starts work from a durable dataset update rather than assuming a
clock implies readiness. These mechanisms improve coordination only when dataset
identity, version, frontier, and ownership are precise.

## Learning objectives

- Separate control metadata, data metadata, lineage, and evidence artifacts.
- Design dataset update events with identity, version, and completeness.
- Join orchestrator, transformation, warehouse, catalog, and consumer evidence.
- Detect stale, missing, duplicated, and cyclic cross-system dependencies.
- Bound metadata cardinality, retention, access, and recovery.

## Prerequisites

- Dataset/run/task identities from guides 01 and 03.
- Source/model artifacts from guide 06.
- Catalog and publication concepts from Area 11.

## Mental model and terminology

```text
input dataset version --used by--> run/invocation --generated--> output version
       |                              |                            |
  catalog/schema                logs/results/plan             quality receipt
       \-------------------------- lineage ----------------------/
                                   |
                         data-aware dependency event
```

| Term | Meaning in this guide |
| --- | --- |
| Operational metadata | Run, task, query, state, timing, resource, and error facts |
| Technical metadata | Schema, partitions, location, statistics, and format facts |
| Lineage edge | Versioned “used” or “generated” relationship with transformation context |
| Artifact | Immutable machine-readable output such as manifest, compiled SQL, or run results |
| Dataset event | Durable notice that a particular dataset version/frontier changed |
| Facet | Structured metadata attached to a run, job, dataset, or lineage edge |

## Requirements, scale assumptions, and invariants

- Dataset identity is environment-qualified and stable across display-name changes.
- An update event identifies dataset version, covered interval/frontier, schema,
  producer run, publication time, and idempotency key.
- Events are emitted only after authoritative commit and may be delivered more than once.
- Consumers deduplicate and verify current authoritative metadata before acting.
- Artifacts are tied to code/config/runtime versions, sanitized, immutable, and retained.
- Lineage distinguishes observed execution from inferred/static dependency.
- Metadata outage must not corrupt data; degraded publication/discovery policy is explicit.
- Estimate: 10,000 task instances/day and 1,000 datasets; event/cardinality/load are unmeasured.

## Data flow, ownership, and trust boundaries

| Boundary | Contract and authority | Failure behavior | Trust level |
| --- | --- | --- | --- |
| Orchestrator metadata | Run/task coordination; platform-owned | May disagree transiently with data commit | Operational evidence |
| Transformation artifacts | Compiled graph/results; release-owned | Missing artifact blocks reproducibility | Trusted if provenance verified |
| Warehouse/catalog | Relation/snapshot/schema truth; dataset-owned | Query/catalog availability may differ | Authoritative data metadata |
| Lineage service | Indexed copies of edges/facets; governance-owned | Rebuild or mark incomplete | Derived index |
| Dataset event channel | At-least-once update notices; producer-owned | Duplicate/delay/out-of-order expected | Untrusted until verified |
| Consumer | Verifies contract and records consumed version | Hold prior version on incompatibility | Separate owner |

## Dataset update contract

```json
{
  "event_id": "daily-product-metric/pub-2026-09-06-v3",
  "dataset_id": "prod.analytics.daily_product_metric",
  "dataset_version": "pub-2026-09-06-v3",
  "interval": "[2026-09-06T00:00:00Z,2026-09-07T00:00:00Z)",
  "input_frontier": "landing-generation-1842",
  "schema_version": "4",
  "producer_run_id": "scheduled__...",
  "quality_receipt": "quality-7f2..."
}
```

The event contains identifiers, not secrets or rows. The consumer resolves the
publication in the catalog/ledger and verifies compatibility. Event order alone
does not select the winner; version/replacement policy does.

### Artifact join

```sql
select p.publication_id, p.dataset_id, p.interval_start, p.interval_end,
       r.code_version, r.input_frontier, q.quality_status
from publication_ledger p
join run_evidence r on r.run_id = p.producer_run_id
join quality_receipt q on q.receipt_id = p.quality_receipt_id
where p.publication_id = :publication_id;
```

The metadata schema is illustrative. Enforce tenant/environment keys and avoid
ambiguous display names.

## Coordination choices

| Need | Prefer | Why | Risk to manage |
| --- | --- | --- | --- |
| Fixed business cutoff | Timetable plus readiness check | Deadline remains visible | Clock is not completeness |
| Producer-driven update | Dataset/asset event | Less polling and tighter dependency | Duplicate, missing, coarse event |
| Cross-system workflow | Versioned event plus catalog verification | Loose coupling | Event/catalog disagreement |
| Bulk backfill | Manifest and explicit range | Bounded, auditable expansion | Event storm |
| Human certification | Signed approval artifact | Clear authority | Delay and bypass controls |

Avoid long chains of workflow-to-workflow triggers that hide interval mappings.
Prefer shared dataset contracts and make each consumer record the version it used.

## Lifecycle, consistency, identity, and time

Metadata can arrive after data, before indexes refresh, or out of order. Store
event time, commit time, observation time, and ingestion time separately. Treat
catalog and lineage views as potentially stale indexes; the publication ledger or
table snapshot is authoritative for version visibility.

Corrections create a new publication linked to the superseded one. Never rewrite
old run artifacts to make history look clean. Erasure may require removing or
tokenizing values embedded accidentally in metadata while preserving audit facts.

## Failure model and recovery

| Failure | Detection/containment | Recovery evidence |
| --- | --- | --- |
| Commit succeeds, event emission fails | Outbox/unemitted-publication scan | Re-emit same event ID; consumer deduplicates |
| Duplicate/out-of-order event | Stable event ID and version policy | One selected publication, no duplicate work |
| Lineage misses dynamic SQL edge | Reconcile runtime query/catalog evidence | Add explicit facet/manual boundary; mark confidence |
| Manifest from wrong release | Provenance/version mismatch | Reject artifact and rerun correct release |
| Catalog/lineage outage | Health and freshness indicators | Continue/hold per policy; replay index later |
| Metadata contains secret/PII | Scanner/access incident | Revoke, redact/expire, rotate secret, audit exposure |
| Cross-DAG cycle | Dependency graph analysis | Introduce owned dataset boundary or redesign trigger |

## Security, privacy, and governance

Metadata reveals names, schedules, structure, users, and sometimes values. Apply
authentication, least privilege, tenant/environment isolation, encryption,
retention, audit, and safe logging. Do not copy SQL literals or sample rows into
widely visible lineage without classification. Validate artifact provenance and
escape identifiers in UI/report consumers.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Event contract | JSON fixtures / local | Schema, duplicate, missing, out-of-order tests | Deterministic accepted/rejected events | Pending |
| Artifact consistency | Synthetic manifest/results/catalog | Join and reconcile IDs/versions | One reproducible evidence chain | Pending |
| Emission fault | Outbox model | Crash around commit/emission | Event eventually emitted once logically | Pending |
| Lineage coverage | Test transformation graph | Compare declared and observed edges | Gaps labeled and reviewed | Pending |
| Metadata load/restore | Test services | Generate volume, lose/rebuild index | SLO and reconciliation hold | Pending |

## Debugging guide

1. Begin with dataset ID/version, interval/frontier, consumer, and expected publication.
2. Trace publication -> quality receipt -> producer run -> invocation -> compiled artifact -> input versions.
3. Compare authoritative ledger/catalog with event channel, lineage index, and orchestration state.
4. Inspect event ID, offsets, retries, schema version, timestamps, and provenance.
5. Hold downstream action when authority is ambiguous; repair index/event delivery separately from data.
6. Replay idempotently and confirm consumers recorded the intended version.

## Common pitfalls

### Pitfall: lineage graph is the source of truth

It is often a delayed or incomplete index. Use it to navigate, then verify the
authoritative dataset and execution artifacts.

### Pitfall: emit readiness before commit

Consumers race an invisible or partial dataset. Emit from a transactional outbox
or reconcile post-commit publication records.

### Pitfall: dataset name is identity

Names can collide across environment or change. Use stable qualified IDs and
record aliases/migrations.

## Performance, capacity, and cost

Budget event rate, artifact bytes, lineage edges, indexed fields, label
cardinality, metadata database growth, retention, API latency, and replay time.
Aggregate high-volume task metrics while retaining trace IDs in logs. Backfills
may emit thousands of updates; batch or rate-limit notifications without losing
per-version truth.

## Compatibility, migration, backfill, and delivery

Version event schemas and artifacts. Producers first add fields; consumers ignore
unknown optional fields; required semantic changes use a new version/topic or
compatibility gate. Dual-emit and compare during migration, backfill the index,
cut over consumers, retain rollback, then remove old emission after measured use.

## Working example

- Python source: Planned event/outbox model under `src/big_data_example/orchestration/`
- SQL: Planned evidence-chain query under `sql/orchestration/`
- Tests: Planned contract, ordering, fault, lineage, and restore tests
- Infrastructure: Planned Airflow/transform/catalog/lineage integration
- Try it: Planned emit, duplicate, reorder, and reconcile command
- Expected result: One verified downstream action per committed publication
- Evidence: Planned artifacts, ledger joins, lineage diff, metrics, and restore report
- Scale represented: Local metadata fixture and estimates only
- Remaining risk: Real event, catalog, lineage, and metadata-system behavior unverified

## Knowledge check

1. Distinguish control metadata, technical metadata, artifacts, and lineage.
2. Predict behavior when an update event arrives twice and out of order.
3. Diagnose a lineage UI showing success while the publication ledger is absent.
4. Design an outbox crash test around data commit and event emission.
5. Estimate metadata growth for 10,000 task instances/day and stated retention.
6. Migrate a dataset ID while preserving consumer and historical lineage.
7. Extend the planned event contract with an explicit supersedes field and tests.

## Key takeaways

- Metadata explains data; it is not automatically data authority.
- Dataset-aware scheduling requires versioned, post-commit, idempotent events.
- Artifacts bind graph, compiled code, results, and runtime to a release.
- Lineage confidence and freshness must be visible.
- Cross-system recovery reconciles every index with authoritative publication state.

## Resources

- [Apache Airflow: assets](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html) (reviewed 2026-09)
- [dbt: artifacts](https://docs.getdbt.com/reference/artifacts/dbt-artifacts) (reviewed 2026-09)
- [OpenLineage specification](https://openlineage.io/docs/spec/) (reviewed 2026-09)
- [W3C PROV overview](https://www.w3.org/TR/prov-overview/) (reviewed 2026-09)

## Related topics

- [SQL transformation projects](06-sql-transformation-projects-models-tests-and-documentation.md)
- [Environment and orchestrator operations](08-environments-secrets-ci-cd-rollout-and-orchestrator-operations.md)
- [Area 11 catalogs](../11-warehouses-lakes-lakehouses-and-serving-systems/05-catalogs-metastores-namespaces-and-discovery.md)

## Completion checklist

- [x] Metadata, artifact, lineage, event, identity, frontier, and authority contracts defined
- [x] JSON/SQL sketches and coordination decision table included
- [x] Ordering, emission, outage, security, privacy, and recovery addressed
- [x] Evidence, capacity, compatibility, migration, and diagnosis covered
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Event/outbox, artifact, lineage, integration, load, and restore evidence executed

