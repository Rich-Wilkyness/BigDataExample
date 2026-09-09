# Event Logs, Brokers, Streams, and Tables

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Messaging / Streaming / Storage / Architecture  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A durable event log stores an ordered sequence of immutable records so producers
and consumers do not have to be available simultaneously. A broker owns delivery,
retention, partitioning, and access to that log. A stream is the continuing
logical sequence being processed; a table is keyed state as of some declared
input frontier. A materialized view is a maintained, derived table.

These are distinct contracts. A queue can delete work after one consumer handles
it; a retained log can serve many consumers and replay old positions. An
append-only log records assertions or changes, while a table answers current-state
questions. This guide covers those durable distinctions, not Kafka-specific APIs
or stream-engine syntax.

## Learning objectives

- Distinguish command queues, retained logs, streams, tables, and materialized views.
- State grain, owner, retention, ordering, and replay guarantees at each boundary.
- Derive a current table and aggregate from an append-only change sequence.
- Explain why unbounded input must still be processed with bounded resources.
- Select a transport/state model from consumer and recovery requirements.

## Prerequisites

- [OLTP, OLAP, batch, streaming, and serving](../01-big-data-and-data-engineering-foundations/04-oltp-olap-batch-streaming-and-serving.md)
- [Sources, sinks, authority, and derived data](../01-big-data-and-data-engineering-foundations/05-sources-sinks-authority-and-derived-data.md)
- [Snapshots, events, and state reconstruction](../05-data-modeling-and-business-semantics/06-snapshots-events-and-state-reconstruction.md)

## Mental model and terminology

```text
append: e0 e1 e2 e3 e4 e5 ...        retained log (history)
                 ^      ^
            consumer A  consumer B    independent positions

fold(log through offset 5, by key) -> table K -> latest value
group(log through frontier, window) -> materialized metric table
```

Room's write-ahead log is a useful analogy for ordered durable change. The analogy
stops because a data broker exposes a shared, partitioned interface to independent
applications and may retain records after every current consumer has processed
them.

| Term | Meaning in this guide |
| --- | --- |
| Record | Immutable bytes plus key, headers, timestamp, and position metadata |
| Log | Retained append sequence whose position identifies an occurrence, not necessarily a business event |
| Queue | Work distribution abstraction, often with destructive acknowledgement semantics |
| Stream | Potentially unbounded logical relation changing over time |
| Table | Keyed state observed at a declared version/frontier |
| Materialized view | Persisted derived table updated from source changes |
| Frontier | Set of source positions through which a result is complete under stated rules |

## Requirements, scale assumptions, and invariants

Assume 3M events/day, 500/s bursts, 16 partitions, 35-day replay, 15-minute
freshness, and at least two independent consumers. Size by encoded bytes and
retention replicas, not event count alone.

- Appending a delivery never mutates an earlier log position.
- Position identifies broker order; stable event identity defines logical duplicates.
- Consumers declare the positions/frontier represented by derived state.
- Retention exceeds detection plus repair plus catch-up, with margin.
- Unbounded input is handled as bounded polls/batches with finite in-flight bytes.
- A materialized view is replaceable derived state unless explicitly made authoritative.
- Replaying the same closed input with pinned logic and dependencies converges to the same result.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Producer | Stable ID, schema, key, event time | Producer team | Retry without inventing identity | Untrusted input |
| Broker/log | Bytes, partition, offset, retention | Messaging platform | Reject, replicate, retain, or expire by policy | Durable receipt boundary |
| Validator | Parsed disposition per delivery | Data contract owner | Accept or protected quarantine | Validated boundary |
| Processor | Closed input positions plus logic version | Pipeline owner | Retry/replay from checkpoint | Derived computation |
| Materialized table | Key/window grain plus frontier | Dataset owner | Versioned correction/rebuild | Consumer-facing derived state |

## From log to table

A current product table can be modeled as a fold over ordered changes. The key is
business identity; the offset only orders occurrences within its log partition.

```python
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class Change:
    tenant_id: str
    product_id: str
    version: int
    operation: str
    value: dict[str, object] | None

def materialize(
    changes: Iterable[Change],
) -> dict[tuple[str, str], tuple[int, dict[str, object] | None]]:
    # Retain a delete tombstone/version so an older update cannot resurrect it.
    table: dict[tuple[str, str], tuple[int, dict[str, object] | None]] = {}
    for change in changes:
        key = (change.tenant_id, change.product_id)
        prior = table.get(key)
        if prior is not None and change.version <= prior[0]:
            continue
        if change.operation == "delete":
            table[key] = (change.version, None)
        elif change.value is not None:
            table[key] = (change.version, change.value)
        else:
            raise ValueError("invalid change operation or missing value")
    return table
```

This bounded reference model is planned, not executed. Production state cannot
fit arbitrarily in one Python dictionary; the internal map deliberately retains
delete tombstones, while a visible current table filters entries whose value is
`None`. A distributed engine needs partitioned state, durable checkpoints,
retention, rescaling, and recovery.

SQL expresses the table at a bounded frontier when versions totally order changes:

```sql
-- ANSI-style sketch; QUALIFY support varies by engine.
SELECT product_id, version, value
FROM (
  SELECT c.*,
         ROW_NUMBER() OVER (
           PARTITION BY tenant_id, product_id
           ORDER BY version DESC, source_position DESC
         ) AS rn
  FROM product_changes AS c
  WHERE source_position <= :closed_frontier
) AS ranked
WHERE rn = 1 AND operation <> 'delete';
```

The source position must be comparable in its declared scope. `NULL` keys or
versions are contract failures rather than an accidental SQL group.

## Lifecycle, consistency, identity, and time

A record is created, serialized, appended, replicated, consumed, validated,
applied to state, checkpointed, and eventually expired. Those are separate
boundaries. Event time describes the producer's domain; append time describes
broker observation; processing time describes computation. None substitutes for
the others.

A log offers history only within retention. Compaction may retain the latest
record per key but is not a complete audit history and does not happen instantly.
A derived table is current only through its recorded frontier and lateness policy.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Duplicate append/delivery | Stable ID and duplicate counters | Idempotent apply; preserve receipt diagnostics |
| Missing/expired position | Offset-range check and retention alert | Stop; restore from authoritative snapshot/log, never skip silently |
| Partial materialization | Frontier/checkpoint mismatch | Keep prior version visible; replay candidate |
| Poison record | Validation/resource bound | Quarantine with safe metadata; advance only per policy |
| Consumer outage | Oldest-position lag | Scale/catch up before retention expires |
| Wrong transformation | Reconciliation/semantic version | Rebuild isolated state from retained input and cut over |

Recovery is complete when input positions are continuous, accepted plus rejected
deliveries reconcile to observed input, and rebuilt state matches an independent
source or bounded batch computation.

## Security, privacy, and governance

Authorize produce, consume, administration, and replay separately. Retained logs,
headers, keys, dead letters, state stores, snapshots, and backups inherit data
classification. Avoid sensitive values in topic names, keys, metrics, and logs.
Encryption does not solve over-retention; deletion must address every retained and
derived copy while preserving lawful audit needs.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Fold semantics | Empty, create, update, duplicate, stale update, delete | Exact final keyed state | Pending |
| Batch/stream equivalence | Close a frontier and compute both ways | Same sessions/metrics | Pending |
| Replay | Reset state and replay same positions | Same output and dispositions | Pending |
| Retention gap | Request an expired position | Explicit stop and rebuild path | Pending |
| Failure | Crash around state/checkpoint publication | Prior or complete new state, never mixed | Pending |

## Common pitfalls

### Pitfall: treating a broker as the source of business truth

The log is authoritative for received bytes during retention; the producer's
database may remain authoritative for current catalog state. Declare authority
per fact and retain the reconciliation route.

### Pitfall: calling every sequence a queue

Destructive work queues and replayable logs imply different fan-out, recovery,
and retention. Choose using consumer independence and rebuild requirements.

### Pitfall: assuming unbounded means infinite memory

The logical input has no end, but each poll, buffer, transaction, window, and
state key must have a finite resource and time policy.

## Performance, capacity, and operations

Measure ingress/egress records and bytes, append/fetch latency percentiles,
replication health, partition distribution, oldest consumer lag in records and
time, retention headroom, state size, checkpoint duration, replay rate, and cost.
Catch-up capacity must exceed incoming rate: if replay processes 700/s while 500/s
arrive, a 360,000-record backlog needs about 30 minutes, excluding overhead.

## Compatibility, migration, and tradeoffs

Version schemas and semantic definitions independently. New consumers can replay
or shadow from a chosen frontier; destructive retention or key changes constrain
rollback. A new partitioning scheme normally needs a new stream or explicit
drain/cutover because it changes ordering scope.

| Need | Prefer | Cost/risk |
| --- | --- | --- |
| Independent replayable consumers | Retained log | Storage, governance, lag operations |
| One worker handles each command | Work queue | Weak history/replay unless separately persisted |
| Fast current lookup | Materialized table | Staleness and rebuild contract |
| Complete historical correction | Immutable retained source plus versioned output | Retention and recomputation cost |

## Working example

- Python/SQL: planned bounded change fold and frontier query
- Data/tests: planned create/update/delete/duplicate/gap fixture and batch-stream comparison
- Infrastructure: planned broker integration in later guides
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: real retention, ordering, replication, replay rate, and storage cost

## Knowledge check

1. Explain why a broker offset is not a business event ID.
2. Derive the final table for create, update, duplicate update, and delete records.
3. Diagnose a materialized view that reports freshness but has skipped a partition.
4. Choose queue or log semantics for two independent consumers and justify retention.
5. Estimate catch-up time when replay throughput barely exceeds ingress.
6. Design a safe rebuild and cutover for a corrected metric definition.

## Key takeaways

- Logs preserve ordered occurrences; tables represent keyed state at a frontier.
- Identity, ordering, retention, and authority are separate contracts.
- Streaming processes unbounded input with bounded resources.
- Replay is useful only while inputs, schemas, logic, and side effects remain reproducible.
- Consumer-visible state must identify its completeness frontier.

## Resources

- [Apache Kafka 4.3 design documentation](https://kafka.apache.org/43/design/) (reviewed 2026-09)
- [Apache Kafka 4.3 introduction](https://kafka.apache.org/43/getting-started/introduction/) (reviewed 2026-09)

## Related topics

- [Snapshots, events, and state reconstruction](../05-data-modeling-and-business-semantics/06-snapshots-events-and-state-reconstruction.md)
- [Kafka topics, partitions, offsets, and consumer groups](02-kafka-topics-partitions-offsets-and-consumer-groups.md)

## Completion checklist

- [x] Log, queue, stream, table, materialized view, authority, and frontier explained
- [x] Identity, time, retention, security, failure, capacity, migration, and evidence addressed
- [ ] Reference fold, broker retention, replay, and batch-stream equivalence evidence run
