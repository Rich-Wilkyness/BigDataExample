# Ingestion Contracts and Raw-Data Ownership

> Status: Documentation complete; executable evidence planned  
> Level: Beginner  
> Applies to: Generic data engineering / Batch / Streaming / Storage  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

An ingestion contract states what a producer offers, what an ingestion system
accepts, and exactly when progress may be acknowledged. A durable raw boundary
preserves the received payload and provenance so parsing defects, downstream
changes, and partial failures can be repaired without asking the source to
recreate history.

This guide covers source agreements, receipt metadata, immutable landing,
acknowledgement, lineage, ownership, and replay. Source-specific acquisition and
downstream transformation are covered elsewhere.

## Learning objectives

- Define a source-to-raw contract with explicit grain, identity, time, and ownership.
- Separate byte receipt, structural acceptance, and business acceptance.
- Design an acknowledgement boundary that survives process failure and retry.
- Trace lineage from a source position through accepted and quarantined records.
- Reconcile a bounded extraction scope without treating raw data as business truth.

## Prerequisites

- Producer/consumer boundaries, delivery semantics, and SLOs from area 01
- Record boundaries and immutable publication from area 04
- Grain, business keys, and source authority from area 05

## Mental model and terminology

Treat ingestion as a write-ahead inbox. Persist the envelope and payload before
marking the source unit complete, then interpret it. This resembles persisting an
Android work item before reporting `Result.success()`. It stops at distributed
sources: an acknowledgement may apply only to one partition or object, and no
single transaction necessarily spans source progress and destination storage.

| Term | Meaning in this guide |
| --- | --- |
| Delivery | One attempt to transfer a source unit; retries may repeat a logical record |
| Receipt | Durable evidence that a named delivery or object was acquired |
| Raw | Minimally changed payload plus provenance at the ingestion boundary |
| Checkpoint | Durable position after which earlier source units need not be reacquired normally |
| Acknowledgement | Signal whose documented meaning permits the producer to advance or discard |
| Replay | Reprocessing retained input without pretending it was newly produced |

## Requirements, assumptions, and invariants

Reference requirements: 3M events/day, 15-minute freshness, seven-day normal
replay, 35-day hot raw retention, and auditable deletion. A receipt must include
`source_system`, source partition/object, source position or version, extraction
ID, observed time, content checksum, schema hint, byte count, and code/config
version. Estimates are invalidated by measured volume, payload, lateness, or
consumer SLOs beyond these bounds.

Invariants:

- A source unit is acknowledged only after payload and receipt metadata are durable.
- Raw bytes are immutable; corrections create new versions or dispositions.
- Every accepted, rejected, deferred, or duplicate outcome links to one or more receipts.
- Advancing a checkpoint never makes an unpersisted source unit unreachable.
- Producer authority over meaning is distinct from ingestion authority over receipt.
- For a closed scope: `observed = accepted + quarantined + duplicate deliveries + deferred`, with categories disjoint and explained.

## Data flow, ownership, and trust boundaries

| Boundary | Contract and grain | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Source | Versioned unit at a named position | Producer | Retain or redeliver until acknowledgement contract is met | External/untrusted |
| Acquisition | One delivery attempt | Ingestion runtime | Retry with bounded backoff; preserve attempt ID | Untrusted |
| Raw landing | Immutable payload plus receipt | Ingestion owner | Atomic publish or remain invisible/incomplete | Evidence, not business truth |
| Classification | One disposition per parsed record | Contract owner | Accept, quarantine safely, or defer | Validated structurally |
| Downstream | Versioned accepted dataset | Data-product owner | Consume only certified snapshot/checkpoint | Trusted for declared use |

The raw copy is authoritative evidence of bytes received. It is not authoritative
for product price, customer identity, or whether a mobile event truly occurred.

## Contract and acknowledgement state machine

```text
discovered -> acquiring -> durably_landed -> classified -> published
                  |              |              |
                retry       acknowledge      quarantine
```

Acknowledging at `acquiring` risks loss after a crash. Requiring downstream
publication before acknowledgement couples source availability to every consumer.
The usual minimum safe boundary is a durable, discoverable receipt and payload;
the contract must state any exception.

A compact receipt model:

```python
@dataclass(frozen=True)
class Receipt:
    source: str
    source_unit: str
    source_position: str | None
    extraction_id: str
    observed_at_utc: datetime
    sha256: str
    byte_count: int
```

The sketch is planned. A real writer must stream checksums, bound record and
object sizes, fsync or use storage-specific durability, publish atomically, and
handle an unknown commit result. Application code alone cannot make two external
systems transactional.

## Lifecycle, identity, consistency, and time

Discovery time, source event/update time, ingestion time, and publication time
answer different questions and must remain separate. Delivery identity diagnoses
transport retries; logical identity supports downstream deduplication. A checksum
proves byte equality, not semantic uniqueness.

Stage data under a run-scoped identity, validate size and digest, commit immutable
objects and their manifest, then advance the checkpoint conditionally. On an
unknown commit outcome, read the receipt/checkpoint before retrying. Retention,
legal hold, correction, and erasure operate through versioned dispositions or
new snapshots rather than mutating undocumented files.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Complete when |
| --- | --- | --- | --- |
| Crash before landing | Attempt without durable receipt | Reacquire | Source unit lands once or is classified |
| Crash after landing before acknowledgement | Receipt exists; source redelivers | Match source identity/checksum; acknowledge safely | Duplicate delivery is explained |
| Payload changes under same source name | Digest/version conflict | Quarantine both or apply declared source-version rule | Scope reconciles to chosen version |
| Partial publication | Missing/invalid manifest | Keep invisible; resume or abandon staging | One certified snapshot is visible |
| Parser defect | Quarantine spike or reconciliation drift | Retain raw; deploy versioned parser and replay | New output reconciles and consumers migrate |
| Lost lineage | Output lacks receipt IDs | Stop certification; reconstruct from manifest or reacquire | Every outcome traces to input |

Retries belong to the boundary that can determine the prior outcome. Blindly
retrying an unknown write may duplicate it; blindly advancing may lose it.

## Security, privacy, and governance

Authenticate the source and authorize only source-specific landing paths. Encrypt
in transit and at rest, keep secrets out of receipts, reject path traversal and
unsafe destinations, and bound decompression/parsing. Raw and quarantine commonly
contain more sensitive data than curated outputs: minimize collection, restrict
access, redact diagnostics, audit replay, and attach retention/deletion policy to
every derivative. A hash of a direct identifier can remain personal data.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Receipt contract | Validate complete/empty/oversized units | Required metadata and bounds enforced | Pending |
| Crash matrix | Fail before/after landing and checkpoint | No loss; retries have explained disposition | Pending |
| Mutation case | Reuse source name with changed bytes | Conflict detected, not overwritten | Pending |
| Reconciliation | Close a deterministic source scope | All observed units partition into outcomes | Pending |
| Lineage replay | Reparse retained raw with a new version | Old and new outputs remain attributable | Pending |

Fixtures and fault injection prove local state transitions only, not remote
durability or atomicity. Real storage integration and restart tests remain needed.

## Common pitfalls

### Pitfall: calling the first copied payload raw

Without source position, checksum, extraction identity, time, and code version,
the copy cannot prove what was received or support a safe replay.

### Pitfall: acknowledging after parsing but before durable landing

A process crash creates acknowledged loss. Land first, then acknowledge according
to the explicit contract.

### Pitfall: silently fixing raw values

Normalization destroys evidence. Preserve bytes and record transformations in
versioned derived data with lineage.

## Performance, observability, and operations

Budget source units/second, bytes/second, object count, record-size percentiles,
concurrency, staging space, checksum CPU, request cost, and replay duration. Bound
labels in metrics; put run, source, partition, checkpoint, dataset version, and
receipt IDs in structured events and traces. Monitor acquisition lag, oldest
unacknowledged unit, bytes/records by disposition, checksum conflicts, quarantine
rate, checkpoint age, and source-to-target reconciliation.

The runbook pauses acknowledgement on unexplained loss, preserves staging,
identifies the last certified checkpoint, repairs or replays a bounded scope, and
requires reconciliation before resuming.

## Compatibility, migration, and tradeoffs

Evolve contracts with expand/migrate/contract: accept old and new envelopes,
retain schema/version hints, compare classifications, migrate producers and
consumers, then retire old behavior. Replays must pin parser/config versions.

| Need | Prefer | Tradeoff |
| --- | --- | --- |
| Maximum forensic recovery | Byte-preserving immutable raw | Storage, privacy, and deletion cost |
| Fast rejection before storage | Bounded envelope/security gate | Must not discard payloads the contract promises to retain |
| Decoupled consumers | Acknowledgement at durable landing | Raw backlog can grow during downstream failure |
| Strong source-target atomicity | Source-native transaction/outbox when available | Higher coupling; rarely spans arbitrary storage |

## Working example

- Python/data/tests: planned receipt ledger, staged writer, crash matrix, and reconciliation fixture
- Try it: planned `python -m unittest` target after implementation
- Expected result: each injected failure converges without unexplained loss or overwrite
- Scale represented: none yet; estimates only
- Remaining risk: real-store durability, concurrent writers, privacy deletion, and distributed restart

## Knowledge check

1. State the grain and authority of a delivery receipt and accepted raw record.
2. Predict the outcome of a crash after landing but before acknowledgement.
3. Diagnose why matching only a filename cannot identify a retry safely.
4. Design a reconciliation equation for a 1,000-record closed extraction.
5. Choose an acknowledgement point for a source that deletes data on success.
6. Add an erasure requirement and trace every retained derivative that changes.

## Key takeaways

- Ingestion correctness starts with a source agreement and durable receipt boundary.
- Raw preserves evidence; it does not automatically become business authority.
- Acknowledgement, checkpoint, and publication are separate commit decisions.
- Identity and reconciliation make retry behavior provable.
- Replay, privacy, retention, and lineage must be designed together.

## Resources

- [NIST Secure Hash Standard (FIPS 180-4)](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) (reviewed 2026-09)
- [W3C PROV overview](https://www.w3.org/TR/prov-overview/) (reviewed 2026-09)

## Related topics

- [File and object ingestion](02-file-and-object-ingestion.md)
- [Validation, quarantine, and schema evolution](07-validation-quarantine-and-schema-evolution.md)
- [Idempotency, deduplication, late data, and reconciliation](08-idempotency-deduplication-late-data-and-reconciliation.md)

## Completion checklist

- [x] Contract, ownership, receipt, acknowledgement, lineage, and replay explained
- [x] Identity, time, failure, security, performance, and migration addressed
- [ ] Receipt writer, crash tests, storage integration, and reconciliation evidence run
