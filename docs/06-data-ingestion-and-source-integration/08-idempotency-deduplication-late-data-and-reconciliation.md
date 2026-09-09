# Idempotency, Deduplication, Late Data, and Reconciliation

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic ingestion / SQL / Batch / Streaming  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Reliable ingestion assumes retries, duplicates, delay, and correction will occur.
Idempotency makes repeating an operation converge; deduplication chooses which
deliveries represent one logical record; late-data policy determines when and how
results change; reconciliation proves that source scope and target outcomes agree.

These are end-to-end properties. A connector, broker, transaction, or `MERGE`
helps at one boundary but cannot alone guarantee the business result.

## Learning objectives

- Define duplicate identity and idempotency scope independently.
- Design retry-safe publication and side effects around ambiguous commits.
- Distinguish late delivery, out-of-order data, correction, and replay.
- Write reconciliation equations at matching grains and consistency points.
- Prove convergence after failure, backfill, and repair.

## Prerequisites

- All preceding area 06 guides
- SQL keys/transactions from area 03 and identity/history from area 05

## Mental model and terminology

Idempotency is like assigning stable work names in Android WorkManager: resubmitting
the same logical work need not create another outcome. The analogy stops because
one ingestion record may affect multiple datasets and external sinks with no
shared transaction; each effect needs identity, commit evidence, and repair.

| Term | Meaning in this guide |
| --- | --- |
| Idempotency | Repeating the same logical operation produces the same committed effect within a named scope |
| Deduplication | Classifying multiple candidate deliveries/versions under a declared identity and winner policy |
| Late data | Valid data arriving after an operational or event-time expectation |
| Correction | New knowledge that supersedes a prior value; not necessarily a duplicate |
| Reconciliation | Comparison of independently derived counts, keys, totals, or digests at aligned scope/grain/time |
| Convergence | After retries/repairs stop, reruns reach the declared correct state without unexplained drift |

## Requirements, assumptions, and invariants

Reference input is 3M events/day, producer IDs retained at least 35 days, normal
lateness within seven days, replay up to 35 days, and daily publication corrected
through a versioned seven-day window. Finance totals require exact cent-level
reconciliation; behavioral counts require zero unexplained missing event IDs.

Invariants:

- Duplicate definition names source namespace, logical key, version, and retention window.
- Delivery attempts remain observable even when only one logical record is accepted.
- Same identity with conflicting immutable fields is a conflict, not silently a duplicate.
- Checkpoint/output advancement is conditional on durable publication and quality gates.
- Late and correction policies are explicit per consumer; no wall-clock discard is hidden.
- Reconciliation compares equal grain, filters, schema/semantic version, and source boundary.
- Repair is complete only when rerun results stabilize and independent evidence agrees.

## Identity and idempotency scopes

| Scope | Candidate key | Effect protected | Limitation |
| --- | --- | --- | --- |
| Source delivery | source + partition/object + position/version | Raw receipt overwrite/retry | Same logical record can arrive elsewhere |
| Logical event | tenant + producer + event_id | Accepted-event uniqueness | Producer must keep IDs stable and scoped |
| Source row version | source table + key + change version | CDC application | Corrections are distinct versions |
| Batch publication | dataset + batch/window + semantic version | Snapshot replacement | External consumers may already have side effects |
| External side effect | operation/payload identity + destination | API/notification/payment-like write | Destination must retain or expose idempotency state |

A content hash is evidence about bytes, not a universal logical key. Generated IDs
at ingestion time cannot recognize a retry of the same producer event.

## Smallest correct pattern

```sql
-- PostgreSQL-style accepted ledger sketch. Payload conflict needs explicit review.
INSERT INTO accepted_event (
    tenant_id, producer_id, event_id, payload_hash, receipt_id, event_time
)
VALUES (:tenant_id, :producer_id, :event_id, :payload_hash, :receipt_id, :event_time)
ON CONFLICT (tenant_id, producer_id, event_id) DO NOTHING;
```

`DO NOTHING` alone hides conflicting payloads and loses delivery lineage. A robust
workflow records every receipt, conditionally claims the logical key, compares
immutable fields/version, classifies exact repeat versus conflict/correction, and
reconciles claims to accepted records. Transaction isolation alone cannot include
an arbitrary object store or remote API.

## Late data, ordering, and correction

```text
event_time -------- expected window close -------- correction cutoff
     |                         |                            |
 on-time              late but correctable          policy exception/backfill
ingestion_time records when each delivery was observed
```

Out of order means relative arrival differs from required event/key order. Late
means arrival missed an expectation. A replay is deliberately re-observed old
input. A correction changes knowledge. Preserve event, source-commit, ingestion,
first-seen, processing, and publication times needed to distinguish them.

Choose among append correction records, recompute versioned partitions/windows,
or upsert current state. Publish a new certified version and notify consumers when
historical results change; do not silently mutate an already exported result whose
consumer cannot retract it.

## Reconciliation design

For a closed extraction scope:

```text
source deliveries
  = accepted first claims
  + exact duplicate deliveries
  + conflicts
  + quarantined
  + deferred

accepted logical events
  = published facts + documented exclusions/unresolved records
```

Counts alone miss substitution errors. Add anti-joins of keys, grouped counts by
source/partition/date/schema, monetary totals at correct grain, min/max positions,
and stable partition digests where canonicalization is defined. Compare at the
same source position and semantic version; live source versus yesterday's target
is not reconciliation.

## Data flow, ownership, and trust boundaries

| Boundary | Identity/commit evidence | Owner | Failure behavior |
| --- | --- | --- | --- |
| Producer | Stable logical ID/version | Producer | Retry same ID; issue explicit correction version |
| Receipt ledger | Delivery/source position and checksum | Ingestion owner | Append attempt before checkpoint |
| Identity claim | Logical key plus immutable-field digest/version | Contract owner | Classify repeat/conflict/correction atomically |
| Published dataset | Batch/window/dataset version and manifest | Data-product owner | Old-or-new visibility; retain rollback version |
| Consumer/export | Consumer checkpoint/idempotency key | Consumer owner | Replay/compensate under its own contract |
| Reconciliation report | Aligned scope, query/config versions, deltas | Joint source/data owners | Block certification on unexplained delta |

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Ack/response lost after commit | Retry finds receipt/identity claim | Return existing result or safely replay |
| Duplicate IDs with different payload | Key matches, immutable digest differs | Quarantine conflict; apply producer version policy |
| Dedup state expires before retry | Duplicate spike beyond retention | Rebuild from authoritative ledger or extend window; repair outputs |
| Late event changes certified aggregate | Lateness/reconciliation delta | Recompute version, publish correction, notify consumer |
| Partial multi-dataset publication | Manifest/version mismatch | Keep uncertified outputs invisible; complete or roll forward |
| Reconciliation compares moving boundaries | Positions/times differ | Pin common boundary and rerun report |
| Repair rerun drifts again | Repeat digest/count changes | Stop; identify nondeterminism or mutable dependency |
| External side effect duplicated | Destination lookup/audit | Use destination idempotency record or compensate explicitly |

Recovery is proven only after the same bounded replay yields the same output,
reconciliation deltas are zero or approved, and consumer-visible versions agree.

## Security, privacy, and governance

Dedup keys and reconciliation extracts can expose stable customer identity. Scope,
tokenize, authorize, audit, and retain them only as long as correctness obligations
require. Do not place raw keys or payloads in metric labels. Deletion must remove
or irreversibly transform accepted data, duplicate/conflict ledgers, raw/quarantine,
reconciliation artifacts, exports, and caches according to policy—while retaining
non-identifying audit evidence where allowed.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Duplicate matrix | Same delivery, same logical ID/new delivery, conflicting payload | Exact dispositions and one accepted logical result | Pending |
| Crash matrix | Fail around claim, publish, checkpoint, and response | Rerun converges without unexplained effect | Pending |
| Time matrix | On-time, boundary, late, out-of-order, replay, correction | Contractual version/result behavior | Pending |
| Reconciliation mutation | Drop, add, substitute, duplicate, alter amount | Counts/keys/totals/digests detect relevant defects | Pending |
| State retention | Retry before/after dedup expiry | Boundary and recovery are explicit | Pending |
| Determinism | Replay same pinned inputs/dependencies twice | Equal manifests and results | Pending |

Local deterministic evidence does not prove distributed races, broker delivery,
remote sink idempotency, or production late-arrival distributions.

## Common pitfalls

### Pitfall: “exactly once” without a scope

Exactly one broker write does not ensure exactly one database row, aggregate
change, or external effect. Name identities and commit boundaries end to end.

### Pitfall: deduplicating by all fields

A harmless metadata difference defeats it, while two legitimate identical events
may collapse. Use producer-stable logical identity and explicit version semantics.

### Pitfall: dropping everything after a fixed lateness threshold

It turns an SLO into silent data loss. Record the disposition and provide repair,
correction, or approved exclusion semantics.

### Pitfall: declaring success from equal row counts

One missing and one extra record cancel. Compare keys and domain totals/digests at
aligned scope.

## Performance, capacity, cost, and operations

Budget identity-state cardinality as arrival rate × retention window adjusted for
key/storage overhead and partitions. Measure delivery and logical-record rates,
duplicate/conflict ratios, lookup latency, state size/expiry, late-arrival age
distribution, correction churn, checkpoint lag, reconciliation scan bytes/runtime,
delta counts/amounts, and repair duration/cost.

Alerts cover unexplained reconciliation deltas, conflicts, duplicate spikes,
late-data SLO burn, state-store capacity, stalled checkpoints, non-deterministic
replays, and correction backlog. Runbooks freeze affected publication, pin inputs
and versions, bound impact, repair, reconcile independently, and communicate the
new dataset version.

## Compatibility, migration, and tradeoffs

Changing identity or lateness policy changes dataset meaning. Run old/new policies
side by side over retained input, compare claims and consumer measures, publish a
new semantic/dataset version, backfill, migrate consumers, and retain rollback.
Merging old and new dedup state in place is unsafe without a mapping proof.

| Requirement | Prefer | Tradeoff |
| --- | --- | --- |
| Authoritative replay | Immutable receipt/event ledger | Storage and governance cost |
| Fast current-state lookup | Unique transactional claim/upsert | Engine coupling and contention |
| Bounded state | Retention based on measured retry/lateness contract | Very late duplicates require offline repair |
| Reproducible corrections | Versioned partition/window rebuild | Consumer version handling and compute cost |
| Strong convergence proof | Counts + anti-joins + totals/digests | Additional scan and independent-control cost |

## Working example

- Python/SQL/data/tests: planned receipt ledger, identity claimant, late/correction fixture, versioned publisher, and reconciliation report
- Expected result: duplicates, retries, lateness, and repairs converge on declared logical results
- Scale represented: none yet; local fixture planned
- Remaining risk: distributed races, state retention sizing, external effects, and production reconciliation cost

## Knowledge check

1. Define delivery identity and logical event identity for the reference scenario.
2. Predict a timeout after commit followed by a producer retry.
3. Diagnose why `ON CONFLICT DO NOTHING` can hide corruption.
4. Design tests that distinguish late, out-of-order, replayed, and corrected data.
5. Create a reconciliation plan that detects one missing and one extra record.
6. Propose a safe migration to a new event-key policy.

## Key takeaways

- Idempotency is scoped to a logical operation and committed effect.
- Deduplication requires stable identity, conflict policy, and retained evidence.
- Late data and corrections are consumer/version decisions, not parser errors.
- Reconciliation aligns grain, scope, boundary, and semantic version.
- Convergence is demonstrated by stable replay plus independent agreement.

## Resources

- [RFC 9110: Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2) (reviewed 2026-09)
- [PostgreSQL documentation: INSERT](https://www.postgresql.org/docs/current/sql-insert.html) (reviewed 2026-09)

## Related topics

- [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md)
- [Change data capture logs and connectors](05-change-data-capture-logs-and-connectors.md)
- [Validation, quarantine, and schema evolution](07-validation-quarantine-and-schema-evolution.md)

## Completion checklist

- [x] Idempotency, duplicate identity, late data, correction, and reconciliation explained
- [x] Time, failure, security, capacity, operations, migration, and evidence addressed
- [ ] Identity, crash, time, mutation, convergence, and distributed evidence run
