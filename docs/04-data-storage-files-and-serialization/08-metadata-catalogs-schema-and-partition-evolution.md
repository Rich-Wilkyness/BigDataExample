# Metadata, Catalogs, Schema, and Partition Evolution

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Catalogs / Table metadata / Storage / Platform / Governance  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A dataset becomes usable when consumers can discover its logical identity,
schema, owner, location, current snapshot, partitions, quality/freshness, lineage,
and access policy. A catalog coordinates that metadata. Files remain the data
payload, while catalog/table metadata determines which files and interpretations
constitute a table at a point in time.

Schema and partition evolution are historical interpretation problems. Safe
systems track stable field/partition identities and versioned snapshots instead
of assuming current names and directory paths correctly describe old files.

## Learning objectives

- Separate file metadata, dataset/table metadata, catalog metadata, and governance metadata.
- Identify the authoritative owner and commit boundary for each metadata class.
- Design safe add, rename, drop, type-promotion, and partition-spec changes.
- Explain why stable field IDs and hidden partition transforms prevent path/name mistakes.
- Recover from stale catalogs, mixed schemas, incomplete commits, and metadata loss.

## Prerequisites

- All preceding guides in this area
- Schema/transaction/migration reasoning from area 03

## Mental model

```text
catalog name: analytics.events
        -> current table metadata version
             -> schema IDs + partition spec IDs + snapshot log
                  -> snapshot -> manifests -> immutable data files
governance metadata: owner, classification, policy, lineage, retention, quality
```

A Room schema version plus migration history is a useful analogy for explicit
evolution. It stops because a table may contain files written under several schemas
and partition specs simultaneously, with many engines planning the same snapshot
without one application process controlling migration.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| File metadata | Schema, counts, offsets, statistics, codec, and properties inside/alongside one file |
| Table metadata | Logical schemas, partition specs, snapshots, manifests, properties, and history |
| Catalog | Service/interface mapping stable table identity to current metadata and coordinating commits |
| Field ID | Stable identity independent of a field's display name or position |
| Partition spec | Versioned transforms that derive physical partition values |
| Hidden partitioning | Queries use source columns while table metadata maps them to physical transforms |
| Tombstone | Metadata indicating logical removal while physical cleanup follows retention rules |
| Metadata repair | Controlled restoration/reconstruction with proof, not speculative path guessing |

## Requirements, boundaries, and invariants

- `analytics.events` has one accountable data-product owner and a documented
  catalog/commit authority.
- A snapshot resolves to one schema, partition-spec history, and exact file set.
- Fields retain stable IDs through rename/reorder; an old ID is never reused for a
  different meaning.
- Type promotion must preserve all historical values and every supported reader/sink.
- Partition evolution does not require consumers to parse directory names or
  rewrite filters; each file is interpreted using its own spec ID.
- Current and historical metadata are backed up/retained consistently with data
  recovery objectives.
- Catalog freshness or lineage failure never silently changes the table's data meaning.

## Metadata layers and authority

| Layer | Examples | Authority | Staleness consequence |
| --- | --- | --- | --- |
| File | Parquet footer, Avro header, checksum | Immutable file writer | File unreadable/misplanned |
| Table | Schemas, specs, snapshots, manifests | Table commit protocol | Wrong file set or interpretation |
| Catalog | Name, namespace, current pointer, permissions | Catalog service | Undiscoverable or stale snapshot |
| Governance | Owner, classification, lineage, retention, quality | Domain/governance owners | Unsafe use or unmanaged lifecycle |
| Operational cache | Cached schemas/plans/listings | Reader/platform | Bounded staleness or incompatible reads |

Copies and indexes can improve discovery but must record source, version, refresh,
and owner. A search index is not automatically authoritative for table state.

## Schema evolution

### Add

Add a new field ID with explicit optionality/default semantics. Old files have no
stored value; readers may project null/default according to table-format rules.
Backfill only when the business requires observed or derived historical values.

### Rename and reorder

Change display metadata while retaining field ID. Name-only formats and engines
may not preserve this guarantee, so mixed-engine evidence is mandatory. Reordering
is presentation, not a reason to change identity.

### Drop

First stop consumers, then stop writers, then remove the field from the current
schema. Historical snapshots/files may still contain bytes until retention and
deletion complete. Do not reuse the ID or name for a new meaning.

### Type promotion and semantic change

Widen only where the table format and every engine support it and historical
values remain representable. A unit, timezone, identity, enum meaning, decimal
scale, or privacy change deserves a new field/version and migration even if the
physical primitive is unchanged.

## Partition evolution

A table may move from `day(event_time)` to `hour(event_time)`, add bucketing, or
remove a poor partition field. New writes use the new spec while old files remain
under earlier specs. The planner evaluates logical predicates against each spec
and produces a unified scan. This is safer than requiring application SQL to know
both path layouts.

Evolution does not eliminate cost: metadata grows, planning handles several specs,
and old layout pruning remains as good or bad as before. Rewrite old files only
when measured benefit exceeds compute, risk, lineage, and storage amplification.

## Evolution decision table

| Change | Safe direction | Main hazard | Required evidence |
| --- | --- | --- | --- |
| Add optional field | New ID, reader support before writer | Absent/default semantic ambiguity | Historical/new mixed-file reads |
| Rename field | Preserve stable ID; alias where needed | Name-mapped engine reads wrong/null data | Every supported engine/version |
| Drop field | Consumer retirement then metadata drop | Historical/privacy bytes persist | Usage inventory and deletion proof |
| Widen integer | Supported promotion | Old sink/reader range overflow | Boundary values and reverse path |
| Day to hour partition | New spec for new files | Mixed-spec planning/skew/tiny files | Query plans, sizes, late data, cost |
| Change timestamp meaning | New field/version | Same bytes represent different instants | Dual calculation and reconciliation |

## Commit, consistency, and caching

Metadata commits must serialize concurrent changes or detect conflicts. A writer
starts from a parent metadata version, writes immutable child metadata, and
conditionally replaces the catalog pointer. Unknown commit outcomes are resolved
by reading table history and matching operation identity.

Readers pin a snapshot/schema/spec set for repeatable planning. Caches key by
immutable metadata identity and obey bounded freshness/invalidation. A long-running
reader may validly retain an older snapshot, so cleanup must protect all snapshots
inside the retention/lease policy.

## Data flow, ownership, and trust boundaries

| Boundary | Owner | Failure behavior |
| --- | --- | --- |
| Producer schema | Source team | Compatibility gate before accepted records |
| Table schema/spec/snapshot | Data-product owner via table protocol | Conditional commit and history |
| Catalog service | Platform | Durable name resolution, auth, backup/restore |
| Governance metadata | Stewards/security/privacy | Policy, lineage, retention and audit review |
| Query-engine adapter/cache | Platform/consumer | Pinned supported metadata; fail on incompatibility |

## Failure model and recovery

| Failure | Detection | Recovery and proof |
| --- | --- | --- |
| Catalog unavailable | Lookup/commit errors and SLI | Use only approved pinned-cache policy; restore service |
| Catalog points to missing metadata | Integrity/read failure | Roll to known valid metadata or restore exact object |
| Stale cache | Freshness/version mismatch | Invalidate/reload; prove snapshot/schema consistency |
| Concurrent schema/append conflict | Conditional commit rejected | Rebase compatible change or require owner review |
| Name-based rename corruption | Cross-engine null/swapped values | Stop affected reader; use stable-ID mapping/rewrite |
| Mixed partition spec omitted | Missing rows in reconciliation | Fix planner/metadata; republish without mutating files |
| Metadata backup inconsistent with files | Restore cannot resolve snapshot | Restore matched recovery point; reconcile reachability |

Reconstructing a table by listing directories loses snapshot history, deletes,
schema/spec identity, and potentially correctness. Use it only as a governed
last-resort recovery with immutable evidence and consumer reconciliation.

## Security, privacy, and governance

Catalogs reveal high-value inventory, schemas, locations, classifications, and
lineage. Authenticate workloads, authorize namespace/table/operation, separate
schema change from data append/delete privileges, encrypt metadata, audit reads
and commits, and limit sensitive statistics/samples. Policy enforcement must occur
in supported query/storage paths; catalog tags alone do not block data access.

Deletion includes current files, historical snapshots, manifests, staging,
caches, replicas, exports, and backups subject to legal holds. Record evidence of
logical unreachability and later physical erasure.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Schema evolution matrix | Add/rename/drop/promotion across old/new files and readers | Pending |
| Partition evolution | Logical query returns identical rows over mixed day/hour specs | Pending |
| Concurrent commits | Conflict detected and compatible rebase preserves both changes | Pending |
| Cache/staleness fault | Pinned reads remain consistent; fresh reads converge within objective | Pending |
| Backup/restore | Catalog metadata and referenced files restore to matched snapshot | Pending |
| Governance negative tests | Unauthorized discovery/read/change/delete denied and audited | Pending |
| Reconciliation | Snapshot file/row/partition counts and keys balance | Pending |

An in-memory metadata model proves state transitions only. It is not catalog,
engine, object-store, IAM, or restore integration evidence.

## Debugging and operations

Capture catalog/table identifier, metadata and snapshot IDs, parent snapshot,
schema/spec IDs, manifest/file counts, operation/run/attempt identity, engine/
connector version, cache version/age, principal, and audit correlation. Monitor
commit conflicts/latency, catalog availability, metadata growth, snapshots/files,
planning latency, stale-cache errors, unsupported features, orphan bytes, lineage
freshness, and restore objectives.

## Common pitfalls

### Pitfall: using column name as permanent identity

Rename can be interpreted as drop plus add or bind old bytes to the wrong meaning.
Use stable IDs when the format/table protocol supports them and test every engine.

### Pitfall: assuming catalog registration guarantees data correctness

A catalog can faithfully point to corrupt or semantically invalid files. Gate
commits with file, schema, quality, and reconciliation checks.

### Pitfall: rewriting all data for every partition change

This increases cost and risk without necessarily helping current queries. Support
mixed specs, measure old-layout pain, and rewrite selectively when justified.

## Performance, capacity, and cost

Model metadata/files/snapshots per table, manifests scanned, catalog calls/latency,
cache hit/age, planning time, partitions/files selected, schema/spec history,
concurrent commits, and retention amplification. Metadata compaction and snapshot
expiration are correctness-sensitive maintenance operations; benchmark them with
active readers, rollbacks, audits, and deletion requirements.

## Compatibility, migration, backfill, and delivery

Inventory producers, consumers, engines, connectors, export tools, and governance
automation. Apply expand/migrate/contract: introduce compatible metadata, deploy
readers, deploy writers, dual-read and reconcile mixed history, backfill only when
needed, cut over, observe, then retire old behavior. Keep prior snapshots and code
through rollback objectives. A catalog/table-format upgrade also needs metadata
backup, canary tables, mixed-version testing, and a forward-repair plan when an
irreversible writer feature has been used.

## Working example

- Python/data/tests/infra: planned metadata state model, mixed-schema/spec fixtures, and later real catalog integration
- Expected result: stable logical rows across supported evolution and atomic metadata commits
- Scale represented: none yet; metadata growth and planning estimates unverified
- Remaining risk: engine interoperability, catalog HA, IAM, backup/restore, and long-lived readers

## Knowledge check

1. Identify the authority and staleness risk for each metadata layer.
2. Predict old-file values after adding an optional field with a reader default.
3. Diagnose a name-based engine after a field rename.
4. Design mixed day/hour partition evidence including late events.
5. Propose catalog plus object recovery that meets one consistent snapshot.
6. Plan expand/migrate/contract for a type change with an incompatible old sink.

## Key takeaways

- Catalog/table metadata turns immutable files into a named, versioned dataset.
- Stable field and partition identities preserve meaning across historical files.
- Schema compatibility includes semantics and every supported reader/sink.
- Partition evolution can coexist with old layout; rewrite only from evidence.
- Metadata needs the same ownership, atomicity, security, backup, and observability rigor as data.

## Resources

- [Apache Iceberg specification](https://iceberg.apache.org/spec/) (example table metadata, snapshot, schema, and partition protocol; reviewed 2026-09)
- [Apache Iceberg partitioning documentation](https://iceberg.apache.org/docs/latest/partitioning/) (example hidden partitioning; reviewed 2026-09)
- [Apache Avro schema resolution](https://avro.apache.org/docs/1.12.0/specification/#schema-resolution) (reviewed 2026-09)
- [Apache Parquet format specification](https://github.com/apache/parquet-format) (reviewed 2026-09)

## Related topics

- [Avro records, schemas, and compatibility](03-avro-records-schemas-and-compatibility.md)
- [Parquet columnar storage and encoding](04-parquet-columnar-storage-and-encoding.md)
- [Object-storage layouts, partitioning, and publication](07-object-storage-layouts-partitioning-and-publication.md)

## Completion checklist

- [x] Metadata layers, authority, stable identity, catalogs, commits, and caches explained
- [x] Schema/partition evolution, recovery, governance, operations, cost, and delivery addressed
- [ ] Evolution, concurrency, cache, authorization, restore, and real-catalog evidence run

