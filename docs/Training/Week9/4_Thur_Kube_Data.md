# Data Architecture, Kubernetes, and Classroom Interview Review

> Level: Beginner to intermediate
>
> Scope: High-level architecture and Kubernetes concepts, followed by the cross-topic interview review from class
>
> Example status: Illustrative reference snippets; no runtime results claimed
>
> Last reviewed: 2026-11-08

## How to use these notes

The architecture and Kubernetes sections focus on explaining responsibilities and recognizing where each concept fits in a data platform. The interview section follows the topics from class in their original order and adds short answers, practical examples, and common mistakes. These are classroom review notes, separate from the repository's standalone interview banks.

Prerequisites: Basic SQL, DataFrames, batch versus streaming, and warehouse/lakehouse concepts. Reading the guide requires no cluster or cloud account. Python examples assume an existing Spark session named `spark`; the repository specifies PySpark 4.2.0. Great Expectations requires its own compatible installation. Code is illustrative and has not been run as part of this edit.

After studying, you should be able to explain who owns data, distinguish entity matching from historical modeling, describe Kubernetes' role, and answer the classroom questions with both the concept and its practical limits.

## Part 1: Data architecture at a high level

### Data mesh, data fabric, Data Vault, and MDM solve different problems

| Concept | Main question | Data-engineering responsibility |
| --- | --- | --- |
| Data mesh | Who owns and supports a domain's data products? | Publish reliable datasets with clear contracts and shared governance. |
| Data fabric | How can data across different systems be discovered, connected, and governed? | Integrate sources with metadata, lineage, access controls, and automation. |
| Data Vault | How can we integrate business keys, relationships, and changing attributes with history? | Build traceable historical integration models. |
| Master data management (MDM) | Which records represent the same customer, product, or other business entity? | Apply matching rules, maintain crosswalks, and publish trusted master records. |

These approaches can coexist. A domain could own a customer data product, use MDM for customer matching, store integrated history in a Data Vault, and expose metadata through shared tooling. They are not interchangeable storage products.

### Data mesh: domain ownership and shared standards

Data mesh puts responsibility for a data product with the business domain that understands its meaning. For example, a Sales domain could own an orders dataset, including definitions of an order, its status, and its freshness expectations. Data engineers may work within that domain or provide shared platform capabilities; ownership does not mean a salesperson must personally build pipelines.

The four principles are:

- **Domain ownership:** Teams remain accountable for their published data.
- **Data as a product:** Consumers receive documented, discoverable, usable data with an owner.
- **Self-service platform:** Shared tools make ingestion, testing, publishing, and access easier.
- **Federated governance:** Domains participate in common policies for compatibility, security, and quality.

**Classroom question: How do data engineers know what Sales is doing with its data?** Through a published contract and catalog entry, named owners, lineage, quality/freshness monitoring, and communication about changes. For example, an orders product could promise one row per order, a stable `order_id`, defined currency units, restricted customer fields, and an agreed update schedule.

The benefit is that data responsibility stays close to business expertise. The tradeoff is coordination: incompatible customer identifiers or conflicting definitions of revenue can still break company-wide analysis. Mesh does not require every dataset to be physically combined in one central store, and handing raw files to a central team does not by itself establish domain ownership.

Reference: [Data mesh principles, by Zhamak Dehghani](https://martinfowler.com/articles/data-mesh-principles.html).

Class video retained: [Data mesh interview reference, starting at 2:00](https://www.youtube.com/watch?v=CD565M8Eta8&t=120s). This is the supplied classroom link; the notes do not claim a transcript review.

### Data fabric: connecting a distributed data environment

A data fabric is an architectural approach to making data across systems easier to discover, integrate, access, and govern using connected metadata and automation. For example, shared metadata could show where a customer field originates, which pipelines transform it, and which access policy applies.

For data engineers, the useful distinction is **mesh emphasizes domain ownership; fabric emphasizes connected data-management capabilities**. Neither automatically fixes bad source data, and fabric does not necessarily mean copying everything into a single database. See [IBM's data fabric overview](https://www.ibm.com/think/topics/data-fabric).

### MDM versus Data Vault: the same customer, different goals

Consider these fictional source records:

| Source | Source customer ID | Customer name | Email |
| --- | --- | --- | --- |
| CRM | CRM-101 | Robert Smith | robert@example.com |
| Billing | BILL-883 | Bob Smith | bob@example.com |
| Support | SUP-204 | R. Smith | robert@example.com |

**MDM asks whether these are the same person and which values should be trusted.** Identity resolution and matching rules identify possible matches; survivorship rules select attributes, and a data steward can review uncertain cases. A golden record might take the name from CRM and a verified contact attribute from another source, retaining lineage and mappings back to each source ID. Similar names or a shared email alone do not prove identity.

**Data Vault organizes integrated data and its history.** Using the customer and order example:

| Component | Stores | Example |
| --- | --- | --- |
| Hub | Distinct business keys, with technical and load metadata | Customer business key in `hub_customer`; order business key in `hub_order`. |
| Link | Relationships between business keys | Customer placed order in `link_customer_order`. |
| Satellite | Descriptive attributes and their history, attached to a hub or link | Customer name, email, source, and load time in a customer satellite. |

A hub does not automatically resolve the three source identities. Engineers must define the business key and cross-system mapping; an MDM crosswalk can help, but is not required by Data Vault. Historical integration also does not automatically decide which conflicting source value is correct for business use.

**Interview distinction:** MDM establishes trusted representations of entities. Data Vault preserves integrated keys, relationships, attributes, and history for traceability. Neither inherently requires the other. References: [IBM on MDM](https://www.ibm.com/think/topics/master-data-management) and [Data Vault modeling overview](https://www.databricks.com/blog/what-is-data-vault).

## Part 2: Kubernetes at a high level

### What Kubernetes does for a data platform

Kubernetes schedules and manages containerized workloads across machines. You describe the desired workload, and its controllers work to maintain that state. A data platform might use it to run ingestion services or Spark driver/executor containers.

```text
Container image: application code and runtime dependencies
    -> Pod: running container(s) with shared local resources
    -> Kubernetes cluster: schedules Pods onto worker nodes
    -> External systems: source databases, durable data, checkpoints, warehouse
```

| Term | High-level meaning | Why a data engineer cares |
| --- | --- | --- |
| Cluster | Control plane plus worker nodes | Supplies the environment in which workloads run. |
| Node | Machine that runs Pods | Has finite CPU, memory, and storage resources. |
| Pod | Smallest deployable Kubernetes unit; contains one or more containers | Can be replaced, so local files should not be the only copy of important data. |
| Deployment | Maintains a desired set of application replicas | Useful for long-running ingestion or API services. |
| Job / CronJob | Runs work to completion / creates Jobs on a schedule | Useful for containerized batch tasks. |
| Service | Stable network access to selected Pods | Lets applications communicate despite Pod replacement. |
| `kubectl` | CLI that talks to the Kubernetes API | Used to inspect workloads, events, and logs. |
| kind / Minikube | Tools for local Kubernetes clusters | Useful for learning; local success does not establish production readiness. |

**Correction to the original note:** Kubernetes manages container workloads; Amazon ECS is a separate container orchestrator. Amazon EKS is AWS's managed Kubernetes offering. Kubernetes does not manage ECS tasks as Kubernetes workloads.

### What Kubernetes does not guarantee about data

A replacement Pod can restore compute capacity while the application still needs to recover its processing state. Data engineers remain responsible for:

- **Durability:** Keep source data, published outputs, and recovery state on appropriate durable storage.
- **Correct retries:** A restarted task must not double-count orders or append duplicate results.
- **Resources:** Set realistic CPU/memory requests and limits; investigate memory failures rather than repeatedly restarting an oversized workload.
- **Access and operations:** Provide appropriate credentials, network access, logs, and monitoring.

For example, if a streaming processor dies after writing output, Kubernetes may replace its Pod. Recovery still depends on source replay, a usable checkpoint, and sink behavior that handles retries correctly. Restarting a container is not proof of exactly-once data delivery.

For this lecture, focus on explaining that boundary. Cluster installation, deployment YAML, and cluster administration are beyond the teacher's high-level scope. Reference: [Kubernetes overview](https://kubernetes.io/docs/concepts/overview/).

## Part 3: Interview prep — questions reviewed in class

These questions span several previous topics. The answers below are study references, not claims of personal production experience.

### 1. What is partition pruning?

**Short answer:** Partition pruning lets a query engine skip storage partitions that cannot match a filter. It reduces data scanned; it does not resize partitions.

Suppose trips are stored by `trip_date`. A query for one day can skip other dates. This differs from `repartition()`, which redistributes data during execution, and from filtering non-partition columns, which may benefit from other forms of pushdown or data skipping.

**Illustrative PySpark/Spark SQL example:** Synthetic data, one row per trip. The temporary directory holds only this example's output and is removed after the actions finish.

```python
from datetime import date
from tempfile import TemporaryDirectory

trips = spark.createDataFrame(
    [(1, date(2026, 11, 5)), (2, date(2026, 11, 5)), (3, date(2026, 11, 6))],
    "trip_id long, trip_date date",
)

with TemporaryDirectory(prefix="partition-pruning-") as example_dir:
    trips.write.partitionBy("trip_date").parquet(f"{example_dir}/trips")
    spark.read.parquet(f"{example_dir}/trips").createOrReplaceTempView("class_trips")

    filtered = spark.sql("""
        SELECT trip_id, trip_date
        FROM class_trips
        WHERE trip_date = DATE '2026-11-05'
    """)
    unfiltered = spark.sql("SELECT trip_id, trip_date FROM class_trips")
    filtered.explain("formatted")
    unfiltered.explain("formatted")
    filtered.show()
    spark.catalog.dropTempView("class_trips")
```

**Expected, not observed here:** The filtered scan should show a date condition under `PartitionFilters`; the unfiltered query has no equivalent date restriction. The filtered result contains trip IDs 1 and 2, with no guaranteed row order. A plan identifies the intended scan; use runtime scan metrics to establish actual bytes/files read. Three rows cannot demonstrate a meaningful performance gain.

Reference: [Spark 4.2 Parquet partition discovery](https://spark.apache.org/docs/4.2.0/sql-data-sources-parquet.html).

### 2. Is Great Expectations similar to Delta Live Tables?

**Short answer:** They overlap in data-quality rules, but have different scopes. Great Expectations (GX) validates data against expectations. Delta Live Tables, now documented in Databricks' Lakeflow pipeline family, also manages pipeline transformations and dependencies; expectations are one capability within it.

| Aspect | Great Expectations | Databricks pipeline expectations |
| --- | --- | --- |
| Main purpose | Data validation, results, and integration into a workflow | Quality rules attached to managed pipeline datasets |
| Example checks | Required IDs, ranges, allowed values, patterns, and types where supported | Conditions such as `trip_duration_minutes > 0` |
| Failure response | Your workflow or configured actions decide what happens | Can record violations, drop invalid records, or fail the update |

**Illustrative GX Core 1.x Spark example:** This uses the Data Source → Asset → Batch pattern. It assumes a compatible GX installation; API/engine compatibility must be checked before running it.

```python
import great_expectations as gx

sample = spark.createDataFrame(
    [("ride-1", 12.0), ("ride-2", -3.0)],
    "ride_id string, trip_duration_minutes double",
)
context = gx.get_context(mode="ephemeral")
source = context.data_sources.add_spark(name="class_spark")
asset = source.add_dataframe_asset(name="trips")
batch_definition = asset.add_batch_definition_whole_dataframe("all_rows")
batch = batch_definition.get_batch(batch_parameters={"dataframe": sample})

checks = [
    gx.expectations.ExpectColumnValuesToNotBeNull(column="ride_id"),
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="trip_duration_minutes", min_value=0.01, max_value=1440,
    ),
]
for check in checks:
    result = batch.validate(check)
    print(result.success)
```

**Expected, not observed here:** The ID check passes and the duration check fails. The duration limits are a fictional classroom contract, not a Citi Bike source rule. Validation reports the problem; this loop does not quarantine records or block publication. Production orchestration must connect failures to the agreed action. Separate not-null checks matter because missing values may be excluded from other checks.

References: [GX DataFrame connections](https://docs.greatexpectations.io/docs/core/connect_to_data/dataframes/), [GX validation workflow](https://docs.greatexpectations.io/docs/core/introduction/try_gx/), and [Databricks expectations](https://docs.databricks.com/aws/en/ldp/expectations).

### 3. What is the difference between an RDD and a DataFrame in Spark?

**Short answer:** An RDD is a distributed collection with lower-level transformations. A DataFrame represents structured data with named columns and a schema, giving Spark information it can use to optimize queries.

| Aspect | RDD | DataFrame |
| --- | --- | --- |
| Data representation | Distributed elements, such as tuples or objects | Rows with named, typed columns |
| Typical operations | `map`, `flatMap`, and `reduceByKey` | `select`, `filter`, joins, aggregations, and SQL |
| Optimization | Spark cannot inspect arbitrary user functions as relational expressions | Spark can optimize the structured query plan |
| Data-engineering use | Specialized lower-level processing | Common choice for structured ETL and analytics |

An RDD is not simply a Python list, and a DataFrame is not just a visual table wrapper. Both represent distributed computation and can use lazy transformations. Prefer DataFrames when their operations express the requirement clearly.

### 4. What is the difference between a DataFrame and a Dataset?

**Short answer:** In Scala and Java, a typed Dataset adds typed objects and encoders. In Scala, a DataFrame is a `Dataset[Row]`. PySpark exposes DataFrames, not the Scala/Java typed Dataset API.

A Scala `Dataset[Trip]` can provide compile-time checking when accessing typed fields through typed operations. String-based column expressions can still fail during analysis or execution. Compile-time types also do not prove business correctness: a valid numeric field can still contain an invalid negative fare.

For both Spark API questions, see [Spark 4.2 DataFrame and Dataset operations](https://spark.apache.org/docs/4.2.0/sql-getting-started.html).

### 5. Why can a Python UDF be slower than built-in Spark functions or a Scala UDF?

**Short answer:** A conventional scalar Python UDF moves data between Spark's JVM execution and Python workers, adding serialization and function-call overhead. Built-in expressions generally stay in Spark's execution engine and give the optimizer more information.

The explanation is broader than “Python is interpreted and Scala is compiled.” A Scala UDF avoids the Python worker boundary, but can still hide useful logic from optimization. A Pandas UDF processes batches with Arrow and may reduce transfer overhead; it is not automatically the fastest option.

For example, use `F.upper("station_name")` for uppercase conversion instead of implementing the same operation as a Python UDF. When custom logic is necessary, compare runtime and validate null handling, types, and results on representative data. Reference: [Spark 4.2 UDF guide](https://spark.apache.org/docs/4.2.0/api/python/user_guide/udfandudtf.html).

### 6. What is the difference between watermarks and checkpoints?

**Short answer:** A watermark controls event-time state handling and late-data behavior for supported streaming operations. A streaming checkpoint stores progress and recovery state. They solve different problems and are often used together.

| Feature | Watermark | Streaming checkpoint |
| --- | --- | --- |
| Question answered | How long should an operation retain event-time state? | Where should this query recover its progress and state? |
| Configured using | `.withWatermark("event_time", "10 minutes")` | `.option("checkpointLocation", "...")` on `writeStream` |
| Depends on | Observed event times and query/operator semantics | Durable checkpoint storage and a compatible query/source/sink |
| Does not guarantee | That every old record is always dropped | Exactly-once writes to every possible external sink |

**Illustrative streaming query:** Assumes a directory receiving new JSON files, one record per trip, with parseable timestamps. Paths are placeholders for a configured environment; do not place the checkpoint inside a disposable container filesystem.

```python
from pyspark.sql import functions as F

incoming = (
    spark.readStream
    .schema("ride_id string, event_time timestamp, station_id string")
    .json("/path/to/new-trip-json")
)
counts = (
    incoming
    .withWatermark("event_time", "10 minutes")
    .groupBy(F.window("event_time", "5 minutes"), "station_id")
    .count()
)
query = (
    counts.writeStream
    .format("parquet")
    .outputMode("append")
    .option("path", "/path/to/durable/station-counts")
    .option("checkpointLocation", "/path/to/durable/checkpoints/station-counts")
    .start()
)
# After observing progress in a configured environment: query.stop()
```

`readStream` defines the input. `withWatermark` is a transformation applied before the stateful aggregation. `writeStream` defines output and recovery configuration. Output grain is one row per five-minute event-time window and station; append mode emits finalized windows as the watermark advances.

For a single stream, think of the watermark as approximately the greatest observed event time minus the allowed delay, with advancement applied across micro-batches. If it reaches 10:20, older windows can become eligible for finalization/state removal. It is not simply wall-clock time minus ten minutes; idle input may delay final output. Events within the supported delay guarantee are protected from being dropped as too late; events beyond it may or may not be processed, depending on state and operator behavior.

Removing the watermark from this append-mode aggregation can make it unsupported because Spark cannot know when a window is final. Removing a durable checkpoint loses the established recovery position. Batch DataFrame checkpointing is different: it materializes data and truncates lineage; it does not automatically resume an arbitrary batch program from its last line.

Reference: [Spark 4.2 Structured Streaming semantics](https://spark.apache.org/docs/4.2.0/streaming/apis-on-dataframes-and-datasets.html).

### 7. What is the difference between a data mart and the Gold layer?

**Short answer:** A data mart is organized around a business subject or audience. Gold describes a business-ready layer in a medallion architecture. A mart can be implemented within Gold; they are not mutually exclusive alternatives.

For example, a Citi Bike operations mart could contain a station dimension and daily station metrics. Those tables could live in Gold, alongside other curated datasets. Define grain, measures, owners, and freshness before choosing the label. Gold is not synonymous with an entire warehouse, and marts do not have to be only aggregated tables. Reference: [Data mart overview](https://www.databricks.com/blog/what-is-data-mart).

### 8. What is Debezium, and where does it fit?

Classroom emphasis: Debezium was discussed as pipeline context rather than a primary interview target. That reflects this class, not a claim that other interviewers never ask about it.

**Short answer:** Debezium captures database changes and exposes change events. In a common deployment, database connectors run through Kafka Connect, capture committed changes from database logs, and publish them to Kafka.

```text
Database: INSERT / UPDATE / DELETE
    -> Database change log or connector-specific change mechanism
    -> Debezium connector
    -> Kafka topics
    -> Spark / Flink / sink connector
    -> Warehouse tables and business marts
```

A simplified update event might look like this:

```json
{
  "op": "u",
  "before": {"customer_id": 101, "balance": 1000},
  "after": {"customer_id": 101, "balance": 1500}
}
```

Actual events include connector/source metadata and timestamps; available before-images depend on database configuration. Initial snapshots can capture existing rows before ongoing change capture. Log capture reduces repeated source-table scans, but snapshots and log retention still impose operational work.

For data engineers, the important concerns are preserving source identity/order metadata, handling replayed events idempotently, applying deletes, managing schema changes, and detecting lag or unavailable log history. Do not assume end-to-end exactly-once delivery: guarantees depend on the connector, deployment, processing engine, and sink. A streaming watermark does not establish database transaction order or replace CDC deduplication.

Typical uses include analytical ingestion, database replication, search-index updates, cache invalidation, and downstream service integration. Debezium supplies changes; it does not replace the transformation engine or warehouse. Reference: [Debezium architecture](https://debezium.io/documentation/reference/stable/architecture.html).

### 9. In Python, what is the GIL?

**Short answer:** In a conventional CPython build, the Global Interpreter Lock allows only one thread at a time to execute Python bytecode within a process. Threads can still help with overlapping I/O; separate processes can parallelize CPU-bound Python work.

| Workload | Common approach | Reason |
| --- | --- | --- |
| Waiting for API responses or files | Bounded threads or asynchronous I/O | Overlaps waiting time. |
| CPU-heavy pure Python transformations | Multiple processes | Separate interpreters avoid sharing one process's GIL, with serialization/memory overhead. |
| Structured distributed ETL | Spark's built-in operations | Distributes execution and uses the engine's execution paths. |

**Correction:** Multithreading does not generally bypass the GIL for CPU-bound Python bytecode. Native extensions may release it, and optional free-threaded CPython builds change the assumption. The GIL also does not replace locks needed to protect application-level shared state. Reference: [Python threading documentation](https://docs.python.org/3/library/threading.html).

### 10. Z-Ordering versus liquid clustering

**Short answer:** Both improve data layout so eligible queries can skip more data. Z-Ordering colocates related values across selected columns. Liquid clustering supports an evolving clustering layout, with keys that can change as query patterns change.

| Aspect | Z-Ordering | Liquid clustering |
| --- | --- | --- |
| Familiar syntax | `OPTIMIZE ... ZORDER BY (...)` | `CLUSTER BY (...)`, with maintenance through supported optimization mechanisms |
| Column selection | Columns selected explicitly | Explicit keys, or automatic key selection on eligible Databricks tables |
| Relationship to partitioning | Often used within existing table partitions | Alternative to traditional table partitioning and Z-Ordering on a table |
| Tuning question | Do chosen columns help common filters? | Do keys, maintenance, and table/runtime support suit the workload? |

**Corrections:** The term is liquid clustering, not liquid processing. It does not universally eliminate human configuration. Automatic key selection, such as `CLUSTER BY AUTO`, has specific platform/table requirements. Z-Ordering still exists; do not combine it with liquid clustering on the same table.

For a trips table filtered by date and station, those columns are candidates to investigate, not automatic winners. Compare files/bytes scanned and query latency, including maintenance cost. These are layout techniques, not replacements for correct joins or business keys. Reference: [Databricks liquid clustering documentation](https://docs.databricks.com/aws/en/tables/clustering).

### 11. What is Teradata?

**Short answer:** Teradata is an established massively parallel analytical database/data-warehouse platform. Its systems distribute storage and query work across processing units. Its history predates modern cloud warehouses; calling it the original cloud storage system is inaccurate.

**BTEQ is a client utility**, used to submit SQL and utility commands interactively or in scripts. The database uses Teradata SQL; BTEQ is not the name of its SQL dialect. See [Teradata's BTEQ documentation](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/Teradata-Tools-and-Utilities-Release-Definition-20.00/Product-Information/Basic-Teradata-Query-Utility).

For a migration discussion involving Redshift, Databricks, or Snowflake, focus on SQL compatibility, data types, distribution and skew, business logic, scheduling, security, and reconciliation. Validate row counts, keys, measures, and query results at the same grain and cutoff. Avoid claiming that all organizations are leaving Teradata or that a platform is obsolete merely because a migration is being discussed.

## Review checkpoints

- Explain a data mesh product's owner, grain, freshness promise, and shared policies without naming a vendor.
- Explain why a trusted customer record and a customer's attribute history are different deliverables.
- Describe what happens to processing state when Kubernetes replaces a Pod.
- Identify partition-pruning evidence in a scan plan and separate expected behavior from measured I/O.
- Explain what action should follow a failed data-quality check.
- Describe the JVM/Python boundary for a Python UDF.
- Explain why a watermark and a durable checkpoint are both useful in one streaming query.
- Explain how CDC replay, deletes, and ordering affect warehouse correctness.
- Distinguish a mart's business scope from a Gold layer's refinement level.
- State the runtime/platform assumptions behind GIL and liquid-clustering answers.

Completion evidence remains pending: execute the illustrative snippets in compatible environments, inspect actual plans and validation results, and test streaming late-data/restart behavior. No Kubernetes deployment, database CDC connector, Databricks optimization, or performance benchmark was run for these notes.
