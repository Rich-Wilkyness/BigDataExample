# File and Object Ingestion

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Filesystems / Object storage / Batch ingestion  
> Data scale: Local fixture; single-machine and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

File ingestion turns a changing namespace into a closed, verifiable input set.
Correctness depends on discovering only complete objects, preserving immutable
versions, validating bytes and record boundaries, and committing progress without
confusing a listing with a transaction.

This guide covers discovery, manifests, readiness, checksums, partial uploads,
duplicates, archive, and reprocessing. Format internals and downstream batch
transformation belong to areas 04 and 07.

## Learning objectives

- Define file/object readiness without relying on timing guesses.
- Use manifests, versions, sizes, and checksums to close an extraction scope.
- Distinguish duplicate delivery, duplicate content, and duplicate logical records.
- Recover from partial upload, listing change, archive failure, and rerun.
- Estimate request, file-count, memory, and source-pressure costs.

## Prerequisites

- [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md)
- Record framing, compression, checksums, file sizing, and publication from area 04

## Mental model and terminology

A directory or object prefix is a mailbox, not a database snapshot. A listing says
what was observed during calls; a producer manifest or immutable versioned prefix
defines what belongs to a batch. This resembles consuming a versioned Android app
bundle more than watching an arbitrary downloads folder. The analogy stops when
listing pages, object versions, and many concurrent producers have independent
consistency and lifecycle rules.

| Term | Meaning in this guide |
| --- | --- |
| Manifest | Immutable inventory of expected object identities and integrity metadata |
| Readiness marker | Producer signal that a named immutable scope is complete |
| Partial upload | Object visible or discoverable before promised bytes are complete/stable |
| Content identity | Digest of bytes; not automatically logical-record identity |
| Archive | Retained source or processed disposition, not proof of successful ingestion by itself |

## Requirements, assumptions, and invariants

Reference drop: 20 GiB nightly, about 200 files, complete by 02:00 UTC, 15-minute
acquisition SLO after readiness, and 35-day hot raw retention. Maximum compressed
object is 512 MiB and maximum expanded/encoded sizes require separate bounds.

Invariants:

- Process only immutable versions declared complete by contract.
- A closed batch has an immutable manifest or equivalent versioned inventory.
- Stored size and digest match the declared source unit before completion.
- A rerun never overwrites a different version under the same destination identity.
- Archive/deletion occurs only after durable landing, checkpoint, and reconciliation.
- File-level completeness and record-level acceptance remain separate.

## Discovery and publication protocol

```text
producer: stage objects -> verify -> publish immutable manifest/readiness marker
consumer: read manifest -> acquire exact versions -> verify -> commit receipt manifest
                                                     -> advance batch checkpoint
```

Prefer producer-assigned object versions and a manifest containing path/key,
version/generation, byte count, checksum algorithm/value, format/compression,
schema version, record-count expectation when reliable, and batch identity.

```python
def ingest_manifest(entries: Iterable[ManifestEntry], *, max_bytes: int):
    for entry in entries:
        with source.open_version(entry.key, entry.version) as chunks:
            receipt = raw_store.put_verified(chunks, entry, max_bytes=max_bytes)
        yield receipt
```

The caller owns the manifest iterator; each stream closes before the next entry.
The sketch requires implementations for bounded decompression, conditional writes,
digest verification, and unknown commit outcomes.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Producer staging | Mutable/incomplete objects | Producer | Never ingest as complete | Untrusted |
| Published manifest | Immutable batch inventory | Producer | Reject conflicts or missing versions | Contract evidence |
| Acquisition | Exact object version stream | Ingestion owner | Bound, checksum, retry exact version | Untrusted bytes |
| Raw object + receipt | Immutable acquired bytes | Ingestion owner | Conditional publish; never overwrite conflict | Receipt evidence |
| Archive/tombstone | Versioned disposition | Producer/ingestion owners | Delay until reconciliation | Operational state |

## Identity, lifecycle, and ordering

Path, version, content digest, batch membership, and logical record key answer
different questions. Same bytes under two paths may be a delivery duplicate; one
file may contain duplicate logical records. Process order is not business event
order. Preserve file modification metadata only as evidence, not as a trustworthy
event timestamp unless the contract says so.

State transitions are `discovered -> acquiring -> verified -> committed ->
classified -> archived`. Store state conditionally per immutable source version.
If the producer replaces a key, acquire the manifest-pinned version or fail the
batch; never silently read the newest object.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| File still uploading | Size/digest/version differs from manifest | Do not acknowledge; retry only after producer republishes readiness |
| Listing misses/duplicates objects | Manifest count/digest mismatch | Read exact manifest versions; reconcile inventory |
| Same path, changed bytes | Version or digest conflict | Quarantine conflict; require a new batch/version |
| Truncated/corrupt compressed stream | Decoder or expanded-size/checksum failure | Preserve safe diagnostics; reacquire exact version |
| Crash during destination write | Missing committed receipt | Resume/replace run-scoped staging; conditional commit |
| Archive succeeds but checkpoint fails | Source absent, receipt present | Recover from receipt ledger; never infer loss from source absence alone |
| Tiny-file flood | File-count/request budget breach | Pause admission; negotiate producer compaction or bounded packing |

Recovery completes when every manifest entry has one durable receipt/disposition,
all counts and bytes reconcile, and archive state no longer controls correctness.

## Security, privacy, and governance

Treat names, archives, CSV formulas, compressed content, and metadata as untrusted.
Reject traversal and unexpected URI schemes, pin bucket/container and prefix,
disable unsafe deserialization, bound files/records/expansion ratio, and isolate
parsers. Use short-lived read credentials and conditional destination writes.
Classify raw and quarantine, encrypt them, audit access/replay, and ensure retention
or erasure covers versions, archives, manifests, samples, and derived records.

## Data quality, testing, and evidence

| Evidence | Fixture/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Manifest contract | Empty, complete, missing, extra, reordered entries | Only exact closed scope commits | Pending |
| Integrity | Truncate/change bytes under same name | Size/digest conflict detected | Pending |
| Restart matrix | Fail during read, stage, commit, checkpoint, archive | Rerun converges without loss/overwrite | Pending |
| Duplicate cases | Same version, same bytes/new path, duplicate records | Distinct dispositions remain explicit | Pending |
| Resource bounds | Huge record, expansion bomb, tiny-file flood | Admission stops within budgets | Pending |

Local fixtures cannot prove remote listing, versioning, conditional-write, or
durability behavior. A real object-store integration suite remains required.

## Common pitfalls

### Pitfall: “unchanged for five minutes” means complete

It is a heuristic with a race window. Prefer immutable upload-then-publish with a
manifest or source-native atomic rename where its semantics are verified.

### Pitfall: moving a file proves processing succeeded

Archive movement can occur before output/checkpoint durability. Base recovery on
the receipt ledger and reconciliation, not directory location.

### Pitfall: checksum equals deduplication

A digest identifies bytes. Logical duplicates may serialize differently, and
identical reference data can legitimately belong to different batches.

## Performance, capacity, cost, and operations

Measure bytes and objects/list pages per batch, open/HEAD/GET/PUT requests, file
size distribution, compression ratio, checksum CPU, acquisition throughput,
staging peak, retry bytes, and archive/storage growth. Parallelism is bounded by
source limits, network, parser CPU, file count, and destination requests; more
workers can amplify throttling and small-file cost.

Expose batch ID, manifest digest, source version, receipt ID, attempts, bytes,
duration, and disposition in bounded-cardinality telemetry. Alert on readiness
lag, missing entries, integrity conflicts, stalled bytes, abnormal file counts,
checkpoint age, and archive backlog. Preserve the last certified manifest during
rollback.

## Compatibility, migration, and tradeoffs

Add new manifest fields compatibly, support old/new readers together, backfill a
new destination namespace from retained immutable inputs, reconcile both, then
cut over the checkpoint owner. Never reinterpret an old path convention without
pinning the convention/version used.

| Constraint | Prefer | Reconsider when |
| --- | --- | --- |
| Producer can publish inventory | Manifest plus exact immutable versions | Source cannot coordinate a closed batch |
| Filesystem atomic rename verified | Stage then rename | Storage is object-based or rename is copy/delete |
| Huge objects | Streaming, bounded read and splittable format | Format requires whole-object validation |
| Many tiny objects | Producer-side packing/compaction | Independent retry latency matters more than request cost |

## Working example

- Python/data/tests: planned local source directory, immutable manifest, staged raw store, corruption and crash fixtures
- Expected result: a batch commits only when every declared object verifies; reruns are idempotent
- Scale represented: none yet; local fixture planned
- Remaining risk: real object-store semantics, concurrent writers, request cost, and scale

## Knowledge check

1. Explain why a prefix listing is not a closed batch.
2. Predict the result when a key is overwritten after its manifest is published.
3. Diagnose an archive directory containing all files but a missing checkpoint.
4. Design fixtures that distinguish three kinds of duplicate.
5. Estimate requests and elapsed time for 200 files under a 20-request concurrency cap.
6. Add a producer that cannot create manifests and state the weaker guarantee.

## Key takeaways

- Completeness is a producer-consumer protocol, not a waiting interval.
- Pin immutable object versions and verify declared size and digest.
- Namespace state, content identity, and logical-record identity are distinct.
- Archive only after durable receipt and reconciliation.
- File count and requests can dominate before byte throughput does.

## Resources

- [Amazon S3 data consistency model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html#ConsistencyModel) (reviewed 2026-09)
- [Google Cloud Storage consistency](https://cloud.google.com/storage/docs/consistency) (reviewed 2026-09)

## Related topics

- [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md)
- [Validation, quarantine, and schema evolution](07-validation-quarantine-and-schema-evolution.md)
- [Idempotency, deduplication, late data, and reconciliation](08-idempotency-deduplication-late-data-and-reconciliation.md)

## Completion checklist

- [x] Discovery, readiness, manifests, integrity, duplicates, and archive explained
- [x] Lifecycle, bounds, security, operations, failure, and migration addressed
- [ ] Adapter, corruption/restart tests, and real object-store evidence run
