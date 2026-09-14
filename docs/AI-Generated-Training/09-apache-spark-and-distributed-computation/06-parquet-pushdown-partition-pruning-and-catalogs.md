# Parquet, Pushdown, Partition Pruning, and Catalogs

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: PySpark / Spark SQL / Parquet / Storage / Catalogs  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Efficient distributed computation begins by avoiding unnecessary reads. Parquet
stores typed columns and per-file/row-group metadata that engines can use for
column pruning and predicate pushdown. A partitioned table can avoid discovering
or scanning unrelated storage partitions. A catalog gives logical names, schemas,
locations, statistics, and sometimes snapshot/transaction semantics depending on
the catalog and table provider.

These are distinct guarantees. A filter appearing in source code does not prove
files or row groups were skipped. A directory layout is not a transactional table.
A catalog entry is not automatically authoritative, current, or compatible with
the files it names.

## Learning objectives

- Distinguish projection pruning, predicate pushdown, data skipping, and partition pruning.
- Explain Parquet schemas, statistics, row groups, nullability, and schema merging.
- Design bounded-cardinality storage partitions from consumer predicates.
- Assign ownership among files, table metadata, catalog, and published generations.
- Prove read efficiency with plans and scan metrics while preserving correctness.

## Prerequisites

- [Data Storage, Files, and Serialization](../04-data-storage-files-and-serialization/README.md)
- [DataFrames, Spark SQL, schemas, and types](02-dataframes-spark-sql-schemas-and-types.md)
- [Partitions, shuffles, parallelism, and output files](04-partitions-shuffles-parallelism-and-output-files.md)

## Mental model and terminology

SQLite can use an index to avoid visiting every row, while selecting only needed
columns reduces materialized data. Parquet metadata and partition pruning serve
a related read-avoidance goal. The analogy stops because a distributed file table
may require listing many objects, statistics exist per row group/file rather than
a centralized B-tree, and catalog/file updates may not share one transaction.

| Term | Meaning in this guide |
| --- | --- |
| Column pruning | Reading only referenced columns where the source supports it |
| Predicate pushdown | Passing eligible filters to the data source reader |
| Data skipping | Avoiding files/row groups using metadata such as min/max statistics |
| Partition pruning | Avoiding storage partitions using predicates on partition fields |
| Partition discovery | Inferring partition columns/values from a directory layout |
| Catalog | Metadata service mapping logical relations to schema, location, properties, and possibly snapshots |
| Schema merge | Reading compatible but differing file schemas as a combined schema; costly and not a governance strategy |
| Base path | Root used to interpret partition directories consistently |

## Requirements, scale assumptions, and invariants

The curated dataset is commonly queried by `event_date_utc` and sometimes tenant.
At 3 million events/day, daily partitioning has bounded growth and selective date
filters. Partitioning directly by product or event ID would create excessive
directories/files. Actual query logs and table-format capabilities must validate
the design.

- The catalog/table snapshot or generation manifest identifies one complete authoritative dataset version.
- Every file in that version has a compatible schema and classification.
- Partition values have one encoding, timezone, and null policy.
- Consumers obtain the same rows whether pruning is enabled or disabled.
- Optimization failure may increase cost/latency but never silently change results.
- Schema evolution follows explicit compatibility and backfill rules; merging arbitrary files is not the normal read path.
- Deletion, retention, encryption, and access policy cover data files, metadata, manifests, and orphan cleanup.

## Efficient read layers

```python
from pyspark.sql import functions as F

events = (
    spark.read.schema(CURATED_EVENT_SCHEMA)
         .parquet(curated_root)
         .where(F.col("event_date_utc") == F.lit(target_date))
         .select("tenant_id", "product_id", "event_type", "revenue_usd")
)

events.explain(mode="formatted")
```

Review the scan for selected columns, partition filters, pushed filters, file count,
bytes read, and output rows. A date predicate can prune directory partitions when
the reader recognizes the partition field. A revenue predicate might be pushed
and use Parquet statistics, but support depends on expression, data source, schema,
and version. Treat plan/metric inspection as evidence, not the presence of `.where`.

```sql
-- Spark SQL. Ordering is unspecified because no ORDER BY is present.
SELECT tenant_id, product_id, SUM(revenue_usd) AS revenue_usd
FROM curated_events
WHERE event_date_utc >= DATE '2026-09-01'
  AND event_date_utc <  DATE '2026-10-01'
GROUP BY tenant_id, product_id;
```

## Parquet contract

Parquet is columnar and preserves schema information, but Spark documents that
columns are converted to nullable on read for compatibility. Business
requiredness must be validated separately. Statistics can skip ranges only when
they exist, are trustworthy for the type/writer, and the predicate is eligible.
Encryption, dictionary encoding, compression, page/row-group layout, and nested
columns affect performance and interoperability.

Schema merging is disabled by default in Spark 4.2 because discovering and merging
schemas is expensive. Enabling `mergeSchema` may make compatible historical files
readable, but it can hide unmanaged schema drift and increase planning/listing
cost. Prefer a governed table schema, compatible writer rollout, contract tests,
and explicit migration/backfill.

## Storage partition design

| Requirement | Prefer | Avoid |
| --- | --- | --- |
| Most reads select date ranges | Date partition/transform at appropriate granularity | Scanning all history |
| Strong tenant isolation and bounded tenant count | Possibly tenant + date after evidence | Millions of direct-ID directories |
| High-cardinality product filters | Clustering/sorting/index metadata if supported | Directory per product |
| Late corrections to days | Independently replaceable/versioned date scopes | In-place mutation without generation identity |
| Small daily data | Coarser time partition or compaction | Thousands of tiny daily files |

Partition directory values are metadata and can conflict with same-named columns
inside files. Establish one ownership rule. Do not derive dates in mixed local
time zones. A Hive-style path like `event_date_utc=2026-09-07/` is a convention,
not proof of complete/atomic publication.

## Catalog and authority boundaries

| Boundary | Contract/authority | Failure behavior |
| --- | --- | --- |
| Candidate Parquet files | Immutable run-scoped derived data; not authoritative | Validate or expire; never expose as current |
| Generation manifest/table snapshot | Exact file/partition set and schema version | Publish atomically or retain prior version |
| Catalog name | Consumer discovery and current-version reference | Stale/unavailable catalog blocks or serves declared cached behavior |
| File/object store | Durable bytes under storage guarantees | Missing/corrupt object fails reconciliation |
| Spark reader | Interprets provider/options/schema into rows | Fail incompatible input; do not silently mix versions |

Catalog capabilities vary. A session catalog over directories, a Hive metastore,
and a transactional table catalog have different concurrency and snapshot
guarantees. Document the selected provider instead of attributing generic
transactions to “Spark.”

## Failure model and recovery

| Failure | Detection | Containment/recovery | Consumer behavior |
| --- | --- | --- | --- |
| Missing partition filter | Plan/scan bytes exceed budget | Fix predicate/type/layout; rerun | Correct but delayed/costly |
| Stale catalog metadata | Missing/new files or stale schema/statistics | Refresh/repair under provider procedure | Fail closed or documented stale view |
| Mixed incompatible schemas | Read/analysis error or wrong coercion | Isolate generation; migrate/backfill | Prior version remains |
| Corrupt/truncated Parquet | Read/checksum/record failure | Quarantine file/scope; rebuild from source | No partial publish |
| Partial directory write | Manifest/file inventory mismatch | Abandon candidate; never register current | Prior generation remains |
| Too many small files | Listing/planning latency, many short tasks | Compact into new certified generation | Reads continue until cutover |
| Deleted data still in cache/copies | Erasure audit mismatch | Invalidate caches, rewrite snapshots, expire files/logs | Restrict access during repair |

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Round-trip contract | Nested/null/decimal/timestamp fixture / local Spark | Write/read explicit Parquet schema | Declared values and schema preserved | Pending |
| Pruning proof | Multi-date fixture | Compare filtered/unfiltered plans and scan metrics | Only target partitions/files read where supported | Pending |
| Pushdown proof | Selective supported/unsupported predicates | Inspect plan and bytes/rows | Eligibility and residual filters explained | Pending |
| Schema evolution | Compatible/incompatible file generations | Read under migration rules | Compatible succeeds; incompatible fails closed | Pending |
| Catalog/publication | Fault-injected candidate registration | Interrupt before/after commit | Exactly prior or new complete generation visible | Pending |

## Debugging guide

Capture the table identifier/provider, catalog namespace, resolved location or
snapshot/generation, reader options, exact schema, input files, partition filters,
pushed filters, scan files/bytes/rows, and relevant statistics. Compare a direct
path read only as a controlled diagnostic: it can bypass catalog authority and
must not become an accidental production workaround. Reconcile manifest objects
against storage inventory before repair.

## Common pitfalls

### Pitfall: assuming a filter proves pruning

Inspect the physical scan and runtime file/byte metrics. A cast, function, type
mismatch, absent metadata, or unsupported connector expression can leave a
residual filter after a full scan.

### Pitfall: enabling schema merge globally

Global merging adds discovery/planning cost and can normalize uncontrolled drift.
Use explicit schemas and governed evolution; enable merging only for a bounded,
tested migration need.

### Pitfall: treating catalog metadata and files as one transaction

Capabilities depend on the provider/table format. Use its supported commit and
snapshot contract or a generation manifest; test interruption at each boundary.

## Security, privacy, performance, and cost

Column pruning reduces bytes processed but is not access control: a job identity
that can read the file may read all columns. Apply storage/catalog authorization,
masking/policy enforcement, encryption, and audited access. Partition paths and
statistics can leak sensitive values. Budget object listings, files opened, bytes
scanned, planning time, task count, decompression CPU, and recurring storage for
old snapshots/orphans.

## Compatibility, migration, backfill, and delivery

Use expand/migrate/contract: add compatible fields and readers, write a shadow
generation, backfill bounded history, validate schema/rows/metrics/pruning, atomically
move the catalog/snapshot reference, then retire old fields/files after consumer
and rollback windows. Mixed-version readers and writers need explicit tests.
Never overwrite the only good generation during a backfill.

## Working example

- Parquet fixtures, PySpark read/write tests, catalog integration: Planned
- Expected result: exact round trip, demonstrated pruning, compatible evolution, atomic generation visibility
- Scale represented: none yet
- Remaining risk: real connector metadata, object-store consistency, catalog concurrency, file statistics, encryption, and production queries

## Knowledge check

1. Distinguish partition pruning, predicate pushdown, data skipping, and column pruning.
2. Explain why a non-null business field can appear nullable after Parquet read.
3. Choose a storage partition strategy for daily data with frequent month-range queries.
4. Diagnose a date-filtered query that scans all files.
5. Design a schema evolution that preserves rollback.
6. State which transactional guarantees belong to the selected catalog/table provider rather than Spark itself.

## Key takeaways

- Efficient reads require aligned predicates, storage layout, metadata, and measured scan behavior.
- Parquet schema metadata does not replace business validation or governance.
- Execution partitions and storage partitions solve different problems.
- Catalog and table-provider guarantees must be named precisely.
- Publish versioned, validated file sets rather than exposing partially written directories.

## Resources

- [Spark Parquet data source](https://spark.apache.org/docs/4.2.0/sql-data-sources-parquet.html) (reviewed 2026-09)
- [Spark SQL data sources](https://spark.apache.org/docs/4.2.0/sql-data-sources.html) (reviewed 2026-09)
- [PySpark SparkSession catalog API](https://spark.apache.org/docs/4.2.0/api/python/reference/pyspark.sql/api/pyspark.sql.SparkSession.catalog.html) (reviewed 2026-09)
- [Apache Parquet format](https://parquet.apache.org/docs/file-format/) (reviewed 2026-09)

## Related topics

- [Caching, memory, serialization, and Python UDFs](07-caching-memory-serialization-and-python-udfs.md)
- [Warehouses, lakes, lakehouses, and serving systems inventory](../COVERAGE.md#11-warehouses-lakes-lakehouses-and-serving-systems)

## Completion checklist

- [x] Parquet, pruning, pushdown, skipping, partitioning, schema merge, catalogs, and authority explained
- [x] Failure, security, quality, cost, publication, and migration addressed
- [ ] Round-trip, pruning, pushdown, evolution, and publication evidence run
