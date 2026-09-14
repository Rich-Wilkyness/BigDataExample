# 01 Big Data and Data Engineering Foundations

> Area status: Documentation complete  
> Level: Beginner  
> Reference scenario: Trace a mobile event from producer to analytical consumer  
> Evidence boundary: Diagrams, requirement models, scale estimates, and boundary review  
> Last reviewed: 2026-09

## Purpose

This area teaches how to reason about a data system before choosing Python, SQL,
Spark, Kafka, a warehouse, or a cloud service. The durable questions are:

1. What does each record mean, and who owns the authoritative state?
2. Which consumers rely on the data, and what do they need from it?
3. What volume, rate, latency, freshness, correctness, availability, retention,
   privacy, and cost constraints apply?
4. Where can data be lost, duplicated, delayed, corrupted, or exposed?
5. What evidence would show that the system meets its promises?

The running scenario is an Android application producing a `screen_viewed`
event. The event moves through collection, immutable raw storage, validation,
transformation, analytical publication, and a daily product dashboard. This is
a learning model, not a claim that every production system needs every stage.

## Learning path

Read the guides in order:

1. [Data engineering landscape and roles](01-data-engineering-landscape-and-roles.md)
   establishes responsibilities and handoffs.
2. [Data lifecycle, control plane, and data plane](02-data-lifecycle-control-plane-and-data-plane.md)
   traces data and the metadata that governs it.
3. [Volume, velocity, variety, and when data becomes big](03-volume-velocity-variety-and-when-data-becomes-big.md)
   turns vague scale language into workload estimates.
4. [OLTP, OLAP, batch, streaming, and serving](04-oltp-olap-batch-streaming-and-serving.md)
   separates workload shapes and processing modes.
5. [Sources, sinks, authority, and derived data](05-sources-sinks-authority-and-derived-data.md)
   makes ownership and consumer contracts explicit.
6. [Correctness, freshness, latency, throughput, and cost](06-correctness-freshness-latency-throughput-and-cost.md)
   defines measurable, conflicting system objectives.
7. [Data architecture patterns and trust boundaries](07-data-architecture-patterns-and-trust-boundaries.md)
   compares flows, layers, isolation, and failure containment.
8. [First end-to-end data pipeline](08-first-end-to-end-data-pipeline.md)
   combines the concepts in a local, inspectable design walkthrough.

## Shared event contract

At the producer boundary, one record represents one observation that one app
installation displayed one named screen once:

```text
screen_viewed v1
event_id: UUID               # producer-generated deduplication identity
installation_id: opaque ID   # pseudonymous; not a person identifier
screen_name: constrained text
event_time: UTC instant      # when the app observed the view
app_version: text
schema_version: integer
```

The mobile producer is authoritative for the observation it made. It is not
authoritative for successful delivery, a person's real identity, or a complete
business session. Each later dataset states its own grain and authority.

## Evidence and scope

The area includes paper estimates, state and data-flow diagrams, decision
tables, and boundary reviews. These validate reasoning and internal consistency;
they do not prove engine behavior, distributed fault tolerance, production
capacity, or cost. Executable implementations are introduced in the Python,
SQL, storage, ingestion, and batch-processing areas.

No vendor product is required. Hadoop, Spark, Kafka, Airflow, warehouses,
lakehouses, and cloud services appear only as later implementation options.

## Area completion checklist

- [x] Eight inventory guides authored in the planned order
- [x] Shared record grain, owners, consumers, and trust boundaries defined
- [x] Workload and service requirements expressed quantitatively
- [x] Batch, streaming, transactional, and analytical boundaries distinguished
- [x] Duplicate, late, invalid, partial-failure, replay, and overload cases covered
- [x] Security, privacy, retention, observability, migration, and cost introduced
- [x] Conceptual evidence and its limitations recorded
- [ ] Executable reference pipeline (owned by later implementation areas)
- [ ] Distributed, integration, performance, and production evidence

