# Identity, RBAC, ABAC, and Least Privilege

> Status: Documentation complete  
> Level: Intermediate to Senior  
> Applies to: Data platforms / Warehouses / Lakes / Orchestration / Services  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Authentication establishes a sufficiently trusted identity; authorization decides
whether that identity may perform an action on a resource in context. Role-based
access control (RBAC) groups stable job functions. Attribute-based access control
(ABAC) evaluates subject, resource, action, and environment attributes. Least
privilege limits scope, duration, and power to what the task requires.

This guide covers humans and workloads, service accounts, row/column controls,
delegation, short-lived access, separation of duties, and access review. It does
not select an identity provider or imply that network location is trust.

## Learning objectives

- Separate authentication, authorization, purpose approval, and data ownership.
- Choose RBAC, ABAC, or a constrained combination based on policy complexity.
- Design short-lived workload and emergency access without shared credentials.
- Verify denied paths, tenant/row/column scope, and revocation.
- Diagnose stale groups, policy drift, confused deputies, and administrator bypass.

## Prerequisites

- [Classification and purpose](02-classification-personal-data-and-purpose-limitation.md).
- Planned policy evaluator and real-engine integration for executable evidence.

## Mental model and terminology

Android runtime permission checks resemble authorization at a use boundary, but
data platforms also authorize scheduled workloads, SQL queries, exports, policy
changes, and cross-tenant operations long after the interactive user disappears.
An identity token is evidence about a subject, not permission by itself.

```text
verified subject + requested action + classified resource + purpose/context
                               |
                        policy decision point
                          /             \
                 allow with scope      deny + reason
                       |                    |
                 enforcement point     audit/alert
```

| Term | Meaning |
| --- | --- |
| Principal | Human, workload, or service identity requesting an action |
| RBAC | Permissions assigned through defined roles |
| ABAC | Decision based on attributes of subject, object, action, and environment |
| Entitlement | Concrete permission available to a principal |
| Separation of duties | Requiring independent identities for conflicting actions |
| Break-glass | Exceptional, time-bounded access with strong approval and review |
| Confused deputy | Authorized component tricked into using its authority for another party |

## Requirements, scale assumptions, and invariants

Assume 1,000 humans, 200 workloads, 100 tenants, 1,000 datasets, 50 roles, and
10,000 access decisions/minute at peak. Measure decision latency, cache hit rate,
revocation convergence, and policy size on the chosen systems.

Invariants:

- Every action is attributable to one non-shared principal and verified workload/user context.
- Default is deny; missing, invalid, expired, or contradictory required attributes do not grant access.
- Tenant, purpose, environment, action, and field/row scope survive every hop.
- Human credentials are not embedded in jobs; workload identities are unique by workload/environment.
- Grant approval, policy deployment, sensitive use, and audit administration are separated by risk.
- Emergency access expires automatically and is reviewed independently.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Identity provider | Principal, assurance, groups, expiry | Identity team | Reject invalid/expired token | External verified claims |
| Workload identity | Service, environment, deployment | Platform team | No fallback to shared account | Machine credential |
| Policy metadata | Roles, attributes, resource class, rules | Security + data owner | Last safe policy or deny | Privileged control state |
| Decision point | Subject/action/resource/context | Policy platform | Bounded timeout; deny risky request | Security boundary |
| Enforcement point | Scoped query/read/write/export | Resource platform | Stop if decision cannot bind action | Must resist bypass |

## RBAC, ABAC, and scoped enforcement

Use RBAC for stable responsibilities such as `metric_reader` or
`pipeline_publisher`. Use ABAC for facts such as tenant membership, dataset
classification, approved purpose, environment, region, time, device assurance,
and incident state. A practical model often uses roles for understandable job
functions and attributes for resource/context scope. Avoid a unique role for
every tenant-field-purpose combination.

| Requirement | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Stable job function | RBAC | Reviewable assignment | Roles explode with context |
| Tenant/data-class conditions | ABAC | Policy uses current attributes | Attribute authority is weak |
| Column/row filtering | Engine-native enforcement | Decision binds actual plan | Exports bypass the engine |
| One-time support case | Just-in-time grant | Narrow and expiring | Automation cannot revoke |

### SQL model

```sql
SELECT tenant_id, event_date, product_id, view_count
FROM governed_daily_metric
WHERE tenant_id = :authorized_tenant_id
  AND event_date >= :authorized_start_date;
```

Parameters prevent injection but do not create authorization. The engine or a
non-bypassable governed view must bind trusted session attributes to predicates;
never trust a tenant value supplied only by the caller. Test `NULL`, optimizer,
view-owner, export, and administrator semantics on the real engine.

### Python model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Request:
    principal: str
    action: str
    resource: str
    tenant: str
    purpose: str

def allowed(request: Request, *, tenants: frozenset[str],
            actions: frozenset[str], purposes: frozenset[str]) -> bool:
    return (request.tenant in tenants and request.action in actions
            and request.purpose in purposes)
```

This is a teaching predicate, not a secure policy engine. Production decisions
need verified attributes, policy versions, deny reasons, expiry, enforcement,
tamper resistance, and consistent semantics across systems.

## Identity and access lifecycle

Joiner/mover/leaver events provision, narrow, and revoke human access. Workload
identity follows deployment lifecycle and cannot be reused across dev/prod.
Access requests bind principal, resource, actions, purpose, approver, start/end,
and ticket/decision version. Reviews compare current entitlements with observed
use and current responsibility; inactivity is a signal, not automatic proof that
access is unnecessary.

Authorization consistency is bounded: cached decisions can briefly outlive a
revocation. Define maximum cache/token lifetime by risk, provide emergency deny,
and test propagation. Long jobs need admission plus renewal or a documented
snapshot rule; otherwise revocation semantics are ambiguous.

## Failure model and recovery

| Failure | Detection/containment | Recovery evidence |
| --- | --- | --- |
| Stale group after transfer | HR/directory/entitlement reconciliation | Old role revoked across all systems |
| Policy service unavailable | Deny risky operations; bounded safe cache | Service restored and decisions reconciled |
| Token stolen | Anomaly signal and emergency revoke | Token invalid after defined convergence bound |
| Row policy misses `NULL`/new tenant | Negative fixture and cross-tenant canary | No forbidden rows through query/export paths |
| Workload uses owner rights | Entitlement and query audit | Unique least-privilege identity deployed |
| Break-glass not revoked | Expiry monitor and alert | Grant expires; use independently reviewed |
| Administrator bypass | Separate admin plane and sensitive-read audit | Bypass constrained, attributed, and reviewed |

## Security, privacy, and governance

Protect identity attributes and policy administration as sensitive control data.
Prevent token forwarding to unintended services; bind audience and resource where
supported. Separate data owners who approve need from platform/security owners
who implement policy. Log decisions without tokens or raw sensitive values.

## Data quality, testing, and evidence

| Evidence | Environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Policy table test | Deterministic principals/resources | Allow/deny matrix | Exact decisions and reasons | Pending |
| Negative access | Real test engine | Query/read/write/export forbidden scopes | All paths deny | Pending |
| Revocation drill | Test identity and caches | Revoke active grant/token | Denied within objective | Pending |
| Separation test | Test approval/deploy/audit roles | Attempt self-approval/tamper | Conflicting action denied | Pending |
| Tenant fuzz | Generated scoped records | Cross-tenant/property cases | Zero foreign rows | Pending |

## Debugging guide

Capture correlation ID, principal, authentication assurance, token audience/expiry
(never the token), action, canonical resource, tenant, purpose, policy version,
decision reason, enforcement point, query/job/run, and cache age. Reproduce with
safe synthetic principals. Determine whether identity, attributes, policy,
decision, or enforcement owns the defect. An allow decision alone does not prove
the engine enforced its scope.

## Common pitfalls

### Pitfall: role per combination

Tenant x dataset x action x environment roles become unreviewable. Use stable
roles plus authoritative attributes and constrained policy composition.

### Pitfall: grant the orchestrator broad downstream access

All jobs inherit one blast radius. Exchange or mint a workload-specific,
short-lived credential scoped to the task and environment.

### Pitfall: test only successful access

Security guarantees live in denied paths. Test wrong tenant, field, purpose,
environment, expired identity, export, admin, and policy-outage cases.

## Performance, observability, and cost

Budget decision p95/p99 latency, availability, policy fetch/cache age, token
issuance, enforcement overhead, group cardinality, and audit volume. Monitor deny
rate by low-cardinality reason, expired grants, dormant privileges, orphan service
accounts, revocation lag, break-glass use, and policy drift. Never label metrics by
raw user or resource ID at high cardinality.

## Compatibility, migration, and delivery

Version policies, attributes, role definitions, token claims, and enforcement
adapters. Shadow-evaluate new rules, diff decisions, resolve unexpected allows,
then canary enforcement. Rollback to the last safe policy must not restore a known
forbidden grant. Mixed-version clients must not omit new required context and gain access.

## Working example

- Policy model: Planned under `src/big_data_example/security/`
- SQL: Planned governed views and negative queries under `sql/security/`
- Tests: Planned matrix, tenant property, expiry, outage, revocation, and separation cases
- Expected result: Only verified, scoped, current decisions reach enforcement
- Scale represented: Local model and production estimate; no identity/engine integration
- Remaining risk: Platform bypass, policy consistency, identity compromise, query semantics, and administrators

## Knowledge check

1. Distinguish authentication, authorization, purpose, and ownership.
2. Predict a decision when one required ABAC attribute is missing.
3. Diagnose cross-tenant rows despite a correct policy-service response.
4. Design support access for one tenant and two hours.
5. Estimate peak policy calls with a stated cache hit rate.
6. Plan shadow-to-enforce migration for a new purpose attribute.
7. Add a negative export-path test.

## Key takeaways

- Identity evidence is input to authorization, not authorization itself.
- Roles express stable responsibility; attributes express dynamic scope and context.
- Least privilege covers action, data, tenant, environment, and time.
- Enforcement and denied-path evidence matter more than policy text alone.
- Revocation and exceptional access need explicit convergence guarantees.

## Resources

- [NIST SP 800-162: ABAC definition and considerations](https://csrc.nist.gov/pubs/sp/800/162/upd2/final) (reviewed 2026-09)
- [NIST SP 800-207: Zero Trust Architecture](https://csrc.nist.gov/pubs/sp/800/207/final) (reviewed 2026-09)
- [NIST SP 800-207A: cloud-native access control](https://csrc.nist.gov/pubs/sp/800/207/a/final) (reviewed 2026-09)

## Related topics

- [Classification and purpose](02-classification-personal-data-and-purpose-limitation.md)
- [Audit and policy enforcement](07-audit-policy-enforcement-and-compliance-evidence.md)
- [Tenant isolation](08-tenant-isolation-abuse-supply-chain-and-governance-operations.md)

## Completion checklist

- [x] Human/workload identity, RBAC, ABAC, least privilege, lifecycle, failure, security, scale, and migration covered
- [x] SQL/Python models and denied-path evidence plan supplied
- [x] Working example accurately marked Planned
- [ ] Policy, engine, revocation, tenant, administrator, scale, and production evidence executed

