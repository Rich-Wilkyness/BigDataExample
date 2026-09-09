# Audit, Policy Enforcement, and Compliance Evidence

> Status: Documentation complete  
> Level: Intermediate to Senior  
> Applies to: Data platforms / SQL / Batch / Streaming / Operations  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Policy states required behavior. Enforcement prevents, constrains, or changes an
action at a boundary. Audit records describe security-relevant decisions and
outcomes. Compliance evidence links scoped requirements to control design,
operation, exceptions, and independently reviewable results. Logs alone prove
neither intent nor compliance.

This guide develops policy-as-versioned-input, decision/enforcement evidence,
tamper detection, access review, control testing, exceptions, and evidence
boundaries. It does not certify the organization against a framework or replace
qualified audit, legal, privacy, or security judgment.

## Learning objectives

- Map requirement -> risk -> control -> enforcement point -> evidence -> owner.
- Design minimal, attributable audit events without logging sensitive payloads.
- Distinguish preventive, detective, corrective, and compensating controls.
- Test policy decisions, enforcement coverage, audit completeness, and tamper handling.
- Explain what a piece of evidence supports and what remains unproven.

## Prerequisites

- [Ownership](01-data-ownership-stewardship-catalogs-and-lineage.md), [access](03-identity-rbac-abac-and-least-privilege.md), and [lifecycle](06-retention-deletion-legal-holds-and-data-subject-workflows.md).
- Planned policy evaluator, audit event store, and real enforcement integration.

## Mental model and terminology

An Android test report does not prove the installed application uses the same
code/configuration. Likewise, a data control screenshot proves a moment, not the
deployed policy, all paths, or operation over time. Evidence must bind requirement,
policy version, subject, resource, deployment, decision, enforcement, and outcome.

```text
requirement -> risk -> control design -> deployed enforcement
                                  |              |
                                  +--> decision/action events
                                                |
                         protected evidence + independent tests
                                                |
                               review / exception / remediation
```

| Term | Meaning |
| --- | --- |
| Policy | Versioned rule describing required/allowed behavior and scope |
| Enforcement point | Component that binds a decision to the actual action |
| Audit event | Attributable record of a security/governance-relevant occurrence |
| Control | Measure that changes likelihood, impact, detection, or recovery |
| Evidence | Artifact supporting a bounded claim for a time/scope/version |
| Exception | Approved, expiring departure with owner and compensating controls |
| Immutable | Not modifiable through normal interfaces; not a claim of absolute impossibility |

## Requirements, scale assumptions, and invariants

For each control record requirement/risk IDs, owner, scope, systems, policy/code/
configuration versions, enforcement point, evidence source, frequency, expected
result, reviewer independence, exception process, and retention. Assume 10,000
decisions/minute peak, 50 million audit events/month, 100 controls, and 1,000 datasets.

Invariants:

- Every high-risk allowed/denied action is attributable to a verified principal, resource, action, decision/policy version, enforcement point, time, and outcome.
- Audit records omit secrets and unnecessary payload while retaining correlation and decision meaning.
- Evidence storage has stricter write/delete separation than ordinary operational logs.
- Missing/stale evidence remains unknown or failed according to the control; it is never silently passing.
- Policy authors cannot unilaterally alter enforcement and erase its evidence.
- Exceptions specify scope, reason, approvers, compensating controls, expiry, review, and closure proof.
- A compliance statement never exceeds the systems, period, sample, control, and reviewer represented.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Requirement/control register | Scope, owner, test, evidence | Governance/risk owner | Unmapped requirement stays open | Approved assertion |
| Policy build/deploy | Source, review, artifact digest, target | Security/platform | Reject unsigned/unapproved artifact | Delivery boundary |
| Enforcement | Decision bound to action/outcome | Resource owner | Deny or documented safe degraded mode | Security boundary |
| Audit collector | Versioned safe event + identity | Evidence platform | Buffer/backpressure/alert; no silent drop | Untrusted producer input |
| Evidence store | Append-oriented events and corrections | Independent admin | Detect tamper; restricted delete | High-value evidence |
| Review/export | Scoped query and attestation | Control owner/reviewer | Redact and expire export | Human boundary |

## Audit event and evidence design

A useful event contains event/schema version, event ID, occurred/observed times,
principal/workload, authentication context reference, canonical action/resource,
tenant/purpose, policy version, decision and reason, enforcement point, outcome,
correlation/run/query ID, source deployment, and integrity metadata. Avoid tokens,
SQL literals, raw subject identity, payload, encryption material, and uncontrolled
exception text.

### SQL model

```sql
SELECT e.policy_version, e.decision_reason,
       COUNT(*) AS decision_count
FROM access_decision_event e
WHERE e.occurred_at_utc >= :window_start
  AND e.occurred_at_utc < :window_end
GROUP BY e.policy_version, e.decision_reason;
```

This summarizes present events; it cannot detect events that were never emitted.
Compare against an independent count of protected operations or gateway/query
receipts. Define late-arrival cutoff and correction behavior.

### Python model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ControlResult:
    control_id: str
    scope_version: str
    expected: int
    observed: int
    failures: int

    def state(self) -> str:
        if self.observed < self.expected:
            return "unknown"
        return "fail" if self.failures else "pass"
```

Real controls need evidence-source independence, duplicate handling, eligibility,
late events, sampling, reviewer identity, and signed/versioned results.

## Policy and evidence lifecycle

Draft policy from approved requirements; peer/security review; compile and test;
sign/version artifact; shadow/canary; deploy to named targets; observe decision
diffs; enforce; periodically review; supersede; retain policy and evidence under
approved schedules. Evidence exports are new sensitive datasets with purpose,
access, watermarking where appropriate, and expiry.

Audit time is both occurrence and observation. Clocks drift and delivery is late;
retain event identity and source sequence where available. Append corrections
rather than editing historical facts. Hash chains, signatures, write-once controls,
and separate administration can raise tamper evidence, but their guarantees and
root-of-trust limitations must be tested and stated.

## Failure model and recovery

| Failure | Detection/containment | Recovery evidence |
| --- | --- | --- |
| Enforcement allows but audit emit fails | Couple receipt/outbox or fail risky action | Backlog replay and independent operation reconciliation |
| Audit flood exhausts storage | Quotas, backpressure, isolation, alert | Restore capacity; account for dropped/late events |
| Attacker injects log delimiters/content | Structured schema and sanitization | Reject/sanitize; preserve safe forensic copy |
| Policy artifact differs by target | Digest/config inventory | Redeploy known artifact; diff decisions |
| Evidence is deleted/modified | Integrity monitor and separate copy | Incident, restore, verify chain/gaps |
| Exception expires unnoticed | Expiry alert and default reversion | Remove grant; assess use after expiry |
| Dashboard green while collector stalled | Collector heartbeat plus independent receipts | Mark unknown; replay; recompute window |
| Sampling misses rare privileged use | Risk-based full capture for critical action | Expand scope; inspect independent source |

## Security, privacy, and governance

Audit systems centralize identity, resource, behavior, incident, and business
information and are prime exfiltration targets. Apply least privilege, tenant
separation, field minimization, encryption, query auditing, export controls,
integrity monitoring, lifecycle, and emergency access. Sanitize untrusted fields
to prevent log injection. Never disable required audit because the actor is
internal or “trusted.”

## Data quality, testing, and evidence

| Evidence | Environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Policy tests | Deterministic decision matrix | Planned allow/deny/mutation cases | Expected decisions/reasons | Pending |
| Enforcement integration | Real test query/storage paths | Forbidden action attempts | Decision binds every action | Pending |
| Completeness | Independent operation receipts | Planned reconciliation | Missing/duplicate events visible | Pending |
| Tamper | Protected test store | Modify/delete/reorder attempts | Prevented or detected with bounded delay | Pending |
| Exception | Expiring test grant | Planned expiry/review drill | Reverts and alerts as designed | Pending |
| Restore | Evidence backup | Planned restore/reconciliation | History, integrity, and gaps accounted | Pending |

## Debugging guide

Start with requirement/control, scope period, policy artifact digest, target,
principal, action, resource, decision, enforcement outcome, event ID/sequence,
collector lag, store partition, evidence query version, exception, and reviewer.
Compare independent operation receipts with audit events. Restrict raw event
access and produce redacted review extracts. Close only when control state,
evidence gaps, affected actions, remediation, and exception status reconcile.

## Common pitfalls

### Pitfall: screenshot equals evidence

A screenshot lacks reproducible query, dataset, scope, version, and completeness.
Store machine-readable results and provenance, then use a view only as presentation.

### Pitfall: “immutable” means trustworthy

An append-only store can faithfully retain forged, missing, duplicated, or
misattributed events. Authenticate producers and reconcile with independent facts.

### Pitfall: collect complete SQL and payloads

Audit becomes a secret/PII warehouse. Record canonical resources, operation
shape/digest, outcome, and protected correlation; retrieve payload only through a
separate approved forensic process.

## Performance, observability, and cost

Budget audit events/bytes, peak ingestion, partitions, index/cardinality, query
latency, hot/archive retention, export volume, and restore time. Monitor collector
availability/lag, rejected/duplicate events, independent completeness ratio,
integrity failures, policy target drift, expired exceptions, sensitive queries,
and review backlog. High-cardinality detail belongs in protected event storage,
not metric labels.

## Compatibility, migration, and delivery

Version event schemas, decision reasons, policy language/compiler, artifacts,
control tests, evidence queries, and reports. Consumers tolerate additive fields;
producers dual-emit or adapt during migration; evidence queries compare old/new
semantics. Preserve historical interpretation. Rollback must retain newly emitted
events and must not reinstall a policy with a known unsafe allow.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Synchronous audit gate | Missing record is intolerable | Availability/latency coupling | Durable outbox gives equivalent proof |
| Full critical capture | Privileged/sensitive actions | Storage/privacy cost | Low-risk high-volume diagnostics |
| Central evidence store | Cross-platform review | Concentrated blast radius | Domain isolation requirements dominate |
| Automated control | Deterministic machine boundary | Shared defect can fool check | Independent human/system evidence needed |

## Working example

- Models: Planned policy/audit/control result under `src/big_data_example/governance/`
- SQL: Planned decision and completeness queries under `sql/governance/`
- Tests: Planned policy, enforcement, injection, completeness, tamper, exception, and restore cases
- Expected result: Missing evidence is unknown; forbidden operations deny; tamper/gaps surface
- Scale represented: Local fixture and production estimate; no audit platform operated
- Remaining risk: Producer compromise, administrator collusion, cross-platform gaps, volume, and audit interpretation

## Knowledge check

1. Trace requirement to enforcement and evidence.
2. Predict control state when expected operations exceed audit events.
3. Diagnose a green report from a stalled collector.
4. Design a safe audit event for restricted table export.
5. Estimate monthly storage from event rate and encoded size.
6. Plan a decision-reason schema migration preserving history.
7. Add an independent completeness check.

## Key takeaways

- Policy, enforcement, audit, and evidence are distinct linked guarantees.
- Evidence claims are bounded by scope, time, version, source, and independence.
- Missing evidence stays visible rather than becoming pass.
- Audit data requires strong privacy, security, lifecycle, and tenant controls.
- Exceptions are expiring governed objects, not permanent tickets.

## Resources

- [NIST SP 800-53 Rev. 5 controls](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) (reviewed 2026-09; tailoring and assessment remain organization-specific)
- [NIST SP 800-53A Rev. 5 assessment procedures](https://csrc.nist.gov/pubs/sp/800/53/a/r5/final) (reviewed 2026-09)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) (reviewed 2026-09)

## Related topics

- [Identity and least privilege](03-identity-rbac-abac-and-least-privilege.md)
- [Retention and deletion](06-retention-deletion-legal-holds-and-data-subject-workflows.md)
- Area 15 reliability and observability (planned)

## Completion checklist

- [x] Policy, enforcement, audit, controls, exceptions, integrity, failure, security, scale, and migration covered
- [x] Compliance/evidence scope boundary explicit
- [x] Working example accurately marked Planned
- [ ] Policy, enforcement, completeness, tamper, exception, load, restore, and production evidence executed

