# Quarantine, Repair, Replay, and Quality Incidents

> Status: Documentation complete; executable recovery evidence planned  
> Level: Intermediate to Senior  
> Applies to: Batch / Streaming / Storage / Warehouses / Operations  
> Data scale: Local fault fixture; production estimate  
> Example status: Planned  
> Evidence status: Documentation and primary-source review only  
> Last reviewed: 2026-09

## Overview

Quarantine contains data that cannot safely enter a declared dataset. Repair
changes data, code, configuration, reference state, or a contract decision.
Replay re-executes bounded input through a known implementation. A quality
incident exists when data violates a guarantee or creates material consumer
risk—not merely whenever a rule emits a warning.

Containment is not recovery. A dead-letter store can silently accumulate loss,
and replay can duplicate effects or reproduce the original defect. Recovery ends
only after authoritative datasets converge, consumers receive a corrected
version, and reconciliation proves the intended result.

## Learning objectives

- Choose reject, quarantine, defer, accept-with-label, or halt dispositions.
- Design safe rejected-record records and bounded backlogs.
- Separate correction authority from replay mechanics.
- Run idempotent, versioned repair and replay with reconciliation.
- Coordinate incident detection, consumer communication, and closure evidence.

## Prerequisites

- [Contracts and enforcement](02-schema-data-and-consumer-contracts.md).
- [Integration/fault testing](04-integration-contract-and-end-to-end-pipeline-testing.md).
- [Reconciliation checks](06-reconciliation-freshness-volume-and-distribution-checks.md).
- Area 07 rerun/backfill and Areas 10–12 replay, publication, and workflow operations.

## Mental model and terminology

```text
violation detected
      |
classify harm and scope
      |
      +--> reject/quarantine/defer/label/halt
      |
preserve prior certified version + communicate
      |
identify authority -> correct privately -> replay bounded interval
      |
reconcile -> certify new version -> consumers confirm -> close/learn
```

| Term | Meaning in this guide |
| --- | --- |
| Quarantine | Access-controlled state for data excluded pending a governed disposition |
| Rejection | Decision that input does not enter a boundary under a named rule/version |
| Repair | Authorized correction of data or behavior with traceable provenance |
| Replay | Reprocessing identified authoritative input through specified versions/configuration |
| Blast radius | Consumers, datasets, tenants, intervals, and decisions that may be affected |
| Convergence | Authoritative and derived states agree with the repaired contract after replay |
| Quality incident | Coordinated response to material data-contract or consumer harm |

This resembles retrying a failed WorkManager task only until durable data effects
matter. Pipeline retries cross external systems and historical versions; rerun
success cannot retract a dashboard export or notification already consumed.

## Requirements, scale assumptions, and invariants

- Every rejected item retains source identity/position, contract and rule
  versions, bounded reason code, first/last observed time, protected payload
  reference or governed digest, and disposition state.
- Raw replay authority remains immutable; corrected records are new governed
  versions linked to originals, not silent overwrites.
- Exact delivery duplicates and conflicting logical duplicates have separate
  dispositions.
- Repair authority belongs to the source/domain owner. Operators may contain and
  execute approved replay but do not invent business values.
- Replay is bounded by tenant, interval, source frontier, contract/code/config
  versions, and destination generation; it is idempotent within that scope.
- Prior certified data remains available unless its harm requires explicit
  withdrawal. Candidates never overwrite certified output in place.
- Closure requires restored SLO/contract, source-to-target reconciliation,
  backlog disposition, corrected consumer publication, and communication.
- 3 million events/day and 35 hot replay days imply up to 105 million events;
  replay throughput, quarantine arrival/backlog, and downstream capacity are
  unmeasured.

## Disposition decision table

| Condition | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Malformed required identity | Reject/quarantine | Cannot safely identify/deduplicate | Producer can synchronously correct before acceptance |
| Unknown future optional field | Accept only if extension policy permits | Preserves compatible evolution | Field may contain sensitive/unsafe content |
| Reference data temporarily unavailable | Defer with bounded retry | Validity is presently unverifiable | Backlog threatens SLO or reference snapshot expires |
| Exact transport redelivery | Deduplicate and account | Logical fact already represented | Payload differs under same key |
| Conflicting duplicate | Quarantine conflict | Arbitrary winner corrupts meaning | Domain contract defines version/sequence resolution |
| Small nonblocking diagnostic anomaly | Accept with quality label | Availability tradeoff is explicit | Consumer harm or error budget exceeds threshold |
| Systemic contract mismatch | Halt/hold publication | Continued processing expands blast radius | Independently safe partitions can be isolated |

## Quarantine state and safe record

```text
observed -> triaged -> {discarded | producer-corrected | rule-corrected}
                              |                  |
                              +------> replay-approved -> replayed -> reconciled
```

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class RejectedRecord:
    rejection_id: str
    source_identity: str
    payload_digest: str
    protected_payload_ref: str | None
    rule_id: str
    rule_version: str
    reason_code: str
    observed_at: datetime
    contract_version: str | None

    # Never put raw payload, secrets, or free-form exception text in the safe
    # operational representation.
```

The payload digest supports correlation, not necessarily identity or anonymity.
The protected payload copy has source-equivalent classification, encryption,
access, retention, deletion, and audit obligations.

## Repair and replay protocol

1. Freeze the affected certification path and preserve current certified versions.
2. Establish blast radius from lineage, frontiers, rules, releases, and first/last bad evidence.
3. Name the authoritative source and obtain domain approval for correction semantics.
4. Create an immutable repair manifest: incident, scope, source frontier, input/correction versions, code/config/rule versions, destination, expected counts, owner, and rollback.
5. Dry-run a minimal fixture and representative interval into an attempt-private destination.
6. Execute with bounded concurrency and current-work reserve; record per-partition receipts.
7. Reconcile raw accounting, validated identities, output grain/measures, and quarantine dispositions.
8. Atomically certify a new publication, notify consumers, and monitor correction behavior.
9. Retain evidence and expire temporary/corrected copies according to policy.

```sql
-- Repair audit relation. Never update original history without trace.
select original_source_identity, count(*) as active_corrections
from event_corrections
where repair_manifest_id = :repair_manifest_id
  and correction_status = 'approved'
group by original_source_identity
having count(*) <> 1;
```

One correction per identity is only an example invariant; superseding corrections
may require effective versions instead. Bind parameters and use a transaction or
table-snapshot commit appropriate to the engine.

## Data flow, ownership, and trust boundaries

| Boundary | Authority/owner | Failure behavior | Trust level |
| --- | --- | --- | --- |
| Raw replay input | Ingestion owner; original bytes/positions | Immutable, access-controlled | Authoritative receipt, not semantic truth |
| Quarantine | Ingestion + domain owner | Bounded, alerted, lifecycle-managed | Untrusted sensitive data |
| Correction manifest | Domain/data owner approval | Immutable versions; reject unauthorized edit | Governance authority |
| Replay job | Pipeline owner | Attempt-private output and resumable receipts | Controlled execution |
| Certification | Dataset owner | Conditional activation after reconciliation | Governed output |
| Consumer remediation | Consumer owner | Requery/reload/retract external effect | Outside pipeline transaction |

## Failure model and recovery

| Failure | Detection/containment | Recovery and convergence |
| --- | --- | --- |
| Quarantine grows silently | Arrival/backlog age and capacity objective | Triage owners, pause source if needed, drain approved cases |
| Payload lost before triage | Missing protected reference/control count | Recover from raw authority; fix retention ordering |
| Repair picks wrong authority | Independent review/reconciliation disagreement | Withdraw candidate, correct manifest, rerun |
| Replay duplicates sink effects | Idempotency ledger/key mismatch | Reconcile effects, compensate if possible, resume fenced run |
| Replay starves current pipeline | Queue/freshness burn | Throttle replay and reserve production capacity |
| Rule fixed but history remains wrong | Publication/consumer version inspection | Rebuild affected closure and certify corrected generation |
| Correction reaches warehouse but not export | Consumer acknowledgement/lineage gap | Regenerate/retract export and communicate |
| Replay input expired | Retention/frontier check | Restore authorized archive or document irrecoverable loss |

## Incident severity and communication

Severity follows consumer harm, affected scope, duration, reversibility, and
regulatory/privacy impact—not row count alone. The incident record names status,
first/last bad versions, affected consumers, safe workaround, certification
state, next update time, and owner. Do not speculate on cause before evidence.

Corrected tables do not automatically correct cached dashboards, extracts,
models, alerts, decisions, or external messages. Each consumer owner acknowledges
its remediation or accepts documented residual risk.

## Security, privacy, and governance

Quarantine is a high-risk trust boundary. Use least privilege, separate service
roles, encryption, short retention, access audit, safe reason codes, and no raw
payload in logs/metrics/tickets. Repairs preserve lineage and approval; privacy
deletions and legal holds apply to raw, rejected, corrected, attempt-private,
backup, and exported copies. Incident communication minimizes sensitive detail.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Disposition fixture | Planned invalid/duplicate/unverifiable cases / local | Apply decision policy | Correct stable state/reason | Pending |
| Replay idempotency | Faulty interval / integration stack | Crash at write/commit/receipt points and resume | One logical corrected outcome | Pending |
| Reconciliation | Repair candidate + controls / real engine | Run accounting and keyed comparison | Exact declared convergence | Pending |
| Capacity isolation | 35-day synthetic replay + current work | Sweep bounded concurrency | Current freshness remains within budget | Pending |
| Incident drill | Staged quality failure | Detect, contain, communicate, repair, replay | Detection/recovery evidence and consumer signoff | Pending |

## Debugging guide

1. Capture incident, source identities/frontier, rules, contracts, releases, publications, and affected consumers.
2. Stop expansion of harm while preserving raw authority and prior certified data.
3. Inspect rejected counts/age, safe reason codes, lineage, and accounting by failure domain.
4. Determine correction authority and distinguish data, code, configuration, reference, and rule defects.
5. Rehearse the exact manifest on a minimal protected case and private destination.
6. Replay, reconcile each boundary, certify a new version, remediate consumers, and record closure evidence.

## Common pitfalls

### Pitfall: quarantine forever

Unbounded quarantine converts visible rejection into hidden data loss and
sensitive storage growth. Define capacity, age objective, disposition owner, and
retention.

### Pitfall: edit bad rows in place

It destroys provenance and replayability. Keep immutable source and versioned
correction/derived publications.

### Pitfall: declare recovery when the job turns green

Consumers may still hold bad exports or caches. Require reconciliation,
corrected certification, and consumer acknowledgement.

## Performance, capacity, and cost

Measure rejection arrival, backlog rows/bytes/oldest age, triage throughput,
payload retention, replay read/write/shuffle, retries, downstream amplification,
current-work latency, and cost. Estimate drain time as backlog divided by net
safe drain rate, not peak benchmark throughput. Reserve capacity and throttle by
downstream bottleneck.

## Compatibility, migration, and delivery

Version rejection reasons, quarantine schema, correction manifests, replay code,
and disposition state. Readers accept old/new records during migration; do not
drop payload references before historical cases close. Canary new rules in
shadow, test rollback of policy and code, and keep data correction rollback
separate from deployment rollback.

## Working example

- Models: Planned rejected-record and repair-manifest types under `src/big_data_example/quality/`
- SQL: Planned repair audit and reconciliation under `sql/quality/`
- Fixtures: Planned invalid, conflict, lost-ack, partial replay, and expired-input cases
- Runbook: Planned under this area with repeatable local/integration commands
- Expected result: Faults are contained; replay produces one reconciled corrected publication
- Evidence: Planned state transitions, receipts, fault timeline, capacity result, and incident record
- Scale represented: Local fixture then production-shaped integration/load drill
- Remaining risk: External effects, distributed fencing, archive restore, production capacity, and human response

## Knowledge check

1. Explain why quarantine is containment rather than recovery.
2. Predict what happens when replay reuses an unstable idempotency key.
3. Diagnose a green rerun whose dashboard export remains wrong.
4. Design a safe rejected-record representation for malformed identity.
5. Estimate drain time and production reserve for a 35-day backlog.
6. Plan correction/replay with an immutable manifest and rollback.
7. Add closure criteria for a consumer with an offline export.

## Key takeaways

- Quarantine requires disposition, capacity, privacy, and age ownership.
- Correction semantics come from an authority; replay is only a mechanism.
- Immutable raw input and versioned repair preserve audit and reproducibility.
- Recovery is proven by end-to-end reconciliation and consumer remediation.
- Deployment rollback and data-effect rollback are distinct operations.

## Resources

- [Google SRE Workbook: incident response](https://sre.google/workbook/incident-response/) (reviewed 2026-09)
- [Google SRE Book: data integrity](https://sre.google/sre-book/data-integrity/) (reviewed 2026-09)
- [NIST SP 800-61 Rev. 3 incident response recommendations](https://csrc.nist.gov/pubs/sp/800/61/r3/final) (reviewed 2026-09; security incidents differ, but lifecycle/coordination principles inform operations)

## Related topics

- [Reconciliation checks](06-reconciliation-freshness-volume-and-distribution-checks.md)
- [Quality objectives and evidence](08-quality-objectives-observability-and-evidence-portfolios.md)
- [Area 07 batch repair](../07-batch-processing-and-etl-elt/README.md)

## Completion checklist

- [x] Quarantine, disposition, correction, replay, incidents, and convergence defined
- [x] Ownership, identity, time, privacy, failure, capacity, migration, and consumer repair covered
- [x] Closure evidence distinguished from task success
- [x] Working example and executable evidence accurately marked Planned
- [ ] State, replay fault, reconciliation, load, incident-drill, and consumer evidence executed
