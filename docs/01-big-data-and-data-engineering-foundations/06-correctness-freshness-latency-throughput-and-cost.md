# Correctness, Freshness, Latency, Throughput, and Cost

> Status: Documentation complete  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / Batch / Streaming / Storage / Platform  
> Data scale: Local fixture through production estimate  
> Example status: Complete requirement model  
> Evidence status: Requirements / Capacity estimate  
> Last reviewed: 2026-09

## Overview

A useful data system turns vague expectations—fast, accurate, reliable, cheap—
into measurable contracts. Correctness asks whether the result has the promised
meaning. Freshness asks how current it is. Latency measures elapsed time for a
defined operation or record path. Throughput measures completed work per time.
Cost includes money and constrained resources, including operational effort.

These objectives conflict. This guide shows how to define and prioritize them
without claiming that one metric captures all consumer value.

## Learning objectives

After completing this guide, you should be able to:

- Define correctness, completeness, freshness, latency, throughput, availability,
  durability, recovery, and cost for a named consumer.
- Select indicators, windows, percentiles, and budgets with units.
- Explain why lowering latency can increase cost or weaken completeness.
- Design error budgets and degradation behavior for a data product.
- Diagnose whether a miss originates in demand, processing, publication, or serving.

## Prerequisites

Read [Volume, velocity, variety, and when data becomes big](03-volume-velocity-variety-and-when-data-becomes-big.md)
and [Sources, sinks, authority, and derived data](05-sources-sinks-authority-and-derived-data.md).

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Correctness | Degree to which data satisfies its declared structural and semantic contract |
| Completeness | Required eligible records or fields present relative to a defined reference |
| Freshness | Age of the latest complete trustworthy data relative to its expected cutoff |
| Latency | Elapsed time between two named boundaries, reported as a distribution |
| Throughput | Successfully completed records, bytes, queries, or jobs per unit time |
| Availability | Fraction of valid demand for which the contracted result is usable |
| SLI/SLO | Measured indicator and its target over a stated window |
| Error budget | Allowed amount of objective miss within that window |

## Requirements, scale assumptions, and invariants

For the daily dashboard example:

| Concern | Proposed contract | Measurement boundary |
| --- | --- | --- |
| Correctness | No duplicate accepted `event_id`; aggregate equals eligible valid inputs | Raw accepted version to curated version |
| Completeness | At least 99.9% of accepted, eligible events represented or explicitly rejected | Declared cutoff and validation report |
| Freshness | Prior UTC day published by 09:00 America/Denver on 99% of days/month | Event interval end to successful version publication |
| Availability | Latest successful version queryable for 99.9% of valid requests/month | Serving boundary |
| Batch latency | p95 run duration under 45 minutes | Run admitted to atomic publish |
| Throughput | At least 1,250 events/s sustained during normal batch | Validated and accounted output |
| Recovery | RPO: no durably accepted raw events lost; RTO: four hours for curated restore | Accepted raw boundary to restored consumer result |
| Cost | Monthly allocation and alert threshold to be established from measured platform prices | Ingestion + storage + processing + serving + operations |

These are teaching targets, not production evidence. Privacy, deletion, and
security requirements are constraints, not expendable error budget.

Invariants: metrics use stable definitions and units; failed/rejected work is not
counted as successful throughput; freshness never hides correctness state; and
every objective names a consumer, owner, window, and response.

## Mental model

```text
event occurs -> accepted -> input closes -> job starts -> publishes -> consumer reads
      |<------- data age / end-to-end latency ----------------------->|
                              |<--- run latency --->|
                                             |<-- serving latency -->|

correctness + completeness qualify whether any timestamp is trustworthy
throughput and capacity determine whether backlog grows
cost constrains every stage
```

Android performance offers a useful analogy: frame time, startup time, crash-free
users, and APK size are different signals; one green metric cannot declare the
app healthy. The analogy stops where data correctness can require historical
reconciliation long after a request completed successfully.

## Measurement design

For every indicator define numerator, denominator, eligible population,
exclusions, time zone/window, data source, delay, and owner. Prefer percentiles
for latency because averages hide slow tails. Pair backlog size with oldest item
age: ten delayed records might matter more than a million recent ones.

Correctness is multi-dimensional. Use schema validity, non-null required values,
unique identity, referential integrity, accepted-to-output reconciliation, domain
bounds, and known-answer fixtures. “The query ran” measures execution, not truth.

## Data flow, ownership, and trust boundaries

| Boundary | Indicator | Owner | Failure behavior | Trust concern |
| --- | --- | --- | --- | --- |
| App/collector | acceptance success and latency | Ingestion with producer | Bounded retry/backpressure | Client timestamps and payload untrusted |
| Collector/raw | acknowledged-to-committed reconciliation | Ingestion/storage | Alert and stop unsafe acknowledgement | Restricted raw identifiers |
| Raw/curated | completeness, rejects, run latency, version | Pipeline/data product | Hold publication on critical checks | Quality rules are versioned control data |
| Curated/serving | publication age, query availability/latency | Serving owner | Last known good with staleness marker | Access and tenant scope enforced |
| Dashboard/user | visible cutoff and correction state | Consumer/product owner | Avoid silent zero or partial data | Metrics reveal business behavior |

## Conflicts and decisions

| Pressure | Tempting action | Risk | Safer decision rule |
| --- | --- | --- | --- |
| Lower freshness delay | Publish before input/checks complete | Incorrect or partial result | Define completeness cutoff and provisional status |
| Higher throughput | Skip validation | Corruption propagates faster | Scale or prioritize checks by explicit severity |
| Lower cost | Remove recovery copies | RPO/RTO violation | Price against recovery contract |
| Higher availability | Serve stale cache silently | Wrong decision under hidden staleness | Expose version and age; define max safe staleness |
| Perfect correctness | Block forever on one bad record | Availability/freshness collapse | Quarantine under an approved error policy |

Business criticality decides priorities. There is no universal ordering, but
security and legal obligations are not traded away as performance tuning.

## Consistency, ordering, identity, and time

Freshness must name the time domain. A newly published table can be operationally
fresh yet contain data only through an old event-time cutoff. Duplicates inflate
throughput counters unless success uses unique accepted identity. Out-of-order
events complicate completeness. Use UTC instants internally, explicit business
calendars for reporting, and preserve receipt and publication times.

## Failure model and recovery

| Failure | Observable signal | Immediate response | Recovery proof |
| --- | --- | --- | --- |
| Source volume drops | Volume/completeness anomaly | Investigate before publishing believable zeros | Reconcile with source/acceptance control totals |
| Job slows | Duration, task skew, cutoff risk | Protect deadline, inspect bottleneck, add safe capacity | Backlog drains; p95 restored |
| Quality rule fails | Critical-check result | Hold new version; quarantine as policy allows | Corrected output matches eligible inputs |
| Serving outage | Availability/latency SLI | Fail over or restore last known good | Valid query and version/freshness confirmed |
| Cost spike | Spend and unit-cost anomaly | Isolate workload; enforce quota safely | Explain usage and restore budget trajectory |
| Telemetry failure | Missing/late indicators | Treat state as unknown; inspect primary boundaries | Monitoring and independent reconciliation agree |

## Security, privacy, and governance

SLI labels and samples must be low-cardinality and privacy-safe. Do not place
installation IDs, free-form screen names, query text with values, or rejected
payloads in general telemetry. Access quality results by role. Audit objective
and exclusion changes so teams cannot improve numbers by redefining eligible
data. Include deletion timeliness and unauthorized-access attempts where policy
requires them.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Requirement review | Shared scenario / paper | Check consumer, owner, units, boundary, window, response | Each target is measurable | Passed; table above |
| Throughput arithmetic | 3M events, 60-minute window, 50% headroom | `3,000,000 / 3,600 * 1.5` | 1,250 events/s | Passed as estimate |
| Indicator test | Deterministic fixture | Inject duplicate, reject, late record, partial output | Each changes the correct indicator | Pending |
| Load/fault test | Representative runtime | Run normal, burst, worker loss, backlog recovery | Targets and recovery met | Pending |

The model checks definitions and arithmetic, not achievability.

## Debugging guide

1. Name the missed consumer objective and interval.
2. Verify the indicator itself and its denominator before trusting the alert.
3. Decompose end-to-end delay into arrival, queue, scheduling, processing,
   publication, serving, and consumer refresh.
4. Compare event/byte rates, oldest age, rejects, reconciliation delta, task
   percentiles, skew, resource saturation, retries, and version state.
5. Mitigate without publishing unknown data; communicate cutoff and impact.
6. Restore, drain backlog, reconcile results, and confirm objective recovery.

## Common pitfalls

### Pitfall: freshness equals job success time

A job can publish at 08:00 using input through midnight two days ago. Measure the
latest complete trustworthy event interval, not only a green run timestamp.

### Pitfall: throughput without success semantics

Counting attempts rewards retry storms. Count durably accepted or correctly
published unique work and separately record failures/retries.

### Pitfall: every target is “five nines”

Targets should follow decision impact and realistic evidence. Excess targets
increase cost and can obscure correctness or recovery priorities.

## Performance, capacity, cost, and operations

Maintain a budget across stages: arrival delay + scheduling delay + processing +
quality/publication + serving/refresh must fit freshness. Track unit economics
such as cost per million accepted events, retained GiB-month, backfill day, and
thousand queries. Include people and incident load qualitatively even when not
assigned a dollar value. Review objectives after workload, consumer, price, or
architecture changes.

## Observability and operations

Dashboards pair service state with data state: accepted/unique/rejected counts,
reconciliation delta, cutoff and publication age, run/task latency, oldest
backlog age, availability, query latency, resource saturation, and cost. Alerts
must name owner and runbook, avoid unbounded labels, and distinguish no data from
no telemetry. Lineage connects an objective miss to dataset and code versions.

## Compatibility, migration, backfill, and delivery

Deploy metric-definition changes as versioned contracts. Compute old and new
indicators in parallel, preserve dashboards and alerts until comparison passes,
then migrate consumers. Backfills have separate throughput/cost budgets and must
not consume the daily pipeline's recovery headroom. Rollback restores both data
logic and compatible observability definitions.

## Engineering tradeoffs

Prefer an explicit priority order for each data product. For the teaching
dashboard: protect raw durability and metric correctness; publish the last known
good version with visible staleness; then optimize freshness, latency, and cost
within those constraints. A fraud or safety system could reasonably choose a
different order.

## Working example

The requirement and latency-budget tables are complete conceptual evidence.
Executable data-quality, load, fault, and cost evidence remains planned.

## Knowledge check

1. Explain why a p95 20-minute job does not imply data is fresh within 20 minutes.
2. Predict which indicators change when all records are retried twice.
3. Diagnose a green job with a sudden 40% count drop.
4. Allocate a 60-minute freshness budget across input readiness, scheduling,
   processing, validation, publication, and contingency.
5. Design a safe degradation mode when publication is late.

## Key takeaways

- Every objective needs a consumer, boundary, unit, window, owner, and response.
- Correctness and completeness qualify whether freshness and latency are useful.
- Throughput must count successful work; capacity must include recovery headroom.
- Faster, cheaper, and more available can conflict with correctness and each other.
- Operational and data-quality evidence must meet at the consumer boundary.

## Resources

- [Google SRE: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Workbook: Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [OpenTelemetry Metrics data model](https://opentelemetry.io/docs/reference/specification/metrics/data-model/)

## Related topics

- [Volume, velocity, variety, and when data becomes big](03-volume-velocity-variety-and-when-data-becomes-big.md)
- [Data architecture patterns and trust boundaries](07-data-architecture-patterns-and-trust-boundaries.md)
- [First end-to-end data pipeline](08-first-end-to-end-data-pipeline.md)

## Completion checklist

- [x] Correctness, freshness, latency, throughput, availability, recovery, and cost defined
- [x] Consumer, units, boundaries, windows, owners, and responses stated
- [x] Identity, time, failures, security, observability, migration, and tradeoffs addressed
- [x] Estimates explicitly separated from executable evidence
- [ ] Indicators, load, recovery, and unit cost measured in a runtime
