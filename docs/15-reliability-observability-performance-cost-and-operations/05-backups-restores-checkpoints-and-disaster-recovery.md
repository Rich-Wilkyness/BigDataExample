# Backups, Restores, Checkpoints, and Disaster Recovery

> Status: Documentation complete; executable recovery evidence planned  
> Level: Intermediate to Senior  
> Applies to: Storage / Batch / Streaming / Metadata / Data platforms  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

A backup is a recoverable copy with known scope and dependencies. A restore is
the act of reconstructing usable state. A checkpoint records progress or state
for resumption and is not automatically an independent backup. Disaster recovery
(DR) restores an agreed business capability after loss of a failure domain.

This guide connects RPO/RTO, state inventory, consistency, metadata, keys,
checkpoints, restore validation, regional failure, dependency ordering, and data
reconciliation. It does not claim a backup exists merely because storage is replicated.

## Learning objectives

- Define recovery scope, RPO, RTO, retention, and evidence per capability.
- Inventory authoritative data, metadata, configuration, identity, keys, and derived state.
- Distinguish replication, backup, checkpoint, replay source, and archive.
- Plan ordered restoration and prove semantic/consumer recovery.
- Test deletion, legal hold, corruption, region loss, and compromised-control scenarios.

## Prerequisites

- [Reliability requirements](01-data-system-reliability-requirements-and-failure-domains.md) and [incident/data repair](04-incident-response-data-repair-and-organizational-learning.md).
- [Area 04 storage](../04-data-storage-files-and-serialization/README.md), [Area 10 streaming state](../10-messaging-streaming-and-change-data-capture/README.md), and [Area 14 lifecycle](../14-governance-security-privacy-and-data-lifecycle/06-retention-deletion-legal-holds-and-data-subject-workflows.md).
- Planned isolated restore target and authorized destructive-failure drill.

## Mental model and terminology

```text
capability -> state/dependency inventory -> RPO/RTO/threats
                     |
      backup / log / checkpoint / code+config / key escrow
                     |
              protected copy + catalog
                     |
declare disaster -> restore dependencies -> restore authority -> replay/rebuild
                     |
        validate integrity + semantics + policy + consumers -> resume
```

| Term | Meaning in this guide |
| --- | --- |
| RPO | Maximum tolerable interval of data/state loss for a named capability |
| RTO | Target elapsed time to restore that named capability to an agreed level |
| Backup set | Data plus metadata/dependencies required for a specific restore claim |
| Checkpoint | Processing progress/state used to resume; may share corruption/failure domain |
| Point-in-time recovery | Restore to an eligible state at or before a chosen time using base plus changes |
| Failover/failback | Move service to recovery environment and later return through controlled migration |
| Restore verification | Evidence that restored state is readable, semantically correct, governed, and usable |

Room/SQLite backup testing is a helpful analogy: a file copy is insufficient if
schema, write-ahead log, app version, or encryption key is missing. The analogy
stops when a data platform has petabytes, independently changing catalogs,
distributed checkpoints, cross-region locality, and a replay backlog competing
with live data.

## Requirements, scale assumptions, and invariants

For every capability document state components, authority, consistency boundary,
change rate, RPO/RTO, retention, location/failure domain, encryption/key recovery,
restore order, capacity, validation, owners, and consumer degraded mode. Assume
3 GiB/day raw growth, 100 million governed records, 35 replay days, 1,000 dataset
catalog records, and a provisional 4-hour read-recovery target. These are untested.

Invariants:

- Every acknowledged authoritative record is covered by a named durability/replay claim or acknowledgement explicitly reports uncertainty.
- Backup inventory binds data, schema/catalog, code/config, policy, identity, key versions, checkpoints/log positions, and creation outcome.
- At least one required recovery path is isolated from the failure/corruption/credential domain it claims to survive.
- Restore credentials and keys are available through tested, least-privileged, audited recovery paths.
- Restoring old data cannot resurrect records whose deletion/retention state is newer; suppression/tombstones are replayed before serving.
- A restored candidate is isolated until integrity, accounting, semantic quality, access policy, and consumer checks pass.
- RPO/RTO are measured at the consumer capability boundary, not at file-copy completion.

## Data flow, ownership, and trust boundaries

| Boundary | Authority/owner | Recovery failure behavior |
| --- | --- | --- |
| Source/log | Source or ingestion owner | Preserve sequence/frontier and acknowledgement evidence |
| Backup writer/catalog | Storage/recovery owner | Failed/partial set is ineligible and alerted |
| Backup storage/account/key | Independent security/storage owners | Deny ordinary writers; detect modification/deletion |
| Restore environment | Recovery commander/platform owner | Isolated network/identity until validation |
| Dataset/catalog activation | Dataset owner | Conditional cutover after receipt |
| Downstream consumer | Consumer owner | Explicit stale/unavailable state until reconciliation |

## Recovery inventory and plan

| State | Preferred recovery source | Validation |
| --- | --- | --- |
| Raw accepted events | Independent immutable/versioned copy or source replay | Event identity, count/accounting, checksum, decrypt/read |
| Warehouse/lakehouse data | Snapshot/log plus catalog/schema metadata | Table integrity, version, row/aggregate/consumer reconciliation |
| Streaming state | Compatible checkpoint plus retained input log | Offset/state consistency and deterministic output comparison |
| Scheduler metadata | DB backup plus workflow definitions/artifacts | Run/interval ownership and no unsafe duplicate scheduling |
| Catalog/lineage/policy | Versioned export/store plus code/config | Ownership, access, policy and dataset mapping checks |
| Secrets/keys/identity | Dedicated recovery process and root dependencies | Authorized retrieval, rotation/revocation, negative access |
| Derived marts/caches | Prefer rebuild from certified authority | Publication version, freshness, consumer behavior |

Restore ordering follows dependencies, not convenience: secure recovery identity
and networking; keys/secrets; metadata/control planes; authoritative data; compute;
derived publications; serving; telemetry; consumers. Some can proceed in parallel
only when their consistency and dependency boundaries permit it.

### SQL model

```sql
-- Compare immutable backup inventory with restored objects. Grain is one object
-- version in one backup set; metadata NULL is a failed verification.
SELECT b.backup_set_id, b.object_key,
       CASE
         WHEN r.object_key IS NULL THEN 'missing'
         WHEN r.byte_count IS DISTINCT FROM b.byte_count THEN 'size_mismatch'
         WHEN r.content_digest IS DISTINCT FROM b.content_digest THEN 'digest_mismatch'
         ELSE 'present'
       END AS restore_state
FROM backup_manifest b
LEFT JOIN restored_object_inventory r
  ON r.backup_set_id = b.backup_set_id
 AND r.object_key = b.object_key
WHERE b.backup_set_id = :backup_set_id;
```

This PostgreSQL-style example uses `IS DISTINCT FROM` so missing metadata fails
verification. It proves only inventory attributes. It does not prove files decrypt, formats
parse, tables are semantically correct, policies apply, or applications can serve.

### Python model

```python
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

@dataclass(frozen=True)
class RecoveryPoint:
    last_durable_at: datetime
    incident_at: datetime

    def loss_window(self) -> timedelta:
        if self.last_durable_at.tzinfo != timezone.utc or self.incident_at.tzinfo != timezone.utc:
            raise ValueError("recovery timestamps must be UTC")
        return self.incident_at - self.last_durable_at
```

The calculation checks an observed loss interval against an RPO; it does not
validate which records exist or whether timestamps themselves are authoritative.

## Checkpoints and consistency

A checkpoint must bind job/operator/version, input partitions and positions,
state schema/serializer, timers/watermarks, output commit state, and integrity.
Restoring an offset without state can lose or duplicate results; restoring state
without compatible code can fail or corrupt semantics. Keep input retention long
enough to recover or explicitly accept the gap.

Crash-consistent storage may reflect a real instant but not an application-consistent
multi-system transaction. Coordinate snapshots, quiesce/fence writes, or record
independent frontiers and reconcile after restore. Never describe asynchronous
copies as one atomic backup without evidence.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Backup job green but objects absent | Manifest versus independent inventory/read test | Mark set ineligible; rebuild from prior/source |
| Replication copies corruption | Integrity/version/anomaly checks | Restore older isolated point; replay verified changes |
| Checkpoint incompatible with code | Compatibility restore test | Run compatible artifact or approved state migration/replay |
| Keys unavailable | Recovery-key drill | Restore access under dual control; rotate after event |
| Region/control account lost | Out-of-band dependency test | Establish recovery control plane then restore ordered state |
| Restore resurrects deleted subject | Suppression/receipt reconciliation | Reapply deletion before serving; incident and reverify copies |
| Recovery capacity too small | Timed restore/backlog test | Prioritize capability, add capacity, revise RTO transparently |
| Failback overwrites newer state | Version/frontier comparison and fencing | Merge/reconcile or one-way rebuild; conditional cutover |

## Security, privacy, and governance

Backups widen access, retention, and location. Encrypt in transit/at rest, separate
write/delete administration, protect and rehearse key recovery, apply immutable/
versioned controls appropriate to threats, inventory access, audit restores, and
expire test copies. A recovery environment must enforce current classification,
tenant, purpose, retention, holds, and deletion rules before consumer access.
Restored production data must not become a convenient nonproduction fixture.

## Data quality, testing, and evidence

| Evidence | Environment/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Manifest/unit | Fixed full/partial/corrupt inventories | Ineligible sets and gaps are explicit | Pending |
| File/object restore | Isolated test destination | Read/decrypt/digest/format checks pass | Pending |
| Application restore | Real metadata/data services | Queries, writes, policies, and consumers function | Pending |
| Checkpoint fault | Kill/restart with retained input | Output reconciles without unexplained loss/duplicate | Pending |
| Deletion/hold | Restore predating lifecycle action | Current suppression/hold semantics prevail | Pending |
| Regional DR | Authorized game day | Dependency order, RPO/RTO, communications, failback measured | Pending |

## Debugging guide

Identify capability, incident time, last known durable frontier, selected backup
set, manifest, storage/key/account/region domains, schema/code/config versions,
checkpoint positions, deletion/hold frontier, and restore target. Verify source
readability before mass restore. Record phase timings and gaps. Do not cut over
until inventory, integrity, semantic, access, freshness, downstream, and consumer
checks pass; preserve the failed environment for investigation where safe.

## Common pitfalls

### Pitfall: replication is backup

Replication improves availability but often propagates deletion/corruption and
shares control. A recovery copy needs a tested threat, isolation, retention, and restore path.

### Pitfall: backup success is recoverability

Writing bytes proves neither completeness nor usability. Restore regularly into
an isolated environment and validate the whole named capability.

### Pitfall: checkpoint is authoritative data

It may be partial, implementation-specific, incompatible, and co-located. Preserve
the source/replay contract and test state/output consistency.

## Performance, capacity, and cost

Model logical/physical bytes, change rate, compression/deduplication, full versus
incremental chains, copy bandwidth, restore parallelism, metadata/key latency,
replay amplification, egress, retention tiers, test environments, and operator
time. Measure effective restore and rebuild throughput under contention; calculate
whether backlog drains before retention expires and within RTO.

## Observability and operations

Track backup eligibility, last successful set/frontier, age, bytes/objects,
read/integrity samples, restore-test age/outcome, key-recovery test, checkpoint age,
input retention margin, predicted/observed RPO/RTO, restore phase timing, deletion
reconciliation, and recovery-capacity headroom. Page on immediate loss of the only
required recovery path, not every transient backup retry.

## Compatibility, migration, and delivery

Version manifest, format, schema, serializer, engine, code, config, catalog, policy,
and key metadata. Test oldest retained recovery point against supported restore
artifacts. During migrations, ensure at least one old/new compatible recovery path,
then retire only after restore evidence. A rollback across irreversible data or
state migration may require forward repair rather than old code.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Snapshot plus change log | Large state and bounded RPO | Chain/dependency complexity | Full copy fits window/cost |
| Rebuild derived data | Authority and code are retained | Compute time and semantic drift | RTO cannot tolerate rebuild |
| Hot standby | Very short service RTO | Cost and shared-corruption risk | Restore-based RTO is acceptable |
| Cross-region copy | Region loss in threat model | Egress, locality, keys, consistency | Regulation or harm disallows it |

## Working example

- Models: Planned recovery point and backup manifest validator under `src/big_data_example/operations/`
- SQL: Planned manifest-to-restored inventory reconciliation under `sql/operations/`
- Tests: Planned partial/corrupt/incompatible/deletion/checkpoint cases
- Operations: Planned isolated restore and regional DR runbook
- Expected result: Only eligible sets restore; current policy/deletion survives; consumer capability meets measured result
- Scale represented: Local manifest fixture and production estimate; no restore or DR run
- Remaining risk: Real storage consistency, keys, bandwidth, control-plane loss, recovery capacity, and failback

## Knowledge check

1. Distinguish replication, backup, archive, replay log, and checkpoint.
2. Predict what the SQL reports when metadata exists but restored content is corrupt.
3. Diagnose why a restored checkpoint duplicates output.
4. Design dependency order for regional recovery.
5. Estimate copy/replay time and compare it with RTO and retention.
6. Plan a checkpoint serializer migration with recoverable rollback.
7. Add a deletion-resurrection restore test.

## Key takeaways

- Recovery objectives name a consumer capability and include dependencies.
- A backup claim is proven through restore, not successful copy alone.
- Checkpoints resume processing but do not automatically protect authoritative data.
- Current security and lifecycle state must survive restoration.
- RPO/RTO end at verified consumer capability, not copied bytes.

## Resources

- [NIST SP 800-34 Rev. 1 contingency planning guide](https://csrc.nist.gov/pubs/sp/800/34/r1/final) (reviewed 2026-09; organizational tailoring required)
- [NIST SP 800-184 cybersecurity event recovery](https://csrc.nist.gov/pubs/sp/800/184/final) (reviewed 2026-09)
- [PostgreSQL continuous archiving and point-in-time recovery](https://www.postgresql.org/docs/current/continuous-archiving.html) (reviewed 2026-09; product-specific example)

## Related topics

- [Incident response and data repair](04-incident-response-data-repair-and-organizational-learning.md)
- [Infrastructure delivery and operations](08-infrastructure-delivery-rollout-rollback-and-operations.md)
- [Area 14 retention and deletion](../14-governance-security-privacy-and-data-lifecycle/06-retention-deletion-legal-holds-and-data-subject-workflows.md)

## Completion checklist

- [x] RPO/RTO, inventories, consistency, checkpoints, keys, deletion, regional DR, validation, cost, and failback covered
- [x] Ownership, identity, time, security, compatibility, and evidence boundaries explicit
- [x] SQL/Python models and working example accurately marked Planned
- [ ] Manifest, restore, checkpoint, deletion, key, regional, load, and production evidence executed
