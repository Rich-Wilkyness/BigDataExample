> Historical reference retained on 2026-10-23. This is the earlier résumé-oriented scope, preserved in full so its topic inventory and source notes remain available. Its original “core” labels are study categories, not the current personally funded capstone deployment plan. For the current learning order, architecture recommendation, and costs, use [GCP foundations and project scope](gcp-data-engineering-scope.md). Original research dates and unverified claims retain their original scope below.

# GCP data engineering: AWS/Azure bridge and résumé study scope

## Purpose and evidence boundary

Build practical GCP data-engineering knowledge using familiar AWS/Azure concepts and the existing SNAP, unemployment, and industry-employment project. The résumé supplies engineering topics to study; it does not determine the project's business domain. This is a study scope and learning sequence, not a completed course, deployment, résumé rewrite, or verified description of PayPal's internal systems.

**Status:** Planned learning material. Primary sources reviewed October 21, 2026. No GCP resources, credentials, Spark jobs, BigQuery tables, or Composer environments have been created or tested for this plan. BNPL data and a synthetic lending project are excluded from the learning implementation scope.

The supplied résumé describes a Lead Data Engineer role covering BNPL data products and a broad platform estate. Treat its bullets as topics to understand and investigate, not evidence that the learner personally performed each task. Keep four categories separate: actual employment responsibilities, publicly reported company context, independent lab work, and conceptual knowledge. A lab can strengthen a truthful technical explanation; it does not establish production ownership, leadership, scale, or employment history.

The current study direction is GCP. Existing [AWS/Azure jobs and SNAP project documentation](us-jobs-snap-pipeline/README.md) and source evidence remain useful references; this file does not silently migrate that project or change the instructor's Azure homework requirements. Preserve the learner's work and keep any GCP implementation/adaptation identifiable.

## Learning objectives

- Explain what each GCP service owns, where it resembles AWS/Azure, and where the analogy breaks.
- Build and explain one batch path through raw, curated, and semantic layers before adding optional streaming or open-table interoperability.
- Demonstrate business keys, idempotent loads, quality gates, market configuration, revision/replay behavior, and SQL analytical results with observed evidence.
- Diagnose one failed workflow and one inefficient query, and explain the evidence used to resolve them.
- Describe personal hands-on work accurately, including data size, limitations, and work still pending.

## Priority meanings

| Priority | What it means |
|---|---|
| Core: hands-on | Build a small working example and explain it; this is the first implementation scope |
| Core: understand | Necessary architectural knowledge; a managed deployment is not required immediately |
| Optional extension | Study after the core batch path works; add one at a time with its own evidence |
| Out of implementation scope | Recognize its purpose/context, but do not install or recreate it in the first project |

The résumé is an estate-wide tool list, not a requirement to use every tool in one pipeline.

## AWS and Azure concepts mapped to GCP

These are comparisons by responsibility, not exact service equivalences. Google currently uses the names **Managed Service for Apache Spark (formerly Dataproc)** and **Managed Service for Apache Airflow** in its documentation. This guide retains Dataproc and Cloud Composer as recognizable résumé terms and links current documentation below.

| Responsibility | AWS bridge | Azure bridge | GCP study target and important distinction |
|---|---|---|---|
| Resource organization | Organizations/accounts | Entra tenant, subscription, resource groups | Organization/folders/projects; projects organize resources and API enablement, with separate billing-account relationships. No exact resource-group substitution |
| Workload identity and access | IAM roles and policies | Managed identities and Azure RBAC | Service accounts, IAM roles/policies, service agents, and workload identity federation; distinguish deploying identity from runtime identity |
| Object storage and raw landing | S3 | Blob Storage / ADLS Gen2 | Cloud Storage buckets and objects; do not assume HDFS semantics or map ADLS hierarchical-namespace behavior directly |
| Small ingestion compute | Lambda | Azure Functions | Cloud Run functions or a Cloud Run job for bounded ingestion; choose based on trigger, packaging, and execution needs |
| Managed Spark | EMR / Glue Spark | Azure Databricks | Dataproc managed clusters or serverless Spark batches; preserves Spark skills but not every Databricks/Unity Catalog feature |
| Analytical warehouse | Redshift | Synapse warehouse / Databricks SQL experience | BigQuery datasets/tables and GoogleSQL; learn serverless execution, jobs, storage/compute separation, location, and pricing model |
| Data workflow orchestration | MWAA; Step Functions for a different workflow style | Data Factory / Airflow | Composer is managed Airflow with Python DAGs; Workflows is another service-orchestration option, not the same product |
| Scheduling | EventBridge Scheduler | Data Factory schedule trigger | Airflow scheduling for Composer DAGs; Cloud Scheduler for other scheduled targets. Avoid two schedulers independently starting the same write path |
| Messaging and event ingestion | SNS/SQS or Kinesis/MSK, depending on the pattern | Service Bus / Event Hubs | Pub/Sub topics/subscriptions, acknowledgment, redelivery, retention, and replay; it is not simply Kafka with renamed topics |
| Batch/stream processing beyond Spark | Managed Flink / Beam options | Stream Analytics / managed engines | Dataflow uses Apache Beam for batch/stream processing; it is not a managed PySpark runtime |
| SQL modeling and tests | dbt on Redshift | dbt on supported Azure targets | dbt with BigQuery; models are executed by the warehouse, and dbt does not replace API ingestion or Spark |
| Open-table lakehouse | Iceberg + catalog/query engines | Delta/Iceberg + catalog/engines | Iceberg with BigLake/lakehouse catalog and BigQuery/Spark integration; choose the supported table mode, catalog, and writer explicitly |
| Observability and secrets | CloudWatch / Secrets Manager | Azure Monitor / Key Vault | Cloud Logging, Cloud Monitoring, Secret Manager; Datadog is an optional external integration |
| BI and consumption | QuickSight / Streamlit | Power BI / SQL editor | BigQuery SQL and optional Looker; a lightweight dashboard product is not proof of Looker semantic-modeling experience |
| Delivery and infrastructure | Terraform, CI, IAM federation | Terraform, GitHub Actions, managed identity | Terraform and GitHub Actions with GCP workload identity federation; separate environment config from application logic |

References: [resource hierarchy](https://docs.cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy), [Cloud Run functions](https://docs.cloud.google.com/run/docs/functions/overview), [managed Spark](https://cloud.google.com/products/managed-service-for-apache-spark), [BigQuery](https://docs.cloud.google.com/bigquery/docs/introduction), [Composer/managed Airflow](https://docs.cloud.google.com/composer/docs/concepts/overview), [Workflows versus Composer](https://cloud.google.com/workflows/docs/choose-orchestration), [Dataflow](https://docs.cloud.google.com/dataflow/docs/overview), and [deployment federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines).

## Résumé responsibility breakdown

| Supplied responsibility | What we should be able to explain or demonstrate | Scope |
|---|---|---|
| Python, PySpark, BigQuery SQL, medallion layers | Preserve raw input; curate typed/deduplicated records in Spark; publish semantic SQL models with explicit ownership of each transformation | Core: hands-on |
| Applications, approvals, disbursements, repayments, delinquency | Recognize that these are résumé-domain concepts. Practice transferable grain/key/metric/reconciliation skills with state/month employment and SNAP records instead | BNPL domain implementation excluded |
| Pipeline kill-switch, circuit breaker, country flags, sensors | Distinguish operator disablement, automated quality blocking, and waiting for input; use source/state enablement as the project's analogous control | Core: hands-on, staged after a successful basic run |
| dbt tests and Great Expectations | Use warehouse relationship/uniqueness/business tests and source/curated validation suites; gate release on recorded results | Core: hands-on, introduce the tools sequentially |
| GraphQL and REST into PySpark on Dataproc | Pagination/cursors, auth, rate limits, typed parsing, schema drift, partial responses, retry ownership, raw capture, then Spark transformations | REST core; GraphQL optional hands-on adapter |
| Configuration-driven Composer enablement | DAG/task parameters, dependencies, scheduling, per-market config, run-frozen config version, and explicit skip/failure outcomes | Core: hands-on; learn Airflow locally before managed deployment |
| Terraform/GitHub Actions dev/staging/prod variants | Reusable definitions plus explicit environment variables, isolated destinations/identities, validation, review, and controlled rollout | Core: hands-on with one development environment; promotion exercise next |
| Query plans, INFORMATION_SCHEMA, Dataproc history | Inspect jobs, stages, scanned bytes, slot time, Spark stages/shuffles, source counts, and run-linked logs | Core: hands-on |
| Iceberg through BigLake, shared Spark/BigQuery access | Explain table files versus metadata/catalog, snapshot history, engine permissions, supported read/write operations, and commit ownership | Core: understand; optional bounded interoperability lab |
| Datadog and internal monitoring | Define freshness, latency, row counts, quality failures, retry/quarantine metrics, alert owner, and troubleshooting steps | GCP-native metrics/logs core; Datadog integration optional; internal tools out of scope |
| Differentiated retry, quarantine, partial load, full failure | Map specific failures to specific actions; preserve valid records without silently publishing incomplete business results | Core: hands-on |
| Kafka/Flink real-time path versus BigQuery batch | Event identity/time, late events, common metric definitions, reconciliation cutoffs, replay, and sink idempotency | Core: understand; streaming implementation optional |
| Partner feeds through Pub/Sub and Cloud Storage | Topic/subscription or file contract, acknowledgment boundary, source identifiers, immutable landing, validation, and BigQuery load | Small Pub/Sub exercise core after batch; multi-partner platform out of scope |
| Reviews, mentoring, architectural refactoring | Write a short design note, review a change, explain tradeoffs, and document a refactor's measured effect | Core learning artifacts; actual team leadership is separate evidence |
| Agile Scrum, Jira, cross-functional collaboration | Explain backlog, acceptance criteria, stakeholders, and delivery decisions using actual work | Lightweight learning backlog; recreating corporate process/tooling out of scope |
| Sprint planning, estimation, release planning | Break the lab into deliverable checkpoints and state risks/dependencies and release criteria | Core planning practice; no invented sprint history |
| Performance/maintainability, partitioning/clustering | Compare query plans and cost indicators before/after a justified change; partition/prune data and avoid unnecessary Spark shuffles | Core: hands-on; no production-scale claim from a small fixture |

## Typical GCP data-engineering use cases to cover

| Use case | Study depth | Reason |
|---|---|---|
| API/files to Cloud Storage to BigQuery | First working batch path | Common ingestion/warehouse pattern and close to the existing AWS/Azure experience |
| Spark transformation before the warehouse | Core | Direct match to the résumé and existing PySpark learning |
| Warehouse ELT and dimensional/semantic models | Core | BigQuery SQL/dbt consumption layer, incremental changes, tests, and governed reporting |
| Orchestration, quality gates, backfills and reruns | Core | Makes the pipeline operable rather than a sequence of successful notebooks |
| Event ingestion through Pub/Sub | One small exercise after batch | Teaches subscriptions, acknowledgments, duplicates, and event-to-table boundaries |
| CDC from an operational database | Conceptual overview; Datastream as an optional future topic | Typical DE requirement, but not necessary for the first API/file pipeline |
| Beam/Dataflow streaming | Service selection knowledge now; implementation later | Important GCP option without forcing a second processing framework into the Spark project |
| Open lakehouse interoperability | Optional Iceberg extension | Direct résumé relevance but additional catalog/engine behavior to verify |
| Security, lineage, regional location, cost, monitoring | Present throughout | A successful query alone does not establish a maintainable or controlled data product |

## Suggested learning sequence and required evidence

| Stage | Scope | Evidence before advancing |
|---|---|---|
| 1. GCP foundations | Projects, billing, IAM/service accounts, APIs, region/location, `gcloud`, `bq`, Cloud Storage | Explain identities and scopes; learner verifies access and a tiny storage/BigQuery operation |
| 2. One batch path | A BLS series or USDA SNAP file, immutable raw capture, one Spark batch, one BigQuery destination | Raw manifest, job result, schema/key checks, source/destination reconciliation, SQL query |
| 3. Curated and semantic ownership | Spark owns selected cleaning; dbt owns selected warehouse models; no duplicate ownership of the same transformation | Data model, incremental rerun without duplicate keys, dbt results and SQL output |
| 4. Orchestration and recovery | Airflow DAG, bounded retries, frozen config, one writer, replay of saved input | Success, failure, and replay logs; explain which layer retried and why |
| 5. Configuration and quality controls | Two selected states or sources, validation suites, enable/disable flags and publication gate | A controlled failure blocks affected output; unaffected valid output remains usable; previous accepted output preserved |
| 6. Delivery and diagnosis | Terraform plan, CI checks, environment parameters, query/Spark inspection, monitoring | Explain a reviewed plan, one diagnosed failure, one before/after performance observation, and remaining limitations |
| 7. Optional integrations | One of Pub/Sub streaming, GraphQL, Iceberg/BigLake, or BI | A separate contract/test and clearly stated scope; no automatic all-tools expansion |

Stages are learning checkpoints, not a fixed deadline promise. Use CLI commands or console steps with explanations of what and why, expected results, and actual verification. The learner executes cloud setup and pipeline steps. Do not auto-deploy Composer, a cluster, or multiple environments merely to match résumé keywords. Learn Airflow behavior locally first; deploying the managed service is a distinct cost/runtime checkpoint.

## Proposed practice architecture

```text
BLS REST API and USDA SNAP workbooks
             |
             v
Bounded Python ingestion -> Cloud Storage raw + manifest
                                     |
                                     v
                         PySpark on Dataproc
                                     |
                                     v
                     Curated data + validation results
                                     |
                                     v
                   BigQuery tables -> dbt semantic models
                                     |
                                     v
                     Release gate -> SQL results / BI

Composer/Airflow: orchestrates work, snapshots source/state config,
waits for inputs, records outcomes, and controls publication.
Logging/Monitoring: correlates ingestion, Spark, validation,
warehouse jobs, and accepted releases using run identifiers.
```

This is a proposed reference design. Native BigQuery tables are the first warehouse path; an Iceberg/BigLake variant is a separately verified extension, not an automatic additional copy. The curated storage/load boundary and Spark-versus-dbt responsibilities must be chosen explicitly when implementing each dataset.

Avoid unbounded external API calls from Spark executors: retries and parallel tasks can duplicate calls or overwhelm the source. First teach bounded capture into raw storage, then parallel processing of captured data. A later direct-source Spark adapter must have an explicit partitioning, rate-limit, and retry design.

## Applying the engineering topics to SNAP and employment

Keep the existing public data and its verified source exceptions. The GCP version can use the same 2015–2025 baseline, initial catch-up, strict six-month ongoing refresh window, monthly date dimension, and two-fact constellation. Final industry selection and the Wyoming negative benefit-cost interpretation remain separate pending decisions; do not reset those findings because the platform changes. See [source verification](us-jobs-snap-pipeline/source-verification.md).

| Résumé engineering topic | Exercise using our existing project |
|---|---|
| Medallion layers and SQL consumption | Raw BLS/USDA captures in Cloud Storage, Spark-curated state/month records, BigQuery facts/dimensions and reporting views |
| Configuration-driven enablement | Enable/disable a chosen state or source, with config version captured for each run; explain how the control resembles country enablement without calling U.S. states countries |
| Quality gates and partial loads | Preserve legitimate source-missing unemployment values, flag the negative SNAP dollar record, and publish only complete comparisons for each report |
| Incremental processing and revisions | Re-read the agreed six-month window, detect changed values, and upsert without duplicate current business keys |
| Data-quality tools | Great Expectations for chosen raw/curated contracts and dbt for BigQuery relationships, uniqueness, and semantic-model checks |
| Monitoring and diagnosis | Link API captures, Spark jobs, BigQuery jobs, validation outcomes, and accepted reporting periods through run identifiers |
| Performance | Inspect partition pruning and query/Spark plans on the available data; label small-data results honestly |
| Optional event exercise | Publish an explicitly labeled replay/notification about captured source data through Pub/Sub; do not claim the monthly publisher provides a real-time feed |

The analytical questions remain how state payroll employment changes compare with SNAP participation changes, and which selected industries gained/lost jobs. No loan, repayment, underwriting, customer-payment, or delinquency dataset is required. We can study the engineering mechanisms in the résumé without recreating its lending domain or claiming this lab is PayPal work.

## Quality gates and failure semantics to teach carefully

| Mechanism | Meaning | Example exercise |
|---|---|---|
| Enablement/kill-switch | Operator/configuration prevents selected work or publication | Market A disabled for this run; Market B remains enabled |
| Quality circuit breaker | Recorded threshold breach blocks downstream acceptance until defined recovery | Unexpected duplicate state/month business keys block the affected release |
| Sensor | Waits for a condition, subject to timeout and resource policy | Wait for an upstream file/ready marker; compare waiting with a failed quality check |
| Retry | Repeats an operation after a transient failure | One API request recovers after rate limiting, without creating duplicate current records |
| Quarantine | Retains problematic records and reasons outside the accepted dataset | An unparseable value or unmapped state isolated for review; a negative published amount is a review flag, not automatically a source error |
| Partial processing | Valid data can advance where the business contract allows | Retain valid source records but withhold incomplete metrics from default reports |
| Full failure | Required correctness/contract cannot be met | Broken source schema or failed required source-to-output reconciliation blocks the release |

An Airflow sensor is not automatically a circuit breaker or a mechanism that stops an already-running external Spark job. Explicitly define DAG dependencies/trigger rules, config-read timing, market scope, and the publication gate. Changing a flag after a job starts does not undo writes; cancellation and cleanup require separate controls. Teach stopping downstream propagation first, and describe active cancellation only if implemented and verified.

Test validation before release: dbt/Great Expectations reports alone do not guarantee that consumers are prevented from reading bad data. Stage candidate outputs, record checks, and select the accepted release only when required checks pass. Frozen config version and run IDs should explain exactly which market rules a run used.

## BigQuery and Iceberg distinctions

Core BigQuery study covers GoogleSQL, datasets/tables/views, explicit schemas, incremental loads/`MERGE`, partition filters, clustering, data location, job permissions, query cost controls, execution graph, and `INFORMATION_SCHEMA`. Compare those mechanisms with Redshift and Databricks SQL without assuming distkeys, indexes, constraints, or compute behavior transfer unchanged. Small data can demonstrate the mechanism, not enterprise performance.

For Iceberg, first distinguish native BigQuery tables, Iceberg external tables, and BigQuery-managed Iceberg tables. The current docs call the latter **Apache Iceberg managed tables**, formerly BigLake tables for Apache Iceberg in BigQuery. Engine read/write support, catalogs, credentials, snapshots, maintenance, and feature limits differ by table mode. Do not assume Spark and BigQuery can concurrently mutate every mode safely. Pick a supported writer/catalog contract and verify cross-engine reads and snapshot behavior in a bounded extension.

References: [partitioned tables](https://docs.cloud.google.com/bigquery/docs/partitioned-tables), [query execution graph](https://docs.cloud.google.com/bigquery/docs/query-plan-explanation), [INFORMATION_SCHEMA](https://docs.cloud.google.com/bigquery/docs/information-schema-intro), [Iceberg managed tables](https://docs.cloud.google.com/bigquery/docs/biglake-iceberg-tables-in-bigquery), and [BigLake table overview](https://docs.cloud.google.com/bigquery/docs/biglake-intro).

## Tool inventory: optional and excluded implementation work

| Tools/area | Treatment |
|---|---|
| Python, PySpark, Cloud Storage, Dataproc, BigQuery/GoogleSQL, Composer/Airflow, dbt, Great Expectations, Terraform, GitHub Actions | Core learning, introduced in sequence; managed deployments are separate learner-executed checkpoints |
| Pub/Sub | Core concepts and one small event-ingestion exercise after the working batch path; full partner/streaming platform optional |
| Apache Iceberg, BigLake | Core architectural understanding; optional interoperable-table implementation after native BigQuery works |
| Kafka and Flink | Compare with Pub/Sub/Dataflow and the existing streaming knowledge; reuse a small local fixture only if a later reconciliation lab needs it |
| Looker | Understand semantic consumption; optional BI implementation if access exists. Do not equate a different dashboard tool with Looker experience |
| Datadog | Define the signals using GCP logs/metrics first; optional integration rather than a new mandatory paid platform |
| Gimel | Recognize PayPal's public Spark-based data-abstraction framework. Do not install/reconstruct it or assume its current internal usage/compatibility; the supplied tool list is not proof of that deployment |
| Apache Hive and HDFS | Explain legacy Hadoop storage/metastore/migration context and how Cloud Storage/catalogs differ; no new Hadoop cluster |
| Bigtable | Selected for the hypothetical BNPL playbook’s derived exposure and customer-profile serving; architecture study only. No Bigtable deployment or public-data project dependency without a real consumer requirement |
| Elasticsearch | Recognize possible search roles; no instance or connector without an actual source/consumer requirement |
| Jira and Agile Scrum | Track a small backlog/design decisions; no Jira deployment, fabricated tickets, or invented team-delivery history |
| Large-scale migration and company internals | Explain inventory, lineage, compatibility, validation, cutover, rollback, and reconciliation conceptually; no 400 PB replication or claim of participation from lab work |
| Extra GCP services | IAM, secrets, monitoring, billing controls, and basic networking support core work. No Kubernetes, elaborate networking, ML, or additional databases merely to enlarge the tool list |

## Public company context requiring careful wording

A February 26, 2026 Google Cloud article authored by PayPal leaders describes roughly **400 PB across a dozen siloed systems**, including Teradata, Hadoop, Redshift, and Snowflake, and reports **more than 300 PB migrated**, with some workloads decommissioned. That is not the same claim as moving all 400 PB exclusively from Hadoop. The article establishes public company context, not the supplied BNPL team's implementation or the learner's individual role. See [PayPal migration account](https://cloud.google.com/blog/products/databases/paypals-historic-data-migration-is-the-foundation-for-its-gen-ai-innovation).

Likewise, the [public Gimel project](https://paypal.github.io/gimel/) establishes that the framework exists and is Spark-based; it does not verify which contemporary PayPal team uses it. Keep unverified internal details as questions to resolve from actual work context rather than fill them in with plausible architecture.

## Narrative and evidence record

For each eventual lab, record the business question, actual dataset and scale, owned work, architecture choices, business keys, quality/failure cases, commands/configuration, observed results, and limitations. For performance claims, keep the measured query/job evidence and comparable workload; do not invent percentages or scale.

Use first-person production/leadership claims only for responsibilities actually performed. Describe independent work as an independent project or lab; describe researched mechanisms as knowledge. Review any supplied résumé wording that does not match actual responsibilities. A defensible narrative comes from understanding and evidence, including what the learner did not own.

## Completion checks and next decisions

- Can the learner trace one record from capture through Spark, BigQuery modeling, validation, release, and SQL consumption?
- Can the learner explain the AWS/Azure/GCP similarities and one important difference for storage, Spark, orchestration, identity, and warehouse queries?
- Are retries, quarantine, NULLs, missing records, market disablement, and publication failure demonstrated as distinct cases?
- Are batch/stream equivalence and Iceberg interoperability still clearly labeled conceptual if no corresponding test ran?
- Does each résumé topic have a status: studied, locally demonstrated, GCP demonstrated, actual job responsibility, or not yet covered?

The next planning choices are which GCP access/billing environment is available and how much managed-service deployment fits the training period. The project data remains SNAP/unemployment/employment, with no BNPL extension planned. Start the GCP walkthrough with one existing public-source checkpoint; this document authorizes no infrastructure deployment. Any future résumé clarification should distinguish actual job responsibilities from these independent exercises.

## Primary study references

- [dbt BigQuery quickstart](https://docs.getdbt.com/guides/bigquery) and [incremental models](https://docs.getdbt.com/docs/build/incremental-models): warehouse modeling, tests, lineage, and incremental behavior.
- [Great Expectations checkpoints/actions](https://docs.greatexpectations.io/docs/core/trigger_actions_based_on_results/create_a_checkpoint_with_actions/): recorded validation and response actions; pin a compatible version before code examples.
- [Airflow deferrable operators](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html): waiting/resource behavior; verify support for the chosen managed version.
- [Pub/Sub subscription behavior](https://docs.cloud.google.com/pubsub/docs/subscription-overview) and [exactly-once scope](https://docs.cloud.google.com/pubsub/docs/exactly-once-delivery): delivery guarantees do not automatically make a downstream database write exactly once.
- [Looker product comparison](https://docs.cloud.google.com/looker/docs/studio-comparison): distinguish semantic modeling and dashboard products when selecting the optional presentation layer.

All examples and proposed evidence above remain unexecuted unless a later checkpoint explicitly records otherwise.
