# Infrastructure, Delivery, Rollout, Rollback, and Operations

> Status: Documentation complete; executable delivery evidence planned  
> Level: Intermediate to Senior  
> Applies to: Infrastructure / Containers / Batch / Streaming / Data platforms  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Operational delivery moves reviewed code, configuration, schemas, data migrations,
and infrastructure from declared intent to running state while preserving service
and data guarantees. Infrastructure as code (IaC) makes desired resources and
change plans inspectable, but providers, state, credentials, controllers, and data
effects still fail. Rollback restores a compatible prior control state; it cannot
automatically undo irreversible data written by new code.

This guide covers artifacts, environments, containers, IaC, health, drain,
rollout, migration, rollback, drift, routine operations, and DR integration. It
does not select a CI/CD system, container platform, or IaC implementation.

## Learning objectives

- Define build-once artifact promotion and environment/configuration boundaries.
- Review IaC plans, state, drift, dependency order, and privileged execution.
- Design startup, readiness, liveness, drain, checkpoint, and shutdown behavior.
- Roll out code/schema/data/infrastructure changes with canaries and reconciliation.
- Distinguish rollback, roll-forward, data repair, restore, and disaster recovery.

## Prerequisites

- [Area 12 environment and rollout operations](../12-workflow-orchestration-and-transformation-management/08-environments-secrets-ci-cd-rollout-and-orchestrator-operations.md).
- [Backups/restores/DR](05-backups-restores-checkpoints-and-disaster-recovery.md), [performance/capacity](06-performance-profiling-query-plans-and-capacity-modeling.md), and [cost/isolation](07-cost-modeling-finops-quotas-and-workload-isolation.md).
- No container runtime, cluster, IaC CLI, registry, or cloud target is selected for this documentation pass.

## Mental model and terminology

```text
source + lock/config/schema/migration
          |
          v
reproducible build -> signed/versioned artifact -> test evidence -> promotion
                                                        |
desired infrastructure -> reviewed plan -> apply/reconcile actual state
                                                        |
canary by failure domain -> observe/gate -> expand -> reconcile -> complete
                              |             |
                         rollback control   +-> data forward repair when needed
```

| Term | Meaning in this guide |
| --- | --- |
| Desired state | Reviewed declaration of intended resources/configuration |
| IaC state | Sensitive mapping/metadata used by a tool to relate declaration to real resources |
| Drift | Actual state differs from governed desired/state knowledge |
| Artifact promotion | Moving the same immutable build digest across environments |
| Canary | Bounded release slice chosen to reveal risk before broad exposure |
| Readiness | Instance may accept its assigned work safely |
| Liveness | Instance is irrecoverably stuck enough that restart is the correct response |
| Drain | Stop new work and finish/checkpoint/fence admitted work before termination |
| Rollback | Restore prior compatible control artifact/configuration; not generic data undo |

A staged Android rollout is a useful analogy for canary exposure and crash-rate
gates. The analogy stops because pipeline jobs may run once per day, background
workers own durable checkpoints, and a new transform can permanently publish
data before enough runtime signal exists. Shadow/differential runs and explicit
data repair often matter more than percentage-of-instances rollout.

## Requirements, scale assumptions, and invariants

Define artifacts, environments/accounts/regions, failure domains, data/control
dependencies, compatibility window, rollout unit, objective gates, access, change
window, drain time, rollback/repair boundary, state/backup, cost, and owners. Assume
100 workflows, 10,000 task instances/day, 100 tenants, 35-day replay, and 120-minute
publication deadline; deployment concurrency and infrastructure size are unmeasured.

Invariants:

- The same immutable artifact digest is promoted; environment-specific values are validated external configuration.
- Plans/builds record source revision, dependencies, tool/provider versions, policy/test results, approver, target, and artifact digest.
- IaC state, plans, secrets, and credentials are protected, locked where required, backed up, and never exposed as ordinary logs/artifacts.
- Mixed versions preserve schema/event/table/checkpoint/API compatibility for the documented window.
- Readiness prevents unsafe admission; liveness does not restart healthy-but-overloaded work into a cascade.
- Termination stops admission, fences ownership, commits/checkpoints consistently, and completes within a measured grace budget.
- Canary gates include consumer correctness/freshness, resource/cost, security, and telemetry health—not process health alone.
- Rollback is permitted only when old code can safely read current state/data; otherwise contain and roll forward/repair.

## Data flow, ownership, and trust boundaries

| Boundary | Authority/owner | Failure behavior | Trust |
| --- | --- | --- | --- |
| Source/dependencies | Engineering owner | Reviewed/locked; untrusted dependency inputs verified | Supply-chain boundary |
| Build/sign/registry | Delivery/platform owner | Reject unknown digest/provenance | Artifact authority |
| Environment config/secrets | Environment/security owners | Validate references; no secret in artifact/plan output | Privileged boundary |
| IaC plan/state/apply | Platform owner and approver | Lock, scoped credentials, explicit partial failure | High-impact control plane |
| Runtime controller | Platform owner | Reconcile instances but not application data semantics | Ephemeral compute |
| Dataset/catalog migration | Dataset owner | Expand/migrate/contract and conditional activation | Durable consumer boundary |
| Observability/change record | Service owner | Stale/unknown blocks unsafe expansion | Derived operational evidence |

## Delivery and infrastructure model

A pipeline promotes an immutable code/container artifact plus independently
versioned configuration/schema/migration. Build in CI, generate SBOM/provenance as
required, scan/test, deploy to an isolated environment, execute contract/data/
recovery checks, then promote by digest. Never rebuild “the same version” per environment.

IaC follows format/validate/policy/test, refresh/read, plan, human or governed
approval, apply with scoped credentials, post-apply inventory/health, and drift
detection. A saved plan is sensitive and time-bound because external state can
change; an apply can partially succeed and needs reconciliation rather than blind retry.

### Infrastructure sketch

```yaml
# Illustrative Kubernetes fragment; exact API/version and values require testing.
startupProbe:
  httpGet: {path: /started, port: 8080}
readinessProbe:
  httpGet: {path: /ready, port: 8080}
livenessProbe:
  httpGet: {path: /live, port: 8080}
terminationGracePeriodSeconds: 120
```

Startup, readiness, and liveness answer different questions. A readiness check
may consider ability to accept work, but it should not require every optional
dependency. A liveness check should detect unrecoverable local lack of progress,
not shared overload; otherwise restarts remove capacity and amplify the incident.

### SQL migration model

```sql
-- Expand: additive nullable column, with old readers/writers still compatible.
ALTER TABLE daily_product_metric ADD COLUMN metric_version INTEGER;

-- Migrate: bounded idempotent backfill in a separate reviewed operation.
UPDATE daily_product_metric
SET metric_version = 1
WHERE metric_version IS NULL
  AND metric_date >= :start_date
  AND metric_date < :end_date;

-- Contract occurs only after all writers/readers and historical data are verified.
```

DDL/locking/transaction behavior is dialect-specific. The sketch does not make a
large update safe; batch size, concurrency, logging, replication, rollback, and
query plans need real-engine evidence.

### Python lifecycle model

```python
from enum import Enum

class WorkerState(Enum):
    STARTING = "starting"
    READY = "ready"
    DRAINING = "draining"
    STOPPED = "stopped"

def can_admit(state: WorkerState) -> bool:
    return state is WorkerState.READY
```

Real workers need synchronized admission, signal handling, lease fencing,
cancellation, deadline, checkpoint/commit, and forced-termination tests.

## Rollout and rollback protocol

1. Define hypothesis, rollout unit/failure domains, guardrails, observation window, abort threshold, and data-effect boundary.
2. Verify backups/restore and rollback compatibility; snapshot relevant config/state and baseline evidence.
3. Deploy one artifact digest to shadow or canary work with representative data and permissions.
4. Compare output, SLIs, telemetry health, resource use, cost, security, and downstream behavior.
5. Expand by independent failure domain with explicit hold points; avoid simultaneous unrelated changes.
6. Complete data backfill/migration and end-to-end reconciliation before contract/removal.
7. On failure, stop expansion, contain data publication, decide rollback versus forward repair, and communicate.
8. Remove temporary compatibility paths/overrides only after evidence and retain change record.

| Change | Safe rollback condition | Otherwise |
| --- | --- | --- |
| Stateless code | Old artifact accepts current API/config | Roll forward compatible fix |
| Additive schema | Old readers ignore new nullable field | Preserve expand state and roll code back |
| State/checkpoint format | Old code can read/write new state or dual format exists | Migrate state or replay from authority |
| Published metric semantics | Old definition remains valid and active version can switch atomically | Withdraw/annotate and forward repair/backfill |
| Destructive IaC/data | Required object/data and state remain recoverable | Restore under incident/change procedure |

## Lifecycle, consistency, identity, and time

Track source revision, artifact digest, SBOM/provenance, config/schema/migration
versions, IaC state/plan/apply IDs, target environment/region, deployment/canary,
workflow run/attempt, and publication. Desired, IaC state, provider actual state,
runtime controller state, and business-data authority are different sources.
Record UTC change events and correlate delayed batch outcomes with the release that
actually processed them.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Artifact rebuilt per environment | Digest/provenance mismatch | Reject; promote one verified artifact |
| IaC apply partially succeeds | State lock/apply result plus actual inventory | Reconcile exact resources; plan again safely |
| State lost or leaked | Access/integrity/backup controls | Incident; restore state/keys and reconcile actual resources |
| Liveness restarts overloaded fleet | Restart/queue/objective correlation | Disable/fix probe safely; restore capacity/admission |
| Termination kills committed ambiguity | Lease/receipt/reconciliation | Fence, resolve commit, retry/repair idempotently |
| Canary misses rare tenant/skew | Segmented/shadow differential | Stop expansion; add representative segment/evidence |
| Rollback cannot read new checkpoint | Compatibility gate | Use compatible version/state migration or replay |
| Old code rollback leaves bad data | Consumer/quality reconciliation | Withdraw, forward repair, recertify, notify consumers |
| Drift bypasses review | Desired/state/actual inventory diff | Contain, import/revert through governed plan |

## Security, privacy, and governance

Use isolated environments/accounts, workload identity, least privilege, signed/
verified artifacts as policy requires, dependency pinning, secret references,
network/egress controls, admission policy, audit, and break-glass expiry. IaC plans
and state may contain sensitive values even when CLI output redacts them. Production
data in test/canary needs explicit purpose, minimization, access, retention, and deletion.

## Data quality, testing, and evidence

| Evidence | Environment/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Reproducible promotion | Two controlled builds/promotion check | Digests match or variance explained/rejected | Pending |
| IaC plan/policy | Disposable target and drift fixture | Intended bounded actions; unsafe actions reject | Pending |
| Lifecycle | Slow start, overload, dependency loss, termination | Probes/drain do not cascade or duplicate effects | Pending |
| Mixed version | Old/new schema/config/state matrix | Supported coexistence behaves correctly | Pending |
| Rollout/rollback | Shadow/canary fault exercise | Gate stops expansion; safe path completes | Pending |
| Restore/DR | Loss of named target/control component | State/data/capability recover and reconcile | Pending |

## Debugging guide

Start with consumer symptom, change/deployment ID, artifact digest, config/schema/
migration/IaC versions, target/failure domain, canary cohort, plan/apply/state lock,
runtime desired/actual instance state, probe/restart/termination events, workflow
runs, publications, and telemetry lag. Determine whether failure is build, config,
control plane, runtime, dependency, schema/state compatibility, or durable data.
Stop expansion before diagnosis and preserve exact artifacts/state/evidence.

## Common pitfalls

### Pitfall: health means process responds

A process can respond while unable to accept safe work or while publishing wrong
data. Separate startup, readiness, liveness, progress, and consumer data health.

### Pitfall: automatic rollback solves every release

Old code may be incompatible with new state, and published data persists. Gate
rollback on compatibility and use withdrawal/repair/roll-forward when necessary.

### Pitfall: declarative IaC means atomic change

Providers perform multiple remote operations that can partially succeed. Protect
state, inspect the plan, constrain concurrency, and reconcile after apply/failure.

## Performance, capacity, and cost

Budget build/test duration, artifact size/pull/startup, scheduling, probe overhead,
drain time, deployment concurrency, spare capacity during rollout, migration load,
IaC API quotas, duplicate environments, telemetry, and DR. A rolling update needs
enough headroom to remove old capacity without breaching objectives. Clean up
ephemeral resources only through verified scoped lifecycle automation.

## Observability and operations

Track desired versus available/ready capacity, startup and drain distributions,
restart/termination reason, lease/checkpoint age, deployment/version mix, canary
output differential, SLI/budget, resource/cost, state lock/apply failures, drift,
certificate/secret/dependency expiry, backup/restore age, and change failure/recovery.
Routine ownership includes patching, rotation, scaling review, restore drills,
runbook/alert review, dependency upgrades, and toil reduction.

## Compatibility, migration, backfill, and delivery

Use expand/migrate/contract across schema, event, table, config, API, and state.
Test old/new readers/writers, dual paths, late events, replay, and historical
backfill. Cut over atomically where possible; reconcile consumers; preserve rollback
until irreversible contract. Document minimum/maximum compatible versions and
decommission old resources, identities, data, and alerts after verification.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Rolling update | Mixed versions are safe | Slow exposure and version complexity | State/schema cannot coexist |
| Blue/green | Fast switch/rollback and duplicate capacity fit | Cost and data synchronization | Writes cannot be safely dual-routed |
| Shadow data run | Output can compare without consumer effect | Duplicate compute/data/privacy | Side effects cannot be isolated |
| Declarative IaC | Review/repeatability/drift matter | State/provider complexity | Resource lacks reliable provider model |

## Working example

- Infrastructure: Planned container/IaC examples under `infra/operations/` after tool selection
- Python: Planned worker lifecycle/fencing model under `src/big_data_example/operations/`
- SQL: Planned expand/migrate/contract example under `sql/operations/`
- Tests: Planned reproducibility, plan, probe, termination, mixed-version, canary, rollback, drift, and restore cases
- Expected result: Change expands only on healthy evidence; drain preserves ownership; incompatible rollback is rejected
- Scale represented: Documentation and production estimate; no container, IaC, or rollout executed
- Remaining risk: Tool/provider semantics, supply chain, state security, delayed data outcomes, capacity, operator permissions, and DR

## Knowledge check

1. Distinguish desired state, IaC state, runtime status, and business-data authority.
2. Predict the cascade caused by a dependency-based liveness probe during outage.
3. Diagnose why a code rollback failed after checkpoint migration.
4. Design canary units/gates for a daily multi-tenant publication.
5. Estimate rollout headroom and drain grace for current work.
6. Plan expand/migrate/contract with historical backfill and rollback boundaries.
7. Add a termination fault test proving no duplicate active publication.

## Key takeaways

- Build once and promote immutable, attributable artifacts.
- Declarative infrastructure still has state, partial failure, drift, and privileged control.
- Startup, readiness, liveness, drain, and data health are different contracts.
- Canary gates must cover consumer data, resources, cost, security, and telemetry.
- Rollback changes control state; durable data may require withdrawal and forward repair.

## Resources

- [Kubernetes Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) (reviewed 2026-09; version-specific implementation example)
- [Kubernetes liveness, readiness, and startup probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/) (reviewed 2026-09)
- [OpenTofu provisioning workflow](https://opentofu.org/docs/cli/run/) (reviewed 2026-09; one IaC implementation example)
- [OpenTofu state](https://opentofu.org/docs/language/state/) (reviewed 2026-09; state/security behavior is version-sensitive)
- [SLSA specification](https://slsa.dev/spec/) (reviewed 2026-09; adopt a pinned level/version only with task-driven need)

## Related topics

- [Backups, restores, checkpoints, and DR](05-backups-restores-checkpoints-and-disaster-recovery.md)
- [Incident response and data repair](04-incident-response-data-repair-and-organizational-learning.md)
- [Area 12 environment and rollout operations](../12-workflow-orchestration-and-transformation-management/08-environments-secrets-ci-cd-rollout-and-orchestrator-operations.md)

## Completion checklist

- [x] Artifacts, environments, containers, IaC, state, probes, drain, rollout, rollback, migration, DR, security, cost, and operations covered
- [x] Authority, identity, time, mixed versions, durable data effects, and evidence boundaries explicit
- [x] SQL/Python/infrastructure sketches and working example accurately marked Planned
- [ ] Reproducibility, IaC, lifecycle, mixed-version, rollout, rollback, drift, restore, load, and production evidence executed
