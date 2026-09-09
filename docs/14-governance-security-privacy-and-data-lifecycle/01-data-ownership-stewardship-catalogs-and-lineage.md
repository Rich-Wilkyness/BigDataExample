# Data Ownership, Stewardship, Catalogs, and Lineage

> Status: Documentation complete  
> Level: Beginner to Senior  
> Applies to: Generic data engineering / Catalog / Batch / Streaming / Storage  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Ownership is accountable authority to define a dataset, approve change, operate
it, repair it, and retire it. Stewardship performs recurring semantic and policy
work under that accountability. A catalog makes metadata discoverable. Lineage
records how named input versions and processing runs produced output versions.
None substitutes for the others.

This guide covers dataset-level governance and column/run lineage. It excludes
product selection and assumes authentication, classification, and deletion are
developed in later guides.

## Learning objectives

After completing this guide, you should be able to:

- Distinguish owner, steward, platform custodian, producer, and consumer decisions.
- Specify a minimum catalog record and useful lineage confidence.
- Diagnose stale ownership, orphan datasets, and incomplete lineage.
- Reconcile catalog declarations with observed storage and executions.
- Evaluate automatic versus asserted metadata and centralized versus federated ownership.

## Prerequisites

- [Area overview](README.md) and Areas 01, 05, 11, and 12 concepts linked there.
- Infrastructure for executable evidence: planned catalog and lineage receiver only.

## Mental model and terminology

A catalog is like a Gradle model of modules and dependencies: useful for discovery
and impact analysis, but it is only correct when inputs are complete and current.
Unlike a build graph, data lineage can be inferred, manually asserted, column-
ambiguous, and split across engines; confidence and observation time matter.

```text
declared contracts ----+
observed jobs ----------+--> normalized metadata --> catalog/search/policy
storage inventory ------+          |                    |
query lineage ----------+          +--> discrepancy ---> owner workflow
```

| Term | Meaning in this guide |
| --- | --- |
| Owner | Accountable team for definition, access approval, operation, repair, and retirement |
| Steward | Role performing classification, terminology, quality, and access-review work |
| Custodian | Platform team operating storage/control infrastructure without owning business meaning |
| Lineage edge | Versioned claim that an operation read, transformed, or produced a dataset |
| Confidence | Provenance of an edge: observed, parsed, inferred, or manually asserted |
| Authoritative dataset | Source from which a stated fact or governed repair is decided |

## Requirements, scale assumptions, and invariants

The catalog must represent stable dataset identifiers, environment, grain,
schema, owners, consumers, classifications, purposes, lifecycle rule, locations,
quality state, and lineage. Assume 1,000 datasets, 10,000 runs/day, 50,000 lineage
edges/day, and 30-day hot metadata; measure actual event and graph growth.

Invariants:

- Every production dataset has one accountable owning team and an escalation route.
- Ownership covers authoritative and derived copies; platform custody is not semantic ownership.
- Lineage refers to immutable dataset/run/schema versions, not display names alone.
- Unknown lineage stays unknown and cannot silently authorize access or certify deletion.
- Metadata changes are versioned, attributable, reviewed where required, and recoverable.
- Catalog unavailability cannot make a previously forbidden action allowed.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Producer declaration | Dataset ID, schema, owner, purpose | Dataset owner | Reject incomplete registration | Authenticated assertion |
| Runtime event | Run, inputs, outputs, code/schema versions | Execution platform | Buffer/replay; mark gaps | Observed but untrusted fields |
| Storage discovery | Location, size, modification evidence | Platform inventory | Report undeclared assets | Observed metadata |
| Normalized graph | Versioned nodes/edges/confidence | Governance platform | Preserve last known; expose staleness | Governed derived state |
| Human correction | Scoped assertion, reason, expiry | Steward with owner approval | Audit and supersede, never rewrite history | Privileged input |

## From registration to useful governance

Start with the smallest catalog record that drives a decision:

```yaml
dataset_id: analytics.governed.mobile_event
grain: one accepted logical event per tenant_id,event_id
owner: event-data
steward: privacy-data-office
authority: raw.mobile_event plus producer contract v2
classification: restricted
approved_purposes: [product_analytics, reliability]
retention_rule: governed-events-v3
```

Then add observed locations, schema versions, consumers, jobs, quality receipts,
and lineage. Do not demand hundreds of fields before registering data; require the
few fields that prevent ownerless or unclassified production data.

### SQL model

The dialect-neutral sketch treats metadata as history, not mutable labels:

```sql
SELECT d.dataset_id
FROM catalog_dataset d
LEFT JOIN catalog_owner_history o
  ON o.dataset_id = d.dataset_id AND o.valid_to IS NULL
WHERE d.environment = 'production'
GROUP BY d.dataset_id
HAVING COUNT(o.owner_team) <> 1;
```

`valid_to IS NULL` means current by contract. A uniqueness constraint or serialized
transition must prevent two current owners. The query detects catalog state only;
reconcile it with storage and job inventories.

### Python model

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class LineageEdge:
    run_id: str
    input_version: str
    output_version: str
    confidence: Literal["observed", "parsed", "asserted"]
    observed_at_utc: str

def missing_outputs(expected: set[str], edges: list[LineageEdge]) -> set[str]:
    return expected - {edge.output_version for edge in edges}
```

The caller owns collection and deduplication. Production ingestion needs bounded
batches, schema validation, idempotency by event identity, and durable replay.

## Lifecycle, consistency, identity, and architecture

A dataset progresses through proposed, registered, active, deprecated, and
retired states. Files and tables can be replaced while the logical dataset ID
remains stable; versions identify concrete snapshots. A rename must be an alias
or migration, not a new unrelated object. Lineage is eventually complete unless
the platform provides an atomic data-and-metadata commit, so consumers need a
staleness indicator.

Business owners define meaning and acceptable use; platform owners provide
collection, graph storage, search, and enforcement hooks. Policy consumes catalog
metadata but should fail safely when required attributes are missing.

## Failure model and recovery

| Failure | Detection and containment | Recovery owner and convergence evidence |
| --- | --- | --- |
| Owner team renamed/deleted | Identity-directory reconciliation | Governance owner assigns successor; no orphan remains |
| Lineage event lost/duplicated | Sequence/idempotency checks and run comparison | Platform replays; graph matches execution receipts |
| Parser infers wrong columns | Confidence flag and owner review | Correct with superseding edge; impact analysis rerun |
| Shadow table/export appears | Storage/query inventory discrepancy | Dataset owner classifies, governs, or removes it |
| Catalog unavailable | Cached deny-safe policy; stop risky change | Platform restores and replays backlog; freshness returns |
| Catalog backup is stale | Restore drill and graph counts | Reingest authoritative declarations/events and reconcile |

## Security, privacy, and governance

Metadata can expose names, schemas, locations, business plans, and relationships.
Classify the catalog itself; separate search visibility from data access; redact
sensitive samples; protect write APIs; and audit classification, ownership, and
lineage corrections. Catalog membership never grants access by itself.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Command or procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Registration contract | Deterministic metadata fixture | Planned schema tests | Missing owner/class/purpose rejected | Pending |
| Graph reconciliation | Fixture jobs and datasets | Planned lineage comparison | Missing, duplicate, stale edges identified | Pending |
| Inventory comparison | Real test storage/catalog | Planned integration scan | Undeclared and dangling assets surfaced | Pending |
| Restore | Catalog test service | Planned backup/restore drill | Declarations and edges converge | Pending |

## Debugging guide

Start from affected dataset/version and consumer. Inspect registration history,
owner directory, schema ID, run ID, input/output versions, lineage confidence,
collector lag, rejected events, and storage inventory. Preserve the original
events before repairing derived graph state. Recovery is complete only when the
graph, inventory, owner approval, and affected policy/impact results agree.

## Common pitfalls

### Pitfall: call the platform team the data owner

The custodian cannot decide business meaning or acceptable use. Assign a domain
owner and make platform responsibilities explicit.

### Pitfall: treat inferred lineage as fact

SQL parsing can miss dynamic SQL, procedures, files, and runtime branches. Store
provenance and confidence, then reconcile critical paths with observed reads and writes.

### Pitfall: optimize catalog field completeness instead of decisions

Teams stop registering data when every optional field blocks publication. Gate a
small required contract; measure and improve the rest by risk.

## Performance, observability, and cost

Measure registration freshness, unowned/unclassified production datasets,
lineage-event acceptance and lag, graph size, search latency, rejected metadata,
storage discrepancies, and owner-review age. Bound labels by dataset/team, not
run or user. Costs include collectors, graph indexes, retention, scanning, and
human stewardship; sample low-risk column lineage only with an explicit gap.

## Compatibility, migration, and delivery

Version the metadata/event schema and policy-required fields. Support mixed
producers with additive fields, backfill from authoritative inventories, compare
old/new graphs, then move enforcement from observe to warn to deny. Preserve old
dataset aliases and lineage. Rollback the consumer before removing new metadata;
never roll back by deleting audit history.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Central catalog | Shared search/control vocabulary matters | Central bottleneck | Domains require autonomous operation |
| Federated metadata | Domains own semantics and delivery | Inconsistent minimums | Cross-domain policy cannot be evaluated |
| Runtime lineage | High confidence on critical paths | Instrumentation/load | Engine cannot emit complete events |
| Parsed lineage | Quick broad coverage | False/missing edges | Decisions require proof |

## Working example

- Metadata and lineage model: Planned under `src/big_data_example/governance/`
- Tests: Planned registration, idempotency, graph, inventory, and restore cases
- Try it: Planned deterministic event replay followed by catalog reconciliation
- Expected result: Orphan and missing-lineage states remain visible and cannot certify policy
- Scale represented: Local fixture plus production estimate; no catalog executed
- Remaining risk: Cross-engine completeness, authorization coupling, graph cost, and organizational ownership

## Knowledge check

1. Explain why catalog, ownership, and lineage are different guarantees.
2. Predict the graph after a duplicate event and a dataset rename.
3. Diagnose a table with an owner label but no reachable team.
4. Design a deny-safe response to stale classification metadata.
5. Estimate monthly lineage events from the starting assumptions.
6. Plan an old/new lineage schema migration and rollback.
7. Add one inventory reconciliation rule and its completion evidence.

## Key takeaways

- Ownership is decision accountability; stewardship and custody are distinct work.
- Metadata needs stable identities, history, provenance, confidence, and freshness.
- Catalog truth must be reconciled with observed storage and execution truth.
- Unknown lineage is a visible risk, never proof of absence.
- Start with metadata that drives decisions, then deepen it by risk.

## Resources

- [OpenLineage specification](https://openlineage.io/docs/spec/) (reviewed 2026-09; implementation versions must be pinned)
- [OpenLineage facets and extensibility](https://openlineage.io/docs/spec/facets/) (reviewed 2026-09)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) (reviewed 2026-09; version 1.1 remained an initial public draft)

## Related topics

- [Classification and purpose](02-classification-personal-data-and-purpose-limitation.md)
- [Audit and policy evidence](07-audit-policy-enforcement-and-compliance-evidence.md)
- [Area 12 metadata and lineage](../12-workflow-orchestration-and-transformation-management/07-metadata-lineage-artifacts-and-data-aware-scheduling.md)

## Completion checklist

- [x] Ownership, stewardship, catalog, lineage, identity, lifecycle, failure, security, scale, and migration covered
- [x] SQL/Python models and planned evidence supplied
- [x] Working example accurately marked Planned
- [ ] Catalog, lineage, inventory, policy-coupling, scale, and restore evidence executed

