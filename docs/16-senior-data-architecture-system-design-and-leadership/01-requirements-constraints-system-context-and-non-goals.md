# Requirements, Constraints, System Context, and Non-goals

> Status: Documentation complete; stakeholder and acceptance evidence planned  
> Level: Senior  
> Applies to: Data products / Pipelines / Platforms / Architecture  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

A system design begins with a bounded decision problem: who needs what outcome,
under which constraints, and what evidence will show it works. Requirements are
testable statements about consumer-visible behavior. Constraints restrict the
solution space. Non-goals prevent accidental scope expansion. A system context
makes people, external systems, ownership, trust, and dependency direction visible.

This guide frames the shared request to add near-real-time product metrics while
preserving the certified daily publication. It does not select an engine, broker,
table format, cloud, team topology, or implementation plan.

## Learning objectives

- Convert a broad request into measurable functional and quality requirements.
- Separate facts, assumptions, constraints, risks, decisions, and non-goals.
- Draw a system context around consumers, authorities, dependencies, and owners.
- Define acceptance evidence and identify requirements that conflict.
- Lead discovery without disguising unresolved product or governance choices as technical facts.

## Prerequisites

- [Area 01 requirements and boundaries](../01-big-data-and-data-engineering-foundations/README.md).
- [Area 05 grain and business semantics](../05-data-modeling-and-business-semantics/README.md).
- [Area 14 governance](../14-governance-security-privacy-and-data-lifecycle/README.md) and [Area 15 reliability](../15-reliability-observability-performance-cost-and-operations/README.md).

## Mental model and terminology

```text
business outcome -> consumer decision -> observable behavior -> acceptance evidence
                           |                       |
                     system context          constraints/risks
                           +-----------> non-goals and scope boundary
```

| Term | Meaning in this guide |
| --- | --- |
| Requirement | Testable behavior or quality needed by a named consumer |
| Constraint | Condition the design must respect, whether desirable or not |
| Assumption | Unverified statement temporarily used to proceed |
| Risk | Uncertain event or condition with consequence and exposure |
| Non-goal | Explicitly excluded outcome, not merely deferred implementation detail |
| Acceptance criterion | Observable pass/fail condition at a named boundary |
| System context | Scope-level view of people and external systems, not an internal component map |

An Android feature brief can similarly trace a user action to API, local state,
and acceptance tests. The analogy stops because a data consumer may never invoke
the pipeline directly, correctness spans historical populations, and several
teams can own authoritative and derived state long after publication.

## Requirements, scale assumptions, and invariants

The initial request is: "show product engagement within five minutes." It is not
yet implementable. Discovery must determine metric definition/version, eligible
events, event-time window, completeness frontier, tenant segmentation, late-data
correction, consumers and decisions, availability/degraded behavior, retention,
access, deletion, and acceptable cost.

Working assumptions, all subject to validation:

- 3 million accepted events/day, 500 events/second burst, 100 tenants, and one tenant possibly producing 35% of traffic.
- Provisional results are 99% visible within five minutes after accepted ingestion; certified daily output remains due within 120 minutes of source readiness.
- Governed accepted history remains authoritative; the fast view is derived and visibly provisional.
- Deletion, tenant isolation, purpose limits, lineage, replay, and metric-version semantics apply to both paths.

Invariants:

- Every requirement names consumer, boundary, measure/unit, evaluation window, target, owner, and acceptance method.
- `event_id` identifies a logical event within `tenant_id`; duplicates do not inflate either publication.
- Provisional and certified outputs never share an ambiguous metric version or certification state.
- Unknown requirements and assumptions remain visible; they are not converted to certainty by diagram or consensus.
- Non-goals cannot contradict a committed consumer outcome or mandatory policy.

## Data flow, ownership, and trust boundaries

```text
[Mobile producer teams] -- versioned events --> [Data platform in scope]
          ^                                          |       |
          | contract feedback                         |       +--> [Approved exports]
          |                                          v
[Identity/policy/catalog] <-------------------- [BI and API consumers]
          ^                                          |
          +------------ governance evidence --------+
```

| Boundary | Contract and authority | Owner | Trust/failure behavior |
| --- | --- | --- | --- |
| Mobile event | Versioned envelope; producer owns intent | Producer team | Untrusted until authenticated and validated |
| Accepted event history | One logical event; governed store authoritative | Ingestion/dataset owner | Durable acceptance, quarantine, deduplication |
| Provisional metric | Named key/window/version and watermark state | Metric product owner | May revise; exposes freshness/completeness state |
| Certified daily metric | Named grain/version/certification receipt | Metric product owner | Stable until governed correction |
| Identity/policy/catalog | Access, purpose, classification, ownership metadata | Platform/governance owners | Fail closed or approved degraded mode |
| Consumer decision | Dashboard/API/export interpretation | Consumer owner | Must distinguish provisional from certified |

The platform does not own mobile instrumentation intent, consumer business
decisions, legal interpretation, or external export behavior. It owns enforcement
and evidence only where the agreed boundary assigns it.

## Requirement model

Use one small record per architecturally significant requirement:

| Field | Example |
| --- | --- |
| ID/outcome | `FRESH-01`: operators detect engagement change promptly |
| Population/grain | Tenant, product, metric version, five-minute window |
| Indicator/target | 99% of eligible windows published within five minutes of readiness |
| Correctness | Deduplicated accepted events under metric version `v2` |
| Degraded behavior | Serve last known value with age/completeness, never silently label certified |
| Owner/evidence | Metric owner; fixture, staged stream, SLI query, consumer acceptance |

Requirements must also cover availability, durability, consistency, throughput,
concurrency, recovery, security, privacy, locality, retention, deletion, audit,
compatibility, operability, cost, and migration. Do not write "scalable" or
"real-time" without a population, number, clock, percentile, and evaluation window.

### SQL acceptance sketch

```sql
-- Dialect-neutral design sketch. Grain: one eligible tenant/window outcome.
SELECT
  COUNT(CASE WHEN published_at <= ready_at + INTERVAL '5' MINUTE THEN 1 END)
    * 1.0 / NULLIF(COUNT(*), 0) AS on_time_ratio
FROM metric_window_receipt
WHERE ready_at >= :evaluation_start
  AND ready_at < :evaluation_end
  AND eligibility_state = 'eligible';
```

The engine-specific interval syntax and integer division need verification. An
empty eligible population returns `NULL` and must be reported as no evidence,
not success. Segment critical tenants so an aggregate cannot hide their failure.

### Python boundary sketch

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    consumer: str
    measure: str
    target: str
    acceptance_evidence: str
    owner: str

    def validate(self) -> None:
        if not all((self.requirement_id, self.consumer, self.measure,
                    self.target, self.acceptance_evidence, self.owner)):
            raise ValueError("requirement fields must be explicit")
```

This validates completeness of the record, not truth, feasibility, priority, or
stakeholder agreement.

## Discovery and acceptance protocol

1. Identify consumers and the decisions they make; observe current work and failure pain.
2. Map authoritative state, derived copies, existing contracts, policy, and owners.
3. Establish current baseline and desired outcome using numbers and time semantics.
4. Record constraints and classify each as mandatory, organizational, temporary, or assumed.
5. Surface conflicts, such as lower latency versus certification completeness or retention versus deletion.
6. State non-goals and consequences; obtain affected-owner acknowledgement.
7. Attach acceptance evidence and an owner to each significant requirement.
8. Review the context with producer, consumer, operations, platform, security/privacy, finance, and delivery perspectives as applicable.

## Lifecycle, consistency, identity, and time

Requirements move through proposed, clarified, accepted, implemented, evidenced,
changed, and retired. Version them with the design. Record event time, acceptance
time, source readiness, processing time, publication time, and consumer observation
separately. Use half-open UTC windows and state timezone/business-calendar rules.

## Failure model and recovery

| Failure | Detection/containment | Recovery owner/action |
| --- | --- | --- |
| Missing consumer | Late objection or unused output | Product/design owner revisits context and acceptance |
| Ambiguous metric | Independent implementations disagree | Domain owner versions definition and fixtures |
| Aggregate hides tenant harm | Segmented SLI fails | Requirement owner adds critical-segment objective |
| Constraint treated as permanent | Source/rationale absent | Decision owner validates or expires constraint |
| Hidden dependency | Rehearsal fails outside diagram | Owning team maps dependency and revises risk |
| Fast path weakens certified result | Reconciliation or resource contention | Preserve certified path; isolate/throttle candidate |
| Policy owner unavailable | Approval/evidence gap | Stop irreversible scope; follow delegated governance path |

## Security, privacy, and governance

Classify fields and derived metrics before samples or diagrams circulate. Record
purpose, legal/policy basis, tenant boundary, least privilege, retention, deletion,
locality, audit, incident, and export constraints. Treat free text, diagrams,
query examples, volumes, and tenant names as potentially sensitive metadata.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Context review | Walk producer-to-consumer diagram with named owners | Scope and dependencies acknowledged | Pending |
| Requirement lint | Check required fields and forbidden vague terms | Significant requirements are testable | Pending |
| Metric fixture | Duplicate, late, deleted, empty, and version-mixed records | Metric semantics and states agreed | Pending |
| SLI query | Pinned engine with eligible/empty/segmented cases | Target computation matches definition | Pending |
| Failure tabletop | Source, policy, catalog, and fast-path failures | Degraded behavior and recovery owned | Pending |
| Consumer acceptance | Representative consumers exercise output | Decision need is met without ambiguity | Pending |

## Debugging guide

When stakeholders disagree, inspect the consumer decision, population, grain,
clocks, denominator, baseline, authority, and claimed constraint. Ask which
observation would prove each interpretation wrong. Trace any missing owner or
dependency in the context and record the unresolved decision rather than forcing
premature consensus.

## Common pitfalls

### Pitfall: solution-shaped requirements

"Use streaming" prevents fair alternatives and hides the required behavior.
State freshness, correction, availability, and cost needs first.

### Pitfall: everyone is a stakeholder, nobody is an owner

Consultation does not assign authority. Each contract, decision, acceptance
criterion, incident, and derived copy needs one accountable owner with delegates.

### Pitfall: non-goals as an escape hatch

Excluding deletion or recovery does not remove mandatory obligations. A valid
non-goal narrows discretionary scope and states the consequence.

## Performance, capacity, and cost

Requirements provide budgets, not a design: peak accepted events/second, bytes,
windows, concurrent consumers, retention, recovery deadline, query latency,
availability, and cost per useful metric/tenant. Area 16.02 tests feasibility and
sensitivity. Missing measurements remain risks.

## Observability and operations

Every critical acceptance statement maps to an indicator, source, owner, and
response. Also observe telemetry health, freshness/completeness/correctness,
lag/backlog, rejected records, publication version/state, access decisions,
deletion progress, and spend. A dashboard is not evidence unless its population
and failure modes are known.

## Compatibility, migration, and delivery

Requirements cover mixed old/new producers, late events, historical recomputation,
dual outputs, consumer adoption, rollback limits, and source decommissioning.
Acceptance is evaluated per increment and at final consumer cutover, not only at launch.

## Engineering tradeoffs

| Tension | Possible priority | Required decision evidence |
| --- | --- | --- |
| Freshness vs completeness | Provisional then certified | Consumer labeling and reconciliation |
| Availability vs policy | Last certified or fail closed | Threat/policy and harm analysis |
| Scope vs delivery date | Narrow consumers/metrics first | Outcome value and migration path |
| Retention vs cost/privacy | Tiered, minimized history | Replay/deletion requirements and cost model |

## Working example

- Context: Planned stakeholder map, scope diagram, and dependency inventory
- Requirements: Planned versioned records for freshness, correctness, security, lifecycle, cost, and recovery
- SQL/Python: Planned SLI acceptance query and requirement lint
- Tests: Planned fixture, segmentation, empty-population, review, and tabletop cases
- Expected result: Every design-driving claim is testable, owned, bounded, and linked to evidence
- Remaining risk: Stakeholder availability, real workload baseline, hidden consumers, policy interpretation, and conflicting objectives

## Knowledge check

1. Rewrite "build a scalable real-time dashboard" as three measurable requirements.
2. Predict the SLI result for an empty eligible population and explain why.
3. Diagnose a design review where every participant assumes another team owns deletion.
4. Draw the context and trust boundaries for one mobile event and two consumers.
5. Identify the estimate that most threatens the five-minute objective.
6. Define a valid non-goal and its consequence.
7. Add acceptance criteria for one failure or degraded mode.

## Key takeaways

- Architecture begins with consumer outcomes and bounded, measurable behavior.
- Context exposes authority, dependencies, ownership, and trust before components.
- Facts, assumptions, constraints, risks, and decisions are different artifacts.
- Non-goals protect focus but cannot waive required guarantees.
- Acceptance evidence is part of the requirement, not a final testing detail.

## Resources

- [C4 model: system context diagram](https://c4model.com/diagrams/system-context) (reviewed 2026-09)
- [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework) (reviewed 2026-09; provider-specific implementation guidance)
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) (reviewed 2026-09; provider-specific implementation guidance)

## Related topics

- [Workload estimation, capacity, and cost](02-workload-estimation-capacity-and-cost-models.md)
- [Architecture alternatives and tradeoffs](03-architecture-alternatives-technology-selection-and-tradeoffs.md)
- [Area 01 architecture boundaries](../01-big-data-and-data-engineering-foundations/07-data-architecture-patterns-and-trust-boundaries.md)

## Completion checklist

- [x] Outcomes, consumers, requirements, constraints, assumptions, risks, context, ownership, and non-goals covered
- [x] Grain, identity, time, security, lifecycle, failure, acceptance, cost, and migration explicit
- [x] SQL/Python sketches and working example accurately marked Planned
- [ ] Stakeholder, fixture, SLI, failure, consumer-acceptance, and production evidence executed
