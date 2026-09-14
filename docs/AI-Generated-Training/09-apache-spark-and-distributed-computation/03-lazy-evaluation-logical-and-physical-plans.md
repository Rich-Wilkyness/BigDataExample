# Lazy Evaluation, Logical Plans, and Physical Plans

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: PySpark / Spark SQL / Distributed computation  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Spark transformations build a logical plan. An action asks Spark to analyze and
optimize that plan, select physical operators, divide work at exchange boundaries,
and run partition tasks. Laziness lets the engine prune columns, push filters,
reorder joins, collapse expressions, and avoid unused branches. It also means
that constructing a DataFrame does not prove the source can be read or the
calculation can finish.

A physical plan is evidence about intended operators, not the full runtime truth.
Adaptive Query Execution (AQE) can revise parts of the plan using runtime
statistics, and task metrics reveal the bytes, rows, skew, spill, and failures
that estimates cannot prove.

## Learning objectives

- Distinguish unresolved, analyzed, optimized logical, initial physical, and final adaptive plans.
- Map transformations and actions to queries, jobs, stages, tasks, and attempts.
- Identify exchanges, scans, broadcasts, sorts, aggregates, and Python boundaries in a plan.
- Detect accidental recomputation and choose a justified materialization boundary.
- Use plan and runtime evidence without coupling tests to unstable plan text.

## Prerequisites

- [MapReduce, DAGs, and data locality](../08-distributed-systems-foundations/05-mapreduce-dags-and-data-locality.md)
- [DataFrames, Spark SQL, schemas, and types](02-dataframes-spark-sql-schemas-and-types.md)

## Mental model

A Gradle build graph provides a useful analogy: declaring tasks is distinct from
executing requested outputs, and dependencies constrain order. It stops where
Spark rewrites relational algebra, creates one task per stage partition, retries
attempts, and may adapt physical operators while data flows.

```text
DataFrame/SQL expressions
          |
          v
 unresolved logical plan -- names/types --> analyzed logical plan
          |                                    |
          +---------- rules/stats -------------+
                                               v
                                    optimized logical plan
                                               |
                                  physical strategy selection
                                               v
                                      initial physical plan
                                               |
                         action -> jobs -> stages -> task attempts
                                               |
                                  runtime statistics / AQE
                                               v
                                       final physical plan
```

| Term | Meaning in this guide |
| --- | --- |
| Transformation | Returns a new deferred dataset description |
| Action | Requests a result or write and initiates execution |
| Exchange | Physical redistribution boundary, commonly a shuffle or broadcast |
| Whole-stage/code generation | Engine technique that fuses supported operators; version-sensitive implementation detail |
| AQE | Runtime re-optimization using statistics collected during execution |
| Materialization | Computing and retaining data in cache or durable storage for reuse/recovery |

## Requirements and invariants

The reference aggregation must read only the pinned input generation, preserve
one accepted event contribution, and publish only one certified output generation.

- Planning and optimization may change operator order but not business semantics.
- Every action and its potential repeated scan/shuffle is intentional.
- Nondeterministic expressions, time, random values, and input discovery are pinned or excluded.
- Plan assertions target semantic properties such as required filters/exchanges, not volatile operator IDs or full text.
- Runtime metrics reconcile scan rows/bytes, shuffle rows/bytes, and output rows with quality controls.
- An adaptive plan is captured after execution when AQE is enabled.

## From expression to execution

```python
from pyspark.sql import functions as F

candidate = (
    spark.read.schema(EVENT_SCHEMA).parquet(input_uri)
         .where(F.col("event_date_utc") == F.lit(target_date))
         .select("tenant_id", "event_id", "product_id", "event_type", "revenue_usd")
         .groupBy("tenant_id", "product_id")
         .agg(
             F.count("event_id").alias("event_count"),
             F.sum("revenue_usd").alias("revenue_usd"),
         )
)

# No data must have been computed merely by constructing candidate.
candidate.explain(mode="formatted")
candidate.write.mode("errorifexists").parquet(candidate_uri)  # action
```

The scan, filter, projection, exchange, and aggregate may appear in one SQL query.
The exchange usually separates stages because downstream aggregate tasks require
records from multiple upstream partitions. The write is an action and adds output
tasks/commit behavior. Calling `count()` first for logging can execute the expensive
plan once, then the write can execute it again unless results are deliberately
materialized.

## Reading a plan

For each plan, answer in order:

1. Which exact files/table snapshot and columns can the scan read?
2. Which filters are partition/data-source filters versus post-scan filters?
3. What are estimated rows/bytes, and what source/catalog/runtime statistics support them?
4. Where are `Exchange`, `BroadcastExchange`, sort, aggregate, or Python evaluation operators?
5. What partitioning does each exchange produce, and how many downstream tasks are expected?
6. Which actions and reused branches can recompute the plan?
7. If AQE is active, what changed between initial and final plans and why?
8. Do SQL UI rows/bytes/shuffle/spill metrics agree with reconciliation expectations?

`explain("cost")` can expose estimates when statistics exist. The formatted plan is
usually easier to connect to operator details. Both should be treated as reviewed
artifacts tied to an exact Spark/configuration/schema version.

## Laziness and side effects

Avoid:

```python
events = read_events(spark)       # no read is proven here
metrics = transform(events)       # no transform is proven here
logger.info("pipeline complete") # false operational signal
metrics.write.parquet(path)       # execution actually begins here
```

Prefer lifecycle events with precise meanings: `plan_built`, `action_started`,
`candidate_write_completed`, `quality_passed`, and `generation_published`. Include
run/input/output generation IDs without embedding sensitive record values.

## Materialization decision

| Situation | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| One downstream action | No cache | Avoid storage and cleanup cost | Upstream is unexpectedly recomputed |
| Same expensive intermediate reused | Persist with explicit level and unpersist | Pay once when reuse benefit exceeds cache cost | Eviction/spill makes it slower |
| Recovery across application loss | Durable staged dataset + manifest | Executor cache dies with application | Storage/lineage cost exceeds recomputation |
| Tiny bounded diagnostic result | Bounded collect/take | Driver inspection is controlled | Bound is not enforceable |
| Quality metric derivable in write flow | Observation/aggregate designed into plan | Avoid a full duplicate action | Instrumentation complicates correctness |

Cache is an execution optimization, not an authoritative checkpoint. Durable
staging adds a data lifecycle and must be versioned, validated, protected, and
expired.

## Failure model and recovery

| Failure | Observable symptom | Cause/containment | Recovery evidence |
| --- | --- | --- | --- |
| Analysis error | Action/explain fails before tasks | Missing/ambiguous column, type/function mismatch | Contract test fails deterministically |
| Repeated full scan | Multiple jobs and scan metrics | Separate actions over uncached plan | One intentional scan after redesign |
| Unexpected exchange | Large shuffle stage | Lost partitioning or join/group requirement | Plan plus measured bytes explained |
| Plan estimate wrong | Strategy/actual rows diverge | Missing/stale statistics or correlated data | Runtime stats and refreshed stats reviewed |
| AQE strategy change | Initial/final plans differ | Runtime partition/size evidence | Final plan recorded; result unchanged |
| Nondeterministic rerun | Same input gives different rows | Incomplete order, random/time, mutable source discovery | Pinned reruns reconcile exactly |
| Driver failure after tasks | Application aborts | Control plane lost | Candidate remains unpublished; whole run restart safe |

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Laziness test | Instrumented tiny source / local Spark | Build plan before action | No source execution before action | Pending |
| Semantic plan test | Fixed schema/config | Inspect structured/normalized plan properties | Required pruning/filter/exchange present | Pending |
| Action accounting | Fixture | Run quality and write path | No unexplained duplicate scans/actions | Pending |
| AQE comparison | Skew/size fixtures | Capture initial and final plans | Adaptation explained; same result | Pending |
| Rerun test | Pinned input | Execute twice with different partition counts | Identical unordered business result | Pending |

Avoid snapshot-testing the entire `explain()` string across engine versions. Assert
data results first and a small set of meaningful plan properties second.

## Debugging guide

Use application/run IDs to find the SQL query, then connect SQL query → jobs →
stages → tasks. Inspect the scan paths and pushed/data/partition filters; compare
estimated with actual rows; locate exchanges and Python operators; sort task
duration, input, shuffle, spill, and GC to find outliers; inspect the final adaptive
plan. Reproduce on the same input manifest and configuration, then shrink the
failing partition without removing its distribution characteristic.

## Common pitfalls

### Pitfall: believing `explain` executes the data

Planning can reveal resolution and intended operators but cannot prove reader
permissions, corrupt data behavior, task memory, runtime skew, or successful
publication. Execute proportional evidence.

### Pitfall: adding `count()` for observability

An extra action may double an expensive lineage. Prefer operator metrics, a
purposeful reused cache, or quality computations integrated into the pipeline.

### Pitfall: forcing a preferred plan from folklore

Hints and fixed partition counts can become wrong as data changes. Start with
cardinality/byte evidence, maintain statistics, inspect AQE decisions, and benchmark
on a representative distribution.

## Security, performance, and operations

Plans, SQL text, paths, and error messages may expose tenant, column, or storage
metadata; restrict UI/history access and sanitize literals. Persist event logs for
post-run diagnosis under retention controls. Define budgets for scan bytes, shuffle
bytes, spill, task duration distribution, and total runtime. Plan shape is a leading
diagnostic; measured runtime/cost and correct results are the acceptance evidence.

## Compatibility and delivery

Optimizer output can change between Spark versions, connector versions, statistics,
and configuration. During upgrades, compare results, initial/final plans, scan and
shuffle metrics, and failure behavior on representative inputs. Canary to a new
candidate location and publish only after reconciliation; do not require incidental
operator names to remain identical.

## Working example

- PySpark plan fixture/tests: Planned
- Try it: planned local Spark test capturing formatted/cost plans and event metrics
- Expected result: one explained exchange, bounded actions, identical rerun output
- Scale represented: none yet
- Remaining risk: AQE, statistics, connector pushdown, distributed shuffle, and plan-version compatibility

## Knowledge check

1. Mark transformations and actions in the example and predict job boundaries.
2. Explain why an exchange normally creates a new stage.
3. Diagnose two full scans caused by a logging `count()` and a write.
4. Choose cache, durable staging, or recomputation for three different reuse/recovery needs.
5. State which claims an initial physical plan cannot prove.
6. Design stable plan assertions for an engine upgrade.

## Key takeaways

- Transformations describe work; actions demand execution.
- Logical intent, selected physical operators, and runtime behavior are distinct evidence layers.
- Exchanges identify major movement and stage boundaries.
- AQE makes the final plan and runtime statistics essential to diagnosis.
- Materialization must have an owner, benefit, lifecycle, and recovery purpose.

## Resources

- [Spark SQL explain syntax](https://spark.apache.org/docs/4.2.0/sql-ref-syntax-qry-explain.html) (reviewed 2026-09)
- [Spark SQL performance tuning and AQE](https://spark.apache.org/docs/4.2.0/sql-performance-tuning.html) (reviewed 2026-09)
- [Spark web UI and SQL plan views](https://spark.apache.org/docs/4.2.0/web-ui.html) (reviewed 2026-09)

## Related topics

- [Partitions, shuffles, parallelism, and output files](04-partitions-shuffles-parallelism-and-output-files.md)
- [Testing, tuning, failure diagnosis, and deployment](08-testing-tuning-failure-diagnosis-and-deployment.md)

## Completion checklist

- [x] Laziness, plans, actions, jobs, stages, tasks, AQE, and materialization explained
- [x] Failure, security, quality, performance, observability, and compatibility addressed
- [ ] Laziness, plan, action-accounting, AQE, and rerun evidence run

