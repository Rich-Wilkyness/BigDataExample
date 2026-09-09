# CDC Streaming Pipelines, Schema Evolution, and Operations

> Status: Documentation complete; executable evidence planned  
> Level: Senior  
> Applies to: CDC / Kafka / Streaming / Databases / Operations  
> Data scale: Local integration fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A production CDC streaming pipeline composes a consistent database snapshot,
ordered transaction-log positions, connector offsets and schema history, broker
retention, stream processing, checkpoints, and sink materialization. Each stage
can be individually healthy while the end-to-end table is wrong because a delete
was lost, a transaction split, an offset outran durable publication, a schema
became undecodable, or retained history expired during an outage.

Area 06 introduced source-log capture and snapshot handoff. This guide carries
that contract through a broker and stateful processor into an operable current
catalog view joined with mobile events, including schema migration, reconciliation,
incident recovery, and resnapshot.

## Learning objectives

- Compose source, connector, broker, processor, checkpoint, and sink guarantees.
- Materialize inserts, updates, deletes, key changes, and transaction metadata.
- Evolve source and event schemas through mixed-version deployments safely.
- Diagnose lag/gaps and choose resume, replay, repair, or resnapshot.
- Design reconciliation, capacity, security, runbooks, delivery, and disaster recovery.

## Prerequisites

- All earlier guides in this area
- [Change data capture logs and connectors](../06-data-ingestion-and-source-integration/05-change-data-capture-logs-and-connectors.md)
- [Validation, quarantine, and schema evolution](../06-data-ingestion-and-source-integration/07-validation-quarantine-and-schema-evolution.md)

## Mental model and terminology

```text
catalog DB -- consistent snapshot S @ position P --+
     \---- committed log changes after P ----------+-> CDC connector
                                                      -> raw CDC topic
                                                      -> validate/order/apply
                                                      -> catalog state checkpoint
mobile event topic ----------------------------------> event-time metrics/session state
                                                      -> versioned serving tables
```

The database log is primarily the database's recovery history; the connector
translates it into a portable change envelope. Broker offsets order deliveries in
transport partitions. The materializer must still use source key, position,
transaction, schema, and operation semantics. No one offset represents the entire
pipeline.

| Term | Meaning in this guide |
| --- | --- |
| Snapshot | Consistent baseline state tied to a source-log position |
| Source position | Database-specific ordered resume coordinate |
| Change envelope | Key, operation, before/after, source/transaction/time/schema metadata |
| Tombstone/delete | Record representing removal; transport compaction and business delete are distinct |
| Schema history | Metadata required to decode retained changes across DDL |
| Handoff | Proven no-gap/no-double-count transition from snapshot to changes |
| Resnapshot | New versioned baseline after loss/incompatibility, followed by catch-up and cutover |
| Reconciliation frontier | Source and downstream positions at which states are validly compared |

## Requirements, scale assumptions, and invariants

Reference catalog: 100,000 current products, 50 changes/s normal, 500/s burst,
seven-day connector outage tolerance, 15-minute current-view freshness, and joins
with the 3M-event/day product stream. Source log, broker, checkpoint, and sink
retention/capacity must cover outage plus catch-up with failure margin.

- Snapshot and changes meet at a proven source position with no gap or unexplained duplicate.
- A connector offset never advances beyond raw CDC records durably published under its contract.
- Envelopes preserve source identity, position, transaction ordering, operation, key, and schema needed to reconstruct state.
- Only committed database transactions materialize; required atomic groupings remain identifiable.
- Deletes and key changes remove the correct prior business state and propagate to derived views.
- Every derived table exposes source/checkpoint frontier and semantic/schema version.
- A missing source or broker position stops the pipeline; operators never jump to latest silently.
- Schema history and old/new decoders survive at least as long as replayable records.
- Resnapshot builds isolated state, catches up, reconciles, and cuts over atomically.

## Change envelope and materialization

```json
{
  "envelope_version": 2,
  "source": {
    "database": "catalog",
    "table": "products",
    "position": "opaque-source-position",
    "schema_version": 7
  },
  "transaction": {"id": "opaque", "sequence": 12},
  "operation": "update",
  "key": {"tenant_id": "t1", "product_id": "p7"},
  "before": {"price": "9.99"},
  "after": {"price": "10.49"},
  "source_commit_time": "2026-09-07T12:00:00Z"
}
```

Before-images may be absent or partial depending on source configuration. The
contract must not promise what the source does not retain. A delete needs enough
key information to remove state. A primary-key change may arrive as update or a
delete/create sequence; test the selected source/connector explicitly.

PostgreSQL-style current-state application can use a source version/position that
the adapter has converted into a comparable per-key order:

```sql
BEGIN;

WITH claimed AS (
  INSERT INTO catalog_apply_ledger (source_event_id, payload_hash)
  VALUES (:source_event_id, :payload_hash)
  ON CONFLICT (source_event_id) DO NOTHING
  RETURNING source_event_id
)
INSERT INTO current_product (
  tenant_id, product_id, name, price, source_version, schema_version
)
SELECT :tenant_id, :product_id, :name, :price, :source_version, :schema_version
FROM claimed
ON CONFLICT (tenant_id, product_id) DO UPDATE
SET name = EXCLUDED.name,
    price = EXCLUDED.price,
    source_version = EXCLUDED.source_version,
    schema_version = EXCLUDED.schema_version
WHERE current_product.source_version < EXCLUDED.source_version;

COMMIT;
```

If the claim returns no row, compare the stored and supplied payload hashes and
fail on a conflict. Deletes use the same ledger/ordering gate in one transaction.
A raw opaque source position may not support lexical/numeric comparison; the
source adapter must define a valid ordering representation and lineage.

## Snapshot-to-stream and transaction handling

The connector-specific handoff typically establishes snapshot consistency and a
log position, emits baseline records with a snapshot identity, then continues
from subsequent log changes. Buffering changes is useful only when buffer bounds,
spill, order, and failure recovery are explicit.

If consumers require multi-row or multi-table atomic visibility, retain transaction
ID, event count/order, and commit marker, partition compatibly, buffer within a
maximum transaction size/time, and publish/apply atomically. Otherwise explicitly
document per-row eventual consistency. Never infer database transaction atomicity
from adjacent Kafka offsets after repartitioning.

## Schema evolution and mixed versions

Separate source DDL, connector decoding schema, envelope schema, materialized table
schema, and metric semantic version. An additive nullable/defaulted field is often
easier but still needs old/new producer, reader, state, sink, and replay tests.
Rename is add/backfill/dual-read/contract—not drop/add in one step when historical
records still use the old name. Type narrowing, key changes, decimal changes,
timezone interpretation, and operation semantics require versioned migration and
usually a rebuild or translation.

```text
expand source/envelope/sink -> deploy tolerant consumers -> populate/backfill
-> validate mixed history -> switch writers/semantics -> contract only after
all retained logs, state, checkpoints, replays, and rollback windows allow it
```

## Data flow, ownership, and trust boundaries

| Boundary | Authority/contract | Owner | Failure behavior |
| --- | --- | --- | --- |
| Source database/log | Committed catalog state and retained changes | Catalog/database team | Protect log; snapshot/resume by source protocol |
| CDC connector | Decode/filter/snapshot/offset/schema history | Ingestion/platform | Stop on gap/decode error; never guess |
| Raw CDC topic | Immutable envelope receipts | Messaging/data platform | Retain/replay within policy |
| Stream materializer | Ordered/idempotent current catalog state | Pipeline owner | Restore/replay/resnapshot |
| Event join/metrics | Versioned event-time derived facts | Metric owner | Correct/rebuild from both frontiers |
| Serving table | Consumer contract and visible generation | Dataset owner | Atomic version cutover/rollback |

## Failure model and incident recovery

| Failure | Detection | Containment | Recovery proof |
| --- | --- | --- | --- |
| Connector offset/output ambiguity | Offset vs raw-topic receipt ledger | Pause connector/partition | Source positions continuous and raw counts reconcile |
| Source log/slot near expiry | Retained bytes/time and oldest required position | Protect source, reduce load, expand only safely | Catch-up rate/headroom demonstrated |
| Log or broker position expired | Out-of-range/gap | Stop downstream publication | Versioned resnapshot + catch-up + source comparison |
| Source failover/timeline change | Position lineage mismatch | Freeze affected source | Continuity proven or new snapshot lineage |
| DDL decode failure | Connector/schema-history error | Retain position; block incompatible records | Old/new decoder fixture and replay pass |
| Huge transaction | Buffer/state/latency bound | Backpressure/controlled spill or stop | Atomic result and capacity evidence |
| Delete/key change missing | Source-vs-current anti-join | Quarantine affected scope | State repaired and absence reconciliation passes |
| Sink outage/partial apply | Sink ledger/frontier mismatch | Stop progress; keep prior visible generation | Idempotent replay and exact state comparison |
| Wrong release/state | Canary or semantic reconciliation | Stop cutover, isolate version | Correct rebuild, atomic switch, rollback retained |

Incident triage first protects the source database from unbounded retained logs,
then preserves source/connector/broker/checkpoint evidence. Operators determine
the last continuous frontier and choose resume, broker replay, state repair, or
resnapshot. Recovery is complete only after continuity and source-to-sink state
reconciliation, not merely when lag returns to zero.

## Security, privacy, and governance

CDC can expose every row version, deleted value, schema, and transaction pattern.
Grant narrow replication/log, table, topic, group, checkpoint, state, sink, and
replay privileges; use table/column allowlists and authenticated encrypted links.
Masking after capture leaves raw logs and before-images governed. Audit connector
configuration, schema changes, offset resets, snapshots, replays, exports, and
manual repairs. Coordinate erasure across source, log, broker, state, materialized
views, quarantine, checkpoints, backups, and legal holds.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Snapshot handoff | Mutate throughout snapshot | Snapshot + subsequent changes equals source at frontier | Pending |
| Operations | Insert/update/delete/key-change/rollback/multi-row transaction | Exact envelope and materialized state | Pending |
| Crash chain | Fail connector, broker, processor, state, sink around commits | Declared duplicates only; no unexplained gaps | Pending |
| Schema matrix | Add/drop/rename/type/key changes with old/new components | Compatible flow or safe containment/migration | Pending |
| Retention/gap | Outage until source/broker positions expire | Alert and rehearsed resnapshot path | Pending |
| Reconciliation | Counts, key sets, hashes/sums at same frontier | Source and materialization agree | Pending |
| Load/recovery | Burst, large transaction, sink slow, broker/node loss | Source protected; catch-up meets budget | Pending |
| Disaster restore | Restore source/connector/schema history/broker/state/sink metadata | Continuity and consumer state proven | Pending |

Mocks are useful only for envelope/reducer states. End-to-end evidence requires a
real selected database, connector, broker, streaming engine, checkpoint store,
and sink, including restarts, DDL, retention, and transaction behavior.

## Debugging guide

Correlate database/source lineage and position, transaction ID/sequence, connector
task and offset, envelope/schema version, Kafka topic/partition/offset, consumer
group, streaming query/operator/checkpoint/batch, materialization effect ID, and
serving generation. Inspect source retained-log headroom, connector snapshot/state,
schema history, broker lag, watermark/state metrics, sink ledger, and source-vs-
target reconciliation. Use protected samples; record every manual offset/reset or
repair as an auditable state transition.

## Common pitfalls

### Pitfall: zero connector lag means correct current state

The pipeline can be caught up after skipping an expired position or misapplying a
delete. Verify continuity, operation dispositions, and source-state reconciliation.

### Pitfall: treating tombstones as business deletes

Transport tombstones support keyed log compaction; source delete envelopes carry
business operation meaning. Define their relationship and test both.

### Pitfall: one-step rename or type replacement

Retained records, old connectors, state, and replays still need the old contract.
Use expand/migrate/contract with an explicit retention and rollback horizon.

### Pitfall: resnapshotting directly into the live table

Consumers can see mixed baseline and catch-up state. Build an isolated version,
reconcile at a frontier, then atomically switch.

## Performance, capacity, cost, and operations

Measure source changes/transactions/bytes per second, retained log/slot bytes and
time, snapshot scan/duration/load, connector queue and publish rates, envelope
expansion/compression, broker partition bytes/lag, transaction size tails,
processor rates/state/checkpoints, sink apply latency, reconciliation time,
catch-up rate, and end-to-end cost. Test source impact as carefully as consumer
throughput. Recovery drain rate must remain above live change rate under one
expected failure.

Operational objectives cover source safety, raw durability, current-view
freshness, completeness, correctness, and restore time separately. Alerts include
retention headroom, stalled source position, snapshot duration, decode errors,
large transactions, broker lag/skew, checkpoint failures, sink frontier, delete
rate anomalies, and reconciliation drift. Owners and escalation paths span the
database, connector, messaging, stream, dataset, and consuming product teams.

## Compatibility, migration, backfill, and delivery

Pin database, connector, broker/client, serialization/registry, Spark, state-store,
and sink versions. Rehearse rolling mixed versions with retained old/new records.
Shadow a connector/query from a declared source frontier when supported, compare
envelopes and state, transfer offset ownership once, and retain a rollback window.
If old source logs expire after cutover, rollback may require a new snapshot rather
than a binary downgrade.

| Decision | Prefer when | Cost/risk |
| --- | --- | --- |
| Log-based CDC | Deletes/order/low-latency changes matter | Privilege, source retention, connector complexity |
| Polling snapshot/delta | Small source and weak history needs | Source load, delete/gap limitations |
| Row-level eventual apply | Consumers tolerate transaction-internal intermediate state | Simpler, but weaker consistency |
| Transaction-aware buffering | Atomic multi-row view required | Large transaction/state/partition constraints |
| Repair selected keys | Gap/defect scope is proven small | Proof burden and missed-corruption risk |
| Full resnapshot | Continuity/state cannot be trusted | Source load, catch-up time, cutover storage |

## Working example

- Python/SQL/PySpark: planned envelope validator, ordered materializer, idempotent ledger, and event/catalog join
- Data/tests: planned snapshot/change/DDL/delete/transaction/gap and reconciliation fixtures
- Infrastructure: planned PostgreSQL, Debezium, Kafka, Spark, checkpoint storage, and serving sink
- Try it: no command yet; no services or connector dependencies were added
- Evidence: documentation review only
- Remaining risk: all source/connector/broker/engine/sink integration, transaction, schema, failure, load, restore, and cost behavior

## Knowledge check

1. Trace the independent source, connector, broker, processor, and sink positions.
2. Explain how a snapshot and log handoff proves no gap.
3. Predict a primary-key change and delete through the materialized table.
4. Diagnose zero lag with source/target key-count drift.
5. Choose resume, repair, or resnapshot after source log expiry.
6. Plan an additive field then rename across the full retention/rollback horizon.
7. Design a game day that kills each component and proves final convergence.

## Key takeaways

- CDC correctness is a chain of source positions, schemas, commits, retention, and derived frontiers.
- Snapshot/log handoff, deletes, key changes, and transactions need explicit evidence.
- Schema history must outlive every record and checkpoint that depends on it.
- Zero lag is not proof of continuity or correct state; reconciliation is mandatory.
- Resnapshot is a versioned rebuild and atomic cutover, not an in-place overwrite.

## Resources

- [Debezium 3.6 stable documentation](https://debezium.io/documentation/reference/stable/) (reviewed 2026-09)
- [Debezium 3.6 architecture](https://debezium.io/documentation/reference/stable/architecture.html) (reviewed 2026-09)
- [PostgreSQL logical decoding](https://www.postgresql.org/docs/current/logicaldecoding.html) (reviewed 2026-09)
- [Apache Kafka 4.3 documentation](https://kafka.apache.org/43/) (reviewed 2026-09)
- [Apache Spark 4.2.0 Structured Streaming guide](https://spark.apache.org/docs/4.2.0/streaming/index.html) (reviewed 2026-09)

## Related topics

- [Change data capture logs and connectors](../06-data-ingestion-and-source-integration/05-change-data-capture-logs-and-connectors.md)
- [Spark Structured Streaming sources, sinks, and triggers](07-spark-structured-streaming-sources-sinks-and-triggers.md)
- [Warehouses, lakes, lakehouses, and serving systems inventory](../COVERAGE.md#11-warehouses-lakes-lakehouses-and-serving-systems)

## Completion checklist

- [x] Snapshot, log, connector, broker, processor, sink, deletes, transactions, schemas, and reconciliation composed
- [x] Failure, security, privacy, capacity, operations, delivery, resnapshot, restore, and evidence addressed
- [ ] Real database/connector/Kafka/Spark/sink handoff, schema, fault, reconciliation, load, and disaster-recovery evidence run
