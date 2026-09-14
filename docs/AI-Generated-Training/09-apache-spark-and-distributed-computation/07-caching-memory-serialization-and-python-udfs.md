# Caching, Memory, Serialization, and Python UDFs

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: PySpark / Spark SQL / Distributed computation  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Spark uses executor memory for task execution and cached data, may spill to disk,
and crosses serialization boundaries among driver, JVM executors, Python workers,
shuffle, and storage. Caching can reduce repeated computation but can also evict
useful blocks, increase GC, spill, duplicate sensitive data, and make a job slower.

Python UDFs allow custom logic Spark SQL cannot express directly. They also add a
language boundary and can reduce optimizer visibility. Built-in SQL functions are
the default because they preserve relational semantics and engine optimization;
Arrow/vectorized forms can reduce boundary overhead but do not remove memory,
typing, correctness, or observability obligations.

## Learning objectives

- Trace decoded rows and columns through JVM, Python, shuffle, cache, spill, and storage.
- Decide whether and where to persist from reuse, recomputation, and capacity evidence.
- Prevent unsafe driver collection and oversized task closures.
- Prefer built-in expressions and choose Python/Arrow/Pandas functions only for justified gaps.
- Test UDF null, type, batch, dependency, retry, and partition behavior.

## Prerequisites

- Python process/serialization/resource behavior from [02 Python for Data Engineering](../02-python-for-data-engineering/README.md)
- [Lazy evaluation, logical plans, and physical plans](03-lazy-evaluation-logical-and-physical-plans.md)
- [Joins, aggregation, broadcasting, and skew](05-joins-aggregation-broadcasting-and-skew.md)

## Mental model and terminology

An Android memory cache can avoid repeated disk/network work but is evictable and
not the source of truth. Spark cache has the same useful property. The analogy
stops because cached blocks are partitioned across executor JVMs, may be serialized
or spilled, are recomputed from lineage, and compete with distributed execution
memory.

```text
driver Python -> plan/closure serialization -> executor JVM
                                             | built-in SQL operators
storage -> decode -> columnar/row execution --+
                                             | Python boundary
                                             v
                                      Python worker batches
                                             |
                         result serialization back to JVM plan
                                             v
                              shuffle / cache / spill / output
```

| Term | Meaning in this guide |
| --- | --- |
| Execution memory | Working memory for joins, aggregations, sorts, and shuffles |
| Storage memory | Memory used for cached/persisted blocks |
| Spill | Writing intermediate state to local disk when memory is insufficient |
| Closure | Code plus captured values serialized for remote task execution |
| Scalar Python UDF | Function applied with Python/JVM data conversion, logically per row |
| Pandas UDF | Vectorized batch interface using Pandas with Arrow transfer |
| Arrow UDF | PyArrow array/batch interface using columnar transfer |
| `toPandas`/`collect` | Materializes distributed results in driver memory; safe only under enforced bounds |

## Requirements, estimates, and invariants

The reference pipeline must finish inside its batch/recovery window on the uncached
path; cache is not a correctness dependency. Assume decoded/intermediate data may
be several times compressed Parquet size until measured.

- Cached and spilled data are derived, replaceable, access-controlled, and expired.
- Eviction or executor loss may slow the job but cannot change results.
- Driver-bound collections have enforced row and byte bounds.
- Task closures do not capture sessions, clients, huge lookup maps, secrets, or non-serializable state.
- UDF input/output Spark schemas, `NULL`, errors, determinism, and dependency versions are explicit.
- UDF retries produce no external side effects.
- Built-in and custom implementations reconcile on fixtures and representative data.

## Cache decision and lifecycle

```python
from pyspark import StorageLevel

validated = validate(raw_events).persist(StorageLevel.MEMORY_AND_DISK)
try:
    quality = compute_quality(validated)  # action when materialized
    metrics = aggregate(validated)        # meaningful reuse
    write_candidate(metrics)
finally:
    validated.unpersist(blocking=False)
```

This is justified only if reuse saves more work than persistence, serialization,
eviction, spill, and cleanup cost. Record which first action materializes the
cache; `persist()` itself remains lazy. If the application must restart after
driver loss, use a durable versioned stage rather than cache.

| Need | Prefer | Why |
| --- | --- | --- |
| One pass | Recompute/no cache | Lowest lifecycle cost |
| Reused expensive deterministic branch | Measured persistence | Avoid duplicated source/shuffle work |
| Cross-application recovery | Durable staged files/table snapshot | Cache is application/executor scoped |
| Small lookup | DataFrame broadcast after size proof | Engine-managed join rather than closure capture |
| Small bounded diagnostic | `take`, aggregate, or strict `limit` plus byte guard | Protect driver |

The default `cache()` storage level and memory internals are version-sensitive;
choose explicit intent and verify in the Storage/UI metrics rather than memorizing
a default.

## Built-ins before UDFs

Avoid:

```python
from pyspark.sql.functions import udf

@udf("string")
def normalize_event_type(value):
    return None if value is None else value.strip().upper()

normalized = events.withColumn("event_type", normalize_event_type("event_type"))
```

Prefer:

```python
from pyspark.sql import functions as F

normalized = events.withColumn(
    "event_type",
    F.upper(F.trim(F.col("event_type"))),
)
```

The built-in expression exposes semantics to Catalyst and stays in the engine's
optimized path. If no equivalent exists, first define the UDF contract, then
benchmark a scalar, Arrow, Pandas, JVM-native, or upstream-normalization option.

## UDF contract example

```python
import pandas as pd
from pyspark.sql.functions import pandas_udf


@pandas_udf("decimal(18,2)")
def clamp_nonnegative(values: pd.Series) -> pd.Series:
    # Contract still needs explicit behavior for nulls, decimals, invalid values,
    # batch size, exceptions, and Arrow/Pandas/Spark coercion.
    return values.clip(lower=0)
```

This decorative example is intentionally not recommended for the clamp operation,
which Spark built-ins can express. It shows that a type annotation is not enough:
Pandas dtype, Arrow conversion, decimal behavior, and returned Spark SQL type must
be tested together. Spark 4.2 changed Arrow defaults for PySpark transfers and
regular Python UDFs, so migration tests must pin configuration and compare values.

## Memory and serialization boundaries

| Symptom | Likely boundary | Evidence to inspect |
| --- | --- | --- |
| Driver OOM | `collect`, `toPandas`, large result metadata/broadcast | Driver heap/process memory, result rows/bytes, call site |
| Executor JVM OOM | Join/aggregate/sort/cache, oversized partition | Peak memory, spill, task input/shuffle, GC, partition distribution |
| Python worker OOM | UDF batch/group loads too much | Python worker metrics/logs, Arrow batch/group size, key skew |
| High GC | Object-heavy rows/cache or insufficient heap | GC time, storage/execution memory, serialization format |
| Huge task size | Closure captures large objects | Serialized task warnings/logs, closure review |
| Slow UDF stage | Boundary conversion or Python logic | Plan Python operator, rows/batch, CPU, comparison with built-in |
| Disk exhaustion | Shuffle/cache spill | Spill bytes, local disk, concurrent tasks, cleanup |

Grouped Pandas operations can materialize an entire group in one Python worker;
Arrow transfer does not bound a hot group. Iterator/batch APIs may bound transfer
units but require strict output cardinality and resource-lifetime contracts.

## Failure model and recovery

| Failure | Detection | Containment/recovery | Result guarantee |
| --- | --- | --- | --- |
| Cache block lost | Storage/UI miss, recomputation | Recompute from immutable lineage | Same business rows |
| Excess eviction/spill | Low cache hit, disk/GC growth | Unpersist, change level/plan, add capacity after measurement | Correct but possibly slower |
| Non-serializable closure | Task serialization/start failure | Remove captured clients/state; initialize scoped resource safely | Fail before publish |
| Python dependency mismatch | Import/version error on executors | Package exact environment; validate every node/image | Fail closed |
| UDF exception on one value | Task retry repeats deterministic failure | Classify before UDF or quarantine declared error | No partial publish |
| UDF external side effect repeats | Duplicate external mutations | Remove side effect; stage and commit idempotently | Repair/reconcile required |
| Arrow coercion drift | Value/schema mismatch after upgrade | Pin config/versions; differential tests | Block rollout |

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Cache equivalence | Deterministic fixture / local Spark | Run cached and uncached | Exact same unordered result | Pending |
| Reuse profile | Representative input | Compare jobs, scans, runtime, memory/spill | Cache benefit exceeds cost | Pending |
| Driver bound | Oversized synthetic result | Exercise diagnostic/export guard | Collection rejected before OOM | Pending |
| UDF contract | Null/type/decimal/error/batch fixtures | Compare built-in/reference/UDF | Declared exact values/errors | Pending |
| Packaging | Cluster executors | Import and execute pinned dependency | Same versions and results on all executors | Pending |
| Failure retry | Inject Python worker/executor loss | Rerun attempt | Exact result; no side effects | Pending |

## Debugging guide

Locate the operator and process boundary first: driver, executor JVM, Python
worker, shuffle disk, or storage. Inspect the physical plan, Storage tab, executor
memory/GC/spill, per-task peak memory and skew, Python logs, dependency versions,
and number/size of driver-bound rows. Reproduce with the same hot group or data
type edge; a uniformly tiny fixture will not reproduce group OOM or coercion drift.

## Common pitfalls

### Pitfall: caching every intermediate

Cache only named reused expensive branches, verify materialization and hits, and
unpersist when the last consumer finishes. Cache pressure can slow unrelated work.

### Pitfall: using `toPandas()` as an export

It collects all selected data to the driver. Write through distributed sinks, or
enforce a small product contract with precomputed row/byte limits.

### Pitfall: assuming Arrow makes Python logic equivalent to built-ins

Arrow reduces transfer overhead in supported paths. It does not restore optimizer
visibility, bound grouped state, guarantee type coercion equivalence, or make
Python dependencies uniform.

## Security, governance, performance, and cost

Caches, spills, Python worker memory, event logs, and crash dumps inherit data
classification. Prevent sensitive values in exception text and UDF diagnostics;
control local disks and cleanup. Benchmark rows/second, boundary bytes, batch
sizes, executor/Python memory, GC, spill, cache hit/recompute, and cost using real
width and skew. Optimization is accepted only with equal data-quality results.

## Compatibility and delivery

Pin Spark, Python, Pandas, PyArrow, UDF dependencies, CPU architecture, and relevant
Arrow/configuration settings. Spark 4.2 documentation states columnar PySpark
exchange and regular Python UDF Arrow optimization are enabled by default, a
behavior change from earlier releases. Run differential null/decimal/timestamp/
nested-type tests, performance tests, and cluster packaging checks before upgrade.

## Working example

- Cache benchmark, UDF fixture, packaging artifact, failure injection: Planned
- Expected result: result-equivalent optimizations within memory/runtime budgets
- Scale represented: none yet
- Remaining risk: real executor/Python memory, Arrow compatibility, cluster dependencies, spill, and sensitive-data cleanup

## Knowledge check

1. Explain when cache helps and who owns its lifecycle.
2. Trace one column through Parquet, JVM execution, a Pandas UDF, and output.
3. Diagnose driver OOM separately from Python-worker OOM.
4. Replace a simple normalization UDF with built-in expressions.
5. Design a test for Arrow decimal/null coercion across an upgrade.
6. Explain why a cached DataFrame is not a recovery checkpoint.

## Key takeaways

- Cache is replaceable performance state and must earn its memory/lifecycle cost.
- Compressed input size does not bound decoded, shuffle, cached, or Python memory.
- Driver collection requires an enforceable product-size contract.
- Built-in SQL expressions preserve optimizer visibility and are the default.
- Arrow changes boundary cost and coercion behavior, not the need for correctness and capacity evidence.

## Resources

- [Spark tuning: memory and serialization](https://spark.apache.org/docs/4.2.0/tuning.html) (reviewed 2026-09)
- [Apache Arrow in PySpark](https://spark.apache.org/docs/4.2.0/api/python/tutorial/sql/arrow_pandas.html) (reviewed 2026-09)
- [PySpark UDF and UDTF guide](https://spark.apache.org/docs/4.2.0/api/python/user_guide/udfandudtf.html) (reviewed 2026-09)
- [PySpark 4.2 migration guide](https://spark.apache.org/docs/4.2.0/api/python/migration_guide/pyspark_upgrade.html) (reviewed 2026-09)

## Related topics

- [Testing, tuning, failure diagnosis, and deployment](08-testing-tuning-failure-diagnosis-and-deployment.md)
- [Python for Data Engineering](../02-python-for-data-engineering/README.md)

## Completion checklist

- [x] Cache, memory, spill, serialization, collection, UDF, Arrow, and packaging boundaries explained
- [x] Failure, security, quality, performance, operations, and compatibility addressed
- [ ] Cache, reuse, driver-bound, UDF, packaging, and failure evidence run

