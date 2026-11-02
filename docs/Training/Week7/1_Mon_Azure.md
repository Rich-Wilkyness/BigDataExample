# Week 7 Monday — Azure Foundations for Data Engineering

> Level: Beginner to intermediate
> Focus: Azure resource hierarchy, identity, ADLS Gen2, and the lakehouse platform
> Practical companion: [Monday steps](1.1_Mon_Steps.md)
> Evidence: Conceptual guide; no cloud execution during this revision
> Primary documentation reviewed: 2026-10-22

## Overview and learning objectives

A data platform needs somewhere to keep data, identities allowed to access it, compute that processes it, and workflows that coordinate the work. Azure provides these as separate services. Understanding their responsibilities helps you diagnose failures and choose permissions.

After this lesson, you should be able to trace the resource hierarchy, distinguish resource management from file access, explain how ADLS Gen2 relates to Blob Storage, read an `abfss://` path, and identify the responsibilities of Spark, Databricks, Delta Lake, and Unity Catalog. Prerequisites are basic files, SQL tables, and the AWS service roles covered previously.

## 1. Mental model: identity, resources, and billing

```text
Microsoft Entra tenant: directory of users, groups, and applications
  └── Subscription: billing, quotas, and resource-management scope
        └── Resource group: related resources managed together
              ├── Storage account
              ├── Data Factory
              └── Azure Databricks workspace
```

A **tenant** establishes the identity directory. A **subscription** is associated with a tenant and contains Azure resources. A **resource group** groups resources by lifecycle. A **resource** is an individual service instance. A resource group's region stores its metadata; its resources can be in different permitted regions.

A tenant is not a role, and a subscription is not a policy. They are boundaries at which identities, resources, permissions, and administration interact. Selecting the correct subscription matters: the same user can access several subscriptions.

## 2. Authentication, authorization, and scope

**Authentication** establishes who a caller is. **Authorization** determines what the caller can do. Microsoft Entra ID provides identities and tokens; Azure RBAC assigns a role to a principal at a scope.

| Concept | Meaning | Example |
| --- | --- | --- |
| Principal | Identity receiving access | Your user or a factory's managed identity |
| Role | Allowed operations | Storage Blob Data Contributor |
| Scope | Resources covered by a grant | One storage account |
| Managed identity | Azure-managed application identity | ADF authenticating without a stored account key |

The **management plane** creates/configures resources. The **data plane** reads/writes their contents. Contributor can manage resource settings but does not itself grant Entra-based access to blob data. Storage Blob Data Contributor grants storage data operations. Assigning roles usually needs separate administrative permission.
- TODO: can you help me find a visual for this? I'm not sure i understand how each of these entra vocabularies relate... or give me an example of their use in a pipeline/resource?

A system-assigned managed identity belongs to one resource. A user-assigned managed identity is a separately managed resource reusable by supported services. ADF, a Databricks Access Connector, and your signed-in user are different callers. Access granted to one does not transfer to another.
- TODO: again, not following this entra stuff. how does managed identity differ from the other entra ideas? 

ADLS also supports POSIX-style access control lists for directories and files. A sufficient RBAC data grant can authorize an operation without an ACL check; ACLs do not subtract access already granted by that role. Where ACLs supply access, traversing parent directories requires appropriate execute permission. See the [ADLS access-control model](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-access-control-model).

## 3. Blob Storage and ADLS Gen2

Azure Blob Storage persists objects in containers within a storage account. **ADLS Gen2** adds data-lake capabilities, including a hierarchical namespace, to Blob Storage. It is not a separate processing engine.

```text
Storage account
  └── Container / filesystem: bronze
        └── Directory: customers/raw
              └── File: customers.csv
```

With a flat namespace, folders are prefixes in object names. With a **hierarchical namespace (HNS)**, directories are explicit objects with filesystem operations. A directory rename can be a namespace operation rather than copying every file beneath a prefix. This benefits analytical workloads and directory-based permission management.

A container is also called a **filesystem** in ADLS APIs. CSV, JSON, Parquet, and other file types can be stored there. HNS does not convert a file into a table or validate its rows. ADLS Gen1 is the retired predecessor, retained here only as historical terminology.

### Reading an ABFS URI

```text
abfss://<filesystem>@<account>.dfs.core.windows.net/<directory>/<file>
abfss://bronze@adlsricharda35b84.dfs.core.windows.net/customers/raw/customers.csv
```

`abfss` is the secure Azure Blob File System URI scheme used by compatible clients. The URI identifies a location; it grants no permissions. Authentication, authorization, and network reachability remain necessary. The concrete account above comes from the captured lab, not a current resource inspection. See [ADLS Gen2 overview](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-introduction).

## 4. Translate AWS knowledge by responsibility

| Responsibility | AWS example | Azure example | Limit of the comparison |
| --- | --- | --- | --- |
| Object/data-lake storage | S3 | Blob Storage / ADLS Gen2 | Namespaces and authorization differ |
| Virtual machines | EC2 | Azure Virtual Machines | Instance families and management differ |
| Event ingestion | Kinesis Data Streams | Event Hubs | Partition and consumer details differ |
| Identity and access | IAM and account boundaries | Entra ID, managed identities, RBAC | No one-to-one object mapping |
| Workflow coordination | Step Functions / managed Airflow | Data Factory | ADF also handles data integration and movement |
| Distributed analytics | EMR / Glue processing | Databricks / Synapse Spark | Platform and execution responsibilities differ |
| SQL analytics | Redshift | Synapse SQL / Databricks SQL | Architectures and workload choices differ |

Data Factory defines pipelines, connectors, dependencies, and activities. A Copy activity moves data; a notebook activity delegates processing. The orchestrator does not become the Spark engine because it schedules the work.

## 5. Spark, Databricks, Delta Lake, and Unity Catalog

| Name | Responsibility | What still needs application design |
| --- | --- | --- |
| Apache Spark | Distributed SQL and DataFrame processing | Correct joins, keys, and transformations |
| Azure Databricks | Managed workspace, compute, notebooks, jobs, data/AI tooling | Business logic and workload choices |
| Delta Lake | Open table format/ecosystem with versioned transaction metadata | Business validation, replay, and retention policy |
| Unity Catalog | Governance and metadata for registered data/AI objects | Correct grants and external storage setup |

Delta Lake, Apache Iceberg, and Apache Hudi are open table-format projects. Delta is also open source. Parquet describes data files; a table format describes table state across files. Their metadata formats and compatible readers differ.

A Databricks notebook generally provides a `spark` session on supported attached compute. `spark` is a session object, not a top-level library replacing all imports. You still import functions and types. Transformations describe a plan; actions such as table writes and `count()` request results.

A workspace organizes collaborative work and execution. Unity Catalog can govern data used by several appropriately configured workspaces. Table names use `catalog.schema.table`; volumes expose governed files through `/Volumes/catalog/schema/volume/...`. A workspace boundary does not automatically mean entirely separate governance.

**Photon** is Databricks' vectorized execution engine implemented in C++ for supported SQL/DataFrame operations. It is not the whole Spark project rewritten in C++. Speedups depend on the workload and supported operations. Serverless compute manages infrastructure; classic compute exposes more provisioning choices. Metastore access depends on compute and configuration, not merely whether resources are manually provisioned. See [Photon](https://learn.microsoft.com/en-us/azure/databricks/compute/photon).

## 6. Medallion architecture and data ownership

```text
Source → Landing files → Bronze → Silver → Gold → Analysis
```

Landing retains source files. Bronze makes source data available with minimal processing. Silver establishes a cleaned contract with keys, types, and validation rules. Gold serves an analytical purpose through facts/dimensions or aggregates. These are responsibilities you implement, not guarantees created by naming a directory.

For `customers.csv`, define what one row represents, which fields identify a customer, how missing values appear, and which duplicates are acceptable before choosing cleanup logic. A successful upload proves storage access; it does not prove unique or valid records. Preserve source input so transformations can be investigated and replayed.

## 7. Synapse and Microsoft Fabric in context

Azure Synapse combines capabilities including SQL analytics, Spark, and integration. Choose services based on the workload, existing architecture, governance, and operating model. Classroom preferences are not evidence that an entire industry has abandoned a platform.

Microsoft Fabric is a SaaS analytics platform with integrated workloads and OneLake, including data integration, engineering, warehousing, real-time analytics, and Power BI experiences. It is not simply an Azure subscription containing bundled Azure Databricks instances. Fabric's Data Factory and Spark experiences differ from standalone ADF and Azure Databricks. See [Microsoft Fabric overview](https://learn.microsoft.com/en-us/fabric/fundamentals/microsoft-fabric-overview).

Informatica, Talend, Pentaho, and Palantir Foundry also address data integration/platform needs. They are context from the discussion, not requirements for this lab.

## 8. Failure model and production considerations

| Symptom | Boundary to inspect |
| --- | --- |
| Cannot create a resource group | Tenant/subscription selection and management permission |
| Can see an account but cannot upload | Storage data role, applicable ACLs, network access |
| Local file not found | Actual filename and absolute local path |
| Upload works but notebook read fails | Notebook identity/governance, path, compute access |
| Files exist but counts are wrong | Source contract and processing rules |

Keep secrets out of notebooks and notes. Use approved regions, reuse intended existing resources, and understand ownership before stopping shared compute. Resource names are labels: a shell variable named `STUDENT` does not create an Entra user.

## Knowledge check and completion checklist

1. Why can Contributor create a storage account yet fail to read files using Entra authentication?
2. What changes with HNS, and what remains the application's responsibility?
3. What does each part of an `abfss://` URI identify?
4. How do Spark, Delta, and Unity Catalog provide different capabilities?
5. What would you check before calling customer records “Silver”?

- [ ] I can explain tenant → subscription → resource group → resource.
- [ ] I can distinguish identity, role, and scope.
- [ ] I can separate storage, compute, orchestration, table formats, and governance.
- [ ] I can identify whether a failure concerns local files, cloud access, or data correctness.

## References

- [Azure resource management](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/overview)
- [Managed identities](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview)
- [ADLS access-control model](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-access-control-model)
- [ADLS Gen2 introduction](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-introduction)
- [Azure Databricks introduction](https://learn.microsoft.com/en-us/azure/databricks/introduction/)
