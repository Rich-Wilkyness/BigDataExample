# Avro Records, Schemas, and Compatibility

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Serialization / Batch / Streaming / Storage  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Apache Avro is a schema-driven row serialization system. Its binary encoding
omits field names and per-value type tags, so correct reading depends on the
writer's schema and the reader's schema-resolution rules. Object container files
embed the writer schema and organize records into blocks separated by sync markers;
single-object encoding instead identifies a schema by fingerprint.

This guide focuses on records, unions, defaults, logical types, writer/reader
resolution, container boundaries, and evolution. RPC and code-generation APIs are
outside scope.

## Learning objectives

- Explain why Avro decoding requires the exact writer schema.
- Predict reader results when fields are added, removed, renamed, or promoted.
- Model optionality with unions without confusing a default with stored data.
- Choose between container files and single-object encoding.
- Design compatibility, corruption, and mixed-version evidence.

## Prerequisites

- Text versus binary and framing from guides 01 and 02
- Schema, null, identity, and migration reasoning from areas 02 and 03

## Mental model

```text
writer datum + writer schema -> bytes
bytes + writer schema + reader schema -> resolved reader datum
```

This resembles decoding a versioned Kotlin DTO with a serializer, except an Avro
reader does not infer absent writer fields from the runtime class. Resolution is
defined between two schemas, and field identity depends on Avro names/aliases—not
on Kotlin property position or a database column ID.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Writer schema | Schema used to encode the bytes; required for decoding |
| Reader schema | Schema describing values requested by the consumer |
| Schema resolution | Specification rules that reconcile writer and reader schemas |
| Union | Value selected from a listed set of schemas; commonly `null` plus one type |
| Default | Value supplied by resolution when the reader field is absent from writer data |
| Logical type | Semantic annotation over an Avro primitive/complex representation |
| Object container file | Header plus schema/codec metadata, sync marker, and data blocks |
| Fingerprint | Compact identifier derived from a schema's parsing canonical form |

## Reference schema

```json
{
  "type": "record",
  "name": "Event",
  "namespace": "example.mobile.v1",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "event_time_micros", "type": {"type": "long", "logicalType": "timestamp-micros"}},
    {"name": "event_name", "type": "string"},
    {"name": "user_id", "type": ["null", "string"], "default": null},
    {"name": "product_id", "type": ["null", "string"], "default": null},
    {"name": "quantity", "type": ["null", "long"], "default": null},
    {"name": "attributes", "type": {"type": "map", "values": "string"}, "default": {}},
    {"name": "schema_version", "type": "int", "default": 1}
  ]
}
```

This is a design sketch, not a verified repository schema. A production schema
also needs documentation of UTC semantics, controlled vocabularies, size bounds,
identity, and sensitive attributes; structural serialization does not enforce all
business invariants.

## Requirements and invariants

- Every payload can locate its exact writer schema through its container header
  or an authenticated, durable fingerprint-to-schema mapping.
- Readers never substitute the newest schema as the writer schema.
- Supported writer/reader pairs pass compatibility and semantic fixture tests.
- Defaults represent the reader's interpretation of absent historical fields;
  they do not rewrite old bytes or guarantee a producer emitted the value.
- Unions are deliberately ordered and their JSON/binary mappings are tested with
  the actual libraries in each language.
- Decimal precision/scale and timestamp unit/time-zone semantics are explicit.
- Unknown or unsupported schema fingerprints fail closed without losing raw data.

## Writer/reader resolution

Resolution matches named record fields by name, with aliases available for
controlled renames. Reader fields absent from the writer need a default or reading
fails. Writer fields absent from the reader are ignored. Certain numeric types can
be promoted, such as `int` to `long`, but narrowing and semantic reinterpretation
are not safe merely because application code can cast them.

Compatibility is directional:

- A new reader reading old data asks whether the new reader schema resolves each
  supported old writer schema.
- An old reader reading new data asks the reverse.
- “Full compatibility” is a registry policy term whose exact supported history
  window and algorithm must be named; it is not a universal Avro guarantee.

Adding a reader field with a default can support old writer data. Removing a
reader field commonly ignores new writer data, but downstream meaning can still
break. Renames require aliases and consumer tests. Changing a field from nullable
to required may strand historical nulls even if schema tooling accepts another
part of the change.

## Container and record boundaries

An Avro object container file stores its writer schema and codec in metadata, then
records in blocks. Sync markers let readers locate block boundaries and enable
format-aware splitting. A corrupt block should be a bounded failure domain only
if checks, offsets, and the reader implementation can safely find the next marker.

Single-object encoding stores a marker, schema fingerprint, and one datum. It
suits message-oriented storage only when the fingerprint registry is available,
durable, authorized, and protected from collisions/misassociation. Confluent-style
wire envelopes and registry compatibility modes are ecosystem protocols, not the
Avro single-object specification; identify which one is in use.

## Data flow, ownership, and trust boundaries

| Artifact | Authority and owner | Failure behavior |
| --- | --- | --- |
| Writer schema version | Producer contract owner | Registration/compatibility gate before use |
| Immutable Avro bytes | Landing/log owner | Preserve with checksum and source identity |
| Schema registry/catalog | Platform plus schema owners | Fail closed on unavailable/unauthorized schema |
| Reader schema/code | Consumer owner | Supports declared writer history window |
| Accepted event dataset | Data-product owner | Semantic validation and reconciliation after decode |

Schema text is untrusted metadata until its identity and authorization are
verified. Parsing a schema can itself consume resources; bound recursion, names,
and registry response sizes.

## Evolution decision table

| Proposed change | Likely structural path | Semantic question | Evidence required |
| --- | --- | --- | --- |
| Add optional `campaign_id` | Union with null plus default | Does absent mean unknown or not applicable? | Old/new cross-read matrix |
| Rename `user_id` | Reader alias during migration | Does identity meaning remain identical? | All-language alias fixtures |
| `int` to `long` | Allowed promotion in direction | Can every sink and old reader accept range? | Boundary and reverse-read tests |
| Change timestamp unit | New field/version | Does numeric reinterpretation change instants? | Instant reconciliation/backfill |
| Remove field | Stop reading, later stop writing | Are audit/backfill consumers retired? | Consumer inventory and historical read |

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Wrong writer schema used | Decode error or plausible corrupted values | Resolve exact header/fingerprint; quarantine and replay |
| Unknown fingerprint | Registry lookup miss | Retain bytes; restore/register authorized schema; retry |
| Incompatible deploy | Cross-version contract test or live decode failure | Roll back reader/writer; use expand/migrate/contract |
| Corrupt/truncated block | Block count/size, checksum/EOF failure | Do not publish partial dataset; replace or safely isolate block |
| Bad default | Semantic quality drift in historical reads | Version reader semantics; rebuild and reconcile |
| Registry unavailable | Lookup latency/error | Cache verified immutable schemas; fail according to freshness policy |

Retries operate on immutable bytes and a pinned reader version. A repaired reader
publishes a new dataset version; it does not silently overwrite a partially
consumed result.

## Security, privacy, and governance

Authorize schema registration separately from reading. Record subject/name,
fingerprint, owner, compatibility policy, review, and lifecycle. Do not place
secrets or unnecessary PII in schema documentation or container metadata. Bound
arrays, maps, strings, nesting, block sizes, decompression output, and schema
lookups. Avro is a data format, not encryption or authentication.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Golden binary round trip | Logical values, nulls, maps, and timestamps preserved | Pending |
| Writer/reader matrix | Every supported old/new direction matches declared policy | Pending |
| Mutation tests | Missing default, bad union, overflow, unknown enum/fingerprint fail | Pending |
| Container corruption | Header, truncated block, altered sync marker contained predictably | Pending |
| Cross-library fixture | Python and JVM implementations agree on canonical records | Pending |
| Size/throughput comparison | Bytes, CPU, memory, and blocks recorded against JSON Lines | Pending |

Passing a registry's compatibility check is contract evidence, not proof of
semantic compatibility or every implementation's behavior.

## Debugging and operations

Log safe schema fingerprint/full name/version, source object/version, block index
and byte range, codec, reader version, run ID, and error category. Monitor unknown
schemas, resolution failures, registry latency/cache age, block size/count,
compression ratio, rejects, and accepted/delivery reconciliation. Never label raw
IDs or full schema/payload text as low-cardinality metrics.

## Common pitfalls

### Pitfall: reading bytes with the expected schema as though it were the writer schema

Binary Avro lacks field names and inline type tags. The result can fail or appear
valid while values are misinterpreted. Always recover the exact writer schema.

### Pitfall: treating defaults as producer-populated values

Defaults participate in resolution. Old bytes remain absent, which matters for
lineage and the distinction between inferred and observed values.

### Pitfall: declaring compatibility from structure alone

A renamed meaning, changed unit, narrower sink, or new privacy classification can
break consumers while schemas resolve. Run semantic golden and downstream tests.

## Performance, capacity, and cost

Measure record width distribution, block size/count, compression ratio, encode/
decode throughput, registry cache hit rate, split parallelism, memory, and cross-
language overhead. Larger blocks can compress better but enlarge retry/corruption
domains and per-task memory. Schema resolution can be cached by immutable schema
identity; an unbounded cache creates another memory risk.

## Compatibility, migration, and delivery

Use expand/migrate/contract: register compatible reader support, deploy readers,
deploy writers, backfill if semantics require it, observe supported-history reads,
then retire old fields/schemas after consumer evidence. Store fixtures for every
supported writer version. Rollback must preserve the ability to read new bytes or
pause their production; reverting code alone may strand data already written.

## Working example

- Schema/data/tests: planned versioned Avro schemas, object containers, and compatibility matrix
- Expected result: canonical events preserved across supported evolution; corrupt/incompatible cases rejected
- Scale represented: none yet; block and distributed split behavior unverified
- Remaining risk: library/version differences, registry availability, and semantic changes

## Knowledge check

1. Explain writer schema versus reader schema without using “old” and “new.”
2. Predict reading v1 data after adding `campaign_id` with a null default.
3. Diagnose a plausible decode produced by supplying the wrong writer schema.
4. Design an old/new cross-library compatibility matrix for `quantity` widening.
5. Propose a safe timestamp-unit migration with rollback.
6. Corrupt one planned container block and define acceptable publication behavior.

## Key takeaways

- Binary Avro is compact because schema supplies structure and types.
- Compatibility is directional and structural; semantic compatibility needs more evidence.
- Defaults resolve absent writer fields rather than rewriting history.
- Container blocks and sync markers establish split and recovery domains.
- Registry authority, immutable schema identity, and cross-version tests are operational dependencies.

## Resources

- [Apache Avro 1.12.0 specification](https://avro.apache.org/docs/1.12.0/specification/) (reviewed 2026-09)

## Related topics

- [CSV, JSON, and JSON Lines](02-csv-json-and-json-lines.md)
- [Compression, splittability, and file sizing](06-compression-splittability-and-file-sizing.md)
- [Metadata, catalogs, schema, and partition evolution](08-metadata-catalogs-schema-and-partition-evolution.md)

## Completion checklist

- [x] Writer/reader schemas, resolution, defaults, unions, containers, and fingerprints explained
- [x] Compatibility, semantic risk, recovery, security, operations, and migration addressed
- [ ] Schemas, containers, cross-library tests, corruption, and performance evidence run

