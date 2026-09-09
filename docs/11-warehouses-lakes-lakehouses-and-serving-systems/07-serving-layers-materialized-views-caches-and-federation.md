# Serving Layers, Materialized Views, Caches, and Federation

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Serving / SQL / Caching / Federation / Architecture  
> Data scale: Local query design; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A serving layer is a consumer-facing representation optimized for a declared
query, latency, concurrency, and freshness contract. Materialized views
precompute results, caches reuse recent results, indexes accelerate access, and
federation queries remote systems without first centralizing all data. Each adds
state or dependencies whose freshness, consistency, security, and recovery must
be owned.

This guide designs those boundaries for BI and application reads. It does not
claim that one serving technology should handle every access pattern.

## Learning objectives

- Choose precomputation, indexing, caching, federation, or direct query from an SLO.
- Define source frontier, refresh, invalidation, and correction semantics.
- Prevent serving workloads from harming authoritative sources and publication.
- Design idempotent materialized-view refresh and atomic cutover.
- Diagnose stale, inconsistent, overloaded, or partially refreshed results.

## Prerequisites

- [Storage and serving system selection](01-storage-and-serving-system-selection.md)
- [Data warehouse architecture and workload management](02-data-warehouse-architecture-and-workload-management.md)
- [ACID tables, time travel, compaction, and maintenance](06-acid-tables-time-travel-compaction-and-maintenance.md)
- [Delivery semantics, ordering, idempotency, and transactions](../10-messaging-streaming-and-change-data-capture/04-delivery-semantics-ordering-idempotency-and-transactions.md)

## Mental model and terminology

```text
authoritative/curated snapshot S42
        |
        +-> materialized metric M17 (through S42)
        +-> key-serving projection K8 (through source position P)
        +-> cache entry C (from M17, expires/invalidates by policy)
        +-> federated query ----> remote source at its own version
```

A cache resembles an Android repository's local cache: it avoids repeated remote
work and needs invalidation. The analogy stops because a data result may depend on
billions of rows, multiple snapshots, tenant policies, semantic definitions, and
distributed refresh jobs; a TTL alone cannot prove correctness.

| Term | Meaning in this guide |
| --- | --- |
| Serving layer | Derived boundary optimized for a consumer workload and SLO |
| Materialized view | Persisted result maintained or refreshed from source data |
| Result cache | Reusable prior query result keyed by query, parameters, identity, and source state |
| Invalidation | Decision that a cached/materialized result may no longer satisfy its contract |
| Federation | Query planning/execution across separately owned remote systems |
| Pushdown | Sending filters, projections, aggregates, or limits to the remote source |
| Staleness budget | Maximum permitted distance in time/version between source truth and served result |

## Requirements, scale assumptions, and invariants

Assume a product-metric API at 500 requests/s bursts and 200 ms p95, 20 concurrent
BI users at 500 ms p95 for selective views, 15-minute source-to-serving freshness,
100K product keys, tenant isolation, and a daily certified batch. Record whether
availability may serve stale results and the maximum permitted age.

- Every served result identifies or can resolve its semantic version and source frontier.
- Cache keys include every parameter and security/policy dimension affecting results.
- Refresh publishes a complete version or retains the prior one.
- Duplicate or out-of-order refresh attempts cannot move the frontier backward.
- Serving failure cannot corrupt the authoritative dataset.
- Federation has bounded remote scans, deadlines, concurrency, and cancellation.
- Correction/deletion propagates within an owned SLA and is reconciled.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure/degradation |
| --- | --- | --- | --- |
| Curated source | Snapshot/frontier and semantic model | Dataset owner | Preserve last certified version |
| Refresh pipeline | Source version to serving version mapping | Serving pipeline owner | Retry idempotently in private candidate |
| Materialized/key view | Declared grain, freshness, lookup/query shape | Serving owner | Serve known stale only if contract allows |
| Cache | Full key, value, source version, expiry | Application/platform owner | Miss/bypass; never cross tenant/policy |
| Federated source | Remote schema, consistency, quota, version | Remote owner | Timeout/partial failure is explicit |
| Consumer API/SQL | Result, version, freshness, error semantics | Consumer contract owner | Bounded response or actionable failure |

## Selecting a serving pattern

| Need | Prefer | Main cost/risk |
| --- | --- | --- |
| Repeated expensive aggregate | Materialized view | Refresh cost and staleness |
| Predictable lookup by key | Keyed projection/index | Extra copy and update ordering |
| Repeated identical bounded query | Result cache | Invalidation, policy-aware keying |
| Rare cross-system exploration | Federation | Remote load, latency, semantic mismatch |
| Fresh ad hoc analytics | Governed warehouse/lakehouse query | Compute/concurrency cost |

Precompute when query savings exceed refresh, storage, governance, and correction
cost. Federation avoids copying but transfers availability, performance, and
security dependencies into query time.

## Materialized refresh and publication

```sql
-- Generic full-refresh candidate; atomic swap syntax is engine-specific.
CREATE TABLE product_metric_candidate AS
SELECT tenant_id,
       product_id,
       event_date,
       COUNT(*) AS event_count,
       :metric_version AS metric_version,
       :source_snapshot AS source_snapshot
FROM product_event_fact /* pinned to :source_snapshot */
WHERE event_date >= :start_date AND event_date < :end_date
GROUP BY tenant_id, product_id, event_date;
```

Validate grain uniqueness, source/output reconciliation, policy, and monotonic
frontier before atomically changing the serving name/pointer. Incremental refresh
must additionally own late input, changed dimensions, deletes, duplicate changes,
and rebuild equivalence. `NULL` tenant/product keys go through explicit unknown or
rejection policy, never accidental shared cache keys.

### Cache key contract

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MetricCacheKey:
    tenant_id: str
    principal_policy_version: str
    metric_version: str
    source_publication: str
    product_id: str
    start_date: str
    end_date: str
```

This planned model prevents cross-tenant, cross-policy, cross-definition, and
cross-publication reuse. A TTL limits age; it does not detect a correction or
authorization change, so versioned keys or explicit invalidation remain necessary.

## Federation and pushdown

A federated planner needs remote schema/type mappings, predicate semantics,
credentials, cost/cardinality estimates, capabilities, and limits. Push down only
operations whose semantics match, especially `NULL`, collation, time zones,
numeric precision, filters, and aggregates. Enforce scan/result/timeout bounds at
both coordinator and remote source.

Avoid federating production OLTP tables for routine heavy analytics. Replicate or
materialize when query load, availability coupling, correction, or reproducibility
cannot meet the contract.

## Lifecycle, consistency, identity, and time

A serving version is planned, built from pinned inputs, validated, published,
cached, superseded, drained, and expired. Distinguish source event time, source
frontier/snapshot, refresh start/end, publication time, cache creation, and expiry.
A multi-widget dashboard needs either one publication token or disclosure that
widgets may use different frontiers.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Partial refresh | Candidate counts/status and missing partitions | Keep prior version; rebuild candidate |
| Late older refresh wins | Frontier monotonicity/fencing | Reject stale publish; retry current plan |
| Cache leaks tenant/policy | Negative access tests/audit | Disable/purge cache, rotate policy version, investigate |
| Stale result beyond budget | Source-vs-serving frontier lag | Mark unavailable/stale; catch up or rebuild |
| Remote federation slowdown | Per-source latency/scan/queue | Cancel, shed, route to snapshot/materialization |
| Source schema/semantics drift | Contract and differential tests | Block refresh/query; compatible rollout or repair |
| Serving store loss | Health and restore/rebuild test | Rebuild from pinned curated source; verify frontier |

Recovery is complete when the source-to-serving version map is continuous,
reconciliation passes, cache/policy state is safe, and consumer latency/freshness
objectives recover.

## Security, privacy, and governance

Apply least privilege to source reads, refresh writes, serving reads, cache admin,
and federation credentials. Cache and materialized keys must include tenant and
policy scope. Push filters does not automatically enforce authorization; validate
policy at the authoritative boundary. Protect query text, parameters, remote
errors, statistics, cache contents, extracts, and logs. Propagate deletion and
policy changes to every serving copy and retained version.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Refresh | Empty/duplicate/late/delete/retry fixture | Correct version and reconciliation | Pending |
| Atomicity | Crash at candidate/publish boundaries | Old or complete new view only | Pending |
| Cache | Tenant/policy/version mutation matrix | No unsafe reuse; correct invalidation | Pending |
| Federation | Type/null/time/pushdown differential suite | Same semantics and bounded remote work | Pending |
| Load/fault | BI/API concurrency and remote loss | SLO or declared degradation | Pending |

Mocked refresh and cache tests do not prove real query isolation, network failure,
remote cancellation, cache eviction, or serving-store recovery.

## Debugging guide

Start with consumer/request ID, tenant/principal policy, semantic version, serving
version, source snapshot/frontier, cache key/hit, refresh run, and federated remote
query ID. Split queue, execution, network, and cache time. Inspect plans/pushdown,
remote scans, source load, refresh partitions, reconciliation, invalidations, and
recent schema/policy releases. Mitigate with a known certified version or bounded
feature disablement.

## Common pitfalls

### Pitfall: TTL as a correctness protocol

TTL bounds elapsed age only. It does not represent source completeness,
corrections, deletes, semantic changes, or policy revocation.

### Pitfall: materialized view without source version

Operators cannot prove freshness or reproduce discrepancies. Persist the pinned
source frontier/snapshot and definition version with every publication.

### Pitfall: federation as free integration

It couples query correctness and availability to remote systems and can overload
them. Bound pushdown, scans, concurrency, timeouts, cancellation, and ownership.

## Performance, capacity, and cost

Measure end-to-end and per-stage latency percentiles, QPS/concurrency, queue depth,
cache hit/miss/eviction, refresh duration/lag, rows/bytes scanned and returned,
remote pushdown, network/egress, write amplification, storage, and cost per consumer.
Capacity includes refresh and rebuild while foreground traffic continues.

## Compatibility, migration, backfill, and delivery

Version serving schemas and semantic definitions. Build a new projection beside
the old, backfill from a pinned source, catch up changes, differential-test,
canary consumers, cut over a stable route, drain caches, and retain rollback.
Federation migrations must handle mixed type/SQL semantics. Never remove the old
source history until the new serving copy is rebuildable and reconciled.

## Working example

- SQL/Python: planned materialized metric refresh, publication ledger, and versioned cache key
- Tests: planned freshness, retry, cache policy, federation semantics, load, and fault cases
- Infrastructure: no serving store, cache, or federation engine selected
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: actual refresh atomicity, cache behavior, pushdown, load, recovery, and cost

## Knowledge check

1. Select direct query, view, keyed projection, cache, or federation for three SLOs.
2. Explain why TTL does not prove data freshness.
3. Diagnose two dashboard widgets using incompatible publications.
4. Design a cache key that cannot leak tenant or policy-scoped results.
5. Plan a fault test for federation timeout and cancellation.
6. Design an atomic serving migration with backfill, catch-up, canary, and rollback.

## Key takeaways

- A serving layer is a derived SLO boundary, not a new source of truth.
- Source and semantic versions make freshness, correction, and reproduction explicit.
- Precomputation exchanges refresh/storage complexity for predictable reads.
- Federation exchanges copy management for runtime coupling and remote risk.

## Resources

- [PostgreSQL materialized views](https://www.postgresql.org/docs/current/rules-materializedviews.html) (reviewed 2026-09)
- [Trino connector documentation](https://trino.io/docs/current/connector.html) (reviewed 2026-09; federation example)
- [HTTP caching specification, RFC 9111](https://www.rfc-editor.org/rfc/rfc9111) (reviewed 2026-09; cache analogy and limits)

## Related topics

- [Storage and serving system selection](01-storage-and-serving-system-selection.md)
- [BI, semantic, and machine-learning consumer boundaries](08-bi-semantic-and-machine-learning-consumer-boundaries.md)

## Completion checklist

- [x] Serving, views, caches, federation, refresh, freshness, and isolation explained
- [x] Identity, time, failure, security, capacity, migration, operations, and evidence addressed
- [ ] Refresh, cache, federation, load, fault, recovery, and consumer evidence run
