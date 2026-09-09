# ETL, ELT, Staging, and Layer Responsibilities

> Status: Documentation complete; executable evidence planned  
> Level: Beginner  
> Applies to: Generic data engineering / Python / SQL / Batch / Storage  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

ETL transforms before loading into the main analytical store; ELT loads retained
source-shaped data first and transforms inside that store. The durable decision
is not the acronym. It is which boundary owns each transformation, which input is
replayable, where untrusted data becomes trusted, and how consumers avoid partial
or semantically mixed results.

This guide defines technology-neutral raw, staging, canonical, curated, and
serving responsibilities. It excludes detailed file loops, SQL optimization,
incremental selection, and orchestration, which follow in later guides.

## Learning objectives

- Compare ETL, ELT, and hybrid designs using contracts rather than product labels.
- Assign authority, grain, retention, validation, and recovery to each layer.
- Separate private run staging from published datasets.
- Trace data and control flow without treating a layer name as a guarantee.
- Choose a transform location based on security, scale, cost, and engine behavior.

## Prerequisites

- Areas 01 through 06, especially raw ownership, file publication, SQL grain, and data-product semantics

## Mental model and terminology

Think of layers as trust and ownership transitions, not colored folders. An
Android clean-architecture comparison can clarify dependency direction: source
DTOs are normalized before domain-facing models. It stops because analytical
layers are durable, independently queried datasets; they are not merely in-memory
objects hidden behind one application boundary.

| Term | Meaning in this guide |
| --- | --- |
| ETL | Extract, transform under a processing boundary, then load a consumer-facing store |
| ELT | Extract and load retained source-shaped data, then transform in the target analytical engine |
| Staging | Run-scoped, non-authoritative workspace not visible as certified output |
| Canonical | Versioned, normalized representation that preserves declared source meaning |
| Curated | Consumer-oriented data with explicit business grain and semantics |
| Serving | Interface optimized for a consumer workload, often derived again |
| Certification | Evidence-backed decision that a named dataset version may be consumed |

## Requirements, assumptions, and invariants

The reference pipeline consumes immutable accepted events plus a versioned
product snapshot and publishes daily facts and metrics. Assume 3M events/day,
256 KiB maximum accepted record size, 35-day hot replay, and a 02:00 UTC daily
deadline. Measure actual row widths, skew, data classifications, and engine cost
before choosing placement.

Invariants:

- Every published record traces to immutable input identities and transform versions.
- Run staging is isolated by run and cannot be mistaken for certified output.
- Canonicalization does not silently invent business truth absent from the producer contract.
- Curated output has one documented grain, key, time basis, and semantic version.
- Consumers observe one certified version, not a mixture of old and new partitions.
- Moving a transform between engines does not silently change null, time, numeric, ordering, or duplicate semantics.

## Data flow, ownership, and trust boundaries

| Boundary | Contract and owner | Failure behavior | Trust level |
| --- | --- | --- | --- |
| Accepted raw | Immutable receipt-linked input; ingestion owner | Replay without source reacquisition | Structurally accepted, semantically untrusted |
| Run staging | Exact selected scope plus intermediate state; batch runtime | Delete only after terminal disposition and retention | Private and uncertified |
| Canonical events | Normalized event grain; canonical product owner | Versioned rebuild from raw | Trusted for declared source semantics |
| Curated facts/metrics | Business grain and definitions; domain data owner | Block or replace version on failed quality | Certified for named use |
| Serving/export | Consumer-specific layout; consumer/interface owner | Rebuild or compensate under consumer contract | Fit only for declared consumers |

Raw remains authoritative evidence of received input. Product source data remains
authoritative for product meaning. Canonical and curated datasets are derived
authorities only for their declared contracts.

## Transform placement and smallest correct design

```text
ETL: source -> bounded extraction -> transform runtime -> target publication
ELT: source -> retained target landing -> target-engine SQL -> publication
hybrid: source -> security/shape gate -> retained landing -> SQL/Python transforms
```

Use ETL when bytes must be filtered or tokenized before reaching a target,
specialized parsing is required, or target compute is unsuitable. Use ELT when
the analytical engine can expose set-based logic, transactions, lineage, and
elastic compute close to the data. A hybrid is common: minimally validate and
protect the landing boundary, then perform relational transformations in place.

```sql
-- Generic SQL sketch; the transaction and replacement syntax are engine-specific.
CREATE TABLE run_stage.canonical_event AS
SELECT tenant_id, producer_id, event_id,
       CAST(event_time AS TIMESTAMP) AS event_time_utc,
       product_id, event_type
FROM accepted_raw.event
WHERE input_batch_id = :input_batch_id;
```

The query is correct only after declaring input uniqueness, timestamp conversion,
invalid-cast behavior, and target constraints. `CREATE TABLE AS` materializes a
private candidate; it is not publication by itself.

## Layer decision table

| Requirement or constraint | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Sensitive fields must never enter warehouse | Pre-load transform/tokenization | Enforces trust boundary | Approved isolated warehouse zone can enforce equivalent controls |
| Large relational joins and aggregates | ELT near target tables | Optimizer sees sets and avoids extraction copies | Target concurrency or scan cost violates budget |
| Complex binary parsing | ETL in bounded application/engine | Better parser and resource controls | Target supplies equivalent safe native support |
| Reproducible source-shaped history | Immutable landing before business transforms | Enables replay and comparison | Law or policy forbids retaining the field/payload |
| Multiple consumers need stable normalized meaning | Canonical layer | Centralizes source semantics | It becomes a lowest-common-denominator dumping ground |
| One consumer needs special latency/layout | Serving derivative | Isolates consumer optimization | It duplicates business definitions without governance |

## Lifecycle, consistency, identity, and time

A run discovers a closed input version, creates an isolated stage, validates and
transforms it, records quality and lineage, publishes a new dataset version, then
retires staging after its diagnostic retention. Temporary data belongs to the run;
published data belongs to the dataset owner.

Keep event time, ingestion time, source-effective time, batch processing time,
and publication time distinct. Use source-scoped event identity before assigning
warehouse surrogate keys. A canonical record may be unique while a curated fact
legitimately has a different grain; document the mapping and reconciliation.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Transform fails midway | Run state incomplete; no certification | Keep staging private; fix or retry from pinned inputs |
| Layer receives mixed input versions | Manifest/version mismatch | Reject run and rebuild one coherent scope |
| Engine migration changes semantics | Old/new comparison differs | Classify expected deltas; block unexplained changes |
| Invalid record enters curated data | Quality gate/reconciliation fails | Quarantine or repair from canonical/raw; publish new version |
| Staging leaks to consumers | Access audit or unregistered read | Revoke access, identify exposure, enforce certified aliases/views |
| Canonical layer becomes source of truth | Source reconciliation diverges | Restore authority boundary and versioned derivation |

## Security, privacy, and governance

Apply least privilege per layer; transformation workers need no broad consumer
write access, and consumers need no staging access. Minimize or tokenize sensitive
fields before crossing prohibited boundaries. Carry classification, purpose,
retention, lineage, and deletion obligations into every derivative. Logs, samples,
rejected records, and temporary tables are data copies subject to the same policy.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Boundary contract review | Trace fields, owner, grain, and trust at every layer | No ambiguous authority or hidden copy | Pending |
| ETL/ELT equivalence fixture | Run both implementations on pinned input | Same declared result and dispositions | Pending |
| Semantic mutation matrix | Null, time-zone, decimal, duplicate, invalid value | Differences are prevented or versioned | Pending |
| Isolation test | Query while candidate build fails | Only prior certified version is visible | Pending |
| Deletion-lineage test | Erase one subject/key | Every governed derivative is found and handled | Pending |

Local fixtures cannot prove target-engine transactions, storage authorization, or
production cost. Real engine and access-control integration remain required.

## Common pitfalls

### Pitfall: naming folders bronze, silver, and gold without contracts

Colors do not define authority, validation, or visibility. State the grain,
owner, entry criteria, exit guarantee, and recovery path for each boundary.

### Pitfall: treating ELT as an excuse to load unsafe data everywhere

Landing first does not remove trust, privacy, size, or parser controls. Isolate and
minimize before a payload reaches systems or users that may not possess it.

### Pitfall: exposing staging as a convenience table

Consumers then observe partial, retry-specific, or incompatible state. Publish a
certified version or stable view only after gates pass.

## Performance, operations, compatibility, and tradeoffs

Measure bytes crossing boundaries, scan bytes, row widths, intermediate size,
shuffle/spill, database log growth, warehouse credits, staging retention, and
end-to-end critical-path time. Track rows/bytes by layer and disposition, quality
gate duration, candidate age, publication version, and input-to-output lineage.

Move transformations with expand/migrate/contract: pin common inputs, dual-run old
and new paths, compare results, publish a new semantic version when behavior
changes, migrate consumers, then retire the old path. Preserve rollback output and
avoid dual writes without reconciliation.

## Working example

- Python/SQL/data/tests: planned layer contract, equivalent transforms, isolated stage, and quality gates
- Expected result: ETL and ELT candidates agree for the declared semantics and failed candidates remain invisible
- Scale represented: none yet; local fixture planned
- Remaining risk: cross-engine semantics, real authorization, target contention, and production cost

## Knowledge check

1. Assign grain and authority to raw, canonical, curated, and serving data.
2. Predict what a consumer sees when an ELT statement fails after staging half its work.
3. Diagnose why a shared staging schema can mix two concurrent runs.
4. Choose ETL, ELT, or hybrid for payment data requiring tokenization before analytics.
5. Design an old/new engine equivalence test for nulls, decimals, and timestamps.
6. Add a deletion requirement and trace the affected temporary and published copies.

## Key takeaways

- ETL versus ELT is a placement decision; contracts and commit boundaries determine correctness.
- Layers represent ownership, trust, grain, and lifecycle transitions.
- Staging is private run state, never an implicitly consumable dataset.
- Raw evidence and producer authority remain distinct from derived analytical authority.
- A transform move requires semantic equivalence evidence or an explicit version change.

## Resources

- [Python documentation: Data Formats](https://docs.python.org/3/library/fileformats.html) (reviewed 2026-09)
- [PostgreSQL documentation: CREATE TABLE AS](https://www.postgresql.org/docs/current/sql-createtableas.html) (reviewed 2026-09)
- [W3C PROV overview](https://www.w3.org/TR/prov-overview/) (reviewed 2026-09)

## Related topics

- [Python file pipelines and chunked processing](02-python-file-pipelines-and-chunked-processing.md)
- [SQL transformations and set-based pipelines](03-sql-transformations-and-set-based-pipelines.md)
- [Ingestion contracts and raw-data ownership](../06-data-ingestion-and-source-integration/01-ingestion-contracts-and-raw-data-ownership.md)

## Completion checklist

- [x] ETL, ELT, hybrid placement, layers, authority, and isolation explained
- [x] Grain, time, failure, security, quality, performance, migration, and evidence addressed
- [ ] Equivalence, isolation, access-control, and real-engine evidence run

