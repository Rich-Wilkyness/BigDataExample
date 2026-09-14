# Full, Incremental, and Change-Based Processing

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Generic data engineering / SQL / Batch / CDC  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A full batch selects the complete declared source scope. An incremental batch
selects records beyond durable progress, often with overlap. A change-based batch
applies an ordered log or explicit versions including deletes. The safest choice
is the simplest one that meets the freshness and cost budget while preserving a
recoverable source boundary.

Incremental does not mean filtering on the current clock, and CDC does not remove
the need for snapshots, reconciliation, or correction policy.

## Learning objectives

- Select full, incremental, or change-based processing from requirements.
- Define total watermarks that do not lose tied or concurrent updates.
- Represent inserts, updates, deletes, late arrivals, and corrections explicitly.
- Separate source progress, processing scope, and publication state.
- Plan periodic rebuild and reconciliation to detect accumulated drift.

## Prerequisites

- Area 06 database extracts, CDC, late-data, and reconciliation guides
- [SQL transformations and set-based pipelines](03-sql-transformations-and-set-based-pipelines.md)

## Mental model and terminology

Imagine synchronizing Room from a remote API: a full refresh replaces all known
state; an incremental request asks for changes after a cursor; a change log
delivers ordered mutations. The analogy stops when source history is partitioned,
many workers apply changes, corrections rewrite analytical history, and output is
a versioned dataset rather than one transactional local database.

| Term | Meaning in this guide |
| --- | --- |
| Full processing | Recomputes the complete declared dataset or bounded partition scope |
| Incremental processing | Recomputes only candidate data beyond/around durable progress |
| Change-based processing | Applies source mutations with operation and ordering/version evidence |
| Watermark | Durable total boundary proving which eligible source records are included |
| Lookback/overlap | Deliberate re-read before the prior boundary to capture delay/correction |
| Tombstone | Explicit delete marker retained long enough to reach all required derivatives |
| Drift | Target state diverges from the authoritative result over time |

## Requirements, assumptions, and invariants

Reference volume is 3M append-like events/day, 100K product rows, 50–500 product
changes/second, seven-day normal correction, 35-day hot replay, and a one-year
full rebuild. Choose modes per dataset: events can be incrementally selected by a
total receipt position; product current state requires versions/deletes; recent
metrics may use partition replacement. Measure full-scan time/cost first.

Invariants:

- Every incremental lower and upper bound is typed, persisted, and totally ordered.
- The upper bound is captured before reading; one run never chases a moving source.
- Progress advances only after the corresponding output is durably published.
- Re-reading overlap is harmless under stable identity and version rules.
- Deletes and corrections remain representable through every dependent dataset.
- A full rebuild from retained authoritative inputs can reproduce the declared version.
- Incremental output reconciles periodically with an independently derived authoritative scope.

## Selection decision

| Requirement or constraint | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Bounded data fits window/cost comfortably | Full rebuild | Minimal state and easiest reasoning | Runtime or source load threatens SLO |
| Append-only input has stable total position | Incremental append | Efficient, precise closed ranges | Corrections/deletes occur outside position contract |
| Mutable source exposes `updated_at` plus tie-break key | Incremental composite watermark with overlap | Captures tied timestamps and delays | Timestamp can move backward or deletes are absent |
| Source exposes ordered operation log | Change-based apply | Preserves mutation order and deletes | Retention gaps or handoff cannot be repaired |
| Derived daily metrics receive late facts | Replace affected partitions/windows | Deterministic correction | Consumer cannot handle versioned replacement |

## Watermark and scope model

```sql
-- Generic keyset boundary. Capture :upper_time/:upper_id before the read.
SELECT *
FROM source_change
WHERE (updated_at, source_id) > (:lower_time, :lower_id)
  AND (updated_at, source_id) <= (:upper_time, :upper_id)
ORDER BY updated_at, source_id;
```

Tuple comparison is dialect-specific; the equivalent disjunction must preserve
the same total order. If multiple versions of one key share both fields, add a
monotonic version/position. A timestamp alone loses rows tied at a boundary or
can repeat ambiguously.

```text
prior committed W0 ---- overlap start ---- captured upper W1 ---- future writes
          |<----------- selected candidate scope ----------->|
                         publish, then commit W1
```

Overlap covers bounded source delay, not arbitrary historical correction. Stable
key/version deduplication makes repeated overlap safe. Keep input boundary time
separate from event time used for business windows.

## Change application and deletes

```sql
-- Pseudocode: first reduce candidate changes to the latest valid version per key.
MERGE INTO product_current AS t
USING product_change_candidate AS s
ON t.tenant_id = s.tenant_id AND t.product_id = s.product_id
WHEN MATCHED AND s.operation = 'DELETE' AND s.version > t.version THEN DELETE
WHEN MATCHED AND s.operation <> 'DELETE' AND s.version > t.version THEN UPDATE SET ...
WHEN NOT MATCHED AND s.operation <> 'DELETE' THEN INSERT (...);
```

Keep an audit/history relation even if the current table removes deleted rows.
Without tombstones or periodic source comparison, an incremental `updated_at`
extract cannot distinguish deleted from never-seen rows. Out-of-order older
versions must not overwrite newer state.

## Lifecycle, identity, consistency, and time

A run reads the last committed source boundary, captures a fixed upper boundary,
records both in its run ledger, stages that closed range, reduces duplicates and
versions, rebuilds affected output scopes, validates, publishes, then advances
progress conditionally. Failed attempts retain the same logical run scope.

Track source commit/version time, business effective/event time, ingestion time,
processing time, and publication time. A newer source version can describe an
older effective date; processing order does not decide business history without
the model's temporal rules.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Timestamp tie skipped | Source-target anti-join at boundary | Return to last safe total boundary and replay |
| Checkpoint advances before output | Progress/output version mismatch | Roll checkpoint back or republish pinned scope |
| Output publishes before checkpoint | Same range is reread | Idempotently replace/merge, then commit progress |
| Delete absent from extract | Periodic full comparison or source count drift | Acquire tombstones/snapshot and repair dependents |
| CDC retention gap | Requested position unavailable | Stop apply; take coordinated snapshot and resume log |
| Late correction outside lookback | Reconciliation or source correction feed | Launch bounded historical repair/backfill |
| Old change overwrites new state | Version-regression assertion | Restore latest version and enforce conditional apply |

## Security, privacy, and governance

Incremental state, tombstones, and logs may preserve identifiers longer than
current tables. Authorize checkpoints and change history as control and sensitive
data, prevent tenant/key injection into dynamic predicates, encrypt retained
state, audit repair and rewind, and propagate deletion across facts, aggregates,
indexes, caches, backfills, and old dataset versions according to policy.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Full/incremental equivalence | Compare both from same closed source version | Equal logical result | Pending |
| Boundary matrix | Tied times, empty range, concurrent insert, clock regression | No missing or unexplained duplicate records | Pending |
| Change matrix | Insert, repeated update, stale update, delete, recreate | Declared version/current/history result | Pending |
| Crash matrix | Fail before/after candidate publish and progress commit | Rerun converges; no skipped scope | Pending |
| Gap/correction drill | Expire log position and mutate old date | Resnapshot/backfill restores equality | Pending |
| Scale comparison | Measure full versus incremental scans and cost | Choice meets runtime/source/cost budgets | Pending |

Local fixtures prove transition logic only. A real source is needed to prove
isolation, timestamp/version guarantees, log retention, and load impact.

## Common pitfalls

### Pitfall: `WHERE updated_at > last_run_time`

Wall-clock run time is not a closed source boundary; ties, transaction visibility,
and clock changes lose data. Persist a source-defined total boundary and capture a
fixed upper bound.

### Pitfall: incrementally applying aggregates forever

One duplicate or missed delete creates lasting drift. Prefer replacement of
bounded affected partitions plus periodic independent rebuild/reconciliation.

### Pitfall: assuming append-only from observed behavior

Unless the producer contract forbids mutation, design for correction and delete
or record the risk explicitly.

### Pitfall: advancing progress per record while publishing per dataset

A crash can make uncommitted output unreachable. Align or recoverably coordinate
source progress with the consumer-visible publication unit.

## Performance, capacity, cost, and operations

Measure change rate, full/source scan bytes, index/pruning selectivity, overlap
amplification, keys/window, state and tombstone size, apply/rebuild throughput,
checkpoint lag, source load, correction age, reconciliation cost, and full-rebuild
duration. Incremental complexity is justified only by observed budget savings.

Alerts cover stalled/regressing checkpoints, growing overlap ratio, log-retention
headroom, delete/correction anomalies, version regressions, source-target deltas,
and full-rebuild budget. Recovery pins boundaries, stops publication, chooses
rewind or resnapshot, repairs, reconciles, and advances state only afterward.

## Compatibility, migration, and tradeoffs

To change selection or key/version policy, retain raw/change history, run old and
new modes from a common boundary, compare current and historical outputs, publish
a new dataset/checkpoint generation, migrate consumers, and retain rollback.
Never reinterpret an old scalar checkpoint under a new composite order.

## Working example

- Python/SQL/data/tests: planned full builder, composite-watermark selector, change reducer, tombstones, checkpoint ledger, and comparison report
- Expected result: full and incremental results agree after retries, deletes, and bounded corrections
- Scale represented: none yet; local transition fixture and real-source load evidence planned
- Remaining risk: source isolation, CDC gap recovery, long-tail corrections, and state cost

## Knowledge check

1. Choose a processing mode for immutable events, mutable products, and daily aggregates.
2. Predict records selected when three rows share the scalar high-water timestamp.
3. Diagnose a target row that survives after its source deletion.
4. Design crash tests around output and checkpoint commit ordering.
5. Estimate when a full rebuild is cheaper than incremental state and repair complexity.
6. Migrate a timestamp checkpoint to a timestamp-plus-ID boundary safely.

## Key takeaways

- Full processing is the correctness baseline when it meets the budget.
- Incremental selection requires a closed total boundary and recoverable progress.
- Change-based processing preserves operations only while log order and retention remain intact.
- Deletes, corrections, and late data must flow through every derivative.
- Periodic full comparison exposes incremental drift.

## Resources

- [PostgreSQL documentation: transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09)
- [PostgreSQL documentation: row and array comparisons](https://www.postgresql.org/docs/current/functions-comparisons.html) (reviewed 2026-09)
- [PostgreSQL documentation: MERGE](https://www.postgresql.org/docs/current/sql-merge.html) (reviewed 2026-09)

## Related topics

- [Checkpoints, idempotency, and atomic publication](05-checkpoints-idempotency-and-atomic-publication.md)
- [Backfills, reprocessing, and historical correction](06-backfills-reprocessing-and-historical-correction.md)
- [Database snapshots and incremental extracts](../06-data-ingestion-and-source-integration/04-database-snapshots-and-incremental-extracts.md)

## Completion checklist

- [x] Full, incremental, change-based, watermarks, deletes, corrections, and drift explained
- [x] Identity, time, failure, security, quality, capacity, migration, and evidence addressed
- [ ] Equivalence, boundary, change, crash, gap, source-load, and scale evidence run
