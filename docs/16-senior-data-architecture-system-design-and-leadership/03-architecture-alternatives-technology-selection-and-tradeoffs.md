# Architecture Alternatives, Technology Selection, and Tradeoffs

> Status: Documentation complete; prototype and comparative evidence planned  
> Level: Senior  
> Applies to: Batch / Streaming / Storage / Warehouses / Data platforms  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Architecture selection compares complete operating approaches against explicit
requirements. A technology feature matrix is insufficient: each option includes
data semantics, integration, migration, people skills, security, operations,
failure recovery, cost, exit path, and opportunity cost. The default alternative
is the simplest change to the system that already works.

This guide compares ways to add provisional five-minute metrics while retaining
certified daily output. It does not select a vendor or claim universal superiority
for batch, streaming, warehouse, lakehouse, managed service, or self-hosting.

## Learning objectives

- Generate a credible baseline and alternatives at the architecture level.
- Evaluate batch/stream, build/buy, managed/self-managed, and centralized/federated tradeoffs.
- Use requirements, prototypes, and reversibility rather than preference or novelty.
- Account for migration, failure, lock-in, skills, operations, and total cost.
- Record a conditional recommendation and triggers for revisiting it.

## Prerequisites

- [Requirements and context](01-requirements-constraints-system-context-and-non-goals.md).
- [Workload/capacity model](02-workload-estimation-capacity-and-cost-models.md).
- Storage, batch, distributed, streaming, and serving behavior from [Areas 04 and 07-11](../README.md).

## Mental model and terminology

```text
requirements + workload + current system
                 |
       smallest viable baseline
          /          |          \
 alternatives -> evidence -> consequences -> conditional decision
                        |                 |
                 migration/exit      revisit trigger
```

| Term | Meaning in this guide |
| --- | --- |
| Baseline | Smallest credible change, including keeping or tuning the current system |
| Alternative | End-to-end operating design, not a product name |
| Fitness criterion | Requirement-linked measure used to compare options |
| Reversibility | Cost and feasibility of changing or exiting a decision |
| Lock-in | Switching cost caused by data, interfaces, skills, operations, or commercial terms |
| Real option | Small investment that preserves a valuable future choice |

Choosing Retrofit versus a direct HTTP client is locally analogous: compare
lifecycle, testing, interoperability, and team cost, not API count. The analogy
stops because changing a data engine may require copying petabytes, replaying
history, preserving semantics, and coordinating independent consumers.

## Requirements, assumptions, and invariants

Use the five-minute provisional and 120-minute certified objectives, shared
workload range, tenant isolation, deduplication, correction, deletion, lineage,
replay, and cost constraints. Assume existing governed batch history is reliable;
that assumption must be verified.

Invariants:

- Compare at least the current/simple baseline and one materially different credible option.
- Score only against defined criteria; mandatory constraints are gates, not low weights.
- Include end-to-end ownership, degraded modes, migration, decommissioning, and evidence cost.
- Product capability claims are version/region/configuration-specific and verified from primary documentation plus prototypes where critical.
- Preference, resume experience, sunk cost, and vendor relationship are disclosed influences, not hidden criteria.
- Recommendation states conditions, uncertainties, dissent, reversible steps, and revisit triggers.

## Data flow, ownership, and trust boundaries

Each option must show producer, authoritative input, processing/checkpoint state,
candidate and active publication, control-plane dependencies, consumers, and
human operational boundaries. New managed or self-hosted components begin as
untrusted dependencies: their guarantees must be mapped to the owning team and
verified at the selected version, configuration, region, and failure boundary.

| Option | Flow | Strength | Principal risk |
| --- | --- | --- | --- |
| A: faster micro-batch | Governed history -> frequent incremental job -> provisional table | Reuses authority and operating path | Startup/scan/queue may miss five minutes |
| B: warehouse incremental | Ingest/land -> managed incremental table/view | Fewer platform components | Cost/concurrency and engine-specific semantics |
| C: streaming projection | Durable log -> stateful stream -> provisional store; batch certifies | Low latency and explicit incremental state | Dual semantics, checkpoint/replay, operations |
| D: producer pre-aggregation | Producers/service emit aggregates | Low central processing | Trust, corrections, version skew, lost raw flexibility |

Option D fails if the platform cannot independently verify governed metric
semantics. It may remain useful for hints, never as unexplained authority.

## Decision method

1. Define mandatory gates: semantics, policy, recovery, locality, and compatibility.
2. Establish baseline and why it may fail, supported by measurements rather than assumption.
3. Generate few genuinely distinct alternatives and a do-nothing consequence.
4. Compare architecture flows, state, ownership, failure domains, and migration.
5. Weight desirable criteria only after gates; run sensitivity on close scores.
6. Prototype the riskiest differentiators, not the happiest common path.
7. Recommend conditionally, identify dissent and evidence gaps, and prefer reversible increments.

### Example evaluation matrix

Scores are hypotheses from 1 (poor) to 5 (strong), not evidence.

| Criterion | Gate/weight | A micro-batch | B warehouse | C stream |
| --- | ---: | ---: | ---: | ---: |
| Five-minute p99 | Gate | Unknown | Unknown | Unknown |
| Certified semantic parity | Gate | 4 | 3 | 3 |
| Tenant/policy enforcement | Gate | 4 | 4 | 3 |
| Recovery and replay | 25 | 4 | 3 | 3 |
| Operability/team fit | 25 | 4 | 4 | 2 |
| Growth/capacity | 20 | 3 | 3 | 5 |
| Three-year cost range | 15 | 4 | 3 | 3 |
| Exit/migration | 15 | 4 | 2 | 3 |

Unknown gate values prohibit a final selection. Weighted totals must not average
away a failed mandatory constraint.

### SQL semantic differential

```sql
-- Both candidates must share grain and metric version before comparison.
SELECT COALESCE(b.tenant_id, s.tenant_id) AS tenant_id,
       COALESCE(b.window_start, s.window_start) AS window_start,
       b.metric_value AS baseline_value,
       s.metric_value AS candidate_value
FROM baseline_metric b
FULL OUTER JOIN candidate_metric s
  ON s.tenant_id = b.tenant_id
 AND s.window_start = b.window_start
 AND s.metric_version = b.metric_version
WHERE b.metric_value IS DISTINCT FROM s.metric_value
   OR b.tenant_id IS NULL OR s.tenant_id IS NULL;
```

PostgreSQL-style `IS DISTINCT FROM` is `NULL`-safe; adapt and test the chosen
dialect. Matching values do not prove correct handling of missing inputs or shared bugs.

### Python decision sketch

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Criterion:
    name: str
    weight: int
    mandatory: bool

def weighted_score(criteria: list[Criterion], scores: dict[str, int]) -> int:
    if any(c.mandatory and c.name not in scores for c in criteria):
        raise ValueError("mandatory criteria require evidence")
    return sum(c.weight * scores[c.name] for c in criteria if c.name in scores)
```

A real decision model must represent unknown, confidence, evidence links, and
failed gates; integers alone create misleading certainty.

## Technology due diligence

For each irreplaceable capability, verify supported semantics, limits/quotas,
consistency, ordering, transactions, schema evolution, replay, portability,
security controls, region availability, observability, backup/restore, upgrade
policy, pricing units, support, and exit/export. Test critical claims with the
actual version and configuration. Managed service transfers tasks, not accountability.

## Lifecycle, consistency, identity, and time

An option progresses from candidate to investigated, prototyped, selected,
delivered, observed, superseded, and retired. Compare the same event identity,
window, lateness, `NULL`, correction, and certification semantics across all
options. Alternative evaluation expires as workloads, prices, skills, or products change.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Baseline omitted | Review sees only favored product | Add current/do-nothing alternative |
| Mandatory gate averaged away | Policy/recovery violation | Reject option until gate passes |
| Prototype tests happy path | Fault/replay evidence absent | Test duplicates, late data, outage, restore, overload |
| Shared semantic bug | Candidates agree but independent control fails | Use separate oracle/reconciliation |
| Managed dependency throttles | Quota/latency signals | Admission, fallback, capacity/support plan |
| Exit path is fictional | Export time/fees/format untested | Run bounded export and price migration |
| Skills gap becomes incident | Operational review/game day fails | Simplify, train, staff, or change option |

## Security, privacy, and governance

Threat-model every new boundary and data copy. Compare identity integration,
least privilege, tenant isolation, encryption/key control, egress, residency,
retention/deletion, audit, supply chain, incident access, and provider responsibility.
Security claims are gates where obligations require them.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Requirement gate | Trace each mandatory criterion | No option passes by weighting a violation | Pending |
| Semantic differential | Shared faulty fixture plus independent oracle | Duplicates/late/corrections match contract | Pending |
| Load/cost prototype | Representative payload, skew, concurrency | Capacity and unit-cost ranges calibrated | Pending |
| Fault/replay | Kill dependency/worker and replay interval | Recovery converges without double effects | Pending |
| Security/exit | Negative access and bounded export | Isolation holds; exit time/cost known | Pending |
| Operability review | On-call walkthrough/game day | Team can diagnose and recover | Pending |

## Debugging guide

When a choice feels predetermined, inspect requirement provenance, gates, score
weights, unknowns, evidence quality, excluded baseline, sunk costs, and who bears
operational work. Re-run sensitivity: if a small weight change flips the answer,
the decision is close and reversibility/evidence should dominate.

## Common pitfalls

### Pitfall: compare products, not systems

The broker or warehouse is only one component. Include sources, state, sinks,
control plane, people, recovery, and migration in every option.

### Pitfall: use a matrix to manufacture objectivity

Scores encode judgment. Preserve rationale, confidence, gates, and sensitivity;
do not present a weighted total as a measurement.

### Pitfall: optimize for the future maximum

Speculative scale adds current complexity and slows learning. Preserve an exit
or expansion seam, measure approach to the breakpoint, and defer irreversible cost.

## Performance, capacity, and cost

Compare end-to-end latency distributions, throughput, state, scan/write/shuffle,
concurrency, peak/skew/recovery capacity, operator load, licensing/support,
transfer, temporary migration, and cost per successful outcome. A cheaper compute
line can be more expensive when it creates a second operating model.

## Observability and operations

Require signals and runbooks for every new state and failure boundary. Evaluate
who receives alerts, diagnoses engine behavior, coordinates providers, repairs
data, manages upgrades, and certifies recovery. Prefer boring observable behavior
over feature breadth that the team cannot safely operate.

## Compatibility, migration, and delivery

Score coexistence, dual read/write risks, schema compatibility, backfill, validation,
cutover, rollback/forward repair, and decommissioning. Favor early increments
that validate an interface or workload without committing all history.

## Engineering tradeoffs

| Decision | Prefer first when | Reconsider when |
| --- | --- | --- |
| Batch/micro-batch | Freshness permits bounded intervals and simpler operations | Measured startup/queue cannot meet objective |
| Streaming | Continuous latency/state justify operational burden | Semantics or replay cannot be operated safely |
| Managed service | Team benefits exceed control/price/exit cost | Required behavior or economics lacks evidence |
| Build | Capability is differentiating and team can own lifecycle | Commodity solution meets constraints |
| Portable interface | Credible exit need justifies lowest-common-denominator cost | Abstraction blocks essential engine behavior |

## Working example

- Alternatives: Planned context/data-flow/failure diagrams for micro-batch, warehouse, and stream
- Decision: Planned gate/weight/confidence matrix with sensitivity
- SQL: Planned semantic differential across duplicate, late, empty, correction, and mixed-version cases
- Prototype: Planned latency, skew, recovery, access, operability, and exit tests
- Expected result: Conditional recommendation tied to requirements and evidence
- Remaining risk: Product/version behavior, pricing, team capacity, correlated dependencies, and migration scope

## Knowledge check

1. Explain why "Kafka versus warehouse" is not an architecture comparison.
2. Predict what happens when an unknown mandatory gate receives a neutral score.
3. Diagnose a prototype where two outputs agree because both share one transform.
4. Design three distinct options for the provisional metric.
5. Run a sensitivity thought experiment on operability and growth weights.
6. Propose a reversible first increment for the streaming option.
7. Add one exit-path test to an alternative review.

## Key takeaways

- Compare end-to-end operating systems, beginning with the simplest viable baseline.
- Mandatory constraints are gates; weighted preferences cannot cancel them.
- Prototypes target decision uncertainty, failure, and migration risk.
- Reversibility has value when evidence and future demand are uncertain.
- Technology selection includes people, operations, governance, and exit cost.

## Resources

- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) (reviewed 2026-09; provider-specific)
- [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework) (reviewed 2026-09; provider-specific)
- [Apache Kafka design documentation](https://kafka.apache.org/documentation/#design) (reviewed 2026-09; product-specific)

## Related topics

- [RFCs, ADRs, and design reviews](04-data-platform-rfcs-adrs-and-design-reviews.md)
- [Area 10 streaming](../10-messaging-streaming-and-change-data-capture/README.md)
- [Area 11 storage and serving selection](../11-warehouses-lakes-lakehouses-and-serving-systems/01-storage-and-serving-system-selection.md)

## Completion checklist

- [x] Baseline, alternatives, gates, scoring limits, prototypes, build/buy, portability, operations, and reversibility covered
- [x] Semantics, failure, security, cost, migration, ownership, and evidence boundaries explicit
- [x] SQL/Python sketches and working example accurately marked Planned
- [ ] Comparative semantic, prototype, load, cost, fault, security, exit, and production evidence executed
