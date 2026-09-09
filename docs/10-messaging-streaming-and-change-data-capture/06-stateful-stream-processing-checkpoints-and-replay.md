# Stateful Stream Processing, Checkpoints, and Replay

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Streaming engines / State stores / Checkpoints / Recovery  
> Data scale: Local deterministic model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Stateful stream processing incrementally updates information that cannot be
computed from one record alone: deduplication sets, counts, joins, windows, and
sessions. A checkpoint records enough source progress, operator metadata, and
state to resume consistently after failure. Replay reconstructs state from
retained authoritative input when a checkpoint is missing, incompatible, or
known wrong.

State converts an unbounded input into a storage problem. Every key needs an
ownership, expiry, migration, backup, and correctness policy; “keep forever” is
not a production design.

## Learning objectives

- Identify which streaming operators require state and its exact grain.
- Couple input progress, state version, and output effects safely.
- Design bounded state retention without silently violating late/replay contracts.
- Recover from worker loss, corrupt/incompatible checkpoints, and sink ambiguity.
- Verify deterministic replay and batch/stream convergence.

## Prerequisites

- [Event time, processing time, windows, and watermarks](05-event-time-processing-time-windows-and-watermarks.md)
- [Delivery semantics, ordering, idempotency, and transactions](04-delivery-semantics-ordering-idempotency-and-transactions.md)
- [Checkpoints, idempotency, and atomic publication](../07-batch-processing-and-etl-elt/05-checkpoints-idempotency-and-atomic-publication.md)

## Mental model and terminology

```text
prior state S(n) + input interval (p(n), p(n+1)]
        -> deterministic transition -> candidate S(n+1), outputs O(n+1)
        -> commit under one declared recovery protocol
        -> checkpoint C(n+1) names state, input positions, code/schema, outputs
```

This resembles a `ViewModel` reducing UI events into state, but durable stream
state is partitioned across machines, outlives processes, may be many terabytes,
and must be restored or rescaled while input continues.

| Term | Meaning in this guide |
| --- | --- |
| Operator state | Data required by one logical streaming operator across records |
| Keyed state | State partitioned by a stable business/routing key |
| Checkpoint | Recoverable snapshot/log of progress, state, and operator topology metadata |
| Replay | Re-read a declared retained input interval to reconstruct results |
| State TTL | Expiry rule; a semantic correctness boundary, not just cleanup |
| Savepoint/export | Deliberately managed state image used for migration where supported |
| Deterministic transition | Same pinned state/input/order policy produces the same logical result |

## Requirements, assumptions, and invariants

Reference state includes 35-day event deduplication, 30-minute session inactivity
plus allowed lateness, and five-minute product-window metrics over 16 input
partitions. Initial cardinality and bytes per key are unmeasured; implementation
is blocked on those measurements, not hidden behind default state-store capacity.

- State grain, key, schema, semantic version, and authoritative rebuild input are explicit.
- Each checkpoint maps every source partition to a precise next offset/frontier.
- No checkpoint is called complete until referenced state and required output protocol are durable.
- Restore either exposes prior complete state or a complete successor, never a mixed generation.
- TTL exceeds the business retry/lateness requirement or records the resulting correctness limit.
- Transitions avoid wall-clock/random/network dependencies, or capture their results as versioned inputs.
- Replay cannot repeat unledgered external side effects.
- Checkpoints have independent integrity, retention, access, and restore evidence.

## State examples

| Operation | State grain | Growth driver | Safe bound/eviction signal |
| --- | --- | --- | --- |
| Deduplication | Logical event ID | Unique IDs × retry horizon | Event/ingestion horizon plus replay contract |
| Tumbling count | Key and window | Active keys × open windows | Watermark/lateness after durable output |
| Sessionization | Key and open session(s) | Active subjects and long/bridging sessions | Gap + lateness/correction policy |
| Stream-table join | Table key/version | Table cardinality/history | Version/retention and join-time need |
| Stream-stream join | Keys and both time ranges | Rates × join horizon | Both watermarks and join constraints |

An exact local reducer can serve as an oracle:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CountState:
    seen_ids: frozenset[str]
    counts: dict[tuple[str, str], int]

def apply_event(state: CountState, event: "Event") -> CountState:
    if event.event_id in state.seen_ids:
        return state
    key = (event.product_id, event.window_start)
    counts = dict(state.counts)
    counts[key] = counts.get(key, 0) + 1
    return CountState(state.seen_ids | {event.event_id}, counts)
```

This intentionally demonstrates semantics, not scale: copying sets/maps per event
is unsuitable for production. A real engine needs partitioned incremental state,
serialization, checkpointing, compaction, and backpressure.

## Checkpoint and output protocols

There are three common shapes:

1. The engine atomically coordinates source positions, state, and supported sink.
2. The sink is idempotent by stable batch/effect identity, so replayed output converges.
3. Candidate output is private until reconciliation and a metadata pointer publish it.

Arbitrary `foreach` side effects do not become recoverable because a checkpoint
directory exists. State exactly which protocol covers each sink.

Checkpoint storage should be durable outside worker-local disks, immutable or
versioned as supported, encrypted, access controlled, monitored, and restored in
tests. A copied checkpoint is not valid unless engine documentation supports the
procedure and every referenced file/metadata item is consistent.

## Replay, rebuild, and determinism

Pin input ranges, schemas, code, configuration, reference tables, timezone data,
and semantic version. Rebuild into isolated state/output; never overwrite the only
healthy state while diagnosing. Compare counts, key sets, sums, window/session
results, rejects, and source frontiers. Cut over atomically, retain rollback, and
document whether old checkpoints can resume the new code.

Nondeterminism sources include processing time, unordered tie selection, mutable
dimension lookups, random IDs, external calls, floating-point reduction order,
and incompatible serialization. Either remove them or record/tolerance-bound them.

## Data flow, ownership, and trust boundaries

| Boundary | Authority | Commit/recovery owner | Trust |
| --- | --- | --- | --- |
| Retained input log | Received-event history during retention | Messaging/source owner | Validated separately |
| Operator state | Derived accelerator/current computation | Streaming engine/pipeline | Sensitive derived state |
| Checkpoint metadata | Recovery pointer and topology | Engine/platform | Critical control data |
| Sink candidate/current | Consumer-visible derived result | Dataset owner | Quality-gated output |
| Replay job | Isolated reconstruction | Pipeline/operator | Privileged bulk reader/writer |

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Worker loss | Engine task/state failure | Restore owned partition state and replay uncommitted input |
| Driver/coordinator loss | Query stops/no progress | Restart from last complete compatible checkpoint |
| Checkpoint partial/corrupt | Integrity/restore failure | Fall back to prior proven checkpoint or full replay |
| State schema/topology incompatible | Startup/migration rejection | Supported migration/savepoint or isolated rebuild |
| Input older than retention | Offset out of range | Restore from authoritative snapshot plus remaining log |
| State grows without bound | State bytes/keys and checkpoint duration | Repair key/TTL/window policy; add capacity only with evidence |
| Sink commit unknown | Batch/effect ledger disagreement | Query/reconcile, then idempotently retry or repair |
| Wrong logic checkpointed | Quality drift | Stop publication, rebuild corrected version, atomic cutover |

## Security, privacy, and governance

State and checkpoints may concentrate identifiers and behavioral history even when
outputs are aggregated. Apply least privilege, encryption, network controls,
retention, erasure, and audit to working directories, local spill, snapshots,
logs, backups, and replay environments. Prevent path injection and unsafe
deserialization; treat checkpoint contents as engine-private unless documented.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Transition unit/property | Permute partitions, duplicates, empty input | Declared final state invariants | Pending |
| Checkpoint crash matrix | Fail state/output/progress phases | Old or complete new recovery point | Pending |
| Restore | Kill workers/coordinator and restart | Exact logical result/frontier | Pending |
| TTL/lateness | Events at expiry boundaries | Approved accept/drop/correct behavior | Pending |
| Corruption/compatibility | Remove/mutate checkpoint and change schema/topology | Safe rejection/fallback/rebuild | Pending |
| Batch-stream equivalence | Close input frontier and compare independent batch result | Reconciled equality | Pending |
| Load/replay | High cardinality, skew, failure during catch-up | State/checkpoint/recovery budgets hold | Pending |

## Debugging guide

Capture query/run ID, operator ID, state partition, key hash, input offsets,
checkpoint ID/path, state schema/version, watermark, trigger/batch ID, output
transaction, and code/config versions. Inspect state row/byte deltas, skew,
checkpoint duration/failures, input/output rates, replay attempts, storage errors,
and sink ledgers. Never delete a suspect checkpoint as a first diagnostic action;
preserve it, isolate recovery, and prove an alternative frontier.

## Common pitfalls

### Pitfall: checkpoint equals backup

It may depend on engine version, topology, external files, and source retention.
Exercise restore and keep authoritative replay/snapshot inputs.

### Pitfall: TTL treated as harmless cleanup

After identity/window state expires, an old delivery may duplicate or alter an
already-final result. Align TTL with the declared late/replay policy.

### Pitfall: rebuilding in place

A failed or semantically different rebuild can destroy the only recoverable state.
Use isolated versioned state and output, reconcile, then switch.

## Performance, capacity, and cost

Measure active keys, state rows/bytes per operator and partition, update/read
latency, cache hit, compaction, local disk, checkpoint bytes/duration/interval,
pause time, storage requests, restore time, input/output/replay rate, skew, and
cost. Checkpointing too frequently adds overhead; too rarely increases recovery
work. Select the interval from recovery objectives and measurements.

## Compatibility, migration, backfill, and delivery

Changes to key, partitioning, operator topology, serializer, state schema, window,
TTL, watermark, or engine version can invalidate recovery. Test mixed producer
schemas separately from checkpoint compatibility. Prefer supported state migration
only with fixture and restore evidence; otherwise rebuild from retained input.
Run live and backfill with isolated checkpoints/groups/sinks and reconcile before
cutover.

| Choice | Prefer when | Cost/risk |
| --- | --- | --- |
| Incremental checkpoint | Fast routine recovery needed | Storage/coordination overhead |
| Full replay | Input retained and logic/state changed | Long recovery and sink safety |
| Longer TTL | Late/replay correctness requires it | State/checkpoint growth |
| External state store | Independent access/scale is required | Network, consistency, and another failure domain |

## Working example

- Python: planned pure state reducer and checkpoint state-machine model
- Tests/data: planned duplicate, late, skew, crash, corruption, compatibility, and replay fixtures
- Infrastructure: planned distributed engine/state-store and durable checkpoint integration
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: engine state format, atomicity, restore, scale, upgrade, and cost

## Knowledge check

1. Identify state grain for dedupe, session, and stream-stream join operators.
2. Predict a crash after sink output but before checkpoint completion.
3. Explain why shortening TTL can change correctness.
4. Diagnose ever-longer checkpoints with flat input rate.
5. Design isolated replay and batch-stream comparison after a logic defect.
6. Plan a key/schema/engine migration with rollback.

## Key takeaways

- Stateful streaming makes storage lifecycle part of computation correctness.
- A checkpoint couples source progress, operator state, topology, and output protocol.
- Replay needs retained authoritative input and deterministic pinned dependencies.
- TTL and watermark choices define which late/repeated facts can still be correct.
- Restore, corruption, compatibility, and load evidence are required before production claims.

## Resources

- [Apache Spark Structured Streaming programming guide](https://spark.apache.org/docs/4.2.0/streaming/index.html) (reviewed 2026-09)
- [Apache Flink documentation: state and fault tolerance](https://nightlies.apache.org/flink/flink-docs-stable/docs/learn-flink/fault_tolerance/) (reviewed 2026-09)

## Related topics

- [Spark Structured Streaming sources, sinks, and triggers](07-spark-structured-streaming-sources-sinks-and-triggers.md)
- [Testing, tuning, failure diagnosis, and deployment](../09-apache-spark-and-distributed-computation/08-testing-tuning-failure-diagnosis-and-deployment.md)

## Completion checklist

- [x] State grain, checkpoint, replay, determinism, TTL, output, restore, and migration explained
- [x] Failure, security, evidence, capacity, operations, and backfill addressed
- [ ] Reducer, checkpoint, engine restore, corruption, equivalence, load, and migration evidence run

