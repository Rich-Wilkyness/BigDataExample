# SQL Transformations and Set-Based Pipelines

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: SQL / Batch / Warehouses / Relational databases  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A SQL batch describes the desired relation while the engine chooses an execution
plan. Correctness therefore depends on explicit grain, keys, null and time
semantics, deterministic selection, transaction/publication boundaries, and
cardinality checks—not on the visual order of CTEs.

This guide turns staged product events into canonical facts and daily metrics.
It covers set-based transformations and materialization boundaries, not one SQL
dialect's complete syntax or distributed-engine tuning.

## Learning objectives

- Express batch transformations as relations with declared input and output grain.
- Prevent duplicate amplification and nondeterministic winner selection.
- Choose views, temporary tables, persisted stages, and final tables deliberately.
- Make incremental SQL rerunnable and publish it transactionally where possible.
- Inspect plans and reconcile every stage at representative cardinality.

## Prerequisites

- Area 03 joins, aggregates, windows, transactions, and query plans
- Area 05 fact, dimension, history, and metric semantics
- [ETL, ELT, staging, and layer responsibilities](01-etl-elt-staging-and-layer-responsibilities.md)

## Mental model and terminology

A SQL statement transforms one relation into another; it is not an imperative
loop over rows. Room query comparisons help with transactions, constraints, and
plans, but stop where analytical scans, large shuffles, append-oriented storage,
and multi-table dataset publication differ from a mobile database.

| Term | Meaning in this guide |
| --- | --- |
| Set-based | Specifies a result over relations instead of issuing one operation per record |
| Stage | Named intermediate relation used for isolation, reuse, inspection, or recovery |
| Materialization | Persisting a relation rather than recomputing it on reference |
| Fan-out | One input row matches multiple rows unexpectedly and multiplies output |
| Sargable | Predicate form an engine can commonly use for pruning/index access |
| Merge/upsert | Engine-specific matched/unmatched change operation, not an automatic idempotency proof |

## Requirements, assumptions, and invariants

The output fact grain is one accepted logical event. Daily metric grain is one
`tenant_id`, `product_id`, and UTC business date. Inputs are a closed raw batch
and a non-overlapping effective-dated product dimension. Assume 3M events/day,
100K products, and a 02:00 UTC deadline; actual plans and spill remain unmeasured.

Invariants:

- Every relation has a stated grain and expected uniqueness key.
- Join cardinality is proven; missing and multiple matches receive explicit dispositions.
- `NULL`, decimal, case/collation, and timestamp behavior are declared per dialect.
- Winner selection has a total order or is rejected as ambiguous.
- Incremental predicates use a total input boundary and never infer completeness from wall time alone.
- Consumers see only a quality-approved relation or dataset version.

## Data flow, ownership, and trust boundaries

| Relation | Grain and owner | Entry requirement | Exit evidence |
| --- | --- | --- | --- |
| `stage_event` | One selected accepted record; run owner | Pinned input manifest/boundary | Input count/digest and duplicate classification |
| `canonical_event` | One logical event; canonical owner | Valid fields and stable identity | Unique key and disposition reconciliation |
| `product_match` | One event plus match bucket; pipeline owner | Temporal/scoped join policy | Exactly one matched/unknown/rejected outcome |
| `fact_product_event` | One business event; fact owner | Certified canonical and dimension version | Constraints, anti-joins, totals |
| `metric_product_day` | Tenant/product/UTC date; metric owner | Certified facts and metric definition | Hand-calculated fixture and fact-to-metric reconciliation |

## Reference SQL model

The following is PostgreSQL-style SQL. `AT TIME ZONE`, temporary-table behavior,
constraint timing, `MERGE`, and atomic replacement differ across engines.

```sql
CREATE TEMPORARY TABLE candidate_event AS
WITH ranked AS (
    SELECT e.*,
           ROW_NUMBER() OVER (
               PARTITION BY tenant_id, producer_id, event_id
               ORDER BY source_version DESC, receipt_id DESC
           ) AS version_rank
    FROM stage_event AS e
    WHERE input_batch_id = :input_batch_id
), canonical AS (
    SELECT tenant_id, producer_id, event_id, event_time_utc,
           product_id, event_type, source_version, receipt_id
    FROM ranked
    WHERE version_rank = 1
)
SELECT c.*, p.product_sk
FROM canonical AS c
LEFT JOIN dim_product AS p
  ON p.tenant_id = c.tenant_id
 AND p.product_id = c.product_id
 AND c.event_time_utc >= p.effective_from_utc
 AND c.event_time_utc <  p.effective_to_utc;
```

The half-open temporal interval avoids double matches at a shared boundary, but a
constraint or quality test must still prove dimension intervals do not overlap.
`receipt_id` is only a valid tie-breaker if the contract intentionally chooses it;
otherwise equal source versions with changed payload are conflicts.

```sql
SELECT tenant_id, product_sk,
       CAST(event_time_utc AS DATE) AS event_date_utc,
       COUNT(*) FILTER (WHERE event_type = 'view') AS views,
       COUNT(*) FILTER (WHERE event_type = 'purchase') AS purchases
FROM candidate_event
GROUP BY tenant_id, product_sk, CAST(event_time_utc AS DATE);
```

Casting to a date must follow the metric's named time zone. `product_sk IS NULL`
requires an unknown-member or rejection policy; allowing it silently changes
grouping semantics.

## Materialization and transaction choices

| Form | Prefer when | Risk and evidence needed |
| --- | --- | --- |
| CTE/subquery | One readable logical statement, no recovery boundary needed | May inline or materialize by engine/version; inspect actual plan |
| View | Consumers need current reusable logic | Results can change with underlying data; version semantics and plans |
| Temporary table | Run-local reuse and database transaction scope | Session lifetime, statistics, disk/log pressure |
| Persisted stage | Expensive boundary needs restart/inspection | Cleanup, privacy, mixed-version access |
| Final table/partition | Stable consumer contract | Atomic replacement and rollback protocol |

Use a database transaction when all affected relations and metadata share its
atomic boundary and size/locking fit. For multiple systems or object files, build
immutable candidates and commit a manifest/catalog pointer; application SQL
cannot manufacture a cross-system transaction.

## Incremental set-based publication

```sql
-- Candidate is deduplicated at fact grain before the mutation.
MERGE INTO fact_product_event AS target
USING candidate_event AS source
ON target.tenant_id = source.tenant_id
AND target.producer_id = source.producer_id
AND target.event_id = source.event_id
WHEN MATCHED AND target.source_version < source.source_version THEN
  UPDATE SET product_sk = source.product_sk,
             event_time_utc = source.event_time_utc,
             source_version = source.source_version
WHEN NOT MATCHED THEN
  INSERT (tenant_id, producer_id, event_id, product_sk, event_time_utc, source_version)
  VALUES (source.tenant_id, source.producer_id, source.event_id,
          source.product_sk, source.event_time_utc, source.source_version);
```

This generic sketch omits dialect restrictions. Prove source uniqueness first;
different engines may fail or behave differently when multiple source rows match
one target. Delete semantics and stale versions require explicit clauses/policy.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Join fan-out | Stage-to-result counts and per-key match cardinality | Block publish; repair dimension/key predicate and rebuild |
| Nondeterministic dedup | Repeated run yields different winner/digest | Add total business order or classify conflict |
| Statement fails in transaction | Database error and rollback state | Verify transaction outcome, then retry pinned run |
| Connection lost at commit | Commit outcome unknown | Query run/publication ledger before retrying |
| Query spills or times out | Actual plan, temp I/O, runtime metrics | Preserve old version; tune/split without changing semantics |
| Partial multi-table publish | Dataset versions disagree | Hide uncertified set; roll forward from candidates |
| Stale statistics change plan | Plan/runtime regression | Refresh approved stats, bound workload, compare plans |

## Security, privacy, and governance

Use parameters or safely generated identifiers; never concatenate untrusted values
into SQL. Grant transform identities read access only to required input versions
and write access only to run staging/publication procedures. Protect temporary and
error tables, query history, samples, and plan literals. Apply row/column policies
at the correct layer and test that `CREATE TABLE AS` does not drop required
classifications or grants.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Hand fixture | Compute canonical facts and metrics manually | SQL equals expected rows and totals | Pending |
| Join mutation | Duplicate dimension, orphan key, tenant collision | Fan-out/missing buckets block or follow policy | Pending |
| Null/time matrix | Null keys, DST boundary, decimal edge, empty scope | Declared results in target dialect | Pending |
| Rerun/commit test | Repeat and interrupt before/after commit | One converged result; outcome discoverable | Pending |
| Plan/cardinality sweep | Small, 3M/day, skewed tenant | Plan, scan, spill, and runtime within budget | Pending |
| Cross-engine comparison | Run supported SQL variants on same fixture | Differences documented or eliminated | Pending |

An embedded database can prove logical fixtures but not warehouse optimizer,
concurrency, transaction, partition replacement, or cost behavior.

## Common pitfalls

### Pitfall: row-by-row SQL from Python

It adds network round trips and fragmented failure boundaries. Load a bounded
candidate set and apply set-based validation/transformation where supported.

### Pitfall: `DISTINCT` as a fan-out repair

It can hide an incorrect join and remove legitimate equal rows. Assert expected
join cardinality and fix the key or temporal condition.

### Pitfall: wrapping a timestamp column in the incremental predicate

Functions can prevent pruning or index use and blur boundaries. Compute typed
lower/upper bounds once and compare the stored column directly.

### Pitfall: assuming `MERGE` means exactly once

Correctness still depends on stable keys, source uniqueness, version ordering,
concurrency semantics, and recoverable commit evidence.

## Performance, observability, and operations

Capture actual plans, estimated versus actual rows, input/scan/output bytes,
partition pruning, index use, join strategy, shuffle/temp I/O, spill, lock time,
log volume, runtime, queue time, and cost. Quality queries are workloads too;
budget them without weakening the checks.

Structured run metadata includes query hash, engine/config version, input/output
dataset versions, statement IDs, row counts by stage/disposition, and publish
transaction/manifest. Alert on deadline miss, plan/runtime regression, fan-out,
unmatched growth, spill, lock waits, and version disagreement.

## Compatibility, migration, and tradeoffs

Run schema and semantic changes through expand/migrate/contract. Create compatible
columns/views, dual-build from pinned inputs, compare rows and domain totals,
publish a versioned contract, migrate consumers, then remove old structures. DDL
transactionality and online behavior are engine-specific and require integration
evidence plus rollback planning.

## Working example

- SQL/data/tests: planned schema, staged events/products, fact transform, metric aggregate, mutations, and plan capture
- Expected result: declared grains remain unique, match buckets reconcile, and failed candidates remain invisible
- Scale represented: none yet; local fixture and representative-cardinality engine run planned
- Remaining risk: optimizer changes, warehouse concurrency, transaction limits, and cost

## Knowledge check

1. State the grain after each CTE in the reference query.
2. Predict output when two product versions overlap the event time.
3. Diagnose why a `DISTINCT` made counts look correct after a join change.
4. Design an atomic publication for two tables in one database and across object storage.
5. Choose evidence that distinguishes logical correctness from plan scalability.
6. Modify the merge policy to represent source deletes and stale updates safely.

## Key takeaways

- SQL batch correctness begins with relation grain and cardinality.
- Declarative SQL exposes work to an optimizer; actual plans remain evidence, not assumptions.
- Materialization boundaries trade recomputation for state, cleanup, and recovery obligations.
- Transactions and merges help only within their documented scope.
- Reconciliation and versioned publication turn queries into a trustworthy pipeline.

## Resources

- [PostgreSQL documentation: WITH queries](https://www.postgresql.org/docs/current/queries-with.html) (reviewed 2026-09)
- [PostgreSQL documentation: MERGE](https://www.postgresql.org/docs/current/sql-merge.html) (reviewed 2026-09)
- [PostgreSQL documentation: EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html) (reviewed 2026-09)

## Related topics

- [Full, incremental, and change-based processing](04-full-incremental-and-change-based-processing.md)
- [Checkpoints, idempotency, and atomic publication](05-checkpoints-idempotency-and-atomic-publication.md)
- [Query plans, indexes, statistics, and optimization](../03-sql-and-analytical-querying/08-query-plans-indexes-statistics-and-optimization.md)

## Completion checklist

- [x] Set-based transforms, grain, materialization, plans, transactions, and merge limits explained
- [x] Null, time, failure, security, quality, performance, migration, and evidence addressed
- [ ] SQL fixtures, mutations, commits, actual plans, cross-engine, and scale evidence run

