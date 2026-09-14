# Schema, Platform, and Pipeline Migration Strategy

> Status: Documentation complete; migration rehearsal evidence planned  
> Level: Senior  
> Applies to: Schemas / Pipelines / Storage / Warehouses / Platforms  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

A data migration is a controlled period in which old and new schemas, logic,
storage, infrastructure, and consumers may coexist. The main design problem is
preserving meaning, authority, recoverability, and consumer trust throughout the
transition. Copy completion alone does not prove a migration succeeded.

This guide covers schema, pipeline, and platform change using expand/migrate/
contract, backfills, validation, cutover, rollback or forward repair, and safe
decommissioning. It does not prescribe online migration for every workload.

## Learning objectives

- Inventory state, contracts, dependencies, and consumers before migration.
- Choose coexistence, dual-read/write, CDC, replay, or downtime deliberately.
- Design idempotent backfills and independent validation by migration wave.
- Define cutover, rollback limits, forward repair, and decommission gates.
- Coordinate owners and communicate semantic or operational change.

## Prerequisites

- [RFCs, ADRs, and design reviews](04-data-platform-rfcs-adrs-and-design-reviews.md).
- Schema evolution, backfill, serving, governance, and delivery from [Areas 04, 06, 07, 11, 14, and 15](../README.md).

## Mental model and terminology

```text
inventory -> expand compatible boundary -> copy/backfill -> validate
                    |                          |             |
             old and new coexist       changes continue   canary
                    +--------------------------+-------------+
                                               v
                                    cut over -> observe -> contract
                                      |             |
                                rollback window   decommission proof
```

| Term | Meaning in this guide |
| --- | --- |
| Migration wave | Bounded tenants, intervals, datasets, or consumers moved together |
| Coexistence | Period when old/new representations or implementations both operate |
| Dual write | One producer attempts two sinks; not inherently atomic or consistent |
| Dual read | Consumer compares/falls back across old and new; semantics must be defined |
| Backfill | Bounded historical computation into a versioned candidate |
| Cutover | Controlled change of authoritative read/write/publication routing |
| Rollback horizon | Last point at which restoring the prior path is safe and complete |
| Forward repair | Correcting the new state when rollback would lose or corrupt accepted work |

This resembles an Android database migration plus staged app rollout. The analogy
stops because data migrations span independently deployed producers/consumers,
massive history, external exports, asynchronous backfills, and writes that may
make application rollback unsafe.

## Requirements, scale assumptions, and invariants

Assume 100 million retained events, 35 hot replay days, 100 tenants, continuing
3 million events/day, and a migration from batch-only publication to an added
provisional projection. Actual sizes, transfer, validation, and cutover durations
are unmeasured.

Invariants:

- Inventory names authoritative state, every derived copy, contract/version, owner, retention, deletion, access, and recovery dependency.
- Migration units have stable identities and half-open intervals; progress is durable and idempotent.
- Historical and concurrent changes are both captured; no unbounded gap exists between copy and cutover.
- Candidate data remains non-authoritative until independent record, aggregate, policy, and consumer validation passes.
- Old/new semantic differences are versioned and intentional; reconciliation never compares unlike definitions silently.
- Rollback preconditions and horizon are explicit; after unsafe writes, forward repair replaces fictional rollback.
- Decommission waits for consumer adoption, retention/hold, recovery, audit, and deletion proof.

## Data flow, ownership, and trust boundaries

| Boundary | Authority/owner | Migration concern |
| --- | --- | --- |
| Source inventory | Source/catalog owners | Hidden tables, streams, files, keys, dependencies |
| Old production path | Existing dataset owner | Remains authoritative until named cutover |
| Change capture | Source/ingestion owner | Gaps, duplicates, ordering, retention, deletes |
| Historical backfill | Migration owner | Versioned logic, bounded attempts, resource isolation |
| New candidate | New dataset owner | Private until validation and policy gates pass |
| Routing/cutover | Product/platform owner | Atomicity, cache, mixed consumers, rollback fence |
| Consumer adoption | Each consumer owner | Semantic acceptance and derived-copy rebuild |
| Decommission | Joint source/platform/governance owners | Holds, backups, contracts, cost, access removal |

## Migration strategy

1. Discover inventory and actual access/lineage; freeze only uncontrolled change, not all delivery.
2. Define source/target grain, keys, `NULL`, types, time, ordering, correction, and certification mapping.
3. Establish wave units, capacity budget, error budget, abort thresholds, and communication.
4. Expand compatible schema/interface and deploy readers before writers where needed.
5. Start change capture or a high-water frontier with gap detection.
6. Backfill immutable candidates in bounded, retryable partitions with manifests.
7. Reconcile using an independent expected population and semantic controls.
8. Shadow/dual read or canary bounded consumers; investigate every material mismatch.
9. Cut over conditionally, observe objectives and consumers, then decide continue/abort.
10. After rollback horizon and adoption proof, contract old interfaces and decommission state safely.

### Migration state model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MigrationWave:
    wave_id: str
    tenant_id: str
    start_utc: str
    end_utc: str
    source_version: str
    target_version: str
    attempt: int

    def validate(self) -> None:
        if self.start_utc >= self.end_utc:
            raise ValueError("wave interval must be half-open and non-empty")
        if self.attempt < 1:
            raise ValueError("attempt must be positive")
```

The real controller needs authenticated ownership, fencing, conditional state
transitions, immutable receipts, and recovery from ambiguous commits.

### SQL reconciliation sketch

```sql
-- Compare one semantic version and wave. FULL OUTER JOIN exposes omissions/additions.
WITH old_wave AS (
  SELECT * FROM expected_old_semantics WHERE wave_id = :wave_id
),
new_wave AS (
  SELECT * FROM new_candidate WHERE wave_id = :wave_id
)
SELECT COALESCE(o.tenant_id, n.tenant_id) AS tenant_id,
       COALESCE(o.event_id, n.event_id) AS event_id,
       CASE
         WHEN o.event_id IS NULL THEN 'unexpected_target'
         WHEN n.event_id IS NULL THEN 'missing_target'
         WHEN o.semantic_digest IS DISTINCT FROM n.semantic_digest THEN 'mismatch'
         ELSE 'match'
       END AS state
FROM old_wave o
FULL OUTER JOIN new_wave n
  ON n.tenant_id = o.tenant_id AND n.event_id = o.event_id
WHERE o.event_id IS NULL OR n.event_id IS NULL
   OR o.semantic_digest IS DISTINCT FROM n.semantic_digest;
```

The CTEs isolate each wave before the full join. Filtering both sides by wave in
the final `WHERE` would accidentally erase unmatched rows. Dialect, digest, and
`NULL` behavior still require verification with independent semantic controls.

## Compatibility patterns

| Change | Safer sequence | Main limit |
| --- | --- | --- |
| Add optional field | Readers tolerate absence -> writers add -> validate adoption | Semantics/default ambiguity |
| Rename/remove field | Add new -> dual-populate -> migrate readers/history -> stop old -> remove | Long-lived consumers |
| Type/meaning change | New version/field/table -> translate explicitly -> cut consumers | Silent coercion is unsafe |
| Storage/engine move | Copy + changes -> reconcile -> shadow/canary -> route -> retain recovery | Transfer and dual-operation cost |
| Pipeline rewrite | Same versioned input -> private output -> differential/fault/load -> cutover | Shared oracle and nondeterminism |

Dual writes can diverge on partial failure. Prefer one durable authority plus
change propagation where possible; otherwise define retry, dedupe, reconciliation,
and which write determines acceptance.

## Lifecycle, consistency, identity, and time

Wave states may be planned, copying, caught-up, validating, ready, cut-over,
observing, complete, aborted, or repairing. State transitions must be retry-safe.
Preserve event time and system/ingestion time separately. Freeze a comparison
frontier or account for changes; otherwise two correct snapshots can disagree.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Hidden consumer uses old schema | Query/access/lineage plus complaint | Pause contract; onboard and retest consumer |
| CDC retention gap | Offset/frontier reconciliation | Re-snapshot affected range and resume safely |
| Dual-write divergence | Per-sink receipt/reconciliation | Repair from authority; never guess winner |
| Backfill overload | Current-work objective/queue | Throttle/isolate wave and resume from manifest |
| Shared transform bug | Independent business control fails | Correct version and rerun candidates |
| Cutover partially applies | Routing/version signals disagree | Fence writes; rollback if safe, else forward repair |
| Rollback resurrects deleted data | Deletion/suppression reconciliation | Reapply tombstones; incident/governance response |
| Source removed too early | Restore/replay fails | Recover retained copy if possible; reopen decommission gate |

## Security, privacy, and governance

Migration creates high-risk copies and elevated access. Minimize fields, isolate
candidates, encrypt transfer and storage, use short-lived identities, validate
tenant/row/column controls, preserve lineage/audit, apply retention/holds/deletion,
and destroy temporary copies with receipts. Never use unmasked production samples casually.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Inventory | Catalog, storage, query, lineage, owner reconciliation | Known state and consumers agree | Pending |
| Compatibility | Old/new producer-reader matrix | Supported mixed versions succeed; forbidden fail visibly | Pending |
| Backfill state | Duplicate/partial/ambiguous attempts | Wave converges without double effects | Pending |
| Differential | Independent record/aggregate controls | Missing, extra, mismatch, deletion visible | Pending |
| Load/isolation | Current traffic plus backfill/dual run | Objectives protected and drain measured | Pending |
| Cutover/restore | Staging rehearsal with injected failures | Abort/rollback/forward repair converge | Pending |
| Consumer/decommission | Adoption and recovery proof | No approved consumer or obligation depends on old path | Pending |

## Debugging guide

Start with wave ID, source/target versions, authoritative frontier, copy/change
offsets, record counts/digests, rejected records, deletion/hold state, routing,
consumer version, and resource contention. Distinguish missing copy, missed
concurrent change, semantic mismatch, visibility/cache delay, and comparison-query defect.

## Common pitfalls

### Pitfall: dual write means safety

Two successful-looking calls can acknowledge different sets. Define acceptance,
partial-failure repair, stable identity, and continuous reconciliation.

### Pitfall: counts match, migration is correct

Wrong keys, values, tenants, versions, or deleted subjects can preserve totals.
Use record, aggregate, distribution, policy, and consumer controls.

### Pitfall: rollback is always possible

New-only writes or incompatible meaning may cross the rollback horizon. State
the fence and rehearse forward repair before cutover.

## Performance, capacity, and cost

Model source scan/impact, network transfer, serialization, target writes, indexes,
temporary copies, CDC/change lag, validation scans, current workload, retries,
backfill drain, dual-operation duration, observability, support, and decommission
savings. Wave size trades overhead against blast radius and rollback time.

## Observability and operations

Track inventory coverage, wave state/age, source and target frontiers, copy rate,
change lag, mismatch counts by class, rejection, objective impact, resource/cost,
consumer adoption, rollback horizon, and old-path traffic. Alert only with a safe
pause/repair action and owner.

## Compatibility, migration, backfill, and delivery

This entire guide is the compatibility contract. Deliver expand before migrate,
and migrate before contract. Use canaries and conditional routing. Record exact
artifact/config/schema versions and post-cutover reconciliation. Decommission is
a separate reviewed change.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk |
| --- | --- | --- |
| Planned downtime | Consumers can tolerate bounded stop and simpler consistency | Availability/business coordination |
| CDC plus backfill | Writes continue and source log is complete | Ordering, retention, connector operations |
| Dual read/shadow | Consumer comparison is safe | Load, ambiguity, privacy, implementation complexity |
| Small waves | Uncertainty/blast radius high | More coordination and fixed overhead |
| Forward repair | New writes make rollback unsafe | Requires trusted new authority and repair tooling |

## Working example

- Inventory: Planned source/copy/consumer/dependency register
- Python: Planned migration-wave state and manifest validation
- SQL: Planned isolated-wave record/aggregate/policy reconciliation
- Tests: Planned compatibility, CDC gap, partial attempt, deletion, cutover, restore, and load cases
- Expected result: Every wave converges, consumers accept, and old path is removed only after proof
- Remaining risk: Hidden consumers, source impact, shared bugs, cutover coordination, rollback horizon, and production duration

## Knowledge check

1. Explain why copy completion is not migration completion.
2. Find the outer-join bug risk in the reconciliation sketch and repair it.
3. Diagnose matching counts with missing and extra target records.
4. Design migration waves and abort criteria for 100 tenants.
5. Estimate backfill drain while current traffic continues.
6. Identify the rollback horizon for a new-only schema write.
7. Add deletion-resurrection evidence to the decommission gate.

## Key takeaways

- A migration is an operating state with explicit coexistence semantics.
- Inventory, stable wave identity, change capture, and independent validation prevent silent gaps.
- Expand/migrate/contract protects mixed versions; it does not remove semantic review.
- Rollback is conditional and expires; forward repair must be designed.
- Decommission requires consumer, recovery, governance, and traffic evidence.

## Resources

- [PostgreSQL logical replication restrictions](https://www.postgresql.org/docs/current/logical-replication-restrictions.html) (reviewed 2026-09; engine-specific)
- [Apache Kafka Connect architecture](https://kafka.apache.org/documentation/#connect) (reviewed 2026-09; product-specific)
- [Microsoft Cloud Adoption Framework: migrate](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/migrate/) (reviewed 2026-09; provider-specific)

## Related topics

- [Data products and ownership](06-data-products-platform-teams-and-ownership-models.md)
- [Area 07 backfills](../07-batch-processing-and-etl-elt/06-backfills-reprocessing-and-historical-correction.md)
- [Area 15 delivery](../15-reliability-observability-performance-cost-and-operations/08-infrastructure-delivery-rollout-rollback-and-operations.md)

## Completion checklist

- [x] Inventory, coexistence, schema evolution, backfill, validation, cutover, rollback, repair, and decommissioning covered
- [x] Grain, identity, time, security, failure, capacity, ownership, and consumer behavior explicit
- [x] SQL/Python sketches and working example accurately marked Planned
- [ ] Inventory, compatibility, backfill, differential, load, cutover, restore, consumer, and production evidence executed
