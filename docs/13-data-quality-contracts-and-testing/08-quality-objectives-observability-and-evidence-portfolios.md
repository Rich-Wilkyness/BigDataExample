# Quality Objectives, Observability, and Evidence Portfolios

> Status: Documentation complete; executable operational evidence planned  
> Level: Intermediate to Senior  
> Applies to: Data products / Pipelines / Platforms / Operations  
> Data scale: Local receipt fixture; production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

A data quality indicator measures consumer-relevant behavior over an eligible
population. An objective defines the target and window. Observability connects a
bad outcome to the dataset version, input frontier, rule results, lineage, and
owning boundary. An evidence portfolio combines complementary tests, runtime
checks, reconciliations, rehearsals, and production observations according to
risk.

A dashboard is not an objective, an alert is not evidence of root cause, and a
large test count is not coverage. Senior practice makes evidence gaps and
response tradeoffs visible.

## Learning objectives

- Define data SLIs/SLOs with populations, windows, exclusions, and error budgets.
- Design quality receipts, metrics, logs, lineage, dashboards, and actionable alerts.
- Measure detection, containment, repair, and consumer recovery delays.
- Build risk-to-evidence portfolios and expose unverified assumptions.
- Govern objective changes, exceptions, and operational reviews.

## Prerequisites

- All earlier guides in this area, especially [requirements](01-data-quality-dimensions-requirements-and-ownership.md), [runtime checks](06-reconciliation-freshness-volume-and-distribution-checks.md), and [quality incidents](07-quarantine-repair-replay-and-quality-incidents.md).
- Area 12 artifacts/operations; Area 15 will deepen general reliability, observability, performance, and incident operations.

## Mental model and terminology

```text
consumer harm model
      |
      v
SLI population + good criterion + window
      |
      v
objective/error budget ----> actionable alert policy
      |                              |
      v                              v
quality receipt + lineage ----> diagnosis/runbook
      |
      v
risk-to-evidence portfolio and review
```

| Term | Meaning in this guide |
| --- | --- |
| DQI/SLI | Quantitative measure of data behavior for a defined eligible population |
| Objective/SLO | Target level for an indicator over a time window; not automatically a legal SLA |
| Error budget | Allowed bad fraction or duration implied by the objective |
| Quality receipt | Immutable result bundle tying a dataset version to inputs, rules, and decisions |
| Burn rate | Rate at which bad events consume the allowed error budget |
| Evidence portfolio | Set of complementary evidence mapped to risks, environments, and known gaps |
| Detection coverage | Which named failure modes can be detected, at what delay and false-positive rate |

An SLO resembles a performance/error budget used in mobile release quality, but
data has several populations: rows, partitions, intervals, tenants, queries, or
consumer decisions. Averaging them without a harm model can hide total failure
for a small but critical segment.

## Requirements, scale assumptions, and invariants

- Each indicator specifies dataset/consumer, eligible events, good criterion,
  measurement point, time origin, window, segments, exclusions, missing-data
  treatment, and owner.
- Correctness and completeness requirements that permit no known violations are
  release gates, not converted into a forgiving aggregate objective without
  consumer approval.
- “Not measured” and “check unavailable” are distinct from good and bad.
- Quality receipts name publication, input frontier, code/schema/contract/rule
  versions, check statuses, counts/denominators, thresholds, exceptions, and
  certification decision.
- Alerts represent actionable threats to consumer objectives, route to an owner,
  and link a runbook. Dashboards may show diagnostic signals that never page.
- Detection delay, time to contain, time to corrected certification, and time to
  consumer recovery use explicit timestamps and incident scope.
- Metric labels remain bounded; publication/run/event IDs belong in logs, traces,
  lineage, or quality-result tables rather than metric dimensions.
- Initial hypothesis: 99% of eligible daily tenant publications become certified
  within 120 minutes of source readiness over 28 days. Consumer review,
  backtesting, and production evidence are pending.

## Indicator definitions

For daily freshness:

```text
eligible = tenant/date publications whose producer readiness frontier was declared
good     = eligible publication certified within 120 minutes of readiness
SLI      = good / eligible over rolling 28 days
target   = 99%
missing  = bad after the deadline, not removed from the denominator
segments = tenant tier and contract version for diagnosis; critical tiers may own separate objectives
```

For record accounting:

```text
eligible = producer control records for a fixed tenant/date/frontier
good     = received == accepted deliveries + rejected + unreadable
target   = 100% before certification
missing control = unavailable and blocking, not good
```

The first tolerates late publications across a service window. The second is an
invariant gate for each publication. Combining them into one score would hide
which guarantee failed.

## Quality receipt model

```json
{
  "dataset": "daily_product_views",
  "publication_id": "candidate-2026-09-07-v3",
  "input_frontier": "producer-control-2026-09-07",
  "code_version": "example-revision",
  "contract_version": "metric-v3",
  "quality_suite_version": "quality-v5",
  "checks": [
    {
      "rule_id": "metric-grain-unique-v1",
      "status": "pass",
      "eligible": 3000000,
      "violations": 0,
      "blocking": true
    }
  ],
  "decision": "certify"
}
```

The example is illustrative; receipts need canonical serialization, integrity,
schema evolution, access control, durable storage, and transactional association
with publication. A success receipt cannot be emitted before the corresponding
dataset commit is authoritative.

## Observability design

| Signal | Contents | Use | Guardrail |
| --- | --- | --- | --- |
| Structured event | Rule/run/publication, status, duration, safe reason | Timeline and correlation | No raw row/payload; bounded reason |
| Metric | Pass/fail/unavailable counts, latency, backlog age, SLI | Trends and alerts | Low-cardinality labels only |
| Quality result table | Segmented numerators, denominators, examples refs | Diagnosis/audit | Row/tenant access and retention |
| Trace | Orchestrator, query/job, check, publication spans | Cross-system latency/failure | Sampling and context propagation |
| Lineage | Input/output versions and transform/check links | Blast radius and replay scope | Record confidence and missing edges |
| Dashboard | Objectives, burn, frontiers, checks, backlog | Shared operational view | Show missing/stale telemetry |

Telemetry is another data pipeline. Its loss must display as unknown; stale green
values cannot authorize publication.

## Alert policy

Page only when immediate human action can reduce material consumer harm. Fast and
slow multi-window burn signals can distinguish acute loss from sustained drift;
the thresholds must be derived from the objective and backtested in the chosen
monitoring system. Deterministic publication-gate failures can notify the owning
run immediately without becoming a global page unless delay threatens the SLO.

Every page includes dataset/consumer, objective, affected segment/window,
current/prior publication, first failure, likely owning boundary, safe immediate
action, and runbook. Warning-only alerts become tickets or dashboard signals with
an explicit review cadence.

## Risk-based evidence portfolio

| Risk | Prevent/detect before release | Runtime evidence | Recovery evidence | Current gap |
| --- | --- | --- | --- | --- |
| Invalid event identity | Schema/semantic unit and contract tests | Rejection/accounting invariant | Producer fix + bounded replay | All executable evidence pending |
| Duplicate metric | Property/SQL grain tests | Uniqueness and reconciliation | Idempotent rebuild | Faulted engine evidence pending |
| Missing tenant/date | Control fixture/end-to-end test | Segmented completeness/frontier | Restore/reingest and recertify | Independent controls pending |
| Silent semantic change | Consumer contract/differential tests | Distribution and consumer reconciliation | Versioned metric backfill/cutover | Consumer journey pending |
| Late publication | Schedule/freshness simulation | Freshness SLI/burn | Catchup with current-work reserve | Production latency baseline pending |
| Unsafe quarantine | Security/negative-access tests | Access audit/backlog/retention | Delete/revoke/incident process | Privacy review pending |
| Bad repair | Manifest/replay integration tests | Post-repair end-to-end reconciliation | Withdraw corrected candidate and rerun | Incident drill pending |

Evidence is strongest when methods fail independently. Unit and SQL tests copied
from the same implementation are correlated; an external control, consumer
query, or fault rehearsal can expose different defects.

## Data flow, ownership, and trust boundaries

| Boundary | Owner | Guarantee | Failure behavior |
| --- | --- | --- | --- |
| Rule execution | Dataset/quality owner | Correct result for one snapshot/version | Explicit failed/unavailable status |
| Receipt store | Platform + dataset owner | Immutable, queryable decision evidence | Block certification if required write fails |
| Publication | Dataset owner | Active version has matching required receipt | Conditional atomic activation |
| Telemetry pipeline | Platform owner | Timely signals with known lag | Surface telemetry unknown/stale |
| Alert/on-call | Operational owner | Actionable routing and acknowledgement | Escalate by policy |
| Consumer review | Consumer owner | Objectives reflect real use/harm | Renegotiate or stop unsupported dependency |

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Receipt emitted before commit | Receipt/publication mismatch | Revoke candidate receipt; make post-commit/outbox atomic |
| Telemetry missing appears green | Heartbeat/lag and unknown status | Restore telemetry; reevaluate affected decisions |
| Global SLO hides critical tenant | Segmented objective/error budget | Define harm-weighted or separate critical objective |
| Alert pages on every row failure | Alert review and page volume | Route local failure to workflow; page on consumer threat |
| Dashboard changes denominator | Definition/version diff | Restore versioned query and annotate migration |
| Evidence shares one defective oracle | Incident escapes all checks | Add independent control/consumer/recovery method |
| Objective met but consumer harmed | Consumer feedback and incident | Revise indicator/target and backtest; preserve history |

## Security, privacy, and governance

Receipts, labels, samples, lineage, and incident records can expose tenants,
identifiers, query text, or sensitive distribution. Minimize, tokenize where
appropriate, enforce row/column access, audit, retain deliberately, and propagate
deletion. Protect objective/rule changes with review and immutable history.
Exceptions name approver, scope, reason, expiry, compensating control, and
affected consumers; an expired exception fails closed according to policy.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Receipt schema/state | Planned pass/fail/unavailable fixtures / local | Validate decisions and publication association | No unavailable required check certifies | Pending |
| SLI calculation | Planned fixed timeline / SQL/Python | Include late/missing/critical segments | Exact documented numerator/denominator | Pending |
| Alert backtest | Labeled incident/normal history | Replay burn policies | Measured detection and page load | Pending |
| Telemetry fault | Integration environment | Delay/drop result and receipt signals | Unknown/stale visible; gate safe | Pending |
| Portfolio drill | Staged end-to-end quality incident | Detect through consumer recovery | Evidence gaps and timings recorded | Pending |

## Debugging guide

1. Start from affected consumer/objective, then capture publication, receipt, rule suite, frontier, and telemetry timestamp.
2. Recalculate numerator/denominator and missing-data handling from immutable results.
3. Follow lineage to the earliest incorrect or unavailable boundary; inspect check query/job IDs and safe failure rows.
4. Compare the evidence portfolio with the actual failure path to identify why prevention/detection missed it.
5. Contain publication/consumer harm, repair and reconcile, then confirm telemetry recovery separately.
6. Update tests, indicators, runbook, ownership, and tracked evidence gaps with an accountable due date.

## Common pitfalls

### Pitfall: count checks as coverage

Many checks can share one blind spot. Map failure modes and harms to independent
prevention, detection, and recovery evidence.

### Pitfall: alert on every failed rule

This overloads on-call and hides consumer impact. Route local diagnostics to the
workflow owner; page on actionable objective threat.

### Pitfall: omit missing intervals from the SLI

The worst outages disappear from the denominator. Define eligibility before
observing success and represent unavailable telemetry explicitly.

## Performance, capacity, and cost

Measure receipt/check result volume, metric cardinality, trace/sample rate,
lineage edges, dashboard query cost, alert evaluation latency, telemetry lag,
retention, and operator page load. At 1,000 datasets and many segments, per-row
metrics are infeasible; aggregate metrics link to access-controlled result tables.
Quality checks share the publication window and need workload isolation.

## Compatibility, migration, and delivery

Version indicator definitions, objective targets, receipt schemas, rule suites,
dashboard queries, alert policies, and runbooks. Shadow and backtest changes,
dual-publish old/new indicators, explain discontinuities, then cut over with
rollback. Contract/metric definition changes may reset comparability; never splice
incompatible histories without an annotation.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Gate every deterministic rule | Violation threatens correctness/privacy | Availability loss from false failure | Rule/authority is nondeterministic |
| Sample diagnostics | Full scan cost exceeds diagnostic value | Rare defects can escape | Zero-tolerance or small critical segment |
| One global objective | Harm is genuinely homogeneous | Small critical consumers disappear | Tiers or failure domains differ |
| Separate receipt store | Cross-system audit/discovery matters | Atomic association is harder | Engine transaction can include receipt safely |
| Multi-window burn alert | Objective/error budget is meaningful | More policy/testing complexity | No immediate action exists |

## Working example

- Models: Planned quality receipt and objective evaluator under `src/big_data_example/quality/`
- SQL: Planned SLI and segmented evidence queries under `sql/quality/`
- Tests: Planned receipt-state, missing-interval, alert-backtest, and fault cases
- Operations: Planned dashboard specification, alert policy, and incident runbook
- Try it: Planned deterministic local evaluation plus integration telemetry fault drill
- Expected result: Required unknown/failure blocks certification; alerts reflect consumer threat
- Evidence: Planned receipts, SLI calculations, backtest, fault timeline, and portfolio review
- Scale represented: Local fixture and production estimate; no operational evidence yet
- Remaining risk: Monitoring semantics, independent signals, cardinality/cost, on-call behavior, and production harm model

## Knowledge check

1. Explain the difference among a data check, SLI, SLO, and alert.
2. Predict how excluding missing publications biases a freshness SLI.
3. Diagnose a green dashboard built from a stalled telemetry pipeline.
4. Design a quality receipt that cannot certify before the dataset commit.
5. Estimate observability cardinality for 1,000 datasets and tenant segments.
6. Plan an objective-definition migration with comparable history.
7. Add prevention, runtime, and recovery evidence for one uncovered risk.

## Key takeaways

- Indicators begin with consumer harm and an eligible population.
- Unknown evidence stays unknown; it never silently becomes green.
- Quality receipts bind checks to the exact dataset/input/version decision.
- Alert on actionable threats; retain richer diagnostics outside page labels.
- A portfolio maps risks to complementary evidence and visible gaps.

## Resources

- [Google SRE Workbook: implementing SLOs](https://sre.google/workbook/implementing-slos/) (reviewed 2026-09)
- [Google SRE Workbook: alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) (reviewed 2026-09)
- [OpenTelemetry metrics data model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/) (reviewed 2026-09; version-sensitive implementation behavior must be pinned)
- [OpenLineage facets and extensibility](https://openlineage.io/docs/spec/facets/) (reviewed 2026-09; optional lineage implementation reference)

## Related topics

- [Reconciliation and runtime checks](06-reconciliation-freshness-volume-and-distribution-checks.md)
- [Quality incidents](07-quarantine-repair-replay-and-quality-incidents.md)
- Area 15 reliability, observability, performance, cost, and operations (planned)

## Completion checklist

- [x] Indicators, objectives, budgets, receipts, signals, alerts, and portfolios defined
- [x] Missing evidence, consumer harm, ownership, security, failure, cost, migration, and recovery covered
- [x] Detection delay and evidence independence made explicit
- [x] Working example and executable evidence accurately marked Planned
- [ ] Receipt, SLI, alert, telemetry-fault, portfolio-drill, load, and production evidence executed
