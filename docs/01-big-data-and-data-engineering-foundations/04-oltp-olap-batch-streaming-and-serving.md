# OLTP, OLAP, Batch, Streaming, and Serving

> Status: Documentation complete  
> Level: Beginner  
> Applies to: Generic data engineering / SQL / Batch / Streaming / Storage  
> Data scale: Local fixture through distributed production estimate  
> Example status: Complete decision walkthrough  
> Evidence status: Requirement and boundary review  
> Last reviewed: 2026-09

## Overview

OLTP and OLAP describe workload shapes. Batch and streaming describe how work is
bounded and triggered. Serving describes how results are exposed to consumers.
They are independent dimensions: an analytical result can be recomputed daily in
batch, updated continuously from a stream, and served from a low-latency store.

The durable skill is matching workload guarantees to system boundaries. This
guide does not equate any category with one database or claim that a system has
only one workload.

## Learning objectives

After completing this guide, you should be able to:

- Compare transactional and analytical workloads by operations and guarantees.
- Explain bounded batch versus conceptually unbounded stream processing.
- Separate processing latency from consumer-serving latency and freshness.
- Choose a simple mode from requirements and identify hybrid boundaries.
- Diagnose damage caused by mixing incompatible workloads without isolation.

## Prerequisites

Read [Volume, velocity, variety, and when data becomes big](03-volume-velocity-variety-and-when-data-becomes-big.md).

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| OLTP | Transaction-oriented workload with small, selective reads/writes and integrity under concurrency |
| OLAP | Analytical workload scanning or aggregating many records, often across history |
| Batch | Processing a finite input set with declared boundaries |
| Streaming | Continuously processing an input that is not naturally complete |
| Serving layer | Consumer-facing representation optimized for its access and service contract |
| Materialized view | Stored result derived from other data and maintained or recomputed under a freshness contract |

## Requirements, scale assumptions, and invariants

The product dashboard needs screen counts by app version for the prior UTC day,
available by 09:00 local business time. It tolerates a documented correction the
next day. The application transaction path must not slow materially when an
analyst scans event history. A future operations consumer might require five-
minute estimates, but that is not a current requirement.

Invariants:

- Analytical reads never mutate source transactions.
- Every batch declares input boundaries and output grain.
- Streaming state declares identity, time domain, ordering scope, and lateness policy.
- Serving exposes a complete version and explicit freshness.
- A faster pipeline may not silently weaken correctness or privacy.

## Mental model

| Dimension | Question | Common choices |
| --- | --- | --- |
| Workload | What operations and concurrency dominate? | OLTP, OLAP, mixed with isolation |
| Processing | When is input considered and output updated? | Batch, micro-batch, continuous streaming |
| Serving | How do consumers access results? | Files/tables, warehouse SQL, API, cache/index |

Room is a useful OLTP analogy: small indexed transactions preserve app state,
while a report over years of telemetry is an analytical scan. The analogy stops
because a production analytical system may partition and replicate data across
many machines and accept deliberately stale snapshots.

## Workload comparison

| Property | OLTP-shaped | OLAP-shaped |
| --- | --- | --- |
| Typical operation | Point lookup or small read/write set | Scan, join, aggregate, rank over many rows |
| Concurrency | Many short independent transactions | Fewer resource-intensive queries/jobs |
| Data orientation | Current operational state | Historical events, snapshots, derived models |
| Correctness focus | Constraints and transactional isolation | Stable grain, reproducible logic, snapshot consistency |
| Physical optimization | Indexes, normalized writes, low contention | Column projection, partition pruning, parallel scans |
| Failure concern | Ambiguous commit, lock/contention | Partial publication, stale/incomplete input, resource contention |

These are tendencies, not definitions of specific products.

## Batch and streaming behavior

Batch makes completeness tractable by bounding input, such as
`2026-09-05T00:00Z <= event_time < 2026-09-06T00:00Z` plus a declared arrival
cutoff. It simplifies reruns and comparison, but freshness waits for schedule,
input readiness, and job duration.

Streaming updates results as records arrive. It reduces potential update delay
but must manage unbounded input, checkpoints, backpressure, state retention,
out-of-order events, and a policy for when results are “complete enough.” It does
not make network delivery immediate or globally ordered.

Micro-batching is an implementation between these operational shapes. The key
contract remains input progress, state, publication, and consumer semantics.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| OLTP source/change interface | Committed source state or event | Application owner | Protect transaction path; bounded extraction | Restricted authority |
| Raw analytical landing | Immutable accepted record | Ingestion owner | Replay/deduplicate; quarantine invalid | Restricted raw |
| Batch interval | Versioned data plus closed cutoff | Batch owner | Retry bounded range; atomic publish | Governed internal |
| Stream partition | Ordered offsets only within stated scope | Stream processor owner | Restore checkpoint; handle duplicates/lateness | Governed internal |
| Serving table/API | Versioned consumer schema and freshness | Serving/data-product owner | Serve last known good or explicit unavailable | Purpose-limited |

Do not let analytical consumers query internal OLTP tables as an undocumented
contract. Extraction must respect source load and transaction consistency.

## Choosing a mode

| Requirement | Prefer initially | Why | Reconsider when |
| --- | --- | --- | --- |
| Correct daily dashboard by 09:00 | Daily batch | Bounded completeness and simple replay | Business value requires intraday decisions |
| Alert within minutes | Streaming or frequent micro-batch | Lower update delay | False urgency does not justify state complexity |
| Historical correction | Isolated batch backfill | Bounded, comparable, controllable cost | Stream engine provides proven replay contract |
| Millisecond keyed lookup | Materialized serving store | Access shaped for consumer | Warehouse/table meets latency and concurrency |
| Ad hoc broad analysis | OLAP engine/table | Scan and aggregation isolation | Workload is actually selective operational access |

For the current scenario, daily batch plus a curated analytical table is the
smallest adequate design. Streaming is a requirement change, not a maturity badge.

## Consistency, ordering, identity, and time

OLTP commit order, broker partition order, event time, arrival time, processing
time, and publication order are different. Batch cutoff states which records
were eligible. Streaming progress states offsets/checkpoints and watermark or
lateness policy. Stable `event_id` enables deduplication in either mode, but
exactly-once effects require the source, state, and sink boundaries to cooperate.

## Failure model and recovery

| Failure | Batch behavior | Streaming behavior | Consumer contract |
| --- | --- | --- | --- |
| Duplicate input | Deduplicate within bounded run and across rerun | Stateful dedupe within declared retention | Counts do not double within scope |
| Late input | Include next correction/backfill | Update until lateness/state limit | Version/finality is explicit |
| Worker crash | Retry tasks/run from immutable input | Restore checkpoint and replay | No partial version exposed |
| Backpressure | Job exceeds window | Lag and state/queue growth | Freshness degraded visibly |
| Bad deployment | Stop, preserve old output, rerun old code | Roll back with checkpoint compatibility plan | Last known good result available if safe |
| OLAP load hits source | Source latency rises | Same if change feed/extract is unbounded | Protect operational priority |

## Security, privacy, and governance

Replicating OLTP data into analytical and serving systems expands access and
deletion scope. Select only needed fields, classify derived columns, isolate
tenants, encrypt boundaries, audit queries, and set retention for state stores,
checkpoints, caches, exports, and backups. Streaming speed must not bypass policy
or make invalid data irretractable.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Mode decision | Scenario requirements | Compare daily batch, stream, and serving choices | Daily batch is simplest sufficient mode | Passed; documented above |
| Boundary review | Paper architecture | Separate OLTP, processing, and serving ownership | Analytical load cannot directly impair source | Passed by design; not executed |
| Runtime comparison | Representative fixture and real engines | Measure freshness, replay, source load, and failures | Selected mode meets objectives | Pending |

## Debugging guide

Identify the affected workload and consumer first. For OLTP inspect transaction
latency, locks, connection pools, and query plans. For batch inspect input cutoff,
run/task states, partitions, rejects, and publication marker. For streaming
inspect offsets, lag, checkpoint/state compatibility, watermark, hot keys, and
sink commits. For serving inspect version, cache age, concurrency, and query
plans. Reconcile source identities to consumer values after repair.

## Common pitfalls

### Pitfall: streaming means real time

Streaming only changes how input is processed. End-to-end latency includes
collection, buffering, state, sink publication, cache, network, and consumer
refresh. Define a percentile objective and measure the whole path.

### Pitfall: analytics on the source database

Convenient direct queries create load and an accidental schema contract. Use a
controlled consistent extraction or replica designed for that workload.

### Pitfall: batch means obsolete

For bounded daily outcomes, batch can provide simpler completeness, replay, and
cost control. Choose from requirements, not perceived sophistication.

## Performance, capacity, cost, and operations

Batch needs enough capacity to finish within its window and recover backlog.
Streaming pays continuously for ingestion, state, checkpoints, and on-call
complexity even at low traffic. Serving systems trade compute, storage, and
freshness for predictable consumer latency. Track source load, input/output
rates, batch duration, oldest-unprocessed age, stream lag, state size, consumer
latency/concurrency, correction rate, and cost per workload.

## Compatibility, migration, backfill, and delivery

To move from batch to streaming, run both against the same versioned inputs,
define equivalent identity/time rules, compare results over late and duplicate
cases, and cut consumers over atomically. Keep batch as a bounded repair path
until streaming replay and historical correction are proven. Schema evolution
must account for stored stream state and historical batch data.

## Engineering tradeoffs

The decision is multi-dimensional. OLTP versus OLAP does not select batch versus
streaming, and processing mode does not select serving technology. Optimize the
boundary that violates a measured requirement while preserving the source of
truth and a repair path.

## Working example

The daily dashboard decision table and failure comparison are complete
conceptual evidence. SQL transformations, stream processors, and serving-engine
integration are planned in later areas.

## Knowledge check

1. Classify a payment write, daily revenue report, five-minute alert, and cached
   account summary by workload, processing, and serving dimensions.
2. Predict dashboard behavior for an event arriving after the batch cutoff.
3. Diagnose why adding a stream did not reduce dashboard freshness delay.
4. Design an isolation boundary that protects the application database.
5. Propose evidence required before replacing the batch path with streaming.

## Key takeaways

- OLTP/OLAP, batch/streaming, and serving answer different questions.
- Batch has explicit bounds; streaming needs progress, state, and lateness rules.
- Faster updates do not automatically provide stronger correctness or lower cost.
- Protect operational sources from analytical workload and accidental contracts.
- Preserve a bounded reconciliation and repair path.

## Resources

- [PostgreSQL documentation: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [Apache Beam Programming Guide: Event time and watermarks](https://beam.apache.org/documentation/programming-guide/)
- [Martin Kleppmann: Turning the database inside-out](https://martin.kleppmann.com/2015/11/05/database-inside-out-at-oredev.html)

## Related topics

- [Sources, sinks, authority, and derived data](05-sources-sinks-authority-and-derived-data.md)
- [Correctness, freshness, latency, throughput, and cost](06-correctness-freshness-latency-throughput-and-cost.md)
- [First end-to-end data pipeline](08-first-end-to-end-data-pipeline.md)

## Completion checklist

- [x] Workload, processing, and serving dimensions separated
- [x] Requirements, grain, owners, identity, time, ordering, and consistency stated
- [x] Duplicate, late, overload, failure, replay, and recovery compared
- [x] Security, performance, cost, observability, and migration covered
- [x] Decision evidence recorded and runtime evidence marked pending
- [ ] Real-engine source isolation, processing, and serving behavior verified
