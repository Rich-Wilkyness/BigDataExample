# Data-System Reliability Requirements and Failure Domains

> Status: Documentation complete; executable resilience evidence planned  
> Level: Intermediate to Senior  
> Applies to: Batch / Streaming / Storage / Serving / Data platforms  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Data-system reliability is the probability that consumers receive an acceptable
data outcome under stated conditions and over a stated time. “Acceptable” can
include durability, correctness, completeness, freshness, availability, and
recoverability; maximizing only uptime can publish wrong data faster.

This guide turns consumer harm into requirements, identifies dependencies and
failure domains, and selects containment and recovery responsibilities. It does
not set real organizational targets or prove a particular distributed design.

## Learning objectives

- Translate consumer journeys into invariants, indicators, objectives, and recovery requirements.
- Separate availability, durability, correctness, completeness, and freshness.
- Map correlated failure domains, dependencies, blast radius, and graceful degradation.
- Evaluate redundancy by independence rather than replica count.
- Design fault and recovery evidence that includes downstream data convergence.

## Prerequisites

- [Area 08 distributed failure](../08-distributed-systems-foundations/README.md), [Area 12 workflow semantics](../12-workflow-orchestration-and-transformation-management/README.md), and [Area 13 quality requirements](../13-data-quality-contracts-and-testing/README.md).
- Planned deterministic failure model and integration environment for executable evidence.

## Mental model and terminology

```text
consumer decision
      |
      v
acceptable outcome + deadline + population
      |
      +-> invariant (must hold per publication)
      +-> SLO (allowed bad fraction over a window)
      +-> RPO/RTO (recoverable loss and restoration time)
      |
dependency graph -> failure domains -> containment -> repair -> convergence
```

| Term | Meaning in this guide |
| --- | --- |
| Reliability | Acceptable consumer outcomes over a defined population, window, and operating conditions |
| Availability | Ability to perform a named operation when eligible demand occurs |
| Durability | Probability acknowledged authoritative data remains recoverable |
| Freshness | Delay between a defined source frontier/event and usable consumer data |
| Failure domain | Resources likely to fail together because they share a dependency or control |
| Blast radius | Consumers, tenants, intervals, datasets, or operations affected by one failure |
| Graceful degradation | Deliberate reduced behavior that preserves stated safety/correctness properties |
| RPO/RTO | Maximum tolerable data-loss interval and target time to restore a named capability |

An Android app’s offline cache can preserve limited reads during an API outage.
A data-system equivalent might serve the last certified snapshot with a visible
age. The analogy stops when stale data can drive irreversible business actions;
degradation is safe only if the consumer approves its semantics.

## Requirements, scale assumptions, and invariants

Start with consumer operation, eligible population, acceptable result, deadline,
measurement point, window, exclusions, impact, owner, and dependency. Assume the
shared scenario from the area README: 3 million events/day, 100 tenants, one
daily publication within 120 minutes of readiness, 35 replay days, and 100
million retained events. All are estimates.

Invariants:

- An accepted event is either durably recoverable or its acknowledgement fails.
- A certified daily publication binds one immutable input frontier, transform version, schema/metric version, and passing blocking checks.
- A retry cannot create two active logical publications for the same tenant/date/version.
- Missing or stale evidence is unknown, never silently healthy.
- Degraded output is explicitly versioned/marked and only served to consumers that accept it.
- Recovery closes only after authoritative state, derived data, downstream consumers, and telemetry reconcile.
- Redundant copies do not count as independent when they share identity, credentials, region, control plane, corruption path, or operator action.

Non-goals are zero failures, a universal “five nines” target, and availability at
the expense of correctness, privacy, or bounded cost.

## Data flow, ownership, and trust boundaries

| Boundary | Authority/owner | Failure behavior | Trust |
| --- | --- | --- | --- |
| Producer acknowledgement | Producer + ingestion contract | Reject, retry, or return uncertain; never invent acceptance | Untrusted network/input |
| Event log/raw store | Ingestion owner; first durable authority | Halt dependent frontier when durability is uncertain | Restricted authority |
| Transformation candidate | Dataset owner; derived and attempt-private | Retry/discard before atomic certification | Untrusted until checks pass |
| Active publication | Catalog/table owner; consumer-visible authority | Retain last certified version or declare unavailable | Governed output |
| Scheduler/catalog/identity | Platform owners | Defined fail-safe/degraded policy per dependency | Control planes |
| Consumer extract/cache | Consumer owner; derived copy | Staleness and invalidation visible | Separate recovery boundary |

## Reliability requirement model

Use different requirement forms for different harms:

```text
Invariant: for each certified tenant/date, accepted = represented + rejected
Freshness SLO: 99% of eligible tenant/date publications certify within 120 min
Query availability SLO: 99.9% of eligible read requests return a certified version
RPO: at most 5 minutes of acknowledged raw events may require producer replay
RTO: restore certified read capability within 4 hours of declared regional loss
```

The numbers are examples requiring consumer negotiation and rehearsals. A ratio
SLO cannot excuse a known invariant violation, and RPO does not state how much
derived history must be recomputed.

### SQL model

```sql
-- Grain: one tenant/date publication. Missing rows remain visible through the
-- expected-population left join rather than disappearing from the denominator.
SELECT e.tenant_id, e.metric_date,
       CASE
         WHEN p.certified_at_utc IS NULL THEN 'missing'
         WHEN p.accepted_count <> p.represented_count + p.rejected_count THEN 'incorrect'
         WHEN p.certified_at_utc > e.ready_at_utc + INTERVAL '120 minutes' THEN 'late'
         ELSE 'good'
       END AS reliability_state
FROM expected_publication e
LEFT JOIN publication_receipt p
  ON p.tenant_id = e.tenant_id
 AND p.metric_date = e.metric_date
 AND p.active = TRUE;
```

This is PostgreSQL-style SQL. `NULL` means no matching receipt; it is not good.
The expected set must come from an authority independent of successful output.

### Python model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FailureDomain:
    name: str
    members: frozenset[str]

def shared_domains(path_a: set[str], path_b: set[str]) -> set[str]:
    """Replica paths are independent only outside their shared domains."""
    return path_a & path_b
```

The bounded model can expose a hidden shared region, account, key, catalog, or
deployment pipeline. It cannot model real failure probability or control-plane
behavior without measured dependency evidence.

## Dependency and failure-domain analysis

Model both data-plane and control-plane dependencies: source, network, broker,
storage, compute, metadata database, scheduler, catalog, identity, keys, DNS,
telemetry, deployment, human approval, and vendor support. For each, record
scope, mode, detection, timeout, safe behavior, recovery owner, alternatives,
capacity, and correlated dependencies.

| Requirement | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Preserve correctness during transform failure | Last certified snapshot | No partial candidate escapes | Staleness becomes more harmful than unavailability |
| Survive one worker loss | Retry attempt-private work | Cheap and bounded | Nondeterministic/external effects cannot be fenced |
| Survive region loss | Independently restorable state and control plane | Addresses correlated infrastructure loss | Data locality or cost prohibits it |
| Limit hot-tenant overload | Tenant/workload quotas and admission | Bounds blast radius | Shared global work needs reserved capacity |

## Lifecycle, consistency, identity, and time

An event moves from unacknowledged to durably accepted, validated, included in a
candidate, certified, served, corrected, retained, and deleted. A job attempt is
not a dataset version. Use stable event, interval, run, attempt, publication,
schema, and repair identifiers.

State the consistency seen by each consumer, the scope of ordering, late-data
cutoffs, time zone, clock source, and readiness frontier. Atomic activation is
the consumer boundary; files appearing one by one are not an atomic publication.

## Failure model and recovery

| Failure | Detection/containment | Recovery and proof |
| --- | --- | --- |
| Worker dies mid-write | Missing heartbeat plus private candidate | Fence attempt; retry; prove one active publication |
| Storage acknowledges then loses data | Independent inventory/read/restore checks | Restore or replay within RPO; reconcile IDs/counts |
| Catalog unavailable | Health/operation errors | Pause activation; keep last safe version; reconcile metadata |
| Bad data passes healthy compute | Consumer/quality signal | Withdraw or mark version; repair/backfill and recertify |
| One tenant overloads shared engine | Queue/resource saturation by bounded tenant label | Throttle; preserve reserved critical/current work |
| Region and credentials share fate | Game-day dependency map reveals coupling | Restore independent identity, keys, metadata, data, then compute |
| Telemetry outage hides impact | Heartbeat and independent probes | Mark state unknown; restore/recompute observations |

## Security, privacy, and governance

Reliability measures never justify copying unrestricted data, bypassing deletion,
or retaining secrets in diagnostics. Recovery paths are privileged attack paths:
apply least privilege, dual control where appropriate, tenant isolation, audit,
key recovery, safe samples, and restoration-time policy enforcement. Track data
residency and legal holds when redundancy crosses locations.

## Data quality, testing, and evidence

| Evidence | Environment/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Requirement review | Consumer journey and harm workshop | Every guarantee has population, deadline, owner, and failure behavior | Pending |
| Failure-domain model | Deterministic dependency graph | Shared domains and blast radius are explicit | Pending |
| Fault matrix | Local/integration injected worker, store, catalog, telemetry faults | Safe containment and convergent retry | Pending |
| Correlated failure | Distributed environment | Redundant paths fail independently as claimed | Pending |
| Recovery drill | Named restored state plus downstream reconciliation | RPO/RTO and consumer correctness measured | Pending |

## Debugging guide

Start from the affected consumer and bad population. Capture dataset/publication,
input frontier, contract/code/config versions, run/attempt, first/last bad times,
failure domain, dependency state, and telemetry lag. Determine whether the symptom
is stale, missing, incorrect, unavailable, duplicated, or unauthorized. Contain
consumer harm before speculative repair. Close only after the authority, derived
copies, missed intervals, downstream caches/exports, and indicators reconcile.

## Common pitfalls

### Pitfall: equate successful jobs with reliability

A job can succeed after publishing wrong, incomplete, or late data. Measure at
the consumer boundary and bind success to an exact certified publication.

### Pitfall: count replicas without mapping shared fate

Two copies under one account/key/region/operator may be one failure domain. Test
the specific fault that redundancy claims to survive.

### Pitfall: retry an ambiguous external effect

An unknown commit can duplicate output. Use stable idempotency identity, attempt-
private state, commit receipts, fencing, and reconciliation before retry.

## Performance, capacity, and cost

Reliability consumes headroom, redundant storage/control planes, telemetry,
testing, and operator time. Record normal and recovery throughput, backlog growth,
drain rate, retry amplification, storage overhead, and cost. A standby unable to
handle recovery demand is documentation, not capacity.

## Observability and operations

Track consumer-good/eligible counts, freshness, publication failures, backlog age,
dependency saturation, durability/restore checks, last successful recovery test,
and telemetry health. Bound metric labels; keep run/publication IDs in structured
events. Every objective threat has an owner, escalation, safe containment, and
runbook. Avoid paging on a cause when no immediate action changes consumer harm.

## Compatibility, migration, and delivery

Version requirements, failure maps, receipt schemas, objective definitions, and
recovery procedures. Shadow new paths, compare results, constrain rollout by
failure domain, preserve old readers during expand/migrate/contract, and reconcile
after cutover. Rollback code cannot undo already published bad data; plan data
withdrawal and forward repair.

## Working example

- Model: Planned failure-domain graph and reliability evaluator under `src/big_data_example/operations/`
- SQL: Planned expected-publication reliability query under `sql/operations/`
- Tests: Planned missing, duplicate, partial commit, shared-domain, overload, and recovery cases
- Try it: Planned deterministic fixture followed by named-service fault exercise
- Expected result: Unsafe candidates never activate; impact and unknown telemetry remain visible; recovery converges
- Scale represented: Local fixture and production estimate; no distributed fault executed
- Remaining risk: Real dependency correlation, failure probability, recovery capacity, consumer behavior, and operator coordination

## Knowledge check

1. Distinguish availability, durability, correctness, completeness, freshness, RPO, and RTO for the reference publication.
2. Predict how a missing expected-publication row affects the SQL result.
3. Diagnose why two regional replicas could still share one failure domain.
4. Design containment for a correct-but-late source versus an incorrect publication.
5. Estimate backlog and drain time after a six-hour outage.
6. Plan a regional migration with a reversible data/publication cutover.
7. Add one failure domain and the evidence required to validate its isolation.

## Key takeaways

- Reliability starts with acceptable consumer outcomes, not component uptime.
- Invariants, SLOs, and recovery objectives answer different questions.
- Independence and blast radius matter more than replica count.
- Recovery includes data and downstream convergence, not merely process restart.
- Unknown evidence remains visible and limits the claim.

## Resources

- [Google SRE: implementing SLOs](https://sre.google/workbook/implementing-slos/) (reviewed 2026-09)
- [Google SRE Workbook: data processing pipelines](https://sre.google/workbook/data-processing/) (reviewed 2026-09)
- [NIST SP 800-34 Rev. 1 contingency planning](https://csrc.nist.gov/pubs/sp/800/34/r1/final) (reviewed 2026-09; organizational tailoring required)

## Related topics

- [Area 13 quality objectives](../13-data-quality-contracts-and-testing/08-quality-objectives-observability-and-evidence-portfolios.md)
- [SLIs, SLOs, alerts, dashboards, and runbooks](03-data-slis-slos-alerts-dashboards-and-runbooks.md)
- [Backups, restores, checkpoints, and DR](05-backups-restores-checkpoints-and-disaster-recovery.md)

## Completion checklist

- [x] Consumer guarantees, requirements, ownership, dependencies, failure domains, blast radius, and degradation covered
- [x] Identity, time, consistency, security, scale, cost, migration, recovery, and evidence boundaries explicit
- [x] SQL/Python models and working example accurately marked Planned
- [ ] Requirement, fault, distributed-isolation, overload, restore, and production evidence executed
