# Object-Storage Layouts, Partitioning, and Publication

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Object storage / Data lakes / Batch / Platform  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Object stores expose objects addressed by keys, commonly with put/get/head/list/
delete operations. A key that resembles a filesystem path does not imply directory
transactions, atomic rename, append, or multi-object commit. Dataset correctness
therefore comes from immutable objects plus a metadata/manifest commit that selects
one complete file set for readers.

Partitioning groups data by derived values to limit scan candidates and organize
lifecycle work. It is a physical design, not a substitute for filters, indexes,
record identity, authorization, or schema.

## Learning objectives

- Distinguish object keys/prefixes from filesystem directories and rename semantics.
- Design partition keys from query, cardinality, skew, file size, and lifecycle requirements.
- Publish a dataset so readers observe an old or new version, not a partial mixture.
- Explain manifests, checksums, conditional commit, orphan cleanup, and idempotent retries.
- Diagnose partial publication, concurrent writers, hot partitions, and unsafe overwrite/delete.

## Prerequisites

- Authority, idempotency, publication boundaries, and analytical query contracts
- All preceding guides in this area, especially file sizing and immutable repair

## Mental model

```text
data/run=R/staging/file-*.parquet  -- immutable PUTs --> validate
                                                        |
                                                   manifest R
                                                        |
                         conditional catalog/pointer commit: S(n) -> S(n+1)
                                                        |
                                    readers use snapshot S(n+1), never LIST guesswork
```

A Gradle build publishing immutable artifacts and then one versioned module
descriptor is a useful analogy. It stops because object-store consistency,
concurrent writers, long-lived analytical readers, and partition pruning create
data-specific coordination and lifecycle requirements.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Object key | Opaque identifier within a bucket/container; slash is usually naming convention |
| Prefix | Leading key substring used for organization/listing/routing |
| Partition | Dataset subset selected by a transform/value in a physical layout/spec |
| Hive-style path | Convention such as `event_date=2026-09-07/`; not a table guarantee |
| Manifest | Metadata listing files and often size, count, partition, schema, statistics, checksum |
| Snapshot | One immutable, committed view of dataset/table state |
| Conditional write | Commit that succeeds only if the referenced prior state/version matches |
| Orphan | Object not referenced by any retained committed snapshot |

## Requirements, estimates, and invariants

The daily event dataset serves date-range queries and occasional event/product
filters. Initial partitioning is day in UTC, subject to measured daily size and
skew. Each file name includes an immutable run/attempt identity and content identity;
files are not overwritten in place.

- Readers derive the visible file set from one committed snapshot/catalog entry,
  not from listing a prefix during concurrent writes.
- A successful commit references only complete, validated immutable files.
- Concurrent writers use compare-and-swap/conditional commit or an owning
  transaction protocol; one cannot silently erase the other's files.
- Retry either reuses verified content-addressed output or creates new immutable
  attempt objects; it never duplicates logical rows in the committed snapshot.
- Partition values use declared transforms and time zones and are validated against records.
- Deletion and orphan cleanup cannot remove data referenced by any retained reader/snapshot.

## Keys and prefixes

Use keys for stable organization and lifecycle, not to simulate mutable POSIX
directories. A possible staging layout is:

```text
events/staging/run=20260907T031500Z-attempt=02/part-00017-<content-id>.parquet
events/manifests/snapshot-<snapshot-id>.json
events/metadata/current   # only if a safe conditional update protocol owns it
```

Avoid embedding sensitive identifiers in keys because keys appear in logs,
inventory, audit trails, and billing. Avoid random user input in paths; construct
keys from validated components. A run ID aids lineage but is not record identity.

## Partitioning design

Partition by predicates and operational boundaries that remove substantial data,
while preserving healthy file sizes. Date is common for append-oriented event
data, but define UTC versus business-local date. High-cardinality identifiers such
as `user_id` usually create sparse tiny partitions. Low-cardinality values can be
skewed and may provide little pruning. Hash/bucket or truncate transforms can
distribute data but bind readers to a known spec unless table metadata hides them.

| Candidate | Benefit | Risk | Evidence/change point |
| --- | --- | --- | --- |
| UTC event day | Range pruning and lifecycle alignment | Late events and oversized days | Daily size/skew and correction frequency |
| Event name | Common filter | Skew; vocabulary change; tiny rare partitions | Selectivity and files per value |
| User ID | Point targeting | Extreme cardinality/privacy/tiny files | Rarely justify as visible directory partition |
| Hash bucket of ID | Bounded distribution | Poor range readability; bucket evolution | Join/filter workload and skew |
| Ingestion day | Stable arrival lifecycle | Event-time queries span late arrivals | Lateness and replay requirements |

Late events should enter a new snapshot and the correct logical partition under a
documented correction policy. Rewriting a day is not the same as overwriting every
object under its prefix.

## Publication protocol

1. Pin source snapshot, schema, partition spec, writer settings, run, and attempt.
2. Write unique immutable data objects to staging/unreferenced keys.
3. Close writers and validate size, checksum, footer, schema, row counts,
   partitions, quality rules, and accepted/rejected reconciliation.
4. Write an immutable manifest containing exact object versions/identities and metrics.
5. Commit the new snapshot/catalog pointer conditionally against the expected parent.
6. Confirm readers can plan/read the snapshot and publish operational success.
7. Delete orphan staging only after retention, concurrent-run, and rollback safety checks.

The commit point is step 5, not the last data-file upload. If the conditional
commit conflicts, reread current state and deliberately merge/rebase or abandon;
never blindly retry a stale whole-dataset replacement.

## Consistency and visibility

Object-store semantics are product and operation specific. For example, current
Amazon S3 documentation states strong read-after-write consistency for object
PUT/DELETE and atomic updates to a single key. That still does not make a group of
data-file PUTs one atomic dataset transaction. The publication protocol must state
exactly which conditional operations and catalog guarantees it relies on for the
selected platform.

Listing is useful for inventory and orphan discovery, but it should not define the
live dataset while writers are active. Readers pin a snapshot for repeatability;
fresh readers can select a newer snapshot according to their freshness contract.

## Data flow, ownership, and trust boundaries

| Boundary | Owner | Failure/authority contract |
| --- | --- | --- |
| Data objects | Pipeline writer | Immutable derived bytes; not visible until referenced |
| Manifest/snapshot metadata | Dataset owner | Authoritative file set and lineage |
| Catalog/commit service | Platform | Conditional serialization and access control |
| Object-store lifecycle | Storage/governance | Cannot delete referenced/held versions |
| Consumer | Data product/analyst | Pins snapshot; observes documented freshness |

## Failure model and recovery

| Failure | Consumer-visible behavior | Recovery |
| --- | --- | --- |
| Worker dies during data PUTs | Current snapshot unchanged | Retry/rewrite; later mark unreferenced objects orphan |
| Manifest write fails | Current snapshot unchanged | Recreate from validated outputs or abandon attempt |
| Commit response lost | Commit outcome unknown | Read catalog and compare snapshot/attempt identity before retry |
| Two writers conflict | One conditional commit loses | Rebase/merge under owner rules; never overwrite blindly |
| Bad partition value | Validation blocks commit | Fix transform/code and rewrite affected output |
| Reader finds missing/corrupt referenced object | Snapshot unavailable/partial by policy | Quarantine snapshot, roll pointer forward/back, rebuild and reconcile |
| Cleanup races reader | Read fails after object deletion | Enforce snapshot retention/leases and conservative reachability |

Rollback normally creates or selects another committed metadata version. Mutating
data objects underneath an existing snapshot destroys reproducibility.

## Security, privacy, and governance

Use workload identities and least privilege: writers create staging objects but
only the publisher commits; readers need committed prefixes/catalogs; cleanup has
separate guarded delete rights. Encrypt data and metadata, audit reads/commits/
deletes, validate destination keys, block public access, and avoid secrets/PII in
key names. Lifecycle policy must cover staging, manifests, versions, replicas,
inventory, logs, and backups. Partition-level access via paths is fragile unless
enforced by the storage/catalog authorization layer.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Local state-machine model | Crash at every pre/post-commit point exposes old or new snapshot | Pending |
| Concurrent writers | One conflict is detected; no lost update or duplicate file | Pending |
| Unknown commit outcome | Read-after-timeout resolves outcome idempotently | Pending |
| Partition mutation | Null/late/time-zone/skew values map and reconcile correctly | Pending |
| Orphan cleanup | Only unreachable objects past safety horizon deleted | Pending |
| Real object store/catalog | Named operations match modeled consistency/conditional guarantees | Pending |

A filesystem rename simulation is not object-store integration evidence.

## Debugging and operations

Correlate dataset, parent/new snapshot, run/attempt, manifest, object version/content
ID, partition spec, schema, writer version, and commit token. Measure staging and
committed bytes/files, size/skew distributions, upload/head/list/commit latency,
request errors/throttles, conflicts, orphan age/bytes, snapshot freshness, missing
objects, and reader failures. Alert on actionable ownership boundaries.

## Common pitfalls

### Pitfall: listing a prefix to discover “the table”

Concurrent/failed writes can expose incomplete and orphan files, leading to
duplicates or missing data. Resolve one committed manifest/snapshot instead.

### Pitfall: using rename as the object-store commit plan

Many object stores do not provide atomic directory rename; an emulation can copy
and delete objects individually. Use the selected catalog/table commit protocol.

### Pitfall: partitioning by every common filter

Combinations multiply sparse directories/files and operational state. Choose a
small physical design from selectivity, skew, size, and lifecycle evidence.

## Performance, capacity, and cost

Track files/bytes per snapshot and partition, size percentiles, object requests,
listing/planning time, range-read bytes, pruning, writer concurrency, commit
latency/conflicts, compaction, storage versions, network, retrieval tiers, and
request/egress cost. Prefix distribution requirements are platform/version
specific; verify current guidance instead of preserving historical folklore.

## Compatibility, migration, and delivery

Treat key layout, partition spec, manifest schema, catalog protocol, encryption,
and retention as versioned interfaces. Prefer readers that use logical metadata
instead of parsing paths. Write old and new layouts concurrently only with one
authoritative snapshot, validate mixed-spec planning, backfill if necessary, cut
over through a new commit, and retain the parent snapshot for rollback. Never move
historical objects merely to make paths look uniform without a requirement.

## Working example

- Python/data/tests/infra: planned local publication state machine and later real object-store/catalog test
- Expected result: crash/concurrency tests expose only committed snapshots
- Scale represented: none yet; request, partition, and object-count estimates unverified
- Remaining risk: provider-specific conditional semantics, throttling, IAM, and lifecycle races

## Knowledge check

1. Explain why strong single-object consistency does not provide a dataset transaction.
2. Predict reader output if it lists during a 100-file upload.
3. Design partitions for event-time ranges with late arrivals and justify UTC choice.
4. Diagnose an unknown commit outcome without blindly duplicating a snapshot.
5. Propose orphan deletion proof that protects retained readers and rollbacks.
6. Model a crash after every publication step and state visible state.

## Key takeaways

- Object keys and prefixes are not transactional directories.
- Immutable files plus one conditional metadata commit define snapshot visibility.
- Partitioning balances pruning, skew, file sizing, and lifecycle work.
- Listings discover objects; committed metadata discovers datasets.
- Unknown outcomes, concurrent writers, cleanup, and rollback require explicit protocols.

## Resources

- [Amazon S3 consistency model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html#ConsistencyModel) (example provider semantics; reviewed 2026-09)
- [Apache Iceberg specification: snapshots, manifests, and commits](https://iceberg.apache.org/spec/) (example open table protocol; reviewed 2026-09)

## Related topics

- [Compression, splittability, and file sizing](06-compression-splittability-and-file-sizing.md)
- [Metadata, catalogs, schema, and partition evolution](08-metadata-catalogs-schema-and-partition-evolution.md)

## Completion checklist

- [x] Object semantics, partitioning, immutable writes, manifests, and conditional publication explained
- [x] Concurrency, failure, cleanup, security, cost, migration, and operations addressed
- [ ] State-machine, concurrency, fault, cleanup, and real-service evidence run

