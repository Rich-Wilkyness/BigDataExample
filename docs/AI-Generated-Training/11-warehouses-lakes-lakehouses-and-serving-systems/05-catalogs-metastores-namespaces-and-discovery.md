# Catalogs, Metastores, Namespaces, and Discovery

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Catalog / Metadata / Governance / Platform  
> Data scale: Local metadata design; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A catalog resolves a stable logical table identity to authoritative metadata and
often attaches schemas, locations, snapshots, permissions, ownership, lineage,
and discovery information. A metastore traditionally persists technical metadata;
a broader data catalog also supports search, governance, and stewardship. Product
names overlap, so define responsibilities rather than relying on labels.

A catalog is a control-plane dependency. It can make many healthy data files
unavailable or unsafe if identity, metadata, authorization, or commit state is
wrong. This guide covers namespaces, resolution, schema authority, multi-engine
access, discovery, and recovery—not a specific catalog deployment.

## Learning objectives

- Separate technical metadata authority from discovery and governance enrichment.
- Resolve a logical table name to catalog, namespace, stable ID, and snapshot.
- Design namespace, ownership, permission, and environment boundaries.
- Explain cache, rename, concurrent update, and catalog-loss failure modes.
- Define multi-engine compatibility and metadata backup/restore evidence.

## Prerequisites

- [Metadata, catalogs, schema, and partition evolution](../04-data-storage-files-and-serialization/08-metadata-catalogs-schema-and-partition-evolution.md)
- [Lakehouse architecture and open table formats](04-lakehouse-architecture-and-open-table-formats.md)
- [CAP, coordination, consensus, and metadata](../08-distributed-systems-foundations/04-cap-coordination-consensus-and-metadata.md)

## Mental model and terminology

```text
query name
  -> catalog endpoint and identity
  -> namespace
  -> stable table ID
  -> authoritative metadata pointer/version
  -> snapshot/manifests/files

search catalog -> description/owner/tags/lineage/quality -> authoritative ID
```

A catalog resembles Gradle dependency resolution: a readable name resolves to
versioned metadata used by multiple tools. The analogy stops because catalog
updates participate in data commits, authorize live data access, and may be the
only route to reconstruct a distributed table safely.

| Term | Meaning in this guide |
| --- | --- |
| Catalog | Authority that maps logical identities to technical table metadata and operations |
| Metastore | Persistence/service for schemas, locations, partitions, and related technical metadata |
| Namespace | Scoped naming and policy boundary containing data objects |
| Stable table ID | Identity preserved independently of mutable display name/location where supported |
| Discovery metadata | Descriptions, owners, tags, lineage, quality, usage, and glossary links |
| Registration | Attaching an existing table's metadata to a catalog without inventing new table state |

## Requirements, scale assumptions, and invariants

Assume 1,000 governed datasets, 50,000 partitions/manifests across hot tables,
two engines, separate development/staging/production environments, tenant and
sensitivity policies, 99.9% provisional metadata availability, and a 15-minute
freshness target. Measure catalog request load and recovery behavior.

- One authority owns table identity, current metadata pointer, and commit concurrency.
- Names and locations can change without silently creating a new logical table.
- Environment and tenant boundaries cannot be crossed by ambiguous default resolution.
- Schema and partition metadata are versioned with the table snapshot when required.
- Authorization covers both catalog operations and underlying storage access.
- Cached metadata has a version/expiry and cannot authorize a forbidden operation.
- Catalog backups plus data objects can reconstruct a tested, coherent state.

## Data flow, ownership, and trust boundaries

| Boundary | Authority/contract | Failure behavior | Trust |
| --- | --- | --- | --- |
| Client configuration | Explicit catalog and environment | Fail closed on ambiguity | Untrusted until authenticated |
| Namespace | Naming, ownership, default policy | Reject cross-boundary names | Governed control plane |
| Table entry | Stable ID, metadata pointer, format | Conditional/versioned update | Highly trusted authority |
| Storage credentials | Permitted objects/operations | Deny direct policy bypass | Restricted data plane |
| Discovery index | Searchable enrichment linked to stable ID | May be stale; not commit authority | Derived metadata |
| Lineage/quality store | Runs, inputs, outputs, assertions | Record gaps explicitly | Evidence plane |

## Name resolution and identity

Prefer fully qualified names in jobs and deployment configuration:

```text
catalog.environment_namespace.dataset
analytics.prod_product.product_event_fact
```

The concrete grammar varies. Never let a working directory, user's default
schema, or environment variable silently redirect production writes.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TableRef:
    catalog: str
    namespace: tuple[str, ...]
    name: str
    expected_table_id: str

def verify_resolution(ref: TableRef, resolved: "TableMetadata") -> None:
    # Planned deployment guard: names route; stable IDs detect accidental replacement.
    if resolved.table_id != ref.expected_table_id:
        raise RuntimeError("logical name resolves to an unexpected table")
```

Renames should preserve stable identity when supported. Drop/recreate under the
same name can be a new table and must not inherit access, lineage, or consumer
trust automatically.

## Schema, location, and commit authority

The table format may store authoritative schemas and partition specs in its
metadata while the catalog stores the pointer; duplicating mutable schema in a
second metastore creates divergence. Declare which field wins, how changes are
committed, and how engines invalidate caches.

Locations are infrastructure details with security consequences. Managed and
external table labels vary; document who may delete data, whether dropping a
catalog entry deletes objects, and how registration/relocation preserves history.

## Multi-engine access and discovery

Each engine/catalog adapter pair must be certified for read and write operations,
type/null/time semantics, snapshots, deletes, evolution, and conflicts. A read-only
engine is safer than a partially correct writer.

Discovery records should answer: what the dataset means; grain; owner/steward;
authority; freshness and quality; classifications; lineage; supported consumers;
semantic version; retention; and how to request access or report an incident.
Popularity is not proof of correctness.

## Lifecycle, consistency, identity, and time

A catalog object is proposed, authorized, created with stable identity, enriched,
used, evolved, deprecated, and eventually deleted or archived. Metadata caches
mean readers may observe old definitions for a bounded period; commits require
stronger coordination than search results. Record catalog version, table snapshot,
schema/spec versions, source frontier, and policy version on runs.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Wrong default catalog/environment | Stable-ID and deployment guard | Fail before read/write; correct configuration |
| Stale client cache | Version mismatch/change notification | Refresh and retry read; revalidate write |
| Concurrent metadata update | Conditional commit conflict | Rebase/abort according to logical operation |
| Catalog/data divergence | Reference and inventory reconciliation | Freeze writes/cleanup; repair authoritative mapping |
| Catalog outage | Availability/error signals | Existing pinned reads only if safe; stop new commits |
| Lost/corrupt catalog | Restore rehearsal/checksum | Restore consistent backup, replay changes, reconcile objects |
| Discovery lag | Metadata freshness and lineage gaps | Mark stale; repair ingestion without changing table authority |

Do not synthesize a current table by listing files during catalog loss. Recovery
is complete after identities, pointers, policies, lineages, and data references
reconcile and representative engines resolve the same snapshots.

## Security, privacy, and governance

Authenticate humans and workloads separately. Authorize create, read metadata,
read data, write, evolve, register, relocate, drop, grant, and administer. Test
direct object access cannot bypass catalog policy. Protect metadata because
schemas, statistics, lineage, locations, and names can expose sensitive facts.
Audit actor, effective policy, object ID, operation, old/new versions, and outcome.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Resolution | Defaults, wrong env, rename, drop/recreate | Correct stable ID or explicit failure | Pending |
| Concurrency/cache | Two writers and stale readers | Conflict detected; cache bounded | Pending |
| Multi-engine | Versioned golden table matrix | Same supported logical result | Pending |
| Authorization | Positive and negative role/tenant cases | Least privilege in catalog and storage | Pending |
| Restore | Catalog backup plus object inventory | Identities/pointers/policies reconcile | Pending |

An in-memory catalog model cannot prove service availability, authorization,
adapter compatibility, backup completeness, or restore time.

## Debugging guide

Capture fully qualified name, stable ID, catalog endpoint/version, namespace,
principal, effective policy, metadata pointer, table snapshot, engine/adapter
version, cache age, and correlation ID. Compare resolution across engines and the
discovery index. Inspect audit events and recent rename/drop/register/grant changes.
Freeze writers and object cleanup when catalog/data divergence is possible.

## Common pitfalls

### Pitfall: treating the catalog as a searchable wiki

Search is useful, but commits need authoritative identity and concurrency. Separate
derived discovery metadata from state that decides table correctness.

### Pitfall: duplicating schema authority

Independent schema copies drift. Choose one authoritative version and make derived
registrations verifiable and refreshable.

### Pitfall: granting catalog access but ignoring files

Broad storage credentials can bypass table policy; overly narrow credentials make
catalog authorization appear broken. Test both layers together.

## Performance, capacity, and cost

Measure resolve/list/search/commit latency, request throughput, cache hit and age,
object/partition/manifest counts, change-notification lag, backup size/duration,
restore time, throttling, and control-plane cost. Avoid high-cardinality discovery
labels and per-record catalog entries. Design degraded behavior before metadata
load or outage reaches the data plane.

## Compatibility, migration, backfill, and delivery

Version catalog APIs/adapters and table features together. For catalog migration,
export stable IDs and metadata, copy/register without rewriting authority, freeze
or replicate changes under a bounded protocol, validate resolution and policies,
canary engines, cut over explicit endpoints, and retain rollback. Never allow both
catalogs to accept independent authoritative commits.

## Working example

- Python: planned fully qualified resolution and stable-ID deployment guard
- Tests: planned rename/recreate, cache, concurrency, policy, and restore cases
- Infrastructure: no catalog, engines, identity provider, or object store selected
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: real atomicity, availability, policies, compatibility, backup, and recovery

## Knowledge check

1. Trace how a query name becomes a pinned table snapshot.
2. Explain why discovery metadata and commit metadata need different consistency.
3. Diagnose a production job resolving a development table under a default namespace.
4. Design negative access tests covering both catalog and storage.
5. Plan catalog restore and prove data objects match restored pointers.
6. Design a migration with one commit authority throughout.

## Key takeaways

- Catalogs are authoritative control-plane services, not only search indexes.
- Stable identity, explicit namespaces, versioned pointers, and coherent policy prevent ambiguity.
- Multi-engine access requires a tested adapter/feature matrix.
- Catalog backup and restore are part of data durability.

## Resources

- [Apache Iceberg catalog specification](https://iceberg.apache.org/spec/#catalog-metastore) (reviewed 2026-09)
- [Apache Hive Metastore administration](https://hive.apache.org/docs/latest/admin/adminmanual-metastore-administration/) (reviewed 2026-09)
- [OpenLineage specification](https://openlineage.io/docs/spec/) (reviewed 2026-09)

## Related topics

- [Lakehouse architecture and open table formats](04-lakehouse-architecture-and-open-table-formats.md)
- [ACID tables, time travel, compaction, and maintenance](06-acid-tables-time-travel-compaction-and-maintenance.md)

## Completion checklist

- [x] Catalog identity, namespaces, schema authority, discovery, policy, and multi-engine access explained
- [x] Cache, failure, security, capacity, migration, restore, and evidence addressed
- [ ] Resolution model, real catalog, policy, compatibility, concurrency, and restore evidence run
