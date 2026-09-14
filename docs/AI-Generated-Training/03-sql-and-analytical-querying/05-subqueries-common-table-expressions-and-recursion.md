# Subqueries, Common Table Expressions, and Recursion

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Generic data engineering / SQL  
> Data scale: Local fixture; production cardinality estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Subqueries and common table expressions (CTEs) compose relational steps without
changing the need to reason about grain and cost. Correlated subqueries express
row-dependent questions such as existence. Recursive CTEs iteratively expand a
seed relation and can traverse trees or graphs, but require cycle, depth, and
resource controls.

Names and indentation improve human reasoning; they do not guarantee
materialization, reuse, optimization, or execution order. Those are engine- and
version-specific plan properties.

## Learning objectives

After completing this guide, you should be able to:

- Choose scalar, table, existence, and correlated subqueries by contract.
- Decompose a query into CTEs with explicit grain at each boundary.
- Recognize where repeated computation or optimization fences may occur.
- Build a bounded recursive traversal with cycle handling.
- Test compositional equivalence, termination, cardinality, and plans.

## Prerequisites

- [Aggregation, grouping, and set operations](04-aggregation-grouping-and-set-operations.md)

## Mental model

A non-recursive CTE is a named relation in one statement, similar to a local
immutable value in Kotlin at the readability level. The analogy stops at runtime:
the optimizer may inline it, materialize it, or transform the whole plan.

A recursive CTE is closer to a fixpoint:

```text
result_0 = seed
result_n+1 = result_n UNION new rows derived from result_n
stop when no new rows exist or an explicit bound is reached
```

`UNION ALL` can revisit the same state forever. Even `UNION` does not guarantee
safe graph traversal if path-specific columns make every row distinct.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Scalar subquery | Subquery required to produce at most one row and one column |
| Correlation | Reference from a subquery to a row of an outer query |
| CTE | Named query expression scoped to one statement |
| Anchor/seed | Non-recursive starting rows of a recursive CTE |
| Recursive term | Step that derives the next rows from prior rows |
| Fixpoint | State in which another iteration adds no qualifying rows |
| Cycle | Traversal path that revisits an already visited identity |

## Requirements and invariants

The reference examples use CTEs to stage eligible events and recursively walk a
product-category hierarchy. A category has at most one parent, roots have null
parents, and analytics traversals are capped even if source constraints fail.

- Every named step documents input and output grain.
- A scalar subquery proves its maximum cardinality; `LIMIT 1` is not a semantic proof.
- Existence questions use `EXISTS` rather than row multiplication.
- Recursion has a stable identity, termination condition, maximum depth, and cycle policy.
- Query results do not depend on CTE textual order implying physical execution.
- Intermediate sensitive columns are still protected even if the final projection omits them.

## Composition patterns

### Staged analytical query

```sql
WITH eligible_events AS (
    -- Grain: one accepted logical event.
    SELECT event_id, product_id, event_name, event_time, revenue_cents
    FROM events
    WHERE event_time >= :start_utc AND event_time < :end_utc
),
product_metrics AS (
    -- Grain: one product_id for the requested interval.
    SELECT product_id,
           COUNT(*) FILTER (WHERE event_name = 'product_view') AS views,
           SUM(revenue_cents) FILTER (WHERE event_name = 'purchase') AS revenue_cents
    FROM eligible_events
    WHERE product_id IS NOT NULL
    GROUP BY product_id
)
SELECT product_id, views, revenue_cents
FROM product_metrics;
```

This creates reasoning boundaries, not dataset publication boundaries. If
multiple jobs need `eligible_events`, a governed persisted model may be clearer
than copying the CTE, but then ownership, freshness, and backfill enter the design.

### Scalar and correlated subqueries

A scalar subquery that returns more than one row fails in many engines. Prove a
key or aggregate to one row. For existence, correlation is direct and grain-safe:

```sql
SELECT p.product_id
FROM products AS p
WHERE EXISTS (
    SELECT 1
    FROM events AS e
    WHERE e.product_id = p.product_id
      AND e.event_time >= :start_utc
      AND e.event_time < :end_utc
);
```

The optimizer may transform this into a semi join; inspect the plan rather than
assuming it executes once per product.

### Bounded recursion

```sql
WITH RECURSIVE category_tree AS (
    SELECT category_id, parent_category_id, 0 AS depth,
           ARRAY[category_id] AS path
    FROM categories
    WHERE category_id = :root_id

    UNION ALL

    SELECT c.category_id, c.parent_category_id, t.depth + 1,
           t.path || c.category_id
    FROM categories AS c
    JOIN category_tree AS t ON c.parent_category_id = t.category_id
    WHERE t.depth < :max_depth
      AND NOT c.category_id = ANY(t.path)
)
SELECT category_id, parent_category_id, depth
FROM category_tree;
```

Array syntax is PostgreSQL-specific. Other engines use different cycle clauses,
path encodings, or application-side traversal. The durable requirements are
stable identity, visited-state handling, and an operational bound.

## Ownership, lifecycle, and trust boundaries

The product system owns category parentage. The query owner owns traversal
semantics and bounds; the database owns statement resources and cancellation.
A CTE disappears with its statement and is not a recoverable checkpoint. A
persisted intermediate becomes a dataset with a new owner, schema, freshness,
retention, access, and atomic-publication contract.

Recursive paths can expose categories a caller is not authorized to view. Apply
authorization at every relevant node/edge boundary, not only after traversal,
and test cross-tenant edges as malicious input.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Scalar subquery returns many rows | Statement error/cardinality assertion | Repair key or aggregation; do not select arbitrary row |
| Correlated work scales poorly | Actual plan and row-loop counts | Rewrite to join/pre-aggregate if equivalent; refresh statistics |
| Cycle or excessive depth | Depth/cycle flags, timeout, resource limits | Stop query, quarantine hierarchy defect, repair owner data |
| CTE assumption changes across engines | Result/plan regression | Pin dialect, compare semantics, document materialization behavior |
| Persisted intermediate partially publishes | Dataset completeness check | Stage, validate, atomically publish, retain prior version |

Statement retry uses the same query version and input snapshot. If the input can
change, an identical rerun may be logically valid but produce different data;
that is not evidence of nondeterminism.

## Data quality, testing, and evidence

Fixtures include an empty hierarchy, one root, a deep chain, branching, orphan
parent, self-cycle, multi-node cycle, duplicate category ID, and a cross-tenant
edge. Query mutations remove depth/cycle guards and replace a unique scalar
lookup with multi-row input.

| Evidence | Expected result | Result |
| --- | --- | --- |
| Step cardinalities | Every CTE matches hand-calculated grain/counts | Pending |
| Equivalent form | CTE, derived table, and safe join return same IDs | Pending |
| Recursive adversarial fixture | Terminates within bound; flags defective paths | Pending |
| Actual plans | Reuse/materialization, loops, rows, memory, and spills recorded | Pending |

## Debugging, performance, and operations

Debug each relation boundary independently: key counts, duplicates, nulls,
estimated versus actual rows, and filters. For recursion, capture root, depth,
visited count, maximum frontier, cycle count, duration, cancellation, and query
version without logging sensitive path contents.

CTEs can clarify ownership inside a query but too many can hide repeated scans
and row-width growth. Recursive cost depends on branching factor and depth; with
branching factor `b`, a tree may visit roughly `1 + b + ... + b^d` nodes. Set
budgets for rows, depth, time, memory, and concurrency, then inspect the actual
plan. Do not tune from CTE syntax folklore.

During engine migration, compare result sets and actual plans for correlated
subqueries, CTE reuse, recursive syntax, search/cycle behavior, and limits. A
materialized intermediate needs separate versioned backfill and rollback.

## Common pitfalls

### Pitfall: CTE as an optimization promise

Treat it as a semantic name. Verify whether it is inlined or materialized in the
specific engine/version and query plan.

### Pitfall: `LIMIT 1` to fix a scalar subquery

Without a total business order, it hides an invalid multiplicity. Enforce the key
or aggregate according to an owned rule.

### Pitfall: recursion without adversarial data

Production hierarchies eventually contain deep paths, cycles, or cross-boundary
edges. Bound resource use even when source constraints claim they cannot occur.

## Working example

- SQL and tests: planned CTE metric and bounded category traversal
- Expected result: stable metric rows and finite authorized hierarchy result
- Scale represented: local graph fixture; production branching/cardinality pending
- Remaining risk: dialect recursion, authorization, optimizer behavior, and cancellation

## Knowledge check

1. State the grain of each relation in the staged metric query.
2. Explain why a CTE is not automatically a checkpoint or cached result.
3. Replace a multi-row scalar subquery with a contract-correct form.
4. Predict traversal output for a self-cycle with and without the guard.
5. Estimate nodes visited for branching factor 4 and depth 6.
6. Design a persisted-intermediate migration and rollback.

## Key takeaways

- Composition does not remove grain, identity, or cardinality obligations.
- `EXISTS` expresses existence without copying matches.
- CTE execution strategy is an observed plan property, not a portable promise.
- Recursive SQL requires identity, cycle, depth, security, and resource policies.
- Persisting an intermediate creates a new data-product boundary.

## Resources

- [PostgreSQL documentation: WITH queries](https://www.postgresql.org/docs/current/queries-with.html) (reviewed 2026-09)
- [PostgreSQL documentation: subquery expressions](https://www.postgresql.org/docs/current/functions-subquery.html) (reviewed 2026-09)

## Related topics

- [Window functions, time series, and analytical patterns](06-window-functions-time-series-and-analytical-patterns.md)
- [Query plans, indexes, statistics, and optimization](08-query-plans-indexes-statistics-and-optimization.md)

## Completion checklist

- [x] Subquery, CTE, correlation, recursion, and optimizer boundaries explained
- [x] Grain, termination, security, failure, performance, and lifecycle addressed
- [x] Adversarial recursion and plan evidence designed
- [ ] Query equivalence, recursive fixtures, and actual plans executed
