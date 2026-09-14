# Data Marts, Domain Products, and Model Evolution

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Warehouses / Lakehouses / Data products / Platform architecture  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A data mart packages facts, dimensions, and metrics for a bounded consumer domain.
A data product makes that interface operational: it has explicit ownership,
contracts, discoverability, quality/freshness objectives, access policy, lifecycle,
and support. Decentralizing ownership does not remove the need for conformed
semantics and platform guarantees.

This guide covers consumer-focused marts, domain boundaries, source-aligned versus
consumer-aligned products, central/federated responsibilities, contracts,
dependency direction, and safe model evolution/deprecation.

## Learning objectives

- Define a mart or data-product boundary from consumers and ownership.
- Separate authoritative, conformed, domain-derived, and presentation models.
- Evaluate centralized and federated ownership tradeoffs.
- Design compatible schema/semantic evolution, backfill, cutover, and rollback.
- Operate a product with discoverability, SLOs, lineage, security, and support.

## Prerequisites

- All previous area 05 guides, especially conformed dimensions and metric contracts
- Area 01 sources of truth, architecture boundaries, SLOs, and publication
- Area 04 schema/catalog evolution and atomic dataset visibility

## Mental model

```text
source-aligned products       conformed integration
catalog | customer | events -> facts + dimensions + governed metrics
                                      |
                         product mart | finance mart
                                      |
                           dashboards | models | APIs
```

A data product resembles an internally published Android library: versioned API,
owner, tests, documentation, compatibility, release, and deprecation. The analogy
stops because data versions contain historical state, backfills can change past
answers, consumers may copy outputs, and access/deletion must propagate across
lineage rather than only upgrading a dependency.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Data mart | Consumer-oriented analytical dataset(s) for a bounded subject/decision |
| Data product | Owned, discoverable, reliable, governed data interface with lifecycle |
| Source-aligned | Product organized around authoritative domain outputs |
| Consumer-aligned | Product shaped for a decision or analytical use case |
| Contract | Versioned structural, semantic, quality, operational, and policy promises |
| Federated governance | Shared rules with enforcement split between domain and platform owners |
| Deprecation | Announced, measured retirement process with migration path |

## Requirements and invariants

The reference product-performance mart serves daily product decisions, not
customer-level operational workflows. It exposes one tenant-product-UTC-day row,
versioned product context, view/purchase components, revenue in declared currency,
and certified conversion metrics.

- Every exposed model has grain, key, owner, source lineage, freshness, retention,
  classification, and compatibility policy.
- Derived marts depend toward authoritative/conformed products; source systems do
  not query consumer marts to make authoritative writes.
- Shared metrics and conformed dimensions are reused or intentionally versioned,
  not privately redefined under the same name.
- Tenant isolation and deletion obligations survive every materialized copy/export.
- Publication is atomic by dataset version; a consumer never sees a half-backfill.
- Breaking grain, key, unit, time, or population changes receive a new interface version.

## Choosing a boundary

| Boundary | Prefer when | Main danger | Required ownership |
| --- | --- | --- | --- |
| Enterprise/conformed core | Cross-domain comparison is central | Bottleneck and lowest-common-denominator model | Central integration plus domain stewards |
| Source-aligned product | Stable authoritative domain output is reusable | Leaks source complexity to consumers | Source/domain team with data SLO |
| Consumer-aligned mart | Known decisions need simple, fast access | Duplicate logic and proliferation | Consumer-domain data owner |
| Presentation extract | Tool-specific shape is unavoidable | Becomes undocumented source of truth | Explicitly derived, short lifecycle |

Start with the smallest boundary that has a real owner and consumers. “Data mesh”
does not mean every team independently chooses identity, calendar, privacy, and
metric meanings; federated decisions require enforceable interoperability.

## Product contract

| Contract facet | Product-performance mart promise |
| --- | --- |
| Interface | Versioned table/snapshot and catalog entry |
| Grain/key | `(tenant_key, product_key, calendar_date)` |
| Semantics | Certified metric and dimension versions |
| Freshness | Published after daily close within stated SLO |
| Quality | Uniqueness, resolution, reconciliation, and volume thresholds |
| Compatibility | Additive columns optional; breaking meaning gets new major version |
| Security | Tenant/role policies; no direct customer identity |
| Recovery | Prior snapshot remains visible until certified replacement commits |
| Support | Named business owner, data owner, escalation, and runbook |

Service levels should describe consumer-visible freshness/correctness, not merely
job success. A green pipeline that publishes wrong or incomplete rows violates
the product contract.

## Dependency direction and trust

The event ledger and catalog/customer authorities are sources; conformed facts,
dimensions, and metrics are reusable derived products; domain marts depend on
them; caches and extracts depend on marts. Feedback about quality flows upstream,
but authoritative writes never depend on a dashboard copy.

Trust is scoped: a certified daily mart may be trusted for seven-day-restated
product reporting but not billing, real-time personalization, or person-level
decisions. Catalog certification must state permitted and prohibited uses.

## Model evolution protocol

Classify a proposed change before implementation:

| Change | Compatibility | Delivery path |
| --- | --- | --- |
| Add nullable descriptive column | Often backward compatible | Expand, test old consumers, announce |
| Make nullable field required | Breaking for existing/history | Populate/validate first; new contract if semantics change |
| Rename while meaning stays same | Potentially breaking | Add alias/new field, dual-populate, migrate, remove later |
| Change grain/key | Breaking | New model/version and full reconciliation |
| Change currency/time/metric population | Semantically breaking | Parallel semantic version and quantified difference |
| Correct bounded historical rows | Contract-dependent | New snapshot, lineage, correction notice |

Use expand/migrate/contract: publish the new interface beside the old, backfill
from pinned authoritative inputs, run structural and semantic comparisons, dual-
run named consumers, cut over atomically, observe, then deprecate. Rollback keeps
the prior snapshot/interface and accounts for new writes or decisions made during
coexistence.

## Backfill and cutover

A backfill has its own run/version ID, bounded partitions, source snapshot,
model/metric/identity versions, resource limits, reconciliation, and cancellation
path. It must not starve the production freshness workload. Historical partitions
are staged out of sight, certified as one coherent version, then made visible
through catalog/manifest metadata.

If old and new outputs differ, classify differences as expected semantic changes,
source corrections, or defects. Aggregate equality alone can hide row reassignment;
compare keys, distributions, dimensions, nulls, and representative consumer queries.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Undocumented downstream copy | Lineage/query/access inventory gap | Find owner; freeze deprecation; migrate or explicitly retire |
| Partial backfill visible | Snapshot completeness/manifest failure | Repoint to prior version; abandon staging |
| Semantic drift across marts | Certified metric/component comparison | Restore shared version; publish explicit divergence if justified |
| Contract-breaking producer deploy | Compatibility/consumer test | Reject or quarantine input; retain old product version |
| Backfill overloads warehouse | Queue/latency/cost SLO breach | Throttle/cancel; resume from bounded partitions |
| Access policy missing on new version | Negative authorization test | Block publication; repair policy and audit exposure |

Recovery is complete after data and policy reconciliation, dependent consumer
verification, corrected catalog/lineage, and an explicit account of decisions
made using affected versions.

## Security, privacy, and governance

Apply least privilege, tenant isolation, purpose constraints, row/column policy,
encryption, retention, deletion, audit, and safe sampling to every product version.
Federation divides responsibilities but must not create policy gaps: the platform
can provide enforcement primitives, while domain owners classify fields and
approve uses. Contracts and lineage should be discoverable without exposing
sensitive samples or secrets.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Contract/schema tests | Published interface matches declared version | Pending |
| Product quality suite | Grain, uniqueness, resolution, freshness, and totals pass | Pending |
| Old/new comparison | Expected differences quantified; unexplained drift is zero | Pending |
| Consumer contract tests | Named critical queries work during coexistence | Pending |
| Negative authorization | Cross-tenant/restricted access denied on every version | Pending |
| Backfill/cutover drill | Partial failure retains old version and safe resume works | Pending |
| Deprecation audit | No active named/observed consumers remain | Pending |

## Common pitfalls

### Pitfall: calling a table a data product

Without owner, consumers, semantics, SLO, policy, discoverability, and lifecycle,
it is an artifact—not an operable product.

### Pitfall: creating one mart per dashboard

This duplicates meaning and makes reconciliation/deprecation unmanageable. Reuse
stable decision grains and let presentation remain thin.

### Pitfall: treating additive schema change as automatically safe

A new column can change `SELECT *`, row width, downstream serialization, privacy,
or interpretation. Test actual consumers and policy.

## Performance, capacity, cost, and operations

Budget rows/bytes, refresh duration, query concurrency/latency, scan bytes,
storage versions, backfill throughput, lineage/catalog load, and per-consumer
cost. Monitor freshness, completeness, reconciliation, contract violations,
consumer errors, snapshot age, access denials, and deprecation usage with bounded
labels. Define on-call/escalation, last-known-good serving, repair, restore, and
disaster-recovery procedures.

Physical pre-aggregation trades flexibility for scan/cost reductions. Choose it
from observed workloads and preserve lower-grain authority for future questions
and repair.

## Working example

- SQL/data/tests/catalog: planned product-performance mart v1/v2 and migration fixture
- Expected result: atomic versions, contract compliance, quantified semantic diff, and safe rollback
- Scale represented: none yet; backfill isolation, concurrency, and cost unverified
- Remaining risk: hidden consumers, policy propagation, workload contention, and organization ownership

## Knowledge check

1. Distinguish a mart artifact from an operable data product.
2. Choose source-aligned versus consumer-aligned ownership for product performance.
3. Classify grain, rename, nullable-addition, and currency changes by compatibility.
4. Design a backfill that cannot expose half-complete history.
5. Diagnose two marts with equal totals but different product assignments.
6. Plan deprecation with lineage, observed usage, consumer sign-off, and rollback.

## Key takeaways

- Product boundaries combine consumer value with accountable ownership and contracts.
- Authority flows from sources through conformed models to marts and extracts.
- Certification is scoped to declared uses and SLOs.
- Semantic changes require versions even when physical schemas remain compatible.
- Backfill, cutover, security, observability, and deprecation are model-design concerns.

## Resources

- [Martin Fowler: Data Mesh Principles and Logical Architecture](https://martinfowler.com/articles/data-mesh-principles.html) (reviewed 2026-09)
- [Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard/latest/) (reviewed 2026-09)

## Related topics

- [Metrics, semantic layers, and consistent meaning](07-metrics-semantic-layers-and-consistent-meaning.md)
- [Area overview](README.md)

## Completion checklist

- [x] Mart/product boundaries, ownership, contracts, evolution, and federation explained
- [x] Backfill, cutover, rollback, security, operations, cost, and deprecation addressed
- [ ] Product contracts, consumer tests, authorization, backfill, and migration evidence run
