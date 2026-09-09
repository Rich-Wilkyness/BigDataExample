# Storage and Serving System Selection

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Storage / Architecture / Serving / Platform  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A storage system is a bundle of guarantees and constraints: access patterns,
latency, consistency, transactions, indexing, retention, concurrency, recovery,
governance, and cost. Selection begins with those requirements and the dataset's
authority and grain. It does not begin with a product category.

This guide compares relational, analytical, key-value, document, wide-column,
search, time-series, and object storage. It covers workload placement and derived
serving copies, not installation or vendor feature matrices.

## Learning objectives

- Turn producer and consumer needs into a storage decision contract.
- Distinguish authoritative storage from analytical and serving projections.
- Compare system families by operations and guarantees rather than labels.
- Identify when one system is insufficient and how to bound derived copies.
- Design evidence that can invalidate a proposed choice.

## Prerequisites

- [OLTP, OLAP, batch, streaming, and serving](../01-big-data-and-data-engineering-foundations/04-oltp-olap-batch-streaming-and-serving.md)
- [Sources, sinks, authority, and derived data](../01-big-data-and-data-engineering-foundations/05-sources-sinks-authority-and-derived-data.md)
- [Requirements, grain, entities, and relationships](../05-data-modeling-and-business-semantics/01-requirements-grain-entities-and-relationships.md)

## Mental model and terminology

Choosing storage resembles choosing Room, a remote API, or an in-memory index for
an Android feature: the caller's operations and offline/consistency needs drive
the boundary. The analogy stops because analytical systems scan many records,
distribute execution, retain historical versions, and may separate metadata,
storage, and compute across teams and services.

| Term | Meaning in this guide |
| --- | --- |
| System of record | Authoritative system allowed to establish or change a fact |
| Serving copy | Derived representation optimized for a consumer access pattern |
| Access path | Key lookup, range scan, text search, aggregate scan, time window, or object read |
| Working set | Data and indexes actively needed to meet the latency objective |
| Polyglot persistence | Multiple storage systems used because their bounded roles differ |

## Requirements, scale assumptions, and invariants

Assume 3M events/day, 100M hot analytical rows, 100K products, 20 BI users,
500 requests/s bursts to a product-metric API, 15-minute analytical freshness,
and 200 ms p95 API latency. Before selection, record query shapes, result sizes,
read/write rates, concurrency, availability, consistency, retention, locality,
privacy, recovery objectives, skills, and total cost.

- One owner and source of truth is declared for each fact.
- Every derived copy records its source version/frontier and can be reconciled.
- A system selected for one access path is not assumed efficient for another.
- Resource and cardinality bounds exist for reads, writes, indexes, and tenants.
- Degradation is explicit when freshness, consistency, or availability cannot all hold.
- Deletion, backup, restore, migration, and exit paths are designed before adoption.

## Data flow, ownership, and trust boundaries

| Boundary | Contract and authority | Failure behavior | Trust |
| --- | --- | --- | --- |
| Source database/log | Authoritative business writes and stable identity | Preserve source; expose position or snapshot | Restricted source |
| Analytical storage | Versioned historical facts and dimensions | Rebuild/reconcile from source | Governed derived data |
| Serving projection | Bounded keys/queries plus source frontier | Serve declared stale version or fail closed | Consumer-facing |
| Search/index/cache | Replaceable acceleration structure | Bypass, rebuild, or degrade explicitly | Derived and least privilege |

## System-family decision model

| Requirement | Typical fit | Strength | Reconsider when |
| --- | --- | --- | --- |
| Multi-row business transactions and constraints | Relational OLTP | Integrity and transactional updates | Large historical scans dominate |
| Large scans, joins, aggregates, governed SQL | Analytical warehouse | Columnar execution and workload controls | Millisecond key serving dominates |
| Predictable lookup by primary key | Key-value | Low-latency horizontal access | Ad hoc predicates/joins are required |
| Aggregate-oriented variable records | Document | Document locality and schema flexibility | Cross-document integrity dominates |
| Huge sparse keyed ranges/time order | Wide-column | Partitioned range access and write scale | Arbitrary analytics are primary |
| Ranked text/filter retrieval | Search index | Inverted indexes and relevance | It would become sole business authority |
| Recent time-window aggregates/retention | Time-series | Time partitioning and rollups | General joins and history modeling dominate |
| Cheap durable files and multi-engine scans | Object storage | Scale, lifecycle, format portability | Per-row mutation/low-latency listing is assumed |

Categories overlap. Validate the exact candidate; a label does not guarantee a
transaction level, index type, SQL feature, durability target, or latency.

### Selection record

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Workload:
    operation: str
    p95_ms: int
    peak_ops_s: int
    result_bytes: int
    consistency: str
    freshness_s: int

def violates(candidate: dict[str, int | set[str]], workload: Workload) -> list[str]:
    # This is a planned contract checker, not a capacity benchmark.
    failures: list[str] = []
    if workload.operation not in candidate["operations"]:
        failures.append("unsupported operation")
    if workload.p95_ms < candidate["measured_p95_ms"]:
        failures.append("latency objective missed")
    if workload.consistency not in candidate["consistency"]:
        failures.append("consistency contract missed")
    return failures
```

The caller owns requirement truth; benchmark results own measured candidate
behavior. Never fill `measured_p95_ms` from marketing limits.

## Architecture and dependency direction

Prefer a narrow authoritative write path and multiple rebuildable read paths:

```text
business command -> system of record -> durable change boundary
                                           |
                       +-------------------+------------------+
                       v                   v                  v
                 warehouse/lake      key serving        search index
```

Dual writes from application code create an atomicity gap unless a shared
transaction truly covers both systems. Publish change durably, then materialize
idempotently. A serving copy never silently becomes authority merely because it
is faster.

## Lifecycle, consistency, identity, and time

Define business keys separately from storage keys. Sharding prefixes, synthetic
IDs, and document paths are physical concerns unless exposed by contract.
Consistency is per operation: a strong key read does not make search results or
cross-partition analytics current. Record source event time, ingestion time,
materialization frontier, and serving refresh time.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Hot key/partition | Per-key/partition load and tail latency | Split keyspace, cache bounded reads, or redesign key |
| Derived copy misses changes | Frontier gaps and reconciliation | Stop claiming freshness; replay/rebuild |
| Unknown write outcome | Operation identity and read-after-timeout | Resolve by idempotency key, not blind duplicate write |
| Index/cache unavailable | Dependency health and error budget | Bypass or degrade under a declared policy |
| Schema/query mismatch | Contract test and rejected request | Roll forward compatible reader or restore prior route |
| Capacity exhausted | Queue depth, throttles, memory/disk | Admit, shed, scale, and protect authority |

Recovery completes when authoritative writes are intact, derived frontiers are
continuous, reconciliation matches, and latency/correctness objectives recover.

## Security, privacy, and governance

Minimize copies because each expands access, retention, breach, deletion, and
audit scope. Separate human, workload, and administrative identities. Test tenant
keys and row/document filters negatively. Encrypt transport and storage, rotate
credentials, sanitize query logs, and propagate classification and deletion to
indexes, caches, exports, backups, and search snippets.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Requirement gate | Workload contract table | Missing owner/SLO/access path rejected | Pending |
| Correctness | Duplicate, null, stale, delete fixture | Candidate preserves declared invariants | Pending |
| Benchmark | Realistic cardinality/skew/concurrency | Meets latency and throughput with headroom | Pending |
| Fault | Timeout, overload, dependency loss | Bounded degradation and convergence | Pending |
| Recovery | Backup plus derived rebuild | RPO/RTO and reconciliation pass | Pending |

Fixtures and test doubles can validate routing logic, not a real system's
durability, concurrency, scale, or cost.

## Debugging guide

Start with the affected operation and consumer, then identify the authoritative
record and each derived frontier. Inspect request IDs, keys, partitions, query
plans, cache hit/miss, replication/refresh lag, throttles, saturation, and recent
schema/configuration changes. Mitigate by isolating overload or routing to a known
version. Do not repair authority from an unverified derived copy.

## Common pitfalls

### Pitfall: one database for every workload

Mixed workloads contend and force incompatible layouts. Isolate them only when
the extra copy has explicit ownership, freshness, reconciliation, and lifecycle.

### Pitfall: architecture by feature checklist

Feature presence says little about behavior at the required scale and failure
boundary. Weight mandatory guarantees first, then test a representative workload.

### Pitfall: premature polyglot persistence

Every new system adds change capture, security, operations, recovery, expertise,
and cost. Add one only when evidence shows a material unmet requirement.

## Performance, capacity, and cost

Estimate storage including replicas, indexes, versions, staging, and backups;
compute including peaks, retries, maintenance, and recovery; network including
replication and egress. Measure p50/p95/p99 latency, throughput, queueing,
amplification, cache hit rate, partition skew, and cost per workload. Averages hide
hot tenants and concurrency.

## Compatibility, migration, and delivery

Use expand/migrate/contract: create the new schema/system, backfill a closed
frontier, consume changes after it, validate shadow reads, cut over gradually,
retain rollback, and reconcile. Avoid indefinite dual writes. Exit cost includes
data export, semantics, security policies, operational history, and consumers.

## Working example

- Python: planned workload-contract checker
- Data/tests: planned requirements, skew, duplicate, deletion, and failure cases
- Infrastructure: candidate systems deliberately unselected
- Try it: no command yet
- Evidence: documentation and decision-table review only
- Remaining risk: actual semantics, latency, concurrency, durability, operations, and cost

## Knowledge check

1. Choose authority and serving systems for product writes, BI scans, API lookups, and text search.
2. Explain why a low-latency key-value projection should not own product truth.
3. Diagnose a fresh dashboard whose search index skipped one change partition.
4. Estimate storage amplification for source, analytical copy, index, versions, and backup.
5. Design a benchmark that includes skew, concurrency, failure, and recovery.
6. Propose a reversible migration without unsafe application dual writes.

## Key takeaways

- Select from workload and guarantees, not product category alone.
- Authority, analytical history, and serving acceleration are different roles.
- Derived copies require identity, frontier, reconciliation, deletion, and rebuild contracts.
- Tail latency, skew, recovery, governance, and total cost decide production fit.

## Resources

- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09)
- [Amazon Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) (reviewed 2026-09)
- [Google Bigtable paper](https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/) (reviewed 2026-09)

## Related topics

- [Data warehouse architecture and workload management](02-data-warehouse-architecture-and-workload-management.md)
- [Serving layers, materialized views, caches, and federation](07-serving-layers-materialized-views-caches-and-federation.md)

## Completion checklist

- [x] Workload-first mental model, requirements, authority, and system families explained
- [x] Identity, consistency, time, security, failure, capacity, migration, and evidence addressed
- [ ] Contract checker, candidate benchmark, fault, restore, and reconciliation evidence run
