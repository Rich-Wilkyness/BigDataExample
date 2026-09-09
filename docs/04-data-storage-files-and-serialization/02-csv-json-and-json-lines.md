# CSV, JSON, and JSON Lines

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Python / Files / Serialization / Batch  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

CSV and JSON are text interchange families, not complete dataset contracts. CSV
needs a dialect plus a schema; JSON has structural types but still leaves number,
timestamp, duplicate-key, and record-stream conventions to applications. JSON
Lines uses one JSON value per line, improving streaming and failure isolation
when producers prohibit literal unescaped newlines between record boundaries.

This guide compares their correctness, evolution, splitting, and operational
behavior. It does not claim that human readability makes a format safe or cheap.

## Learning objectives

- Define CSV using delimiter, quote, escape, header, newline, encoding, and schema rules.
- Preserve missing, empty, null, numeric, boolean, and timestamp distinctions.
- Explain why one large JSON array and JSON Lines have different streaming behavior.
- Parse untrusted inputs with resource bounds and deterministic rejection.
- Select a text format from consumer needs, not familiarity alone.

## Prerequisites

- [Bytes, text, encodings, and record boundaries](01-bytes-text-encodings-and-record-boundaries.md)
- Python iteration, validation, typed boundaries, and safe resource lifetime

## Mental model

```text
bytes -> UTF-8 records -> syntax parser -> generic values -> versioned schema
                                                        -> semantic validation
```

`Map<String, Any?>` is a useful Kotlin analogy for a freshly parsed JSON object:
the structure exists, but domain types and invariants do not. The analogy stops
at JSON number interoperability and duplicate member names, where parsers can
make different choices before application validation sees the input.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| CSV dialect | Delimiter, quote, escape, newline, header, whitespace, and encoding rules |
| Header | Optional field-name record; not by itself a versioned schema |
| JSON value | Object, array, number, string, boolean, or null |
| JSON Lines / NDJSON | Operational convention of one complete JSON value per line |
| Missing | Field/member absent from the record |
| Empty | Present string or collection with length zero |
| Explicit null | Present field whose value is JSON null or a mapped CSV null token |

## Requirements and invariants

The reference exchange uses UTF-8. CSV declares comma delimiter, double-quote
quoting, CRLF or LF acceptance with normalized parsing, one header, and a sidecar
schema. JSON Lines requires exactly one object per line. Both cap records at 1 MiB,
nesting/field counts, string lengths, and `attributes` entries.

Invariants are:

- `event_id` and `delivery_id` remain strings even if they contain only digits.
- Missing, empty, and explicit null do not collapse unless a named mapping says so.
- Timestamps are validated and normalized to UTC; formatting is not used as identity.
- Integers outside the accepted 64-bit range are rejected, not rounded through float.
- Unknown and duplicate fields follow an explicit version policy.
- Each delivery receives exactly one durable accepted or rejected outcome.

## CSV contract

CSV is excellent for flat exchange with broad tool support, but widespread
dialects differ. Quoted fields may contain delimiters and line breaks, so a
physical line is not always a logical record. Headers can be absent, reordered,
duplicated, or renamed; bind by a validated contract, not unchecked position or
the first row alone.

CSV has no native type or null syntax. A robust sidecar contract specifies each
column, logical type, nullability, missing-column policy, null token, empty-string
meaning, decimal scale, timestamp/time-zone rule, and unknown-column behavior.
Spreadsheet formula interpretation is a separate export threat when untrusted
values begin with formula-triggering characters.

## JSON and JSON Lines contracts

JSON supports nested objects and arrays plus string, number, boolean, and null.
It does not define application timestamp or decimal types. Interoperable systems
must agree on numeric range/precision and reject non-standard values such as NaN
or Infinity unless a separately named protocol permits them.

Duplicate object member names are dangerous because receivers may retain the
first, retain the last, report all, or reject them. The reference validator rejects
duplicates. A single top-level JSON array commonly requires whole-document state
or a streaming parser and has one broad corruption domain. JSON Lines provides
independent record framing and append-friendly processing, but it is a convention
that must still define blank-line and final-newline behavior.

## Python model

```python
import json
from decimal import Decimal
from typing import Any

def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key!r}")
        result[key] = value
    return result

def parse_json_record(text: str) -> dict[str, Any]:
    value = json.loads(
        text,
        parse_float=Decimal,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-standard number: {token}")
        ),
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError("event record must be a JSON object")
    return value
```

This establishes safer syntax behavior but does not validate the event schema,
integer range, timestamps, string sizes, or nested depth. The Python CSV module
similarly needs files opened with `newline=""` so its parser owns newline handling;
the chosen dialect and field-size limit must be explicit.

## Decision table

| Requirement | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Flat partner export opened in common desktop tools | Contracted CSV | Ubiquitous and inspectable | Nested data or null/type fidelity dominates |
| Nested API/debug payload | JSON | Natural hierarchy and broad libraries | Many-record streaming or size dominates |
| Append/stream one text record at a time | JSON Lines | Per-record framing and isolation | Embedded producer output violates the convention |
| Stable typed high-volume storage | Avro or Parquet | Stronger schema/physical efficiency | Human text interchange is the primary need |

## Data flow, ownership, and trust boundaries

| Boundary | Authority | Contract | Failure behavior |
| --- | --- | --- | --- |
| Producer export | Source team | Encoding, dialect/JSON profile, schema version | Delivery rejected or retained for repair |
| Raw landing | Ingestion | Immutable bytes, checksum, source/version | Preserve what arrived |
| Parser | Ingestion library owner | Bounded syntax and duplicate policy | Safe error category and location |
| Domain validator | Data-product owner | Logical types and cross-field invariants | Accept or quarantine; reconcile |

Raw text is authoritative evidence of delivery, not necessarily business truth.
The accepted event dataset is authoritative for analytical use under its contract.

## Failure model and recovery

| Failure | Symptom | Repair |
| --- | --- | --- |
| CSV delimiter inside unquoted field | Shifted columns or field-count mismatch | Reject; fix producer quoting; replay raw version |
| Quoted CSV newline split as two records | Parse failures and count inflation | Use dialect-aware parser/splitter; republish |
| Header reordered/duplicated | Values bind to wrong fields | Validate unique names and bind explicitly |
| JSON duplicate member | Parser-dependent value | Reject duplicates at syntax boundary |
| Large/nested JSON | CPU or memory exhaustion | Enforce byte, depth, member, and collection limits |
| Numeric precision loss | IDs/amounts change after round trip | Parse to bounded integer/decimal contract |
| Partial last line | Unexpected EOF | Do not publish; retry stable object or replace source |

Per-record quarantine is safe only when the parser can reliably locate the next
record. For a damaged CSV quoted field spanning newlines, quarantining one physical
line can misclassify everything afterward; fail the file or use a proven recovery rule.

## Security, privacy, and governance

CSV/JSON inputs can contain formula strings, control characters, huge values,
deep nesting, deceptive Unicode, and sensitive fields. Bound parser resources,
sanitize only at a named export boundary, use safe structured errors, and restrict
raw/quarantine access. Never use dynamic object hooks or unsafe deserialization
to instantiate arbitrary classes from these formats.

## Data quality, testing, and evidence

| Evidence | Cases | Expected result | Result |
| --- | --- | --- | --- |
| Golden round trip | Unicode, commas, quotes, newlines, empty/null/missing | Contract-equivalent typed records | Pending |
| Dialect mutation | Delimiter, quote, header order/duplicate, line ending | Deterministic accept/reject | Pending |
| JSON mutation | Duplicate keys, deep nesting, huge number, NaN, trailing bytes | Bounded deterministic rejection | Pending |
| Compatibility | Old/new fields across schema versions | Declared matrix passes; forbidden cases fail | Pending |
| Reconciliation | Delivery, accepted, rejected, duplicate counts | Totals balance by file and run | Pending |
| Size/profile | CSV vs JSON/JSONL fixture | Bytes, CPU, memory, and throughput recorded | Pending |

## Debugging and operations

Capture source object/version/checksum, declared media type and schema version,
dialect or JSON profile, parser version, byte/record location, safe error code,
and reconciliation counts. Monitor unexpected columns, null/empty rates, reject
rate, record-size distributions, parser latency, and repeated producer failures.

## Common pitfalls

### Pitfall: splitting CSV with `line.split(",")`

Quoted delimiters, escaped quotes, and embedded newlines violate the assumption.
Use a conforming parser with a pinned dialect and adversarial fixtures.

### Pitfall: treating a CSV header as a schema

Names do not declare type, nullability, units, time zone, or compatibility. Store
and version those rules independently.

### Pitfall: assuming every parser agrees on JSON

Duplicate keys, numeric precision, invalid constants, and resource limits vary.
Configure and test the actual producer/consumer library pair.

## Performance, capacity, and cost

Measure encoded/compressed bytes, parse CPU, peak memory, throughput, records per
file, average/tail width, rejection cost, and parallel split behavior. Text often
costs more bytes and parsing CPU than typed binary formats, but that hypothesis
must be measured on representative fields and compression. JSON Lines can be
streamed record by record; a top-level array still can be streamed with a suitable
parser, so the distinction is an implementation and failure-domain choice, not
an absolute format limitation.

## Compatibility, migration, and delivery

Version dialect/profile and logical schema separately. Prefer additive fields
with tolerant new readers only when defaults and semantics are explicit. Test all
writer/reader combinations in the supported window, dual-read a bounded sample,
compare canonical typed records rather than text bytes, publish a new immutable
dataset version, and retain a rollback pointer until downstream reconciliation.

## Working example

- Python/data/tests: planned CSV and JSON Lines readers plus golden/mutation fixtures
- Expected result: equivalent accepted event records and deterministic rejections
- Scale represented: none yet; local fixture planned
- Remaining risk: partner dialect drift, distributed CSV splitting, and adversarial parser cost

## Knowledge check

1. Specify a CSV null/empty/missing contract for `product_id`.
2. Predict how two JSON parsers might handle `{"quantity": 1, "quantity": 2}`.
3. Diagnose count inflation caused by a quoted newline and naive file splitting.
4. Design a compatibility matrix for adding nullable `campaign_id`.
5. Estimate when text parsing CPU could dominate the 15-minute batch window.
6. Add one mutation fixture and state the exact durable outcome it should produce.

## Key takeaways

- CSV needs a dialect and sidecar schema; JSON needs an application profile.
- Missing, empty, and null are separate states until the contract maps them.
- JSON Lines narrows record failure domains but does not supply schema or safety bounds.
- Parser configuration and producer/consumer compatibility require executable tests.
- Human readability is useful, not a correctness or efficiency guarantee.

## Resources

- [RFC 4180: Common Format and MIME Type for CSV Files](https://www.rfc-editor.org/rfc/rfc4180.html) (reviewed 2026-09; informational, not an Internet Standard)
- [RFC 8259: The JSON Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259.html) (reviewed 2026-09)
- [RFC 7464: JSON Text Sequences](https://www.rfc-editor.org/rfc/rfc7464.html) (reviewed 2026-09; distinct framing from newline-only JSON Lines)
- [Python documentation: `csv`](https://docs.python.org/3/library/csv.html) and [`json`](https://docs.python.org/3/library/json.html) (reviewed 2026-09)

## Related topics

- [Bytes, text, encodings, and record boundaries](01-bytes-text-encodings-and-record-boundaries.md)
- [Avro records, schemas, and compatibility](03-avro-records-schemas-and-compatibility.md)
- [Compression, splittability, and file sizing](06-compression-splittability-and-file-sizing.md)

## Completion checklist

- [x] CSV dialect and JSON profile semantics explained
- [x] Types, missing/null/empty, framing, splitting, failure, security, and migration addressed
- [x] Decision and evidence tables included
- [ ] Readers, fixtures, compatibility, corruption, and performance evidence run

