# AWS streaming data engineering: Kinesis, MSK, Glue, and Aurora

> Status: Revised lecture; illustrative examples, no cloud execution performed. Level: Beginner → intermediate, with senior design considerations. Applies to: Streaming ingestion, processing, serving, and operations. Sources reviewed: 2026-10-12.

## Overview and study route

A streaming pipeline must keep accepting events while downstream systems slow down or fail, preserve enough history for recovery, and produce trustworthy outputs when records arrive twice or out of order. Choosing an AWS service is one part of that problem.

Use these three files in order:

1. **This lecture:** Learn the concepts and tradeoffs needed for the assignment and for explaining a design at work or in an interview.
2. **[Kinesis walkthrough](1.1-mon-kinesis-steps.md):** Capture real Citi Bike station observations, build a bounded ingestion-to-S3 pipeline, inspect records, replay them, and collect operational evidence. Cloud practice is optional and billable.
3. **[Homework](1.2-mon-kinesis-msk-homework.md):** Complete the instructor's original questions and exercises yourself. No AWS resources are required.

Prerequisites: Python dictionaries and JSON, basic SQL, IAM roles, S3 objects, and the [Week 5 Citi Bike ingestion walkthrough](../Week5/3.2-wed-citibike-steps.md). Read sections 1–5 before the lab, then sections 6–10 before the homework. Sections 11–12 connect the material to job responsibilities and later projects.

The [lab artifact concept map](1.3-mon-kinesis-lab/README.md) identifies which lecture concepts have runnable examples, which are prepared configuration, and which remain design exercises.

## Learning objectives

After this lesson, you should be able to:

- Trace one event from source to durable storage and identify the producer, transport, processor, and sink.
- Explain partitioning, retention, replay, consumer lag, checkpoints, and delivery guarantees.
- Choose between Kinesis, MSK, Firehose, Lambda, Glue, and Flink using workload requirements.
- Diagnose schema, permission, connectivity, and database-write failures at the correct boundary.
- Explain how event identity, database constraints, and recovery design work together.
- Evaluate freshness, throughput, security, and cost without treating “serverless” as “free when idle.”

## 1. Batch, streaming, and the pipeline mental model

**Batch processing** works on a bounded input: yesterday's files, a database extract, or one API snapshot. Batch is often simpler when daily or hourly results meet the business need.
**Streaming processing** repeatedly processes an input that can keep growing. Streaming is valuable when consumers need fresh results soon after events arrive.

A scheduled API poll is a batch retrieval. Publishing the returned observations to a stream lets downstream consumers process continuously, but it cannot make the external API more current than its own update schedule.

The instructor's assignment describes this architecture:

```text
External Citi Bike API
        │ fetched when Lambda is invoked
        ▼
Lambda producer → Kinesis Data Streams → Glue Streaming → Aurora PostgreSQL
                       │                    │                   │
                 retained events      Spark processing    queryable tables
```

- **Producer:** Creates or publishes records. Here, the ingestion Lambda fetches an API snapshot and publishes station observations.
- **Transport / retained log:** Kinesis buffers events independently of the database and retains them for replay.
- **Consumer / processor:** Glue reads the stream, validates and transforms records, and writes outputs.
- **Sink:** Aurora stores relational data for applications and queries.
- **Trigger:** Something must invoke ingestion. A manual invocation runs once; recurrence requires a scheduler, application, or another event source. A running Glue consumer does not repeatedly invoke the producer.

**Why insert a stream between Lambda and PostgreSQL?** It separates ingestion availability from database availability, permits independent consumers, and provides a replay window. The cost is another service, more operational boundaries, and duplicate/recovery behavior to manage. Direct writes can still be reasonable for a small workload with acceptable coupling.

## 2. Terminology, record grain, and time

| Term | Meaning |
| --- | --- |
| Event / observation | One fact or measurement published by a source |
| Grain | What one row represents; here, one station availability observation |
| Partition key | Value used to route records into a shard under partition-key routing |
| Shard | A unit of stream storage and throughput |
| Sequence number | A shard-scoped position assigned by Kinesis; not a business event ID |
| Retention | How long the stream keeps events available to consumers |
| Consumer lag | How far processing trails incoming data, measured in time or records |
| Checkpoint | Persisted progress and, for stateful processing, recovery state |
| Idempotency | Repeating an operation preserves its intended final effect |
| Backpressure | Downstream limits reduce the rate at which upstream work can progress |

Use an explicit event contract. For example, a station observation may contain `station_id`, `num_bikes_available`, `num_docks_available`, `last_reported`, and `ingested_at`; add a schema version and stable event identity when designing a production contract.

- Event time: When the station reported its state, represented by the source’s last_reported.
- Ingestion time: When the producer captured the observation from the API, represented by ingested_at.
- Processing time: When the consumer, such as Glue/Spark, processed the observation.
- Receipt time: When the destination received or recorded the observation, represented by received_at in the homework table.

These clocks answer different questions. “Latest observation” should normally use source event time; receipt time can place an old replayed observation ahead of a newer one. Normalize timestamps to UTC and document source clock assumptions.

Repeated API polls can return the same station state and source timestamp. Decide whether your grain is a **source observation** or a **poll snapshot**. `(station_id, last_reported)` might identify an observation if the source guarantees it; a poll snapshot needs snapshot identity as well. Include source/city in the key if station IDs are not globally unique.

**See it in code:** [Capture metadata](1.3-mon-kinesis-lab/capture.py) creates ingestion/snapshot time; [event identity](1.3-mon-kinesis-lab/contract.py) preserves source time and hashes source content; [stream inspection](1.3-mon-kinesis-lab/inspect-stream.py) exposes Kinesis arrival time alongside those payload fields. None of these timestamps is a real consumer’s processing time.

## 3. Kinesis Data Streams: storage, ordering, and scale

Kinesis is an AWS-managed streaming service with its own API. It is not Kafka, and a stream is not a broker renamed. A Kinesis stream contains shards; a Kafka topic contains partitions hosted by brokers.
- TODO: so how are brokers different from streams?
- TODO: a shard seems like a partition, how are the same/different?

Under partition-key routing, a key such as `station_id` maps records to a shard. Many keys share one shard. Reading preserves shard sequence order, but that is not a global order across the stream and does not prove source event-time order. Concurrent producers, retry timing, and partial batch failures can change arrival order. [AWS key concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html) and [PutRecord ordering](https://docs.aws.amazon.com/cli/latest/reference/kinesis/put-record.html).

### Capacity choices

- **Provisioned:** You select shard count and manage capacity changes. Useful for predictable traffic and learning how sharding affects throughput.
- **On-demand:** AWS manages shard capacity. Useful for variable traffic, with scaling behavior and quotas that still need review.
- **A hot key:** One disproportionately busy key can concentrate writes under partition-key routing. Extra overall capacity does not automatically solve a skewed key distribution.

The lab uses one provisioned shard for a handful of small records. That is a bounded teaching choice, not a production sizing recommendation. Check current capacity modes, per-stream configuration, quotas, and regional pricing before a real deployment; avoid memorizing old limit numbers. [Capacity modes](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html), [quotas](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html), and [pricing](https://aws.amazon.com/kinesis/data-streams/pricing/).

### Retention and independent consumers

Records remain available after a consumer reads them. Independent applications maintain their own positions. Shared-throughput consumers compete for shard read capacity; enhanced fan-out supplies dedicated read throughput per registered consumer, with its own costs.

The default retention is 24 hours, extendable up to 365 days. A stopped consumer can catch up only while the required records remain available. A checkpoint does not preserve expired events; extending retention later does not recover records already expired. Long-term raw storage in S3 gives you a separate repair source. [Retention](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html).

## 4. Producer choices and ingestion reliability

| Choice | What it supplies | Typical use | What you still own |
| --- | --- | --- | --- |
| Kinesis Agent | File collection and forwarding | Server log ingestion | Installation, file configuration, permissions |
| AWS SDK | API calls such as `PutRecord` / `PutRecords` | Application events, API integrations | Serialization, retry policy, partial failures, event identity |
| Kinesis Producer Library (KPL) | Optimized asynchronous production, aggregation, retries, metrics | High-throughput producers with many small events | Application integration, flush/shutdown, contract and identity |

These are producer implementations, not three competing stream-storage platforms. [Producer documentation](https://docs.aws.amazon.com/streams/latest/dev/building-producers.html).

**Batching** sends multiple records in a request. **Aggregation** combines multiple user events inside a Kinesis record. They reduce different kinds of overhead; consumers must support the chosen representation.

A successful HTTP response from `PutRecords` can still contain failed individual records. Inspect each result, retry failed entries with bounded exponential backoff and jitter, and preserve identity across retries. A timeout can occur after a write succeeded, so retrying may publish a duplicate. A newly assigned sequence number does not make it a new business observation. [PutRecords](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_PutRecords.html) and [duplicate handling](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html).

For an API producer, also define timeouts, rate-limit behavior, polling frequency, and what to do when one snapshot is incomplete. Avoid reporting “all stations ingested” based only on a successful Lambda invocation.

**See it in code:** [producer.py](1.3-mon-kinesis-lab/producer.py) maps per-record results, preserves serialized payloads, and retries only unresolved work with bounded backoff and jitter. Run [demonstrate-retries.py](1.3-mon-kinesis-lab/demonstrate-retries.py) to observe HTTP 200 with one failed entry, followed by a lost reply and duplicate storage. The [partial-success fixture](1.3-mon-kinesis-lab/fixtures/put-records-partial.json) makes the response shape inspectable.

## 5. Consumer choices: delivery versus computation

| Consumer | Suitable work | Main design concern |
| --- | --- | --- |
| Amazon Data Firehose | Managed buffered delivery to S3 and supported analytics destinations | Delivery latency, destination failures, format and file layout |
| Lambda event source mapping | Short, bounded per-record or per-batch processing | Retries, poison records, concurrency, idempotent effects |
| Glue Streaming | Managed Spark microbatch ETL | Explicit schema, checkpointing, sink throughput, continuous compute cost |
| Spark Structured Streaming on EMR | Spark-based pipelines needing runtime/connector control | Compatible connector and runtime, capacity and operations |
| Amazon Managed Service for Apache Flink | Stateful event-time processing, windows, joins | State growth, checkpoints, late events, sink guarantees |
| Kinesis Client Library (KCL) application | Custom consumer behavior on your own compute | Worker deployment, checkpoint decisions, output correctness |

**Firehose** is the current product name; older material calls it Kinesis Data Firehose. It can buffer, compress, convert supported formats, and invoke Lambda transformations. Pandas is possible inside suitable Lambda code, not a built-in Firehose execution engine. Firehose is not an arbitrary Spark runtime. Redshift delivery uses S3 staging and loading rather than inserting each event directly. [Firehose delivery](https://docs.aws.amazon.com/firehose/latest/dev/basic-deliver.html) and [transformation](https://docs.aws.amazon.com/firehose/latest/dev/data-transformation.html).

**Lambda** is a normal choice for bounded stream processing, not only a rare demonstration tool. Its event source mapping polls and batches Kinesis records; duplicate processing can occur. Adding a Spark dependency does not create a managed distributed Spark cluster. Use Glue or EMR when distributed Spark is the requirement. [Lambda with Kinesis](https://docs.aws.amazon.com/lambda/latest/dg/with-kinesis.html).

**KCL** coordinates workers, shard leases, and checkpoints using DynamoDB-backed coordination. It is not a Flink-style processing engine. **Flink** supports Java, Python, and SQL-based application patterns; select supported APIs/connectors for the managed runtime. **Spark** commonly uses microbatches; support for other processing modes depends on the source, sink, engine, and deployment. [KCL](https://docs.aws.amazon.com/streams/latest/dev/kcl.html), [managed Flink](https://docs.aws.amazon.com/managed-flink/latest/java/what-is.html), and [Spark Structured Streaming](https://spark.apache.org/docs/latest/streaming/index.html).

## 6. Glue, microbatches, and schema failures

A **microbatch** is a finite group of stream records processed as one unit of work. A nominal 30-second processing interval trades freshness for fewer scheduling and sink-write operations. It is not a promise that every result appears within 30 seconds: processing, retries, backlog, and database latency add time.

A **processing trigger** controls when work runs. An **event-time window** groups observations by when events happened. A 30-second trigger does not automatically calculate a 30-second aggregate. Watermarks help stateful engines bound late-data state; they are a chosen lateness policy, not proof that no older events will arrive.

**Schema inference** derives field names and types from observed data. **An explicit schema** declares the expected contract before processing. Explicit schemas stabilize empty-batch behavior and type interpretation, but invalid input still requires validation and quarantine. Adding optional fields may be compatible; renaming or changing a field's type requires coordinated evolution. [Glue streaming ETL](https://docs.aws.amazon.com/glue/latest/dg/add-job-streaming.html).

The classroom symptom was:

```text
BATCH 0: columns=[]
AnalysisException: UNRESOLVED_COLUMN.WITHOUT_SUGGESTION
```

This means the analyzed DataFrame did not expose the requested column. It does not establish that the source JSON was malformed. Possibilities include an empty inference batch, selecting from the wrong DataFrame, missing parsing, a nested envelope such as `data.stations`, or incorrect source options.

A practical investigation:

1. Inspect a safe raw record and verify whether it represents one station or an entire snapshot.
2. Log `printSchema()` and column names at the source and after parsing; do not repeatedly run expensive full counts for diagnostics.
3. Check whether payload fields are top-level columns or require decoding/parsing first.
4. For Glue's Kinesis connector, configure `classification`, `inferSchema`, and an explicit `schema` consistently. Its non-Avro schema option uses DDL text; other Spark APIs can use `StructType`. Do not interchange the two API shapes.
5. Handle empty batches without writing; reject or quarantine missing IDs, incompatible types, and negative counts before publication.

See [Glue Kinesis connection options](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-connect-kinesis-home.html) and [Spark `from_json`](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.functions.from_json.html). A schema declaration alone does not enforce every business rule.

**See it in files:** [contract.py](1.3-mon-kinesis-lab/contract.py) demonstrates explicit field/business validation. [Glue source options](1.3-mon-kinesis-lab/glue-source.template.json) declare a stable DDL projection without inference; they are a prepared source configuration, not an executed Glue job.

## 7. Checkpoints, replay, and delivery guarantees

A streaming checkpoint records recoverable progress and, where needed, state. Give each query a durable checkpoint location that survives worker replacement. Glue streaming uses checkpoints, not Glue batch job bookmarks. Restart with the same compatible checkpoint to recover progress; changing a starting-position option normally does not override recovered progress. [Glue streaming recovery](https://docs.aws.amazon.com/glue/latest/dg/add-job-streaming.html).

| Guarantee | Failure tradeoff |
| --- | --- |
| At-most-once | May lose work; avoids retry-driven duplicate processing |
| At-least-once | Retries unconfirmed work; duplicates are possible |
| Exactly-once effect | Each logical event contributes once within a defined correctness boundary |

An engine's exactly-once state recovery does not automatically make an external database write exactly once. Consider:

```text
1. Read batch 42.
2. Commit its rows to PostgreSQL.
3. Crash before committing streaming progress.
4. Restart and read batch 42 again.
```

Ordinary `INSERT` statements can duplicate rows. A database constraint may instead reject the repeat, which still requires an intentional retry policy. [AWS duplicate-processing example](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html).

For a reliable design, define stable event identity, enforce it at the destination, and make repeated writes idempotent. A batch ledger can help only when its identity remains valid and its progress marker commits atomically with the relevant data. Spark batch IDs alone are not durable business identity across checkpoint resets. `foreachBatch` gives you a place to implement sink behavior; it does not supply an automatic transaction across Spark and PostgreSQL. [Spark `foreachBatch` guarantees](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html#using-foreach-and-foreachbatch).

Deleting a checkpoint can replay data, reset state, or skip data depending on the new start configuration and remaining retention. Use a new isolated replay path, reconcile outputs, and prove idempotency before replacing a serving dataset.

**See the sink boundary:** The optional [PostgreSQL illustration](1.3-mon-kinesis-lab/sql/idempotency-demo.sql) applies a uniqueness constraint and conflict handling to one repeated event in a dedicated learning table. It does not solve the homework queries or establish a transaction spanning Spark and the database. PostgreSQL execution remains pending.

## 8. RDS, Aurora, and relational serving

**Amazon RDS** manages relational database operations for supported engines. It is more than a virtual server: managed backups, patching, and availability options change operational responsibilities. You still own schema design, indexes, access, query behavior, and capacity choices. You select from supported engines, not arbitrary SQL software. **Aurora** is an AWS relational database architecture with PostgreSQL-compatible and MySQL-compatible editions, not simply PostgreSQL on EC2. [RDS overview](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html) and [Aurora overview](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html).

Self-managed PostgreSQL on EC2 gives more operating-system and extension control but makes your team responsible for installation, patching, backups, and failover. Aurora supplies managed operations and distributed storage, with service-specific cost, compatibility, and operational constraints. Compatibility does not mean every extension or behavior is identical.

Separate **history** from **current state**:

- A history table preserves observations at the declared event grain.
- A latest-state table or view serves dashboards without repeatedly scanning all history.
- S3 can hold long-term raw/curated history for analytics and repair.
- A warehouse such as Redshift serves larger analytical scans; PostgreSQL often serves operational lookups and application queries.

Repeated database writes need bounded connections, transactions, and a retry policy. Opening one connection per event can overwhelm a database. Parallel Spark partitions can also create excessive concurrent writers. Measure database capacity before increasing consumer parallelism.

For SQL analysis, distinguish “average over all observations” from “average over current stations.” Frequently observed stations contribute more rows to a historical average. Window functions can select latest observations, but timestamp ties need a declared policy. These grain decisions matter more than memorizing a query.

## 9. Security, permissions, and trust boundaries

| Boundary | Contract and owner | Required protection |
| --- | --- | --- |
| External API → producer | Source owns observations; ingestion owns capture completeness | Validate external input, timeouts, bounded retries |
| Producer → Kinesis | Ingestion owns serialization and event identity | Scoped write permissions and encryption |
| Stream → consumer | Pipeline owns progress, validation, and recovery | Scoped reads, durable checkpoints, quarantine |
| Consumer → Aurora | Data team owns schema and idempotent publication | Network path, TLS, authentication, SQL authorization |
| Raw archive → analytics | Archive preserves what was received; derived datasets have separate owners | Access policy, retention, lineage, repair procedure |

**IAM database authentication** uses a short-lived signed token when opening a connection. Tokens are valid for 15 minutes; expiration does not automatically terminate an established session. Generate fresh tokens for new connections and verify TLS certificates. This avoids embedding a permanent password in code, but does not grant database privileges by itself. [IAM authentication](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.IAMDBAuth.html).

For Aurora PostgreSQL, enable supported IAM authentication, grant the database user `rds_iam`, and grant the caller `rds-db:connect` to the correct database resource-ID/user ARN. Separately grant database `CONNECT`, schema `USAGE`, table write privileges, and sequence access if needed. A cluster's ordinary management ARN is not the database-user authorization ARN. [IAM policy](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.IAMDBAuth.IAMPolicy.html) and [database account setup](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.IAMDBAuth.DBAccounts.html).

A Glue role existing is not proof of access. Private database connectivity additionally requires correct subnets, security groups, DNS, and access to Kinesis, S3, logs, and any other service the job calls. IAM authorization does not create a network route. [Glue Kinesis networking prerequisites](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-connect-kinesis-home.html).

**See the identity boundaries:** The [policy templates](1.3-mon-kinesis-lab/policies/README.md) distinguish producer writes, diagnostic reads, and Firehose source/destination access. They are permission templates, not evaluated access evidence or a replacement for service trust.

## 10. Failure model, monitoring, and costs

Trace the pipeline boundary by boundary. Record event/run/batch identity so evidence from one stage can be correlated with another.

| Symptom | Inspect | Recovery and proof |
| --- | --- | --- |
| No new API snapshots | Lambda `Invocations`, `Errors`, `Duration`, logs, trigger configuration | Restore invocation/API access; confirm new capture timestamps |
| Producer runs but stream stays quiet | Kinesis `IncomingRecords`, `IncomingBytes`, producer API results, write throttling | Repair permission/serialization/partial retries; confirm accepted writes |
| Stream receives data but results stop | Glue run status, logs, batch progress, consumer lag | Fix source/schema/compute; restart with compatible checkpoint and observe lag fall |
| Writes fail or stall | JDBC/SQL errors, Aurora connections/CPU, network and TLS settings | Restore connectivity or privileges, limit writers, retry idempotently |
| Duplicate or stale results | Observation keys, source/receipt times, replay history | Repair sink identity/latest-state logic; reconcile affected data |
| Files arrive slowly | Firehose delivery freshness/success, buffering settings, error logs | Distinguish normal buffering from failures; verify payloads after delivery |

Kinesis `GetRecords.IteratorAgeMilliseconds` describes standard reads, not the freshness of every downstream table. Track a business freshness indicator such as “age of latest successfully published source observation” too. Low lag with no new source data is still stale data. [Kinesis metrics](https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html).

| Service | Cost reasoning when arrivals stop |
| --- | --- |
| Lambda | Invocation/execution charges generally fall when invocations cease; provisioned concurrency and supporting services can still cost money |
| Kinesis Data Streams | Provisioned shard-hours continue while the stream exists; on-demand modes have their own ongoing and usage components |
| Glue Streaming | A running job uses billable compute while waiting for records; stop the job when finished |
| Aurora Serverless v2 | Scales within configured bounds; eligible versions/configurations can auto-pause at a zero-ACU minimum, but it is not universal |
| Redshift Serverless | Compute billing follows activity under its rules; stored data and backups can remain billable without queries |
| Firehose / S3 / supporting services | Delivered volume, storage, requests, logs, encryption, and networking can generate separate charges |

There is no general “serverless stops after five minutes and costs nothing” rule. Aurora auto-pause depends on engine/configuration and can be prevented by connections or features; storage charges remain when paused. Redshift has separate billing behavior. Inspect actual configuration and billing instead of assuming inactivity proves zero cost. [Aurora auto-pause](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html), [Redshift billing](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing.html), [Glue pricing](https://aws.amazon.com/glue/pricing/), and [Lambda pricing](https://aws.amazon.com/lambda/pricing/).

**See operational evidence:** [Archive inspection](1.3-mon-kinesis-lab/inspect-archive.py) compares raw counts with business identities. The [producer journal](1.3-mon-kinesis-lab/producer.py) records attempts and acknowledgements, which must still be reconciled with downstream delivery. Local failure checks in [tests/test.py](1.3-mon-kinesis-lab/tests/test.py) cover bounded recovery and ambiguous outcomes.

## 11. MSK and architecture decisions at work

**Amazon MSK** manages Apache Kafka infrastructure. Kafka clients still use Kafka topics, partitions, offsets, and consumer groups. AWS reduces broker operations, while your team still owns topic design, partition keys, retention, client security, consumer behavior, and data contracts. MSK offers provisioned and serverless deployment options with different constraints. [MSK overview](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

### 11.1. Compare responsibilities before comparing names

References in this comparison were reviewed on 2026-10-12; Kafka citations use its 4.1 documentation for the stated concepts, not as a deployment/version recommendation.

Kafka and Kinesis both let producers append events to a retained log and let independent applications read that history. This is why much of your streaming knowledge transfers. Their components divide the responsibilities differently, so the closest counterpart is sometimes several components working together.

```text
Kafka                                      Kinesis Data Streams

Cluster: brokers hosting partition logs    AWS-managed streaming service
  └─ Topic: citibike-status                  └─ Stream: citibike-status
       ├─ Partition 0                            ├─ Shard A
       └─ Partition 1                            └─ Shard B

Producer client → topic                    SDK / KPL producer → stream
Consumer group → assigned partitions       KCL application → leased shards
```

These are conceptual counterparts, not matching APIs or identical implementations. The picture assumes a conventional Kafka consumer group and a KCL-based Kinesis consumer. Lambda, Glue, and Firehose manage their consumption differently; using Kinesis does not require you to write a KCL application. [Kafka introduction](https://kafka.apache.org/41/getting-started/introduction/) and [Kinesis terminology](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html).

| Responsibility | Kafka | Kinesis | Where the analogy stops |
| --- | --- | --- | --- |
| Operate retained event storage | A cluster of brokers | The managed Kinesis Data Streams service | A broker is a server/process, not a topic or stream; AWS hides the hosting infrastructure |
| Name one logical event collection | Topic | Stream | Similar role, different configuration and APIs |
| Divide the log for ordering and parallel reads | Partition | Shard | Shards also define provisioned capacity; capacity/scaling mechanics differ |
| Route related events | Record key plus producer partitioning policy | Partition key under partition-key routing | Hash algorithms and routing configuration differ; do not expect matching bucket assignments |
| Locate a stored record | Topic + partition + offset | Stream + shard + sequence number | Neither identifies a unique business observation; sequence numbers are not arithmetic offsets |
| Track recoverable progress | Committed partition offsets for a consumer group | KCL checkpoints associated with shard leases | An offset/sequence position identifies data; committing/checkpointing decides recovery progress |
| Share work within one logical subscriber | Consumers with the same `group.id` | Workers using the same KCL application identity/coordination state | Kafka supplies group coordination; KCL uses AWS-backed coordination outside the stream |
| Read the full dataset independently | A separate consumer group | A separate consumer application | Kinesis applications can share read capacity; enhanced fan-out is a distinct throughput feature |
| Keep records after processing | Topic retention policy | Stream retention policy | Kafka also supports log compaction; Kinesis retention is not a latest-value-per-key compaction policy |

References for the mapping: [Kafka partition distribution](https://kafka.apache.org/41/implementation/distribution/), [Kafka consumer positions and groups](https://kafka.apache.org/41/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html), [KCL concepts](https://docs.aws.amazon.com/streams/latest/dev/kcl-concepts.html), and [Kafka topic operations and compaction](https://kafka.apache.org/41/operations/basic-kafka-operations/).

**Enhanced fan-out is not a consumer group.** It supplies dedicated Kinesis read throughput for a registered consumer. Worker assignment and recovery are separate concerns, handled by KCL or the chosen integration.

**Stream versus broker:** Both participate in getting records from producers to consumers, but compare at the same level. A Kafka broker hosts partition replicas for potentially many topics. A Kinesis stream is the named dataset you write/read, so its closer counterpart is a Kafka topic. The Kinesis service handles managed storage and serving responsibilities that Kafka brokers provide within a cluster.

### 11.2. KCL versus the Kafka consumer client, coordinator, and management tools

KCL is a library used by your consumer application. It discovers shards, coordinates worker ownership through leases, supports checkpoints, and helps recovery after worker failure. Its closest functional comparison is **Kafka's consumer client working with consumer-group coordination**, rather than a single Kafka management product. [KCL responsibilities](https://docs.aws.amazon.com/streams/latest/dev/kcl.html).

| Job | Kafka side | Kinesis/KCL side |
| --- | --- | --- |
| Fetch records and participate in coordinated consumption | Consumer client | KCL worker/record processor |
| Track which workers own which log divisions | Group coordinator and assignment protocol | KCL shard leases and worker coordination |
| Save progress for restart | Offset commits, normally stored in Kafka's internal offsets topic | KCL checkpoints in DynamoDB-backed metadata |
| Reassign after worker failure or membership change | Consumer-group reassignment/rebalancing | Lease reassignment and KCL load balancing |
| Operate or inspect the platform | Admin API, CLI tools, management dashboards | AWS console, CLI, APIs, and CloudWatch |

These rows compare responsibilities; the assignment algorithm and protocol vary by client/runtime version. Your business code still decides when processing is complete and when progress may safely advance. [Kafka coordination and offset storage](https://kafka.apache.org/41/implementation/distribution/) and [KCL metadata](https://docs.aws.amazon.com/streams/latest/dev/kcl-concepts.html).

If by “Kafka manager” you mean a dashboard/admin tool, that tool helps you inspect and configure the system; it does not replace the consumer client's coordination behavior. If you mean **KRaft**, that is Kafka's cluster metadata/controller mechanism, another responsibility again. Older Kafka material uses ZooKeeper for cluster coordination; Kafka 4.x uses KRaft. Neither is the direct counterpart of KCL. The consumer **group coordinator** and cluster **controller** have different jobs. [Kafka KRaft controller roles](https://kafka.apache.org/41/operations/kraft/) and [KRaft migration/version boundary](https://kafka.apache.org/41/getting-started/upgrade/).

### 11.3. Producer, connector, and processing tools

| Need | Kafka ecosystem | Kinesis/AWS ecosystem | Important distinction |
| --- | --- | --- | --- |
| Publish application events | Kafka producer client | AWS SDK or KPL | KPL adds aggregation/production helpers; it is not the stream itself |
| Integrate external systems | Kafka Connect source/sink connectors | Firehose for supported delivery, agents or SDK integrations for ingestion | Connect is a connector framework; Firehose is a managed delivery service, not a universal Connect replacement |
| Write custom consumers | Kafka consumer clients | KCL or direct Kinesis APIs | Direct API reads leave coordination and recovery responsibilities to your code |
| Apply stateful transformations | Kafka Streams, Flink, Spark with appropriate connectors | Flink, Glue Streaming, Spark with appropriate connectors | KCL is not the counterpart of Kafka Streams; Streams is a processing library |
| Define event schema compatibility | A chosen schema registry and serializers | A chosen schema registry, including AWS Glue Schema Registry with supported integrations | Neither a topic nor a stream automatically validates every payload/business rule |

A Kafka producer can use idempotent production to protect against certain client retries and transactions to coordinate Kafka writes. That does not deduplicate arbitrary application resends or automatically include an external PostgreSQL transaction. Kinesis `PutRecords` requires checking individual results; the lab's [producer](1.3-mon-kinesis-lab/producer.py) preserves event identity through retries but cannot promise duplicate-free storage. [Kafka producer guarantees](https://kafka.apache.org/41/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html) and [Kinesis partial results](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_PutRecords.html).

Schema registries are also not exclusive to one platform: AWS Glue Schema Registry supports integrations with both Kafka/MSK and Kinesis. Compatibility enforcement depends on configuring the supported serializers/deserializers and consumers; merely creating a registry does not validate arbitrary raw writes. [Glue Schema Registry integrations](https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html).

Kafka Connect handles integration tasks; Kafka Streams supplies stateful processing APIs. Do not treat either as another name for the broker. Sources: [Kafka Connect](https://kafka.apache.org/41/kafka-connect/user-guide/) and [Kafka Streams introduction through the quickstart](https://kafka.apache.org/41/getting-started/quickstart/).

### 11.4. Trace the same Citi Bike workload in both systems

Suppose station observations feed two applications: **dashboard updates** and **historical archiving**.

- **Kafka:** Publish to topic `citibike-status`, keyed by `station_id`. Put dashboard workers in one group and archive workers in a different group. Within each conventional group, partitions are assigned among workers; the two groups consume independently.
- **Kinesis with KCL:** Publish to stream `citibike-status`, using `station_id` as the partition key. Give dashboard and archive separate application identities/coordination state. Workers within each application coordinate shard leases. In our actual lab, Firehose provides archival consumption without you deploying KCL workers.

Putting both Kafka applications in the **same** group can split the records between them when the intent was for both to receive all records. Accidentally sharing KCL coordination state between logically independent applications has a similar ownership problem. Independent subscription and additional worker capacity are different design decisions.

Now let the dashboard sink commit an observation to PostgreSQL and crash before saving its progress. Restarting from an older committed offset or checkpoint can write that observation again. The same destination identity/idempotency problem appears in both systems. The [SQL illustration](1.3-mon-kinesis-lab/sql/idempotency-demo.sql) demonstrates one database boundary; it does not implement Kafka transactions or a KCL checkpoint. [Kafka external-write recovery](https://kafka.apache.org/41/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) and [Kinesis duplicate recovery](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html).

### 11.5. Pitfalls that become clearer through comparison

- **A hot key stays a routing problem.** With the chosen keyed routing, one busy station/tenant can concentrate traffic in one partition/shard. More workers alone do not divide that key's ordered log. Decide whether the ordering requirement allows changing the key.
- **More workers do not automatically mean more source parallelism.** In a conventional Kafka group, partition assignments bound active source readers. KCL similarly assigns shard ownership; processing inside a worker can have additional concurrency, but it still needs safe progress tracking.
- **Scaling changes routing.** Increasing Kafka partitions can change key-to-partition mappings; existing records remain in their original partitions. Kinesis resharding creates parent/child shard relationships. KCL handles that lineage during consumption; a basic manual reader must account for it explicitly. [Kafka partition expansion](https://kafka.apache.org/41/operations/basic-kafka-operations/) and [Kinesis resharding](https://docs.aws.amazon.com/streams/latest/dev/kinesis-using-sdk-java-resharding.html).
- **Positions are not event IDs.** A producer resend can receive a different offset/sequence number for the same business observation. Do not use a transport position as the only deduplication identity when duplicates originate before storage.
- **A saved position cannot recover expired data.** Retention must cover outage plus catch-up time, or another archive must support repair. Neither platform is automatically a permanent historical store.
- **Exactly-once has a scope.** Kafka transactions can coordinate processing between Kafka topics under the required producer/consumer settings. External database effects still need sink-specific coordination or idempotency. A KCL checkpoint likewise does not make a database write exactly once. [Kafka transactional processing boundary](https://kafka.apache.org/41/design/design/).

### 11.6. Choose using requirements, not name matching

Compare **Kafka as a technology**, **MSK as an AWS-managed Kafka offering**, and **Kinesis as an AWS streaming service**. Self-managed Kafka and MSK have different operational burdens; “Kafka requires running all brokers yourself” is not a fair comparison with Kinesis.

Use the table below as a starting point, then measure peak bytes/events, skew, replay needs, independent consumer count, latency, networking, and total cost. The presence of similar concepts does not make applications portable between their APIs. For an interview, explain the shared retained-log model first, then identify one guarantee, operational boundary, or ecosystem requirement that changes your choice.

| Decision | Favor Kinesis when… | Favor MSK when… |
| --- | --- | --- |
| Ecosystem | AWS-native integration is the main need | Existing Kafka applications/connectors are important |
| Client model | Kinesis APIs and shard-based consumption fit the team | Kafka APIs and consumer-group behavior are required |
| Operations | A managed AWS stream fits the operating model | Kafka compatibility justifies its configuration and networking |
| Required log behavior | Time-retained replay fits the requirement | Kafka log compaction or Kafka-to-Kafka transactions are explicit requirements |
| Deployment portability | AWS service integration fits the deployment boundary | The Kafka protocol/ecosystem across deployment environments is a requirement |
| Cost | Measured stream/consumer costs fit the workload | Measured cluster/serverless/client costs fit the workload |

The mappings above describe comparable responsibilities, not interchangeable implementations. Neither service removes the need to define event identity, recovery progress, and external sink correctness.

For the homework's 10,000 stations reporting every 30 seconds, the average arrival rate is approximately **333 observations/second**, or **28.8 million observations/day**. This is a planning estimate, not a tested capacity result. Synchronized station reports can create much larger bursts. Size using bytes, peak rate, key skew, retention, consumer count, processing time, and database write capacity.

At work, turn those quantities into a freshness objective, replay requirement, cost estimate, and incident runbook. In an interview, explain the requirement first, choose a design, identify its failure case, and describe how you would verify recovery. Useful prompts: Why a stream instead of direct writes? What survives a database outage? What makes a retry safe? What evidence distinguishes source silence from consumer failure?

## 12. Related classroom ideas: dashboards, ML, and RAG

These were proposed extensions in the original notes, not required completed class work:

- **Streamlit on ECS/Fargate:** A dashboard is a serving application. Fargate supplies managed container compute; it is not the stream processor. Query a curated/current-state dataset with a defined freshness target.
- **SageMaker AI and ML pipelines:** Curated historical data can feed training; deployed inference can enrich new observations. Monitor model quality separately from pipeline freshness and schema quality.
- **RAG:** Retrieval-augmented generation retrieves relevant external material and supplies it as context to a model. A directory alone does not implement retrieval: parsing, indexing, permissions, retrieval quality, and freshness all matter.
- **Vector databases/indexes:** Store/search embeddings using similarity. They are not simply databases formatted for AI rather than humans, and a vector database is not mandatory for every RAG design.
- **MLflow and MLOps:** Experiment tracking, model packaging/registry, deployment, and monitoring support a model lifecycle. They do not replace ingestion contracts, data lineage, or validation.

These distinctions help identify the ownership boundary between data engineering, application engineering, and ML engineering without adding extra homework.

## Requirements, invariants, and production considerations

Before deploying, write down the acceptable freshness, expected peak volume, recovery window, authoritative data, retention policy, and budget. For this station example, preserve these invariants:

- Every accepted observation has a valid station identity, schema version, and interpretable time.
- Reprocessing the same observation does not unintentionally multiply its final contribution.
- An older replay cannot silently replace newer current state.
- Invalid records remain traceable without blocking unrelated valid records indefinitely.
- Recovery completes before source retention expires, or a durable archive supports repair.

Production delivery also needs reviewed infrastructure/configuration, deployment and rollback procedures, a schema compatibility policy, load/replay tests, and named operational owners. A successful small lab demonstrates mechanics; it does not establish production readiness.

## Data quality, testing, and evidence

Test the contract with valid, empty, malformed, duplicate, late, missing-field, negative-count, and zero-capacity inputs. Reconcile accepted source counts with valid/rejected output counts by a defined interval; compare observation identities rather than S3 object counts.

| Evidence | Expected outcome | Current status |
| --- | --- | --- |
| Lecture/reference review | Homework concepts and original topics covered; claims linked to primary sources | Reviewed 2026-10-12 |
| Static document checks | Valid fences, links, sample JSON, and shell syntax | See repository coverage record |
| Kinesis/Firehose/S3 lab | Publish/read/archive/replay observations with saved evidence | Not executed |
| Glue/Aurora integration | Schema, network, authentication, idempotent write and restart verified | Not executed |
| Load, outage, and billing experiments | Freshness/recovery/budget requirements measured | Not executed |

## Common pitfalls

- Calling a stream a broker, or assuming Kinesis speaks the Kafka protocol.
- Treating a processing interval as an event-time aggregation window.
- Assuming a checkpoint makes ordinary database inserts exactly once.
- Assuming an explicit schema validates all business rules.
- Using receipt time as source event time, or sequence numbers as business event IDs.
- Treating a one-time API fetch as a recurring producer.
- Leaving continuous compute running because the service is called serverless.

## Knowledge check and completion checklist

- [ ] Trace one station observation through every component and identify its grain.
- [ ] Explain how two independent consumers read the same stream.
- [ ] Map topic/partition/consumer group to stream/shard/KCL application, and explain why a broker, KRaft controller, and KCL library are different kinds of components.
- [ ] Explain what happens during an outage longer than retention.
- [ ] Diagnose `columns=[]` without assuming malformed JSON.
- [ ] Draw the database-commit/checkpoint failure timeline and propose safe recovery.
- [ ] Distinguish historical average, latest observation, and current dashboard state.
- [ ] Explain both IAM authorization and network connectivity for Glue → Aurora.
- [ ] Identify which resources keep charging while input is idle.
- [ ] Complete the separate homework in your own words and code.

## Homework concept map

| Homework | Lecture sections |
| --- | --- |
| Q1–4: architecture, producer/consumer, decoupling | 1–5 |
| Q5: retention and recovery | 3, 7 |
| Q6–8: microbatches and schemas | 6 |
| Q9–10: checkpoints and delivery | 7 |
| Q11–12: Aurora and authentication | 8–9 |
| Q13–14: costs and troubleshooting | 10 |
| Python/SQL exercises | 2, 6, 8; implement your own functions/queries |
| Q15: design challenge | 7–11 and production invariants |
