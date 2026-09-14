# Event Time, Processing Time, Windows, and Watermarks

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Streaming / SQL / Time-series processing  
> Data scale: Local deterministic fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Event time says when a fact occurred in its business domain. Ingestion time says
when the platform first observed it. Processing time says when an operator handled
it. A window groups an unbounded stream into finite logical scopes. A watermark is
an engine/operation-specific claim about event-time progress used to bound state
and decide how late records are handled; it is not a wall clock and not universal
proof that no earlier event can arrive.

Correct streaming results require an explicit late-data contract. A result may be
early and revisable, final after a policy threshold, or corrected later through a
different path. Dropping late records to save state is a business decision, not a
neutral optimization.

## Learning objectives

- Distinguish event, ingestion, and processing time and choose each deliberately.
- Define half-open tumbling, sliding, and session-window membership.
- Explain watermarks, allowed lateness, triggers, and output completeness.
- Handle clock skew, duplicates, delayed records, and late corrections.
- Size and test window state from observed lateness and key distribution.

## Prerequisites

- [Window functions, time series, and analytical patterns](../03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)
- [Delivery semantics, ordering, idempotency, and transactions](04-delivery-semantics-ordering-idempotency-and-transactions.md)
- UTC and timestamp contracts from Areas 03–05

## Mental model and terminology

```text
event time:     10:00  A ------- B ---- C  10:30
arrival order:          B, C, ... A(late)
watermark W:                  10:15

W is derived progress under a policy. It can permit state older than a threshold
to close/evict; it does not repair clocks or guarantee all earlier facts exist.
```

Android event timestamps often originate on imperfect device clocks. They remain
useful domain evidence when paired with ingestion time and quality bounds. The
analogy to `debounce`/`window` operators stops because distributed watermarks
combine progress across partitions, survive checkpoints, and control durable
state and correction semantics.

| Term | Meaning in this guide |
| --- | --- |
| Event time | Domain timestamp assigned by the event contract |
| Ingestion time | Trusted platform observation time |
| Processing time | Runtime clock when an operator processes a record |
| Tumbling window | Non-overlapping fixed intervals |
| Sliding window | Fixed intervals that overlap by a slide interval |
| Session window | Per-key interval extended/merged while gaps stay below a threshold |
| Watermark | Declared lower-bound/progress mechanism used by an operation to manage lateness/state |
| Allowed lateness | Policy duration for accepting/revising event-time results |

## Requirements, scale assumptions, and invariants

Reference metrics use UTC half-open 5-minute tumbling windows; sessions use a
30-minute inactivity gap. Provisional allowed lateness is 30 minutes. Inputs may
arrive out of order, repeat, or carry a device clock outside a configured validity
range. The product owner must approve finality and correction behavior.

- Timestamps are timezone-aware instants normalized to UTC; original zone/context is retained if required.
- Window boundaries are half-open `[start, end)` and tested exactly at both edges.
- Deduplication happens at logical event identity before non-idempotent aggregation.
- Watermark definition, delay, partition/idleness behavior, and operator scope are documented.
- Evicted state has an explicit too-late disposition: drop with evidence, correction stream, or rebuild.
- Empty windows and `NULL` timestamps have defined semantics.
- A session's key, gap comparison (`<` or `<=`), merge behavior, and late reopening policy are explicit.

## Window models

For epoch time `t`, tumbling width `w`, and aligned origin `o`:

```text
window_start = floor((t - o) / w) * w + o
window_end   = window_start + w
membership  = window_start <= t < window_end
```

Sliding windows can multiply one event into approximately `width / slide`
windows, affecting state, shuffle, output, and cost. Session windows are data
dependent: a late event can bridge two sessions and require retractions/updates.

SQL at a closed bounded frontier can act as a reference oracle:

```sql
-- PostgreSQL-style arithmetic; production dialect and negative epochs need tests.
SELECT tenant_id,
       product_id,
       to_timestamp(floor(extract(epoch FROM event_time) / 300) * 300) AS window_start,
       COUNT(*) AS view_count
FROM deduplicated_events
WHERE event_type = 'product_viewed'
  AND event_time >= :scope_start
  AND event_time < :scope_end
GROUP BY tenant_id, product_id, window_start;
```

`event_time IS NULL` does not pass the predicates and must already have an explicit
quarantine/disposition. SQL output order is unspecified without `ORDER BY`.

## Watermark and output lifecycle

```text
receive event -> validate time -> deduplicate -> assign/merge window state
             -> emit early update(s) -> watermark advances
             -> close/evict eligible state -> later event follows late policy
             -> optional correction/backfill reconciles authoritative result
```

Watermark implementations differ. Some derive progress from maximum observed
event time minus a delay; multi-partition combination and idle-source behavior
are engine/configuration specific. Review actual plans, progress records, and
state metrics instead of inferring behavior from one timestamp setting.

## Data flow, ownership, and trust boundaries

| Boundary | Time contract | Owner | Failure behavior |
| --- | --- | --- | --- |
| Device/producer | Event time and clock-quality metadata | Producer/domain owner | Reject/flag impossible times |
| Ingestion | Trusted ingestion time | Platform | Preserved through replay |
| Broker | Append timestamp/position where configured | Messaging owner | Transport order only |
| Processor | Parse zone, windows, watermark, triggers | Metric owner | Checkpoint/replay deterministically |
| Serving table | Window version, status, last frontier | Dataset owner | Upsert/retract/correct per contract |

## Failure model and recovery

| Failure | Detection | Recovery/consumer behavior |
| --- | --- | --- |
| Device clock far future | Event-vs-ingestion skew bound | Quarantine/cap only by explicit policy; prevent watermark distortion |
| One partition idle/stalled | Per-partition progress and watermark age | Diagnose idleness; do not silently claim completeness |
| Late event within policy | Late counter and updated window | Revise output idempotently |
| Event after eviction | Too-late disposition ledger | Correction stream/backfill/drop per approved contract |
| Late event bridges sessions | Session merge mutation case | Retract/upsert affected sessions if supported, else repair |
| Timezone/schema change | Contract/version mismatch | Dual read/migrate state or rebuild from retained input |
| Replay uses processing time | Batch-stream comparison differs | Replace nondeterminism with recorded event/ingestion time |

## Security, privacy, and governance

Timestamps and session keys can reveal behavior and presence. Minimize precision
and retention where the use case permits, restrict raw and per-user session state,
and avoid keys/timestamps as high-cardinality metric labels. Deletion must cover
retained events, window/session state, emitted corrections, checkpoints, and
backups. Log safe ranges and hashed identifiers, not complete behavioral trails.

## Data quality, testing, and evidence

Use hand-calculated fixtures with exact boundary timestamps, out-of-order arrival,
duplicates, missing/invalid zones, future/past skew, idle partitions, late records
before/after threshold, and a bridging session event.

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Window boundaries | Events just before/at/after start/end | Exact half-open membership | Pending |
| Arrival permutation | Permute same closed multiset | Same final result under policy | Pending |
| Watermark | Advance active/idle partitions deliberately | Declared close/eviction behavior | Pending |
| Late/session | Inject late extension and bridge | Expected update/retraction/correction | Pending |
| Replay | Change wall-clock run time | Result depends only on pinned input/time policy | Pending |
| Batch comparison | SQL over closed frontier vs stream state | Exact/tolerance-defined equivalence | Pending |

## Debugging guide

Inspect raw event time, ingestion time, append position/time, parsed timestamp and
zone, current watermark, max observed event time per partition, window/session key,
state row/byte counts, late disposition, trigger/batch ID, and sink version. A
stale dashboard may be an idle source, a stalled watermark, slow processing, or
an output sink delay; “streaming lag” alone does not locate it.

## Common pitfalls

### Pitfall: watermark equals current time minus delay

It is data/engine/operator progress, not automatically wall time. Verify actual
derivation and idle-partition rules.

### Pitfall: dropping late data without a product contract

State cost is real, but silent drops corrupt metrics. Quantify lateness, agree on
finality, expose late counts, and provide correction/reconciliation.

### Pitfall: processing-time logic in replayable computation

Rerunning tomorrow changes results. Use recorded times and pin reference data;
reserve processing time for operational triggers, not business membership.

## Performance, capacity, and cost

State roughly grows with active keys × overlapping windows × per-window state,
plus deduplication and overhead. Measure event/ingestion skew distribution,
watermark delay/age, active keys, windows per event, session merges, state rows/
bytes, update/eviction rates, checkpoint time, output revisions, too-late rate,
shuffle, memory, disk, and replay throughput. Sweep lateness delay and skew rather
than selecting 30 minutes by intuition.

## Compatibility, migration, and tradeoffs

Changing timezone parsing, window origin/width/slide, session gap, lateness, or
watermark behavior changes metric meaning and state compatibility. Assign a new
definition version, shadow/rebuild from retained input, compare closed windows,
cut over atomically, and keep rollback output/input.

| Choice | Prefer when | Cost/risk |
| --- | --- | --- |
| Event time | Domain-correct historical grouping matters | Late data and clock-quality complexity |
| Processing time | Operational reaction time is the actual definition | Nondeterministic historical replay |
| Longer lateness | Late correctness is valuable | More state and later finality |
| Shorter lateness + correction | Fast bounded state is required | Separate repair path and temporary drift |
| Session windows | Activity-defined groups matter | Merge/retraction and skew complexity |

## Working example

- Python/SQL: planned reference tumbling/session assignment and closed-frontier query
- Tests/data: planned boundary, skew, permutation, idle, late, and session-bridge fixtures
- Infrastructure: planned real streaming-engine watermark/state integration
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: engine watermark/idle behavior, state scale, sink revisions, and production lateness

## Knowledge check

1. Assign events exactly at 10:00 and 10:05 to half-open five-minute windows.
2. Explain why ingestion order cannot define a user's session accurately.
3. Predict what a late bridging event does to two previously emitted sessions.
4. Diagnose a watermark stalled by one partition.
5. Choose a late-data policy from correctness, state, and finality requirements.
6. Plan a window-definition migration with backfill and rollback.

## Key takeaways

- Event, ingestion, and processing time answer different questions.
- Windows bound logical scope; watermarks help bound state under an explicit policy.
- Finality and too-late behavior are product/data contracts.
- Session windows can merge and revise previously emitted state.
- Closed-frontier batch comparison is strong correctness evidence.

## Resources

- [Apache Spark Structured Streaming programming guide](https://spark.apache.org/docs/4.2.0/streaming/index.html) (reviewed 2026-09)
- [Beam programming guide: event time and watermarks](https://beam.apache.org/documentation/programming-guide/#watermarks-and-late-data) (reviewed 2026-09)

## Related topics

- [Stateful stream processing, checkpoints, and replay](06-stateful-stream-processing-checkpoints-and-replay.md)
- [Spark Structured Streaming sources, sinks, and triggers](07-spark-structured-streaming-sources-sinks-and-triggers.md)

## Completion checklist

- [x] Time domains, window types, watermarks, lateness, finality, and corrections explained
- [x] Identity, failure, security, quality, state cost, migration, and operations addressed
- [ ] Reference, SQL, real-engine watermark, session, replay, and load evidence run

