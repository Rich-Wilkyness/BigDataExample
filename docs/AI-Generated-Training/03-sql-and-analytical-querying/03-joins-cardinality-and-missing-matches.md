# Joins, Cardinality, and Missing Matches

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / SQL  
> Data scale: Local fixture; production cardinality estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A join combines relationships; it does not merely attach columns. Its correctness
depends on the grain and key multiplicity of both inputs. One-to-many and
many-to-many matches can legitimately change row count, while an accidental
many-to-many match can multiply facts and inflate every downstream metric.

This guide covers inner and outer joins, semi and anti joins, missing matches,
predicate placement, and cardinality evidence. Join algorithms belong to the
optimization guide; dimensional history is developed later in the curriculum.

## Learning objectives

After completing this guide, you should be able to:

- Predict output grain and minimum/maximum matches before writing a join.
- Choose inner, outer, semi, or anti semantics from consumer requirements.
- Detect many-to-many explosions and distinguish them from valid fan-out.
- Preserve unmatched rows and classify missing references deliberately.
- Reconcile input keys, matched keys, unmatched keys, and output rows.

## Prerequisites

- [Relations, sets, bags, keys, and NULL](01-relations-sets-bags-keys-and-null.md)
- [SELECT, filter, project, order, and limit](02-select-filter-project-order-and-limit.md)

## Mental model

For every left row, a join finds zero, one, or many right rows. Write that
multiplicity before choosing syntax:

| Relationship | Expected matches per left row | Output effect |
| --- | --- | --- |
| many-to-one | zero or one | preserves left grain with an outer join |
| one-to-many | zero to many | changes grain to the matched child relationship |
| many-to-many | zero to many on both sides | pairwise multiplication; require explicit intent |

A Kotlin `associateBy` lookup resembles a many-to-one join only after duplicate
keys have been rejected. SQL does not silently build a unique map: all matching
pairs survive under bag semantics.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Cardinality | Row count or distinct-value count at a stated boundary |
| Fan-out | Number of output matches produced for one input row |
| Semi join | Retain a left row when at least one right match exists, without copying right rows |
| Anti join | Retain a left row when no qualifying right match exists |
| Orphan | A non-null reference with no qualifying authoritative target |
| Join explosion | Unexpected multiplicative growth caused by non-unique or incomplete join keys |

## Requirements and invariants

The reference enrichment attaches one current product to each eligible product
event. `events` has one row per `event_id`; `products` must have one row per
`product_id`. A missing product remains observable for quality accounting.

- Validate right-key uniqueness before relying on many-to-one behavior.
- Join on the full business relationship, including tenant or effective-time
  components when they belong to identity.
- State whether null keys are invalid, unmatched, or matched by an explicit
  null-safe rule.
- Reconcile left rows into matched, null-key, and orphan buckets.
- Never repair unexplained fan-out with final `DISTINCT`.

## Join patterns

### Inner and outer joins

```sql
-- Output grain: one eligible event if products.product_id is unique.
SELECT e.event_id, e.event_time, e.product_id, p.category
FROM events AS e
LEFT JOIN products AS p
  ON p.product_id = e.product_id
WHERE e.event_name = 'product_view';
```

This left join preserves an event with a null or unresolved product. Moving a
right-side filter into `WHERE` can discard that row and effectively produce
inner semantics:

```sql
-- Preserve unmatched events while restricting qualifying product rows.
LEFT JOIN products AS p
  ON p.product_id = e.product_id
 AND p.lifecycle_state = 'active'
```

Whether inactive products should be unmatched or excluded is a business rule,
not a formatting preference.

### Semi and anti joins

Use `EXISTS` when only existence matters:

```sql
SELECT e.event_id
FROM events AS e
WHERE EXISTS (
    SELECT 1
    FROM products AS p
    WHERE p.product_id = e.product_id
);
```

Use `NOT EXISTS` for missing matches. It behaves predictably with nulls in the
subquery compared with `NOT IN`, whose result can become unknown when the list
contains `NULL`.

```sql
SELECT e.event_id, e.product_id
FROM events AS e
WHERE e.product_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM products AS p WHERE p.product_id = e.product_id
  );
```

### Cardinality assertion

```sql
-- Must return zero rows before treating products as the one side.
SELECT product_id, COUNT(*) AS row_count
FROM products
GROUP BY product_id
HAVING COUNT(*) > 1;
```

For a valid historical product table, `product_id` alone may intentionally have
many versions; the event-time containment condition then becomes part of the
join contract and overlapping effective intervals are invalid.

## Data flow, ownership, and trust boundaries

| Boundary | Owner and contract | Failure behavior | Trust |
| --- | --- | --- | --- |
| `events` | Pipeline; one accepted event | Null and orphan product IDs remain countable | Governed |
| `products` | Product data owner; unique current product | Duplicate keys block enrichment publication | Authoritative dimension |
| Enriched events | Analytics owner; one row per event | Reconcile before atomic publication | Derived |
| Metric consumer | Product analyst/service | Receives completeness indicator with metrics | Purpose-limited |

The enrichment does not become authoritative for product attributes. It is a
versioned derived snapshot with lineage to both inputs.

## Failure model and recovery

| Failure | Observable symptom | Recovery |
| --- | --- | --- |
| Duplicate right key | Output rows exceed eligible events; revenue inflates | Quarantine conflicting dimension state, repair owner data, rerun and reconcile |
| Incomplete composite key | Cross-tenant or cross-region matches | Add full key, assess exposure, republish, and audit affected consumers |
| Right filter in `WHERE` | Missing products disappear | Restore intended outer semantics and compare bucket counts |
| `NOT IN` sees a null | Anti-join returns zero/unexpected rows | Use correlated `NOT EXISTS` with explicit outer null policy |
| Late dimension record | Orphan rate spikes temporarily | Apply freshness contract; replay affected interval after dimension catches up |

Contain join explosions with row-count and fan-out gates before publishing. A
retry is safe only against pinned input versions or under a documented snapshot.

## Data quality, testing, and evidence

The future fixture includes zero/one/two right matches, null left keys, orphan
keys, duplicate right keys, and tenant-key collisions. Mutation tests remove one
join component and move a predicate between `ON` and `WHERE`; assertions must fail.

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Join truth table | Run all join kinds on bounded keys | Predicted matched/unmatched IDs | Pending |
| Fan-out gate | Inject duplicate product | Publication blocked; duplicate identified | Pending |
| Reconciliation | Compare eligible, matched, null, orphan, output counts | Buckets balance under declared multiplicity | Pending |
| Realistic plan | Join estimated 100M events to 100K products | Runtime, memory, spill, and plan captured | Pending |

## Debugging, pitfalls, and operations

When a metric changes unexpectedly, inspect distinct business keys and fan-out
distributions on each join edge before inspecting the aggregate. Record input
dataset versions, join/query version, output rows, distinct event IDs, unmatched
counts, maximum matches per key, duration, memory/spill, and skewed keys.

### Pitfall: incomplete join conditions

Joining only on `product_id` when identity is `(tenant_id, product_id)` can leak
data and multiply rows. Prefer constraints and a join condition that express the
full identity.

### Pitfall: checking existence with an ordinary join

An inner join duplicates left rows for multiple right matches. Prefer `EXISTS`
when the consumer asks only whether a related row exists.

### Pitfall: hiding explosion with `DISTINCT`

It may make row counts look plausible while attributes or aggregates remain
arbitrary. Repair keys, relationship rules, or pre-aggregation at an explicit
grain.

Capacity planning considers left/right rows, key cardinality, match-frequency
distribution, row width, skew, and concurrent queries. Alerts should target
violated contracts and consumer impact, not a universal row-count threshold.

Schema evolution requires both sides to coexist through expand/migrate/contract.
Dual-run old and new joins on identical snapshots, compare key buckets and
metrics, cut over atomically, and retain a rollback-compatible version.

## Working example

- SQL and tests: planned event-to-product enrichment and join mutations
- Expected result: one output per eligible event plus explicit missing-match flags
- Scale represented: bounded fixture; 100M-to-100K join remains unmeasured
- Remaining risk: skew, temporal joins, concurrent snapshots, and engine strategy

## Knowledge check

1. Predict output rows for two left rows and three right rows sharing one key.
2. Explain why a left join followed by `WHERE right.status = 'active'` drops misses.
3. Design matched, null-key, and orphan reconciliation buckets.
4. Replace an unsafe `NOT IN` query with explicit anti-join semantics.
5. Diagnose a 12% metric increase after a dimension refresh.
6. Extend the product join for tenant identity and propose a migration test.

## Key takeaways

- A join is a cardinality transformation governed by relationship multiplicity.
- Right-side uniqueness must be enforced or asserted before claiming grain preservation.
- Outer, semi, and anti joins encode different consumer contracts.
- Missing matches are data-quality information, not automatic garbage.
- Reconcile keys and fan-out before trusting downstream aggregates.

## Resources

- [PostgreSQL documentation: joined tables](https://www.postgresql.org/docs/current/queries-table-expressions.html#QUERIES-JOIN) (reviewed 2026-09)
- [PostgreSQL documentation: subquery expressions](https://www.postgresql.org/docs/current/functions-subquery.html) (reviewed 2026-09)

## Related topics

- [Aggregation, grouping, and set operations](04-aggregation-grouping-and-set-operations.md)
- [Query plans, indexes, statistics, and optimization](08-query-plans-indexes-statistics-and-optimization.md)

## Completion checklist

- [x] Join kinds, grain, multiplicity, missing matches, and null behavior explained
- [x] Ownership, security, failure, recovery, operations, and migration addressed
- [x] Explosion failure and mutation evidence designed
- [ ] Fixture, reconciliation, mutations, and plans executed

