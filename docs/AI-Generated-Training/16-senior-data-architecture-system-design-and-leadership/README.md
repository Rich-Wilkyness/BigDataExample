# 16 Senior Data Architecture, System Design, and Leadership

> Area status: Documentation complete; capstone implementation and review evidence planned  
> Level: Senior data engineering  
> Applies to: Batch / Streaming / Storage / Warehouses / Data products / Data platforms / Technical leadership  
> Reference scenario: Design and defend an evolution of the governed mobile-event platform  
> Evidence boundary: Documentation and current primary-source review; no prototype, migration rehearsal, design review, or game day has run  
> Last reviewed: 2026-09

## Purpose

Senior data architecture is the practice of turning business outcomes and hard
constraints into an evolvable socio-technical system. The deliverable is not a
diagram or a product list. It is a defensible set of boundaries, contracts,
estimates, decisions, delivery increments, ownership, and evidence that lets
teams operate and change the system safely.

An Android architecture proposal is a useful bridge: both begin with user
outcomes, boundaries, lifecycle, failure, and migration rather than framework
preference. The analogy stops where data systems retain years of independently
consumed state, execute asynchronously across many engines, and require old and
new semantics to coexist during backfills and cutovers.

This area synthesizes Areas 01-15. It remains vendor-neutral and does not make
the senior engineer a central approval queue, people manager, enterprise
architect, procurement owner, or substitute for security, privacy, legal,
finance, product, and domain expertise.

## Prerequisites

- The durable data concepts, SQL/Python behavior, and processing/storage models in [Areas 01-11](../README.md).
- Orchestration, quality, governance, security, reliability, performance, cost, and delivery from [Areas 12-15](../README.md).
- Ability to state record grain, authority, consumer contracts, time semantics, and failure recovery before selecting a tool.
- No cloud account, third-party service, or production access is required for this documentation pass.

## Learning path

1. [Requirements, constraints, system context, and non-goals](01-requirements-constraints-system-context-and-non-goals.md) turns a request into measurable acceptance and bounded responsibility.
2. [Workload estimation, capacity, and cost models](02-workload-estimation-capacity-and-cost-models.md) quantifies steady state, burst, growth, recovery, and uncertainty.
3. [Architecture alternatives, technology selection, and tradeoffs](03-architecture-alternatives-technology-selection-and-tradeoffs.md) compares the smallest viable baseline with credible alternatives.
4. [Data-platform RFCs, ADRs, and design reviews](04-data-platform-rfcs-adrs-and-design-reviews.md) makes decisions, evidence, dissent, and follow-through inspectable.
5. [Schema, platform, and pipeline migration strategy](05-schema-platform-and-pipeline-migration-strategy.md) evolves long-lived data while old and new worlds coexist.
6. [Data products, platform teams, and ownership models](06-data-products-platform-teams-and-ownership-models.md) aligns authority, self-service, stewardship, and incentives.
7. [Delivery risk, incidents, mentoring, and technical strategy](07-delivery-risk-incidents-mentoring-and-technical-strategy.md) connects technical direction to sequencing, communication, learning, and organizational capacity.
8. [Senior data-engineering capstone](08-senior-data-engineering-capstone.md) integrates the area into an evidence-backed design and defense.

The path moves from framing to numbers, choices, decision process, change,
organization, leadership, and synthesis. In real work, discoveries loop back:
a prototype changes an estimate, a migration constraint changes an alternative,
or an ownership gap changes the design.

## Shared reference scenario

```text
mobile applications -> regional ingestion -> governed event history
                                               |
                    +--------------------------+-------------------------+
                    |                          |                         |
              daily metrics             near-real-time metrics      approved exports
                    |                          |                         |
                  BI/API                  operations consumers       partners/science

control plane: identity | contracts | catalog/lineage | orchestration | policy
operating loop: objectives | telemetry | incidents | repair | cost | delivery
decision loop: requirements -> estimates -> alternatives -> RFC/ADR -> evidence
```

The capstone change is deliberately under-specified at first: add a
near-real-time metric without weakening the certified daily result, tenant
isolation, deletion, replay, or cost controls. The learner must discover and
record missing requirements rather than silently inventing them.

Starting hypotheses are 3 million accepted events/day (about 3 GiB encoded), a
500 events/second burst, 100 tenants with a possible 35% hot tenant, 100 million
retained governed events, 35 replayable days, and 99% of provisional metrics
visible within five minutes. These are teaching estimates, not measurements or
commitments.

## Senior design contract

Every proposal must make these claims inspectable:

- The consumer decision, success measure, scope, constraints, non-goals, and acceptance evidence.
- Record grain, identities, time semantics, authority, derived copies, owners, and trust boundaries.
- Workload envelope, sensitivity, saturation point, recovery demand, cost unit, and uncertainty.
- A simple baseline and credible alternatives compared against weighted requirements.
- Failure domains, degraded behavior, repair, security, privacy, governance, and operational ownership.
- Interface and schema compatibility, migration waves, validation, cutover, rollback/forward-fix, and decommissioning.
- Decision status, rationale, dissent, assumptions, expiry triggers, and follow-up owners.
- Delivery increments that retire risk early and produce evidence before irreversible commitments.

An architecture claim is a hypothesis until its required evidence exists. A
senior engineer distinguishes facts from estimates and decisions from open
questions, then updates the design when evidence changes.

## Evidence ladder

| Evidence | What it can support | What remains unproven |
| --- | --- | --- |
| Requirement/context review | Scope, owners, consumers, constraints, and acceptance are coherent | Runtime feasibility and organizational behavior |
| Arithmetic/sensitivity model | Units, demand range, dominant variables, and rough feasibility | Engine overhead, nonlinear saturation, and real prices |
| Alternative/RFC review | Options and consequences were examined by affected owners | Correct implementation or production fitness |
| Bounded prototype | A risky mechanism works for a named fixture/environment | Representative scale, failure, and operability |
| Migration rehearsal | Coexistence, validation, cutover, and recovery work in staging | Hidden consumers and production-specific behavior |
| Load/fault/game day | Capacity, isolation, failure response, and repair under controlled stress | Unmodeled correlated failures |
| Incremental production evidence | Consumer outcomes and operations under real bounded exposure | Future growth and unseen failure modes |

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] Requirements, estimates, alternatives, reviews, migration, ownership, delivery, and leadership connected
- [x] Data semantics, failure, security, privacy, governance, cost, operations, and organizational boundaries explicit
- [x] Primary standards and official guidance linked with review dates
- [x] Capstone deliverables and acceptance rubric defined
- [x] Executable and organizational evidence accurately marked Planned
- [ ] Learner RFC, ADRs, model, prototype, reviews, migration rehearsal, and owned change completed
- [ ] Representative scale test, fault game day, governance review, cost validation, and design defense completed
