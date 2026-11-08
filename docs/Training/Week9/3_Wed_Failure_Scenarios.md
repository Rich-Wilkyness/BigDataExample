# Spark Failure Scenarios, Debugging, and Performance Tuning

> Status: Organized and expanded lecture study guide
>
> Level: Beginner to intermediate, with production considerations
>
> Applies to: Spark SQL, PySpark, batch pipelines, and streaming recovery concepts
>
> Example status: Illustrative scenarios; runnable failure labs planned
>
> Evidence status: Documentation review and static checks only
>
> Last reviewed: 2026-11-04

## Overview

A data pipeline can fail by crashing, missing its delivery window, or publishing incorrect results. Debugging means finding evidence that explains the failure, applying a targeted change, and verifying both performance and data correctness afterward.

These notes organize the Wednesday lecture around Spark execution, the Spark UI, logs, dashboards, partitions, data skew, Adaptive Query Execution (AQE), out-of-memory errors (OOM), broadcast joins, `collect()`, and recovery. The original screenshots are retained as lecture references; they do not establish that the examples below were executed.

## Learning objectives

After studying these notes, you should be able to:

- Trace an application through jobs, stages, tasks, and executors.
- Choose the UI, logs, metrics, and query-plan evidence needed for a symptom.
- Distinguish uneven input, hot join keys, memory pressure, and infrastructure problems.
- Explain the tradeoffs between `coalesce`, `repartition`, shuffle partitions, and AQE.
- Separate driver memory failures from executor memory failures.
- Explain the limits of broadcast joins, lineage, retries, and checkpoints.
- Verify that a performance repair preserves the intended records and output grain.

Prerequisites: DataFrame transformations and actions, basic SQL joins and aggregations, and the distinction between a driver and workers. No cloud account or monitoring installation is needed to read the guide. The [Tuesday lecture](2_Tue_Open_Table_Formats.md) provides related publication and transaction concepts.

## 1. Mental model: how Spark divides work

| Term | Meaning | Debugging question |
| --- | --- | --- |
| Application | The driver and its executors for one Spark program | Which run, version, inputs, and settings are affected? |
| Driver | Coordinates execution and receives driver-side results | Did planning or result collection exhaust this process? |
| Executor | Worker process that executes tasks and holds intermediate data | Is this process alive, overloaded, or repeatedly lost? |
| Job | Computation triggered by an action; a SQL action can involve multiple jobs | Which action became slow or failed? |
| Stage | A group of tasks separated from other stages by shuffle dependencies | Where does progress stop? |
| Task | Work on one partition in a stage, with possible retry attempts | Are a few partitions much more expensive than others? |
| Partition | A logical piece of data processed by a task | How much data and computation land in each piece? |
| Shuffle | Redistribution of records between partitions | Is the exchange causing network, disk, or memory pressure? |

```text
DataFrame transformations build a plan
                 |
                 v
Action triggers execution
                 |
                 v
Jobs -> stages -> tasks operating on partitions
                 |
                 v
Executors run tasks; the driver coordinates and tracks progress
```

An executor can run multiple tasks concurrently and many more over its lifetime. Partitions do not need to equal executors. A useful mental model is parcels and delivery trucks: a truck carries several parcels, and a large parcel can dominate a trip. Unlike fixed delivery assignments, Spark can schedule later task attempts on different executors.

Spark's [RDD programming guide](https://spark.apache.org/docs/latest/rdd-programming-guide.html) explains distributed execution and recomputation.

## 2. Start with a repeatable debugging workflow

When someone says, “This job used to take 10 minutes and now takes 40,” treat the cause as unknown. These times are an illustrative scenario, not a measured classroom result.

1. **Define the impact.** Is the application failing, running slowly, waiting for resources, or producing wrong data? Which dataset and consumers are affected?
2. **Compare with a healthy run.** Record input rows and bytes, file count, key distribution, code version, Spark version, effective settings, cluster resources, and competing workloads.
3. **Locate the delay.** Separate scheduling or startup time from scanning, joining, aggregating, shuffling, and writing.
4. **Inspect the slow stage.** Compare task duration, input/shuffle bytes, spill, garbage collection, retries, and executor placement. Inspect the associated SQL plan.
5. **Form a hypothesis.** For example: one station key became unusually common, a join started multiplying rows, or available CPU capacity fell.
6. **Change one relevant factor.** Use a bounded fixture or isolated output destination. Save the baseline so the effect is reviewable.
7. **Verify recovery.** Compare runtime and resource use, then reconcile row counts, keys, aggregates, completeness, and freshness before publishing.

Keep application ID, run ID, job/stage/task IDs, failure timestamps, and code/configuration versions together. The final wrapper exception is often less useful than the earlier driver, executor, or platform event that caused it.

## 3. Spark UI and logs

### Where the UI lives

The live UI belongs to the **application lifetime**, rather than the lifetime of one job. A notebook application can finish a job and keep its UI available while its Spark context remains active.

| Interface | Typical address | Availability |
| --- | --- | --- |
| Local Spark application UI | `http://localhost:4040` | While the application is running; another application may use 4041 or a later port |
| Cluster application UI | Driver UI through the platform's supported route or proxy | Depends on routing and access controls; the driver address may be private |
| Spark History Server | `http://<history-host>:18080` | Can reconstruct application history from retained event logs |

For history, enable `spark.eventLog.enabled` before execution, choose a persistent `spark.eventLog.dir`, and configure the history server to read that location using `spark.history.fs.logDirectory`. Event logs support UI reconstruction; retain driver/executor text logs separately for stack traces. See [Spark monitoring and history](https://spark.apache.org/docs/latest/monitoring.html).

![Lecture reference: Spark UI dashboard](<Screenshot 2026-11-04 at 12.38.24 PM.png>)

### Which tabs answer which questions?

| Tab | What to inspect | What it helps distinguish |
| --- | --- | --- |
| Jobs | Duration, status, associated stages | Which action or job regressed |
| Stages | Task-duration distribution, shuffle bytes, spill, failed attempts | A few expensive partitions versus broad slowdown |
| Executors | Active/failed tasks, GC time, shuffle totals, lost executors, log links where available | Process-wide pressure or infrastructure loss |
| SQL / DataFrame | Physical plan and operator metrics | Join strategy, exchanges, unexpected row growth, and adaptive changes |
| Storage | Materialized cached data and storage use | Cache pressure, eviction, or unexpected persistence |
| Environment | Reported Spark properties and runtime information | Whether a requested configuration was actually applied |

A “hanging executor” is a symptom. If unrelated tasks run slowly only on that executor, investigate its host, disk, network, and memory. If unusually large shuffle partitions take longer wherever they run, skew becomes a stronger hypothesis. See the [Spark UI guide](https://spark.apache.org/docs/latest/web-ui.html).

### Follow the error to its owner

Inspect the driver log for planning, submission, and result-handling failures. Inspect the failed executor or Python-worker log for task-level errors. Inspect the resource manager or container events when a process disappears without a useful Spark exception. Log paths and links depend on deployment; there is no universal Spark installation directory containing every application's logs.

## 4. Partitions, coalesce, and repartition

**Input partitions**, **shuffle partitions**, and **output files** describe different points in execution. Increasing a shuffle setting does not necessarily change how the input is scanned. Writing a partitioned dataset can produce multiple files per task across output directories, so task count is not a universal file-count guarantee.

| Mechanism | What it changes | Cost and useful case | Main limitation |
| --- | --- | --- | --- |
| `df.coalesce(n)` | Reduces DataFrame partitions without a redistribution shuffle in the usual reduction case | Often useful after a large filter to reduce unnecessary output tasks | Can concentrate work and preserve unevenness; requesting more partitions does not increase them |
| `df.repartition(n)` | Redistributes rows into a requested partition count using a shuffle | Can increase or decrease parallelism and improve row-count balance | Adds exchange cost; equal row counts do not guarantee equal bytes or CPU work |
| `df.repartition(n, "station_id")` | Hash-partitions by the specified key | Useful when a downstream operation needs key locality | All rows for one hot key still map together |
| `spark.sql.shuffle.partitions` | Sets the initial partition count for ordinary SQL/DataFrame shuffles | Influences joins and aggregations; tune with observed workload | Too few can create large tasks; too many can create scheduling overhead; AQE can alter the result |

The DataFrame [`coalesce`](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.coalesce.html) and [`repartition`](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.repartition.html) APIs document these behaviors.

### Interpreting the classroom partition example

The lecture compared uneven sizes after coalescing with more even sizes after repartitioning, including approximately 100 KB versus 200 KB. Retain that as a classroom observation, not a general benchmark: twice the bytes does not guarantee twice the runtime. Compression, row width, computation, caching, hardware, and fixed task overhead also matter.

Coalesce is useful when reducing overhead after shrinking a dataset. Repartition is useful when redistribution is worth its cost. Neither operation is a universal repair for a slow job.

## 5. Data skew: a few tasks do most of the work

**Data skew** means work is distributed unevenly. It can come from uneven file sizes, popular keys, default values, or records with very different processing costs.

Consider an illustrative Citi Bike dataset with one row per station observation. Most stations contribute similar numbers of observations, but a producer incorrectly assigns many rows the key `UNKNOWN`. A shuffle by station ID can send those rows to one partition. Adding hash partitions does not divide that single key.

### Evidence before repair

- Compare maximum task duration and shuffle-read bytes with typical tasks in the same stage.
- Inspect frequent keys, including default values and missing identifiers; distinguish invalid records from legitimate high-volume entities.
- Check join-side uniqueness and output cardinality. Duplicate station metadata can multiply observations even without an unusually popular input key.
- Check whether the same host is slow across unrelated tasks, or the same logical work is repeatedly slow across hosts.

### Match the repair to the cause

| Cause | Candidate repair | Correctness condition |
| --- | --- | --- |
| Uneven upstream partitions | Redistribute before the expensive operation | Preserve all required rows |
| Oversized partitions across most tasks | Increase useful parallelism and reduce row width | Measure scheduler overhead and memory after the change |
| Invalid/default key dominates | Apply the producer contract and quarantine invalid rows | Account for rejected records; do not silently discard them |
| Small eligible join side | Consider a broadcast join | Validate join semantics and memory fit |
| Eligible skewed SQL join | Evaluate AQE skew-join handling | Inspect the executed plan and reconcile results |
| Legitimate hot-key aggregation | Consider partial aggregation; use salting only with a correct recombination design | SUM can combine partial sums; AVG needs partial sums and counts; exact distinct counts need additional care |

This repair table is a diagnostic design aid. Its remedies must be tested against the actual operator and dataset.

## 6. AQE: adapting the SQL plan at runtime

**Adaptive Query Execution** uses runtime statistics to revise a Spark SQL/DataFrame physical plan. It can coalesce small shuffle partitions, change an eligible join strategy, and split supported skewed join work. AQE is not a general optimizer for arbitrary Python or RDD code.

Useful configuration names include `spark.sql.adaptive.enabled`, `spark.sql.adaptive.coalescePartitions.enabled`, and `spark.sql.adaptive.skewJoin.enabled`. Inspect their effective values and compare initial and executed plans rather than assuming a configuration switch changed the work. The [Spark 4.2 performance guide](https://spark.apache.org/docs/4.2.0/sql-performance-tuning.html) matches the repository's pinned PySpark dependency; managed runtimes can differ.

For an AQE comparison, hold the input, query, and resource budget constant; record both plans, task distribution, runtime, and result equivalence. A small local fixture may show a plan change without producing a meaningful speedup. AQE cannot repair incorrect join conditions, missing source records, or unrestricted driver collection.

## 7. Out-of-memory errors: identify the process first

An OOM is a resource symptom, not a diagnosis. First determine whether the driver, executor JVM, Python worker, or containing process/container exhausted its allowance.

| Location | Typical trigger | Evidence | Candidate repair |
| --- | --- | --- | --- |
| Driver | `collect()`, `toPandas()`, oversized local objects | Driver traceback/log, result volume, memory limit | Bound returned data or write distributed output |
| Executor JVM | Large join/aggregation state, oversized partitions, excessive cached data | Executor OOM, GC time, spill, task/shuffle distribution | Reduce work/state, address skew, remove unused cache, tune concurrency/partitioning |
| Python worker | UDF allocations, wide batches, loading large objects per worker | Python traceback, process/container memory | Prefer built-in expressions where suitable, bound batches and allocations |
| Container/process limit | Heap plus Python/native/direct-memory usage exceeds allocation | Resource-manager termination reason and memory metrics | Size heap and non-heap allowances together; reduce concurrent memory demand |

### Memory sizing is about concurrent working state

Compressed file size is not a reliable estimate of required executor memory. Decoding, object representation, hash tables, sort buffers, cached data, and simultaneous tasks all affect memory use. Some operators spill to disk, so the whole input also need not fit in memory at once.

Conceptual budget, not a Spark allocation formula:

```text
Executor/container demand depends on:
  simultaneous task working sets
  + cached data
  + broadcast state
  + JVM/runtime overhead
  + Python/native buffers where applicable
```

An executor running four demanding tasks can exhaust memory even if one fits on its own. More partitions may reduce average work per task, but a hot key can remain large and extra concurrent tasks can still increase pressure. See [Spark memory tuning](https://spark.apache.org/docs/latest/tuning.html).

Increasing `spark.executor.memory` can help when heap capacity is the measured constraint. Also consider `spark.executor.memoryOverhead`, Python/native use, driver memory, and resource-manager limits. Apply deployment memory settings at the appropriate launch boundary; changing a session property does not resize an already running JVM. See [Spark configuration](https://spark.apache.org/docs/latest/configuration.html).

## 8. Broadcast joins and safe result inspection

### Broadcast joins

A broadcast join makes the eligible smaller relation available to executors so matching can happen without shuffling the large relation for that join. It still transfers the broadcast data and consumes memory; it does not eliminate all network traffic or exchanges elsewhere in the query.

Spark can select broadcasting using estimated size and `spark.sql.autoBroadcastJoinThreshold`; supported join hints can influence selection. The threshold is not a memory safety guarantee, and a hint may request broadcasting above it. Join type, statistics, runtime settings, and actual in-memory representation matter. See [SQL join strategy and broadcast tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html).

A broadcast variable shares a read-only application value. A broadcast join is a SQL execution strategy. They have a similar replication idea, but broadcasting a Python dictionary does not itself select a SQL broadcast join.

### `collect()` moves the result to the driver

`collect()` returns every result row as a local list. It is appropriate only when the **entire result** is known to be small enough for driver memory. A distributed computation can succeed on executors and then fail while delivering results to the driver.

Use a bounded `show()` or `take(n)` for inspection, or aggregate first and collect a demonstrably small summary. For large results, write through the distributed sink. A row limit bounds the number of returned rows, not their byte size or the total upstream computation. The [`collect()` API](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.collect.html) explicitly limits its use to results that fit in driver memory.

## 9. Common errors: symptom, evidence, and response

Error wording varies by Spark version, language, connector, and platform. These are representative diagnostic cases, not executed failure traces.

| Error or symptom | First evidence to inspect | Likely cause to test | Targeted response |
| --- | --- | --- | --- |
| `Task not serializable` in JVM code; serialization/pickling error in PySpark | Driver stack trace and captured closure values | Function captures a session, connection, lock, or other unsuitable object | Pass serializable values; initialize required external resources in the worker/partition with cleanup and retry-safe effects |
| `java.lang.OutOfMemoryError: Java heap space` | Identify which JVM failed; inspect GC and task metrics | Excessive local result, cache, partition, join, or aggregation state | Use the driver/executor diagnosis in Section 7 before resizing |
| `ExecutorLostFailure` or process killed | Executor logs plus platform termination events | Memory limit, host loss, preemption, or another process failure | Repair the recorded termination cause; the wrapper message alone does not prove OOM |
| `FetchFailed` | Failed reduce task, missing shuffle block, earlier executor events | Shuffle data lost or unavailable due to process, disk, or network failure | Find why the shuffle producer disappeared or became unreachable; repeated retry cannot fix permanent disk failure |
| `AnalysisException` / unresolved column | Analyzed query, current schema, catalog object | Rename, wrong alias, missing field, or incompatible expression | Correct the expression or contract; check intended types and NULL semantics |
| SQL query suddenly multiplies rows | Join keys, side-specific duplicates, operator row counts | Many-to-many join or missing predicate | Define the intended grain and fix the join/cardinality contract |
| Access denied / forbidden storage read | Exact identity, operation, target, and authorization error | Wrong credentials, missing permission, or expired session | Restore intended access; performance tuning will not resolve authorization |
| Write succeeds partly, then fails | Destination files, table history/commit state, run manifest | Some effects completed before failure | Determine visible committed state before retry; reconcile and repair through the sink's supported protocol |

“Make it serializable” is incomplete advice when the object represents a live external connection. Resource ownership, lifecycle, and repeated task attempts still need a design.

## 10. Recovery: lineage, retries, checkpoints, and publication

| Mechanism | What it provides | Boundary to remember |
| --- | --- | --- |
| RDD lineage | Recompute lost partitions from transformations and available inputs | Does not preserve an entire failed driver process or make external effects idempotent |
| Task/stage retries | Retry work within configured limits | A deterministic bad record, OOM, or unavailable dependency can fail repeatedly |
| Batch DataFrame checkpoint | Materialize a DataFrame and truncate its logical plan | Does not automatically restart an arbitrary application at that statement |
| Structured Streaming checkpoint | Persist progress and state needed for a compatible query restart | Requires retained/replayable input, valid checkpoint data, and supported query changes |
| Sink commit / idempotency protocol | Control what output becomes visible and what a retry repeats | Depends on the sink and operation, not just Spark task completion |

The batch [`DataFrame.checkpoint()` API](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.checkpoint.html) differs from [Structured Streaming recovery](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html#recovering-from-failures-with-checkpointing). For streaming, delivery guarantees depend on the source, sink, and processing mode; custom `foreachBatch` writes require their own deduplication/idempotency design. Deleting a checkpoint changes recovery state and can trigger replay or loss, depending on the source and restart settings.

### Recovery invariants and ownership

For the illustrative station-observation pipeline, define one output row per accepted `(station_id, observed_at)` observation, assuming the source contract permits that key. The source owner defines identity and replay availability; the pipeline owner accounts for validation and retries; the storage/table owner defines publication behavior; the consumer owner verifies downstream freshness.

Before declaring recovery complete, establish that:

- Every intended input record is accounted for as accepted or rejected under an explicit contract.
- The output has the intended grain and no unexplained join multiplication or retry duplicates.
- Consumers see a complete published result under the chosen sink protocol.
- Corrected data reaches downstream tables and freshness targets recover.

A green Spark job is execution evidence. Reconciliation is evidence that the data recovered correctly.

## 11. Dashboards and deployment environments

![Lecture reference: Grafana dashboard](<Screenshot 2026-11-04 at 12.53.11 PM.png>)

### Logs, metrics, and dashboards serve different purposes

**Logs** explain events and exceptions. **Metrics** describe changes over time, such as latency, failures, memory, and backlog. **Dashboards** bring these signals together; they do not collect all signals automatically.

Prometheus collects and stores time-series metrics, typically by scraping instrumented targets or exporters. Grafana queries configured data sources to visualize data; Datadog is another monitoring platform discussed in class. Spark metrics require a compatible export/scrape path and configuration. See the [Prometheus overview](https://prometheus.io/docs/introduction/overview/) and [Spark metrics documentation](https://spark.apache.org/docs/latest/monitoring.html#metrics).

Typical local ports are Prometheus `9090` and Grafana `3000`; service configuration, proxies, and container mappings can change them. The [Grafana configuration reference](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#http_port) documents its HTTP port setting. These notes do not install or connect either tool.

| Dashboard signal | Why it matters | Follow-up evidence |
| --- | --- | --- |
| Runtime trend and task-duration distribution | Detect regressions and long tails | Compare input volume and slow-stage tasks |
| Shuffle bytes, spill, GC time, memory | Identify exchange and memory pressure | Correlate with join/aggregation plans and process limits |
| Failed attempts and executor losses | Detect repeated instability | Read the first relevant exception and platform event |
| Latest complete publication and backlog | Show consumer freshness risk | Check source progress and sink commit state |
| Counts, duplicate keys, rejects, reconciliation | Detect incorrect success | Trace the affected input interval and output version |

Keep high-cardinality run/task IDs in searchable logs or traces rather than unbounded metric labels. Avoid placing credentials, raw PII, or unrestricted input records in logs or dashboards. Grant access to the UI and retained telemetry according to their data exposure.

### Same investigation, different evidence locations

| Environment | Evidence sources to locate | Questions to answer |
| --- | --- | --- |
| Local / on-premises Spark | Live UI, configured event logs, driver terminal/logs, executor logs, host metrics | Was history enabled before the run? Did the OS kill a process? |
| AWS-hosted Spark | Platform job history and driver/executor logs; configured CloudWatch or S3 log delivery | Which service/cluster ran it, and were logs actually retained? |
| Google Cloud-hosted Spark | Platform job history, Cloud Logging, and configured storage log destinations | Which project, job ID, identity, and log destination apply? |
| Azure-hosted Spark | Workspace/platform job history and configured Azure Monitor or storage destinations | Which runtime and workspace own the driver/executor evidence? |
| SQL warehouse outside Spark | Warehouse query history/profile, plans, queueing, spill, and access errors | Did execution slow down, or was it waiting for capacity? |

These are navigation examples, not universal logging guarantees or service setup instructions. Stackdriver is an older name associated with Google's monitoring/logging products. A managed platform may proxy its own UI instead of exposing driver port 4040.

## 12. Planned local failure labs

The original request for a directory of runnable examples is retained here as **planned follow-up work**. No lab directory, failure script, or benchmark is included in this notes edit. A proposed location is `failure-scenario-labs/` alongside this lecture.

| Proposed lab | Controlled comparison | Evidence to capture |
| --- | --- | --- |
| Coalesce versus repartition | Same bounded input and target partition count | Partition row counts, exchanges, task durations, and output equivalence |
| Shuffle partition counts | Same aggregation with a few selected counts | Task count, duration, spill, and result equality |
| Skew | Uniform versus hot-key input; count-only versus key-based repartition | Key frequencies, task/shuffle distribution, and unchanged aggregates |
| AQE off versus on | Eligible SQL join with otherwise identical settings | Initial/executed plans, skew handling, task distribution, result equality |
| Serialization failure | Closure capturing an unsuitable object versus worker-owned initialization | Error origin, closure contents, cleanup, and retry behavior |
| Driver result pressure | Guarded oversized-result example versus bounded inspection | Estimated returned bytes and driver limit; start with a guard rather than exhausting memory |
| Executor memory pressure | Explicitly bounded, opt-in workload versus reduced working state | Termination cause, concurrent tasks, spill/GC, and correct output |

Each future lab should generate deterministic synthetic data, explain its grain, cap its work, write to an isolated local destination, and provide expected observations without claiming exact timing. Inspect existing local environment settings before writing launch commands. Local mode can teach task and plan behavior but cannot prove multi-host network, executor-loss isolation, or cloud recovery behavior.

## Knowledge check

1. A few tasks take ten times longer than the median. What evidence would distinguish skew from a slow host?
2. Why can `repartition(100, "station_id")` leave one hot station expensive?
3. When is coalesce useful, and what can go wrong with `coalesce(1)`?
4. Why might a 1 GB compressed input require substantially more than 1 GB of working memory?
5. A job fails during `collect()`. Which process and limits would you inspect first?
6. What would demonstrate that AQE changed an executed plan?
7. Why does a checkpoint not automatically make a custom database write safe to repeat?
8. A repaired job finishes faster. What checks establish that its output is still correct?

## Completion checklist and evidence status

- [ ] Explain jobs, stages, tasks, executors, and partitions in your own words.
- [ ] Trace one actual slow or failed run from symptom to supporting evidence.
- [ ] Compare two plans and reconcile outputs after one tuning change.
- [ ] Demonstrate recovery with the intended sink and retained input.
- [ ] Build and run the planned local labs, recording exact environment and results.

The explanations and primary references were reviewed, and local documentation checks are recorded in [curriculum coverage](../../AI-Generated-Training/COVERAGE.md). No Spark job, failure injection, history server, monitoring deployment, cloud operation, or performance benchmark was run for this edit. The runnable labs and all behavioral recovery/performance evidence remain pending.
