# 05 Data Modeling and Business Semantics

> Area status: Documentation complete; executable reference models planned  
> Level: Beginner to Intermediate data engineering  
> Applies to: Relational systems / Warehouses / Lakehouses / Semantic layers  
> Reference scenario: Product catalog, customers, and mobile product events  
> Evidence boundary: Documentation and contract review; no database or semantic engine execution yet  
> Last reviewed: 2026-09

## Purpose

This area explains how records acquire stable business meaning. A storage schema
can describe columns and types, but a usable model must also state what one row
means, how identity is resolved, which history is retained, which system is
authoritative, and how consumers calculate measures consistently.

For an Android engineer, a data model initially resembles a Room schema plus
domain entities. The analogy helps with keys, constraints, migrations, and
ownership. It stops when the same business fact is represented at several grains,
historical answers must be reproducible after source state changes, and many
independently deployed consumers reuse governed analytical definitions.

## Prerequisites

- Complete [01 Big Data and Data Engineering Foundations](../01-big-data-and-data-engineering-foundations/README.md), especially grain, authority, lineage, and consumer requirements.
- Understand relations, bags, keys, `NULL`, joins, aggregation, and transactions from [03 SQL and Analytical Querying](../03-sql-and-analytical-querying/README.md).
- Understand schema and dataset evolution from [04 Data Storage, Files, and Serialization](../04-data-storage-files-and-serialization/README.md).
- No warehouse, modeling framework, or semantic-layer product is required for this documentation pass.

## Learning path

1. [Requirements, grain, entities, and relationships](01-requirements-grain-entities-and-relationships.md) turns stakeholder language into explicit row meaning and invariants.
2. [Relational modeling, normalization, and integrity](02-relational-modeling-normalization-and-integrity.md) protects transactional authority with dependencies and constraints.
3. [Dimensional modeling: facts, dimensions, and stars](03-dimensional-modeling-facts-dimensions-and-stars.md) reshapes business processes for understandable analytical queries.
4. [Business keys, surrogate keys, and identity resolution](04-business-keys-surrogate-keys-and-identity-resolution.md) separates durable business identity from storage and source identifiers.
5. [Slowly changing dimensions and bitemporal history](05-slowly-changing-dimensions-and-bitemporal-history.md) makes historical change, correction, and as-of answers explicit.
6. [Snapshots, events, and state reconstruction](06-snapshots-events-and-state-reconstruction.md) compares change records, current state, periodic state, and process milestones.
7. [Metrics, semantic layers, and consistent meaning](07-metrics-semantic-layers-and-consistent-meaning.md) defines reusable measures, denominators, dimensions, cohorts, and versions.
8. [Data marts, domain products, and model evolution](08-data-marts-domain-products-and-model-evolution.md) packages models for consumers and evolves them without silent semantic breakage.

## Shared reference model

The planned example follows product interactions from authoritative operational
state to analytical consumption:

```text
catalog + customer authority       immutable mobile-event deliveries
             |                                  |
             +---------- validate/resolve ------+
                                |
                 conformed product/customer dimensions
                                |
                    event and purchase facts
                                |
                 governed metrics + domain marts
                                |
                  product, growth, finance consumers
```

| Dataset | Grain | Authority | Representative consumer |
| --- | --- | --- | --- |
| Product source table | One current product per source-scoped product key | Catalog service | Operational workflows and dimension builder |
| Event ledger | One accepted logical event per `event_id` | Event data-product owner | Replay and fact builder |
| Product dimension | One product history version per validity/system interval | Analytical model owner; derived | Historical joins |
| Product-event fact | One accepted product event | Analytical model owner; derived | Behavioral analysis |
| Daily product snapshot | One product, tenant, and UTC day | Mart owner; derived | Dashboard and anomaly detection |
| Metric definition | One versioned semantic contract | Named business and data owners | BI, experiments, and alerts |

Starting assumptions are 3 million accepted events/day, 100,000 current products,
5 million customers, 35 days of hot event data, and two years of daily aggregates.
These figures maintain continuity with earlier areas and are estimates, not
measurements. Tenant is part of every scoped business key; event time is retained
in UTC; late events and corrections publish new versioned outputs rather than
silently rewriting a previously certified result.

## Durable separation of concerns

| Need | Model optimized for it | Do not assume |
| --- | --- | --- |
| Enforce current write invariants | Normalized relational authority | It is the easiest shape for analytics |
| Preserve what happened | Immutable event/transaction facts | The latest entity state describes past context |
| Make analytical joins legible | Star schema with declared fact grain | Every measure is additive |
| Reproduce historical context | Versioned dimensions and temporal joins | A type-2 table is automatically bitemporal |
| Reuse business meaning | Governed metric/semantic contract | A shared SQL expression alone establishes ownership |
| Serve a consumer domain | Mart/data-product interface | A copied table remains consistent without a contract |

These are roles, not mandatory physical platforms. One database may initially
implement several roles, provided authority and publication boundaries remain
explicit.

## Evidence and scope

The guides contain model sketches, SQL patterns, failure cases, migration plans,
and exact future evidence. No schema, constraint, temporal query, identity merge,
metric engine, performance test, or consumer migration has run. All working
examples are therefore Planned.

Physical warehouse tuning, vendor-specific DDL, dbt project mechanics, streaming
state stores, statistical experimentation, BI visualization, and organization-wide
governance implementation are outside this area. Later areas supply ingestion,
processing, orchestration, quality, governance, and operational evidence.

## Area completion checklist

- [x] Eight inventory guides authored in the planned order
- [x] Grain, identity, authority, relationships, and integrity made explicit
- [x] Normalized, dimensional, event, snapshot, semantic, and mart roles compared
- [x] Historical validity, knowledge time, late data, correction, and replay covered
- [x] Security, privacy, ownership, quality, observability, and migration addressed
- [x] Evidence limitations recorded without claiming runtime verification
- [ ] Relational and dimensional DDL plus deterministic fixtures implemented
- [ ] Constraint, history, identity, reconciliation, and metric tests executed
- [ ] Query plans, realistic cardinalities, operational recovery, and migration verified

