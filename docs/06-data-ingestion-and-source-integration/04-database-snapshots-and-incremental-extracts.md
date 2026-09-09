# Database Snapshots and Incremental Extracts

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Relational databases / Batch ingestion / SQL  
> Data scale: Local database fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Database extraction must define a consistent source cut while protecting the
operational owner. Full snapshots copy state at a point; incremental queries copy
rows satisfying a change predicate. Neither automatically captures deletes,
transaction boundaries, or changes made while a paginated scan runs.

This guide covers consistency points, high-water marks, isolation, keyset scans,
source load, deletes, and reconciliation. Transaction-log CDC is the next guide.

## Learning objectives

- State the snapshot or interval represented by an extract.
- Design a high-water mark with a stable total order and overlap policy.
- Explain isolation anomalies that cause missing or inconsistent rows.
- Capture updates and deletes without using an unreliable business timestamp.
- Bound source load and recover after an unknown checkpoint outcome.

## Prerequisites

- SQL keys, ordering, transactions, isolation, and plans from area 03
- Identity/history modeling from area 05
- [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md)

## Mental model and terminology

An extract is a read transaction plus a durable publication contract. It resembles
copying a Room database under a consistent backup API, not looping over DAO pages
while application writes continue. The analogy stops because a remote production
database has replication lag, MVCC cleanup, locks, log retention, and workload
owners whose SLOs outrank the analytical copy.

| Term | Meaning in this guide |
| --- | --- |
| Consistent cut | Source state that can be explained as of one transaction/snapshot boundary |
| High-water mark | Greatest fully acquired position in a declared total order |
| Low-water mark | Previous committed boundary from which the next scope begins, often with overlap |
| Snapshot isolation | Engine-specific transaction view; guarantees must be verified for the source |
| Tombstone | Explicit evidence that a previously known logical row was deleted |

## Requirements, assumptions, and invariants

Reference source: 100,000 current products, 5M customers, 50 changes/second with
500/second bursts, p95 operational query objective under 100 ms, and a 15-minute
ingestion freshness objective. Extract through a replica only if its lag and
snapshot semantics satisfy the contract.

Invariants:

- Full-extract rows share one documented consistency boundary or are labeled otherwise.
- Incremental order is stable and unique, for example `(change_version, primary_key)`.
- The watermark advances only after all rows through it are durably published.
- Inserts, updates, key changes, and deletes have explicit capture behavior.
- Source queries are parameterized, bounded, cancellable, and reviewed with plans.
- Counts/digests reconcile at the same source boundary, not against later live state.

## Full snapshot protocol

```text
begin verified consistent read
  -> capture source snapshot/version and schema
  -> keyset-read bounded pages under that view
  -> record counts/digests
end read -> atomically publish extract manifest -> advance snapshot checkpoint
```

Long transactions may retain old row versions and harm source maintenance. Prefer
a source-native snapshot/export or a governed replica where available. If pages
use separate transactions, document that the result is a moving scan and add
change capture/reconciliation rather than calling it point-in-time.

## Incremental query pattern

```sql
-- PostgreSQL-style sketch; change_version must be source-maintained and monotonic.
SELECT tenant_id, product_id, name, price, change_version, deleted
FROM source_product_changes
WHERE (change_version, tenant_id, product_id)
    > (:last_version, :last_tenant_id, :last_product_id)
  AND change_version <= :run_upper_bound
ORDER BY change_version, tenant_id, product_id
LIMIT :page_size;
```

`updated_at > last_timestamp` is unsafe when timestamps tie, precision truncates,
clocks move, updates omit the column, or transactions commit out of timestamp
order. An overlap plus deterministic merge reduces some risks but does not invent
unrecorded deletes. Use a source-maintained version/change table or CDC when the
contract requires complete change history.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Primary database | Operational transactions | Source team | Protect SLO; cancel excessive reads | Business authority |
| Replica/export | Declared lag and snapshot position | Source/platform | Detect lag, promotion, snapshot loss | Derived source interface |
| Extract query | Pinned schema, predicate, order, upper bound | Ingestion owner | Bound and retry from durable page | Untrusted transport |
| Raw extract | Rows plus source/snapshot/query metadata | Ingestion owner | Immutable versioned publish | Receipt evidence |
| Watermark state | Last completely durable order tuple | Ingestion owner | Conditional advance | Trusted control state |

## Consistency, identity, time, and deletes

Retain primary/business keys, source transaction/change version, source commit or
effective time when available, extraction time, and snapshot identity separately.
Surrogate page order is not business event time. A primary-key change may appear
as delete plus insert and must preserve lineage.

Delete choices are source tombstones/change tables, periodic anti-join of complete
snapshots, soft-delete fields whose enforcement is contractual, or log-based CDC.
Hard deletion plus `updated_at` polling is invisible. Replica lag means “as of
replica position,” not necessarily the primary's current state.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Moving full scan | Counts/versions disagree or source contract lacks snapshot | Use one snapshot/export or reconcile with changes |
| Equal watermark values | Boundary tests show skips | Add unique tie-breaker and inclusive overlap/merge |
| Long read harms source | Locks, MVCC age, I/O, latency alerts | Cancel; reduce pages; use export/replica; coordinate window |
| Replica falls behind/promotes | Lag/timeline or position discontinuity | Pause, establish new compatible position, resnapshot if needed |
| Schema changes mid-run | Metadata/decoder mismatch | Fail closed; retain old snapshot; migrate reader |
| Page landed, watermark unknown | Receipt/state mismatch | Read both, replay idempotently or conditionally advance |
| Delete missing | Full reconciliation finds extra target keys | Emit corrective tombstones and repair capture design |

Recovery finishes when source and target compare at a common boundary, watermarks
are continuous, and the source owner confirms workload recovery.

## Security, privacy, and governance

Use a read-only, column- and row-scoped identity; do not grant broad production
credentials for convenience. Use TLS, secret rotation, parameterized SQL, query
timeouts, resource groups, and audited access. Minimize extracted PII, classify
raw snapshots, protect temp/spill/export locations, and propagate retention and
erasure through snapshots, tombstones, backups, and derivatives.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Snapshot concurrency | Insert/update/delete while pages scan | Result matches documented isolation boundary | Pending |
| Watermark edges | Ties, precision loss, late commit, key update | No unexplained skip; duplicates converge | Pending |
| Restart | Fail after page publish and checkpoint | Safe bounded replay/resume | Pending |
| Delete capture | Hard/soft delete and snapshot diff | Target removal is explicit and reconciled | Pending |
| Source safety | Actual plan plus concurrent load/timeout | Budgets hold without unacceptable source regression | Pending |

An in-memory or local database cannot certify production isolation, replica, plan,
or lock behavior. Run integration and load evidence on the selected engine.

## Common pitfalls

### Pitfall: `updated_at > last_run_time`

It conflates wall time with committed change order and commonly loses ties or late
commits. Prefer source-maintained positions or a total key plus overlap and proof.

### Pitfall: `OFFSET` pages during writes

Rows move between pages and large offsets grow expensive. Use a pinned snapshot
and keyset ordering.

### Pitfall: validating against the current source after the extract

The source has moved. Compare at the same snapshot/log position or explain the
expected delta.

## Performance, capacity, cost, and operations

Measure rows/bytes per page, result width, plan shape, index usage, buffer reads,
locks, MVCC age, replica lag, source CPU/I/O, query latency, extraction throughput,
checkpoint lag, and target storage. Page size trades round trips against memory,
transaction duration, cancellation latency, and retry cost.

Alert on source-lag budget, stalled position, extraction age, plan regression,
timeouts, schema drift, reconciliation deltas, and delete backlog. The runbook can
cancel reads, preserve the last certified watermark, reduce admission, switch only
to a position-compatible replica, or resnapshot after estimating recovery time.

## Compatibility, migration, and tradeoffs

Coordinate additive schema changes and type widening, capture source schema IDs,
dual-read old/new extracts, reconcile at a common position, and cut over watermark
ownership once. Breaking key/order changes generally require a fresh snapshot and
a versioned target.

| Requirement | Prefer | Tradeoff |
| --- | --- | --- |
| Small source, loose freshness | Periodic consistent snapshot | Repeated read/storage cost |
| Reliable source change version | Incremental keyset extract | State and delete contract required |
| Complete ordered changes | Log-based CDC | Connector/log retention complexity |
| Protect primary | Governed export or replica | Lag and operational dependency |

## Working example

- SQL/Python/tests: planned PostgreSQL-style source, concurrent mutation fixture, keyset reader, watermark store, and snapshot diff
- Expected result: snapshot and incremental outputs reconcile at named positions across restart
- Scale represented: none yet; local integration planned
- Remaining risk: production plans, MVCC pressure, replica transitions, and source-specific semantics

## Knowledge check

1. Explain why a full table scan may not be a point-in-time snapshot.
2. Predict the result of two updates sharing the watermark timestamp.
3. Diagnose extra target rows when the source hard-deletes records.
4. Design a total incremental order and safe upper bound.
5. Choose snapshot, polling, or CDC for the reference workload and justify it.
6. Plan recovery after a replica promotion invalidates the prior position.

## Key takeaways

- Every extract needs a named consistency boundary.
- A high-water mark is a proven source position, not the job's wall clock.
- Stable total ordering, durable page receipts, and conditional state enable restart.
- Deletes and source load are first-class requirements.
- Reconciliation must compare the same source and target moment.

## Resources

- [PostgreSQL documentation: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09)
- [PostgreSQL documentation: Backup and Restore](https://www.postgresql.org/docs/current/backup.html) (reviewed 2026-09)

## Related topics

- [API ingestion, pagination, and rate limits](03-api-ingestion-pagination-and-rate-limits.md)
- [Change data capture logs and connectors](05-change-data-capture-logs-and-connectors.md)
- [Idempotency, deduplication, late data, and reconciliation](08-idempotency-deduplication-late-data-and-reconciliation.md)

## Completion checklist

- [x] Snapshots, increments, isolation, watermarks, deletes, and source load explained
- [x] Failure, security, capacity, observability, evolution, and evidence addressed
- [ ] Database concurrency, plan, restart, delete, and reconciliation evidence run
