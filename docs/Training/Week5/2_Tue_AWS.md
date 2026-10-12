# Tuesday lecture: AWS for data engineering

> Status: Organized lecture guide with illustrative architecture, IAM, CLI, Glue, and SQL examples; no AWS resources were created or cloud commands executed for this revision.
> Level: Beginner → practical data engineering → production design decisions.
> Applies to: AWS storage, compute, metadata, ingestion, analytics, security, and operations.
> Last reviewed: 2026-10-06 against official AWS and Apache Spark documentation.

## Overview

A data platform must receive data, preserve it, transform it, describe it, and serve it to consumers. It also needs permissions, reliable recovery, and a sustainable operating cost. **Amazon Web Services (AWS)** provides services for these responsibilities, but selecting services does not automatically produce a correct pipeline.

Start with the data requirement, then choose the service. “We need to preserve source files for replay” leads to a storage decision. “Analysts need daily SQL summaries” leads to processing, schema, and query decisions. “The same arrival event may be delivered twice” leads to an idempotency decision.

This guide teaches the services discussed in class and the boundaries between them. Examples illustrate mechanisms; they are not a deployed platform or verified cloud lab.

## Learning objectives

After studying, you should be able to:

- Explain accounts, Regions, Availability Zones, IAM, VPCs, and serverless computing.
- Distinguish objects, blocks, database records, catalog entries, and query results.
- Connect S3, Glue, the Glue Data Catalog, and Athena without confusing storage with metadata.
- Choose among EC2, Lambda, Glue, and EMR using workload requirements.
- Explain how Redshift, RDS, DynamoDB, and SageMaker AI serve different consumers.
- Trace an event from arrival through processing, validation, publication, and recovery.
- Identify the security, correctness, performance, and billing evidence needed before production use.

## Prerequisites and study route

Conceptual prerequisites:

- Files versus tables; CSV versus Parquet; schema, grain, primary keys, and indexes.
- OLTP versus OLAP, and Bronze/Silver/Gold as data-design conventions.
- Basic Spark concepts: driver, executors, partitions, shuffles, and DataFrames.
- See [database and warehouse foundations](../Week2/4_Thur_Databases.md), [Spark foundations](../Week3/1_Mon_Spark.md), and [dbt transformations and tests](1_Mon_DBT.md) for those topics.

Read in this order:

1. Understand the platform boundaries and AWS foundations.
2. Learn permissions, networking, and durable storage.
3. Separate processing from metadata and querying.
4. Compare databases and analytical services.
5. Practice architecture choices, failure reasoning, and cost estimation.

Reading the guide requires no AWS account. Executing examples would require an account, an authorized identity, the selected Region, separately provisioned resources, and service-specific configuration. Example bucket names, account IDs, schemas, and paths are placeholders.

## Mental model: five responsibilities

```text
Producer ──► durable storage ──► processing ──► published data ──► consumer
                   S3          Glue / EMR        S3 / Redshift     SQL / BI
                    ▲                                ▲
                    └──── metadata: Glue Data Catalog ┘

Permissions: IAM and resource policies
Connectivity: VPC, subnets, routes, endpoints, security groups
Coordination: events, schedules, workflow state, retries
Operations: logs, metrics, audit, retention, cost controls
```

**Data plane** means the actual reads, writes, and computations. **Control plane** means configuration and coordination, such as defining a job or granting permissions. A catalog describes data; it does not hold the source file contents. A workflow starts and monitors work; it does not replace the transformation engine.

### Service map

| Responsibility | Service | Unit or abstraction | Data-engineering use |
| --- | --- | --- | --- |
| Identity and permissions | IAM | Identity, role, policy | Give a job access to particular datasets |
| Network isolation and routing | VPC | Virtual network and subnets | Connect compute to private databases |
| Durable object storage | S3 | Bucket, object, key | Raw files, Parquet datasets, lakehouse files |
| Virtual machines | EC2 | Instance | Run software with control over the operating system |
| Persistent block storage | EBS | Volume | Filesystems, databases, or working storage attached to EC2 |
| Short event-driven compute | Lambda | Function invocation | Validate an arrival or initiate processing |
| Managed big-data processing | EMR | Cluster or serverless application | Run Spark and other supported frameworks |
| Managed integration and ETL | Glue | Job, worker, crawler, catalog table | Transform data and maintain metadata |
| SQL over external data | Athena | Query and workgroup | Analyze S3 datasets using catalog definitions |
| Analytical warehouse | Redshift | Tables and warehouse compute | Serve repeated SQL analytics and BI |
| Managed relational databases | RDS | Database instance or supported cluster configuration | Operate application databases and ingestion sources |
| Managed key-value/document database | DynamoDB | Item, key, secondary index | Serve application access patterns and pipeline state |
| Event routing | EventBridge | Event bus, rule, target | Match events and route them to downstream services |
| Workflow coordination | Step Functions | State machine execution | Wait for jobs, branch, retry, and track completion |
| Machine-learning platform | SageMaker AI | Training job, model, endpoint | Train and deploy models using prepared data |

The tables in this guide are selection aids. Exact service behavior depends on deployment mode, configuration, Region, and version; references appear alongside the detailed sections below.

## AWS foundations: why cloud, and what still belongs to you?

### Why use AWS?

- **Elastic capacity:** acquire more resources for a busy period and release them afterward.
- **Managed services:** delegate some infrastructure maintenance to AWS.
- **Service integration:** connect storage, processing, identity, and monitoring through supported APIs.
- **Geographic placement:** place a workload near users, source systems, or required jurisdictions.
- **Consumption-based spending:** match some costs to usage instead of buying hardware in advance.

Cloud is not automatically cheaper. Continuously idle resources, repeated scans, cross-Region movement, and unmanaged retention can erase the benefit. On-premises systems can be reasonable for stable workloads, existing investments, or particular regulatory constraints.

The **shared responsibility model** separates AWS's responsibility for cloud infrastructure from your responsibility for data, access, and workload configuration. A managed service reduces some maintenance tasks; you still own business rules, data quality, retention choices, and consumer correctness. See [AWS shared responsibility](https://aws.amazon.com/compliance/shared-responsibility-model/).

### Account, Region, Availability Zone, and edge location

| Term | Meaning | Why it matters |
| --- | --- | --- |
| Account | A boundary for resources, identities, billing, and administration | Teams commonly separate development and production accounts |
| Region | A geographic area containing multiple Availability Zones | Affects locality, service availability, residency, and cost |
| Availability Zone (AZ) | An isolated infrastructure location within a Region | Helps design resilience; EC2 subnets and EBS placement have AZ implications |
| Edge location | Infrastructure closer to end users for supported edge services | Useful for content delivery; it is not a substitute for a full Region |

Choose a Region by evaluating residency rules, source and consumer proximity, supported services, quotas, resilience strategy, and price. Keeping compute and its main datasets together usually reduces transfer and latency. Multi-AZ design addresses a different failure scope from cross-Region disaster recovery. IAM is global in scope, while many compute and storage resources are regional. See [AWS Regions](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html).

### What does serverless mean?

**Serverless** means AWS manages server provisioning and operation behind a service abstraction. Servers still exist. You configure identities, capacity or concurrency settings, code, data locations, and operational behavior.

- Lambda runs functions; Glue runs managed jobs; Athena executes queries; EMR Serverless supplies job workers.
- Serverless does not mean unlimited, instantaneous, free, or free of capacity decisions.
- Startup delays, quotas, timeouts, retries, and resource limits still affect a pipeline.
- Pricing differs by service and purchase model; storage and supporting services can incur costs between executions.

The important question is: **which operational responsibilities disappear, and which ones remain?**

## IAM: who can do what?

**Identity and Access Management (IAM)** controls access to AWS resources. Authentication establishes identity; authorization determines allowed actions.

### Users, roles, and policies

| Concept | Meaning | Example |
| --- | --- | --- |
| IAM user | An identity in an account that can have long-lived credentials | A legacy integration requiring an access key |
| IAM role | An identity assumed by a trusted principal, normally using temporary credentials | A Glue job's execution role |
| IAM policy | A permission document describing allowed or denied actions, resources, and conditions | Allow reading objects under a Bronze prefix |
| Trust policy | A role policy specifying who can assume the role | Permit the Glue service to assume the job role |
| Resource policy | A policy attached to a resource | A bucket policy permitting a particular cross-account role |
| Principal | The identity making an AWS request | An assumed-role session running a job |
| ARN | Amazon Resource Name: an identifier for an AWS resource | An S3 bucket or IAM role identifier |

A role's trust policy answers **who can assume it**. Its permission policies answer **what it can do afterward**. Both relationships must work.

### Sign-in and least privilege

- Protect the account root identity with MFA and reserve it for tasks that require root access, including on personal accounts.
- Prefer federated access through IAM Identity Center or an identity provider for people, and execution roles for AWS workloads.
- Use temporary credentials rather than embedding access keys in source code or notebooks.
- `AdministratorAccess` grants broad access; a routine pipeline role should have only the actions and paths it needs.
- A job reading Bronze and writing Silver does not need permission to delete every bucket or change IAM policies.
- Permission grants can be constrained by organization policies, permission boundaries, resource policies, and explicit denies. Being an administrator does not erase every guardrail.

See [IAM security best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html).

### Small policy example: read one Bronze dataset

Illustrative identity policy; replace the bucket name before considering deployment:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example-de-bronze",
      "Condition": {
        "StringLike": {"s3:prefix": ["sensor-readings/*"]}
      }
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::example-de-bronze/sensor-readings/*"
    }
  ]
}
```

- `ListBucket` applies to the bucket; `GetObject` applies to its objects.
- The condition restricts the prefixes the caller can list.
- This policy does not supply Silver writes, logging, catalog access, a role trust policy, or access to a customer-managed encryption key.
- For SSE-KMS data, the role and KMS key policy must also permit the necessary key operations.

**Checkpoint:** explain why changing the input bucket path can break a job even when the Python code is unchanged.

## VPC: connectivity is separate from authorization

A **Virtual Private Cloud (VPC)** is a logically isolated virtual network. A **VPN** is a connection mechanism that can connect another network to it.

- **Subnet:** an address range within a VPC, located in one AZ.
- **Route table:** determines where network traffic goes.
- **Security group:** stateful traffic rules associated with supported resources or network interfaces.
- **Network ACL:** subnet-level, stateless traffic filtering.
- **Internet gateway:** supports internet connectivity for appropriately configured resources.
- **NAT gateway:** can give resources in private subnets outbound connectivity; it also introduces cost.
- **VPC endpoint:** supplies supported private connectivity to AWS services, such as an S3 gateway endpoint.

A public subnet has a route to an internet gateway; that alone does not give every instance a public address or open its ports. A private database can accept connections from an application security group without being internet-accessible.

For an EC2 application connecting to RDS, all of these must succeed:

1. The endpoint resolves and the route reaches it.
2. Traffic rules allow the connection on the database port.
3. Database authentication succeeds.
4. Database authorization permits the requested query.

An IAM permission error differs from a network timeout. An S3 bucket is not deployed into your subnet; an endpoint changes the access path to S3. See [VPC components](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html).

## S3: durable objects for lakes and lakehouses

**Amazon Simple Storage Service (S3)** is object storage. It can hold structured datasets, logs, images, audio, and other bytes. Relational databases can store binary data too, but object storage is often a better home for large file collections.

### Bucket, object, key, and prefix

```text
s3://example-de-bronze/sensor-readings/ingest_date=2026-10-06/batch-001.csv
     └──── bucket ────┘└──────────────── object key ─────────────────┘
```

- **Bucket:** container for objects and a boundary for configuration.
- **Object:** the discrete stored unit, consisting of data and metadata.
- **Key:** the object's name within the bucket.
- **Prefix:** a shared beginning of keys, useful for organizing and selecting objects.
- **Version ID:** identifies a particular object version when versioning applies.

For ordinary general-purpose buckets, slash-separated keys look like folders but are not a mounted filesystem hierarchy. S3 APIs read and write objects; EBS provides block storage that can support a filesystem. Specialized S3 bucket types have different features, so do not generalize this example to every S3 offering.

S3 provides strong consistency for object operations such as reads after successful writes and listings. That does **not** make a multi-object Spark output an atomic table transaction or make its events ordered. See [S3 concepts and consistency](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html).

### Bronze, Silver, and Gold placement

| Layer | Purpose | Typical content | Important rule |
| --- | --- | --- | --- |
| Bronze | Preserve the source for inspection and replay | Original payloads plus arrival metadata | Do not silently replace the only replayable copy |
| Silver | Produce validated, normalized data at a defined grain | Typed records, deduplication results, rejected-record references | State what is valid and what identifies a record |
| Gold | Serve a business question | Daily summaries, facts/dimensions, consumer datasets | Define metric meaning and freshness |

Two reasonable layouts are:

- Separate buckets: `example-de-bronze`, `example-de-silver`, `example-de-gold`.
- One bucket with prefixes: `bronze/`, `silver/`, `gold/`.

Separate buckets can simplify distinct access, retention, and administrative boundaries. Prefixes can simplify a smaller platform. Neither layout automatically implements medallion quality rules. Choose based on security and ownership; do not assume three buckets are mandatory.

### Data lake versus lakehouse

A **data lake** stores datasets in object storage for multiple uses and engines. A **lakehouse** adds table-management capabilities, commonly through a table format such as Apache Iceberg: snapshots, transactions, schema evolution, and supported update behavior.

- CSV or Parquet files in S3 are not automatically a lakehouse.
- Parquet is a columnar file format; Iceberg is a table format that manages files and metadata.
- A Glue Catalog table describing a plain Parquet folder does not alone create transactional publication.
- An execution engine must support the selected table format and operations.

See [Athena support for Iceberg](https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg.html).

### Versioning, lifecycle, and archival

- **Versioning** retains multiple versions of an object; a normal delete in a versioned bucket generally adds a delete marker rather than erasing every version.
- **Lifecycle rules** can transition objects between storage classes or expire them, including separate treatment for noncurrent versions.
- **S3 Glacier storage classes** are archival choices within S3. Instant Retrieval, Flexible Retrieval, and Deep Archive differ in retrieval behavior and economics.
- Flexible Retrieval and Deep Archive typically require restoration before ordinary access. Do not transition actively queried datasets there and expect unchanged query behavior.
- Versioning helps recover from overwrites; it is not a complete backup, disaster-recovery, or immutable-retention plan.
- More versions increase storage. Lifecycle rules must agree with replay windows and deletion requirements.

See [S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html), [lifecycle management](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html), and [storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html).

**Checkpoint:** a file is overwritten, a job has already processed its old contents, and a new arrival event appears. Explain which version should be processed and how you would identify it.

## EC2 and EBS: machine control and persistent block storage

**Elastic Compute Cloud (EC2)** provides virtual machines. You choose an instance type, machine image, network placement, identity, and storage. You own more software and operating-system maintenance than with a managed job service.

Choose hardware from workload evidence:

- CPU for computation; memory for large joins or caches.
- Network throughput for data movement and shuffles.
- Disk throughput for spill and working data.
- GPUs for workloads that benefit from supported parallel numerical kernels.

A data engineer does not automatically need the largest instance or a GPU. Many pipelines are limited by I/O, inefficient queries, or skew rather than available GPU compute.

### EBS versus instance store versus S3

| Storage | Access model | Persistence boundary | Typical purpose |
| --- | --- | --- | --- |
| EBS | Block device attached to EC2; commonly formatted as a filesystem | Persists independently of a running instance, subject to deletion settings | Boot disk, application data, database files, working storage |
| EC2 instance store | Local storage supplied by supported instance types | Ephemeral; data can be lost when an instance stops, terminates, or hardware fails | Reconstructable temporary data |
| S3 | Object API | Independent of an EC2 instance's lifecycle | Shared durable datasets and artifacts |

EBS is not limited to small system files; it can hold substantial datasets and databases. An EBS-backed instance commonly already has a persistent root volume. Persistence still depends on configuration: a root volume may be deleted on termination, and snapshots or another recovery mechanism are needed for recovery from deletion or corruption.

A normal EBS volume attaches within its AZ. Stopping an instance generally stops its instance compute charges, while retained EBS storage can continue to cost money. Other retained resources may also incur charges. See [EBS volumes](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html) and [EC2 lifecycle](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html).

SSH requires a reachable instance, suitable traffic rules, and valid credentials. Systems Manager Session Manager is another supported access approach when configured. Access to a shell is separate from the instance role's permission to read S3.

### GPU quotas and SageMaker access

Quotas are service- and Region-specific limits. EC2 GPU instances can require a quota increase, and an approved quota does not guarantee available capacity. SageMaker AI also has quotas; it is not a guaranteed way around EC2 restrictions. Verify the particular training, hosting, or instance quota before planning capacity. See [EC2 quotas](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-resource-limits.html) and [SageMaker AI quotas](https://docs.aws.amazon.com/sagemaker/latest/dg/regions-quotas.html).

## EMR: managed Spark and other big-data frameworks

**Amazon EMR**, historically Elastic MapReduce, runs supported big-data frameworks such as Spark and Hadoop. It is broader than a Hadoop-only cluster.

| Deployment model | What you manage | When to consider it |
| --- | --- | --- |
| EMR on EC2 | Cluster configuration, instance choices, scaling, and lifecycle | Greater cluster and hardware control; shared or specialized workloads |
| EMR Serverless | Application/job configuration, runtime, resources, and access | Spark jobs without managing an EC2 cluster |
| EMR on EKS | EMR job configuration plus a Kubernetes environment | An organization already operating suitable Kubernetes infrastructure |

For **EMR on EC2**, the common node roles are:

- **Primary:** coordinates cluster activity and runs management components.
- **Core:** runs tasks and, when HDFS is used, stores HDFS data.
- **Task:** adds compute capacity without storing HDFS data.

Persist authoritative inputs and outputs outside a disposable cluster. S3 can be the durable dataset store while the cluster supplies computation and temporary working storage. HDFS storage on a terminating cluster is not a durable lake retention strategy.

An EMR release selects a tested collection of framework versions. Check the release's Spark, Python, Scala, connectors, and APIs rather than assuming your laptop's packages match. Startup time depends on configuration and capacity; do not treat a rough classroom estimate as a guarantee.

See [EMR overview](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html) and [EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/emr-serverless.html).

### Spark Connect: laptop client, remote execution

Spark Connect introduced a client/server architecture in **Spark 3.4**. A client submits DataFrame plans to a remote Spark server; the server executes the distributed work and returns results.

- The laptop can author code and inspect bounded results.
- Large data processing still happens on the server's compute.
- Returning a large result to the laptop can still exhaust client memory.
- Classic Spark internals, RDD APIs, and direct `SparkContext` access are not interchangeable with Connect.
- A usable endpoint depends on the selected service, release, networking, and authentication.

See [Apache Spark Connect](https://spark.apache.org/docs/latest/spark-connect-overview.html). A classic Glue script using `SparkContext`, such as the example below, is not a Spark Connect client script.

## AWS Glue: processing, discovery, and metadata

**AWS Glue** is a managed data-integration service. Its Spark ETL jobs use Apache Spark with AWS integrations; Glue is not a separate imitation of Spark.

### Separate the Glue components

| Component | Responsibility | What it does not establish |
| --- | --- | --- |
| Glue ETL job | Executes transformation code | That output is correct merely because the job succeeded |
| Glue Studio | Authors and manages visual or code-based jobs | That generated logic meets your data contract |
| Glue crawler | Inspects sources and creates or updates catalog definitions | That inferred types and partitions are authoritative |
| Glue Data Catalog | Stores table/schema/location/partition metadata | The underlying dataset's file contents |
| Glue connection | Describes supported connectivity settings | That networking and database permissions already work |

A **Data Processing Unit (DPU)** measures provisioned processing capacity. A standard DPU corresponds to 4 vCPUs and 16 GB of memory; worker families and job types have additional resource characteristics. For applicable Spark jobs, billing uses DPU capacity and duration, rather than a direct fee per input row or byte. Crawlers, catalog features, and other Glue capabilities have their own billing dimensions. See [Glue components](https://docs.aws.amazon.com/glue/latest/dg/components-overview.html) and [Glue pricing](https://aws.amazon.com/glue/pricing/).

### Glue versus familiar PySpark syntax

- `SparkContext`: classic Spark execution context.
- `GlueContext`: adds Glue integrations around that context.
- `spark_session`: the Spark SQL/DataFrame entry point.
- `DynamicFrame`: Glue's record abstraction, including support for inconsistent types.
- `DataFrame`: Spark's structured transformation abstraction.
- `getResolvedOptions`: retrieves selected Glue job arguments.
- `Job.init()` and `Job.commit()`: initialize and finalize Glue job bookkeeping, including applicable bookmark behavior; they are not an S3 multi-file transaction.

See [Glue PySpark scripts](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-python.html), [GlueContext](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-crawler-pyspark-extensions-glue-context.html), and [DynamicFrame](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-crawler-pyspark-extensions-dynamic-frame.html).

### Annotated plumbing example

This classic Glue Spark example reads a pre-existing catalog table and converts its data to Parquet. It demonstrates setup and API boundaries, not complete cleaning or reliable publication. `bronze.sensor_readings`, the job arguments, and all permissions must already exist. Use a new, empty run-specific output prefix for this example.

```python
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

# Glue supplies JOB_NAME; supply OUTPUT_PATH as a custom job argument.
args = getResolvedOptions(sys.argv, ["JOB_NAME", "OUTPUT_PATH"])

# These are classic Spark and Glue runtime objects.
sc = SparkContext.getOrCreate()
glue_context = GlueContext(sc)
spark = glue_context.spark_session

job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# The catalog describes the data; the source files remain in S3.
source = glue_context.create_dynamic_frame.from_catalog(
    database="bronze",
    table_name="sensor_readings",
    transformation_ctx="read_sensor_readings",
)

# Switch to ordinary Spark DataFrame APIs.
df = source.toDF()
df.printSchema()

# A DataFrame write normally produces multiple objects under this prefix.
# errorifexists helps expose accidental reuse of this demonstration path.
df.write.mode("errorifexists").parquet(args["OUTPUT_PATH"])

# Finalizes Glue bookkeeping; does not validate or atomically publish a table.
job.commit()
```

Before treating the output as Silver, add an explicit schema, validity rules, duplicate handling, source/run identifiers, rejected-record handling, reconciliation, and a publication strategy. `errorifexists` detects a reused output directory; it does not implement safe retry recovery. A failed write may leave partial output requiring inspection.

**Checkpoint:** identify which lines are AWS Glue integration, which are Apache Spark APIs, and which names were chosen by the author.

### EMR versus Glue: compare requirements, not slogans

| Requirement | Natural starting candidate | What could change the decision? |
| --- | --- | --- |
| Periodic Spark ETL closely integrated with Glue metadata | Glue Spark job | Specialized dependencies, runtime restrictions, measured cost |
| Explicit instance choice and extensive cluster customization | EMR on EC2 | Whether managed/serverless configuration is sufficient |
| Spark processing without an EC2 cluster to maintain | Glue or EMR Serverless | Supported runtime, integrations, startup time, price/performance |
| Continuously running processing | Evaluate Glue streaming and EMR options | Latency, state recovery, connectors, utilization, operational ownership |
| Small independent action after an event | Lambda | Input size, duration, memory, or need for distributed computation |

“Continuous → EMR, occasional → Glue” is an initial intuition, not a complete rule. Glue supports streaming jobs; EMR can run transient clusters or serverless jobs. Compare total cost and recovery behavior under the actual workload.

## Athena, crawlers, and the Data Catalog: SQL over external data

**Athena** is a managed query service commonly used to query S3 data. In this pattern:

- S3 holds file contents.
- The Glue Data Catalog holds the table definition.
- Athena reads that definition and executes SQL over the referenced data.
- Query results are persisted through the configured results mechanism; Athena is not a conventional database server holding all source tables.
- Supported federated connectors can query sources outside S3, but require separate connectivity, permissions, and connector configuration.

### Schema-on-read

**Schema-on-read** applies a table schema when interpreting stored data. Raw storage does not need to enforce every table rule at file arrival, but queries still need compatible column names, types, formats, and locations.

```text
S3 objects ── inspected by crawler ──► Glue Data Catalog table
    ▲                                            │
    └──────────── Athena reads objects ◄─────────┘
                    using table metadata
```

The Data Catalog fills a role similar to the Hive Metastore. A catalog “database” groups metadata tables; it is not an RDS database server or a physical directory.

A crawler is **optional**. You can define tables through Athena DDL, Glue APIs, or infrastructure configuration. Automatic inference helps explore unfamiliar data; a controlled schema is often preferable for stable production contracts. See [creating Athena tables](https://docs.aws.amazon.com/athena/latest/ug/creating-tables.html).

### Minimal external-table example

Assume a separate illustrative dataset already contains unpartitioned Parquet files with `sensor_id` as string, `reading_ts` as timestamp, and `temperature_c` as double. This schema is an example contract, not a claim about existing course data. The `silver` catalog database and Athena result settings must exist.

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS silver.sensor_readings (
    sensor_id STRING,
    reading_ts TIMESTAMP,
    temperature_c DOUBLE
)
STORED AS PARQUET
LOCATION 's3://example-de-silver/sensor-readings/published/';

SELECT
    sensor_id,
    AVG(temperature_c) AS average_temperature_c
FROM silver.sensor_readings
WHERE reading_ts >= TIMESTAMP '2026-10-06 00:00:00'
  AND reading_ts < TIMESTAMP '2026-10-07 00:00:00'
GROUP BY sensor_id;
```

Creating the external table registers metadata; it does not upload, clean, or convert files. `IF NOT EXISTS` also does not repair an existing table with the wrong definition. Athena `CREATE TABLE AS SELECT` is different: it executes a query and writes result data, commonly to S3. See [external-table DDL](https://docs.aws.amazon.com/athena/latest/ug/create-table.html) and [CTAS](https://docs.aws.amazon.com/athena/latest/ug/create-table-as.html).

### Partitions and cost

- A prefix such as `reading_date=2026-10-06/` can organize a partitioned dataset, but a folder name alone does not establish query metadata.
- Register partitions or configure a supported mechanism such as partition projection or table-format metadata.
- Filter on partition columns to reduce the relevant files.
- Parquet, compression, and selecting only needed columns can reduce bytes scanned.
- Too many tiny files increase overhead; choosing a partition key requires workload evidence.
- On-demand SQL queries commonly charge by data scanned; provisioned-capacity options use a different model. Workgroup scan controls help contain accidental large queries.

See [Athena partitioning](https://docs.aws.amazon.com/athena/latest/ug/partitions.html) and [Athena pricing](https://aws.amazon.com/athena/pricing/).

**Checkpoint:** why can the files exist in S3 while Athena returns no rows, fails to parse them, or scans far more data than expected?

## Lambda and EventBridge: react to arrivals

**Lambda** runs functions without requiring you to maintain a VM. Common data-engineering uses include checking an object, adding metadata, or initiating a larger job. It is not the default engine for a large Spark transformation.

- A function has bounded memory, temporary storage, concurrency, and execution duration.
- The maximum invocation duration is 15 minutes.
- Execution environments can be reused; durable state should live in an external store.
- Invocation volume, duration, retries, concurrency, and downstream services determine cost. A small function is not automatically inexpensive at any volume.

See [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html).

### Direct notification versus routed event

Two supported approaches include:

- **S3 notification → Lambda:** invoke a function for matching object events.
- **S3 → EventBridge → downstream target/workflow:** enable event delivery, match a rule, and route the event.

EventBridge routes event descriptions; it does not itself clean a CSV. EventBridge Scheduler supplies time-based scheduling, which is a separate concept from an object-arrival event. Event payloads are structured messages, commonly JSON, rather than the entire uploaded dataset.

S3 notifications are delivered at least once and can arrive out of order. Design for duplicate notifications. Avoid writing outputs into the same triggering path without filters, because that can create a processing loop. See [S3 event notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html).

### Starting a job is different from completing a workflow

A function can start a Glue job and return successfully while that job later fails. A workflow must wait for completion, inspect results, and decide whether consumers may see the output. Step Functions supports a Glue job integration that waits for completion; Glue workflows or another orchestrator can also coordinate relevant work. See [Step Functions and Glue](https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html).

A robust event handler should:

1. Validate the event source, bucket, key, and applicable version.
2. Establish a stable ingestion identity rather than using only a notification ID.
3. Claim or record work safely so concurrent deliveries cannot both publish it.
4. Start and monitor processing with bounded retries.
5. Validate results before publication.
6. Record completion only after the intended publication boundary succeeds.

## Redshift: an analytical warehouse

**Amazon Redshift** is an analytical SQL warehouse using **massively parallel processing (MPP)**: multiple compute resources cooperate on a query. It supports OLAP workloads, columnar storage, and parallel execution. Distribution, data skew, joins, and workload concurrency still affect performance; MPP is not a guarantee that every query is fast.

### Provisioned versus serverless

- **Provisioned Redshift:** select and operate a provisioned warehouse configuration, with supported scaling and lifecycle features.
- **Redshift Serverless:** use managed warehouse capacity without provisioning a conventional cluster. Workgroups organize compute settings; namespaces organize database-related resources.
- Both modes exist. Serverless did not replace provisioned Redshift.
- On-demand Serverless compute is measured in **RPU-hours**, with storage billed separately. It is not simply a flat storage subscription plus a fixed price per query.
- Capacity, usage limits, concurrency, and billing model influence costs. Reservations introduce commitments and different idle-cost implications.

See [Redshift Serverless on-demand billing](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing-on-demand.html) and [billing details](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing.html).

### COPY: bulk loading

`COPY` bulk-loads data from supported sources into an existing Redshift table. Parallel bulk loading is usually preferable to sending individual inserts for a large file dataset.

```sql
COPY analytics.sensor_readings
FROM 's3://example-de-silver/sensor-readings/load-batch-001/'
IAM_ROLE 'arn:aws:iam::123456789012:role/example-redshift-load-role'
FORMAT AS PARQUET;
```

This requires a compatible target table, authorized attached role, supported file layout and types, and appropriate regional configuration. It does not create the table or guarantee deduplication. Loading the same batch again can duplicate data; use a batch ledger and staging/merge strategy where appropriate. See [Redshift COPY](https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html).

### Athena versus Redshift versus Snowflake

| Choice | Common starting use | Important consideration |
| --- | --- | --- |
| Athena | SQL exploration and analysis over S3 datasets | File layout, scan cost, catalog accuracy, query latency |
| Redshift | Managed warehouse tables and recurring analytical workloads | Load strategy, physical design, concurrency, warehouse capacity |
| Snowflake | Managed warehouse and platform capabilities on supported clouds | Platform governance, workload design, integrations, commercial model |

Athena and Redshift can coexist. Redshift can also query external lake data through supported features such as Spectrum. Redshift and Snowflake both have broader capabilities than a simple “warehouse only versus full platform” comparison. Google BigQuery is another managed analytical platform; compare workload and pricing dimensions rather than assuming that all serverless warehouses charge identically.

## RDS and DynamoDB: operational data systems

### RDS: managed relational engines

**Relational Database Service (RDS)** manages supported database engines and associated infrastructure. Examples include PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, and Db2; Amazon Aurora is an AWS relational offering compatible with MySQL or PostgreSQL. Availability and options depend on the engine and Region.

- Applications commonly use RDS for transactions, constraints, and indexed access.
- A database endpoint supplies connectivity; a Python connection/cursor submits work using database credentials and permissions.
- RDS manages infrastructure and supported maintenance, but you still design schemas, queries, access, and recovery requirements.
- You cannot treat an RDS database as an ordinary EC2 shell and install arbitrary software or an unsupported engine.
- Relational databases support multiple indexes per table. Indexes improve selected reads while adding storage and write maintenance.
- RDS can be an ingestion source for analytical pipelines. Large scans can burden the application; evaluate replicas, incremental extraction, or CDC.

Using RDS instead of self-hosting a database on EC2 is primarily an operational responsibility decision. EC2 with EBS can persist database data, but then your team owns database installation, maintenance, backup configuration, and availability. See [RDS overview](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html).

### DynamoDB: design around access patterns

**DynamoDB** is a managed NoSQL key-value and document database. It is not a columnar analytical warehouse or a column-family database optimized for arbitrary column comparisons.

- A table has a partition key and, optionally, a sort key.
- Items can have different non-key attributes.
- Secondary indexes support additional key-based access patterns, including global secondary indexes.
- Good key design spreads load and matches the application's queries.
- Broad scans are different from efficient key lookups; hot keys can cause concentrated load.
- Global secondary index reads are eventually consistent. Do not assume identical consistency across every access path.
- On-demand and provisioned capacity models have different economics; indexes, replication, and request patterns also affect cost.

Possible data-engineering uses include ingestion state, conditional claims for work, or serving a lookup dataset. Calling it “the fastest” or “very cheap” without a workload, consistency requirement, and measurement is not useful. See [DynamoDB overview](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html) and [read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html).

## SageMaker AI: the boundary with machine learning

**SageMaker AI** supplies capabilities for building, training, and deploying machine-learning models. The broader SageMaker platform also includes data and analytics capabilities, so distinguish the particular product and task being discussed.

- Glue typically prepares and integrates data; SageMaker AI trains or hosts a model using prepared data.
- A pipeline may publish validated training data in S3, then start a training job.
- GPUs can accelerate supported matrix and tensor computations, such as neural-network training and inference.
- Tokenization converts text into token identifiers; it does not itself produce all of a model's learned weights. A model uses learned parameters to compute predictions.
- Not every model needs a GPU. Match hardware to framework support, dataset size, runtime, and cost.
- Data engineers own training-data lineage, point-in-time correctness, access, and leakage prevention alongside ML teams.

See [SageMaker AI overview](https://docs.aws.amazon.com/sagemaker/latest/dg/whatis.html) and the [quota reference](https://docs.aws.amazon.com/sagemaker/latest/dg/regions-quotas.html).

## Requirements and invariants before choosing an architecture

Write down the contract first:

- **Input:** format, schema version, record grain, source identity, expected volume, arrival pattern.
- **Output:** consumer, business meaning, grain, valid values, location, and schema.
- **Freshness:** when complete data must be available, and how late arrivals behave.
- **Replay:** how long inputs remain available and how duplicates/corrections are recognized.
- **Security:** who may read raw data, derived data, secrets, and logs.
- **Capacity:** rows, bytes, file count, peak arrivals, concurrency, and expected growth.
- **Cost:** budget for storage, processing, querying, networking, and operations.

Useful invariants include:

- Reprocessing the same source version does not duplicate published logical records.
- Input records reconcile to accepted, rejected, and explicitly explained exclusions.
- Failed transformations do not expose partial output as complete data.
- Each published dataset identifies its input versions, schema, code version, and run.
- Source retention covers the agreed recovery window.

These guarantees come from the design and evidence, not from the number of services in the diagram.

## Architecture patterns and data ownership

### Pattern 1: an analytical lake

```text
Application logs ──► S3 raw ──► Glue or EMR job ──► S3 curated Parquet
                                                       │
                                      catalog definition / partitions
                                                       ▼
                                              Glue Data Catalog
                                                       │
                                                       ▼
                                                Athena ──► analyst
```

Use this when durable files and SQL over lake datasets meet the consumer requirements. A crawler can help discover unfamiliar raw logs; controlled definitions can describe curated output. The processing job owns validation and publication. Athena owns query execution, not source ingestion.

### Pattern 2: operational database to analytical warehouse

```text
Application ──► RDS ── extraction / CDC ──► S3 landing
                                                │
                                         validate and load
                                                ▼
                                         Redshift staging
                                                │
                                      SQL / dbt transformations
                                                ▼
                                         warehouse marts ──► BI
```

Use this when the application needs transactions and analysts need repeated analytical joins or summaries. RDS remains the application source of truth. Extraction must preserve ordering or source positions where required; the warehouse must handle retries and updates. dbt manages warehouse transformations, while another process owns extraction and loading.
- NOTE: `warehouse marts → BI` means (BI = Business Intelligence) curated analytical data feeds a reporting or dashboard tool. That could be Power BI or another tool

### Pattern 3: ML data preparation

```text
Source datasets ──► S3 ──► Glue / EMR validation and feature preparation
                                               │
                                 versioned training dataset in S3
                                               ▼
                                       SageMaker AI training
                                               │
                                       evaluated model / endpoint
```

The critical boundary is reproducibility: identify the exact data and feature logic used for training. A technically successful training run can still use leaked, incomplete, or incorrectly labeled data.

### Ownership table

| Boundary | Owner's responsibility | Evidence to retain |
| --- | --- | --- |
| Producer → landing | Deliver complete source data and identify corrections | Source ID/version, arrival time, expected count |
| Landing → curated | Apply the schema, quality, and duplicate rules | Input/output counts, rejections, code/schema version |
| Curated → catalog | Describe the published data accurately | Table location, types, partitions, schema changes |
| Catalog/warehouse → consumer | Serve the agreed grain and freshness | Query checks, publication timestamp, reconciliation |
| Platform → every boundary | Supply access, connectivity, monitoring, and recoverability | Access checks, logs, audit, restore and replay evidence |

## Failure model and recovery

| Failure | Observable symptom | Recovery owner and action | Evidence that recovery worked |
| --- | --- | --- | --- |
| Duplicate arrival event | Same batch processed twice | Ingestion owner uses a stable source/version identity and conditional work claim | Rerun preserves logical output count |
| Concurrent retries | Two runs publish the same input | Workflow/publisher coordinates claims and publication | One accepted publication; other run safely stops |
| Invalid schema or malformed row | Parser fails or silent NULLs appear | Transformation owner rejects/quarantines with reason and source reference | Accepted + rejected + explained exclusions reconcile to input |
| Job fails after writing some files | A prefix contains incomplete output | Publisher isolates run outputs and publishes only validated completion | Consumers see the previous complete version or the new complete version |
| Catalog points to wrong location | Empty result or unexpected rows | Metadata owner checks location, format, schema, and partitions | Bounded queries reconcile to the published dataset |
| IAM or KMS denial | `AccessDenied` | Platform owner inspects caller, action, resource, policies, and key access | Intended read/write succeeds with scoped permissions |
| Network failure | Connection timeout | Platform owner checks DNS, routes, endpoints, and traffic rules | Connectivity succeeds before data processing is retried |
| Quota or capacity exhaustion | Throttling or job start failure | Platform owner bounds concurrency and checks quota/capacity | Backlog drains within the freshness target |
| Lifecycle removes needed input | Backfill cannot read its source | Dataset owner restores archived data where possible and repairs retention | Recovery window has accessible inputs |
| Repeated Redshift load | Duplicate warehouse rows | Load owner uses batch identity and staging/merge strategy | Counts and business keys reconcile after replay |

For plain files, write each run to an isolated location, validate it, and then deliberately change the consumer-visible pointer or metadata. An S3 prefix is not a transaction. A transactional table format can provide stronger table publication semantics when the engine and workflow use it correctly.

**Failure demonstration to reason through:** a Spark job writes three of four output files and crashes. A retry appends four new files into the same queryable prefix. Explain which records Athena might expose, why successful retry status is insufficient, and how isolated output plus controlled publication changes the result. This is a proposed experiment; it was not executed.

## Data quality, testing, and evidence

A green job status proves only that its execution completed according to the service. Validate data and consumer behavior separately.

| Check | Expected guarantee | Suggested evidence | Current status |
| --- | --- | --- | --- |
| Documentation syntax | Examples are structurally readable | Parse JSON/Python, inspect fences and links | Static validation only; see repository coverage |
| Identity and permissions | Correct role can perform only intended actions | Scoped allowed and denied access tests | Pending in AWS |
| Schema and values | Published types and business rules hold | Valid and invalid bounded fixtures | Pending |
| Reconciliation | Records are accounted for | Input, accepted, rejected, and output counts | Pending |
| Duplicate replay | Same source version does not duplicate logical output | Deliver the same event twice | Pending |
| Partial failure | Incomplete files are not published | Interrupt a job and retry it | Pending |
| Query correctness | Consumer sees intended grain and values | Athena/Redshift assertions over fixture data | Pending |
| Capacity and cost | Freshness and budget hold under representative load | Job metrics, query scans, billing observations | Pending |
| Recovery | Retained source and configuration can restore output | Backfill/restore rehearsal | Pending |

Keep fixture evidence separate from scale claims. A small successful load does not verify production throughput, concurrent publication, or disaster recovery.

## Debugging guide

Start at the first failing boundary:

1. **Identity:** verify account, assumed role, and Region. An expired login differs from an authorization denial.
2. **Input:** confirm bucket, exact key/version, format, size, completeness, and encryption.
3. **Connectivity:** inspect endpoint resolution, routes, traffic rules, and service endpoints when applicable.
4. **Job:** inspect CloudWatch logs, run arguments, runtime version, worker usage, Spark failures, and rejected rows.
5. **Output:** compare counts and grain; look for partial or duplicated files and an incorrect publication path.
6. **Metadata:** check schema, location, format, partitions, and whether a crawler changed the definition.
7. **Consumer:** inspect query results, freshness, scan volume, warehouse load errors, and business assertions.

A minimal, read-only CLI orientation after authorized IAM Identity Center setup could be:

```bash
aws sso login --profile de-dev
aws sts get-caller-identity --profile de-dev
aws s3api head-object \
  --bucket example-de-bronze \
  --key sensor-readings/ingest_date=2026-10-06/batch-001.csv \
  --profile de-dev \
  --region us-east-1
```

`de-dev` is an author-chosen profile name, not an AWS keyword. Configure it with the organization's actual sign-in settings; `us-east-1` is illustrative. Caller identity verifies who the request uses, not all of its dataset permissions. Object metadata inspection does not validate file contents. See [AWS CLI IAM Identity Center configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

## Common pitfalls

| Tempting assumption | More precise understanding |
| --- | --- |
| A bucket is the discrete data unit | A bucket contains objects; an object is the stored unit |
| Three buckets automatically create medallion architecture | Quality, grain, access, lineage, and publication rules create the layers |
| VPC means VPN | A VPC is a virtual network; a VPN connects networks |
| EC2 cannot keep data | EBS-backed storage can persist, subject to lifecycle and deletion settings |
| EBS is only for operating-system files | EBS can support application datasets and databases too |
| Root is the normal personal-account login | Use an appropriate non-root identity for routine work |
| Glue is not real Spark | Glue Spark jobs use Apache Spark plus AWS integrations |
| EMR must always be an EC2 cluster | EMR also has Serverless and EKS deployment models |
| Athena requires a crawler | Tables can also be defined explicitly |
| A crawler validates business correctness | It discovers metadata; quality rules require separate checks |
| Serverless means nothing costs money while idle | Stored data, retained capacity, reservations, and supporting resources can incur costs |
| RDS tables have only one index | Relational tables can have multiple indexes |
| DynamoDB is a columnar warehouse | It is a key-value/document service oriented around access patterns |
| Job completion means output is safe to publish | Quality, completeness, and publication checks are separate |
| A source event is processed exactly once | Delivery and retries require explicit idempotency and coordination |

## Production considerations

### Security and governance

- Assign separate runtime roles where stages need different privileges; keep analyst access away from raw sensitive data where appropriate.
- Keep S3 public access blocked unless there is a deliberate public-data requirement.
- Use encryption in transit and at rest; know who controls and can use encryption keys.
- Store credentials in an appropriate secrets service; do not log passwords, tokens, or raw sensitive records.
- Use CloudTrail for audit and CloudWatch for operational logs/metrics; choose required coverage and retention rather than assuming every event is retained automatically.
- Consider Lake Formation when centralized lake permissions and supported fine-grained access are needed. Catalog metadata alone is not access enforcement.
- Apply retention and deletion requirements to raw data, derived data, noncurrent object versions, backups, results, and logs.

See [Lake Formation permissions](https://docs.aws.amazon.com/lake-formation/latest/dg/permissions-reference.html).

### Performance, capacity, and cost

A useful estimate is:

```text
Monthly platform cost ≈ storage + requests/retrieval + processing
                      + analytical queries + networking + operations
```

| Service/boundary | Main dimensions to inspect | Common waste |
| --- | --- | --- |
| S3 | Stored bytes, class, requests, retrieval, retention, versions | Unbounded old versions or unnecessary copies |
| EC2/EBS | Instance time, volume capacity/type, retained resources | Idle instances and forgotten volumes |
| Glue | Applicable DPU-hours, job runs, crawler/catalog usage | Excess workers, repeated full reads, frequent unnecessary crawls |
| EMR | Deployment-specific compute/storage/service charges | Unused cluster capacity or oversized jobs |
| Lambda | Requests, duration, memory, retries | Trigger loops and retry storms |
| Athena | On-demand bytes scanned or selected capacity model | Broad scans of uncompressed CSV |
| Redshift | Selected capacity/purchase model, storage, workload | Unbounded concurrency or repeated inefficient queries |
| Network | Transfer paths, NAT, endpoints, cross-Region movement | Moving the same dataset repeatedly |

For applicable Glue processing, `DPU-hours ≈ allocated DPUs × billed runtime hours`; for example, 4 DPUs for 15 billed minutes is 1 DPU-hour before considering applicable minimums or other charges. This is a unit calculation, not a quoted AWS price.

Measure input bytes, output bytes, files, job duration, worker utilization, shuffle/spill, failed attempts, scan volume, query latency, and freshness. Then optimize the bottleneck. Prices, minimums, quotas, and available instance types change; consult the chosen Region's current pricing and verify with billing data.

Set budgets and alerts, with appropriate service usage limits. Budget alerts are not universal automatic spending caps. A job finishing faster is not necessarily cheaper if it uses substantially more capacity.

### Observability, recovery, and change

- Correlate source identity, object version, event, workflow execution, job run, and publication version.
- Alert on missing arrivals and stale datasets as well as explicit job failures.
- Record quality metrics with units and stable labels; avoid using every object key as a metric dimension.
- Agree on **RPO** (acceptable data loss) and **RTO** (acceptable recovery time).
- Version transformation code, schemas, job definitions, and infrastructure; promote tested configurations between environments.
- Treat a schema change as a consumer contract change. Test old and new records before updating a shared catalog definition.
- Use retained inputs for backfills, compare old/new output, and publish deliberately. Do not replay into a live append path without a duplicate strategy.
- Verify recovery by reconciliation and consumer checks, not just a successful restart.

## Knowledge check

Use these questions to explain mechanisms in your own words:

1. Which components hold bytes, hold metadata, execute code, route events, and answer queries?
2. How can an IAM permission be correct while an RDS connection still times out?
3. What changes when a job reads SSE-KMS objects rather than objects using S3-managed keys?
4. Why can one bucket with prefixes and three separate buckets both implement medallion layers?
5. What remains your responsibility when moving from EC2 Spark to a managed job service?
6. When would you choose explicit catalog definitions instead of a crawler?
7. Why can converting CSV to Parquet change analytical cost without changing logical row count?
8. What evidence would justify choosing Glue over EMR Serverless for a particular job?
9. How could duplicate events create duplicate output even when every job reports success?
10. Why is an RDS read replica or CDC feed sometimes preferable to repeatedly scanning the application database?
11. Which parts of a warehouse load need idempotency beyond `COPY` itself?
12. What would you measure before describing a DynamoDB or Athena workload as inexpensive?

## Architecture decision exercise

Without deploying anything, consider an application-log platform with changing requirements:

- Begin with hourly compressed logs, daily SQL exploration, and 30 days of replayable source retention.
- Add a curated dataset with a stable schema and a five-minute freshness target.
- Add many repeated dashboard queries with predictable latency expectations.
- Add sensitive identifiers, duplicate arrivals, and a request to backfill a changed rule.

For each stage, record the chosen storage, processing, metadata, query, coordination, and access boundaries. Explain one alternative, one failure scenario, and the measurement that would make you reconsider the choice. A larger diagram is not automatically a better design.

## Completion checklist

- [ ] I can explain the core services by responsibility rather than memorized slogans.
- [ ] I can identify where an input, schema, job, output, and query result live.
- [ ] I can state the pipeline's grain, freshness, replay, and publication invariants.
- [ ] I can distinguish IAM, database permissions, encryption-key access, and network connectivity.
- [ ] I can compare processing and query options using requirements and billing units.
- [ ] I can describe duplicate, partial-failure, schema-change, and recovery behavior.
- [ ] I can identify which claims are documentation-based and which require cloud execution evidence.

## Possible follow-up learning artifacts

- An architecture-decision lab could compare the same workload across a lake query pattern, a warehouse pattern, and an ML preparation pattern, then introduce failures and cost evidence.
- Common-stack comparisons could cover S3/Glue/Athena, S3/Redshift/dbt, Snowflake/dbt, and Databricks lakehouse workflows. Evaluate responsibilities and requirements rather than treating stacks as fixed recipes.
- Standalone interview banks remain a separate workflow from these lecture notes. These follow-up ideas are not implemented or verified by this revision.
