# Big data engineering curriculum

This directory is the learning map for `BigDataExample`. It begins with no
assumed data-engineering knowledge and progresses to senior-level design,
delivery, diagnosis, and operation of data-intensive systems. Python and SQL
provide the primary executable path, but each subject begins with the durable
data contract, execution model, or failure mode before introducing a tool.

The learner is assumed to have middle-to-senior Kotlin and Android experience.
The guides should reuse that experience when it clarifies a concept—for example,
comparing Kotlin sequences with Python generators or Room transactions with
warehouse publication—but must identify where the comparison stops working.

Every learning topic answers six questions:

1. What does one record represent, and who produces and consumes it?
2. Which dataset or system is authoritative, and who owns its lifecycle?
3. What correctness, freshness, scale, security, and cost requirements apply?
4. What happens with invalid, missing, duplicate, late, out-of-order, or
   partially processed data?
5. How do Python, SQL, and the selected engine implement the decision?
6. What inspectable evidence shows that the implementation satisfies its contract?

New learning guides begin with the [canonical topic template](TOPIC_TEMPLATE.md).
Interview-question discovery and completion use the
[interview preparation workflow](INTERVIEW_PREP_WORKFLOW.md), while completed
answers use the separate
[interview question template](INTERVIEW_QUESTION_TEMPLATE.md). Guide, example,
test, and production-evidence status is tracked in [COVERAGE.md](COVERAGE.md).

## System mental model

```text
producers and source systems
  apps | APIs | databases | files | devices
                    |
          ingestion and contracts
                    |
      raw, immutable landing data
                    |
       batch or stream processing
                    |
      validated and modeled datasets
                    |
 warehouse | lakehouse | serving systems
                    |
 analytics | operations | applications | ML

Cross-cutting: orchestration, metadata, quality, lineage,
security, privacy, observability, reliability, and cost.
```

Data often outlives every program that produced it. A locally correct function
is not enough: sources change, records arrive late or twice, jobs are rerun,
partitions skew, outputs are published partially, consumers coexist on different
schema versions, and repair work can be larger than the original computation.

## Curriculum areas

The 16 areas are stable ownership categories, not single lessons. Each area will
contain an unnumbered `README.md` plus multiple numbered guides. Detailed planned
guide inventories live in `COVERAGE.md`.

| Area | Purpose | Initial status |
| --- | --- | --- |
| 01 Big Data and Data Engineering Foundations | Data lifecycles, roles, scale, batch/streaming, OLTP/OLAP, requirements, boundaries, and the first end-to-end mental model | Scope planned |
| 02 Python for Data Engineering | Python semantics, typing, iteration, resource ownership, packaging, concurrency, testing, memory, and profiling for a Kotlin engineer | Documentation complete; package smoke test verified; reference implementation planned |
| 03 SQL and Analytical Querying | Relational thinking, joins, aggregation, `NULL`, analytical SQL, transactions, query plans, indexes, and performance | Documentation complete; executable query suite planned |
| 04 Data Storage, Files, and Serialization | Encodings, CSV/JSON, Avro, Parquet, Arrow, compression, object storage layouts, partitioning, metadata, and schema evolution | Scope planned |
| 05 Data Modeling and Business Semantics | Grain, normalization, dimensional models, keys, history, snapshots, events, metrics, marts, and model evolution | Scope planned |
| 06 Data Ingestion and Source Integration | Files, APIs, databases, CDC, events, validation, quarantine, idempotency, rate limits, security, and reconciliation | Documentation complete; executable ingestion and integration evidence planned |
| 07 Batch Processing and ETL/ELT | Pipeline stages, Python/SQL transformations, incremental loads, checkpoints, publication, reruns, backfills, lineage, and recovery | Documentation complete; executable batch pipeline and evidence planned |
| 08 Distributed Systems Foundations | Partitions, replication, consistency, coordination, MapReduce, locality, shuffles, skew, backpressure, and partial failure | Scope planned |
| 09 Apache Spark and Distributed Computation | Spark architecture, DataFrames/SQL, lazy plans, jobs/stages/tasks, partitions, joins, memory, UDFs, tuning, testing, and deployment | Documentation complete; executable PySpark and distributed evidence planned |
| 10 Messaging, Streaming, and Change Data Capture | Logs, brokers, Kafka, delivery and ordering, event time, windows, watermarks, state, replay, Structured Streaming, and CDC | Scope planned |
| 11 Warehouses, Lakes, Lakehouses, and Serving Systems | Storage-system selection, analytical architectures, catalogs, table formats, transactions, compaction, serving, BI, and ML boundaries | Scope planned |
| 12 Workflow Orchestration and Transformation Management | DAGs, scheduling, Airflow, task isolation, retries, backfills, SQL model management, environments, metadata, and delivery | Scope planned |
| 13 Data Quality, Contracts, and Testing | Quality dimensions, contracts, assertions, fixtures, integration/system tests, reconciliation, anomaly response, and quality objectives | Scope planned |
| 14 Governance, Security, Privacy, and Data Lifecycle | Ownership, catalogs, lineage, classification, access control, encryption, masking, auditing, retention, deletion, and isolation | Scope planned |
| 15 Reliability, Observability, Performance, Cost, and Operations | Signals, objectives, incidents, recovery, capacity, optimization, cost controls, infrastructure, rollout, and disaster recovery | Documentation complete; executable operational evidence planned |
| 16 Senior Data Architecture, System Design, and Leadership | Requirements, estimation, alternatives, migrations, data products, platform ownership, RFCs, delivery risk, incidents, strategy, and capstones | Documentation complete; learner capstone and executable evidence planned |

## Recommended learning path

Follow numbered areas in ascending order for a first pass, with these deliberate
overlaps:

1. Learn Python and SQL together after the foundational mental model.
2. Use bounded local files, DuckDB-style analytical SQL, and a relational
   database before adding a cluster.
3. Introduce testing, quality, security, observability, and cost in the first
   executable pipeline; their dedicated areas later synthesize the practices.
4. Learn distributed-systems mechanics before Spark so partitions, shuffles,
   skew, laziness, and recovery are not treated as framework magic.
5. Learn batch correctness before streaming adds event time, unbounded state,
   replay, and continuous operation.
6. Complete a senior capstone only after individual guarantees have focused,
   inspectable evidence.

```text
foundations
    |
Python + SQL
    |
files + modeling + local analytical processing
    |
ingestion + reliable batch pipelines
    |
distributed systems + Spark
    |
messaging + streaming + CDC
    |
warehouse/lakehouse + orchestration
    |
quality + governance + production operations
    |
senior architecture and leadership capstone
```

## Progressive reference system

The curriculum should grow one coherent example rather than accumulate unrelated
snippets. The initial reference system will model mobile product events because
the domain is familiar while the data-engineering problems are new:

```text
versioned mobile events
        |
bounded ingestion and quarantine
        |
immutable raw files
        |
validated sessions and product facts
        |
incremental batch, then streaming aggregates
        |
analytical tables and consumer-facing metrics
```

Later iterations add database CDC, object storage, Spark, a broker, orchestration,
schema evolution, late events, deletion, backfills, quality incidents, capacity
planning, and recovery. The domain may change if a better capstone emerges; its
learning invariants should remain stable.

## Topic workflow

Every implemented topic follows the same inspectable loop:

```text
requirements and grain
        |
smallest correct example
        |
realistic data or system failure
        |
diagnose the owning boundary
        |
repair and explain the guarantee
        |
tests, quality checks, plans, or measurements
        |
production and evolution tradeoff
        |
coverage update
```

An authored guide is not verified merely because generated code looks plausible.
Evidence must distinguish bounded fixtures, in-process doubles, local real
engines, distributed environments, and production observations.

## Documentation layout

As areas are implemented, use this convention:

```text
docs/
|-- 01-big-data-and-data-engineering-foundations/
|   |-- README.md
|   |-- 01-first-topic.md
|   `-- 02-second-topic.md
|-- ...
|-- 16-senior-data-architecture-system-design-and-leadership/
|-- COVERAGE.md
|-- INTERVIEW_PREP_WORKFLOW.md
|-- INTERVIEW_QUESTION_TEMPLATE.md
|-- LANGUAGE_INTERVIEW_QUESTIONS.md
|-- PLATFORM_INTERVIEW_QUESTIONS.md
|-- README.md
`-- TOPIC_TEMPLATE.md
```

Numbering restarts at `01` inside every area. Area READMEs establish prerequisites,
study order, examples, and evidence expectations; they are not numbered lessons.

An area README should stay compact. It needs only the area's purpose, prerequisites,
ordered guide index, recommended study path, reference example, current evidence
status, and links to related areas. The detailed teaching contract belongs in the
topic guides, and planned scope/status belongs in `COVERAGE.md`.

## Definition of complete

A learning topic is complete only when, where relevant, it includes:

- A durable mental model and precise terminology.
- Explicit record grain, ownership, authority, consumers, and trust boundaries.
- Scale, freshness, correctness, privacy, retention, and cost requirements.
- Relevant Python, SQL, engine, storage, and infrastructure behavior.
- A focused correct example and realistic failure demonstration.
- Tests, data-quality checks, query plans, measurements, or operational evidence.
- Debugging and recovery paths that identify the owning layer.
- Duplicate, late, out-of-order, partial, incompatible, and overload behavior.
- Security, governance, observability, performance, and lifecycle implications.
- Schema evolution, backfill, deployment, reconciliation, and rollback concerns.
- Engineering tradeoffs tied to requirements rather than a preferred product.
- An accurate coverage entry that does not overclaim scale or verification.

Area completion requires all foundational guides plus the area-level integration
exercise. Senior readiness additionally requires cross-area capstones and the
ability to predict, diagnose, repair, modify, and explain the system without
copying a guide.
