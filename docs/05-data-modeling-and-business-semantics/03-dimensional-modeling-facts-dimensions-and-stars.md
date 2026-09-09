# Dimensional Modeling: Facts, Dimensions, and Stars

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Warehouses / Lakehouses / Analytical SQL / BI  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Dimensional modeling organizes a business process into fact tables at explicit
grains and dimensions that describe the surrounding who, what, where, when, and
how. A star schema accepts controlled denormalization so analytical questions use
predictable joins and understandable aggregation.

This guide covers transaction, periodic-snapshot, accumulating-snapshot, and
factless facts; conformed dimensions; additive behavior; degenerate dimensions;
and bridges. Historical version mechanics are expanded in guide 05.

## Learning objectives

- Declare a fact grain before choosing dimensions or measures.
- Classify measures as additive, semi-additive, non-additive, or derived.
- Design conformed dimensions and predictable star-schema joins.
- Diagnose fan-out, double counting, unknown members, and current-state leakage.
- Compare dimensional, normalized, and wide-table choices using consumer needs.

## Prerequisites

- [Requirements, grain, entities, and relationships](01-requirements-grain-entities-and-relationships.md)
- [Relational modeling, normalization, and integrity](02-relational-modeling-normalization-and-integrity.md)
- SQL joins, aggregation, windows, and query plans from area 03

## Mental model

```text
                  dim_date
                     |
dim_customer --- fact_product_event --- dim_product
                     |
                  dim_tenant
```

The fact row records an occurrence or measured state; dimension rows provide
descriptive context. The schema is designed from a business process and grain,
not by copying source tables and labeling the largest one “fact.”

This is somewhat like a stable telemetry event referencing normalized lookup
objects for UI labels. It stops because dimensions intentionally preserve
historical analytical context, may integrate multiple sources, and are optimized
for group-by scans rather than object navigation or transactional mutation.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Fact table | Rows at one declared process grain with foreign keys and measures |
| Dimension | Descriptive analytical context with stable join identity |
| Star schema | Fact table directly surrounded by dimensions |
| Conformed dimension | Shared meaning, keys, and values usable across fact models |
| Degenerate dimension | Business identifier stored on the fact without a separate dimension |
| Factless fact | Relationship/event fact whose occurrence is the measure |
| Bridge | Explicit relation for multivalued or hierarchical dimension membership |

## Requirements and invariants

- `fact_product_event` has one row per accepted `(tenant_id, event_id)`.
- Every dimension foreign key resolves to exactly one dimension row, including a
  governed unknown/not-applicable member when resolution is legitimately pending.
- Historical joins use event time and a non-overlapping applicable version.
- Quantity and revenue exist only for applicable event types and retain exact
  units/currency; missing is not silently zero.
- Measures are aggregated only along dimensions/time axes for which additivity is declared.
- Joining optional or multivalued dimensions cannot multiply a fact unnoticed.

Starting estimates remain 3M event facts/day, 100K products, and 5M customers.
Product dimensions are small relative to facts but history, tenant skew, and
many-to-many category bridges can still dominate joins.

## Choose the business process and grain

| Fact design | Grain | Useful measures | Update behavior |
| --- | --- | --- | --- |
| Transaction/event | One accepted product event | Event count, quantity, revenue | Insert/correct by versioned rebuild |
| Periodic snapshot | One product-location-day | Closing inventory, daily balance | One row per period after close |
| Accumulating snapshot | One order line lifecycle | Ordered-to-paid/shipped durations | Milestones update as process advances |
| Factless fact | One customer-campaign eligibility | Count eligible relationships | Insert/end-date relationship |

Do not combine these grains in one table. A daily inventory balance repeated on
each event is not additive and will inflate under event counts.

## Star-schema sketch

Generic analytical SQL; DDL is planned.

```sql
SELECT
    d.calendar_date,
    p.category_name,
    COUNT(*) FILTER (WHERE f.event_name = 'product_view') AS views,
    SUM(f.quantity) FILTER (WHERE f.event_name = 'purchase') AS units,
    SUM(f.extended_amount) FILTER (WHERE f.event_name = 'purchase') AS revenue
FROM fact_product_event AS f
JOIN dim_date AS d ON d.date_key = f.event_date_key
JOIN dim_product AS p ON p.product_key = f.product_key
WHERE f.tenant_key = :tenant_key
  AND d.calendar_date >= :start_date
  AND d.calendar_date < :end_date
GROUP BY d.calendar_date, p.category_name;
```

The result grain is one date-category pair. `COUNT(*)` counts fact rows only
because every joined dimension is many-to-one at the applicable version. `SUM`
ignores `NULL`; the model must prove null means non-applicable rather than missing
purchase data. Ordering is not guaranteed without `ORDER BY`.

## Measures and additivity

| Measure | Across product | Across time | Safe treatment |
| --- | --- | --- | --- |
| Purchase amount in one currency | Additive | Additive | Sum facts after currency filter/conversion |
| End-of-day inventory | Additive | Semi-additive | Sum products, not daily balances across dates |
| Conversion rate | Non-additive | Non-additive | Sum numerator and denominator, then divide |
| Unit price | Non-additive | Non-additive | Use weighted calculation appropriate to question |
| Event count | Additive if fact uniqueness holds | Additive | Count fact identity, not joined deliveries |

A derived ratio stored on each fact rarely aggregates correctly. Preserve
components and define the final aggregation in the metric contract.

## Dimension patterns

Conformed date, product, customer, tenant, channel, and campaign dimensions allow
facts from different processes to align. Conformance means more than matching
column names: key resolution, hierarchy, null members, history rules, privacy,
and owner must agree.

Order number can remain a degenerate dimension on a line fact when it has useful
filtering/drill-through identity but no independent descriptive attributes. A
product-category many-to-many relation needs a bridge with validity and an
allocation rule when measures must be distributed; an unweighted bridge will
repeat full fact measures for each membership.

## Data flow, ownership, and trust boundaries

Source authorities own current products, customers, and orders. The event ledger
owns accepted event identity. Dimension pipelines own integration and history;
fact builders own key resolution and measures; mart/semantic owners govern exposed
joins. BI tools consume stars but cannot retroactively define their grains.

Publish facts and the dimension versions they reference under a compatible
dataset snapshot. A fact visible before its dimension creates transient unknowns;
either accept that contract explicitly or commit them together.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Duplicate fact identity | Unique quality assertion/reconciliation | Deduplicate from ledger and rebuild affected partitions |
| Dimension overlap | More than one as-of match | Quarantine new version; repair intervals and re-key facts |
| Unresolved dimension surge | Unknown-key rate by safe dimensions | Restore lookup/input; late-bind and republish |
| Bridge fan-out | Pre/post-join counts and allocation sum | Correct validity/allocation; recalculate metrics |
| Current dimension used historically | Golden as-of query changes after update | Restore versioned join and backfill certified results |
| Partial star publication | Snapshot manifest mismatch | Keep prior snapshot; complete or abandon staged version |

## Security, privacy, and governance

Dimensions concentrate descriptive and identifying data. Minimize customer
attributes, tokenize identifiers, separate restricted mappings, and apply row/
column access at every serving copy. Small groups can re-identify people even
without direct IDs, so semantic outputs need suppression or policy enforcement.
Track lineage from source fields through dimension attributes and measures.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Fact uniqueness | One fact per declared event identity | Pending |
| Dimension resolution | Every fact maps to exactly one governed member | Pending |
| Hand-computed star query | Counts, units, revenue, and null cases match | Pending |
| Join mutation | Duplicate/overlapping dimension causes test failure | Pending |
| Bridge allocation | Allocated measures reconcile to original fact total | Pending |
| Query plan/profile | Scan, join, spill, and bytes recorded at scale | Pending |

## Common pitfalls

### Pitfall: building a star from available source tables

Sources describe operational boundaries, not necessarily one business process.
Choose process and grain, then source each required fact and dimension.

### Pitfall: assuming every numeric column is additive

Balances, percentages, prices, distinct counts, and cross-currency amounts need
declared aggregation rules. Store reusable components and units.

### Pitfall: snowflaking by habit

Normalizing dimensions can reduce repetition but adds joins and exposes internal
relationships to consumers. Use it when update/size/governance evidence outweighs
the simpler star, not because source authority was normalized.

## Performance, operations, and migration

Measure fact rows/bytes per partition, dimension and history cardinality, unknown
rate, join fan-out, skew, scan bytes, shuffle/spill, p50/p95 latency, concurrency,
and storage growth. Partition/filter primarily by actual access and lifecycle
needs; high-cardinality dimension columns are rarely good directory partitions.

Evolve a star by adding compatible attributes/facts, backfilling a new snapshot,
validating old and new metric outputs, migrating consumers, and contracting only
after lineage shows no use. A grain or key-strategy change requires a new model
version and explicit cutover.

## Working example

- SQL/data/tests: planned event fact, dimensions, dated category bridge, and six-event fixture
- Expected result: exact fact count, historical joins, measures, and bridge allocation reconcile
- Scale represented: none yet; query plans and distributed joins unverified
- Remaining risk: skew, late dimensions, history growth, and consumer-generated joins

## Knowledge check

1. Declare grains for transaction, periodic, and accumulating facts.
2. Predict which inventory and conversion measures can be summed across time.
3. Diagnose a revenue doubling after joining product categories.
4. Design unknown and not-applicable product members without conflating them.
5. Propose a conformance test for product across view and purchase facts.
6. Migrate an event fact to line-item purchase grain with rollback.

## Key takeaways

- Business process and grain determine a fact model.
- Dimensions make facts legible; conformance makes multiple facts comparable.
- Additivity is part of each measure's contract.
- Historical, multivalued, and unresolved dimensions require explicit join rules.
- Star simplicity is purchased with disciplined integration, quality, and governance.

## Resources

- [Kimball Group: Fact Tables](https://www.kimballgroup.com/2008/11/fact-tables/) (reviewed 2026-09)
- [Kimball Group: Dimensional Modeling Techniques](https://www.kimballgroup.com/wp-content/uploads/2013/08/2013.09-Kimball-Dimensional-Modeling-Techniques11.pdf) (reviewed 2026-09)

## Related topics

- [Business keys, surrogate keys, and identity resolution](04-business-keys-surrogate-keys-and-identity-resolution.md)
- [Slowly changing dimensions and bitemporal history](05-slowly-changing-dimensions-and-bitemporal-history.md)

## Completion checklist

- [x] Fact grains, dimensions, stars, conformance, and additivity explained
- [x] Bridges, unknowns, history, failure, security, scale, and migration addressed
- [ ] DDL, fixtures, reconciliations, plans, and scale evidence run
