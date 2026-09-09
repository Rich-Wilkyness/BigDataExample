# Spark Architecture: Driver, Executors, and Clusters

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Apache Spark / PySpark / Batch / Platform  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A Spark application is one coordinated computation with a driver process and
executor processes. The driver builds plans, requests resources, schedules work,
tracks task attempts, and decides whether the application succeeds. Executors
run tasks and hold shuffle/cache state for that application. A cluster manager
allocates resources but does not own the dataset's business correctness.

This separation matters because driver failure, executor failure, task failure,
and output-publication failure have different blast radii and recovery owners.
Spark can retry pure task computation, but it cannot make an external API call or
multi-file publication safe merely by retrying it.

## Learning objectives

- Distinguish application, driver, executor, worker, cluster manager, job, stage, task, and attempt.
- Trace control and data flow in client and cluster deployment modes.
- Assign configuration, secrets, temporary data, retry, and shutdown ownership.
- Predict the effects of driver loss, executor loss, network delay, and capacity exhaustion.
- Evaluate local, standalone, Kubernetes, and YARN-like deployment choices without confusing the cluster manager with Spark execution semantics.

## Prerequisites

- [Processes, networks, clocks, and partial failure](../08-distributed-systems-foundations/01-processes-networks-clocks-and-partial-failure.md)
- [Retries, idempotency, speculation, and fault recovery](../08-distributed-systems-foundations/07-retries-idempotency-speculation-and-fault-recovery.md)
- Infrastructure for runtime evidence: planned exact Java, Python, PySpark, and cluster-manager versions

## Mental model and terminology

An Android app process coordinating WorkManager jobs is a useful first sketch:
one component describes work and other processes may execute units. It stops being
accurate because Spark executors are application-scoped compute processes, task
attempts operate on distributed partitions, and the driver is a centralized
control-plane dependency for the active application.

```text
submission client
      |
      | submit artifact + configuration
      v
cluster manager ------ allocates CPU/memory ------ worker nodes
      |                                             |
      | launches                                    | hosts
      v                                             v
driver <----- task status / heartbeats ---------- executors
  |                                                  |
  | plans jobs/stages/tasks                          | read source partitions
  +------ serialized task descriptions ------------>| write shuffle/candidates
```

| Term | Meaning in this guide |
| --- | --- |
| Application | One driver and its executors, identified and observed as a unit |
| SparkSession | Structured API entry point; not a durable dataset transaction |
| Driver | Process owning application planning, scheduling, and coordination |
| Executor | Application-scoped process running tasks and storing cache/shuffle state |
| Worker/node | Machine or container host; it may host multiple processes |
| Cluster manager | Resource allocator such as Standalone, Kubernetes, or YARN |
| Task attempt | One execution of one stage partition; retries/speculation create more than one attempt |
| Deployment mode | Whether the driver runs near the submitting client or inside cluster-managed infrastructure |

## Requirements, scale assumptions, and invariants

Assume the daily reference application reads 3 GiB compressed, needs at least 16
parallel scan tasks, and must finish in 45 minutes with 15 minutes left for a retry.
The exact executor count and memory are hypotheses until measured.

- The driver receives metadata and bounded results, never the whole raw dataset.
- Executor-local cache and shuffle are derived, replaceable, and not authoritative.
- Task code is deterministic for pinned input, schema, code, and configuration.
- Task retries do not perform non-idempotent external side effects.
- Candidate files stay invisible until one complete generation is certified.
- Application, run, stage, partition, attempt, and dataset-generation IDs remain distinguishable.
- Secrets are delivered to the processes that need them and never embedded in plans or logs.

## Process and ownership boundaries

| Boundary | Input contract | Owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Submitter → cluster | Pinned artifact, configuration, identity | Release/platform owner | Reject before admission or record application ID | Trusted control input |
| Driver → executor | Serialized closure/expression and partition assignment | Spark runtime | Retry/fail stage after timeout or exception | Trusted code; untrusted data |
| Executor → storage | Scoped reads, shuffle, candidate writes | Engine + storage platform | Retry only under declared commit protocol | Sensitive derived data |
| Driver → catalog/publisher | Certified generation metadata | Dataset owner | Keep previous generation visible on failure | Privileged control boundary |
| UI/log/metrics sink | Sanitized operational telemetry | Platform/operations | Monitoring degradation must not corrupt output | Restricted metadata |

## Lifecycle and deployment modes

1. The submitter resolves the exact application artifact and non-secret configuration.
2. The cluster manager admits or rejects the resource request.
3. The driver creates the Spark context/session and discovers executors.
4. An action causes the driver to plan jobs, stages, tasks, and attempts.
5. Executors read partitions, exchange derived blocks, and write candidate results.
6. The application validates/reconciles the candidate and invokes a separate publication contract.
7. The driver stops; executors and temporary resources are reclaimed; event history remains according to retention policy.

In client mode the driver remains with the submitting process, so client network
and lifecycle are production dependencies. In cluster mode the platform launches
the driver within managed infrastructure. Neither mode changes the need for
idempotent inputs, controlled outputs, observability, or a recoverable publication
boundary.

## SparkSession ownership

```python
from pyspark.sql import SparkSession


def run() -> None:
    # Configuration required during startup belongs in submission/configuration,
    # not scattered through transformations after the context exists.
    spark = SparkSession.builder.appName("daily-product-metrics").getOrCreate()
    try:
        build_candidate(spark)  # Planned repository implementation.
    finally:
        spark.stop()  # Releases the application control plane on normal exit.
```

Library functions should normally accept a `SparkSession` rather than silently
creating their own. This resembles injecting a coroutine scope or database handle:
the caller controls lifetime. The analogy ends because a Spark session fronts
remote executors and shared cluster resources, not merely in-process objects.

## Failure model and recovery

| Failure | Detection | Containment/recovery owner | Consumer-visible behavior |
| --- | --- | --- | --- |
| Invalid submission/config | Admission or startup error | Release owner fixes and resubmits same input scope | Prior generation remains |
| Driver process lost | Application state/heartbeat loss | Orchestrator restarts whole pinned run | Candidate abandoned; no partial publish |
| Executor lost | Missing heartbeat, task/executor failure | Spark reschedules lost tasks; platform may replace executor | No effect if task is pure and commit is safe |
| Task repeatedly fails | Attempt exceptions exceed policy | Dataset owner diagnoses data/code; quarantine or repair | Run fails closed |
| Network/storage throttling | Latency, fetch/read/write failures | Platform and job owners bound retries/backoff | Freshness degrades; prior data remains |
| Driver collects too much | Driver memory/GC/process death | Code owner replaces collection with distributed/bounded operation | Run fails before publication |
| Duplicate task side effect | Duplicate external rows/messages | Application owner reconciles and repairs | Correctness breach unless idempotency key exists |
| Cluster capacity shortage | Pending executors/tasks, queue time | Platform admission/scaling owner | Deadline risk; do not silently relax correctness |

Spark recomputation works for derived partitions with replayable lineage. It does
not rewind arbitrary external systems, restore deleted source files, or establish
exactly-once side effects outside a supported commit protocol.

## Security, privacy, and governance

- Give driver and executors distinct least-privilege identities when the platform supports it.
- Scope source reads, candidate writes, catalog updates, event logs, and UI access separately.
- Encrypt network, shuffle/spill, event-log, and object-storage paths as classification requires.
- Treat serialized functions and dependencies as deployable code; prohibit untrusted deserialization.
- Redact data samples, SQL literals, paths, environment variables, exception messages, and accumulator labels.
- Apply retention and deletion policy to shuffle, cache, event logs, candidate files, and failed-run diagnostics.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Lifecycle test | Tiny deterministic fixture / local mode | Start session, run, stop | One clean application lifecycle | Pending |
| Executor-loss test | Cluster fixture | Terminate executor during shuffle | Tasks retry; result reconciles exactly | Pending |
| Driver-loss test | Cluster fixture | Terminate driver before publish | No candidate becomes visible | Pending |
| Side-effect negative test | Instrumented sink | Force task retry around write | Demonstrates duplicate without commit protocol | Pending |
| Capacity evidence | Representative input | Record queue, executor, task, CPU, memory, I/O | Meets batch and recovery budget | Pending |

Local mode proves API and deterministic-result behavior only. It does not prove
remote serialization, executor replacement, network shuffle, permissions, or
cluster-manager recovery.

## Debugging guide

1. Identify application/run and whether failure occurred before admission, in the driver, in a stage, or during publication.
2. Inspect driver logs first for planning and application termination; inspect executor logs for partition-specific failures.
3. Correlate failed stage, task, partition, attempt, executor, input path, and generation IDs.
4. Compare task failure distribution: one partition suggests bad data/skew; many executors suggest dependency/configuration/platform failure.
5. Confirm whether any candidate or external side effect escaped before retrying.
6. Replay the smallest safe input scope and reconcile counts, keys, sums, and generation metadata before closing recovery.

## Common pitfalls

### Pitfall: treating the driver as a data-processing node

`collect()` and `toPandas()` move results to the driver. A result that fits in a
developer laptop sample may terminate the production driver. Use distributed
aggregations and bounded diagnostics; enforce a maximum row/byte contract before
intentional collection.

### Pitfall: putting external writes inside a transformation

Tasks can retry or run speculatively. A REST call, mutable database insert, or
message publish inside `map` can occur more than once. Prefer Spark-supported
transactional/commit-aware sinks or stage candidate data and publish through an
idempotent dataset-level protocol.

### Pitfall: confusing executor count with useful parallelism

Executors without runnable partitions sit idle; too many tasks add scheduling
overhead. Size from partition bytes, operator behavior, per-task memory, cores,
and deadline—not an arbitrary executor target.

## Performance, capacity, and operations

Track submission queue time, executor allocation delay, active/pending tasks,
task p50/p95/p99 duration, failed/retried tasks, executor loss, CPU time, JVM/Python
memory, GC, input/shuffle/spill/output bytes, and publication latency. A 45-minute
objective should reserve recovery time; an initial success at 44 minutes has no
useful failure budget.

Enable durable event logs for production diagnosis and protect them like dataset
metadata. Alerts need an owner and distinguish queue delay, no progress, retry
storm, skewed stage, storage failure, and failed publication.

## Compatibility, migration, and delivery

Pin Spark, Java, Python, PySpark dependencies, connector/catalog versions, and
configuration. Validate the same artifact in local tests and a cluster environment;
local success is not binary/package compatibility evidence. Deploy with a small
input scope or shadow output, compare plans and results, then cut over the catalog
pointer. Rollback normally republishes the last certified generation, not partial
files from a failed application.

## Working example

- PySpark source, fixtures, tests, and cluster configuration: Planned
- Entry point: planned `spark-submit` application accepting immutable input and candidate-output URIs
- Expected result: one reconciled candidate generation; failures leave the previous generation visible
- Scale represented: none yet
- Remaining risk: process isolation, executor loss, serialization, credentials, cluster scheduling, and publication integration

## Knowledge check

1. Draw the processes and network boundaries for client mode and cluster mode.
2. Predict what is lost when an executor dies versus when the driver dies.
3. Explain why retry-safe computation does not imply retry-safe external side effects.
4. Diagnose an application with idle executors and four long-running tasks.
5. Design driver shutdown and candidate cleanup without hiding a failed publish.
6. Specify the evidence required before moving from local mode to a production cluster.

## Key takeaways

- The driver owns the active application control plane; executors own replaceable task execution state.
- The cluster manager allocates resources but does not own business correctness.
- A task may have multiple attempts, so side effects require explicit idempotency or commit protocols.
- Driver memory is a bounded control-plane resource, not a convenient dataset sink.
- Candidate certification and publication remain dataset-level responsibilities outside task completion.

## Resources

- [Spark cluster mode overview](https://spark.apache.org/docs/4.2.0/cluster-overview.html) (reviewed 2026-09)
- [Spark standalone deployment modes](https://spark.apache.org/docs/4.2.0/spark-standalone.html) (reviewed 2026-09)
- [Spark configuration](https://spark.apache.org/docs/4.2.0/configuration.html) (reviewed 2026-09)
- [Spark monitoring and instrumentation](https://spark.apache.org/docs/4.2.0/monitoring.html) (reviewed 2026-09)

## Related topics

- [DataFrames, Spark SQL, schemas, and types](02-dataframes-spark-sql-schemas-and-types.md)
- [Testing, tuning, failure diagnosis, and deployment](08-testing-tuning-failure-diagnosis-and-deployment.md)

## Completion checklist

- [x] Application, session, driver, executor, cluster manager, task, and attempt explained
- [x] Ownership, deployment, failure, security, capacity, observability, and publication addressed
- [x] Local evidence distinguished from cluster evidence
- [ ] Lifecycle, executor-loss, driver-loss, side-effect, and capacity evidence run

