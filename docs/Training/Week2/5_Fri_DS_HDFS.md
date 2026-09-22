# Friday: Distributed Systems, Hadoop, HDFS, Hive, and Spark

> Status: Guided introduction
>
> Level: Beginner, with modern data-engineering context
>
> Applies to: Distributed storage, cluster resource management, batch processing, SQL over files, and analytical file formats
>
> Evidence: Documentation reviewed against current Apache project documentation; one complete YouTube caption track and both videos' metadata were reviewed; no Hadoop cluster commands were run
>
> Last reviewed: 2026-09

## Overview

Hadoop is important because it established many of the ideas that still shape large-scale data systems: divide large datasets into pieces, store those pieces across machines, move computation close to the data, recover from machine failure, and coordinate work across a cluster.

You may not build a new system with every Hadoop-era tool in this guide. Modern platforms often use cloud object storage, Spark, distributed SQL engines, and open table formats instead. The durable concepts remain valuable because storage, compute, metadata, partitioning, failure recovery, and resource scheduling still have to be solved.

This lesson focuses on those concepts. It gives the core Hadoop components more attention than the long list of projects surrounding them.

## Learning objectives

After completing this guide, you should be able to:

- Explain why data systems scale horizontally across multiple machines.
- Distinguish fault detection, fault tolerance, high availability, and consensus.
- Describe the roles of Hadoop Common, HDFS, YARN, and MapReduce.
- Trace an HDFS file from its path and metadata to its blocks and replicas.
- Explain why many small files create operational and processing overhead.
- Use basic HDFS filesystem commands and distinguish local paths from HDFS paths.
- Compare MapReduce with Spark without claiming that Spark performs every operation in memory.
- Explain what Hive and the Hive Metastore add to files stored in HDFS or object storage.
- Compare schema-on-write with schema-on-read and managed with external Hive tables.
- Distinguish partitioning, bucketing, compression, file formats, and table formats.
- Explain where Docker and Kubernetes fit without confusing them with HDFS, YARN, or Spark.
- Place major Hadoop-ecosystem tools into storage, compute, ingestion, orchestration, security, governance, or administration categories.

## Prerequisites

- Basic terminal and filesystem concepts from the Linux lessons.
- Basic SQL concepts from [Wednesday's SQL lesson](3_Wed_SQL.md).
- Basic analytical storage concepts from [Thursday's database lesson](4_Thur_Databases.md).
- No local Hadoop installation is required for this conceptual lesson.

---

## 1. Why distributed systems exist

A **distributed system** is a group of independent computers that communicate over a network and work together as one system. A connected group of machines is often called a **cluster**, and each machine is a **node**.

A cluster and a supercomputer can both combine substantial computing power, but the terms are not interchangeable. A data cluster is usually designed around many networked machines, distributed storage, independent failures, and software coordination. A supercomputer is often built as a tightly integrated system for high-performance scientific computing.

### Vertical and horizontal scaling

There are two basic ways to add capacity:

| Scaling method | What changes | Main limitation |
| --- | --- | --- |
| Vertical scaling | Add CPU, memory, or storage to one machine | One machine has a physical and financial limit |
| Horizontal scaling | Add more machines and divide the work | Distribution adds network, coordination, skew, and failure complexity |

Horizontal scaling is not automatically faster. The workload must be divided into useful pieces, data may need to move across the network, and slow or uneven partitions can delay the whole job.

### Failure is normal at cluster scale

Adding nodes increases total capacity, but it also increases the number of components that can fail. Distributed systems therefore need explicit behavior for:

- Detecting an unavailable process or node.
- Retrying safe operations.
- Reassigning work.
- Reconstructing or reading another copy of data.
- Electing or activating a replacement leader when the architecture supports it.
- Alerting an operator when automatic recovery is insufficient.

These behaviors are related, but they are not the same:

| Term | Meaning |
| --- | --- |
| Fault detection | Suspecting that a process or node is unavailable |
| Fault tolerance | Continuing useful work despite a failure |
| High availability | Reducing service downtime, often with redundant active and standby components |
| Consensus | Allowing multiple participants to agree on ordered state despite failures |

### Heartbeats and failure detection

A **heartbeat** is a periodic message that indicates a process is still communicating. If expected heartbeats stop arriving, another component may mark that process unhealthy after a timeout.

Missing a heartbeat does not prove that a machine has permanently failed. The machine might be slow, the network might be partitioned, or the monitoring process might be overloaded. Distributed systems use timeouts and other evidence to make a practical failure decision under uncertainty.

HDFS DataNodes, for example, send heartbeats and block reports to the NameNode. If a DataNode stops sending heartbeats, the NameNode eventually stops sending new I/O requests to it and arranges replacement replicas for under-replicated blocks.

### Consensus is not the same as cluster management

Raft and ZooKeeper's Zab are consensus or atomic-broadcast approaches used by some distributed systems. They can support leader election and replicated metadata, but not every cluster manager is an instance of Raft or Zab, and consensus is not required on every worker node.

Examples of coordination designs include:

- HDFS high availability can use active and standby NameNodes, JournalNodes, and ZooKeeper-based failover.
- Kafka's KRaft mode manages Kafka metadata using a Raft-based controller quorum.
- Kubernetes uses `etcd`, which uses Raft, for authoritative cluster state.
- YARN schedules cluster resources but should not be described as a general consensus algorithm.

### A careful CAP theorem mental model

The **CAP theorem** concerns what a distributed data system can guarantee when a network partition prevents some nodes from communicating:

- **Consistency:** every successful read observes the required current value under the system's stated model.
- **Availability:** every request to a non-failing participant receives a non-error response, even if that response cannot contain the newest value.
- **Partition tolerance:** the system continues operating according to some defined behavior despite lost or delayed messages between groups of nodes.

“Pick any two” is only a shortcut. During a real partition, a system or operation must decide whether to reject or delay some work to preserve consistency, or continue serving work with weaker consistency. Different operations in the same platform can make different tradeoffs.

Do not label HDFS simply as “eventually consistent.” HDFS is designed primarily for large, streaming reads and a write-once-read-many model. A file has one writer at a time, arbitrary in-place updates are not supported, and the NameNode authoritatively manages namespace and block metadata. Those semantics are more useful than assigning HDFS a single CAP label.

---

## 2. The core Hadoop mental model

Apache Hadoop contains four core modules:

| Module | Main responsibility |
| --- | --- |
| Hadoop Common | Shared libraries and utilities used by the other modules |
| HDFS | Distributed storage for large files |
| YARN | Cluster resource management and job scheduling framework |
| MapReduce | YARN-based parallel batch-processing system |

Keep **storage**, **resource management**, and **processing** separate in your mind:

```text
User code and query tools
           |
           v
Spark / Hive / MapReduce / Tez
           |
           v
YARN or another cluster manager
           |
           v
HDFS or another storage system
           |
           v
Cluster machines, disks, memory, CPU, and network
```

This diagram is a learning model, not a rule that every tool must use every layer. Spark can run with several cluster managers and can read from HDFS, object storage, databases, and other sources. Hive can use different execution engines and storage systems.

### Storage and compute are different responsibilities

- **HDFS stores bytes and filesystem metadata.** It is not a relational database or query engine.
- **YARN grants applications CPU and memory resources.** It is not the filesystem.
- **MapReduce and Spark perform computation.** They are not durable storage systems.
- **Hive adds table metadata and SQL-oriented behavior over data in files.** It does not turn HDFS itself into a relational database.

---

## 3. HDFS: distributed storage for large files

**HDFS** stands for **Hadoop Distributed File System**. It presents files and directories to users while storing each large file as blocks across DataNodes.

HDFS is optimized for:

- Large files, commonly from gigabytes to terabytes.
- High-throughput sequential access.
- Batch-oriented workloads.
- Operation across commodity machines where component failure is expected.

HDFS is not optimized for:

- Low-latency record-by-record queries.
- Large numbers of tiny files.
- Frequent arbitrary updates in the middle of a file.
- Relational constraints, indexes, transactions, or SQL by itself.

### NameNode and DataNodes

```text
                         metadata request
HDFS client ------------------------------------> NameNode
     |                                      path -> block locations
     |                                                   |
     | block reads and writes                            |
     v                                                   v
DataNode A <--------------> DataNode B <--------------> DataNode C
 block 1                  block 2                    block replicas
```

| Component | Responsibility |
| --- | --- |
| NameNode | Maintains the filesystem namespace, permissions, file-to-block mapping, and block locations; directs block operations |
| DataNode | Stores block data on local storage, serves client reads and writes, and performs replication when instructed |
| HDFS client | Requests metadata from the NameNode, then transfers file data directly with DataNodes |

The file's data does not normally flow through the NameNode. This keeps the NameNode focused on metadata, but it also makes NameNode memory and availability important design concerns.

### Blocks and replication

HDFS divides a file into large **blocks**. A commonly documented HDFS block size is 128 MiB, but block size is configurable. A file's last block uses only the bytes it needs; a 5 MiB file does not automatically consume 128 MiB of physical storage merely because the configured block size is 128 MiB.

**Replication** stores additional copies of each block on different DataNodes. A replication factor of three means HDFS normally attempts to maintain three copies of each block, subject to cluster size, placement policy, and configuration.

Example for a 700 MiB file with 128 MiB blocks and replication factor three:

```text
Logical file
700 MiB
   |
   v
5 full 128 MiB blocks + 1 final 60 MiB block
   |
   v
6 logical blocks x 3 replicas
   |
   v
approximately 2,100 MiB of block data across the cluster
```

That estimate ignores checksums, metadata, filesystem overhead, compression, and any erasure-coding policy. Replication improves tolerance of disk, node, and some rack failures, but it costs storage and network bandwidth.

### What happens when a DataNode fails?

```text
1. A DataNode stops sending heartbeats.
2. After the configured timeout, the NameNode marks it unavailable.
3. The NameNode no longer directs new I/O to that DataNode.
4. Some blocks may now have fewer replicas than required.
5. The NameNode instructs healthy DataNodes to create replacement replicas.
6. Operators investigate the failed node while the cluster continues when enough healthy replicas remain.
```

Replication is not a backup strategy by itself. Accidental deletion, bad application logic, compromised credentials, or corruption copied to every replica can still affect all live copies. Backups, snapshots, retention rules, and tested recovery procedures solve different problems.

### The small-files problem

The HDFS small-files problem is not that every small file reserves an entire 128 MiB block. The main problems are:

- Every file, directory, and block adds metadata that the NameNode must manage, much of it in memory.
- Listing and opening many files creates metadata operations.
- Processing engines may create too many short tasks and file-open operations.
- Tiny output files reduce scan efficiency and can burden downstream query planning.

Object storage changes the storage architecture, but it does not make tiny analytical files harmless. Spark and distributed query engines can still spend excessive time listing, opening, planning, and scheduling work for them. Compaction remains a common data-engineering operation.

### Compression

HDFS does not automatically compress every file. It stores the bytes written by the client. An application or processing engine can write compressed formats such as Parquet with Snappy compression.

Compression creates a tradeoff:

```text
less storage + less network I/O
                 versus
CPU time to compress and decompress
```

For distributed processing, a compression choice can also affect whether an engine can split a file into independent tasks.

### NameNode availability roles

| Role | Purpose |
| --- | --- |
| Active NameNode | Serves current namespace operations |
| Standby NameNode | Maintains synchronized metadata and can take over in an HA configuration |
| JournalNode | Stores shared edit-log records for quorum-based NameNode high availability |
| ZooKeeper Failover Controller (ZKFC) | Monitors local NameNode health and helps coordinate automatic failover |
| Secondary NameNode | Creates metadata checkpoints by combining namespace image and edit information; it is not simply a standby NameNode |

The word “secondary” is misleading. A Secondary NameNode does not by itself provide the active/standby failover design used for HDFS high availability.

---

## 4. Basic HDFS commands

The HDFS filesystem shell resembles familiar Unix commands, but local and HDFS paths belong to different filesystems.

```bash
# Create an HDFS directory.
hdfs dfs -mkdir -p /training/input

# Copy a local file into HDFS.
hdfs dfs -put data.csv /training/input/

# List files in HDFS.
hdfs dfs -ls /training/input

# Display an HDFS text file.
hdfs dfs -cat /training/input/data.csv

# Copy an HDFS file back to the local filesystem.
hdfs dfs -get /training/input/data.csv ./downloaded-data.csv

# Show HDFS space usage in human-readable units.
hdfs dfs -du -h /training/input
```

Read the `-put` command as:

```text
hdfs dfs -put <local-source> <hdfs-destination>
```

The one-argument form `hdfs dfs -put data.csv` can depend on the HDFS working directory and is less explicit for a beginner. Naming the destination makes the boundary clear.

These commands require an HDFS client configured to reach a cluster. They are examples only; this repository does not currently provide an HDFS cluster for executing them.

---

## 5. YARN: cluster resources and application scheduling

**YARN** stands for **Yet Another Resource Negotiator**. Its main job is to allocate cluster resources and coordinate applications running on those resources.

| Component | Responsibility |
| --- | --- |
| ResourceManager | Arbitrates cluster resources across applications |
| NodeManager | Runs on a worker machine, manages allocated containers, monitors resource use, and reports status |
| ApplicationMaster | Coordinates one application and negotiates resources for its tasks |
| YARN container | An allocation of resources such as memory and CPU in which work runs; it is not the same concept as a Docker container |

```text
Application submitted
        |
        v
ResourceManager starts an ApplicationMaster
        |
        v
ApplicationMaster requests resource containers
        |
        v
NodeManagers launch and monitor tasks
```

YARN separates resource management from a specific compute engine. MapReduce was redesigned to run on YARN, and other distributed applications can also use YARN.

---

## 6. MapReduce and Spark

### MapReduce

MapReduce is both a programming model and Hadoop's original large-scale batch-processing system.

```text
Input
  |
  v
Map: process input records and emit key-value pairs
  |
  v
Shuffle and sort: move values so identical keys meet
  |
  v
Reduce: combine or summarize values for each key
  |
  v
Output
```

Example: counting orders by state.

```text
Map outputs:       (ID, 1), (CA, 1), (ID, 1)
Shuffle groups:    ID -> [1, 1], CA -> [1]
Reduce outputs:    (ID, 2), (CA, 1)
```

MapReduce made reliable distributed batch processing practical, but multi-stage pipelines frequently materialize intermediate results and can perform substantial disk and network I/O. Direct MapReduce application development is now often treated as historical or legacy context, but MapReduce remains an Apache Hadoop module and its map-shuffle-reduce mental model is still useful.

### Spark

Apache Spark is a general-purpose distributed processing engine that supports structured batch processing, SQL, streaming, machine learning libraries, and lower-level distributed collections.

A Spark application commonly contains:

| Component | Responsibility |
| --- | --- |
| Driver | Runs the main application, builds work, and coordinates execution |
| Cluster manager | Allocates resources; examples include standalone Spark, YARN, and Kubernetes |
| Executors | Run tasks and store application data on worker nodes |
| Task | A unit of work applied to one data partition |

Spark can reduce repeated disk materialization and can cache reused data, which makes many iterative and interactive workloads faster than equivalent MapReduce pipelines. However, “Spark runs everything in memory” is inaccurate:

- Input and output still use storage.
- Shuffles transfer data over the network and may spill to disk.
- Cached data can use memory, disk, or both depending on its storage level.
- Data that does not fit in memory may be recomputed or spilled.
- Performance also depends on partitioning, serialization, CPU, skew, and network capacity.

### RDDs, DataFrames, and Spark SQL

An **RDD**, or Resilient Distributed Dataset, is Spark's lower-level distributed collection abstraction. It is partitioned across the cluster and can be recomputed from lineage after some failures.

A **DataFrame** represents structured data with named columns and a schema. DataFrames and Spark SQL give the optimizer more information than arbitrary RDD functions, so they are normally the better starting point for structured data engineering.

```text
SQL query or DataFrame operations
              |
              v
logical plan
              |
              v
optimized physical plan
              |
              v
tasks run across data partitions
```

Spark does not replace storage, a catalog, data modeling, orchestration, or data-quality contracts. It is the computation layer in a larger system.

---

## 7. Hive: SQL and metadata over distributed data

Apache Hive provides a distributed data-warehouse and SQL layer over data stored in systems such as HDFS. It lets users define tables and query them with HiveQL instead of writing low-level MapReduce code.

Hive is not an ORM. An ORM maps application objects to a database interface; Hive provides SQL-oriented metadata and query processing over distributed datasets.

```text
SQL / HiveQL
     |
     v
Hive table definition and optimizer
     |
     v
execution engine such as Tez
     |
     v
files in HDFS or another configured storage system
```

Hive has evolved beyond “SQL translated only into MapReduce.” Execution behavior depends on the Hive version and configuration, and engines such as Tez can execute Hive work.

### The Hive Metastore

The **Hive Metastore** stores metadata such as:

- Database and table names.
- Column names and data types.
- Partition definitions.
- Storage locations.
- File-format and table properties.
- Statistics used during query planning.

The metastore usually stores metadata about a table, not the table's business-data rows.

```text
Catalog or metastore
  table: sales
  columns: order_id, order_date, amount
  location: /warehouse/sales/
  format: Parquet
          |
          v
Storage
  actual Parquet files
```

This separation remains central in modern data platforms. Different processing engines can use a shared catalog to discover the same datasets, although compatibility and concurrent writes still require explicit guarantees.

### Schema-on-write and schema-on-read

| Approach | When structure is enforced | Strength | Risk |
| --- | --- | --- | --- |
| Schema-on-write | Before or while data is accepted into its target | Consumers receive cleaner, more predictable records | New or unexpected input may be rejected or quarantined |
| Schema-on-read | When a consumer interprets stored data | Raw data can be landed quickly and interpreted for different uses | Errors and drift may appear late, and consumers can disagree |

These are not absolute opposites. A Parquet or Avro file has an encoded schema, while a table or job can still apply additional schema and business rules when it reads the file. Mature systems normally validate important contracts at ingestion even when raw data is retained.

### Managed and external Hive tables

| Table type | Who is expected to manage the data lifecycle? | Typical effect of `DROP TABLE` |
| --- | --- | --- |
| Managed table | Hive | Removes the table metadata and its managed data, subject to configuration and trash behavior |
| External table | Another process or shared storage owner | Removes Hive metadata while leaving the referenced data by default |

Use a managed table when Hive should own the table's data lifecycle. Use an external table when the files have an independent owner, are shared with other engines, or must remain after the Hive definition is removed.

Do not rely on the simplified rule without checking configuration. For example, external-table purge settings can change deletion behavior. Production deletion policy should be tested in the actual environment.

---

## 8. Partitioning, bucketing, and shuffles

These terms all describe divisions of data or work, but they refer to different mechanisms.

### Table or file partitioning

**Partitioning** places rows into separate storage paths or file groups based on one or more values.

```text
sales/
  order_year=2025/
    order_month=01/
      part-00000.parquet
  order_year=2025/
    order_month=02/
      part-00000.parquet
```

A query filtering for February 2025 may use **partition pruning** to avoid reading January's files.

A storage partition is not permanently tied one-to-one to a physical machine. Files can be replicated, moved, or read by different workers, and several partitions can reside on the same node or storage service.

Choose partition columns that support common filters without creating an excessive number of tiny directories and files. A high-cardinality identifier such as `customer_id` is often a poor directory-partition choice unless workload and scale evidence support it.

### Bucketing

**Bucketing** hashes a chosen column into a fixed number of buckets.

```text
bucket_number = hash(customer_id) % 32
```

Rows with the same bucket key are directed to the same bucket number under a stable compatible hashing definition. That does not mean only identical full rows share a bucket; hash collisions and many different key values per bucket are expected.

Bucketing may help some joins, sampling strategies, and data distribution patterns, but only when the engine understands and preserves the bucket metadata. It is not automatically beneficial.

### Spark execution partitions and shuffles

A **Spark partition** is a chunk of data processed by one task at a time. It is an execution concept, although input files and table partitions influence how Spark creates those partitions.

A **shuffle** redistributes records across executors, commonly for joins, `groupBy`, distinct operations, or repartitioning.

```text
before shuffle                 after hash partition by customer_id

executor A: C1, C2, C1         partition 0: C2, C4
executor B: C3, C4       -->   partition 1: C1, C1
executor C: C2, C3             partition 2: C3, C3
```

Shuffles can be expensive because they involve serialization, network transfer, sorting, memory pressure, and possible disk spill. Uneven keys can create **data skew**, where one task receives much more work than the others.

---

## 9. File formats, compression codecs, and table formats

These layers solve different problems:

```text
Table format:      Iceberg
                         manages table snapshots, metadata, and file membership
File format:       Parquet
                         organizes records and columns inside each data file
Compression codec: Snappy
                         compresses encoded data blocks or pages
Storage system:    HDFS or object storage
                         stores the bytes
```

### Common data formats

| Format | Layout | Good fit | Important limitation or tradeoff |
| --- | --- | --- | --- |
| CSV | Text rows | Simple exchange and human inspection | Weak typing, ambiguous nulls and escaping, inefficient analytical scans |
| JSON | Text records | Flexible nested exchange and APIs | Verbose, repeated field names, expensive parsing |
| Parquet | Columnar binary | Analytical scans, Spark, warehouses, and lakehouse data | Poor fit for frequent single-record mutation |
| ORC | Columnar binary | Analytical scans, especially in Hive-oriented ecosystems | Engine support and tuning vary |
| Avro | Row-oriented binary with schema | Record exchange, event data, and schema-aware serialization | Usually less efficient than columnar formats for selecting a few columns from large analytical datasets |

### Parquet and ORC

Columnar formats store values so an engine can read only the needed columns and use statistics or indexes to skip some irrelevant data.

```text
Row-oriented idea
1, Ada, Boise, 92000
2, Lin, Austin, 88000

Column-oriented idea
id:     1, 2
name:   Ada, Lin
city:   Boise, Austin
salary: 92000, 88000
```

Columnar storage works well for queries such as `SUM(salary)` because the engine does not necessarily need to decode every name and city value.

### Avro

Avro is not “compressed JSON.” It is a binary serialization system whose schema is represented in JSON. Avro object-container files store the schema with the data, and their data blocks may use a compression codec.

Avro is useful when records move between systems and producers and consumers need explicit schema resolution. Schema evolution still requires compatibility rules; a format cannot decide business meaning when a field is renamed, removed, or reinterpreted.

Consider an online retailer that publishes order events:

```text
Checkout service            Kafka topic                 Independent consumers
(producer)                  orders.created             |-- Fulfillment service
                                                        |-- Fraud detector
                                                        `-- Spark order pipeline
```

The checkout service is the **producer** because it creates an `OrderCreated` record. Kafka is the transport and retention system. Fulfillment, fraud detection, and Spark are **consumers** because each reads the same record for a different purpose. Avro defines how the record is encoded and how a consumer can interpret records written with compatible schema versions.

Suppose version 1 contains `order_id`, `customer_id`, and `total_cents`. Version 2 adds `currency` with a default of `"USD"`:

```json
{
  "type": "record",
  "name": "OrderCreated",
  "fields": [
    {"name": "order_id", "type": "string"},
    {"name": "customer_id", "type": "string"},
    {"name": "total_cents", "type": "long"},
    {"name": "currency", "type": "string", "default": "USD"}
  ]
}
```

During **schema resolution**, Avro compares the schema that wrote a record with the schema the consumer expects:

- A new consumer reading an old record supplies `"USD"` because the reader's new `currency` field has that default.
- An old consumer reading a new record ignores `currency` because its reader schema does not request that field.
- A compatible numeric promotion such as `int` to `long` can be resolved, but narrowing or changing a field to an unrelated type may fail.
- A field rename needs an alias or a coordinated migration. Even when bytes remain readable, changing the meaning of `total_cents` from “before tax” to “after tax” is a business-contract break that Avro cannot solve.

An Avro object-container file carries its writer schema in the file. For individual Avro messages in Kafka, teams commonly place a schema identifier in the message and retrieve the matching schema from a schema registry; that registry convention is separate from the Avro file format itself. Compatibility checks should run before a producer deploys so one producer does not unexpectedly break several consumers.

### Snappy

Snappy is a **compression codec**, not a standalone analytical file format. A filename such as `part-00000.snappy.parquet` commonly means that the file uses the Parquet format and a writer used Snappy for compressed data within it. Snappy is frequently paired with Parquet, but formats such as Avro and ORC can also use it.

### Open table formats

A file format describes bytes within one file. Parquet does have metadata: each Parquet file contains a schema plus metadata about its row groups, column chunks, offsets, encodings, and often statistics such as minimum and maximum values. An engine can use that metadata to decode the file, select columns, and skip some irrelevant data.

What a Parquet file does **not** know is whether it is still part of a logical table, which other Parquet files belong to the same committed version, which schema and partition rules govern the table as a whole, or whether a multi-file write completed successfully.

A **table format** such as Apache Iceberg adds that table-level control layer:

```text
Catalog or metastore
  orders -> current Iceberg metadata file
                         |
                         v
Iceberg table metadata: schemas, partition specs, properties, snapshots
                         |
                         v
Snapshot -> manifest list -> manifests -> exact data and delete files
                                                |
                                                v
                                    Parquet files and their own metadata
```

The layers have different scopes:

| Metadata layer | Typical responsibility |
| --- | --- |
| Parquet file metadata | Describes the columns, row groups, encodings, offsets, and statistics inside one file |
| Iceberg manifests and manifest lists | Track the data and delete files in a snapshot, their partition values, and file-level metrics |
| Iceberg table metadata | Tracks table schemas, partition specifications, properties, snapshot history, and the current snapshot |
| Catalog or metastore | Resolves a logical name such as `analytics.orders` to the current Iceberg metadata location and may also manage namespaces, ownership, or access integration |

This structure enables several behaviors:

- **Snapshots:** each committed snapshot identifies an exact set of files. A reader can keep using the snapshot it started with while a newer snapshot is committed, and retained older snapshots can support time travel or rollback.
- **Schema evolution:** Iceberg tracks columns with stable field IDs. Adding, dropping, reordering, or renaming a column can be a metadata change rather than an immediate rewrite of every old Parquet file. Compatibility rules still limit unsafe type changes.
- **Partition evolution:** a new partition specification can apply to new files while old files remain under the earlier specification. The scan planner uses the specification recorded for each manifest, so callers continue to filter on logical columns instead of manually knowing every historical directory layout.
- **Atomic table updates:** a writer first creates new data files, manifests, and a new metadata file. It then commits by atomically replacing the table's current metadata reference, often through a catalog, from the old version to the new one. Readers see either the old committed snapshot or the new committed snapshot, not a half-published file set. The exact atomic mechanism depends on the catalog, and optimistic concurrency checks prevent one writer from silently overwriting a concurrent commit.

Iceberg metadata does not replace Parquet metadata or a catalog. It connects catalog-level table identity to snapshot-level file membership while Parquet continues to describe the contents of each data file. Do not use “Parquet table” and “Iceberg table” as synonyms: an Iceberg table may use Parquet data files, but the Iceberg metadata supplies table-level behavior that Parquet alone does not provide.

---

## 10. Organizing the Hadoop ecosystem

The ecosystem is easier to learn by responsibility than by memorizing one giant list.

### Learn these first

| Area | Technologies | What to remember |
| --- | --- | --- |
| Core storage | HDFS, NameNode, DataNode | Files become blocks; metadata and block storage have different owners |
| Resource management | YARN, ResourceManager, NodeManager, ApplicationMaster | Cluster CPU and memory are allocated to applications |
| Batch compute | MapReduce, Spark | Engines divide work into tasks and move data when required |
| SQL and catalog | Hive, Hive Metastore | SQL/table metadata is separate from file bytes |
| Data layout | Partitions, buckets, Spark partitions, shuffles | Similar words can describe storage layout or execution work |
| Formats | Parquet, ORC, Avro, Snappy | Columnar files, row-oriented serialization, and compression are different layers |

### Recognize these by responsibility

| Responsibility | Technologies | Short description |
| --- | --- | --- |
| Interactive SQL | Impala, Trino | Distributed SQL engines designed for interactive or federated queries |
| Specialized storage | HBase, Kudu, Ozone | Key-value access, mutable analytical storage, or distributed object storage |
| Stream transport and processing | Kafka, Flink, Spark Structured Streaming | Event transport and stateful or incremental processing |
| Data movement | NiFi, Kafka Connect | Managed flows and reusable source/sink connectors |
| Orchestration | Oozie, Airflow | Coordinate dependent jobs; Oozie is Hadoop-oriented, while Airflow is general-purpose |
| Coordination | ZooKeeper | Distributed coordination used by several Hadoop-era systems |
| Security | Kerberos, Ranger, Knox | Authentication, authorization/auditing, and secured gateway access |
| Governance | Atlas | Metadata discovery, classification, governance, and lineage |
| Administration | Cloudera Manager, Hue | Cluster administration and browser-based data/query tooling |

### Historical or legacy context

These names may appear in older systems, migration projects, or interviews:

| Technology | Historical role | Common modern context |
| --- | --- | --- |
| Sqoop | Bulk relational database transfers to and from Hadoop | Often replaced by managed connectors, CDC, or engine-native ingestion |
| Flume | Log and event ingestion into Hadoop | Kafka and other managed ingestion systems are more common in newer designs |
| Pig | High-level Pig Latin data-flow language over Hadoop | Mostly legacy; SQL and Spark are more common |
| Oozie | Hadoop-specific workflow scheduling | Existing clusters may retain it; general orchestrators are common for new workflows |
| Storm | Early real-time stream processor | Flink, Kafka Streams, and Spark Structured Streaming are common alternatives |
| Mahout | Hadoop-era distributed machine learning | Spark ML libraries and dedicated ML platforms cover many modern workloads |
| SequenceFile and RCFile | Earlier Hadoop storage formats | Parquet, ORC, and Avro are more important starting points today |
| Ambari and Sentry | HDP management and CDH authorization history | Useful when maintaining historical Hortonworks or Cloudera estates |

### Cloudera and Hortonworks context

Historically, **CDH** meant **Cloudera Distribution Including Apache Hadoop**, and **HDP** meant **Hortonworks Data Platform**. They packaged many of the same Apache projects but emphasized different management, SQL, security, and governance components. Their histories explain why older environments may use different combinations of Impala, Kudu, Ambari, Ranger, Atlas, Knox, Sentry, Tez, and ORC.

For a beginner, the architectural responsibility matters more than memorizing which vendor originally emphasized each project. Ask these questions instead:

1. Where are the durable data bytes stored?
2. Where is table and schema metadata stored?
3. Which engine performs computation or answers SQL?
4. Which system allocates cluster resources?
5. Which system moves or orchestrates data?
6. Which systems enforce identity, authorization, and auditing?
7. How does each component recover from failure?

#### Example: an on-premises retailer

Imagine a retailer that keeps five years of web-click events and order data. Application servers produce JSON click events, PostgreSQL owns current order records, analysts need interactive SQL, and a nightly job builds sales summaries. The company chooses an on-premises Hadoop cluster because this historical scenario predates its cloud migration and the data volume exceeds one database server.

The seven questions can be answered without choosing a vendor first:

1. **Durable bytes:** HDFS stores landed events, database extracts, Parquet/ORC analytical files, and derived outputs. PostgreSQL remains the source of truth for current operational orders.
2. **Table metadata:** the Hive Metastore records table names, columns, partitions, formats, and HDFS locations; it does not contain the order rows themselves.
3. **Compute and SQL:** Spark performs nightly transformations. An interactive SQL engine answers analysts' queries over curated files.
4. **Resources:** YARN allocates CPU and memory to Spark and other applications designed to use YARN. An interactive SQL engine may use YARN or its own admission-control mechanism, depending on the engine and distribution.
5. **Movement and orchestration:** Kafka or NiFi receives click events, a database ingestion process copies order changes, and Oozie schedules the historical nightly workflow.
6. **Security and audit:** Kerberos authenticates identities; an authorization service controls table or file access and records audit events.
7. **Recovery:** HDFS replication and NameNode high availability protect service continuity, YARN and Spark retry failed work, and the pipeline uses idempotent batch identifiers so a rerun does not double-count sales. Separate snapshots or backups protect against deletion and application mistakes.

The vendor distribution mainly changes the packaged tools used to implement some responsibilities:

| Responsibility | Historical CDH-style answer | Historical HDP-style answer |
| --- | --- | --- |
| Administration | Cloudera Manager | Ambari |
| Interactive SQL | Impala, sharing Hive Metastore metadata | Hive with Tez, with other engines possible |
| Common analytical format emphasis | Parquet | ORC, while Parquet was also available |
| Authorization and audit | Sentry with related Cloudera tooling | Ranger |
| Governance and lineage | Cloudera Navigator in enterprise deployments | Atlas |
| Edge gateway | Product and deployment dependent | Knox was commonly packaged for secured gateway access |

This is historical orientation, not a recommendation to build a new CDH or HDP cluster. Cloudera and Hortonworks merged, their product lines evolved, and modern platforms may use object storage, Kubernetes, cloud identity, and newer catalogs. The responsibility questions remain useful during both maintenance and migration.

---

## 11. Hadoop ideas in modern data platforms

The physical components may change, but their responsibilities remain:

| Hadoop-era responsibility | One possible modern implementation | Durable question |
| --- | --- | --- |
| Distributed storage | HDFS or cloud object storage | How are bytes durably stored, located, and recovered? |
| Table metadata | Hive Metastore, cloud catalog, or Iceberg-compatible catalog | Which schema, partitions, and files define the table? |
| Distributed compute | Spark, Flink, or a distributed SQL engine | How is work divided, shuffled, retried, and measured? |
| Resource management | YARN, Kubernetes, or a managed service | Who admits work and allocates CPU and memory? |
| Workflow orchestration | Airflow or a managed orchestrator | How are dependencies, retries, backfills, and alerts controlled? |
| Security and governance | Platform IAM, catalog policies, lineage, and audit services | Who may discover, read, change, and delete data? |

HDFS and object storage are not identical:

| Concern | HDFS | Cloud object storage |
| --- | --- | --- |
| Namespace | Hierarchical filesystem-like paths | Objects addressed by keys, often displayed like folders |
| Compute relationship | Traditionally deployed near cluster compute | Storage and compute are commonly separated |
| Data placement | Blocks and replicas managed across DataNodes | Placement and durability managed by the storage service |
| Rename and mutation semantics | Filesystem operations with HDFS-specific guarantees | Provider and API semantics; rename may be implemented as copy and delete |
| Operations | Team may manage disks, nodes, replication, and NameNode HA | Provider manages storage infrastructure; the team still manages layout, access, lifecycle, cost, and correctness |

Moving from HDFS to object storage changes the operational model. It does not remove the need to design file sizes, partitions, schemas, commits, retention, security, or recovery.

### Where Docker and Kubernetes fit

Docker and Kubernetes matter to modern data platforms, but they solve different problems from HDFS, Hive, and Iceberg:

| Technology | Responsibility in this lesson | What it does not provide by itself |
| --- | --- | --- |
| Docker image | Packages an application runtime, libraries, and configuration defaults into a portable image | Cluster scheduling, distributed storage, table metadata, or data durability |
| Kubernetes | Places and manages containerized workloads across cluster nodes using pods, resource requests, health behavior, networking, and other control-plane features | HDFS semantics, Spark transformations, or analytical table transactions |
| YARN | Allocates cluster resources to Hadoop-style applications | A Docker image format or durable filesystem |

Spark can use standalone Spark, YARN, or Kubernetes as its cluster manager. With Kubernetes, a Spark application commonly has a driver pod and executor pods created from container images. Kubernetes decides where pods can run and manages their lifecycle; Spark still divides the data work into jobs, stages, and tasks.

Be careful with the word **container**. A YARN container is primarily an allocation of CPU, memory, and related resources. It is not automatically a Docker container. YARN can be configured to launch its allocated work inside Docker containers, but those are two distinct layers.

Kubernetes also does not automatically replace HDFS. A platform might run Spark on Kubernetes while keeping durable data in cloud object storage, HDFS, or another storage service. The storage system owns byte durability, a catalog or table format owns table state, Spark owns computation, and Kubernetes owns the containerized processes and cluster resources.

---

## 12. Video summaries and takeaways

The first summary is based on the video's complete auto-generated caption track. The second video currently exposes no YouTube caption track, so its section is based on the presenter-provided description and a community-posted timestamp index visible with the video rather than a transcript. Auto-generated captions and community chapter labels can contain mistakes, so use the videos themselves when exact wording matters.

### Video 1: Intro to Hadoop and Big Data, Part 1 — Frank Kane

- [Watch the video](https://www.youtube.com/watch?v=0AzF4BGdVVM&list=PLKjwSP1bnrvOCon-j9Gm6ehf1JWk9Rhqk)
- **Length and transcript:** 1:36; complete English auto-generated captions reviewed.
- **Transcript summary:** Frank Kane introduces a course intended to turn “big data” and “cloud computing” from buzzwords into concrete concepts. He previews Hadoop architecture, MapReduce, Hive, Pig, Spark, and Amazon Elastic MapReduce, then explains that learners will examine movie-rating data and simple MapReduce code rather than stay entirely at the conceptual level. He presents the course as accessible without prior programming experience, with the main goal of understanding the tools, techniques, and terminology used to extract useful information from large datasets at scale.
- **Big data / data engineering takeaways:** The video is a course trailer, not a technical explanation of Hadoop. Its durable message is that a data engineer should connect architecture and terminology to an actual dataset and executable processing logic. Its tool list reflects the Hadoop ecosystem of its time: HDFS, resource management, data movement, and distributed computation remain useful concepts, while Pig and direct MapReduce are more likely to appear in legacy systems than in a new pipeline.

### Video 2: Advanced Apache Spark Training — Sameer Farooqui

- [Watch the full video](https://www.youtube.com/watch?v=7ooZ4S7Ay6Y); the originally saved link begins at [3:05:55](https://www.youtube.com/watch?v=7ooZ4S7Ay6Y&t=11155s), near the memory, persistence, and serialization portion.
- **Length and source limitation:** 5:58:30; published from Spark Summit 2015. YouTube currently exposes no caption track, so the following is a description-and-chapter-based overview, not a transcript summary.
- **Content overview:** The training starts with the big-data ecosystem and Spark history, then develops the RDD model and Spark runtime architecture. Later sections cover resource managers, memory and persistence, serialization, stages, shuffles, broadcast variables, accumulators, PySpark, improvements to shuffle behavior, Spark Streaming, and the technical ideas behind Spark's 2014 100 TB sort result. The presenter-provided agenda emphasizes Spark Core, RDDs, YARN and standalone deployment, internal behavior, shared variables, streaming, and large-scale sorting.
- **Big data / data engineering takeaways:** RDD lineage explains how Spark can recompute lost partitions; transformations are lazy and actions cause Spark to construct and execute work; stage boundaries and shuffles matter because network transfer, serialization, memory pressure, and disk spill often dominate performance; persistence is a deliberate reuse decision rather than proof that Spark performs everything in memory; and broadcast variables and accumulators have narrow distributed roles rather than behaving like ordinary shared mutable variables.
- **Age warning:** Treat the video as a valuable explanation of durable Spark internals, not as current API or deployment documentation. It teaches a 2015-era Spark stack centered on RDDs, YARN, and standalone mode. Current work commonly emphasizes DataFrames, Spark SQL, structured APIs, Adaptive Query Execution, Structured Streaming, and Kubernetes in addition to YARN. Confirm syntax and configuration in the documentation for the Spark version you actually run.

---

## 13. Common misconceptions

| Misconception | Better explanation |
| --- | --- |
| HDFS is a database | HDFS is a distributed filesystem; databases and query engines add other behavior |
| A 5 MiB HDFS file consumes a full 128 MiB block | The final block uses the bytes it needs; the small-files problem is mainly metadata and processing overhead |
| Replication is the same as backup | Replication supports live availability; backups and recovery plans protect against other failure modes |
| HDFS is simply eventually consistent | HDFS has a specific write-once/read-many model, one writer per file, and authoritative namespace metadata |
| Every cluster manager uses Raft or Zab on every machine | Consensus and resource scheduling are separate concerns, and implementations differ |
| MapReduce no longer matters at all | Direct use is often legacy, but its architecture remains foundational and the Hadoop module still exists |
| Spark performs everything in memory | Spark can cache data but also reads storage, shuffles over the network, spills, and writes output |
| Hive is an ORM over MapReduce | Hive is a SQL/data-warehouse layer with metadata and configurable execution behavior |
| Partitioning means one partition per machine | Storage and execution partitions can move, coexist on one node, or be processed by different workers |
| Snappy is a file format | Snappy is a compression codec often used inside formats such as Parquet |
| Avro is compressed JSON | Avro uses JSON to describe schemas but encodes records in a binary serialization format |
| Parquet has no metadata | A Parquet file has file- and page-level metadata; it lacks Iceberg's table-wide snapshots and committed file membership |
| Object storage eliminates the small-files problem | Query engines still pay listing, planning, open, scheduling, and metadata costs for many tiny files |
| A YARN container is a Docker container | A YARN container is a resource allocation; YARN may optionally launch that work inside Docker |
| Kubernetes replaces HDFS | Kubernetes manages containerized workloads; durable data still needs HDFS, object storage, or another storage system |

---

## 14. Knowledge check

1. Why does horizontal scaling create new failure and coordination problems?
2. What is the difference between a NameNode and a DataNode?
3. What happens to block replication after a DataNode becomes unavailable?
4. Why are many tiny HDFS or Parquet files a problem even when they do not each reserve a full block?
5. Why is HDFS better described by its file-access model than by the phrase “eventually consistent”?
6. What responsibility does YARN have that HDFS does not?
7. During which MapReduce phase do records with the same key move together?
8. Why can Spark be faster than a multi-stage MapReduce pipeline, and why is “everything is in memory” still wrong?
9. What information belongs in the Hive Metastore, and what remains in storage?
10. When should an external Hive table be preferred over a managed table?
11. What is the difference between table partitioning, bucketing, and a Spark execution partition?
12. In `part-00000.snappy.parquet`, which name refers to the compression codec and which refers to the file format?
13. What additional responsibility does Iceberg have beyond the Parquet files it may reference?
14. Where would you place Kafka, Airflow, Ranger, and Atlas in the ecosystem responsibility map?
15. What are Hadoop's four core modules, and which three responsibilities do HDFS, YARN, and MapReduce represent?
16. How do Docker, Kubernetes, YARN, and HDFS differ from one another?

## 15. One-sentence mental model

> HDFS stores distributed file blocks, YARN allocates cluster resources, MapReduce or Spark performs distributed computation, Hive adds SQL-oriented table metadata, and formats such as Parquet, ORC, and Avro define how records are encoded in files.

## References

- [Apache Hadoop modules](https://hadoop.apache.org/modules.html)
- [Apache Hadoop HDFS architecture](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [Apache Hadoop HDFS high availability with the Quorum Journal Manager](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/HDFSHighAvailabilityWithQJM.html)
- [Apache Hadoop filesystem shell](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-common/FileSystemShell.html)
- [Apache Hadoop YARN architecture](https://hadoop.apache.org/docs/current/hadoop-yarn/hadoop-yarn-site/YARN.html)
- [Introduction to Apache Hive](https://hive.apache.org/docs/latest/introduction-to-apache-hive/)
- [Apache Hive managed and external tables](https://hive.apache.org/docs/latest/language/managed-vs--external-tables/)
- [Apache Spark cluster overview](https://spark.apache.org/docs/latest/cluster-overview.html)
- [Apache Spark RDD programming guide](https://spark.apache.org/docs/latest/rdd-programming-guide.html)
- [Apache Parquet documentation](https://parquet.apache.org/docs/)
- [Apache Parquet metadata](https://parquet.apache.org/docs/file-format/metadata/)
- [Apache ORC specification](https://orc.apache.org/specification/)
- [Apache Avro specification](https://avro.apache.org/docs/current/specification/)
- [Apache Iceberg specification](https://iceberg.apache.org/spec/)
- [Apache Spark on Kubernetes](https://spark.apache.org/docs/latest/running-on-kubernetes.html)
- [Kubernetes overview](https://kubernetes.io/docs/concepts/overview/)
- [Apache Hadoop: launching YARN applications using Docker containers](https://hadoop.apache.org/docs/current/hadoop-yarn/hadoop-yarn-site/DockerContainers.html)
