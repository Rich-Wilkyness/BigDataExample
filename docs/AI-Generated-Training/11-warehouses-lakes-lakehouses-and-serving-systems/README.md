# 11 Warehouses, Lakes, Lakehouses, and Serving Systems

> Area status: Documentation complete; executable storage and serving evidence planned  
> Level: Beginner to Senior data engineering  
> Applies to: Warehouses / Data lakes / Lakehouses / Catalogs / Serving / Analytics  
> Reference scenario: Governed mobile-event facts and product metrics for BI and application consumers  
> Evidence boundary: Documentation and contract review; no warehouse, object store, table format, catalog, or serving engine execution yet  
> Last reviewed: 2026-09

## Purpose

This area explains how durable records become discoverable, governed datasets and
consumer-facing results. The central design problem is not choosing a fashionable
storage product. It is matching workload, authority, consistency, latency,
concurrency, recovery, governance, and cost requirements to a system boundary.

For an Android engineer, a warehouse table can resemble a Room table and a serving
cache can resemble an in-process cache. The analogy stops when storage and compute
scale independently, files are immutable objects, metadata commits select a table
snapshot, many engines share a catalog, and consumers may observe different
freshness frontiers.

## Prerequisites

- Requirements, authority, trust, SLOs, and capacity from [Area 01](../01-big-data-and-data-engineering-foundations/README.md).
- SQL semantics, transactions, concurrency, and plans from [Area 03](../03-sql-and-analytical-querying/README.md).
- Files, Parquet, object storage, publication, catalogs, and evolution from [Area 04](../04-data-storage-files-and-serialization/README.md).
- Grain, dimensional models, facts, dimensions, history, and metrics from [Area 05](../05-data-modeling-and-business-semantics/README.md).
- Incremental publication, backfills, repair, and lineage from [Area 07](../07-batch-processing-and-etl-elt/README.md).
- Distribution, partitioning, consistency, coordination, and capacity from [Area 08](../08-distributed-systems-foundations/README.md).
- Spark SQL, Parquet, pruning, catalogs, and deployment from [Area 09](../09-apache-spark-and-distributed-computation/README.md).
- Event frontiers, CDC, checkpoints, and replay from [Area 10](../10-messaging-streaming-and-change-data-capture/README.md).
- No cloud account, warehouse, object store, or table-format runtime is required for this documentation pass.

## Learning path

1. [Storage and serving system selection](01-storage-and-serving-system-selection.md) chooses a system from workload and guarantee requirements.
2. [Data warehouse architecture and workload management](02-data-warehouse-architecture-and-workload-management.md) separates analytical storage, compute, admission, isolation, and governed SQL.
3. [Data lakes, zones, and object storage](03-data-lakes-zones-and-object-storage.md) makes file publication, discovery, lifecycle, and failure explicit.
4. [Lakehouse architecture and open table formats](04-lakehouse-architecture-and-open-table-formats.md) adds transactional metadata and portable table semantics to object storage.
5. [Catalogs, metastores, namespaces, and discovery](05-catalogs-metastores-namespaces-and-discovery.md) establishes table identity, authority, permissions, and multi-engine resolution.
6. [ACID tables, time travel, compaction, and maintenance](06-acid-tables-time-travel-compaction-and-maintenance.md) manages concurrent change and physical health without losing logical correctness.
7. [Serving layers, materialized views, caches, and federation](07-serving-layers-materialized-views-caches-and-federation.md) trades freshness, latency, isolation, and precomputation deliberately.
8. [BI, semantic, and machine-learning consumer boundaries](08-bi-semantic-and-machine-learning-consumer-boundaries.md) defines stable metrics, extracts, features, and ownership limits.

## Shared reference architecture

```text
authoritative databases + replayable event/CDC logs
                         |
                         v
             immutable validated landing data
                         |
              snapshot/table-format commit
                         v
        governed event facts + product dimensions
                    /           \
                   v             v
       warehouse SQL models    lakehouse tables
                   \             /
                    v           v
          semantic metrics and serving views
                /        |          \
               v         v           v
             BI      application    ML features
```

| Dataset or boundary | Grain and identity | Authority | Consumer-visible version |
| --- | --- | --- | --- |
| Raw accepted event | One logical event per tenant and event ID | Retained validated log/files | Input positions and landing generation |
| Event fact | One accepted business event under a model version | Curated dataset owner | Table snapshot plus semantic version |
| Product dimension | One product version or current product row | Source database for business state; analytical table is derived | Source frontier plus table snapshot |
| Daily product metric | One tenant, product, metric definition, and UTC date | Metric owner | Definition version, input frontier, publication ID |
| Serving projection | One key or query result at a refresh frontier | Derived serving owner | Source snapshot and refresh time |

Starting assumptions are 3 million events/day (about 3 GiB encoded), 35% from
one tenant, 100 million retained fact rows, 100 thousand products, 20 concurrent
BI readers, a 15-minute freshness target for operational metrics, a 02:00 UTC
daily certified publication, 35-day hot replay, and seven-year governed fact
retention. These are hypotheses, not measurements.

## Durable publication and serving contract

Every design in this area must answer:

- What is the record grain, stable identity, authoritative source, and derived copy?
- Does a table name resolve to one atomic snapshot, and what does that snapshot cover?
- Which schema, partition, semantic, and policy versions apply to the snapshot?
- How are concurrent reads, writes, maintenance, retries, and unknown commit outcomes handled?
- What are the freshness frontier, correction policy, retention horizon, and deletion path?
- Which workloads receive isolation, admission control, quotas, and predictable capacity?
- How can a consumer reproduce, reconcile, audit, and safely roll back a result?

## Evidence and scope

This pass provides requirement models, architecture diagrams, SQL/Python sketches,
failure matrices, capacity arithmetic, maintenance policies, migration sequences,
and exact pending evidence. It adds no dependencies or executable services.
Local metadata models, real-engine transactions, catalog authorization,
multi-writer conflicts, compaction, vacuum, concurrent BI load, cache invalidation,
federation pushdown, and consumer reconciliation therefore remain unverified.

Product behavior is referenced only to illustrate durable concepts. Exact engine,
catalog, table-format, client, and object-store versions must be pinned and tested
together before claiming interoperability or production guarantees.

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] Selection, warehouses, lakes, lakehouses, catalogs, ACID maintenance, serving, and consumers covered
- [x] Grain, authority, snapshots, concurrency, failure, security, cost, migration, and recovery addressed
- [x] Primary specifications and documentation linked; version-sensitive guarantees bounded
- [x] Examples and executable evidence accurately marked Planned
- [ ] Deterministic metadata/publication fixtures implemented
- [ ] Real warehouse, object-store, catalog, table-format, serving, fault, scale, and consumer evidence executed
