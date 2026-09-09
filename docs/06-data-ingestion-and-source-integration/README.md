# 06 Data Ingestion and Source Integration

> Area status: Documentation complete; executable reference ingestion planned  
> Level: Beginner to Intermediate data engineering  
> Applies to: Files / Object storage / APIs / Databases / Change logs / Events  
> Reference scenario: Product catalog, orders, and mobile product events  
> Evidence boundary: Documentation and contract review; no external source or broker execution yet  
> Last reviewed: 2026-09

## Purpose

This area explains how data crosses from a producer-owned system into a durable,
replayable analytical boundary. Ingestion is not merely moving bytes: it must
preserve source meaning, prove what was received, bound source and platform load,
and recover without silently dropping or multiplying logical records.

For an Android engineer, an ingestion adapter resembles a repository that reads a
remote API and persists a local cache. The analogy helps with contracts, retries,
pagination, and ownership. It stops where years of immutable deliveries, multiple
writers, distributed acknowledgements, historical replay, and reconciliation are
part of the interface.

## Prerequisites

- Understand producers, consumers, SLOs, lineage, and delivery semantics from [01 Big Data and Data Engineering Foundations](../01-big-data-and-data-engineering-foundations/README.md).
- Understand bounded Python processing and resource lifetime from [02 Python for Data Engineering](../02-python-for-data-engineering/README.md).
- Understand keys, transactions, and query boundaries from [03 SQL and Analytical Querying](../03-sql-and-analytical-querying/README.md).
- Understand formats, checksums, immutable publication, and schema evolution from [04 Data Storage, Files, and Serialization](../04-data-storage-files-and-serialization/README.md).
- Understand grain and identity from [05 Data Modeling and Business Semantics](../05-data-modeling-and-business-semantics/README.md).
- No cloud account, database, broker, or connector platform is required for this documentation pass.

## Learning path

1. [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md) defines the receipt boundary, evidence, authority, and acknowledgement contract.
2. [File and object ingestion](02-file-and-object-ingestion.md) handles discovery, completeness, manifests, checksums, duplicates, and archive.
3. [API ingestion, pagination, and rate limits](03-api-ingestion-pagination-and-rate-limits.md) makes page traversal, quotas, retries, and incremental state recoverable.
4. [Database snapshots and incremental extracts](04-database-snapshots-and-incremental-extracts.md) selects consistent cuts, high-water marks, delete handling, and source-safe extraction.
5. [Change data capture logs and connectors](05-change-data-capture-logs-and-connectors.md) follows snapshots into ordered transaction-log changes and detects gaps.
6. [Event ingestion, batching, and backpressure](06-event-ingestion-batching-and-backpressure.md) controls admission, batching, acknowledgements, and overload.
7. [Validation, quarantine, and schema evolution](07-validation-quarantine-and-schema-evolution.md) separates structural acceptance from semantic fitness and safe reprocessing.
8. [Idempotency, deduplication, late data, and reconciliation](08-idempotency-deduplication-late-data-and-reconciliation.md) proves that retries and corrections converge on the intended result.

## Shared reference flow

```text
files + API + database + mobile-event endpoint
                     |
          source-specific acquisition
                     |
        durable receipt + source metadata
                     |
      validate -----+----- quarantine
                     |
        immutable accepted raw dataset
                     |
       downstream batch/stream processing
```

| Boundary dataset | Grain | Authority | Required identity |
| --- | --- | --- | --- |
| Delivery receipt | One acquired source unit or event delivery | Ingestion owner | Source, extraction/run, and delivery position |
| Raw payload | One byte-preserving acquired object/message | Ingestion owner for the copy; producer for meaning | Content checksum plus source identity |
| Accepted raw record | One structurally accepted source record | Ingestion data-product owner | Source-scoped logical or delivery identity |
| Quarantine record | One rejected payload plus safe diagnostic metadata | Ingestion owner | Stable rejection ID linked to receipt |
| Checkpoint | One committed progress boundary per source partition | Ingestion owner | Source plus partition and monotonic position |

Starting estimates are 3 million mobile events/day, a 20 GiB nightly file drop,
100,000 catalog rows per full extract, 50 database changes/second normally with a
500/second burst, and a 15-minute freshness objective. These are design inputs,
not measurements.

## Durable ingestion contract

Every source adapter must answer:

- What source unit is discoverable, complete, stable, and safe to read?
- Which bytes and source metadata are durably retained before progress advances?
- Does acknowledgement mean received, durably stored, validated, or published?
- What identity distinguishes a retry from a new logical record?
- How are omissions, duplicates, gaps, deletes, late arrivals, and corrections detected?
- Who may replay, quarantine, redact, retain, and delete the raw copy?
- Which counts or digests reconcile source scope to accepted, rejected, and deferred outcomes?

Raw is immutable evidence, not automatically authoritative business truth. The
producer remains authoritative for source meaning; the ingestion owner is
authoritative for what was received and how it was classified.

## Evidence and scope

The guides specify state machines, SQL and Python sketches, failure cases,
reconciliation equations, and future evidence. No real API, database log, broker,
object store, connector, load test, or recovery drill has run. All working
examples are Planned.

Downstream transformation, distributed processing, streaming windows, serving
systems, orchestration products, and organization-wide governance are handled in
later areas. This area defines the handoff contracts those systems consume.

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] File, API, database, CDC, and event acquisition boundaries compared
- [x] Identity, checkpoints, acknowledgements, retries, gaps, deletes, and late data addressed
- [x] Raw ownership, validation, quarantine, replay, lineage, privacy, and retention addressed
- [x] Capacity, backpressure, source protection, observability, and recovery plans included
- [x] Evidence limits recorded without claiming runtime verification
- [ ] Bounded source adapters, fixtures, state stores, and reconciliation reports implemented
- [ ] Contract, fault, restart, rate-limit, database, broker, and object-store evidence executed
