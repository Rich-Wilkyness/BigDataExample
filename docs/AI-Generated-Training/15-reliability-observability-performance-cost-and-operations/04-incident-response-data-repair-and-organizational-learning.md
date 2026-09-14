# Incident Response, Data Repair, and Organizational Learning

> Status: Documentation complete; executable incident evidence planned  
> Level: Intermediate to Senior  
> Applies to: Data products / Pipelines / Platforms / Operations  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Incident response coordinates decisions under uncertainty to reduce consumer
harm. Data incidents add a durable dimension: restarting compute may not retract
bad publications, restore missing history, refresh extracts, or reverse decisions
already made from incorrect data. Repair must be scoped, idempotent, auditable,
reconciled, and communicated.

This guide covers declaration, roles, triage, containment, communication, repair,
replay, consumer recovery, postmortems, and action ownership. It is not a legal,
regulatory, security-forensics, or crisis-communications substitute.

## Learning objectives

- Classify impact and establish command without waiting for complete diagnosis.
- Preserve evidence while applying reversible containment.
- Design repair manifests, replay, certification, and downstream reconciliation.
- Communicate facts, uncertainty, decisions, and next updates safely.
- Produce blameless learning with specific, prioritized, verified actions.

## Prerequisites

- [SLIs, alerts, dashboards, and runbooks](03-data-slis-slos-alerts-dashboards-and-runbooks.md).
- [Area 13 quarantine and repair](../13-data-quality-contracts-and-testing/07-quarantine-repair-replay-and-quality-incidents.md) and [Area 14 governance operations](../14-governance-security-privacy-and-data-lifecycle/08-tenant-isolation-abuse-supply-chain-and-governance-operations.md).
- Planned staging environment and authorized participants for a drill.

## Mental model and terminology

```text
detect -> declare -> establish command -> bound impact -> contain
                                                   |
                                                   v
preserve evidence -> choose authority -> repair/replay -> certify -> republish
                                                             |
                                                             v
communicate -> downstream reconcile -> consumer confirms -> close -> learn
```

| Term | Meaning in this guide |
| --- | --- |
| Incident | Coordinated response to actual or credible material harm/degradation |
| Incident commander | Owns response process, priorities, decisions, and role clarity |
| Mitigation | Action reducing current/future impact without necessarily removing cause |
| Repair | Governed correction of authoritative or derived data |
| Replay | Re-execution from a named source frontier under explicit semantics |
| Reconciliation | Independent comparison proving expected state and copies converge |
| Postmortem | Evidence-based learning record of impact, timeline, contributors, response, and actions |

The incident commander resembles the single coordinator used during a severe
mobile release regression. The analogy stops because a rollback may fix app code
but cannot erase exported data or rebuild historical aggregates; data repair and
consumer notification remain separate workstreams.

## Requirements, scale assumptions, and invariants

Define severity from consumer harm, scope, duration, data sensitivity, correctness,
freshness, irreversibility, and recovery uncertainty—not executive visibility.
Assume a possible 6-hour ingestion gap (~750,000 events at the daily average),
100 tenants, 30 derived datasets, and 35 replayable days. Real arrival skew,
throughput, and repair time are unmeasured.

Invariants:

- One declared incident has a commander, technical/data leads, communications owner, scribe, channel, timeline, and next update time.
- Facts, hypotheses, decisions, actions, owners, timestamps, and outcomes are distinguishable.
- Containment never destroys the only recoverable source or evidence.
- Every repair names authority, scope, identities, versions, transformation, dry run, capacity, approval, and rollback/forward-fix boundary.
- Replay is idempotent at the consumer-visible publication boundary and cannot starve critical current work.
- Closure requires consumer-visible reconciliation, not just green infrastructure.
- Postmortem actions have owner, priority, due condition, risk addressed, verification, and closure evidence.

## Data flow, ownership, and trust boundaries

| Boundary | Authority/owner | Incident concern |
| --- | --- | --- |
| Alert/support report | Consumer/on-call | May be noisy, incomplete, or sensitive; acknowledge and validate |
| Command channel/timeline | Incident commander/scribe | Operational record; restrict and preserve appropriately |
| Source/raw authority | Source/ingestion owner | Preserve before transformation repair |
| Active publication | Dataset owner | Withdraw, freeze, annotate, or retain last certified safely |
| Repair candidate/manifest | Repair lead + approver | Attempt-private until validation/certification |
| Downstream extract/cache/model | Consumer owner | Separate state requiring invalidation/rebuild/confirmation |
| External communication | Communications/legal/security owners as applicable | Approved facts and audience; no speculative disclosure |

## Incident control loop

1. Acknowledge and declare based on credible impact; create stable incident ID.
2. Assign command, technical/data, communications, and scribe roles.
3. State known impact, uncertainty, affected consumers, safe immediate actions, and next update.
4. Bound first/last bad frontier, datasets/versions, tenants, contracts, and downstream lineage.
5. Apply the smallest reversible containment: pause certification, serve last good, isolate tenant/workload, revoke access, or rate-limit.
6. Preserve inputs, receipts, logs, lineage, configs, artifacts, queries, and change records under policy.
7. Choose authoritative source and repair strategy; estimate backlog, drain rate, capacity, and collision with current work.
8. Dry-run into private candidates, validate/reconcile independently, canary consumers, then atomically publish.
9. Rebuild/invalidate downstream copies and obtain consumer recovery confirmation.
10. Close response, schedule learning review, track actions, and verify their effect.

### SQL model

```sql
-- Grain: one expected logical event in the repair scope. FULL OUTER JOIN exposes
-- both missing output and unexpected output; NULL-safe equality is dialect-specific.
SELECT COALESCE(e.tenant_id, a.tenant_id) AS tenant_id,
       COALESCE(e.event_id, a.event_id) AS event_id,
       CASE
         WHEN e.event_id IS NULL THEN 'unexpected_output'
         WHEN a.event_id IS NULL THEN 'missing_output'
         WHEN e.payload_digest IS DISTINCT FROM a.payload_digest THEN 'mismatched_output'
         ELSE 'matched'
       END AS reconciliation_state
FROM expected_repair_output e
FULL OUTER JOIN repair_candidate a
  ON a.tenant_id = e.tenant_id AND a.event_id = e.event_id
WHERE e.event_id IS NULL OR a.event_id IS NULL
   OR e.payload_digest IS DISTINCT FROM a.payload_digest;
```

This uses PostgreSQL `IS DISTINCT FROM` for `NULL`-safe comparison. Digest
equality is a bounded comparison, not proof of semantic correctness or
cryptographic authenticity. Aggregate and consumer-level controls are also needed.

### Python model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RepairManifest:
    incident_id: str
    source_frontier: str
    interval_start: str
    interval_end: str
    transform_version: str
    target_candidate: str
    idempotency_scope: str

    def validate(self) -> None:
        if self.interval_start >= self.interval_end:
            raise ValueError("repair interval must be half-open and non-empty")
        if self.target_candidate == "active":
            raise ValueError("repair must not write directly to active output")
```

Real repair control needs authenticated approvals, catalog/storage transactions,
fencing, immutable receipts, quotas, audit, and recovery from controller failure.

## Communication and organizational learning

An update states incident ID/severity, observed consumer impact, bounded scope,
known facts, material uncertainty, containment, current work, requested consumer
action, next update, and owner. Avoid raw personal data, secrets, blame, unsupported
causes, or optimistic recovery estimates without assumptions.

A postmortem records impact with evidence, detection and response timeline,
technical and organizational contributing conditions, what helped/hindered,
counterfactual safeguards, and actions. “Human error” ends investigation too soon;
ask why the action was reasonable given interfaces, incentives, access, procedures,
and evidence. Blamelessness does not remove accountability for completing changes.

## Lifecycle, consistency, identity, and time

Incident state moves through suspected, declared, contained, repairing, monitoring,
consumer-recovered, closed, and learning/action follow-up. These states may regress.
Use UTC and preserve source timestamps; record when a fact became known separately
from when the underlying event occurred. Corrections append to the timeline.

Repair uses half-open data intervals, stable business/event keys, explicit late-
data policy, old/new publication IDs, and conditional activation. Downstream
systems may observe mixed versions unless cutover and cache/extract behavior are designed.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| No clear commander | Conflicting priorities/actions | Assign role; restate objectives and decision log |
| Premature root cause | Evidence conflicts/new impact appears | Mark hypothesis; broaden checks and preserve alternatives |
| Blind retry duplicates effects | Reconciliation/idempotency conflict | Fence attempts; repair duplicates; update procedure |
| Repair overloads current ingestion | Queue/freshness/resource signals | Throttle repair and reserve current-work capacity |
| Bad data already exported | Lineage plus consumer inventory | Notify, invalidate/rebuild, and confirm each consumer |
| Status leaks sensitive data | Review/access incident | Redact/restrict, rotate if secret, follow privacy/security process |
| Action ticket closes without evidence | Review finds risk unchanged | Reopen; define test and accountable acceptance |
| Incident system unavailable | Missing channel/page/timeline | Use rehearsed out-of-band communications and later reconcile |

## Security, privacy, and governance

Engage security/privacy/legal specialists when unauthorized access, sensitive data,
deletion, retention, fraud, or notification obligations may apply. Restrict raw
samples and forensic evidence; document chain/provenance; use break-glass access
with expiry and audit. Repair must reapply tenant isolation, classification,
retention, holds, and deletion suppression so restored/replayed data does not resurrect.

## Data quality, testing, and evidence

| Evidence | Environment/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Tabletop | Named missing/incorrect/unauthorized scenario | Roles, decisions, dependencies, communications exercised | Pending |
| Repair state/unit | Deterministic manifests and reruns | Invalid scope rejects; rerun converges | Pending |
| Reconciliation | Faulted candidate and independent expected set | Missing/unexpected/mismatch visible | Pending |
| Capacity isolation | Concurrent current + repair load | Current objective protected; drain measured | Pending |
| Consumer recovery | Staged extracts/cache/dashboard | Every known derived copy corrected/acknowledged | Pending |
| Postmortem action | Repeated fault after remediation | Detection/containment/recovery improves as claimed | Pending |

## Debugging guide

Start with incident ID, commander, consumer impact, first/last bad publication,
expected/current frontiers, change timeline, code/config/schema versions, lineage,
quality receipts, queue/resource state, and telemetry health. Separate the trigger,
proximate mechanism, enabling conditions, and systemic contributors. Before repair,
confirm authority and snapshot evidence. After repair, compare expected/actual at
record, aggregate, publication, and consumer boundaries.

## Common pitfalls

### Pitfall: fix first, preserve later

Overwriting candidates, logs, or configs destroys diagnosis and recovery inputs.
Apply reversible containment and preserve evidence before invasive change.

### Pitfall: declare recovery when the job is green

Historical gaps and downstream copies remain wrong. Reconcile the authoritative
dataset, derived publications, extracts/caches, and consumer-visible indicators.

### Pitfall: write “be more careful”

It is unactionable and untestable. Change a guardrail, interface, ownership,
automation, test, capacity policy, or review with measurable closure evidence.

## Performance, capacity, and cost

Model backlog rows/bytes, repair throughput, current arrival rate, effective drain
rate (`repair throughput - competing arrivals` where resources overlap), retry
amplification, storage for candidates/evidence, downstream rebuilds, and operator
load. Faster repair can expand blast radius or starve current work; optimize for
consumer recovery within safety and cost constraints.

## Observability and operations

Track detection, declaration, acknowledgement, containment, repair, certification,
and consumer-recovery timestamps; affected intervals/tenants/consumers; incident
reopens; page volume; communication cadence; repair backlog; reconciliation gaps;
and action aging. Metrics support learning but do not rank individual performance.

## Compatibility, migration, and delivery

Preserve old transform/contract environments long enough for governed replay or
define an approved semantic migration. Version repair manifests and comparison
queries. Incident changes follow expedited but reviewed delivery, canary, rollback,
and later reconciliation. Emergency access/config must expire and be removed.

## Working example

- Models: Planned repair manifest/state machine under `src/big_data_example/operations/`
- SQL: Planned record and aggregate reconciliation under `sql/operations/`
- Tests: Planned duplicate retry, partial publication, overload, downstream-copy, and resurrection cases
- Operations: Planned incident scenario, timeline, communications template, runbook, and postmortem
- Expected result: Harm is contained; repair is private/idempotent; every copy and consumer converges
- Scale represented: Local fixture and production estimate; no game day run
- Remaining risk: Real authority, workload contention, hidden consumers, privileged access, communications, and operator behavior

## Knowledge check

1. Explain why compute recovery and consumer recovery differ.
2. Predict the reconciliation output for missing, extra, and changed rows.
3. Diagnose a repair that restores the warehouse but not a BI extract.
4. Design roles and first update for an incorrect-publication incident.
5. Estimate drain time for a 750,000-event backlog under current traffic.
6. Plan replay across a transform-version change and rollback constraint.
7. Write one postmortem action with owner, risk, verification, and closure evidence.

## Key takeaways

- Incident command coordinates decisions before diagnosis is complete.
- Reversible containment and evidence preservation come before risky repair.
- Repair is a versioned data publication with independent reconciliation.
- Recovery includes every downstream copy and consumer-visible outcome.
- Learning actions are owned, prioritized, tested system changes.

## Resources

- [Google SRE Workbook: incident response](https://sre.google/workbook/incident-response/) (reviewed 2026-09)
- [Google SRE Workbook: postmortem culture](https://sre.google/workbook/postmortem-culture/) (reviewed 2026-09)
- [NIST SP 800-184 recovery guidance](https://csrc.nist.gov/pubs/sp/800/184/final) (reviewed 2026-09; cybersecurity recovery requires organizational tailoring)

## Related topics

- [Backups, restores, checkpoints, and DR](05-backups-restores-checkpoints-and-disaster-recovery.md)
- [Area 13 quarantine and repair](../13-data-quality-contracts-and-testing/07-quarantine-repair-replay-and-quality-incidents.md)
- [Infrastructure delivery and rollout](08-infrastructure-delivery-rollout-rollback-and-operations.md)

## Completion checklist

- [x] Roles, severity, containment, communication, repair, replay, reconciliation, learning, security, capacity, and delivery covered
- [x] Identity, time, authority, downstream recovery, and evidence boundaries explicit
- [x] SQL/Python models and working example accurately marked Planned
- [ ] Tabletop, repair, reconciliation, isolation, consumer, action, game-day, and production evidence executed
