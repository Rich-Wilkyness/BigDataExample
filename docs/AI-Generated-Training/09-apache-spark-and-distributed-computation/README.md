# 09 Apache Spark and Distributed Computation

> Area status: Documentation complete; local PySpark environment smoke-tested; topic and distributed evidence planned
> Level: Beginner to Senior data engineering  
> Applies to: PySpark / Spark SQL / Batch / Distributed computation / Storage / Platform  
> Reference scenario: Spark batch version of the curated mobile product-event pipeline  
> Evidence boundary: Documentation and contract review plus one local environment smoke check; no topic-specific or cluster Spark evidence yet
> Last reviewed: 2026-09

## Purpose

This area turns the distributed-computation models from Area 08 into concrete
Spark engineering practice. The durable problem is to compute a complete,
repeatable dataset from bounded input while work is partitioned, reordered,
retried, spilled, and sometimes lost. Spark supplies a driver, executors, a DAG
scheduler, Catalyst planning, SQL/DataFrame APIs, shuffle, and data-source
integrations; it does not by itself define the business grain, make arbitrary
side effects idempotent, certify data quality, or atomically publish a complete
multi-file dataset.

For an Android engineer, a `DataFrame` chain can initially resemble a lazy Kotlin
`Sequence` or `Flow`. The useful part is that transformations describe work before
a terminal operation consumes it. The analogy stops because Spark may rewrite the
relational plan, split it into stages, run thousands of task attempts on remote
processes, and materialize shuffle or spill data outside Python memory.

## Prerequisites

- Data contracts, SLOs, trust boundaries, and capacity estimates from [01 Big Data and Data Engineering Foundations](../01-big-data-and-data-engineering-foundations/README.md).
- Python functions, iterators, packaging, testing, and resource ownership from [02 Python for Data Engineering](../02-python-for-data-engineering/README.md).
- SQL types, `NULL`, grouping, joins, windows, and plans from [03 SQL and Analytical Querying](../03-sql-and-analytical-querying/README.md).
- Parquet, partition layout, schema evolution, and atomic publication from [04 Data Storage, Files, and Serialization](../04-data-storage-files-and-serialization/README.md).
- Grain, keys, dimensions, and metric semantics from [05 Data Modeling and Business Semantics](../05-data-modeling-and-business-semantics/README.md).
- Incremental processing, checkpoints, backfills, and repair from [07 Batch Processing and ETL/ELT](../07-batch-processing-and-etl-elt/README.md).
- Partitions, DAGs, shuffle, skew, retries, and capacity from [08 Distributed Systems Foundations](../08-distributed-systems-foundations/README.md).
- No Spark installation or cluster is required to read this documentation; the repository's optional `spark-notebook` dependency group supports local notebook practice.

## Learning path

1. [Spark architecture: driver, executors, and clusters](01-spark-architecture-driver-executors-and-clusters.md) assigns process, resource, and failure ownership.
2. [DataFrames, Spark SQL, schemas, and types](02-dataframes-spark-sql-schemas-and-types.md) establishes the typed relational contract and Python/JVM boundary.
3. [Lazy evaluation, logical plans, and physical plans](03-lazy-evaluation-logical-and-physical-plans.md) translates expressions into jobs, stages, and tasks.
4. [Partitions, shuffles, parallelism, and output files](04-partitions-shuffles-parallelism-and-output-files.md) connects execution layout to movement and durable file layout.
5. [Joins, aggregation, broadcasting, and skew](05-joins-aggregation-broadcasting-and-skew.md) reasons from cardinality and statistics to join strategy and hot-key repair.
6. [Parquet, pushdown, partition pruning, and catalogs](06-parquet-pushdown-partition-pruning-and-catalogs.md) aligns storage metadata with efficient, correct reads.
7. [Caching, memory, serialization, and Python UDFs](07-caching-memory-serialization-and-python-udfs.md) manages reuse and language-boundary cost.
8. [Testing, tuning, failure diagnosis, and deployment](08-testing-tuning-failure-diagnosis-and-deployment.md) turns local code into operable cluster delivery.

## Shared reference pipeline

```text
immutable raw event files + declared schema + run manifest
                         |
                  Spark file scan
                         |
       validate / normalize / quarantine invalid rows
                         |
      deduplicate by (tenant_id, event_id)
                         |
 enrich with a small versioned product dimension
                         |
 shuffle by (tenant_id, product_id, event_date_utc)
                         |
       aggregate candidate daily product metrics
                         |
    reconcile + quality checks + generation manifest
                         |
       atomically publish one curated generation
```

| Boundary | Grain | Authority and owner | Stable identity |
| --- | --- | --- | --- |
| Raw event | One producer event receipt | Ingestion/raw owner | Tenant, producer, event ID |
| Valid event | One contract-conforming logical event | Pipeline owner; raw remains authoritative | Tenant and event ID |
| Product dimension row | One product version in an effective-time interval | Product master owner | Tenant, product, valid-from |
| Candidate metric | One tenant, product, and UTC event date | Spark job until certification | Business key + definition version + run |
| Published generation | Complete certified output scope | Curated dataset owner | Dataset, closed input scope, generation |

Starting workload assumptions are 3 million events/day, about 3 GiB compressed
input, 16 initial file partitions, a product dimension below 10 MiB serialized,
35% of events from one tenant, a 45-minute batch objective, and 15 minutes of
recovery reserve. These are design hypotheses, not measurements.

## Durable Spark contract

Every production design should answer:

- What is the row grain at every DataFrame boundary and which schema is enforced?
- Which expressions preserve SQL `NULL`, timestamp, decimal, and overflow semantics?
- Which action creates each job, which exchanges create stages, and how many tasks result?
- Where do bytes move, spill, cache, cross Python/JVM boundaries, and become durable?
- Which statistics justify broadcast, partition count, and adaptive-plan decisions?
- How do duplicate inputs and duplicate task attempts converge to one business result?
- What candidate-output and manifest protocol prevents partial consumer visibility?
- Which plan, task, quality, reconciliation, failure, and load evidence proves the claim?

## Evidence and scope

This pass contains worked DataFrame/SQL fragments, plan-reading procedures, decision tables, failure models, capacity arithmetic, deployment controls, and explicit pending evidence. The repository now declares an optional PySpark notebook dependency group, and a Windows environment smoke check started PySpark 4.2.0 with Python 3.14.5 and Java 21, ran a `local[2]` DataFrame filter through Python workers, collected the expected row, and stopped the session on 2026-09-12. It does not add an Area 09 executable job, deterministic fixture, committed test, cluster configuration, or benchmark. Therefore topic-level local behavior, physical plans, shuffle metrics, skew handling, executor loss, packaging, and cluster behavior remain unverified.

Spark 4.2.0 documentation was the version-sensitive reference reviewed in
2026-09. Pin and test an exact Spark/Python/Java/catalog combination before adding
runtime artifacts; `latest` documentation and defaults can change.

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] Architecture, structured APIs, planning, partitions, joins, storage, memory, Python boundaries, and operations covered
- [x] Grain, ownership, `NULL`, time, failure, security, quality, capacity, compatibility, and publication addressed
- [x] Current Spark primary documentation linked and review version/date stated
- [x] Examples and evidence accurately marked Planned
- [x] Optional PySpark notebook environment declared and local startup/worker smoke check passed
- [ ] Deterministic fixtures and topic-level local-mode tests implemented
- [ ] Plans, shuffle/skew metrics, executor-failure, load, and cluster evidence executed
