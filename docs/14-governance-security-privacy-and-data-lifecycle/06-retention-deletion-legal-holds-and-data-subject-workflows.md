# Retention, Deletion, Legal Holds, and Data-Subject Workflows

> Status: Documentation complete  
> Level: Intermediate to Senior  
> Applies to: Batch / Streaming / Storage / Warehouses / Backups  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Retention defines how long data is kept for an approved purpose or obligation.
Deletion is a convergent workflow across authoritative data, derived copies,
indexes, caches, exports, safe fixtures, and recovery media. A legal hold is an
authorized, scoped suspension of normal destruction. A data-subject workflow
locates the correct subject, evaluates the applicable request, executes approved
actions, communicates status, and preserves safe evidence.

This guide teaches engineering controls, not whether a request must be fulfilled
under a particular law. Privacy and legal owners decide identity assurance,
jurisdiction, exceptions, deadlines, holds, and response content.

## Learning objectives

- Define retention from purpose and obligations rather than storage convenience.
- Design deletion identity, copy inventory, tombstones, and convergence receipts.
- Reconcile legal holds with expiration without turning holds into indefinite copies.
- Handle backups, immutable logs, late/replayed data, and restored snapshots.
- Test request correctness, idempotency, partial failure, and proof boundaries.

## Prerequisites

- [Ownership and lineage](01-data-ownership-stewardship-catalogs-and-lineage.md), [classification/purpose](02-classification-personal-data-and-purpose-limitation.md), and [safe data](05-masking-tokenization-and-safe-nonproduction-data.md).
- Planned subject map, lifecycle state machine, fixtures, and restore environment.

## Mental model and terminology

Deleting a Room row is a useful local analogy, but distributed data has immutable
files, aggregates, stream state, materialized views, exports, and backups. One
transaction cannot cover them. Treat deletion as a durable saga with per-copy
receipts and a convergence objective, while avoiding resurrection from replay.

```text
verified request + policy/hold decision -> immutable case manifest
                    |
            resolve scoped subject IDs
                    |
       fan out commands to known copy owners
                    |
       receipts + reconciliation + late-data fence
                    |
     complete / exception / retry / investigated gap
```

| Term | Meaning |
| --- | --- |
| Retention rule | Versioned trigger, duration, action, scope, authority, and exceptions |
| Deletion identity | Stable scoped key used to locate a subject without ambiguous matching |
| Tombstone/suppression marker | Durable fact preventing deleted identity from reappearing during replay |
| Legal hold | Approved scope that suspends specified destructive actions until release |
| Deletion receipt | Safe evidence of action/outcome for a dataset version and request |
| Crypto-shredding | Destruction of scoped key authority; effectiveness depends on all copies/key paths |

## Requirements, scale assumptions, and invariants

For every dataset specify lifecycle trigger (event, ingest, publish, case close),
duration, action, policy version, time zone, owner, derived copies, backup behavior,
hold precedence, subject locator, evidence retention, and deletion objective.
Assume 3 million events/day, 35 hot days, 30 derived datasets, 100 deletion cases/
day, and backups retained under a separately approved recovery schedule.

Invariants:

- Every governed copy has a retention rule or an explicit time-bounded exception.
- Request scope and subject identity are verified before reading, exporting, or deleting data.
- Deletion is idempotent and retryable; missing data is distinguished from failed search.
- A completed case accounts for every in-scope known copy and outstanding exception.
- Replay, backfill, CDC, cache fill, and restore cannot silently resurrect deleted data.
- Holds are authorized, minimal, reviewable, expiring/released, and hidden from unauthorized parties.
- Evidence proves system actions without retaining the deleted payload or excessive identity.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Request intake | Case ID, verified subject, scope, jurisdiction facts | Privacy operations | Reject/hold ambiguous identity | Highly restricted |
| Decision service | Applicable rule, actions, hold/exception | Privacy/legal owner | No destructive action on unknown | Privileged control state |
| Subject map | Scoped subject -> dataset identities | Identity/data owner | Incomplete result blocks completion | Restricted authority |
| Dataset command | Case, policy, identity, deadline | Dataset owner | Idempotent retry; receipt per scope | Cross-team command |
| Backup/restore | Suppression ledger and restore procedure | Resilience owner | Restore isolated until deletion reapplied | Recovery boundary |
| Evidence store | Minimal decision/action/receipt | Audit owner | Append correction; no payload | Confidential evidence |

## Retention and deletion protocol

A retention rule is executable only if it names the clock and action. “Keep 30
days” is ambiguous: 30 days after event time, ingestion, publication, account
closure, or purpose expiry? Decide whether expiration deletes rows, drops
partitions, rewrites files, destroys scoped keys, anonymizes under an approved
method, or moves to an archive with a different purpose.

Deletion case state:

```text
RECEIVED -> IDENTITY_VERIFIED -> DECIDED -> DISPATCHED
   -> PARTIAL -> RECONCILED -> COMPLETED
                 |              |
             EXCEPTION/HOLD  superseding correction
```

State transitions are append-oriented and attributable. `COMPLETED` requires the
manifest's in-scope copies to report terminal outcomes and independent inventory
reconciliation to find no unexplained copy.

### SQL model

```sql
SELECT m.dataset_id
FROM deletion_manifest_item m
LEFT JOIN deletion_receipt r
  ON r.case_id = m.case_id
 AND r.dataset_id = m.dataset_id
 AND r.policy_version = m.policy_version
WHERE m.case_id = :case_id
GROUP BY m.dataset_id
HAVING COUNT(CASE WHEN r.outcome IN ('deleted', 'not_found', 'approved_exception')
                  THEN 1 END) = 0;
```

This identifies missing terminal receipts under a fixed manifest. Engine-specific
`FILTER` could be clearer. `not_found` is valid only after a successful complete
search; `NULL`/timeout cannot be coerced to it.

### Python model

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Receipt:
    dataset_id: str
    outcome: Literal["deleted", "not_found", "retry", "exception"]
    policy_version: int

def unresolved(expected: set[str], receipts: list[Receipt]) -> set[str]:
    terminal = {r.dataset_id for r in receipts
                if r.outcome in {"deleted", "not_found", "exception"}}
    return expected - terminal
```

Production receipts need case/item identity, dataset/snapshot boundary, timestamps,
attempts, safe error classes, approval for exceptions, and authenticated writers.

## Records, files, streams, and backups

Mutable tables can delete by indexed identity; immutable files/table snapshots
need rewrite plus snapshot expiration; aggregates may need recomputation if the
subject contribution is material or policy requires it. Stream processors need
state removal and a suppression check before accepting replayed history. Search
indexes, caches, extracts, emails, notebooks, CI artifacts, and vendor copies are
datasets even when catalog tooling does not call them tables.

Backups usually cannot be selectively edited safely. Minimize/expire them on an
approved schedule, restrict use, carry the suppression ledger and cases forward,
restore into isolation, reapply deletions before consumers reconnect, and test
this. Crypto-shredding works only if keys are scoped, all decryptable copies use
them, caches/plaintext are absent, and key recovery paths are addressed.

## Failure model and recovery

| Failure | Detection/containment | Recovery evidence |
| --- | --- | --- |
| Wrong subject match | Identity confidence and approval gate | Stop; correct manifest; assess improper access/deletion |
| Dataset misses command | Receipt deadline and catalog reconciliation | Redispatch; owner repairs; terminal receipt |
| Partial immutable-file rewrite | Candidate + atomic snapshot commit | Discard candidate; rerun; reconcile rows/files |
| Late CDC/replay resurrects row | Suppression check and post-delete monitor | Delete again; repair ingestion boundary |
| Hold arrives during deletion | Serialized policy transition | Stop remaining actions; record completed irreversible actions |
| Hold never released | Review-age alert | Authorized release; resume retention; audit closure |
| Backup restore resurrects data | Isolated restore reconciliation | Reapply ledger before publication |
| Evidence store includes payload | Classification/scanner | Restrict, minimize, migrate, delete excess evidence |

## Security, privacy, and governance

Requests and holds reveal sensitive facts. Apply strong identity assurance,
least-privilege case access, dual control for bulk/destructive actions, tenant
scope, rate limits, and anomaly detection. Protect against malicious mass deletion,
path/query injection, forged receipts, subject-map enumeration, and insiders using
request tooling as a search interface.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| State/idempotency | Deterministic multi-copy fixture | Duplicate/out-of-order commands | One terminal outcome per item | Pending |
| Copy reconciliation | Catalog plus planted shadow copy | Planned inventory comparison | Shadow copy prevents completion | Pending |
| Replay | Deleted identity plus late event | Planned pipeline test | No consumer-visible resurrection | Pending |
| Hold race | Controlled transition schedule | Planned concurrency test | Policy-defined serialization | Pending |
| Restore | Real test backup | Restore in isolation and reapply ledger | Deleted identity absent before publish | Pending |
| Scale | Generated case/backlog | Planned load/cost test | Objective met without starving current work | Pending |

## Debugging guide

Inspect case, subject-scope hash, policy/hold version, manifest, dataset/snapshot,
command/attempt, receipt, lineage, suppression version, replay offset, backup
generation, and restore publication ID. Keep raw identity out of general logs.
Contain publication if resurrection or wrong-person action is plausible. Completion
needs owner receipts plus independent copy and consumer reconciliation.

## Common pitfalls

### Pitfall: delete from the source table only

Derived tables, files, indexes, caches, exports, and backups remain. Build lineage
and observed inventory into the manifest.

### Pitfall: retain tombstone payload forever

Prevention evidence becomes a new personal dataset. Store the minimum scoped
suppression identity with its own authority, access, and retention.

### Pitfall: report success when a dependency timed out

Unknown is not not-found. Retry, escalate, or record an explicit approved exception.

## Performance, observability, and cost

Measure cases/day, identities/case, copies/case, dispatch and completion latency,
retry/backlog age, expired bytes, file rewrite amplification, restore reapplication
time, outstanding holds, exceptions, and resurrection signals. Partition pruning
may make scheduled expiration cheap while subject deletion scattered across files
is expensive; design delete indexes/mappings and capacity before promises.

## Compatibility, migration, and delivery

Version retention rules, manifests, subject-map semantics, commands, receipts,
suppression format, and restore procedures. Shadow new copy discovery, dual-read
old/new subject IDs, backfill mappings, rehearse deletion, then cut over. Preserve
case history through migration. Rollback of workflow code must still understand
new tombstones and cannot recreate deleted data.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Partition expiration | Lifecycle aligns with partition | Coarse deletion | Subject-specific action required |
| File rewrite | Exact rows must be removed | Compute/I/O and snapshots | Scoped key destruction is valid |
| Suppression ledger | Replay can resurrect | It is sensitive durable state | Upstream history is physically gone |
| Backup expiry + reapply | Selective edit unsafe | Delayed physical removal | Obligation requires another design |

## Working example

- Workflow model: Planned under `src/big_data_example/lifecycle/`
- SQL: Planned manifest/receipt/reconciliation queries under `sql/lifecycle/`
- Data: Planned multi-copy, hold, late-event, and backup fixtures
- Tests: Planned idempotency, partial failure, replay, restore, load, and security cases
- Expected result: Completion only after every scoped copy converges or has approved exception
- Scale represented: Local state fixture and production estimate; no legal or service evidence
- Remaining risk: Shadow copies, identity resolution, immutable storage cost, vendors, holds, and jurisdiction

## Knowledge check

1. Explain why deletion is a convergent workflow rather than one SQL statement.
2. Predict behavior when a late event arrives after completion.
3. Diagnose a `not_found` receipt produced after timeout.
4. Design restore publication that prevents resurrection.
5. Estimate worst-case commands/day and file rewrite amplification.
6. Plan subject-key migration without losing active cases.
7. Add a planted-shadow-copy reconciliation case.

## Key takeaways

- Retention needs a trigger, duration, action, scope, owner, and exception model.
- Deletion identity and complete copy inventory determine correctness.
- Tombstones/suppression protect against replay but are governed sensitive state.
- Backups require expiry, isolation, reapplication, and restore evidence.
- Technical receipts demonstrate actions, not legal compliance by themselves.

## Resources

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) (reviewed 2026-09)
- [EU GDPR official text](https://eur-lex.europa.eu/eli/reg/2016/679/oj) (reviewed 2026-09; applicability and exceptions require qualified legal review)
- [NIST SP 800-53 Rev. 5 controls](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) (reviewed 2026-09; control catalog, not automatic compliance)

## Related topics

- [Ownership and lineage](01-data-ownership-stewardship-catalogs-and-lineage.md)
- [Safe nonproduction data](05-masking-tokenization-and-safe-nonproduction-data.md)
- [Audit and compliance evidence](07-audit-policy-enforcement-and-compliance-evidence.md)

## Completion checklist

- [x] Retention, deletion, holds, requests, copies, backups, replay, security, scale, and migration covered
- [x] Legal decision and technical evidence boundaries explicit
- [x] Working example accurately marked Planned
- [ ] State, inventory, replay, hold, restore, load, vendor, and production evidence executed

