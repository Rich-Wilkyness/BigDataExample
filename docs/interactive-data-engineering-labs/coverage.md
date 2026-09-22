# Interactive Lab Coverage

> Status: Active inventory; update whenever a lab adds or materially deepens practice

## Purpose

This inventory tracks whether the lab sequence covers the tools, workflow stages, correctness concerns, and operational responsibilities encountered in data-engineering work. It is separate from source-question counts: one source question may exercise several areas, and repeated shallow exposure does not equal production readiness.

## Depth scale

| Depth | Meaning |
| --- | --- |
| Introduced | The notebook explains or demonstrates the concept. |
| Practiced | The learner must use the concept to complete an exercise. |
| Verified | Automated evidence checks the learner-visible behavior or maintained reference implementation. |
| Operated | The learner handles state, failure, reruns, observability, or another production lifecycle concern. |

## Implemented lab evidence

| Lab | Workflow coverage | Tool coverage | Correctness coverage | Operational coverage | Current depth |
| --- | --- | --- | --- | --- | --- |
| `DV-E23` High-Engagement Video Filtering | Interpret request; inspect input grain and schema; implement transformation; check result; inspect plan; reflect on production placement | Python function; PySpark DataFrame API; Spark local execution | Explicit schema; strict and inclusive predicates; null exclusion; exact projection; deterministic tie order; reference unit tests | Identifies global-sort shuffle and driver collection limits; no persisted state or recovery | Practiced and verified technique drill |
| `OP-C01` Containerized Pipeline Runtime | Read command and configuration APIs; trace host/runtime configuration; build a pipeline image; wire two services; orchestrate one command; inspect persisted and generated state | Dockerfile instruction API; Docker Compose service API; Bash and Docker CLI APIs; PostgreSQL; SQLAlchemy connection boundary; Python verification harness | Static placeholder/configuration checks; PostgreSQL row-count check; independent source-to-report reconciliation | Health-gated startup; one-shot versus long-running service lifecycle; bind mounts; named volume persistence; rerun and bounded reset procedures | Starter scaffold, API field guide, and checks implemented; runtime verification requires completed learner files |
| `OP-C02` Python Pipeline Setup with SQLAlchemy | Read function and method APIs; read runtime configuration; define analytical SQL; establish the engine and transaction; create database objects; full-refresh a table; query and publish a report | Python environment and filesystem APIs; SQLAlchemy Core; pandas SQL I/O and CSV publication; PostgreSQL DDL and aggregation; supplied Docker Compose runtime | Explicit PostgreSQL types and key; transaction-scoped DDL/load/query; deterministic report order; static contract checks; runtime row-count and independent report reconciliation | Commit/rollback boundary; connection-pool disposal; idempotent object creation; repeatable full refresh; bounded reset | Starter module, API field guide, and checks implemented; runtime verification requires the completed learner module |
| `WH-M01` Medallion Sales Pipeline | Environment and isolation; deterministic source delivery; manifest verification; pandas source profiling; idempotent raw ingestion; Bronze inspection and reconciliation; Silver and later stages are pending | Python; pandas; SQLAlchemy; PostgreSQL; notebook | Fixed database allowlist; SHA-256 source integrity; exact 40-to-40 reconciliation; stable batch/file/row lineage; exact source-value preservation; author tests | Creates and verifies isolated lab state; restores deterministic source data; provides Gold-only, Silver-and-Gold, all-layer, and full-database reset commands | Stage 1 practiced and verified through Bronze; stop before Silver |

## Coverage by capability

| Capability | Evidence so far | Depth | Important next expansion |
| --- | --- | --- | --- |
| Requirements and consumer contract | DV-E23 business request and exact output contract | Practiced | Ambiguous requirements, freshness, SLAs, and consumer negotiation |
| Grain, schema, and types | DV-E23 explicit Spark schema; WH-M01 source grain, 11-column string DataFrame, and 16-column permissive Bronze table | Introduced and verified | Learner-authored Silver types, schema evolution, decimals, timestamps, and nested data |
| Batch transformation | DV-E23 filter, projection, and deterministic ordering; OP-C02 database aggregation and CSV publication | Practiced and verified in DV-E23; practiced with runtime verification pending in OP-C02 | Joins, windows, deduplication, incremental processing, and atomic publication |
| Spark execution reasoning | DV-E23 lazy plan, pushed filters, exchange, and global sort | Introduced | Partition sizing, joins, skew, caching, spill, tuning, and cluster execution |
| Data testing | DV-E23 learner result checker; WH-M01 deterministic generator tests, manifest verification, lineage checks, and exact source-to-Bronze reconciliation | Practiced and verified | Silver data-quality gates, property tests, broader integration tests, and failure injection |
| Data ingestion | WH-M01 generates a versioned CSV delivery, verifies its manifest, and idempotently replaces one batch in Bronze | Practiced and verified | Multiple batches, late files, schema evolution, quarantine, and replay |
| ETL and ELT layers | WH-M01 implements and verifies source → Bronze while outlining later boundaries | Practiced and verified through Bronze | Implement Bronze → Silver and Silver → Gold, then add an ELT comparison |
| SQL | OP-C02 learner-authored schema/table DDL, `TRUNCATE`, and `GROUP BY`/`SUM`/`ORDER BY` reporting query through SQLAlchemy | Practiced; runtime verification pending | Joins, windows, incremental SQL, migrations, and query-plan work |
| Linux and scheduling | OP-C01 uses strict Bash, path anchoring, file checks, exit codes, and a one-command job entry point | Introduced and practiced for Bash job entry | Scheduling, structured logging, cron, reruns under failure, and locks |
| Messaging and streaming | No implemented lab | Not covered | Producer, Kafka broker, consumer groups, offsets, schemas, checkpoints, and replay |
| Storage and table formats | DV-E23 CSV input; OP-C02 learner-defined PostgreSQL reporting table; WH-M01 deterministic CSV plus JSON manifest and PostgreSQL Bronze table | Practiced; verified for existing completed labs | JSON Lines, Parquet, partitioning, object-store layout, and transactional table formats |
| Orchestration | OP-C01 coordinates a health-gated PostgreSQL dependency and one-shot pipeline through Compose and Bash; OP-C02 supplies that runtime while the learner implements its Python execution lifecycle | Introduced and practiced locally | DAG schedulers, retries, backfills, time zones, and deployment |
| Reliability and observability | DV-E23 Spark plan discussion; OP-C01 readiness, persisted-state inspection, reconciliation, rerun, and bounded reset; OP-C02 transaction commit/rollback, connection cleanup, repeatable refresh, and bounded reset; WH-M01 idempotent database setup and author-verified bounded reset entry points | Introduced across labs; OP-C02 runtime verification pending | Metrics, structured logs, alerts, runbooks, partial failure, repair, and SLOs |
| Governance and security | WH-M01 protects credentials, verifies source integrity, and records batch/file/row lineage | Introduced and verified | Classification, access boundaries, masking, end-to-end lineage, retention, and audits |
| Performance and cost | Global ordering cost introduced | Introduced | Workload estimates, benchmarks, capacity, cloud cost, and tradeoff decisions |

## Maintenance rule

Update this file only from implemented lab behavior and evidence that actually exists. Record a capability as Operated only when the learner manipulates state or responds to realistic runtime conditions; prose discussion alone is Introduced. Before generating a large batch of similar labs, use this inventory to prefer uncovered techniques or a deeper delivery scope over another near-duplicate drill.
