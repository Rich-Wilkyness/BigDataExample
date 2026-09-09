# Compression, Splittability, and File Sizing

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Files / Storage / Batch / Distributed processing  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Compression trades representation size and I/O/network cost for CPU, memory, and
recovery behavior. Splittability determines whether independent workers can start
at safe boundaries without processing all preceding compressed bytes. File sizing
then determines planning requests, task parallelism, retry domains, metadata load,
and the small-file problem.

Codec, format block structure, file size, and data order must be evaluated together.
There is no universally optimal codec or target size.

## Learning objectives

- Distinguish compression ratio, throughput, latency, and total workload cost.
- Explain why a compressed stream may be non-splittable while a container is splittable by blocks.
- Model file counts, task parallelism, requests, memory, and recovery scope.
- Diagnose small-file amplification and oversized-file under-parallelism.
- Design a representative codec/size/order benchmark and safe compaction workflow.

## Prerequisites

- Record framing and container blocks from guides 01 and 03
- Parquet row groups/pages and Arrow memory from guides 04 and 05

## Mental model

```text
logical values
  -> format encoding (dictionary/delta/RLE)
  -> compression block/stream (codec)
  -> file/object
  -> split planning -> task -> decompress -> decode -> rows
```

APK compression is a limited analogy: smaller transfer can cost CPU to unpack.
It stops because a data engine also needs many workers to seek to independent
record/container boundaries, and object request/task overhead repeats per file.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Compression ratio | Uncompressed bytes divided by compressed bytes; state convention explicitly |
| Codec | Compression/decompression algorithm and framing implementation |
| Splittable | Independent reader can begin near a planned byte range using valid boundaries/state |
| Split | Logical unit offered to one read task; not necessarily one file |
| Small-file problem | Per-file metadata/request/task overhead dominates useful work |
| Compaction | Rewriting many input files into fewer/sized files under a new commit |
| Amplification | Extra metadata, requests, reads, writes, or retries relative to useful data |

## Requirements, estimates, and invariants

The reference dataset begins at 3 million rows and roughly 3 GiB uncompressed per
day. Daily output must publish in 15 minutes and support selective analytical
reads. These estimates will be invalidated by measured row width, compression,
skew, request latency, or cluster capacity.

- Compression never changes canonical decoded records.
- A reader starts only at format/codec-approved boundaries.
- Planned parallelism is sufficient without creating unbounded tasks or requests.
- Writers and readers stay within per-task memory and temporary-storage budgets.
- Compaction preserves row identity/count/schema/partition membership and publishes atomically.
- Raw and compacted versions have explicit retention and rollback ownership.

## Codec and format interaction

Compressing a whole newline file as one stream can require reading from the stream
start because decoder state is not available at arbitrary offsets. A splittable
container instead records independent blocks, sync points, or indexed boundaries.
Parquet compresses pages inside column chunks and plans work at file/row-group
boundaries; Avro containers use data blocks and sync markers.

“Gzip is not splittable” is shorthand that needs a boundary: a conventional single
gzip member is generally sequential for common distributed readers, while a
dataset of many gzip files can run files in parallel and specialized indexes or
multi-member designs may change behavior. Verify the exact engine and codec.

## Decision table

| Workload constraint | Direction to test | Why | Counter-cost |
| --- | --- | --- | --- |
| Network/object I/O dominates | Stronger compression | Fewer transferred bytes | More CPU/latency |
| CPU saturated, local fast storage | Faster codec or no compression | More decode throughput | More bytes and requests/time |
| Large distributed scans | Splittable block/container | Parallel readers | Metadata/block overhead |
| Selective repeated values | Column encoding + compression | Better locality and redundancy | Writer complexity/memory |
| Frequent tiny arrivals | Buffer then compact | Reduce file/task amplification | Added freshness and rewrite cost |

Codec names are insufficient: record codec version/level, library, format settings,
data ordering, hardware, concurrency, warm/cold state, and encrypted/compressed
interaction.

## File sizing and parallelism

For compressed dataset bytes `B`, average file size `F`, and available scan slots
`W`, an initial model is:

```text
file_count = ceil(B / F)
parallel_waves ~= ceil(file_count / W)
request_overhead ~= file_count * requests_per_file * request_cost
```

This ignores pruning, skew, row groups, retries, metadata, throttling, locality,
and variable file sizes, but makes assumptions reviewable. Too few large files
limit parallelism and enlarge retries; too many small files multiply listings,
opens, footers, requests, tasks, scheduler state, and catalog metadata.

Size targets should normally refer to compressed on-storage bytes plus row-group/
block objectives, not unqualified “file size.” Track distribution, not average
alone, because a few oversized files determine tail latency.

## Data flow, ownership, and trust boundaries

| Boundary | Owner | Contract |
| --- | --- | --- |
| Writer settings | Pipeline/data-product team | Codec, level, block/row-group and target file bounds |
| Storage objects | Storage platform | Immutable bytes, integrity, request/throttle behavior |
| Split planner | Query/compute engine | Safe format-aware boundaries and task admission |
| Compaction job | Dataset owner | Snapshot input, identity-preserving output, atomic commit |
| Capacity/cost evidence | Platform plus product | Reproducible workload and unit-priced estimates |

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Non-splittable huge file | One long task, low utilization | Rewrite to a splittable container/sized objects |
| Tiny-file explosion | Planning latency, requests/tasks, catalog pressure | Compact committed snapshot; fix writer batching |
| Decompression bomb/corrupt length | Ratio/output bound or decoder failure | Abort/quarantine; never allocate from untrusted size alone |
| Hot/oversized partition file | Tail task and memory failure | Rebalance partitioning and size; mitigate skew |
| Compaction partial output | Staging/manifest mismatch | Leave old snapshot current; clean orphan staging later |
| Codec unsupported by reader | Compatibility gate/read failure | Block commit or roll back feature; rewrite with supported codec |

Retry cost is the split/block/file recovery domain, not simply the corrupt record.
Completion evidence includes old/new count and key reconciliation, readable output,
consumer objectives, and removal of unreferenced objects only after rollback expiry.

## Security, privacy, and governance

Bound decompressed bytes, expansion ratio, nesting, blocks, and CPU time for
untrusted content. Compression side channels matter when secrets and attacker-
controlled values share contexts; avoid designs that expose size-based oracle
behavior. Encrypt after compression in normal pipelines because ciphertext is not
meaningfully compressible, while ensuring metadata and key policy cover all files.
Compaction must preserve retention, deletion, lineage, and legal-hold rules.

## Data quality, testing, and evidence

| Evidence | Matrix | Expected result | Result |
| --- | --- | --- | --- |
| Round trip | Codec/level x format x null/skew/order | Canonical records identical | Pending |
| Size/throughput | Representative event fixture | Ratio, encode/decode CPU and p95 recorded | Pending |
| Split behavior | Large text/Avro/Parquet files | Planned task boundaries and no loss/duplication | Pending |
| File-size sweep | Small/target/large with fixed total bytes | Planning, requests, waves, memory, tail latency | Pending |
| Corruption/expansion | Truncated blocks and high-ratio input | Bounded containment and no partial commit | Pending |
| Compaction | Duplicates/nulls/partitions/schema versions | Counts, keys, values, and membership reconcile | Pending |

## Debugging and operations

Track input/output/uncompressed bytes, ratio convention, codec/version/level,
file/block/row-group counts and size percentiles, task waves/duration/skew, open/
list/range requests, throttles, CPU, peak memory, temporary bytes, retries, and
compaction rewrite amplification. Correlate dataset snapshot, partition, file, job,
and configuration version without turning file IDs into metric labels.

## Common pitfalls

### Pitfall: choosing the smallest output in a microbenchmark

It may violate batch latency, CPU, memory, reader support, or selective-scan needs.
Compare the end-to-end workload under concurrency.

### Pitfall: treating file count as harmless

Each object adds metadata, requests, scheduling, and failure/reconciliation work.
Monitor distributions and planning time before query latency collapses.

### Pitfall: compacting in place

Readers can see missing/duplicated mixtures. Write new immutable files, validate,
then swap the snapshot/manifest pointer.

## Performance, capacity, and cost

Define budgets for publication time, scan latency, writer/reader CPU, task memory,
requests, storage, network, temporary space, and recovery. Benchmark cold and warm
paths with representative width, cardinality, repetition, sort order, null rates,
partitions, concurrency, and failure. Convert measurements to monetary estimates
using current platform prices only when the target platform is selected.

## Compatibility, migration, and delivery

Before changing codec, level, size, or container block settings, inventory every
reader and supported library version. Write a canary partition/snapshot, run
cross-reader correctness and capacity tests, dual-read/reconcile, then expand.
Keep the old snapshot through rollback and recovery objectives. Historical rewrite
is optional unless requirements demand uniformity; mixed files must remain readable.

## Working example

- Scripts/data/tests: planned codec and file-size matrix plus atomic compaction simulation
- Expected result: identical records with measured byte/CPU/memory/split/task tradeoffs
- Scale represented: none yet; 3 GiB/day estimate only
- Remaining risk: distributed scheduler, storage request cost, throttling, and production skew

## Knowledge check

1. Explain why format framing and codec splittability must be considered together.
2. Calculate files and minimum waves for 300 GiB at 256 MiB and 100 slots.
3. Diagnose low cluster utilization while one compressed input task runs for hours.
4. Design a matrix that avoids comparing codecs on different data orderings.
5. Propose an atomic small-file compaction and rollback procedure.
6. Predict how doubling batch/file targets affects freshness, memory, and requests.

## Key takeaways

- Compression trades bytes for CPU, memory, latency, and compatibility.
- Safe parallelism depends on format-aware boundaries, not extension alone.
- Both tiny and oversized files amplify different costs and failures.
- Compaction is a versioned dataset rewrite with reconciliation and rollback.
- Representative end-to-end evidence beats universal codec or file-size rules.

## Resources

- [Apache Hadoop `SplittableCompressionCodec` API](https://hadoop.apache.org/docs/current/api/org/apache/hadoop/io/compress/SplittableCompressionCodec.html) (reviewed 2026-09)
- [Apache Avro object container specification](https://avro.apache.org/docs/1.12.0/specification/#object-container-files) (reviewed 2026-09)
- [Apache Parquet concepts](https://parquet.apache.org/docs/concepts/) (reviewed 2026-09)

## Related topics

- [Avro records, schemas, and compatibility](03-avro-records-schemas-and-compatibility.md)
- [Parquet columnar storage and encoding](04-parquet-columnar-storage-and-encoding.md)
- [Object-storage layouts, partitioning, and publication](07-object-storage-layouts-partitioning-and-publication.md)

## Completion checklist

- [x] Codec, encoding, split, sizing, small-file, compaction, and cost models explained
- [x] Bounds, corruption, recovery, security, migration, and observability addressed
- [ ] Round-trip, codec, split, sizing, corruption, and compaction evidence run

