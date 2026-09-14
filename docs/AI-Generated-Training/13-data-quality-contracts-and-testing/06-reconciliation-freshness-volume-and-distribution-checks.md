# Reconciliation, Freshness, Volume, and Distribution Checks

> Status: Documentation complete; executable runtime-check evidence planned  
> Level: Intermediate to Senior  
> Applies to: Batch / Streaming / Warehouses / Lakehouses / Serving datasets  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Runtime dataset checks ask whether a particular version is plausibly complete,
timely, internally valid, and consistent with an authority. Reconciliation
accounts for records or measures across boundaries. Freshness compares usable
data with a meaningful frontier. Volume and distribution checks detect missing,
duplicated, or shifted populations. Statistical anomaly detection proposes
suspects; it does not explain them or replace deterministic contracts.

## Learning objectives

- Reconcile counts and measures with explicit accounting identities.
- Distinguish event, ingestion, source-ready, processing, and publication time.
- Design segmented volume and distribution checks with stable denominators.
- Backtest thresholds and control false positives, blind spots, and baseline drift.
- Diagnose gaps without exposing sensitive row samples.

## Prerequisites

- [Quality requirements](01-data-quality-dimensions-requirements-and-ownership.md).
- [Fixtures and sampling](05-fixtures-golden-datasets-sampling-and-determinism.md).
- Area 03 aggregation/`NULL`, Area 05 grain, and Areas 07/10 interval/frontier semantics.

## Mental model and terminology

```text
source authority/frontier
      |  control counts, sums, positions
      v
accepted + rejected + documented duplicate/exclusion accounting
      |
      v
candidate output at declared grain
      |  deterministic rules + baselined diagnostics
      v
quality receipt -> certification or hold
```

| Term | Meaning in this guide |
| --- | --- |
| Reconciliation | Comparison through an explicit accounting identity between sufficiently independent states |
| Control total | Authoritative count, sum, checksum, or position used in reconciliation |
| Frontier | Boundary up to which input is declared complete or processing/certification has progressed |
| Freshness | Delay between a relevant source/event/readiness time and consumer-usable publication |
| Distribution check | Compares categorical or numerical population shape across versions/segments |
| Baseline | Versioned reference behavior and exclusions used by an anomaly rule |
| Detection delay | Time from the first harmful condition to detection/notification |

## Requirements, scale assumptions, and invariants

- Reconciliation operates at tenant and UTC date before global aggregation.
- For a fixed raw frontier: `received = accepted deliveries + rejected + unreadable`.
  Separately, `accepted deliveries = unique logical accepted + exact duplicate
  deliveries`; conflicting duplicates are counted explicitly, never discarded.
- Metric reconciliation compares unique eligible logical events with aggregated
  view counts after named exclusions.
- A missing control total is `unverifiable`, not zero and not pass.
- Freshness starts at producer readiness for daily completeness and at event time
  for consumer latency; both may be reported, but not conflated.
- Checks read a consistent input/candidate snapshot and write immutable results
  before certification.
- Deterministic zero-tolerance rules gate publication. Statistical signals begin
  in observation mode and require backtesting, segmentation, and owner review.
- Expected scale is 3 million events/day, 100 million retained events, 500/s
  burst, and 35% hot tenant. Thresholds, normal seasonality, scan time, and cost
  are unmeasured.

## Reconciliation model

```sql
-- Dialect-neutral sketch. Grain: one tenant and UTC source date.
-- Each input relation must come from the same declared frontier/snapshot.
with accounted as (
  select tenant_id, source_date,
         sum(accepted_delivery_count) as accepted_deliveries,
         sum(rejected_count) as rejected,
         sum(unreadable_count) as unreadable
  from ingestion_accounting
  group by tenant_id, source_date
)
select c.tenant_id, c.source_date,
       c.received_count,
       a.accepted_deliveries + a.rejected + a.unreadable as accounted_count
from producer_controls c
left join accounted a
  on a.tenant_id = c.tenant_id and a.source_date = c.source_date
where c.received_count is null
   or a.accepted_deliveries is null
   or c.received_count <> a.accepted_deliveries + a.rejected + a.unreadable;
```

The producer control must be independent enough to expose loss. If it is computed
from the same incomplete landing files, agreement proves only internal
consistency. Counts can agree while values differ, so high-risk money-like or
business measures may also require sums, keyed checksums, or record-level anti-
joins with clear decimal and `NULL` semantics.

```sql
-- Metric-level check: one failing tenant/product/date.
with expected as (
  select tenant_id, product_id, metric_date, count(*) as expected_views
  from unique_eligible_product_views
  group by tenant_id, product_id, metric_date
)
select coalesce(e.tenant_id, m.tenant_id) as tenant_id,
       coalesce(e.product_id, m.product_id) as product_id,
       coalesce(e.metric_date, m.metric_date) as metric_date,
       e.expected_views, m.view_count
from expected e
full outer join candidate_daily_product_views m
  on e.tenant_id = m.tenant_id
 and e.product_id = m.product_id
 and e.metric_date = m.metric_date
where e.expected_views is distinct from m.view_count;
```

`IS DISTINCT FROM` and `FULL OUTER JOIN` support vary by engine; verify the pinned
dialect. An “independent” query that repeats the same faulty join is a weak oracle.

## Time and freshness model

```text
event time ----> ingestion time ----> source-ready time ----> publication time
    |                 |                      |                       |
user reality     transport delay       complete frontier      consumer usable
```

For eligible publication `i`, define daily readiness freshness as
`publication_time_i - source_ready_time_i`. Define the SLI as the fraction
published within 120 minutes over a 28-day window. Missing eligible intervals
remain in the denominator. A latest-row timestamp alone can look fresh while
most partitions are absent; track frontier coverage by required segment.

## Volume and distribution checks

| Signal | Good use | Failure mode | Guardrail |
| --- | --- | --- | --- |
| Absolute min/max count | Known physical/business bound | Growth makes static bound stale | Version and review capacity assumptions |
| Ratio to prior comparable period | Stable seasonal workload | Holidays/releases shift legitimately | Calendar/cohort baseline and shadow mode |
| Segment share | Tenant/version/category outage or surge | Small segment is noisy | Minimum denominator and multiple windows |
| Quantiles/histogram | Numeric latency/value shift | Approximation/bin changes mimic drift | Pin method/bins and compare error bounds |
| Distinct count | Key/cardinality collapse | Approximate estimates fluctuate | Tolerance from measured estimator error |
| `NULL`/accepted-value rate | Field population drift | New legitimate category | Contract-version segmentation |

A global count can remain stable while one tenant disappears and another doubles.
Segment by failure domains and consumer risk, but keep observability labels
bounded; store high-cardinality results in queryable quality tables.

## Statistical baseline model

```python
from dataclasses import dataclass
from statistics import median

@dataclass(frozen=True)
class RelativeBand:
    lower_ratio: float
    upper_ratio: float

def outside_median_band(current: int, comparable_history: list[int], band: RelativeBand) -> bool:
    if current < 0 or not comparable_history or any(value < 0 for value in comparable_history):
        raise ValueError("nonnegative current and history required")
    center = median(comparable_history)
    if center == 0:
        raise ValueError("zero baseline requires an explicit cold-start policy")
    ratio = current / center
    return ratio < band.lower_ratio or ratio > band.upper_ratio
```

This is a teaching baseline, not a generally adequate anomaly detector. It does
not model trend, multiple seasonalities, autocorrelation, releases, or skew. Its
window, exclusions, and thresholds must be backtested against labeled history.

## Data flow, ownership, and trust boundaries

| Boundary | Authority/owner | Failure behavior | Trust level |
| --- | --- | --- | --- |
| Producer control | Producer-owned independent count/frontier | Mark unavailable and hold required reconciliation | External authority |
| Ingestion accounting | Ingestion owner | Immutable reason/control counts | Derived control |
| Candidate profile | Dataset owner | Never profile mixed versions | Uncertified data |
| Baseline store | Quality/dataset owner | Version, exclude incidents with review | Fallible historical model |
| Certification | Dataset owner | Required unavailable/fail prevents activation | Governed decision |
| Alert channel | Operations owner | Route actionable burn, retain receipt | Operational control |

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Shared source and control lose same files | Independent producer position/control disagrees | Restore source; recompute accounting |
| Counts match but amounts/keys differ | Measure checksum or keyed anti-join | Repair transform and affected publication |
| Latest timestamp masks missing tenants | Per-segment frontier coverage | Recover missing segment and recertify |
| Baseline absorbs incident | Version/change review and labeled history | Rebuild baseline excluding incident |
| Expected launch triggers alert | Change calendar/release annotation | Validate event, adjust reviewed baseline—not raw threshold bypass |
| Approximate distinct count fluctuates | Error-bound-aware comparison | Recompute exact diagnostic where feasible |
| Check queries stale/mixed snapshots | Publication IDs do not align | Re-evaluate one consistent snapshot |

## Security, privacy, and governance

Prefer aggregate controls and protected keyed hashes; recognize that small-cell
counts and distributions can still reveal individuals or tenants. Suppress or
restrict sensitive segments, sanitize failure samples, control query access, and
apply retention/deletion to quality tables. Store rule/baseline provenance,
approvals, exceptions, and query lineage.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Accounting fixture | Planned accepted/rejected/duplicate/gap cases / SQL | Execute source accounting identity | Every injected gap is localized | Pending |
| Metric differential | Planned fan-out/omission cases / SQL | Compare candidate with independent oracle | Key/value differences returned | Pending |
| Freshness clock | Planned fixed timeline | Evaluate event/readiness/publication delays | Missing intervals stay in denominator | Pending |
| Baseline backtest | Labeled synthetic/history-safe measurements | Sweep thresholds and segments | Detection delay/false positives measured | Pending |
| Scale/cost | Production-shaped data / real engine | Profile full and incremental checks | Meets gate window and cost budget | Pending |

## Debugging guide

1. Capture dataset/publication, input frontier, control version, rule/baseline version, interval, and segments.
2. Validate numerator, denominator, `NULL`, exclusions, time domain, and snapshot alignment.
3. Follow the accounting identity from producer controls through accepted, rejected, duplicate, and output totals.
4. Localize by tenant, source partition, contract/client version, and event type in protected queries.
5. Determine deterministic violation, control failure, expected business shift, or statistical false positive.
6. Hold publication if required; repair, replay, reconcile, and record detection/recovery times.

## Common pitfalls

### Pitfall: compare only with yesterday

Weekly seasonality, launches, and incidents cause noise or missed shifts. Use
comparable cohorts/windows and backtest.

### Pitfall: treat no control row as zero

This turns an unavailable authority into a false result. Preserve `unverifiable`
as a first-class status.

### Pitfall: sample a zero-tolerance rule

Sampling can miss a rare duplicate or privacy violation. Use full deterministic
checks or preventive constraints where the guarantee requires zero violations.

## Performance, capacity, and cost

Budget certification checks inside the publication window. Measure rows/bytes
scanned, shuffle, distinct-state memory, spill, partition pruning, control size,
baseline storage, query concurrency, p95 duration, and monetary cost. Incremental
profiles need correction/backfill logic and periodic full reconciliation to test
their own state.

## Compatibility, migration, and delivery

Version accounting formulas, baselines, bins, hash/approximation algorithms, and
time semantics. Shadow new checks on historical and current data, compare old/new
results, then gate. During schema or metric migration, reconcile old and new
publications over overlapping intervals and preserve consumer-visible version
labels. Backfills use the historical rule context or an explicit restatement.

## Working example

- SQL: Planned accounting, metric anti-join, freshness, volume, and distribution checks under `sql/quality/`
- Python: Planned deterministic baseline evaluator under `src/big_data_example/quality/`
- Fixtures: Planned gaps, duplicates, fan-out, skew, and time cases under `data/fixtures/quality/`
- Try it: Planned local test suite plus pinned-engine quality command
- Expected result: Faults localize by boundary/segment; unavailable controls do not pass
- Evidence: Planned quality receipt, backtest report, plan/runtime, and cost
- Scale represented: Local fixture first; production-shaped real-engine run separate
- Remaining risk: Independent controls, seasonal history, engine plans, production thresholds, and cost

## Knowledge check

1. Explain why agreement with a control derived from the same files is weak completeness evidence.
2. Predict the result of dropping a tenant while another tenant's count rises equally.
3. Diagnose a freshness metric based only on maximum event time.
4. Design an accounting identity for accepted, rejected, duplicated, and unreadable events.
5. Estimate full-scan versus partition-profile cost at 100 million rows.
6. Plan a baseline algorithm migration without rewriting history.
7. Add one distribution check with segments and a minimum denominator.

## Key takeaways

- Reconciliation starts with an explicit identity and sufficiently independent authority.
- Freshness names its time origin, eligible population, and missing-interval behavior.
- Global volume can hide local outages; segment by risk and failure domain.
- Statistical anomalies are diagnostic signals, not semantic proof.
- Version controls, baselines, approximations, and quality receipts.

## Resources

- [PostgreSQL aggregate functions](https://www.postgresql.org/docs/current/functions-aggregate.html) (reviewed 2026-09; engine-specific `NULL` behavior)
- [NIST/SEMATECH e-Handbook: process monitoring](https://www.itl.nist.gov/div898/handbook/pmc/pmc.htm) (reviewed 2026-09)
- [Google SRE Workbook: implementing SLOs](https://sre.google/workbook/implementing-slos/) (reviewed 2026-09)

## Related topics

- [Quality requirements](01-data-quality-dimensions-requirements-and-ownership.md)
- [Fixtures and sampling](05-fixtures-golden-datasets-sampling-and-determinism.md)
- [Quality objectives](08-quality-objectives-observability-and-evidence-portfolios.md)

## Completion checklist

- [x] Reconciliation, controls, frontiers, freshness, volume, distributions, and baselines explained
- [x] `NULL`, segments, time, authority, approximation, failure, privacy, cost, and migration covered
- [x] Deterministic and statistical evidence limits explicit
- [x] Working example and executable evidence accurately marked Planned
- [ ] SQL, control, backtest, engine, scale, cost, and production evidence executed

