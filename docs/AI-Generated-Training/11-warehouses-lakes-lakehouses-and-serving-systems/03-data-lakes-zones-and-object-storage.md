# Data Lakes, Zones, and Object Storage

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Data lake / Object storage / Files / Governance  
> Data scale: Local metadata design; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A data lake stores durable datasets in file formats on scalable storage while
allowing multiple engines and use cases. Object storage supplies immutable-like
objects, keys, conditional requests, and lifecycle policies; it does not by itself
supply table identity, transactions, schema authority, complete listings, or safe
multi-file publication.

Zones are trust and lifecycle boundaries, not decorative folders. This guide
covers landing, quarantine, validated, curated, and published data; open files,
discovery, retention, and lake failure modes. Table formats follow in Guide 04.

## Learning objectives

- Separate object, file, dataset, table, and catalog contracts.
- Design zones by trust, owner, mutability, and consumer permission.
- Publish multi-file datasets through immutable generations and manifests.
- Explain discovery, small-file, partition, retention, and deletion failure modes.
- Define evidence for a lake that is recoverable rather than merely cheap storage.

## Prerequisites

- [Object-storage layouts, partitioning, and publication](../04-data-storage-files-and-serialization/07-object-storage-layouts-partitioning-and-publication.md)
- [Metadata, catalogs, schema, and partition evolution](../04-data-storage-files-and-serialization/08-metadata-catalogs-schema-and-partition-evolution.md)
- [ETL, ELT, staging, and layer responsibilities](../07-batch-processing-and-etl-elt/01-etl-elt-staging-and-layer-responsibilities.md)
- [Storage and serving system selection](01-storage-and-serving-system-selection.md)

## Mental model and terminology

```text
untrusted bytes -> landing generation -> validate -> quarantine + accepted
                                                    |
                                                    v
                                            curated generation
                                                    |
                                      manifest/catalog publication
                                                    v
                                             governed consumers
```

Android asset directories are a useful analogy for named immutable files. The
analogy stops because an object prefix is not a transactional directory, listings
are an API operation rather than table metadata, and thousands of distributed
writers/readers need an explicit publication protocol.

| Term | Meaning in this guide |
| --- | --- |
| Object | Bytes addressed by a key with service metadata and version behavior |
| Dataset | Related records/files governed as one logical contract |
| Zone | Boundary with declared trust, ownership, mutation, retention, and access policy |
| Generation | Immutable candidate set of data files for one dataset publication |
| Manifest | Authoritative enumeration of files and metadata in a generation |
| Data swamp | Stored data whose identity, ownership, contracts, discovery, or quality are unreliable |

## Requirements, scale assumptions, and invariants

Assume 3 GiB/day arriving in bursts, 35-day hot replay, seven-year curated fact
retention, 128–512 MiB target analytical files as an initial hypothesis, 15-minute
freshness, multiple engines, and tenant-restricted access. Measure before fixing
file sizes or partition schemes.

- Object keys are never inferred as the sole table authority from an ad hoc listing.
- Data files are immutable after publication; correction creates a new generation.
- Every generation declares schema, partition spec, files, checksums/counts, source frontier, and parent.
- Untrusted landing data cannot be queried as certified data.
- Accepted, rejected, duplicated, and omitted records reconcile to source input.
- Retention and deletion operate on references and legal policy, not age alone.
- Consumers observe one published generation, never an in-progress prefix.

## Data flow, ownership, and trust boundaries

| Zone | Grain/contract | Owner | Access and failure behavior |
| --- | --- | --- | --- |
| Landing | Source delivery bytes plus receipt metadata | Ingestion owner | Append-only, restricted, bounded retention |
| Quarantine | Rejected delivery plus safe reason/reference | Contract owner | Highly restricted; replay after repair |
| Validated | Typed accepted records and dispositions | Pipeline owner | Internal input; versioned schema |
| Curated | Modeled facts/dimensions at declared grain | Dataset owner | Governed, quality-gated generations |
| Published | Stable dataset/table reference | Domain owner | Consumer contract and SLO |
| Temporary | Shuffle/stage/candidate files | Job/platform owner | No consumer access; bounded cleanup |

Names such as bronze/silver/gold can communicate progression but do not define
these contracts. Record the actual guarantees.

## Object and dataset publication

```json
{
  "dataset": "product_event_fact",
  "publication_id": "pub-2026-09-07T020000Z",
  "parent": "pub-2026-09-06T020000Z",
  "schema_version": 3,
  "partition_spec_version": 2,
  "source_frontier": {"product-events": {"0": 41822, "1": 39911}},
  "files": [
    {"key": "candidate/pub-.../event_date=2026-09-06/part-000.parquet",
     "bytes": 201445376, "rows": 192004, "sha256": "..."}
  ]
}
```

Writers upload uniquely named candidate files, validate them, create an immutable
manifest, then conditionally update a small authoritative pointer/catalog entry
from the expected parent to the new publication. A compare-and-set failure means
the writer lost a race and must rebase or abort. After a timeout, read the pointer
before retrying. A rename/copy loop is not assumed atomic.

```python
def publish(expected_parent: str, candidate: str, catalog: "Catalog") -> str:
    # Planned protocol model: the catalog must implement atomic compare-and-set.
    current = catalog.current("product_event_fact")
    if current != expected_parent:
        raise RuntimeError("stale writer")
    return catalog.compare_and_set(expected_parent, candidate)
```

Application code cannot manufacture conditional durability, list consistency, or
cross-object transactions; use and test the storage/catalog primitives actually
provided.

## Layout, partitioning, and discovery

Partition on common selective predicates with bounded cardinality and enough data
per partition. Avoid user IDs, raw timestamps, and unstable business values in
paths. A date partition does not prove event-time completeness. Record partition
spec versions so evolution does not omit old layouts.

Discovery through recursive listing scales with object count and can include
candidates, orphans, and mixed schemas. Prefer authoritative manifests/table
metadata for reads. Catalog search, owners, descriptions, lineage, quality,
classifications, and sample-safe statistics make data discoverable.

## Lifecycle, consistency, identity, and time

An object progresses through upload, verification, candidate reference,
publication, supersession, expiration eligibility, and deletion. A dataset
snapshot owns references; a file name does not define record identity. Preserve
event time, ingestion time, source frontier, publication time, and retention
eligibility separately.

Readers pin one publication for repeatable work. A latest pointer provides a new
starting snapshot, not live mutation of an already pinned job.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Truncated/corrupt object | Size/checksum/footer validation | Reject generation; re-upload immutable candidate |
| Writer dies before commit | Candidate age and run ledger | Keep invisible; resume or garbage-collect after safety horizon |
| Unknown pointer update | Read authoritative pointer/publication ID | Accept committed result or retry with same identity |
| Missing referenced object | Manifest verification and read errors | Stop snapshot; restore object or roll back pointer |
| Mixed schemas/layouts | Manifest schema/spec IDs and contract test | Read by version or rewrite isolated generation |
| Small-file explosion | File counts, planning/list/request latency | Compact to new snapshot; expire safely later |
| Unsafe lifecycle deletion | Reference audit/restore test | Halt policy; restore version/backup and repair references |

Recovery completes when the current manifest is closed and readable, files match
checksums/counts, source reconciliation passes, and orphan cleanup cannot touch
any retained snapshot.

## Security, privacy, and governance

Use separate identities and policies per zone, deny public access, constrain
write/delete administration, and protect catalog updates more tightly than bulk
reads. Encrypt and rotate keys; do not put sensitive values in object keys,
manifests, logs, or tags. Enforce tenant and column/row restrictions in every
engine, not only a catalog UI. Lifecycle deletion must cover replicas, versions,
caches, inventories, and backups under retention and legal-hold rules.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Manifest | Empty/multi-file/corrupt fixtures | Exact files, counts, checksum handling | Pending |
| Publication | Two writers plus timeout injection | One winner; no partial consumer view | Pending |
| Evolution | Mixed schema and partition specs | Complete, compatible reads | Pending |
| Lifecycle | Retained/superseded/orphan graph | Only unreachable eligible objects deleted | Pending |
| Real store | Listing, conditional update, permissions | Documented behavior observed | Pending |

Local filesystem tests cannot prove object-store request semantics, permissions,
throughput, durability, or lifecycle behavior.

## Debugging guide

Start with dataset ID, publication/snapshot ID, source frontier, schema/spec ID,
manifest, and a missing/corrupt object's version metadata. Compare catalog state
to manifests and object inventory; inspect request failures, throttling, list and
planning latency, file sizes, partition distribution, encryption identity, and
recent lifecycle policy changes. Freeze destructive cleanup while references are
uncertain.

## Common pitfalls

### Pitfall: treating prefixes as transactions

A consumer listing a path during writes can observe a mixed candidate. Publish
immutable files through a single authoritative metadata commit.

### Pitfall: zones defined only by folder names

Without owners, trust, quality, retention, and permissions, bronze/silver/gold are
labels rather than boundaries.

### Pitfall: partitioning by every query field

High-cardinality paths create tiny files, excessive metadata, and poor planning.
Use file statistics, clustering, or indexes for dimensions unsuitable as paths.

## Performance, capacity, and cost

Measure object count, size distribution, files/partition, list/head/get/put/delete
requests, planning latency, bytes scanned, pruning, throughput, retries, compaction
write amplification, retained snapshots, storage tiers, retrieval, and egress.
At 3 GiB/day, raw bytes are modest; millions of tiny objects can still dominate
planning and request cost. Reserve capacity and time for rewrites and recovery.

## Compatibility, migration, backfill, and delivery

Add fields compatibly, publish readers before writers where needed, and retain
schema/spec IDs. Backfill to a separate generation, validate old/new readers,
then atomically move the reference. Storage migration copies and verifies
immutable objects and metadata before cutover; dual-location reads need one
authority. Rollback retains the old manifest and required objects.

## Working example

- Python/data: planned manifest and compare-and-set publication model
- Tests: planned corruption, concurrent writer, unknown outcome, mixed spec, and lifecycle graph
- Infrastructure: no object store or catalog selected
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: real conditional operations, listing, permissions, scale, lifecycle, and cost

## Knowledge check

1. Explain why an object prefix is not a table transaction.
2. Assign owner, trust, access, retention, and recovery to each lake zone.
3. Diagnose a query that read half old and half new files.
4. Design a safe publication protocol for two concurrent writers.
5. Estimate how tiny files alter request, planning, and compaction cost.
6. Design a schema/partition evolution and rollback without deleting old files early.

## Key takeaways

- Object storage stores objects; metadata makes them a consistent dataset.
- Zones are contractual trust and lifecycle boundaries.
- Immutable generations plus an atomic metadata pointer contain partial failure.
- Manifests, reconciliation, reference-aware retention, and restore make a lake operable.

## Resources

- [Amazon S3 consistency model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html#ConsistencyModel) (reviewed 2026-09; product example)
- [Google Cloud Storage consistency](https://cloud.google.com/storage/docs/consistency) (reviewed 2026-09; product example)
- [Apache Parquet documentation](https://parquet.apache.apache.org/docs/) (reviewed 2026-09)

## Related topics

- [Lakehouse architecture and open table formats](04-lakehouse-architecture-and-open-table-formats.md)
- [Catalogs, metastores, namespaces, and discovery](05-catalogs-metastores-namespaces-and-discovery.md)

## Completion checklist

- [x] Lake, object, zone, publication, discovery, lifecycle, and failure contracts explained
- [x] Identity, snapshots, security, capacity, compatibility, and evidence addressed
- [ ] Manifest model, real-store publication, evolution, lifecycle, fault, and scale evidence run
