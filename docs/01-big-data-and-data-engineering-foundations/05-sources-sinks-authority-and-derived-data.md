# Sources, Sinks, Authority, and Derived Data

> Status: Documentation complete  
> Level: Beginner  
> Applies to: Generic data engineering / Batch / Streaming / Storage / Platform  
> Data scale: Local fixture through production estimate  
> Example status: Complete lineage and authority walkthrough  
> Evidence status: Contract / Boundary review  
> Last reviewed: 2026-09

## Overview

A source produces data for a flow; a sink receives it. Those words describe an
edge, not authority. A warehouse can be a sink for ingestion and a source for a
dashboard. A system of record is authoritative for a specific fact under a
specific contract. Derived tables, materialized views, indexes, caches, and
exports reproduce or reinterpret facts and need lineage, lifecycle, and owners.

This guide prevents two costly mistakes: treating every upstream copy as truth,
and treating every derived copy as disposable. It does not prescribe one global
database or forbid fit-for-purpose serving copies.

## Learning objectives

After completing this guide, you should be able to:

- State source, sink, grain, authority, and owner at each edge.
- Distinguish authoritative observations from authoritative interpretations.
- Model lineage and consumer contracts for derived datasets.
- Define idempotent copy, replay, correction, and deletion behavior.
- Evaluate source-of-truth, cache, index, event, and snapshot tradeoffs.

## Prerequisites

Read [Data lifecycle, control plane, and data plane](02-data-lifecycle-control-plane-and-data-plane.md)
and [OLTP, OLAP, batch, streaming, and serving](04-oltp-olap-batch-streaming-and-serving.md).

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Source | Upstream endpoint for one data-flow edge |
| Sink | Downstream endpoint for one data-flow edge |
| System of record | Authoritative system for a defined fact and lifecycle |
| Derived data | Data computed, copied, indexed, aggregated, or reinterpreted from other data |
| Grain | What exactly one record represents at a named boundary |
| Provenance | Origin and relevant history of a data value or dataset |
| Consumer contract | Meaning, structure, service, compatibility, and use guarantees offered to consumers |

## Requirements, scale assumptions, and invariants

The app emits an observation, ingestion retains accepted observations, and a
daily aggregate publishes counts by `event_date`, `screen_name`, and
`app_version`. Product consumers require the count by 09:00, traceable to a
versioned input cutoff and transform. Raw data is retained 30 days; curated
retention and export policy must be explicit.

Invariants:

- Authority is stated per fact; no store is universally authoritative.
- Each dataset has one declared grain and stable record identity or key.
- Derived data can be traced to versioned inputs and logic.
- Rebuilding a derived dataset from the same inputs and logic converges to the
  same logical result.
- Consumers never depend on staging locations or undocumented internal columns.
- Corrections and deletion propagate to obligated copies with auditable status.

## Mental model

```text
Observed fact                 Accepted fact                 Interpreted fact
Android event  ------------> raw accepted event ----------> daily screen count
producer authority            ingestion authority           metric/data-product authority
       |                              |                              |
       + event_id                     + receipt + raw version        + key + logic version
                                      \________ lineage _____________/
```

A Room entity and a UI view model provide a limited analogy: the database can
own persisted app state while the view model derives display state. The analogy
stops because analytical copies may be independently retained, exported,
backfilled, queried by many unknown consumers, and rebuilt with later logic.

## Data flow, ownership, and trust boundaries

| Dataset/edge | Grain and identity | Authority and owner | Failure behavior | Trust/access |
| --- | --- | --- | --- | --- |
| App event | One observed view; `event_id` | Mobile producer owns observation semantics | Retry same identity; bounded local retention | External/untrusted input |
| Raw accepted event | One durable accepted envelope; `event_id` plus receipt | Ingestion owner owns receipt fact | Immutable append/quarantine; reconcile acknowledgements | Restricted raw |
| Validated event | One accepted event meeting rule version | Pipeline owner owns validation result | Preserve rejection reason safely; rerunnable | Governed processing |
| Daily screen count | One date/screen/version aggregate key | Data product owner owns analytical definition | Atomic version publish; repair from raw | Purpose-limited curated |
| Dashboard cache/export | One consumer-specific projection/version | Consumer/serving owner | Expire/invalidate on correction or policy | Narrow consumer boundary |

The app is not authoritative for durable receipt; raw storage is not
authoritative for the daily metric definition; the dashboard cache is not
authoritative for either.

## Consumer contracts

A useful dataset contract states:

1. Grain, keys, field meanings, units, nullability, and time zone.
2. Source authority, lineage, transformation version, and known exclusions.
3. Freshness cutoff, availability, late-data correction, and retention behavior.
4. Compatibility and deprecation process.
5. Classification, permitted uses, access, deletion, and audit expectations.
6. Quality checks, incident owner, and consumer communication channel.

Schemas are necessary but insufficient. A string can validate structurally while
changing from a route name to a localized screen title and breaking semantics.

## Record and dataset lifecycle

Source facts are created and accepted with stable IDs. Raw versions are immutable
within retention. Derived outputs are staged, validated, and atomically published
with lineage. A correction produces a new version and invalidates or refreshes
dependent caches and exports. Expiration removes data by policy; deletion handles
specific obligated identities across all discoverable copies. Rebuilding uses
the original bounded input and pinned logic/configuration.

## Consistency, ordering, identity, and time

`event_id` identifies an observation; the aggregate key identifies a derived row.
Event time selects the reporting date; receipt time establishes arrival and
lateness; publication time marks visibility. The curated dataset is consistent
for its declared input version, not necessarily with source events still in
flight. Lineage must preserve these distinctions.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Proof |
| --- | --- | --- | --- |
| Duplicate delivery | Duplicate identity/rate check | Idempotently retain/deduplicate in declared scope | Unique accepted identities and reconciled counts |
| Source deletes/changes history | Snapshot/change contract violation | Preserve authorized immutable history or process deletion | Source-versus-raw reconciliation |
| Derived logic defect | Consumer anomaly/reconciliation | Hold publication, fix versioned logic, backfill | Old/new diff and approved totals |
| Stale cache after repair | Version mismatch | Invalidate or version cache keys | Consumer reads corrected version |
| Unknown export | Catalog/access audit | Restrict, assign owner, migrate or delete | All dependencies accounted for |
| Lineage unavailable | Missing metadata alert | Stop risky repair/cutover; restore lineage | Input/output versions traceable |

## Security, privacy, and governance

Copies expand exposure. Minimize fields at each consumer boundary; use opaque
identifiers; apply least privilege, encryption, purpose restrictions, retention,
and audit independently to raw, curated, quarantine, cache, export, lineage, and
backup locations. “Derived” does not mean anonymous: aggregates and joined values
can remain sensitive. Provenance supports governance but can itself reveal paths,
identifiers, and operational details.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Authority review | Shared paper scenario | Assign fact, grain, identity, owner, and consumers per dataset | No universal or ambiguous source of truth | Passed; documented above |
| Lineage review | Raw-to-dashboard path | Trace aggregate back to raw/input and logic versions | Correction scope is discoverable | Passed by design; not executed |
| Rebuild/reconciliation test | Deterministic fixture and engine | Publish twice and compare identities/totals | Same logical result; no duplicates | Pending |
| Deletion propagation test | Safe synthetic identity | Delete across derived copies and backups per policy | Auditable completion | Pending |

## Debugging guide

Start from the incorrect consumer value and record dataset/version, aggregate key,
freshness cutoff, and transformation version. Traverse lineage backward to input
manifest and source identities. Compare counts at each boundary: produced if
available, accepted, valid, rejected, deduplicated, aggregated, published, and
served. Inspect cache/version mismatch and undocumented exports. Repair from the
nearest authoritative retained boundary and reconcile forward.

## Common pitfalls

### Pitfall: calling the lake or warehouse the source of truth

Name the fact. It may be authoritative for accepted history or a governed metric,
but not for the source transaction or producer intent.

### Pitfall: treating a cache as disposable without a rebuild contract

If consumers require it and rebuild takes longer than the recovery objective, it
is operationally important derived state. Own, observe, and test restoration.

### Pitfall: schema-only contracts

Types do not protect grain, units, time interpretation, allowed use, or business
meaning. Version semantic changes and notify consumers.

## Performance, capacity, cost, and operations

Copies trade storage and lifecycle cost for isolation and access speed. Record
size, row count, file count, retention, refresh frequency, query concurrency,
rebuild duration, dependency fan-out, and egress. Track reconciliation deltas,
lineage completeness, stale-version reads, cache hit/age, rejected/duplicate
rates, and deletion backlog. Budget for a full rebuild inside the recovery window.

## Compatibility, migration, backfill, and delivery

Use versioned contracts and expand/migrate/contract. Create the new derived
dataset beside the old one, backfill from a pinned authoritative input, compare
keys/counts/semantics, migrate consumers, and then retire the old copy after its
rollback and retention window. Dual writes require reconciliation and should not
create two competing authorities.

## Engineering tradeoffs

| Choice | Prefer when | Benefit | Risk |
| --- | --- | --- | --- |
| Recompute derived data | Inputs and logic are retained; recovery fits objective | Simple authority and correction | Compute/time cost |
| Persist derived data | Query or rebuild cost is high | Fast serving and reproducibility | More lifecycle and consistency work |
| Read source directly | Small controlled operational use | Minimal copy latency | Coupling, load, weak history |
| Publish contract dataset | Multiple analytical consumers | Isolation and stable meaning | Storage and stewardship cost |

## Working example

The authority and lineage tables are complete conceptual evidence. Executable
rebuild, reconciliation, and deletion workflows are planned in later areas.

## Knowledge check

1. For each shared-scenario dataset, state one fact it is and is not authoritative for.
2. Predict what happens if a dashboard caches rows without the dataset version.
3. Diagnose a count mismatch by ordering the boundaries you would reconcile.
4. Design a contract for a second consumer that needs hourly counts.
5. Plan migration from localized `screen_name` values to stable route identifiers.

## Key takeaways

- Source and sink are edge-relative; authority is fact-specific.
- Every record and dataset needs declared grain, identity, owner, and consumers.
- Derived data requires lineage, operation, security, retention, and recovery.
- A schema cannot express the whole consumer contract.
- Corrections converge only when dependent copies are discoverable and reconciled.

## Resources

- [W3C PROV overview](https://www.w3.org/TR/prov-overview/)
- [OpenLineage specification](https://openlineage.io/docs/spec/)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)

## Related topics

- [Data lifecycle, control plane, and data plane](02-data-lifecycle-control-plane-and-data-plane.md)
- [Data architecture patterns and trust boundaries](07-data-architecture-patterns-and-trust-boundaries.md)
- [First end-to-end data pipeline](08-first-end-to-end-data-pipeline.md)

## Completion checklist

- [x] Source, sink, authority, grain, identity, lineage, and contract explained
- [x] Owners, consumers, trust, time, consistency, correction, and deletion modeled
- [x] Failure, recovery, security, capacity, observability, and migration addressed
- [x] Boundary evidence distinguished from pending executable proof
- [ ] Rebuild, reconciliation, cache invalidation, and deletion executed

