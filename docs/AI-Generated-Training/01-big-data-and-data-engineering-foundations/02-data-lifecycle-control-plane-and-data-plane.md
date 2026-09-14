# Data Lifecycle, Control Plane, and Data Plane

> Status: Documentation complete  
> Level: Beginner  
> Applies to: Generic data engineering / Batch / Streaming / Storage / Platform  
> Data scale: Local fixture through distributed production estimate  
> Example status: Complete conceptual walkthrough  
> Evidence status: Diagram / Boundary review  
> Last reviewed: 2026-09

## Overview

A data lifecycle follows records from creation through ingestion, storage,
processing, publication, use, correction, retention, and deletion. The data
plane carries or computes the records. The control plane decides how that work
runs: schemas, catalog entries, policies, schedules, topology, checkpoints,
permissions, configuration, and deployment state.

This distinction helps locate failures. A valid record can be stranded by a bad
schedule; a healthy scheduler can run a transformation over incomplete input.
Specific products often combine both planes, so the boundary is conceptual
rather than necessarily a network or service boundary.

## Learning objectives

After completing this guide, you should be able to:

- Trace a record and dataset through creation, publication, correction, and deletion.
- Classify components and failures as data-plane, control-plane, or cross-plane.
- Identify commit, acknowledgement, checkpoint, and consumer-visibility boundaries.
- Explain metadata authority and why catalogs do not automatically make data correct.
- Design recovery that converges after retries and partial failure.

## Prerequisites

Read [Data engineering landscape and roles](01-data-engineering-landscape-and-roles.md).
No runtime infrastructure is required.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Data plane | Paths and compute that transport, store, transform, or serve records |
| Control plane | Configuration and metadata that admit, coordinate, secure, and observe data-plane work |
| Metadata | Data describing schemas, owners, locations, lineage, runs, policies, or quality |
| Commit boundary | Point after which an output or state transition is durably accepted and visible by contract |
| Checkpoint | Durable progress state used to resume without intentionally starting over |
| Lineage | Recorded relationship from output data and logic back to inputs and versions |

## Requirements, scale assumptions, and invariants

Use the shared estimate of 3 million events and roughly 3 GiB raw data per day.
Assume daily curated output, raw retention for 30 days, and a dashboard freshness
target of 09:00 local business time. These requirements are illustrative.

Invariants:

- Acknowledgement means exactly the documented durable boundary, not merely that
  a process saw the request.
- Raw accepted events remain replayable throughout their retention window.
- A published dataset identifies input cutoff, schema, transformation version,
  and quality outcome.
- Control-plane loss cannot silently redefine previously published data.
- Deletion and retention cover data plus metadata that may expose sensitive values.

## Mental model

```text
CONTROL PLANE
schema + catalog + policy + schedule + deployment + lineage + quality rules
   |          |          |          |             |              |
   v          v          v          v             v              v
DATA PLANE
producer -> collect -> raw -> validate/transform -> curated -> serve -> consume
                A          B                    C          D
              accept    raw commit          publish    query/read
```

The letters are distinct boundaries. If collection acknowledges at A before the
raw commit at B, a crash between them can lose an acknowledged event. If output
files exist before atomic publication at C, consumers must not discover them as
a complete dataset.

Gradle offers a partial analogy: build configuration and the task graph resemble
a control plane, while compiler and packaging processes resemble a data plane.
The analogy stops because production data planes are long-lived, stateful, and
may continue under an older control-plane decision during partitions.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Producer/collector | Versioned event envelope | Producer owns observation; ingestion owns receipt | Authenticate, validate bounds, acknowledge only defined durability | External/untrusted |
| Collector/raw store | Accepted event plus receipt metadata | Raw dataset owner | Idempotent append or quarantine; never silently drop | Restricted raw |
| Raw/transform | Immutable dataset version and cutoff | Pipeline owner | Stop or isolate bad partition; retain retry state | Validated structure |
| Transform/curated | Staged output plus quality report | Curated owner | Publish atomically only after checks | Governed internal |
| Curated/consumer | Dataset contract and freshness marker | Consumer-facing product owner | Serve last known good version with explicit staleness | Purpose-limited |
| Operator/control API | Authenticated desired state | Platform owner | Audit, authorize, reconcile, and roll back | Privileged |

Raw is authoritative for accepted inputs; catalog metadata is authoritative for
approved identity and location; a scheduler is authoritative for run state, not
for business correctness.

## Lifecycle walkthrough

1. The app creates an event with `event_id` and UTC `event_time`.
2. Collection authenticates the client context, checks size and schema version,
   adds server receipt time, and durably accepts or explicitly rejects it.
3. Immutable raw storage groups accepted events into a dataset version. A
   manifest or transactional metadata record marks completeness.
4. Validation separates structurally valid, semantically valid, and quarantined
   records without overwriting the raw source.
5. Transformation computes a daily screen grain from a bounded input interval.
6. Quality checks reconcile counts and required fields. Publication changes one
   pointer or transaction so consumers see either the old or new complete version.
7. Consumers read the version and its freshness state. Lineage connects the
   displayed number to input and code versions.
8. Corrections create a new version; they do not rewrite history invisibly.
9. Retention expires eligible raw and derived data; deletion workflows find
   applicable copies, exports, indexes, and backups according to policy.

## Consistency, ordering, identity, and time

`event_id` is the deduplication identity. Event time describes the observation;
receipt time describes arrival; publication time describes consumer visibility.
No global arrival ordering is assumed. The daily dataset is snapshot-consistent
at its declared input cutoff, but can exclude late events until a later repair.
Consumers must not infer exactly-once production merely because curated rows are
deduplicated.

## Architecture and dependency direction

Data flows toward consumers; contracts and feedback flow both ways. Processing
depends on immutable inputs and versioned metadata. Consumers depend on a
published contract, not staging paths or scheduler internals. The catalog points
to governed datasets but does not become a second mutable source of business
facts.

## Failure model and recovery

| Failure | Detection | Containment | Recovery and convergence evidence |
| --- | --- | --- | --- |
| Crash before durable acceptance | Client timeout; missing receipt | Client retains bounded retry state | Retry same `event_id`; one accepted raw identity |
| Raw file exists but manifest does not | Orphan scan | Readers ignore uncommitted object | Resume/finalize or expire orphan |
| Schema registry unavailable | Control-plane health | Continue only with safely cached compatible rules; otherwise reject/defer | Audit version used; reconcile deferred input |
| Transformation writes partial output | Run and publication state differ | Consumers remain on old version | Discard/reuse safe staging; republish atomically |
| Catalog unavailable | Lookup/authorization error | Do not bypass policy with guessed paths | Restore metadata, verify identity and permissions |
| Late event after daily cutoff | Late-arrival metric | Keep in raw; flag affected interval | Recompute interval and reconcile version totals |
| Deletion workflow partially fails | Per-copy deletion ledger | Restrict affected data | Retry idempotently; prove all obligated copies handled |

Retry ownership belongs to the component that can determine whether its side
effect committed. A caller that cannot distinguish success from timeout must
reuse stable identity rather than invent a new event.

## Security, privacy, and governance

The control plane is high impact: changing permissions, retention, schema, or
publication pointers can expose or corrupt large datasets. Require strong
workload identity, least privilege, change audit, separated production roles,
and secret rotation. Keep raw identifiers out of logs and metric labels. Treat
catalog descriptions, lineage parameters, quarantines, and checkpoints according
to the sensitivity of the data they describe.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Lifecycle diagram review | Shared scenario / paper design | Trace create through delete and mark authority/commit points | Every transition and owner is explicit | Passed; documented above |
| Partial-publication review | Paper failure scenario | Fail between staging and publish | Consumers remain on prior complete version | Passed by design; not executed |
| Runtime fault injection | Real storage/scheduler | Interrupt acceptance, manifest, catalog, and publication | Recovery converges without silent loss | Pending |

Conceptual review finds ambiguous contracts; it cannot validate real storage
atomicity, cached-control behavior, or concurrent writers.

## Debugging guide

1. Record consumer symptom, expected dataset version, and freshness cutoff.
2. Follow lineage backward through publication ID, run ID, input manifest, and
   source receipt or event ID.
3. Compare control-plane desired state with data-plane observed state.
4. Inspect rejection/quarantine counts, object manifests, checkpoints, run
   attempts, authorization decisions, and schema versions.
5. Mitigate by holding publication or serving the last known good version.
6. Replay only from an authoritative durable boundary, then reconcile identities,
   counts, and consumer output.

## Common pitfalls

### Pitfall: control plane equals metadata database

The control plane includes decisions and reconciliation behavior, not just a
database. If agents continue with cached configuration, restoring the database
alone may not restore a consistent system.

### Pitfall: existence equals publication

Part files in storage do not prove completeness. Readers need a transaction,
manifest, immutable version pointer, or another explicit publication protocol.

### Pitfall: deletion means removing the curated table

Derived copies, caches, exports, quarantines, logs, indexes, and backups may
remain. Track lineage and policy-specific lifecycle for each copy.

## Performance, capacity, cost, and operations

At the estimate above, 30-day uncompressed raw retention is about 90 GiB before
replication, metadata, rejects, and derived datasets. Measure compression rather
than assuming a ratio. Control-plane operations are lower volume but often
latency- and availability-sensitive. Track accepted/rejected events, commit
latency, manifest age, run state, input/output reconciliation, publication age,
catalog errors, and deletion backlog with bounded-cardinality dimensions.

## Compatibility, migration, backfill, and delivery

Schema and policy changes must declare effective versions. During migration,
readers may observe old data produced under old rules while new data uses new
rules. Preserve the relevant control-plane snapshot with lineage. Backfills use
bounded immutable input versions, isolated staging, quality comparison, atomic
cutover, and a rollback pointer where retention allows.

## Engineering tradeoffs

| Choice | Benefit | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Central control plane | Consistency and visibility | Large blast radius | Domains require isolation or disconnected operation |
| Immutable versions plus pointer | Simple rollback and reader isolation | Extra storage and cleanup | Write frequency or object count overwhelms metadata |
| In-place mutation | Low apparent storage cost | Ambiguous readers and recovery | Prefer only with transactional storage and required semantics |
| Cached control state | Data-plane continuity | Temporary stale policy/configuration | Safety requires fail-closed behavior |

## Working example

The lifecycle diagram and failure table are complete conceptual evidence. A
local executable implementation and integration fault tests are planned for the
storage, ingestion, and batch-processing areas.

## Knowledge check

1. Classify schema registration, file upload, task scheduling, query execution,
   authorization, and lineage emission by plane; explain ambiguous cases.
2. Predict what a consumer sees when a job writes three of four files and fails
   before the manifest commit.
3. Diagnose an acknowledged event missing from raw storage by enumerating commit
   points and evidence.
4. Design a backfill that preserves the original output until validation passes.
5. Add deletion to the lifecycle and list every state that requires proof.

## Key takeaways

- The data plane handles records; the control plane governs and coordinates work.
- Acknowledgement, commit, checkpoint, and publication are different boundaries.
- Files existing is not the same as a complete dataset being visible.
- Metadata needs ownership, security, versioning, recovery, and observability.
- Recovery is proven by reconciliation at the consumer-visible boundary.

## Resources

- [Kubernetes documentation: Controllers](https://kubernetes.io/docs/concepts/architecture/controller/)
- [Apache Iceberg specification](https://iceberg.apache.org/spec/)
- [OpenLineage specification](https://openlineage.io/docs/spec/)

## Related topics

- [Data engineering landscape and roles](01-data-engineering-landscape-and-roles.md)
- [Sources, sinks, authority, and derived data](05-sources-sinks-authority-and-derived-data.md)
- [First end-to-end data pipeline](08-first-end-to-end-data-pipeline.md)

## Completion checklist

- [x] Lifecycle, planes, metadata, and commit boundaries explained
- [x] Owners, trust, identity, time, consistency, and deletion addressed
- [x] Partial failure, retry, replay, publication, and recovery modeled
- [x] Security, observability, scale, compatibility, and cost included
- [x] Conceptual evidence and remaining runtime evidence distinguished
- [ ] Real-engine atomicity and fault behavior verified
