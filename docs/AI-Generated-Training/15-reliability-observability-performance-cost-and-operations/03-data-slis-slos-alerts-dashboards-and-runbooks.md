# Data SLIs, SLOs, Alerts, Dashboards, and Runbooks

> Status: Documentation complete; executable SLO and alert evidence planned  
> Level: Intermediate to Senior  
> Applies to: Data products / Pipelines / Platforms / Operations  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

A service-level indicator (SLI) quantifies a consumer-relevant outcome over a
defined eligible population. A service-level objective (SLO) sets a target over
a window; its error budget is the allowed bad portion. Dashboards communicate
state, alerts request action, and runbooks make the first safe actions executable.

Data systems need more than request uptime: publications can be late, incomplete,
incorrect, inaccessible, or unrecoverable. This guide generalizes Area 13 quality
objectives into a complete operational design without turning every metric into a page.

## Learning objectives

- Define availability, freshness, completeness, correctness, latency, lag, and recovery SLIs.
- Choose populations, windows, segments, exclusions, and missing-data behavior.
- Derive error budgets and alert policies from consumer harm and actionable response.
- Design dashboards that expose objectives, causes, deployments, and telemetry health.
- Write safe, owned, testable runbooks and backtest their alerts.

## Prerequisites

- [Reliability requirements](01-data-system-reliability-requirements-and-failure-domains.md), [telemetry design](02-logs-metrics-traces-lineage-and-correlation.md), and [Area 13 quality objectives](../13-data-quality-contracts-and-testing/08-quality-objectives-observability-and-evidence-portfolios.md).
- Planned fixed timeline and monitoring integration for executable evidence.

## Mental model and terminology

```text
consumer harm -> eligible population -> good/bad/unknown measurement -> SLI
                                                                  |
stakeholder target + window ------------------------------------> SLO
                                                                  |
allowed bad outcomes --------------------------------------> error budget
                                                                  |
fast/slow threat + human action -> alert -> dashboard -> runbook -> incident
```

| Term | Meaning in this guide |
| --- | --- |
| Eligible | Outcome that belongs in the denominator, defined before knowing success |
| Good event | Eligible outcome satisfying the exact consumer criterion |
| Unknown | Measurement is unavailable or stale; not silently good or excluded |
| Error budget | `eligible * (1 - target)` for a ratio objective, subject to definition/window |
| Burn rate | Observed bad rate divided by the bad rate allowed by the objective |
| Page | Interrupt demanding immediate human action to reduce material harm |
| Dashboard | Versioned operational view for status, diagnosis, planning, or review |
| Runbook | Tested decision/action sequence with prerequisites, safety checks, escalation, and verification |

An Android ANR SLO resembles a query-latency SLO. A daily batch has far fewer
events and delayed truth, so percentage arithmetic may be unstable: one missed
publication can consume the entire monthly budget. Use absolute guards or per-
critical-consumer objectives when the population is sparse.

## Requirements, scale assumptions, and invariants

Each SLI specifies consumer/dataset, eligible event, good criterion, measurement
point, time origin, window, segmentation, exclusions, correction, unknown handling,
owner, and query/version. Assume 100 tenants publish daily, giving roughly 2,800
tenant-days in a 28-day window. A 99% freshness objective allows about 28 bad
tenant-days; this teaching target is neither approved nor backtested.

Invariants:

- Eligibility is independent of successful output, so outages cannot vanish.
- Exactly one active receipt may match each expected tenant/date; duplicates fail a separate uniqueness gate rather than multiplying the SLI population.
- Correctness/reconciliation conditions requiring zero known errors remain release gates.
- Unknown and stale telemetry are explicit; policy defines whether they count bad or block a decision.
- Aggregation never hides a named critical tier or failure domain with materially different harm.
- Pages are actionable, owned, deduplicated, severity-aware, and linked to a tested runbook.
- Dashboard and alert definitions are versioned with the indicator semantics they display.
- Maintenance and exclusions are approved, bounded, recorded, and visible in history.

## Data flow, ownership, and trust boundaries

| Boundary | Owner/contract | Failure behavior |
| --- | --- | --- |
| Expected population | Producer/consumer contract owner | Missing expectation blocks trustworthy denominator |
| Measurement event | Dataset/platform owner | Late/duplicate events corrected by identity/window rule |
| SLI evaluator | Reliability owner | Failed evaluation reports unknown, not green |
| Monitoring store | Observability owner | Ingest/query lag displayed separately |
| Alert router | On-call owner | Delivery test and escalation path; no silent discard |
| Runbook/change systems | Service owner | Last reviewed/version visible; privileged action audited |

## Indicator and objective design

Example definitions:

```text
freshness eligible = expected tenant/date after source readiness is final
freshness good     = certified within 120 minutes of ready_at
availability eligible = authorized read requests for a supported publication
availability good     = response returns a certified version within 2 seconds
completeness gate     = accepted = represented + rejected for each publication
recovery SLI          = duration from incident declaration to consumer reconciliation
```

Do not combine these into one health score. A fresh but incorrect publication is
bad for correctness even if it helps freshness.

### SQL model

```sql
WITH outcomes AS (
  SELECT e.tenant_id, e.metric_date,
         CASE WHEN p.certified_at_utc IS NOT NULL
                    AND p.certified_at_utc <= e.ready_at_utc + INTERVAL '120 minutes'
              THEN 1 ELSE 0 END AS good,
         CASE WHEN p.publication_id IS NULL THEN 1 ELSE 0 END AS missing
  FROM expected_publication e
  LEFT JOIN publication_receipt p
    ON p.tenant_id = e.tenant_id
   AND p.metric_date = e.metric_date
  WHERE e.ready_at_utc >= :window_start
    AND e.ready_at_utc < :window_end
)
SELECT COUNT(*) AS eligible,
       SUM(good) AS good,
       SUM(missing) AS missing,
       1.0 * SUM(good) / NULLIF(COUNT(*), 0) AS freshness_sli
FROM outcomes;
```

This PostgreSQL-style query counts missing publications as not good. An empty
eligible set yields `NULL`, meaning no measurement rather than 100%.

### Python model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Window:
    eligible: int
    bad: int
    target: float

    def burn_rate(self) -> float | None:
        allowed_rate = 1.0 - self.target
        if self.eligible == 0 or allowed_rate <= 0:
            return None
        return (self.bad / self.eligible) / allowed_rate
```

Production alert evaluation also needs delayed/corrected samples, multiple
windows, reset behavior, sparse traffic handling, and monitoring-system semantics.

## Alerts, dashboards, and runbooks

| Signal | Route | Required response |
| --- | --- | --- |
| Fast, severe objective burn | Page | Immediate containment can preserve budget or reduce harm |
| Slow sustained burn | Page or urgent ticket | Owner can act within remaining budget horizon |
| One retrying task | Workflow notification | Local owner action; page only if consumer objective is threatened |
| Capacity forecast breach in 30 days | Planned work | Add/optimize capacity before saturation |
| Diagnostic skew/cardinality change | Dashboard/ticket | Investigate during owned review cadence |

A landing dashboard shows consumer outcomes, objectives and remaining budget,
eligible/good/bad/unknown counts, affected segments, freshness frontier, active
incidents, recent changes, telemetry timestamp/lag, and links to diagnostic views.
Diagnostic dashboards add queue depth/age, throughput, errors, dependency latency,
resource saturation, partitions/skew, run lineage, and cost.

A runbook starts with purpose, trigger, owner/escalation, access prerequisites,
safety warnings, known-good baseline, diagnosis decision tree, reversible containment,
data-repair boundary, verification, communication, and when to stop/escalate. It
must never advise blind retry of an ambiguous write or destructive cleanup before
preserving evidence.

## Lifecycle, consistency, identity, and time

Definitions move through proposed, backtested, shadow, approved, active,
superseded, and retired states. Preserve historical version and annotate changes.
Use occurrence/readiness/certification/observation times explicitly. A rolling
window changes continuously; a calendar window resets. Corrections should
recompute affected windows without silently rewriting the definition.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Missing publications excluded | Compare expected population/count | Repair denominator and recompute history |
| Global average hides critical tenant | Segmented objective/guardrail | Define separate tier/failure-domain objective |
| Alert floods on one dependency | Group/inhibit with ownership preserved | Repair routing and backtest recall/reset |
| Page has no safe action | On-call feedback and response audit | Downgrade/remove or build automation/runbook |
| Dashboard stale but green | Independent telemetry freshness canary | Mark unknown; restore evaluation path |
| Threshold changed without history | Version/config audit | Restore definition; annotate/recompute comparable windows |
| Runbook retries partial commit | Reconciliation reveals duplicates | Fence, repair data, update runbook and test |

## Security, privacy, and governance

Dashboards and alerts can reveal tenant health, incidents, resource topology, and
sensitive volumes. Use bounded categorical labels, access control, safe links,
redacted notifications, encrypted destinations, audited privileged steps, and
retention. Runbooks must not embed secrets. Objective exceptions identify approver,
reason, scope, compensating control, expiry, and affected consumers.

## Data quality, testing, and evidence

| Evidence | Environment/procedure | Expected result | Result |
| --- | --- | --- | --- |
| SLI fixture | Fixed expected/present/late/unknown timeline | Exact numerator, denominator, and empty behavior | Pending |
| Segment test | Critical and bulk tenant faults | Critical harm cannot hide in aggregate | Pending |
| Alert backtest | Labeled normal/incident history | Precision, recall, detection, reset, and page load measured | Pending |
| Telemetry fault | Delay/drop evaluator inputs | Dashboard becomes stale/unknown and route works | Pending |
| Runbook drill | Staged freshness/partial-publication incident | Safe containment through reconciliation | Pending |
| Delivery test | Alert router/on-call schedule | Acknowledgement/escalation measured | Pending |

## Debugging guide

Validate the exact SLI and alert version, window, target, eligible count, good/bad/
unknown treatment, segments, exclusions, and data timestamp. Recalculate from
source receipts. Correlate first burn with changes, dependency health, queues,
lineage, and publications. Test notification delivery. Follow the runbook’s safe
containment and declare recovery only when the consumer outcome and telemetry path
are both healthy.

## Common pitfalls

### Pitfall: alert on every cause

CPU, task, or dependency symptoms can create noisy duplicate pages. Page on
actionable consumer impact and retain causes for diagnosis/capacity alerts.

### Pitfall: negotiate a target before defining the population

“99.9% reliable” is meaningless without eligible events, good criteria, window,
segments, and missing-data rules. Define the measurement contract first.

### Pitfall: runbook equals a list of commands

Commands without decision gates, safety, ownership, verification, and rollback
can amplify harm. A runbook is an operational control, not a shell transcript.

## Performance, capacity, and cost

Measure evaluator delay, query/cardinality cost, dashboard latency, alert volume,
acknowledgement time, operator interruption, and data retention. Objectives have
cost: tighter freshness may require headroom and around-the-clock response. Make
the tradeoff explicit with consumers instead of silently overprovisioning.

## Observability and operations

Review objective attainment, budget trend, exclusions, unknown periods, alert
precision/recall proxies, page volume, acknowledgement, runbook use, false pages,
missed incidents, and definition changes. Test alerts end to end and rehearse
runbooks. An alert query compiling does not prove notification or human response.

## Compatibility, migration, and delivery

Shadow and backtest new definitions; dual-display old/new SLI versions; explain
discontinuities; update dashboards, alerts, runbooks, reports, and consumers in
one governed rollout. Roll back alert logic independently when possible. Preserve
incident-period definitions for later review.

## Working example

- SQL: Planned freshness and completeness evaluation under `sql/operations/`
- Python: Planned burn-rate evaluator under `src/big_data_example/operations/`
- Tests: Planned missing/late/empty/segment/window/backtest cases
- Operations: Planned dashboard contract, alert policy, and freshness runbook
- Expected result: Missing work consumes the correct objective; pages are actionable and telemetry loss is unknown
- Scale represented: Deterministic timeline and production estimate; no live monitoring run
- Remaining risk: Consumer target, sparse populations, backend query semantics, routing, operator load, and production baseline

## Knowledge check

1. Define separate freshness, availability, completeness, and recovery indicators.
2. Predict the SQL result for an empty window and a missing publication.
3. Diagnose a healthy global SLO with one failed critical tenant.
4. Design a page and runbook for fast freshness-budget burn.
5. Calculate allowed bad tenant-days for 99% over 2,800 eligible outcomes.
6. Plan a definition change that preserves historical interpretation.
7. Backtest one alert and report precision, recall, detection, and reset limits.

## Key takeaways

- Every SLI needs an independent eligible population and explicit unknown behavior.
- Invariants are not traded away through an aggregate error budget.
- Pages request immediate action; dashboards support more than paging.
- Alert and runbook behavior needs end-to-end evidence.
- Objective definitions and changes are versioned data contracts.

## Resources

- [Google SRE Workbook: implementing SLOs](https://sre.google/workbook/implementing-slos/) (reviewed 2026-09)
- [Google SRE Workbook: alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) (reviewed 2026-09; thresholds require local backtesting)
- [Google SRE Workbook: monitoring](https://sre.google/workbook/monitoring/) (reviewed 2026-09)
- [Google SRE Workbook: on-call](https://sre.google/workbook/on-call/) (reviewed 2026-09)

## Related topics

- [Incident response and data repair](04-incident-response-data-repair-and-organizational-learning.md)
- [Logs, metrics, traces, lineage, and correlation](02-logs-metrics-traces-lineage-and-correlation.md)
- [Area 13 quality objectives](../13-data-quality-contracts-and-testing/08-quality-objectives-observability-and-evidence-portfolios.md)

## Completion checklist

- [x] SLI/SLO, population, budget, alert, dashboard, runbook, ownership, security, failure, cost, and migration covered
- [x] SQL/Python models and sparse/unknown behavior explicit
- [x] Working example and evidence accurately marked Planned
- [ ] SLI, segmentation, alert-backtest, telemetry-fault, routing, runbook, and production evidence executed
