# 10 Messaging, Streaming, and Change Data Capture

> Area status: Documentation complete; executable streaming evidence planned  
> Level: Beginner to Senior data engineering  
> Applies to: Messaging / Kafka / Stream processing / Spark Structured Streaming / CDC / Platform  
> Reference scenario: Replayable mobile product-event log with incremental sessions and product metrics  
> Evidence boundary: Documentation and contract review; no broker, streaming engine, or CDC connector execution yet  
> Last reviewed: 2026-09

## Purpose

This area explains how an open-ended sequence of records becomes durable,
replayable input and then bounded, recoverable derived state. The durable problem
is not merely moving records quickly: it is preserving identity, ordering scope,
time semantics, progress, and recovery across independent producer, broker,
processor, state-store, sink, and database commits.

For an Android engineer, a stream may resemble a Kotlin `Flow`. Both represent
values arriving over time and can propagate backpressure. The analogy stops at
the process boundary: a durable event log retains records after collectors stop,
multiple consumer groups track independent positions, partitions constrain
ordering and parallelism, and replay can reconstruct years of derived state.

## Prerequisites

- Contracts, SLOs, trust boundaries, and capacity estimates from [Area 01](../01-big-data-and-data-engineering-foundations/README.md).
- Bounded iteration, concurrency, resource lifetime, and testing from [Area 02](../02-python-for-data-engineering/README.md).
- SQL aggregation, windows, transactions, and query plans from [Area 03](../03-sql-and-analytical-querying/README.md).
- Serialization, schemas, compression, and durable storage from [Area 04](../04-data-storage-files-and-serialization/README.md).
- Grain, keys, event modeling, and temporal semantics from [Area 05](../05-data-modeling-and-business-semantics/README.md).
- Ingestion, CDC handoff, validation, deduplication, and reconciliation from [Area 06](../06-data-ingestion-and-source-integration/README.md).
- Incremental processing, checkpoints, publication, and backfills from [Area 07](../07-batch-processing-and-etl-elt/README.md).
- Partitions, partial failure, retries, coordination, and backpressure from [Area 08](../08-distributed-systems-foundations/README.md).
- Spark DataFrames, plans, shuffles, deployment, and evidence limits from [Area 09](../09-apache-spark-and-distributed-computation/README.md).
- No Kafka, Spark, database, or CDC connector installation is required for this documentation pass.

## Learning path

1. [Event logs, brokers, streams, and tables](01-event-logs-brokers-streams-and-tables.md) separates transport, retained history, and derived state.
2. [Kafka topics, partitions, offsets, and consumer groups](02-kafka-topics-partitions-offsets-and-consumer-groups.md) defines Kafka's units of ordering, scaling, retention, and ownership.
3. [Producers, consumers, acknowledgements, and backpressure](03-producers-consumers-acknowledgements-and-backpressure.md) bounds work and makes overload explicit.
4. [Delivery semantics, ordering, idempotency, and transactions](04-delivery-semantics-ordering-idempotency-and-transactions.md) composes guarantees across commit boundaries.
5. [Event time, processing time, windows, and watermarks](05-event-time-processing-time-windows-and-watermarks.md) makes late and out-of-order computation explicit.
6. [Stateful stream processing, checkpoints, and replay](06-stateful-stream-processing-checkpoints-and-replay.md) manages durable incremental state and recovery.
7. [Spark Structured Streaming sources, sinks, and triggers](07-spark-structured-streaming-sources-sinks-and-triggers.md) applies those contracts to incremental tables.
8. [CDC streaming pipelines, schema evolution, and operations](08-cdc-streaming-pipelines-schema-evolution-and-operations.md) composes snapshot, log, broker, processor, and materialized-view recovery.

## Shared reference pipeline

```text
mobile event producers                 catalog database
        |                                     |
        v                                     v
 product-events topic                 snapshot + CDC log
        |                                     |
        +---------------+---------------------+
                        v
            validated immutable event log
                        |
           event-time parse + deduplicate
                        |
            keyed session/stateful metrics
                        |
          checkpoint + idempotent/transactional sink
                        |
             current sessions and metrics
```

| Boundary | Grain and identity | Authority | Progress evidence |
| --- | --- | --- | --- |
| Product event | One producer-observed action; `(tenant_id, producer_id, event_id)` | Product-event producer for observation; raw log for receipt | Topic, partition, offset plus producer identity |
| Catalog CDC | One committed row change; source key plus source position | Catalog database | Snapshot ID, source position, transaction metadata |
| Validated event | One accepted logical event | Stream contract owner; raw remains replay authority | Input position and disposition |
| Session state | One open/closed session per tenant and subject | Processor-owned derived state | Checkpoint version and covered offsets |
| Product metric | One definition version, tenant, product, and window | Metric owner | Input frontier, watermark, output generation/transaction |

Starting design assumptions are 3 million product events/day, about 35 events/s
average, 500 events/s bursts, 256 KiB maximum encoded event, 16 partitions,
35% of events from one tenant, 15-minute freshness, 35-day event replay, seven-day
CDC outage tolerance, and a provisional 30-minute allowed-lateness policy. These
are hypotheses, not measurements.

## Durable streaming contract

Every production design should answer:

- Which record is authoritative, what is its stable identity, and where may duplicates appear?
- What does an acknowledgement prove, and which later commits remain independent?
- What ordering exists per key or partition, and what reordering occurs across boundaries?
- Which source positions are retained, committed, checkpointed, and exposed to operators?
- Which clock defines correctness, which windows can change, and when is state evicted?
- How are late records, corrections, deletes, poison records, gaps, and schema changes handled?
- How do replay and recovery avoid duplicate external effects and prove convergence?
- What finite capacity protects brokers, consumers, state stores, sinks, and source databases?

## Evidence and scope

This pass supplies mental models, contract fragments, SQL/Python/PySpark sketches,
failure matrices, capacity arithmetic, runbooks, and exact pending evidence. It
does not add dependencies, services, fixtures, executable jobs, or infrastructure.
Consequently broker replication, producer fencing, group rebalancing, watermark
behavior, checkpoint compatibility, state-store recovery, CDC continuity, load,
and cost remain unverified.

Official Apache Kafka 4.3, Apache Spark 4.2.0, and Debezium 3.6 documentation were
reviewed in 2026-09. Product defaults are not treated as end-to-end guarantees;
pin exact versions and test the selected producer, broker, engine, connector,
state store, and sink together.

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] Logs, Kafka, flow control, delivery, time, state, Structured Streaming, CDC, and operations covered
- [x] Grain, ownership, ordering, identity, failure, security, quality, capacity, compatibility, and recovery addressed
- [x] Current primary documentation linked and version-sensitive claims bounded
- [x] Examples and evidence accurately marked Planned
- [ ] Deterministic reference model and fixtures implemented
- [ ] Kafka, Structured Streaming, database/CDC, fault, replay, load, and recovery evidence executed
