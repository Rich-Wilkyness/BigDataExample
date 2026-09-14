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

## Coverage by capability

| Capability | Evidence so far | Depth | Important next expansion |
| --- | --- | --- | --- |
| Requirements and consumer contract | DV-E23 business request and exact output contract | Practiced | Ambiguous requirements, freshness, SLAs, and consumer negotiation |
| Grain, schema, and types | DV-E23 record grain, explicit CSV schema, `LongType` count | Introduced and verified | Learner-authored schemas, schema evolution, rejected records, decimals, timestamps, and nested data |
| Batch transformation | DV-E23 filter, projection, and deterministic ordering | Practiced and verified | Joins, aggregation, windows, deduplication, incremental processing, and publication |
| Spark execution reasoning | DV-E23 lazy plan, pushed filters, exchange, and global sort | Introduced | Partition sizing, joins, skew, caching, spill, tuning, and cluster execution |
| Data testing | DV-E23 learner result checker and author-side reference tests | Practiced and verified | Data-quality gates, reconciliation, property tests, integration tests, and failure injection |
| Data ingestion | No implemented lab | Not covered | File/API/database ingestion, batch identity, validation, quarantine, and replay |
| ETL and ELT layers | No implemented lab | Not covered | Raw/source to bronze, bronze to silver, and silver to gold with both ETL and ELT variants |
| SQL | No implemented lab | Not covered | Query drills followed by durable transformation models and query-plan work |
| Linux and scheduling | No implemented lab | Not covered | Shell safety, CLI jobs, exit codes, logging, cron, reruns, and locks |
| Messaging and streaming | No implemented lab | Not covered | Producer, Kafka broker, consumer groups, offsets, schemas, checkpoints, and replay |
| Storage and table formats | CSV input only | Introduced | JSON Lines, Parquet, partitioning, object-store layout, and transactional table formats |
| Orchestration | No implemented lab | Not covered | DAGs, dependencies, retries, backfills, time zones, and deployment |
| Reliability and observability | Spark plan discussion only | Introduced | Metrics, structured logs, alerts, runbooks, partial failure, repair, and SLOs |
| Governance and security | No implemented lab | Not covered | Classification, access boundaries, masking, secrets, lineage, retention, and audits |
| Performance and cost | Global ordering cost introduced | Introduced | Workload estimates, benchmarks, capacity, cloud cost, and tradeoff decisions |

## Maintenance rule

Update this file only from implemented lab behavior and evidence that actually exists. Record a capability as Operated only when the learner manipulates state or responds to realistic runtime conditions; prose discussion alone is Introduced. Before generating a large batch of similar labs, use this inventory to prefer uncovered techniques or a deeper delivery scope over another near-duplicate drill.
