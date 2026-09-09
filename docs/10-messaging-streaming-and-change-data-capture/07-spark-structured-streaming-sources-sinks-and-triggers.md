# Spark Structured Streaming Sources, Sinks, and Triggers

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: PySpark / Spark SQL / Structured Streaming / Platform  
> Data scale: Local Spark fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Spark Structured Streaming models an incoming stream as an incrementally changing
table and executes a DataFrame/SQL plan repeatedly or continuously according to
supported engine modes. Sources define readable progress and replay behavior;
stateful operators define retained state; output modes describe which changed rows
are emitted; triggers govern when progress is attempted; sinks define commit and
duplicate behavior; checkpoints bind the query to recoverable state and offsets.

The same DataFrame vocabulary as batch is useful, but not every batch operation is
valid or bounded on an unbounded table. A successful micro-batch also does not
prove an arbitrary sink side effect is exactly once.

## Learning objectives

- Map an incremental-table query to sources, plan, state, trigger, sink, and checkpoint.
- Choose output mode and sink behavior from result/update semantics.
- Configure explicit schemas, event time, watermarks, and bounded source rates.
- Use query progress, plans, and state metrics to diagnose latency and correctness.
- Test restart, replay, checkpoint compatibility, and deployment on real integrations.

## Prerequisites

- All earlier guides in this area
- [DataFrames, Spark SQL, schemas, and types](../09-apache-spark-and-distributed-computation/02-dataframes-spark-sql-schemas-and-types.md)
- [Testing, tuning, failure diagnosis, and deployment](../09-apache-spark-and-distributed-computation/08-testing-tuning-failure-diagnosis-and-deployment.md)

## Mental model and terminology

```text
source offsets/files
       |
incremental logical plan -> physical tasks -> optional state store
       |                                      |
       +-------- trigger/batch epoch ---------+
                         |
               sink commit + checkpoint
                         |
                  query progress event
```

A streaming DataFrame resembles a lazy Kotlin `Flow` because transformations are
declared before execution. The analogy stops because Spark plans relational work
across executors, treats a streaming query as a long-lived application, maintains
distributed state, and recovers from durable source/checkpoint metadata.

| Term | Meaning in this guide |
| --- | --- |
| Incremental table | Conceptual relation updated as new source data becomes available |
| Trigger | Policy controlling when the engine attempts processing |
| Micro-batch | Bounded input interval processed as one query epoch |
| Output mode | Whether a trigger emits appended, updated, or complete result rows where supported |
| Checkpoint location | Query-specific durable recovery metadata/state path |
| Query progress | Engine report of rates, offsets, watermark, state, timing, and sink progress |
| `foreachBatch` | User callback over a micro-batch DataFrame and epoch ID; sink semantics remain the callback's responsibility |

## Requirements, assumptions, and invariants

Reference query consumes validated product events from Kafka, deduplicates stable
event IDs under a bounded policy, computes five-minute product metrics and
30-minute-gap sessions, and writes versioned upserts. Assumptions: 500/s burst,
16 source partitions, 15-minute freshness, 30-minute lateness, and 35% hot tenant.

- Source schema, timezone, starting-position policy, and data-loss behavior are explicit.
- One production query owns one durable checkpoint path; tests and backfills use isolated paths.
- Output keys include metric definition/window identity and support updates/corrections.
- Source rate bounds limit bytes as well as records where the connector permits; downstream capacity remains finite.
- Watermark/TTL policy is attached to the correct event-time column and stateful operation.
- `foreachBatch` effects are idempotent by epoch/effect identity before offsets may advance.
- A checkpoint resumes only compatible code, plan, configuration, and source/sink contracts proven by tests.
- Query success is gated by data-quality reconciliation and sink visibility, not input rate alone.

## Planned PySpark model

```python
from pyspark.sql import DataFrame, SparkSession, functions as F
from pyspark.sql.types import StructType

def build_metrics(events: DataFrame) -> DataFrame:
    valid = (
        events
        .filter(F.col("event_id").isNotNull())
        .filter(F.col("event_time").isNotNull())
        .withWatermark("event_time", "30 minutes")
        .dropDuplicatesWithinWatermark(["tenant_id", "producer_id", "event_id"])
    )
    return (
        valid
        .filter(F.col("event_type") == "product_viewed")
        .groupBy(
            "tenant_id",
            "product_id",
            F.window("event_time", "5 minutes").alias("event_window"),
        )
        .count()
    )

def start_query(spark: SparkSession, schema: StructType, checkpoint: str):
    raw = (
        spark.readStream.format("kafka")
        .option("subscribe", "product-events-v1")
        .load()
    )
    # Planned parsing splits valid and rejected records before this function.
    events = parse_declared_event_schema(raw, schema)
    metrics = build_metrics(events)
    return (
        metrics.writeStream
        .outputMode("update")
        .option("checkpointLocation", checkpoint)
        .foreachBatch(write_idempotent_metric_batch)
        .trigger(processingTime="30 seconds")
        .start()
    )
```

This is a design sketch, not executed repository code. Exact availability and
restrictions of APIs such as watermark-bounded deduplication must be verified for
the pinned Spark version. Parsing must decode Kafka bytes with an explicit schema,
preserve topic/partition/offset, and route invalid data safely. `foreachBatch`
must use its epoch plus stable row identity to make retries converge.

## Sources and starting positions

| Source | Progress identity | Key risk |
| --- | --- | --- |
| Kafka | Topic/partition/offset | Retention expiry, key/partition changes, permissions |
| Files | Discovered immutable file identity | Partial/mutable files, listing scale, cleanup |
| Table/change feed | Snapshot/version/commit | Retention, schema/table-format compatibility |
| Rate/test source | Synthetic engine progress | Does not prove real source behavior |

Starting at latest is an explicit data-loss choice for history, not a safe recovery
default. On restart with a valid checkpoint, source options may not override the
stored progress. Test the exact source contract, offset-loss setting, and retention
failure rather than assuming configuration names imply behavior.

## Output modes, triggers, and sinks

| Requirement | Candidate | Important limit |
| --- | --- | --- |
| Final append-only rows | Append mode where the plan can prove final rows | Stateful queries may wait for watermark/finality |
| Revisable aggregates | Update/upsert sink | Sink key and idempotency required |
| Entire result each trigger | Complete mode | Output grows with total state; rarely scalable |
| Custom transactional write | `foreachBatch` | Callback owns retries, cache, side effects, and atomicity |
| Drain currently available bounded input | Available-now style trigger if supported | Still requires checkpoint/sink semantics |

A processing-time trigger sets an attempt cadence, not an end-to-end latency
guarantee. If one batch takes longer than the interval, batches do not create
infinite parallel capacity; progress falls behind. Select trigger from workload,
sink cost, freshness, and checkpoint overhead measurements.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior |
| --- | --- | --- | --- |
| Kafka source | Bytes plus topic/partition/offset | Messaging owner | Retain/replay within policy |
| Parser/validator | Typed event or protected rejection | Data contract owner | Per-record disposition |
| Spark plan/state | Deterministic incremental table | Pipeline owner | Retry/restore checkpoint |
| Checkpoint storage | Query topology, offsets, state | Spark/platform owner | Stop on corruption/incompatibility |
| Sink | Idempotent/transactional row effects | Dataset/sink owner | Reconcile epoch/frontier |
| Serving consumer | Versioned metric/session semantics | Product/analytics owner | Read declared freshness/finality |

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Invalid Kafka value | Parse/schema quality result | Quarantine safe metadata; preserve source position |
| Executor loss | Task/stage failure | Spark retries pure work; verify in multi-worker test |
| Driver/query loss | Query termination/no progress | Restart same compatible query/checkpoint |
| Checkpoint corrupt/incompatible | Restore error or semantic mismatch | Preserve evidence; prior checkpoint or isolated replay |
| `foreachBatch` fails after partial writes | Epoch ledger and sink reconciliation | Idempotent retry/transaction; no blind offset reset |
| Kafka offset expired | Source offset-range failure | Stop and rebuild from authoritative retained source/snapshot |
| Watermark/state stalls | Progress/state/watermark metrics | Inspect skew, idle input, bad times, sink/backpressure |
| Bad release | Canary result/plan/state regression | Stop, restore compatible version or rebuild isolated state |

## Security, privacy, and governance

Use least-privilege Spark driver/executor identities for Kafka, checkpoint storage,
catalog, sink, and quarantine. Keep secrets in platform facilities, not options or
plans. Restrict Spark UI/history/event logs, query progress, checkpoint/state data,
and exception samples. Validate untrusted bytes before expansion and prohibit
arbitrary deserialization. Exercise deletion across input retention, state,
checkpoints, sink versions, spill, event logs, and backups.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Pure reference | Hand-calculated bounded fixture | Exact dedupe/window/session results | Pending |
| Local Spark | Memory/file sources with manual clock where possible | Schema, output mode, watermark, restart semantics | Pending |
| Kafka integration | Real pinned Kafka source and Spark connector | Offsets, keys, retries, retention behavior | Pending |
| Sink integration | Real database/table sink | Idempotent retry and atomic visibility | Pending |
| Checkpoint/fault | Kill driver/executors around state/sink commits | Exact recovered result/frontier | Pending |
| Plan/progress | Capture analyzed plan and progress JSON | Operators, state, offsets, rates explained | Pending |
| Load/skew | Representative widths, keys, lateness, sink latency | Freshness/recovery/resource/cost budgets hold | Pending |

## Debugging guide

Capture query/run ID, source offsets per partition, batch/epoch ID, input and
processed rows/s, trigger phase durations, watermark, state rows/bytes, dropped-late
counts where exposed, task/shuffle/skew metrics, checkpoint errors, and sink
transactions. Inspect both initial and runtime-adapted physical plans as applicable.
Do not infer correctness from `isActive`; reconcile source positions, dispositions,
state, and sink results.

## Common pitfalls

### Pitfall: reusing or deleting a checkpoint to fix startup

Reuse can bind unrelated queries; deletion discards the recovery frontier and may
duplicate or skip effects. Preserve it, diagnose compatibility, and rebuild into
an isolated checkpoint/sink when necessary.

### Pitfall: assuming `foreachBatch` is exactly once

The callback can run again after failure. Use epoch and stable row/effect identity,
a real sink transaction or idempotent write, and crash tests.

### Pitfall: using input rows/second as health

Zero input can be healthy or disconnected; high input can coexist with stale
output. Monitor source frontier, watermark, state, sink progress, quality, and
consumer freshness.

## Performance, capacity, and cost

Measure admission delay, batch duration by phase, scheduling/tasks, input/output
records and bytes, source lag, shuffle, spill, state rows/bytes, checkpoint time/
bytes, sink latency, late/update amplification, executor CPU/memory/GC, files/
requests, replay speed, and cost. Tune one evidenced bottleneck while holding
input and expected result fixed. Maintain catch-up and executor-loss headroom.

## Compatibility, migration, backfill, and delivery

Pin Spark, Python, JVM, connector, source, state-store, and sink combinations.
Changes to query name/ID, checkpoint path, source subscription, key, stateful
operator, schema, watermark, output mode, or sink can be recovery migrations.
Canary with a new group/checkpoint/sink from a shared frontier, compare closed
windows, cut over serving metadata, and retain rollback input/output. Never let a
backfill accidentally join the live group or share its checkpoint.

## Engineering tradeoffs

| Decision | Prefer when | Cost/risk |
| --- | --- | --- |
| Micro-batch | Broad source/sink support and throughput | Per-trigger latency and commit overhead |
| Update/upsert | Results revise with late data | Sink identity and correction semantics |
| Append/final | Immutable closed results required | Delayed visibility and plan restrictions |
| `foreachBatch` | Custom batch sink logic is needed | User owns idempotency, caching, and errors |
| Stream-batch rebuild comparison | Strong reconciliation needed | Additional compute/storage |

## Working example

- PySpark: planned explicit-schema Kafka parser, watermark/dedupe, window/session metrics, and idempotent sink
- Tests/data: planned local and real Kafka fixtures with duplicates, lateness, skew, corruption, and restart
- Infrastructure: planned Kafka, checkpoint store, sink, multi-worker Spark, and fault injection
- Try it: no command yet; no Spark/Kafka dependency is installed for Area 10
- Evidence: documentation review only
- Remaining risk: all real-engine source, watermark, state, checkpoint, sink, failure, load, and cost behavior

## Knowledge check

1. Trace source offsets through one micro-batch, state update, sink write, and checkpoint.
2. Choose an output mode for late-updating window metrics and specify the sink key.
3. Predict a retry after `foreachBatch` writes but throws before completion.
4. Diagnose an active query whose watermark and sink frontier do not advance.
5. Design a real Kafka plus sink restart/fault test.
6. Plan a stateful-query upgrade that cannot reuse its old checkpoint.

## Key takeaways

- Structured Streaming is an incremental table plan with explicit source, state, trigger, sink, and checkpoint contracts.
- Output mode describes emitted changes; it does not supply sink idempotency.
- `foreachBatch` is a powerful boundary whose user code owns retry correctness.
- Plans and query progress must be reconciled with source and sink frontiers.
- Stateful changes and checkpoint reuse require version-specific migration evidence.

## Resources

- [Apache Spark 4.2.0 Structured Streaming guide](https://spark.apache.org/docs/4.2.0/streaming/index.html) (reviewed 2026-09)
- [Apache Spark 4.2.0 Kafka integration guide](https://spark.apache.org/docs/4.2.0/streaming/structured-streaming-kafka-integration.html) (reviewed 2026-09)
- [Apache Spark 4.2.0 Structured Streaming migration guide](https://spark.apache.org/docs/4.2.0/streaming/ss-migration-guide.html) (reviewed 2026-09)
- [Apache Spark 4.2.0 monitoring](https://spark.apache.org/docs/4.2.0/monitoring.html) (reviewed 2026-09)

## Related topics

- [Stateful stream processing, checkpoints, and replay](06-stateful-stream-processing-checkpoints-and-replay.md)
- [CDC streaming pipelines, schema evolution, and operations](08-cdc-streaming-pipelines-schema-evolution-and-operations.md)

## Completion checklist

- [x] Incremental tables, sources, sinks, triggers, modes, checkpoints, plans, and progress explained
- [x] Failure, security, quality, state, capacity, compatibility, deployment, and operations addressed
- [ ] Local Spark, Kafka, sink, checkpoint, fault, plan/progress, load, and upgrade evidence run
