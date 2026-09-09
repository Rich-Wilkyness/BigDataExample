# Requirements, Grain, Entities, and Relationships

> Status: Documentation complete; executable evidence planned  
> Level: Beginner  
> Applies to: Generic data engineering / SQL / Batch / Warehousing  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Data modeling begins by defining the decisions a dataset supports and what one
record represents. **Grain** is that record-level promise. Entities and
relationships become useful only after their identity, scope, cardinality,
optionality, time semantics, authority, and consumers are stated.

This guide covers requirements discovery, grain declarations, business events,
entities, relationships, and conceptual/logical/physical boundaries. It does not
choose a warehouse product or attempt a complete physical schema.

## Learning objectives

- Turn a business question into a dataset contract and declared grain.
- Distinguish an entity, event, relationship, attribute, and measure.
- Predict join cardinality from relationship rules before writing SQL.
- Detect mixed-grain models and requirements that cannot all be satisfied.
- Design evidence that proves row meaning rather than only column types.

## Prerequisites

- Area 01 concepts: producers, consumers, sources of truth, derived data, and SLOs
- Area 03 concepts: relations, keys, `NULL`, joins, and aggregation

## Mental model

A class name does not define an object's lifecycle, and a table name does not
define a row's meaning. Write a grain sentence that remains true for every row:

```text
one row represents one accepted product interaction
for one tenant, identified by event_id, at its producer event_time
```

Then make every field answerable at that grain. `product_name` may be the name
observed at event time, the current catalog name, or a foreign key to historical
context; those are different contracts.

The Kotlin analogy is a sealed domain event whose constructor enforces required
state. It stops at referential and historical questions: a distributed dataset
can contain years of independently produced records, and no constructor runs
across all files to enforce global uniqueness.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Grain | The exact real-world fact represented by one row at a named boundary |
| Entity | A thing whose identity and lifecycle matter independently |
| Event | An occurrence fixed to a time and identity; later knowledge may correct its representation |
| Relationship | An association with stated cardinality, optionality, scope, and time validity |
| Measure | A value aggregated or compared for a business decision |
| Dimension | Descriptive context used to group, filter, or interpret facts |
| Business process | A sequence or occurrence the organization needs to observe, such as product viewing or purchasing |

## Requirements, scale assumptions, and invariants

The reference consumer needs daily views, purchases, quantity, and revenue by
tenant and product as understood when the event occurred. Finance needs purchase
amount reconciliation; product teams accept corrections within seven days.

Starting estimates: 3M events/day, 100K products, 5M customers, a 15-minute daily
publication window, and 35 hot days. These assumptions are invalidated by source
profiles or consumer SLOs outside those bounds.

Invariants:

- `(tenant_id, event_id)` identifies one logical event; delivery retries do not add facts.
- Every fact declares whether its time is producer event time, ingestion time, or business-effective time.
- Product and customer identifiers are tenant-scoped unless an approved global mapping exists.
- A row contains attributes from one declared grain; lower-grain collections are separate relations.
- Unknown, not applicable, withheld, and not yet resolved are not collapsed into one accidental sentinel.
- Counts reconcile from accepted events through every published aggregate.

## From questions to models

| Consumer question | Required grain | Identity/time needed | Dangerous shortcut |
| --- | --- | --- | --- |
| How many product views occurred? | One accepted view event | Logical event ID and event time | Counting deliveries |
| How many products had stock at day end? | One product-location-day snapshot | Product, location, snapshot instant | Treating events as current state |
| How long did fulfillment take? | One order-line lifecycle or accumulating row | Milestone timestamps | Averaging event timestamps without pairing |
| What was revenue by category then? | One purchase line plus historical product version | Purchase identity and valid-time join | Joining to current category |

Requirements must name the decision, consumer, freshness, correction window,
dimensions, exclusions, security class, and acceptable reconciliation tolerance.
“Build a customer table” is not yet a modeling requirement.

## Entities and relationships

The reference domain includes tenant, customer, product, category, event, order,
and order line. An order contains one or more lines; a product may belong to
multiple categories over time; an event may lack a resolved customer.

```text
Tenant 1 --- * Product 1 --- * ProductEvent
Tenant 1 --- * Customer 0..1 --- * ProductEvent
Order  1 --- * OrderLine * --- 1 Product
Product * --- * Category     (through a dated bridge)
```

Many-to-many relationships require a relationship entity/bridge with its own
grain. Flattening category IDs into one string destroys referential integrity,
membership time, and predictable joins.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Mobile delivery | Versioned envelope | Producer owns emitted meaning | Validate; quarantine malformed input | Untrusted |
| Catalog | Tenant-scoped current product | Catalog team | Preserve source version; reject ambiguous keys | Authoritative for current catalog state |
| Accepted event ledger | One logical event | Event data-product owner | Deduplicate and reconcile deliveries | Authoritative analytical event record |
| Analytical fact/dimensions | Declared historical grains | Modeling owner; derived | Versioned publish or no visibility | Trusted after quality gates |
| Metric/mart | Versioned consumer contract | Business and data co-owners | Retain prior version on failed certification | Fit only for declared uses |

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Mixed event and daily rows | Grain assertion and key-profile failure | Reject publication; split models and rebuild |
| Hidden many-to-many join | Join row count exceeds input/key expectation | Stop aggregation; repair relationship grain |
| Reused source ID across tenants | Composite-key collision | Scope key, replay identity mapping, reconcile facts |
| Late product relationship | Unmatched foreign-key bucket | Retain unresolved fact; resolve with dated version and republish |
| Requirement changes silently | Metric/result drift without contract version | Restore prior output; approve and publish a new version |

Recovery is complete only when source-to-target counts and business totals converge,
affected versions are identified, and consumers receive an explicit correction.

## Security, privacy, and governance

Collect only attributes needed for declared decisions. Classify direct and
quasi-identifiers; keep raw customer identifiers out of broadly served marts;
authorize identity mappings separately. Record owner, steward, purpose, retention,
deletion behavior, and permitted joins. Samples, logs, diagrams, and quarantine
records inherit the highest relevant classification.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Grain fixture | Each row satisfies its grain sentence and declared key | Pending |
| Cardinality cases | 0/1/many relationship cases produce predicted join counts | Pending |
| Duplicate delivery | Two deliveries of one event yield one fact | Pending |
| Missing/unknown cases | Null reason and resolution state remain distinguishable | Pending |
| Reconciliation | Accepted events = facts + named exclusions | Pending |

These deterministic fixtures will prove local model behavior, not distributed
uniqueness enforcement or production source quality.

## Common pitfalls

### Pitfall: defining grain from a table name

“Events” can mean deliveries, logical events, sessions, or daily counts. State
identity, scope, and time in a sentence and test it with counterexamples.

### Pitfall: attaching convenient attributes from another grain

An order header total repeated on every order line inflates sums. Store or derive
it at order grain, or allocate it with an explicit rule that reconciles.

### Pitfall: drawing cardinality without time

A product has one current category may still have many historical categories.
Relationship validity must participate in an as-of join.

## Performance, operations, and migration

Estimate row multiplication before joins: input cardinality × match distribution,
not merely table sizes. Profile key cardinality, null/unresolved rates, duplicate
rates, relationship fan-out, late-arrival age, and row-width distribution. Alert
on unexpected changes with bounded-cardinality labels.

To change grain, publish a new model beside the old one, backfill from authoritative
inputs, reconcile shared measures, migrate consumers, and deprecate the old model.
A column migration cannot safely convert one row meaning into another in place.

## Working example

- SQL/data/tests: planned product-event conceptual model and cardinality fixture
- Expected result: declared grains, relationship cases, and reconciliation hold
- Scale represented: none yet; estimates only
- Remaining risk: ambiguous source semantics, cross-tenant identity, and real join fan-out

## Knowledge check

1. Write the grain sentence for a delivery table and an accepted-event table.
2. Predict the row count when three events join two valid category memberships.
3. Diagnose why summing an order total after joining order lines inflates revenue.
4. Design a model for products whose category membership changes over time.
5. Propose a safe migration from session-grain rows to event-grain rows.
6. Add an `anonymous_id` requirement and identify privacy and identity consequences.

## Key takeaways

- Grain is the first invariant, not documentation added after schema design.
- Identity, scope, cardinality, optionality, and time make relationships precise.
- Consumer decisions and reconciliation requirements shape useful models.
- One model should not mix facts from different grains for convenience.
- Changing grain is a versioned data-product migration.

## Resources

- [Kimball Group: Declare the Grain](https://www.kimballgroup.com/2008/11/fact-tables/) (reviewed 2026-09)
- [PostgreSQL documentation: Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) (reviewed 2026-09)

## Related topics

- [Relational modeling, normalization, and integrity](02-relational-modeling-normalization-and-integrity.md)
- [Dimensional modeling: facts, dimensions, and stars](03-dimensional-modeling-facts-dimensions-and-stars.md)

## Completion checklist

- [x] Requirements, grain, entities, relationships, ownership, and time explained
- [x] Scale, privacy, failure, reconciliation, and migration addressed
- [ ] Conceptual model, fixture, cardinality, and reconciliation evidence run

