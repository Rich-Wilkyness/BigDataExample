# Partitioning, Hashing, Range Routing, and Rebalancing

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / Storage / Batch / Streaming  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Partitioning assigns each record and unit of work to a bounded subset of storage
or compute. A good scheme enables parallelism and pruning while preserving the
co-location and ordering contracts consumers need. A poor key creates hotspots,
broad scans, unstable routing, or expensive movement during growth.

This guide separates logical partitions from physical workers and files, compares
hash and range routing, and treats rebalancing as a versioned data migration.

## Learning objectives

- Choose a key from access, grouping, locality, cardinality, and skew requirements.
- Distinguish hash, range, directory, and composite routing.
- Explain why partition count and worker count must not be conflated.
- Quantify skew, movement, fan-out, and headroom.
- Design a recoverable, mixed-version rebalance.

## Prerequisites

- [Processes, networks, clocks, and partial failure](01-processes-networks-clocks-and-partial-failure.md)
- Keys and grain from [05 Data Modeling and Business Semantics](../05-data-modeling-and-business-semantics/README.md)

## Mental model and terminology

Android resource qualifiers route a request into a bucket, but data partitioning
differs because buckets contain durable state, may be huge, and must migrate while
reads and writes continue.

```text
record key -> canonical bytes -> routing function + routing version
           -> logical partition -> current replica/worker assignment
```

| Term | Meaning in this guide |
| --- | --- |
| Logical partition | Stable unit of data/work addressed independently of a machine |
| Physical assignment | Current worker, disk, or replica serving a logical partition |
| Hash partitioning | Route using a deterministic hash-derived bucket or token |
| Range partitioning | Route using ordered boundaries over a comparable key |
| Hot partition | Partition whose resource demand approaches a limit |
| Rebalancing | Moving responsibility/state after topology or routing changes |

## Requirements, assumptions, and invariants

The event pipeline groups by `(tenant_id, product_id, event_date_utc)` and starts
with 16 logical aggregation partitions. One tenant may own 35% of events; null or
unknown keys are explicitly quarantined or assigned to a deliberately bounded
bucket, never accidentally collapsed into one hotspot.

- Equivalent canonical keys always route identically under one routing version.
- Routing metadata is authoritative and versioned; workers are replaceable assignments.
- Every accepted record belongs to exactly one logical partition per stage.
- Rebalancing neither loses nor double-publishes records.
- Consumer order is promised only within an explicitly named partition, if at all.
- Partition count leaves recovery and burst headroom rather than consuming all slots.

## Routing choices

| Requirement | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Even point-key load | Hash partitioning | Spreads high-cardinality keys | Range scans dominate |
| Ordered range pruning | Range partitioning | Adjacent values stay together | Monotonic keys create a hot tail |
| Tenant isolation | Directory/composite routing | Ownership and policy are explicit | One tenant exceeds a partition |
| Topology changes with less movement | Token/rendezvous-style mapping | Decouples keys from worker count | Operational complexity exceeds benefit |
| Co-located join/group | Same canonical key and partition contract | Avoids redistribution | Independent scaling or skew requires salting |

Never use a language runtime's process-randomized hash as a durable routing
contract. Define key encoding, normalization, hash algorithm, seed, modulo/token
mapping, null handling, and routing version. A composite key needs unambiguous
length framing, not naive string concatenation.

## Rebalancing lifecycle

```text
plan V2 -> copy immutable ranges -> verify counts/digests
        -> dual-route or forward under explicit epoch
        -> conditional ownership cutover
        -> observe and reconcile -> retire V1 copies
```

A rebalance records source and target partitions, routing epochs, copy progress,
checksums, catch-up position, and cutover state. Readers use an authoritative
routing snapshot for the operation; they do not independently guess ownership.
Writes during movement require a defined protocol such as epoch-fenced ownership,
dual write plus reconciliation, or append-log catch-up.

## Failure model and recovery

| Failure | Detection | Recovery | Consumer behavior |
| --- | --- | --- | --- |
| Skewed key | Per-key/partition bytes and task time | Split, salt, isolate, or change model | Contracted aggregate is recombined |
| Monotonic range hotspot | Tail queue/throughput | Pre-split ranges or add key dimension | Freshness may degrade within SLO |
| Worker loss | Assignment heartbeat/lease | Reassign logical partitions | Routing version remains stable |
| Copy interrupted | Durable range/checksum progress | Resume immutable chunks | Old owner remains authoritative |
| Split-brain ownership | Conflicting epochs | Fence older epoch; reconcile writes | No mixed publication |
| Routing-version mismatch | Request/version telemetry | Serve compatible version or reject/retry | Explicit transient failure, not silent loss |

## Security, privacy, and governance

Partition keys can expose tenant, location, or behavioral information through
paths and metrics. Authorize routing metadata, isolate tenant partitions when
required, sanitize path components, and cap metric labels. Rebalancing identities
need separate copy and cutover privileges with an audit trail.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Routing property test | Generate canonical keys across processes | Stable, total, deterministic assignment | Pending |
| Distribution test | Uniform and Zipf-like fixtures | Skew metrics identify imbalance | Pending |
| Null/adversarial key test | Empty, huge, Unicode, and colliding-looking keys | Explicit bounded disposition | Pending |
| Rebalance fault test | Stop copy before/during/after cutover | No loss or duplicate publication | Pending |
| Capacity test | Increase partitions, bytes, and hot-key rate | Measured limit and headroom | Pending |

## Common pitfalls

### Pitfall: partition count equals worker count

Scaling workers then changes data identity and forces movement. Keep logical
partitioning stable enough for recovery while assigning many partitions to workers.

### Pitfall: date partitioning guarantees balanced work

Dates enable pruning but say nothing about tenant or key distribution within a
day. Measure bytes, records, and compute cost per partition.

### Pitfall: salting without a merge contract

Salting spreads one key but changes grouping. Preserve the original business key
and add a second aggregation stage that deterministically recombines salts.

## Performance, operations, and compatibility

Track records, bytes, distinct keys, largest-key share, partition percentiles,
scan fan-out, movement bytes, rebalance duration, queue depth, and per-partition
CPU/disk/network. Changing canonical encoding or routing is a data migration:
version readers, backfill, validate, cut over atomically, retain rollback state,
then retire old routing only after all producers and consumers advance.

## Working example

- Python/tests/data: planned stable router, synthetic skew fixture, rebalance state machine, and capacity report
- Expected result: deterministic ownership, visible hotspots, and fault-safe movement
- Scale represented: none yet; local property tests then multi-process copy/cutover
- Remaining risk: storage topology, concurrent mutations, network saturation, and tenant isolation

## Knowledge check

1. Choose hash or range routing for point lookup, date pruning, and co-located aggregation.
2. Predict the consequence of routing with `hash(key) % worker_count` across restarts.
3. Diagnose a partition that holds 35% of all records.
4. Design a rebalance cutover that survives worker death.
5. Estimate movement and recovery headroom before doubling topology size.

## Key takeaways

- Partition identity, routing, and physical assignment are separate decisions.
- Key encoding and routing version are durable contracts.
- Average distribution hides hot keys and hot partitions.
- Rebalancing is a recoverable migration with an authoritative cutover.
- Co-location saves movement only when it preserves the required business grain.

## Resources

- [Amazon Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) (reviewed 2026-09)
- [Apache Cassandra documentation: partitioners](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html#partitioning) (reviewed 2026-09)

## Related topics

- [Shuffles, skew, stragglers, and hot partitions](06-shuffles-skew-stragglers-and-hot-partitions.md)
- [Resource scheduling, backpressure, and capacity](08-resource-scheduling-backpressure-and-capacity.md)

## Completion checklist

- [x] Hash, range, composite routing, locality, hotspots, movement, and rebalancing explained
- [x] Identity, nulls, ownership, security, failure, recovery, capacity, and migration addressed
- [ ] Routing, distribution, adversarial-key, rebalance-fault, and capacity evidence run
