# Event Ingestion, Batching, and Backpressure

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Event endpoints / Brokers / Streaming ingestion  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Event ingestion accepts an open-ended stream while keeping producer latency,
platform capacity, and durability within explicit bounds. Batching and compression
improve efficiency; admission control and backpressure prevent those optimizations
from becoming unbounded queues, memory pressure, or retry storms.

This guide covers envelopes, batches, compression, admission, acknowledgements,
and overload. Stateful windows and stream processing are deferred to area 10.

## Learning objectives

- Define event and delivery identity, acknowledgement, and ordering scope.
- Choose batch bounds using count, bytes, and time together.
- Propagate backpressure or reject load before queues become unsafe.
- Recover from partial batches, producer retries, broker failure, and poison input.
- Relate throughput, latency, compression, and durability tradeoffs to evidence.

## Prerequisites

- [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md)
- Bounded concurrency/resource lifetime from area 02 and event identity from area 05

## Mental model and terminology

An ingestion endpoint is a finite-capacity queueing system, not a function that
can always accept another coroutine. Kotlin `Flow` backpressure is a helpful model
inside one process; it stops at network clients and brokers that may buffer,
disconnect, redeliver, or acknowledge independently.

| Term | Meaning in this guide |
| --- | --- |
| Event envelope | Versioned routing, identity, time, schema, and trace metadata around a payload |
| Micro-batch | Bounded group formed for transport or storage efficiency |
| Admission control | Decision to accept, delay, shed, or reject before exhausting capacity |
| Backpressure | Feedback that slows upstream production or bounds outstanding work |
| In-flight | Accepted work not yet at its promised acknowledgement boundary |
| Poison event | Input that repeatedly fails deterministically or consumes excessive resources |

## Requirements, assumptions, and invariants

Reference load: 3M events/day (~35/second average), 500/second burst, 256 KiB
maximum encoded event, p95 acknowledgement under 500 ms, 15-minute raw freshness,
and one-hour bounded producer replay. Design capacity uses bursts and payload
percentiles, not averages.

Invariants:

- Acknowledgement meaning is explicit: accepted to volatile queue, durable receipt, or downstream publication.
- In-flight events and bytes have hard bounds; overload is observable and intentional.
- A batch is bounded by record count, encoded bytes, expanded bytes, and age.
- One invalid event cannot corrupt or indefinitely retry an otherwise valid batch.
- Producer retry identity survives rebatching, compression, and transport partitions.
- Ordering claims name the key/partition scope; global event-time order is not implied.
- Shutdown stops admission, drains or persists accepted work, then closes resources.

## Envelope, batch, and acknowledgement

```json
{
  "event_id": "producer-stable-id",
  "event_type": "product_viewed",
  "schema_version": 2,
  "producer_id": "android-app",
  "event_time": "2026-09-07T12:00:00Z",
  "tenant_id": "t1",
  "trace_id": "safe-correlation-id",
  "payload": {"product_id": "p7"}
}
```

Batch on the smaller of count/byte limits or a maximum dwell time. Validate
envelope/security bounds before expensive decompression or parsing. Persist batch
and per-record identity/disposition before returning a durable acknowledgement.
If the response is lost, producers retry the same event IDs.

```python
async def submit(event: bytes) -> Ack:
    reservation = await admission.reserve(encoded_bytes=len(event))
    try:
        return await durable_batcher.append(event, reservation)
    finally:
        reservation.release_if_uncommitted()
```

The planned implementation needs bounded wait/deadlines, cancellation-safe
reservations, durable spool behavior, and precise response-loss semantics.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Producer | Stable event ID, versioned bounded envelope | Producer | Retry same ID within retention/budget | Untrusted |
| Edge/admission | Auth, size, quota, capacity | Ingestion service | Reject/throttle before acceptance | Security boundary |
| Batcher/spool | Bounded accepted deliveries | Ingestion owner | Flush by bytes/count/age; recover spool | Internal uncommitted state |
| Durable raw/broker | Receipt/partition/offset | Platform owner | Acknowledge per configured durability | Receipt evidence |
| Validator/quarantine | Per-event disposition | Contract owner | Isolate poison events | Validated boundary |

## Ordering, time, identity, and consistency

Event time is producer-observed domain time; ingestion time measures pipeline lag;
batch flush time is an implementation detail. Retain all three where needed.
Network arrival, batch order, and broker offset do not repair a wrong device clock.

Use source-scoped `event_id` for logical deduplication and a delivery/receipt ID for
transport diagnostics. Preserve partition key and offset where applicable. Keyed
partitioning can order one entity's deliveries but may create hot partitions and
does not provide global time order.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Response lost after durable commit | Producer retries same event ID | Return prior/new receipt; downstream deduplicates |
| Crash with volatile batch | Accepted-not-durable ledger gap | Do not promise durable ack before commit; recover spool if promised |
| One malformed event in batch | Per-record validation/disposition | Quarantine record, not whole batch unless atomic contract requires |
| Sink/broker slows | Queue age/depth and publish latency | Reduce admission, spill only within budget, reject explicitly |
| Retry storm | Attempt/duplicate rate and client cohort | Backoff/jitter, quotas, circuit/load shedding |
| Oversized/compression bomb | Encoded/expanded/ratio bounds | Reject before resource exhaustion; safe diagnostics |
| Hot key/partition | Per-partition lag/skew | Revisit key/partition capacity without breaking required order |
| Shutdown/cancel | In-flight gauge and drain timeout | Stop admission; drain, persist, or fail accepted work per contract |

Recovery completes when every accepted event has a durable receipt or explicit
failure allowed by the acknowledgement contract and backlog returns within SLO.

## Security, privacy, and governance

Authenticate producer and tenant, authorize event types, validate tenant binding,
rate-limit by bounded identities, and prevent one tenant from exhausting shared
capacity. Bound envelopes before decompression, reject unsafe encodings, rotate
keys, encrypt transport/storage, and avoid payloads or high-cardinality IDs in
metrics. Data minimization begins in the producer schema; raw, spool, quarantine,
broker retention, samples, and traces all inherit classification/deletion duties.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Batch boundaries | Empty, exact count/bytes, timer, oversized record | Bounds and flush semantics hold | Pending |
| Ack crash matrix | Fail before/during/after durable commit and response | No acknowledged unexplained loss | Pending |
| Backpressure/load | Sweep rate, size, concurrency, sink latency | Memory/in-flight bounded; overload explicit | Pending |
| Poison isolation | Malformed and expansion-bomb events in valid batch | Safe per-record outcome | Pending |
| Ordering/retry | Keyed events, disconnect, rebatch, redelivery | Stated order holds; logical result deduplicates | Pending |
| Drain/restart | Cancel with queued/in-flight work | Contractual drain or recovery completes | Pending |

Local async tests cannot establish broker replication, distributed ordering, or
network behavior. Real broker/service integration and fault/load tests are needed.

## Common pitfalls

### Pitfall: unbounded queue absorbs bursts

It converts overload into memory growth and delayed failure. Reserve finite
records/bytes before accepting and propagate delay or rejection.

### Pitfall: batching only by record count

Payload sizes vary; one batch can exceed memory/request limits. Bound encoded and
expanded bytes as well as count and age.

### Pitfall: acknowledging receipt into process memory

A crash loses events the producer believes durable. Either document volatile
acceptance or acknowledge only after the promised durable boundary.

## Performance, capacity, cost, and operations

Use Little's Law as a diagnostic estimate: in-flight work is arrival rate times
time in system when the system is stable. Measure accepted/rejected events and
bytes, payload percentiles, compression ratio/CPU, batch fill/age, queue depth in
records/bytes, publish and acknowledgement percentiles, partition skew, retries,
duplicates, errors, and end-to-end lag. Load tests sweep rate, size distribution,
burst length, sink latency, and failure—not only steady small messages.

Alerts distinguish approaching saturation, active shedding, stalled partitions,
oldest accepted event, spool capacity, acknowledgement failure, and SLO burn. The
runbook stops admission before durability is threatened, preserves accepted work,
and calculates whether drain capacity exceeds incoming rate.

## Compatibility, migration, and tradeoffs

Version envelopes and payloads separately, accept compatible old/new versions,
shadow-validate new rules, and migrate producers before removing old support.
Changing partition keys can reorder a logical entity; use a versioned stream,
drain/cutover boundary, and reconciliation.

| Requirement | Prefer | Tradeoff |
| --- | --- | --- |
| Low event latency | Small batches/short dwell | More requests and compression overhead |
| High throughput/cost efficiency | Larger bounded compressed batches | Higher latency and retry scope |
| Strong producer confirmation | Ack after replicated durable receipt | Higher latency and dependency coupling |
| Graceful overload | Bounded admission plus explicit retry signal | Producers must implement retry/buffering |

## Working example

- Python/tests: planned bounded async batcher, durable fake sink, producer retry client, and load/fault harness
- Expected result: memory stays bounded and acknowledged inputs converge across failures
- Scale represented: none yet; local and distributed evidence pending
- Remaining risk: broker durability, tenant fairness, partition skew, and production burst shape

## Knowledge check

1. Define the exact promise made by a durable acknowledgement.
2. Predict queue behavior when arrival remains above service capacity.
3. Diagnose why a 1,000-record batch can still exhaust memory.
4. Design producer retry after a response timeout.
5. Estimate in-flight events at 500/second and two-second residence time.
6. Plan a partition-key migration without silently reordering entity events.

## Key takeaways

- Capacity is finite; backpressure and admission make overload explicit.
- Batch by bytes, count, and time, with expanded-input bounds.
- Acknowledgement must name its durability boundary.
- Logical identity survives transport retries and rebatching.
- Throughput, latency, durability, fairness, and cost require measured tradeoffs.

## Resources

- [Reactive Streams specification](https://www.reactive-streams.org/) (reviewed 2026-09)
- [Apache Kafka documentation: Design](https://kafka.apache.org/documentation/#design) (reviewed 2026-09)

## Related topics

- [Change data capture logs and connectors](05-change-data-capture-logs-and-connectors.md)
- [Validation, quarantine, and schema evolution](07-validation-quarantine-and-schema-evolution.md)
- [Idempotency, deduplication, late data, and reconciliation](08-idempotency-deduplication-late-data-and-reconciliation.md)

## Completion checklist

- [x] Envelopes, batching, compression, admission, acknowledgements, and overload explained
- [x] Ordering, security, failure, capacity, operations, migration, and evidence addressed
- [ ] Batcher, ack/restart, poison, backpressure, broker, and load evidence run
