# Data-platform RFCs, ADRs, and Design Reviews

> Status: Documentation complete; authored RFC and review evidence planned  
> Level: Senior  
> Applies to: Data products / Platforms / Architecture / Technical leadership  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

An RFC invites review of a proposed change; an architecture decision record
(ADR) preserves one significant decision and its consequences; a design review
tests assumptions, interfaces, risks, and evidence with affected people. These
artifacts reduce decision loss and coordination risk. They are not substitutes
for prototypes, accountable decisions, or delivery.

This guide defines a lightweight decision process for the near-real-time metric
proposal. It does not impose a universal template, committee, or centralized approval gate.

## Learning objectives

- Choose an RFC, ADR, diagram, prototype, or runbook for the information need.
- Write a reviewable proposal with requirements, alternatives, evidence, and migration.
- Facilitate review that surfaces risk and dissent without seeking performative consensus.
- Record decision authority, status, assumptions, consequences, and revisit triggers.
- Track follow-through and detect documentation drift.

## Prerequisites

- [Requirements and context](01-requirements-constraints-system-context-and-non-goals.md).
- [Alternatives and tradeoffs](03-architecture-alternatives-technology-selection-and-tradeoffs.md).
- [Area 15 delivery and operations](../15-reliability-observability-performance-cost-and-operations/08-infrastructure-delivery-rollout-rollback-and-operations.md).

## Mental model and terminology

```text
proposal/RFC -> asynchronous review -> focused discussion -> decision
      |                 |                       |              |
 assumptions       comments/dissent       evidence/action     ADR
      +--------------------------------------------------------+
                           delivery -> observation -> revisit
```

| Term | Meaning in this guide |
| --- | --- |
| RFC | Time-bounded request for comments on a proposed material change |
| ADR | Immutable-in-history record of one significant decision and rationale |
| Design review | Risk-focused evaluation by affected and specialist perspectives |
| Decision owner | Person accountable for making or escalating the decision |
| Dissent | Material disagreement preserved with rationale, not erased by vote count |
| Revisit trigger | Observable condition that invalidates an assumption or consequence |
| Fitness evidence | Test or observation showing an architectural property still holds |

A Kotlin API proposal and ADR use the same separation of public contract from
implementation. The analogy stops where data reviews must cover historical
state, independent consumers, replay, data governance, and mixed-version operation.

## Requirements, scale assumptions, and invariants

Use the shared workload and requirements. A full RFC is warranted because the
proposal changes consumer semantics, long-lived state, operations, governance,
and multiple team interfaces. A reversible configuration default may need only
a small ADR or code review.

Invariants:

- The artifact states status, owner, deadline, decision authority, scope, audience, and requested feedback.
- Facts, estimates, assumptions, decisions, open questions, and evidence links are visually distinguishable.
- Alternatives include the baseline; consequences include operation, migration, and decommissioning.
- Affected producer, consumer, dataset, platform, operations, security/privacy/governance, and cost owners review where relevant.
- Silence is not consent; blocking concerns and unresolved risks receive owners and dispositions.
- ADR history is append-only: supersede a decision rather than rewriting why the old decision was made.
- Review depth follows blast radius, irreversibility, and uncertainty, not author seniority.

## Data flow, ownership, and trust boundaries

| Artifact/boundary | Authority | Failure behavior |
| --- | --- | --- |
| RFC working draft | Author | Clearly non-authoritative; sensitive content access-controlled |
| Requirements/evidence links | Owning source | RFC references rather than silently copying stale facts |
| Review comments | Reviewer for named perspective | Concern remains open until disposition recorded |
| Decision | Named decision owner | Escalates if outside authority or mandatory gate unresolved |
| ADR/decision log | Repository owner | Immutable rationale; later record supersedes |
| Delivery actions | Named implementers/owners | Tracked independently with verification and due condition |

## RFC contract

A useful RFC contains:

1. Executive summary and decision requested.
2. Consumer outcome, current state, context diagram, scope, non-goals, and glossary.
3. Functional/quality requirements, constraints, assumptions, risks, and workload model.
4. Data grain, authority, contracts, identity, `NULL`, ordering, time, consistency, and lifecycle.
5. Baseline and alternatives with evidence, cost, failure, security, operability, and reversibility.
6. Proposed architecture with dependency and trust boundaries.
7. Migration/backfill/cutover/rollback/decommission plan.
8. Test, load, fault, governance, operational, and acceptance evidence plan.
9. Delivery increments, owners, open questions, dissent, decision deadline, and revisit triggers.

Use context and container/data-flow diagrams when they answer scope and runtime
questions. Add sequence, state, lineage, deployment, or migration diagrams only
when each makes a different relationship materially clearer.

### ADR sketch

```text
ADR-004: Use provisional streaming projection while batch remains certifier
Status: Proposed | Accepted | Superseded by ADR-NNN
Context: requirement IDs, workload model, constraints, evidence
Decision: exact boundary and behavior chosen
Alternatives: baseline and rejected options with reasons
Consequences: positive, negative, risks, operations, migration, exit
Assumptions/revisit triggers: measurable conditions and owner
Dissent: concern, author, disposition
Links: RFC, prototype, rollout, runbook, metrics, incident/change records
```

One ADR captures one architecturally significant decision. Do not copy the whole
RFC and call it a decision log.

### Python review-state sketch

```python
from dataclasses import dataclass
from enum import Enum

class Disposition(Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    MITIGATED = "mitigated"
    NOT_ACCEPTED = "not_accepted"

@dataclass(frozen=True)
class ReviewConcern:
    concern_id: str
    perspective: str
    risk: str
    owner: str
    disposition: Disposition
    evidence_link: str | None = None
```

Workflow enforcement cannot prove review quality or psychological safety.

### SQL follow-through sketch

```sql
-- Grain: one required action from an accepted decision.
SELECT decision_id, action_id, owner, due_at, verification_state
FROM decision_action
WHERE due_at < CURRENT_TIMESTAMP
  AND verification_state NOT IN ('verified', 'cancelled_with_rationale');
```

The operational system must define time zone, status authority, access, and
notification behavior. Aging actions are risk signals, not individual scorecards.

## Review protocol

1. Author posts a readable draft, diff, decision request, reviewers by perspective, and deadline.
2. Reviewers comment asynchronously against requirements and evidence before meetings.
3. Facilitator groups concerns: blocking constraint, evidence gap, alternative, consequence, clarification, or preference.
4. Meeting time addresses high-impact unresolved points, not a page-by-page presentation.
5. Decision owner records accepted/rejected/deferred status, rationale, dissent, and conditions.
6. Owners complete prototypes or actions; the record links evidence and delivery changes.
7. At triggers or scheduled review, confirm, amend via new decision, or supersede.

## Lifecycle, consistency, identity, and time

RFC states are draft, review, revision, decided, implementing, observed, and
closed/superseded. Use stable IDs and timestamps; preserve links to the exact
requirement, model, schema, code, and evidence versions reviewed. Concurrent
comments may refer to stale revisions, so label revision digests and dispositions.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Review arrives after decision | Timeline shows token consultation | Reopen if material; improve notice/ownership |
| Senior voice suppresses dissent | Missing/withdrawn specialist concern | Independent facilitation and written dissent |
| Endless review | No decision deadline/authority | Bound questions, prototype uncertainty, escalate owner |
| ADR rewrites history | Diff removes old rationale | Restore and supersede with a new record |
| Diagram and system drift | Fitness/review evidence disagrees | Update artifact or design; assign owner |
| Action without verification | Ticket closed, risk remains | Reopen with measurable closure evidence |
| Sensitive detail leaks | Access/audit alert | Restrict/redact and follow incident process |

## Security, privacy, and governance

Invite specialist review early, but do not dump sensitive schemas, samples,
tenant identifiers, credentials, vulnerabilities, or provider details into a
broad document. Link access-controlled evidence. Record threat boundaries,
classification, purpose, retention/deletion, locality, audit, abuse, and supply-chain concerns.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Template lint | Required sections/IDs/owners/links | Missing decision context is visible | Pending |
| Perspective review | Named affected/specialist reviewers | Material risks have dispositions | Pending |
| ADR history | Supersede exercise and repository diff | Prior rationale remains recoverable | Pending |
| Traceability | Requirement -> evidence -> decision -> change | No orphan critical claim/action | Pending |
| Review tabletop | Conflict, deadline, and failed gate scenario | Authority/escalation/dissent work | Pending |
| Drift review | Compare deployed contracts/metrics/runbooks | Stale decisions are corrected/superseded | Pending |

## Debugging guide

If review stalls, identify the exact decision, owner, deadline, unresolved gate,
missing evidence, and consequence of delay. If discussion becomes preference,
return to requirements and falsifiable claims. If consensus is superficial,
ask each affected owner to state risk, operational obligation, and acceptance evidence.

## Common pitfalls

### Pitfall: RFC as a polished announcement

A proposal that cannot change is not a request for comments. Review while options
and evidence can still influence the outcome.

### Pitfall: architecture court

A central board approving every reversible choice creates queues and weakens
ownership. Establish guardrails and delegate two-way decisions; deeply review
high-blast-radius or hard-to-reverse changes.

### Pitfall: document every detail forever

Decision records preserve significant rationale, not meeting transcripts. Link
owned living contracts and evidence instead of duplicating them.

## Performance, capacity, and cost

Budget review effort according to risk and decision reversibility. RFCs include
workload/cost ranges and the cost of implementation, migration, operation,
decommissioning, delay, and evidence. Review queues and aged actions are also
organizational capacity signals.

## Observability and operations

Track decision lead time, rework, overdue risk actions, assumption expiry,
architecture drift, repeated exceptions, and incident links. Avoid optimizing
document count or approval speed; measure whether reviews discover material risk
early and whether actions change outcomes.

## Compatibility, migration, and delivery

The RFC owns the transition design; ADRs capture significant choices within it.
Delivery records link versions, rollout evidence, deviations, and follow-ups.
When implementation changes a premise, revise the RFC and create/supersede the ADR.

## Engineering tradeoffs

| Mechanism | Prefer when | Avoid when |
| --- | --- | --- |
| Short ADR | One bounded significant decision | Broad unresolved design needs collaboration |
| RFC | Cross-boundary proposal with alternatives | Tiny reversible local change |
| Prototype | Feasibility/behavior uncertainty dominates | Requirement or ownership question dominates |
| Design review | Multiple risks/perspectives matter | Used as ceremonial approval after commitment |

## Working example

- RFC: Planned provisional-metric proposal with diagrams, model, alternatives, migration, and evidence
- ADRs: Planned certification authority, processing mode, and publication interface decisions
- Automation: Planned required-field/action traceability checks
- Review: Planned producer, consumer, platform, operations, security/privacy, and finance perspectives
- Expected result: Decision, dissent, risks, and follow-through remain inspectable
- Remaining risk: Real decision authority, reviewer incentives, evidence quality, drift, and delivery behavior

## Knowledge check

1. Explain when an RFC is more useful than an ADR.
2. Predict the failure caused by rewriting an accepted ADR in place.
3. Diagnose a six-week review with no decision owner.
4. Design reviewers by perspective for the provisional metric.
5. Identify which unknown needs a prototype rather than more discussion.
6. Record one dissent and a legitimate non-acceptance disposition.
7. Define a fitness check and revisit trigger for a chosen architecture.

## Key takeaways

- RFCs enable change before a decision; ADRs preserve rationale after it.
- Review tests risks and evidence, not author status or document polish.
- Silence is not consent and consensus is not always required.
- Decision authority, dissent, actions, and revisit triggers must be explicit.
- Documentation stays useful through traceability to delivery and observation.

## Resources

- [Architectural Decision Records organization](https://adr.github.io/) (reviewed 2026-09)
- [MADR templates](https://adr.github.io/madr/) (reviewed 2026-09)
- [C4 model diagrams](https://c4model.com/diagrams) (reviewed 2026-09)
- [AWS Well-Architected review process](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html) (reviewed 2026-09; provider-specific)

## Related topics

- [Architecture alternatives](03-architecture-alternatives-technology-selection-and-tradeoffs.md)
- [Migration strategy](05-schema-platform-and-pipeline-migration-strategy.md)
- [Delivery risk and technical strategy](07-delivery-risk-incidents-mentoring-and-technical-strategy.md)

## Completion checklist

- [x] RFC, ADR, diagrams, review, authority, dissent, follow-through, drift, and revisit behavior covered
- [x] Security, operations, cost, migration, failure, and organizational boundaries explicit
- [x] SQL/Python sketches and working example accurately marked Planned
- [ ] RFC, ADR, review, traceability, drift, tabletop, and production evidence executed
