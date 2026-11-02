# Week 7 Wednesday — Declarative Pipelines, Data Quality, and Governance

> Level: Intermediate
> Prerequisites: [Tuesday's architecture, Spark, Delta, and Unity Catalog](2_Tue_Azure_Adv.md)
> Practical companion: [Wednesday Lakeflow steps](3.1-wed-steps.md)
> Evidence: Conceptual guide and reconstructed examples; no pipeline executed for this revision
> Primary documentation reviewed: 2026-10-22

## Overview and learning objectives

A notebook can read Bronze, write Silver, then write Gold. As dependencies grow, someone must maintain execution order, refresh behavior, state, and quality reporting. A declarative pipeline describes datasets and their dependencies so the platform can plan and manage their updates.

After this lesson, you should be able to distinguish notebooks, declarative pipelines, and Jobs; explain streaming tables and materialized views; select an expectation policy; describe Auto Loader's role; and reason about schema, quality, and governance during a refresh.

## 1. Mental model: describe datasets and dependencies

```text
Source JSON files
       ↓ Auto Loader discovers new files
Bronze streaming table
       ↓ parse station arrays, cast, validate
Silver materialized view
       ↓ define an hourly reporting convention
Gold materialized view
```

A **declarative definition** describes what a dataset contains. The engine derives dependencies by inspecting reads of upstream datasets. You still own the definitions, data contracts, permissions, and handling of problematic input. Declaring a table does not guarantee correct business logic.

The original name **Delta Live Tables (DLT)** appears in older tutorials and the captured lecture. **Lakeflow Spark Declarative Pipelines** is its newer product naming; current documentation also uses **Lakeflow pipelines**. Lakeflow Jobs is the separate workflow orchestration capability. “Lakeflow” alone can refer to a broader product family.

| Tool | What you author | What manages execution |
| --- | --- | --- |
| Interactive notebook | Cells and explicit read/write operations | You and the attached compute session |
| Declarative pipeline | Dataset definitions, dependencies, expectations | Pipeline engine |
| Lakeflow Job | Tasks, dependencies, schedules, retry behavior | Job scheduler |

A notebook can contain pipeline definitions, but those definitions must be evaluated in a configured pipeline context. They are not an ordinary sequence of notebook writes. A Job can orchestrate notebooks and pipeline updates together.

## 2. Python decorators and the `dp` API

A Python **decorator** adds behavior or metadata to a function. `@dp.table` registers a dataset definition, and the decorated function returns a Spark DataFrame describing that dataset. Returning a streaming DataFrame defines streaming-table behavior; use `@dp.materialized_view` to express batch materialized results clearly.

The current import is `from pyspark import pipelines as dp`. Older examples import `dlt`. Read older code with that naming history in mind; do not mechanically mix APIs or assume every Databricks extension exists in open-source Spark.

Pipeline definitions may be evaluated multiple times during planning and execution. Keep the functions focused on returning DataFrames. Avoid manual table writes, starting streams, API calls, driver-side collection, and other side effects inside definitions. A pipeline manages publishing and streaming state for its datasets. See [Python pipeline development](https://learn.microsoft.com/en-us/azure/databricks/ldp/developer/python-dev).

## 3. Tables, views, and materialization

| Object | Persisted result? | How it changes |
| --- | --- | --- |
| Session temporary view | No independent persisted result | Query evaluates its definition; registration belongs to the session |
| Persistent SQL view | Definition persists, result normally does not | Queries evaluate the saved definition |
| Materialized view | Yes | Refresh recomputes or incrementally maintains results where supported |
| Streaming table | Yes | Streaming ingestion/processing updates persistent table state |

“View” does not always mean session-only: a persistent view's definition survives the session. **Materialization** means storing the computed result so reads can use it without computing the whole definition each time. A refresh still consumes resources, and supported incremental maintenance depends on the query and platform.

In this week's example, Bronze incrementally ingests files. Silver and Gold are materialized results using batch read semantics over upstream tables. This is a deliberate reconstruction choice: the capture names those layers but does not preserve the exact instructor definitions.

## 4. Auto Loader and processing state

Auto Loader is Databricks' incremental file-ingestion capability, selected with `.format("cloudFiles")`. The file encoding remains a separate option, such as `cloudFiles.format = json`. It tracks file-processing progress through persistent state so subsequent updates can discover and process new files.

Auto Loader does not copy an S3 folder into Azure in place of Tuesday's ADF workflow. Here, ADF lands files in ADLS; Auto Loader ingests those landed files into a Delta table. ADF is a broader integration/orchestration service, while Auto Loader is a file-ingestion mechanism within Databricks.

A file processed once can contain duplicate station observations, and different files can repeat the same observations. File tracking therefore does not replace Silver business-key validation or deduplication. Pipeline-managed Auto Loader handles schema/checkpoint state differently from a manually configured notebook stream; Thursday covers the explicit notebook options.

## 5. Quality expectations are policies

An **expectation** names a Boolean condition and an action when a record violates it.

| Decorator | Invalid-record behavior | Suitable use |
| --- | --- | --- |
| `@dp.expect` | Retain invalid records and report violations | Observe quality before deciding enforcement |
| `@dp.expect_or_drop` | Remove invalid records from that dataset and report violations | A documented acceptance rule |
| `@dp.expect_or_fail` | Fail the affected update when the rule is violated | A condition that must block publication |

Use explicit NULL checks: `num_bikes_available >= 0` alone is not a full contract for missing values. A nonnegative integer can still be stale or wrong. Cross-record uniqueness, temporal consistency, and completeness usually need additional validation beyond row-level predicates.

For station observations, the intended Silver key is `(station_id, snapshot_timestamp)`. Exact duplicates may be removed, but conflicting values at that key require a defined resolution or rejection policy. Retain landing/Bronze evidence and reconcile accepted/rejected/duplicate counts before deciding a refresh is sound.

Dropping records changes coverage. A Gold total over fewer reporting stations can fall even if actual bike availability has not. Display coverage alongside aggregates. See [Pipeline expectations](https://learn.microsoft.com/en-us/azure/databricks/ldp/expectations).

## 6. Schema describes structure, not all business meaning

`StructType` describes a collection of fields. Each `StructField` names a field, its Spark type, and its nullability. `ArrayType` represents repeated elements. A snapshot containing `data.stations` is a nested struct containing an array of station structs.

```text
snapshot: struct
  last_updated: epoch seconds
  data: struct
    stations: array<struct<station_id, num_bikes_available, ...>>
```

An explicit schema makes parsing assumptions visible. Inferred schemas can help explore data but require deliberate handling of new/missing columns and incompatible values. A nullable flag is not a complete business-quality policy. Casts, required-value expectations, and rescued-data inspection make failures visible.

Avro is one serialization format with its own schema machinery. Databricks schema evolution is not automatically “using Avro”; Auto Loader schema tracking and Delta schema enforcement are separate features.

## 7. Triggered versus continuous updates

A **triggered** pipeline processes available data and finishes. A **continuous** pipeline keeps processing new data according to its update behavior. These modes belong to the pipeline configuration and are distinct from a manually started notebook stream's trigger API.

Triggered updates fit the classroom demonstration and periodic workloads. Continuous processing can improve freshness but changes operational and cost requirements. Serverless reduces infrastructure management; it does not remove the need to monitor failures or define correctness.

## 8. Failure model and production considerations

| Failure or surprise | Explanation and response |
| --- | --- |
| `dp` code fails in a normal notebook | Run definitions through the configured pipeline context |
| Bronze fails to read the volume | Inspect pipeline run identity, Unity Catalog privileges, storage access, and path |
| Silver drops many rows | Inspect expectation metrics, cast failures, NULLs, and retained input |
| Graph succeeds but Gold is misleading | Validate grain, uniqueness, time zone, and reporting coverage |
| One dataset fails | Inspect which updates committed; do not assume all outputs refreshed together |
| A new field appears | Apply a compatible schema policy; do not silently redefine business meaning |

The pipeline's run identity must have source access and destination privileges. Your personal notebook access alone does not establish that a scheduled pipeline identity has access. Changing the destination schema or checkpoint state can create a new processing history rather than resume the old one.

## 9. Related classroom discussion: search and migration governance

**Elasticsearch** is a distributed search and analytics engine built on Apache Lucene, using document indexing for retrieval. The Elastic Stack combines Elasticsearch with ingestion and visualization tools. Logstash processes/routes events; Beats collect data, including Filebeat for logs and Metricbeat for metrics; Kibana provides exploration and visualization. Logstash is not the primary persistent data store, and the whole stack is not written in JavaScript. See [Elastic Stack](https://www.elastic.co/docs/get-started/the-stack) and [Logstash processing](https://www.elastic.co/docs/reference/logstash/how-logstash-works).

The migration discussion emphasized inventorying schemas, reconciling source/target data, preserving access controls, and planning cutover while source writes continue. A large migration may involve type conversions and layout changes as well as byte transfer. Its duration cannot be inferred from the data volume alone. Data engineers implement and validate governance with platform/security owners.

BigQuery **dynamic data masking** changes query-visible values according to the caller's permissions while retaining the underlying original value. Upstream de-identification changes what enters the destination. These solve different requirements. See [BigQuery masking](https://docs.cloud.google.com/bigquery/docs/column-data-masking-intro). Detailed GCP study remains in the [separate scope guide](gcp-data-engineering-scope.md); names such as Great Expectations, Gimel, BigLake, Composer, Looker, Aerospike, Couchbase, and Datadog were discussion topics, not implementations completed in this class.

## Knowledge check and completion checklist

1. How can a notebook hold pipeline source without acting as an ordinary imperative notebook job?
2. Why would Bronze use a streaming table while a downstream aggregate uses a materialized view?
3. How do the three expectation policies differ when a count is NULL or negative?
4. Why does a checkpoint not prove one row per business key?
5. Which permissions must the pipeline run identity have?

- [ ] I can distinguish notebook execution, dataset dependencies, and Job task dependencies.
- [ ] I can explain materialization and streaming-table state.
- [ ] I can choose quality behavior and explain its effect on coverage.
- [ ] I can distinguish schema parsing from business validation.
- [ ] I can describe what remains pending when a pipeline has not been run.

## References

- [Python pipeline development](https://learn.microsoft.com/en-us/azure/databricks/ldp/developer/python-dev)
- [Python API reference](https://learn.microsoft.com/en-us/azure/databricks/ldp/developer/python-ref)
- [Pipeline expectations](https://learn.microsoft.com/en-us/azure/databricks/ldp/expectations)
- [Auto Loader](https://learn.microsoft.com/en-us/azure/databricks/ingestion/cloud-object-storage/auto-loader/)
- [Materialized views](https://learn.microsoft.com/en-us/azure/databricks/views/materialized)
