# Snapshots, Events, and State Reconstruction

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Batch / Streaming / Warehouses / Lakehouses / State models  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

An event records a change or occurrence; a snapshot records state at a defined
boundary. State can sometimes be reconstructed by ordering and applying events,
but only when the event contract is complete, deterministic, ordered at the
required scope, and retained from a known starting point.

This guide compares transaction facts, periodic snapshots, accumulating
snapshots, change logs, event-sourcing boundaries, replay, compaction, and
reconciliation. Broker mechanics and streaming state-store implementation belong
to later areas.

## Learning objectives

- Choose event, current-state, periodic-snapshot, or accumulating-snapshot models.
- Define the ordering, identity, and initial state required for replay.
- Reconstruct state while handling duplicates, gaps, late events, and corrections.
- Use snapshots/compaction without silently changing historical meaning.
- Design reconciliation and recovery evidence for derived state.

## Prerequisites

- Fact grains from guide 03 and time/history from guide 05
- Area 01 lifecycle, publication, idempotency, and recovery concepts

## Mental model

```text
authoritative baseline S0 + ordered changes E1..En --fold--> state Sn
              |                                      |
       periodic checkpoint Ck -----------------------+
```

A Kotlin `fold` over immutable actions is a useful analogy. It stops where real
data systems have only partition-scoped ordering, duplicated/missing events,
versioned reducer logic, external side effects, and retention that may remove the
prefix required for replay.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Event | Immutable claim that something occurred, with stable identity and time |
| State | Latest known values for an entity at a named boundary/version |
| Periodic snapshot | State sampled at regular, declared times |
| Accumulating snapshot | One process-grain row updated as milestones occur |
| Replay | Reapply a known input history with pinned logic and reference data |
| Checkpoint | Certified state plus position/version from which processing resumes |
| Compaction | Create a smaller equivalent representation under a declared query contract |

## Requirements and invariants

- Each logical event has a stable identity and schema/semantic version.
- Ordering is stated by entity/partition; no global order is assumed.
- A replay pins baseline, event range, reducer code, identity mappings, reference
  data, and correction policy.
- Applying a duplicate event is idempotent or detected before state mutation.
- Gaps, unknown event types, and invalid transitions stop or quarantine state for
  the affected scope rather than producing plausible silent results.
- Snapshot time means a precise cutoff and completeness rule, not file creation time.
- Compaction output reconciles to uncompacted inputs for supported queries.

## Model comparison

| Model | Best question | Main strength | Main limitation |
| --- | --- | --- | --- |
| Immutable transaction fact | What occurred? | Audit/reaggregation | Current state requires derivation |
| Current-state table | What is known now? | Simple low-latency lookup | Past states overwritten |
| Periodic snapshot | What was state at each close? | Trend and point-in-time access | Storage; misses within-period changes |
| Accumulating snapshot | Where is each process now/how long between stages? | Lifecycle analysis | Updates and late milestone corrections |
| Event-sourced aggregate | Can domain state be rebuilt from decisions/events? | Explicit domain transition history | Strong event completeness/version discipline |

A database change-data-capture log is not automatically a domain event stream.
It describes row mutations, may expose transaction/connector semantics, and may
lack the intent or invariants required to rebuild a domain aggregate.

## Reconstruction sketch

Typed Python-like pseudocode; implementation planned:

```python
def apply_inventory(state: InventoryState, event: InventoryEvent) -> InventoryState:
    if event.event_id in state.applied_ids:
        return state
    if event.sequence != state.next_sequence:
        raise SequenceGap(state.next_sequence, event.sequence)
    if event.kind == "stock_received":
        return state.receive(event.quantity, event.event_id)
    if event.kind == "stock_reserved":
        return state.reserve(event.quantity, event.event_id)
    raise UnsupportedEvent(event.kind, event.schema_version)
```

Keeping every applied ID in state is unbounded; a real design needs a durable
deduplication/index contract or contiguous source sequence plus replay rules.
Sequence is per inventory entity, not a claim of global ordering.

## Periodic and accumulating snapshots

A daily inventory snapshot has grain `(tenant, product, location, business_date)`
and a cutoff such as 00:00 in the tenant's named time zone after an allowed-late
window. Inventory balance is additive across products/locations but not dates.

An order-line accumulating snapshot can carry `ordered_at`, `paid_at`,
`shipped_at`, and `delivered_at`. Updates must be idempotent, milestone ordering
validated, and the row's system history retained if earlier dashboard results
must be reproducible. A single “last_updated” timestamp is insufficient proof.

## Replay, checkpoints, and compaction

A checkpoint is usable only with the exact last-applied source position, entity
scope, state schema, reducer version, checksum, and atomic publication. If state
commits but offset does not, duplicates follow; if offset commits first, data can
be lost. Application code alone cannot make independent stores atomic.

Compaction may replace old changes with a baseline plus later events, but it must
preserve every supported answer, audit/retention need, deletion tombstone, and
correction rule. Never delete source events merely because one derived snapshot
currently agrees.

## Data flow, ownership, and trust boundaries

Domain/source owners define authoritative transitions; ingestion preserves raw
delivery; the event ledger establishes accepted logical events; a reducer owner
publishes derived state/snapshots; consumers declare their cutoff and correction
expectations. Scheduler timestamps and object listings are operational metadata,
not business ordering.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Duplicate event | Identity/sequence conflict | No-op or reject; reconcile state checksum |
| Sequence gap | Expected versus observed sequence | Pause entity/partition; recover missing input |
| Late event before snapshot cutoff | Completeness watermark/reconciliation | Publish corrected snapshot version |
| Reducer bug | Golden replay or invariant violation | Pin fixed reducer; rebuild from trusted baseline |
| Corrupt checkpoint | Checksum/schema/position mismatch | Fall back to prior checkpoint and replay |
| Partial snapshot publication | Manifest/version mismatch | Keep old snapshot; abandon or complete staging |
| Event schema unsupported | Version gate | Retain raw event; deploy compatible reducer; replay |

Recovery is proven when rebuilt state matches authoritative point samples and
aggregate invariants, source positions are contiguous, and repeated replay yields
the same published version.

## Security, privacy, and governance

Immutable history can preserve data beyond its permitted purpose. Minimize event
payloads, separate/tokenize identity, authorize replay, audit bulk reconstruction,
encrypt checkpoints, and carry deletion/tombstone semantics through snapshots and
compaction. A tombstone must survive long enough to prevent an older replay from
resurrecting deleted state.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Ordered fold fixture | Known events produce hand-computed state | Pending |
| Duplicate/gap/out-of-order mutations | Duplicate is safe; gaps/order fail explicitly | Pending |
| Checkpoint restart | Replay after every crash boundary converges | Pending |
| Late correction | New snapshot changes only declared affected scope | Pending |
| Compaction equivalence | Supported queries match pre/post compaction | Pending |
| Authoritative reconciliation | Sample entity state and totals agree at cutoff | Pending |

## Common pitfalls

### Pitfall: calling every audit table event sourcing

Audit/CDC records may not encode domain intent, completeness, or replay-stable
semantics. State exactly which questions the log can reconstruct.

### Pitfall: using latest event by timestamp as state

Clocks tie, events arrive late, and different event types may combine. Use a
declared per-entity order and transition function.

### Pitfall: treating a snapshot as a backup

A derived snapshot may omit history and inherit reducer defects. Backup/restore
must protect the authoritative inputs and metadata needed to rebuild.

## Performance, operations, and migration

Measure events/entity, bytes/day, late-age distribution, sequence gaps, dedup
state, replay throughput versus arrival rate, checkpoint time/size, snapshot rows,
compaction amplification, skew, and recovery-time objective. Replay must process
faster than new data accumulates or recovery never catches up.

Migrate current state to event-derived state by capturing a consistent baseline,
starting changes at a precise position, replaying in shadow, comparing entity and
aggregate checksums, observing live convergence, cutting over reads, and retaining
rollback. Do not fabricate pre-baseline events.

## Working example

- Python/SQL/data/tests: planned inventory events, daily snapshot, checkpoint, and fault matrix
- Expected result: deterministic state, restart convergence, and snapshot reconciliation
- Scale represented: none yet; distributed ordering and recovery throughput unverified
- Remaining risk: source completeness, event evolution, skew, and deletion replay

## Knowledge check

1. Choose a model for “what happened,” “current stock,” and “stock at each close.”
2. Predict state after a duplicate and then a sequence gap.
3. Diagnose why `MAX(event_time)` produced the wrong current status.
4. Define the metadata required for a valid replay checkpoint.
5. Prove a proposed compaction preserves supported queries.
6. Plan a current-state-to-events migration without inventing history.

## Key takeaways

- Events and snapshots answer different questions at different grains.
- Reconstruction needs complete inputs, scoped order, deterministic logic, and versions.
- Checkpoint state and source position form one recovery contract.
- Compaction preserves only explicitly tested semantics.
- Replay, correction, deletion, and recovery capacity must be designed together.

## Resources

- [Martin Fowler: Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html) (reviewed 2026-09)
- [Kimball Group: Timespan Accumulating Snapshot Fact Tables](https://www.kimballgroup.com/2012/05/design-tip-145-timespan-accumulating-snapshot-fact-tables/) (reviewed 2026-09)

## Related topics

- [Slowly changing dimensions and bitemporal history](05-slowly-changing-dimensions-and-bitemporal-history.md)
- [Metrics, semantic layers, and consistent meaning](07-metrics-semantic-layers-and-consistent-meaning.md)

## Completion checklist

- [x] Event, state, snapshot, replay, checkpoint, and compaction models explained
- [x] Ordering, failures, privacy, recovery capacity, and migration addressed
- [ ] Fold, restart, late-data, compaction, reconciliation, and scale evidence run
