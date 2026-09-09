# CAP, Coordination, Consensus, and Metadata

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic data engineering / Distributed storage / Control planes  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

During a network partition, a distributed operation cannot simultaneously promise
that every request receives a successful response and that all responses behave
like one current copy. CAP describes that constrained interval; it is not a
three-way product label and does not describe normal-operation latency, durability,
or every useful consistency model.

Coordination orders only the decisions that require shared agreement. Consensus
lets participants choose a durable ordered value despite some failures; it does
not execute the data plane, make arbitrary side effects exactly once, or remove
the need for idempotency.

## Learning objectives

- State CAP precisely for a concrete operation during partition.
- Identify invariants that require coordination and operations that commute.
- Explain consensus in terms of quorum, term, log, commit, and state machine.
- Separate control-plane metadata from high-volume data-plane work.
- Design metadata recovery, fencing, and degraded behavior.

## Prerequisites

- [Processes, networks, clocks, and partial failure](01-processes-networks-clocks-and-partial-failure.md)
- [Replication, consistency, quorums, and availability](03-replication-consistency-quorums-and-availability.md)

## Mental model and terminology

A Room transaction coordinates local rows under one database boundary. Consensus
is not a distributed Room transaction: it orders state-machine commands among
replicas, while external files, services, and task attempts remain separate
effects requiring their own commit and recovery protocols.

| Term | Meaning in this guide |
| --- | --- |
| Network partition | Communication failure that separates participants while some remain live |
| Consistency in CAP | Single-copy/linearizable behavior for the operation under discussion |
| Availability in CAP | Every request to a non-failing participant eventually receives a non-error response |
| Coordination | Communication needed to preserve an invariant across actors |
| Consensus | Agreement on one ordered sequence/value despite bounded faults |
| Control plane | Lower-volume metadata deciding placement, ownership, schemas, and generations |
| Data plane | High-volume movement and processing of records and blocks |

## Requirements and invariants

The reference pipeline uses coordinated metadata for routing epochs, stage state,
leases, and the published dataset head. Bulk event processing remains partitioned
and independent until a generation-wide quality and publication boundary.

- A dataset head references one complete, certified generation.
- At most one lease generation can commit for a stage partition.
- Routing and schema versions used by a run remain recoverable.
- Minority or stale coordinators cannot authorize conflicting ownership.
- Data-plane progress may continue only where its later validation/commit is safe.
- Loss of metadata availability never silently fabricates success.

## CAP per operation

| Operation during partition | Consistency-first behavior | Availability-first behavior | Required reconciliation |
| --- | --- | --- | --- |
| Read published generation | Reject/route if current head is unknown | Serve explicitly stale cached head | Verify freshness and generation later |
| Claim partition lease | Only quorum side grants new generation | Multiple sides may accept work | Fence outputs and discard losers |
| Accept immutable event | Wait for required authority/replicas | Buffer locally with stable ID | Deduplicate and confirm durability |
| Update routing metadata | Stop without consensus quorum | Accept conflicting routes | Usually unsafe; needs explicit conflict protocol |

Ask CAP at the granularity of one operation and contract. A platform can make a
different choice for immutable ingestion than for lease assignment or metadata
publication.

## Coordination and consensus model

```text
client command -> current leader -> replicated ordered log -> quorum commit
               -> deterministic metadata state machine -> response
```

Terms/epochs distinguish leadership generations. Log positions provide ordering;
quorum commitment establishes the protocol's durable decision. Clients still need
stable request identities because a committed response can be lost. Membership
changes are consensus decisions too and must avoid two independent majorities.

Reduce coordination by partitioning ownership, using immutable/versioned data,
making operations associative/commutative where business semantics permit, and
coordinating only publication or conflicting updates. Do not weaken a required
invariant merely to avoid latency.

## Metadata ownership and lifecycle

| Metadata | Authority | Update boundary | Recovery dependency |
| --- | --- | --- | --- |
| Routing epoch | Cluster control plane | Consensus commit | Historical routing snapshots |
| Stage/attempt state | Execution coordinator | Conditional transition | Run ledger and worker reconciliation |
| Schema/version | Catalog owner | Compatible registered version | Immutable schema history |
| Dataset head | Publisher/catalog | Conditional generation swap | Manifest and output checksums |
| Lineage/quality | Data-product owner | Certification record | Inputs, code, rules, and results |

Back up metadata and rehearse restore together with referenced data. Restoring a
catalog to an older point can orphan new data or point at retired objects even
when both backups independently succeeded.

## Failure model and recovery

| Failure | Detection | Recovery | Consumer behavior |
| --- | --- | --- | --- |
| Consensus quorum unavailable | Leader/commit progress absent | Stop coordinated writes; restore quorum safely | Explicit unavailable or allowed stale read |
| Minority leader continues | Higher term/fencing rejection | Step down; reject old generation writes | No conflicting head |
| Metadata/data mismatch | Manifest/object reconciliation | Restore objects or roll head to certified generation | Prior valid generation remains |
| Duplicate client command | Request ID already in state machine | Return prior result | One logical transition |
| Membership change interrupted | Configuration state incomplete | Resume protocol-defined transition | Avoid two-quorum split |
| Catalog restore is stale | Version/lineage cross-check | Reconcile newer generations before serving | Readiness remains false |

## Security, privacy, and governance

Control-plane compromise can redirect or publish an entire dataset. Use strong
machine identity, least privilege, protected audit logs, authenticated membership,
encrypted transport, dual control for destructive recovery, and bounded metadata
payloads. Never store secrets or raw sensitive records in consensus logs.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| CAP scenario review | Partition each operation's participants | Declared reject/stale/buffer behavior | Pending |
| Consensus state-model test | Reorder/duplicate commands and change terms | One committed metadata history | Pending |
| Minority/fencing fault | Isolate old leader then recover it | Old term cannot publish | Pending |
| Metadata restore drill | Restore control plane and reconcile manifests | No dangling or mixed generation | Pending |
| Load test | Increase metadata clients and payload size | Bounded queue/latency and admission | Pending |

## Common pitfalls

### Pitfall: labeling a whole database “CP” or “AP”

Different operations and configurations expose different behavior. State the
specific operation, failure, consistency contract, and response.

### Pitfall: using consensus for bulk data

Large event payloads inflate the ordered log and control-plane latency. Agree on
small metadata that names immutable data-plane objects.

### Pitfall: consensus means exactly-once side effects

A log command may be applied deterministically, but external calls can be retried
after lost responses. Use idempotency, outbox/intent records, and reconciliation.

## Performance, compatibility, and tradeoffs

Observe leader changes, term, commit/applied index lag, quorum health, proposal
latency, log/snapshot size, metadata queue, rejected stale generations, and data-to-
metadata reconciliation. Evolve command and snapshot formats with mixed-version
readers, staged membership changes, snapshot restore tests, and explicit rollback
limits once new commands are committed.

## Working example

- Python/tests: planned metadata state machine, CAP operation scenarios, minority fault, and manifest restore model
- Expected result: one fenced metadata history and explicit degraded behavior
- Scale represented: none yet; deterministic model then multi-process coordinator
- Remaining risk: real consensus implementation, correlated control-plane failure, and disaster recovery

## Knowledge check

1. State the CAP choice for a lease claim during a network partition.
2. Explain why serving a stale published manifest can be valid while issuing two leases is not.
3. Identify which reference-scenario actions require coordination.
4. Diagnose a restored catalog that references missing output objects.
5. Design a mixed-version metadata rollout and rollback boundary.

## Key takeaways

- CAP constrains specific operations during partition; it is not a product score.
- Coordination follows invariants, not fashion.
- Consensus orders durable metadata decisions, not every external side effect.
- Small authoritative control-plane records should name data-plane artifacts.
- Metadata and data must be backed up, restored, and reconciled together.

## Resources

- [Brewer's CAP theorem retrospective](https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/) (reviewed 2026-09)
- [Paxos Made Simple](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf) (reviewed 2026-09)
- [Raft paper](https://raft.github.io/raft.pdf) (reviewed 2026-09)

## Related topics

- [Replication, consistency, quorums, and availability](03-replication-consistency-quorums-and-availability.md)
- [MapReduce, DAGs, and data locality](05-mapreduce-dags-and-data-locality.md)

## Completion checklist

- [x] CAP, partition scope, coordination, consensus, metadata, and control/data planes explained
- [x] Ownership, fencing, failure, security, restore, capacity, compatibility, and tradeoffs addressed
- [ ] CAP, consensus-model, minority, metadata-restore, and load evidence run
