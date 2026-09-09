# Environments, Secrets, CI/CD, Rollout, and Orchestrator Operations

> Status: Documentation complete; executable delivery and operations evidence planned  
> Level: Intermediate to Senior  
> Applies to: Airflow / SQL transformation / CI/CD / Security / Platform operations  
> Data scale: Local validation; production deployment estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Workflow delivery moves code, configuration, and metadata contracts across
environments while data stays environment-owned. A safe release is reproducible,
least-privileged, compatible with running work, observable, and reversible within
declared limits. Operating the orchestrator also requires metadata backup/restore,
component health, capacity, log retention, drain, and disaster-recovery practice.

## Learning objectives

- Separate immutable artifacts from environment configuration and secrets.
- Design CI evidence for graphs, SQL, contracts, security, and compatibility.
- Promote one reviewed artifact without copying production data or credentials.
- Roll out DAG/model/platform changes with canary, drain, reconciliation, and rollback.
- Operate and restore the control plane without confusing it with data recovery.

## Prerequisites

- All earlier guides in this area, especially Airflow architecture and artifacts.
- Area 02 packaging/reproducibility and Areas 11/14/15 storage, security, and operations concepts.
- No production environment is required for this documentation pass.

## Mental model and terminology

```text
source commit -> CI -> signed immutable artifact + evidence
                              |
                  promote same bytes/config schema
                    /         |          \
                  dev       staging      production
                    \         |          /
              environment-owned config, identity, data, secrets
```

| Term | Meaning in this guide |
| --- | --- |
| Artifact | Immutable deployable code/dependencies plus provenance |
| Promotion | Authorizing the same artifact for another environment |
| Configuration | Non-secret environment-specific values validated against a schema |
| Secret reference | Identifier resolved at runtime; secret value is not in source/artifact |
| Canary | Bounded real execution used to validate a release before wider activation |
| Drain | Stop admitting new work while allowing/cancelling in-flight work by policy |
| Rollback | Restore prior compatible code/config/publication; not automatically undo data effects |

Unlike installing an Android build, deploying a DAG can change scheduling of
historical intervals and coexist with older running tasks. Rolling back files does
not revert warehouse tables already published.

## Requirements, scale assumptions, and invariants

- Build once; record source revision, dependency lock, runtime, provider/adapter,
  artifact digest, schema migrations, and evidence.
- Environment identifiers are explicit in dataset names, connections, policies,
  artifacts, logs, and destructive-operation guards.
- Secrets never enter Git, images, CI logs, rendered templates, or test artifacts.
- CI uses synthetic/deidentified fixtures and no production write credentials.
- Releases are compatible with queued/running old tasks or use a declared drain.
- Database and dataset migrations use expand/migrate/contract and reconciliation.
- Control-plane RPO/RTO and data-plane recovery are specified and rehearsed separately.
- Estimates: 100 DAGs, 10,000 task instances/day, 99.9% provisional control-plane
  availability; no load, availability, cost, or restore measurement exists.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Developer/SCM | Reviewed source and signed commits/tags | Workflow owners | Block unreviewed changes | Human/supply-chain boundary |
| CI runner | Pinned toolchain, unprivileged fixtures | Delivery platform | Fail closed; redact output | Ephemeral untrusted compute |
| Artifact registry | Digest, SBOM/provenance, evidence | Release/platform owner | Reject mutation/unverified artifact | Trusted distribution |
| Environment config/secret store | Validated keys and runtime references | Platform/security owners | Missing secret fails task without disclosure | High trust |
| Orchestrator deployment | Artifact plus configuration | Airflow platform owner | Canary/pause/drain/rollback | Privileged control plane |
| Data systems | Environment-qualified targets/policies | Dataset owners | Atomic candidate/cutover | Separate authoritative plane |

## Environment and secret design

Configuration chooses connection references, dataset namespaces, schedules,
feature gates, pool names, and limits. Code defines behavior. Secrets are resolved
only by the component that needs them, rotated independently, and never used as
general configuration.

```python
@dataclass(frozen=True)
class EnvironmentConfig:
    name: Literal["dev", "staging", "prod"]
    dataset_namespace: str
    connection_ref: str
    publish_enabled: bool
    max_active_runs: int

def validate_target(config: EnvironmentConfig) -> None:
    expected_prefix = f"{config.name}."
    if not config.dataset_namespace.startswith(expected_prefix):
        raise ValueError("environment/namespace mismatch")
```

This guard complements IAM and warehouse policies; application checks alone are
not a security boundary.

## CI evidence ladder

1. Format/lint, dependency and secret scanning, license/provenance policy.
2. Python unit/property tests and SQL static/compile checks.
3. DAG import, stable-ID, cycle, task-policy, and schedule/calendar tests.
4. Transformation graph, schema, data tests, docs, and compiled SQL review.
5. Real adapter/metadata database integration with isolated schema.
6. Retry, crash, timeout, cancellation, partial publication, and restore tests.
7. Production-shaped plan, load, skew, concurrency, and cost tests.
8. Artifact signing, manifest/evidence retention, staged canary, and post-deploy reconciliation.

Fast CI may select a changed subgraph only when the comparison artifact is trusted
and deferral cannot point development work at a write-capable production target.
Run periodic full suites to detect selection gaps.

## Rollout state machine

```text
built -> verified -> staged -> canary -> active -> observed -> complete
                       |         |         |
                       +------ rollback / roll-forward / contain ------+
```

Before activation, decide how old queued/running tasks access code and templates.
Keep task IDs and serialized interfaces compatible or drain. Canary one interval
and low-risk consumer, compare output and operational metrics, then expand.
Rollback restores the prior artifact but data repair may require a new fenced
publication or compensating operation.

### Change decision table

| Change | Safe delivery shape | Special evidence |
| --- | --- | --- |
| Add optional field | Expand readers, add producer, backfill, contract later | Mixed-schema consumer tests |
| Change task ID/topology | Add new IDs/path, migrate history deliberately | Run-state and alert/link continuity |
| Change schedule/time zone | Enumerate old/new intervals and cutover instant | Gap/overlap calendar test |
| Metadata DB migration | Back up, stage exact migration, maintenance/live-upgrade plan | Restore and mixed-version support |
| Provider/adapter upgrade | Pin full matrix and canary real operations | Serialization, SQL, cancel/retry tests |
| Metric semantic change | New version, dual-build, consumer approval | Reconciliation and rollback publication |

## Operations and observability

Monitor scheduler/DAG-processor/triggerer/API/worker heartbeats; metadata DB
latency, locks, storage, and connections; parse errors/duration; runnable, queued,
deferred, retrying, and zombie work; task-start latency; freshness; failures;
remote log delivery; artifact version; and secret-resolution failures.

Runbooks cover pause versus drain, ambiguous task state, stuck queues, retry storm,
metadata saturation, expired secret, broken DAG release, bad transformation,
backfill overload, component loss, backup restore, and regional disaster. Define
who can declare incidents, override readiness, clear tasks, rotate credentials,
or certify repaired data.

## Shutdown, backup, restore, and disaster recovery

Graceful shutdown stops admission, drains or cancels attempts within a deadline,
fences late commits, persists state, and verifies no orphaned remote work. Abrupt
loss is expected and recovered through idempotent tasks and metadata reconciliation.

Back up orchestrator metadata, encryption keys/configuration required to interpret
it, artifact registry, environment configuration, connection definitions or
recoverable references, audit records, and infrastructure declarations according
to classification. A metadata restore may recreate run history yet leave external
datasets ahead or behind; reconcile publication ledgers and current task effects
before scheduling resumes.

## Failure model and recovery

| Failure | Detection/containment | Recovery evidence |
| --- | --- | --- |
| Wrong environment target | Guard/IAM denial and audit | No cross-environment write; fix config |
| Secret leaked to logs/artifact | Scanner/incident alert | Revoke/rotate, restrict/delete per policy, audit |
| DAG import fails after release | Import health and missing/stale DAG | Restore prior bundle, fix and canary |
| Old/new workers incompatible | Serialization/runtime errors | Drain or restore compatible matrix; reconcile effects |
| Metadata migration fails | Migration/health checks | Restore tested backup or roll forward per supported path |
| Canary data incorrect | Reconciliation/consumer test | Stop activation; retain prior publication; repair |
| Rollback code cannot undo data | Version comparison | Publish corrected replacement and notify consumers |
| Region/control plane lost | Health/DR declaration | Restore components/metadata, fence old region, reconcile data |

## Security, privacy, and governance

Use least privilege, short-lived workload identity, network segmentation, encrypted
transport/storage, artifact verification, dependency scanning, protected branches,
separation of deploy/publish/admin duties, and audited break-glass access. Mask
samples and logs; sanitize error records; enforce retention and deletion in
staging, test, backup, metadata, and documentation—not only production tables.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Reproducible build | Clean runner / pinned inputs | Build twice and compare declared artifact metadata | Equivalent artifact/provenance | Pending |
| Environment isolation | Dev/staging fixtures | Attempt cross-environment target/access | Denied and audited | Pending |
| CI graph/data | Synthetic project / pinned runtimes | Run evidence ladder through integration | Required gates block defects | Pending |
| Rollout/rollback | Staging deployment | Canary bad/good release and reconcile | Prior or corrected complete data visible | Pending |
| Backup/restore/DR | Test control plane | Restore metadata and reconcile external data | Measured RPO/RTO and safe resume | Pending |
| Load/soak | Production-shaped deployment | Run normal plus backfill/component restart | SLO/capacity/cost budgets hold | Pending |

## Debugging guide

1. Identify environment, artifact digest, config version, DAG/model version, interval, and publication.
2. Compare deployed artifact and dependency matrix with CI evidence and running-worker versions.
3. Inspect component health, metadata DB, queues, secret provider, logs, remote queries, and data ledger.
4. Contain by pausing activation/publication or draining admission; rotate exposed credentials immediately.
5. Roll back code only if compatible; otherwise roll forward and repair data under a new publication.
6. Reconcile control and data planes, measure consumer recovery, and preserve incident evidence.

## Common pitfalls

### Pitfall: rebuild separately in every environment

Dependency resolution can drift. Promote the same verified artifact and supply
validated environment-owned configuration.

### Pitfall: production-shaped CI means production data

Use generated or deidentified fixtures with representative sizes/distributions.
Production secrets and raw records do not belong in CI.

### Pitfall: rollback deployment equals rollback data

Published effects persist. Plan table versions, fences, compensation, consumer
cutover, and reconciliation independently from code rollback.

## Performance, capacity, and cost

Budget CI duration/parallelism, artifact size/startup, DAG parse time, metadata DB
connections/storage, worker slots, log/metric volume, secret-provider requests,
backup size, restore time, current/backfill capacity, and standby cost. Measure
tail latency during rolling restart and recovery, not only steady state.

## Compatibility, migration, backfill, and delivery

The delivery unit records Airflow, providers, Python, executor image, metadata DB,
dbt runtime, adapter/packages, warehouse, and configuration-schema compatibility.
Use expand/migrate/contract across graph, metadata, schema, and consumers. Preserve
old artifacts and readable data versions for the rollback horizon; test restore
before a release makes the old runtime unable to interpret current state.

## Working example

- CI configuration: Planned under repository delivery configuration
- Infrastructure: Planned pinned local/staging Airflow and transformation services under `infra/`
- Source/tests: Planned environment validator, import, integration, fault, and restore suites
- Try it: Planned build-inspect, canary, rollback, backup, and restore procedures
- Expected result: Same artifact promoted; bad release contained; safe reconciled recovery
- Evidence: Planned provenance, SBOM, test reports, deployment events, RPO/RTO, and cost
- Scale represented: Documentation and estimates only
- Remaining risk: Every delivery, security, platform, load, and DR claim is unverified

## Knowledge check

1. Distinguish artifact, configuration, secret, promotion, and publication.
2. Predict the risk of changing a task ID while old runs are queued.
3. Diagnose a staging-only pass caused by a different adapter version.
4. Design a canary whose task succeeds but data reconciliation fails.
5. Estimate recovery capacity and metadata growth for the stated workload.
6. Plan a metadata DB/runtime upgrade with drain, backup, restore, and rollback constraints.
7. Implement the environment-target guard and a negative access test.

## Key takeaways

- Promote immutable evidence-backed artifacts; environments own config, identity, data, and secrets.
- CI spans graph, data, compatibility, failure, security, and delivery—not syntax alone.
- Mixed-version tasks and durable data effects make rollout stateful.
- Code rollback and data recovery are separate operations.
- Control-plane restore finishes only after reconciliation with authoritative data systems.

## Resources

- [Apache Airflow: administration and deployment](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/index.html) (reviewed 2026-09)
- [Apache Airflow: production deployment](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html) (reviewed 2026-09)
- [Apache Airflow: secrets backends](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html) (reviewed 2026-09)
- [dbt: continuous integration](https://docs.getdbt.com/docs/deploy/continuous-integration) (reviewed 2026-09)
- [SLSA specification](https://slsa.dev/spec/) (reviewed 2026-09)

## Related topics

- [Airflow architecture and lifecycle](03-airflow-architecture-dags-and-task-lifecycle.md)
- [Metadata, lineage, and artifacts](07-metadata-lineage-artifacts-and-data-aware-scheduling.md)
- [Area 02 environments and packaging](../02-python-for-data-engineering/06-environments-packaging-dependencies-and-reproducibility.md)

## Completion checklist

- [x] Environment, artifact, configuration, secret, CI, rollout, and operations contracts defined
- [x] Isolation guard, evidence ladder, rollout state, and change decision table included
- [x] Mixed-version, security, shutdown, backup, restore, DR, and data repair addressed
- [x] Capacity, compatibility, migration, observability, and diagnosis covered
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Reproducible build, isolation, integration, rollout, restore, load, and DR evidence executed
