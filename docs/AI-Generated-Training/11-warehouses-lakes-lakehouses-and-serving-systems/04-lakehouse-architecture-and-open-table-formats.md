# Lakehouse Architecture and Open Table Formats

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Lakehouse / Table formats / Object storage / SQL / Platform  
> Data scale: Local metadata model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A lakehouse combines scalable file/object storage with a transactional metadata
layer that makes files behave as versioned tables. An open table format specifies
snapshots, manifests, schema and partition evolution, and commit rules so multiple
engines can share table state without discovering it from directory listings.

The format is not the whole system. Catalog atomicity, engine implementations,
object-store behavior, access control, maintenance, and tested interoperability
determine real guarantees. This guide compares durable concepts; it does not pick
Apache Iceberg, Delta Lake, or Apache Hudi for the project.

## Learning objectives

- Trace a logical table read from catalog pointer through snapshots to data files.
- Explain optimistic metadata commits and conflict/retry boundaries.
- Separate logical table state from physical layout and maintenance.
- Compare formats using requirements and tested engine interoperability.
- Design snapshot, evolution, portability, and recovery evidence.

## Prerequisites

- [Data lakes, zones, and object storage](03-data-lakes-zones-and-object-storage.md)
- [Metadata, catalogs, schema, and partition evolution](../04-data-storage-files-and-serialization/08-metadata-catalogs-schema-and-partition-evolution.md)
- [Retries, idempotency, speculation, and fault recovery](../08-distributed-systems-foundations/07-retries-idempotency-speculation-and-fault-recovery.md)

## Mental model and terminology

```text
catalog: table ID -> current metadata version
                         |
                         v
                  snapshot lineage
                         |
                  manifest list(s)
                         |
               manifests + file stats
                         |
              data files + delete/change files
```

A table snapshot resembles an immutable Kotlin data object referenced by an
`AtomicReference`: writers construct a new value then compare-and-set the head.
The analogy stops because the graph and files are durable/distributed, conflicts
may be semantic rather than memory races, and many engines implement the protocol.

| Term | Meaning in this guide |
| --- | --- |
| Table format | Specification and libraries defining table metadata and change semantics over files |
| Snapshot | Immutable logical table version with parentage and file-level changes |
| Manifest | Metadata describing a set of files, partitions, statistics, or status |
| Optimistic concurrency | Build independently, validate against current state, atomically commit if compatible |
| Delete file/vector | Metadata or file structure representing logical row deletion without immediate full rewrite |
| Portability | Ability to preserve semantics across tested catalogs, engines, and storage—not just file readability |

## Requirements, scale assumptions, and invariants

Assume 100M hot fact rows, hourly incremental writes, daily compaction, concurrent
BI reads, two processing engines, schema and partition evolution, 35-day time
travel for operations, and seven-year logical retention. Validate metadata growth,
commit rate, delete density, and engine support.

- A table identifier resolves through one authoritative catalog to one current metadata version.
- Readers pin a snapshot and never mix file sets from different snapshots.
- Writers create immutable candidates and expose them only through one atomic metadata commit.
- Conflict validation matches the operation; blind retry cannot overwrite a conflicting change.
- Schema fields retain stable identity where the format supports it; names alone are not assumed identity.
- Old snapshots and files remain until every retention, rollback, legal-hold, and reader requirement allows expiry.
- Every supported engine produces equivalent logical rows for the tested feature subset.

## Data flow, ownership, and trust boundaries

| Boundary | Authority | Failure behavior | Trust |
| --- | --- | --- | --- |
| Catalog table entry | Table identity and current metadata pointer | Conditional update or explicit conflict | Highly trusted control plane |
| Table metadata/snapshot | Schema, specs, lineage, properties, file changes | Immutable; validate before reference | Governed metadata |
| Manifest layer | Planning inventory and statistics | Reject corrupt/missing metadata | Trusted after validation |
| Data/delete files | Columnar records and row changes | Immutable candidate; restore/rewrite | Governed data plane |
| Engine adapter | Planning/read/write interpretation | Fail unsupported features; never silently downgrade | Version-pinned dependency |

## Read and commit protocols

A reader resolves the table identifier, pins metadata/snapshot, plans only its
referenced manifests/files, applies deletes under the format rules, and reports
the snapshot ID. A job that re-resolves `latest` midway violates repeatability.

```python
def commit(base_snapshot: str, candidate: "Snapshot", catalog: "Catalog") -> str:
    current = catalog.current_snapshot(candidate.table_id)
    if current != base_snapshot:
        # Planned model: revalidate touched partitions/keys; do not blindly retry.
        raise RuntimeError("commit conflict")
    validate_complete(candidate)
    return catalog.compare_and_set(candidate.table_id, base_snapshot, candidate.id)
```

The catalog supplies the atomic head change. The table-format implementation
defines conflict checks and metadata. The engine owns correct planning and write
behavior. Object storage owns object durability and request semantics. None alone
provides the end-to-end transaction.

### Logical and physical change

An insert may add data files. An update/delete may rewrite files or add position/
equality deletes or a change log, depending on format and engine. Compaction can
replace many physical files while preserving the same visible rows. Optimize
physical layout separately from logical correctness.

## Format-selection questions

| Requirement | Evidence to request |
| --- | --- |
| Multi-engine reads/writes | Exact version matrix and golden table suite |
| Row-level update/delete | Semantics, isolation, delete representation, read cost |
| Streaming/incremental consumption | Snapshot/change enumeration and checkpoint compatibility |
| Schema/partition evolution | Stable IDs, mixed-history reads, unsupported transformations |
| Branch/tag/time travel | Retention, authorization, merge/conflict, audit behavior |
| Portability/exit | Metadata spec, catalog export, unsupported product extensions |

Do not compare only feature names. Compare the exact supported subset, failure
semantics, operational tooling, and migration constraints.

## Lifecycle, consistency, identity, and time

The lifecycle is candidate files, candidate metadata, validation, head commit,
reader pinning, supersession, expiration eligibility, orphan cleanup, and physical
deletion. Snapshot ID defines a table version; publication time does not prove the
source event-time frontier. Maintain record business identity, table field IDs,
file identity, and snapshot identity separately.

Snapshot isolation is not automatically serializability. Concurrent operations
may be compatible or conflicting based on predicates, partitions, and format/
engine rules. State the tested isolation for append, overwrite, merge, schema
change, and maintenance separately.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Writer dies before head commit | Run ledger/unreferenced candidates | Current snapshot unchanged; later safe cleanup |
| Commit response lost | Resolve current snapshot and commit identity | Accept success or retry after conflict validation |
| Concurrent conflicting writers | Base/head and operation conflict checks | Abort/rebase/recompute; do not overwrite |
| Missing/corrupt metadata/file | Snapshot validation/read failure | Restore object or point to intact snapshot |
| Engine semantic mismatch | Cross-engine golden/reconciliation test | Block version/feature; use compatible reader |
| Metadata explosion | Planning latency and manifest/snapshot counts | Rewrite/compact metadata under snapshot-safe procedure |
| Unsafe expiration | Reference graph and active-reader audit | Halt deletion; restore or roll back if retained |

Recovery is complete when the catalog points to a valid snapshot, all references
resolve, cross-engine reads reconcile, source frontier is known, and cleanup is
safe for retained readers.

## Security, privacy, and governance

Authorize namespace/table metadata and underlying files coherently. Direct file
access can bypass row/column policy and snapshot semantics; restrict it. Protect
branches/tags, snapshot history, metadata statistics, and deleted data because
time travel can expose old sensitive values. Audit administrative and write
commits with actor, operation, base/new snapshot, and correlation ID.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Metadata model | Insert/delete/evolve snapshots | Exact visible rows by snapshot | Pending |
| Concurrency | Append/overwrite/merge conflicts | Compatible commits or explicit abort | Pending |
| Cross-engine | Golden tables and feature matrix | Equivalent schema, rows, null/time semantics | Pending |
| Fault | Crash and lost response at commit points | Old or complete new snapshot | Pending |
| Retention | Pinned reader plus expiration/cleanup | Required files remain; eligible orphans removed | Pending |

A mocked catalog can validate a state machine but not real format compatibility,
object-store atomicity, distributed conflicts, or engine recovery.

## Debugging guide

Capture table identifier, catalog, metadata location, snapshot and parent IDs,
operation/commit ID, engine/version, schema/spec IDs, manifest/file references,
source frontier, and active retention leases. Compare the catalog head to snapshot
lineage and storage inventory. Inspect conflict diagnostics, planning time,
manifest counts, delete density, file sizes, and recent engine upgrades. Freeze
expiration and writes if metadata integrity is uncertain.

## Common pitfalls

### Pitfall: calling Parquet a lakehouse

Parquet defines files, not an atomic multi-file table, concurrent commits, schema
authority, or retention graph. A table metadata and catalog protocol supplies them.

### Pitfall: assuming open means identical behavior

A published format enables interoperability, but engines may support different
features and versions. Certification needs a versioned compatibility suite.

### Pitfall: blind commit retries

A newer head may contain a conflicting overwrite, delete, or schema change.
Re-resolve and revalidate the logical operation before retrying.

## Performance, capacity, and cost

Measure data/delete file sizes, delete density, manifest counts/bytes, snapshots,
planning and commit latency, catalog requests, scan/pruning, cache behavior,
conflict rate, write amplification, cleanup backlog, and storage/compute/egress
cost. Maintenance consumes production capacity and must be budgeted with foreground
work and recovery.

## Compatibility, migration, backfill, and delivery

Pin a catalog-format-engine matrix. Introduce new features only after old and new
readers are compatible or isolated. For format migration, copy or rewrite into a
separate table, preserve source snapshot/frontier mappings, validate row and
semantic equivalence, dual-read or shadow, cut over catalog names/views, and retain
rollback inputs. File readability alone is not a complete migration.

## Working example

- Python: planned catalog/snapshot/manifest optimistic-commit model
- Data/tests: planned evolution, conflict, corruption, expiration, and cross-reader fixtures
- Infrastructure: no table format, catalog, engines, or object store selected
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: real atomicity, isolation, compatibility, recovery, performance, and cost

## Knowledge check

1. Trace a table read from logical name to visible rows.
2. Explain which boundary makes an optimistic commit atomic.
3. Diagnose a reader that mixes data from two snapshots.
4. Decide whether concurrent append and partition overwrite may commute and what must validate it.
5. Design a cross-engine compatibility and fault matrix.
6. Plan a reversible migration between table formats.

## Key takeaways

- A lakehouse adds transactional table metadata to durable files; it is a composed system.
- Readers pin snapshots and writers publish immutable candidates through an atomic head change.
- Logical state, physical layout, catalog authority, and engine behavior are separate contracts.
- Openness enables portability only for a tested, versioned feature subset.

## Resources

- [Apache Iceberg specification](https://iceberg.apache.org/spec/) (reviewed 2026-09)
- [Delta Lake protocol](https://github.com/delta-io/delta/blob/master/PROTOCOL.md) (reviewed 2026-09)
- [Apache Hudi technical specification](https://hudi.apache.org/tech-specs/) (reviewed 2026-09)

## Related topics

- [Data lakes, zones, and object storage](03-data-lakes-zones-and-object-storage.md)
- [Catalogs, metastores, namespaces, and discovery](05-catalogs-metastores-namespaces-and-discovery.md)
- [ACID tables, time travel, compaction, and maintenance](06-acid-tables-time-travel-compaction-and-maintenance.md)

## Completion checklist

- [x] Lakehouse layers, snapshots, manifests, commits, formats, and portability explained
- [x] Isolation, identity, lifecycle, failure, security, capacity, migration, and evidence addressed
- [ ] Metadata model, format-engine integration, conflicts, faults, retention, and performance evidence run
