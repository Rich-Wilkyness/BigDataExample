# Kafka Topics, Partitions, Offsets, and Consumer Groups

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Apache Kafka / Messaging / Distributed systems / Platform  
> Data scale: Local broker fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Kafka stores a topic as partitions. Each partition is an ordered append log, and
an offset identifies one record occurrence within that partition. A consumer
group assigns each partition to at most one active member at a time so members
can divide work; separate groups consume independently.

Partitions are simultaneously units of ordering, parallelism, storage, failure,
and reassignment. More partitions can raise concurrency, but cannot repair a bad
key, provide global order, or make a slow sink infinitely scalable.

## Learning objectives

- Explain topic, partition, record key, offset, replica, and consumer-group ownership.
- Choose a partition key from ordering, locality, skew, privacy, and migration needs.
- Distinguish log end, committed offset, consumer position, and event-time progress.
- Predict rebalancing, retention, compaction, and partition-count change behavior.
- Diagnose lag and capacity per partition rather than from cluster averages.

## Prerequisites

- [Event logs, brokers, streams, and tables](01-event-logs-brokers-streams-and-tables.md)
- [Partitioning, hashing, range routing, and rebalancing](../08-distributed-systems-foundations/02-partitioning-hashing-range-routing-and-rebalancing.md)
- [Replication, consistency, quorums, and availability](../08-distributed-systems-foundations/03-replication-consistency-quorums-and-availability.md)

## Mental model and terminology

```text
topic product-events
  partition 0: [offset 0][1][2][3]  -> group A member 1; group B member 1
  partition 1: [offset 0][1][2]     -> group A member 2; group B member 1
  partition 2: [offset 0][1][2][3]  -> group A member 3; group B member 2
```

A consumer group resembles workers pulling shards from a coordinated pool. It is
not like several collectors on one `SharedFlow`: records are durable, positions
survive process death, and assignment changes must transfer progress and local
state safely.

| Term | Meaning in this guide |
| --- | --- |
| Topic | Named logical record stream with broker configuration and authorization |
| Partition | Ordered append log and assignment unit |
| Offset | Partition-local position assigned to one record occurrence |
| Key | Bytes used by a producer partitioner; also often business locality identity |
| Consumer position | Next offset a running consumer intends to fetch/process |
| Committed offset | Durable group restart point; exact interpretation depends on commit discipline |
| Lag | Distance from a chosen log frontier; records, bytes, and time answer different questions |
| Rebalance | Group assignment transition caused by membership or subscription changes |

## Requirements, assumptions, and invariants

Reference topic: 16 partitions, replication configured by the platform, 500/s
burst, 35-day replay, 35% hot-tenant possibility, maximum 256 KiB record, and two
consumer groups. The selected cluster must be benchmarked with real record widths,
compression, acknowledgement, replication, and failure settings.

- Order is claimed only within one partition and observed offset sequence.
- All events requiring relative order use a stable canonical partition key.
- A group checkpoint contains a next offset for every assigned partition.
- Committed offsets never advance past effects that the recovery contract cannot reproduce.
- Group reassignment revokes ownership before another member safely resumes it.
- Retention is independent of whether one group has consumed a record.
- Partition and replica placement leave failure headroom; all replicas on one fault domain do not provide the intended durability.

## Partition-key design

| Requirement | Candidate key | Benefit | Risk |
| --- | --- | --- | --- |
| Per-user session order | `(tenant_id, subject_id)` | Related events share partition/state | Celebrity or default subjects can be hot |
| Per-product metric locality | `(tenant_id, product_id)` | Product updates colocate | Sessions require reshuffle |
| Tenant isolation | `tenant_id` | Simple tenant ordering | One large tenant caps throughput at one partition |
| Even distribution | Stable event-ID hash | Balanced writes | No entity ordering/locality |

The reference session pipeline keys by tenant and subject. Invalid/missing subject
IDs are quarantined; mapping all missing keys to one sentinel would create both a
semantic collision and a hot partition.

Adding partitions changes common key-to-partition mappings. It does not reorder
records already in a partition, but future records for a key may land elsewhere;
cross-boundary per-key order then needs a migration protocol or new topic.

## Offsets, commits, and rebalances

The safe handoff sequence is contract-dependent:

```text
poll records -> process/apply -> durably record effect + next offsets
             -> expose/commit progress -> revoke/drain on reassignment
```

Committing before a non-idempotent effect can lose work after a crash. Applying
the effect before committing can repeat it. Later guides develop idempotency and
transactions; a group alone provides neither end-to-end outcome.

During rebalance, stop admitting revoked-partition work, finish or cancel it under
a bounded deadline, durably commit only safe progress, release partition-local
resources, and fence stale workers. A thread that continues writing after losing
ownership can corrupt state even if its network call succeeds.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Producer partitioner | Serialized key and versioned routing rule | Producer/data platform | Reject missing invalid keys | Untrusted routing input |
| Partition leader/replicas | Offset order and configured durability | Kafka platform | Failover within configured guarantees | Durable transport |
| Group coordinator | Membership and partition assignments | Kafka platform | Rebalance/rejoin | Control plane |
| Consumer member | Poll, process, checkpoint, revoke | Pipeline owner | Retry/fence/drain | Application boundary |
| Sink/state | Idempotent effect plus input frontier | Dataset owner | Reconcile/replay | Derived truth |

## Failure model and recovery

| Failure | Evidence to inspect | Recovery |
| --- | --- | --- |
| Consumer crash after effect/before commit | Effect ID and committed offset | Re-deliver and deduplicate/idempotently apply |
| Commit before effect | Offset ahead of sink frontier | Reset to proven frontier and replay |
| Rebalance thrashing | Join/leave rate, poll gaps, assignment logs | Repair timeouts/processing, static membership only if justified |
| Hot partition | Per-partition bytes, lag, processing time | Repair key/state strategy; partitions alone may not help |
| Leader/broker loss | Replica/leader and acknowledgement metrics | Fail over; verify acknowledged records under tested config |
| Offset expired | Requested offset outside retained range | Stop and rebuild/resnapshot from authority |
| Stale member writes | Assignment epoch/fence violation | Reject stale generation and replay current owner |

## Security, privacy, and governance

Use least-privilege topic/group/admin access and encrypted authenticated links.
Group IDs, topic names, keys, headers, offsets, and metrics can disclose tenancy or
business activity. Quotas should contain noisy tenants without hiding overload.
Retention, compaction, remote tiers, replicas, consumer caches, and backups all
participate in deletion and legal-hold policy.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Key routing | Golden/property cases across producer versions | Same valid key routes as declared | Pending |
| Ordering | Interleaved keyed events with retries | Offset order preserved per partition | Pending |
| Group ownership | Start/stop members during load | Every partition has one active group owner | Pending |
| Commit crash | Kill around effect and offset commit | Declared duplicate/loss behavior only | Pending |
| Retention | Pause beyond configured boundary | Alert precedes expiry; recovery path is explicit | Pending |
| Capacity | Skewed records/keys plus broker loss | SLO holds within failure headroom | Pending |

An in-memory fake cannot prove Kafka replication, coordinator, retention,
compaction, or rebalance behavior. Use a real pinned broker integration, then a
multi-broker failure environment for durability claims.

## Common pitfalls

### Pitfall: offset means event ID

A retry can append the same logical event at another offset. Preserve producer
identity and use offset for transport progress.

### Pitfall: average lag hides one stalled partition

Consumer freshness is bounded by the oldest required partition. Alert on maxima
and age, and retain partition labels within a controlled cardinality.

### Pitfall: adding consumers above the partition count

Extra members are idle for that subscription while adding coordination cost.
Scale only after identifying CPU, I/O, sink, key skew, or partition count as the
actual bound.

## Performance, capacity, and operations

Measure records/bytes by partition, request/batch size, compression, produce and
fetch latency, under-replicated/offline partitions, ISR changes, disk/network,
consumer poll and processing duration, rebalance duration, and lag in records,
bytes, and event/ingestion time. Retention capacity includes replication and a
failure/catch-up margin.

The runbook identifies the oldest partition, compares arrival with drain rate,
protects retention, checks coordinator/rebalance events, inspects the downstream
sink, and chooses scale, throttle, replay, or rebuild from evidence.

## Compatibility, migration, and tradeoffs

Pin client/broker protocol compatibility and test rolling mixed versions. Treat
partition-key, partition-count, topic, serialization, compression, and security
changes as data migrations. Shadow a new topic/group from a declared frontier,
compare outputs, cut over consumers, and retain rollback input.

| Decision | Prefer when | Cost/risk |
| --- | --- | --- |
| Fewer partitions | Low throughput and strong entity locality | Lower parallelism/failure granularity |
| More partitions | Measured balanced parallelism need | Metadata, files, connections, rebalances |
| Delete retention | Complete replay for bounded time | Storage grows with throughput |
| Compaction | Latest keyed value is useful | No instantaneous or complete history guarantee |

## Working example

- Source/tests: planned keyed producer, group consumer, assignment ledger, and lag inspector
- Infrastructure: planned pinned single-broker semantic test then multi-broker fault test
- Data: planned balanced/hot/missing-key and variable-width fixture
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: real routing, rebalance, replication, retention, skew, and upgrade behavior

## Knowledge check

1. State the strongest ordering claim for a 16-partition topic.
2. Predict group assignments for 16 partitions with 1, 8, and 20 members.
3. Diagnose zero average lag when one required partition has stopped advancing.
4. Design a partition-key migration that preserves per-subject order.
5. Explain crash behavior when an offset is committed before a sink write.
6. Estimate retention bytes including replicas and recovery margin.

## Key takeaways

- A partition is Kafka's unit of order, assignment, storage, and much scaling.
- Offsets identify deliveries and progress, not logical business identity.
- Consumer groups distribute partitions; they do not supply end-to-end atomicity.
- Rebalance is an ownership transfer that requires draining, checkpoints, and fencing.
- Per-partition tails and retention headroom matter more than averages.

## Resources

- [Apache Kafka 4.3 design](https://kafka.apache.org/43/design/) (reviewed 2026-09)
- [Apache Kafka 4.3 consumer configuration](https://kafka.apache.org/43/configuration/consumer-configs/) (reviewed 2026-09)
- [Apache Kafka 4.3 operations](https://kafka.apache.org/43/operations/) (reviewed 2026-09)

## Related topics

- [Partitions, shuffles, parallelism, and output files](../09-apache-spark-and-distributed-computation/04-partitions-shuffles-parallelism-and-output-files.md)
- [Producers, consumers, acknowledgements, and backpressure](03-producers-consumers-acknowledgements-and-backpressure.md)

## Completion checklist

- [x] Topics, partitions, offsets, keys, groups, rebalances, replicas, retention, and compaction explained
- [x] Failure, security, capacity, operations, compatibility, and evidence addressed
- [ ] Real Kafka routing, group, commit, retention, replication, skew, and load evidence run
