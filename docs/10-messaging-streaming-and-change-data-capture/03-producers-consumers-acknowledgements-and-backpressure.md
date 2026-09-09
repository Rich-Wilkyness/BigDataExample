# Producers, Consumers, Acknowledgements, and Backpressure

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Messaging / Kafka / Streaming ingestion / Operations  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Producers convert application work into bounded records and wait for a declared
acknowledgement. Consumers fetch bounded batches, process them, and expose safe
progress. Backpressure is the chain of signals and limits that prevents a slow
broker, processor, state store, or sink from turning temporary overload into
unbounded memory, latency, retry traffic, or data loss.

Acknowledgements are local facts: a producer acknowledgement can prove a broker
accepted a record under configured durability, while a consumer offset can prove
a restart position. Neither alone proves a dashboard, database, or external API
reflects the business outcome.

## Learning objectives

- Define acknowledgement boundaries from producer through sink.
- Batch by count, encoded bytes, expanded bytes, and time without unbounded memory.
- Apply backpressure using finite in-flight work, pause/resume, quotas, and shedding.
- Design graceful consumer drain, retry, and poison-record behavior.
- Diagnose lag as a rate, capacity, dependency, or skew problem.

## Prerequisites

- [Kafka topics, partitions, offsets, and consumer groups](02-kafka-topics-partitions-offsets-and-consumer-groups.md)
- [Event ingestion, batching, and backpressure](../06-data-ingestion-and-source-integration/06-event-ingestion-batching-and-backpressure.md)
- [Resource scheduling, backpressure, and capacity](../08-distributed-systems-foundations/08-resource-scheduling-backpressure-and-capacity.md)

## Mental model and terminology

Android coroutine cancellation and bounded channels help reason about local
ownership: admission should fail or suspend before memory becomes unsafe, and
shutdown should stop new work before draining. The analogy stops at remote
acknowledgements: timeout means an unknown outcome, brokers can retain work, and
process restart may redeliver records.

```text
producer queue -> serialize/batch -> broker in-flight -> broker ack
                                                    |
consumer poll <- fetch buffer <- partition log -----+
     |
bounded workers -> sink transaction -> safe offset/checkpoint

Every arrow has: byte/count bound, timeout, retry owner, and metric.
```

| Term | Meaning in this guide |
| --- | --- |
| Acknowledgement | Evidence that one named boundary accepted/completed work |
| In-flight | Admitted work without its promised terminal acknowledgement |
| Backpressure | Feedback that slows or bounds upstream admission |
| Load shedding | Intentional rejection/degradation before unsafe exhaustion |
| Lag | Difference between a source frontier and consumer progress, measured in a declared unit |
| Poison record | Deterministically failing or resource-abusive record |
| Drain | Stop admission, settle or persist admitted work, commit safe progress, then close |

## Requirements, budgets, and invariants

Assume 500 events/s burst, 256 KiB maximum encoded record, p95 producer durable
acknowledgement under 500 ms, 15-minute end-to-end freshness, 16 partitions, and
one-hour producer retry. Define limits for producer queued bytes, batch bytes/count/
age, requests in flight, consumer fetch bytes, poll records, per-partition work,
worker concurrency, sink transactions, retry attempts, and drain time.

- Admission reserves both record and byte capacity before accepting work.
- Batches close on the first count, encoded-byte, expanded-byte, or age limit.
- A timeout produces an unknown outcome unless the protocol proves rejection.
- Retries reuse stable event identity and consume a bounded attempt/deadline budget.
- Consumers do not advance durable progress past irreproducible effects.
- Partition-local work completes or is discarded before revoked ownership is released.
- Poison handling cannot silently convert invalid input into success or block a partition forever.
- Shutdown has an observable finite state machine and never reports success with volatile accepted work.

## Producer path

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SendRequest:
    event_id: str
    partition_key: bytes
    encoded: bytes

async def publish(request: SendRequest, budget: "Deadline") -> "Receipt":
    # Planned contract: both record and byte permits are acquired atomically.
    permit = await capacity.reserve(records=1, bytes=len(request.encoded), budget=budget)
    try:
        return await retrying_sender.send_same_identity(request, budget)
    finally:
        permit.release_when_no_longer_in_flight()
```

Serialization and validation happen before expensive admission where possible,
but the parser itself needs input and expansion limits. Batching improves request
amortization and compression at the cost of dwell time, memory, and larger retry
units. Flush by the first bound, not only record count.

Producer retry should distinguish definite rejection, definite durable success,
and unknown outcome. Retrying an unknown outcome is safe only because logical
identity or broker idempotence handles possible duplicates within its scope.

## Consumer path and drain

```text
RUNNING -> stop/pause intake -> DRAINING
        -> finish bounded work or persist retryable work
        -> commit only safe per-partition positions
        -> revoke/close -> STOPPED
                 \-> timeout -> FAILED_WITH_RECOVERY_POINT
```

Fetching 10,000 records is not bounded if one record may expand to hundreds of
MiB or if all records fan out into unconstrained futures. Bound fetched bytes,
decoded bytes, active tasks, state mutations, and sink operations. Preserve
partition order when the contract requires it; concurrency can occur across
partitions or through ordered completion.

Do not block the consumer's required liveness/poll loop behind arbitrary processing.
If processing pauses, continue the protocol-specific heartbeat behavior while
preventing additional unsafe fetch/admission, then resume when low-water marks
are reached.

## Backpressure and overload policy

| Signal | Normal response | Escalation |
| --- | --- | --- |
| Producer queued bytes high | Slow admission, form efficient batches | Reject/throttle by tenant before OOM |
| Broker request latency high | Reduce in-flight requests, backoff with jitter | Shed optional events or spool only within budget |
| Consumer work queue high | Pause affected partitions | Reduce producer/source rate or add proven capacity |
| Sink latency/throttling high | Reduce concurrency, retry retryable errors | Circuit-break and protect retention/state |
| One partition lagging | Inspect key/state/record distribution | Isolate/split key via migration, not blind scaling |
| Retry rate high | Stop multiplicative attempts | Quarantine deterministic failures; enforce budget |

Hysteresis matters: pause at a high-water mark and resume below a lower mark so
the system does not oscillate. If upstream cannot slow, intentional rejection or
durable bounded spill is safer than pretending an infinite queue exists.

## Data flow, ownership, and trust boundaries

| Boundary | Ack meaning | Retry owner | Overload behavior |
| --- | --- | --- | --- |
| Mobile client to ingestion | HTTP/API contract: rejected, volatile, or durable receipt | Client within age/attempt budget | Throttle/reject before acceptance |
| Producer client to broker | Broker acceptance under selected acknowledgement config | Producer library/application | Bound queue/in-flight; fail request |
| Broker to consumer | Fetched delivery, not completed outcome | Consumer/group | Pause fetch/admission |
| Consumer to state/sink | Applied transaction or idempotency receipt | Pipeline | Backoff/circuit/quarantine |
| Processor progress | Recoverable next offsets/checkpoint | Pipeline/platform | Block progress if effect uncertain |

## Failure model and recovery

| Failure | Detection | Recovery and convergence evidence |
| --- | --- | --- |
| Response lost after broker append | Send timeout plus later duplicate ID | Retry same identity; broker/log and logical dedupe evidence |
| Producer process dies with buffered records | Missing durable receipt and startup ledger | Producer retries only work promised recoverable |
| Consumer dies mid-batch | Lease/member loss and last durable progress | Reassign and replay from committed/checkpointed position |
| Slow sink | Queue age, sink p95/p99, throttle errors | Pause, bound retries, restore drain rate above ingress |
| Poison record | Stable failure at same identity/offset | Protected quarantine or explicit stop; preserve position/disposition |
| Retry storm | Attempts/input ratio and dependency load | Shared budget, jitter, circuit breaking, source throttling |
| Shutdown timeout | Drain timer and in-flight ledger | Persist/abandon per contract; restart from proven position |

## Security, privacy, and governance

Authenticate producer and consumer identities, bind tenant claims to authorized
keys/topics, and apply quotas before expensive parsing. Treat payload buffers,
spools, retry queues, logs, dead-letter records, traces, and exception messages as
classified data. Avoid event IDs as unbounded metric labels. Bound decompression,
nesting, headers, and batch expansion to resist resource-exhaustion attacks.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Batch boundary | Exact count/byte/time and oversized cases | Never exceeds declared bounds | Pending |
| Ack crash matrix | Fail before/after send and response | Only declared retry/duplicate outcomes | Pending |
| Consumer bound | Variable-width records and slow sink | In-flight records/bytes remain bounded | Pending |
| Poison isolation | Deterministic failure among valid records | Explicit disposition; healthy progress per policy | Pending |
| Backpressure load | Burst plus sink throttling | Intentional pause/reject before resource failure | Pending |
| Drain/rebalance | Stop/revoke during active work | Safe position and no stale-owner effect | Pending |

## Debugging guide

Start with the affected consumer and oldest required partition. Compare ingress
and egress records/bytes per second, then queue age/bytes, producer request
latency, broker health, consumer poll/processing time, retry amplification, state
size, sink latency, and recent rebalances. Correlate by safe event ID hash,
partition, offset, group, assignment generation, checkpoint, and sink transaction.
Mitigation is complete only when backlog drains, resource bounds recover, and
counts/frontiers reconcile.

## Common pitfalls

### Pitfall: asynchronous means unbounded

Launching a coroutine/future per record only moves the queue into heap and
scheduler state. Reserve bounded capacity before launch.

### Pitfall: retrying at every layer

Client, proxy, producer, consumer, and sink retries multiply load. Assign one
retry owner per boundary with a shared deadline and attempt budget.

### Pitfall: dead-letter and continue without reconciliation

A dead-letter record is a data-quality disposition, not success. Protect it,
retain lineage, alert on rates, and prove accepted + rejected = observed.

## Performance, capacity, and cost

Use rate and residence time to estimate in-flight work, then add byte width and
burst shape. Measure queue/in-flight records and bytes, batch fill/age,
serialization/compression CPU, request and processing percentiles, fetch sizes,
retry amplification, lag age, memory, network, disk/spool, sink concurrency, and
cost per million accepted events/reprocessed events. Test steady, burst, skew,
large-record, dependency-slow, and failure-recovery cases.

## Compatibility, migration, and tradeoffs

Producer and consumer releases overlap. Use additive schemas, tolerant readers,
bounded dual processing, canary groups, and pinned client/broker compatibility.
Changing batch, acknowledgement, retry, key, or poison policy is a behavioral
migration requiring fault tests and reconciliation.

| Choice | Prefer when | Tradeoff |
| --- | --- | --- |
| Larger batches | Throughput dominates and latency/memory budget permits | Dwell, retry amplification, tail latency |
| More in-flight requests | Network latency is limiting and ordering permits | Memory and uncertainty on failure |
| Pause/resume | Upstream log safely retains backlog | Freshness and retention consumption |
| Reject/shed | No safe capacity remains | Explicit loss/degradation contract required |

## Working example

- Python: planned byte-aware batcher, bounded worker pool, retry budget, and drain state machine
- Tests/data: planned boundary, variable-width, poison, timeout, sink-slow, and shutdown fixture
- Infrastructure: planned Kafka producer/consumer integration and network fault injection
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: client buffering, broker acks, heartbeat behavior, real sink pressure, and load cost

## Knowledge check

1. Name each acknowledgement boundary from mobile producer to metric table.
2. Predict memory behavior for count-only batching with one huge decoded record.
3. Diagnose rising lag when consumer CPU is idle but sink p99 rises.
4. Design high/low-water backpressure for a bounded work queue.
5. Assign retry ownership and a shared deadline across three network hops.
6. Specify safe shutdown when a rebalance begins during sink writes.

## Key takeaways

- Every acknowledgement proves only one named boundary.
- Bound records, bytes, age, concurrency, attempts, and time together.
- Backpressure is an end-to-end capacity contract, not just a client setting.
- Timeouts create unknown outcomes; stable identity and reconciliation resolve them.
- Graceful shutdown and rebalance are correctness paths.

## Resources

- [Apache Kafka 4.3 producer configuration](https://kafka.apache.org/43/configuration/producer-configs/) (reviewed 2026-09)
- [Apache Kafka 4.3 consumer configuration](https://kafka.apache.org/43/configuration/consumer-configs/) (reviewed 2026-09)
- [Reactive Streams specification](https://www.reactive-streams.org/) (reviewed 2026-09)

## Related topics

- [Delivery semantics, ordering, idempotency, and transactions](04-delivery-semantics-ordering-idempotency-and-transactions.md)
- [Stateful stream processing, checkpoints, and replay](06-stateful-stream-processing-checkpoints-and-replay.md)

## Completion checklist

- [x] Producer, consumer, batching, acknowledgement, retry, backpressure, poison, lag, and shutdown contracts explained
- [x] Failure, security, quality, capacity, compatibility, and operations addressed
- [ ] Batcher, consumer, Kafka, backpressure, drain, fault, and load evidence run
