# Data Warehouse Architecture and Workload Management

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: Warehouse / SQL / Storage / Platform  
> Data scale: Local SQL design; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A data warehouse is a governed analytical system that stores modeled history and
executes many-record SQL workloads. Its contract includes atomic publication,
isolation, workload admission, predictable freshness, security, and recovery—not
only columnar storage or SQL syntax.

This guide covers shared-nothing and separated storage/compute mental models,
loading, concurrency, elasticity, and governed SQL. Vendor administration and BI
modeling details are outside scope.

## Learning objectives

- Trace a warehouse query through control, compute, storage, and result boundaries.
- Design idempotent staged loads and atomic consumer publication.
- Separate transactional isolation from workload isolation.
- Define queues, quotas, priorities, timeouts, and elasticity from SLOs.
- Diagnose freshness and query-latency failures using plans and workload signals.

## Prerequisites

- [Dimensional modeling](../05-data-modeling-and-business-semantics/03-dimensional-modeling-facts-dimensions-and-stars.md)
- [DDL, constraints, transactions, and concurrent change](../03-sql-and-analytical-querying/07-ddl-constraints-transactions-and-concurrent-change.md)
- [Query plans, indexes, statistics, and optimization](../03-sql-and-analytical-querying/08-query-plans-indexes-statistics-and-optimization.md)
- [Storage and serving system selection](01-storage-and-serving-system-selection.md)

## Mental model and terminology

```text
SQL client -> auth/catalog/optimizer -> admitted compute work
                                          |
                              scan/join/aggregate/spill
                                          |
                                  warehouse storage
                                          |
                            result + query/run identifiers
```

A warehouse resembles Room plus a query executor only at the relational surface.
The analogy stops because a warehouse coordinates distributed scans, shuffles,
elastic workers, queues, shared storage, and concurrent organizational workloads.

| Term | Meaning in this guide |
| --- | --- |
| Virtual warehouse/compute pool | Isolated or logically allocated compute for admitted work |
| Workload management | Admission, queueing, priority, quota, timeout, and resource policy |
| Transaction isolation | Which concurrent database states an operation may observe |
| Workload isolation | How one workload's resource use affects another |
| Certified dataset | Published version that passed owner-defined quality and governance gates |

## Requirements, scale assumptions, and invariants

Assume a 3 GiB/day fact load, 100M hot rows, 20 interactive readers, four scheduled
transforms, 500 ms p95 for selective dashboards, 30 seconds for bounded aggregate
queries, and a daily certified version by 02:00 UTC. Set separate budgets for
ingestion, transformation, BI, exploration, maintenance, and recovery.

- Consumers see the prior certified version or the complete new version, never a partial load.
- A `load_id` and source frontier make retries idempotent and auditable.
- Accepted plus rejected plus deduplicated inputs reconcile to observed source input.
- Interactive work cannot consume capacity reserved for publication and recovery.
- Query results identify data and semantic versions.
- Scaling and suspension never replace correctness, cancellation, or cost controls.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Owner | Commit/failure behavior |
| --- | --- | --- | --- |
| Landing/stage | Immutable files, checksums, source frontier | Ingestion owner | Quarantine or reject before target mutation |
| Warehouse staging | Typed rows keyed by `load_id` | Pipeline owner | Retry/replace isolated load |
| Curated facts/dimensions | Declared grain and model version | Dataset owner | Transactional merge or generation swap |
| Certified schema/view | Stable names and semantic contract | Domain/metric owner | Expose only passed publication |
| Workload pools | Priority, concurrency, timeout, quota | Platform owner | Queue, throttle, cancel, or isolate |

## Loading and atomic publication

```sql
-- Generic SQL sketch; MERGE and transaction semantics vary by engine.
BEGIN;

INSERT INTO fact_product_event (tenant_id, event_id, event_time, product_id, load_id)
SELECT tenant_id, event_id, event_time, product_id, :load_id
FROM staged_product_event AS s
WHERE s.disposition = 'accepted'
  AND NOT EXISTS (
    SELECT 1
    FROM fact_product_event AS f
    WHERE f.tenant_id = s.tenant_id AND f.event_id = s.event_id
  );

INSERT INTO dataset_publication(dataset_name, publication_id, source_frontier, published_at)
VALUES ('fact_product_event', :publication_id, :source_frontier, CURRENT_TIMESTAMP);

COMMIT;
```

The fact grain is one accepted logical event. `NULL` identity is rejected before
loading. The query is only rerunnable if concurrent writers cannot insert the same
identity unchecked; use a supported uniqueness or merge/fencing mechanism and test
the engine's actual isolation. Large loads may instead build a complete generation
and atomically move a metadata/view pointer.

### Load lifecycle

```text
registered -> validating -> staged -> transforming -> quality_passed
     -> publishing -> published
              \-> failed/quarantined -> repaired -> retry
```

Persist transitions independently of worker memory. An unknown commit outcome is
resolved by `load_id`/`publication_id` lookup before retry.

## Storage and compute architecture

In shared-nothing systems, workers often own or cache partitions and moving data
has rebalance cost. With separated storage and compute, multiple pools can read
common durable storage, but metadata, network, cache warming, request limits, and
egress still couple them. Neither model creates infinite instantaneous elasticity.

Distribution, clustering, partitioning, sort order, statistics, materialization,
and compression shape pruning and movement. Logical SQL remains portable only
until physical features or dialect semantics become part of the workload.

## Concurrency and workload management

| Class | Priority and bound | Degradation policy |
| --- | --- | --- |
| Certified publication | Reserved capacity; deadline-driven | Delay exploration first; alert freshness risk |
| Interactive BI | Short queue, concurrency cap, scan/result bound | Cancel runaway query; serve prior certified result |
| Exploration | Lower priority, bytes/time quota | Queue or reject with actionable reason |
| Backfill/maintenance | Explicit window and resource ceiling | Pause/checkpoint before harming foreground work |
| Recovery | Reserved headroom and tested procedure | Suspend nonessential classes |

Transactional isolation prevents incompatible data states; workload isolation
prevents resource starvation. Both are required. Put deadlines on queued plus
running time and propagate cancellation to workers.

## Consistency, identity, and time

Define whether one query sees a statement snapshot or transaction snapshot and
whether separate dashboard queries share a publication. Warehouse freshness is
the age of the newest complete source frontier, not `CURRENT_TIMESTAMP` at query
time. Use UTC instants and explicit business calendars. Surrogate warehouse keys
do not replace source business identity or deduplication keys.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Partial/stale staged load | Counts, checksums, frontier gap | Discard isolated stage; preserve certified target |
| Writer dies during publish | Transaction/publication ledger | Resolve outcome, then retry idempotently |
| Runaway query | Scan, spill, elapsed, queue metrics | Cancel; tune or constrain before readmission |
| Workload starvation | Queue age by class/tenant | Enforce reservations, weights, and concurrency limits |
| Compute pool loss | Query/job state and health | Retry from durable stage; do not duplicate publish |
| Bad model release | Reconciliation/consumer canary | Restore prior view/generation or forward repair |

Recovery is proven by source-to-target reconciliation, one visible publication,
restored queue health, and consumer queries against the intended semantic version.

## Security, privacy, and governance

Separate raw, staging, curated, certified, and administrative privileges. Use
least-privilege workload identities, row/column policies where required, protected
staging, and audited changes. Parameterize queries; prevent sensitive values from
query text, tags, plans, result caches, history, exports, and logs. Resource groups
also limit abuse and noisy-neighbor denial of service.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Load contract | Empty, duplicate, invalid, retry fixture | Stable fact set and reconciliation | Pending |
| Transaction | Crash before/during/after publish | Old or complete new version only | Pending |
| Concurrency | Two writers and mixed readers | Declared isolation; no duplicate identity | Pending |
| Workload | Interactive plus backfill/load | SLO and class isolation within budget | Pending |
| Recovery | Compute loss and bad release | Convergence and rollback/repair | Pending |

Generic SQL review does not prove any engine's `MERGE`, constraint, transaction,
elasticity, or workload-management behavior.

## Debugging guide

Start with consumer, query ID, workload class, dataset publication, and source
frontier. Inspect queue and execution time separately; scan bytes, partitions,
statistics, join cardinality, shuffle/spill, memory, cache state, locks/conflicts,
load ledger, quality results, and recent DDL/configuration. Preserve failed stage
metadata and safely sampled rejected rows. Validate recovery with reconciliation,
not a green query alone.

## Common pitfalls

### Pitfall: direct append to consumer tables

Readers observe mixed generations and retries duplicate data. Stage, validate,
then use a tested transaction or atomic generation pointer.

### Pitfall: scaling instead of admission control

Unbounded concurrency can increase queueing, spill, and cost faster than capacity.
Bound requests and protect critical classes before adding compute.

### Pitfall: treating successful SQL as certified data

Execution success does not prove completeness, uniqueness, semantic correctness,
or source continuity. Publication follows quality and reconciliation gates.

## Performance, capacity, and cost

Measure queue wait, planning, execution, scan/return bytes, pruning, cache hit,
shuffle, spill, slots/workers, concurrency, load throughput, credits/currency, and
recovery capacity. For a 30-minute recovery reserve, a failed 45-minute load must
not require more than the remaining window to rerun. Benchmark cold and warm
caches and realistic tenant skew.

## Compatibility, migration, backfill, and delivery

Use expand/migrate/contract for schemas and semantic views. Backfill into an
isolated generation, consume incremental change beyond its frontier, compare old
and new metrics, canary consumers, atomically redirect stable names, and retain a
bounded rollback window. Destructive column/type changes and expired source data
may make rollback impossible; state that before deployment.

## Working example

- SQL: planned staged fact load, reconciliation, publication ledger, and stable view
- Tests/data: planned duplicate, invalid, crash-point, concurrency, and skew fixtures
- Infrastructure: no warehouse selected
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: actual dialect, transactions, plans, concurrency, scale, isolation, and cost

## Knowledge check

1. Trace a staged load and identify its only consumer-visible commit.
2. Explain the difference between transaction and workload isolation.
3. Diagnose a dashboard that is fast but uses a partial publication.
4. Design queues and quotas for BI, publication, exploration, and recovery.
5. Predict how stale statistics or a hot tenant changes a join plan and tail latency.
6. Design a backfill, canary, cutover, reconciliation, and rollback sequence.

## Key takeaways

- A warehouse combines governed analytical state with execution and workload contracts.
- Staging plus atomic publication keeps retries and partial failure from consumers.
- Transaction isolation and workload isolation solve different problems.
- Elasticity needs admission, cancellation, observability, recovery headroom, and cost bounds.

## Resources

- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09)
- [BigQuery introduction to workload management](https://docs.cloud.google.com/bigquery/docs/reservations-intro) (reviewed 2026-09; product example)
- [Snowflake virtual warehouses](https://docs.snowflake.com/en/user-guide/warehouses) (reviewed 2026-09; product example)

## Related topics

- [Storage and serving system selection](01-storage-and-serving-system-selection.md)
- [Data lakes, zones, and object storage](03-data-lakes-zones-and-object-storage.md)

## Completion checklist

- [x] Warehouse architecture, loading, publication, isolation, workloads, and governance explained
- [x] Identity, time, failure, security, capacity, compatibility, and evidence addressed
- [ ] Real-engine load, transaction, concurrency, workload, fault, and cost evidence run
