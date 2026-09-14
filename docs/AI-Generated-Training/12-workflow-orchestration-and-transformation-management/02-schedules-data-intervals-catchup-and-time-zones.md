# Schedules, Data Intervals, Catchup, and Time Zones

> Status: Documentation complete; executable calendar evidence planned  
> Level: Beginner to Senior  
> Applies to: Generic orchestration / Airflow / Batch / Time-based data  
> Data scale: Local calendar fixture; distributed production estimate  
> Example status: Planned  
> Evidence status: Documentation and contract review only  
> Last reviewed: 2026-09

## Overview

A schedule proposes workflow runs; a data interval defines the data each run owns.
Those are not the same as the wall-clock time when a worker starts. Reliable jobs
use explicit half-open intervals and readiness frontiers, so delay, retry, manual
triggering, catchup, and daylight-saving changes do not alter which records belong.

This guide covers recurring batch time. Event-time windows and watermarks remain
in Area 10; product-specific timetable implementation is secondary.

## Learning objectives

- Separate logical interval, scheduled time, actual start, and data readiness.
- Use half-open UTC boundaries without duplicate or missing records.
- Predict catchup and rerun behavior across calendar and DST transitions.
- Design completeness gates and bounded late-data correction.
- Test calendars, manual triggers, pauses, and backfills deterministically.

## Prerequisites

- Timestamp, time-zone, and interval semantics from Areas 03 and 07.
- Workflow run and publication identity from the previous guide.
- Event-time frontier concepts from Area 10.

## Mental model and terminology

```text
interval start       interval end       readiness/cutoff       actual start
     |-------------------|--------------------|----------------------|
      data owned by run    expected arrivals    scheduler/queue delay
```

| Term | Meaning in this guide |
| --- | --- |
| Data interval | Half-open range `[start, end)` whose records a run owns |
| Logical date | Orchestrator identifier derived from timetable semantics; not current time |
| Actual start | Wall-clock instant execution begins |
| Readiness frontier | Durable claim that required input through a position/time is available |
| Catchup | Creation of scheduled runs for prior unmaterialized intervals |
| Rerun | Another attempt or replacement calculation for an already identified interval |
| Civil schedule | Calendar rule in an IANA time zone, subject to offset changes |

Android's periodic work is a useful reminder that requested and actual execution
times differ. The analogy stops because data orchestration normally assigns a
historical interval and may intentionally execute dozens of old intervals.

## Requirements, scale assumptions, and invariants

- Daily certified metrics own `[00:00, 24:00)` UTC and publish by 02:00 UTC.
- Every query receives explicit UTC `interval_start` and `interval_end` parameters.
- The same interval and model version select the same eligible input frontier.
- Scheduler delay never changes data membership.
- Catchup is bounded by interval count, parallelism, source retention, and sink load.
- Late corrections create auditable replacement publications; they do not mutate silently.
- Civil-time business calendars use a named IANA zone and tested DST policy.
- Non-goal: treating processor wall clocks as an authoritative readiness signal.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Timetable | Calendar, zone, start/end policy | Workflow owner | Fail graph validation on ambiguity | Trusted configuration |
| Scheduler | Timetable and stored run history | Platform team | May be late; must not redefine interval | Control plane |
| Source frontier | Manifest/offset through interval cutoff | Producer owner | Hold run if incomplete | Authoritative readiness |
| Transform query | Explicit interval and input version | Dataset owner | Reject missing/naive timestamps | Controlled execution |
| Publication | Interval, semantic version, frontier | Dataset owner | Replace only by declared correction policy | Authoritative derived data |

## Interval selection and completeness

```sql
-- Dialect: illustrative ANSI SQL. Parameters are timezone-aware UTC instants.
SELECT tenant_id, product_id, COUNT(*) AS view_count
FROM curated_event_fact
WHERE event_time >= :interval_start
  AND event_time <  :interval_end
GROUP BY tenant_id, product_id;
```

Avoid `DATE(event_time) = :date` when it obscures time-zone conversion or prevents
partition pruning. Avoid `BETWEEN` for adjacent timestamp intervals because both
ends are inclusive in common SQL dialects.

```python
@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    def validate(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("timezone-aware boundaries required")
        if self.start >= self.end:
            raise ValueError("non-empty increasing interval required")
```

Normalize boundaries to UTC for storage and comparison. Retain the named business
zone and calendar rule as metadata; a numeric offset alone cannot express future
or historical DST rules.

## Calendar and schedule decision table

| Requirement | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Global daily facts | Fixed UTC interval | Stable 24-hour partition contract | Business definition is local civil day |
| Local retail day | IANA-zone calendar | Represents 23/24/25-hour days correctly | Consumers can adopt UTC semantics |
| Input arrives variably | Data-aware readiness plus deadline | Separates completeness from clock | Producer has no durable frontier |
| Historical rebuild | Explicit bounded backfill | Auditable range and capacity | Single correction interval suffices |
| Near-real-time updates | Streaming/window engine | Scheduler is too coarse | Micro-batch contract is acceptable |

For a local day, derive the next local midnight in the named zone and convert
both boundaries to UTC. Do not add 24 hours to the previous UTC instant and call
that a local day.

## Catchup, reruns, and late data

A pause of five days can create five missing daily intervals, not one five-day
run, unless the contract explicitly chooses coalescing. Before catchup, calculate:

```text
eligible intervals = requested intervals
                   ∩ retained source intervals
                   - already certified equivalent versions
peak queries       = min(backfill concurrency, pool slots, warehouse quota)
```

Late records require a policy: reject after cutoff, include in the next interval
with explicit semantics, or recompute affected historical intervals. For facts
whose identity includes original event time, the last option generally preserves
truth best but creates correction and consumer-notification work.

## Lifecycle, consistency, identity, and time

Store interval boundaries, timetable/time-zone version, trigger type, requested
by, actual start/end, input frontier, code version, and publication ID. Manual
runs must receive or derive an explicit interval; a button-click timestamp is not
a safe substitute. Reruns should not use `now()` to select source data.

Consumers may receive publication-time freshness later than interval end. Report
both: “data through 2026-09-06T00:00Z” and “published at 02:07Z” answer different
questions.

## Failure model and recovery

| Failure | Detection and containment | Recovery and evidence |
| --- | --- | --- |
| Scheduler down at boundary | Missing expected run and heartbeat | Restore scheduler; create exact missed intervals |
| Source incomplete at schedule | Frontier behind required cutoff | Wait with deadline; alert producer; do not publish partial silently |
| DST creates nonexistent/duplicate local hour | Calendar fixture detects count/boundary mismatch | Apply declared zone policy and rerun affected interval |
| Catchup floods warehouse | Queue/concurrency/query latency alarms | Pause expansion, retain current-work reserve, resume bounded |
| Manual run selects wrong interval | Preflight displays parameters and frontier | Cancel before publish or issue auditable replacement |
| Source retention expired | Preflight finds unavailable partitions | Restore archive or mark interval unrecoverable; never fake success |
| Late event after certification | Reconciliation/correction feed | Rebuild affected intervals and notify consumers |

## Security, privacy, and governance

Authorize who can trigger historical ranges, override readiness, and replace a
certified interval. Treat interval parameters as typed values, not interpolated
SQL. Record actor, reason, ticket, range, code version, and result. Bounds prevent
an accidental or malicious multi-year query from exhausting systems.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Command or procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Boundary property | Events at start/end / local | Generate adjacent intervals | Every event belongs to exactly one interval | Pending |
| DST calendar | IANA transition dates / local | Enumerate spring/fall local days | Declared 23/25-hour boundaries result | Pending |
| Delay invariance | Fixed interval / scheduler double | Vary actual start and retry time | Selected records/checksum unchanged | Pending |
| Catchup control | 35 intervals / test orchestrator | Dry-run then execute bounded range | Count/order/concurrency match plan | Pending |
| Real readiness | Manifest-producing source / integration | Delay and repair frontier | Publication waits then converges | Pending |

## Debugging guide

1. Capture run ID, trigger type, logical date, interval boundaries, actual times, zone, and timetable version.
2. Compare interval with source frontier and query parameters.
3. Count boundary records at exactly start/end and inspect partition pruning.
4. Compare expected schedule instances with stored runs; include paused periods.
5. Contain by stopping certification or catchup expansion, not by changing dates ad hoc.
6. Recompute one interval, reconcile identity sets/checksums, then resume bounded history.

## Common pitfalls

### Pitfall: use current time inside the task

A retry tomorrow reads different data. Use the run's explicit interval and fixed
input version.

### Pitfall: schedule time means data is ready

Clock passage is not completeness. Require a producer manifest/frontier or make
the lateness policy visible.

### Pitfall: every day is 24 hours

That is true for fixed UTC daily intervals, not local civil days across DST.

## Performance, capacity, and cost

A 35-day catchup at normal daily concurrency could consume 35 times a day's
warehouse work in a short period. Budget current-work reserve, maximum active
runs, task pool slots, query concurrency, bytes scanned, API quotas, and output
compaction. Measure scheduler lag separately from task queue and execution time.

## Observability and operations

Emit interval start/end, expected schedule time, actual start, readiness time,
input frontier, publication time, trigger type, and version identifiers. Track
schedule delay, readiness delay, queue delay, runtime, end-to-publication
freshness, missing intervals, and correction count. Alert on consumer impact and
deadline risk, not merely “task has not started at midnight.”

## Compatibility, migration, backfill, and delivery

Changing schedule, time zone, start date, or interval semantics is a data
migration. Freeze the old frontier, enumerate old/new intervals, detect gaps and
overlaps, dual-calculate representative boundaries, cut over at a named instant,
and preserve a rollback mapping. Never silently reinterpret historical run IDs.

## Working example

- Python source: Planned calendar/interval model under `src/big_data_example/orchestration/`
- SQL: Planned half-open selection under `sql/orchestration/`
- Tests: Planned boundary, DST, delay, and catchup tests under `tests/orchestration/`
- Data: Planned events exactly before, at, and after interval boundaries
- Try it: Planned deterministic interval enumeration command
- Expected result: No gaps/overlaps; delayed execution selects identical records
- Evidence: Planned property, SQL, scheduler integration, and load results
- Scale represented: Documentation plus 35-day production estimate
- Remaining risk: Timetable, zone-database, scheduler, and warehouse behavior unverified

## Knowledge check

1. Distinguish data interval, logical date, scheduled time, readiness time, and actual start.
2. Predict which interval owns an event exactly at midnight.
3. Diagnose a daily run that starts “one day late” but is actually correct.
4. Design tests for a local-day schedule across both DST transitions.
5. Estimate catchup pressure for 35 intervals and a pool of four slots.
6. Propose migration from America/Denver civil days to UTC days without overlap.
7. Implement the planned interval validator and a boundary property test.

## Key takeaways

- Schedules request runs; intervals define data ownership.
- Half-open UTC ranges make adjacent batches composable.
- Completeness is a durable producer frontier, not the wall clock.
- Catchup and corrections need explicit capacity and audit policies.
- Calendar changes are data-contract migrations.

## Resources

- [Apache Airflow: DAG runs and data intervals](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html) (reviewed 2026-09)
- [Apache Airflow: scheduler](https://airflow.apache.org/docs/apache-airflow/stable/concepts/scheduler.html) (reviewed 2026-09)
- [IANA Time Zone Database](https://www.iana.org/time-zones) (reviewed 2026-09)
- [Python `zoneinfo`](https://docs.python.org/3/library/zoneinfo.html) (reviewed 2026-09)

## Related topics

- [DAG and dependency design](01-dags-workflows-tasks-and-dependency-design.md)
- [Backfills and concurrency](05-backfills-dynamic-workflows-and-concurrency-controls.md)
- [Area 10 event time and watermarks](../10-messaging-streaming-and-change-data-capture/05-event-time-processing-time-windows-and-watermarks.md)

## Completion checklist

- [x] Interval, logical date, readiness, catchup, rerun, and time-zone models defined
- [x] SQL and Python sketches state boundary and time assumptions
- [x] DST, late data, pause, manual trigger, failure, recovery, and security addressed
- [x] Capacity, observability, migration, and knowledge exercises included
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Calendar fixtures, scheduler integration, readiness, and load evidence executed
