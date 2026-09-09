# Bytes, Text, Encodings, and Record Boundaries

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / Python / Files / Storage  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Storage returns bytes. Text exists only after a decoder maps those bytes through
a named character encoding, and records exist only after a framing rule divides
the decoded text or raw byte stream. Decoding, framing, parsing, and semantic
validation are distinct boundaries with different errors and recovery choices.

This guide covers Unicode, UTF-8, byte order marks, line endings, delimiters,
length-prefixing, checksums, truncation, and quarantine. It does not teach a
particular distributed filesystem or define CSV/JSON parsing, which follows in
the next guide.

## Learning objectives

After completing this guide, you should be able to:

- Distinguish bytes, code units, code points, grapheme clusters, and rendered glyphs.
- Choose and enforce an encoding and record-framing contract.
- Explain why byte offsets, character positions, and displayed characters differ.
- Detect and contain invalid encoding, truncated records, mixed line endings, and delimiter collisions.
- Design bounded, restartable ingestion without silently replacing corrupt input.

## Prerequisites

- Grain, source authority, trust boundaries, and immutable raw data from area 01
- Python byte streams, iterators, validation, and resource lifetime from area 02

## Mental model

```text
bytes --decode(encoding, strict)--> text --frame(rule)--> record text
  |                                  |                    |
checksum/length                 Unicode policy       parser + schema
```

A Kotlin `ByteArray.decodeToString()` boundary is a useful starting analogy.
It stops at file scale: a worker may begin at an arbitrary byte range, a corrupt
sequence may cross that boundary, and a retry must reproduce the same records
without rereading an unbounded stream.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Encoding | Reversible mapping between character data and byte sequences under a named standard |
| Code point | Unicode numeric value; not necessarily one user-perceived character |
| Grapheme cluster | One user-perceived text element, possibly several code points |
| Framing | Rule that identifies where one record begins and ends |
| Sentinel | Special byte or character sequence used as a delimiter |
| Length prefix | Record size encoded before the record payload |
| Resynchronization | Finding a trustworthy later boundary after corruption |

## Requirements, scale assumptions, and invariants

The reference landing contract is UTF-8 without a byte order mark, LF-delimited
records, a maximum encoded record size of 1 MiB, and immutable source objects.
The producer must escape or structurally protect embedded newlines at the
serialization layer. The ingest reader uses strict decoding; it never converts
malformed bytes to the replacement character as if they were valid data.

Invariants are:

- The same accepted byte range yields the same record boundaries on every rerun.
- Byte length limits are checked before unbounded allocation.
- Invalid bytes and incomplete terminal records are rejected with safe location,
  source identity, and checksum metadata; raw sensitive payloads are not logged.
- Normalization, case folding, and trimming are explicit semantic transforms, not
  accidental side effects of decoding.
- A checkpoint advances only past a fully framed and durably handled record.

## Unicode and UTF-8

UTF-8 is variable-width and represents ASCII code points using the same single
bytes. Indexing a Python or Kotlin string does not necessarily select a displayed
character, and slicing raw bytes may split a multi-byte encoding sequence. Text
equality can also differ for visually similar sequences; if Unicode normalization
is a business rule, name the normalization form and apply it consistently to keys
before uniqueness or joins. Do not normalize opaque identifiers without owner
approval because the transformed value may cease to be the source identity.

A byte order mark is not an automatic encoding detector. Specify whether it is
forbidden, accepted and stripped, or treated as content. Mixed encodings inside
one object are a contract violation rather than a guessing exercise.

## Framing strategies

| Strategy | Strength | Failure mode | Good fit |
| --- | --- | --- | --- |
| Newline delimiter | Simple, streamable, easy recovery | Embedded or mixed newline rules | Properly escaped text records |
| Other sentinel | Low overhead | Collision and escape ambiguity | Restricted payload alphabets |
| Fixed width | Direct offsets | Wasted space; schema change pain | Truly fixed binary records |
| Length prefix | Arbitrary payload; direct next boundary | Corrupt length can lose synchronization | Typed binary protocols with bounds |
| Container blocks + sync/checksum | Parallelism and recovery domains | More metadata and implementation complexity | Large analytical/row container files |

CRLF and LF are different byte sequences. Universal-newline convenience can hide
source differences, so validation should decide whether mixed endings are accepted,
normalized, or rejected before record hashes and byte offsets are recorded.

## Python model

```python
from collections.abc import BinaryIO, Iterator

MAX_RECORD_BYTES = 1_048_576

def strict_utf8_lines(source: BinaryIO) -> Iterator[tuple[int, str]]:
    """Yield (starting byte offset, text); caller owns and closes source."""
    offset = 0
    while raw_line := source.readline(MAX_RECORD_BYTES + 1):
        if len(raw_line) > MAX_RECORD_BYTES:
            raise ValueError(f"record exceeds {MAX_RECORD_BYTES} bytes at {offset}")
        if not raw_line.endswith(b"\n"):
            raise ValueError(f"unterminated record at {offset}")
        payload = raw_line[:-1]
        if payload.endswith(b"\r"):
            payload = payload[:-1]
        text = payload.decode("utf-8", errors="strict")
        yield offset, text
        offset += len(raw_line)
```

This sketch bounds each record, reports byte rather than character positions, and
leaves file lifetime with the caller. It still assumes a seekable/stable source
and accepts both LF and CRLF; a real contract must test those choices. `readline`
does not solve embedded-newline framing for a serialization dialect that permits
unescaped newlines.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Producer to landing | Named encoding, framing, maximum size | Source team | Reject delivery or retain immutable failed object | Untrusted |
| Landing to decoder | Stable object version and checksum | Ingestion/platform | Retry reads; alert on changed bytes | Untrusted |
| Decoder to parser | Valid Unicode records with byte offsets | Ingestion | Quarantine invalid record metadata | Valid framing only |
| Parser to accepted dataset | Versioned semantic schema | Data product | Reject/quarantine; reconcile counts | Validated |

The immutable landed object is authoritative for what was received. Decoded text
and accepted events are derived states. Authorization to read quarantine data
should be narrower than authorization to view aggregated metrics.

## Failure model and recovery

| Failure | Detection and containment | Recovery and completion evidence |
| --- | --- | --- |
| Invalid UTF-8 | Strict decoder reports source version and byte offset | Producer repair or approved transcoding; all counts reconcile |
| Truncated final record | Missing delimiter/declared length or checksum | Do not publish; retry stable source or request replacement |
| Delimiter in payload | Parse/framing mismatch and abnormal field count | Fix producer escaping; replay immutable bytes with new parser version |
| Corrupt length prefix | Length exceeds bound or container checksum fails | Stop within block; recover only at specified sync marker |
| Worker dies after handling record | Checkpoint remains before uncommitted boundary | Replay; deduplicate by business identity at the owning boundary |
| One huge line | Bound triggers before allocation grows without limit | Quarantine object/record and protect worker capacity |

Replacement decoding such as `errors="replace"` destroys evidence about the
original bytes and can merge distinct keys. It may be useful only in a separately
labeled forensic preview, never as silent production acceptance.

## Security, privacy, and governance

Treat filenames, offsets, and decoded fields as untrusted. Reject path traversal
when materializing files, cap record and field sizes, avoid logging payloads, and
protect raw/quarantine locations with least privilege and retention policy.
Unicode confusables and control characters can mislead operators; identifiers
need an explicit allowed-character and display policy. Checksums detect accidental
change but do not authenticate a malicious producer unless keyed/signed within a
defined trust model.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Expected result | Result |
| --- | --- | --- | --- |
| UTF-8 round trip | ASCII, multilingual, combining, supplementary characters | Bytes reproduce exactly under declared contract | Pending |
| Invalid-sequence mutations | Truncated and illegal sequences at every boundary | Strict deterministic rejection with safe offset | Pending |
| Framing matrix | LF, CRLF, empty, embedded newline, no final delimiter | Contract choice enforced without loss | Pending |
| Size boundary | Maximum-1, maximum, maximum+1 bytes | First two accepted; last bounded and rejected | Pending |
| Retry/property test | Random record chunks and injected worker stop | Same records; checkpoint never skips partial data | Pending |

Fixtures are local and deterministic. They cannot prove distributed split
behavior, object-store stability, malicious-input resistance, or production memory.

## Debugging and operations

Record source URI/key, immutable version, byte length, checksum, parser version,
encoding, framing rule, batch/run ID, byte offset, accepted/rejected counts, and
bounded error category. Alert on decode error rate, oversize records, truncation,
count reconciliation failure, repeated retries, and unexpected encoding markers.

Before replay, confirm the raw version has not changed and the repair is versioned.
Recovery is complete when every delivery is accepted or accounted for in a durable
quarantine and downstream counts converge.

## Common pitfalls

### Pitfall: assuming one byte, code point, and character are interchangeable

The symptom is split text, invalid decoding, incorrect truncation, or unstable
keys. Count bytes for storage/network bounds, code points only for rules defined
that way, and grapheme clusters for user-visible length when required.

### Pitfall: decoding before preserving raw evidence

An incorrect decoder can irreversibly change the data. Land immutable bytes and
their checksum before applying a replaceable decoder whenever the source contract
and risk justify retention.

### Pitfall: checkpointing reads instead of handled records

A buffer may be read before its final record is validated and published. Commit
only at a boundary whose outputs or rejection are durable and rerunnable.

## Performance, capacity, and cost

Track encoded bytes, records, p50/p95/p99 record size, decoder throughput, peak
buffer memory, invalid rate, and reread bytes. Chunk size affects syscall/network
overhead but must not change record boundaries. Parallel byte-range readers need
a format-specific resynchronization rule; arbitrary newline search is unsafe when
newlines may appear inside quoted records.

## Compatibility, migration, and delivery

An encoding or framing change is a protocol migration. During coexistence, route
by explicit producer/schema metadata rather than guessing. Test old-writer/new-reader
and new-writer/old-reader combinations, preserve original bytes, dual-parse a
sample, compare counts/hashes, then cut over. Rollback means selecting the prior
decoder for the same immutable bytes, not mutating history in place.

## Working example

- Python/data/tests: planned bounded UTF-8 reader and corruption fixture matrix
- Try it: pending exact command after implementation
- Expected result: deterministic decode/frame/reject behavior and count reconciliation
- Scale represented: none yet; 3 GiB/day is an estimate
- Remaining risk: distributed byte-range reads, adversarial input, and object-store behavior

## Knowledge check

1. Explain why decoding and framing must report different failure categories.
2. Predict what happens when a byte-range split begins inside a four-byte UTF-8 sequence.
3. Design fixtures for CRLF, embedded newline, invalid bytes, and a truncated final record.
4. Diagnose how replacement decoding could create an identity collision.
5. Propose a safe migration from a legacy encoding to UTF-8 with rollback.
6. Modify the planned reader to enforce one line-ending policy and specify its tests.

## Key takeaways

- Files contain bytes; encoding and framing create text records.
- Byte, code-point, and user-perceived-character boundaries are different.
- Bounds, strict decoding, immutable evidence, and durable rejection make recovery possible.
- A checkpoint is safe only after a whole record has a durable outcome.
- Parallel reading requires format-aware split and resynchronization rules.

## Resources

- [Unicode Standard 17.0, Chapter 2: UTF-8](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-2/) (reviewed 2026-09)
- [Unicode Standard Annex #15: Normalization Forms](https://www.unicode.org/reports/tr15/) (reviewed 2026-09)
- [Python documentation: Unicode HOWTO](https://docs.python.org/3/howto/unicode.html) (reviewed 2026-09)

## Related topics

- [CSV, JSON, and JSON Lines](02-csv-json-and-json-lines.md)
- [Compression, splittability, and file sizing](06-compression-splittability-and-file-sizing.md)
- [Object-storage layouts, partitioning, and publication](07-object-storage-layouts-partitioning-and-publication.md)

## Completion checklist

- [x] Byte/text/framing mental model and ownership boundaries explained
- [x] Encoding, Unicode, line endings, truncation, corruption, recovery, and security addressed
- [x] Evidence and operational signals specified conservatively
- [ ] Reader, fixtures, property tests, and memory evidence implemented and run

