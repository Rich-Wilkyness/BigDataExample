# Senior Data Engineering Capstone

> Status: Documentation complete; learner capstone evidence planned  
> Level: Senior  
> Applies to: End-to-end data products / Data platforms / Architecture / Leadership  
> Data scale: Local prototype plus production estimate  
> Example status: Planned  
> Evidence status: Documentation and acceptance rubric only  
> Last reviewed: 2026-09

## Overview

The capstone asks you to design, prototype, test, migrate, operate, and defend one
bounded evolution of the curriculum's mobile-event platform. It assesses whether
you can connect semantics, distributed behavior, governance, operations, economics,
delivery, and team ownership under uncertainty. The goal is not maximum technology.
The goal is a small defensible system and an honest account of what remains unproven.

The prompt: add a near-real-time product-engagement metric without weakening the
certified daily metric, governed event authority, tenant isolation, deletion,
replay, or cost control. Missing product choices are deliberate; discover and
record them as assumptions or questions.

## Learning objectives

- Frame an ambiguous request as a bounded, measurable system-design problem.
- Estimate the workload and compare credible complete architectures.
- Author and defend an RFC/ADRs with dissent, migration, ownership, and evidence.
- Implement one thin vertical slice and prove correctness/failure behavior locally.
- Plan and rehearse scale, fault, governance, migration, delivery, and operations.
- Communicate tradeoffs and adapt the proposal when reviewers challenge evidence.

## Prerequisites

- All previous Area 16 guides in order.
- The relevant contracts and models from [Areas 01-15](../README.md).
- Python 3.12+ and a local SQL engine only if selected for the prototype; any new dependency requires an explicit design need and repository update.
- No production data, external account, or cloud resource is required or authorized by this capstone.

## Mental model and terminology

```text
frame -> estimate -> compare -> decide -> implement -> verify -> migrate -> operate
  |         |          |         |          |          |          |         |
context   ranges   alternatives  RFC/ADR  thin slice  tests     rehearsal  game day
  +-------------------------------------------------------------------------+
                review, dissent, evidence, adaptation, defense
```

| Term | Meaning in this capstone |
| --- | --- |
| Thin vertical slice | Producer-shaped input through consumer-shaped output with real boundaries kept minimal |
| Certified result | Publication that passed the stated completeness/correctness contract |
| Provisional result | Explicitly revisable publication with visible frontier/age/version |
| Defense | Evidence-backed explanation and response to challenge, not salesmanship |
| Evidence packet | Reproducible artifacts, raw results, environment, limitations, and conclusions |
| Learner-owned change | Bounded modification chosen, implemented, tested, and explained by the learner |

Treat the exercise like owning an Android feature from product requirement through
API/database migration and rollout. The analogy ends because a data result can be
recomputed and redistributed long after execution, with historical corrections
and downstream copies outside the original deployment boundary.

## Requirements, scale assumptions, and invariants

The following fixed requirements serve as capstone invariants unless the learner
documents a justified conflict and obtains the named authority's decision:

- Governed accepted events remain authoritative at grain `tenant_id,event_id`.
- One provisional product-engagement result exists per tenant, product, five-minute event-time window, and metric version.
- The provisional path targets 99% publication within five minutes of source readiness and exposes completeness/frontier state.
- The certified UTC-daily result remains due within 120 minutes of source readiness and is not inferred from a provisional label.
- Duplicates, late/out-of-order events, corrections, empty intervals, invalid input, replay, and mixed versions have explicit behavior.
- Tenant isolation, least privilege, classification, purpose, audit, retention, deletion, lineage, and safe telemetry apply end to end.
- Current critical work remains protected during backfill/recovery; cost has a stated budget and unit.

Starting estimates: 3M events/day, about 3 GiB encoded/day, 500 events/second
burst, 100 tenants, possible 35% hot tenant, 100M retained events, and 35 replayable
days. The learner must preserve ranges and say which measurements replace them.

Non-goals for the first capstone increment:

- A multi-region production launch, universal metric platform, ML feature platform, or enterprise reorganization.
- Exactly-once claims beyond a precisely named identity, state, and publication boundary.
- Vendor procurement, legal interpretation, or access to sensitive production data.
- Replacing the certified daily publication unless a separately reviewed requirement demands it.

## Data flow, ownership, and trust boundaries

The learner must refine, not blindly copy, this baseline:

| Boundary | Required contract | Initial accountable role |
| --- | --- | --- |
| Producer event | Versioned untrusted envelope, stable tenant/event identity | Producer domain owner |
| Acceptance | Authentication, validation, dedupe, durable receipt/frontier | Ingestion owner |
| Governed history | Authoritative accepted/corrected/deleted event state | Governed dataset owner |
| Provisional computation | Window/version/frontier, retry/replay state | Metric product owner |
| Candidate publication | Private attempt plus quality and policy receipts | Processing owner |
| Active provisional view | Atomic visible version with non-certified status | Metric product owner |
| Certified daily view | Independently reconciled certification | Metric product owner |
| Consumer/export | Version/state-aware use and downstream lifecycle | Consumer owner |
| Platform control plane | Identity, catalog, orchestration, telemetry, delivery | Platform owners |

## Required deliverables

### 1. Problem framing packet

- Consumer interviews or simulated stakeholder questions and decision outcomes.
- System context, data flow/lineage, trust, and failure-domain diagrams.
- Requirement records, constraints, assumptions, risks, non-goals, conflicts, and acceptance matrix.
- Grain, semantics, time, identity, authority, ownership, and lifecycle contract.

### 2. Workload and economics packet

- Low/base/high workload table with sources, units, confidence, and owners.
- Steady, burst, skew, dependency-loss, replay, backfill, and dual-run scenarios.
- Bottleneck, drain-time, breakpoint, three-year cost range, and sensitivity model.
- Measurement plan and at least one calibrated local result if implementation exists.

### 3. Architecture decision packet

- Simple/current baseline and at least two materially different complete alternatives.
- Mandatory gates, weighted preferences with sensitivity, failure/security/operations, migration, cost, and exit paths.
- RFC with review questions, evidence links, open risks, dissent, owners, and delivery increments.
- ADRs for at least two significant decisions, including revisit triggers.

### 4. Thin vertical slice

Implement the smallest useful path allowed by repository conventions:

- Deterministic fixture including empty, invalid, duplicate, late/out-of-order, corrected, deleted/suppressed, mixed-version, and hot-tenant cases.
- Typed Python boundary or SQL schema with explicit parse/validation failure.
- Idempotent incremental transform at the declared grain and time semantics.
- Attempt-private output and atomic local publication representation.
- Provisional state/frontier plus independent certified reconciliation.
- Safe rejected-record metadata, correlation IDs, receipts, and bounded metrics.

If implementation is deliberately deferred, mark each artifact Planned and do
not award executable evidence. Decorative code inside the RFC does not satisfy this deliverable.

### 5. Verification and operations packet

- Unit/property and SQL assertions for invariants and mutation-resistant edge cases.
- Contract/compatibility and independent record/aggregate reconciliation.
- Measured local performance/profile, rate/concurrency/skew sweep, and resource/cost report.
- Injected partial publication, crash/retry, checkpoint/state loss, dependency outage, overload, and repair/replay.
- Negative tenant/access and deletion-resurrection checks.
- SLI/SLO, dashboard/alert design, runbook, incident tabletop/game day, and postmortem action.

### 6. Migration, ownership, and defense packet

- Source/copy/consumer inventory; expand/migrate/contract waves; validation, cutover, abort, rollback horizon, forward repair, and decommission gates.
- Product and platform contracts, responsibility/authority map, support and escalation.
- Delivery forecast/risk register and one learner-owned implementation or operational change.
- Recorded or written design defense, reviewer concerns/dissent, dispositions, and revised decision.

## Reference correctness model

The metric definition itself is a learner decision. A valid example might count
distinct accepted `view` events by tenant/product/window/version, excluding
quarantined and logically deleted identities. It must define whether a correction
changes event time/product and how previously published windows are repaired.

```sql
-- PostgreSQL-oriented sketch; adapt interval/date functions to the selected engine.
-- Grain: tenant/product/5-minute event-time window/metric version.
SELECT tenant_id,
       product_id,
       metric_version,
       DATE_TRUNC('hour', event_time_utc)
         + FLOOR(EXTRACT(MINUTE FROM event_time_utc) / 5) * INTERVAL '5 minutes'
           AS window_start_utc,
       COUNT(DISTINCT event_id) AS distinct_views
FROM governed_event_snapshot
WHERE event_type = 'view'
  AND deletion_state = 'active'
  AND event_time_utc >= :start_utc
  AND event_time_utc < :end_utc
GROUP BY tenant_id, product_id, metric_version,
         DATE_TRUNC('hour', event_time_utc)
           + FLOOR(EXTRACT(MINUTE FROM event_time_utc) / 5) * INTERVAL '5 minutes';
```

`COUNT(DISTINCT)` and timestamp arithmetic are engine-specific performance and
semantic choices. The query says nothing about readiness, watermark, publication,
or correction; the design must supply those contracts.

### Publication model

```python
from dataclasses import dataclass
from enum import Enum

class Certification(Enum):
    PROVISIONAL = "provisional"
    CERTIFIED = "certified"

@dataclass(frozen=True)
class Publication:
    publication_id: str
    metric_version: str
    input_frontier: str
    attempt_id: str
    certification: Certification
    content_digest: str

def may_replace(active: Publication | None, candidate: Publication) -> bool:
    return active is None or (
        candidate.metric_version == active.metric_version
        and candidate.input_frontier >= active.input_frontier
        and candidate.publication_id != active.publication_id
    )
```

Lexical frontier comparison is safe only for a canonical order-preserving encoding.
Real activation needs atomic conditional update/fencing, policy receipts, and
well-defined correction/version behavior. Add a test that exposes the lexical-order bug.

## Required failure game day

In an isolated local or staging environment:

1. Establish baseline output, objectives, capacity, owners, communication, and abort controls.
2. Inject a duplicate/reordered burst from the hot tenant.
3. Interrupt processing between candidate write and activation.
4. Corrupt or remove incremental state/checkpoint while preserving the authoritative source.
5. Make one control-plane dependency unavailable or stale.
6. Accumulate a backlog, recover/replay under current traffic, and observe isolation/drain.
7. Attempt unauthorized cross-tenant access and replay a previously deleted identity.
8. Reconcile provisional, certified, historical, and consumer-visible copies.
9. Record timeline, decisions, evidence gaps, and one owned verified improvement.

Never simulate failure against an environment or account not explicitly authorized.

## Lifecycle, consistency, identity, and time

Document record acceptance, validation, deduplication, window state, watermark/
frontier, late correction, candidate creation, activation, certification, replay,
retention, deletion, and retirement. State which operations are atomic and where
consumers can see mixed versions. Use UTC instants and half-open intervals; separate
event, acceptance, readiness, processing, publication, observation, and deletion time.

## Failure model and recovery

At minimum, analyze and test where locally feasible:

| Failure | Required containment | Convergence evidence |
| --- | --- | --- |
| Invalid/malicious event | Reject/quarantine safely | Accepted population unaffected; safe reason recorded |
| Duplicate/out-of-order/late event | Stable identity and lateness policy | Rerun/replay reaches expected window result |
| Hot tenant/overload | Admission and tenant isolation | Other tenants/current certified work protected |
| Crash before/after candidate write | Attempt isolation and fencing | At most one active correct publication |
| State/checkpoint loss | Restore/rebuild from named authority | Frontier and output reconcile |
| Catalog/policy/telemetry outage | Fail-safe or explicit degraded mode | No silent uncertified or unauthorized output |
| Bad schema/code deployment | Compatibility gate and canary | Abort/repair without losing accepted data |
| Deleted subject replay | Suppression/tombstone reapplied | No active copy resurrected |
| Consumer cache/export stale | Lineage and consumer runbook | Every known copy confirms corrected version |

## Security, privacy, and governance review

Produce a threat/trust-boundary review; field classification and purpose map;
identity/RBAC/ABAC and tenant controls; secret/key lifecycle; safe sample/log/metric
rules; retention/deletion/hold behavior; lineage/audit completeness; supply-chain
and privileged-admin controls; negative tests; and residual-risk owner. Security
features without enforcement and negative evidence do not pass.

## Data quality, testing, and evidence

| Evidence level | Minimum capstone evidence | Status |
| --- | --- | --- |
| Contract | Requirements, fixtures, schemas, compatibility, owners | Pending |
| Unit/property/SQL | Identity, windows, duplicates, late/correction/delete, rerun | Pending |
| Integration | Pinned real local engine/storage behavior | Pending |
| Performance | Repeated workload, profile/plan, skew/concurrency, raw results | Pending |
| Resilience | Faults, ambiguous publication, state rebuild, replay/reconciliation | Pending |
| Governance | Negative access, lineage/audit, retention/deletion/restore | Pending |
| Operational | SLI/alert/runbook, migration rehearsal, game day, postmortem action | Pending |
| Delivery | Reproducible artifact, canary/cutover/rollback or forward repair | Pending |
| Production | Authorized bounded observation only | Not required; do not imply |

Every result records command/procedure, fixture/workload, environment, versions,
raw artifact, expected outcome, actual outcome, limitations, and conclusion.

## Debugging guide

Start at consumer symptom and publication ID. Trace metric/schema version, window,
frontier, run/attempt, event identities, accepted/rejected counts, candidate/active
state, checkpoint, lineage, policy/deletion decisions, partition sizes, lag, resource
saturation, and downstream copies. Reproduce with safe fixtures and distinguish
telemetry loss from data loss. Recovery is complete only after independent and
consumer-visible reconciliation.

## Common pitfalls

### Pitfall: impressive diagram, missing contract

Technology boxes cannot define grain, authority, clocks, duplicates, correction,
or certification. Begin the defense at the consumer and record lifecycle.

### Pitfall: local green test becomes a scale claim

A fixture proves bounded logic only. Label integration, distributed, operational,
and production gaps, then specify evidence that would close each gap.

### Pitfall: capstone becomes platform rewrite

Large scope hides reasoning and prevents complete evidence. Keep one vertical
slice, make seams explicit, and propose later increments conditionally.

### Pitfall: defend the original idea at all costs

A strong defense changes the design when evidence or critique invalidates an
assumption. Preserve the decision trail and explain the revision.

## Performance, capacity, and cost

Report low/base/high event and byte rates, partition skew, state/windows, scan/
shuffle/write, files, concurrency, backlog/drain, failure-loss headroom, migration
amplification, retention/copies, and a three-year cost range. Measure local
throughput/memory/latency distributions without claiming production prediction.

## Observability and operations

Define freshness, completeness, correctness, availability, lag/backlog, resource,
cost, policy, deletion, and telemetry-health indicators. Each alert names symptom,
threshold/window, affected consumers, owner, safe action, escalation, and runbook.
Include readiness, drain, shutdown, repair, restore, and consumer communication.

## Compatibility, migration, backfill, and delivery

Version schemas, metrics, state, code, configuration, and publications. Test old/
new producer-consumer combinations. Rehearse expand/migrate/contract, historical
backfill, live-change capture, validation, conditional cutover, abort, rollback
horizon, forward repair, post-cutover reconciliation, and decommission proof.

## Engineering tradeoffs

The defense must address at least:

| Tradeoff | Required reasoning |
| --- | --- |
| Micro-batch vs stream | Measured latency breakpoint, state/replay, operations, cost |
| Single authority vs dual path | Certification, semantic drift, correction, reconciliation |
| Exact vs approximate | Consumer harm, error/bias contract, independent controls |
| Managed vs self-managed | Responsibility, limits, skills, support, exit, total cost |
| Central vs domain ownership | Meaning, cognitive load, interoperability, operations |
| Faster delivery vs migration safety | Reversibility, wave size, evidence, blast radius |

## Execution phases and exit criteria

1. Frame: requirement and context reviewers agree on unresolved decisions and acceptance evidence.
2. Model: units pass arithmetic tests; high/sensitivity cases and breakpoints are visible.
3. Decide: mandatory gates and highest-risk unknowns have evidence or explicit owners.
4. Build: deterministic thin slice publishes only validated attempt-private candidates.
5. Verify: correctness, failure, performance, and governance tests produce reproducible results.
6. Migrate: staged rehearsal meets abort/recovery and consumer reconciliation criteria.
7. Operate: game day closes consumer-visible recovery and verifies one improvement.
8. Defend: reviewers can trace claims; learner records changes, dissent, and residual risk.

Do not advance merely because a calendar milestone elapsed. A waived criterion
requires named authority, consequence, expiry, compensating control, and follow-up.

## Evaluation rubric

| Dimension | Does not meet | Meets | Strong evidence |
| --- | --- | --- | --- |
| Framing | Tool-first, vague, hidden scope | Testable outcomes/boundaries | Conflicts and unknowns drive decisions |
| Semantics | Ambiguous grain/time/authority | Versioned lifecycle contract | Independent edge/correction evidence |
| Scale/cost | One average/no units | Ranges, recovery, sensitivity | Calibrated bottleneck/breakpoint evidence |
| Architecture | One favored product | Baseline + alternatives + gates | Prototype changes/validates decision |
| Reliability/governance | Checklist claims | Failure, recovery, access, deletion design | Fault/negative/reconciliation evidence |
| Migration/delivery | Big-bang launch | Waves, cutover, abort, repair | Rehearsal and consumer proof |
| Ownership/leadership | Hero or committee | Clear authority/support/communication | Learner-owned change expands capability |
| Evidence/defense | Conclusions without artifacts | Reproducible results and limitations | Critique produces traceable adaptation |

A capstone is complete only when all "Meets" behaviors have actual artifacts and
the claimed evidence ran. Documentation alone leaves the capstone Planned.

## Working example

- Source: Planned `src/big_data_example/architecture_capstone/`
- SQL: Planned `sql/architecture-capstone/`
- Tests: Planned `tests/architecture-capstone/`
- Data: Planned deterministic safe fixtures under `data/architecture-capstone/`
- Docs: This area plus planned RFC, ADRs, diagrams, runbook, migration, cost, and evidence packet
- Try it: Commands will be added only with implementation and pinned dependencies
- Expected result: One safe provisional metric path, independent daily certification, and recovery convergence
- Scale represented: Planned local fixture and production estimate; distributed/production evidence remains separate
- Remaining risk: Actual workload, engine semantics, multi-node failure, organizational operation, cloud limits/prices, and consumer adoption

## Knowledge check and defense prompts

1. Explain the consumer outcome, grain, authority, and difference between provisional and certified.
2. Predict results for a duplicate late correction after a window was first published.
3. Diagnose an active candidate whose digest is correct but policy receipt is stale.
4. Defend the simplest alternative and state the measured trigger for adopting more complexity.
5. Estimate recovery with current arrival, one failure domain lost, and a hot tenant.
6. Demonstrate cutover abort, forward repair, and deletion non-resurrection.
7. Hand one bounded decision/change to another learner with authority and evidence criteria.
8. Identify the weakest evidence claim and revise the recommendation accordingly.

## Key takeaways

- Senior architecture integrates consumer semantics, scale, failure, governance, economics, delivery, and ownership.
- A thin vertical slice plus adverse evidence is more informative than a broad decorative prototype.
- Provisional and certified outputs need explicit, independently verifiable contracts.
- Migration and operations are part of design, not work left after selection.
- A credible defense exposes uncertainty and changes when evidence changes.

## Resources

- [C4 model diagrams](https://c4model.com/diagrams) (reviewed 2026-09)
- [Architectural Decision Records](https://adr.github.io/) (reviewed 2026-09)
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/) (reviewed 2026-09)
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) (reviewed 2026-09; provider-specific)
- [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework) (reviewed 2026-09; provider-specific)

## Related topics

- [Area 16 learning path](README.md)
- [Area 01 first end-to-end pipeline](../01-big-data-and-data-engineering-foundations/08-first-end-to-end-data-pipeline.md)
- [Area 15 operated pipeline](../15-reliability-observability-performance-cost-and-operations/README.md)

## Completion checklist

- [x] Capstone prompt, fixed requirements, non-goals, deliverables, phases, failure game day, defense, and rubric defined
- [x] Grain, identity, time, authority, scale, cost, security, governance, recovery, migration, ownership, and leadership explicit
- [x] SQL/Python reference sketches and all unexecuted artifacts accurately marked Planned
- [ ] Learner framing, model, alternatives, RFC, ADRs, thin slice, and verification completed
- [ ] Migration rehearsal, scale test, fault game day, governance review, cost validation, owned change, and defense completed
