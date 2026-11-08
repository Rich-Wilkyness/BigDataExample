# Mock interview questions and practice answers

These answers use the BNPL scenario in the [interview playbook](richard-wilkerson-interview-playbook.md) and [pitch and project notes](pitch-and-project-notes.md). The résumé and employment scenario are fictional interview practice. The proposed details below make the architecture coherent; they are not evidence of Richard's employment, PayPal's implementation, or measured production results. Answers use “I would” to preserve that distinction.

Start with the **Interview answer** and use the supporting notes when the interviewer asks for depth. Aim for roughly 60–90 seconds per answer. Product documentation was reviewed on 2026-11-04; exact runtime, connector, and catalog versions remain unspecified and would need validation before implementation.

## 1. End-to-end architecture

**Original question:** tell me about e2e architecture and pipeline you worked on in recent role

**Interview answer**

“For this BNPL scenario, I would describe a pipeline supporting application-funnel, approval, and repayment reporting. The main challenge is assembling trustworthy financial data from APIs and partner feeds with different schemas and delivery schedules.

I would preserve source responses and files in Cloud Storage with batch and source identifiers. PySpark on Dataproc would standardize timestamps and amounts, resolve application and loan identifiers, and handle duplicates and corrections. Schema checks would identify incompatible inputs, and quality checks would reconcile accepted records against source totals before publication.

Airflow running in Cloud Composer would coordinate extraction, validation, transformation, and publication. Processing and publication controls would operate by market, allowing independent markets to continue when one feed fails. BigQuery would hold the analytical facts and dimensions, with dbt models defining reporting metrics.

For a separate low-latency exposure requirement, Kafka would carry events to Flink, which would update derived customer balances in Bigtable. The original events would also be archived for batch reconciliation. My proposed contribution would focus on ingestion, transformations, quality gates, and reliable publication.”

**Architecture to explain**

```text
APIs / partner feeds
        -> GCS originals -> validation -> Dataproc PySpark
        -> BigQuery staging -> validated facts / dbt marts -> reporting
           Airflow coordinates the batch workflow and publication gates

Loan / repayment events -> Kafka -> Flink -> Bigtable -> backend lookups
                            |
                            -> configured GCS archive -> batch reconciliation
```

**Follow-up points**

- Lead with batch; introduce streaming when discussing freshness requirements.
- Retain a run manifest, source boundary, configuration version, rejected records, and published-batch status so an operator can explain any output.
- A failed publication should leave a clearly labeled previous dataset available where appropriate. That requires a deliberate staging/publication design; an Airflow sensor alone does not provide it.
- The operational loan ledger remains authoritative for financial obligations. BigQuery supports analytical history; Bigtable serves derived exposure.

## 2. BigQuery consumption-layer data model

**Original question:** paypal's bigquery consumption layer - how did you design the data model to support applications approvals and repayments while handling high transaction volumes and ensuring data integrity?

**Interview answer**

“I would begin with the grain of each table. Applications, decisions, installments, and repayments represent different business events, so combining everything into one joined table would risk double-counting amounts.

I would use an application accumulating snapshot for submitted, decided, and disbursed milestones; a repayment fact for each business repayment; an installment fact for each scheduled installment; and a daily loan snapshot for balance and delinquency analysis. Separate decision-event history would preserve repeated decisions when needed. Shared customer, product, market, and date dimensions would make reports consistent. Customer history would use effective-dated versions where analysis needs the attributes at application time.

For scale, I would partition large facts by the relevant business date and choose clustering columns from actual filtering patterns. I would use incremental processing and reporting aggregates where they reduce repeated scans.

For integrity, I would validate unique business keys, parent references, valid lifecycle transitions, and monetary totals. Replays would use source versions and repeatable writes. Approval-rate definitions and repayment status rules would be explicit, so the same business measure means the same thing across reports.”

**Grain to defend**

| Dataset | Proposed grain | Important rule |
| --- | --- | --- |
| Application snapshot | One application | Repeated decisions do not create additional applications. |
| Decision history | One decision event/version | Distinguish first, latest, and final decision metrics. |
| Repayment fact | One business repayment, with its accepted current version | Preserve source versions and reversal history separately for audit. |
| Installment fact | One loan × installment | Multiple payment allocations must not duplicate the amount due. |
| Loan daily snapshot | One loan × business date × currency, within its market | A corrected historical day requires a controlled rebuild. |

**Follow-up points**

- Aggregate repayments to loan grain before joining them to loan amounts. A loan of USD 300 with three repayments must not become USD 900 of financed principal.
- If one repayment covers multiple installments, use an allocation table at repayment × installment grain, and reconcile allocations to the repayment total.
- Store money as fixed-precision decimals or defined integer minor units with currency. Do not sum currencies together without an explicit conversion policy.
- Resolve SCD Type 2 customer versions using the business event time and non-overlapping effective intervals.
- BigQuery does not enforce primary or foreign keys. Pipeline checks must maintain those guarantees before declaring constraints. [BigQuery key constraints](https://docs.cloud.google.com/bigquery/docs/primary-foreign-keys)
- Partitioning and clustering should follow measured query access patterns; clustering supports block pruning rather than acting as a point-lookup index. [BigQuery clustered tables](https://docs.cloud.google.com/bigquery/docs/clustered-tables)

## 3. PySpark ingestion: API limits and responses

**Original question:** on pyspark - how you design the ingestion to handle the api rate limits, responses, etc

**Interview answer**

“I would separate controlled API extraction from distributed Spark transformation. Spark can create far more concurrent requests than a source API allows, and task retries can repeat requests.

I would first establish the provider's quota scope, pagination rules, change-tracking capability, and response contract. A bounded extractor would apply a shared request budget, follow cursors, and land each response durably in Cloud Storage. Spark would process those landed objects at scale.

For throttling, I would honor Retry-After when supplied and otherwise use capped exponential backoff with jitter. Timeouts and eligible server failures would have bounded retries. Authentication or contract errors would need explicit handling rather than endless retrying. I would inspect the response body as well as the HTTP status, particularly for GraphQL partial errors.

Progress tracking would distinguish saved pages from a completed extraction interval. I would only mark an interval complete after every required page is safely landed and validated, and only mark it published after downstream checks pass. Overlapping extracts would be deduplicated using source identifiers and versions. Metrics would track throttling, retry counts, missing pages, and extraction lag.”

**Follow-up points**

- A pagination cursor locates the next page within an extract. An extraction watermark records progress between runs. Neither is a Flink event-time watermark.
- A per-executor limiter cannot enforce a shared account quota by itself. If distributed extraction is necessary, coordinate the total budget and account for retries/speculative attempts.
- Validate content type, response structure, required fields, pagination completion, and any source control totals. A GraphQL HTTP 200 can still contain errors or partial data.
- Use a bounded source interval or source snapshot when supported. If pagination can change during extraction, document how overlap and reconciliation address omissions; do not assume cursors provide a snapshot.
- Spark retries require replay-safe landing identifiers. Any API write would also need the provider's idempotency contract.
- HTTP 429 denotes rate limiting and may include Retry-After. [HTTP rate-limit semantics, RFC 6585](https://www.rfc-editor.org/rfc/rfc6585.html#section-4)

## 4. PySpark ingestion: inconsistent schemas

**Original question:** on pyspark - how do you design ingestion for inconsistent schema

**Interview answer**

“I would preserve the original payload and validate it against a versioned source contract before creating the curated dataset. Inconsistent schemas should not silently change the meaning of financial fields.

I would parse with an explicit schema for the expected source version and use source-specific adapters to map fields into a common model. An additional optional field could be retained in raw data without immediately exposing it downstream. A missing loan identifier, incompatible amount type, or changed currency meaning would require quarantine or a batch hold.

I would also validate values after parsing. A field can parse successfully and still be wrong, such as an amount changing from dollars to cents. Cast failures and malformed records would be counted and retained with the source object and rejection reason.

Publication would depend on the agreed contract. If rejected records make a financial batch incomplete, I would hold that market's output. Once the source or adapter is corrected, I would replay the retained input and reconcile it before publication.”

**Follow-up points**

- Distinguish absent fields, explicit nulls, malformed values, incompatible types, and changed units. They require different handling.
- Example: adapting `paymentAmount` to `amount` is safe only after confirming currency, units, precision, and business meaning.
- Schema inference and schema merging do not establish semantic compatibility. Required identifiers and money fields need explicit validation.
- Spark JSON parsing offers permissive and fail-fast behavior. With an explicit schema, include the configured corrupt-record string field when needed to capture malformed input; retain the original objects regardless. Parsing success is only one validation step. [Spark JSON data source](https://spark.apache.org/docs/latest/sql-data-sources-json.html)

## 5. Spark join repeatedly fails with executor OOM

**Original question:** suppose your spark job processes 500m transactions but one executor repeatedly fails iwht oom error during a join - how to id root cause?

**Interview answer**

“I would first identify whether the failure follows the same task partition across executors or stays with one worker. A partition that fails wherever it runs suggests a data or execution-plan problem; failures confined to one worker suggest a worker-specific issue.

I would inspect the failed stage, physical join plan, and executor logs. The error could be JVM heap exhaustion, Python-worker memory pressure, or a container memory limit, so I would distinguish those before changing settings. I would compare the failed tasks' shuffle sizes, spill, duration, and garbage collection with the rest of the stage.

Then I would test the main hypotheses: a hot join key, too few shuffle partitions, an oversized broadcast side, or a many-to-many join that multiplies rows. I would profile key frequencies and check whether the supposed dimension key is actually unique.

The fix would follow that evidence: correct the join grain, filter and project early, change an unsafe broadcast, or address oversized/skewed partitions. I would validate both output totals and stage metrics afterward. More memory helps only if the remaining workload is legitimate and appropriately distributed.”

**Diagnostic sequence**

| Evidence | Hypothesis | Next check or fix |
| --- | --- | --- |
| Same partition fails on different workers | Skew, oversized partition, or problematic records | Profile keys and row sizes for that partition. |
| Same worker fails on different partitions | Worker/container issue | Inspect worker health, limits, logs, and other workloads. |
| A few tasks have far larger shuffle inputs | Hot keys | Test adaptive skew handling or isolate/salt hot keys while preserving join semantics. |
| Most partitions are large | Too little parallelism or excessive input | Reduce input and size shuffle partitions from observed bytes. |
| Failures occur while building a broadcast relation | Broadcast side exceeds practical memory | Check the executed plan and actual build-side size; remove an unsafe hint. |
| Output rows grow unexpectedly | Many-to-many join | Verify uniqueness and effective-date conditions; correct the model. |

**Follow-up points**

- Repartitioning by the same hot key leaves that key together. Adding executors alone also leaves a single oversized task unresolved.
- Salting requires matching treatment of both join sides and careful validation, especially for outer joins. Do not remove legitimate records simply to make the job fit.
- Spark's UI/event logs expose stage and executor evidence. [Spark monitoring](https://spark.apache.org/docs/latest/monitoring.html)
- Adaptive Query Execution can split eligible skewed join partitions; behavior depends on the join and configuration. It cannot repair a logically incorrect join. [Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html)

## 6. Why Iceberg instead of only native BigQuery tables?

**Original question:** iceberg - why you choose it instead of keeping everything in native biquery tables

**Interview answer**

“I would use Iceberg for selected curated datasets when Spark and BigQuery need a shared open table representation on object storage. That requirement can justify avoiding separately maintained copies and keeping processing options open.

Iceberg provides table metadata and snapshots over data files, with atomic table commits and schema/partition evolution. It is a table format, so I would still choose the compute engines, catalog, and maintenance approach separately.

I would keep native BigQuery tables for reporting workloads where warehouse integration and simpler operations are the priority. Time travel alone would not justify adding Iceberg because BigQuery also has historical recovery capabilities.

The tradeoff is operational responsibility: catalog consistency, compatible readers and writers, small-file compaction, snapshot retention, and metadata visibility. For this scenario, I would use shared Iceberg curated data only where interoperability is a real requirement, then materialize selected native BigQuery reporting marts. If BigQuery were the only consumer, I would question whether Iceberg adds enough value.”

**Follow-up points**

- This hybrid is a proposed clarification of the playbook's broad “Iceberg through BigLake” description; the notes do not establish the deployed integration mode.
- Atomic table commits do not provide a transaction across Kafka, Iceberg, BigQuery, and Bigtable. [Iceberg reliability and concurrency](https://iceberg.apache.org/docs/latest/reliability/)
- BigQuery supports different Iceberg integration modes with different ownership and maintenance responsibilities. Identify the actual mode before claiming capabilities. [Iceberg external tables](https://docs.cloud.google.com/bigquery/docs/iceberg-external-tables), [Iceberg managed tables](https://docs.cloud.google.com/bigquery/docs/biglake-iceberg-tables-in-bigquery)

## 7. Iceberg versus BigQuery: performance and metadata

**Original question:** what architecture did you need for query performance metadata management when you were working with iceberg vs bigquery - tradeoffs?

**Interview answer**

“I would separate data layout, table metadata, and query execution. For this example, I would assume Spark-owned Iceberg curated tables in GCS, a supported shared catalog, and BigQuery external access, with selected reporting marts materialized natively.

For Iceberg, I would choose partition transforms and file sizes from the access patterns, compact small files, maintain metadata, and manage snapshot retention. I would establish one catalog commit authority for each table and verify that readers see the intended committed snapshot. If BigQuery were configured against a specific metadata JSON file, updating that reference would be an explicit publication step.

For native BigQuery tables, I would tune partitioning, clustering, incremental loads, and reporting aggregates while Google manages the underlying storage organization. I would inspect query plans, bytes scanned, and slot consumption.

I would benchmark representative queries against equivalent data and freshness. Iceberg offers interoperability with additional maintenance and compatibility work. Native BigQuery simplifies warehouse operations. The choice should follow measured performance, cost, and ownership needs.”

**Architecture decisions to defend**

| Concern | Proposed Iceberg external path | Native BigQuery path |
| --- | --- | --- |
| Table state | Catalog resolves committed Iceberg metadata and snapshots; BigQuery integration must track the intended state | BigQuery manages table metadata. |
| Scan efficiency | Partition/file pruning, suitable file sizes, sorting, and maintenance | Partition and cluster pruning, query design, and reporting materializations. |
| Maintenance | Assign compaction, metadata maintenance, snapshot expiry, and safe cleanup to an owner | Google manages storage internals; the team owns query/model tuning and retention settings. |
| Publication | Record snapshot/batch identity and verify reader visibility | Record batch identity and publish validated staging results. |
| Access | Validate engine/catalog/storage permissions and equivalent controls | Configure BigQuery permissions and applicable row/column policies. |

**Follow-up points**

- Metadata refresh is integration-specific. A direct metadata-file reference needs updating after commits; do not assume a BigQuery reader discovers new files automatically. [BigQuery Iceberg metadata updates](https://docs.cloud.google.com/bigquery/docs/iceberg-external-tables#update_table_metadata)
- Managed Iceberg modes can automate maintenance responsibilities that this external-table example assigns to the platform team. Do not apply this table unchanged to every Iceberg product. [Managed Iceberg table management](https://docs.cloud.google.com/bigquery/docs/biglake-iceberg-tables-in-bigquery)
- Retention must protect snapshots needed by active readers and recovery. Never delete files merely because they look old.

## 8. Consistency between Kafka, Flink, and the BigQuery batch path

**Original question:** maintaining consistency between kafka, flink, and bq batch path. how did you reconcile them

**Interview answer**

“I would establish common event identifiers, source versions, and financial definitions before comparing systems. Both paths need the same interpretation of posted repayments, reversals, payment allocation, currency, and rounding.

Kafka would carry the events, Flink would calculate current exposure for Bigtable, and an independent archive path would retain the original events for batch processing into BigQuery. Each path would record source progress and rule versions. Flink recovery would use checkpoints and a tested sink write contract; batch reruns would use repeatable writes.

Reconciliation would compare equivalent outputs at the same customer, loan, currency, and source cutoff. I would compare event counts, monetary totals, and derived balances, then investigate differing identifiers. Expected timing differences would be tracked until both paths were complete for the agreed boundary.

If there were a defect, I would trace the event through Kafka, archive, transformation, and destination, fix the cause, and replay the affected scope. This provides eventual agreement with auditability; it does not imply one atomic transaction across all systems.”

**Follow-up points**

- Record Kafka topic/partition/offset on archived events where feasible, plus source business identifiers. Offsets locate records within one partition; they are not global business IDs.
- A reconciliation boundary can include per-partition offset ranges and a business cutoff. The same wall-clock timestamp alone does not prove both paths consumed the same inputs.
- Comparing current Bigtable state to an earlier batch requires retained stream snapshots or deterministic reconstruction at that earlier boundary.
- Deduplicate duplicate deliveries by stable identity/version. Treat genuine corrections and reversals as business changes. A bounded stream deduplication window needs a policy for duplicates arriving after its state expires.
- Flink's exactly-once state recovery does not automatically give every external write exactly-once effects. End-to-end guarantees require replayable sources and transactional or idempotent sinks. [Flink fault tolerance](https://nightlies.apache.org/flink/flink-docs-stable/docs/learn-flink/fault_tolerance/)

## 9. Streaming reports 25,000 repayments; batch reports 24,000

**Original question:** if streaming pipeline reported 25k repayments but batch pipeline only recorded 24k

**Interview answer**

“I would first confirm that both numbers represent the same thing: unique posted repayments for the same markets, currencies, time window, and source boundary. A stream event count and a batch count of final repayment records can legitimately differ.

I would check completion and freshness next: Kafka offsets, archive delivery, batch manifests, rejected records, and publication status. If the batch is still behind, the difference may be temporary, but I would keep it visible until it reconciles.

Once both paths are complete, I would compare distinct repayment identifiers in both directions, then compare versions, statuses, and amounts for matching IDs. That separates missing records from duplicates, filter differences, and incorrect updates.

For any disputed repayment, I would trace the source event through Kafka, GCS, staging, and the final fact. The repair would follow the cause: replay an omitted file, correct a transformation, resolve quarantined records, or fix streaming deduplication. I would rerun reconciliation and validate balances before considering the incident resolved.”

**Investigation order**

| Check | What it can reveal |
| --- | --- |
| Same metric and grain? | 25,000 messages might include retries or status changes for only 24,000 repayments. |
| Same cutoff and market time zone? | A batch boundary can exclude events included in a live dashboard. |
| Same source progress? | Missing archive objects, unfinished loads, or a held market can make batch incomplete. |
| Stream IDs absent from batch? | Trace those events through archive, parsing, quarantine, joins, and publication. |
| Batch IDs absent from stream? | Investigate stream filtering, state retention, source coverage, or batch-only corrections. |
| Same IDs but different values? | Check source versions, status transitions, reversal rules, currency units, and allocation logic. |

**Small example**

If streaming contains 25,000 rows but only 24,000 distinct repayment IDs, and batch contains those same 24,000 IDs, the first hypothesis is duplicate delivery or multiple events per repayment. If streaming contains 25,000 distinct IDs, batch contains 24,000, and batch-only IDs also exist, the number of stream-only IDs can exceed 1,000. The net count difference alone does not identify the missing population.

**What makes the answer senior-level**

Define completeness before diagnosing loss, compare actual records and monetary values, and repair the responsible path with a controlled replay. Financial reporting and decisioning should expose affected data as incomplete or stale according to the agreed incident policy until the discrepancy is resolved.


# New batch of questions

Handling Streaming backpressure
- Flink backpressure happens when downstream operators can't process records as quickly as upstream operators produce them, causing data to accumulate and throughput to drop.
- use flink UI to check metrics like backpressuretime, busytime, idletime
- EX:
```
At PayPal, I worked with Kafka and Flink real-time processing alongside our BigQuery batch pipelines for BNPL acquisition and servicing data. When troubleshooting backpressure, I would start with the Flink Web UI and trace the pressure upstream from the slowest operator. For example, if a keyed aggregation was showing high busy time while other subtasks were mostly idle, I'd investigate data skew, key distribution, and operator parallelism before increasing cluster resources. I'd also correlate those findings with Kafka consumer lag and Datadog monitoring to understand whether the problem was caused by incoming traffic or processing capacity.

If the bottleneck was downstream, I'd focus on sink throughput, batching, and external service latency rather than simply adding more TaskManagers. For stateful processing, I'd also review checkpoint duration, state growth, and RocksDB performance because large state and slow checkpoints can affect overall pipeline stability. After making changes, I'd compare records processed per second, backpressure metrics, consumer lag, and end-to-end latency to verify that throughput improved without compromising checkpoint recovery or data consistency.
```


How do you handle Kafka schema evolution?
- Managing changes to event schemas without breaking existing producers, consumers, or downstream data pipelines.
- Schema Registry: I use Confluent Schema Registry with Avro schemas to maintain versioning and enforce compatibility between producers and consumers.
- Schema Changes: I handle new fields using optional attributes and default values, while avoiding incompatible field removals or data type changes.
- Backward Compatibility: I prefer backward-compatible schema changes so newer consumers can process events written with older schemas.
- Example:
```
My approach would be to use Avro with Schema Registry, enforce backward compatibility, and make sure new fields were introduced without breaking existing consumers. For example, if we added a new repayment attribute, I'd introduce it as an optional field with a default value, update the Flink transformation logic, and validate the change against existing events.

I would also coordinate schema changes with downstream BigQuery and dbt models so the streaming and batch processing paths stayed consistent. Before deployment, I'd run compatibility checks and integration tests against historical and current schema versions. If a consumer encountered an incompatible event, I'd route it to quarantine with the original payload and error details for investigation. That way, we could introduce new event attributes safely, maintain backward compatibility, and avoid unnecessary downtime in production.
```

How do you handle idempotency in streaming?
- means processing the same event multiple times produces the same final result without duplicates or incorrect aggregations.
- use transaction IDs, event IDs, or composite business keys to identify duplicate records.
- Kafka Offsets: I track consumer offsets and coordinate offset commits with processing checkpoints to support reliable recovery.
- Flink Checkpointing: I use Flink's checkpointing mechanism to maintain consistent operator state and recover from failures without losing processing progress.
- Exactly-Once Semantics: I combine Flink's exactly-once state processing with transactional or idempotent sinks to prevent duplicate writes.
- Example:
```
my approach would start with assigning a stable transaction or event ID to every financial event. In Flink, I'd use keyBy() on the appropriate business key and maintain keyed state to track processed events. If Kafka redelivered a message because of a consumer restart or retry, the pipeline could recognize that event and avoid applying the same transaction twice. I'd also enable Flink checkpointing so operator state and Kafka offsets could be restored consistently after a failure.

On the downstream side, I'd make sure writes were idempotent as well, because Flink's exactly-once processing doesn't automatically guarantee exactly-once delivery to every external database. For BigQuery, I'd typically land events in a staging table and use MERGE statements based on transaction IDs, event versions, or sequence numbers to prevent duplicate inserts and stale updates. I'd also reconcile the streaming results against the batch pipeline, especially for repayments, disbursements, and delinquency calculations. The goal is to make retries, restarts, and historical replays safe without double-counting financial transactions or compromising data accuracy.
```

How do you handle dead letter queue and retries?
- Dead Letter Queue (DLQ): A DLQ isolates failed or malformed events so the main streaming pipeline can continue processing valid records.
- Kafka DLQ Topics: I would configure dedicated Kafka topics for failed events, separating schema validation errors, transformation failures, and downstream processing errors.
- Error Classification: I distinguish transient failures, such as API timeouts, from permanent failures, such as malformed JSON, invalid schemas, or missing required fields.
- Retry Strategy: I use exponential backoff, bounded retries, and circuit breakers for recoverable failures before routing exhausted events to the DLQ.
- Event Metadata: I preserve the original payload, event ID, Kafka topic, partition, offset, schema version, error message, and failure timestamp.
- Example:
```
At PayPal, I worked on Kafka and Flink streaming pipelines alongside BigQuery processing for BNPL applications, approvals, disbursements, and repayments. We also had differentiated retry, quarantine, partial-load, and full-failure handling in our PySpark and Airflow pipelines. For a Kafka/Flink DLQ implementation, I'd follow the same principle. If a repayment event failed because of a temporary downstream timeout, I'd retry it with exponential backoff. But if it failed because of an incompatible schema or invalid transaction data, I'd route it to a dedicated DLQ with the original payload and error metadata. That way, one bad financial event wouldn't repeatedly crash the entire streaming job. I'd also use circuit breakers to stop downstream propagation when data quality thresholds were breached.

For event replay, I'd build a controlled recovery process using Kafka retention or events preserved in Cloud Storage. Once the issue was fixed, I'd select the affected events and replay them through the same validation and transformation logic, with replay identifiers for auditing. I'd preserve the original transaction IDs and use version-aware BigQuery MERGE operations so previously processed transactions weren't duplicated or overwritten by stale events. I'd also monitor replay throughput to avoid overwhelming downstream systems. Finally, I'd run reconciliation checks against source transaction counts and financial totals to confirm that every valid event was processed correctly and that repayments or disbursements weren't double-counted.
```


How do you handle concurrency and _ in your streaming pipeline?
- Optimistic Concurrency Control (OCC): I used Apache Iceberg's snapshot-based transaction model to manage concurrent batch and streaming writes without corrupting table data.
- Snapshot Isolation: I leveraged Iceberg snapshots to provide consistent reads while batch and streaming jobs committed changes independently.
- Atomic Commits: I relied on Iceberg's atomic metadata commits to ensure readers never saw partially committed transactions.
- Commit Conflicts: I handled concurrent commit failures through retry logic with exponential backoff and refreshed table metadata.
- Conflict Validation: I distinguished retryable metadata commit conflicts from actual data conflicts involving overlapping partitions or records.
- Partition Isolation: I would separate batch and streaming workloads by partition or processing window wherever possible to minimize overlapping writes.
- Example:
```
At PayPal, I worked with Apache Iceberg tables through BigLake, allowing our Spark workloads on Dataproc and BigQuery consumers to share curated BNPL datasets. The important part of managing concurrency was Iceberg's optimistic concurrency control. Every writer operates against a table snapshot, and commits are atomic. If two jobs attempted to commit changes simultaneously, one could succeed while the other needed to refresh its metadata and retry. For append-only workloads, that retry could often succeed without rewriting the data. For overlapping updates or deletes, though, I'd revalidate the operation against the latest snapshot rather than blindly retrying, because we couldn't risk inconsistent repayment or disbursement records.

For the batch and streaming architecture, I'd minimize conflicts by keeping ingestion append-only where practical and using controlled MERGE operations for curated transaction states. I'd also coordinate Airflow batch jobs with streaming ingestion, apply bounded commit retries, and use stable transaction IDs to make recovery idempotent. For financial datasets, the final validation would include duplicate detection, source-to-target reconciliation, and checking transaction totals after retries or backfills. That approach lets batch and streaming workloads operate concurrently while maintaining Iceberg's transactional consistency and protecting the accuracy of downstream BigQuery analytics.
```


