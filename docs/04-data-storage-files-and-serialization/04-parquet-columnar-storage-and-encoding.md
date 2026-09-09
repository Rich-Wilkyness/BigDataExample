# Parquet Columnar Storage and Encoding

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Analytical storage / Batch / Query engines / Object storage  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Apache Parquet stores a table in column chunks organized within row groups, with
each column chunk divided into encoded and compressed pages. File metadata records
schema, locations, sizes, and optional statistics. Analytical readers can avoid
unrequested columns and may skip row groups/pages whose trustworthy metadata
proves they cannot match a predicate.

Parquet improves selected analytical access patterns; it does not supply table-
level transactions, object discovery, partition evolution, or semantic governance.

## Learning objectives

- Trace a logical row through row group, column chunk, page, encoding, and compression.
- Distinguish column projection, partition pruning, and predicate pushdown/filtering.
- Explain how statistics can avoid reads and how invalid statistics threaten correctness.
- Choose row-group/file sizes from workload and memory evidence.
- Design corruption, compatibility, pruning, and cross-engine tests.

## Prerequisites

- Logical rows, types, `NULL`, filters, and query plans from area 03
- Encoding, Avro schema evolution, compression, and publication concepts in this area

## Mental model

```text
Parquet file
  row group 0: [event_id chunk][event_time chunk][event_name chunk]...
                 pages...          pages...          pages...
  row group 1: [event_id chunk][event_time chunk][event_name chunk]...
  footer: schema + row groups + column metadata + offsets/statistics
```

A Room query that selects two columns is a partial analogy: avoiding unused data
can reduce work. It stops at the physical boundary because Parquet's pruning and
decoding are file metadata operations, and no database transaction manager or
index maintenance automatically coordinates a directory of files.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Row group | Horizontal logical partition of rows; primary parallel/read-skipping unit |
| Column chunk | Contiguous values for one column within one row group |
| Page | Encoded/compressed unit within a column chunk |
| Encoding | Representation such as dictionary or run-length encoding before/with compression |
| Projection | Reading only requested columns |
| Predicate pushdown | Reader/engine carries a filter toward scan; may enable pruning or early filtering |
| Statistics | Metadata such as null counts and lower/upper bounds used for planning/skipping |
| Footer | File metadata needed to locate and interpret row groups/columns |

## Requirements and invariants

The reference dataset has one accepted event per row and preserves stable field
identity, UTC microsecond instants, 64-bit quantity, and nullable fields. It targets
daily analytical scans that frequently select date, event name, product, and a
small subset of other columns.

- The authoritative logical schema and field IDs/names are versioned outside any
  one file; every file declares a compatible physical schema.
- Column projection cannot change row count, ordering contract, or values.
- Pruning is an optimization only: enabled and disabled scans return identical results.
- `NULL`, empty, NaN, decimal, timestamp, nested, and dictionary semantics are tested
  across the actual writers and readers.
- A file becomes discoverable only after its footer and integrity checks are durable.
- Partial or corrupt files never enter a committed dataset snapshot.

## Physical layout and access

Parquet writes each row group's column values contiguously. A query selecting
`event_time`, `event_name`, and `product_id` can omit the remaining column chunks,
reducing storage I/O, transfer, decompression, and decode work. It still reads the
selected columns for candidate row groups and must reconstruct nested/null state.

Within pages, encodings exploit patterns: dictionary encoding can replace repeated
strings with indexes; run-length/bit packing can compact repeated or small values;
delta encodings can help ordered values. Compression then operates on page data.
Effectiveness depends on cardinality, order, width, and implementation.

## Statistics and pruning

Suppose each row group records trustworthy `event_time` minimum/maximum. For a
predicate outside that interval, the reader may skip the row group. This differs
from filtering: pruning avoids reading a region; filtering evaluates candidate
rows. Partition pruning happens at dataset/file planning and is covered later.

Statistics require care for truncated bounds, NaN, signed/unsigned ordering,
legacy writers, logical types, and privacy. A reader must follow the specification
and implementation safety rules; blindly trusting malformed or incompatible
statistics can cause false negatives and wrong results. Sensitive lower/upper
bounds may also leak values through metadata even when column data is encrypted.

## SQL model

```sql
-- Logical contract; actual pruning must be confirmed in the engine scan plan.
SELECT event_name, COUNT(*) AS event_count
FROM events
WHERE event_time >= TIMESTAMP '2026-09-01 00:00:00+00:00'
  AND event_time <  TIMESTAMP '2026-09-02 00:00:00+00:00'
GROUP BY event_name;
```

The half-open UTC interval defines semantics. A plan should report files/row groups,
columns, pushed filters, and bytes considered/read. The SQL text alone proves none
of those physical optimizations.

## Data flow, ownership, and trust boundaries

| Boundary | Owner | Contract/failure behavior |
| --- | --- | --- |
| Accepted typed records | Data-product owner | Authoritative row semantics and identity |
| Parquet writer | Pipeline owner | Pinned schema/options; local temp/staging output |
| File validation | Publisher | Footer readable, counts/schema/stats/integrity pass |
| Dataset snapshot/catalog | Dataset owner | Only complete validated files become visible |
| Query engine | Platform/consumer | Supported features and safe pruning behavior tested |

A standalone file is derived data. The committed dataset snapshot defines which
files constitute the consumer-visible table.

## Row-group and file sizing

Larger row groups often improve compression and sequential I/O but increase writer
memory, minimum work, corruption/retry domains, and latency for selective access.
Tiny row groups multiply metadata and tasks. File size additionally affects object
requests, scheduling, compaction, and publication. Start from target query ranges,
available task memory, desired parallelism, and object-store costs, then measure a
size matrix; do not copy a universal “128 MB” rule without evidence.

Within a row group, data ordering changes statistics selectivity. Sorting or
clustering by event time may allow more skipping but costs write CPU/shuffle and
can worsen other predicates or skew. Record the chosen workload.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Truncated/missing footer | Reader/footer validation fails | Exclude staging file; rewrite from source records |
| Corrupt page | Checksum/decode/count failure where supported | Fail snapshot read or quarantine file; rebuild and recommit |
| Mixed incompatible schemas | Planning/read or contract check fails | Exclude bad files; publish corrected snapshot |
| Unsafe/incorrect statistics | Pruning-on/off results differ | Disable unsafe pruning for affected files; rewrite/upgrade |
| Too-large row group | Writer/read task OOM or tail latency | Reduce batch/row-group size based on profile; compact safely |
| Many tiny files | Planning/request/task overhead | Compact into a new snapshot; retain rollback until reconciliation |

Never “repair” a committed Parquet file in place. Rebuild immutable files and
atomically change dataset metadata so readers see an old or new file set.

## Security, privacy, and governance

Validate paths and schemas, restrict file/footer access, and assume metadata can
expose column names, counts, and value ranges. Parquet supports modular encryption,
but key retrieval, authorization, rotation, footer mode, and engine compatibility
need an end-to-end design. Compression and encoding are not encryption. Apply
retention/deletion to data files, staging files, snapshots, manifests, caches, and
backups according to the table owner.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Round trip | Canonical records including null/nested/time/large integer equal | Pending |
| Cross-engine matrix | Python/JVM/query engine agree for supported feature set | Pending |
| Projection test | Same rows/values; fewer columns/bytes read | Pending |
| Pruning mutation | Enabled/disabled identical; selected row groups match prediction | Pending |
| Corruption matrix | Header/footer/page/truncation never becomes committed partial output | Pending |
| Size/order matrix | Bytes, ratio, write/read CPU, memory, tasks, pruning recorded | Pending |

Small local files prove format behavior only for the tested libraries. They do not
prove distributed scheduling, object-store request behavior, or production skew.

## Debugging and operations

Capture dataset snapshot, file content checksum/size, writer library/version,
schema fingerprint, row count, row-group/page sizes, codec/encodings, statistics
availability, engine/version, selected files/groups/columns, bytes read, and run/
query ID. Use bounded-cardinality labels; file-level detail belongs in logs or
query profiles rather than metrics labels.

## Common pitfalls

### Pitfall: calling Parquet “a database”

The format defines files and metadata, not multi-file transactions, locks,
concurrent updates, catalogs, or access policy. Add a publication/catalog contract.

### Pitfall: saying predicate pushdown guarantees pruning

A pushed predicate may still read and filter every candidate. Verify actual
files, row groups, columns, and bytes in the engine plan/profile.

### Pitfall: optimizing compression ratio alone

The smallest file may cost more CPU, block parallel reads, or exceed memory and
latency objectives. Optimize total workload and operational cost.

## Performance, capacity, and cost

Record uncompressed/compressed bytes, row width/cardinality, row groups/files,
metadata/footer size, writer peak memory, encode/decode CPU, throughput, selected
versus read bytes, requests, task counts, spill, and latency percentiles. Test
cardinality, skew, order, codec, file size, row-group size, projection width, and
predicate selectivity one controlled dimension at a time.

## Compatibility, migration, and delivery

Schema evolution support varies by table metadata and engine, especially for
renames, nested fields, logical types, and field identity. Test mixed old/new files
against every supported reader. Write new immutable files, validate them, commit a
new snapshot, dual-read/reconcile, and retain the prior snapshot for rollback.
Rewriting history is a backfill with new lineage, not an invisible format update.

## Working example

- Python/data/tests: planned Parquet fixtures, metadata inspector, corruption mutations, and scan profiles
- Expected result: round-trip equality and measured projection/pruning/size behavior
- Scale represented: none yet; 3M events/day and 15-minute window are estimates
- Remaining risk: cross-engine features, distributed memory, object-store requests, and production distributions

## Knowledge check

1. Draw one row group with three column chunks and two pages per chunk.
2. Distinguish projection, predicate pushdown, row-group pruning, and partition pruning.
3. Predict why sorting by `event_time` can improve one query and hurt a write path.
4. Diagnose a pruning-on/off result mismatch and define immediate containment.
5. Design a row-group/file-size experiment with memory and cost measures.
6. Propose a safe rewrite-and-snapshot rollback for corrupt files.

## Key takeaways

- Row groups organize rows; column chunks and pages organize column data within them.
- Projection and trustworthy metadata can avoid work without changing query semantics.
- Parquet is a file format, not a table transaction or catalog.
- Physical size and ordering are workload hypotheses that require measurements.
- Immutable file replacement plus snapshot publication makes repair reviewable.

## Resources

- [Apache Parquet concepts](https://parquet.apache.org/docs/concepts/) (reviewed 2026-09)
- [Apache Parquet file-format metadata](https://parquet.apache.org/docs/file-format/metadata/) (reviewed 2026-09)
- [Apache Parquet format specification](https://github.com/apache/parquet-format) (reviewed 2026-09)

## Related topics

- [Arrow and in-memory columnar data](05-arrow-and-in-memory-columnar-data.md)
- [Compression, splittability, and file sizing](06-compression-splittability-and-file-sizing.md)
- [Metadata, catalogs, schema, and partition evolution](08-metadata-catalogs-schema-and-partition-evolution.md)

## Completion checklist

- [x] Row groups, chunks, pages, encoding, compression, projection, and pruning explained
- [x] Sizing, correctness, corruption, security, operations, and migration addressed
- [ ] Fixtures, scans, metadata inspection, cross-engine, and size evidence run

