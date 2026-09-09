# Arrow and In-Memory Columnar Data

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: In-memory analytics / Interprocess interchange / Python / JVM  
> Data scale: Single process and host; distributed estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Apache Arrow specifies a language-independent columnar memory layout and IPC
representations for tabular data. Arrays combine a logical type with buffers such
as validity bitmaps, fixed-width values, offsets, variable-width bytes, and child
arrays. Compatible components can share or transfer these buffers with fewer
row-by-row conversions.

Arrow is primarily an active-memory and interchange contract. It is not a durable
table, object-store publication protocol, query engine, or universal guarantee of
zero copying.

## Learning objectives

- Describe fixed-width, variable-width, null, dictionary, and nested Arrow layouts.
- Explain record batches, chunks, IPC streams/files, and schema metadata.
- Identify which operations can reuse buffers and which require allocation/copying.
- Manage buffer ownership and lifetime across Python/native/JVM boundaries.
- Compare Arrow's in-memory role with Parquet's durable analytical storage role.

## Prerequisites

- Python memory/iteration and process boundaries from area 02
- [Parquet columnar storage and encoding](04-parquet-columnar-storage-and-encoding.md)

## Mental model

```text
logical Utf8 array: ["a", null, "cat"]
validity bitmap:     1     0      1
offsets:             0     1      1      4
data bytes:          a c a t
```

This resembles a group of Kotlin primitive arrays plus a null bitmap and offsets,
which explains cache-friendly vector operations. The analogy stops at foreign
memory ownership: a Python object, native allocator, JVM wrapper, and downstream
engine may all reference the same buffers while only one component controls their
lifetime.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Array | Typed logical sequence represented by one or more buffers |
| Validity bitmap | One-bit-per-slot null/non-null representation when present |
| Offset buffer | Start positions delimiting variable-size values or children |
| Record batch | Equal-length ordered fields sharing one schema |
| Chunked array | Logical array composed of multiple physical arrays/chunks |
| IPC stream | Schema followed by sequential messages/record batches |
| IPC file | Random-access form with footer metadata |
| Zero-copy | Operation reuses existing data buffers; metadata/allocation may still occur |

## Requirements and invariants

The reference transfer batches accepted events between a reader and analytical
transform. It preserves field order/name/type, null validity, UTC timestamp unit,
64-bit quantity, nested attributes, and row count.

- Every field array in a record batch has the declared batch length.
- Buffer offsets and lengths are validated before access.
- Null and empty values remain distinguishable.
- Timestamp unit and time-zone metadata are part of the semantic contract.
- Producers do not mutate buffers while consumers may read them.
- The owner keeps buffers alive until every borrower has finished.
- Batch size is bounded by memory and latency budgets; transfer applies backpressure.

## Layouts and access

Fixed-width arrays usually use a validity bitmap and a contiguous values buffer.
Variable-width strings add offsets plus a data buffer. Struct arrays combine child
arrays; list arrays add offsets into a child. Dictionary encoding stores integer
indices and a separate values array. Slicing can often create a new view with an
offset over the same buffers, but filtering, sorting, concatenating incompatible
dictionaries, casting, or crossing a non-Arrow API often allocates.

Record batches bound work and transport. A table may contain chunked columns whose
chunks do not match downstream batch assumptions; combining chunks can copy large
buffers. An Arrow schema provides physical/logical types and metadata, but business
constraints such as uniqueness, allowed event names, and ownership remain external.

## Arrow, Parquet, and application objects

| Representation | Optimized boundary | Strength | Missing guarantee |
| --- | --- | --- | --- |
| Python/Kotlin row objects | Application logic | Natural per-record behavior | Compact/vector layout and cross-language ABI |
| Arrow | Active columnar memory/IPC | Vector access and interoperable buffers | Durable dataset lifecycle/publication |
| Parquet | Durable analytical file | Projection, encoding, compression, statistics | Ready-to-compute memory and table commit |

Reading Parquet into Arrow normally involves I/O, decompression, decoding, and
allocation even though both are columnar. Writing Arrow to Parquet similarly
encodes/compresses rather than dumping memory bytes unchanged.

## Data flow, ownership, and trust boundaries

| Boundary | Owner | Lifetime/failure contract |
| --- | --- | --- |
| Parquet/other reader | Reader adapter | Produces bounded batches; validates external bytes |
| Arrow allocator/buffers | Runtime component | Accounts memory; remains live through last consumer |
| Transform | Data-product code | Treats borrowed inputs as immutable; owns outputs |
| IPC transport | Platform boundary | Frames schema/messages; applies size and flow control |
| Sink | Consumer | Acknowledges only after durable handling |

Shared memory is a trust boundary. A process able to mutate or read the mapped
region may violate isolation even when language wrappers appear immutable.

## Zero-copy reasoning

Ask four questions for any “zero-copy” claim:

1. Which specific buffers are reused?
2. Are offsets/validity/schema metadata copied or rebuilt?
3. Does casting, alignment, endianness, chunk consolidation, device transfer, or
   garbage collection force a copy?
4. Who owns memory and what event proves the borrower is finished?

Avoiding one data-buffer copy can still leave serialization, kernel/network copies,
decompression, and allocations elsewhere. Measure end-to-end CPU, memory, and
latency rather than marketing labels.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Buffer freed too early | Crash, invalid read, corrupted values | Fix ownership/reference lifetime; replay source batch |
| Unbounded batches | Allocator limit/OOM/long pauses | Cap rows and bytes; backpressure and retry smaller units |
| Schema mismatch | IPC/read/cast failure | Negotiate/version schema; reject unsupported batch |
| Invalid offsets | Validation failure or unsafe native access | Reject input before kernel execution |
| Dictionary disagreement | Wrong labels or merge failure | Unify/remap dictionaries explicitly and test nulls |
| Consumer dies before ack | Missing durable acknowledgement | Retain/replay batch; deduplicate at sink identity boundary |

Arrow buffers are derived and normally rebuildable. Recovery restarts from a
durable source/checkpoint, not from assumed surviving process memory.

## Security, privacy, and governance

Validate IPC metadata, recursion, buffer sizes, offsets, and compression before
allocation or native kernels. Limit shared-memory permissions and erase/release
sensitive buffers according to runtime guarantees; memory reuse can retain bytes.
Schema metadata and dictionary values may contain sensitive information. Arrow
does not provide encryption, authentication, tenant isolation, or durable deletion.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Layout fixtures | Null/empty/string/nested/dictionary buffers match prediction | Pending |
| Round trip | Python IPC to supported JVM reader preserves canonical records | Pending |
| Slice/filter/cast audit | Reused versus allocated buffers identified | Pending |
| Lifetime fault | Early release is caught/contained by owned wrapper design | Pending |
| Batch-size sweep | Throughput, peak memory, and latency curve recorded | Pending |
| Malformed IPC | Invalid lengths/offsets/nesting rejected within resource budget | Pending |

Process-local success does not prove shared-memory safety, network transport, GPU
behavior, or distributed executor memory.

## Debugging and operations

Capture schema fingerprint, batch rows/bytes, buffer bytes, null counts, chunk
counts, allocator current/peak memory, queue depth, processing/transfer latency,
copy/cast operations where observable, producer/consumer versions, and correlation
ID. Do not label metrics with field names from untrusted schemas without bounding.

## Common pitfalls

### Pitfall: equating columnar with durable

Arrow memory disappears with the process unless explicitly serialized and
published. Use a durable file/table contract for recovery.

### Pitfall: claiming an entire pipeline is zero-copy

One adapter may share a values buffer while casts, IPC, decompression, or the sink
copies it. Name and measure the exact boundary.

### Pitfall: ignoring memory ownership

Garbage collection in one runtime does not understand every foreign borrow. Use
documented lifetime handles and close/release in dependency order.

## Performance, capacity, and cost

Budget source batch bytes + decoded Arrow buffers + validity/offset/dictionary
buffers + transform outputs + concurrency + temporary casts. Measure allocator
peak, resident memory, batch p50/p99 size, throughput, latency, cache behavior,
copies, and queue depth. Larger batches amortize call overhead and enable vector
kernels but increase latency, allocation spikes, and retry scope.

## Compatibility, migration, and delivery

Pin the Arrow format/library feature set across languages and test schema metadata,
extension types, dictionary behavior, IPC versions, timestamps, decimals, and
nested types. Deploy readers before writers use new fields/features. Dual-transfer
canonical fixtures, observe memory and errors, then cut over. Rollback requires
the producer to continue emitting a representation the old consumer understands.

## Working example

- Python/JVM/data/tests: planned Arrow batch builder, IPC transfer, and buffer inspector
- Expected result: canonical record equivalence with measured memory/copy behavior
- Scale represented: none yet; single-host first
- Remaining risk: native-library compatibility, foreign memory lifetime, and distributed executors

## Knowledge check

1. Draw buffers for `["a", null, "cat"]` and explain null versus empty.
2. Name an operation likely to share buffers and one likely to allocate.
3. Diagnose a use-after-free across a Python/native boundary.
4. Estimate memory for four concurrent input and output batches with overhead.
5. Design a cross-language timestamp and dictionary compatibility test.
6. Modify a planned batch-size limit and predict throughput and latency changes.

## Key takeaways

- Arrow defines typed columnar arrays as buffers plus metadata.
- Record batches bound transfer and computation; chunking affects materialization.
- Zero-copy is a precise boundary claim, not an end-to-end default.
- Buffer ownership, immutability, and backpressure are correctness requirements.
- Arrow complements rather than replaces Parquet and dataset metadata.

## Resources

- [Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html) (format 1.5; reviewed 2026-09)
- [Apache Arrow format specifications](https://arrow.apache.org/docs/format/) (reviewed 2026-09)

## Related topics

- [Parquet columnar storage and encoding](04-parquet-columnar-storage-and-encoding.md)
- [Compression, splittability, and file sizing](06-compression-splittability-and-file-sizing.md)

## Completion checklist

- [x] Buffers, arrays, batches, chunks, IPC, lifetime, and zero-copy limits explained
- [x] Interoperability, security, failure, capacity, and migration addressed
- [ ] Cross-language, buffer, malformed-input, lifetime, and performance evidence run

