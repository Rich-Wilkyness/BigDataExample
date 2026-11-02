# GCP Data Engineering — From AWS and Azure to the Jobs/SNAP Capstone

> Level: Beginner to intermediate, with production design questions
> Purpose: Learn GCP theory, choose project technologies, then implement in explained checkpoints
> Project companion: [GCP learning plan and steps](us-jobs-snap-pipeline/gcp-learning-plan.md)
> Evidence: Documentation and pricing research only; no GCP account, resource, deployment, or pipeline execution verified
> Primary sources reviewed: 2026-10-23; recheck offers and regional prices before using paid services

## Overview and study order

You already know the shape of a data pipeline: retrieve data, preserve raw input, transform it, publish tables, and coordinate the work. GCP changes the platform services and operating details. Your Python, PySpark, SQL, modeling, and failure-handling knowledge remains useful.

Use this guide in three passes:

1. **Understand:** Read Sections 1–7, connecting each responsibility to the AWS and Azure lessons.
2. **Choose:** Read Sections 8–10 for the proposed project stack and personally funded cost strategy.
3. **Build:** Follow the [project checkpoints](us-jobs-snap-pipeline/gcp-learning-plan.md), beginning with account choice and a small warehouse exercise. Execute one checkpoint at a time and record what actually happened.

By the end, you should be able to trace an observation through the GCP services, identify its storage and runtime identities, explain BigQuery's role, distinguish scheduling from orchestration, and estimate which resources cost money even when no transformation is running.

Prerequisites: [Week 6 provisioning and orchestration](../Week6/2_Tue_Terraform_Airflow.md), [Week 6 Step Functions](../Week6/3_Wed_Step_Functions.md), [Week 7 Azure identity and storage](1_Mon_Azure.md), and [Week 7 processing and governance](2_Tue_Azure_Adv.md). Revisit a linked topic when its bridge is unfamiliar; you do not need to master every optional service before beginning.

The [earlier résumé topic inventory](gcp-resume-topic-reference.md) is preserved separately. It is a reference for later depth, not a shopping list for this capstone. The existing Azure project guides and homework retain their original scope; this guide adds an identifiable GCP adaptation using the same public data and logical model.

## 1. The mental model transfers

| Responsibility | Week 6 AWS connection | Week 7 Azure connection | GCP connection |
| --- | --- | --- | --- |
| Store raw files | S3 Bronze | ADLS Gen2 landing | Cloud Storage |
| Run bounded Python ingestion | Lambda | Azure Functions | Cloud Run job or function |
| Transform with Spark | Glue / EMR | Databricks PySpark | Managed Service for Apache Spark, formerly Dataproc |
| Store/query analytical tables | Redshift | Gold Delta tables queried with Spark SQL | Native BigQuery tables queried with GoogleSQL |
| Coordinate dependent work | Step Functions | Data Factory / Lakeflow Jobs | Workflows; managed Airflow for an Airflow approach |
| Start work on a schedule | EventBridge Scheduler | ADF schedule trigger | Cloud Scheduler |
| Author infrastructure | Terraform | Portal/CLI or Terraform | Console/CLI or Terraform |
| Authorize runtime access | Execution roles | Managed identities and RBAC | Service accounts and IAM |

These are responsibility mappings, not interchangeable service APIs. Databricks is a broad platform, while managed Spark supplies a Spark execution service. ADF includes integration and data movement; Workflows coordinates service calls. BigQuery native tables differ from Delta tables stored in your Azure lakehouse.

```text
Familiar AWS shape:  source → Lambda → S3 → Glue → Redshift
Familiar Azure shape: source → Function → ADLS → Databricks → Delta/SQL
GCP target shape:    source → Python job → Cloud Storage → Spark → BigQuery
```

Storage owns persisted bytes, compute runs transformations, the table system determines how queries see rows, and the orchestrator coordinates operations. A successful job does not by itself prove data correctness.

## 2. Account, project, billing, and location

A personal Google Account can be your sign-in identity. You do not need to buy Google Workspace, a company domain, or an enterprise organization to start this personal project.

```text
Your Google Account: human identity signing in
  └── GCP project: resources, enabled APIs, permissions, quotas
        ├── Cloud Storage bucket
        ├── BigQuery datasets and tables
        └── Workload definitions and executions

Cloud Billing account ── linked to project when billing is enabled
```

Organizations and folders provide additional hierarchy in company environments. For personal learning, **No organization** is a valid starting point. A project is neither an Entra tenant nor an exact Azure resource-group equivalent. A billing account pays for linked projects; it is separate from the project's resource hierarchy. See [resource hierarchy](https://docs.cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy).

A **project name** is a display label. A **project ID** is the stable identifier used in paths and API requests. A **project number** is a different system-assigned numeric identifier. Record all three when learning; do not interchange them.

An **API** exposes a service's operations. Enabling an API permits use in a project; it does not deploy every resource for that service or make every operation free. A region identifies a location for regional resources. A project is not globally “set to a region” that overrides all resource locations.

Proposed lab location: **`us-central1`**, with the Cloud Storage bucket and project-owned BigQuery datasets in that same single region. BigQuery's `US` multi-region is a different location. Colocation reduces avoidable transfer complexity; inspect public-dataset location separately before using one. See [BigQuery locations](https://docs.cloud.google.com/bigquery/docs/locations).

## 3. IAM and service accounts: connect this to execution roles

A **principal** is an identity, a **role** groups permissions, and an **IAM policy binding** grants a role to a principal at a scope. Your signed-in user creates/configures resources. A **service account** identifies a workload when it runs. Google-managed **service agents** perform service-specific tasks; they are not simply another name for your custom workload identity.

For example, your ingestion job's runtime service account can write raw objects while its deployer needs permission to configure the job and attach that identity. A Spark workload needs access to its inputs and output destination. Permission to launch a job is different from permission to read its data.

GCP service accounts connect conceptually to AWS execution roles and Azure managed identities, but impersonation, role assignment, and token acquisition differ. Prefer attached runtime identities and short-lived credentials over downloading long-lived JSON keys. Local CLI sign-in and Application Default Credentials used by Python libraries are also separate configurations; one successful console login does not establish every local SDK's credentials. See [service accounts](https://docs.cloud.google.com/iam/docs/service-account-overview) and [local development credentials](https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

**Think through:** The console shows a bucket, but a Spark batch gets access denied. Which runtime identity made the failed request, and which resource permission is missing?

## 4. Cloud Storage: connect this to S3 and ADLS

Cloud Storage stores **objects** inside **buckets**. A `gs://` URI identifies one object or prefix:

```text
gs://<your-unique-bucket>/bronze/bls/ingestion_date=YYYY-MM-DD/run_id=<run>/attempt_id=<attempt>/response.json
```

The bucket contains data; the URI supplies no authorization. With a flat namespace, slashes organize object-name prefixes. GCP also offers a separately enabled hierarchical namespace with real folders, so the blanket statement “GCP has no real directories” is inaccurate. Use a simple flat-namespace bucket for the first exercise; ADLS filesystem behavior should not be assumed for every GCP bucket. See [objects](https://docs.cloud.google.com/storage/docs/objects) and [hierarchical namespace](https://docs.cloud.google.com/storage/docs/hns-overview).

For this project, Bronze means immutable source captures and manifests. Keep BLS JSON, original USDA workbooks/archive members, source URL, retrieval time, reporting window, hash, run ID, and attempt ID. A retrieval date and a reporting month answer different questions. Changing the platform does not change the source contract.

A bucket holding Parquet files is not automatically a transactional table. A native BigQuery load creates managed warehouse storage separately from those files. An external-table design reads external storage instead; it has different behavior and is not selected for the first version.

## 5. Spark and BigQuery: processing versus warehouse

### 5.1 Spark skills that transfer

`select`, casts, joins, windows, grouping, partitioning, and Spark SQL remain useful. **Managed Service for Apache Spark**, historically called Dataproc, offers cluster and serverless execution modes. With serverless batches you submit the application and configuration while the service manages execution infrastructure. With clusters you manage a provisioned runtime lifecycle. Neither automatically provides every Databricks notebook, Unity Catalog, Auto Loader, or Lakeflow feature. See [managed Spark serverless](https://docs.cloud.google.com/managed-spark/docs/serverless-overview).

Local PySpark is a good first development environment for this small aggregate-statistics project. It tests transformations on your machine. A later managed batch teaches cloud storage access, runtime/service-account configuration, job submission, logs, and billing. Record that as a separate result; local success does not establish distributed GCP success. Match Spark/Python/dependency versions before moving the same logic to a managed runtime.

### 5.2 What BigQuery does

BigQuery is a managed analytical warehouse with native tables and GoogleSQL. You submit a **job** to load, query, copy, or export data. You do not need to provision a traditional warehouse cluster for the on-demand learning path.

```text
<project-id>.jobs_snap_gold.fact_state_month
      project       dataset          table
```

A **dataset** groups BigQuery tables/views and has a location and access configuration. It resembles a database namespace more than an ADF dataset: an ADF dataset describes an activity's input/output, while a BigQuery dataset contains warehouse objects. A Unity Catalog schema is a closer namespace analogy, but its governance model is different.

A normal view stores a query definition; a table stores results. Native BigQuery tables are not directories of Delta files under your bucket. **GoogleSQL** is BigQuery's SQL dialect. SQL joins/window reasoning transfers, while types, functions, scripting, constraints, loading, and cost controls need their own study. See [BigQuery overview](https://docs.cloud.google.com/bigquery/docs/introduction).

### 5.3 Assign transformation ownership once

For this capstone adaptation, use Spark to parse/normalize/validate source records and write source-grain Silver Parquet. Load that output into BigQuery staging tables. Use GoogleSQL to join the shared dimensions, build the two facts, validate candidates, and expose complete-only reporting views. Add dbt later if you want versioned SQL models/tests; it orchestrates warehouse transformations, not the original API capture.

The Azure version stores Gold as Delta. The GCP version proposed here stores Gold as native BigQuery tables. The logical model is shared; the physical storage choice is intentionally different. Parquet Silver is replayable derived file output, not a claim of Delta-style transactions or time travel.

## 6. Ingestion, orchestration, scheduling, and deployment

A **Cloud Run job** runs containerized work to completion, which fits bounded API/download ingestion. A function fits a small event/HTTP handler. Neither is a Spark cluster. Start the ingestion locally, then package the same bounded logic as a job if automated cloud execution becomes part of the capstone. See [Cloud Run](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run).

**Workflows** coordinates service calls, branching, waiting/polling, and error handling. This is the closest bridge to Week 6 Step Functions. **Managed Service for Apache Airflow**, also recognized as Cloud Composer, runs Python DAGs and connects to the Airflow lesson. It is not required merely because the project processes data. See [Workflows versus managed Airflow](https://docs.cloud.google.com/workflows/docs/choose-orchestration).

**Cloud Scheduler** starts work on a schedule; it does not itself validate source data or wait for every downstream computation. A job-submission response can arrive before the job finishes. The orchestrator must observe completion before loading its outputs. For the first milestone, start tasks manually in order; add exactly one scheduler only after reliable manual runs.

Terraform creates/configures resource definitions; it does not replace runtime orchestration. Reuse the Week 6 distinction between creating a job, starting an execution, and validating the resulting data. Learn the console once, then codify the chosen configuration rather than maintaining competing manual and Terraform definitions.

## 7. Services to recognize without adding them yet

| Service/topic | Connection to prior learning | Why it waits |
| --- | --- | --- |
| Pub/Sub | Messaging, redelivery, consumers; compare Kinesis/MSK/Event Hubs by pattern | Monthly BLS/USDA publication is not a live event stream |
| Dataflow | Managed Apache Beam batch/stream processing | Different processing framework; it does not run PySpark code unchanged |
| Managed Airflow / Composer | Python DAGs, dependencies, retries | Managed environment has costs beyond individual task execution |
| BigLake / Iceberg | Table/catalog interoperability, compare Delta/open table formats | Native BigQuery avoids an additional catalog/writer contract initially |
| dbt / Great Expectations | SQL modeling/tests and validation suites | Add when each solves a clear modeling or quality need |
| Secret Manager | AWS Secrets Manager / Azure Key Vault | Add with hosted ingestion if it needs a source API secret |
| Looker Studio / Looker | BI and semantic consumption | SQL results first; they are different products, and dashboard refreshes can run warehouse queries |
| Terraform / CI federation | Existing infrastructure-as-code ideas | Introduce after understanding a minimal, working resource set |

Cloud Logging and Cloud Monitoring support job/operational evidence. Start with run IDs, service error messages, row counts, freshness, and bytes processed. An extra paid observability platform is unnecessary for the first project.

## 8. Recommended technology choices for your capstone

The project is small enough to teach good engineering without large compute. A full 50-state × 132-month state fact has 6,600 expected business keys, not millions of people. Source workbooks, retained versions, staging copies, and retries still add storage; measure them rather than assuming cost from the fact row count.

| Responsibility | First working version | Later hosted version, if useful |
| --- | --- | --- |
| Ingestion | Bounded local Python, saving original source evidence | Cloud Run job |
| Bronze | Local captures during preparation; Cloud Storage once trial is started | Same Cloud Storage layout |
| Silver processing | Local PySpark; upload prepared Parquet | One serverless managed Spark batch, then repeated batches if justified |
| Warehouse | BigQuery native staging, candidate Gold, accepted Gold/reporting views | Same warehouse |
| Data quality | Explicit Python/Spark/SQL checks with recorded outcomes | Same gates, optionally wrapped with dbt or Great Expectations |
| Coordination | Learner-run ordered checkpoints | Workflows; optional Cloud Scheduler on day 1 |
| Presentation | Saved SQL and a small result/chart | Optional Looker Studio |

**Recommendation:** Target Cloud Storage + PySpark + BigQuery. Make the first cloud-Spark run a short, measured learning milestone. Workflows and hosted ingestion are the automation extension. Keep Composer, permanent clusters, Kubernetes, streaming, Iceberg, and multiple environments out of the initial deployment.

```text
Development path:
BLS/USDA → local Python → saved raw captures → local PySpark
                         ↓ upload                    ↓ upload
                 Cloud Storage Bronze       Cloud Storage Silver Parquet
                                                      ↓ batch load
                                             BigQuery source staging
                                                      ↓ GoogleSQL
                                      candidate dimensions and two facts
                                                      ↓ quality gate
                                          accepted tables/reporting views

Managed Spark milestone: replace local PySpark with a serverless batch.
Automation extension: Cloud Run ingestion + Workflows + one schedule.
```

Cloud Storage and native BigQuery contain different physical datasets here. The cost is justified by explicit ownership: retained source, curated replay files, and analytical warehouse tables. Do not repeatedly materialize every possible layer in both engines without a purpose.

## 9. Preserve the project's data contract

Use the [accepted logical model](us-jobs-snap-pipeline/data-model.md) and [verified sources/exceptions](us-jobs-snap-pipeline/source-verification.md). The GCP adaptation must preserve:

- Baseline January 2015–December 2025, then initial catch-up. Ongoing refresh covers only the six reporting months ending at each source's latest available month; no automatic older-gap expansion or annual reconciliation.
- `dim_state`, `dim_industry`, and monthly `dim_date`. The date dimension has exactly `date_key`, `year`, `quarter`, `month_number`, and `month_name`.
- `fact_state_month` at state/month grain and `fact_state_industry_month` at state/industry/month grain. Joining SNAP across industries does not turn it into industry-specific recipient data.
- Source values, units, seasonal-adjustment metadata, revision evidence, immutable captures, and stable business keys. Unchanged reruns must not duplicate facts or invent revisions.
- Valid partial measurements remain NULL/status-aware. Default reports require complete comparable input for their actual scope. Technical failures must not overwrite previous accepted values with “missing” placeholders.

The October 20 source inspection found an October 2025 unemployment marker for every state, unavailable standalone construction series for Delaware/Hawaii, and a negative Wyoming August 2022 SNAP dollar amount requiring review. These are recorded source findings, not new live checks. Preserve them. Manufacturing and retail are the simpler proposed first industry set; the learner's final selection remains pending. Participant/job reports can be developed separately from unresolved dollar-dependent interpretations.

A sensible first vertical slice is Idaho, January–December 2024, using total jobs, unemployment, SNAP counts, and one supported industry. This is a proposed development fixture, not a reduction of the final 50-state scope or a claim that all existing source decisions are settled.

## 10. Personally funded account and cost strategy

### 10.1 Three access modes

| Mode | What you can learn | Billing relationship and limitation |
| --- | --- | --- |
| BigQuery sandbox | Datasets, schemas, file loads, SELECT/join/aggregate practice | No billing account/card required; excludes DML such as MERGE, streaming, and transfer service; objects expire after 60 days |
| Eligible Free Trial, without paid upgrade | Cloud Storage, fuller BigQuery exercises, and allowed credit-funded service experiments | Current offer: $300 for 90 days; payment verification required; trial is not automatically upgraded to paid billing |
| Paid billing account with Free Tier | Continue selected services within their free allowances | Usage beyond allowances/credits can charge the payment method; this is not a guaranteed $0 account |

Sandbox currently has a **lifetime 10 GiB storage quota that deletion does not refund**, plus 1 TiB/month processed query data. Use it for a tiny orientation exercise rather than repeated bulk reloads. The trial ends when credits/time expire unless upgraded, with resources stopped and later at risk of deletion. See [sandbox limits](https://docs.cloud.google.com/bigquery/docs/sandbox) and [Free Trial terms and eligibility](https://docs.cloud.google.com/free/docs/free-cloud-features).

Until a personal spending limit is selected, the planning assumption is **$0 out of pocket**: learn locally/sandbox first, then use an eligible non-upgraded trial deliberately. Start its 90-day clock when you are ready for cloud exercises. A $300 trial balance is not a reason to deploy $300 worth of infrastructure. Prior trial/payment history can affect eligibility; check the actual offer displayed during signup.

### 10.2 What drives the bill

| Component | Cost driver | Lab choice |
| --- | --- | --- |
| Cloud Storage | Stored bytes, operations, transfer, retained versions/soft-deleted bytes | Standard storage in `us-central1`, small captures, inspect retention/soft-delete settings |
| BigQuery on-demand | Processed query bytes plus storage and applicable additional operations | Native small tables, query estimates, maximum bytes billed, no capacity reservation |
| Managed Spark | Allocated resources × duration, plus shuffle/storage/network | Short standard-tier batch after local testing; no persistent cluster |
| Managed Airflow | Environment resources while running | Theory/local Airflow initially; no managed environment |
| Hosted ingestion/build | Job compute plus image registry/build/log/storage costs | Add only after local ingestion works; keep resources bounded |
| Orchestration/scheduling/BI | Executions/steps and any triggered downstream usage | Manual first, then one schedule; avoid unattended dashboard refresh loops |

Cloud Storage's current eligible regional allowance includes 5 GB-month Standard storage, 5,000 Class A and 50,000 Class B operations per month across `us-west1`, `us-central1`, and `us-east1`. Storage, operations, and transfer are separate meters. Standard avoids the early-deletion minimum-duration charges associated with colder storage classes. See [Cloud Storage pricing](https://cloud.google.com/storage/pricing).

BigQuery's billed-project free usage includes the first 10 GiB of eligible storage and 1 TiB/month of on-demand query processing. This differs from sandbox's lifetime storage restriction. These allowances do not make every BigQuery feature free. See [BigQuery pricing and free usage](https://cloud.google.com/bigquery/pricing).

For a concrete managed-Spark illustration, the current `us-central1` standard rate is $0.06/DCU-hour with a default workload minimum of 12 DCUs. Ten minutes at that unchanged allocation gives `12 × (10/60) × $0.06 = $0.12` **compute only**. Actual runtime/scaling, shuffle, retained data, and transfer change the total; this is not a quoted all-in job price. See [managed Spark pricing](https://cloud.google.com/products/managed-service-for-apache-spark/pricing).

A small stored-and-queried dataset could remain within free allowances. That is a design target, not a guaranteed monthly invoice. Begin with measured bytes and usage, then forecast a month; do not infer a price from “serverless” or a successful query.

### 10.3 Controls to configure before paid-capable work

- Use a dedicated personal project so its usage is easy to inspect. Keep the billing account's trial/paid state visible and record the trial end date.
- Configure an **alerts-only budget** scoped to that project, with low actual/forecast thresholds and credits excluded if you want to see gross resource consumption. Alerts report spend; they are not automatic shutdown. [Budget guidance](https://docs.cloud.google.com/billing/docs/how-to/budgets)
- GCP also has **service-specific spend caps** for eligible services, including Cloud Run. They are not an all-project ceiling; the current eligible list does not cover BigQuery, Cloud Storage, or managed Spark. [Spend cap scope](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)
- For on-demand BigQuery, inspect estimated bytes before running, set **maximum bytes billed**, and use project/user query quotas for daily control. `LIMIT 10` does not generally limit bytes scanned from a table. These controls do not cap storage or other services. [BigQuery cost controls](https://docs.cloud.google.com/bigquery/docs/best-practices-costs)
- Keep managed Spark manual, with bounded resources/time and no retry/schedule loop until observed costs are understood. Save the output before checking cleanup; retained storage can still cost money after compute finishes.
- Before the trial ends, export the evidence/results you need and decide whether to stop or deliberately continue with paid billing. Keep local source/code backups. Do not assume a budget email preserves data or suspends every service immediately.

For the concrete account creation and control sequence, use [account checkpoint](us-jobs-snap-pipeline/gcp-learning-plan.md#1-account-and-billing-choice).

## 11. Failure model, quality, and recovery

| Symptom | Boundary to inspect | Evidence |
| --- | --- | --- |
| Resource creation denied | Active project, API enablement, deployer IAM, billing | Exact service error and selected identity/project |
| Spark cannot read Bronze | Runtime service account, object path, location/network | Failed object request and job logs |
| BigQuery load fails | File format/schema, job identity, data location | Load job ID and error details |
| Table loads but facts multiply | Source/business-key uniqueness and join grain | Duplicate keys, matches per key, before/after counts |
| Refresh makes reporting incomplete | Acceptance contract and source status | Candidate validation versus prior accepted output |
| Usage exceeds expectations | Bytes scanned, repeated runs, retained files, idle environments | Billing report, query/job IDs, storage inventory |

Retry transient operations at their owner boundary with bounded attempts. Replaying saved Bronze is different from re-fetching a source. A source-missing value is different from a timeout or parser failure. One scheduler and a manual run can still overlap; the hosted version needs a deliberate single-writer/locking strategy before writes, not merely a hopeful schedule interval.

Candidate outputs should pass checks before becoming the accepted reporting version. Separate successful table statements do not automatically publish every table atomically. Choose and test a BigQuery-appropriate transaction/release mechanism when reaching that checkpoint; do not assume Tuesday's Delta behavior transfers unchanged.

## Knowledge check and completion checklist

1. What transfers from Glue/Databricks PySpark, and what needs new platform-specific configuration?
2. Why is a BigQuery dataset different from an ADF dataset?
3. Which identity launches an ingestion job, and which identity reads/writes its objects?
4. Why can local Spark be a useful first stage without being evidence of a cloud Spark deployment?
5. Which costs remain after compute finishes?
6. Why is sandbox insufficient for the final incremental MERGE exercise?
7. How do a query byte limit, a budget alert, and a service-specific cap differ?
8. How will the project distinguish a valid NULL, an absent row, and a failed extraction?

- [ ] I can map each service to a responsibility and state one limit of the AWS/Azure analogy.
- [ ] I can explain the chosen storage/processing/warehouse boundaries.
- [ ] I know my billing mode, data location, and personal spending decision.
- [ ] I can describe the two fact grains and the monthly refresh/source-exception rules.
- [ ] I can name the next learner-executed checkpoint and its required evidence.

## Next action

Start [Checkpoint 1](us-jobs-snap-pipeline/gcp-learning-plan.md#1-account-and-billing-choice) with a personal sign-in and sandbox/trial decision. No account or payment details belong in this repository. The first implementation task is a small explained checkpoint, not deployment of the entire proposed stack.


# Lecture Notes

Cloud Data Flow - data processing services (like AWS Glue, Databricks/synapse notebook)
- main language/processing framework is Apache Beam
      - can be used on prem with Hadoop stack
      - connects to a data processor, while providing just the syntax
```python
pipeline
| "Read JSON" >> beam.io.ReadFromText(input_path)
| "Parse JSON" >> beam.Map(parse_json)
# continues to use this type of syntax to describe the work
```

BigQuery - marketted as much less expensive than Redshift 
- storage was charged the same for the cloud storage (buckets)
- charged more on the queries


Google Cloud Run Functions -> like AWS Lambda or Azure Functions

Google Cloud Composer -> basically managed Airflow -> like AWS MWAA (Managed Workflows for Apache Airflow)

Cloud SQL -> like AWS RDS and Azure SQL

Google App Engine -> like AWS EC2

Google Cloud Run -> Like AWS ECS


