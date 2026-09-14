# First End-to-End Data Pipeline

> Status: Documentation complete  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / Python / SQL / Batch / Storage  
> Data scale: Local fixture with production estimate  
> Example status: Complete design walkthrough; executable artifacts planned  
> Evidence status: Contract / Data quality design / Boundary review  
> Last reviewed: 2026-09

## Overview

This guide assembles the area into one bounded pipeline: accept mobile
`screen_viewed` events, retain immutable raw input, validate and normalize them,
publish daily counts, and expose an explicit freshness/version contract to a
dashboard. The design begins with record meaning and consumer guarantees; Python,
SQL, and storage engines are replaceable implementations.

The walkthrough is manually inspectable and includes expected results and failure
behavior. Executable artifacts are intentionally planned for later areas so this
foundation does not pretend that paper evidence proves runtime semantics.

## Learning objectives

After completing this guide, you should be able to:

- Trace producer, validation, normalization, transformation, publication, and consumer use.
- State grain, identity, owner, trust, time, and authority at every dataset boundary.
- Derive an aggregate from duplicates, invalid records, and late arrivals.
- Design idempotent rerun, quarantine, reconciliation, and atomic publication behavior.
- Identify the evidence still required before production use.

## Prerequisites

Complete guides 01–07 in this area. No runtime infrastructure is required for the
paper walkthrough. A future executable version will require Python, SQL, local
fixtures, and tests owned by their respective curriculum areas.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Raw accepted event | Immutable producer envelope plus ingestion metadata, authoritative for durable receipt |
| Valid event | Raw event satisfying a named structural and semantic rule version |
| Quarantine record | Restricted error representation sufficient for authorized diagnosis/reprocessing |
| Daily screen count | One row per UTC date, stable screen name, and app version |
| Input cutoff | Latest eligible receipt boundary included in a dataset version |
| Atomic publication | Consumer transition from one complete version to another without observing staging |
| Reconciliation | Comparison of control totals/identities across boundaries to prove accounting |

## Requirements, scale assumptions, and invariants

### Consumer contract

The product dashboard shows prior-UTC-day counts by stable `screen_name` and
`app_version` by 09:00 America/Denver. It displays dataset version, event-time
interval, receipt cutoff, publication time, and quality status. Late eligible
events may produce a corrected version the following day.

### Estimated workload

Baseline is 100,000 daily active installations x 30 events/day = 3 million
events/day, approximately 2.86 GiB/day at 1 KiB/event. A 60-minute window with
50% headroom implies at least 1,250 successfully accounted events/s. This is a
capacity hypothesis, not benchmark evidence.

### Invariants

- `event_id` is stable across producer retries and unique within retained history.
- Raw acknowledged events are durably retained or the acknowledgement contract is violated.
- Raw input is immutable; validation and transformation versions are recorded.
- Every accepted input becomes valid, quarantined, or an explicitly deferred item.
- Daily rows count unique valid eligible identities, never delivery attempts.
- Consumers see either the old complete version or the new complete version.
- Rerunning identical input and logic produces the same logical rows and totals.
- Logs, errors, and metrics do not expose installation identifiers or full payloads.

Non-goals are real-time alerts, person identity, cross-device identity resolution,
sessionization, marketing attribution, and distributed-engine selection.

## Mental model

```text
Android app
  one observed view/event_id
        |
        v  authenticate + bound + structural validation
collector ----reject----> safe rejection signal
        |
        v  durable commit + receipt_time
raw dataset version (authoritative accepted history)
        |
        +----semantic validation----> restricted quarantine
        |
        v
valid normalized events (one event_id)
        |
        v  filter interval + deduplicate + group
staged daily counts + reconciliation report
        |
        v  quality gate + atomic version switch
curated daily screen counts ----> dashboard with cutoff/freshness
```

This resembles an Android offline-first sync pipeline: local identity, retry,
server acknowledgement, stored state, and UI projection. The analogy stops
because analytical publication groups large historical sets, accepts controlled
staleness, and must support versioned backfills for many consumers.

## Data contracts and ownership

| Boundary | Grain/key | Authority and owner | Contract/failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Producer event | One observed view / `event_id` | Android team owns observation meaning | Versioned UTC event; retry stable ID | External input |
| Raw accepted | One durable envelope / `event_id` | Ingestion owns receipt fact | Immutable; add receipt/batch metadata; reject bounded invalid envelope | Restricted |
| Quarantine | One validation failure / event + rule version | Pipeline/security jointly govern | Safe reason and reference; restricted retention/reprocess | Highly restricted |
| Valid event | One unique accepted valid event / `event_id` | Pipeline owns validation result | Stable screen vocabulary; typed time/version | Governed internal |
| Daily count | One date/screen/app-version / composite key | Data product owns metric | Count of unique eligible events and full version metadata | Purpose-limited |
| Dashboard | One rendered metric/version | Product consumer owns presentation | Show stale/failed status; no silent zero | Consumer boundary |

## Input fixture and expected decisions

Assume dataset version `raw-2026-09-05-r1`, receipt cutoff
`2026-09-06T08:00:00Z`, and validation rules `screen-event-v1`:

| Row | event_id | screen_name | event_time (UTC) | app_version | receipt_time (UTC) | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `e1` | `home` | 2026-09-05 10:00 | `1.0` | 2026-09-05 10:00:02 | Include |
| 2 | `e2` | `details` | 2026-09-05 10:01 | `1.0` | 2026-09-05 10:01:01 | Include |
| 3 | `e2` | `details` | 2026-09-05 10:01 | `1.0` | 2026-09-05 10:02:10 | Duplicate delivery; do not recount |
| 4 | `e4` | empty | 2026-09-05 10:03 | `1.0` | 2026-09-05 10:03:02 | Quarantine: invalid screen |
| 5 | `e5` | `home` | 2026-09-04 23:59 | `1.0` | 2026-09-05 10:04:00 | Valid but not in 2026-09-05 event interval |
| 6 | `e6` | `home` | 2026-09-05 23:59 | `1.1` | 2026-09-06 08:30:00 | Deferred: after receipt cutoff |

The first published version contains:

| event_date | screen_name | app_version | unique_event_count |
| --- | --- | --- | ---: |
| 2026-09-05 | `details` | `1.0` | 1 |
| 2026-09-05 | `home` | `1.0` | 1 |

Control totals are six raw rows, five distinct event IDs, four structurally and
semantically valid distinct events (`e1`, `e2`, `e5`, `e6`), one quarantined
identity, two eligible included identities, one valid outside the event interval,
and one valid deferred by cutoff. Categories are mutually exclusive at this run
boundary and sum to five distinct identities. Delivery-row counts are reported
separately so the duplicate remains observable.

## Transformation contract

In SQL-like relational form, using half-open UTC intervals and an explicit receipt
cutoff:

```sql
-- Dialect-neutral design sketch; executable dialect is planned.
WITH eligible AS (
    SELECT event_id, screen_name, app_version, event_time, receipt_time,
           ROW_NUMBER() OVER (
               PARTITION BY event_id
               ORDER BY receipt_time, raw_sequence
           ) AS delivery_rank
    FROM valid_screen_events
    WHERE event_time >= :event_start_utc
      AND event_time <  :event_end_utc
      AND receipt_time <= :receipt_cutoff_utc
)
SELECT CAST(event_time AS DATE) AS event_date,
       screen_name,
       app_version,
       COUNT(*) AS unique_event_count
FROM eligible
WHERE delivery_rank = 1
GROUP BY CAST(event_time AS DATE), screen_name, app_version;
```

The production dialect must define UTC date conversion, parameter types,
`NULL` constraints, stable `raw_sequence`, and execution-plan behavior. Input is
bounded before aggregation. The staged result is not consumer-visible until
quality gates and publication commit pass.

A Python implementation should stream or process bounded chunks rather than load
the retained dataset without a memory budget. Runtime validation remains required
despite type hints. The caller/job owns file and connection lifetimes; the
publication component owns cleanup of staging and the final commit.

## Walkthrough

1. **Produce:** the app creates one UUID per observation and reuses it on retry.
2. **Accept:** collection validates envelope version, required types, payload
   size, and authentication; it adds trusted receipt metadata.
3. **Commit raw:** acknowledgement follows the durable boundary. An immutable
   manifest/version distinguishes complete input from orphan files.
4. **Validate:** semantic rules constrain `screen_name`, timestamps, and allowed
   versions. Invalid data is represented safely in restricted quarantine.
5. **Normalize:** timestamps become UTC instants and screen values map only under
   a versioned owned vocabulary; unknowns are not guessed.
6. **Transform:** select the half-open event interval and receipt cutoff,
   deduplicate stable identity, then group by the declared aggregate grain.
7. **Check:** compare raw delivery rows, distinct identities, valid, quarantined,
   outside-window, deferred, and included totals; check unique output key,
   nonnegative counts, known screens, and expected volume range.
8. **Publish:** write an immutable output version, quality report, lineage, input
   cutoff, and code/config versions; atomically switch the curated pointer.
9. **Consume:** dashboard reads only the published contract and shows version,
   cutoff, freshness, and stale/error state.

## Record, file, job, and dataset lifecycle

Records progress through accepted, valid/quarantined, eligible/deferred, included,
and expired/deleted states. Files or objects progress through write, validation,
manifest commit, read, compaction if needed, and expiration. Jobs progress through
admitted, running, staged, checked, published or failed, then reconciled. Dataset
corrections create new immutable versions; backfills operate on bounded intervals
and never mutate the currently published version in place.

## Consistency, ordering, identity, and time

Only order needed for deduplication is a deterministic choice among deliveries of
the same `event_id`; no global event order is promised. Event time selects daily
membership, receipt time determines cutoff eligibility, and publication time
determines freshness. A later `e6` creates a corrected version for September 5 if
the lateness policy permits. Consumers receive snapshot consistency for one
published version, not immediate source consistency.

## Failure model and recovery

| Failure | Detection | Containment/retry owner | Consumer behavior and recovery proof |
| --- | --- | --- | --- |
| Timeout after raw commit | Client lacks acknowledgement | Client retries same `event_id`; ingestion deduplicates/account deliveries | One logical identity after reconciliation |
| Invalid or hostile payload | Bounds/schema/semantic failure | Collector rejects envelope or pipeline quarantines safe reference | No partial aggregate; failure count visible |
| Missing input partition | Manifest/readiness failure | Pipeline does not publish; ingestion repairs input | Prior version remains; manifest and totals pass |
| Worker fails during output | Run state lacks publish commit | Pipeline retries from immutable input | No staging visible; rerun equals expected rows |
| Quality mismatch | Reconciliation gate | Pipeline owner holds version and investigates | Dashboard shows old cutoff/staleness |
| Late `e6` | Deferred/late metric | Next correction run includes stable identity | New version adds one `home`/`1.1` count |
| Bad code deployment | Fixture/quality/consumer anomaly | Roll back code, rerun bounded interval, compare versions | Corrected version and impact communicated |
| Overload/backlog | Oldest age and throughput | Apply admission/backpressure; add safe capacity | Backlog drains and freshness plus totals recover |

Exactly-once wording is avoided. The design provides idempotent logical output
within the declared retained identity and publication scope; real engines must
prove their own source, state, and sink behavior.

## Security, privacy, and governance

Use transport authentication, bounded inputs, strict parsing, parameterized SQL,
least privilege, encryption, separated raw/curated roles, audited control changes,
and managed secrets. `installation_id` is pseudonymous but still sensitive; it is
excluded from the aggregate, ordinary logs, and metric labels. Quarantine stores
only the authorized diagnostic minimum. Retention and deletion cover raw, valid,
quarantine, curated, staging, cache, export, lineage, logs, and backups according
to their policies.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Command or procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Fixture walkthrough | Six-row table / paper | Classify identities, derive aggregates and totals | Two output rows; counts and categories above | Passed manually |
| Rerun reasoning | Same input/version / paper | Apply deterministic identity and immutable publication rules twice | Same logical output; no double count | Passed by contract; not executed |
| SQL/Python unit and quality tests | Local deterministic fixture | Future repository test command | Duplicate/invalid/late/empty cases pass | Pending |
| Storage/publication integration | Real selected local engine | Interrupt writes and concurrent reads | Consumers see old or new complete version | Pending |
| Load/skew/fault evidence | Representative generated data | Profile baseline/high case, hot keys, failure, recovery | Meets objectives with headroom | Pending |

Manual evidence verifies the arithmetic and contract are internally consistent.
It does not verify SQL dialect behavior, parser safety, filesystem/object-store
atomicity, concurrent execution, distributed recovery, performance, or cost.

## Debugging guide

1. Capture consumer dataset version, cutoff, aggregate key, expected/actual value,
   and first affected interval.
2. Inspect publication metadata, quality report, transformation/rule versions,
   run attempts, and input manifest.
3. Reconcile output count to included unique IDs, then valid, quarantined,
   deferred/outside-window, distinct raw IDs, and delivery rows.
4. Search by privacy-safe authorized `event_id` reference; compare event, receipt,
   and publication times.
5. Check partition/file counts, largest keys, task duration, retries, resource
   saturation, and backlog age for scale failures.
6. Hold publication or serve last known good with visible staleness. Repair from
   immutable raw input, republish a new version, invalidate dependent caches, and
   confirm consumer reconciliation.

## Common pitfalls

### Pitfall: count rows before declaring identity

Row 3 would make `details` equal two. Deduplicate by the producer's stable event
identity in a declared retention scope and preserve delivery counts separately.

### Pitfall: filter only on event date

Without a receipt cutoff, the same run is not reproducible as late events arrive.
Record both half-open event interval and input/receipt version.

### Pitfall: write directly to the consumer path

Readers can observe a partial mixture. Stage an immutable version, validate it,
then use a supported atomic publication mechanism.

### Pitfall: turn invalid input into null or “unknown” silently

That changes meaning and hides producer defects. Apply an owned normalization
rule or quarantine with observable reason and bounded sensitive detail.

## Performance, capacity, cost, and operations

The baseline batch needs at least 1,250 successful events/s with stated headroom,
but benchmarks must include parsing, deduplication state, aggregation cardinality,
quality checks, staging, publication, and retries. Measure rows/bytes/files,
compression, memory, spill, CPU, disk/network, partition skew, run percentiles,
backlog drain, query concurrency, retained copies, and unit cost. Monitor accepted,
duplicate, valid, quarantined, deferred, included, and published totals; cutoff
age; run state; version; saturation; and deletion backlog with bounded labels.

## Compatibility, migration, backfill, and delivery

Schema changes use expand/migrate/contract with old and new readers during the
retention window. Transformation changes write a new dataset version, replay a
bounded interval, compare keys and counts, receive semantic approval, and switch
consumers atomically. Preserve old version and code/config for rollback. Isolate
backfill resources from daily capacity and reconcile every affected date before
retiring old data or permissions.

## Engineering tradeoffs

| Decision | Selected baseline | Reason | Reconsider when |
| --- | --- | --- | --- |
| Processing | Daily batch | Meets consumer freshness with simple bounded replay | Approved intraday decision requires lower delay |
| Raw storage | Immutable versioned landing | Repair, audit, and reproducibility | Policy forbids retention or measured cost requires redesign |
| Invalid data | Restricted quarantine plus explicit count | Diagnose without corrupting curated data | Payload sensitivity requires rejection without retention |
| Publication | Immutable version plus atomic pointer/transaction | Reader consistency and rollback | Selected engine offers a stronger appropriate transaction |
| Serving | Governed analytical table | Few consumers and noninteractive daily workload | Query latency/concurrency requires projection/cache |

## Working example

- Python source: Planned under `src/big_data_example/...` in later implementation work
- SQL: Planned under `sql/...` with a declared executable dialect
- Tests: Planned under `tests/...`
- Data: Planned safe JSON Lines fixture under `data/...`
- Try it: Manual classification and aggregation from the six-row table above
- Expected result: Two published rows, one quarantined identity, one duplicate
  delivery, one valid outside interval, and one valid deferred event
- Evidence: Manual contract, boundary, arithmetic, lineage, and failure review
- Scale represented: Six-row local reasoning fixture plus production estimate
- Remaining risk: All runtime, integration, distributed, security-negative,
  performance, resilience, operational, delivery, and production evidence

## Knowledge check

1. Predict the corrected output after the cutoff advances to include `e6`.
2. Diagnose how counts change if deduplication occurs after aggregation.
3. Design reconciliation equations for delivery rows through published identities.
4. Estimate storage and batch throughput if the high-case assumptions from guide
   03 apply, then name the first measurements needed.
5. Propose an additive `device_class` field migration, historical backfill,
   consumer cutover, and rollback.
6. Replace the daily consumer with a five-minute alert and identify every contract
   that must change before selecting technology.

## Key takeaways

- Start with grain, authority, consumer contract, and invariants—not tools.
- Stable identity, explicit time boundaries, and reconciliation make reruns explainable.
- Immutable input plus atomic publication creates a safe correction path.
- Invalid, duplicate, late, partial, and overloaded states need owned behavior.
- Paper evidence validates design reasoning only; production claims require
  executable, real-engine, scale, fault, security, and operational evidence.

## Resources

- [Python documentation](https://docs.python.org/3/)
- [PostgreSQL documentation: Queries](https://www.postgresql.org/docs/current/queries.html)
- [Apache Iceberg specification](https://iceberg.apache.org/spec/)
- [OpenLineage specification](https://openlineage.io/docs/spec/)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)

## Related topics

- [Area README](README.md)
- [Data lifecycle, control plane, and data plane](02-data-lifecycle-control-plane-and-data-plane.md)
- [Correctness, freshness, latency, throughput, and cost](06-correctness-freshness-latency-throughput-and-cost.md)
- [Data architecture patterns and trust boundaries](07-data-architecture-patterns-and-trust-boundaries.md)

## Completion checklist

- [x] Durable concept, objectives, prerequisites, non-goals, and mental model included
- [x] Grain, owners, consumers, authority, trust, identity, time, and consistency explicit
- [x] Scale, freshness, correctness, availability, retention, privacy, and cost estimated
- [x] Duplicate, invalid, late, retry, overload, partial output, and recovery traced
- [x] SQL model and Python/runtime responsibilities described with limits
- [x] Quality, security, observability, compatibility, backfill, and rollback addressed
- [x] Manual fixture evidence and remaining risks recorded accurately
- [x] Practical prediction, diagnosis, design, estimate, migration, and modification exercises included
- [ ] Executable Python, SQL, fixture, and tests implemented and run
- [ ] Real storage, distributed, performance, resilience, security, and production evidence collected
