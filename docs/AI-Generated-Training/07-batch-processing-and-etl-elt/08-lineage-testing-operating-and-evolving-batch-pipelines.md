# Lineage, Testing, Operating, and Evolving Batch Pipelines

> Status: Documentation complete; executable evidence planned  
> Level: Senior  
> Applies to: Generic data engineering / Python / SQL / Batch / Platform  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A production batch pipeline is a maintained data product, not a scheduled script.
Its owners must trace every published version, test business and failure behavior,
operate freshness and correctness objectives, evolve contracts without mixing
versions, and repair history when change or failure invalidates prior results.

This guide assembles area 07 into a release and operating model. It does not claim
that local fixtures prove distributed, cloud, scheduler, or production behavior.

## Learning objectives

- Capture run-, dataset-, field-, and consumer-level lineage with useful limits.
- Build an evidence ladder from unit tests through operational recovery drills.
- Define freshness, completeness, correctness, latency, and availability objectives.
- Diagnose a failed or incorrect batch from authoritative metadata outward.
- Evolve schema, semantics, code, configuration, dependencies, and consumers safely.

## Prerequisites

- All preceding area 07 guides
- Data-product evolution from area 05 and ingestion lineage/reconciliation from area 06

## Mental model and terminology

Treat a pipeline like a versioned public library plus a stateful release system:
tests check behavior, compatibility constrains change, and telemetry supports
operation. The analogy stops because data outputs preserve historical semantics,
consumer queries may be undiscoverable, and correcting data can require rebuilding
years of derived state rather than redeploying code alone.

| Term | Meaning in this guide |
| --- | --- |
| Run lineage | Inputs, code/config, attempts, gates, and output versions for one logical run |
| Dataset lineage | Directed dependencies among versioned datasets and publications |
| Column lineage | Declared or observed mapping from source fields/expressions to output fields |
| Data SLI | Measured indicator such as freshness, completeness, correctness, or availability |
| Data SLO | Target for an SLI over a window, with owner and consequence |
| Contract test | Evidence that a producer/consumer boundary satisfies schema and semantic expectations |
| Certification | Decision that required evidence passes for a named dataset version |

## Requirements, assumptions, and invariants

Reference publication is due daily by 02:00 UTC, with a provisional design target
of 99.5% on-time days per 30-day window and zero unexplained missing accepted
event IDs in a closed scope. These are curriculum assumptions, not approved
production SLOs. Completeness tolerances for declared quarantines and metric
accuracy must come from consumers and business owners.

Invariants:

- Every published version names immutable inputs, code/config/schema/semantic versions, and gate results.
- Operational success requires data contract evidence, not task status alone.
- Tests compare records at declared grain and aligned input/version boundaries.
- Telemetry dimensions are bounded and contain no raw sensitive values.
- Breaking schema or semantic change creates a migration path and usually a new contract version.
- Repair/backfill lineage remains distinguishable from original processing.
- Ownership and runbooks exist for every alert that can page or block publication.

## Lineage model and trust boundaries

```text
receipt/input manifests --+
product history version --+--> logical run --> candidate manifest --> certified dataset version
code artifact digest ------+         |                 |                         |
config/rule version -------+       attempts         gate results              consumers
```

| Evidence | Grain | Owner | Retention/use |
| --- | --- | --- | --- |
| Run ledger | One logical run and attempts | Pipeline operator | Retry, diagnosis, audit |
| Dataset manifest | One certified dataset version | Data-product owner | Consumer resolution, restore, reconciliation |
| Record lineage | Source identity to output key/disposition where required | Pipeline/data owner | Repair and regulated traceability |
| Column mapping | Output field to source fields/rules | Model owner | Impact analysis and review |
| Consumer registry | Dataset contract/version to known consumer | Producer and consumer owners | Migration and incident communication |

Column lineage helps impact analysis but can mislead around dynamic SQL, UDFs,
aggregates, filters, and external lookups. Pair automated extraction with declared
business semantics and tests. Do not retain record-level personal identifiers
without a correctness or regulatory need.

## Evidence ladder

| Level | Example evidence | What it does not prove |
| --- | --- | --- |
| Unit/property | Parser, transform, boundary, state-machine invariants | Storage/database semantics or scale |
| SQL/data quality | Grain, uniqueness, validity, referential integrity, reconciliation | Concurrent commit and production distributions |
| Contract/compatibility | Old/new schemas, producers, consumers, semantic fixtures | Full historical impact |
| Integration | Real database, storage, catalog, scheduler | Distributed failure and production load |
| End-to-end/fault | Crash, timeout, retry, restore, backfill, consumer read | Long-duration capacity and rare production data |
| Performance/resilience | Scale, skew, soak, concurrency, fault injection, cost | Organizational response and real demand shifts |
| Operational/delivery | Dashboards, alerts, runbooks, canary, rollback, review | Future behavior without continuing measurement |

Use mutation tests that remove a row, duplicate a key, shift a timestamp, overlap
a dimension interval, change a schema, corrupt a file, and bypass a candidate.
Passing only happy fixtures gives weak confidence in detection.

## Reference release gates

```text
input contract -> transform tests -> candidate schema/grain
              -> validity/referential checks
              -> source/canonical/fact/metric reconciliation
              -> old/new semantic diff when changing
              -> performance/cost and consumer contract checks
              -> publish or reject
```

Gate thresholds are versioned configuration with owner and rationale. A warning
cannot silently become a pass, and “no result” is not success. Emergency overrides
must record scope, approver, consumer impact, expiry, and mandatory repair.

## Observability and objectives

| SLI | Definition | Diagnostic dimensions | Initial action |
| --- | --- | --- | --- |
| Freshness | `now - max certified source boundary/publication time` per contract | Dataset, environment | Inspect upstream boundary, queue, and active run |
| Completeness | Expected closed-scope identities minus explained dispositions/output | Dataset version, source partition/date | Freeze publication; reconcile keys |
| Correctness | Failed invariants or domain-total delta | Check/rule version, dataset version | Quarantine candidate or invalidate version |
| Pipeline latency | Admission to certification duration | Pipeline/node class | Inspect critical path, skew, spill, dependency latency |
| Availability | Fraction of valid reads/resolutions of certified version | Dataset/interface | Restore metadata/storage or select good version |

Avoid event ID, customer ID, file path with unbounded cardinality, exception text,
or query text as metric labels. Put high-cardinality correlation in protected logs,
traces, lineage, or diagnostic tables with retention and access controls.

## Debugging guide

1. Identify affected consumers, dataset contract/version, scope, and first bad publication.
2. Read the authoritative dataset head, manifest, checkpoint, and run ledger; do not infer truth from scheduler color.
3. Compare input manifests/positions, code/config/schema/semantic versions, and dependency versions to the last good run.
4. Inspect gate results, disposition counts, anti-joins, totals, partition sizes, plans, task timelines, retries, and resource metrics.
5. Reproduce one bounded failing input under protected conditions and preserve evidence.
6. Mitigate by retaining/selecting a known-good version, pausing unsafe publication, or declaring scoped degradation.
7. Repair with a versioned rerun/backfill, independently reconcile it, validate consumers, and communicate correction.
8. Close only after convergence, root cause, impact, preventive evidence, and runbook/monitor updates are recorded.

Correlate dataset, logical run, attempt, batch/window, input manifest, source
partition/position, schema, semantic, code/config, query/statement, candidate,
publication generation, and consumer version identifiers.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Lineage missing for candidate | Gate cannot resolve inputs/versions | Reject publication; reconstruct only from durable evidence |
| Quality check silently stops | Expected check inventory/result absent | Treat as gate failure; restore check and retest scope |
| Fresh but wrong dataset | Correctness/reconciliation/consumer signal | Freeze new reads if possible; select prior good or forward-repair |
| Schema-compatible semantic break | Golden/old-new/consumer test delta | Version semantics, rebuild, and migrate consumers |
| Alert floods or never fires | Synthetic probe/review | Fix SLI/query/routing and rehearse response |
| Catalog/metadata unavailable | Head/lineage resolution failure | Use tested backup/restore or declared read continuity path |
| Backup restores files but not truth | Manifest/checkpoint/reconciliation mismatch | Rebuild coherent metadata/data version and reconcile |

## Security, privacy, and governance

Classify datasets and operational evidence; minimize record lineage; mask samples;
protect query history and error payloads; encrypt storage and transport; audit
publication, override, replay, and deletion; and separate duties where risk demands
it. Test tenant isolation and row/column policies on candidates and final objects.

Deletion and retention require lineage-driven propagation across raw, canonical,
facts, aggregates, candidates, quarantine, checkpoints, manifests, backups, caches,
and exports. Record legal exceptions and prevent a backfill from resurrecting
erased data. Observability data is not exempt from purpose limitation.

## Data quality, testing, and evidence plan

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Unit/property suite | Deterministic local fixture | Transform, range, state, manifest properties | Core invariants hold | Pending |
| SQL/quality mutations | Local/real SQL engine | Inject missing, extra, duplicate, null, fan-out, time defects | Every material defect is detected | Pending |
| Contract/compatibility | Old/new schemas and consumers | Producer/consumer plus semantic golden cases | Supported versions pass; breaks block | Pending |
| Integration/fault | Real DB/storage/catalog/scheduler | Timeout, crash, race, restart, corrupt object | Old/new visibility and convergence | Pending |
| Backfill/restore | Representative retained scope | Rebuild, cut over, roll back/forward, reconcile | Coherent reproducible version | Pending |
| Scale/skew/cost | Representative cardinality/distribution | Sweep volume, file/partition size, concurrency | SLO/capacity/cost budget holds | Pending |
| Operational rehearsal | Staging environment | Fire alerts and execute runbooks | Owner restores and proves correctness | Pending |

## Common pitfalls

### Pitfall: measuring task success as data health

A green task can publish zero, duplicate, stale, or semantically wrong records.
Measure the consumer-visible dataset contract and reconcile closed input scope.

### Pitfall: lineage as a graph with no versions

“Table A feeds table B” cannot reproduce a result. Capture exact input/output,
code, config, schema, semantic, and dependency versions.

### Pitfall: testing only transforms

Most severe failures live at selection, commit, retry, schema, dependency,
backfill, and consumer boundaries. Exercise the full lifecycle and failure matrix.

### Pitfall: backward-compatible schema means safe change

Renamed meaning, changed filter, time zone, key, or denominator can preserve types
while breaking results. Version and test semantics as well as schema.

## Performance, capacity, cost, and operations

Maintain a workload model for rows/bytes/files/partitions, growth, skew, scan and
shuffle, peak memory/disk/network, concurrency, critical path, recovery reserve,
retention, rebuild time, and monetary cost. Record plans and results with engine,
configuration, code, dataset version, and representative data distribution.

Operational reviews examine SLO burn, incidents, recurring retries, gate trends,
late/correction distributions, capacity headroom, cost per publication/backfill,
stale consumers, lineage gaps, restore age, and runbook rehearsal. Liveness shows
the process can run; readiness proves required dependencies and safe commit access;
neither proves dataset correctness.

## Compatibility, migration, backfill, and delivery

Classify changes to schema, grain, keys, time, nulls, filters, reference data,
metrics, file/table layout, engine, dependencies, configuration, security policy,
and retention. Use expand/migrate/contract: produce compatible old/new contracts,
dual-run pinned scopes, compare semantics and performance, backfill if required,
canary known consumers, atomically switch, monitor, then retire after the declared
support and rollback window.

Package immutable code and dependencies; validate configuration as a versioned
contract; run migrations before code that requires them; and avoid changing code,
schema, and semantic logic without independently attributable evidence. Rollback
selects a compatible known-good data/code combination; when privacy or exported
effects prohibit rollback, use a forward correction.

## Engineering tradeoffs

| Requirement | Prefer | Tradeoff |
| --- | --- | --- |
| Strong reproducibility | Immutable inputs/artifacts/config and versioned references | Storage and release discipline |
| Fast diagnosis | Rich run/dataset lineage and retained candidates | Metadata, privacy, and retention cost |
| Early defect detection | Layered contract, mutation, reconciliation, and consumer tests | Runtime and maintenance cost |
| Low alert fatigue | Consumer-oriented SLOs with owned actionable alerts | Requires careful thresholds and review |
| Safe evolution | Dual runs, versioned contracts, backfill, atomic cutover | Temporary compute/storage and migration complexity |
| Rapid emergency repair | Pre-approved runbooks and isolated forward correction | Still requires audit and post-incident proof |

## Working example

- Python/SQL/data/tests: planned end-to-end product-event fixture, lineage/run manifests, quality gates, mutation suite, fault harness, dashboards-as-contract, and migration/backfill rehearsal
- Try it: planned exact commands after implementation
- Expected result: only traceable, reconciled, compatible versions publish; injected defects and failures are detected and recoverable
- Scale represented: none yet; local, integration, representative scale, then operational evidence planned
- Remaining risk: distributed failure, production distributions, unknown consumers, restore time, and organizational response

## Knowledge check

1. Trace one metric row back through fact, canonical, raw, code, config, and input versions.
2. Predict which evidence catches one missing and one extra event when counts remain equal.
3. Diagnose a green run that publishes yesterday's product dimension.
4. Design an SLO and alert for a daily dataset without unbounded metric labels.
5. Plan a semantic key change requiring one-year backfill and mixed consumer migration.
6. Rehearse restoration and state the evidence required before declaring recovery.
7. Add one bounded mutation to the planned reference suite and name its expected detection layer.

## Key takeaways

- A batch pipeline is operated through the consumer-visible data contract.
- Versioned lineage makes reproduction, impact analysis, repair, and audit possible.
- Evidence must cover logic, data quality, integration, failure, scale, delivery, and operations.
- Freshness without completeness and correctness is not health.
- Safe evolution couples compatibility, semantic comparison, backfill, cutover, rollback, and consumer coordination.

## Resources

- [W3C PROV overview](https://www.w3.org/TR/prov-overview/) (reviewed 2026-09)
- [OpenLineage specification](https://openlineage.io/docs/spec/) (reviewed 2026-09)
- [Python documentation: logging](https://docs.python.org/3/library/logging.html) (reviewed 2026-09)
- [PostgreSQL documentation: EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html) (reviewed 2026-09)

## Related topics

- [Area 07 overview](README.md)
- [Backfills, reprocessing, and historical correction](06-backfills-reprocessing-and-historical-correction.md)
- [Dependencies, retries, partial failure, and recovery](07-dependencies-retries-partial-failure-and-recovery.md)
- [Data marts, domain products, and model evolution](../05-data-modeling-and-business-semantics/08-data-marts-domain-products-and-model-evolution.md)

## Completion checklist

- [x] Lineage, evidence ladder, SLOs, debugging, operations, evolution, delivery, and ownership explained
- [x] Security, privacy, quality, capacity, compatibility, backfill, rollback, and evidence limits addressed
- [ ] Reference implementation, integration, fault, scale, restore, delivery, and operational evidence run
