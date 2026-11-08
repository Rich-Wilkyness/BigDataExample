# Open Table Formats, ACID Transactions, and Reliable Data Pipelines

> Status: Expanded lecture study guide  
> Level: Beginner to intermediate, with production considerations  
> Applies to: Data lakes, lakehouses, batch and streaming pipelines  
> Example status: Illustrative walkthroughs; no executable lab included  
> Evidence status: Documentation review and static checks only  
> Last reviewed: 2026-11-03

## Overview

A data pipeline needs to publish complete changes, keep readers on a consistent view, accommodate changing schemas, and protect the information it stores. These responsibilities connect open table formats, ACID transactions, data catalogs, governance, data contracts, and operational reliability.

## Learning objectives

After studying these notes, you should be able to:

- Distinguish object storage, file formats, table formats, catalogs, and processing engines.
- Explain how a table commit protects readers during a failed write.
- Describe the four ACID properties and the limits of their guarantees.
- Compare Iceberg, Hudi, and Delta Lake using workload requirements.
- Explain table schema evolution and Avro/Protobuf compatibility.
- Connect catalogs, lineage, PII protection, and producer–consumer contracts.
- Diagnose pipeline failures using the nine Rs discussed in class.

## 1. Mental model: from files to tables

### Storage, file format, table format, and engine

| Layer | Question it answers | Examples |
| --- | --- | --- |
| Storage | Where do the bytes live? | Amazon S3, Azure Data Lake Storage, Google Cloud Storage |
| File format | How are records encoded inside a file? | Parquet, Avro |
| Table format | Which files and metadata form a valid table version? | Apache Iceberg, Apache Hudi, Delta Lake |
| Catalog | How do tools find named tables and their metadata? | AWS Glue Data Catalog; catalogs used by lakehouse platforms |
| Processing engine | What executes reads, joins, transformations, and writes? | Spark, Flink, compatible SQL engines |
| Governance layer | Who may access which data, and under what policies? | Platform permissions, access policies, auditing |

Parquet organizes data by column, which helps analytical queries read selected fields efficiently. A directory of Parquet files does not by itself define a transaction protocol for replacing several files together. A table format adds the metadata and rules that let compatible tools interpret those files as a changing table.

The comparison is therefore **Parquet as a file format, with Iceberg, Hudi, and Delta Lake as table management choices**. Iceberg tables can store Parquet data; these technologies can work together.

```text
Producer: API or database
        |
        v
Processing engine: validation and transformation
        |
        v
Table format: publish a valid table version
        |
        v
Object storage: data files and metadata
        ^
        |
Consumer engine resolves the named table through its catalog,
then reads the files belonging to the selected table version.
```

This is a conceptual flow. The catalog and storage are separate dependencies, and their exact interaction depends on the table format and catalog implementation.

- TODO: I still don't understand table formats... it's like txt vs md vs docx, but more like excel vs google sheets vs csv. I need to understand the difference between a file format and a table format, and how they work together. 

### Why a folder overwrite can fail

Suppose an analytical table contains ten files. A job deletes the existing files and starts writing replacements, but crashes after writing six. A reader scanning the folder may see an incomplete dataset. Successful individual file writes do not make the ten-file replacement atomic.

S3 provides strong read-after-write consistency and atomic updates for individual keys. It does not make a collection of ordinary object writes into one atomic transaction across keys. A table protocol supplies the additional coordination needed for table publication. See the [S3 consistency model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html#ConsistencyModel).

## 2. Apache Iceberg: snapshots and atomic publication

Iceberg is an open table format for analytical datasets. A **snapshot** describes a committed table state; it is not necessarily a full physical copy of the dataset. Different snapshots can reference unchanged files in common.

A simplified metadata path is:

```text
Catalog entry -> table metadata -> selected snapshot
              -> manifest list -> manifests -> data/delete files
```

Manifests describe files and information used to plan reads. The metadata determines table membership; reading every file found in the storage directory bypasses that definition. The precise layout is defined in the [Iceberg specification](https://iceberg.apache.org/spec/).

### Illustrative Citi Bike write failure

Assume a new batch contains 100,000 station observations. One row represents one station at one source observation time.

1. Readers are using committed snapshot A.
2. Spark writes candidate files for the new batch.
3. The job crashes after writing files containing 60,000 observations, before committing.
4. Those files are absent from the committed snapshot, so table readers continue seeing A.
5. A successful retry writes and validates its output, then publishes a new metadata version through the configured commit mechanism.
6. New reads can select snapshot B; reads already using A retain a consistent view.

Publication changes the authoritative table state atomically. Uncommitted files can remain in storage until safe cleanup. Concurrent writers must validate their changes; conflicts may require a retry. See [Iceberg reliability](https://iceberg.apache.org/docs/latest/reliability/).

The example explains atomic visibility. It does not establish that a retry is duplicate-free: if the commit succeeded but its acknowledgment was lost, blindly appending the batch again can duplicate records. The pipeline also needs batch identity, record keys, and an idempotent publication strategy.

### Time travel, updates, and deletes

- **Time travel:** Read an available historical snapshot to investigate earlier results.
- **Rollback:** Change the table's current state to an available earlier version through supported operations; review what happens to later valid changes before doing this.
- **Update/delete:** A compatible writer can rewrite affected files or use supported row-level change mechanisms. This depends on the engine and format version.
- **Retention:** Historical queries depend on retaining the required metadata and files. Time travel is not an independent backup.

Snapshot expiration and orphan-file cleanup have different purposes. Expiration removes retained history according to policy; orphan cleanup removes files no longer referenced by valid metadata. A cleanup window must account for active writes and readers. See [Iceberg maintenance](https://iceberg.apache.org/docs/latest/maintenance/).

## 3. Iceberg, Hudi, and Delta Lake

All three manage changing analytical tables over files, but their designs and surrounding ecosystems differ. Compatibility depends on the engine, connector, table features, and versions used.

| Technology | Useful concepts to understand | Questions to investigate |
| --- | --- | --- |
| Iceberg | Snapshots, manifests, field IDs, schema and partition evolution | Can every required engine read and write the chosen table features? |
| Hudi | Commit timeline, record keys, upserts, incremental queries, Copy on Write and Merge on Read | How frequent are updates, and who operates compaction and concurrency control? |
| Delta Lake | Transaction log, versioned table state, schema enforcement, optimistic concurrency | Do the required connectors support the chosen protocol and features? |

Hudi's **Copy on Write** rewrites affected base files when applying changes. **Merge on Read** can place changes in log files and merge them with base files during snapshot reads, with compaction combining them later. This shifts work between writing, reading, and maintenance; a read-optimized view can omit changes not yet compacted. See [Hudi concepts](https://hudi.apache.org/docs/concepts/).

Delta Lake records table changes in its transaction log. Its optimistic concurrency process reads relevant state, stages changes, and validates before committing; conflicting operations can fail and require handling. See [Delta Lake concurrency control](https://docs.delta.io/concurrency-control/).

Start selection with requirements: append versus update volume, consumer freshness, supported engines, recovery needs, governance integration, maintenance capacity, and measured cost. A frequent-upsert workload makes Hudi worth investigating; multi-engine analytics makes connector interoperability especially important; an existing Delta environment makes its supported workflows relevant. These are investigation paths, not universal rankings.

## 4. ACID transactions

A **transaction** groups operations into a unit with defined commit and failure behavior. ACID describes four properties of that unit.

| Property | Meaning | Question it answers | Illustrative example |
| --- | --- | --- | --- |
| Atomicity | All changes in the transaction commit together, or none commit | Did the complete operation become committed? | A bank transfer cannot commit only the debit |
| Consistency | Committed transactions preserve defined integrity rules | Does the result satisfy the enforced rules? | A constrained account cannot have a negative balance |
| Isolation | Concurrent transactions interact according to defined isolation guarantees | What can another transaction observe or change? | Two reservations compete for one seat |
| Durability | Committed changes survive failures covered by the system's guarantees | Will the committed result survive recovery? | A committed order remains after a supported restart |

### Correcting common definitions

**Atomicity** concerns a transaction's all-or-nothing outcome. Interaction between concurrent transactions belongs to isolation.

**Consistency** concerns defined invariants, such as uniqueness, valid references, and allowed balances. It does not mean every distributed replica always has the same value at the same instant. It also does not make an incorrect transformation correct: validly storing the wrong unit of measurement can still satisfy every database constraint.

**Isolation** does not mean transactions never affect shared data. They can update the same records; the system controls their interaction. Different isolation levels permit different anomalies and concurrency tradeoffs.

**Durability** has an explicit failure boundary. It is not a promise to survive every catastrophe or administrator deletion. Logging, persistent storage, replication, and backups address different recovery risks.

The [PostgreSQL transaction tutorial](https://www.postgresql.org/docs/current/tutorial-transactions.html) explains commit and rollback; its [isolation documentation](https://www.postgresql.org/docs/current/transaction-iso.html) explains concurrent behavior.

### Small database example and transaction scope

Imagine two operations: subtract $100 from account A, then add $100 to account B. They belong in one transaction. A failure must leave neither committed alone. Constraints or application logic must also enforce the intended rules, such as sufficient funds and conservation of the transferred amount.

In a lakehouse, identify the boundary just as carefully. An atomic update to one table does not automatically include a second table, a Kafka offset, an email, or a dashboard refresh. Multi-table and cross-system behavior requires explicit platform support or a publication/recovery design.

### Which systems support ACID?

The original lecture named PostgreSQL, MySQL/InnoDB, SQL Server, Oracle, SQLite, MongoDB, Couchbase, Aerospike, Spanner, CockroachDB, DynamoDB, BigQuery, Snowflake, Redshift, Hive, Kafka, Spark, and the three table formats. Use these as systems to investigate rather than treating a “Yes” label as an identical guarantee.

| Category | What to verify |
| --- | --- |
| Relational and distributed databases | Storage engine, isolation level, constraints, replication behavior, and transaction boundary |
| NoSQL systems | Single-record versus multi-record APIs, supported versions, limits, and regional scope |
| Cloud warehouses | Supported transactional statements, DDL behavior, isolation, and restrictions |
| Open table formats | Table/engine support, atomic commit mechanism, conflict handling, and constraint enforcement |
| Hive and Kafka | Required transactional configuration and the exact table or messaging boundary |
| Spark | Guarantees of its source, sink, connector, and checkpoint/commit integration |
| Plain Parquet files and ordinary object storage | No general table transaction protocol supplied by the files alone |

Schema validation is not equivalent to enforcing primary keys, foreign keys, or every business rule. Verify each invariant where the selected stack actually enforces it.

### ACID consistency and distributed consistency

| Meaning | Concern | Example |
| --- | --- | --- |
| ACID consistency | Validity of committed data under defined rules | A unique key remains unique |
| Distributed consistency | Visibility and ordering of operations across clients or replicas | Whether a read can return a value older than a completed write |

A system can support transactions while offering replica reads with lag under a particular configuration. Identify which read path and consistency guarantee the consumer uses.

## 5. Schema evolution: tables, Avro, and Protobuf

A **schema** defines a record's structure, including fields and types. **Schema evolution** changes that structure over time. Storage compatibility, message decoding compatibility, and application meaning must all be considered.

TODO: can we get a code/schema example? 
TODO: how does schema evolution work with Iceberg, Avro, and Protobuf? Why do we add them to a pipeline? Like here:
```
RAW      - GCS + BigQuery raw  (market= / load_date=)
     |  [GCS finalize -> Pub/Sub -> Cloud Function schema-drift check]
     |  [CIRCUIT BREAKER: quality thresholds per market -> open/closed]
     v
CURATED  - PySpark (Dataproc) + BigQuery SQL
     |  retry / quarantine / partial-load / full-failure per stage
     |  [dbt: staging -> intermediate -> marts]
     v
SEMANTIC - BigQuery marts + Apache Iceberg via BigLake
     v
CONSUMERS  risk & credit . product . market partners . Looker
```

### Table changes and downstream consumers

| Change | Storage concern | Consumer concern |
| --- | --- | --- |
| Add a nullable column | How are historical rows represented? | Can consumers tolerate missing values? |
| Rename a column | Does the format preserve field identity? | Existing SQL still references the old name |
| Drop a column | What happens to old files and retained history? | Consumers may still require the field |
| Widen a numeric type | Is the change supported by the engine and format? | Consumers may assume a smaller range |
| Change integer to string | It may require migration rather than an in-place change | Arithmetic, validation, and joins can break |

Iceberg uses field IDs to track column identity and supports specified schema changes without rewriting existing data files. Partition evolution lets new writes use a changed partition specification while older files retain their original organization. This does not automatically reorganize historical files. See [Iceberg evolution](https://iceberg.apache.org/docs/latest/evolution/).

**Physical compatibility is insufficient:** renaming a column safely in metadata can still break a dashboard query. Adding a field does not populate historical observations with facts that were never collected. Specify `NULL` and backfill behavior explicitly.

### Avro: writer and reader schemas

TODO: are open table formats just applying a format to a table or file that allows for it? like Redshift, BigQuery, Databricks, etc. can be formatted in a specific way? like how a car can be red, green, blue, etc, it's just a paint we apply to the car? but that just means the default white is not there anymore? like if the car is red, it's not white?

Avro serialization uses schema resolution between the writer's schema and the reader's schema. If a reader expects a field absent from the writer's record, a suitable reader-side default permits resolution; without a default, that missing field can cause an error. A nullable type alone does not supply the reader default.

For example, a new reader adds a nullable `source_version` field with default `null` so it can interpret old records lacking the field. This does not mean the writer can omit required encoding arbitrarily. See the [Avro schema resolution rules](https://avro.apache.org/docs/1.12.0/specification/#schema-resolution).

### Protobuf: stable field numbers

Protobuf's binary encoding identifies fields by number. Preserve existing numbers, reserve removed field numbers and names, and avoid reusing a number for a new meaning. Adding a field can be binary-compatible while still requiring application changes. JSON representations have additional compatibility considerations. See the [Protobuf schema update guide](https://protobuf.dev/programming-guides/proto3/#updating).

### Compatibility and a safe change sequence

- **Backward compatibility:** A new consumer can read data written with the old schema.
- **Forward compatibility:** An old consumer can read data written with the new schema.
- **Full compatibility:** Both directions work under the selected compatibility policy.

These labels must be tied to the serialization format, registry policy, and supported schema history. Test retained historical records as well as the latest version.

For a renamed field, consider an expand/migrate/contract sequence: introduce the new field, define how both fields agree, update consumers, backfill if needed, confirm migration, then retire the old field. Version the contract and retain a rollback plan. A registry can validate structural compatibility; it cannot infer that a field changed from seconds to milliseconds without a documented semantic rule.

## 6. Data catalogs, metadata, and lineage

| Concept | Meaning | Example question |
| --- | --- | --- |
| Catalog | Named inventory that helps tools discover and resolve datasets | Where is `silver.station_observations`? |
| Table metadata | Information describing a table's structure and state | Which schema and files belong to this version? |
| Lineage | Recorded relationships between sources, transformations, and outputs | Which source batch produced this daily summary? |
| Governance | Ownership, policies, access, auditing, and lifecycle decisions | Who can read sensitive columns? |

The [AWS Glue Data Catalog](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html) stores dataset metadata such as schema and location. Crawlers can discover metadata; catalog entries can also be defined explicitly. A crawler's inference is not an approved data contract.

In AWS and Databricks workflows, distinguish discovery from enforcement: registering a table does not establish every permission or quality rule. Also distinguish the table name from the underlying storage path. In Iceberg, the configured catalog participates in resolving the table and its current metadata; catalog capabilities and availability matter to commits.

Lineage should connect source capture, transformation code/version, run identity, and output version. A pipeline owner needs this information to find affected consumers after a bad batch. A table schema alone cannot reconstruct the transformation history.

## 7. PII and data governance

**Personally Identifiable Information (PII)** is information that identifies an individual or can be linked to an individual in context. Direct identifiers include names and personal contact details; combinations such as precise location and timestamps can also create identification risk. NIST discusses context-based protection in its [PII confidentiality guide](https://csrc.nist.gov/pubs/sp/800/122/final).

For the station examples here, use public station observations without rider identities. A separate hypothetical dataset containing rider accounts or individual trip histories would need its own privacy assessment; do not assume that example data exists in this repository.

| Control | Purpose | Limit to understand |
| --- | --- | --- |
| Data minimization | Collect only information needed for the purpose | Unneeded copies increase exposure |
| Masking | Hide values in a particular display or output | The underlying data may remain accessible elsewhere |
| Encryption | Protect bytes in storage or transit | Authorized readers can still expose decrypted data |
| Pseudonymization | Replace identifiers with controlled substitutes | Linkability or a lookup mapping can preserve identification risk |
| Role-based access and least privilege | Limit access to necessary people and processes | Catalog permissions and direct storage access must align |
| Retention and deletion controls | Manage how long data and copies remain | Current-table deletion may leave historical copies |

Hashing an identifier does not automatically anonymize it. Protect mappings, backups, exports, logs, rejected-record storage, and notebook outputs as appropriate to their contents.

### Why snapshots complicate deletion

Removing a person's row from the current table view can leave it in older files, historical snapshots, storage versions, backups, and downstream extracts. A deletion workflow must identify those copies and apply the organization's authorized retention and erasure rules. Coordinate snapshot expiration and file cleanup with recovery needs; do not delete files manually from under active metadata.

A recovery procedure must also prevent restoring previously removed sensitive records into active use. Retention, access restrictions, and restoration procedures belong to the dataset lifecycle.

## 8. Producer–consumer data contracts

A **data contract** states what a producer promises and what consumers may rely on. It covers structure and meaning, with ownership, quality, freshness, and change expectations. Machine-readable specifications can support validation and monitoring, but an unused contract document cannot enforce a promise. See the [Data Contract Specification](https://datacontract-specification.com/).

### Illustrative station-observation contract

The following is a proposed teaching contract, not an assertion about all Citi Bike feeds or the existing pipeline.

| Contract element | Example agreement |
| --- | --- |
| Owner | Ingestion team owns source capture; curated-data team owns the published Silver table |
| Grain | One station at one source observation timestamp |
| Identity | `(station_id, observed_at)` identifies an observation; revisions need an explicit policy |
| Types and meaning | Station ID is a string; available-bike count is a nonnegative integer; observation timestamp is UTC |
| Missing values | Missing observations are tracked; unknown counts remain unknown rather than becoming zero |
| Quality | Required keys are present; duplicate keys and invalid counts are detected before publication |
| Freshness | An illustrative objective is publication within five minutes of observation; measure source delay separately |
| Compatibility | Breaking type or meaning changes require a versioned migration and consumer notice |
| Failure handling | Invalid records are quarantined with safe error details and an accountable owner |

If a producer changes a count from integer `12` to string `"unknown"`, a consumer expecting arithmetic can fail or silently lose records through casting. The producer should publish a compatible representation or coordinate a migration; the consumer should validate input and report the violation. Silent coercion hides a contract problem.

A complete contract also specifies units, time zones, late-arrival handling, source corrections, empty batches, retention, access classification, and deprecation expectations. Consumer teams remain responsible for using the dataset according to those meanings.

## 9. The Rs of data engineering

The Rs are a classroom organizing framework, not one universally standardized list. The original lecture emphasized six principles and added three more; all nine are useful operational questions.

| Principle | Meaning | Illustrative Citi Bike application |
| --- | --- | --- |
| Reliability | Produce correct results consistently within agreed requirements | Scheduled observations arrive and pass quality checks |
| Resilience | Withstand disruption and continue or recover acceptably | Durable captured data absorbs a temporary consumer outage |
| Recoverability | Restore data and processing after failure | Repair a bad transformation and replay retained source captures |
| Reproducibility | Obtain consistent results from recorded inputs, code, and configuration | Rebuild a historical summary using the same source versions |
| Reusability | Share useful datasets and components across consumers | One validated station dimension serves multiple analyses |
| Responsiveness | Meet the consumer's delivery and latency requirements | A dashboard receives updates within its agreed freshness window |
| Robustness | Handle malformed input and edge cases predictably | Invalid counts are quarantined without corrupting valid output |
| Repeatability | Execute a defined process consistently | A documented recovery procedure has predictable steps |
| Reconciliation | Account for accuracy and completeness across boundaries | Source records reconcile to accepted and rejected records |

Retries contribute to reliability only when repeated execution is safe. Retention supports resilience only while the data needed for replay remains available. Recovery from an old snapshot may restore availability while losing later valid changes; quantify that consequence.

**Reproducibility** emphasizes the result and its recorded inputs. **Repeatability** emphasizes consistent execution of the procedure. Their usage overlaps across disciplines; state the intended meaning when discussing them.

ACID protects a transaction boundary. The Rs evaluate the pipeline's wider behavior. A perfectly atomic table commit can still publish an incorrect calculation or deliver correct data too late.

## 10. Requirements, ownership, and recovery walkthrough

### Proposed invariants and ownership

For the illustrative pipeline, keep source captures as the replay authority under an explicit retention policy. Treat Silver observations and Gold summaries as derived datasets. Assume multiple batches and retries, without claiming a production scale or measured throughput.

| Boundary | Owner's responsibility | Invariant or consumer expectation |
| --- | --- | --- |
| Source to Bronze | Ingestion owner records capture and source timing | A failed capture is visible; missing data is not fabricated |
| Bronze to Silver | Transformation owner validates schema and observation identity | A retry does not silently duplicate accepted observations |
| Silver publication | Writer and catalog/storage operators maintain the commit path | Readers select a complete committed table version |
| Silver to Gold | Analytical owner defines aggregation grain and correction policy | Totals match the documented input selection and units |
| Gold to consumers | Dataset owner communicates freshness and revisions | Consumers can identify the published version and its coverage |

The original classroom architecture connects API producers, Kafka or Bronze storage, Spark/Glue transformations, analytical tables such as Iceberg or Redshift, and dashboards or ML consumers. These are possible component choices; a single pipeline does not need every named product.

### Failure model and recovery

| Failure | Consumer-visible symptom | Containment and recovery | Evidence to require |
| --- | --- | --- | --- |
| Crash before table commit | Previous version remains visible; freshness falls | Writer retries safely; maintenance later removes eligible orphan files | Current snapshot, batch identity, and accepted-record counts |
| Commit acknowledgment lost | Outcome is uncertain to the writer | Resolve committed batch state before replaying | Publication ledger or equivalent durable batch identity |
| Concurrent writes conflict | One operation may need retrying | Re-read state and retry according to supported conflict rules | Commit result and no lost/duplicated observations |
| Source schema breaks | Validation rejects new records | Quarantine, notify producer owner, and migrate explicitly | Compatibility tests and consumer acceptance |
| Transformation commits bad values | New snapshot is complete but wrong | Stop affected publication, repair logic, then rollback or replay deliberately | Corrected totals and downstream reconciliation |
| Catalog becomes unavailable | New table resolution or commits may fail | Preserve safe state and restore catalog access | Successful resolution/commit and identified affected runs |
| Consumer falls behind retention | Required replay data is missing | Restore from an available authorized copy or coordinate backfill | Complete recovered time range and known unrecoverable gaps |

Bound retries, use backoff, and monitor backlog so a dependency outage does not trigger an uncontrolled retry surge. See Google's [discussion of cascading failures](https://sre.google/sre-book/addressing-cascading-failures/). Recovery planning should define recovery time and acceptable data loss; the [AWS Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html) provides broader operational guidance.

## 11. Data quality, testing, and production considerations

### Reconciliation before declaring success

Consider an illustrative 100,000-record batch before deduplication:

```text
100,000 input records = 99,500 valid records + 500 quarantined records
```

If deduplication then removes 200 of the valid records, 99,300 accepted observations remain. Record the duplicate policy and rejection reasons; a smaller destination count is explainable only when all dispositions are accounted for. These are invented teaching numbers, not measured results.

Row counts alone cannot establish accuracy. Check required keys, uniqueness at the defined grain, valid ranges, timestamp coverage, units, reference joins, aggregate values, and freshness. For an empty batch, distinguish “no observations expected” from “source capture failed.” For late data, define whether and how historical Gold summaries are revised.

### Proposed validation plan

| Check | Expected evidence | Current status |
| --- | --- | --- |
| Atomic publication | A reader never observes a partially committed batch during a controlled write failure | Planned; not executed |
| Replay/idempotency | Replaying an accepted batch does not increase logical observation count | Planned; not executed |
| Schema compatibility | Old/new producers and consumers handle approved schema versions and retained data | Planned; not executed |
| Data quality | Accepted, rejected, and duplicate counts reconcile; key and semantic checks pass | Planned; not executed |
| Recovery | A bounded restore/replay reaches the expected version and totals | Planned; not executed |
| Privacy lifecycle | Authorized deletion and restore procedures account for retained copies | Planned; not executed |

### Performance, maintenance, and observability

Small files increase metadata and read-planning overhead. Compaction can improve reads but consumes compute and may conflict with other operations. Partitioning can reduce scanned data when aligned with queries; excessive partition cardinality can create many small files. Retained snapshots, logs, and storage versions increase storage and maintenance costs.

Measure rows and bytes per batch, file counts and sizes, update frequency, concurrent writers, scan volume, backlog, commit latency, freshness, failed commits, quarantined counts, and restore duration before drawing performance conclusions. Define the required latency and recovery objectives before tuning.

Record run and batch IDs, source range, schema version, code version, and committed output version. Keep record-level sensitive values out of operational logs. Assign an owner to alerts and recovery procedures; a dashboard without an accountable response does not complete the operational design.

## 12. Common pitfalls

| Misunderstanding | Correction |
| --- | --- |
| “Iceberg replaces Parquet.” | Iceberg can manage tables whose data files are Parquet |
| “Strong S3 consistency makes a multi-file write transactional.” | Individual-object guarantees do not atomically publish a whole table update |
| “ACID means every business rule is automatically enforced.” | Invariants need actual constraints, validation, or correct transactional logic |
| “An atomic write makes retries exactly once.” | Retry safety also needs identity and deduplication/publication rules |
| “A safe schema rename cannot break consumers.” | SQL names, application logic, and message representations can still break |
| “A catalog entry proves quality, lineage, and access control.” | These require separate capabilities, configuration, and evidence |
| “Deleting the current row erases every copy.” | Historical files, backups, and derived datasets need lifecycle controls |
| “Rollback and time travel replace backups.” | They depend on retained metadata and files in the same recovery environment |
| “A successful job proves reliability.” | Verify completeness, correctness, freshness, and recovery behavior |

## Knowledge check

1. Explain what Parquet, Iceberg, Spark, object storage, and a catalog each contribute to a table read.
2. A writer creates six of ten candidate files and crashes before commit. Predict what a table-aware reader sees and what can remain physically stored.
3. A retry appends the same batch after an acknowledgment timeout. Which problem does atomicity leave unresolved?
4. Explain each ACID property using a bank transfer or station-observation pipeline, including its limits.
5. A source changes a bike-count field from integer to string. Identify the schema, semantic, and consumer risks, then propose a migration.
6. Compare adding a field in Avro with adding one in Protobuf. What must remain compatible, and what should be tested against historical data?
7. A catalog shows the right schema, but a dashboard reports incorrect totals. What lineage and quality evidence would you inspect?
8. Explain why deleting sensitive data from the latest snapshot may leave other accessible copies.
9. Reconcile 100,000 inputs when 500 are invalid and 200 more are duplicates. State the grain and assumptions behind the destination count.
10. Choose three Rs and identify concrete evidence that would demonstrate each in a project you understand.
11. Design a recovery from a bad committed batch without losing later valid observations. Identify what would change your choice between rollback and replay.

## Key takeaways

- File formats encode data; table formats coordinate versioned table state over files.
- ACID guarantees apply to a defined transaction boundary and failure model.
- Table evolution, message compatibility, and consumer semantics must be managed together.
- Catalogs, lineage, contracts, and governance connect ownership with usable, protected data.
- Reliable pipelines need quality checks, retry safety, reconciliation, monitoring, and tested recovery in addition to transactional storage.

## Completion checklist

- [ ] Explain the layers and trace a complete table read/write in your own words.
- [ ] Identify transaction boundaries and the rules enforced at each boundary.
- [ ] Describe a compatible schema migration and its rollback limitations.
- [ ] State dataset grain, owner, keys, freshness, and retention expectations.
- [ ] Identify retained copies relevant to recovery and sensitive-data deletion.
- [ ] Propose evidence for atomic publication, retry safety, quality, and recovery.

The mechanisms above were checked against the linked primary documentation on 2026-11-03. Examples and validation plans remain conceptual; no table engine, broker, registry, cloud operation, fault injection, or performance benchmark was executed for these notes. Engine and connector compatibility must be verified for a concrete implementation.
