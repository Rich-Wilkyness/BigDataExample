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
| `WH-M01` Medallion Sales Pipeline | Environment and isolation; deterministic source delivery; manifest verification; pandas source profiling; idempotent raw ingestion; Bronze inspection and reconciliation; Silver and later stages are pending | Python; pandas; SQLAlchemy; PostgreSQL; notebook | Fixed database allowlist; SHA-256 source integrity; exact 40-to-40 reconciliation; stable batch/file/row lineage; exact source-value preservation; author tests | Creates and verifies isolated lab state; restores deterministic source data; provides Gold-only, Silver-and-Gold, all-layer, and full-database reset commands | Stage 1 practiced and verified through Bronze; stop before Silver |

## Coverage by capability

| Capability | Evidence so far | Depth | Important next expansion |
| --- | --- | --- | --- |
| Requirements and consumer contract | DV-E23 business request and exact output contract | Practiced | Ambiguous requirements, freshness, SLAs, and consumer negotiation |
| Grain, schema, and types | DV-E23 explicit Spark schema; WH-M01 source grain, 11-column string DataFrame, and 16-column permissive Bronze table | Introduced and verified | Learner-authored Silver types, schema evolution, decimals, timestamps, and nested data |
| Batch transformation | DV-E23 filter, projection, and deterministic ordering | Practiced and verified | Joins, aggregation, windows, deduplication, incremental processing, and publication |
| Spark execution reasoning | DV-E23 lazy plan, pushed filters, exchange, and global sort | Introduced | Partition sizing, joins, skew, caching, spill, tuning, and cluster execution |
| Data testing | DV-E23 learner result checker; WH-M01 deterministic generator tests, manifest verification, lineage checks, and exact source-to-Bronze reconciliation | Practiced and verified | Silver data-quality gates, property tests, broader integration tests, and failure injection |
| Data ingestion | WH-M01 generates a versioned CSV delivery, verifies its manifest, and idempotently replaces one batch in Bronze | Practiced and verified | Multiple batches, late files, schema evolution, quarantine, and replay |
| ETL and ELT layers | WH-M01 implements and verifies source → Bronze while outlining later boundaries | Practiced and verified through Bronze | Implement Bronze → Silver and Silver → Gold, then add an ELT comparison |
| SQL | No learner SQL implemented; WH-M01 currently uses SQLAlchemy only for environment verification | Not covered | Durable DDL and transformation SQL, analytical queries, and query-plan work |
| Linux and scheduling | No implemented lab | Not covered | Shell safety, CLI jobs, exit codes, logging, cron, reruns, and locks |
| Messaging and streaming | No implemented lab | Not covered | Producer, Kafka broker, consumer groups, offsets, schemas, checkpoints, and replay |
| Storage and table formats | DV-E23 CSV input; WH-M01 deterministic CSV plus JSON manifest and PostgreSQL Bronze table | Practiced and verified | JSON Lines, Parquet, partitioning, object-store layout, and transactional table formats |
| Orchestration | No implemented lab | Not covered | DAGs, dependencies, retries, backfills, time zones, and deployment |
| Reliability and observability | DV-E23 Spark plan discussion; WH-M01 idempotent database setup and author-verified bounded reset entry points | Introduced and verified for WH-M01 setup state | Metrics, structured logs, alerts, runbooks, partial failure, repair, and SLOs |
| Governance and security | WH-M01 protects credentials, verifies source integrity, and records batch/file/row lineage | Introduced and verified | Classification, access boundaries, masking, end-to-end lineage, retention, and audits |
| Performance and cost | Global ordering cost introduced | Introduced | Workload estimates, benchmarks, capacity, cloud cost, and tradeoff decisions |

## Maintenance rule

Update this file only from implemented lab behavior and evidence that actually exists. Record a capability as Operated only when the learner manipulates state or responds to realistic runtime conditions; prose discussion alone is Introduced. Before generating a large batch of similar labs, use this inventory to prefer uncovered techniques or a deeper delivery scope over another near-duplicate drill.
