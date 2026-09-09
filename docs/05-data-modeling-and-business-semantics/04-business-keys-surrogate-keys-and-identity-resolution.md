# Business Keys, Surrogate Keys, and Identity Resolution

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Relational systems / Warehouses / Integration / Governance  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Identity answers whether two records refer to the same business thing. A business
key expresses identity in a business/source domain; a surrogate key gives a model
stable internal row identity. Neither automatically resolves conflicting sources,
reused identifiers, history versions, or real-world people.

This guide covers key scope, surrogate purpose, crosswalks, late binding, match/
merge/unmerge, collision handling, and unknown members. Probabilistic entity-
resolution algorithms are introduced only as a risk boundary, not implemented.

## Learning objectives

- Distinguish business, natural, source, surrogate, and fact identity.
- Choose key scope and prove uniqueness over the required lifetime.
- Model source crosswalks and deterministic identity resolution.
- Handle late-arriving mappings, merges, splits, and ID reuse safely.
- Protect sensitive identity data and quantify false-match consequences.

## Prerequisites

- Grain and relationship contracts from guide 01
- Relational keys/constraints from guide 02 and dimensional joins from guide 03

## Mental model

Keys answer different questions:

```text
(tenant, source_system, source_product_id)  business/source identity
                         |
                    identity map
                         |
product_entity_id                         integrated business entity
                         |
product_key                               one analytical history row
```

An Android database's auto-generated `Long` is comparable to a warehouse
surrogate: compact and local to one database. It does not establish that two
contact rows represent the same person, remain meaningful after export, or can
be regenerated identically during a rebuild.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Natural key | Real-domain attribute set that may identify an entity |
| Business key | Governed identifier meaningful within a stated business scope |
| Source key | Identifier assigned by one source system, qualified by source/scope |
| Surrogate key | Model-controlled identifier without external business meaning |
| Crosswalk | Versioned mapping from source identity to integrated identity |
| Identity resolution | Decision process that links observations to an entity |
| Merge/split | Correction that combines identities or separates an incorrect match |

## Requirements and invariants

- Every key names its namespace, tenant/domain scope, issuer, and reuse policy.
- Event identity `(tenant_id, event_id)` remains independent from delivery ID.
- A dimension surrogate identifies one history row, not merely the entity across all time.
- Source keys are never joined across systems without the source namespace.
- Crosswalk decisions retain rule/model version, evidence, decision time, effective
  time, confidence where applicable, and an auditable reversal path.
- Unknown, anonymous, deleted, withheld, and not-applicable identities remain distinct.

At 5M customers and 3M events/day, even a 0.1% incorrect automatic match can
misattribute thousands of records. That is a sensitivity illustration, not a
measured error rate.

## Key choice table

| Need | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Deduplicate delivered events | Stable producer event ID plus tenant | Represents logical event | Producer cannot guarantee lifecycle uniqueness |
| Reference current product authority | Tenant-scoped source/business key | Enforceable at issuer | Keys can be reused or corrected |
| Join compact fact to type-2 dimension | Surrogate history-row key | One version, efficient join | Regeneration cannot preserve/re-key facts safely |
| Integrate two product systems | Versioned crosswalk to entity ID | Makes decision explicit | Sources already share governed global identity |
| Analyze anonymous activity | Separate pseudonymous device/session identity | Avoids false person claim | Consent and deterministic account link arrive |

## Identity map sketch

Generic SQL design; not executed:

```sql
CREATE TABLE product_identity_map (
    tenant_id          bigint NOT NULL,
    source_system      text NOT NULL,
    source_product_id  text NOT NULL,
    product_entity_id  text NOT NULL,
    effective_from     timestamptz NOT NULL,
    effective_to       timestamptz,
    decided_at         timestamptz NOT NULL,
    decision_version   text NOT NULL,
    PRIMARY KEY (tenant_id, source_system, source_product_id, effective_from),
    CHECK (effective_to IS NULL OR effective_to > effective_from)
);
```

The primary key alone does not prevent overlapping effective intervals. The real
implementation needs an engine-supported exclusion/validation rule plus a
concurrent-writer test. Hashes of business fields are useful change detectors,
not collision-free identities unless collision handling is part of the contract.

## Deterministic and probabilistic resolution

Deterministic rules can link an authenticated account ID or governed catalog
cross-reference. Normalize only according to explicit domain rules: lowercasing
may be correct for one identifier and corrupt another.

Probabilistic matching compares imperfect signals such as name, address, or
device behavior. It produces a scored decision, not truth. Define thresholds,
clerical-review paths, protected-attribute policy, false-positive/false-negative
cost, drift monitoring, and unmerge behavior before use. Sensitive attributes
must not be added merely because they improve match rate.

## Late binding, merge, and split lifecycle

Facts may arrive before a mapping. Keep the source-scoped identity and assign a
specific unresolved member; later mapping can re-key affected facts in a new
dataset version. Do not discard source identity after assigning a surrogate.

A merge records that identities A and B now map to C from a stated effective and
decision time. Consumers need a policy: restate history or apply only going
forward. A mistaken merge requires a split/unmerge that can locate every derived
fact and metric version influenced by the old decision.

## Data flow, ownership, and trust boundaries

Source owners issue source IDs. A domain identity owner governs match policy and
the integrated entity; the dimension pipeline issues surrogate history keys;
fact builders preserve source and resolved identities. Consumers may not invent
private crosswalks and still claim conformed metrics.

Identity inputs are untrusted and often highly sensitive. Resolution outputs are
derived claims with confidence and provenance, not replacements for source truth.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Key reused by source | Temporal collision/profile discontinuity | Split by validity; re-resolve affected facts |
| Surrogate regenerated differently | Fact-to-dimension misses/checksum drift | Restore mapping or atomically re-key full fact set |
| False merge | Review, contradictory authenticated evidence | Versioned unmerge; rebuild lineage descendants |
| Duplicate entity race | Unique/concurrency test | Select winner under transaction; redirect loser audibly |
| Mapping arrives late | Unresolved-age metric | Bind in new snapshot and reconcile affected periods |
| Hash collision/truncation | Distinct source keys share derived key | Compare original keys; replace key scheme and migrate |

## Security, privacy, and governance

Identity graphs enlarge privacy and breach impact. Use least privilege, tokenized
serving IDs, separate re-identification mappings, encryption, retention/deletion
rules, purpose limitation, audit logs, and human-review controls. Do not log raw
email, device IDs, addresses, match features, or secrets. Deletion must propagate
through crosswalks and derived facts according to legal retention and tombstone
policy without accidentally re-linking the person on replay.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Namespace collision fixture | Same raw ID in two sources/tenants stays distinct | Pending |
| Concurrent claim | One integrated identity decision commits | Pending |
| Late mapping | Unresolved facts become resolved without count drift | Pending |
| Merge/unmerge replay | Derived facts and totals follow declared restatement policy | Pending |
| Hash collision mutation | Collision is detected, not silently merged | Pending |
| Privacy/delete test | Restricted mapping and derived copies follow policy | Pending |

## Common pitfalls

### Pitfall: treating a surrogate as business truth

It guarantees identity only inside its issuing model. Preserve source keys,
provenance, and crosswalk decisions.

### Pitfall: joining on normalized names or emails

Formatting changes, shared values, recycled addresses, and privacy constraints
make these unsafe implicit identities. Use governed resolution with measured error.

### Pitfall: overwriting a merge mapping

An overwrite destroys reproducibility and makes unmerge impossible. Version both
effective and decision history and rebuild descendants explicitly.

## Performance, operations, and migration

Profile uniqueness, reuse intervals, collision buckets, match/unmatched rates,
confidence distribution, manual-review queue, mapping age, skewed entities, join
cost, and re-key blast radius. Metric labels must not contain identifiers.

Changing keys requires a crosswalk between old and new, dual-key publication,
backfilled facts/dimensions, referential and metric reconciliation, consumer
cutover, rollback while both mappings remain readable, and eventual deprecation.
Never renumber a dimension in place while facts still refer to it.

## Working example

- SQL/data/tests: planned tenant/source product crosswalk with late, merge, split, and collision cases
- Expected result: identity decisions are deterministic, reversible, and reconciled
- Scale represented: none yet; concurrency and 5M-entity behavior unverified
- Remaining risk: source reuse, probabilistic error, privacy, and re-key cost

## Knowledge check

1. Classify `delivery_id`, `event_id`, `product_sku`, and `product_key` by purpose.
2. Predict the result of joining two sources on unqualified `product_id`.
3. Diagnose why a dimension rebuild orphaned all existing fact foreign keys.
4. Design late-binding behavior for an unknown product.
5. Define evidence and rollback for merging two customer identities.
6. Add deletion requirements without permitting replay to resurrect identity.

## Key takeaways

- Identity is a scoped, time-aware business claim; a key is its representation.
- Surrogates support model joins but do not resolve real-world identity.
- Preserve source identity, provenance, and reversible mapping decisions.
- Late binding and merges require explicit restatement and reconciliation policy.
- Identity resolution is a high-risk privacy and quality boundary.

## Resources

- [PostgreSQL documentation: Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) (reviewed 2026-09)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) (reviewed 2026-09)

## Related topics

- [Dimensional modeling: facts, dimensions, and stars](03-dimensional-modeling-facts-dimensions-and-stars.md)
- [Slowly changing dimensions and bitemporal history](05-slowly-changing-dimensions-and-bitemporal-history.md)

## Completion checklist

- [x] Key roles, namespaces, resolution, late binding, merge, and split explained
- [x] History, failure, privacy, operations, and migration addressed
- [ ] Crosswalk, concurrency, collision, merge/unmerge, and deletion evidence run
