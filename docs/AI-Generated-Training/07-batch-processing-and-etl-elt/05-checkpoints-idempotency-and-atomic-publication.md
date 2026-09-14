# Checkpoints, Idempotency, and Atomic Publication

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic data engineering / Batch / SQL / Storage  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A checkpoint records durable processing progress. Idempotency makes repeating a
logical run converge on the same declared effect. Atomic publication makes a
complete dataset version visible without exposing its construction. These are
related but distinct guarantees: none automatically supplies the others.

This guide designs a run ledger, immutable candidates, validation gates, manifest
commit, and conditional progress advancement. Storage-specific transactions and
distributed task commit protocols require later integration evidence.

## Learning objectives

- Separate source checkpoint, run state, candidate output, and publication commit.
- Define idempotency identity and effect at each boundary.
- Design old-or-new consumer visibility for one- and multi-file datasets.
- Recover safely from crashes and unknown commit outcomes.
- Prove rerun convergence with manifests and reconciliation.

## Prerequisites

- [Full, incremental, and change-based processing](04-full-incremental-and-change-based-processing.md)
- Area 04 immutable publication and area 06 receipt/idempotency concepts

## Mental model and terminology

Treat a published dataset like an immutable application release: artifacts are
built under a unique version, verified, then a small pointer selects the active
release. The analogy helps with atomic cutover and rollback. It stops where
multiple data consumers may pin different snapshots, source progress has a
separate commit, and storage metadata may offer weaker concurrency guarantees.

| Term | Meaning in this guide |
| --- | --- |
| Source checkpoint | Highest closed input boundary durably reflected in certified output |
| Logical run ID | Stable identity derived from dataset, input scope, and transform/config version |
| Attempt ID | One execution attempt of a logical run |
| Candidate | Immutable output not yet selected for consumer visibility |
| Manifest | Versioned metadata naming all output objects, sizes, checksums, counts, and lineage |
| Publication pointer | Authoritative metadata selecting a certified manifest/version |
| Unknown outcome | Caller cannot tell whether a commit succeeded and must inspect durable state |

## Requirements, assumptions, and invariants

One daily version may contain multiple fact and metric files/partitions. Consumers
must see the prior complete version or the new complete version. Concurrent runs
for the same dataset/scope are possible. The normal input range is one day with a
seven-day correction window and 35-day retry/replay evidence.

Invariants:

- Logical run identity is stable across attempts and excludes attempt start time.
- Candidate object names are immutable and collision-safe.
- A manifest names only closed, validated objects and includes their integrity metadata.
- Publication uses a compare-and-set, transaction, or single-writer protocol with discoverable outcome.
- Source progress never advances beyond the input reflected in the active certified version.
- A retry either reuses verified candidates or creates a new attempt; it never appends blindly to final output.
- Consumers resolve one manifest/version per read contract.

## State and ownership model

```text
PLANNED -> RUNNING -> CANDIDATE_READY -> VALIDATED -> PUBLISHED
               |             |              |
             FAILED        FAILED         REJECTED

source checkpoint W0 -------- publish version V1 -------- checkpoint W1
```

The scheduler may request a run; the pipeline owner owns logical state and retry;
the writer owns candidates until closed; quality owners approve declared gates;
the publisher owns the authoritative pointer; consumers own how long they pin a
version. A scheduler's green task is not publication evidence.

## Manifest and run ledger sketch

```python
@dataclass(frozen=True)
class DatasetManifest:
    dataset: str
    version: str
    logical_run_id: str
    input_manifest_ids: tuple[str, ...]
    code_version: str
    config_version: str
    files: tuple[FileEntry, ...]  # path, bytes, rows, checksum, partition
    schema_fingerprint: str
```

The manifest must be serialized canonically if its digest is used as identity.
Do not put credentials or unnecessary personal data in it. A run ledger records
logical run, attempts, input lower/upper bounds, state transitions, candidate
manifest, gate results, publication version, checkpoint generation, timestamps,
and safe diagnostics.

```sql
-- Transactional metadata-store sketch.
UPDATE dataset_head
SET version = :new_version, generation = generation + 1
WHERE dataset = :dataset
  AND version = :expected_version
  AND generation = :expected_generation;
```

Exactly one updated row wins. Zero means conflict or prior success, so read the
head and manifest before deciding to retry. Object-store conditional writes or a
catalog transaction can provide an analogous primitive; plain overwrite does not.

## Commit sequence

1. Derive logical run ID from the pinned input scope and transform contract.
2. Register/read the run ledger and acquire only the required coordination lease.
3. Write immutable attempt-scoped candidates; close and compute integrity metadata.
4. Construct the complete manifest and run schema, quality, and reconciliation gates.
5. Publish the manifest/head conditionally against the expected prior generation.
6. Resolve unknown outcomes by reading the authoritative head and verifying identity.
7. Advance the source checkpoint conditionally to the published input upper bound.
8. Emit the terminal run record and later clean only unreferenced candidates.

Steps 5 and 7 may not share a transaction. If publication succeeds and checkpoint
advance fails, re-reading the range must be idempotent and recognize the existing
published logical run. Advancing checkpoint first is unsafe because the missing
output may become unreachable.

## Publication patterns

| Storage/requirement | Prefer | Limit |
| --- | --- | --- |
| One database transaction | Stage, validate, then swap/update metadata transactionally | Lock/log size and engine DDL semantics |
| Local same-filesystem single file | Closed temp file then atomic replace where documented | Not multi-file; durability and readers need proof |
| Object/multi-file dataset | Immutable objects plus manifest/catalog pointer commit | Conditional metadata and orphan cleanup required |
| Partition correction | New immutable partition set plus new dataset manifest | Consumers must pin manifest, not list directories |
| External side effects | Separate outbox/idempotency or compensating workflow | No universal transaction across destinations |

## Failure demonstration

A writer that creates `final/part-000`, `final/part-001`, and then crashes lets a
directory-listing consumer observe an incomplete dataset. Retrying may overwrite
some parts and mix attempts. The repair writes attempt-qualified immutable paths,
validates a manifest listing the complete set, and changes only the manifest head.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Complete when |
| --- | --- | --- | --- |
| Worker dies mid-candidate | Missing/invalid candidate manifest | Leave invisible; retry or clean after lease/retention | Certified head unchanged or new run publishes |
| Publish response lost | Caller sees timeout | Read authoritative head/generation and manifest | Prior success or conflict is proven |
| Concurrent publisher wins | Conditional update affects zero rows | Rebase/revalidate or reject duplicate scope | One coherent head selected |
| Publish succeeds, checkpoint fails | Head contains run; checkpoint behind | Idempotently advance checkpoint after verification | Head and progress agree |
| Checksum mismatch after publish | Consumer/gate verification | Mark version invalid, roll head forward/back per contract, investigate storage | Active version verifies and consumers reconcile |
| Cleanup races reader/run | Reference/lease check fails | Never delete referenced objects; retry later | Only unreachable expired candidates removed |

Rollback usually publishes/selects another known-good version; it does not erase
evidence or reverse external side effects. When consumers already exported data,
correction may require a forward version and notification.

## Security, privacy, and governance

Separate permissions for candidate write, gate approval, head update, checkpoint
update, and cleanup. Validate manifest paths and schemas; sign or strongly protect
metadata where tampering is in scope. Encrypt data and metadata, audit every state
transition and override, redact diagnostics, and enforce retention/deletion on
orphaned and old versions. A manifest is lineage/control data and may reveal
sensitive partition keys or counts.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| State-machine unit/property tests | Generate valid/invalid transition sequences | Only permitted monotonic transitions persist | Pending |
| Crash matrix | Fail at every write/close/gate/publish/checkpoint boundary | No partial visibility or skipped input | Pending |
| Rerun determinism | Repeat logical run with same pinned dependencies | Equivalent manifest/result; explained physical differences | Pending |
| Concurrency test | Race two publishers against same generation | One winner; loser detects conflict | Pending |
| Reader consistency | Read throughout publication | Reader resolves complete old or new version | Pending |
| Cleanup/restore drill | Mix referenced, orphaned, pinned, and expired objects | Only safe objects removed; prior version restorable | Pending |

An in-memory metadata fake cannot prove database isolation, object-store conditional
writes, network unknown outcomes, or reader behavior in the real query engine.

## Common pitfalls

### Pitfall: checkpointing after each processed record

Processing is not durable publication. Align progress with a recoverable output
commit or guarantee safe replay between the two boundaries.

### Pitfall: timestamp-based output names as idempotency

Every retry creates another effect. Derive a stable logical identity and keep
attempt identity separate.

### Pitfall: success marker beside directory-listed files

The marker is useful only if consumers read it as an authoritative manifest and
verify the named immutable files rather than listing whatever happens to exist.

### Pitfall: retrying a timed-out commit blindly

The first commit may have succeeded. Read authoritative metadata using stable
identity before issuing another mutation.

## Performance, capacity, cost, and operations

Budget candidate duplication, manifest size, checksums, quality scans, metadata
contention, publish latency, old-version retention, orphan growth, and recovery
time. Keep manifests hierarchical or otherwise bounded for very large file counts,
but preserve complete reachability and integrity evidence.

Metrics include run attempts, state age, candidate bytes/files, gate duration,
publish conflicts/latency, checkpoint lag, orphan bytes, manifest verification
failures, active/pinned versions, and recovery time. Alerts and runbooks identify
the authoritative head first, freeze unsafe cleanup/publication, reconcile state,
then retry, roll forward, or select a prior known-good version.

## Compatibility, migration, and tradeoffs

Version manifest schema and readers. During migration, write metadata old readers
can tolerate or dual-publish under a new head namespace, validate both readers,
migrate consumers, and retire old metadata after the longest pin/rollback window.
Changing logical run identity or checkpoint encoding requires an explicit mapping
and common-boundary cutover.

## Working example

- Python/SQL/data/tests: planned run ledger, immutable candidate writer, manifest validator, conditional publisher, and crash/concurrency harness
- Expected result: every failure yields a complete old/new visible version and safe rerun path
- Scale represented: none yet; local state machine followed by real storage/metadata integration planned
- Remaining risk: remote durability, concurrent readers, catalog semantics, cleanup races, and large manifests

## Knowledge check

1. Distinguish checkpoint, logical run, attempt, candidate, manifest, and head.
2. Predict recovery after publish succeeds but its response and checkpoint update fail.
3. Diagnose why a `_SUCCESS` file plus directory listing can mix attempts.
4. Design an old-or-new publication protocol for five output files.
5. Identify the idempotency scope for a corrected daily partition.
6. Add concurrent publishers and specify conflict evidence and recovery.

## Key takeaways

- Checkpoint, idempotency, and atomic visibility solve different problems.
- Immutable candidates plus one authoritative metadata commit simplify publication.
- Progress advances only after output is recoverably published.
- Unknown outcomes must be inspected, not blindly retried.
- Manifests, gates, and reconciliation make rerun convergence provable.

## Resources

- [Python documentation: `os.replace`](https://docs.python.org/3/library/os.html#os.replace) (reviewed 2026-09)
- [PostgreSQL documentation: explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html) (reviewed 2026-09)
- [W3C PROV overview](https://www.w3.org/TR/prov-overview/) (reviewed 2026-09)

## Related topics

- [Backfills, reprocessing, and historical correction](06-backfills-reprocessing-and-historical-correction.md)
- [Dependencies, retries, partial failure, and recovery](07-dependencies-retries-partial-failure-and-recovery.md)
- [Object-storage layouts, partitioning, and publication](../04-data-storage-files-and-serialization/07-object-storage-layouts-partitioning-and-publication.md)

## Completion checklist

- [x] Checkpoints, identities, candidates, manifests, conditional commit, and visibility explained
- [x] Failure, security, quality, capacity, operations, migration, rollback, and evidence addressed
- [ ] State, crash, rerun, concurrency, reader, cleanup, and real-store evidence run

