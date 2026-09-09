# Backfills, Reprocessing, and Historical Correction

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic data engineering / Batch / SQL / Storage  
> Data scale: Local fixture; one-year production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Reprocessing runs retained input again. A backfill computes a deliberately bounded
historical scope, often for new logic or missing data. A correction publishes new
knowledge about previously published history. Safe historical work pins inputs,
code, configuration, and dependencies; isolates output; respects current
production capacity; validates differences; and cuts consumers over atomically.

Reusing today's code against mutable dependencies is not reproducibility, and
overwriting history in place is not a controlled correction.

## Learning objectives

- Define a backfill by business scope, input boundary, and semantic version.
- Make historical execution deterministic enough to explain intended differences.
- Isolate backfill compute, staging, checkpoints, and publication from current runs.
- Validate old/new results and reconcile complete bounded ranges.
- Plan cutover, rollback, consumer communication, retention, and deletion.

## Prerequisites

- [Full, incremental, and change-based processing](04-full-incremental-and-change-based-processing.md)
- [Checkpoints, idempotency, and atomic publication](05-checkpoints-idempotency-and-atomic-publication.md)
- Area 05 temporal history and model evolution

## Mental model and terminology

A backfill resembles a database migration that recomputes durable derived state,
but it may span months of partitions and many downstream consumers. The Android
schema-migration analogy helps with versioning and rollback; it stops because
historical facts may already be exported, cached, or used in irreversible
decisions, so a data rollback cannot retract every consequence.

| Term | Meaning in this guide |
| --- | --- |
| Replay | Read retained inputs again, usually under the same logical contract |
| Reprocessing | Re-execute one or more pipeline stages from a recoverable boundary |
| Backfill | Bounded historical computation to add, replace, or repair output |
| Correction | New version that intentionally changes previously certified results |
| Backfill shard | Independently retryable subrange with no hidden overlap or gap |
| Semantic diff | Expected/unexpected result difference attributable to contract change |
| Cutover | Controlled change selecting the new historical dataset version for consumers |

## Requirements, assumptions, and invariants

The reference rebuild covers one year at 3M events/day, potentially 1.095B input
events before duplicates/rejections. Normal daily work must still meet 02:00 UTC.
Backfill input is retained accepted raw plus effective-dated product history.
Available parallelism, scan cost, downstream load, and correction notification
limits are estimates to measure before admission.

Invariants:

- Scope uses half-open business/input ranges with explicit time zone and no gap/overlap.
- Every shard pins input manifests/positions, code artifact, config, schema, reference data, and semantic version.
- Backfill checkpoints and candidate paths cannot advance or overwrite current-production state.
- Repeating a successful shard produces equivalent output for the pinned contract.
- Expected semantic changes are quantified; unexplained differences block cutover.
- Cutover selects a complete coherent version, with a retained rollback or forward-repair plan.
- Consumers and downstream derivatives receive the correction contract and lineage.

## Backfill specification

```yaml
# Contract sketch, not a selected repository format.
backfill_id: product-event-v2-2025
dataset: curated_product_event
scope: "[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)"
input_manifests: [accepted-events-snapshot-2026-09-01]
product_dimension_version: product-history-2026-09-01
code_version: immutable-artifact-digest
config_version: canonical-config-digest
semantic_version: "2"
shard_unit: utc_day
expected_change: "exclude synthetic QA events"
```

A branch name, mutable container tag, current dimension table, or current wall
clock is not a pinned dependency. Record unavoidable nondeterminism and define a
comparison tolerance only when the business contract permits it.

## Range planning and admission

```text
year scope [------------------------------------------------------)
shards      [day 1)[day 2)[day 3) ...                    [day 365)
             build independently -> reconcile all -> dataset cutover
```

Shard on a boundary matching source/output partitioning and correction semantics.
Each input record belongs to exactly one shard, while cross-boundary operations
such as sessions need deliberate overlap plus one ownership rule. Estimate:

```text
duration ≈ total input bytes / sustainable backfill throughput
cost     ≈ scan + compute + shuffle + candidate storage + quality + downstream rebuild
```

Use measured sustainable throughput below the platform's safe residual capacity,
not peak benchmark throughput. Admission limits concurrency, queue priority,
source requests, warehouse slots, storage I/O, and downstream publication rate.

## Execution and cutover workflow

1. Approve purpose, owner, scope, consumer impact, budget, and stop conditions.
2. Pin and validate every input and dependency; dry-run a representative shard.
3. Register all half-open shards and prove coverage/no overlap.
4. Build immutable, isolated candidates with separate backfill checkpoints.
5. Validate each shard, then reconcile the complete scope across boundaries.
6. Compare old/new keys, counts, totals, distributions, and named semantic deltas.
7. Rebuild dependent aggregates/indexes under the same dataset generation.
8. Select the complete new version atomically and notify/coordinate consumers.
9. Monitor, retain rollback evidence, and retire old data per approved policy.

For a small database table, one transactional replacement may suffice. For a
large multi-partition dataset, publish new immutable partitions and one manifest
that selects the coherent set. Never let a reader combine v1 January with v2
February unless that mixed-version contract is explicitly supported.

## Historical time and dependency semantics

“As known then” and “recomputed with current corrected knowledge” are different
products. Pin bitemporal/system-time inputs when reproducing a historical report;
use corrected dimension history when deliberately restating it. Record event,
effective, source commit, ingestion, original publication, and correction
publication times needed by the consumer contract.

Randomness requires a stable seed and deterministic partition rule. External API
lookups should be snapshotted or versioned. Locale, time-zone database, library,
decimal, collation, and engine behavior can change outputs even with identical
business code.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Missing/overlapping shard | Interval/key coverage audit | Block cutover; correct registry and run scope |
| Current job starved | SLO/queue/resource saturation | Throttle or pause backfill; current SLA retains priority |
| Shard succeeds with wrong dependency | Manifest lineage mismatch | Invalidate candidate; rerun from pinned dependencies |
| Some shards publish early | Dataset manifest/version mismatch | Keep all candidates private until global certification |
| Logic changes mid-backfill | Artifact/config digest differs | Reject mixed set; rerun affected or entire semantic scope |
| Downstream aggregate partly rebuilt | Dependency version mismatch | Hide new graph; complete same generation and reconcile |
| Cutover causes consumer defect | Consumer checks/SLO regression | Select retained old version if safe or publish forward repair |
| Source history unavailable | Manifest/object missing | Stop; restore authorized backup or disclose unrecoverable scope |

## Security, privacy, and governance

Backfills magnify access, data movement, and retention risk. Grant temporary,
scope-limited access; isolate compute and candidates; audit reads, overrides, and
cutover; prevent raw values in job parameters/logs; and enforce encryption. Apply
current purpose, minimization, legal-hold, residency, retention, and erasure rules
to historical inputs and all temporary/output versions. Rebuilding deleted data
from an old backup can violate policy even if technically possible.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Range property test | Generate shard boundaries for empty/leap/DST/year scopes | Exact one-time ownership of every record | Pending |
| Golden shard | Hand-calculate old/new results and expected semantic diff | Only approved changes occur | Pending |
| Determinism test | Repeat pinned shard under equivalent environment | Equal canonical output/manifest | Pending |
| Fault/resume test | Kill shards and coordinator at each boundary | Completed work reused safely; no mixed publication | Pending |
| Full reconciliation | Keys, counts, totals, distributions, lineage across year | Zero unexplained difference | Pending |
| Load/cost rehearsal | Throttled representative period beside normal run | Current SLO and approved budget hold | Pending |
| Cutover/rollback drill | Switch test consumers new then old | Coherent versions and documented downstream limits | Pending |

A one-day fixture cannot prove one-year capacity, cross-partition correctness,
consumer compatibility, or production rollback. Test at representative scope.

## Common pitfalls

### Pitfall: one giant backfill run

Failure restarts too much work and hides progress. Use registered, bounded,
idempotent shards plus a global certification boundary.

### Pitfall: reading “latest” reference tables

Different shards see different dependencies. Pin versions and decide explicitly
whether the product is historical-as-known or corrected-as-of-now.

### Pitfall: overwriting partitions as each shard completes

Consumers see mixed logic and rollback becomes ambiguous. Keep candidates private
and publish one coherent dataset version.

### Pitfall: comparing only total row count

Missing and extra rows cancel, and intended exclusions hide corruption. Compare
keys, domain totals, grouped distributions, lineage, and named semantic changes.

## Performance, capacity, cost, and operations

Measure bytes/rows per shard, skew, scan and shuffle, throughput, retries, critical
path, queue time, source/platform utilization, candidate storage, quality scan,
downstream amplification, monetary cost, and carbon/location constraints when
required. Define concurrency and stop thresholds before launch.

Dashboards distinguish current and backfill work with bounded labels. Alerts cover
SLO interference, stalled shards, cost burn, repeated failure, dependency mismatch,
unexplained diffs, storage headroom, and cutover health. The runbook can pause new
shards, preserve completed candidates, diagnose one shard, resume safely, or abort
without changing the current certified dataset.

## Compatibility, migration, and tradeoffs

A semantic change normally creates a new data-product version. Dual-build and
compare, support a consumer migration window, publish dependencies coherently,
and document whether old exports can be corrected. Retain old versions only as
long as rollback, governance, and storage budgets permit. If rollback would
reintroduce a security/privacy defect, plan forward repair instead.

## Working example

- Python/SQL/data/tests: planned backfill specification, range planner, shard ledger, isolated candidates, semantic diff, reconciliation, and cutover harness
- Expected result: one-year candidate is complete, internally version-consistent, and contains only approved historical changes
- Scale represented: none yet; small fixture, representative-period load, then one-year rehearsal planned
- Remaining risk: long-tail skew, shared-platform contention, consumer exports, and deletion constraints

## Knowledge check

1. Distinguish replay, reprocessing, backfill, and correction for one failed day.
2. Prove that daily half-open shards cover a leap-year interval once.
3. Diagnose why January and February differ after using a mutable product table.
4. Design semantic-diff evidence for excluding synthetic events.
5. Estimate runtime and platform headroom for 1.095B events.
6. Plan cutover when one consumer cannot retract previously exported metrics.

## Key takeaways

- A backfill is a versioned historical data change, not merely an old scheduled run.
- Pin scope, inputs, code, config, reference data, and semantics.
- Isolated shards make execution retryable; one global publication keeps consumers coherent.
- Semantic diffs and independent reconciliation distinguish correction from corruption.
- Capacity, consumers, privacy, rollback, and forward repair belong in the initial plan.

## Resources

- [Python documentation: `zoneinfo`](https://docs.python.org/3/library/zoneinfo.html) (reviewed 2026-09)
- [PostgreSQL documentation: date/time types](https://www.postgresql.org/docs/current/datatype-datetime.html) (reviewed 2026-09)
- [W3C PROV overview](https://www.w3.org/TR/prov-overview/) (reviewed 2026-09)

## Related topics

- [Dependencies, retries, partial failure, and recovery](07-dependencies-retries-partial-failure-and-recovery.md)
- [Lineage, testing, operating, and evolving batch pipelines](08-lineage-testing-operating-and-evolving-batch-pipelines.md)
- [Slowly changing dimensions and bitemporal history](../05-data-modeling-and-business-semantics/05-slowly-changing-dimensions-and-bitemporal-history.md)

## Completion checklist

- [x] Scope, pinning, sharding, isolation, comparison, cutover, and rollback explained
- [x] Time, failure, security, quality, capacity, operations, migration, and evidence addressed
- [ ] Range, golden, deterministic, fault, reconciliation, load, cutover, and rollback evidence run
