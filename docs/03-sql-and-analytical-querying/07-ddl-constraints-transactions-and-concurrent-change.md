# DDL, Constraints, Transactions, and Concurrent Change

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Generic data engineering / SQL / Storage  
> Data scale: Single database; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

DDL turns assumptions into database structure; constraints reject invalid states;
transactions define which groups of reads and writes become visible together.
Concurrency introduces histories that cannot be understood from a single
statement alone. Safe change therefore requires an invariant, isolation contract,
lock/resource budget, migration sequence, and recovery evidence.

This guide covers relational schema changes and database-local transactions. It
does not claim atomicity across a database, broker, object store, or external API.

## Learning objectives

After completing this guide, you should be able to:

- Express grain and domains with DDL and constraints.
- Place atomic commit boundaries around publication and state changes.
- Explain dirty/nonrepeatable/phantom reads, write skew, and lost updates.
- Distinguish isolation names from demonstrated workload guarantees.
- Plan expand/migrate/contract schema changes with rollback and reconciliation.
- Test locks, timeouts, cancellation, retry, and concurrent anomalies.

## Prerequisites

- [Relations, sets, bags, keys, and NULL](01-relations-sets-bags-keys-and-null.md)
- [Aggregation, grouping, and set operations](04-aggregation-grouping-and-set-operations.md)

## Mental model

```text
begin -> read/write tentative state -> validate invariant -> commit atomically
                                               \-> rollback on failure
```

A transaction resembles a critical section only superficially. It does not
necessarily block every conflicting operation, and isolation may use locks,
versions, validation, or combinations. Kotlin synchronization protects memory in
one process; database transactions coordinate durable shared state among clients.
Neither extends automatically to external systems.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| DDL | Statements that define or evolve database objects |
| Atomicity | Transaction effects become visible as all-or-nothing within the database guarantee |
| Isolation | Rules governing interaction among concurrent transactions |
| Durability | Committed state survives failures covered by the database contract |
| Phantom | A repeated predicate read observes a changed set of qualifying rows |
| Write skew | Concurrent transactions make disjoint writes based on a shared predicate and jointly violate it |
| Lock | Engine coordination state that may block or reject conflicting work |

## Requirements and invariants

The reference publication replaces one `(metric_date, product_id)` metric version
as a unit and records lineage to query/input versions. Readers see either the old
complete publication or the new complete publication, never a partially loaded day.

- Primary/business keys and checks encode database-verifiable validity.
- The transaction boundary contains every database write needed for one publication.
- External side effects use a separate idempotency/outbox/reconciliation design.
- Retry handles only classified transient conflicts and reruns the whole owned unit.
- Connections never return to a pool with an unknown/open transaction.
- Migrations remain compatible with mixed old/new application versions.
- Lock duration, statement time, batch size, and rollback space are bounded.

## DDL and constraint design

```sql
CREATE TABLE daily_product_metrics (
    metric_date       date NOT NULL,
    product_id        text NOT NULL,
    metric_version    integer NOT NULL,
    view_count        bigint NOT NULL CHECK (view_count >= 0),
    purchase_count    bigint NOT NULL CHECK (purchase_count >= 0),
    revenue_cents     bigint,
    input_version     text NOT NULL,
    published_at      timestamptz NOT NULL,
    PRIMARY KEY (metric_date, product_id, metric_version),
    CHECK (purchase_count <= view_count)
);
```

The final check is valid only if every purchase is contractually also a view in
the same population. Constraints must encode owned truth, not a correlation that
happens to hold in a sample. Choose `ON DELETE` foreign-key behavior explicitly;
cascades can amplify accidental writes and still may be required for lifecycle
correctness.

## Transactions and concurrency

```sql
BEGIN;

-- Load a staging table beforehand or within the same owned transaction.
DELETE FROM daily_product_metrics
WHERE metric_date = :metric_date
  AND metric_version = :metric_version;

INSERT INTO daily_product_metrics (...)
SELECT ...
FROM staged_daily_product_metrics
WHERE metric_date = :metric_date;

-- Also insert publication metadata/reconciliation status here.
COMMIT;
```

The precise locking and visibility of DDL, `DELETE`, inserts, readers, failures,
and retries depends on the selected engine and isolation level. At high volume, a
metadata pointer/snapshot swap may be preferable to delete-and-insert, but that is
an engine/storage design, not portable SQL syntax.

Isolation levels are names for allowed histories, not magic labels. Demonstrate
the actual invariant with two concurrent connections. For example, two workers
may both read "no active publication" and insert distinct rows unless a unique
constraint, predicate lock, advisory protocol, or serializable retry prevents it.

## Ownership and boundaries

| Boundary | Owner | Guarantee and limit |
| --- | --- | --- |
| Migration artifact | Schema owner | Ordered, reviewed, immutable change; deployment tool behavior separate |
| Database transaction | Publishing job | Atomic only for enlisted database state |
| Connection/session | Client adapter/pool | Must set timeout/isolation and close or rollback on every path |
| Published metric pointer | Data-product owner | Exposes one validated version to consumers |
| External notification | Publisher/integration owner | Not atomic with DB unless a proven coordination pattern exists |

Least privilege separates migration, writer, reader, and operational roles. DDL
must not be assembled from untrusted names. Audit records contain actor/change
IDs and safe object metadata, not sensitive row payloads.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Constraint violation | Statement error and quality gate | Roll back; quarantine/repair source; rerun whole publication |
| Deadlock/serialization failure | Engine-classified transient error | Roll back, jittered bounded retry, alert on sustained rate |
| Client loses connection after commit request | Commit outcome unknown | Reconnect and query idempotency/publication key; do not blindly repeat side effects |
| Long migration blocks readers/writers | Lock wait and latency objectives breached | Cancel if safe; use phased migration or maintenance window |
| Process dies mid-transaction | Database rollback/recovery | Verify no active/ambiguous publication, then rerun |
| Old binary sees new schema | Compatibility tests fail | Keep additive schema, roll back binary, complete/repair migration |

Backups do not replace transaction recovery, and transaction success does not
prove backup restoration. Both require separate evidence.

## Safe schema evolution

For a new required `definition_version`:

1. Expand: add nullable or default-compatible storage without breaking old code.
2. Migrate: backfill in bounded, restartable batches with progress and reconciliation.
3. Dual-read/write or compute both forms where needed; compare semantics.
4. Enforce: validate completeness and add the non-null/uniqueness rule using an
   engine-appropriate low-risk method.
5. Cut over consumers and observe mixed-version behavior.
6. Contract: remove obsolete state only after rollback no longer requires it.

Rollback cannot always undo an irreversible data rewrite. Preserve source data,
version mappings, and a forward-fix path.

## Data quality, testing, and evidence

The planned integration suite needs a real engine and two or more independent
connections. It covers invalid DDL states, commit/rollback, cancellation, deadlock
or serialization conflict, unknown commit, mixed application versions, partial
backfill, and concurrent publication attempts.

| Evidence | Expected result | Result |
| --- | --- | --- |
| Constraint cases | Every invalid state rejected without partial publication | Pending |
| Transaction fault injection | Old or new complete state, never mixed | Pending |
| Concurrent history | Target anomaly reproduced, then prevented/retried | Pending |
| Migration rehearsal | Restart, rollback/forward-fix, and reconciliation succeed | Pending |
| Restore rehearsal | Published data and metadata recover within stated objectives | Pending |

Mocks cannot establish database isolation, lock, DDL, crash, or durability behavior.

## Debugging, operations, performance, and cost

Capture transaction/migration ID, query name, dataset version, connection role,
isolation level, start/commit timestamps, retry count, affected rows, lock waits,
blocked/blocking session IDs, and error class. Do not log SQL parameters containing
sensitive data. An unknown commit outcome remains unresolved until authoritative
state is queried.

Indexes and constraints increase write, storage, validation, and migration cost.
Large updates generate logs/versions and can extend recovery or replication lag.
Budget batch rows/bytes, transaction duration, lock wait, statement timeout,
replication lag, disk headroom, and rollback time. Observe p95/p99 commit latency,
deadlocks, retries, lock queues, log growth, and migration progress.

## Common pitfalls

### Pitfall: transaction around an external side effect

A database rollback cannot unsend a message or undo an API call. Use an outbox,
idempotency key, and reconciliation appropriate to the boundary.

### Pitfall: retrying only the failed statement

After a concurrency failure the transaction snapshot and prior decisions may be
invalid. Roll back and rerun the owned transaction from its beginning.

### Pitfall: one-step breaking migration

Adding an immediately required column while old writers run creates a mixed-version
outage. Use expand/migrate/contract and test the overlap.

## Working example

- Infrastructure/SQL/tests: planned real-engine schema, publisher, and two-connection tests
- Expected result: enforced invariants and old-or-new atomic visibility under failure
- Scale represented: local database first; production lock/log/cardinality tests pending
- Remaining risk: engine isolation, crash durability, replica visibility, and migration duration

## Knowledge check

1. Explain which metric constraints are database-verifiable and which need source ownership.
2. Trace a lost connection immediately after `COMMIT` and design resolution.
3. Reproduce a write-skew or duplicate-publication history with two transactions.
4. Explain why database atomicity does not cover a message broker.
5. Design expand/migrate/contract for a required definition version.
6. Choose evidence needed before applying the migration to 100M rows.

## Key takeaways

- DDL and constraints convert owned assumptions into enforced database states.
- Transactions define a database-local visibility and failure boundary.
- Isolation guarantees must be tested against the actual concurrent invariant.
- Unknown commit, retry, locks, and cancellation are normal design cases.
- Safe migrations explicitly support mixed versions, backfill, cutover, and recovery.

## Resources

- [PostgreSQL documentation: constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) (reviewed 2026-09)
- [PostgreSQL documentation: transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09)
- [PostgreSQL documentation: explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html) (reviewed 2026-09)

## Related topics

- [Query plans, indexes, statistics, and optimization](08-query-plans-indexes-statistics-and-optimization.md)
- [Aggregation, grouping, and set operations](04-aggregation-grouping-and-set-operations.md)

## Completion checklist

- [x] DDL, constraints, atomicity, isolation, locks, and migration mental models explained
- [x] Concurrency, unknown commit, security, recovery, capacity, and operations addressed
- [x] Real-engine and multi-connection evidence requirements stated
- [ ] Transaction, concurrency, migration, and restore evidence executed

