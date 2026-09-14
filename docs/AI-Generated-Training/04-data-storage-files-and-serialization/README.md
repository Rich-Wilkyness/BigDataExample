# 04 Data Storage, Files, and Serialization

> Area status: Documentation complete; executable reference fixtures planned  
> Level: Beginner to Intermediate data engineering  
> Applies to: Files / Serialization / Storage / Batch / Analytical interchange  
> Reference scenario: Versioned mobile-event deliveries and partitioned datasets  
> Evidence boundary: Documentation and contract review; no format library or object-store execution yet  
> Last reviewed: 2026-09

## Purpose

This area explains how logical records become bytes, files, and discoverable
datasets. The durable lesson is that a filename extension does not define a safe
contract. A consumer also needs the byte encoding, record framing, schema and
null semantics, compression and split behavior, publication boundary, and the
metadata that identifies the current dataset version.

For an Android engineer, a file format is loosely comparable to a versioned
Parcelable or Room schema at an application boundary. The analogy helps with
explicit types and compatibility tests. It stops when one dataset spans thousands
of independently written objects, readers project only a few columns, and no
single filesystem transaction makes the whole result visible atomically.

## Prerequisites

- Complete [01 Big Data and Data Engineering Foundations](../01-big-data-and-data-engineering-foundations/README.md), especially grain, authority, derived data, and commit boundaries.
- Be able to read bounded Python examples from [02 Python for Data Engineering](../02-python-for-data-engineering/README.md).
- Understand keys, `NULL`, analytical access, and transactions from [03 SQL and Analytical Querying](../03-sql-and-analytical-querying/README.md).
- No Avro, Parquet, Arrow, distributed filesystem, object store, or catalog is required for this documentation pass.

## Learning path

1. [Bytes, text, encodings, and record boundaries](01-bytes-text-encodings-and-record-boundaries.md)
   establishes the physical boundary and shows why decoding and framing are separate operations.
2. [CSV, JSON, and JSON Lines](02-csv-json-and-json-lines.md) compares common text interchange formats and their ambiguous type contracts.
3. [Avro records, schemas, and compatibility](03-avro-records-schemas-and-compatibility.md) introduces writer/reader schema resolution and binary row serialization.
4. [Parquet columnar storage and encoding](04-parquet-columnar-storage-and-encoding.md) connects row groups, pages, statistics, projection, and predicate pushdown.
5. [Arrow and in-memory columnar data](05-arrow-and-in-memory-columnar-data.md) distinguishes an in-memory interchange layout from durable storage.
6. [Compression, splittability, and file sizing](06-compression-splittability-and-file-sizing.md) treats codec and object size as execution-plan inputs.
7. [Object-storage layouts, partitioning, and publication](07-object-storage-layouts-partitioning-and-publication.md) defines immutable keys, manifests, and dataset-level visibility.
8. [Metadata, catalogs, schema, and partition evolution](08-metadata-catalogs-schema-and-partition-evolution.md) makes logical identity and safe historical change explicit.

## Shared reference contract

The planned example begins with delivery envelopes and publishes accepted logical
events. Every format must preserve or explicitly reject the following contract:

| Field | Logical contract | Important edge |
| --- | --- | --- |
| `delivery_id` | Non-empty string; unique per received envelope | Retry creates a new delivery, not a new event |
| `event_id` | Non-empty stable business identity | Duplicate deliveries may repeat it |
| `event_time` | UTC instant at microsecond precision | Offset text must normalize without changing the instant |
| `event_name` | Controlled string vocabulary | Unknown values are quarantined |
| `user_id` | Nullable string | Missing, explicit null, and empty string are distinct |
| `product_id` | Nullable string | Required only for named product events |
| `quantity` | Nullable 64-bit integer | JSON numbers must not silently become lossy floats |
| `attributes` | Bounded string-to-string map | Size and sensitive-key policy apply |
| `schema_version` | Positive integer | Selects the producer contract, not merely parser code |

```text
untrusted byte stream
    -> decode + frame
    -> parse text or binary container
    -> resolve schema + validate semantics
    -> immutable accepted records / safe quarantine
    -> write sized files to staging keys
    -> validate manifests and metrics
    -> commit one dataset snapshot in the catalog
    -> readers plan files, row groups, and columns
```

The starting estimate is 3 million accepted events per day, roughly 3 GiB/day
before columnar encoding and compression, 35 days of hot analytical retention,
and a daily publication window of 15 minutes. These are continuity assumptions
from earlier areas, not measurements. Planned evidence will use small deterministic
fixtures first and must not be described as distributed or production proof.

## Format-selection frame

| Need | Plausible starting point | Main limitation to test |
| --- | --- | --- |
| Human exchange with spreadsheet tools | CSV with an explicit sidecar contract | Weak nested/type/null semantics and dialect drift |
| Human-readable nested messages | JSON Lines | Number/time semantics, size, repeated keys, and malformed-record isolation |
| Compact row records with schema resolution | Avro object container | Library compatibility and schema-governance discipline |
| Durable analytical scans over selected columns | Parquet | Row-group sizing, statistics safety, and append/publication design |
| In-process or cross-process analytical interchange | Arrow | Buffer lifetime, memory bounds, and semantic metadata |

This is a requirements table, not a ranking. A pipeline commonly uses more than
one representation at different boundaries.

## Evidence and scope

The guides include contract sketches, failure cases, decision tables, and exact
future evidence. No round-trip, compatibility, corruption, compression, pruning,
size, real-library, object-store, or catalog test has run. The working example is
therefore Planned throughout this area.

Database pages and transaction logs, distributed filesystem internals, streaming
message brokers, table-format implementation tutorials, storage hardware design,
and vendor-specific administration are outside this area. Later areas build on
these storage guarantees for ingestion, batch, distributed processing, lakes,
lakehouses, governance, and operations.

## Area completion checklist

- [x] Eight inventory guides authored in the planned order
- [x] Encoding, framing, type, null, identity, ordering, and time contracts covered
- [x] Row and column formats distinguished from in-memory representation
- [x] Compression, splitting, file sizing, partitioning, and publication connected
- [x] Catalog authority, schema evolution, partition evolution, security, and repair documented
- [x] Evidence limitations recorded without claiming runtime verification
- [ ] Versioned CSV/JSON/Avro/Parquet fixtures implemented
- [ ] Round-trip, compatibility, corruption, compression, pruning, and size tests executed
- [ ] Object-store publication and catalog integration behavior verified

