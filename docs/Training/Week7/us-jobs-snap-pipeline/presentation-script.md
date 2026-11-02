# U.S. Jobs and SNAP: speaking script and demonstration cues

## Working format

Use this file alongside the [presentation requirements](presentation.md). “Slide content” can move into Google Slides; “What to say” can become speaker notes; “What to show/do” records the presenter’s actions. Start with the high-level purpose and then add detail.

The [slide-by-slide outline](presentation-slide-outline.md) maps this material to 14 suggested main slides, visuals, speaking points, demo actions, and optional appendix content. It is an editable starting point; its approximately 20-minute allocation has not been rehearsed.

Richard approved the introduction on October 31, 2026, and the source explanation on November 1, 2026. Unapproved sections remain labeled as drafts or preparation prompts to work through together. The suggested time budget is approximately 18 minutes within the required 10–30-minute range. No rehearsal or fresh cloud verification is claimed here.

## 1. Introduction and data sources

**Suggested time:** 2 minutes. **Status:** Introduction, source explanation, and historical coverage/refresh wording approved. High-level architecture is next.

### Slide content

- U.S. Jobs and SNAP Participation Pipeline
- Comparing employment and food-assistance trends across states
- BLS and USDA public data → GCP pipeline → interactive dashboard

### What to say — approved introduction

“My project brings together U.S. employment data from the Bureau of Labor Statistics and SNAP participation data from USDA. I wanted to make it easier to compare how jobs and food-assistance participation changed across states over time. The pipeline preserves the original data, transforms it into consistent monthly datasets, and publishes results to an interactive dashboard.”

### What to say — approved source explanation

“These are monthly statistics, rather than individual worker or SNAP-recipient records. BLS provides employment and unemployment measures, while USDA publishes SNAP participation, households, and benefits in fiscal-year workbooks. I align the records to calendar months so they can be compared by state.”

### What to say — approved historical coverage and refresh explanation

“I started with historical data from January 2015 through December 2025, then added a catch-up and monthly refresh process. Each source publishes on its own schedule, so I compare jobs and SNAP using months available in both datasets.”

### What to show/do

Show the title and a brief source summary before opening cloud services or code. Explain that jobs and participants are different measures and the charts do not establish causation. Introduce the 50-state core scope; explain construction’s 48-state availability when moving into industry comparisons. Confirm current source dates before quoting them.

## 2. High-level architecture

**Suggested time:** 2 minutes. **Status:** Service-specific speaking overview approved November 1, 2026; actual GCP diagram still to review.

### Slide content

- Cloud Scheduler → Workflows: trigger and coordination
- Cloud Run Jobs → Cloud Storage Bronze: ingestion and raw captures
- Serverless Dataproc/PySpark → Cloud Storage Silver: transformation
- Staging/publishing jobs → BigQuery Gold: publication and reporting
- BigQuery reporting views → Data Studio dashboard

### What to say — approved high-level overview

“Cloud Scheduler triggers Google Cloud Workflows each month. Workflows starts our Cloud Run Jobs, which run containerized Python scripts to retrieve data from BLS and USDA and save the original files in the Bronze layer in Cloud Storage.

Next, Workflows submits a serverless Dataproc batch running PySpark to clean, standardize, and validate the data, producing Silver datasets in Cloud Storage.

Additional Cloud Run Jobs stage and merge the accepted data into our Gold tables in BigQuery, including revision history. BigQuery reporting views then connect to Data Studio for the interactive dashboard.”

### What to show/do

Show one simple diagram and follow the arrows once. Use the [slide-ready PNG](presentation-assets/gcp-pipeline-architecture.png) or [editable SVG](presentation-assets/gcp-pipeline-architecture.svg), created November 1, 2026 and pending Richard's review. Dashed arrows show execution control; solid arrows show data movement or query results. Workflows coordinates ingestion, Spark, and publication; it does not carry the bulk data. The diagram groups staging and publication Cloud Run Jobs in one box and omits build tooling and credential dependencies for clarity. Use the actual GCP deployment, not the older Azure proposal diagram. The console may show Managed Apache Spark; the project submits serverless Dataproc batches. This Silver processing is not Dataflow. The Workflows execution graph remains the runtime demonstration visual.

## 3. Component details and technical decisions

**Suggested time:** 4 minutes. **Status:** Outline; develop the spoken explanation together.

### 3.1 Scheduling and orchestration — approved

**Slide content:** Cloud Scheduler supplies the monthly trigger; Workflows coordinates service calls and waits for job completion. Cloud Composer/Airflow was the orchestration alternative.

**What to say — approved November 1, 2026:** “Because we chose Workflows for orchestration, we use Cloud Scheduler to trigger the monthly run. If we had chosen Cloud Composer with Airflow, we would use Airflow’s built-in scheduling instead.

Cloud Scheduler handles when the pipeline starts: the first day of each month at 08:00 UTC. Workflows handles what happens next. It starts the ingestion jobs, waits for them to finish successfully, and then coordinates Spark processing and publication to BigQuery.

I chose Workflows because this is a monthly pipeline that mainly starts Cloud Run Jobs and a Dataproc batch, waits for completion, and checks their results. Workflows charges for executed steps without requiring a dedicated orchestration environment between runs. Cloud Composer keeps an Airflow environment running, with baseline costs even when no pipeline tasks are executing. For this project, I didn’t need that ongoing environment or Airflow’s broader scheduling and operator ecosystem. Composer would be worth reconsidering if I were coordinating many related data pipelines.”

**What to show/do:** Highlight Scheduler and Workflows in the diagram. Show the saved schedule and a completed execution’s ordered steps when reaching the demonstration section; avoid starting a new run merely to explain orchestration. Point out that Workflows coordinates the transformation but does not execute PySpark itself. Treat the saved schedule as something to verify before the live presentation, not evidence that every scheduled run has succeeded.

**Technical reference:** [Google’s Workflows versus managed Airflow comparison](https://docs.cloud.google.com/workflows/docs/choose-orchestration), reviewed November 1, 2026. Current documentation may call Cloud Composer Managed Airflow. Both products can orchestrate this batch pipeline; the choice is based on project fit, not an inability of Airflow to run it. No quantified cost saving is claimed.

**Cost wording:** “Serverless” here means no dedicated orchestration environment to provision or pay for between executions, not that a personal server literally shuts down. Workflows bills executed steps, including applicable retry/polling steps; Cloud Run, Dataproc, Scheduler, storage, and BigQuery have separate billing. Composer workers can scale, but a running environment retains baseline resources/costs. Compare the [Workflows pricing model](https://cloud.google.com/workflows/pricing) and [managed Airflow pricing model](https://cloud.google.com/composer/pricing), reviewed November 1, 2026. This is a design rationale, not a measured project cost comparison.

### Orchestration decision: supporting detail and Q&A

These notes support the presentation and questions; do not read the entire comparison aloud. They explain the rationale without treating run frequency, tool count, or input size as a universal migration threshold.

| Decision factor | Why Workflows fits this project | When Composer/Airflow could earn its overhead |
| --- | --- | --- |
| Setup and operations | Deploy a YAML workflow with a runtime identity and service permissions; no Airflow environment, DAG parsing, or Python provider dependency environment to maintain. Downstream IAM and networking still require setup. | A team benefits from a shared Airflow environment, Python DAGs, operator/provider packages, task/run visibility, resource pools, and a common operational interface. |
| Frequency and cost | One monthly execution leaves little reason for a dedicated orchestration environment. Workflows can also run daily, hourly, or on demand. | Many active workflows may share the environment’s baseline cost. Frequency alone does not establish a cost crossover; evaluate actual executions/steps and environment sizing. |
| Data volume | Pass object paths, run IDs, and job/status metadata. Cloud Run, Spark, and BigQuery process the records; the orchestrator does not carry the bulk data. | Large data does not inherently require Airflow. It can indirectly create many partition-specific tasks, dependencies, retries, and historical reruns that benefit from Airflow’s run model. |
| Integrations | The existing jobs have Google Cloud APIs and return operations/results that the workflow can inspect. | Supported operators and hooks for a mixture of databases, file transfers, dbt, cloud services, and external systems may avoid custom service wrappers. Check exact provider/version support and authentication. |
| Recovery and historical dates | The project uses explicit run IDs, saved captures, a fixed refresh policy, and a defined sequence of jobs. | Repeatedly reprocessing many logical dates and inspecting/clearing individual failed tasks may be more natural with Airflow’s DAG/task history and backfill tooling. Tasks still need date-aware, idempotent code. |
| Team and complexity | One project with a manageable service sequence. Workflows supports branches, parallel work, retries, and waits too; it is not limited to trivial flows. | A shared data platform has interdependent pipelines, differing calendars, resource contention, operational ownership, and existing Airflow expertise/conventions. |

**Why setup can be more involved:** Composer manages infrastructure, but the user still chooses/configures an environment, service identity, networking, capacity/scaling settings, and an Airflow/runtime version; develops/deploys Python DAGs; and manages any added packages and connections. Scheduler/worker/metadata services and DAG parsing add concepts that our YAML service sequence does not need. This is a comparison of responsibilities, not a claim that Composer is always difficult or Workflows requires no configuration. See [environment creation](https://docs.cloud.google.com/composer/docs/composer-3/create-environments).

**Illustrative Composer example:** A retailer ingests daily sales from multiple regional databases, waits for partner files delivered at different times, runs Spark transformations and dbt models, and publishes inventory and finance reports only after their separate dependencies pass. A source correction may require rerunning selected daily partitions for the previous three months while today’s runs continue under concurrency limits. A shared Airflow environment can express the Python task dependencies and schedules, use the required supported providers, and give operators one place to inspect and rerun affected tasks/dates. This could be a daily system; it does not need to run hourly to justify Airflow. Workflows could implement a similar system, but more scheduling/reprocessing coordination might need to be designed explicitly. This is an example, not an implemented project extension.

**Volume example:** One Dataproc job processing 1 TB can still be one Workflows task. A much smaller dataset split across many independently arriving files and business-date dependencies may create a more complex orchestration problem. Data size influences processing capacity directly and orchestrator choice indirectly through task/dependency/recovery structure.

**Practical reconsideration point:** Revisit Composer when its ready-made integration and task/date operations would replace enough custom coordination to justify the environment’s cost and maintenance. There is no documented universal cutoff of pipelines, gigabytes, or hourly runs. Preserve Workflows for this project unless those requirements actually emerge.

**References:** [Google’s comparison](https://docs.cloud.google.com/workflows/docs/choose-orchestration) and [Airflow backfill concepts](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html), reviewed November 1, 2026. Airflow feature/UI availability depends on the version supported by the selected Composer environment. No Composer environment was created or benchmarked.

### Scheduling alternatives — supporting Q&A

Cloud Scheduler is the timer; Workflows coordinates the jobs. Other scheduling choices exist, but some replace both roles or cover only a narrower task.

| Alternative | When it could fit | Tradeoff for this project |
| --- | --- | --- |
| Composer/Airflow DAG schedule | Airflow already owns related data pipelines and their logical-date scheduling | Can replace the separate Scheduler trigger as well as orchestration, but adds an Airflow environment we otherwise do not need. |
| Scheduled GitHub Actions | A repository-owned automation workflow already authenticates to GCP and invokes its API/CLI | Adds GitHub runner/authentication and repository scheduling dependencies; scheduled starts may be delayed. |
| Kubernetes CronJob | A team already operates GKE/Kubernetes and needs recurring container jobs | The cluster and its operations are unnecessary additions just to start this monthly pipeline. A CronJob could invoke Workflows but is not automatically a replacement for the multi-stage coordination. |
| BigQuery scheduled query | Recurring SQL transformations/reports within BigQuery | Useful for a SQL-only stage, not a full substitute for source ingestion and Spark orchestration. |

An event-driven trigger is a different policy: Workflows can start when a file/message arrives instead of on a calendar schedule. That is useful when arrival controls processing, but it does not by itself detect that a public publisher has released new data. Cloud Run Jobs’ console scheduling integration uses Cloud Scheduler; it is not an independent timer.

**Approved short scheduler rationale:** “Because we chose Workflows for orchestration, we use Cloud Scheduler to trigger the monthly run. If we had chosen Cloud Composer with Airflow, we would use Airflow’s built-in scheduling instead.”

References reviewed November 1, 2026: [Airflow schedules](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/cron.html), [GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), [Kubernetes CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/), [BigQuery scheduled queries](https://docs.cloud.google.com/bigquery/docs/scheduling-queries), and [Cloud Run job scheduling](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule). Alternatives are explanatory, not implemented project components.

### 3.2 Ingestion with Cloud Run Jobs — approved

**Slide content:** Separate BLS and USDA ingestion jobs; Python packaged in Docker; images built by Cloud Build and stored in Artifact Registry; original captures saved in Cloud Storage Bronze.

**What to say — approved November 1, 2026:** “For ingestion, I use separate Cloud Run Jobs for BLS and USDA. Cloud Build builds their container images, and Artifact Registry stores the versions that Cloud Run executes.

The BLS job calls the API for the configured series and reporting years, while the USDA job downloads the SNAP archive. Both save the original responses or files in Cloud Storage Bronze, along with manifests that record retrieval information and checksums.

I chose Cloud Run Jobs because this is a batch task with a clear finish: retrieve the data, save the capture, and exit. Workflows starts each job and waits for its execution result before continuing. A Cloud Run function could also perform this ingestion through an HTTP or event handler, with less explicit image-packaging work. Jobs fit the execution model we wanted; we did not rule out functions because of a measured performance limitation.

If we had chosen Cloud Composer, we could implement this lightweight ingestion as Airflow tasks instead. Airflow can also launch Cloud Run Jobs when separate compute or dependency isolation is useful.”

**What to show/do:** Highlight the two ingestion jobs, image repository, and Bronze destination. Show one small source manifest excerpt later during the demonstration. Explain that an image is the packaged application and a job execution is an instance of it running. Use the supporting Q&A for the approved comparison with functions and Composer tasks. Do not show the BLS key or treat a checksum as validation of economic meaning.

### Supporting Q&A: Cloud Run Jobs, functions, or Composer tasks?

The presentation decision is the cloud execution tool. Cloud Run Jobs runs a program to completion and reports an execution result that Workflows can wait for. Cloud Run functions invoke a handler through HTTP or an event; Workflows can invoke functions too. Both are viable for our bounded ingestion, and both support an automated schedule through orchestration. Being monthly or having a clear finish does not make functions unsuitable.

With our chosen Workflows architecture, Jobs provides the batch execution interface we use. If we had selected Composer, an Airflow task could execute the lightweight ingestion directly on its workers. This could avoid a separate ingestion deployment, but its dependencies and resource use would then belong to the Airflow environment. Airflow can alternatively launch a Cloud Run Job, so choosing Composer does not require removing Jobs.

Supporting references: [executing Cloud Run Jobs from Workflows](https://docs.cloud.google.com/workflows/docs/tutorials/execute-cloud-run-jobs), [function triggers](https://docs.cloud.google.com/run/docs/function-triggers), and [Workflows versus managed Airflow](https://docs.cloud.google.com/workflows/docs/choose-orchestration).

### Background reference only: container packaging

Keep this explanation available for questions; it is not part of the main spoken cloud-tool comparison.

We did not replace Python with Docker. The script contains the ingestion logic; the container image packages that script and its environment; Cloud Run Jobs supplies the compute; Workflows coordinates the execution. Uploading a `.py` file to Cloud Storage alone would not execute it.

Our ingestion Dockerfiles select `python:3.12-slim`, install the application dependencies, and start either `bls_ingest.py` or `snap_ingest.py`. The ingestion requirements include the Cloud Storage Python client. This is not a case where ingestion required Spark or Java inside its container: Spark transformation runs separately in Dataproc.

The useful benefits are an explicit runtime definition, a deployable image version, and separation from local setup. An image digest identifies the built artifact we deploy. Rebuilding later from a moving base-image tag and dependency ranges can produce different bytes, so containerization alone does not guarantee identical future builds. We build a new version when code or dependencies change; the monthly schedule runs an existing deployed version.

### Supporting Q&A: what other ingestion options could we use?

| Option | What we would supply | When it would make sense and its tradeoff |
|---|---|---|
| Source-deployed Cloud Run function | Python handler, dependencies, and runtime configuration | A close alternative for this bounded ingestion. Google builds and stores the container image automatically, reducing Dockerfile maintenance. We would adapt the script to the handler interface. |
| Python on a Compute Engine VM | Script, Python environment, and a managed VM | Useful when an existing VM or persistent host is required. We would also own OS maintenance and instance lifecycle; a virtual environment isolates Python packages but does not package the OS environment. |
| An Airflow task in Cloud Composer | DAG/task code, dependencies, and service permissions | Reasonable if Composer already orchestrated the wider platform. It could run lightweight Python ingestion or launch a separate job. Creating a Composer environment solely to run these scripts would add platform overhead. |
| A Kubernetes Job on GKE | Container image and Kubernetes job configuration | Reasonable on an existing Kubernetes platform with relevant operational needs. Adding a cluster just for these monthly captures would introduce more infrastructure to manage. |
| Storage Transfer Service (assuming this is what STS means) | A supported file/object source, destination, and transfer configuration | Useful for managed bulk transfer, retries, and copying from other storage systems or suitable public URLs. It would still need separate logic for BLS API requests, USDA page discovery, parsing, and our source acceptance rules. |
| Kafka | Producers, topics, consumers, retention, and service operations | Useful for durable event buffering, replay, and multiple independently consuming applications. Our monthly publications do not require an event bus; adding one introduces another service and delivery/offset management without improving source publication freshness. |

**Ingestion alternative examples:** Storage Transfer Service would be worth considering if a partner supplied a large collection of files in another cloud's bucket. Kafka would be worth considering if the source became a continuous stream of transactions or change events consumed by several systems. Neither scenario is an implemented project input. If STS means Security Token Service instead, that is an authentication topic rather than a file-transfer alternative.

References for these additional options: [Storage Transfer Service](https://docs.cloud.google.com/storage-transfer/docs/overview) and [Kafka introduction](https://kafka.apache.org/intro/), reviewed November 1, 2026.

Choosing Cloud Run Jobs and choosing an explicitly authored Docker image are related but separate decisions. Source-deployed functions also run in containers underneath. We chose the script-oriented job interface and explicit image packaging; we have not demonstrated that functions would be too slow, too small, or more expensive. Containers also require dependency and base-image maintenance, and do not solve API failures or data correctness automatically.

References reviewed November 1, 2026: [Cloud Run Jobs execution model](https://docs.cloud.google.com/run/docs/create-jobs), [automatic image building for source-deployed functions](https://docs.cloud.google.com/run/docs/deploy-functions), and [function handler interfaces](https://docs.cloud.google.com/run/docs/write-functions). These alternatives are explanatory, not additional implemented services.

### Ingestion detail: historical loading and monthly refresh — approved

**What to say — approved November 1, 2026:** “The initial load built the January 2015 through December 2025 history, followed by a catch-up to each source's latest available month. The recurring pipeline refreshes the latest six reporting months for each source. That lets us pick up new publications and recent revisions without reprocessing the entire history.

The reporting window follows source availability, not the date the pipeline runs. BLS and USDA can publish through different months. Their download formats also differ: BLS returns API responses, while USDA supplies an archive of fiscal-year workbooks. We preserve the downloaded inputs, then select the intended reporting months during processing.”

**Additional wording — approved November 1, 2026:** “Six months is our chosen refresh policy, not a source requirement. We revisit those months because previously published figures can change. For example, if July is the latest SNAP month, we refresh February through July. When August becomes available, the window moves to March through August. We retain the earlier history, but corrections outside the window require a separate deliberate backfill.”

**Source-interface clarification:** Our SNAP ingestion uses USDA's published file downloads, not a monthly records API. The landing page provides the historical ZIP archive and separate latest-month Excel/PDF tables. The archive is useful here because we need historical data and several recent months, including revisions. The job automatically discovers its download link, preserves the archive, and identifies the required fiscal-year workbooks; Silver parses the state/month measurements. Do not claim USDA has no APIs anywhere or only publishes archives. [USDA SNAP Data Tables](https://fns-prod.azureedge.us/pd/supplemental-nutrition-assistance-program-snap), checked November 1, 2026.

**Supporting detail:** BLS monthly capture batches the configured series and requests the previous and current calendar years, then identifies the latest six monthly observations per series. SNAP capture reads the latest-month metadata from the preserved USDA landing page, downloads its archive, and identifies the fiscal-year workbooks needed for the six-month window. The six-month processing policy does not mean only six months of raw bytes are downloaded. Older gaps and revisions are not automatically backfilled; they remain a documented limitation. Retries preserve attempt artifacts, while current-fact and history deduplication belongs to the later Gold publication explanation. Historical loading was an earlier setup milestone; do not imply that the monthly workflow reruns that baseline.

**What to show/do:** Use a simple timeline: historical baseline → initial catch-up → rolling six-month refresh. Illustrate source-specific windows if useful: when jobs are available through September and SNAP through July, their windows end in September and July respectively. Label these as an example, not freshly verified current cutoffs.

### 3.3 Bronze landing in Cloud Storage — approved

**Slide content:** Original source captures; separate captures for each run and attempt; retrieval metadata, checksums, and lineage.

**What to say — approved November 1, 2026:** “The ingestion jobs save the original source responses and files in Cloud Storage, forming our Bronze layer. Each capture is kept separately, so a new run does not overwrite earlier inputs.

We also save manifests that record what was retrieved, when it was captured, and its checksum. This lets us trace published results back to their inputs and investigate whether a discrepancy came from the source or our processing.”

**What to show/do:** Highlight Bronze on the architecture diagram. During the demonstration, show one capture and its matching manifest, with no credentials visible. Explain that a checksum concerns captured-byte integrity, not whether the source statistic is economically correct. No landing-storage alternatives comparison is needed in the main presentation.

**Supporting Q&A — would Composer change the landing location?** We could retain the same dedicated Cloud Storage Bronze bucket if Airflow tasks performed or orchestrated ingestion. The orchestrator choice does not require changing the raw-data storage choice. Composer's own environment bucket holds DAGs, plugins, dependencies, and logs; keep the project's Bronze captures separate from those environment files. [Composer environment storage](https://docs.cloud.google.com/composer/docs/composer-3/cloud-storage). This is an architecture alternative, not an implemented Composer deployment.

### 3.4 Silver transformation with serverless Dataproc and PySpark — approved

**Slide content:** Workflows submits a managed Spark batch; parse and standardize source records; validate keys, coverage, and measurement ranges; retain missing-value statuses and review flags; write separate BLS and SNAP Parquet datasets to Cloud Storage Silver.

**What to say — approved November 1, 2026:** “Once the captures are saved, Workflows submits a serverless Dataproc batch running PySpark. This turns the source-specific files into consistent, validated datasets in our Silver layer.

For example, BLS publishes payroll employment in thousands, so we convert those values into jobs. Unemployment rates remain percentages. For SNAP, we extract the state records from the fiscal-year workbooks and organize them by calendar month, so both sources use the same monthly keys.

We also check for duplicate records, expected source coverage, and invalid values. Missing source measurements stay NULL, with an explicit status. An average excludes that missing measurement; replacing it with zero would count zero as a real value and distort the result. We still check coverage because the average then represents only the available measurements. When a published SNAP benefit value is negative, we preserve it and flag it for review. The accepted datasets are written as Parquet files in Cloud Storage for the BigQuery publication stage.”

**Technology rationale — approved November 1, 2026:** “I chose serverless Dataproc to run our existing Spark transformations as a managed batch, without maintaining a persistent cluster between monthly runs. It produces typed Parquet datasets that we can validate before publishing to BigQuery. A Cloud Run processing job would also be a reasonable option at this data volume; our choice does not mean the dataset requires distributed computing.”

### Supporting Q&A: what other Silver processing options could we use?

| Option | Fit for this project | When it becomes more attractive |
|---|---|---|
| Cloud Run Job with ordinary Python processing | The closest simplification. The current source parsers already run in the driver, and the remaining unit conversions, validation, and Parquet writing could be implemented without Spark. It would require replacing the Spark-specific operations and measuring runtime/resource use. | Bounded transformations fit within one task's available memory, CPU, and execution limits; avoiding a distributed processing runtime is valuable. |
| BigQuery SQL after a parsing step | A small job would first unpack and normalize the Excel/API inputs into supported records, then load staging tables. SQL could perform conversions, key checks, joins, and modeling. BigQuery batch loading does not directly parse Excel workbooks. Silver could be tables instead of files if we deliberately changed the physical design. | Inputs are already structured or easily normalized, most processing is relational, and the warehouse is the main destination. |
| Dataflow with Apache Beam | Can handle batch as well as streaming. We would adapt processing to Beam; it is not a runtime for the existing PySpark code. The spreadsheet extraction still needs an appropriate parser and work distribution. | A Beam-based platform, useful connectors, or streaming requirements such as event-time windows and late-event handling justify that execution model. Streaming is an example, not a requirement for choosing Dataflow. |
| Dataproc cluster | Can run Spark with greater cluster, machine, and software control. We would manage cluster lifecycle; clusters can be temporary rather than permanently running. Our current monthly batch does not show a need for that added control. | Shared sustained workloads, existing Hadoop tooling, or infrastructure customization that serverless execution does not provide. |
| Airflow tasks in Composer | Lightweight transformations could execute on Airflow workers; larger or isolated processing can be delegated to Dataproc, Cloud Run, or Dataflow. Composer does not replace the Spark engine itself. | Composer already orchestrates the platform and the direct task workload fits its workers without impairing orchestration. |
| Apache Flink | Supports stateful processing of bounded and unbounded streams. We would adapt our transformations to Flink and provide an execution environment, connectors, and operational recovery configuration. | Continuous event-time computations, keyed state, and late-event handling are central requirements, or an existing Flink platform makes batch reuse worthwhile. For our monthly snapshots, changing engines would add work without an identified need for those capabilities. |

**Flink tradeoff example:** A continuously updated per-state count from incoming events could justify keyed state and time windows. Our government inputs are already published monthly aggregates, so there is no underlying live event stream for Flink to make fresher. Flink can run batch workloads too; it is not excluded because it is streaming-only. Kafka transports and retains events; Flink processes them, so they can be complementary components rather than alternatives to each other. [Flink architecture](https://flink.apache.org/what-is-flink/flink-architecture/), reviewed November 1, 2026.

**Decision boundary:** At today's project size, a Cloud Run processing job or parsing-plus-BigQuery SQL could simplify the architecture. Dataproc's specific advantage here is managed execution of the Spark implementation we already have, with infrastructure scoped to each batch. Distributed processing can help when data and transformations grow, but our current driver-side workbook parsing would need redesign before claiming the entire pipeline scales across executors. No alternative has been benchmarked for project cost or performance.

Supporting references reviewed November 1, 2026: [managed Spark serverless versus clusters](https://docs.cloud.google.com/managed-spark/docs/concepts/serverless-spark-compare), [Dataflow and the Beam programming model](https://docs.cloud.google.com/dataflow/docs/concepts/beam-programming-model), and [BigQuery batch-load formats](https://docs.cloud.google.com/bigquery/docs/batch-loading-data).

**Supporting examples:** An illustrative CES source value of `700.5` thousand jobs becomes `700500` jobs; an unemployment rate of `4.2` stays `4.2` percent. October 2025 belongs to USDA fiscal year 2026 but receives calendar-month key `202510`. Missing observations remain NULL with source status. Duplicate BLS series/month or SNAP state/month keys fail validation rather than being silently discarded. Preserve published negative SNAP benefits with a review flag; do not replace them with zero or assume they are corrected by transformation.

**Why NULL matters for aggregation:** `AVG(column)` excludes NULL measurements from both its sum and its count. For an illustrative three-month sequence `3.6, NULL, 3.6`, the available-value average is `3.6`; replacing NULL with zero would produce `2.4`, implying a real 0% unemployment month. The NULL-based average covers two available months, not a complete three-month period. Check `COUNT(column)` against the expected observation count; `COUNT(*)` includes rows whose measurement is NULL. If all values are NULL, `AVG()` returns NULL. Do not use an unweighted average of state unemployment percentages as an official national rate.

**Actual source example checked November 1, 2026:** The saved Idaho October 2025 BLS record (`LASST160000000000003`, `M10`) contains `value: "-"` and the footnote “Data unavailable due to the 2025 lapse in appropriations.” The matching historical Gold row retains NULL for `unemployment_rate_pct` and `source_missing` for `unemployment_status`, while valid jobs and SNAP measures remain populated. This is a read-only check of saved historical artifacts, not a fresh cloud ingestion. It illustrates a source gap rather than a lost transformation value.

**Implementation boundary:** The batch reuses shared source-parsing functions. JSON and Excel parsing, checksums, source coverage checks, and some key checks run in the batch's driver process before Spark DataFrames are created. Spark applies typed schemas and BLS unit normalization, checks measurement ranges, and writes Parquet. Do not describe workbook parsing as distributed across Spark executors or claim every validation is a Spark operation. BLS and SNAP remain separate Silver datasets; their analytical joins belong to Gold.

**What to show/do:** Highlight the Dataproc batch and Silver destination on the diagram. Show a small before/after unit example and a Silver schema or summary. Use a known completed execution for runtime evidence. The historical source exceptions are examples from the baseline, not a claim that each monthly window contains them. The runtime choice and supporting alternatives comparison were approved November 1, 2026.

Reference reviewed November 1, 2026: [serverless managed Spark overview](https://docs.cloud.google.com/managed-spark/docs/serverless-overview). Google may label the console service Managed Service for Apache Spark; our workflow uses the Dataproc batches API. Managed Spark execution charges are separate from retained storage and other services. No cost or speed advantage over alternative processing engines has been measured for this project.

### 3.5 Gold publication in BigQuery — approved explanation

**Presentation visuals:** Use the [Gold fact-constellation diagram](presentation-assets/gold-fact-constellation.png) to explain the shared dimensions and different grains. Use the [Bronze → Silver → Gold examples](presentation-assets/bronze-silver-gold-examples.png) to trace actual saved Idaho January 2015 measurements across layers. [Example tables and provenance](presentation-data-examples.md) provide selected fields and source links. These are the October 25 historical snapshot, not the November 1 scheduled-run artifacts. Both visuals have matching editable SVGs in `presentation-assets/`; Richard's review is pending.

**Slide content:** Native BigQuery tables; state/month and state/industry/month facts; shared state/date dimensions and an industry dimension; revision history; guarded publication; comparable reporting views for Data Studio.

**What to say — approved November 1, 2026:** “The Gold layer organizes the accepted measurements into native BigQuery tables. One fact table has a row per state and month, containing employment, unemployment, and SNAP measures. A second has a row per state, industry, and month. Shared dimensions provide consistent state, month, and industry labels.

Keeping those grains separate prevents state-level SNAP figures from being repeated and accidentally summed across industries. The publication jobs stage the accepted data and merge it into the current facts. An unchanged rerun leaves the measurements unchanged; a detected revision updates the current value and records the old and new values in measurement history.

The fact changes, history events, and publication record commit together in a guarded transaction. Reporting views then expose the labels, calculations, and complete comparable scope needed by the dashboard. The underlying facts can retain legitimate partial measurements without presenting an incomplete comparison as complete.”

**Technology rationale — draft:** “BigQuery fits the analytical workload: SQL joins, aggregations, historical comparisons, and dashboard queries. Native tables keep publication and reporting in the warehouse. An Iceberg-based lakehouse would be worth considering if multiple processing engines needed to share open-format tables in Cloud Storage, but that is not a requirement of this project.”

### Reporting views over Gold tables — additional wording for review

“We then create reporting views over the Gold tables. These save the SQL that joins measurements to their labels, selects comparable records, and calculates metrics such as year-over-year change. That gives the dashboard reusable reporting definitions instead of rebuilding the logic in each chart.

The tables store the accepted data; the views define how we report it. A logical view stores the query rather than another copy of its results, so it reflects the underlying tables when queried. We do not need a separate monthly job to rebuild copied reporting tables.”

**Supporting tradeoff:** Logical views simplify reuse and avoid maintaining another stored result, but querying their joins and calculations still uses BigQuery compute. They are not inherently faster or cheaper than a precomputed reporting table. If measured query cost or latency justified it, consider a maintained reporting table or a supported materialized view. Those options introduce refresh/storage considerations. Our dashboard's own query-result cache is separate from the logical view and can temporarily show older results. [BigQuery logical views](https://docs.cloud.google.com/bigquery/docs/views-intro), reviewed November 1, 2026. Do not imply that a view automatically grants access to base tables; authorized-view configuration is a separate decision.

**Evidence boundary:** The unchanged-input publication and same-run retry path were observed previously. The implementation includes revision events and a control-version guard, but do not claim that a real nonzero source revision or a concurrent-publication conflict was demonstrated. Refer to the execution record when choosing demo evidence. Iceberg snapshots would not automatically replace our explicit old/new measurement-history model.

### Supporting Q&A: Gold storage and serving alternatives

These are supporting comparisons, not additional implemented components or a claim that all were evaluated before deployment. Storage Transfer Service and Kafka are discussed with ingestion; Flink is discussed with Silver. Here, compare native warehouse tables with lakehouse storage and operational serving.

| Technology | When it would help | Tradeoff against our current design |
|---|---|---|
| Bigtable | An application needs frequent, low-latency reads/writes by designed keys at operational scale. | Requires access-pattern and row-key design. It could complement BigQuery as a serving store, but would add a data copy or synchronization path if we retained warehouse analytics. Our dashboard mainly needs joins, aggregates, and historical comparisons; time-series data alone does not require Bigtable. |
| Apache Iceberg | Spark, BigQuery, or other supported engines need shared open-format tables in object storage, with snapshots and schema/partition evolution. | Adds table metadata/catalog and writer-compatibility decisions, plus maintenance responsibilities that depend on the managed implementation. Parquet files alone are not Iceberg tables. Table snapshots do not automatically provide our explicit old/new measurement-history model. Native BigQuery tables currently keep publication and analytical queries in one warehouse. |
| BigLake | We need governed lake-data access and a lakehouse architecture integrated with BigQuery and supported engines. | Requires choosing the specific table type, catalog, access model, and supported readers/writers. It can work with Iceberg; the two are not interchangeable databases. It is a useful architecture option when sharing lake tables matters, but our current consumers do not require that additional integration. |

**Lakehouse example:** If another team needed Spark to read the same governed Gold tables queried by BigQuery without maintaining a separate warehouse copy, an Iceberg/BigLake design would merit investigation. Confirm read/write support and transactional requirements for the selected integration before promising interchangeable engines. Our existing multi-table publication transaction must not be assumed to transfer unchanged to lakehouse tables.

**Optional spoken comparison:** “We chose native BigQuery tables for analytical SQL and dashboard access. Iceberg with BigLake would be worth considering if several engines needed to share open-format lake tables. Bigtable would address a different requirement: low-latency operational serving by key.”

**What to show/do:** Show the two fact grains and their shared dimensions, then a small reporting-view query. Explain the unchanged rerun with known evidence and a revision with an explicitly illustrative old/new example if no verified real revision is available. Keep the alternative technologies in Q&A unless the audience asks about lakehouse or streaming designs.

References reviewed November 1, 2026: [BigQuery overview](https://docs.cloud.google.com/bigquery/docs/introduction), [Bigtable workload fit](https://docs.cloud.google.com/bigtable/docs/overview), [Storage Transfer Service](https://docs.cloud.google.com/storage-transfer/docs/overview), [Kafka introduction](https://kafka.apache.org/intro/), [Flink architecture](https://flink.apache.org/what-is-flink/flink-architecture/), [Iceberg table specification](https://iceberg.apache.org/spec/), [BigLake tables](https://docs.cloud.google.com/bigquery/docs/biglake-intro), and [Iceberg managed tables in BigQuery](https://docs.cloud.google.com/bigquery/docs/biglake-iceberg-tables-in-bigquery).

### What to say — points to develop

- Explain Bronze: retained original captures, manifests, checksums, and lineage. A checksum checks captured-byte integrity, not whether the publisher’s statistic is correct.
- Explain Silver: parse source formats, align fiscal/calendar months, standardize types and units, validate keys, and preserve source exceptions.
- Explain Gold: state/month and state/industry/month facts, shared dimensions, measurement history, and comparable reporting views.
- Explain baseline, catch-up, and six-reporting-month refresh. Discuss insert/update behavior and the limit on automatic older corrections.
- Explain Docker as packaging, Cloud Build as image building, Artifact Registry as image storage, and Cloud Run Jobs as execution. Discuss source-deployed functions as the considered alternative.
- Explain why managed Spark and BigQuery serve different processing/reporting roles and why the dashboard connects to views.

### What to show/do

Highlight each layer on the architecture diagram. Show a short manifest excerpt and the two fact-table grains. Select only code snippets needed to explain a decision. Keep this public-data project separate from the hypothetical BNPL interview playbook: Bigtable is not an implemented component of this pipeline.

## 4. Working demonstration and correctness checks

**Suggested time:** 4 minutes. **Status:** Walkthrough and speaking draft for review; exact artifacts and queries still to choose, verify, and rehearse.

Sections 4 and 5 form one continuous demonstration, approximately seven minutes total: pipeline execution → Bronze/Silver traceability → BigQuery results/checks → Looker Studio dashboard interaction and interpretation. Section 5 is the user-facing analytics portion of the demonstration, not an optional extra. The current interface calls Looker Studio “Data Studio”; this project does not use the separate Looker enterprise platform.

### What to say — transition draft

“I’ll show one completed execution, trace its saved input and output, and query the published data. These checks address different questions: did the workflow finish, did the expected records arrive, and are the business keys and reporting scope correct?”

### What to show/do — proposed four-minute walkthrough

| Stop | Suggested time | What to show | What to say — draft |
|---|---|---|---|
| Scheduled execution | 45 seconds | November 1 Scheduler delivery evidence and the corresponding successful `jobs-snap-monthly` execution, after verification | “The pipeline is scheduled for the first day of each month at 08:00 UTC. Here is the November 1 scheduled invocation and its completed workflow, covering ingestion, Spark processing, staging, and publication. I will also check the published output.” Use this wording only after confirming the linked delivery and workflow result. |
| Trace the inputs and outputs | 60 seconds | Pre-open one matching Bronze manifest and the corresponding Silver summary or schema | “This manifest identifies a saved source capture and its reporting window. The Silver output carries its lineage forward, so I can trace processed measurements back to the input. Here is one example of the normalized units or source status.” |
| Query Gold and check keys | 90 seconds | Run a prepared read-only query returning recent months for one state; show a compact fact-key uniqueness check | “These are the published measurements for the selected state and months. Each row has the intended grain. This additional check looks for duplicate state/month or state/industry/month keys. A new execution should not create another current row for the same key.” |
| Explain rerun evidence and transition | 45 seconds | A previously verified unchanged-rerun result, then open the dashboard | “In our unchanged-input rerun, publication reported no new measurements or revisions. We also verified that retrying an already committed refresh was recognized as already published. Next, I will use the reporting views in the dashboard to explore the results.” |

For the Gold query, choose fields that show a meaningful result and at least one source status or lineage field if useful. For the uniqueness check, zero duplicate groups is the expected result to verify, not a result to assume. These are focused checks; they do not establish all numeric values or source coverage by themselves.

The last stop uses the previously observed rerun evidence, not a promised fresh replay. Show the result only after locating the exact evidence. If it is not ready, explain the implementation briefly and spend that time on the live query instead. Keep actual dashboard interaction and chart interpretation in Section 5 rather than duplicating it here.

### Preparation and backup

Three read-only statements are prepared in [presentation-demo-queries.md](presentation-demo-queries.md): recent Idaho jobs/SNAP measurements, latest Idaho industry YoY changes, and recent committed publications with revision-event counts. Richard executes them in BigQuery and reviews the actual output before they become verified demo evidence. The publication query can help locate the November 1 run, but does not prove Scheduler provenance by itself.

Choose exact run IDs, paths, and queries when preparing this checkpoint rather than copying potentially stale handoff values. Check console access and keep secrets hidden. A fresh full run is optional and may exceed this segment’s duration. Prepare dated screenshots/results as fallback evidence and describe them honestly if live access fails.

### November 1 schedule evidence and optional manual run

**Richard's selected demo plan — November 1, 2026:** Show that the scheduled pipeline ran on November 1 as planned; optionally launch a manual execution as well. The execution's actual status, identity, and schedule provenance still need inspection before recording this as verified runtime evidence.

**Preparation:** Confirm the saved cron `0 8 1 * *` and UTC timezone. Locate the November 1 scheduled delivery in Cloud Scheduler history/logs, correlate it with the workflow execution using timestamps and available identifiers, and confirm that workflow's terminal status and publication result. Scheduler delivery success establishes that invocation was accepted; it does not by itself establish that ingestion through Gold completed. Record the workflow execution ID, UTC start/end times, publication/run ID, and matching summary paths when verified. A workflow timestamp alone does not prove it was scheduled rather than manually started.

**Optional live action:** Launch a manual execution using Scheduler's **Force run**, demonstrating the same configured invocation path. Alternatively, start an execution directly from Workflows to demonstrate that manual interface; state which route is being used. Richard performs this action during the demo after confirming no execution is still active. Launch it near the beginning and continue the walkthrough with the completed November 1 artifacts rather than waiting on the live run. Check its status again at the end if time permits; call it running until it actually completes.

**What to say — optional:** “The scheduled run shows unattended execution. I can also invoke the same pipeline manually, for example to pick up a newly available publication without waiting for next month's schedule. While that runs, I will use the completed scheduled execution to show the outputs.”

A manual rerun discovers current inputs and may legitimately find new or revised data; do not promise it will produce zero changes. Keep its artifacts distinct from the completed scheduled run. This plan does not authorize an agent to start a cloud execution.

## 5. Dashboard results

**Suggested time:** 3 minutes. **Status:** Select final visuals and observations together.

### What to say — transition draft

“The BigQuery reporting views feed our Looker Studio dashboard. This is where a user can explore the results without writing SQL. I will select a state and date range, compare jobs with SNAP participation, then look at how the selected industries changed over time.”

### Proposed dashboard demonstration

| Action | What to explain |
|---|---|
| Select one state and a reporting period | The controls set the geography and time window for the comparison. Confirm that the intended charts respond. |
| Show jobs and SNAP trends | Identify whether each chart shows a level or a year-over-year rate, and explain its units. Discuss one observation after verifying the selected data. |
| Open the industry comparison | Compare construction, manufacturing, and retail trade; explain levels versus growth rates and any scope restrictions. |
| End on a useful result | Connect one verified observation to the opening question about employment and SNAP participation. Treat association as descriptive rather than proof of causation. |

### Dashboard technology choice — draft for review

**What to say — draft:** “I chose Looker Studio because the project needs an interactive reporting dashboard: state and date filters, time-series comparisons, and industry views. It connects directly to our BigQuery reporting views, so I can build the report in the browser without deploying a separate application.

The reporting views keep the comparison definitions and reusable calculations in BigQuery. Looker Studio handles presentation and user controls. Once connected, it automatically picks up new accepted data through that connection when it fetches fresh results, according to its data-freshness settings. We do not manually export or re-import data each month.”

**Naming:** The current interface calls Looker Studio “Data Studio.” Use the name familiar to the audience and clarify the rename once if needed. This project does not use the separate Looker enterprise platform or a LookML model.

### Supporting Q&A: Power BI or Streamlit instead?

| Option | When it would make sense | Tradeoff for this project |
|---|---|---|
| Looker Studio — chosen | Standard interactive reporting directly over BigQuery views, browser authoring, and a hosted report | Avoids a separately deployed dashboard application. Chart behavior, supported calculations, and customization are constrained by the BI tool; put reusable complex calculations in BigQuery. Query performance and cost still depend on the underlying queries and caching. |
| Power BI | A team already uses its semantic models, DAX measures, reporting workflows, or Microsoft BI environment | BigQuery is supported through Import and DirectQuery. Import introduces a separate refreshable data copy; DirectQuery queries the source as needed. We would manage its semantic model, credentials, refresh/query behavior, and sharing/license requirements. It is not excluded merely because our warehouse is on GCP. |
| Streamlit | Custom visual interactions, Python analyses, what-if controls, or an application workflow beyond standard BI charts | Can query BigQuery and offer more code-level flexibility. We would own the application code, deployment, access controls, dependencies, and cache behavior. Hosting and authentication choices determine how much operational work this adds. We do not currently need those custom application features. |

**Power BI licensing note:** Personal authoring and organizational sharing have different requirements. Sharing generally involves paid licenses and/or qualifying capacity; verify the intended sharing arrangement rather than claiming Power BI always costs money or always requires every viewer to pay. No price comparison has been measured for this project.

**Freshness versus schema changes:** New rows and revised values flow through the existing BigQuery connection when the report fetches fresh results. Data freshness is a query-result caching policy, not an independent monthly ingestion schedule. Prior screenshots showed a 12-hour setting; verify the actual setting before the demonstration. Adding or renaming columns can require refreshing the data-source fields and updating charts. Manual data refresh can issue new BigQuery queries and incur normal query charges. Do not promise an immediate dashboard update at the instant a workflow commits, or describe the connection as a continuously pushed live stream.

### Supporting Q&A: caching and Pause updates

**Optional spoken detail:** “While editing the dashboard, we can pause updates, make several changes, and resume data requests when ready. This reduces unnecessary requests during report configuration. Looker Studio also caches chart results according to its data-freshness settings.”

**Editing instructions:** In report edit mode, select **Pause updates** in the toolbar, configure the components, then select **Resume updates** to fetch their data. Pausing affects the current editor's report session; it does not stop the monthly pipeline or pause other collaborators. Pure layout/style changes normally do not change the data query. Adding components or changing data settings, filters, grouping, or sorting can request data. [Pause report updates](https://docs.cloud.google.com/data-studio/pause-report-updates).

**BigQuery cache:** There is no per-view cache configuration required for ordinary logical views. Query-result reuse is enabled by default unless the submitting client disables it. Eligible repeated identical SQL can reuse results, typically for approximately 24 hours on a best-effort basis. This is not a guaranteed 24-hour view snapshot or refresh schedule. Changes to referenced tables or views, different query text, non-deterministic functions, and other documented exceptions can prevent reuse. Looker Studio's cache is separate; its hits can avoid submitting a BigQuery query at all. Do not assume every dashboard query qualifies for either cache. [BigQuery cached results](https://docs.cloud.google.com/bigquery/docs/cached-results).

**Verification if needed:** Inspect a BigQuery query job's **Job Information** for cached results and processed bytes; the API exposes `statistics.query.cacheHit`. A cache hit has no query-processing charge. These are documented behaviors, not a live inspection of our dashboard's submitted job settings. References checked November 1, 2026.

**Examples for questions:** Power BI becomes more attractive if the audience already depends on a shared Power BI model and measures. Streamlit becomes more attractive if users need to enter assumptions and run a custom scenario calculation. Our current requirement is filtering and comparing published statistics, which fits the existing Looker Studio report.

References reviewed November 1, 2026: [BigQuery table/view connector](https://docs.cloud.google.com/data-studio/connect-to-google-bigquery), [data freshness and query costs](https://docs.cloud.google.com/data-studio/manage-data-freshness), [Power BI BigQuery connector](https://learn.microsoft.com/en-us/power-query/connectors/google-bigquery), [Power BI license capabilities](https://learn.microsoft.com/power-bi/fundamentals/service-features-license-type), and [Streamlit data connections and caching](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data).

### What to say — points to develop

- Explain one state’s jobs and SNAP levels, then year-over-year growth: each month compared with the same month a year earlier.
- Explain the selected industries and common 48-state comparison scope.
- If showing the scatter/trendline, explain association rather than causation.
- If showing accumulated positive/negative monthly YoY rates, label them percentage-point months, not total job growth. Their totals depend on selected dates and geography.
- Describe one or two observations after checking the final chart and selected period.

### What to show/do

Select one state and a deliberate reporting period. Explain axes, units, legend, and controls before interpreting the pattern. Keep a single state selected for unweighted growth-rate comparisons. Disclose any date exclusion relating to January–February 2019 SNAP early issuance and its following-year comparison effects. Do not sum participants across months and call the result unique people.

## 6. Challenges and lessons learned

**Suggested time:** 2 minutes. **Status:** Two challenges selected by Richard on November 1, 2026. Richard will supply his own explanations of investigation, resolution, and verification.

### What to say — points to develop

### Challenge 1: different source formats and definitions

**Challenge wording:** “BLS provided API responses, while USDA SNAP data came in fiscal-year spreadsheets. The challenge was bringing them into a consistent monthly structure while handling different units, missing measurements, and source exceptions.”

**Richard's explanation — to complete:** Describe how you investigated and resolved these differences, and what you checked to establish that the resulting data was correct. Leave this answer in Richard's own words.

### Challenge 2: a growth chart that appeared broken

**Challenge wording:** “On the Looker Studio page ‘U.S. Jobs and SNAP,’ including 2020 in the jobs-versus-SNAP year-over-year comparison produced such a large spike that the other changes looked almost flat. At first, the chart appeared broken.”

**Richard's explanation — to complete:** Describe what you investigated, what you concluded, how you chose to present the data, and how you verified that choice. Richard will supply the resolution and lesson in his own words.

**Optional query to show:** Richard's [Alabama growth-outlier query](presentation-demo-queries.md#optional-challenge-query-investigate-alabama-snap-growth-outliers) sorts by absolute SNAP YoY growth and displays current/prior-year counts. Use its returned month to connect the BigQuery investigation to the Looker Studio chart. Keep this diagnostic separate from the revision-history check.

**Accuracy note for preparation:** COVID-era employment changes are relevant context for 2020, but do not attribute the previously investigated extreme SNAP spike to COVID without evidence. The supplied Alabama result for February 2020 compared 704,788 participants with 3,926 in February 2019, yielding a YoY fraction of about 178.518 (approximately 17,852%). That low prior-year denominator accounts for the extreme comparison. Keep this distinction available when Richard develops his explanation; it is not a prewritten resolution or a claim about every state's 2020 trend.

### What to show/do

For the source-format challenge, use one BLS/SNAP example if useful. For the visual challenge, open the Looker Studio page Richard identifies as **U.S. Jobs and SNAP**, specifically the chart comparing `jobs_yoy_growth_rate` and `snap_yoy_growth_rate` by reporting month. Confirm the page label and selected state in the current report before rehearsal. Include the relevant 2020 comparison in the date range to reproduce the scaling issue; the previously investigated extreme value was Alabama February 2020. Do not assume selecting any state or any month in 2020 reproduces it. Prepare the chart state beforehand and let Richard demonstrate his chosen resolution.

Use concise dated evidence where useful. Explain relevant limitations only where they affect the example: source lags, missing unemployment, unavailable construction series, flagged benefit values, and older revisions outside the automatic window. Do not claim every possible fault or nonzero-revision scenario has been tested.

## 7. Conclusion

**Suggested time:** 1 minute. **Status:** Closing wording approved November 1, 2026.

### What to say — approved

“This project brings employment and SNAP data into a repeatable monthly pipeline, from preserved source captures through validated datasets to an interactive dashboard. It lets users compare state and industry trends while keeping results traceable to their sources.

One limitation is that automatic refreshes cover only the latest six reporting months, so older corrections require a separate backfill.”

Invite questions after the closing statement. Add a prioritized next step only if Richard wants to include one. AI/ML/RAG is not currently included; only add that demonstration if a functioning component is deliberately introduced and reviewed.

### What to show/do

Return to the objective, architecture, or a final dashboard view. Connect the delivered functionality to the opening question. Avoid unmeasured cost/performance claims or unimplemented features.

## Review and rehearsal checklist

- [x] Introduction approved by Richard.
- [x] Source explanation approved by Richard on November 1, 2026.
- [x] Historical coverage and refresh explanation approved by Richard on November 1, 2026.
- [x] High-level service overview approved by Richard on November 1, 2026.
- [x] Scheduling/orchestration explanation and scheduler rationale approved by Richard on November 1, 2026.
- [x] Cloud Run ingestion explanation and alternatives approved by Richard on November 1, 2026.
- [x] Historical loading, six-month refresh policy, and USDA file-download clarification approved by Richard on November 1, 2026.
- [x] Bronze preservation and traceability explanation approved by Richard on November 1, 2026; landing-storage alternatives omitted from the main talk.
- [x] Silver transformations, validation examples, and processing-tool comparison approved by Richard on November 1, 2026.
- [x] Gold data-model and publication explanation approved by Richard on November 1, 2026.
- [x] Conclusion wording approved by Richard on November 1, 2026.
- [x] Richard reports checking the November 1 scheduled run; exact execution/publication identifiers and backup capture remain to assemble for the demo.
- [x] Richard reports executing all four prepared data/revision/outlier queries; complete revision results were not supplied in this conversation.
- [x] Richard ran the fact-key validation query and reported all zeros on November 1, 2026: no duplicate keys, extra duplicate rows, or NULL-key rows in either fact. This does not establish all source coverage or numeric correctness.
- [x] Actual GCP architecture diagram reviewed and accepted by Richard on November 1, 2026.
- [x] Historical Bronze/Silver/Gold examples and Gold fact-constellation visual accepted by Richard on November 1, 2026.
- [ ] Component explanations and technical decisions reviewed.
- [ ] Exact demo artifacts/queries selected and checked.
- [ ] Final chart settings, dates, and observations checked.
- [ ] Richard's challenge investigation, resolution, and verification explanations completed; conclusion already approved.
- [ ] Google Slides and speaker notes assembled.
- [ ] Backup evidence prepared.
- [ ] Rehearsal completed within 10–30 minutes.
