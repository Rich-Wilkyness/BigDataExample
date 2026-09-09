# 13 Data Quality, Contracts, and Testing

> Area status: Documentation complete; executable quality evidence planned  
> Level: Beginner to Senior data engineering  
> Applies to: Batch / Streaming / SQL / Python / Storage / Data products  
> Reference scenario: Mobile-event quality suite with deliberately faulty inputs, quarantine, reconciliation, and certification  
> Evidence boundary: Documentation and current primary-source review; no quality suite, real engine, or production monitoring executed yet  
> Last reviewed: 2026-09

## Purpose

Data quality is the degree to which a dataset is fit for a stated use, not a
universal score attached to a table. Contracts make the producer's guarantees
and the consumer's assumptions explicit. Tests, runtime checks, reconciliation,
and operational objectives supply different kinds of evidence that those
contracts still hold. None proves all possible data is correct.

An Android type and its unit tests are a useful starting analogy: a type can
exclude malformed states and tests can exercise behavior. The analogy stops at
the data boundary. Historical rows outlive a deployment, multiple producers and
consumers evolve independently, cross-row properties require dataset queries,
and a syntactically valid event can still describe the wrong real-world fact.

This area develops a risk-based evidence system from requirements through
incident repair. It remains vendor-neutral and does not select a validation
framework, schema registry, warehouse, or observability product.

## Prerequisites

- Requirements, boundaries, scale estimates, and guarantees from [Area 01](../01-big-data-and-data-engineering-foundations/README.md).
- Python boundary and test fundamentals from [Area 02](../02-python-for-data-engineering/README.md).
- SQL `NULL`, constraints, grouping, joins, and query plans from [Area 03](../03-sql-and-analytical-querying/README.md).
- Grain, keys, dimensions, facts, and semantic ownership from [Area 05](../05-data-modeling-and-business-semantics/README.md).
- Schema evolution from [Area 06](../06-data-ingestion-and-source-integration/README.md), reruns and repair from [Area 07](../07-batch-processing-and-etl-elt/README.md), and distributed failure from [Area 08](../08-distributed-systems-foundations/README.md).
- Publication and consumer boundaries from [Area 11](../11-warehouses-lakes-lakehouses-and-serving-systems/README.md) and workflow evidence from [Area 12](../12-workflow-orchestration-and-transformation-management/README.md).
- No third-party Python package, database, broker, or cloud account is required for this documentation pass.

## Learning path

1. [Data quality dimensions, requirements, and ownership](01-data-quality-dimensions-requirements-and-ownership.md) turns vague claims such as “clean data” into consumer-visible requirements.
2. [Schema, data, and consumer contracts](02-schema-data-and-consumer-contracts.md) locates structural and semantic guarantees at enforceable boundaries.
3. [Unit, property, and SQL transformation testing](03-unit-property-and-sql-transformation-testing.md) verifies pure transformations and dataset invariants cheaply and deterministically.
4. [Integration, contract, and end-to-end pipeline testing](04-integration-contract-and-end-to-end-pipeline-testing.md) verifies real engines and cross-system outcomes without confusing test scope.
5. [Fixtures, golden datasets, sampling, and determinism](05-fixtures-golden-datasets-sampling-and-determinism.md) builds reproducible, representative, privacy-safe test inputs.
6. [Reconciliation, freshness, volume, and distribution checks](06-reconciliation-freshness-volume-and-distribution-checks.md) detects missing, duplicated, delayed, and implausibly shifted data.
7. [Quarantine, repair, replay, and quality incidents](07-quarantine-repair-replay-and-quality-incidents.md) contains bad records and converges datasets after failure.
8. [Quality objectives, observability, and evidence portfolios](08-quality-objectives-observability-and-evidence-portfolios.md) connects consumer impact to indicators, objectives, alerts, and evidence gaps.

## Shared reference scenario

```text
mobile producers
      |
      v
raw immutable events -----> safe rejected-record store
      |                              |
 structural + semantic checks        | governed repair decision
      |                              |
      v                              v
validated event generation <---- corrected/replayed events
      |
 deduplicate + transform + aggregate
      |
      v
candidate daily product metrics
      |
 SQL assertions + source reconciliation + quality receipt
      |
      v
atomically certified publication -----> BI and application consumers
```

| Dataset boundary | Grain and identity | Authority and owner | Required evidence before certification |
| --- | --- | --- | --- |
| Raw event | One received envelope per tenant, producer, partition, and position | Ingestion owner; immutable replay authority | Parse status, source position, checksum, arrival time |
| Validated event | One accepted logical event per `tenant_id,event_id` and contract version | Event producer owns meaning; ingestion owns enforcement | Schema result, semantic rules, duplicate decision, rejection reason |
| Daily product metric | One tenant, product, metric version, and UTC date | Metric owner | Grain uniqueness, completeness/freshness, source-to-target reconciliation |
| Rejected record | One failed attempt with protected payload reference | Ingestion and domain owners share resolution | Safe reason code, rule version, source identity, disposition |
| Quality receipt | One dataset version and quality-suite version | Dataset owner | Check results, denominators, thresholds, input frontier, code version |

Starting assumptions are 3 million events/day (about 3 GiB encoded), a burst of
500 events/s, 35 days of hot replay, 100 million retained validated events, a
02:00 UTC daily certification, a 15-minute operational freshness target, and 35%
of traffic from one tenant. These are design estimates, not measurements.

## Durable quality contract

Every quality claim in this area must answer:

- Which consumer decision is protected, and what harm follows a violation?
- What is the record or dataset grain, authoritative identity, time domain, and
  completeness frontier?
- Is the rule structural, semantic, cross-record, cross-dataset, temporal, or
  statistical, and where can it be enforced reliably?
- What denominator, threshold, evaluation window, segmentation, and allowed
  exceptions define success?
- Who owns detection, triage, correction, replay, certification, communication,
  and retirement of the rule?
- What happens to invalid, duplicate, late, out-of-order, or unverifiable data?
- Which evidence proves the claim, and which engine, scale, failure, privacy, or
  production assumptions remain untested?

## Evidence ladder and scope

| Layer | Proves | Does not prove |
| --- | --- | --- |
| Static/schema review | Contract syntax and intended compatibility | Runtime data meaning or producer behavior |
| Unit/property test | Local transformation properties over generated/fixture cases | SQL dialect, distributed state, or real service integration |
| SQL data test | Invariants in one inspected snapshot | Upstream completeness or future snapshots |
| Integration/contract test | Pinned boundary behavior against a real dependency | Full workflow or production scale |
| End-to-end test | A critical outcome across deployed test boundaries | Exhaustive failures or production distributions |
| Runtime quality check | Observed dataset property for a window/version | Real-world accuracy without an external authority |
| Reconciliation | Agreement with a defined independent control | Correctness when both sides share the same defect |
| Production objective/incident evidence | Consumer-visible reliability over time | Correct behavior outside observed conditions |

This pass supplies definitions, SQL/Python sketches, failure models, decision
tables, operational procedures, and exact pending evidence. The intentionally
faulty fixture portfolio, executable test library, SQL suite, integration
services, dashboards, alerts, and incident drill are planned rather than
implied. Local deterministic evidence will not be labeled distributed or
production evidence.

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] Quality dimensions, contracts, test layers, fixtures, reconciliation, incidents, and objectives covered
- [x] Grain, ownership, identity, `NULL`, time, failure, privacy, scale, migration, and recovery addressed
- [x] Primary specifications and documentation linked with review dates
- [x] Examples and executable evidence accurately marked Planned
- [ ] Faulty fixture portfolio and standard-library reference checks implemented
- [ ] Real SQL engine, schema compatibility, pipeline, fault, load, objective, and repair evidence executed
