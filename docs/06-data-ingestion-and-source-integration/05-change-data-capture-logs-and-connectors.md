# Change Data Capture Logs and Connectors

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Database logs / CDC connectors / Batch-stream handoff  
> Data scale: Local integration fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Change data capture (CDC) reads a source's ordered change mechanism—commonly a
transaction log—and publishes inserts, updates, and deletes with source positions.
It can avoid repeated full scans and preserve change history, but correctness also
depends on snapshot handoff, log retention, transaction boundaries, offset
durability, connector behavior, and schema evolution.

This guide covers source logs, initial snapshots, offsets, ordering, gaps, and
connector contracts. Broker internals and stateful streaming computation belong
to area 10.

## Learning objectives

- Explain what a CDC position proves and the scope of its ordering.
- Design a gap-free initial-snapshot-to-log handoff.
- Preserve transaction, before/after, delete, and schema metadata needed downstream.
- Recover from restarts, expired logs, connector changes, and partial publication.
- Distinguish source, connector, transport, and consumer guarantees.

## Prerequisites

- [Database snapshots and incremental extracts](04-database-snapshots-and-incremental-extracts.md)
- Transaction, identity, history, and schema-evolution concepts from areas 03–05

## Mental model and terminology

A database log is a commit-ordered journal for database recovery; CDC is a reader
and translator of that journal. It resembles observing ordered Room invalidations
only superficially. The log may contain row fragments, transaction metadata,
schema records, and positions meaningful only to one server timeline; the
connector must reconstruct a portable event contract.

| Term | Meaning in this guide |
| --- | --- |
| Source position | Engine-specific location or transaction coordinate used to resume |
| Log retention | Time/space for which unread source positions remain available |
| Initial snapshot | Baseline state paired with a position from which subsequent changes continue |
| Change envelope | Operation plus key, before/after values where available, transaction/source/schema metadata |
| Connector offset | Durable record of source progress; not proof every downstream consumer applied it |
| Gap | Missing required position/transaction in the declared source history |

## Requirements, assumptions, and invariants

Reference stream: 50 changes/second normally, 500/second bursts, 15-minute
freshness, seven-day connector outage tolerance, and 100,000-row initial catalog
snapshot. Source log capacity must exceed worst-case outage plus recovery margin.

Invariants:

- Snapshot rows and log changes meet at one proven source position with no gap.
- A source position advances only after corresponding raw change envelopes are durable.
- Ordering claims name their scope: source transaction, table, key, or transport partition.
- Deletes retain enough key and source metadata to retract prior state.
- Transaction metadata permits atomic grouping when consumers require it.
- An unavailable/expired position stops processing; it never silently jumps to latest.
- Schema history needed to decode retained positions is itself durable and versioned.

## Snapshot-to-stream handoff

```text
establish consistent snapshot S at log position P
        |                         |
 emit baseline rows tagged S     retain changes after P
        +------------+------------+
                     |
       publish baseline manifest, then apply/read P+
```

Exact sequencing is engine- and connector-specific. A naive `SELECT *` followed
by “start CDC now” loses changes between operations. Starting the log first and
snapshotting later avoids loss only if buffered changes and baseline rows are
merged with a defined position/identity rule.

Representative envelope:

```json
{
  "source": {"database": "catalog", "position": "opaque", "schema_version": 3},
  "transaction": {"id": "opaque", "sequence": 12},
  "operation": "update",
  "key": {"tenant_id": "t1", "product_id": "p7"},
  "before": {"price": "9.99"},
  "after": {"price": "10.49"},
  "source_commit_time": "2026-09-07T12:00:00Z"
}
```

Before-images may be unavailable or partial. The contract must not promise fields
the source log/configuration does not retain.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Database log/slot | Retained positions and transaction records | Source/platform | Backpressure or expire per policy | Business change authority |
| Connector | Decode/filter/envelope and offset state | Ingestion/platform | Stop on gap or incompatible schema | Privileged translator |
| Raw CDC stream | Immutable change envelope by source position | Ingestion owner | Idempotent publish and reconcile | Receipt evidence |
| Transport | Partitioned delivery/retention | Messaging owner | Retry/reorder within stated guarantees | Delivery mechanism |
| Materialized consumer | Applied source changes | Consumer owner | Deduplicate, order, checkpoint | Derived state |

## Ordering, identity, consistency, and time

Source commit order can differ from row update time and event-effective time.
Preserve source position, transaction ID/order, source commit time, ingestion time,
table, key, operation, and schema version. A transport may repartition by key and
lose global transaction order; do not claim atomic multi-table materialization
unless transaction grouping survives that boundary.

Connector delivery is commonly replayable and may duplicate after failure.
Downstream identity should include stable source identity and position/transaction
sequence, while business state uses the source key. Tombstones and key changes
need explicit semantics.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Connector restarts before offset commit | Repeated source positions | Deduplicate/reapply idempotently; then advance |
| Offset points past durable output | Reconciliation or missing receipt | Restore earlier proven position/resnapshot; never guess |
| Source log expires | Resume-position rejection/retention metric | Stop, take new consistent snapshot, version the discontinuity |
| Source failover/timeline change | Position lineage mismatch | Validate continuity or resnapshot on new lineage |
| DDL incompatible with decoder | Schema-history/decode error | Pause, retain position, update contract/decoder, replay |
| Transaction split/reordered | Transaction count/sequence violation | Buffer bounded transaction or use transport preserving requirement |
| Sink unavailable | Lag and retained-log growth | Backpressure connector; protect source with capacity/escalation plan |

Recovery completes when source position continuity is proven, snapshot plus
changes reconcile to a source state, and all duplicates/gaps have dispositions.

## Security, privacy, and governance

CDC identities can expose every table and old value. Restrict replication/log
privileges, table/column allowlists, network paths, offset stores, and schema
history. Masking after capture still leaves raw sensitive data, before-images,
logs, connector buffers, dead letters, and backups to govern. Audit configuration
changes and replays. Coordinate source deletion obligations with immutable change
retention and approved erasure/tombstone policy.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Handoff | Mutate during initial snapshot | Baseline plus changes equals source at target position | Pending |
| Operations | Insert/update/delete/key change/rollback transaction | Only committed changes with declared envelope appear | Pending |
| Restart | Fail before/after output and offset commits | Duplicates possible; no unexplained loss | Pending |
| Gap/retention | Remove/expire required log segment | Connector stops and resnapshot path works | Pending |
| Schema | Add/drop/rename/type-change under mixed versions | Compatible changes flow; incompatible change is contained | Pending |
| Transaction | Multi-row/multi-table commit | Ordering/grouping matches stated scope | Pending |

Mocks cannot verify log semantics. Evidence requires a real selected database and
connector, including restart, retention, schema, and source-load observations.

## Common pitfalls

### Pitfall: CDC means exactly-once business outcomes

CDC captures source changes; connector and transport retries can redeliver, and
consumer side effects have separate commit boundaries. Use identity, idempotency,
and reconciliation end to end.

### Pitfall: connector offset equals consumer completion

It proves only the connector's declared progress. Record raw publication and each
consumer checkpoint independently.

### Pitfall: resuming at latest after retention loss

This hides a gap. Stop, version the discontinuity, resnapshot, and reconcile.

## Performance, capacity, cost, and operations

Size log retention from peak change bytes/second, outage, snapshot, maintenance,
and recovery duration—not only average rows/second. Measure transactions and bytes
per second, envelope expansion, large-transaction size, snapshot rate, lag in
positions/time, log/slot retained bytes, buffer/disk use, publish latency, retries,
schema errors, and duplicate rate.

Alerts cover approaching retention exhaustion, stalled positions, connector
restarts, snapshot duration, large transactions, decode errors, output lag, and
reconciliation drift. The runbook protects the source first, preserves offsets
and schema history, estimates catch-up faster than incoming load, and decides
resume versus resnapshot explicitly.

## Compatibility, migration, and tradeoffs

Version envelopes independently of source schemas. Test connector/database
upgrades against retained representative logs, run old/new pipelines from a common
position when supported, compare envelopes and materialized state, and cut over
offset ownership once. Rollback may be impossible after source log expiration.

| Requirement | Prefer | Tradeoff |
| --- | --- | --- |
| Complete ordered changes/deletes | Log-based CDC | Privilege, retention, connector complexity |
| Small low-change source | Snapshot/incremental extract | Polling load and weaker delete/history capture |
| Atomic multi-row consumer | Preserve transaction metadata/grouping | Buffering and partitioning constraints |
| Source protection during outage | Sufficient log capacity plus bounded backpressure | Source disk/cost and operational coupling |

## Working example

- Infrastructure/tests: planned real-database snapshot+CDC fixture, connector offset store, materializer, and gap/schema fault suite
- Expected result: committed source state reconstructs across handoff and restart; gaps stop safely
- Scale represented: none yet; local integration planned
- Remaining risk: engine failover, production log retention/load, connector upgrade, and distributed transport

## Knowledge check

1. Explain why snapshot then “start now” can lose changes.
2. Predict a crash after output publication but before connector offset commit.
3. Diagnose a consumer that sees half of a multi-row transaction.
4. Design log retention for a seven-day outage plus catch-up.
5. Choose a gap response when the required source position expired.
6. Plan a connector envelope upgrade with rollback constraints.

## Key takeaways

- CDC positions are source-specific progress evidence with limited ordering scope.
- Snapshot and stream need a proven, gap-free handoff.
- Offset, output durability, and consumer application are separate commits.
- Schema history, deletes, transactions, and log retention are part of the contract.
- A missing position requires resnapshot or proof, never silent skipping.

## Resources

- [PostgreSQL documentation: Logical Decoding](https://www.postgresql.org/docs/current/logicaldecoding.html) (reviewed 2026-09)
- [Debezium documentation: Architecture](https://debezium.io/documentation/reference/stable/architecture.html) (reviewed 2026-09)

## Related topics

- [Database snapshots and incremental extracts](04-database-snapshots-and-incremental-extracts.md)
- [Event ingestion, batching, and backpressure](06-event-ingestion-batching-and-backpressure.md)
- [Idempotency, deduplication, late data, and reconciliation](08-idempotency-deduplication-late-data-and-reconciliation.md)

## Completion checklist

- [x] Logs, snapshots, offsets, ordering, schema, gaps, and connectors explained
- [x] Failure, security, capacity, operations, evolution, and evidence addressed
- [ ] Real database/connector handoff, restart, gap, schema, and load evidence run
