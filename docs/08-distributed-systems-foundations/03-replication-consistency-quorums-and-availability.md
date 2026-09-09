# Replication, Consistency, Quorums, and Availability

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Generic data engineering / Distributed storage / Metadata  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Replication stores related copies so data can survive failures and serve load.
Copies alone do not define what a read may observe: a system also needs a write,
read, conflict, and repair protocol. Availability, durability, freshness, and
consistency are separate dimensions.

This guide develops leader/follower and quorum reasoning without presenting a
replication factor or quorum equation as a complete correctness proof.

## Learning objectives

- Separate replication, durability, availability, and consistency guarantees.
- Trace writes and reads through leader/follower and quorum-style protocols.
- State the assumptions behind quorum intersection.
- Choose a consumer-visible freshness and conflict model.
- Design repair, failover, and convergence evidence.

## Prerequisites

- [Processes, networks, clocks, and partial failure](01-processes-networks-clocks-and-partial-failure.md)
- [Partitioning, hashing, range routing, and rebalancing](02-partitioning-hashing-range-routing-and-rebalancing.md)

## Mental model and terminology

Room with a remote sync backend is a useful consistency analogy: local reads may
lag server state and conflicts need policy. It stops because distributed storage
replicas jointly implement one service and may acknowledge, elect, and repair at
machine scale.

| Term | Meaning in this guide |
| --- | --- |
| Replica | Copy participating in a defined replication protocol |
| Replication factor `N` | Number of intended replicas for one item/partition |
| Write/read quorum `W`/`R` | Required acknowledgements/responses under a stated protocol |
| Linearizability | Operations appear in one real-time-respecting order |
| Eventual convergence | Replicas become equal after writes and failures stop, given repair |
| Stale read | Read that omits a write already accepted under the relevant contract |
| Read-your-writes | A session observes its own successful writes |

## Requirements, assumptions, and invariants

The reference pipeline stores immutable inputs and one authoritative published
manifest. Analytical consumers may accept a boundedly stale prior generation,
but must never see a manifest naming missing or mixed output partitions.

- Acknowledgement criteria state whether data is in memory, journaled, or durably stored.
- Each read guarantee names its scope: key, session, partition, or dataset generation.
- Replica placement accounts for correlated rack, zone, and administrative failure.
- Failover cannot create two unfenced writers for the same authoritative epoch.
- Repair never overwrites a newer version using wall-clock guesswork alone.
- Publication metadata and referenced data have compatible durability guarantees.

## Replication and consistency choices

| Need | Possible design | Tradeoff |
| --- | --- | --- |
| Ordered writes for one partition | Fenced leader and replicated log | Failover/coordination on leader loss |
| Low-latency local reads | Nearby follower | Explicit staleness/session policy |
| Immutable object durability | Redundant copies plus verified checksums | Listing/metadata semantics still matter |
| Concurrent multi-writer acceptance | Versioned writes plus conflict resolution | More complex semantics; not every value is mergeable |
| Atomic dataset visibility | Strongly controlled manifest/head | Metadata path may be a smaller availability boundary |

For a simplified quorum model with `N` replicas, requiring `W + R > N` creates
set intersection only if reads and writes contact the same replica set model and
versions are compared correctly. It does not alone guarantee linearizability:
sloppy quorums, concurrent writes, failed writes, clock-based conflict resolution,
membership changes, and weak repair can violate the expected result.

## Read, write, and repair lifecycle

```text
write(operation, version)
  -> route to replica set/leader
  -> persist according to acknowledgement contract
  -> return success, rejection, or unknown

read(key, consistency)
  -> contact required replicas
  -> compare protocol versions
  -> return allowed value
  -> optionally schedule repair
```

Anti-entropy detects divergence outside the foreground path. Read repair can
reduce observed inconsistency but increases read work. Hinted handoff improves
temporary availability but is not a permanent replica and needs bounded backlog,
expiry, replay, and observability.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Consumer behavior |
| --- | --- | --- | --- |
| Follower lag | Replication offset/time lag | Throttle, catch up, or exclude | Bounded-stale/read-from-leader policy |
| Leader loss | Lease/term/health plus quorum | Elect/assign new fenced epoch | Temporary unavailability or declared stale reads |
| Acknowledged replica loss | Placement/durability alert | Restore replica and verify | Guarantee depends on ack durability |
| Concurrent versions | Multiple incomparable versions | Domain merge, reject, or preserve conflict | Explicit conflict, never silent last timestamp wins |
| Repair backlog | Age/bytes/divergence metrics | Prioritize and rate-limit repair | Reduced durability/freshness is visible |
| Membership change | Joint/epoch configuration state | Complete or roll back protocol | No split replica-set interpretation |

## Security, privacy, and governance

Replication expands the data surface. Apply encryption, least privilege, deletion,
retention, and audit to every replica, repair stream, snapshot, and backup. Locality
rules constrain placement. A deletion is not complete until replicas, indexes,
repair queues, backups, and derived datasets follow their declared lifecycle.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Consistency model test | Enumerate reads/writes/failures | Only declared observations occur | Pending |
| Quorum assumption test | Partition replica sets and vary `R/W` | Intersection limits are explicit | Pending |
| Failover test | Stop leader around acknowledgement | No unfenced dual writer; outcome recoverable | Pending |
| Repair test | Corrupt/drop one replica version | Divergence detected and converged safely | Pending |
| Durability restore drill | Lose replica/zone in harness | Required data and metadata recover | Pending |

## Common pitfalls

### Pitfall: replication means backup

Replication can quickly copy corruption or deletion. Keep independently governed,
restorable versions and rehearse restore.

### Pitfall: `W + R > N` means strong consistency

Intersection is one condition inside a protocol. Document membership, versioning,
concurrency, failed-write, and repair assumptions before claiming a guarantee.

### Pitfall: replication lag is only a platform metric

Lag changes consumer correctness and freshness. Tie it to affected datasets and
the maximum staleness promised by each read path.

## Performance, operations, and compatibility

Replication multiplies storage and network write cost; synchronous acknowledgement
adds tail latency. Track per-replica lag, acknowledgement latency, unavailable
replicas, divergent versions, repair bytes/age, failover duration, and placement
compliance. Protocol or membership changes require mixed-version tests, staged
rollout, compatible version records, and restore/rollback rehearsal.

## Working example

- Python/tests: planned replica-state model, quorum simulator, failover/fencing cases, and repair ledger
- Expected result: observed reads stay within the selected contract and failures converge
- Scale represented: none yet; deterministic model followed by multi-process faults
- Remaining risk: real disk durability, network partitions, correlated failures, and operational repair load

## Knowledge check

1. Distinguish availability, durability, freshness, and linearizability.
2. Explain which assumptions make quorum intersection useful.
3. Predict a read during follower lag and during a leader failover.
4. Design conflict handling for immutable events versus a mutable profile field.
5. Define evidence that deletion and repair reached every governed copy.

## Key takeaways

- Replication creates copies; a protocol creates a consistency guarantee.
- Acknowledgement must say what became durable and where.
- Quorum arithmetic is not a substitute for membership and version semantics.
- Failover requires fencing; repair is continuous correctness work.
- Consumer freshness and conflict behavior belong in the data contract.

## Resources

- [Amazon Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) (reviewed 2026-09)
- [Raft paper](https://raft.github.io/raft.pdf) (reviewed 2026-09)
- [Consistency in Non-Transactional Distributed Storage Systems](https://arxiv.org/abs/1512.00168) (reviewed 2026-09)

## Related topics

- [CAP, coordination, consensus, and metadata](04-cap-coordination-consensus-and-metadata.md)
- [Retries, idempotency, speculation, and fault recovery](07-retries-idempotency-speculation-and-fault-recovery.md)

## Completion checklist

- [x] Replication, leader/follower, quorums, consistency, staleness, durability, and repair explained
- [x] Ownership, failure, security, deletion, observability, capacity, and compatibility addressed
- [ ] Consistency, quorum, failover, repair, and restore evidence run
