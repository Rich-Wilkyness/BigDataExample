# Relations, Sets, Bags, Keys, and NULL

> Status: Documentation complete; executable evidence planned  
> Level: Beginner  
> Applies to: Generic data engineering / SQL  
> Data scale: Local fixture; production cardinality estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A relational query describes a result relation from input relations. Correctness
starts by stating what one row means, which attributes identify it, whether
duplicates are legal, and how absence is represented. SQL engines usually expose
bag semantics: a result may contain duplicate rows unless a constraint or
`DISTINCT` operation says otherwise. `NULL` represents an absent or unknown value
and participates in three-valued logic, not Kotlin's ordinary Boolean logic.

This guide establishes the semantics used throughout the area. It does not teach
physical storage, normalization theory in depth, or vendor-specific types.

## Learning objectives

After completing this guide, you should be able to:

- State the grain, candidate keys, and owner of a relation.
- Predict when a SQL operation preserves or multiplies duplicates.
- Distinguish an enforced key from an observed unique sample.
- Reason about `TRUE`, `FALSE`, and `UNKNOWN` in predicates and constraints.
- Design tests for uniqueness, completeness, and missing-value behavior.

## Prerequisites

- [First end-to-end data pipeline](../01-big-data-and-data-engineering-foundations/08-first-end-to-end-data-pipeline.md)
- No database is required until the planned working example is implemented.

## Mental model

A table is a contract-shaped bag of rows. The schema defines allowed attributes;
constraints narrow allowed states; grain says what each row claims to represent.
Neither a meaningful name nor a clean fixture proves uniqueness.

```text
relation contract = row meaning + domains + keys + constraints + owner
observed rows       = one database state that may or may not satisfy that contract
query result        = another bag whose grain must be derived from its operators
```

Kotlin's `List<Event>` is a useful bag analogy because it preserves duplicates.
It stops being accurate when SQL encounters `NULL`: `a = NULL` is not false but
unknown, and a `WHERE` clause keeps only rows whose predicate is true.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Relation | A set-like collection of tuples described by attributes; SQL tables and results approximate it with bag behavior |
| Grain | The real-world claim represented by one row |
| Bag | A collection in which equal rows may occur more than once |
| Candidate key | A minimal attribute set that uniquely identifies a row by contract |
| Primary key | The candidate key chosen as the table's main relational identity |
| Foreign key | A constraint that requires a referenced identity, subject to its declared `NULL` and action rules |
| `NULL` | Marker for missing or unknown information, not a value equal to itself |

## Requirements, scale assumptions, and invariants

The reference `events` relation has one accepted logical mobile event per
`event_id`. `session_id` is absent before sessionization or when policy excludes
an event; `product_id` is absent for events unrelated to a product. Empty string
and sentinel IDs are not substitutes for absence.

Invariants are:

- `event_id` is non-null and unique in retained accepted history.
- Every non-null `product_id` is intended to resolve to an authoritative product;
  unresolved IDs are measured before deciding whether to reject or retain them.
- Duplicate deliveries are allowed in `event_deliveries`, but duplicate logical
  events are not allowed in `events`.
- A query never relies on sample uniqueness where no constraint or assertion exists.
- `NULL`, zero, empty text, and an unknown business category remain distinct.

The initial estimate is 100 million retained event rows. It affects physical
design later but does not change these logical invariants.

## Relational and SQL behavior

### Set theory versus SQL bags

Projection can expose duplicates even when inputs have unique keys:

```sql
-- PostgreSQL-compatible design sketch. Result grain: one occurrence per event.
SELECT event_name
FROM events;

-- Result grain: one distinct event-name value, including at most one NULL.
SELECT DISTINCT event_name
FROM events;
```

`DISTINCT` is a semantic operation, not a general repair for an unexplained join
or duplicate. It may hide violated identity while adding sort or hash work.

### Keys and constraints

```sql
CREATE TABLE events (
    event_id       text PRIMARY KEY,
    event_name     text NOT NULL,
    event_time     timestamptz NOT NULL,
    receipt_time   timestamptz NOT NULL,
    session_id     text,
    product_id     text,
    revenue_cents  bigint CHECK (revenue_cents IS NULL OR revenue_cents >= 0)
);
```

The primary key makes logical-event uniqueness enforceable inside this database.
It does not prove that the producer chose stable IDs, nor does it deduplicate a
different upstream table. A foreign key can enforce reference existence at a
transaction boundary, but its availability and load-order cost are design inputs.

### Three-valued logic

For a row with `product_id IS NULL`, `product_id = 'p1'` and
`product_id <> 'p1'` both evaluate to `UNKNOWN`. Therefore this query excludes
missing product IDs as well as `p1`:

```sql
SELECT event_id
FROM events
WHERE product_id <> :excluded_product_id;
```

If the contract wants missing values retained, say so:

```sql
SELECT event_id
FROM events
WHERE product_id <> :excluded_product_id OR product_id IS NULL;
```

Use `IS NULL` and `IS NOT NULL` for absence. Prefer `IS NOT DISTINCT FROM` only
when the chosen engine supports it and null-safe equality is truly the intended
business rule.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Delivery to validation | One envelope / `delivery_id` | Ingestion | Duplicate delivery retained; malformed input rejected safely | Untrusted |
| Validation to `events` | One logical event / `event_id` | Pipeline | Key or type violation prevents publication | Governed internal |
| `events` to metric query | Versioned accepted snapshot | Analytics owner | Quality assertion failure blocks new metric version | Trusted with verification |

`event_deliveries` is authoritative for receipt facts; `events` is an explicitly
derived source for accepted logical events. A primary key does not transfer
authority from the source system to the database.

## Failure model and recovery

| Failure | Detection and containment | Recovery and convergence proof |
| --- | --- | --- |
| Retried delivery collides on `event_id` | Unique violation or duplicate-count assertion | Rebuild from immutable deliveries using the versioned winner rule; reconcile identities |
| Sentinel value such as `''` stands for missing | Domain-frequency and validity checks | Normalize under a new transformation version; backfill and compare null counts |
| Nullable predicate silently drops rows | Reconcile input into true/false/unknown buckets | Repair predicate, republish atomically, and verify bucket totals |
| Supposed key is only unique in sample | Constraint creation or adversarial fixture fails | Define business identity with owner; quarantine or merge conflicts explicitly |

Consumers keep the previous complete dataset while a replacement is repaired.
SQL errors, rejection records, and metrics must avoid raw device or user identifiers.

## Data quality, testing, and evidence

The planned fixture includes an empty table, one duplicate delivery, a null
product, an empty string product, zero revenue, and a missing product reference.
Assertions cover uniqueness, nullability, accepted/rejected reconciliation, and
the truth-table result of each predicate.

| Evidence | Environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Bag and `DISTINCT` result | Bounded fixture / real SQL engine | Run paired projections | Counts differ only by specified duplicates | Pending |
| `NULL` predicate truth table | Bounded fixture / real SQL engine | Query true, false, unknown buckets | Every input appears in exactly one bucket | Pending |
| Key constraints | Bounded fixture / real SQL engine | Attempt duplicate and null inserts | Invalid state rejected atomically | Pending |

Documentation review is not engine evidence. Exact error timing, constraint
validation, and null-safe operators will be recorded for the selected engine.

## Debugging guide and common pitfalls

Start with the affected result's stated grain. Compare `COUNT(*)` with counts of
the candidate key, duplicate groups, and null counts. Trace the dataset version,
query version, input snapshot, and quality-run ID.

### Pitfall: treating `DISTINCT` as deduplication

Avoid adding `DISTINCT` until the source of multiplicity is explained. Prefer a
business-key winner rule with deterministic ordering and a reconciliation report.

### Pitfall: equality with `NULL`

Avoid `column = NULL` and `column <> NULL`. Prefer `IS NULL`, `IS NOT NULL`, or an
explicit null-safe rule whose consumer meaning is documented.

### Pitfall: declaring a surrogate key and forgetting business identity

A generated row ID prevents duplicate row IDs, not duplicate business events.
Retain and constrain the stable producer identity when that is the contract.

## Performance, operations, and evolution

Keys and constraints can require indexes, validation scans, and coordination with
writes. Those costs must be measured at realistic cardinality. Operational
signals include duplicate-key violations, null rates by column, unresolved
foreign keys, rejected rows, and input/output reconciliation.

For existing dirty data, use an expand/migrate/contract sequence: add a
compatible column or unvalidated rule, populate and inspect it, repair conflicts,
validate the invariant, switch consumers, then remove the obsolete representation.
Rollback must preserve the old readable version until reconciliation passes.

## Working example

- SQL: planned under `sql/03-sql-and-analytical-querying/`
- Fixture: planned bounded mobile event/product dataset under `data/`
- Try it: pending engine selection and exact command
- Expected result: deterministic bag counts, null truth table, and rejected invalid keys
- Scale represented: local fixture only; 100 million rows is an untested estimate
- Remaining risk: dialect differences, concurrent writes, constraint cost, and production distributions

## Knowledge check

1. State the grain and candidate key of `event_deliveries` and `events`.
2. Predict the output of `WHERE product_id <> 'p1'` for `NULL`, `'p1'`, and `'p2'`.
3. Explain why `SELECT DISTINCT` can make a wrong join look correct.
4. Design a repair for duplicate business keys without choosing a winner arbitrarily.
5. Add a nullable `campaign_id` while distinguishing missing, not applicable, and unknown.
6. Propose evidence needed before enforcing a key on 100 million existing rows.

## Key takeaways

- Start every query with grain and identity.
- SQL results are bags unless an operation or constraint establishes distinctness.
- `NULL` produces unknown comparisons; predicate placement changes retained rows.
- Constraints prove database states, not upstream business semantics.
- Reconciliation is part of correctness, especially during repair and migration.

## Resources

- [PostgreSQL documentation: table expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html) (reviewed 2026-09)
- [PostgreSQL documentation: comparison functions and operators](https://www.postgresql.org/docs/current/functions-comparison.html) (reviewed 2026-09)
- [SQLite documentation: SQL expressions](https://www.sqlite.org/lang_expr.html) (reviewed 2026-09)

## Related topics

- [SELECT, filter, project, order, and limit](02-select-filter-project-order-and-limit.md)
- [Joins, cardinality, and missing matches](03-joins-cardinality-and-missing-matches.md)
- [DDL, constraints, transactions, and concurrent change](07-ddl-constraints-transactions-and-concurrent-change.md)

## Completion checklist

- [x] Durable concept, grain, keys, bags, and `NULL` mental model explained
- [x] Ownership, trust, quality, failure, security, and migration boundaries stated
- [x] Kotlin analogy and its relational limits identified
- [x] Planned example and evidence distinguished from executed behavior
- [ ] SQL fixture and assertions implemented and run
- [ ] Constraint and realistic-cardinality evidence recorded

