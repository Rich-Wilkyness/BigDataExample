# ACID Tables, Time Travel, Compaction, and Maintenance

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Warehouse / Lakehouse / Transactions / Storage operations  
> Data scale: Local state model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

ACID describes atomicity, consistency, isolation, and durability at a stated
transaction boundary. It does not mean every engine, catalog, external side
effect, or multi-table operation shares one transaction. Time travel exposes
retained table versions; compaction and optimization change physical layout;
vacuum/expiration removes history and makes recovery paths impossible.

This guide connects concurrent writes, snapshots, row changes, maintenance,
retention, and recovery. Exact syntax and guarantees vary by warehouse and table
format and must be verified for the selected stack.

## Learning objectives

- State ACID properties and isolation scope for each table operation.
- Predict concurrent append, overwrite, merge, schema, and maintenance conflicts.
- Use time travel for diagnosis and rollback without confusing it with backup.
- Compact files while preserving visible rows and snapshot correctness.
- Design safe expiration, orphan cleanup, backfill, and repair procedures.

## Prerequisites

- [DDL, constraints, transactions, and concurrent change](../03-sql-and-analytical-querying/07-ddl-constraints-transactions-and-concurrent-change.md)
- [Lakehouse architecture and open table formats](04-lakehouse-architecture-and-open-table-formats.md)
- [Catalogs, metastores, namespaces, and discovery](05-catalogs-metastores-namespaces-and-discovery.md)

## Mental model and terminology

```text
logical history:  S10 -> S11 -> S12 -> S13
                           \        \
physical changes:      add/delete   compact files

reader pins S11 -------- sees S11 until completion
latest reader ----------------------------- sees S13
expiration after safety proof -> older references/files become deletable
```

MVCC resembles immutable UI state versions: readers keep one state while a new
one is prepared. The analogy stops because physical files outlive processes,
delete representations may be merged later, and retention/cleanup can permanently
remove historical states shared by many engines.

| Term | Meaning in this guide |
| --- | --- |
| Atomicity | Transaction effects become visible together or not at all within its scope |
| Consistency | Declared invariants hold before and after a committed operation |
| Isolation | Rules governing interaction and visibility among concurrent operations |
| Durability | Acknowledged commit survives the stated failures and retention scope |
| Time travel | Querying an older retained snapshot/version |
| Compaction | Replacing many/small or delete-heavy files with fewer optimized files |
| Vacuum/expiration | Removing historical metadata/data no longer retained by policy |
| Orphan | Object not reachable from any protected table state or active candidate |

## Requirements, scale assumptions, and invariants

Assume hourly increments, daily compaction, concurrent BI readers, occasional
`MERGE` corrections, 35-day operational time travel, seven-year logical fact
retention, 15-minute freshness, and a 30-minute recovery reserve. Specify
transaction and retention scope per engine/format/catalog combination.

- Readers pin one table version; no snapshot mixes pre- and post-commit files.
- Business uniqueness and grain survive retry, concurrency, maintenance, and backfill.
- Unknown commit outcomes are resolved by operation/publication identity.
- Maintenance changes physical representation but preserves the snapshot's logical rows.
- Expiration never removes data needed by protected snapshots, branches/tags, active readers, legal holds, or rollback.
- Time travel is not the only backup and does not supersede source reconciliation.
- Delete and correction semantics reach all derived consumers under an explicit SLA.

## Data flow, ownership, and trust boundaries

| Boundary | Owner/authority | Commit or recovery responsibility |
| --- | --- | --- |
| Writer operation | Pipeline/domain owner | Identity, predicates, base snapshot, retry policy |
| Transaction manager/catalog | Platform/table system | Conflict detection and atomic visibility |
| Snapshot/files | Dataset owner | Logical history and reference integrity |
| Maintenance service | Platform with dataset policy | Optimize without semantic change; fenced commit |
| Retention/deletion service | Governance + platform | Prove eligibility and audit deletion |
| Consumer | Consumer owner | Pin/report version and tolerate declared correction model |

## Transaction and concurrency model

Define each operation's read set, write set, predicate, base version, conflict
rule, and retry behavior.

| Pair | May commute when | Must conflict/revalidate when |
| --- | --- | --- |
| Append + append | Independent files and no cross-row invariant | Uniqueness or shared quota must hold |
| Append + partition overwrite | Appended rows cannot match overwritten predicate | Predicate overlap is possible |
| Merge + merge | Disjoint keys under proven routing | Same keys/predicates or stale source versions |
| Schema change + write | Writer schema remains compatible | IDs/types/requiredness semantics differ |
| Compaction + data change | Rewrite protocol preserves concurrent additions/deletes | Maintenance would resurrect/drop changes |

```sql
-- Generic diagnostic pattern; snapshot syntax is engine-specific.
SELECT tenant_id, event_id, COUNT(*) AS copies
FROM product_event_fact /* AT SNAPSHOT :snapshot_id */
GROUP BY tenant_id, event_id
HAVING COUNT(*) <> 1;
```

`NULL` business identity is invalid. A `MERGE` statement is not inherently
idempotent: source duplicates, nondeterministic matches, stale ordering, or changed
predicates can alter results on retry.

## Time travel, correction, and rollback

Time travel helps reproduce a report, compare versions, diagnose a bad write, and
create a corrected forward version. Pointing the head back may discard concurrent
good changes; often the safer repair reads an old snapshot, applies the intended
delta atop current state, validates, and publishes a new snapshot.

Snapshot retention protects recent logical states but shares failure domains with
the live system. Backups protect against catalog corruption, account deletion,
region loss, or malicious expiration only when independent and restore-tested.

## Compaction and maintenance lifecycle

```text
select files from pinned base -> rewrite private candidates -> validate equivalence
 -> commit replacements if base/conflicts allow -> observe -> expire old references later
```

Compaction goals include fewer files, better clustering, merged deletes, and lower
planning/scan cost. It consumes reads, writes, requests, catalog commits, temporary
storage, and foreground capacity. It should be incremental, resumable, fenced,
observable, and cancellable.

Orphan cleanup differs from snapshot expiration. First expire permitted references;
then delete only objects proven unreachable and older than the maximum active
writer/reader safety horizon. A prefix-age deletion script cannot prove that.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Concurrent lost update | Conflict/uniqueness/reconciliation | Abort and recompute against current snapshot |
| Unknown commit | Operation ID and snapshot lineage | Resolve before retry |
| Compactor dies mid-write | Candidate ledger and unreferenced files | Current snapshot safe; resume or later clean |
| Compaction semantic drift | Row/key/aggregate checks across snapshots | Do not commit or restore prior head; investigate |
| Long reader loses files | Active-reader/retention test and read error | Restore retained object; increase safety policy |
| Vacuum deletes rollback state | Audit/restore failure | Restore backup/source and forward rebuild |
| Corrupt snapshot/catalog | Reference validation | Freeze commits/cleanup; restore metadata and reconcile |

Recovery is complete when one valid current snapshot exists, record-level and
aggregate reconciliation passes, protected readers work, and retention state is
known—not merely when a maintenance job turns green.

## Security, privacy, and governance

Restrict update/delete/merge, snapshot restore, retention change, tag/branch,
vacuum, orphan deletion, and catalog administration separately. Time travel and
backups can expose deleted or superseded sensitive values, so access and legal
retention apply to history. Record actor, operation ID, base/new snapshots,
predicate or scope, affected files/rows, policy version, and outcome without
logging sensitive row values.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Transaction | Duplicate source, two writers, unknown commit | Invariants hold or explicit conflict | Pending |
| Snapshot | Readers pin before/during write | Old or complete new rows only | Pending |
| Compaction | Skewed tiny/delete-heavy files | Logical equivalence; improved physical metrics | Pending |
| Retention | Long reader, tag, legal hold, orphan | Protected data retained; only eligible data deleted | Pending |
| Restore | Catalog/data loss rehearsal | RPO/RTO and reconciliation pass | Pending |

Local state-machine tests cannot prove distributed isolation, storage durability,
engine maintenance semantics, or deletion recovery.

## Debugging guide

Capture table ID, operation/commit ID, base/current snapshot, query/run IDs,
schema/spec versions, touched predicates/partitions/files, delete representation,
active readers, branches/tags, retention policy, and cleanup audit. Compare row
identity and aggregates between snapshots, then inspect conflicts, manifest/file
counts, delete density, maintenance backlog, storage errors, and recent policy
changes. Freeze writers and cleanup if reference integrity is uncertain.

## Common pitfalls

### Pitfall: ACID as a universal label

Ask: for which operation, tables, catalog, engines, failures, and isolation level?
A single-table commit does not include an API call or another catalog.

### Pitfall: time travel as backup

History can share credentials, metadata, storage, lifecycle policy, and region
with current data. Maintain independent, restore-tested protection for required failures.

### Pitfall: compaction as harmless housekeeping

Rewrites race with changes and can saturate the platform. Treat maintenance as a
versioned data job with correctness checks, admission, rollback, and ownership.

## Performance, capacity, and cost

Measure commit/conflict latency, file and manifest counts, delete density, planning
time, scan/pruning, rewrite bytes, temporary storage, write amplification,
foreground latency, maintenance backlog, retained history bytes, cleanup requests,
and recovery throughput/cost. Trigger maintenance from measured degradation and
budget, not a universal schedule or file size.

## Compatibility, migration, backfill, and delivery

Test mixed writer/reader versions, transaction features, delete forms, schema
evolution, and maintenance. Backfill isolated partitions/snapshots, reconcile,
then commit with conflict validation. Change retention only after the maximum old
reader/rollback/restore need is measured. Rollout cleanup in report-only mode,
canary a narrow scope, and retain auditable recovery.

## Working example

- Python/SQL: planned snapshot transaction and identity/equivalence checks
- Tests: planned concurrent operations, lost response, compaction, reader, retention, and restore faults
- Infrastructure: no warehouse/table format/catalog/object store selected
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: actual isolation, conflicts, recovery, maintenance load, retention, and cost

## Knowledge check

1. Define ACID scope for an append, merge, and multi-table publication.
2. Predict whether two operations commute and name the required conflict check.
3. Diagnose a retry that duplicates rows after a lost commit response.
4. Design compaction that cannot erase a concurrent delete.
5. Explain why a protected snapshot and an independent backup solve different failures.
6. Design a safe retention-policy reduction and rollback boundary.

## Key takeaways

- ACID guarantees are meaningful only with an explicit operation and system boundary.
- Time travel supports reproducibility and repair but is not independent backup.
- Maintenance must preserve logical rows under concurrency and partial failure.
- Expiration is an irreversible governance and recovery decision, not mere cleanup.

## Resources

- [Apache Iceberg reliability](https://iceberg.apache.org/docs/latest/reliability/) (reviewed 2026-09)
- [Delta Lake concurrency control](https://docs.delta.io/latest/concurrency-control.html) (reviewed 2026-09)
- [Apache Hudi concurrency control](https://hudi.apache.org/docs/concurrency_control/) (reviewed 2026-09)

## Related topics

- [Lakehouse architecture and open table formats](04-lakehouse-architecture-and-open-table-formats.md)
- [Serving layers, materialized views, caches, and federation](07-serving-layers-materialized-views-caches-and-federation.md)

## Completion checklist

- [x] ACID scope, concurrency, time travel, compaction, expiration, and recovery explained
- [x] Identity, security, failure, capacity, compatibility, operations, and evidence addressed
- [ ] Real transaction, conflict, compaction, retention, restore, load, and cost evidence run
