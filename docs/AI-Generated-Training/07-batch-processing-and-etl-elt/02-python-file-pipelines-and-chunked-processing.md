# Python File Pipelines and Chunked Processing

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Python / Files / Batch / Single machine  
> Data scale: Local fixture; single-machine estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A correct local file pipeline reads bounded units, validates at the boundary,
transforms without accidental whole-dataset materialization, writes only to a
private candidate, and publishes after validation. Chunking bounds memory; it
does not by itself make processing idempotent, atomic, or distributed.

This guide covers a standard-library-first Python design for accepted JSON Lines
events. Distributed DataFrames, scheduler deployment, and format-specific tuning
belong to later areas.

## Learning objectives

- Stream records with explicit ownership and resource bounds.
- Separate decode, validation, normalization, transformation, and publication.
- Choose record, byte, and chunk bounds using measured memory behavior.
- Contain corrupt input and clean up incomplete outputs safely.
- Test empty, invalid, duplicate, retry, interruption, and overload cases.

## Prerequisites

- Area 02 bounded Python and resource-lifetime concepts
- Area 04 record boundaries and atomic file publication
- Area 06 accepted-raw and quarantine contracts
- [ETL, ELT, staging, and layer responsibilities](01-etl-elt-staging-and-layer-responsibilities.md)

## Mental model and terminology

The pipeline is a pull-based sequence of bounded record transformations with one
explicit materialization boundary. Kotlin `Sequence` and `use {}` are useful
analogies for lazy iteration and deterministic close. They stop at Python object
overhead, serialization behavior, process failure, and filesystem/object-store
publication semantics.

| Term | Meaning in this guide |
| --- | --- |
| Chunk | Bounded group used for amortized processing; not necessarily a commit unit |
| Streaming read | Incremental consumption without loading the entire logical dataset |
| Candidate output | Run-isolated files not yet visible as certified data |
| Reject | Input record plus safe reason and provenance that did not enter normal output |
| Materialization | Point where lazy records become an in-memory collection or durable output |

## Requirements, assumptions, and invariants

Reference input is newline-delimited UTF-8, at most 256 KiB per encoded record,
roughly 3M events/day and 3 GiB/day. One local run targets peak resident memory
below 512 MiB and emits files near a measured target rather than one file per
chunk. These are design estimates; profile representative widths and invalid data.

Invariants:

- The caller owns input discovery; the reader owns each opened stream until its context exits.
- No record crosses validation before decode and size checks succeed.
- Output identity derives from input scope and transform version, not wall-clock randomness.
- A failed run leaves no certified partial output.
- Accepted plus rejected plus intentionally filtered records reconcile to observed records.
- Repeating a run with pinned inputs/config produces equivalent ordered or canonically unordered output.

## Data flow and ownership

```text
manifest -> open one file -> bounded bytes/line -> decode -> validate
                                                   |          |
                                                reject      normalize
                                                               |
                                                  transform -> candidate writer
                                                               |
                                                   close -> validate -> publish
```

The manifest owns scope and order. The iterator owns no open file after it advances
past that file. The candidate writer owns temporary files, counts, checksums, and
cleanup. The publisher alone changes consumer-visible metadata.

## Smallest correct implementation

```python
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
import json

@dataclass(frozen=True)
class CanonicalEvent:
    tenant_id: str
    event_id: str
    product_id: str
    event_type: str

def transform(lines: Iterable[bytes], max_record_bytes: int) -> Iterator[CanonicalEvent]:
    for position, raw in enumerate(lines, start=1):
        if len(raw) > max_record_bytes:
            raise ValueError(f"record {position} exceeds byte limit")
        value = json.loads(raw.decode("utf-8", errors="strict"))
        yield CanonicalEvent(
            tenant_id=require_text(value, "tenant_id"),
            event_id=require_text(value, "event_id"),
            product_id=require_text(value, "product_id"),
            event_type=require_text(value, "event_type"),
        )
```

`require_text` is deliberately not shown as trivial syntax: the contract must
decide whether blank, null, number, normalization collision, and unknown fields
are invalid. Production code should return an explicit accepted/rejected outcome
rather than aborting a whole file for every record-level defect.

```python
def chunks(records: Iterable[CanonicalEvent], size: int) -> Iterator[list[CanonicalEvent]]:
    if size <= 0:
        raise ValueError("size must be positive")
    chunk: list[CanonicalEvent] = []
    for record in records:
        chunk.append(record)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
```

A list materializes one chunk. Peak memory depends on decoded object size, writer
buffers, libraries, and concurrent chunks—not only input bytes. A chunk boundary
is not a checkpoint unless output and progress commit together under a declared
protocol.

## Avoid / Prefer

```python
# Avoid: full materialization and in-place final output.
rows = [json.loads(line) for line in open(input_path)]
write_final(transform_all(rows))

# Prefer: context-managed streaming into a run-scoped candidate.
with input_path.open("rb") as source, candidate_path.open("xb") as destination:
    for batch in chunks(transform(source, max_record_bytes=262_144), size=10_000):
        write_batch(destination, batch)
```

The preferred sketch still needs binary-safe framing, rejection handling, fsync
or storage durability where required, checksum/row-count validation, and an atomic
publish step. Exclusive creation prevents accidental overwrite but not concurrent
logical publication.

## Record, file, and job lifecycle

Discover only manifest-listed immutable inputs. Open one or a bounded number of
files, decode incrementally, and close them deterministically. Write candidate
files under a run-specific path, close and validate them, record manifest entries,
then publish the dataset version. After success or terminal failure, retain or
remove staging according to diagnostic and privacy policy.

Cancellation stops admission of new records, finishes or abandons the current
candidate safely, closes resources, and records a non-success terminal state.
Never catch `BaseException` or broad errors merely to continue: classify expected
record failures separately from process, disk, and programming failures.

## Identity, ordering, consistency, and time

Retain source file, receipt, byte/record position, producer event ID, event time,
and ingestion time. File order is not event-time order and directory enumeration
order is not a contract. If output ordering matters, specify a total tie-breaker
and accept the external sort cost; otherwise canonicalize only for comparison.

Local rename can provide old-or-new visibility only under the documented
filesystem boundary. Object stores require their own immutable-object and
manifest/metadata commit design. A Python context manager closes resources; it
does not guarantee durable bytes or atomic multi-file publication.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Invalid UTF-8/JSON | Decoder/parser outcome with position | Reject safely or fail unit according to contract; retain provenance |
| Oversized record/decompression | Byte and expansion limits | Stop before unbounded allocation; quarantine unit |
| Disk full during write | Write/flush/close error | Candidate stays uncertified; free capacity and rerun |
| Crash after some files close | Missing terminal manifest/commit | Ignore or clean candidate; rerun same identity |
| Duplicate input in manifest | Manifest identity/checksum validation | Fail scope or classify exact duplicate before transform |
| Mutable input during read | Size/digest/version mismatch | Reject run; reacquire immutable version |
| Poison record causes retry loop | Repeated stable failure fingerprint | Quarantine under policy or stop; do not retry forever |

## Security, privacy, and governance

Resolve and validate paths against an allowed root; reject traversal and symbolic
link surprises according to platform policy. Bound record, file, archive-member,
decompressed, and total-run bytes. Avoid unsafe deserialization. Candidate,
reject, sample, and log data inherit the input classification. Use least-privilege
directories, restrictive creation modes where applicable, encrypted storage, safe
diagnostics, retention, and audited deletion.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Unit/property matrix | Empty, boundaries, random chunk splits, Unicode, invalid records | Stable dispositions and no boundary loss | Pending |
| Memory profile | Sweep record width and chunk size over representative data | Peak stays within 512 MiB budget | Pending |
| Crash matrix | Interrupt before/during/after close and publish | No partial certified output; rerun converges | Pending |
| Reconciliation | Compare manifest inputs to accepted/rejected/filtered counts and keys | No unexplained record | Pending |
| Determinism | Run pinned scope twice | Equal canonical result/manifests under declared ordering | Pending |
| Filesystem integration | Exercise actual target volume and concurrent publisher | Documented visibility and conflict behavior | Pending |

Mocks prove transformation branches, not file durability, buffering, disk-full
behavior, process restart, or remote-store semantics.

## Common pitfalls

### Pitfall: calling `readlines()` chunked processing

It first materializes the whole file. Iterate the stream and materialize only a
bounded chunk when a downstream API requires it.

### Pitfall: using chunk size as a memory limit

Ten thousand unusually wide records can exceed the budget. Enforce record and
byte bounds and profile decoded, transformed, and serialized representations.

### Pitfall: writing directly to the final filename

A crash exposes truncated output. Write isolated candidates, validate, then
publish through a storage-appropriate commit boundary.

### Pitfall: swallowing every exception into quarantine

Programming errors and storage failures become silent data loss. Quarantine only
declared input defects; fail the run for violated infrastructure or code contracts.

## Performance, observability, and operations

Measure input/output bytes, records/second, decode/transform/write time, peak RSS,
allocation rate, chunk widths, open descriptors, rejected counts, compression
ratio, staging space, and checksum cost. Tune chunk size only after identifying
whether CPU, memory, disk, serialization, or downstream calls dominate.

Structured events carry run, dataset, input, file, record-position, code/config,
and candidate IDs without raw sensitive values. Alerts cover stalled progress,
failure/reject spikes, disk headroom, candidate age, and missed publication. The
runbook preserves evidence, closes writers, identifies the last certified version,
cleans only verified run staging, reruns, and reconciles.

## Compatibility, migration, and tradeoffs

Accept old and new schemas during an expand window, emit a versioned canonical
schema, dual-run on pinned input, compare dispositions and output, then migrate
consumers. Python/library upgrades require golden files and output compatibility
checks when serialization is a contract.

| Need | Prefer | Tradeoff |
| --- | --- | --- |
| Simple bounded local transform | Standard-library iterator pipeline | Manual schema, metrics, and publication plumbing |
| Vectorized work that fits memory | DataFrame chunks | Extra object copies and library-specific null/type semantics |
| Larger-than-one-machine data | Distributed engine after contract is proven | Scheduling, shuffle, retry, and commit complexity |
| Record-level recovery | Explicit outcome stream and reject dataset | More I/O and governance obligations |

## Working example

- Python/data/tests: planned JSONL fixture, bounded reader, outcome model, candidate writer, manifest, and fault injection
- Try it: planned `python -m unittest` target after implementation
- Expected result: bounded processing reconciles every record and interruption never exposes partial output
- Scale represented: none yet; local and memory-profile evidence planned
- Remaining risk: filesystem durability, object-store publication, concurrency, and production widths

## Knowledge check

1. Identify every point where the Python sketch materializes data.
2. Predict peak-memory behavior when one record is 100 times wider than average.
3. Diagnose a final file containing half a batch after process termination.
4. Design dispositions for malformed JSON versus an unexpected `OSError`.
5. Estimate chunk memory from encoded bytes, Python expansion factor, and writer buffers.
6. Modify the design to support deterministic cancellation and rerun.

## Key takeaways

- Streaming and explicit byte bounds keep local pipelines predictable.
- Resource closure, durable write, and atomic publication are different guarantees.
- Chunk boundaries improve resource behavior but are not automatic commit boundaries.
- Every record needs a reconciled outcome and safe provenance.
- A local pipeline is a contract reference, not evidence of distributed scale.

## Resources

- [Python documentation: I/O](https://docs.python.org/3/library/io.html) (reviewed 2026-09)
- [Python documentation: `json`](https://docs.python.org/3/library/json.html) (reviewed 2026-09)
- [Python documentation: `contextlib`](https://docs.python.org/3/library/contextlib.html) (reviewed 2026-09)

## Related topics

- [ETL, ELT, staging, and layer responsibilities](01-etl-elt-staging-and-layer-responsibilities.md)
- [Checkpoints, idempotency, and atomic publication](05-checkpoints-idempotency-and-atomic-publication.md)
- [Bytes, text, encodings, and record boundaries](../04-data-storage-files-and-serialization/01-bytes-text-encodings-and-record-boundaries.md)

## Completion checklist

- [x] Bounded iteration, validation, resource ownership, publication, and cleanup explained
- [x] Identity, order, time, failure, security, quality, performance, and migration addressed
- [ ] Reader, writer, fixture, memory, crash, filesystem, and reconciliation evidence run
