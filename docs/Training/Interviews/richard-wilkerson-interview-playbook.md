# Richard Wilkerson

TODO: mention more of the architecture and quality controls / governance 

## Interview Playbook

Principal / Lead Data Engineer  ·  GCP  ·  AWS  ·  Snowflake & Databricks  ·  Payments, Luxury Retail & Banking

Three case studies from the three most recent roles — PayPal (BNPL), Neiman Marcus, Ally Bank — each with a STAR talk track, a batch-pipeline walkthrough, a streaming lane, dimensional model, data quality, security, and sample data. Code lives in the companion Snippet Library.

*Prepared October 2026 · United States market*

*Practice context: The role scenarios and added technical examples are hypothetical interview preparation, not verified employment or company architecture. Figures marked † require supporting evidence. Explanatory bullets were added with primary technical references reviewed October 27–28, 2026. Learner questions were replaced with labeled explanations; these do not establish employer implementation or measured outcomes.*

#### How to Use This Playbook

**Open with the batch pipeline. Only bring up streaming if the interviewer asks for it** — or after you’ve finished batch and want to show range. Your headline is “Principal Data Engineer | Payments & Cloud Warehousing,” so expect design-level questions: why you chose a pattern, what you’d do differently, and how you led others.

- **Say “I”, not “we.”** “I designed”, “I built”, “I led.” Credit the team once, then own your part.

- **Lead with the business pain, then the design.** “Bad partner data kept reaching risk datasets, so I built a per-market circuit breaker” beats “I used Airflow sensors.”

- **Quantify every result.** Your one hard number in these roles is the 25% runtime cut at Neiman Marcus. Figures marked † are suggested framing — confirm or replace each before the interview.

- **Separate company context from your results.** PayPal’s ~400 PB migration and Zoom’s pandemic growth are context.

- **Draw two lanes.** Batch on top, streaming below, meeting at the shared storage layer.

- **When they ask for code**, open the Snippet Library — every pattern here has a matching snippet, numbered by case.

#### Your 60-Second “Tell Me About Yourself”

*“I’m a data engineer with over fourteen years building secure, high-throughput platforms for payments, retail, banking, automotive and SaaS. Right now I lead the Buy Now, Pay Later acquisition and servicing data products at PayPal on BigQuery, where I built a circuit-breaker framework that stops bad upstream data from reaching risk datasets, market by market. Before that I led the data engineering team at Neiman Marcus, introducing dbt on Snowflake, securing payment and client data, and cutting critical pipeline runtimes by 25%. At Ally Bank I built the Databricks lakehouse for deposits and auto lending, with CDC from Debezium and full history for audit.

#### The Three Case Studies

| **#** | **Company & dates** | **Cloud** | **Domain** | **Headline patterns** |
| --- | --- | --- | --- | --- |
| 1 | PayPal · 2026–now | GCP | Consumer credit — BNPL | Circuit breaker & kill switch, per-stage error semantics, config-driven market rollouts, Iceberg/BigLake, Kafka/Flink, Bigtable |
| 2 | Neiman Marcus · 2023–2026 | Snowflake on AWS | Luxury retail | dbt adoption, shared macros, semantic layer, tokenization & masking, 25% faster, Snowpipe Streaming |
| 3 | Ally Bank · 2021–2023 | AWS + Databricks | Digital banking | Debezium CDC on MSK, MERGE SCD2 for audit, Teradata → dbt, Unity Catalog, FDIC/CFPB/BSA/SOX |

For Azure questions, Neiman Marcus also used Azure Data Factory for some feeds; for connected-vehicle or IoT questions, use Honda; for high-volume streaming, use Zoom (back-up stories at the end).

#### Five Questions to Have Cold

- “How do you stop bad data from spreading?” → PayPal, Section 03 (your circuit breaker).
> “I put validation before publication so a successful pipeline run doesn’t automatically mean the data is safe to use. In the PayPal example, each market’s batch goes through schema checks, completeness checks, and business rules, such as linking disbursements to approved applications. If a critical check fails, that market’s batch is quarantined and downstream publication is blocked, while independent healthy markets continue. The circuit breaker keeps the affected market blocked until the issue is resolved and the batch passes revalidation. I also have an audited kill switch for manually holding publication.”

- “How did you handle unexpected schema changes?” → Section 03 of each case.
> “I separate changes we can safely tolerate from changes that break the data contract. For incoming files, I compare the observed schema with a versioned contract before curated processing. An optional new field can remain in raw data under an approved compatibility policy, while downstream models continue selecting known columns explicitly. If a required field disappears or changes to an incompatible type, I quarantine the batch, block its downstream publication, and alert the source owner. After we agree on the intended change, I update the contract and transformations, test them, and replay the affected data.”

- “How do you handle slowly changing dimensions?” → Section 07 (Ally is your strongest answer).
> “I start by asking whether reporting needs the current value or the value that applied when an event happened. At Ally, account attributes such as product, rate tier, and ownership needed historical tracking, so I used Type 2. When a tracked attribute changed, I closed the existing version and inserted a new row with a new surrogate key, effective dates, and a current flag. Facts reference the version valid at their business timestamp. That preserves historical reporting when an account changes later. For attributes where history isn’t required, I use Type 1 and overwrite the value.”

- “Why NoSQL instead of your warehouse?” → Track 2, NoSQL hot path.
> “The decision comes from the access pattern. The BNPL decisioning service needs a customer’s current exposure and selected profile attributes by key during an application request. I would use Bigtable for those derived serving records and keep BigQuery for historical analysis and reconciliation. Flink owns exposure updates, while a separate pipeline owns profile updates. That adds operational complexity, so I would justify it with measured lookup latency, concurrency, freshness, and cost. I would also prevent older replay writes from replacing newer state and define what the service does when the data is stale.”

- “How did you protect payment and banking data?” → Section 09.
> “I used several layers of protection. In the retail example, card numbers stayed out of analytics through upstream tokenization, and customer contact information was masked for roles without an approved need. In the banking example, account numbers and SSNs were tokenized before curated processing. I restricted sensitive attributes through role-based access, used encryption and managed keys, and gave pipeline identities only the permissions they needed. I also maintained source lineage, audit evidence, and reconciliation so reporting teams could trace the data. Access changes went through code review and controlled deployment.”

**Case Study 1 of 3  ·  Most Recent Role**

## PayPal — Buy Now, Pay Later (BNPL) Acquisition & Servicing Data

Lead Data Engineer  ·  PayPal, San Jose, CA  ·  GCP  ·  Consumer Credit — BNPL Applications, Repayments & Delinquency  ·  Mar 2026 – Present

#### Your 30-Second Opener

*“At PayPal I lead development of the Buy Now, Pay Later acquisition and servicing data products — applications, approvals, disbursements, repayments and delinquency — on the BigQuery layer PayPal standardized on after leaving on-prem Hadoop. The piece I’d highlight is a kill-switch and circuit-breaker framework I built: when upstream quality drops below threshold in a market, it stops bad data from propagating downstream. Let me start with the batch platform.”*

*Keep the ~400 PB Hadoop-to-BigQuery migration as company context — “the platform we build on.” Your personal story is BNPL data products, the circuit breaker, and the error-handling refactor.*

### S   ·  SITUATION

PayPal offers BNPL products to consumers in the U.S. and several international markets. Each market has its own partners, rules and data feeds. Product and risk teams need accurate data on who applied, who was approved, what was disbursed, how repayments are going, and who is delinquent.

The pain: when an upstream feed in one market broke, bad data flowed straight into downstream datasets used for risk decisions and reporting — there was no automatic way to stop it. Pipelines treated every error the same way: either retry everything or fail everything, so one bad partner file could block a whole run. Rolling out a pipeline change to one market meant deploying it everywhere. And the real-time Kafka/Flink path and the BigQuery batch path could drift apart in their logic.

The people who felt it: risk and credit teams, product managers for BNPL, international market partners, and analysts.

### T   ·  TASK

As Lead Data Engineer, I lead BNPL pipeline development in Python, PySpark and BigQuery SQL across raw, curated and semantic layers: API and partner-feed ingestion, the acquisition and servicing datasets, quality suites, the circuit-breaker framework, configuration-driven market rollouts in Cloud Composer, Iceberg publication through BigLake, environment builds with Terraform and GitHub Actions, and consistency reviews between the streaming and batch paths. I also review code and mentor engineers.

### A   ·  ACTION

- Built BNPL datasets in **BigQuery** across **raw, curated and semantic layers** — applications, approvals, disbursements, repayments, delinquency.
  - **Raw / curated / semantic:** Yes, these roughly map to Bronze / Silver / Gold. Raw preserves source records with ingestion metadata so you can investigate and replay them. Curated makes them reliable and reusable: parse types, deduplicate, standardize currencies and timestamps, validate keys, and join related entities. Semantic gives consumers agreed business definitions, such as approval rate by market and day. These are responsibilities, not mandatory products or separate physical databases; Gold can contain both detailed facts and aggregates.
  - **BNPL example:** A raw repayment payload becomes one validated repayment transaction in curated, then contributes to a semantic metric such as total repayments received per market/day.
  - **Applications:** Requests to obtain BNPL credit, such as a customer asking to split a purchase into installments. The grain might be one row per `application_id`; button clicks are separate behavioral telemetry that could be joined to the application funnel.
  - **Approvals:** Credit decisions on those applications: approved, declined, or pending, with decision time and approved amount. An approval does not guarantee that the customer completes the purchase.
  - **Disbursements:** Funds released under an accepted financing arrangement, for example settlement to a merchant. Exact settlement mechanics depend on the product and partner.
  - **Repayments:** Money collected against the customer's installment obligation, including payment timing, amount, allocation, reversals, and refunds where applicable.
  - **Delinquency:** An obligation overdue under the product's agreed due-date and payment rules. For example, an unpaid installment can contribute to a days-past-due measure. Each entity has its own key and grain; do not count decision retries or payment attempts as new loans.

- Integrated **GraphQL and REST APIs** into **PySpark on Dataproc**, and **partner feeds** from international markets through **Pub/Sub and Cloud Storage** landing zones.
  - **Partner feed:** Data delivered by an external organization, such as a lending or servicing partner sending daily loan balances and repayment statuses. Delivery could be a CSV/Parquet file, an API response, or events. “Feed” describes the ongoing data supply.
  - **Pub/Sub:** Google's managed messaging service. A producer publishes messages to a topic; subscribers consume them through subscriptions. A message could contain a repayment event or a pointer to a landed file. A subscriber or delivery integration still has to write data to Cloud Storage or BigQuery. See the [Pub/Sub overview](https://docs.cloud.google.com/pubsub/docs/overview).
  - **Landing zone:** The first receiving location, such as a Cloud Storage bucket path organized by market and arrival date. It usually belongs to Raw/Bronze, but is not automatically a validated raw table. Preserve the original object and record its source, arrival time, batch ID, and schema version.

- Added a **Cloud Function schema-drift check** on every landing.
  - **Schema drift:** A source changes the shape or types of its data: a field appears or disappears, `amount` becomes text, or a nested object changes. Compare the landed file's schema or parsed payload against a versioned contract: required fields, types, nullability, and approved optional fields. A landing-triggered function can do a lightweight check; large-file validation belongs in a processing job.
  - **Why check:** A partner renaming `repayment_amount` to `paid_amount` could break a job or silently produce missing values. Compatible additions may proceed under policy; missing required fields or incompatible types should block that batch and alert its owner. Keep value checks too: cents changing to dollars is a semantic change that a schema-only check may miss.

- Built a **kill-switch and circuit-breaker framework** — country configuration, feature flags and Airflow sensors halt downstream propagation when quality thresholds are breached.
  - **Kill switch:** An explicit operational override, usually set by a person, that blocks a scope such as one market during an incident or rollout.
  - **Circuit breaker:** An automatic protective mechanism that opens when a failure threshold is exceeded. A full implementation persists state and defines recovery, often closed → open → half-open probe → closed. Closed permits processing; open blocks it. A task that simply fails a quality check is a quality gate; it becomes part of a circuit breaker only with those state and recovery rules.
  - **Together:** Quality failures can open the breaker automatically while a kill switch lets an operator keep the market stopped until investigation and recovery are complete.
  - **Sensor:** An Airflow task that waits for a condition, such as “the validation result for this market and batch is available.” Pending means wait with a finite timeout; passed means continue; failed means raise a failure and block dependent publication. Use reschedule mode or a suitable deferrable sensor to avoid occupying a worker while waiting. See [Airflow sensors](https://airflow.apache.org/docs/apache-airflow/2.8.2/core-concepts/sensors.html).
  - **Where to configure:** The sensor's logic and dependencies live in the Python DAG file. In GCP Console, open your Cloud Composer environment, upload the DAG through its DAGs folder, and follow its Airflow webserver link to inspect runs. Market settings can be stored in Airflow UI → Admin → Variables for this small lab. There is no generic GCP “circuit breaker sensor” switch. Follow the [market rollout walkthrough](gcp-airflow-market-rollout-walkthrough.md).

- Refactored error handling to support **retry, quarantine, partial-load and full-failure** semantics per stage.
  - **Before, in this hypothetical design:** A whole multi-market load might run inside one task with one retry policy. A temporary API timeout and a permanently malformed partner file both trigger a full retry; after retries are exhausted, every market fails. If writes append without stable keys or batch IDs, retries can also duplicate already-written records.
  - **Improvement:** Classify failures, isolate market/batch work, retry only transient failures with bounds, preserve rejected inputs, and make repeated writes safe. Splitting tasks alone does not guarantee idempotency or correct publication.
  - **Quarantine:** Retain rejected records/files separately with source, batch ID, validation failures, and an owner for correction/replay. Example: a repayment file has no loan IDs. Quarantine is an observable holding area, not silently deleting bad rows.
  - **Partial load:** Publish independently valid scopes while explicitly recording incomplete ones. Example: publish the complete US batch while holding the UK batch. Do not call a market's loan balance complete after dropping its bad repayments, and do not publish a global total as complete while a required market is absent.
  - **Full failure:** Block the affected publication when a critical dependency is unreliable, such as inconsistent reconciliation totals or an invalid currency conversion table used by all markets.
  - **Why per stage:** Raw can preserve a malformed payload for investigation; curated must reject invalid keys; semantic must reject an incorrect join, stale reference data, or inconsistent totals. Knowing the expected shape does not prove each later transformation or dependency is correct. Quarantine scope and publication scope are separate decisions.

- Ran **configuration-driven market enablement in Cloud Composer** for controlled rollouts; built environment variants with **Terraform and GitHub Actions**.
  - **Controlled rollout:** Deploy code that understands both the existing and new behavior, then use a market configuration such as `US.enabled=true`, `UK.enabled=false`. Enable one market, compare its output and timeliness against acceptance criteria, then enable another. If a check fails, stop new publication for that market and investigate before resuming.
  - **Is it a ramp-up?** Yes, by market. A percentage rollout is another option, but splitting financial records arbitrarily can break totals and joins. Keep the unit coherent, such as a whole market or an explicitly defined customer cohort with all dependent records.
  - **Control detail:** Record code/config versions with each run, isolate market outputs, and check the stop flag again before publication. Disabling a flag does not undo published data or automatically cancel a running task.
  - **Environment variants:** Yes: Dev for development, UAT/staging for acceptance and integration checks, and Prod for consumer-facing data. Terraform can reuse modules with different project IDs, bucket/dataset names, service accounts, networking, capacity, and schedules. GitHub Actions can validate changes and deploy the intended version into each environment.
  - **Separate dimensions:** Dev/UAT/Prod identifies the environment; US/UK identifies the market. Both markets can exist in each environment. Keep production identities and sensitive data out of development, and keep credentials in a secrets service rather than Terraform variable files.

- Published curated datasets as **Apache Iceberg tables through BigLake** for Spark and BigQuery consumers.
  - **Iceberg:** An open table format: data files, typically Parquet, plus metadata describing schemas, partitions, files, and committed snapshots. It adds table-level transaction and evolution capabilities above a directory of files.
  - **BigLake framing:** Specify the integration. In a Spark-managed pattern, Spark commits an Iceberg table in Cloud Storage and BigQuery accesses it as an Iceberg external table through the supported catalog/metadata configuration. BigQuery-managed Iceberg tables are a different ownership model. BigLake is an access/catalog integration, not a cleansing transformation; either curated/Silver or semantic/Gold data can use Iceberg. See [Iceberg external tables](https://docs.cloud.google.com/bigquery/docs/iceberg-external-tables) and [Iceberg managed tables](https://docs.cloud.google.com/bigquery/docs/biglake-iceberg-tables-in-bigquery).

- Enforced **dbt tests and Great Expectations**; monitored in **Datadog**; reviewed **Kafka/Flink vs. BigQuery** logic for consistency.
  - **dbt tests:** Assertions on warehouse models, usually expressed as SQL that identifies violating rows: non-null keys, uniqueness, accepted statuses, relationships, or custom business rules. They sit close to the dbt transformation graph. See [dbt data tests](https://docs.getdbt.com/docs/build/data-tests).
  - **Great Expectations:** Defines expectation suites and runs validations against configured data batches, useful for checking incoming or intermediate datasets as well as warehouse data. For example, validate required repayment fields before a model runs. See [GX validations](https://docs.greatexpectations.io/docs/core/run_validations/).
  - **Overlap:** Both can check nulls, ranges, and uniqueness. Choose where a rule belongs and who owns it; you do not need duplicate tests in both tools. Neither tool stops publication unless the orchestrator enforces its result.
  - **What to review:** Compare the Flink streaming transformation with the BigQuery batch transformation for the same business definition: keys and grain, duplicate handling, event timestamps and time zones, late arrivals, currency units, refunds, deletes, joins, and aggregation windows. Kafka transports the events; it is not the SQL transformation being compared.
  - **Example:** Compare total posted repayments for the same market/day and source cutoff. The live stream may initially be lower because some events have not arrived. After the agreed lateness/reconciliation window, explain or repair remaining differences. Match inputs and cutoff before expecting matching results; batch versus streaming does not excuse different business logic.

### R   ·  RESULT

*This role is recent and the resume has no metrics for it, so figures marked † are suggested framing. Replace each with a number you can defend, or speak to it qualitatively.*

- **Bad upstream data stopped at the source** — the circuit breaker halts propagation per market instead of letting it reach risk datasets.
  - **Risk here:** Yes, the credit/risk team evaluates exposure and repayment behavior. Its consumer dataset might contain outstanding balance, days past due, or repayment performance; the dataset can support analysis and models without itself being the live credit-decision service.
  - **Bad-data example:** A partner accidentally duplicates repayment events. If those duplicates reduce outstanding balance twice, a borrower can appear less indebted and more up to date than they are. Alternatively, missing repayments can falsely make a borrower look overdue. Duplicate-key, completeness, and source-total checks should block the affected publication while the raw data is retained.

- **One bad partner file no longer blocks a whole run** — partial loads and quarantine let healthy markets publish on time.
  - **Meaning:** Suppose US and UK deliver independent daily repayment files. The UK CSV has an invalid schema; the US file is complete and passes checks. Quarantine the UK batch, keep UK publication blocked, publish US, and mark overall coverage as incomplete. A partner file is an externally supplied object; an API is another delivery method and can fail in a similar way.
  - **Boundary:** This works only when the publications are independent. A cross-market report requiring both markets must still wait or clearly disclose its incomplete scope.

- **Market-by-market rollouts** through configuration, so a change can go live in one country first.
  - **Hands-on workflow:** Follow [GCP Console + Airflow: market rollout walkthrough](gcp-airflow-market-rollout-walkthrough.md). It includes a small companion DAG, Airflow Variable values, where to upload it, expected task states, enabling a second market, and blocking one market while another continues.
  - **Scope:** The exercise simulates quality results and publication in logs. It teaches orchestration controls without building the full BNPL data platform or claiming a complete stateful circuit breaker.

- **On-time publication across markets above 99%†** after the error-handling refactor.
  - **On-time publication:** The validated dataset is available to its consumers by an agreed deadline, for example 07:00 in the market's reporting time zone. A DAG finishing before 07:00 is insufficient if the output is incomplete, fails reconciliation, or has not been made available.
  - **Measurement:** On-time eligible market/day publications ÷ all eligible market/day publications × 100. Define the reporting period, deadlines, and exclusion rules in advance; do not remove failed markets from the denominator. The 99% figure above is an unverified practice placeholder.
  - **Why error handling helps:** Bounded retries recover temporary outages; quarantine avoids repeatedly retrying malformed files; isolated tasks let healthy markets finish. These can improve timeliness, but held markets still miss their deadlines unless recovered in time.

- **Data incidents reaching risk consumers down sharply†** once thresholds gated publication.
  - **Breakdown:** A data incident is an unexpected problem with a dataset, such as duplicate repayments, missing balances, or stale records. “Risk consumers” means the teams, reports, or models using those datasets. “Reaching consumers” means the defective version was published and became available for use.
  - **Before/after example:** Before a gate, duplicate repayments can reach a risk report and understate balances. With a gate, validation rejects the batch and preserves the last accepted version, with its age and blocked-refresh status visible. Source defects may still occur; fewer are allowed through to consumers.
  - **Tradeoff and evidence:** Blocking publication protects correctness but can make data stale. Alert the owner, show freshness, and track both escaped defects and missed deadlines. “Down sharply” needs actual before/after incident records for comparable periods; this playbook does not establish that result.

- **One Iceberg table serving both Spark and BigQuery consumers**, with snapshot time travel.
  - **Shared table:** In the Spark-managed example, Spark writes Parquet files plus Iceberg metadata to Cloud Storage and commits a snapshot. BigQuery's Iceberg external-table integration references that table's catalog/metadata; both engines then read the same committed table state. Keep metadata discovery current and grant the appropriate storage/catalog access. This avoids maintaining a separate copied table for every engine; it does not make all engine features or write paths interchangeable.
  - **Spark versus BigQuery:** These are processing/query engines, not synonyms for batch and streaming. Spark supports batch and Structured Streaming; BigQuery supports analytical SQL over data loaded through batch or streaming ingestion. Two batch consumers can read the same Iceberg table. See [BigQuery Iceberg access](https://docs.cloud.google.com/bigquery/docs/iceberg-external-tables).
  - **Native BigQuery tables:** Yes, time travel is built in, with a default seven-day window configurable from two to seven days. It allows querying recent historical table state; it is not permanent audit history or SCD Type 2. See [BigQuery time travel](https://docs.cloud.google.com/bigquery/docs/time-travel).
  - **Iceberg tables:** Historical reads depend on retained Iceberg snapshots, metadata, and referenced files. For Iceberg external tables, BigQuery can query retained snapshots using `FOR SYSTEM_TIME AS OF`, but the native BigQuery time-travel/fail-safe retention windows do not apply. Snapshot expiration and file cleanup can remove that history. See [external-table historical queries](https://docs.cloud.google.com/bigquery/docs/iceberg-external-tables#query_historical_data).

### ◆   ·  ARCHITECTURE AT A GLANCE

**Batch lane (primary)**

```text
SOURCES
  BNPL application, decision, disbursement & repayment services (GraphQL/REST)
  international partner feeds (Pub/Sub + Cloud Storage landing zones)
  market configuration (country rules, feature flags)
     |  [PySpark on Dataproc API ingestion]  [Pub/Sub -> GCS -> BigQuery]
     v
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
 
ORCHESTRATION  Cloud Composer: config-driven market enablement + sensors
```

**Streaming lane (separate — supplementary)**

```text
loan & repayment events -> Kafka -> Flink -> Bigtable: customer_exposure
                              |                 ^
                              |                 | backend decisioning reads
                              v                 |
                      GCS -> BigQuery     Bigtable: customer_profile
                    (retained history)           ^
                                                |
                                    profile-owning update pipeline
```
- **Bigtable and the decisioning hot path:** Bigtable is Google Cloud’s managed wide-column/key-value database. In this hypothetical design, it serves two separate tables: customer_exposure for stream-derived balances and customer_profile for selected profile attributes. A backend decisioning service retrieves the required rows by customer key. The “hot path” is the time-sensitive request sequence that must finish before the application decision can continue. BigQuery remains the analytical history and reconciliation layer. Measure lookup latency and event-to-serving freshness separately; no sub-millisecond result is established here. See the [Bigtable overview](https://docs.cloud.google.com/bigtable/docs/overview).
- **What GCS means and how Kafka events reach BigQuery:** GCS means Google Cloud Storage, the object-storage service comparable in role to S3. The arrows mean producer → Kafka → Flink → separate sinks. A configured sink writes retained events/files to GCS; a later load or processing job reads those files into BigQuery. Kafka does not automatically move GCS files into BigQuery. Also distinguish retained original events from transformed stream outputs: choose and document which is archived.
- **How incoming records merge into BigQuery:** A Python task can submit SQL, but BigQuery performs the warehouse merge. First stage and deduplicate incoming records by their business key, such as repayment_id, then use SQL MERGE: insert an unseen key; update an existing key only when the incoming source version is newer. Prefer a source sequence/version with explicit tie-breaking rules; updated_at alone may tie or arrive out of order. Replaying a duplicate repayment must not subtract the amount again. This is a keyed upsert, not a whole-table Python timestamp diff. History requires an explicit append/SCD policy beyond the current-row merge. See [BigQuery MERGE](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/dml-syntax#merge_statement).
- **One serving technology, two responsibilities:** Flink updates customer_exposure; a separately owned profile pipeline updates customer_profile from authoritative customer-service data. Keep independent schemas, versions, freshness markers, writer permissions, and retention policies so balance updates cannot overwrite verification attributes. Both tables can use the same Bigtable service; separate clusters/instances require an isolation, placement, or capacity need. These are derived serving copies, not the authoritative loan ledger or customer system of record. Expired or unavailable data requires an approved fallback or decision hold, not a silent zero balance. A Bigtable application profile controls request routing; it is not a customer-profile record.

**Governance & DevOps**

```text
GOVERNANCE  IAM . CMEK . BigQuery policy tags . row access by market
            tokenized customer identifiers
DEVOPS      Terraform + GitHub Actions (dev / staging / prod variants)
QUALITY     dbt tests . Great Expectations . circuit breaker . Datadog
```
- **CMEK: who controls the encryption key:** CMEK means customer-managed encryption keys. Google Cloud already provides default encryption; CMEK lets your organization control a supported resource’s encryption key through Cloud KMS, including access and lifecycle policies. It does not replace IAM, masking, or tokenization. Disabling a key can disrupt access to dependent data, so ownership and recovery matter. The cloud account organization is the “customer” in this term, not the borrower. See [Cloud KMS CMEK](https://docs.cloud.google.com/kms/docs/cmek).
- **Policy tags versus table and row access:** A BigQuery policy tag governs column access rather than granting access to an entire table. Table/dataset IAM controls access to resources, while a policy tag classifies a column and supports column-level authorization. For example, analysts may read approved loan facts but need an additional grant to read a tagged tax_identifier column. Row access policies separately restrict which market rows they see; masking policies can return a permitted masked representation. A label alone is not a complete access-control configuration. See [BigQuery column-level controls](https://docs.cloud.google.com/bigquery/docs/column-level-security-intro).
- **Why tokenize customer identifiers:** A stable token replaces a direct identifier before general analytical use: customer 12345 becomes an opaque token used consistently in applications and repayments, so joins still work without spreading the original identifier. A protected mapping/tokenization service controls any permitted reversal. This is pseudonymization, not guaranteed anonymization: linked behavior can still identify someone, and tokens remain sensitive. A simple unsalted hash of an email is not an adequate substitute for a designed tokenization scheme. See [Google pseudonymization guidance](https://docs.cloud.google.com/sensitive-data-protection/docs/pseudonymization).

*Accepted practice-design decision (2026-10-29): use Bigtable for both customer exposure and profile serving. This is a hypothetical architecture choice supported by workload fit, not evidence of PayPal’s private implementation or Richard’s employment experience. The [Google financial-serving example](https://cloud.google.com/blog/products/databases/fraud-detection-with-cloud-bigtable?hl=en) illustrates profiles and transaction features in one Bigtable service; it does not establish our workload size or performance.*


### TRACK 1 — BATCH PIPELINE

*Primary story. Lead with the circuit breaker — it’s your most distinctive design.*

### 01   ·  SOURCE SYSTEMS & INGESTION

**Sources:**  BNPL application, decision, disbursement and repayment services (GraphQL and REST); partner feeds from international markets; market configuration.

**APIs:**  PySpark on Dataproc with functional transformation patterns — incremental extracts by updated-since watermark, cursor paging.
- **Functional transformation patterns in PySpark:** Functional transformation patterns can organize raw → curated PySpark processing. “Functional” describes small composable transformations that return a new DataFrame rather than mutating shared application state. For example: parsed → normalize_currency → normalize_timestamps → deduplicate → validate. Keep API calls and writes as explicit I/O boundaries rather than hiding them inside every row transformation. Spark DataFrames are immutable logical plans, and execution is lazy; a clean function chain is an organization technique, not a different ingestion service or a promise of parallel API safety.
- **Incremental extracts based on updated records:** “Incremental extract by updated time” means request records created or changed since the last successfully committed source checkpoint. If a repayment from Monday is corrected on Wednesday, updated_at can bring it into Wednesday’s extract. A created_at-only filter could miss it. Define a bounded extraction interval, allow an overlap if the API supports it, and deduplicate/upsert the overlap. Persist the next checkpoint only after the associated data is safely accepted; an API without change tracking may require another strategy.
- **Extraction watermarks versus pagination cursors:** API cursor paging is like a client app following next_cursor until all pages are fetched. The extraction watermark is a persisted boundary such as last_successful_updated_at. Illustratively, GET /repayments?updated_since=2026-10-27T00:00:00Z&cursor=abc continues one bounded extract. The cursor tracks position within that extract; the watermark tracks progress across runs. Cursor expiry, stable ordering, ties, updates during pagination, and retry behavior depend on the source API. This is different from a Flink event-time watermark, which describes progress for event-time processing and late-event handling.

**Partner feeds:**  Arrive through **Pub/Sub** and **Cloud Storage** landing zones, one per market and partner.

**Market configuration:**  Country rules and feature flags kept as configuration, versioned in Git.
- **Example market configuration in JSON:** Market-specific enablement, publication controls, schema versions, and quality thresholds can be expressed in JSON or YAML. Git stores reviewed versions, and a deployment step publishes a validated runtime copy for jobs to read. The example below contains invented settings, no credentials, and is not an Airflow built-in schema. enabled controls processing policy; a separate allow_publish flag lets an operator hold publication while ingestion continues.
```json
{
  "config_version": 3,
  "markets": {
    "US": {
      "enabled": true,
      "allow_publish": true,
      "schema_contract": "repayments-v2",
      "max_invalid_fraction": 0.01
    },
    "UK": {
      "enabled": true,
      "allow_publish": false,
      "schema_contract": "repayments-v2",
      "max_invalid_fraction": 0.01
    }
  }
}
```

Example interpretation: US processing and publication are enabled; UK ingestion/validation can run while publication is held. `0.01` is an invented 1% threshold, not a compliance rule. Never commit API keys or borrower data to this configuration.


**Credentials:**  Google Secret Manager; service accounts per workload.

### 02   ·  RAW LANDING

**Storage:**  GCS and BigQuery raw tables — data exactly as received.
- **Why use BigQuery raw tables as well as GCS:** GCS can retain immutable original API responses/files cheaply and independently of warehouse schemas. BigQuery raw/staging tables make landed rows directly queryable and can suit database replication, direct ingestion, or SQL-first validation; they are not restricted to SQL-origin data. Loading parsed JSON into typed columns can change representation, so “exactly as received” should refer to the retained object when byte fidelity matters. One design keeps originals in GCS plus a queryable raw/staging copy in BigQuery. Use both only when replay/audit and query needs justify the extra copy and cost. Preserve event time, ingestion time, source key/version, and source-object lineage. GCS has path prefixes rather than SQL partitions; BigQuery partitioning/clustering is a separate physical design.

**Partitioning:**  market / load\_date.

**Audit columns:**  ingested\_at, source, market, api\_version, batch\_run\_id.

Raw is partitioned by market from the start, so a problem in one market can be isolated, quarantined or replayed without touching the others.

### 03   ·  SCHEMA DRIFT CHECK & CIRCUIT BREAKER

**Drift trigger:**  GCS object-finalize → Pub/Sub → **Cloud Function**.
- **How a raw file arrival triggers schema validation:** The schema-validation trigger responds to a source file landing in GCS during raw ingestion, before Raw → Silver. Example: a partner uploads raw/US/repayments/batch-123.csv; successful object finalization emits an event; a configured Eventarc trigger invokes a Cloud Run function, or a configured storage notification publishes to Pub/Sub and a subscriber invokes validation. These are alternative delivery arrangements, not automatic behavior from merely creating a bucket. The event contains object metadata; the handler reads that object, checks the schema, and records a result tied to bucket/object/generation/batch. Deduplicate repeated deliveries. See [Cloud Storage events through Eventarc](https://docs.cloud.google.com/eventarc/docs/standard/direct-events).

**Additive change:**  New field → auto-approved, registry updated, logged.
- **What automatic schema approval actually changes:** Automatically approving an additive schema change means validator code accepts it under an explicitly approved compatibility policy; it does not mean automatically rewriting pipeline code. For example, preserve unknown optional fields in raw JSON, record the observed schema fingerprint, and allow known required fields through curated processing. Record accepted versions with an atomic/version-checked update so simultaneous arrivals do not overwrite each other. Do not let arbitrary new fields automatically acquire approved business meaning or downstream access. Exposing a new column to SQL models can still require a schema migration, tests, and a code review. A generic pass-through pipeline may tolerate additions without a code change; it is not automatically generating new business transformations. Registry product/implementation remains a design choice here.

**Breaking change:**  Missing or retyped field → quarantine that market’s batch, alert.

**Circuit breaker:**  After drift and quality checks, each market gets a status. If thresholds are breached (volume drop, null spike, failed contract), the breaker opens for that market; Airflow sensors keep downstream tasks for that market from running until it closes.

**Kill switch:**  A feature flag lets the team stop a market’s pipeline instantly, without a deploy.
- **How operators flip a pipeline kill switch:** A pipeline kill switch works similarly to a mobile feature flag: an operator changes a setting through an authorized UI/API/CLI, and workers read a versioned runtime configuration. The companion exercise uses Airflow Variables; a production design might use a configuration table/service. Record who changed which market/stage, when, why, and the old/new version; require appropriate authorization. Git can own reviewed defaults while a separate audited override handles incidents. A check before publication blocks the next publish; it does not cancel a running task instantly. Streaming consumers need their own policy checks and freshness handling.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How do you stop bad data from spreading downstream?”*
>
> **Say:** “I built a circuit breaker. Every market’s batch passes schema and quality checks; if it breaches a threshold — a volume drop, a null spike, a broken contract — the breaker opens for that market only. Airflow sensors hold every downstream task for that market until it closes, so risk datasets keep yesterday’s good data instead of today’s bad data. A kill switch, driven by a feature flag, lets us stop a market immediately without deploying anything.”
>
> **Then link to schema drift:** “Schema changes are one input to the breaker: additive changes pass; breaking ones open it.”

### 04   ·  CURATED LAYER — TRANSFORMATION & ERROR SEMANTICS

**Engine:**  PySpark on Dataproc and BigQuery SQL.

Transform categories:

- **Standardization** — amounts to fixed-precision decimals with currency code; timestamps to UTC with market time zone kept.

- **Lifecycle assembly** — application → decision → disbursement → installments → repayments, linked by application and loan IDs.
  - **Lifecycle assembly: joining the BNPL business journey:** Lifecycle assembly connects records for the same application/loan journey; the lifecycle is the financial product’s journey, rather than a pipeline task’s execution. Application APP1 receives decision DEC1, creates loan LOAN1, schedules installments I1–I4, and receives posted repayments R1 and R2. Join/resolve those identifiers while preserving their different grains. An application retry is not another loan, and a one-to-many repayment join must not duplicate the financed amount. Late-arriving records and failed/disapproved applications need explicit handling; not every application reaches every stage.

- **Delinquency** — days past due and delinquency bucket per installment and loan.
  - **Delinquency means overdue borrower payments:** Delinquency describes a borrower’s overdue payment, not slow pipeline data. If an installment of USD 100 was due October 1 and USD 40 remains unpaid at the October 10 business cutoff, a simplified rule may classify it as nine days past due. Grace periods, partial-payment allocation, reversals, market calendars, and bucket definitions require an agreed product policy. Pipeline lateness is a different concern: a missing posted repayment could incorrectly make the customer appear delinquent.

- **Deduplication** — latest version per event key.
  - **Deduplication versus preserving old versions:** Remove duplicates or superseded versions from the current analytical projection, not automatically from raw history. A repeated event_id/source_version is one business event, so count it once. A genuine correction with a newer source version can replace the current row while an append-only change log or SCD structure preserves prior values as required. Do not deduplicate distinct repayments merely because their customer, amount, and timestamp happen to match.

**Error semantics:**  
- **Retry** for transient failures (API timeouts); 
- **quarantine** for bad records; 
- **partial load** when some markets pass and others don’t; 
- **full failure** only when shared data is unusable.

*“Before the refactor, one bad partner file failed the whole run. After it, that market was quarantined and every other market published on time.”*

### 05   ·  SEMANTIC LAYER — DBT, BIGQUERY & ICEBERG

**Tool:**  dbt models on BigQuery.

**Marts:**  application funnel, approvals, disbursements, repayment performance, delinquency roll rates.

**Iceberg:**  Curated datasets published as **Apache Iceberg tables through BigLake** — shared by Spark on Dataproc and BigQuery, with snapshot time travel.

**Tuning:**  Partitioning and clustering strategy tuned with query plans and INFORMATION\_SCHEMA job statistics.
- **Using execution metrics to tune expensive pipeline stages:** Pipeline and query execution metrics help identify expensive stages, including skew and hot keys; inspect the relevant engine’s evidence. BigQuery query plans and INFORMATION_SCHEMA.JOBS expose bytes processed, slot time, stages, and symptoms such as skewed joins or excessive shuffle; partition filters and clustering can reduce scanned data. Dataproc/Spark job and stage metrics reveal skewed tasks, spill, shuffle, and executor pressure. A hot key is a join/grouping/partition key with unusually much work, not simply a frequently read column. Measure correctness and cost/runtime before and after each change. See [BigQuery compute optimization](https://docs.cloud.google.com/bigquery/docs/best-practices-performance-compute).

**Macros:**  generate\_surrogate\_key, safe\_divide (approval rate, roll rate), date\_spine.

### 06   ·  ORCHESTRATION

**Scheduler:**  **Cloud Composer** (managed Airflow).

**Config-driven enablement:**  Which markets and stages run is read from configuration, so a change can be enabled in one market for a controlled rollout or experiment.

**Environments:**  Dev, staging and production variants built with Terraform and GitHub Actions, with market-specific behavior.

**Per-market DAG (generated from config)**

```text
CONFIG       read enabled markets + feature flags (kill switch)
   v
MAPPED       per-market ingest (APIs + partner landing zones)
   v
SENSOR       circuit breaker CLOSED for this market?  (else wait / skip)
   v
MAPPED       curated transforms (retry / quarantine / partial-load)
   v
SEQUENTIAL   dbt build + tests -> Iceberg publish -> Datadog metrics
```

> **🎯 COACH’S CUE**
>
> **When they ask:** *“What does Composer do that Dataproc and BigQuery don’t?”*
>
> **Say:** “Dataproc and BigQuery do the work. Composer decides what runs: it reads which markets are enabled, waits on each market’s circuit breaker with sensors, runs the curated and dbt steps only for healthy markets, and applies the right retry or failure behavior per stage. Turning a market on or off is a config change, not a code change.”

### 07   ·  WAREHOUSE & DIMENSIONAL MODEL

| **Table** | **Type** | **Grain** | **Notes** |
| --- | --- | --- | --- |
| fact\_bnpl\_application | Accumulating snapshot | one application | submitted, decided, disbursed; decision; amount |
| fact\_installment | Transactional | loan × installment | due date, amount due, paid, days past due |
| fact\_repayment | Transactional | one repayment | amount, method, status |
| fact\_loan\_daily | Periodic snapshot | loan × day | outstanding balance, delinquency bucket |
| dim\_customer | SCD Type 2 | customer version | risk tier, market, verification status |
| dim\_product / dim\_market / dim\_merchant / dim\_date | SCD Type 1 / static | one row per member | Pay in 4, Pay Monthly; market rules |

**Why SCD Type 2 on dim\_customer:** a customer’s risk tier and verification status change. Approval and delinquency analysis must use the tier the customer had at application time — otherwise approval rates by tier shift every time customers are re-scored.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How do you handle slowly changing dimensions?”*
>
> **Say:** “For BNPL, the history that matters is the customer’s risk tier at the time of the decision. dim\_customer is Type 2 — a new row when tier or verification status changes, with effective dates — and every application carries the key of the version in effect when it was submitted. That way approval rates and delinquency by tier stay stable when customers are re-scored later.”

### 08   ·  DATA QUALITY FRAMEWORK

**Great Expectations:**  Per-market checks: volume vs. trailing baseline, required fields, amounts positive, decision values in the allowed set, every disbursement linked to an approved application.
- **Choosing Great Expectations versus dbt tests:** Choose between Great Expectations and dbt tests based on where validation runs and which workflow owns the data. dbt data tests are SQL assertions attached to warehouse models: not_null on application_id, relationships from disbursements to applications, or custom SQL checking installment totals. Great Expectations (GX) organizes expectation suites, validations, results, and actions across supported data backends; it can validate a landed batch or Spark/SQL dataset before publication. GX is not limited to raw data, and dbt can test staging/raw relations. There is no universal requirement to deploy both. Prefer dbt tests when the workflow already lives in dbt/SQL; add GX when pre-warehouse validation or its reusable validation/reporting workflow earns the extra dependency. Avoid duplicating every rule in both systems; assign each rule an owner, stage, and failure action. Neither tool alone supplies the full operational circuit breaker. See [dbt data tests](https://docs.getdbt.com/docs/build/data-tests) and [GX Checkpoints and Actions](https://docs.greatexpectations.io/docs/core/trigger_actions_based_on_results/create_a_checkpoint_with_actions/).

**dbt tests:**  Keys, relationships, accepted values; custom rules (sum of installments = financed amount; paid ≤ due).

**Thresholds:**  Check results feed the circuit breaker — quality is enforced, not just reported.

**Debugging:**  BigQuery query plans, INFORMATION\_SCHEMA and Dataproc job history for staging validation and issue resolution.

### 09   ·  SECURITY & GOVERNANCE

- **Consumer credit regulation** — Pay Monthly is closed-end credit under Truth in Lending (Regulation Z); application decisions fall under ECOA/Regulation B; credit data under FCRA; customer financial data under GLBA. International markets follow local rules.
  - **Credit laws, implementing regulations, and regulators:** TILA, ECOA, FCRA, and GLBA name laws; Regulation Z and Regulation B are implementing regulations. They are not regulatory bodies. TILA/Regulation Z concerns consumer-credit disclosures; ECOA/Regulation B concerns equal credit opportunity and related application requirements; FCRA concerns consumer-report information; GLBA concerns financial-information privacy/security. CFPB and FTC are examples of authorities; which requirements apply depends on product structure, lender, activity, jurisdiction, and current rules. Do not treat the sentence above as a verified legal classification of a PayPal product. The engineering lesson is to implement approved access, retention, decision-lineage, and reproducibility requirements supplied by legal/compliance, rather than decide legal applicability yourself. See [Regulation Z](https://www.consumerfinance.gov/rules-policy/regulations/1026/), [Regulation B](https://www.consumerfinance.gov/rules-policy/regulations/1002/), and [FTC GLBA guidance](https://www.ftc.gov/business-guidance/privacy-security/gramm-leach-bliley-act).

- **Data protection** — customer identifiers tokenized; sensitive columns behind BigQuery policy tags.
  - **Masking versus tokenization:** Sensitive-column masking can complement customer-identifier tokenization when a reader needs a restricted representation. Tokenization replaces an identifier with a stable joinable surrogate; dynamic masking changes what a particular reader sees, such as a redacted email or NULL. Authorized operational users may see the original while analysts see the masked representation. Column authorization, row restrictions, and encryption solve other parts of the problem. Masking does not necessarily remove the underlying original value. See [BigQuery data masking](https://docs.cloud.google.com/bigquery/docs/column-data-masking-intro).
  - **Sensitive measurements that still need protection:** Tokenizing customer_id does not protect every sensitive field: income, loan balance, delinquency status, risk score, date of birth, precise location, decision reasons, and free-text support notes can still expose private information. An analyst may need a numeric income or balance for approved analysis, so replacing it with an opaque identifier would destroy the measurement. Instead minimize precision, restrict access, mask where appropriate, and constrain retention. Even with tokenized customer_id, combinations of attributes can re-identify someone; tokenization alone does not make the dataset public or harmless.

- **Market isolation** — row access policies so market teams see only their markets.

- **Encryption and access** — CMEK, least-privilege service accounts, audit logs.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How do you protect consumer credit data across markets?”*
>
> **Say:** “Customer identifiers are tokenized before curated layers, sensitive columns sit behind BigQuery policy tags, and row access policies keep each market team to its own data. Because application decisions fall under fair-lending rules, I make sure decision data is complete and reproducible — Iceberg snapshots let us show exactly what a dataset looked like on any date.”

### 10   ·  LAST MILE — REACHING CONSUMERS

- **Risk and credit teams** — approval, repayment and delinquency datasets.

- **Product** — application funnel and conversion by market.

- **Market partners** — partner-driven feeds across international markets.

- **Analysts** — Looker on BigQuery; Spark users read the same Iceberg tables.

### Batch Narrative
“One project I worked on focused on making our BNPL batch pipelines more reliable, particularly when partner feeds arrived with missing fields, duplicate records, or unexpected changes.
 
A duplicate repayment could make a customer’s outstanding balance look lower than it really was, while a missing repayment could make them appear overdue. The existing error handling also meant that one malformed partner file could hold up otherwise valid data from other markets.
 
My responsibility was to strengthen validation and error handling so we could hold back unreliable data without unnecessarily blocking healthy markets.
 
As API responses and partner files landed, we preserved the originals, checked their schemas, and validated the transformed records before publishing them to BigQuery. I checked for things like missing loan IDs, duplicate repayments, and totals that didn’t match the source. If a batch failed those checks, we held it for investigation.
 
I separated temporary failures from bad data: an API timeout could be retried, while a malformed file was quarantined. When markets were independent, a problem in one didn’t have to stop the others.
 
I also added controls by market so quality failures could block publication automatically, and an operator could pause a market during an incident without deploying new code. Airflow running in Cloud Composer coordinated those checks and read the market configuration before publication, so only approved batches moved downstream.
 
The goal was to give risk and product teams dependable datasets, with clear visibility into which markets were current and which were waiting on a correction.”

### TRACK 2 — STREAMING PIPELINE

*Supplementary. Your role here was consistency between the real-time and batch paths.*
- **Why maintain both batch and streaming paths:** A batch/stream split can separate different latency and completeness needs. Streaming serves urgent operational needs such as current exposure during an application; batch can incorporate partner files, corrections, and broader history for reconciliation and analytics. They may share events and business rules but produce different outputs. Streaming-only is possible when it meets all latency, correction, replay, and analytical needs; two paths are not mandatory. In this proposed split, freshness and fast point reads justify the stream, while batch provides repeatable backfills and reconciled views. Prevent duplicated logic from drifting through shared contracts, fixtures, and comparisons at the same cutoff.

#### STAR — Trustworthy BNPL Exposure for Streaming Consumers

*Hypothetical first-person practice narrative. Keep ownership focused on reviewing and aligning streaming and batch logic; the wider Kafka/Flink/Bigtable platform is team context. The results below describe intended outcomes, not measured PayPal results. No production throughput, latency, or financial-impact figures have been supplied.*

##### S · Situation

The batch platform produced reconciled BNPL history, but a new application could arrive after a customer had taken another loan or made a repayment. Waiting for the next batch would leave the decisioning service with an outdated view of that customer's outstanding obligations. A separate Kafka → Flink → Bigtable path maintained current exposure for fast lookups, while events also reached Cloud Storage and BigQuery for history and reconciliation.

The challenge was trust: the stream could be fast and still disagree with batch because of duplicate events, late repayments, reversals, different currency rules, or inconsistent definitions of outstanding balance. My focus was making those two paths tell the same financial story.
- **Why the same events can yield different stream and batch results:** Batch and streaming can begin with the same application, disbursement, and repayment events yet produce different balances because of processing rules or input timing. A repayment at 10:00 updates the stream immediately, while a batch cut at 09:00 still excludes it. A duplicate event may be counted twice in one path, or a later reversal/partner correction may reach only one path initially. They need not physically rejoin into a single table: reconcile customer/loan/currency balances at the same source cutoff, classify timing gaps versus defects, and apply an explicit correction process. Never add a stream balance to a batch balance: they may represent the same obligation twice.

##### T · Task

I was responsible for reviewing the streaming and batch calculations, agreeing on shared business definitions with the owning teams, and defining checks that distinguish an expected timing difference from a genuine data defect. The goal was fresh, dependable exposure data for decisioning while preserving reproducible history for risk and analytics.

##### A · Action — Applying the Five Vs

- **Volume — how much data and state the system must handle.**
  - I reviewed the design against daily event counts, peak events per second, active customers and loans, retained history, and Flink state size. Daily totals alone can hide bursts or a small number of unusually busy customer keys.
  - I worked with the streaming owners to review customer-key partitioning, processing parallelism, state retention, and backpressure. The question was whether the pipeline could keep up and recover after an outage without creating incorrect balances. These are capacity considerations; no specific PayPal workload size is established here.

- **Velocity — how quickly events arrive and become useful.**
  - I separated event freshness from lookup speed: how long after a repayment occurs does the updated exposure become available, and how quickly can the decisioning service retrieve it? A fast Bigtable read can still return stale data if the stream is behind.
  - I reviewed event timestamps, late-event handling, consumer lag, and recovery behavior. With the consuming team, I defined how to recognize stale exposure and when to use an approved fallback or hold a decision rather than silently trust an old value. A daily reconciliation detects longer-lived discrepancies; freshness needs continuous monitoring.

- **Variety — the different events and business meanings.**
  - I mapped application, disbursement, repayment, and reversal events into an agreed contract containing an event ID, tokenized customer ID, loan ID where applicable, market, currency, business timestamp, and schema version.
  - I checked that both paths applied the same financial rules. An application is a request for credit, not money already disbursed; a repayment attempt is not necessarily a posted repayment. Refunds, reversals, and fees require explicitly agreed treatment. Balances stay separate by currency unless an approved conversion rule is applied.

- **Veracity — whether the data and calculation can be trusted.**
  - I reviewed duplicate handling by business event ID, required-field and amount checks, and how out-of-order events affect state. Kafka's partition order does not establish business-time order across separate application and repayment topics.
  - I reviewed recovery and sink writes: checkpoints protect recoverable Flink state, while external writes also need replay-safe behavior and protection against older updates overwriting newer exposure. Checkpointing alone does not establish end-to-end exactly-once behavior.
  - I defined reconciliation at the same customer/loan/currency grain and the same input cutoff, allowing an agreed period for late events. Differences were classified as timing gaps, missing or duplicate events, or calculation defects, with an owner and a correction/replay path. A comparison to today's live state would be misleading if batch only included yesterday's events.

- **Value — what the business gains from the data.**
  - I connected the technical checks to the decisioning use case: missing a new disbursement can understate existing exposure, while missing a repayment can overstate it. Either can distort the next credit assessment.
  - I kept the streaming view focused on current exposure for operational use and the batch view focused on reconciled history and analysis. The pipeline supplies an input to credit decisions; credit policy and the decisioning service determine the lending outcome.

##### R · Result

*Suggested qualitative result language for this practice scenario; replace it with observed outcomes if evidence becomes available.*

- **Fresher exposure for operational use:** Decisioning could use the current exposure view rather than waiting for the next scheduled batch, subject to an explicit freshness check.
- **Consistent financial definitions:** Streaming and batch applied the same rules for posted repayments, disbursements, reversals, and currencies, with understandable timing differences separated from defects.
- **Recoverable, explainable discrepancies:** Event identities, retained history, and reconciliation made it possible to trace and correct a mismatch instead of treating every difference as an unexplained balance error.
- **Evidence to collect:** Peak sustained event rate and backlog recovery time for Volume; p95/p99 event-to-serving latency and lookup latency for Velocity; supported event/schema families for Variety; duplicate, rejection, and reconciliation mismatch rates for Veracity; stale-exposure incidents and decisioning-team acceptance for Value. Claims of fewer defaults, higher approvals, or lower losses require separate business evidence.

##### Small Example to Explain Veracity and Value

A customer has a USD 1,000 disbursement and a posted USD 200 repayment, so the simplified outstanding principal is USD 800. If the same repayment event is counted twice, the stream incorrectly reports USD 600. If it is missing, the stream reports USD 1,000. Deduplication and completeness checks address different defects; comparing both paths at the same source cutoff helps expose either one. This example excludes fees, refunds, interest, and other product-specific adjustments.

##### Spoken Version — About 90 Seconds

“My work on the BNPL streaming pipeline focused on making sure its exposure calculations were both current and consistent with our batch results.

A customer could take out a loan or make a repayment between batch runs, so the next credit decision needed a fresher view of their outstanding balance.

Kafka carried the loan and repayment events, Flink calculated the updated exposure, and Bigtable made it available for fast lookups. I reviewed the streaming and batch logic to make sure both applied the same financial rules.

For example, a repayment should reduce exposure only once and only after it posts. I checked how both paths handled duplicates, late events, and reversals so those situations wouldn’t produce different balances.

I also reviewed whether the pipeline could keep up during busy periods and catch up after an outage, because a fast lookup isn’t useful if the balance behind it is stale.

To check the results, I compared streaming and batch balances for the same customer, loan, and currency at the same cutoff, so we could distinguish expected timing differences from actual defects.

The goal was to give credit decisioning a current, dependable exposure figure, backed by reconciled history and a clear way to investigate discrepancies.”

#### Why Streaming Earns Its Place

*“Batch produces the reconciled BNPL history. Separately — because credit decisions need a customer’s current open BNPL exposure at the moment they apply — a Kafka and Flink path keeps that exposure current. My job was making sure the real-time logic and the batch logic produce the same numbers.”*

#### Streaming Architecture

```text
loan / repayment / reversal events -> Kafka (key = customer token)
                                      |
                         +------------+--------------+
                         v                           v
                 Flink keyed state          retained-event archive
                         |                           |
                         v                           v
              Bigtable: customer_exposure      GCS -> BigQuery
                         |                      batch balances
                         |                           |
                         +---- reconciliation -------+

profile-owning pipeline -> Bigtable: customer_profile

backend decisioning service -> reads required Bigtable rows
```
- **GCP alternatives to AWS MSK and Kinesis:** AWS MSK stands for Managed Streaming for Apache Kafka. Google Cloud’s comparable managed Kafka offering is Managed Service for Apache Kafka. Pub/Sub supplies managed messaging with different APIs and delivery/ordering semantics; it is a functional comparison to Kinesis for some workloads, not a drop-in replacement. Flink processes streams; Kafka/Pub/Sub transport and retain messages. Google Dataflow is a managed Apache Beam processing service for streaming and batch, not a synonym for Kafka or a hosted Flink runtime. Service selection depends on client compatibility, ordering, retention, replay, operations, and processing needs. See [Google’s Pub/Sub versus managed Kafka comparison](https://docs.cloud.google.com/pubsub/docs/choose-pubsub-kafka).
- **Applying kill switches and circuit breakers to streaming:** Batch and streaming kill switches/circuit breakers should enforce a coordinated policy in this hypothetical design, but an Airflow batch sensor does not stop an already-running Flink job. Stream operators or the serving service must receive/check control changes explicitly. Distinguish pause consumption, quarantine one market, hold sink publication, and deny use of stale exposure: those have different consequences. Preserve/replay offsets and state where supported; continuing to ingest while holding publication can be safer than dropping events. Keep per-market isolation, audit, bounded propagation, and an approved fallback. A disabled market must not silently keep serving old balances as current.

#### Kafka & Flink

**Keys:**  customer\_id — a consistent partitioning strategy keeps a customer’s records together within each topic partition. Separate topics do not provide a shared total order; review business timestamps and source sequencing when combining them.

**State:**  Open balance per loan and total exposure per customer in Flink keyed state.
- **What Flink keyed state remembers:** State is the information a running processor remembers between events, not a geographic state. After a USD 1,000 disbursement, Flink remembers the loan/customer balance; after a posted USD 200 repayment, it updates that balance to USD 800. With keyBy(customer_token), keyed state is scoped to that key and managed by Flink’s state backend. Checkpoints capture recoverable state together with source progress; this is different from the externally served Bigtable record. Retention/TTL must not discard still-needed loan or deduplication state. See [Flink stateful processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/stateful-stream-processing/).

**Recovery guarantees:** Flink checkpoints support recoverable state. Bigtable sink writes must retain stable versions/timestamps across retries and prevent older updates from replacing newer exposure. A customer key alone is not event deduplication. End-to-end guarantees depend on the source, processing, connector, and recovery integration and are not established by this unexecuted practice design.

**Consistency:**  A daily job compares stream-derived exposure with batch-derived balances; differences are investigated as defects in one path or the other.

#### Operational Serving — Bigtable

**Purpose:** Serve current derived exposure and selected customer attributes by key for backend decisioning. Bigtable is the one serving technology for both tables; BigQuery retains reconciled analytical history. Neither serving table replaces the authoritative operational ledger/customer service.

| Table | Illustrative row key | Selected columns | Writer |
| --- | --- | --- | --- |
| customer_exposure | hash_prefix#market#customer_token#currency | exposure:balance_minor, exposure:open_loans, meta:state_version, meta:event_cutoff, meta:computed_at, meta:rule_version | Flink exposure pipeline |
| customer_profile | hash_prefix#market#customer_token | profile:verification_status, profile:risk_tier, meta:profile_version, meta:updated_at | Profile-owning pipeline |

**Schema meaning:** Bigtable has rows, column families, and column qualifiers—not “bins.” exposure, profile, and meta are illustrative families. Store money as explicitly encoded integer minor units plus currency; applications must agree on the encoding and currency’s minor-unit scale. The deterministic hash prefix spreads keys for point lookups; its benefit and effects on scans require workload testing. Keep direct personal identifiers out of row keys. See [schema design](https://docs.cloud.google.com/bigtable/docs/schema-design).

**Write ownership and replay:** Flink writes the calculated exposure snapshot with a deterministic version per output key, not an unguarded “subtract repayment again” increment. Specify how that version maps to Bigtable cell timestamps or a conditional update. Retries must reuse the same version, and older writes must not replace the latest accepted state. Restore/rebuild must preserve or advance the version contract. Profile updates have their own writer/version in a separate table. Two independent row reads do not provide an atomic snapshot across exposure and profile tables; a requirement for an indivisible combined decision record would need a different materialization/transaction design.

**Connector boundary:** Google documents a Flink Bigtable sink. Choose and test a compatible connector/Flink version; provision required column families before running it. Its idempotent-write semantics depend on stable row/cell identity and timestamps, and the source/checkpoint pipeline must meet its own requirements. A connector alone does not protect every business calculation or guarantee correctly ordered updates. See [Flink connector](https://docs.cloud.google.com/bigtable/docs/flink-connector).

**Routing and freshness:** For this initial practice design, use an explicit single-cluster routing policy for serving reads/writes, with the consistency/failover tradeoff documented. Do not assume any multi-cluster policy has identical read-your-writes or single-row transaction behavior. Independently validate event cutoff, computed_at, profile age, and market publication controls before using the data. A strongly consistent database read can still return a stream-derived balance that is stale because ingestion is behind. See [routing](https://docs.cloud.google.com/bigtable/docs/routing).

**Access and operations:** Backend services use least-privilege identities; clients do not directly modify balances or verification attributes. BigQuery policy tags and row policies do not secure Bigtable tables—configure Bigtable access separately. Monitor p95/p99 reads, event-to-serving lag, hot keys, write errors, backlog recovery, and reconciliation differences. Establish capacity and cost from workload tests; no throughput or latency benchmark has been measured for this practice architecture.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“Why use Bigtable rather than read exposure from BigQuery?”*
>
> **Say:** “The decisioning service needs keyed access to a customer’s current exposure and profile attributes, so I would use Bigtable for those derived serving records and BigQuery for historical analysis and reconciliation. Flink updates exposure, while the profile pipeline owns profile updates. I would validate freshness, prevent stale replay writes, and measure lookup latency rather than assume a performance number. Reconciliation compares both balance calculations at the same source cutoff.”

#### How Batch and Streaming Meet

A configured archive path retains the agreed original event stream in GCS, which batch loads into BigQuery. Flink separately publishes calculated exposure to Bigtable. Reconciliation compares derived balances at the same grain, cutoff, and rule version; BigQuery Gold is reconciled analytical history, while the operational loan ledger remains authoritative for financial obligations.
- **Reconciliation compares derived balances, not raw bytes:** Stream/batch reconciliation compares Flink-derived exposure with independently computed batch-derived balances, not transformed output directly with raw bytes. Retain original events in GCS (via a configured sink/archive path); Flink computes current exposure; batch applies the agreed financial rules to retained events and authoritative corrections to compute a reconciled balance. Compare both outputs at the same customer/loan/currency grain, source cutoff, and rule version. Raw records provide evidence to investigate a difference. Archiving only an already-aggregated stream result would weaken the ability to rebuild it independently.

#### Sample Datasets

`fact_bnpl_application  (accumulating snapshot)`

| **application** | **market** | **product** | **amount** | **ccy** | **decision** | **disbursed** | **customer tier** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| APP-26-0911-4417 | US | PAY IN 4 | 240.00 | USD | APPROVED | 2026-09-11 | B |
| APP-26-0911-4420 | US | PAY MONTHLY | 1,180.00 | USD | APPROVED | 2026-09-11 | A |
| APP-26-0911-4433 | US | PAY IN 4 | 410.00 | USD | DECLINED | — | D |
| APP-26-0912-0108 | AU | PAY IN 4 | 300.00 | AUD | APPROVED | 2026-09-12 | B |
| APP-26-0912-0215 | DE | PAY IN 4 | 199.00 | EUR | PENDING | — | C |

*Markets and products are illustrative; customer tiers are internal risk tiers.*

`dim_customer  (SCD Type 2)`

| **cust\_sk** | **customer** | **market** | **risk tier** | **verified** | **eff start** | **eff end** | **current** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 7710442 | cus\_tk\_91a0 | US | C | Y | 2025-04-02 | 2026-06-30 | N |
| 7788120 | cus\_tk\_91a0 | US | B | Y | 2026-07-01 | 9999-12-31 | Y |
| 7710587 | cus\_tk\_33f2 | US | A | Y | 2024-09-18 | 9999-12-31 | Y |
| 7710913 | cus\_tk\_08bd | AU | B | Y | 2025-11-05 | 9999-12-31 | Y |

*cus\_tk\_91a0 moved from tier C to B on 2026-07-01. June applications still analyze under tier C.*

`Streaming BNPL event (Kafka: bnpl.repayments)`

| **Field** | **Type** | **Example** |
| --- | --- | --- |
| event\_id | string | bnpl-20260911-3e8a01 |
| customer\_id | string | cus\_tk\_33f2 (tokenized) |
| loan\_id | string | LN-26-0911-4420 |
| event\_type | string | REPAYMENT (DISBURSEMENT / REPAYMENT / REVERSAL / LATE\_FEE) |
| amount / currency | decimal / string | 98.33 / USD |
| installment\_no | integer | 2 |
| market | string | US |
| event\_ts | timestamp | 2026-10-11T15:02:44.880Z |
| schema\_version | integer | 6 |

#### Likely Follow-Ups — One-Line Answers

- **When does the breaker close again?** When the market’s next batch passes all checks, or when an engineer approves a manual override after review.

- **Partial load vs. full failure?** Partial when markets are independent; full failure only when shared reference data is broken, since every market depends on it.

- **How do you debug BigQuery cost or slowness?** Query plans for stage-level bytes and slot time; INFORMATION\_SCHEMA.JOBS for the heaviest recurring queries; then fix partition and cluster filters.

- **How did you keep stream and batch consistent?** Shared business definitions, code review of both paths, and a daily comparison job.



# **Case Study 2 of 3**

## Neiman Marcus — Governed Snowflake Estate for Luxury Retail

Lead Data Engineer  ·  Neiman Marcus, Dallas, TX  ·  Snowflake on AWS (S3, Glue, Lambda) + Fivetran, Kafka  ·  Luxury Retail — Clienteling, Merchandising & Fulfillment  ·  Oct 2023 – Feb 2026

#### Your 30-Second Opener

*“At Neiman Marcus I led the data engineering team behind a governed Snowflake estate that unified customer, clienteling, merchandising and fulfillment data. I introduced dbt, built the shared transformation layer, secured payment and customer data with tokenization and masking, and cut critical pipeline runtimes by 25%. Let me walk you through the batch platform.”*

### S   ·  SITUATION

Neiman Marcus is a luxury retailer where much of the business runs through personal relationships: sales associates “clientele” their customers, and the InCircle loyalty program rewards top clients. That means customer, purchase, inventory and fulfillment data need to come together accurately — an associate needs to know a client’s history and whether an item is available.

The pain: transformation logic was scattered SQL with no version control or tests, so the same metric was defined differently across Tableau and Power BI. Payment and customer data needed stronger protection inside the warehouse. Critical pipelines ran long and dashboards were slow. Snowflake compute spend grew because batch and interactive workloads shared warehouses. Inventory and order-tracking feeds arrived late, limiting visibility across stores and online.

The people who felt it: merchandising, marketing and clienteling teams, supply chain and fulfillment, finance, and BI users across Tableau and Power BI.

### T   ·  TASK

As Lead Data Engineer, I owned the ingestion, modeling and security architecture on Snowflake: the medallion and dimensional design, dbt adoption, the shared transformation layer as dbt macros and PySpark libraries, Gold marts and the semantic layer, payment and PII protection, real-time inventory and order feeds, performance and cost optimization, the testing framework and GitLab CI/CD, and leading and mentoring a team of four engineers.

### A   ·  ACTION

- Designed a **modular medallion and dimensional architecture on Snowflake**, so ingestion, transformation and serving can evolve independently.

- Ingested sources with **Fivetran (CDC), AWS Lambda APIs, Kafka and Snowpipe Streaming**, landing files in **S3** with a **Lambda schema-drift check**.

- **Pioneered dbt** for documented, version-controlled models aligned with Neiman Marcus business definitions.

- Built the **shared transformation layer** as reusable **dbt macros and PySpark libraries** across merchandising, marketing and supply chain.

- Delivered **Gold marts** integrated with a **shared semantic layer** for consistent metrics in Tableau and Power BI, including an SCD Type 2 client dimension.

- Protected cardholder and customer data with **tokenization, Snowflake masking policies and RBAC**.

- Cut runtimes **25%** with profiling, **clustering keys and result caching**; reduced compute with **warehouse right-sizing, auto-suspend and workload isolation**.

- Built a **testing framework** (dbt tests, Great Expectations) and **GitLab CI/CD** for dbt projects and Airflow DAGs; led a **team of four**.

### R   ·  RESULT

- **Critical pipeline runtimes cut by 25%**, with noticeably more responsive Tableau dashboards.

- **Snowflake compute spend reduced** through right-sizing, auto-suspend and workload isolation — about 20%† (confirm the figure).

- **One definition per metric** across Tableau and Power BI through the shared semantic layer.

- **Faster release cadence** after GitLab CI/CD for dbt and Airflow.

- **Cardholder and customer PII protected** with tokenization, masking and RBAC.

- **A team of four engineers** raised to shared SQL and PySpark standards through reviews and mentoring.

*The 25% runtime cut, faster releases and team of four come from the resume. The cost figure is a suggestion (†) — the resume says spend was reduced without a number.*

### ◆   ·  ARCHITECTURE AT A GLANCE

**Batch lane (primary)**

```text
SOURCES
  order & payment systems (CDC)  .  POS & e-commerce  .  clienteling app
  InCircle loyalty  .  merchandising & inventory  .  fulfillment & carriers
     |  [Fivetran CDC]  [AWS Lambda API pulls -> S3]  [Glue jobs]
     v
BRONZE  - S3 landing + Snowflake RAW (external stage / Snowpipe)
     |  [EventBridge "Object Created" -> Lambda schema-drift check]
     v
SILVER  - Snowflake + dbt (shared macros) / PySpark libraries
     |  tokenize . conform . dedupe . identity resolution
     |  [dbt: staging -> intermediate -> marts]
     v
GOLD    - Snowflake marts + shared semantic layer
     v
CONSUMERS  merchandising . marketing . clienteling . supply chain
           finance . Tableau & Power BI
 
ORCHESTRATION  Apache Airflow   .   CI/CD: GitLab CI   .   IaC: Terraform
```

**Streaming lane (separate — supplementary)**

```text
inventory movements . order status . localized content
     v
Apache Kafka  (key = sku|location / order_id)
     +----------------------------------+-------------------------------+
     v                                  v                               v
Snowpipe Streaming -> Snowflake  Lambda consumer -> DynamoDB    order-tracking
(rows queryable in seconds)        (hot path: availability by      services
                                    SKU & location, <10 ms)
```

**Governance & DevOps**

```text
SECURITY    tokenization . Snowflake masking policies . RBAC . PCI DSS
PRIVACY     CCPA/CPRA requests . PII restricted roles
DEVOPS      GitLab CI (dbt + Airflow) . Terraform . Docker
QUALITY     dbt tests . Great Expectations . testing framework
```

*Assumption to confirm: the resume names Kafka and Snowpipe Streaming for real-time inventory but not a key-value store. DynamoDB for SKU-by-location availability is a framing; name the actual store if it differed.*

### TRACK 1 — BATCH PIPELINE

*Primary story. Lead with dbt adoption and the shared transformation layer.*

### 01   ·  SOURCE SYSTEMS & INGESTION

**Sources:**  Order and payment systems, POS and e-commerce, clienteling app, InCircle loyalty, merchandising and inventory, fulfillment and carrier data.

**Database CDC:**  **Fivetran** for change data capture from operational databases into Snowflake.

**APIs:**  **AWS Lambda** functions pull partner and service APIs into S3; **AWS Glue** for heavier file processing.

**Events:**  **Kafka** and **Snowpipe Streaming** for real-time inventory and order tracking (Track 2).

**Credentials:**  AWS Secrets Manager; Snowflake key-pair authentication for service users.

### 02   ·  BRONZE — RAW LANDING

**Storage:**  S3 landing plus Snowflake RAW schema (external stages and Snowpipe for files; Fivetran-managed tables for CDC).

**Audit columns:**  loaded\_at, source\_system, source\_file, \_fivetran\_synced, \_fivetran\_deleted.

Card data is tokenized before it reaches Snowflake; raw tables never hold a card number.

### 03   ·  SCHEMA DRIFT CHECK (POST-BRONZE)

**File sources:**  EventBridge on S3 “Object Created” → **AWS Lambda** compares landed files to the registered schema.

**Fivetran sources:**  Fivetran propagates source schema changes; a dbt source-freshness and schema test run flags new or changed columns before staging models use them.

**Additive change:**  New column → allowed; staging models select columns explicitly, so nothing breaks.

**Breaking change:**  Dropped or retyped column → quarantine (files) or failed staging test (CDC), alert; that source’s models are skipped.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How do you handle unexpected schema changes?”*
>
> **Say:** “Two paths. For files, a Lambda checks each landing against the registered schema and quarantines breaking changes. For Fivetran CDC, Fivetran syncs the new schema, so the protection is in dbt: staging models select columns explicitly, and schema tests fail if a column we depend on disappears or changes type. Additive changes pass quietly; breaking ones stop that source’s models and alert us.”

### 04   ·  SILVER — SHARED TRANSFORMATION LAYER

**Engine:**  Snowflake SQL through dbt, plus PySpark libraries where Python logic is needed.

**Shared layer:**  Reusable **dbt macros** (currency conversion, fiscal calendar, return netting, tokenized-key joins) and **PySpark libraries**, used by merchandising, marketing and supply chain.

Transform categories:

- **Conformance** — products, stores, channels and fiscal calendar conformed to shared definitions.

- **Identity resolution** — POS, online and clienteling records resolved to one client key.

- **Returns and exchanges** — netted against original sales so net demand is correct.

- **Deduplication** — CDC and API redeliveries removed on business keys.

*“The shared layer was the real win of adopting dbt. A fiscal-calendar or return-netting rule is written once as a macro, tested once, and used everywhere.”*

### 05   ·  GOLD — MARTS & SEMANTIC LAYER

**Tool:**  dbt on Snowflake.

**Marts:**  sales and margin, client value and clienteling performance, inventory and sell-through, fulfillment and delivery.

**Semantic layer:**  Shared metric definitions consumed by both Tableau and Power BI, so “net sales” means the same thing in both.

**Performance:**  Clustering keys on large facts (date and division), result caching for repeated dashboard queries — part of the 25% runtime cut.

**Macros:**  generate\_surrogate\_key, safe\_divide (sell-through, margin rate), date\_spine with the fiscal calendar.

### 06   ·  ORCHESTRATION

**Scheduler:**  **Apache Airflow** — dependencies across Fivetran syncs, Lambda pulls, dbt runs and BI extracts.

**Data movement:**  **Fivetran** and **Lambda/Glue** move data; Airflow triggers or waits on them.

**CI/CD:**  **GitLab CI** builds, tests and deploys dbt projects and Airflow DAGs.

**Daily DAG**

```text
PARALLEL     trigger/await Fivetran syncs . Lambda API pulls . Snowpipe loads
   v
CHECK        drift gate + dbt source freshness
   v
SEQUENTIAL   dbt build: staging -> intermediate -> marts (+ tests)
   v
SEQUENTIAL   semantic layer refresh -> BI extract refresh -> notify
```

> **🎯 COACH’S CUE**
>
> **When they ask:** *“What’s the difference between Fivetran and Airflow?”*
>
> **Say:** “Fivetran moves data — it handles CDC from source databases into Snowflake. Airflow orchestrates — it triggers or waits on Fivetran syncs and Lambda pulls, runs dbt only after sources are fresh, refreshes BI extracts, and alerts on SLA misses. Airflow never moves the data itself.”

### 07   ·  WAREHOUSE & DIMENSIONAL MODEL

| **Table** | **Type** | **Grain** | **Notes** |
| --- | --- | --- | --- |
| fact\_sales\_line | Transactional | one sale / return line | gross, discount, net, associate, channel |
| fact\_inventory\_daily | Periodic snapshot | SKU × location × day | on hand, on order, available to sell |
| fact\_fulfillment | Accumulating snapshot | one order line | ordered, picked, shipped, delivered |
| dim\_client | SCD Type 2 | client version | InCircle tier, assigned associate, home store |
| dim\_product / dim\_store / dim\_associate / dim\_date | SCD Type 1 / static | one row per member | designer, class; fiscal calendar |

**Why SCD Type 2 on dim\_client:** clients move between InCircle tiers and are reassigned to different associates and stores. Clienteling performance must credit each sale to the associate and tier in place at the time — otherwise a reassignment moves a year of sales to a different associate.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How do you handle slowly changing dimensions?”*
>
> **Say:** “In luxury retail the relationship is the history. When a client is reassigned to a new associate, past sales still belong to the previous one. So dim\_client is Type 2 — a new row when tier, associate or home store changes — and each sale carries the key of the version in effect. Associate performance and tier analysis stay correct after every reassignment.”

### 08   ·  DATA QUALITY FRAMEWORK

**Testing framework:**  dbt tests and Great Expectations for the shared codebase, run in GitLab CI on every merge request.

**Checks:**  Keys, relationships, accepted values; custom rules (net = gross − discount − returns; inventory never negative).

**Freshness:**  dbt source freshness on Fivetran and Snowpipe sources.

**Reconciliation:**  Daily sales totals vs. POS and order-management control totals.

### 09   ·  SECURITY & GOVERNANCE

- **PCI DSS** — card data tokenized before Snowflake; no card numbers in analytics.

- **Customer PII** — Snowflake masking policies on names, emails, phones and addresses; unmasked only for approved roles.

- **RBAC** — role hierarchy by function (merchandising, marketing, clienteling, finance).

- **Privacy** — CCPA/CPRA access and deletion requests supported through the client key.

- **Change control** — Terraform and GitLab CI, so access and schema changes are reviewed.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How did you protect payment and customer data in Snowflake?”*
>
> **Say:** “Card data is tokenized before it lands, so Snowflake never holds a card number. Customer PII sits behind masking policies — most roles see masked values, and only approved roles see the original. Roles follow business functions, and everything is defined in Terraform and deployed through GitLab CI, so access changes are reviewed like code.”

### 10   ·  LAST MILE — REACHING CONSUMERS

- **Merchandising** — sales, margin, sell-through and inventory marts.

- **Marketing and clienteling** — client value and associate performance.

- **Supply chain and fulfillment** — inventory and delivery performance.

- **BI users** — Tableau and Power BI on the shared semantic layer.

### TRACK 2 — STREAMING PIPELINE

*Supplementary. Only if they ask about real time.*

#### Why Streaming Earns Its Place

*“The batch platform covers reporting. Separately — because associates and customers need to know whether an item is available, and where an order is, right now — inventory movements and order status stream through Kafka into Snowflake via Snowpipe Streaming, with current availability served for fast lookups.”*

#### Streaming Architecture

```text
inventory.movements . order.status (Kafka, key = sku|location / order_id)
   +--> Snowpipe Streaming (Kafka connector) -> Snowflake RAW
   |      rows queryable in seconds; dbt models refresh frequently
   +--> AWS Lambda consumer -> DynamoDB item_availability
          (available units per SKU and location, single-digit ms reads)
```

#### Kafka & Snowpipe Streaming

**Keys:**  sku|location for inventory; order\_id for order status.

**Snowpipe Streaming:**  Rows written directly into Snowflake tables through the Kafka connector — no intermediate files, low latency.

**Exactly-once:**  Connector offset tracking plus idempotent merges on event ID in dbt.

#### NoSQL Hot Path — Amazon DynamoDB

**Table:**  item\_availability — partition key sku, sort key location\_id.

**Attributes:**  available\_units, reserved\_units, updated\_ts.

**Access:**  Clienteling app and e-commerce read availability in single-digit milliseconds.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“Why not query Snowflake for item availability?”*
>
> **Say:** “An associate checking whether a size is in stock needs an answer instantly, and thousands of those checks happen at once. That’s a key lookup — DynamoDB returns it in milliseconds. Snowflake is built for analytical queries; serving point lookups there would add latency and compute cost. The same events still land in Snowflake for reporting.”

#### How Batch and Streaming Meet

Snowpipe Streaming lands events in Snowflake RAW, where the same dbt models build inventory and fulfillment facts. DynamoDB holds only current availability; the history is in Snowflake.

#### Sample Datasets

`fact_sales_line`

| **sale line** | **date** | **client** | **associate** | **store** | **product** | **net $** | **channel** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SL-25-0918-0041 | 2025-09-18 | cl\_tk\_5a10 | AS-1182 | NM-DAL-01 | DSG-HB-22014 | 3,450.00 | STORE |
| SL-25-0918-0042 | 2025-09-18 | cl\_tk\_5a10 | AS-1182 | NM-DAL-01 | DSG-SH-81077 | 1,195.00 | STORE |
| SL-25-0918-0107 | 2025-09-18 | cl\_tk\_c204 | AS-2045 | ONLINE | DSG-RTW-40912 | 890.00 | DIGITAL |
| SL-25-0919-0012 | 2025-09-19 | cl\_tk\_7e33 | AS-3307 | NM-BH-02 | DSG-JW-10456 | 12,800.00 | STORE |
| SL-25-0919-0013 | 2025-09-19 | cl\_tk\_7e33 | AS-3307 | NM-BH-02 | DSG-HB-22014 | -3,450.00 | RETURN |

*Client keys are tokenized; product codes and values are illustrative.*

`dim_client  (SCD Type 2)`

| **client\_sk** | **client** | **InCircle tier** | **associate** | **home store** | **eff start** | **eff end** | **current** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6100211 | cl\_tk\_5a10 | TIER 3 | AS-0907 | NM-DAL-01 | 2023-02-01 | 2025-04-30 | N |
| 6188402 | cl\_tk\_5a10 | TIER 4 | AS-1182 | NM-DAL-01 | 2025-05-01 | 9999-12-31 | Y |
| 6100388 | cl\_tk\_c204 | TIER 1 | AS-2045 | ONLINE | 2024-08-12 | 9999-12-31 | Y |
| 6100517 | cl\_tk\_7e33 | TIER 5 | AS-3307 | NM-BH-02 | 2022-11-20 | 9999-12-31 | Y |

*cl\_tk\_5a10 moved up a tier and was reassigned to a new associate on 2025-05-01. Earlier sales stay credited to AS-0907. Tier labels are illustrative.*

`Streaming inventory event (Kafka: inventory.movements)`

| **Field** | **Type** | **Example** |
| --- | --- | --- |
| event\_id | string | inv-20250918-77c0a2 |
| sku | string | DSG-HB-22014 |
| location\_id | string | NM-DAL-01 |
| event\_type | string | SALE (RECEIPT / SALE / TRANSFER\_OUT / TRANSFER\_IN / RESERVE) |
| quantity\_delta | integer | -1 |
| available\_after | integer | 2 |
| event\_ts | timestamp | 2025-09-18T19:12:03.441Z |
| schema\_version | integer | 4 |

#### Likely Follow-Ups — One-Line Answers

- **Where did the 25% come from?** Query profiles showed full scans on large facts; clustering keys fixed pruning, result caching helped repeated dashboard queries, and a few models were rewritten incrementally.

- **How did you get the team to adopt dbt?** Started with one high-value domain, built shared macros and tests, wrote standards, and reviewed every merge request.

- **How did you reduce Snowflake spend?** Separate warehouses per workload, right-sized each, short auto-suspend, and moved heavy batch off interactive warehouses.

- **Snowpipe vs. Snowpipe Streaming?** Snowpipe loads files; Snowpipe Streaming writes rows directly with lower latency.

**Case Study 3 of 3**

## Ally Bank — Digital Bank Lakehouse for Deposits & Auto Lending

Senior Data Engineer  ·  Ally Bank, Detroit, MI  ·  AWS + Databricks  ·  Banking — Deposits, Transfers & Auto Loans  ·  Apr 2021 – Sep 2023

#### Your 30-Second Opener

*“At Ally Bank — a branchless, digital-first bank — I helped build the enterprise lakehouse on Databricks: deposit balances, fund transfers, auto loan originations and servicing, and transaction history, with full SCD Type 2 history for audit. Because Ally runs entirely through digital channels, every risk, servicing and marketing decision depends on this data, so reliability and regulatory traceability drove every design choice. Let me walk you through the batch platform.”*

### S   ·  SITUATION

Ally has no branches; customers do everything digitally. That makes data the operating backbone: risk, servicing and marketing all run on deposit, transfer and auto-loan data, and regulators and auditors expect every reported number to be traceable.

The pain: much of the logic lived in legacy Teradata stored procedures that were hard to read, test or change. Account and loan history wasn’t consistently kept, which made point-in-time and audit questions slow to answer. Account numbers and Social Security numbers needed stronger protection. Real-time account and payment updates weren’t integrated into the analytics platform, and batch windows were unpredictable as volumes grew.

The people who felt it: risk, servicing and collections, marketing, finance and regulatory reporting, and internal audit.

### T   ·  TASK

As Senior Data Engineer, I built critical banking data domains in Delta Lake on Databricks with full history; landed CDC through Kafka (Amazon MSK) into bronze, silver and gold; implemented field-level encryption, tokenization and Unity Catalog access control; refactored Teradata stored procedures into dbt; tuned Databricks jobs and Delta tables; enforced coding standards through code review; ensured adherence to FDIC, CFPB, BSA/AML and SOX requirements with audit logging and lineage; and built unit, integration and reconciliation tests.

### A   ·  ACTION

- Integrated **Debezium CDC through Kafka on Amazon MSK** and REST ingestion for account updates, payment events and servicing activity, landing in **Delta Lake bronze** on S3.

- Added a **Lambda schema-drift check** on file landings and schema-registry compatibility on CDC topics.

- Built **deposit balances, fund transfers, auto loan originations and servicing, and transaction history** domains in Delta Lake with **MERGE-based SCD Type 2**.

- **Refactored Teradata stored-procedure ETL into dbt models**, improving transparency and testability.

- Protected data with **field-level encryption, tokenization of account and SSN attributes, KMS-managed keys and Unity Catalog RBAC**.

- Kept batch windows predictable with **OPTIMIZE, Z-ORDER, auto-compaction** and Spark shuffle and incremental-load tuning.

- Ensured **FDIC, CFPB, BSA/AML and SOX** support with **immutable audit logging in Delta** and **lineage in Unity Catalog**.

- Built **PyTest, dbt tests, Great Expectations and PyDeequ** suites plus **reconciliation tests**; orchestrated with **Airflow**; CI/CD in **Jenkins** with **Terraform**.

### R   ·  RESULT

*The resume says “significantly reducing production data defects” and “keeping batch windows predictable” without numbers. Figures marked † are suggested framing — replace with your own or speak to them qualitatively.*

- **Full SCD Type 2 history on every critical banking domain** — point-in-time and audit questions answered from the lakehouse.

- **Production data defects down significantly** after unit, integration and reconciliation tests — roughly half†.

- **Batch windows predictable as volumes grew** — nightly runtime variance cut by ~40%† after Delta and Spark tuning.

- **Teradata stored procedures retired into tested dbt models.**

- **Account numbers and SSNs tokenized**, with access enforced through Unity Catalog.

- **Real-time account and payment events** integrated through Debezium and MSK.

### ◆   ·  ARCHITECTURE AT A GLANCE

**Batch lane (primary)**

```text
SOURCES
  core deposit system . transfer/payment systems . auto loan origination
  auto loan servicing . digital banking events . reference data
     |  [Debezium CDC -> Kafka (Amazon MSK) -> Delta]  [REST -> S3]
     v
BRONZE  - Delta Lake on S3 (CDC events with op & commit LSN)
     |  [S3 file landings -> EventBridge -> Lambda schema-drift check]
     |  [CDC topics: Schema Registry compatibility]
     v
SILVER  - Databricks: tokenize . apply CDC . MERGE-based SCD Type 2
     |  [dbt (from Teradata stored procs): staging -> intermediate -> marts]
     v
GOLD    - Delta marts (deposits, transfers, auto loans) + Snowflake/SQL
     v
CONSUMERS  risk . servicing & collections . marketing . finance
           regulatory reporting . audit . Tableau & self-service SQL
 
ORCHESTRATION  Apache Airflow (+ Step Functions)  .  Jenkins + Terraform
```

**Streaming lane (separate — supplementary)**

```text
account updates . payment events . servicing activity
     v
Debezium -> Kafka (Amazon MSK)  (key = account_id / loan_id)
     v  [Spark Structured Streaming on Databricks]
     |  watermark . dedupe on LSN . latest state per account/loan
     +-------------------------------+------------------------------+
     v                               v                              v
Delta bronze/silver             Amazon DynamoDB                audit log
(shared with batch)             (hot path: latest payment      (immutable
                                 & servicing status, <10 ms)    Delta table)
```

**Governance & Compliance**

```text
SECURITY    field-level encryption . tokenized account & SSN . KMS keys
ACCESS      Unity Catalog RBAC . column masks . IAM least privilege
REGULATORY  FDIC . CFPB . BSA/AML . SOX — audit logging + lineage
QUALITY     PyTest . dbt tests . Great Expectations . PyDeequ . recon
```

*Assumption to confirm: the resume describes real-time account and payment events through Debezium and MSK but not a serving store. DynamoDB is the AWS-native framing for the hot path.*

### TRACK 1 — BATCH PIPELINE

*Primary story. Lead with SCD Type 2 history for audit — it’s the heart of this case.*

### 01   ·  SOURCE SYSTEMS & INGESTION

**Sources:**  Core deposit system, transfer and payment systems, auto loan origination and servicing, digital banking events, reference data.

**CDC:**  **Debezium** reads database transaction logs and publishes inserts, updates and deletes to **Kafka on Amazon MSK**; each event carries the operation and the source log position (LSN).

**APIs:**  REST ingestion for servicing activity and partner data, landed in S3.

**Credentials:**  AWS Secrets Manager; IAM authentication to MSK.

*“Log-based CDC was the right fit for a bank: it captures every change, including deletes, in commit order, without putting query load on the core systems.”*

### 02   ·  BRONZE — RAW LANDING

**Storage:**  Delta Lake on S3 — CDC events appended as received.

**Audit columns:**  ingested\_at, source\_table, op (c/u/d), source\_lsn, commit\_ts, kafka\_offset.

**Immutability:**  Bronze is append-only; time travel and the audit log table record every write.

Keeping the source log position on every row means any curated record can be traced to the exact database change that produced it — which is what auditors ask for.

### 03   ·  SCHEMA DRIFT CHECK (POST-BRONZE)

**CDC topics:**  **Schema Registry** compatibility rules on Debezium topics stop breaking changes at the producer.

**File landings:**  EventBridge on S3 “Object Created” → **AWS Lambda** compares landed files to the Glue/Unity Catalog schema.

**Additive change:**  New column → auto-approved; Delta schema evolution on the next MERGE.

**Breaking change:**  Dropped or retyped column → quarantine, flag, alert. That source pauses; others continue.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How do you handle unexpected schema changes?”*
>
> **Say:** “For CDC topics, Schema Registry compatibility rules catch most breaking changes before they’re published. For file sources, a Lambda checks every landing against the catalog. Additive changes are auto-approved and Delta evolves the table. Dropped or retyped columns quarantine that source with an alert. In a bank, a silent type change in a balance column is exactly the kind of error that ends up in a regulatory report, so breaking changes always need a human.”

### 04   ·  SILVER — CDC APPLY & SCD TYPE 2

**Engine:**  PySpark on **Databricks**.

Transform categories:

- **Tokenization first** — account numbers and SSNs replaced with tokens before Silver; field-level encryption for the few attributes that must stay recoverable, with KMS-managed keys.

- **Apply CDC in order** — events ordered by source log position; deletes honored.

- **SCD Type 2 MERGE** — changed attributes expire the current row and insert a new version.

- **Conformance** — product codes, account statuses and loan states standardized.

- **Derived measures** — daily balances, interest accrued, days past due, payment status.

**Tuning:**  OPTIMIZE and Z-ORDER on account and date keys, auto-compaction, shuffle-partition tuning, and incremental MERGE on only the partitions touched by new changes.

*“The MERGE only touches the accounts that changed today, and Z-ordering on account ID means it reads only the files that hold them. That’s what kept the batch window predictable as volumes grew.”*

### 05   ·  GOLD — DBT MARTS

**Tool:**  dbt models, many refactored from legacy Teradata stored procedures.

**Marts:**  deposit balances and flows, fund transfers, auto loan originations, auto loan servicing and delinquency, transaction history.

**Consumers:**  Curated marts published to Tableau and self-service SQL.

**Macros:**  generate\_surrogate\_key, safe\_divide (delinquency rate, utilization), date\_spine.

*“Converting stored procedures to dbt turned hidden logic into readable, tested SQL with lineage. Reviewers could finally see what a number meant.”*

### 06   ·  ORCHESTRATION

**Scheduler:**  **Apache Airflow** — dependencies, retries, SLAs; **AWS Step Functions** for event-driven file flows.

**Execution:**  Databricks jobs (Silver), dbt (Gold), MSK connectors (CDC).

**CI/CD:**  **Jenkins** with **Terraform** for infrastructure.

**Daily DAG**

```text
SENSOR       CDC caught up to end-of-day log position . file landings
   v
CHECK        drift gate (quarantined = skip)
   v
PARALLEL     Databricks Silver: CDC apply + SCD2 MERGE per domain
   v
SEQUENTIAL   Great Expectations / PyDeequ -> dbt build + tests
   v
SEQUENTIAL   reconciliation to core systems -> publish -> audit log
```

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How do you make sure the daily run uses a complete day of CDC?”*
>
> **Say:** “The DAG starts with a sensor that waits until CDC has caught up to the end-of-day position in the source log, so we never build a day from half the changes. Airflow then runs the Silver MERGEs, quality checks, dbt and reconciliation in order. Databricks and dbt do the work; Airflow enforces the sequence and alerts if the window is at risk.”

### 07   ·  WAREHOUSE & DIMENSIONAL MODEL

| **Table** | **Type** | **Grain** | **Notes** |
| --- | --- | --- | --- |
| fact\_deposit\_balance\_daily | Periodic snapshot | account × day | ledger & available balance, interest accrued |
| fact\_transfer | Transactional | one transfer | amount, direction, rail, status |
| fact\_auto\_loan\_daily | Periodic snapshot | loan × day | principal, days past due, status |
| fact\_auto\_loan\_payment | Transactional | one payment | amount, applied to principal/interest |
| dim\_deposit\_account | SCD Type 2 | account version | product, APY tier, status, ownership type |
| dim\_customer / dim\_product / dim\_date | SCD Type 2 / 1 / static | one row per member | tokenized customer; product terms |

**Why SCD Type 2 here:** account products, rate tiers, statuses and ownership change. Interest, balances and regulatory reports must use the terms in effect on each day, and auditors need to see the exact history of every account. Full Type 2 history in Delta — plus time travel — answers “what did we know, and when?”

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How do you handle slowly changing dimensions?”*
>
> **Say:** “At Ally every critical domain had full Type 2 history, because auditors and regulators ask what an account looked like on a given date. I implemented it as a Delta MERGE from the CDC stream: when a tracked attribute changes — rate tier, status, ownership — the current row is closed and a new version inserted, with effective dates and a current flag. Facts carry the key of the version in effect, and Delta time travel adds a second layer for reproducing past reports.”

### 08   ·  DATA QUALITY & RECONCILIATION

**Unit tests:**  **PyTest** for transformation functions.

**Constraint checks:**  **Great Expectations** and **PyDeequ** on Spark DataFrames: required keys, valid statuses, non-negative principal, balances consistent with transactions.

**dbt tests:**  Keys, relationships, accepted values on Gold.

**Reconciliation:**  Daily totals by product — balances, transfers, loan principal — compared with core-system control totals; any break holds publication.

**Effect:**  Production data defects reduced significantly.

### 09   ·  SECURITY & REGULATORY COMPLIANCE

- **Tokenization and encryption** — account numbers and SSNs tokenized; field-level encryption with KMS-managed keys where values must be recoverable.

- **Access** — fine-grained RBAC and column masks through **Unity Catalog**; least-privilege IAM.

- **Regulatory** — data supporting FDIC, CFPB, BSA/AML and SOX reporting, with **immutable audit logging in Delta** and **lineage in Unity Catalog**.

- **Change control** — Jenkins CI/CD and Terraform; code review on every change.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“How did you support FDIC, CFPB, BSA/AML and SOX requirements?”*
>
> **Say:** “My part was making the data defensible. Every curated record traces back to a source log position; every critical domain keeps full history; an immutable Delta audit log records every write; and Unity Catalog shows lineage from source to report. Daily reconciliation to the core systems proves completeness. Combined with tokenized SSNs and account numbers and role-based access, that’s what auditors and examiners need to see.”
>
> **Avoid:**  claiming to own the regulatory filings. Say you built the controls and evidence they rely on.

### 10   ·  LAST MILE — REACHING CONSUMERS

- **Risk** — deposit and auto loan performance, delinquency.

- **Servicing and collections** — loan status and payment history.

- **Marketing** — customer and product engagement (tokenized).

- **Finance and regulatory reporting** — reconciled balances and flows.

- **Analysts** — Tableau and self-service SQL on curated marts.

### TRACK 2 — STREAMING PIPELINE

*Supplementary. Only if they ask about real time.*

#### Why Streaming Earns Its Place

*“Batch produces the reconciled daily picture. Separately — because a digital bank’s servicing teams need to see a payment the moment it posts — account updates, payment events and servicing activity stream through Debezium and MSK, with the latest status served for fast lookups.”*

#### Streaming Architecture

```text
deposits.cdc . payments.cdc . servicing.events  (MSK, key = account/loan)
   v
Spark Structured Streaming on Databricks
   |  order by source LSN . dedupe . latest state per account / loan
   |  foreachBatch -> idempotent sinks
   +-------------------------------+------------------------------+
   v                               v                              v
Delta bronze (shared lakehouse) DynamoDB servicing_status     Delta audit log
                                (last payment, status, <10 ms)
```

#### Kafka on Amazon MSK

**Topics:**  One per source table from Debezium, plus servicing events.

**Keys:**  account\_id / loan\_id — each account’s changes stay in order.

**Security:**  IAM authentication, TLS, encryption at rest with KMS.

#### NoSQL Hot Path — Amazon DynamoDB

**Table:**  servicing\_status — partition key loan\_id (or account\_id).

**Attributes:**  last\_payment\_amount, last\_payment\_ts, current\_status, days\_past\_due, source\_lsn.

**Idempotency:**  Conditional writes only when the incoming LSN is newer — replays can’t move state backward.

**Access:**  Single-digit-millisecond reads for servicing tools.

> **🎯 COACH’S CUE**
>
> **When they ask:** *“Why not have servicing tools query the lakehouse?”*
>
> **Say:** “A servicing agent looks up one loan at a time and needs an answer immediately. DynamoDB answers that in milliseconds. The lakehouse is built for scanning large histories for analysis. Using the source log position in a conditional write also guarantees the hot store never shows an older status than it already has.”

#### How Batch and Streaming Meet

The stream writes CDC events into the same Delta bronze tables batch uses. The daily batch applies CDC and SCD Type 2 to Silver, reconciles to core systems, and publishes Gold. One lakehouse, one history.

#### Sample Datasets

`fact_deposit_balance_daily`

| **date** | **account** | **product** | **ledger $** | **available $** | **APY** | **interest $** | **status** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023-06-30 | acct\_tk\_77a1 | ONLINE SAVINGS | 25,410.88 | 25,410.88 | 4.00% | 2.78 | OPEN |
| 2023-06-30 | acct\_tk\_2c90 | INTEREST CHECKING | 3,118.20 | 2,968.20 | 0.25% | 0.02 | OPEN |
| 2023-06-30 | acct\_tk\_51e4 | 12-MO CD | 50,000.00 | 0.00 | 4.80% | 6.58 | OPEN |
| 2023-06-30 | acct\_tk\_0b3f | ONLINE SAVINGS | 0.00 | 0.00 | — | 0.00 | CLOSED |
| 2023-06-30 | acct\_tk\_9d12 | MONEY MARKET | 112,904.51 | 112,904.51 | 3.75% | 11.60 | OPEN |

*Accounts are tokenized; products, rates and balances are illustrative.*

`dim_deposit_account  (SCD Type 2)`

| **acct\_sk** | **account** | **product** | **APY tier** | **ownership** | **status** | **eff start** | **eff end** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4400118 | acct\_tk\_77a1 | ONLINE SAVINGS | 3.30% | INDIVIDUAL | OPEN | 2022-11-01 | 2023-03-31 |
| 4471209 | acct\_tk\_77a1 | ONLINE SAVINGS | 4.00% | INDIVIDUAL | OPEN | 2023-04-01 | 2023-05-14 |
| 4480533 | acct\_tk\_77a1 | ONLINE SAVINGS | 4.00% | JOINT | OPEN | 2023-05-15 | 9999-12-31 |
| 4400390 | acct\_tk\_0b3f | ONLINE SAVINGS | 3.30% | INDIVIDUAL | CLOSED | 2023-02-10 | 9999-12-31 |

*acct\_tk\_77a1 had a rate change in April and became a joint account in May. Interest and ownership reporting for each period uses the version in effect.*

`Debezium CDC event (MSK: payments.cdc)`

| **Field** | **Type** | **Example** |
| --- | --- | --- |
| op | string | u (c = create / u = update / d = delete) |
| source.table | string | loan\_servicing.payments |
| source.lsn | long | 84417728193 |
| ts\_ms | long | 1688140923441 |
| after.loan\_id | string | ln\_tk\_3f81 (tokenized) |
| after.payment\_amount | decimal | 486.22 |
| after.status | string | POSTED |
| after.posted\_date | date | 2023-06-30 |

#### Likely Follow-Ups — One-Line Answers

- **Why Debezium over periodic extracts?** Log-based CDC captures every change and delete in commit order without querying the core system.

- **How do you apply CDC in order?** Order by source log position within each key before the MERGE; ignore events older than the current version.

- **OPTIMIZE and Z-ORDER — when?** Nightly on the hottest tables, Z-ordered on the MERGE key so MERGE and lookups read fewer files.

- **What changed when stored procedures became dbt?** Logic became readable SQL with tests, docs and lineage, reviewed like any other code.

#### Cross-Case Quick Reference

| **Topic** | **PayPal (GCP)** | **Neiman Marcus (Snowflake/AWS)** | **Ally Bank (AWS + Databricks)** |
| --- | --- | --- | --- |
| Raw / Bronze | GCS + BigQuery raw, per market | S3 + Snowflake RAW (Fivetran, Snowpipe) | Delta bronze from Debezium CDC |
| Drift / gate | Cloud Function + circuit breaker | Lambda (files) + dbt schema tests (CDC) | Schema Registry + Lambda |
| Middle layer | PySpark on Dataproc + BigQuery SQL | dbt shared macros + PySpark libs | Databricks CDC apply + SCD2 MERGE |
| Gold | dbt on BigQuery + Iceberg/BigLake | dbt marts + semantic layer | dbt marts (from Teradata procs) |
| Orchestrator | Cloud Composer (config-driven) | Airflow (+ Fivetran syncs) | Airflow + Step Functions |
| SCD2 dimension | dim\_customer (risk tier) | dim\_client (tier, associate) | dim\_deposit\_account |
| Stream | Kafka → Flink | Kafka → Snowpipe Streaming | Debezium → MSK → Structured Streaming |
| Hot path | Bigtable | DynamoDB | DynamoDB |
| Compliance hook | Reg Z, ECOA, FCRA, GLBA | PCI DSS, CCPA/CPRA | FDIC, CFPB, BSA/AML, SOX |

#### Back-Up Stories

- **Zoom (2019–21, AWS)** — re-architected ingestion and aggregation for the 2020 surge in meeting participants; Kafka and Spark Structured Streaming for call-quality telemetry with S3 checkpoints, backpressure and Kubernetes autoscaling; semantic models in Snowflake and low-latency rollups in Apache Druid. Use for any high-volume streaming question.

- **American Honda (2018–19, AWS)** — connected-vehicle telemetry through Kinesis into S3; Lambda and Step Functions for serverless enrichment; Redshift and DynamoDB datasets for real-time vehicle metrics; VIN pseudonymization. Use for IoT or serverless questions.

- **Hawaiian Airlines (2016–17)** — helped stand up the Snowflake estate; CDC with Spark on EMR; reconciliation against SQL Server and Oracle before publication.

- **Coach (2014–16)** — Spark, Hive and Presto on EMR and Redshift for e-commerce and merchandising.

#### Questions to Ask Them

- When upstream data goes bad today, how far does it get before someone notices?

- How are data contracts and schema changes handled between producers and consumers?

- Which datasets have the strictest SLAs or regulatory exposure?

- What would make someone in this role clearly successful at six months?
