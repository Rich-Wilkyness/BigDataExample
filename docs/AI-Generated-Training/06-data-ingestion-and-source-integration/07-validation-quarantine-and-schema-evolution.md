# Validation, Quarantine, and Schema Evolution

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Generic ingestion / Python / SQL / Batch / Streaming  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Validation decides whether untrusted input is safe and fit to cross a named
boundary. Quarantine retains the minimum protected evidence needed to diagnose
and reprocess rejected input. Schema evolution changes that decision over time;
therefore every disposition must identify the contract and code version used.

This guide separates envelope, structural, semantic, and cross-record checks. It
does not replace downstream business-quality monitoring or organization-wide
governance.

## Learning objectives

- Place validation gates according to cost, trust, and recovery needs.
- Distinguish malformed, invalid, unresolved, duplicate, and late records.
- Design safe quarantine with stable lineage and bounded sensitive diagnostics.
- Evaluate backward, forward, and full compatibility from producer and consumer views.
- Reprocess rejected data without corrupting lineage or operational metrics.

## Prerequisites

- Typed validation and untrusted-input handling from area 02
- Schema/format evolution from area 04 and business invariants from area 05
- [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md)

## Mental model and terminology

Validation is a sequence of border checkpoints, not one boolean at the end. This
resembles parsing a network DTO into a Kotlin domain type, except a data pipeline
must retain millions of mixed-version failures, distinguish temporary resolution
from permanent invalidity, and reproduce old decisions months later.

| Term | Meaning in this guide |
| --- | --- |
| Structural validation | Framing, parseability, required fields, types, and declared schema checks |
| Semantic validation | Domain constraints such as allowed currency or nonnegative quantity |
| Contextual validation | Check requiring external/reference or cross-record state |
| Quarantine | Access-controlled rejected evidence plus reason, lineage, and lifecycle |
| Compatibility | Ability of a named writer/reader version pair to exchange intended meaning |
| Disposition | Accepted, quarantined, deferred, duplicate, or another mutually defined outcome |

## Requirements, assumptions, and invariants

Reference intake is 3M events/day with a 256 KiB encoded-record bound, at least
99.9% structural acceptance objective, seven-day correction/replay window, and
35-day hot raw retention. Acceptance rate is not a goal to weaken validation;
unexpected change pages the contract owner.

Invariants:

- Cheap size, framing, and security checks occur before expensive parse/decompression.
- Every observed record receives one explicit current-run disposition.
- Validation is deterministic for pinned payload, reference snapshot, schema, config, and code versions.
- Quarantine failure cannot be mistaken for successful source acknowledgement.
- Diagnostics never expose more sensitive data than policy permits.
- Reprocessing creates a new attempt/output version while preserving original receipt and rejection history.
- Compatibility is tested with real writer/reader representations, not inferred from similar field names.

## Layered validation

```text
bytes
  -> envelope/security bounds
  -> framing/decompression/parse
  -> schema/type contract
  -> record semantics
  -> reference/cross-record checks
  -> accepted | quarantined | deferred
```

Defer a valid record when required reference state is temporarily missing and the
contract allows later resolution; quarantine malformed or contract-invalid input.
Do not call duplicates or late records invalid merely because they require
separate identity/time policy.

```python
@dataclass(frozen=True)
class Rejection:
    receipt_id: str
    record_locator: str
    contract_version: str
    reason_code: str
    safe_detail: str

def classify(raw: bytes, context: ValidationContext) -> Accepted | Rejection | Deferred:
    # Planned: bounded parsing and version-selected validators.
    ...
```

Reason codes are low-cardinality and stable; safe detail is bounded and redacted.
Raw payload access remains separate and more restricted.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Raw receipt | Immutable bytes and provenance | Ingestion owner | Retain according to policy | Untrusted evidence |
| Envelope/parser | Bounded format/version | Format/platform owner | Quarantine unsupported/corrupt input | Structurally assessed |
| Semantic validator | Versioned domain constraints | Source and data contract owners | Reject or defer with reason | Contract assessed |
| Reference resolver | Versioned reference snapshot | Reference owner | Defer or map unknown per policy | Context-dependent |
| Accepted dataset | One normalized accepted record | Data-product owner | Atomic versioned publication | Trusted for declared use |
| Quarantine | Rejection metadata and protected payload link | Ingestion/security owners | Alert if unavailable | Restricted |

## Schema and contract evolution

Compatibility is directional:

| Change | Possible effect | Safe approach |
| --- | --- | --- |
| Add optional field with stable default semantics | Old readers ignore; new readers accept old | Golden old/new writer-reader tests |
| Add required field | Old data/new reader failure | Expand as optional, backfill/observe, then require in a new contract |
| Rename field | Often remove plus add; meaning may split | Dual field/version, migrate, reconcile, retire |
| Widen numeric/string domain | Storage may support it while consumers do not | Inventory consumers and boundary-test values |
| Change units/time zone/meaning | Wire-compatible but semantically breaking | New field/contract version and explicit migration |
| Remove or redact field | Old consumers fail; retained raw still contains it | Usage/lineage review, dual versions, lifecycle repair |

Schema IDs must resolve to immutable definitions. Unknown versions stop or
quarantine according to the source agreement; silently applying latest is unsafe.
Mixed versions may coexist during rollout and replay.

## Identity, time, lifecycle, and reprocessing

A rejection identity includes receipt and record locator; it is not the logical
business key. Preserve producer event time, ingestion time, validation time,
reference-as-of time, schema version, and attempt time separately.

Quarantine transitions are `rejected -> triaged -> contract-fix | producer-fix |
waived -> reprocessed -> resolved`, with append-only audit. A repaired record
links to the rejection and original receipt; metrics retain both first-pass and
eventual outcomes so reprocessing does not erase incident evidence.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Parser accepts corrupt/trailing data | Mutation/property/golden tests | Fix versioned parser; replay retained raw; compare outputs |
| Validator deploy rejects good version | Version-segmented rejection spike | Stop rollout, restore prior accepted snapshot, replay with fixed version |
| Quarantine unavailable | Write failure before disposition commit | Pause acknowledgement/checkpoint or use approved durable fallback |
| Reference data late | Deferred-age/unknown-key metric | Retry against pinned newer reference; reconcile |
| Schema registry unavailable | Cache miss/lookup error | Use verified bounded cache or pause; never guess schema |
| Poison record loops | Attempt count/reason stable | Terminal quarantine with manual policy; keep normal flow moving |
| Reprocess duplicates accepted output | Identity/reconciliation failure | Version output and apply idempotent merge; repair affected scope |

Recovery completes when the cause is versioned, affected receipts are bounded,
reprocessing reconciles, and consumers receive a correction or confirmed no-op.

## Security, privacy, and governance

Parsers face malicious inputs: enforce byte, nesting, field-count, string, numeric,
decompression, and processing-time limits; avoid unsafe object deserialization.
Quarantine is not a dumping ground. Store only required evidence, segregate access,
encrypt, audit, expire, and delete it with derivatives. Redact payload fragments,
tokens, paths, SQL, and identifiers from logs and metrics. Approvals are required
for waivers that change acceptance semantics.

## Data quality, testing, and evidence

| Evidence | Fixture/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Boundary table | Missing/null/empty/type/range/encoding/size cases | Stable dispositions and reason codes | Pending |
| Property/fuzz | Arbitrary/truncated/nested/oversized bytes | No crash/hang/unbounded allocation | Pending |
| Compatibility matrix | Old/new writer and reader golden data | Declared pairs preserve intended meaning | Pending |
| Reference failure | Unknown/late/stale reference snapshots | Declared defer/reject behavior | Pending |
| Quarantine outage | Fail before/after rejection write | No acknowledged unaccounted input | Pending |
| Reprocess | Fix parser/schema/reference and rerun scope | Lineage preserved; outputs reconcile | Pending |

Fixtures prove deterministic validator behavior, not distributed registry,
quarantine durability, or production data distributions.

## Common pitfalls

### Pitfall: one “bad records” bucket

It merges actionable causes and makes safe replay impossible. Use stable reason,
stage, version, retryability, owner, and protected lineage metadata.

### Pitfall: logging the offending record

It duplicates sensitive data into a broadly accessible, long-lived system. Log a
receipt/rejection ID and safe bounded detail.

### Pitfall: schema-compatible means meaning-compatible

Changing cents to dollars may pass type checks and still corrupt every measure.
Version semantic changes and reconcile representative consumer results.

## Performance, capacity, cost, and operations

Budget encoded/expanded record size, parser CPU and allocation, reference lookup
latency/cache, quarantine write capacity, reason-cardinality, retained bytes, and
replay throughput. Measure records/bytes by stage and disposition, validation
latency percentiles, unknown schema/reference rates, first-pass acceptance,
quarantine age/volume, reprocess attempts, eventual resolution, and reconciliation.

Alerts segment by source and contract version without high-cardinality labels.
Runbooks identify the last good contract/code, stop unsafe acknowledgements,
preserve raw, estimate affected scope, roll back or forward, replay, and certify
reconciliation before closing.

## Compatibility, migration, and tradeoffs

Use expand/migrate/contract: accept and observe the new representation, dual-write
or translate where justified, migrate consumers, backfill/replay, compare semantic
outputs, then remove old support. Pin validators during replay.

| Need | Prefer | Tradeoff |
| --- | --- | --- |
| Fast edge protection | Minimal bounds/security envelope gate | Deeper invalid records reach durable raw |
| Forensic repair | Protected raw plus compact rejection metadata | Retention/privacy cost |
| Temporary missing reference | Deferred state with expiry and owner | More lifecycle/queue state |
| Stable operations | Low-cardinality reason taxonomy | Less free-form detail; use linked restricted evidence |

## Working example

- Python/data/tests: planned versioned event schemas, validator, protected rejection ledger, compatibility matrix, and replay tool
- Expected result: malformed and mixed-version records have safe deterministic outcomes
- Scale represented: none yet; local fixture planned
- Remaining risk: production distributions, registry/reference availability, quarantine security, and replay load

## Knowledge check

1. Classify framing, domain, reference, duplicate, and late-event cases.
2. Predict what happens when quarantine fails before acknowledgement.
3. Diagnose an acceptance drop isolated to one schema version.
4. Design a safe reason record for a payload containing customer data.
5. Evaluate whether changing milliseconds to seconds is schema-compatible and safe.
6. Plan a replay that preserves first-pass incident evidence.

## Key takeaways

- Validation is layered by trust and cost, not one boolean.
- Quarantine is a governed dataset with lineage and lifecycle.
- Deterministic reprocessing requires pinned code, schema, config, and reference state.
- Compatibility includes meaning and consumer behavior, not only wire types.
- Every observed record needs one explicit, reconcilable disposition.

## Resources

- [JSON Schema specification](https://json-schema.org/specification) (reviewed 2026-09)
- [Apache Avro 1.12.0 specification: Schema Resolution](https://avro.apache.org/docs/1.12.0/specification/#schema-resolution) (reviewed 2026-09)

## Related topics

- [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md)
- [Event ingestion, batching, and backpressure](06-event-ingestion-batching-and-backpressure.md)
- [Idempotency, deduplication, late data, and reconciliation](08-idempotency-deduplication-late-data-and-reconciliation.md)

## Completion checklist

- [x] Layered validation, dispositions, quarantine, compatibility, and replay explained
- [x] Security, time, failure, capacity, operations, migration, and evidence addressed
- [ ] Validator, fuzz/property, compatibility, quarantine, and replay evidence run
