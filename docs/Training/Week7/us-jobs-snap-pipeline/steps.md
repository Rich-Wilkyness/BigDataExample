# Project steps and learning record

## How we will work

Work one checkpoint at a time. Each concrete step will include its purpose, prerequisites, commands or console actions, explanations of what and why, expected results, verification, and observed evidence. The learner executes the implementation; this document records what actually happened. See [project guidance](AGENTS.md).

The original checkpoints below follow the Azure instructor-project path. The separate [GCP learning plan](gcp-learning-plan.md) owns the GCP adaptation and detailed setup history. GCP checkpoints are recorded separately here and do not mark Azure work complete.

## Current checkpoint record

| Checkpoint | Purpose | Current evidence / status |
|---|---|---|
| Select sources and analytical question | Compare jobs and SNAP over time | Questions accepted; [state source verification](source-verification.md) completed with documented exceptions |
| Agree the model | Keep state/month measures separate from state/industry/month measures | Logical design accepted; five-column monthly `dim_date` documented; no tables implemented |
| Agree the batch workflow | Historical load, then monthly six-month refresh | Architecture documented; no Azure workflow deployed |
| Write the initial proposal | Summarize business problem, sources, architecture, transformations, and final output | [Proposal](proposal.md) drafted on October 20, 2026; no submission or implementation claimed |
| Check prerequisites and choose authoring path | Identify assigned Azure resources/permissions and choose console, CLI, or Terraform for the next step | Not started; do not recreate or alter shared resources |
| Validate state/industry source coverage | Establish exact series IDs, state mappings, units, and missing periods | Public-source checks completed October 20: tested BLS candidate inventory and all 6,600 SNAP state/month keys; final industry scope and source anomalies need review |
| Implement one ingestion checkpoint | Learn to save one source response to Bronze with traceable metadata | Pending learner walkthrough and execution |
| Expand initial load and build Silver | Load historical/catch-up records and validate source measurements | Pending |
| Build dimensions and two Gold facts | Produce validated analytical tables at the accepted grains | Pending |
| Add orchestration and monthly schedule | Configure retries, concurrency, freshness checks, and replay | Pending; activate schedule only after initial load and verification |
| Demonstrate results and recovery | Query results, show revision behavior, and rerun safely | Pending |

This is a roadmap, not evidence that these implementation steps have run.

## Public-source verification checkpoint — October 20, 2026

Purpose: confirm the data actually supports the proposed states, industries, dates, and units before building Azure ingestion. Read-only source inspection was authorized; it did not deploy resources or implement Silver/Gold work.

Actual observations: 20 unregistered BLS API batch requests checked 250 candidate series; total jobs, manufacturing, and retail trade each provide 6,600 numeric baseline observations. Construction is supported for 48 states. All 50 unemployment series include a source-missing October 2025 marker. Twelve USDA fiscal-year members across 84 regional sheets contain all 6,600 expected state/month records; Wyoming August 2022 has negative dollar values flagged for review. Detailed locations, source hashes, and exceptions are in [verification](source-verification.md).

Learning checkpoint: distinguish an absent series, a present row with a missing-value marker, and a numeric amount requiring interpretation. Do not repeat all requests manually; use the evidence to understand these cases. Final industry choice and Wyoming handling are pending. No pipeline runtime success is claimed.

## Separate daily classwork

The learner reports that the daily customers-file Azure exercise is complete. It is separate from the jobs/SNAP project and is not a project source or outstanding project step. This records the learner's report, not a fresh inspection of those Azure resources.

## Implementation checkpoint format

For each new checkpoint, record the following in plain language:

- Purpose and why this step comes next.
- Prerequisites and known resource ownership.
- Chosen method: console steps, CLI commands, or Terraform guidance.
- Exact actions and explanations, with placeholders identified and no secrets included.
- Expected result, explicitly separated from actual observations.
- Verification and evidence supplied by the learner or observed with authorization.
- Errors, resolution, and remaining work.

## Decisions recorded from the planning discussion

- The first historical assignment window is 2015–2025. Initial catch-up bridges later months; ongoing runs use a strict six-month reporting window per source.
- Older revisions and gaps outside that window are not automatically loaded or corrected for this project.
- Run monthly on day 1; 06:00 UTC is the proposed configuration default, not an activated schedule.
- Bronze paths describe ingestion date/run/attempt, not the observation month.
- One orchestrating pipeline with `concurrency=1` is the proposed way to prevent overlapping runs of this workflow.
- Request retries and activity retries are different. Their proposed values and limitations are explained in [architecture](architecture.md).

## Questions clarified before implementation

- Function request retries repeat a failed API request; Data Factory activity retries repeat the Function invocation. Three Function retries and two activity retries can multiply to 12 attempts for one failing operation. Proposed ingestion setting: request retries in code and zero Data Factory ingestion activity retries.
- Missing-data policy is accepted: process valid available records, retain legitimate partial facts with NULLs/source-level status, and show only complete comparable records/months in default Gold reporting views and visuals. Define completeness for the report's actual state/industry scope; an all-state report must not silently omit missing states. Unexpected technical failures are different from legitimately unpublished data.
- Concurrency requires no new architecture selection: use the documented single pipeline and configure `concurrency=1` during learner-led setup. This does not protect independent writing notebooks or other pipelines.
- Gold means the agreed five tables, not charts. Their names/grains and complete-only visual reporting policy are settled; report-specific required inputs and the concrete validated-output publication mechanism will be explained at implementation time.
- Retry ownership follows the operation being repeated; it is not file ownership. Request retries belong to the Function's client/code for this project, while saved Bronze files allow later processing replay without re-fetching APIs.
- Both analytical questions are accepted: compare state payroll job changes with SNAP participation changes, and compare job gains/losses across selected industries within each state. Processing will use Spark/PySpark; the plan is Delta storage with Spark SQL queries for Gold, without selecting a separate SQL database.

## GCP checkpoint — local access, billing inspection, and guardrails — October 23, 2026

**Purpose:** Establish authenticated access and usage controls before the first warehouse exercise. **Prerequisites:** Personal Google account, installed CLI, intended project/billing account, and learner control of console changes. **Method:** Learner-executed CLI and console setup plus one agent-executed read-only MCP project lookup. Exact installation/authentication/MCP commands and console settings are in [GCP setup history](gcp-learning-plan.md#14-local-cli-and-mcp-preparation) and [results](gcp-learning-plan.md#15-setup-and-cost-control-results--october-23-2026).

**Expected result:** Connected read access, project/account identification, an alerts-only budget, per-query bytes limit, and a reviewed daily quota; account inconsistencies explicitly recorded.

**Observed evidence:** SDK 590.0.0 and active personal CLI login from supplied output; MCP project description returned the intended project ACTIVE. Learner saved `jobs-snap-monthly-alert`: $5/month, All projects (1), all services, both savings groups excluded, actual 20/50/90/100% thresholds plus forecast 100%, billing-admin/user email enabled. Saved-budget screenshot shows $0/$5 and no spend cap; email delivery remains untested. Learner reports saving maximum bytes billed `104857600` in BigQuery query settings. Daily Query usage per day remains 200 TiB; screenshot/learner report say nonadjustable, so the proposed 1 GiB/day quota is not configured.

**Billing evidence and remaining work:** Overview says Free trial account, $300 and 90 days remaining ending January 22, 2027, alongside a trial-over banner. Transaction ledger shows a $30 manual payment, −$30 ending balance, and a separate declined attempt with $0 impact; learner reports payment details say Completed. Refund eligibility and bank settlement are not verified. Learner chose to defer further billing investigation. No upgrade or additional payment is instructed. These checks do not establish any capstone data processing.

## GCP checkpoint — first BigQuery query job — completed October 23, 2026

**Purpose:** Observe a warehouse query job and its result before creating a dataset or loading source data. A BigQuery project groups resources and query jobs; a dataset groups tables/views within a location; a table stores rows; a query job executes SQL. This first query needs no user-created dataset or source table.

**Prerequisites:** Select `project-4b0f63f3-e441-4289-b42` in BigQuery Studio and confirm maximum bytes billed is `104857600` in the query configuration. The nonadjustable daily quota and billing-banner inconsistency remain recorded limitations.

**Learner console instructions:** Open a blank SQL query tab in [BigQuery Studio](https://console.cloud.google.com/bigquery?project=project-4b0f63f3-e441-4289-b42). Run this invented orientation query:

```sql
SELECT
  'ID' AS state_abbreviation,
  202401 AS date_key,
  'orientation_only' AS record_kind;
```

**What it does and why:** SELECT returns three constant values with descriptive column names. There is no FROM clause and no source-table scan. This verifies query execution, not actual Idaho measurements, ingestion, or table-reading cost controls. Do not save this row as a project fact.

**Expected result, not observed output:** One row with `ID`, `202401`, and `orientation_only`. Open Job information/details and note success/failure, job ID, execution location, bytes processed, and bytes billed where displayed. The planned `us-central1` resource location is not established by the console's default query location.

**Verification / observed evidence:** Learner pasted the expected one-row result and supplied Job information showing a successful job in the intended project, location `US`, duration 185 ms, bytes processed `0 B`, bytes billed `0 B`, priority INTERACTIVE, legacy SQL false, and a temporary destination table. Creation time displayed October 23, 2026 at 12:20:06 PM UTC−6; start/end were 12:20:07 PM. The screenshot contains the job ID; the personal account email is not transcribed. This establishes a real constant-only query job, not source-table access or enforcement of the 100 MiB limit. `US` is the observed multi-region job location, distinct from the planned `us-central1` region for owned datasets. **Remaining work:** Create and inspect the practice dataset, then load/query a tiny practice table. Reference: [Google query execution guide](https://docs.cloud.google.com/bigquery/docs/running-queries).

## GCP checkpoint — create a practice dataset — completed October 23, 2026

**Purpose:** Create the named container that will hold practice tables/views and establish its data location. In a table reference, `project.dataset.table` identifies the owning project, dataset, and table. A BigQuery dataset is a storage/access container, whereas an Azure Data Factory dataset describes data used by activities.

**Prerequisites:** Completed first query job; intended personal project selected. The prior query's `US` location does not require creating a `US` dataset.

**Learner console instructions:** In BigQuery Studio, open Explorer (expand the collapsed pane beside the editor if necessary). Find `project-4b0f63f3-e441-4289-b42`, open its three-dot actions menu, and select Create dataset. Enter Dataset ID `jobs_snap_practice`; choose Location type Region and region `us-central1` (Iowa). Use an ordinary native dataset, leaving external-dataset linking off. Review the form, then select Create dataset. If the form differs, inspect it before accepting defaults. Do not create a table during this checkpoint.

**Expected result:** An empty dataset named `jobs_snap_practice` appears beneath the intended project. Open its Details and verify dataset ID and data location `us-central1`. Location is selected at creation and cannot be edited afterward. Table-expiration settings can be reviewed in the following checkpoint before uploading practice data; do not assume the earlier optional seven-day suggestion is configured.

**Observed evidence:** Learner reported creation and supplied dataset Details showing `project-4b0f63f3-e441-4289-b42.jobs_snap_practice`, created October 23, 2026 at 12:27:06 PM UTC−6, data location `us-central1`, default table expiration Never, and time travel window 7 days. Screenshot verifies dataset identity/location; table data has not been supplied or inspected. The seven-day time travel window is a recovery setting, not automatic table expiration. **Remaining work:** Configure practice-table expiration, then load a tiny clearly labeled fixture with explicit types. Reference: [Google dataset creation guide](https://docs.cloud.google.com/bigquery/docs/datasets).

## GCP checkpoint — practice-table automatic expiration — learner-confirmed October 23, 2026

**Purpose:** Limit the lifetime of disposable practice tables before loading them. **Prerequisites:** Verified `jobs_snap_practice` dataset in `us-central1`; preserve original practice files locally for reloading. **Method:** Learner console edit of this practice dataset only.

**Instructions:** Open the dataset Details → Edit Details. Under Default table expiration, select Enable table expiration and set Default maximum table age to 7 days, then Save. Return to Details and verify Default table expiration shows 7 days. If the form differs, inspect its options before saving.

**Expected behavior:** New ordinary tables inherit a seven-day lifetime unless a table-specific expiration overrides it; expiry deletes a table and its contents. Changing this dataset default does not retroactively set expiration on existing tables. The dataset itself remains. This is distinct from the separately displayed time travel window. Keep this disposable practice policy separate from later capstone retention decisions.

**Observed evidence:** After the instruction to save and confirm seven days in Details, the learner replied done. Record the seven-day default as learner-confirmed, without a fresh screenshot or API read. The earlier screenshot showing Never predates this change. **Remaining work:** Prepare the fixture and verify the first loaded table inherits the intended expiration. Reference: [Google default table expiration guide](https://docs.cloud.google.com/bigquery/docs/updating-datasets#update_default_table_expiration_times).

## GCP checkpoint — practice CSV load — Preview verified October 23, 2026

**Purpose:** Connect a local CSV file to a native BigQuery table, separating text-file representation from typed warehouse columns. **Prerequisites:** Verified `jobs_snap_practice` in `us-central1`, seven-day default expiration confirmed by learner, a local plain-text editor, and a retained copy of the file. **Method:** Learner creates the fixture locally and reviews the console form before submitting a load.

**Instructions:** Save the following as a plain-text UTF-8 file named `orientation-practice.csv` in a local folder you can find in the browser file picker. These are invented practice counts, not BLS or USDA observations. Copy only the CSV content, not Markdown fences.

```csv
state_abbreviation,date_key,practice_job_count,record_kind
ID,202401,100,orientation_only
ID,202402,105,orientation_only
WA,202401,200,orientation_only
```

Open `jobs_snap_practice` → Create Table. Set Create table from to Upload, select the local file, and choose CSV format. Verify destination project `project-4b0f63f3-e441-4289-b42`, dataset `jobs_snap_practice`, table name `orientation_practice`. Pause before Create table and inspect/share the form; explicit schema and header handling are the next checkpoint. Do not rely on autodetection or upload to a capstone fact table.

**Expected result:** A local file with one header and three data rows and an unsubmitted Create table form targeting the practice dataset. Intended schema for the next review is `state_abbreviation STRING`, `date_key INTEGER`, `practice_job_count INTEGER`, `record_kind STRING`, in that order; skip one header row. **Observed evidence at instruction issue:** File preparation and load were pending; the subsequent form and Preview evidence below supersede this status. **Remaining work:** Verify saved schema and table expiration before a table-reading query. Reference: [Google local file loading guide](https://docs.cloud.google.com/bigquery/docs/loading-data-local).

### Upload form review — explicit schema and CSV header

The learner supplied the Create table form at Schema, with Auto detect unchecked, no fields yet, No partitioning selected, clustering blank, and Advanced options collapsed. The screenshot does not show the source file or destination fields; the learner must confirm those before submitting. No table/load success is established.

Keep Auto detect off and Edit as text off. Click Add field for each column below, preserving CSV order. Select NULLABLE mode for each field. STRING preserves text; INTEGER stores whole numbers for the month key and invented practice count. These practice choices do not define the later capstone source schema.

| Field name | Type | Mode |
| --- | --- | --- |
| state_abbreviation | STRING | NULLABLE |
| date_key | INTEGER | NULLABLE |
| practice_job_count | INTEGER | NULLABLE |
| record_kind | STRING | NULLABLE |

Keep No partitioning and leave clustering blank for this three-row fixture. Expand Advanced options and set Header rows to skip to 1, so the CSV header is not loaded as data. Keep the comma delimiter and zero allowed bad records. Recheck the source is the intended local CSV and destination is `project-4b0f63f3-e441-4289-b42.jobs_snap_practice.orientation_practice`, then select Create table once.

Expected verification after the load: inspect Schema for the four intended types, Preview for the three matching data rows with no header row, and Details for location and inherited table expiration. Share Preview or the exact error next; creation, schema acceptance, row reconciliation, and expiration remain pending until evidence is supplied. This step issues learner-executed load instructions; no agent cloud operation occurs.

### Observed load result and next verification — October 23, 2026

The learner supplied Advanced options showing Write if empty, zero errors allowed, comma delimiter, double-quote character, Default source column match, and one header row skipped; Unknown values, Quoted newlines, and Jagged rows were unchecked. A later screenshot shows `project-4b0f63f3-e441-4289-b42` → `jobs_snap_practice` → `orientation_practice`, with Preview displaying 1–3 of 3 rows. Values match the issued fixture: `(ID, 202401, 100, orientation_only)`, `(ID, 202402, 105, orientation_only)`, and `(WA, 202401, 200, orientation_only)`. The header was excluded. This establishes a created practice table and visible data matching all three intended rows; separate load-job ID/status details were not supplied.

Next learner actions: open Schema and verify `state_abbreviation STRING`, `date_key INTEGER`, `practice_job_count INTEGER`, `record_kind STRING`, all NULLABLE. Open Details and check data location `us-central1`, row count 3, creation time, and table expiration about seven days after creation. Supply those observations or screenshots. These metadata checks are pending; Preview does not independently prove types, expiration, or per-query byte-limit enforcement. Previewing the table is separate from running a table-reading SQL query. All fixture values remain illustrative; no BLS/USDA data or capstone facts have been loaded.

### Saved table metadata — learner-confirmed October 23, 2026

After reviewing the requested Schema and Details checks, the learner reported they look good. Record this as learner confirmation of STRING/INTEGER/INTEGER/STRING columns, all NULLABLE, location `us-central1`, row count 3, and expiration about seven days after creation. No fresh schema/Details screenshot or API response was supplied; the exact expiration timestamp remains unrecorded. This confirmation supersedes the pending metadata checks above. Separate load-job ID/details and byte-limit rejection testing remain unverified.

## GCP checkpoint — first query against stored practice rows — issued, execution pending

**Purpose:** Distinguish reading stored table data from the earlier constant-only query and from Preview. **Prerequisites:** Created/Preview-verified `orientation_practice` table and learner-confirmed schema/location/expiration. **Method:** Learner-authored GoogleSQL in BigQuery Studio; the learner executes it.

**Instructions:** Open a SQL query tab, confirm Maximum bytes billed is `104857600`, and set processing location to `us-central1` if it is explicitly fixed to the earlier `US` job location. Write your own SELECT that returns `state_abbreviation`, `date_key`, and `practice_job_count` from the full table identifier below, filters for Idaho (`ID`), and orders by `date_key` ascending. Enclose the full identifier in backticks because the project ID contains hyphens. Inspect the estimated bytes before Run; if above the configured ceiling, inspect the query rather than raising it automatically.

```text
project-4b0f63f3-e441-4289-b42.jobs_snap_practice.orientation_practice
```

**Expected result, not observed output:** Two rows: `(ID, 202401, 100)` and `(ID, 202402, 105)`. This is synthetic practice data. Supply the SQL attempt, actual result, and Job information showing location, bytes processed, and bytes billed. Tiny-table billing can differ from logical bytes read, so record both values as displayed rather than predicting the charge. **Observed evidence:** Pending learner query/result/job details. **Remaining work:** Validate the query and explain filtering, ordering, and processed versus billed bytes before moving to the next exercise. A small successful query alone does not prove rejection of queries over the byte ceiling.

### First table-reading attempt — observed October 23, 2026

Learner screenshot shows successful `SELECT * FROM ` followed by the backtick-quoted full `orientation_practice` identifier and `LIMIT 1000`. Results show all three fixture rows and all four columns. The editor validator estimates 114 B when run, shows on-demand processing, and displays Maximum bytes billed 104857600. This establishes table-reading SQL execution and visible per-query configuration, not actual job bytes billed, location, or rejection above the ceiling. Job information was not shown for this run.

Feedback: the full table identifier and backticks are correct. `*` selects all columns; LIMIT 1000 permits all three existing rows and does not implement the requested Idaho filter or date order. For this unpartitioned/unclustered table, LIMIT is not a scan-cost control. Next learner edit: select the three requested columns explicitly, add a WHERE condition for `state_abbreviation` equal to `'ID'`, and ORDER BY `date_key` ascending. Remove the unnecessary LIMIT for this tiny fixture. Expected filtered result remains two Idaho rows, ordered January then February. Filter/order execution and actual Job information bytes/location remain pending. Preserve the learner's attempt rather than substituting a completed answer.

### Progression decision — October 23, 2026

The learner stated that they understand SQL and that successful query execution is already proven, and requested moving on. The additional Idaho filter/order exercise is skipped by learner choice and is not a prerequisite for storage. Preserve the original attempt and feedback above as history. BigQuery orientation is sufficient to advance: constant query, dataset creation, fixture load/Preview, metadata confirmation, and table-reading query have evidence. Actual bytes billed/location for the table-reading query and rejection above the byte ceiling remain unverified; do not imply the skipped exercise ran. Later guidance should focus on GCP-specific concepts rather than reteaching familiar SQL.

## GCP checkpoint — Cloud Storage bucket configuration review — issued, execution pending

**Purpose:** Establish private object storage for later immutable Bronze source captures. Cloud Storage holds files as objects in buckets, comparable in responsibility to S3/ADLS; BigQuery tables hold typed warehouse rows. This checkpoint creates no ingestion or compute workflow. **Prerequisites:** Intended project selected, recorded budget/query controls, and local original files retained. Billing-banner inconsistency remains deferred by learner; do not upgrade billing to bypass an error. **Method:** Learner console authoring.

**Instructions:** Open [Cloud Storage Buckets](https://console.cloud.google.com/storage/browser?project=project-4b0f63f3-e441-4289-b42) and choose Create. Proposed globally unique name: `jobs-snap-bronze-620503845148` (availability not checked). Choose Region `us-central1`, default storage class Standard, hierarchical namespace disabled, uniform bucket-level access, and public access prevention enforced. Keep optional replication, caching, and Autoclass off for this initial simple bucket. Advance to the data-protection section but pause before final Create; inspect/share soft-delete, object-versioning, and retention settings. Do not lock retention. No second storage configuration or paid compute is needed.

**Expected result:** An unsubmitted bucket form with the intended region/storage/access settings and visible protection choices. **Observed evidence:** Pending learner form review; no bucket created or name availability established. **Remaining work:** Explain and select recovery/retention settings, let the learner create the bucket, verify its configuration, then upload one small practice file under a clearly labeled practice prefix before capturing real sources. Source snapshots later use distinct source/ingestion-date/run/attempt paths; object versioning alone is not that immutability contract. Reference: [Google bucket creation guide](https://docs.cloud.google.com/storage/docs/creating-buckets).

### Optional extra information — shorter table names and unsaved query text

This section is reference material, not a required exercise or prerequisite for Cloud Storage. The learner chose not to save the disposable query draft and requested moving on; no saved-query creation is claimed. The optional default-dataset statements below have not been executed or configured.

Correction to the earlier blanket backtick instruction: GoogleSQL permits dashes in the first identifier of a table path in FROM/TABLE clauses, so a dashed project ID alone does not make backticks universally required. Backticks quote identifiers and remain a useful convention for full paths. See [lexical table-name rules](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/lexical#table_names).

With the intended default project, `jobs_snap_practice.orientation_practice` is a valid shorter table reference without backticks. A bare `orientation_practice` additionally requires a default dataset. One explicit script-scoped method is `SET @@dataset_id = 'jobs_snap_practice';` followed by the SELECT in the same script; it does not establish a permanent default for all future query tabs. The default project may also be specified with `SET @@dataset_project_id = 'project-4b0f63f3-e441-4289-b42';`. These are optional illustrative configuration statements, not learner-executed evidence. See [system variables](https://docs.cloud.google.com/bigquery/docs/reference/system-variables).

The earlier screenshot shows an asterisk beside Untitled query. A leave-page unsaved-work warning is consistent with unsaved SQL editor text; running SQL does not mean saving a named query. Save through the editor Save menu to preserve the query, or explicitly discard/leave if that disposable SQL text is no longer needed. Leaving/discarding the editor draft does not delete the already-created dataset/table. A separate unsaved bucket/configuration form, if open, would need its own handling. No query-save action is required; the learner intends to leave without saving. Actual editor dismissal has not been inspected. See [saved queries](https://docs.cloud.google.com/bigquery/docs/work-with-saved-queries).

### Bucket protection review — October 23, 2026

Learner screenshots show the unsubmitted bucket form with Soft delete policy enabled and default duration selected (UI describes seven days), Object versioning unchecked, compliance Retention unchecked, and Google-managed encryption key selected. Encryption enforcement shows Google-managed and Cloud KMS keys Allowed, customer-supplied keys Restricted. Allowing a key type does not itself provision a Cloud KMS key. Screenshots do not independently verify the earlier bucket name/location/access sections or establish bucket creation.

Recommended learner action: keep these protection/encryption settings. Seven-day soft delete provides recovery after deletion and retains billable deleted bytes during that period; it is not a seven-day automatic expiration of live source objects, unlike the practice-table expiration. Keep versioning off for the first bucket; later immutable source capture relies on unique ingestion date/run/attempt paths and overwrite prevention, not merely retained object versions. Leave compliance retention off and do not lock retention. Use Google-managed encryption with no separate KMS setup required.

Confirm earlier form sections match `jobs-snap-bronze-620503845148`, Region `us-central1`, Standard, hierarchical namespace disabled, Uniform access, and enforced public access prevention. Then the learner may click Create. If a confirmation appears for public access prevention, confirm it remains enforced. Supply the bucket Overview/Configuration after creation to verify its actual name, location, storage class, protection, and access settings. If creation fails, preserve the error rather than upgrading billing. Bucket creation remains pending until learner evidence arrives. Reference: [Google soft delete guide](https://docs.cloud.google.com/storage/docs/soft-delete).

### Bucket creation — configuration verified October 23, 2026

Learner Configuration screenshot confirms bucket `jobs-snap-bronze-620503845148`, URI `gs://jobs-snap-bronze-620503845148`, created October 23, 2026 at 1:06:17 PM UTC−6. Region is `us-central1` (Iowa), default class Standard, hierarchical namespace Not enabled, cross-bucket replication Not enabled, Requester Pays Off, access control Uniform, public access prevention Enabled via bucket setting, and public access status Not public. Header shows Soft Delete protection. Exact saved soft-delete duration, encryption, versioning, and compliance-retention settings are not visible in this screenshot; earlier form screenshots show the intended settings, not independent post-creation verification of those fields. Bucket creation and the visible configuration are verified from learner evidence. No object upload or ingestion is established yet.

## GCP checkpoint — upload a practice object — verified October 23, 2026

**Purpose:** Verify the learner can write/read object metadata in the bucket and understand its object path before real source capture. **Prerequisites:** Created private bucket, retained local `orientation-practice.csv` from the BigQuery exercise, and learner console access. **Method:** Learner console upload; no agent cloud writes.

**Instructions:** Open bucket Objects → Create folder, enter `practice`, and open it. Select Upload files and choose the existing `orientation-practice.csv`. If that object already exists, stop before overwriting it and inspect what is present. After upload completes, click the file to open object details. In this flat-namespace bucket, `practice/` is an object-name prefix displayed as a folder; the final object name is `practice/orientation-practice.csv`.

**Expected result:** One uploaded practice object at `gs://jobs-snap-bronze-620503845148/practice/orientation-practice.csv`, with a positive byte size and displayed creation/update metadata. Share the object name, size in bytes, and gs:// URI (or object Details screenshot). Confirm the file content remains the same synthetic three-row fixture if preview/download is available; do not treat successful metadata display alone as content-hash reconciliation. Keep the local copy. This practice prefix distinguishes invented data from future source snapshots, which will use source/ingestion-date/run/attempt paths.

**Observed evidence:** Learner object Details screenshot verifies `practice/orientation-practice.csv` in the intended bucket, Cloud Storage URI `gs://jobs-snap-bronze-620503845148/practice/orientation-practice.csv`, size 151 B, type text/csv, Standard class, Not public, created/modified October 23, 2026 at 1:13:19 PM (no timezone displayed in this screenshot). Retention expiration and object-retain-until fields show None. Object bytes have not been independently downloaded/hash-compared; the screenshot establishes object presence/path/positive size. A displayed Public URL is an address, not proof of anonymous permission; the status explicitly says Not public. **Remaining work:** Exact saved bucket soft-delete duration when available, and the first bounded real-source capture. Console upload permissions do not establish a future service account's access. Reference: [Google object upload guide](https://docs.cloud.google.com/storage/docs/uploading-objects).

## GCP checkpoint — define the first real BLS request — issued, execution pending

**Purpose:** Begin a bounded real-source slice after successful warehouse/storage orientation. **Prerequisites:** Existing source schemas and tested state-series inventory, local plain-text editor, and retained local files. **Method:** Learner prepares a nonsecret request JSON locally; no API call or cloud deployment in this preparation step.

Use the tested Idaho total nonfarm series `SMS16000000000000001`, seasonally adjusted, in thousands of jobs. This identity is taken from the October 20 inventory and is not a fresh observation retrieval. Start with calendar year 2024 only, within the agreed development slice; this does not replace the full historical/catch-up/six-month refresh scope or settle industry selection.

Save this as `bls-idaho-2024-request.json` in your local working folder:

```json
{
  "seriesid": ["SMS16000000000000001"],
  "startyear": "2024",
  "endyear": "2024"
}
```

The series ID selects state/program/measure; year strings bound the request. There is no source API credential in this small unregistered request. **Expected result:** A valid local JSON request for one series and one year. **Observed evidence:** Pending learner preparation. **Remaining work:** Guide one bounded POST to the BLS endpoint, preserve original response bytes under ingestion-date/run/attempt identity, inspect request/series/period/value status, then add retrieval/hash/request metadata to a manifest before real Bronze upload. The user writes pipeline implementation; this request example is source-access setup, not completed ETL. References: [source schema](source-schemas.md), [tested series inventory](evidence/state-series-verification.json), and [BLS API signatures](https://www.bls.gov/developers/api_signature_v2.htm).

### Python ingestion direction and request-file verification — October 23, 2026

The learner supplied [data/bls-idaho-2024-request.json](data/bls-idaho-2024-request.json) and asked about a Lambda-style Python ingestion job. Agent read/JSON validation confirms one series `SMS16000000000000001` and start/end year 2024. Request preparation is complete; no BLS response has been retrieved in this implementation checkpoint.

Use a reusable Python ingestion module executed locally first, consistent with the GCP plan. Cloud Run functions offer the function/event style analogous to Lambda; a Cloud Run job is the planned hosted fit for a bounded script that fetches, saves, and exits. A Python function is ordinary reusable code and does not require deploying a cloud function. Later packaging/runtime identity/retry/timeouts are separate deployment checkpoints. Reference: [Cloud Run execution forms](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run).

Next learner coding checkpoint: create `ingest_bls.py` beside this steps file and implement only a `load_request(request_path)` function that reads the existing JSON and returns a Python dictionary. Use pathlib/json from the standard library; resolve the request relative to the script directory rather than assuming terminal cwd. The intended following checkpoints are bounded HTTP POST, preservation of original response bytes, source-level response checks, manifest with retrieval/request/hash/run/attempt metadata, then immutable Cloud Storage upload. No pandas/Spark transformations or BigQuery writes belong in this ingestion function. The user writes code and executes it; no implementation or deployment performed by the agent.

Expected first evidence: learner code and printed request dictionary matching the existing JSON. Local Python execution, response capture, manifest, and cloud source upload remain pending.

### Local request loader — path correction and learner execution — October 23, 2026

The learner placed the script at [code/ingest_bls.py](code/ingest_bls.py), rather than beside steps.md. Their first execution failed with FileNotFoundError because a single parent resolved to code/data. Correction: `Path(__file__).resolve().parent.parent / "data" / "bls-idaho-2024-request.json"` resolves sibling data/ from code/. The learner then ran `python code/ingest_bls.py` from the project folder and supplied output beginning with a Python dictionary and seriesid list; the pasted output is truncated. Agent inspected the saved source: REQUEST_PATH uses parent.parent, load_request reads UTF-8 and returns json.loads(text), and the main guard prints the parsed request. Static AST parsing and existing request JSON parsing passed. Full printed field values are not separately verified from the truncated learner output; the saved JSON remains the previously verified one-series/2024 request. No HTTP request, response capture, or cloud ingestion has run in this checkpoint.

### Next coding checkpoint — bounded BLS HTTP fetch, implementation pending

Add a learner-written `fetch_bls(payload)` function using standard-library urllib.request (no new dependency required). POST to `https://api.bls.gov/publicAPI/v2/timeseries/data/`; serialize the dictionary with json.dumps and UTF-8 encode it for the request body; specify Content-Type application/json and method POST. Use urllib.request.Request and urlopen with a 30-second timeout, then read and return the raw response bytes within a context manager. Preserve HTTP exceptions and avoid indefinite retries. A socket timeout is not a strict total-runtime guarantee; explicit bounded retries/overall deadline will be addressed before automation. Share the code before invoking the HTTP fetch. The next step will preserve original bytes, inspect BLS status/messages/series/periods, and record retrieval/hash/run/attempt metadata. Do not replace the raw response with reserialized parsed JSON, upload yet, or transform measures in this function.

### Fetch function review and capture-path evidence — October 23, 2026

Learner implemented `fetch_bls(payload)` with json.dumps/UTF-8 request bytes, the BLS endpoint, POST method, JSON content type, urllib Request/urlopen, a 30-second timeout, and response.read() within a context manager. Agent inspected the saved code and parsed its AST successfully without invoking it. The main block loads the request and calls `checkPath()` only. The learner supplied the printed local capture path ending `data/bronze/bls/ingestion_date=2026-10-23/run_id=92226a135718463bbf17ddedf4807d12/attempt_id=001`. This is path-generation evidence, not directory creation or an HTTP request. The current checkPath function prints but does not return its Path.

Next learner edit: add `return capture_dir` to checkPath, retaining its optional print, then call it once as `capture_dir = checkPath()` from the main block. Create that directory with `capture_dir.mkdir(parents=True, exist_ok=False)` before the network call. Fetch once with `raw_response = fetch_bls(payload)`, record `retrieved_at = datetime.now(timezone.utc).isoformat()`, and save `response.json` with exclusive binary creation (`open("xb")`) and write the original bytes. Print the saved file path and len(raw_response). Exclusive directory/file creation prevents this local path from silently overwriting an existing capture; it does not establish cloud object immutability. Each script execution currently generates a new run ID and performs one attempt, not a retry of the previous run.

Run from the project directory using `python code/ingest_bls.py` and share its saved path/byte count or exact error. Expected: a new local attempt directory with a positive-size original response file. Actual HTTP execution/file evidence is still pending. Do not rerun merely to obtain a different response or overwrite failures. HTTP success alone is insufficient: BLS status/messages, returned series identity, and monthly coverage will be checked next, followed by request/retrieval/hash/run/attempt manifest metadata before Bronze upload. No real-source cloud upload, transformation, or accepted warehouse fact is claimed.

### First real BLS response — local capture verified October 23, 2026

Learner ran `python code/ingest_bls.py` and reported 1,166 saved bytes under `data/bronze/bls/ingestion_date=2026-10-23/run_id=bf3358b945a54a18a052a5944ddd12c4/attempt_id=001/response.json`. Agent inspected that file offline without another API request. Actual checks passed: valid JSON; REQUEST_SUCCEEDED; empty message list; exactly one returned series matching SMS16000000000000001; exactly 12 distinct year/period keys for 2024 M01–M12; no duplicate or missing requested months; all 12 values parse as positive numbers. Source values remain strings in original bytes. January is 854.7 and December 870.6 (thousands of jobs under the previously verified series definition); these are observed source values, not the earlier synthetic practice counts.

SHA-256 of the 1,166 original bytes: `e1c373e75fb63fcb550b72ca59e8ca939ab58e8bf4d21b9f729ee268ed19fefc`. The source file was read, not rewritten. Static AST check of the learner script passed. This proves one real local capture and its scoped source checks, not historical ingestion, cloud Bronze publication, or accepted warehouse facts.

Code review for next checkpoint: the learner factored capture into `makeRequest(capture_dir)`, which currently reads payload from a global and computes retrieved_at only as a local variable that is not returned or persisted. Pass payload explicitly as a second argument and return capture metadata so the later manifest can use it. The past run's exact retrieval timestamp was not persisted; do not manufacture it from the current time. Preserve this raw capture and label any later recovered filesystem timestamp as approximate rather than actual retrieval evidence. Next learner edit should return response_path and retrieved_at and pass payload explicitly; review before running again because the current main block performs a new live fetch on every invocation. Subsequent work: durable request/retrieval/hash/run/attempt manifest, repeatable offline validation, then upload original response and manifest without overwrite. Those steps remain pending.

### Capture metadata return reviewed — October 23, 2026

Learner corrected return parentheses to dictionary braces. Agent inspected the saved script: `makeRequest(capture_dir, payload)` now uses the supplied payload and returns response_path (Path) plus retrieved_at (UTC ISO string); the caller passes both arguments, but currently discards the returned dictionary. Static AST parsing passed; the agent did not execute ingestion. The original response remains preserved and no new fetch is established by this review.

Next learner edit: assign `capture = makeRequest(capture_dir, payload)` in main. Draft a `write_manifest(capture_dir, payload, capture)` function for review, without rerunning the live main yet. Build a JSON-safe dictionary containing source endpoint, request payload, retrieved_at, response filename, original byte size, SHA-256, and ingestion_date/run_id/attempt_id matching the capture directory. Read saved response bytes for size/hash; use `hashlib.sha256(raw_bytes).hexdigest()`. Store a filename/string rather than the returned Path object, because json.dumps does not serialize Path automatically. Write manifest.json beside response.json with exclusive creation, preserving the response unchanged. The learner writes the implementation; exact manifest field choices and ID extraction will be reviewed with the attempt. For the earlier capture, the exact retrieved_at is unknown and must not be replaced with the time of manifest creation. Manifest implementation/execution and real-source Bronze upload remain pending.

### Manifest implementation — offline verification passed October 23, 2026

At the learner's request for another check, agent inspected the saved [ingestion script](code/ingest_bls.py). BLS_ENDPOINT is shared between request and manifest; request_params embeds payload directly; response_filename uses the Path.name string; original saved bytes supply size and SHA-256; ingestion date/run/attempt come from directory names; retrieved_at is returned by make_request and supplied to write_manifest. Main calls load_request → get_capture_dir → make_request → write_manifest; make_request internally calls fetch_bls once.

An offline behavior check imported the module without running its main block, copied the existing 1,166-byte response into a temporary test directory, and invoked write_manifest with a clearly synthetic timestamp/run ID. All ten serialized fields matched expected values, including nested request parameters, response filename, exact bytes/hash, extracted IDs, and unchanged supplied timestamp. A second write raised FileExistsError and preserved the first manifest. The source capture hash was unchanged after the check. Temporary test files were removed; no source code was edited, no real retrieval timestamp invented, no BLS request made, and no cloud operation performed. This verifies manifest writing in isolation, not a real capture-plus-manifest execution.

Next learner action: run `python code/ingest_bls.py` once from the project folder to create a new real capture with the now-complete manifest-writing path. The old capture remains unchanged; its previously missing exact timestamp is not reconstructed. Share terminal output and the new manifest.json. Review response status/series/months and verify manifest bytes/hash/IDs/timestamp match the new response before uploading anything to Cloud Storage. Error handling, bounded retry/deadline behavior, runtime identity, hosted deployment, and automated acceptance remain later checkpoints.

### Real capture plus manifest — verified October 23, 2026

Learner executed the updated script and supplied 1,166 saved bytes for run `d5f4779a927c49729c681030c5c10341`, attempt `001`, ingestion date `2026-10-23`. Agent inspected response.json and manifest.json locally without a new API call. The 501-byte manifest matches endpoint, original request parameters, response filename, 1,166-byte size, SHA-256 `53698562da13ffe2bf06c79d1eae45d9172fcebaa2aeb847acc8aa6bc39be9ed`, and all path-derived IDs. Retrieval timestamp is persisted as `2026-10-23T21:00:11.899131+00:00`, valid UTC on the ingestion date. BLS response checks pass REQUEST_SUCCEEDED, empty messages, exactly one matching series, exactly twelve unique 2024 M01–M12 observations, and positive numeric values. Earlier capture remains separate. This is verified local capture/manifest evidence; no real-source cloud upload is established.

## GCP checkpoint — upload the verified source capture and manifest — deferred by learner

**Purpose:** Preserve original source bytes and their lineage record in cloud Bronze under the same ingestion/run/attempt identity. **Prerequisites:** Verified local run above, intended private bucket, active local gcloud credentials, terminal working directory `docs/Training/Week7/us-jobs-snap-pipeline`. **Method:** Learner-executed local CLI upload; no agent cloud writes.

Run from the project folder:

```bash
capture_rel="data/bronze/bls/ingestion_date=2026-10-23/run_id=d5f4779a927c49729c681030c5c10341/attempt_id=001"
bronze_uri="gs://jobs-snap-bronze-620503845148/bls/ingestion_date=2026-10-23/run_id=d5f4779a927c49729c681030c5c10341/attempt_id=001/"

gcloud storage cp --if-generation-match=0   "$capture_rel/response.json"   "$capture_rel/manifest.json"   "$bronze_uri"
```

The command uploads only the two named files to the explicit source/date/run/attempt prefix. The destination generation precondition 0 permits creation only when no live destination object exists, preventing replacement by this command. This is command-level overwrite protection, not retention locking or removal of the user's delete/overwrite permissions. If either object already exists or the operation partially fails, inspect the result before retrying; do not remove the precondition. Two-file upload is not atomic and must not trigger later automation until both objects are verified.

**Expected result:** Both object uploads complete; remote names are response.json (1,166 B) and manifest.json (501 B). **Observed evidence:** Pending learner output and remote verification. Share command output/errors; next inspect remote listing and integrity before treating cloud Bronze capture as accepted. Do not rerun the ingestion script just to upload this already-verified run. References: [gcloud storage cp](https://docs.cloud.google.com/sdk/gcloud/reference/storage/cp) and [request preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions).

## Revised ingestion sequence and shared modules — accepted October 23, 2026

The learner deferred the proposed single-capture cloud upload and chose to complete local historical ingestion for all required states/source measures first, then implement and prove monthly refresh behavior before hosted scheduling. Prior upload commands remain reference only and are not the next action. The learner accepted shared Python modules for reusable functions/constants and source-specific ingestion logic. No refactor, full historical run, monthly refresh, or cloud deployment has been implemented by this decision.

Four operating responsibilities remain: BLS historical/initial load, BLS monthly refresh, USDA SNAP historical/initial load, and USDA SNAP monthly refresh. These can share two source-specific modules with historical/refresh modes rather than duplicating full ingestion implementations. Historical baseline is January 2015–December 2025, followed by catch-up to each source's latest available month. Ongoing refresh is only the six reporting months ending at each source's latest available month; older gaps are reported without silently expanding scope. Monthly operation is a revision-aware refresh, not append-only loading. BLS encompasses LAUS unemployment plus CES total/selected-industry series; they have distinct definitions despite sharing the BLS API.

Proposed module responsibilities: shared constants/manifest/hash/run-context helpers; BLS API client/request-window planning; USDA workbook/archive discovery and byte capture; and a small entry point that selects source/mode and invokes the proper module. Keep source-specific response checks separate from truly shared mechanics. Define endpoint constants in source-specific modules, nonsecret adjustable settings in configuration, and future credentials through runtime authentication/secrets rather than shared constants. Modules should be safe to import, with live fetching behind explicit function calls/main guards. This describes a structure to build with the learner, not new source files created by the agent.

Cloud portability: Python imports work when the whole application package and needed configuration/dependencies are included in the Cloud Run build/container. Files on the learner laptop are not automatically present in Cloud Run; parameterize local output paths and later use Cloud Storage for durable results. The same source logic can be run locally and invoked by a Cloud Run job entry point. Packaging, runtime identity/access, resource limits, and scheduling are later learner-executed checkpoints. Reference: [Google Python job source deployment](https://docs.cloud.google.com/run/docs/quickstarts/jobs/build-create-python).

Next checkpoint: finalize the BLS series inventory before refactoring/expanding requests. Total jobs and unemployment plus manufacturing/retail for all 50 states are the proposed set; construction would add its explicitly supported 48-state subset. Industry choice remains pending learner response. Then plan bounded series/year batches, request limits, completeness checks, and restart/checkpoint behavior. Use existing verified inventory as input, preserving its dated evidence and exceptions; do not infer that the existing one-state request proves full backload coverage or current source availability.

## Industry scope accepted and operational BLS inventory — October 24, 2026

**Purpose:** Establish exactly which state/measure/industry series the historical loader should request before batching or refactoring source capture. **Accepted scope:** Manufacturing and retail for all 50 states plus standalone construction for its supported 48 (Delaware/Hawaii excluded for that category only). Industry is a categorical dimension in the same industry fact and BLS ingestion flow; no separate pipeline per industry. Total nonfarm and unemployment remain separate state/month measures. Other BLS industries exist, but are outside this initial accepted set and require their own definition/coverage checks before addition. The learner accepted this scope after the previous industry-choice discussion; prior pending-choice entries above are history.

**Prerequisites / evidence:** Existing October 20 [candidate inventory](evidence/state-series-verification.json), accepted logical model, and learner Python/JSON familiarity. Agent read the saved inventory on October 24: 250 candidates, five groups of 50; the two standalone construction candidates for Delaware/Hawaii have zero historical observations. Expected supported operational inventory is 248 series: 50 total nonfarm, 50 unemployment, 50 manufacturing, 50 retail, 48 construction. Counts were recomputed from the local evidence, not a new all-state API call. Current [Idaho publication structure](https://www.bls.gov/sae/additional-resources/list-of-published-state-and-metropolitan-area-series/idaho.htm) confirms additional published industries such as Financial Activities, Information, Leisure and Hospitality, and Health Care and Social Assistance. These are examples, not newly accepted categories or proof of all-state historical coverage. Do not mix aggregate categories with their components and sum them as independent industries.

**First learner coding action:** Create `code/bls_inventory.py`. Reuse the pathlib/json reading pattern to implement `load_series_inventory(inventory_path)` returning the top-level `series` list from `evidence/state-series-verification.json`. Resolve the evidence file relative to this script's project parent so terminal cwd does not matter. Under a main guard, print the candidate count and the first candidate's series_id, state_name, measure, and industry_name. No API request or ingestion call belongs in this module's import or this inspection run.

**Expected result, not learner execution evidence:** 250 candidate dictionaries, with intact metadata. The next checkpoint will select the agreed 248 supported IDs, preserve the two unsupported coverage exceptions separately, check uniqueness/category/state counts, then plan bounded historical requests and restart/checkpoint behavior. Do not filter on numeric completeness: the 50 valid unemployment series include the legitimate October 2025 source gap. Do not hand-type 248 IDs, regenerate them by guesswork, or mutate the original dated evidence file.

**Verification / remaining work:** Agent inventory inspection/counts are observed; learner inventory module creation/execution is pending. Shared-helper extraction, historical batching/backload, catch-up, six-month refresh tests, real-source cloud upload, and hosted schedule remain pending. No learner source code or operational inventory output was written by the agent. Historical baseline and reporting completeness rules remain unchanged.

### Runtime inventory configuration boundary — October 24, 2026

The learner clarified that evidence/ is dated source verification and config/ should define operational requests. This supersedes the earlier proposed direct evidence-backed runtime loader. The learner created `config/bls-series-inventory.json` (currently empty) and `code/bls_inventory.py`; agent inspection confirms the loader reads UTF-8 JSON and returns inventory["series"], but its current filename points to `config/state-series-verification.json` instead of the existing config filename. Change that final path component to `bls-series-inventory.json`. The one-state request was moved to config/ and ingest_bls.py now points there. These are observed saved-file states; no new ingestion or inventory execution occurred.

**Next learner checkpoint:** Create a one-time preparation script `code/prepare_bls_inventory.py`, separate from the runtime loader. It may read the preserved evidence JSON as provenance/input, select the accepted supported candidates, and write the operational config. Exclude only the two known unsupported construction IDs `SMS10000002000000001` and `SMS15000002000000001`; retain them as explicit excluded-series records with reasons. Do not filter out unemployment series for their legitimate October 2025 source gap. For each of the 248 selected records retain series_id, state_fips, state_name, program, measure, industry_code, industry_name, units, and seasonal_adjustment. Omit dated observed-value and coverage-statistics fields from the runtime series records.

Config should have a top-level series list plus excluded_series records (series_id and reason), and source_inventory identifying the preserved evidence filename. This provenance reference does not make runtime ingestion read evidence. Historical baseline and refresh-window configuration remain separate from the series inventory. Since the learner-created destination file is empty, the one-time script may populate that known empty file; if it is nonempty when run, stop and inspect rather than overwrite unreviewed content.

**Expected result:** Operational config contains 248 unique selected IDs with group counts 50 total nonfarm, 50 unemployment, 50 manufacturing, 50 retail, and 48 construction; two explicit excluded IDs; original evidence unchanged. Share the preparation-script attempt before running it. After preparation/verification, `python code/bls_inventory.py` should print 248 while reading config only. The saved empty config is not yet valid JSON, so running the loader now would fail. Preparation code, populated config, loader execution, batching and broader ingestion remain pending; no learner implementation completed by the agent.

### Candidate selection and metadata projection checkpoint — October 24, 2026

Learner supplied output 250 after implementing the candidate JSON loader. Subsequent saved preparation script separates prepare_inventory (load evidence series) and select_series (filter against supplied excluded_ids); its main prints candidate and selected counts. Agent inspected the script and parsed its AST without running it or writing config. The runtime config file remains empty. Selected count 248 remains the expected result; no additional terminal output was supplied for that filtering stage.

Next learner function: `build_series_records(selected)` should return a new list of dictionaries containing only series_id, state_fips, state_name, program, measure, industry_code, industry_name, units, and seasonal_adjustment. A SERIES_FIELDS tuple can define this reusable metadata projection; for each selected candidate, copy those named keys into a fresh dictionary. Preserve source strings, leading-zero state FIPS, and legitimate None industry fields for unemployment. Do not copy historical counts, observations, latest_observed_month, or missing-value statistics into operational series definitions. Do not modify the original evidence or selected dictionaries in place.

Call the function after selection and print the first projected record plus total records for review. Expected: 248 records with exactly nine metadata fields, without dated verification results. Manifest/raw-capture functions remain separate; this step writes no config and makes no API call. After review, assemble top-level series, excluded_series with reasons, and source_inventory, then write/validate the operational JSON config. Projection implementation, config assembly/write, runtime loading, and historical request batching remain pending.

### Operational BLS configuration — saved and verified October 24, 2026

Learner ran prepare_bls_inventory.py and supplied 250 candidate / 248 selected / 248 projected counts plus a nine-field Alabama example. An initial write attempt failed before writing because CONFIG_PATH.exitst was misspelled; after correction to exists(), the learner reran successfully. Agent inspected the saved 85,086-byte config/bls-series-inventory.json without rerunning the preparation script. Checks passed: valid JSON; 248 distinct selected series IDs; exactly the nine agreed metadata fields per record; exact selected metadata match to the preserved evidence definitions (including state FIPS strings/None industry fields); two reasoned construction exclusions for Delaware/Hawaii, disjoint from selection; group counts 50 total nonfarm, 50 unemployment, 50 manufacturing, 50 retail, and 48 construction. Preparation and runtime-loader scripts parse successfully. No new BLS request or cloud operation occurred.

The saved runtime loader now correctly points at config/bls-series-inventory.json and returns its series list. This supersedes earlier empty-config/wrong-filename states. Next learner verification: run `python code/bls_inventory.py` from the project folder; expected output is 248. That command reads config only, without evidence lookup, config rewriting, API requests, or ingestion. Do not rerun the one-time preparation script just to load the finished config: its nonempty-file guard is expected to stop replacement. Runtime loader execution, bounded historical request planning, restart behavior, full backload/catch-up, refresh modes, source cloud upload and hosting remain pending.

### Learner HTTP 503 attempt — October 24, 2026

While the current checkpoint was config-only loader verification, the learner ran `python code/ingest_bls.py`, which still executes a live BLS POST for the one-state request. Supplied traceback shows urllib.error.HTTPError: HTTP Error 503: Service Unavailable raised in urlopen before response.read. Agent inspected the unchanged saved script and local attempt directory `data/bronze/bls/ingestion_date=2026-10-24/run_id=d52e03202e2a4c1fa0a34130e932de89/attempt_id=001`: directory exists and is empty. No response.json or manifest.json was produced for this attempt. Older captures remain separate. No agent API retry performed.

HTTP 503 indicates the responding server cannot currently handle the request; this traceback alone does not establish a BLS-wide outage, exact cause, or Retry-After value. It is a technical request failure, not a missing-publication marker or a reason to exclude the series. The current code does not persist failed-attempt metadata or handle retry/backoff yet; retain the empty attempt and this error record for the later failure/restart checkpoint. Do not treat it as successful capture or repeatedly rerun the live script while investigating.

Next learner action remains `python code/bls_inventory.py`, which reads the saved config without calling BLS and should print 248. Only ingest_bls.py performs the live source call at present. After loader verification, continue historical request planning; bounded retries, error metadata, and retry-attempt identity must be addressed before broad live backload. HTTP semantics reference: [RFC 9110, 503 Service Unavailable](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.6.4).

### Runtime inventory loader confirmed; failed request scope clarified — October 24, 2026

Learner ran bls_inventory.py and supplied output 248. This confirms config-only loading; no source query ran in that command. Agent reread ingest_bls.py and config/bls-idaho-2024-request.json: the live script still reads the one-state config, containing only SMS16000000000000001 with startyear/endyear 2024. It is not yet wired to the 248-series runtime inventory. All these BLS API series use the same request endpoint, distinguished by payload series IDs; there are not 248 separate endpoint URLs.

Current [BLS API limits](https://www.bls.gov/developers/api_faqs.htm) were checked: unregistered 25 queries/day, 25 series/query, 10 years/query; registered 500/day, 50/query, 20 years/query. The failed one-series/one-year payload is below per-request size limits. Total daily usage is unknown, so the error does not prove or rule out quota/network/service causes. A 503 alone is not evidence a particular series is unsupported. No additional source request made. Next planning must batch 248 IDs and the 11-year baseline within the applicable limits, account for catch-up/retries, and record failures. Loader checkpoint complete from learner output; batching implementation and robust HTTP error capture remain pending.

### Request identity and HTTP error diagnostics — guidance issued October 24, 2026

Agent inspected the saved fetch and one-state payload: outgoing application headers currently include Content-Type application/json; no BLS registrationkey or Google authorization is supplied. This public API request is unregistered BLS access from the local Python process, independent of gcloud login/MCP identity. Registering for BLS higher limits is a separate source credential decision. If later using a registration key, inject it into the outgoing request at runtime and redact it from the durable manifest/request logging rather than embedding it in the operational config or blindly persisting credential-bearing payloads.

Next learner diagnostic edit: import urllib.error.HTTPError; wrap urlopen in try/except HTTPError, print status code/reason, selected response headers (Retry-After, Content-Type, Server), and up to 2,048 error-body bytes decoded with UTF-8 errors=replace; re-raise the exception so failure cannot be accepted as a normal response. This is console diagnostics only, not durable failed-attempt metadata or a retry implementation. Do not print every outgoing header/payload after credentials are introduced. Adding Accept application/json and an honest application User-Agent is optional request identification; it does not establish authentication or guarantee a fix for HTTP 503. HTTPError includes response headers and file-like body access per [Python urllib.error](https://docs.python.org/3/library/urllib.error.html). Diagnostic implementation/execution remains pending; no agent request performed.

### HTTP diagnostics implementation — offline check passed October 24, 2026

At the learner's request, agent inspected saved ingest_bls.py: fetch_bls catches HTTPError, prints code/reason, selected Retry-After/Content-Type/Server response headers and at most 2,048 decoded body bytes, then re-raises. AST parsing passed. An isolated offline check imported the module without main execution and mocked urlopen to raise a synthetic 503 with a Retry-After header/body. Output contained expected diagnostics; the same exception was re-raised. Outgoing POST payload and timeout=30 matched the request configuration. No real network call, response file, or cloud action occurred. This is HTTP-error diagnostic verification, not outage diagnosis or bounded-retry/error-manifest completion. URL/DNS/TLS failures and socket timeouts remain separate unhandled exception paths.

Next learner diagnostic action: execute `python code/ingest_bls.py` once and share either successful capture output or the added HTTP diagnostics. Header values may be None if absent, which is expected and not a new failure. A successful call would not explain the earlier 503; a repeat failure may supply new evidence. Do not loop repeatedly or change series selection to work around the failure.

### Live HTTP diagnostic result — October 24, 2026

Learner ran ingest_bls.py once with the diagnostic handler. Run `24583f8a14684b3d99a61172eacc8f90`, attempt 001, received HTTP 503 Service Unavailable, Retry-After None, Content-Type text/html, Server None. The printed body starts with an HTML page titled "The BLS website is busy"; remaining printed content includes site monitoring JavaScript rather than BLS series JSON. The HTTPError was correctly re-raised and the process failed before normal response/manifest writing. Agent inspected the attempt directory locally: it exists and is empty. No new API request was performed by the agent.

This confirms the diagnostic path works and supplies a BLS-branded busy-page response, not a Python JSON-serialization or inventory-selection failure. Exact underlying cause (load, maintenance, intermediary/traffic filtering, or other service condition) is not established; neither a BLS-wide outage nor exhausted quota follows from this response alone. Absence of Retry-After means no server-provided retry delay was observed. Current live request remains the small one-series/one-year development request, not the 248-series inventory.

Do not immediately loop requests or alter the series inventory to work around this technical failure. Next robustness work should persist failed-attempt metadata/error body separately from normal captures and implement bounded retries with backoff/attempt identity; do not relabel the HTML error as successful response.json or suppress the exception. Historical batching/config planning can continue offline using the verified inventory and previously saved successful response. Diagnostic HTML was supplied in terminal output; it has not yet been durably captured as an error artifact by the learner script. The exact failed-attempt retrieval timestamp is not available from this transcript; do not invent it.

### Failed-attempt writer review — corrections pending October 24, 2026

Agent inspected learner ingest_bls.py at the request to check the saved file. Handler correctly moved into make_request, reads the HTTP body once, populates the diagnostic fields, and re-raises. Three corrections are needed before execution: module-level ERROR_PATH calls undefined PATH(), causing NameError during import; error output must instead be capture_dir / "error.json" inside the handler and opened with exclusive "x" rather than shared/global overwrite "w"; retrieved_at currently precedes the fetch, so move success retrieval timestamp after fetch completion and compute failed_at independently inside the except block. Keep each error artifact within its own run/attempt folder.

Static AST parsing passed but isolated module import reproduced NameError for PATH before main or any HTTP request. Full error-file behavior was not tested because import is blocked. Agent did not edit learner source, invoke a request, or generate an ingestion capture. Learner fixes and offline verification of failure persistence remain pending. This is a code-review issue, separate from the earlier server 503.

### Failed-attempt persistence — offline verification passed October 24, 2026

Learner removed the leftover ERROR_PATH/PATH block and implemented error_path under capture_dir with exclusive creation. Agent imported the saved module successfully and exercised make_request with mocked fetches in temporary directories. Simulated HTTP 503 produced only error.json, preserving endpoint/payload/status/reason/Retry-After/content-type/body preview and a valid UTC failed_at; original HTTPError was re-raised. Simulated successful fetch preserved original bytes, returned retrieval metadata, and write_manifest produced a matching timestamp/size with no error.json. Reusing an existing attempt raised FileExistsError before fetch and left prior error bytes unchanged. Syntax/import and those behavior checks passed. No BLS call, cloud action, or original capture modification occurred.

Next learner design checkpoint is bounded retry coordination above make_request: retain one run ID/date while giving each network attempt its own attempt_id directory (001, 002, 003); max_attempts=3 means three total calls, not three retries after the initial call. Begin with the observed HTTP 503 condition; do not retry every exception or suppress final failure. Use server Retry-After when provided, otherwise a proposed local learning policy of five then fifteen seconds between attempts. Parsing a supplied Retry-After and enforcing an overall deadline must be addressed before live retry execution; this remains a design proposal, not implemented behavior. Keeping the retry loop outside make_request lets its existing single-attempt error/response recording remain reusable. Current main still runs only one attempt with a fresh run ID per execution. Next work remains learner-written retry wrapper/offline simulation, then bounded historical batching. No broad live backload is authorized by this offline verification.

### Retry structure — stable run directory refactor issued October 24, 2026

Learner added run_with_retries with a loop formatting attempt IDs 001–003 and printing paths. Agent inspected saved code: main currently uses get_capture_dir().parent and calls only this print-only loop, with earlier live-request/manifest calls commented out. This is a temporary non-network scaffold, not implemented retry execution. No claimed terminal output or retry runtime evidence is added here.

Next learner refactor makes the permanent ownership explicit: rename get_capture_dir to get_run_dir, remove its attempt_id variable and attempt path component, name/return the resulting Path run_dir, and call `run_dir = get_run_dir()` in main. It still defines ingestion_date/run_id once per invocation without creating directories. run_with_retries retains responsibility for appending attempt_id paths, while make_request creates and records each attempt. Leave the loop non-network until transient-error conditions, delay/Retry-After handling, final re-raise and success return are implemented/reviewed. This refactor preserves the source/date/run/attempt layout used by existing response/manifest helpers and introduces no second resource configuration.

Expected structural verification: run_dir ends at run_id, all loop paths share that run ID, and each has a distinct attempt_id. Subsequent coordinator wiring should call make_request for an attempt, write a manifest and immediately return on success; HTTP retries must not catch manifest/local-file failures as source outages. Learner source edits and offline verification are pending; agent source/runtime execution not performed for this guidance.

### Run-directory refactor reviewed; coordinator implementation next — October 24, 2026

Agent inspected learner code after the reported edit. get_run_dir now generates ingestion_date/run_id without an attempt component, and main calls it directly before the print-only coordinator. The local variable remains named capture_dir but denotes the run path; this is functional, with an optional clarity rename later. No source call was executed by the agent.

Next learner implementation replaces print-only behavior with one make_request(attempt_dir, payload) inside a narrowly scoped try. Catch HTTPError; re-raise for non-503 errors or final attempt. For a retry-eligible 503, delay before continuing to the next attempt. Write the success manifest outside the HTTPError retry try-block, then return capture immediately so later attempts do not run after success. Add import time for sleep. Proposed fallback delays remain five then fifteen seconds for the three-total-attempt policy; if Retry-After is present, do not retry earlier than instructed. Header parsing/delay bounds/overall deadline need review before live execution, and no live call is requested while the learner drafts this coordinator. Final failure must propagate, not silently fall out of the loop. Broad request batching and source acceptance checks are later work.

Expected offline review cases: first-attempt success calls fetch once; 503 followed by success creates distinct same-run attempt paths and one delay; three 503s stop after three attempts with no final delay; a nonretryable HTTP error stops immediately; manifest/local-write errors propagate without causing a refetch. Implementation and offline coordinator checks remain pending. Existing single-attempt error/response/manifest evidence remains valid.

### Coordinator review before delays — October 24, 2026

Agent read the saved run_with_retries after the learner asked to proceed. It calls make_request in try and writes the manifest in else, but is missing return capture after successful manifest writing. Without it, the loop fetches again even after success. Its exception comment also says not to retry 503 while its condition actually permits retry for 503 with attempts remaining. Correct the success return and comment before invoking the live main. No coordinator execution was performed by the agent.

Next learner helper: get_retry_delay(attempt_number, retry_after) returns seconds to wait, independently of sleeping or fetching. Proposed policy: absent header means five seconds after attempt 1 and fifteen after attempt 2; a valid header is either nonnegative integer seconds or an HTTP date, converted to a nonnegative remaining duration using UTC. Do not truncate a server-requested wait to retry earlier. For this interactive learning run, if the required wait exceeds a selected 60-second per-delay bound, stop/defer the run rather than retrying early; malformed headers should stop with a clear error pending policy review. These limits are proposed application choices, not BLS guarantees. RFC 9110 section 10.2.3 was consulted for header formats. Draft/review helper before adding time.sleep to the coordinator; bounded overall execution and additional exception categories remain later work. No new API request or error capture observed in this review.

### Initial retry coordinator — offline scenarios passed October 24, 2026

Saved learner coordinator now uses MAX_ATTEMPTS=3, fallback RETRY_DELAYS=(5,15), HTTP 503-only retry eligibility, final-attempt re-raise, conservative immediate stop when Retry-After is present (parsing not implemented), and return after successful manifest writing. import time is present. Agent ran isolated behavior checks with temporary attempt directories, mocked fetch_bls, and mocked sleep: first success makes one fetch/no sleep; 503 then success makes two fetches/one five-second delay call; three 503s make exactly three fetches with five/fifteen-second delay calls and no final sleep; 403 stops immediately; 503 with Retry-After stops immediately without sleeping; manifest OSError propagates without refetch. Attempt IDs and per-attempt success/error artifact sets matched expectations. All six scenarios passed. No real API call, actual sleep, cloud operation, or existing capture mutation.

Small pending corrections: the exception comment still incorrectly says not to retry 503; change it to retry 503 only while attempts remain and no server wait instruction requires deferral. max_attempts accepts arbitrary values while the delay tuple supports at most three total attempts: validate 1 <= max_attempts <= len(RETRY_DELAYS)+1 before entering the loop so zero cannot silently succeed and larger values cannot exhaust delay indexes. MAX_RETRY_DELAY=60 is currently unused because header parsing remains deferred and fixed fallback delays are below the proposed bound; do not claim that constant enforces an overall deadline. Additional network-error categories/failure capture, Retry-After parsing, run-level deadlines and broader historical batching remain pending. Three-attempt default behavior is verified offline, not live retry recovery.

### Retry guard complete; historical batch planning begins — October 24, 2026

Learner saved the range guard and corrected the 503 comment. Agent inspected the saved coordinator and checked zero/four attempt values with mocked make_request: both raise ValueError before any request. No real HTTP call, sleep, or output file occurred. Prior six offline coordinator scenarios remain the default-behavior evidence. Retry-After is still conservatively deferred, other network categories/overall deadlines remain pending; this is sufficient to continue non-network request planning, not an instruction to launch the backload.

**Next learner module:** `code/bls_request_plan.py`, which imports INVENTORY_PATH and load_series_inventory from bls_inventory (safe main guard) and defines `batch_series(series, batch_size=25)`. Convert configured records to their series_id strings, split into consecutive lists with at most batch_size elements, and return the list of batches without requests or writes. Reject batch_size <= 0. Preserve inventory order; do not drop the final partial batch. Under main, load the config, call the batcher, and print batch count and each batch size.

**Expected result:** 248 configured IDs become ten batches: nine of 25, one of 23; their flattened IDs exactly match the configured IDs in order, without loss/duplication. This uses current unregistered BLS limits already checked. Next combine batches with baseline year windows 2015–2024 and 2025–2025 (11 years requires two windows under the ten-year per-request limit), giving twenty planned baseline requests before catch-up/retries. This arithmetic is a plan, not executed ingestion; daily budget accounting and restart/work-item identity must precede live backload. Catch-up/latest-source-month and six-reporting-month refresh remain separate stages. Learner module creation, batching implementation, and execution pending.

### Series batching — learner execution and offline checks passed October 24, 2026

Learner implemented batch_series in code/bls_request_plan.py with positive batch-size validation, extraction of configured series IDs, consecutive list slicing in a while loop, and returning the batches. Supplied output is 10 batches with sizes [25,25,25,25,25,25,25,25,25,23]. Agent inspected saved source and exercised the pure planner offline: flattened batches exactly match all 248 unique configured IDs in order; original metadata input is unchanged; empty input returns []; zero/negative sizes raise ValueError. No API request or ingestion output generated. This validates batch grouping, not response coverage or successful historical loading.

Next learner function in the same planner: `build_year_windows(start_year, end_year, max_years=10)`, returning inclusive (start,end) integer pairs. For 2015 through 2025, expected windows are [(2015,2024),(2025,2025)]. Each window end is the lesser of start+max_years-1 and requested end; next start is previous end+1. Reject max_years <= 0 and start_year > end_year. This preserves all eleven baseline calendar years without overlaps/gaps and respects the currently applicable ten-year unregistered request limit. Keep registration-dependent settings configurable; no new API request is needed to build the plan.

After learner year-window output is verified, combine the ten series batches with the two year windows to produce twenty baseline request payloads, preserving work-item identity for later restart planning. Initial catch-up is separate from this 2015–2025 baseline. Request-count/retry budget, checkpoints, failure classification, and live source freshness still require review before execution.

### Historical year windows — verified October 24, 2026

Learner supplied planner output: ten series batches [25,25,25,25,25,25,25,25,25,23] and year windows [(2015,2024),(2025,2025)]. Agent inspected build_year_windows and checked it offline: baseline, single-year range, exact ten-year boundary, and one-year windows match expected inclusive coverage without overlap/gaps; reversed years and nonpositive window sizes raise ValueError. No network or ingestion execution occurred. Saved planner constants are BATCH_SIZE=25, MAX_YEARS=10, START_YEAR=2015, END_YEAR=2025; these plan the historical baseline under current unregistered limits, not initial catch-up or monthly refresh.

Next learner function in the same planner: `build_request_payloads(batches, windows)`. Use nested loops so each batch is paired with each (start_year,end_year) tuple, append a dictionary with seriesid=batch and startyear/endyear as strings, then return the list. Preserve the API field names and do not confuse internal snake_case metadata with outgoing API keys. Expected twenty payloads, each at most 25 IDs and at most ten inclusive years. Main should print payload count and the first payload for review, without importing/calling fetch or the live ingestion entry point. Following work includes stable work-item IDs, plan persistence/restart, daily request/retry budgeting, source-level acceptance, and only then learner-executed broader requests. Payload construction implementation/execution remains pending.

### Historical request payloads — verified October 24, 2026

Learner planner output shows ten batches, two baseline year windows, twenty payloads, and the first 25-series payload using seriesid/startyear/endyear with string years 2015/2024. Agent inspected the saved build_request_payloads and tested it offline: twenty dictionaries have exactly those API keys, no more than 25 unique series and ten inclusive years each, and together cover all 496 expected selected-series/year-window pairs exactly once (248 series times two windows). No API request, raw backload, or cloud action occurred.

Next learner helper: `build_request_id(payload)` in the planner. Serialize with json.dumps(payload, sort_keys=True), UTF-8 encode, and return the full hashlib.sha256(...).hexdigest(). This stable ID identifies the same configured BLS payload within the plan and is distinct from a run_id (execution instance) and attempt_id (one try). Preserve current series order when hashing; sort_keys canonicalizes dictionary keys, not list order. Identical payloads yield identical IDs; a changed requested year range yields a different ID. These IDs do not alone prove prior completion or allow skipping records: later durable source validation/checkpoint evidence must support restart decisions. Keep credentials out of the planned payload/hash and durable plan when registration is later introduced.

Expected first check: print build_request_id(payloads[0]) twice and verify equal 64-character strings without fetching. Then attach IDs to work items and persist a reviewed plan before execution. Twenty planned baseline requests are not a daily budget: retries, earlier daily calls, and initial catch-up also consume requests under source limits; execution/restart budgeting remains pending. No live backload instruction issued.

### Stable request IDs — verified October 24, 2026

Learner ran the planner and printed the same first-payload ID twice: `34cdda8fd8155dc8b1a687b3cb00bdb2f40089ece51b3341adafecd873061f67`. Agent inspected build_request_id and checked it offline: reported hash matches, repeated input matches, reversed dictionary-key insertion order matches, a changed end year changes the ID, and all twenty baseline payload IDs are unique. This hashes the planned request, unlike the separate checksum of actual response bytes. Canonicalization preserves series-list order; reordering/rebatching IDs creates different payload identities. No API or cloud action occurred.

Next learner task: assemble work_items as a list of dictionaries, one per payload, with request_id=build_request_id(payload) and payload=payload. This wrapper is local planning metadata; send only its nested payload to BLS later, not the request_id field. Print len(work_items) and work_items[0] for review; expected twenty items with stable IDs and intact API payloads. Do not mark them completed or infer prior completion from an ID alone. Persisting the reviewed plan, associating attempts/manifests with request IDs, validating completion, and budgeted/restartable execution remain pending. Draft construction in the planner main block is sufficient; a new helper is optional, not required for this small transformation.

### Historical work items — verified October 24, 2026

Learner planner output shows twenty work items and the first request_id/payload pair. Agent inspected the saved build_work_items and checked it offline: exactly twenty unique IDs; every ID matches build_request_id of its unchanged nested payload; wrapper keys are exactly request_id/payload; JSON serialization round trip preserves the structure; empty payload input returns []. No BLS request, run capture, or cloud action occurred. This verifies planned identity association, not completion tracking or backload execution.

**Next learner checkpoint — save reviewed baseline plan:** Define PLAN_PATH as INVENTORY_PATH.parent / f"bls-historical-plan-{START_YEAR}-{END_YEAR}.json". Destination currently does not exist. In planner main, after work_items construction assemble a plan dictionary with source="bls", mode="historical", start_year/end_year from baseline constants, series_inventory=INVENTORY_PATH.name, series_inventory_sha256 computed over INVENTORY_PATH.read_bytes(), and work_items. The checksum links the plan to exact inventory definitions; request IDs identify payloads, not the source metadata inventory. Use PLAN_PATH.open("x", encoding="utf-8") and json.dump(plan, file, indent=2), then print the saved path. Never mark work items completed merely because they were planned or saved.

Expected result: config/bls-historical-plan-2015-2025.json containing twenty unchanged work items and inventory provenance. This is generated nonsecret execution configuration, separate from raw source data and dated verification evidence. Save once; if the path already exists, inspect the saved plan rather than replacing it automatically. Agent did not create or prefill the plan. After learner save, validate file bounds/IDs/inventory hash before daily-budget/restart design and before live execution. Initial catch-up and ongoing six-month refresh plans remain separate from this frozen baseline. Plan assembly/write and execution remain pending.

### Historical baseline plan — saved and verified October 24, 2026

Learner ran bls_request_plan.py and supplied the saved config/bls-historical-plan-2015-2025.json path. Agent read the 21,421-byte saved plan without regenerating it. Checks passed source=bls/mode=historical, baseline 2015–2025, exact current inventory SHA-256 match, twenty unique request IDs matching their payload hashes, <=25 IDs/<=10 inclusive years per payload, and exact coverage of all 496 expected series/window pairs without duplication. File SHA-256 is `b8be6a68633825b379b757a14940079cc7c45fab2421c116c28dea2464e8e488`. No source request or cloud operation occurred. This is a frozen baseline plan, not executed backload or completed work items.

Before live execution, enforce a run-wide request budget: twenty initial payloads can produce up to sixty HTTP attempts under a three-attempt-per-request policy, exceeding the currently documented unregistered daily limit of twenty-five even before earlier calls/catch-up. Twenty-five is a published service limit, not proof of remaining personal allowance. Daily usage/reset provenance and registration choice need resolution; do not launch the entire plan with unrestricted per-item retries.

Next learner safety checkpoint: create code/run_bls_plan.py as a plan-reading entry point, initially non-network. Implement load_historical_plan(plan_path): read JSON; resolve series_inventory beside the plan; hash the referenced inventory bytes; compare with series_inventory_sha256 and raise ValueError if different; return the plan when it matches. This prevents a changed inventory from silently being used with a previously approved plan. Print len(plan["work_items"]) for the saved plan, expected twenty. Source fetching/sleep/retry calls do not belong in this initial dry-run main. This reader is distinct from the planner: it consumes the frozen file instead of regenerating/writing it on every invocation. After review, add runtime plan validation, request-budget/checkpoint design and limited execution in explainable stages. Reader code/runtime evidence remains pending; agent has not implemented it for the learner.

### Plan-reader hash comparison correction — October 24, 2026

Learner run_bls_plan.py raised ValueError("Inventory differs from the saved plan"). Agent inspected saved code and independently hashed the referenced inventory: actual and plan-recorded SHA-256 both equal `762218dcde8045167a452e0969c79132cbe96e1f1880695c35e81ae028c8fcf7`. The inventory has not mismatched the saved checksum. Saved loader uses `.hexdigest` without parentheses, so check_hash holds a method object rather than a digest string. Learner correction is `.hexdigest()`, followed by rerunning the non-network plan reader; expected output twenty. No source/config regeneration, live request, or learner code edit performed by agent. Reader execution after correction remains pending.

### Frozen plan reader — learner execution confirmed October 24, 2026

After correcting .hexdigest() invocation, learner ran `python code/run_bls_plan.py` and supplied output twenty with no error. This confirms the current runner parses the frozen baseline plan and validates its inventory checksum; it does not execute work items. Previous independent hash comparison confirmed the referenced inventory matches. No BLS request or cloud operation is established by this reader output.

Before live execution, choose source access/usage policy. Current request is unregistered with documented twenty-five daily queries; the frozen plan contains twenty base requests and may require retries. A separate BLS registration key increases documented limits; it is unrelated to Google Cloud credentials and must be injected into outgoing requests at runtime rather than saved into request config, plan, manifest, or diagnostic payload logs. Existing manifests currently include payload verbatim, so credential redaction/separation must precede any registered request. Choosing registered access does not require replacing the valid conservative twenty-request plan. Regardless of registration, add explicit call budgeting, failure/restart tracking and completion validation before broad backload. No live-run instruction or key setup performed at this checkpoint.

## BLS registration completed — learner screenshot October 25, 2026

Learner supplied the official registration confirmation page stating registration completed successfully and the Public Data API can continue to be used. This supersedes the earlier registration-page busy observation; it does not prove API service recovery, key injection, or higher-limit request execution. The screenshot's validation URL/token and any email/key are intentionally not transcribed or fetched. Current saved fetch_bls still sends only the original nonsecret payload, without a registrationkey. Official BLS guidance requires including the issued key in requests to receive registered access limits; Google Cloud identity remains separate.

**Next learner checkpoint — configure key in current terminal only:** In zsh, run `read -rs "BLS_API_KEY?BLS API key: " && export BLS_API_KEY`, paste the issued key into the hidden prompt, then press Enter. The command contains no literal key and the prompt input is not shell-history command text. Verify presence only with `python -c 'import os; print("BLS key configured:", bool(os.getenv("BLS_API_KEY")))'`. Expected True; never print/paste the value. This terminal environment is temporary and inherited by Python processes started from that terminal; it is not a permanent shell configuration or a cloud secret setup.

Next code checkpoint will inject the environment key into a new outgoing payload copy inside fetch_bls while preserving the original nonsecret payload for plan/request IDs, manifests and errors. Do not modify payload in place or add the key to JSON config; durable logging currently records payload verbatim. Offline checks must establish the key is absent from persisted records before any registered request. The existing conservative twenty-request plan remains usable; no regeneration or larger-batch execution is instructed. Environment setup, key integration/registered request validation, request budgeting and broad backload remain pending. Reference: [BLS registration and limits](https://www.bls.gov/developers/api_faqs.htm).

### BLS key environment presence — learner-confirmed October 25, 2026

Learner supplied presence-only output `BLS key configured: True`. This confirms a nonempty BLS_API_KEY was visible to Python launched from that learner terminal; the agent did not read the key and this does not establish key validity, registered API acceptance, permanent configuration, or Cloud Run secret setup. Current saved fetch function was inspected and still serializes the nonsecret original payload, so runtime key injection remains pending.

Next learner edit: import os; inside fetch_bls read BLS_API_KEY from the environment (strip whitespace, fail clearly if missing/blank); create a separate outgoing dictionary combining original payload and registrationkey; JSON-encode that copy for Request.data. Do not mutate payload, put the key in constants/config/plans, or print the outgoing body. Original payload remains the source of request IDs and persisted manifest/error request_params. Share the saved edit before live execution; offline checks will verify the dummy key is present in outgoing bytes and absent from original payload/durable request_params, and review any error-body credential echo before registered diagnostics are persisted. The twenty-request plan is unchanged. Key validity, registered response, request budgeting, restart and broad execution remain pending.

## Accelerated implementation boundary — October 25, 2026

Learner clarified that implementation code must be provided in chat for them to add/run, rather than edited into code files by the agent. Agent removed only the newly created pipeline_common.py and empty tests directory from the immediately preceding implementation attempt; existing learner files were unchanged. Documentation edits/read-only local inspection/offline checks remain allowed. Learner owns live source ingestion, transformations/loading, cloud uploads, and all console resource creation. Prior broader agent-coding permission is superseded by this instruction. Work now proceeds in larger source-to-output stages with explanatory comments rather than repeated micro-checkpoints.

### Historical BLS Bronze baseline — learner-executed, verified October 25, 2026

Learner created the chat-provided standalone backfill_bls.py and ran it with --execute. Run 7882c36124674a5cbe44f04a8b32c715 captured all 248 configured series for 2015–2025 in five registered-API batches. Supplied accepted observation counts are 6600,6600,6600,6600,6336. Agent inspected saved summary/response manifests offline: complete status; checksums and byte sizes match all five original responses; 32,736 monthly observations total with 50 source-missing markers. This establishes local historical BLS capture, not BigQuery loading, cloud Bronze upload, source catch-up, or monthly automation. The fifty missing markers remain source-level missing values, not zero or failed API requests.

### Next source checkpoint — SNAP historical archive capture, instructions issued

Learner will create code/backfill_snap.py from code supplied in chat. It discovers the historical ZIP link from the official USDA SNAP data-tables page (or accepts an explicit archive URL), downloads original ZIP bytes into immutable source/date/run/attempt Bronze, validates the twelve fiscal-year members FY2015–FY2026 needed for January 2015–December 2025, and records archive/member checksums without modifying workbooks. Dry-run mode makes no calls; --execute is learner-run. Source archive structural/member validation does not prove parsed 50-state/month measurements; that acceptance belongs to the subsequent Silver stage. Keep the regional-sheet and missing/anomalous-value rules from source-schemas.md. No agent source download or SNAP ingestion execution performed. The default USDA main hostname returned 403 to the read-only page tool; its official azureedge data-tables page was accessible and lists the historical ZIP and July 2026 latest publication, not accepted 2026 pipeline coverage. Files and APIs for this next stage remain learner-executed/pending.

### SNAP archive capture — learner-executed, verified October 25, 2026

Learner created chat-provided backfill_snap.py and executed it. Run a4a640c086d74c21b472f08f84306277 attempt 001 contains accepted archive.zip and manifest.json. Agent read the local files: archive size 1,661,153 bytes; archive checksum and all twelve FY2015–FY2026 selected workbook checksums match. Original ZIP is preserved. This validates capture/member identity only; no 6,600-state-month parse result is yet claimed. Read-only XLSX XML inspection confirms regional-sheet state headers/month labels and unscaled A–F roles match documented contracts. No agent source download or transformation occurred.

### Next checkpoint — local PySpark Silver from saved Bronze

Learner will install openpyxl/xlrd into the already-active repo .venv (currently absent at inspection); PySpark and PyArrow are already present. Chat-provided build_silver.py will verify Bronze hashes, parse regional XLS/XLSX state sections, preserve raw strings/footnotes and manifest/row lineage, enforce exact baseline keys, normalize CES thousands to jobs, preserve missing rates as NULL/status, and flag negative SNAP benefits without altering them. It writes new versioned Silver Parquet tables for BLS observations and SNAP state/month measurements using local PySpark. No API/network/cloud operation belongs in this stage. Negative Wyoming benefit values remain preserved and require benefit-specific reporting exclusion/review; participant comparisons remain independently evaluable.

Expected baseline outputs: 32,736 BLS source-grain monthly observations (50 known source-missing rate values from current capture) and 6,600 unique SNAP state/month records. Expected status is a target, not executed Silver evidence. Learner owns installation and transformation execution; agent only supplies code in chat. Subsequent Gold dimensions/facts and BigQuery load remain pending. Source catches/refresh are outside this baseline execution and remain explicitly pending.


### Local historical Silver — completed October 25, 2026

Purpose: normalize the accepted historical captures at source grain before modeling Gold. Prerequisites: completed BLS run `7882c36124674a5cbe44f04a8b32c715`, SNAP run `a4a640c086d74c21b472f08f84306277`, and the learner-created `code/build_silver.py` with its dependencies.

Learner executed:

```bash
python code/build_silver.py \
  --bls-run "data/bronze/bls/ingestion_date=2026-10-25/run_id=7882c36124674a5cbe44f04a8b32c715" \
  --snap-manifest "data/bronze/snap/ingestion_date=2026-10-25/run_id=a4a640c086d74c21b472f08f84306277/attempt_id=001/manifest.json"
```

Observed evidence: learner output and saved `summary.json` both report complete status, 32,736 BLS observations, 6,600 SNAP state/month rows, 50 BLS source-missing values, and one SNAP benefit review row. Output: `data/silver/ingestion_date=2026-10-25/run_id=7282829984ac46e1912d2edc0622daf0`. Source parsing, normalization, and Parquet writes completed locally. Spark hostname, native-library, task-size, and pandas compatibility warnings were printed; none aborted this run. The agent did not execute ingestion or ETL.

### Next checkpoint — local historical Gold

Purpose: create the accepted three dimensions and two facts from the completed Silver version, retaining source statuses and lineage. Learner creates `code/build_gold.py` from chat-provided code and runs it with `--silver-run` pointing to the completed Silver directory. Expected targets: 50 states, 132 monthly dates, three industries, 6,600 state/month facts, and 19,536 supported industry facts. These remain targets until execution is observed.

Use expected membership/calendar grids and reject missing source rows or duplicate keys before joins. Preserve legitimate NULL measurements and the flagged benefit value in facts. A jobs/participation report requires all 50 states per month; an all-three-industry report uses the common 48 supported states and requires all 144 state/industry combinations per month. Benefit-specific comparisons require a separate review-aware reporting filter. Initial revision metadata describes a first load only; incremental comparison and old/new revision logs remain pending. Write a new version and single Parquet part per output for subsequent learner-run BigQuery loading. No cloud resources are created by the local stage.


### Local historical Gold — completed October 25, 2026

Learner executed `python code/build_gold.py --silver-run "data/silver/ingestion_date=2026-10-25/run_id=7282829984ac46e1912d2edc0622daf0"`. First execution failed before output creation because Spark received a dictionary keys view in `isin`; learner replaced it with `[code for code, _ in INDUSTRIES]` and reran successfully. No source changes or cleanup were required.

Observed learner output and saved summary agree: `dim_state` 50, `dim_date` 132, `dim_industry` 3, `fact_state_month` 6,600, `fact_state_industry_month` 19,536, `report_jobs_snap` 6,600, and `report_industry_month` 19,008 rows. Completed output is `data/gold/ingestion_date=2026-10-25/run_id=9b11e5713cbe4ba6abc45d7cdd2b622e`; its summary identifies the Silver version and individual Parquet load files. This establishes the learner-executed local historical ingestion → Bronze → Silver → Gold milestone. It does not establish BigQuery loading, cloud Bronze copies, catch-up, six-month refresh, or revision-history execution.

### Next checkpoint — create the GCP Gold dataset

Purpose: provide a separate BigQuery namespace for the accepted analytical tables. Prerequisite: completed local Gold output and the existing selected GCP project. In BigQuery Studio, open the project actions menu, choose Create dataset, enter `jobs_snap_gold`, select Region `us-central1`, retain Google-managed encryption, and leave default table expiration unset for this baseline. Create the dataset, then verify its Details show the intended project, dataset ID and location. This is learner-executed console work; dataset creation remains pending confirmation. Individual Parquet table loading follows after dataset verification. Reference: https://docs.cloud.google.com/bigquery/docs/datasets.


### GCP Gold dataset — learner-confirmed October 25, 2026

Learner reported done after instructions to create `jobs_snap_gold` in `us-central1` with no default table expiration and Google-managed encryption. Dataset creation is learner-confirmed; no screenshot or independent cloud lookup was supplied at this checkpoint.

Next load checkpoint: in BigQuery, select `jobs_snap_gold` → Create table → Upload; select the single `part-*.parquet` file from the completed Gold run's `dim_state` directory, choose Parquet format and native table name `dim_state`, and use its embedded schema. Leave partitioning/clustering unset for this small dimension. Create the table and verify Preview/Details show 50 rows, with state FIPS/key fields kept as STRING. Repeat only after successful first-load confirmation for the other four core tables. Ignore `_SUCCESS` and filesystem checksum files. No table load is yet confirmed. Reference: https://docs.cloud.google.com/bigquery/docs/loading-data-local.


### BigQuery Gold table loads — learner-confirmed October 25, 2026

Learner confirmed loading `dim_state`, then `dim_date`, `dim_industry`, `fact_state_month`, and `fact_state_industry_month` as native tables in `jobs_snap_gold` from the corresponding single-part Parquet files in local Gold run `9b11e5713cbe4ba6abc45d7cdd2b622e`. Instructions used console Upload, Parquet embedded schemas and no partitioning/clustering. Learner observed identical FIPS/state keys with leading zeros preserved; their duplication in the dimension was discussed and retained. Load jobs, cloud row counts and relationships have not been independently inspected. Local report Parquet files have not been uploaded.

Next verification: learner runs a read-only GoogleSQL query in the selected project to compare five table counts against 50/132/3/6600/19536, count distinct business keys, and check both facts for orphan dimension references. Expected: counts match, no duplicate keys or orphan rows. This checks the warehouse load, not source reconciliation or monthly automation. Reporting views follow after results. Source exceptions remain in fact statuses; complete reporting scope must still be enforced.


### BigQuery baseline count/key/relationship check — passed October 25, 2026

Learner supplied the read-only query result: all five rows passed. dim_date expected/actual/distinct 132; dim_industry 3; dim_state 50; fact_state_industry_month 19,536; fact_state_month 6,600. Every invalid_keys count is zero. This confirms the loaded row counts, unique modeled business keys and fact-to-dimension references for this baseline. It is not a complete source-value reconciliation or incremental/revision test.

Next checkpoint: learner runs chat-provided CREATE VIEW statements for `v_jobs_snap` and `v_industry_month` in BigQuery Studio. These logical views read the native facts and dimensions. Jobs/participation requires available, non-NULL jobs and SNAP persons for all 50 states in a month; unemployment and benefit dollars are not required inputs. The industry view explicitly excludes Delaware/Hawaii for its common three-industry comparison and requires all 144 valid state/industry combinations per month. Expected view rows are 6,600 and 19,008 respectively; create/query success remains pending learner evidence. Benefit-dollar reporting is not exposed by these views and still requires review-aware acceptance.


### BigQuery reporting views — learner-confirmed October 25, 2026

Learner reported done after receiving CREATE VIEW statements for `jobs_snap_gold.v_jobs_snap` and `jobs_snap_gold.v_industry_month` plus a view-count query. Creation is learner-confirmed; exact returned view counts were not pasted, so 6,600 and 19,008 remain expected cloud view counts rather than independently observed results. The views enforce complete 50-state jobs/participation months and common 48-state, three-industry months respectively. They do not expose benefit dollars or require missing unemployment values for unrelated comparisons.

Next analytical checkpoint: run a read-only query against `v_jobs_snap` comparing January 2015 with December 2025 by state, calculating absolute job/participant changes and percent changes with SAFE_DIVIDE. Expected grain is one row per state (50 rows for this baseline). Payroll jobs and participants describe different populations; changes show association, not causation. SNAP participation is not seasonally adjusted, and comparing different calendar months can include seasonal effects. A same-calendar-month comparison is an optional follow-up. Real-source cloud Bronze/Silver copies, initial source catch-up, six-month refresh, revision history and orchestration remain pending.


### First BigQuery analytical result — observed October 25, 2026

Learner supplied all 50 rows from `v_jobs_snap` comparing January 2015 and December 2025. Idaho: payroll jobs 662,600 → 882,100 (+219,500; +33.13%); SNAP persons 199,944 → 123,859 (-76,085; -38.05%). These are warehouse query results over the accepted captured baseline, not causal estimates or population-adjusted rates. Different states show different directions of participation change. The result also demonstrates successful querying of the jobs/SNAP view, although the separate two-view count result has not been supplied.

### Next checkpoint — preserve accepted historical Bronze in Cloud Storage

Purpose: retain original source captures and manifests in the existing private `jobs-snap-bronze-620503845148` bucket. In the console Objects tab create/open `bls/ingestion_date=2026-10-25/`, then Upload folder selecting local `data/bronze/bls/ingestion_date=2026-10-25/run_id=7882c36124674a5cbe44f04a8b32c715`. Repeat under `snap/ingestion_date=2026-10-25/` selecting `data/bronze/snap/ingestion_date=2026-10-25/run_id=a4a640c086d74c21b472f08f84306277`. Upload folder preserves nested run/batch/attempt layout; use Chrome if the current browser does not expose folder uploads. These are copies of existing original bytes, not fresh source requests. Preserve manifests unchanged, including their original local-path lineage; portable cloud path resolution remains future implementation work.

Read-only local inspection before upload counted 12 BLS files totaling 2,920,338 bytes and three SNAP files totaling 1,712,571 bytes. Expected remote run folders contain BLS inventory/summary and five batch response/manifest pairs, and SNAP attempt 001 archive/manifest/landing HTML. Verify upload completion and the expected object paths; cloud object counts and byte/hash reconciliation remain pending. The bucket already represents Bronze, so source prefixes start at `bls/` and `snap/`, without an extra `bronze/` directory. Reference: https://docs.cloud.google.com/storage/docs/uploading-objects.


### Historical cloud Bronze copies — learner-confirmed October 25, 2026

Learner confirmed uploading the complete BLS run folder under `gs://jobs-snap-bronze-620503845148/bls/ingestion_date=2026-10-25/`, then the complete SNAP run folder under `gs://jobs-snap-bronze-620503845148/snap/ingestion_date=2026-10-25/`. Clarified that these uploads contain captured data/manifests, not Python scripts. Remote object lists, counts and checksums have not been independently inspected. Local originals remain the executed processing inputs; cloud copies do not establish cloud ingestion or Spark execution.

Next acceptance query: learner checks exact view row counts (6,600 and 19,008), missing unemployment values (50), and retained negative/review-required SNAP benefits (one each) in BigQuery. These confirm the known source exceptions survived the native table load. Exact query output remains pending. Catch-up to each source's latest month, six-month monthly refresh, current-fact merging/revision logs and cloud orchestration are not implemented. Read-only inspection confirms existing backfill scripts still fix years at 2015–2025; they must not be treated as catch-up-ready by changing constants without adapting validation and downstream baseline assumptions.


### BigQuery view scope and source-exception check — passed October 25, 2026

Learner supplied exact query results: jobs_snap_rows 6,600; industry_rows 19,008; missing_unemployment 50; benefit_review_rows 1; negative_benefit_rows 1. Both reporting scopes and the retained source exceptions match the executed local baseline. No missing unemployment was zero-filled and the anomalous benefit amount remains preserved/flagged.

### Next checkpoint — 2026 BLS catch-up Bronze

The baseline remains immutable. Chat guidance adds an optional validator callback to `backfill_bls.capture_batch`, defaulting to its existing full-year validator, and a separate learner-created `catchup_bls.py`. This reuses authentication, retries, raw-byte preservation and manifests while accepting an incomplete publication year. Each requested series must have contiguous monthly rows from January through its own latest returned month; unequal latest months are reported per series, not silently forced to a common cutoff. Missing-value markers remain source missing. It requests 2026 in five registered batches, saves a new Bronze run and does not update Silver/Gold. Dry-run then learner-authorized --execute are required; catch-up execution remains pending. Initial catch-up is distinct from the later six-month refresh. The official USDA SNAP page inspected October 25 lists July 2026 as its latest month; selected workbooks still need their own parsed coverage verification. Do not assume SNAP and BLS share a cutoff.


### BLS 2026 catch-up Bronze — completed, run dated October 26, 2026 UTC

Learner executed `python code/catchup_bls.py --execute`. Run `43e4e0749e4349ceb1f92122acfc26a6` accepted 450/450/450/450/432 monthly observations (2,232 total), 248 series over January–September 2026. Every latest-series cutoff is 202609. Saved summary inspected read-only confirms complete status and frozen inventory hash. Run date is 2026-10-26 in UTC even if local execution was still October 25. Catch-up Silver/Gold and cloud upload of this new run remain pending.

Read-only inspection of the previously captured FY2026 SNAP workbook found January–September labels on all seven regional sheets; sampled July rows contain numeric measurements while August/September rows contain '--' placeholders. Labels alone do not establish publication. Reuse the original archive for January–July 2026 parsing; all-state row coverage and measurements will be checked by the learner-run Silver stage. No new SNAP download is required for those saved months.

Next checkpoint: add optional target-month sets to the existing Silver parsers while preserving their baseline defaults, then learner creates/runs `build_silver_catchup.py` from chat. It parses only the new requested source periods, reads the existing baseline Parquet, checks unique keys and matching inventory, and writes a new combined Silver version. Expected BLS 34,968 rows (32,736 + 2,232) through September 2026 and SNAP 6,950 rows (6,600 + 350) through July 2026. This stage does not revise older baseline measurements or update Gold; source-lag-aware Gold modeling follows separately. Prior captures/outputs remain unchanged.


### Initial catch-up Silver — completed, run dated October 26, 2026 UTC

Learner executed chat-provided `build_silver_catchup.py` with baseline Silver `7282829984ac46e1912d2edc0622daf0`, BLS catch-up `43e4e0749e4349ceb1f92122acfc26a6` and the original SNAP manifest. New Silver version `4a67bce75c5d4c5680b158119930c6ec` completed: 34,968 BLS rows through September 2026 and 6,950 SNAP rows through July 2026. Learner output and saved summary agree; 50 missing BLS values and one flagged SNAP benefit remain. Agent only inspected files; no transformation execution performed.

Next: learner copies `build_gold.py` to `build_gold_catchup.py` and applies chat-provided edits to accept combined Silver, extend the monthly grid to the BLS cutoff, validate SNAP only through its independently accepted cutoff, and mark later SNAP statuses `not_yet_published`. No values are filled with zero. Expected dimensions 50/141/3, state facts 7,050, industry facts 20,868, jobs/SNAP report 6,950 and common-industry report 20,304. A fresh versioned Gold rebuild is not a revision-aware merge: original historical outputs remain retained and incremental first-load/revision preservation remains pending. BigQuery continues to contain the historical baseline until learner explicitly publishes the catch-up output.


### Initial catch-up Gold — completed, run dated October 26, 2026 UTC

Learner executed `build_gold_catchup.py` on combined Silver `4a67bce75c5d4c5680b158119930c6ec`. Gold run `6efac951e42245c389eb7659d92a8fa4` completed with dimensions 50/141/3, state facts 7,050, industry facts 20,868, jobs/SNAP report 6,950 and industry report 20,304. Learner output and saved complete summary agree. BLS cutoff is September 2026; SNAP cutoff July 2026. This is a fresh local snapshot rebuild; revision-aware updating remains pending.

Next publication checkpoint: learner uses BigQuery console Create table → Upload → Parquet, selects each new run part file for dim_date/fact_state_month/fact_state_industry_month, targets the existing same-named jobs_snap_gold table, and sets Advanced options → Write preference → Overwrite table. These full snapshots must not be appended. State/industry dimensions are unchanged. Table loads are separate operations, so avoid reporting during the three-load transition and verify both views afterward. Existing logical view definitions remain in place. Expected table counts 141/7050/20868 and view counts 6950/20304; 100 state/month records after the SNAP cutoff should have NULL SNAP measures and not_yet_published statuses. BigQuery catch-up publication remains pending learner confirmation. Reference: https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-parquet#appending_to_or_overwriting_a_table_with_parquet_data.


### BigQuery catch-up snapshot publication — learner-confirmed October 25 local / October 26 UTC, 2026

Learner reported done after instructions to overwrite dim_date, fact_state_month and fact_state_industry_month from Gold run `6efac951e42245c389eb7659d92a8fa4`. Unchanged state/industry dimensions and existing logical views were retained. This confirms learner-reported completion, not independent inspection of load jobs or loaded values.

Next acceptance query checks dimension/fact/report counts (141/7050/20868/6950/20304), maximum fact month 202609, maximum jobs/SNAP report month 202607, 100 correctly marked August/September not-yet-published SNAP rows, zero such rows containing SNAP measures, 50 missing unemployment values and one retained benefit review row. This bounded query is learner-executed and read-only; exact cloud results remain pending.


### BigQuery initial catch-up acceptance — passed October 25 local / October 26 UTC, 2026

Learner supplied the full post-publication query result: date_rows 141; state_fact_rows 7,050; industry_fact_rows 20,868; jobs_snap_report_rows 6,950; industry_report_rows 20,304; latest_fact_month 202609; latest_comparable_month 202607; correctly_pending_snap_rows 100; missing_unemployment 50; benefit_review_rows 1. Every value matches the planned snapshot. This establishes published catch-up counts/cutoffs and source-lag handling; it does not establish recurring refresh, revision merges, cloud ETL or scheduling.

Next preservation checkpoint: learner opens existing bucket `jobs-snap-bronze-620503845148`, creates/opens `bls/ingestion_date=2026-10-26/`, and uploads the entire local `data/bronze/bls/ingestion_date=2026-10-26/run_id=43e4e0749e4349ceb1f92122acfc26a6` folder. Preserve all batch/attempt responses and manifests plus inventory/summary. Original SNAP archive is already uploaded and was reused for catch-up, so it needs no duplicate upload. Cloud copy of the new BLS run remains pending learner confirmation. After preservation, monthly refresh must bound each source to its latest six reporting months, upsert current facts without duplicates, and log actual old/new revisions; it must not replay the full baseline or reset first-loaded metadata on every refresh.


### Catch-up BLS cloud copy and UTC convention — learner-confirmed

Learner confirmed uploading BLS catch-up run `43e4e0749e4349ceb1f92122acfc26a6` beneath `gs://jobs-snap-bronze-620503845148/bls/ingestion_date=2026-10-26/`. Remote checksum/object inspection remains unperformed. Clarified that ingestion_date is the UTC capture date, so October 26 UTC can correspond to October 25 evening in Boise. Reporting date_key is independent; existing paths need no renaming.

### Next checkpoint — explicit monthly replay windows

Learner creates chat-provided `plan_monthly_refresh.py`. Its pure month arithmetic validates YYYYMM and calculates exactly six consecutive reporting months across year boundaries. Replay mode reads the accepted Gold summary and prints BLS April–September 2026 and SNAP February–July 2026, with 1,488 and 300 expected source business keys. This uses already accepted cutoffs to rehearse idempotence, not live publication discovery or a newly executed refresh. No network calls or output data writes occur. Subsequent merge must preserve first_loaded_at and unchanged last_changed_at/revision_count, emit old/new revision records only for actual changes, and enforce these source-specific windows without historical widening. Planner execution and merge behavior remain pending.


### Monthly automation destination clarified — October 25, 2026

Learner explicitly requires automated monthly execution in GCP, comparable in responsibility to AWS Step Functions. Cloud Workflows owns orchestration and Cloud Scheduler owns the monthly trigger. The accepted GCP processing path remains Cloud Run ingestion → Cloud Storage Bronze → managed Spark Silver → BigQuery staging/validated revision-aware Gold publication. Local replay is a prerequisite check, not an ongoing operating procedure. Shared code must accept cloud paths/configuration and use Secret Manager/service accounts instead of personal terminal credentials. Next order: prove unchanged replay once, package cloud entrypoints and source discovery, learner creates runtime identities/resources, manually trigger the complete cloud workflow and verify acceptance/failure paths, then enable the monthly schedule with overlap prevention. Hosted automation is required for the GCP target but not yet deployed; Azure baseline responsibilities remain unchanged. References: https://docs.cloud.google.com/workflows/docs/overview and https://docs.cloud.google.com/workflows/docs/schedule-workflow.


### Six-month replay planner — learner-executed and accepted

Learner supplied planner output using accepted Gold `6efac951e42245c389eb7659d92a8fa4`: BLS months 202604–202609, 1,488 source keys; SNAP months 202602–202607, 300 source keys; expected inserts and revisions both zero. Planner execution does not yet prove the merge itself.

Next checkpoint: learner creates chat-provided cloud-independent `monthly_merge.py` and read-only `replay_monthly_refresh.py`. The merge indexes business keys, preserves first-load timestamps, changes revision metadata only for meaningful content changes, retains old/new values with source lineage in returned revision records, and rejects unreviewed valid-to-NULL regressions. Replay projects bounded Silver observations into four source groups (jobs 300, unemployment 300, industry 888, SNAP 300), checks exact expected keys against accepted Gold, and invokes the merge without writing Gold or cloud data. Expected 1,788 unchanged source contributions, zero inserts, zero revisions and exactly unchanged final facts/metadata. Focused in-memory checks exercise one true update and its unchanged rerun before replaying actual input. No live source discovery, cloud execution, scheduling or publication is established by this checkpoint; these remain next deployment work.


### Monthly revision-query requirement clarified

Learner wants to query revised reporting months, observed adjustment counts, and first-observed versus latest measurements, including reporting years from 2026 onward. Accepted direction is current facts plus durable source-specific history, not dimension SCD2. Capture baseline observations, distinguish first measurement arrival from revision/status-only change, add stable event IDs and run/fact identity, restrict lineage to the changing source, and publish history/current facts consistently. Existing monthly_merge returns revision dictionaries but persistence and the richer event classification remain pending; no revision-history execution is claimed. Read-only inspection also found the replay script and a prose heading appended to monthly_merge.py, with no separate replay_monthly_refresh.py file. Learner must split those supplied blocks into their intended two files before import/replay. Agent has not edited implementation files.


### Next checkpoint — finalize merge event semantics before replay

Read-only inspection confirms monthly_merge.py and replay_monthly_refresh.py are now separate. Learner receives a replacement pure merge module plus focused contract checks and replay-call updates in chat. Events are measure-level: initial_observation for first non-NULL value, revision for a change between previously observed non-NULL values, and status_change for availability/quality-only changes. Previously pending SNAP arriving on an existing state/month row does not increment measurement revision_count. Row last_changed_at changes for meaningful content changes; first_loaded_at remains unchanged. Fact revision_count counts source contributions that revise existing measurements, while measure-level revision counts come from revision events.

Stable event IDs use logical refresh_run_id, fact table, source, business key and measure; retries must reuse that run identity. Event identity is independent of wall-clock retry time. Only candidate-source lineage fields are paired with corresponding old lineage. Valid-to-NULL regressions fail for review. Explicit run/table identity and known content fields are required. Baseline observation seeding, durable event storage, single-writer protection and atomic/idempotent cloud publication remain pending; no persisted revision history or monthly execution is claimed by code guidance alone.


### Monthly merge contract and real-data replay — passed

Learner executed check_monthly_merge.py: all contract checks passed, including initial observations, changed measurements, stable event IDs across retries, unchanged reruns, source arrival on pending facts, status-only changes and valid-to-NULL rejection. Learner then executed replay_monthly_refresh.py against accepted Gold 6efac951e42245c389eb7659d92a8fa4. Observed unchanged contributions: jobs 300, unemployment 300, SNAP 300, industry 888 (1,788 total). Inserts/revisions/initial observations/status changes all zero. Final facts remain 7,050/20,868, revision_metadata_preserved true, outputs_written false. This is local in-memory merge/replay evidence; no cloud monthly writer or persisted revision table is yet established.

### Next checkpoint — establish a durable measurement-history baseline

Learner runs chat-provided BigQuery CREATE TABLE IF NOT EXISTS AS SELECT for jobs_snap_gold.fact_measure_history, with one baseline_observation per accepted source/key/measure. Exclude not_yet_published SNAP placeholders; retain published missing values and their statuses. Expected 55,818 baseline rows: jobs 7,050; unemployment 7,050 (50 NULL values); industry jobs 20,868; SNAP persons/households/benefits 6,950 each. Stable event IDs include fixed accepted baseline identity and source/fact/key/measure. IF NOT EXISTS preserves a previously created history table on rerun. Baseline events describe the currently accepted snapshot, not original publisher releases, and do not count as measurement revisions. Future monthly events require durable staging and consistent fact/history publication; creation/seeding remains pending learner result. Existing current facts are not changed by this step.


### Durable BigQuery measurement-history baseline — learner-verified

Learner supplied query results for fact_measure_history: industry_nonfarm_jobs 20,868; snap_benefit_cost_usd 6,950; snap_households 6,950; snap_persons 6,950; total_nonfarm_jobs 7,050; unemployment_rate_pct 7,050. Unique event counts equal row counts in each group, totaling 55,818 baseline events. Only unemployment has missing measurements (50). These are baseline_observation records of the accepted catch-up snapshot, not publisher-original values or observed revision events. Current facts remain unchanged. Subsequent monthly event publication, concurrency control, and transaction/retry behavior in BigQuery are not yet implemented.

### Next cloud setup checkpoint — BLS credential in Secret Manager

Purpose: allow scheduled ingestion to authenticate without a laptop environment variable. Learner selects project project-4b0f63f3-e441-4289-b42, opens Secret Manager and enables its API if prompted, then creates secret `bls-api-key` containing the existing BLS key as its value (no quotes/export prefix). Use Google-managed encryption, default automatic replication, and no rotation schedule for initial setup. If secret type is presented, Access key is appropriate. Verify version 1 is Enabled without displaying or sharing its payload. Do not put credentials into code, chat, screenshots or documentation. Creation is pending learner confirmation. Runtime service account and secret-scoped access are configured next; no agent resource creation or secret access occurs. Reference: https://docs.cloud.google.com/secret-manager/docs/creating-and-accessing-secrets.


### BLS Secret Manager setup — learner-confirmed

Learner reported done after instructions to create secret `bls-api-key` and confirm enabled version 1. This is learner-confirmed setup; no secret payload or independent API lookup was accessed by the agent.

### Next checkpoint — dedicated ingestion runtime service account

Learner creates service account `jobs-snap-ingest` through IAM & Admin → Service Accounts → Create service account, with description BLS and SNAP ingestion runtime. Skip project-role and optional user-access grants in the creation wizard. Expected email: `jobs-snap-ingest@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com`. Attach this identity to the future Cloud Run ingestion job; do not download a service-account key.

Grant Secret Manager Secret Accessor (`roles/secretmanager.secretAccessor`) on secret bls-api-key to that service account through the secret's access panel. Grant Storage Object Creator (`roles/storage.objectCreator`) on bucket jobs-snap-bronze-620503845148 through bucket Permissions → Grant access. These grants are resource-scoped: secret payload read and creation of new Bronze objects. Existing-object reads, overwrites/deletion, BigQuery writes and orchestration permissions are not granted by these instructions; the processing/publishing identities will be configured separately. Account creation and both grants remain pending learner confirmation; no cloud job or authentication test is yet executed.


### Ingestion runtime identity and grants — learner-confirmed

Learner reported done after creating jobs-snap-ingest and granting secret-scoped Secret Manager Secret Accessor on bls-api-key plus bucket-scoped Storage Object Creator on jobs-snap-bronze-620503845148. No service-account key was requested. Effective permissions, secret access and object creation from a running job are not yet tested; no agent IAM mutation occurred.

### Next checkpoint — container repository and build/runtime APIs

Purpose: store the Python ingestion container that Cloud Run Jobs will execute. Learner enables Artifact Registry API, Cloud Build API and Cloud Run Admin API through APIs & Services → Library, then creates Artifact Registry repository jobs-snap with format Docker, Standard mode, Region us-central1, Google-managed encryption and other defaults. This stores packaged code/images; Bronze bucket continues to store source data. Image build/push and job creation/execution follow after code is prepared. Repository and API setup remain pending learner confirmation. Reference: https://docs.cloud.google.com/artifact-registry/docs/repositories/create-repos.


### Artifact Registry and APIs — learner-confirmed

Learner screenshot showed Artifact Registry API enabled (Disable API button). Learner subsequently reported done after instructions to enable Cloud Build/Cloud Run Admin APIs and create jobs-snap Docker repository, Standard mode, us-central1, Google-managed encryption, automatic scanning disabled. Repository/API configuration is learner-confirmed; no independent repository lookup or image build is yet observed.

### Next checkpoint — build a small cloud runtime-check image

Chat provides runtime_check.py, requirements.txt and Dockerfile for learner to place in code/cloud-ingestion. The runtime check requires CLOUD_RUN_JOB and injected BLS_API_KEY, uses the attached service account through Application Default Credentials, and uploads only a small nonsecret JSON record to practice/runtime-check/ingestion_date=<UTC>/run_id=<UUID>/check.json with if_generation_match=0. It does not call either source, read existing Bronze objects or mutate current facts. This tests secret injection and object creation once in the actual cloud runtime before source ingestion.

Learner zips the three explicit files without source data/secrets, uploads the ZIP through Cloud Shell, unpacks into jobs-snap-runtime, configures Docker authentication for us-central1-docker.pkg.dev, builds and pushes image us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/runtime-check:v1. These user-run Cloud Shell packaging operations are deployment preparation, not the monthly operational process. Cloud Run Job creation/execution follows in console using jobs-snap-ingest and secret version 1. Build/push and runtime checks remain pending; agent has not edited implementation files, built/pushed images or executed jobs.


### Runtime-check image built; registry push blocked by connection refusal

Learner-supplied Cloud Shell output confirms Docker build completed successfully in 383.1 seconds. Most time was downloading the Python base layer (about 366 seconds). Image was tagged us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/runtime-check:v1; local manifest-list digest sha256:5a61bb0a357f0b5b0f5c933454bc8ec6c8206dea306caca7117131ec90a791ad. Docker credential helper was already registered correctly. The subsequent push failed on an HTTPS HEAD connection with TCP connect: connection refused to us-central1-docker.pkg.dev:443. This does not establish an IAM denial or successful registry upload; do not rebuild or broaden IAM based on this error. Next learner diagnostic is unauthenticated curl to the registry /v2/ endpoint with bounded timeouts, then one push retry if HTTP is reachable. HTTP 401 from the unauthenticated probe is expected evidence of reachability. No Cloud Run Job has been deployed/executed.


### Repeated Cloud Shell Docker push failure — switch to managed build

Learner's unauthenticated curl HEAD request to registry /v2/ returned HTTP/2 405, proving an HTTP response from the shell path; the earlier expectation of specifically 401 was too narrow. A subsequent docker push again failed with TCP connection refused, now to a different resolved address. This isolates a repeatable Docker push connectivity failure without establishing the underlying network cause or IAM denial. Avoid further identical push retries and do not broaden IAM from a TCP error.

Next learner action, from Cloud Shell ~/jobs-snap-runtime: submit the three-file Docker build context through `gcloud builds submit --project=project-4b0f63f3-e441-4289-b42 --region=us-central1 --tag=us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/runtime-check:v1 .`. Cloud Build performs build/push on managed workers rather than the Cloud Shell Docker daemon. Cloud Build IAM/default build-account readiness has not been independently verified; inspect any exact denial before granting roles, and keep build identity separate from jobs-snap-ingest. Build status SUCCESS and registry digest remain pending. Source context contains only runtime_check.py, requirements.txt and Dockerfile, with no API key or captured data. No agent build or cloud mutation performed.


### Managed build source-read denial — identified build identity

Learner ran gcloud builds submit from the three-file runtime directory. CLI uploaded the approximately 2 KiB source archive to bucket project-4b0f63f3-e441-4289-b42_cloudbuild, then Cloud Build rejected source resolution: 620503845148-compute@developer.gserviceaccount.com lacks storage.objects.get for that source object. This is specific build-account IAM evidence, distinct from the earlier Docker TCP refusal. The omitted final dot in the pasted command did not prevent current-directory archiving; source upload succeeded.

Next learner fix: grant Storage Object Viewer on the Cloud Build source bucket to that identified build service account, and Artifact Registry Writer on the jobs-snap repository to the same account for the subsequent push. Keep these grants scoped to the source bucket/repository; do not grant them to jobs-snap-ingest or grant project Editor. Rerun the same Cloud Build command after granting. These grant changes and build success remain pending learner confirmation. Source archive bucket is separate from the Bronze data bucket.


### Runtime-check managed image build/push — successful October 26, 2026 UTC

Learner supplied Cloud Build SUCCESS for build 936e6aab-b346-44c8-b98e-788574b9693e in us-central1, 33 seconds. Image us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/runtime-check:v1 was pushed with digest sha256:f13edc1447e0498ceb024c0fdbc123325c82edb66d4f2a7f5e2f82f20020e80b. Source fetch and image push now succeed after guided build-account grants. Python 3.12 image installed google-cloud-storage 3.17.1. Cloud Build emitted a nonfatal notice that its default compute build account lacks roles/logging.logWriter for Cloud Logging; supplied build output exists, but Cloud Logging write permission remains unresolved. Container runtime execution is not proved by a successful image build.

### Next checkpoint — execute the Cloud Run runtime check

Learner creates Cloud Run Job jobs-snap-runtime-check in us-central1, selecting the published runtime-check image (prefer digest above), one task/parallelism one, 1 vCPU, 512 MiB, task timeout two minutes and retries zero. Runtime service account jobs-snap-ingest@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com. Environment PROJECT_ID=project-4b0f63f3-e441-4289-b42 and BRONZE_BUCKET=jobs-snap-bronze-620503845148. Expose secret bls-api-key version 1 as environment variable BLS_API_KEY through the secret reference control, not a literal value. Leave image command/arguments unchanged. Create then execute once; expected exit success and nonsecret log status passed/secret_injected true/object_created gs://.../practice/runtime-check/.../check.json. Check object exists. This establishes only secret injection and create-only bucket access, not BLS-key validity, source ingestion or pipeline automation. Job creation and execution remain pending learner evidence; agent has not deployed or executed resources.


### Cloud Run runtime-check configuration correction and reported success

Learner screenshot verified the creation form's image reference prefix, job name jobs-snap-runtime-check, region us-central1 and one task. Subsequent creation error identified default compute account 620503845148-compute@developer.gserviceaccount.com and secret version latest, rather than the intended ingestion account/version 1. Guided correction: select jobs-snap-ingest under Security and pin BLS_API_KEY secret reference to version 1; no additional secret grant to the default compute account was advised. Learner then reported says succeeded. It is not yet explicit whether this refers to job creation or a completed execution; the nonsecret result log and created object URI remain pending. Next learner check is Jobs → jobs-snap-runtime-check → Executions → latest execution → Logs, looking for status passed, secret_injected true and object_created URI. No live source ingestion is established by this runtime test.


### Cloud Run runtime-check execution — screenshot verified

Learner screenshot shows jobs-snap-runtime-check in us-central1, execution jobs-snap-runtime-check-w6nz6, a nonsecret object_created log under gs://jobs-snap-bronze-620503845148/practice/runtime-check/ingestion_date=2026-10-26/, container exit(0), and a completed execution. The earlier readiness failure is followed by a successful configuration replacement. Given the executed image's guard, success establishes nonempty secret injection and object creation using the configured runtime identity; exact saved IAM/configuration and full object URI were not independently queried. It does not validate the BLS key against BLS or establish live ingestion/Silver/Gold automation.

### Next checkpoint — live BLS cloud capture image

Chat guidance reuses backfill_bls.capture_batch and plan_monthly_refresh.reporting_months through a new cloud entry point. A rolling two-calendar-year API request supports January boundaries; original bytes remain in Bronze while validation and downstream processing are bounded to six months per returned series. Record series-specific cutoffs rather than assuming a shared latest month. Use Cloud Run execution identity as capture run ID, and a separate logical refresh ID for later orchestration correlation. Capture files/manifests upload create-only, and summary.json is written last with complete/failed status and portable gs:// batch-manifest references. No current facts are updated. Build a separate bls-ingest:v1 image using explicit source-file packaging and Cloud Build; create/execute the source job only after build success. This stage is guidance/pending execution, not observed live cloud ingestion.


### Optional explanation — source-deployed functions versus container jobs

Learner compared this packaging approach with the earlier AWS S3/Python/Lambda ingestion lab. GCP supports source-deployed Cloud Run functions, including console authoring; the platform builds the runtime image, so a learner-managed Dockerfile is not mandatory for Python ingestion. Cloud Run Jobs is the chosen GCP batch execution path: a program runs to completion, exits with success/failure, and can be invoked/waited on by Workflows. Container images package code/dependencies/runtime; Cloud Storage stores data artifacts, while Workflows orchestrates execution. The ingestion scripts could also fit a function; Jobs is a design choice, not the only GCP approach or a universal performance/cost improvement. Source-based functions would reduce explicit container-management work; Jobs offers explicit runtime packaging and batch task behavior. No alternative function deployment or architecture migration is authorized by this comparison alone. Existing Workflows/monthly automation target remains unchanged. References: https://docs.cloud.google.com/run/docs/deploy-functions and https://docs.cloud.google.com/run/docs/create-jobs.


### Presentation reference — ingestion deployment tradeoff, decision open

Learner requested a file explaining source-deployed functions versus container Jobs for the presentation and stated the final preference is undecided. Created gcp-ingestion-functions-vs-jobs.md with a short speaking summary, responsibility map, AWS packaging comparison, GCP execution comparison, build-versus-monthly-run distinction, observed deployment friction/runtime evidence, cost/ownership considerations, and decision questions. Official sources checked October 25 local / October 26 UTC, 2026. README and GCP plan link the reference; hosted ingestion interface is explicitly open. Existing runtime-check evidence is retained without treating it as a production deployment decision. No implementation code, cloud resources or live execution changed.


### BLS image build failed — Dockerfile filename mismatch identified

Learner supplied Cloud Build failure 7dcdd47c-c12c-497a-8924-7537e55ce733: /workspace/Dockerfile.bls missing. Read-only workspace inspection confirms the BLS Docker contents were saved as code/cloud-ingestion/Dockerfile, while cloudbuild-bls.yaml references Dockerfile.bls. jobs-snap-bls.zip contains six files and no Dockerfile of either name. The managed build-source fetch succeeded; this failure is packaging, not IAM/network or the unrelated nonfatal Cloud Logging notice.

Learner correction: rename the local BLS Dockerfile to Dockerfile.bls, add that file to the existing ZIP, upload the updated archive into Cloud Shell, extract Dockerfile.bls into ~/jobs-snap-bls and rerun the same build. Agent has not renamed or edited implementation files. Corrected packaging/build success remains pending.


### BLS cloud image build — learner-confirmed successful

After correction of the Dockerfile filename/archive omission, learner reported success for the BLS image build. Target image us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/bls-ingest:v1. Exact successful build ID/image digest was not supplied. Final ingestion-interface preference remains open; this continues the container candidate experiment, not an irrevocable choice.

Next execution: learner creates Cloud Run Job jobs-snap-bls-ingest in us-central1 using the built image, tasks/parallelism 1, 1 vCPU, 512 MiB, timeout 20 minutes, retries 0, runtime account jobs-snap-ingest. Set PROJECT_ID and BRONZE_BUCKET as in the verified runtime check, and reference bls-api-key version 1 as BLS_API_KEY. Leave command/arguments unchanged. Execute once after creation. This makes five sequential BLS batches (up to three application attempts per batch), preserves the rolling-year original responses, validates six months per series, uploads immutable artifacts and a complete/failed summary. Expected accepted refresh observations total 1,488 across 248 series; latest dates must be read from the resulting summary rather than assumed from the calendar. No Silver/Gold/history updates occur in this ingestion job. Execution remains pending learner output.


### First live BLS cloud capture — independently verified read-only

Learner reported success. Agent used the existing GCP MCP for read-only execution listing and storage cat, without running or modifying cloud resources. Execution jobs-snap-bls-ingest-6zgpx in us-central1 has Completed=True and succeededCount=1; runtime jobs-snap-ingest, one task, 512 MiB, 1 vCPU, 1200-second timeout, retries zero, and secret version 1 were observed as references without accessing the secret payload. Image digest b738699b9aef4053e869a4bc65c040dd4ae87eb68f88dfcbc334d08a49b87c7c. Saved summary gs://jobs-snap-bronze-620503845148/bls/ingestion_date=2026-10-26/run_id=jobs-snap-bls-ingest-6zgpx/summary.json reports complete, five batches, 1,488 selected observations, zero selected missing values, and every series latest month 202609. Artifact list has 11 objects excluding summary itself. This establishes live BLS cloud capture, not cloud Silver/Gold updates, monthly publication or scheduling. Final function-versus-Job selection remains open while the container candidate is exercised.

Next SNAP candidate: parameterize the existing workbook selector/capture helper while preserving historical defaults, reuse page download/archive discovery and retry behavior, discover latest reporting month from the preserved landing page, identify fiscal-year members needed for six months, and write cloud Bronze. The saved local landing HTML was inspected read-only: proposed Latest Available Month regex returns July 2026. Current official page also lists July 2026. This is metadata discovery; full state/month parsing remains a downstream Silver acceptance step. SNAP image build and live cloud execution remain pending.


### SNAP cloud image build — learner-confirmed successful

Learner reported success after preparing the parameterized SNAP capture helper, cloud snap_ingest.py, Dockerfile.snap and cloudbuild-snap.yaml and running Cloud Build. Target image us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/snap-ingest:v1; exact successful build ID/digest not supplied. Historical helper defaults are intended to remain unchanged; build success alone does not prove archive capture or state parsing.

Next learner execution: create Cloud Run Job jobs-snap-usda-ingest in us-central1, image snap-ingest:v1, one task/parallelism one, 1 vCPU, 512 MiB, timeout 20 minutes, retries zero, runtime jobs-snap-ingest. Set PROJECT_ID=project-4b0f63f3-e441-4289-b42 and BRONZE_BUCKET=jobs-snap-bronze-620503845148, with no BLS_API_KEY secret reference. Leave command/arguments unchanged and execute once. Expected complete source-capture summary with discovered latest month and six target months; current page suggests 202607 and February–July, but actual run metadata must be inspected. Expected state/month scope 300 is a downstream target, not parsed acceptance. No Silver/Gold/history mutation occurs. Source job creation/execution remains pending learner evidence; no agent deployment or execution performed.


### SNAP cloud archive capture — screenshot and saved summary verified

Learner screenshot shows jobs-snap-usda-ingest complete log, latest_month 202607, and summary URI gs://jobs-snap-bronze-620503845148/snap/ingestion_date=2026-10-26/run_id=jobs-snap-usda-ingest-2dxln/summary.json. Agent read-only MCP storage inspection confirms complete summary, target months 202602–202607, required fiscal year 2026, expected_state_months 300, manifest attempt_id=001/manifest.json, three artifact objects excluding summary, and explicit validation scope archive/workbook structure/checksums with state measurements pending Silver. No source request, job execution or cloud mutation was performed by the agent. This establishes cloud capture and metadata discovery, not numeric/state coverage acceptance.

### Next checkpoint — processing artifact bucket

Purpose: provide cloud paths for processing code, versioned Silver outputs and temporary/staging artifacts, separate from immutable source Bronze. Learner creates Cloud Storage bucket jobs-snap-processing-620503845148 in Region us-central1, Standard storage, flat namespace, Uniform access, enforced public access prevention, Google-managed encryption, default seven-day soft delete, no versioning or retention lock. Bucket creation remains pending learner confirmation. Processing service-account permissions, managed Spark submission and BigQuery publication follow separately; no permanent cluster is required for the proposed serverless batch path. Existing ingestion jobs retain create-only access to the Bronze bucket and need no permissions on this processing bucket.


### Silver bucket name accepted and configuration verified read-only

Learner selected jobs-snap-silver-620503845148 for naming parity with Bronze and reported creation complete. Read-only MCP describe verifies bucket exists in US-CENTRAL1, STANDARD storage, Uniform bucket-level access true, public_access_prevention enforced and soft-delete retention 604800 seconds (seven days). This supersedes the earlier proposed jobs-snap-processing-620503845148 name. Processing artifacts may use code/, silver/ and staging/ prefixes within this bucket. Agent created no resource or IAM grant.

### Next checkpoint — dedicated Spark workload identity

Learner enables Dataproc API if needed and creates jobs-snap-process, description PySpark Bronze-to-Silver processing. For the proposed managed Spark runtime 3.x, grant Dataproc Serverless Node (roles/dataproc.serverlessNode) at project scope to the workload account, per current custom-account runtime-3 documentation. Grant Storage Object Viewer on jobs-snap-bronze-620503845148 and Storage Object User on jobs-snap-silver-620503845148. Silver object CRUD supports temporary-file commits and versioned outputs; Bronze remains read-only for this identity. No secret accessor or BigQuery writes are required for this stage. Account/grants are pending learner confirmation; no Spark batch submitted. Runtime 3.x defaults to end-user credentials unless a custom account is specified, so batch configuration must explicitly select jobs-snap-process. Reference: https://docs.cloud.google.com/managed-spark/docs/concepts/personas-and-serverless-iam-roles.

### Spark workload identity — permissions verified read-only

Learner reported setup complete. Read-only GCP queries verify jobs-snap-process exists, has roles/dataproc.serverlessNode at project scope, roles/storage.objectViewer on jobs-snap-bronze-620503845148, and roles/storage.objectUser on jobs-snap-silver-620503845148. No Spark execution or processing acceptance is inferred from these grants. Agent made no cloud changes.

### Next checkpoint — managed Spark dependency image

Purpose: package the existing SNAP parser's openpyxl/xlrd dependencies and the GCS Python client for managed Spark runtime 3.0 (Python 3.12). Learner creates code/cloud-processing/requirements.txt, Dockerfile.silver and cloudbuild-silver.yaml using the chat-provided contents. The image supplies a Python 3.12 environment, required OS utilities and spark user/group ID 1099; PYSPARK_PYTHON selects the packaged interpreter. Managed Spark supplies Spark and its PySpark package at execution time. This image is a dependency environment; the application entry point will be supplied with the Spark batch separately.

Prerequisites: existing jobs-snap Artifact Registry repository and successful Cloud Build permissions from ingestion builds. Upload only the three new files to a separate Cloud Shell directory, then run gcloud builds submit --project=project-4b0f63f3-e441-4289-b42 --region=us-central1 --config=cloudbuild-silver.yaml . from that directory. Expected image is us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/silver-runtime:v1 and Cloud Build STATUS SUCCESS. Verification is learner build output; build and Spark execution remain pending. Next work is the cloud Silver adapter, selected-month parsing, immutable output and completion summary. References: https://docs.cloud.google.com/managed-spark/docs/guides/custom-containers and https://docs.cloud.google.com/managed-spark/docs/concepts/versions/spark-runtime-3.0.

### Managed Spark dependency image — learner-confirmed build success

Learner reported success for the silver-runtime:v1 build. Exact build ID and image digest were not supplied; no managed Spark execution or dependency-import acceptance has yet been observed. The next checkpoint adapts load_bls_rows in code/build_silver.py to accept optional series-specific month windows and deliberately filter a wider saved response envelope, while keeping historical callers strict by default. This is needed because cloud captures preserve two calendar years of original BLS bytes but monthly processing selects only six months per series. Guidance is provided in chat for the learner to apply; the agent has not edited implementation files. Next verification is Python syntax compilation, followed by cloud adapter integration and an actual managed Spark batch.

### Next checkpoint — cloud Silver application adapter

Learner confirmed the parser edits/syntax checkpoint. Read-only inspection confirms load_bls_rows now accepts months_by_series and filter_outside while retaining historical defaults. Chat supplies code/cloud-processing/build_silver_cloud.py for the learner to create. It downloads only artifacts referenced by complete Bronze summaries into an isolated driver temporary directory, adapts local manifest references without changing cloud Bronze, reuses the existing checked parsers and schemas, restores gs:// lineage, validates six consecutive reporting months per source/series, normalizes jobs, and writes versioned Silver Parquet. A create-only started marker reserves the output run; a complete summary is written last. An interrupted/failed run has no complete summary and is not an accepted Silver input. A later retry uses a new output run ID; resumable execution is not implemented at this checkpoint.

Learner runs python -m py_compile code/build_silver.py code/cloud-processing/build_silver_cloud.py locally, then uploads both Python files through the Storage console to gs://jobs-snap-silver-620503845148/code/silver-v1/. The existing dependency image need not be rebuilt for these application edits. Managed Spark will receive build_silver.py as a Python dependency and build_silver_cloud.py as its entry point. Expected first cloud inputs are the saved BLS jobs-snap-bls-ingest-6zgpx and SNAP jobs-snap-usda-ingest-2dxln summary URIs; selected coverage is 1,488 BLS rows and 300 SNAP state/month rows. Code creation, syntax result, upload and managed execution remain pending learner evidence. This adapter writes refresh slices, not a replacement historical baseline or updated Gold facts. Reference for separate application/dependency submission: https://docs.cloud.google.com/sdk/gcloud/reference/dataproc/batches/submit/pyspark.

### Cloud Silver Python uploads — existence verified read-only

Learner reported checkpoint complete. Read-only Storage object describes verify code/silver-v1/build_silver.py (22,106 bytes) and code/silver-v1/build_silver_cloud.py (11,130 bytes) in jobs-snap-silver-620503845148. Existence and sizes do not prove cloud imports or processing success. Agent inspected local argument names and confirmed the application has no local Spark master setting; no cloud execution was performed.

### Next checkpoint — submit the first managed Spark Silver batch

Purpose: process the two already-saved monthly source captures entirely in GCP. In Managed Service for Apache Spark/Dataproc Serverless, open Batches and Create. Select batch ID jobs-snap-silver-001, region us-central1, type PySpark, runtime 3.0, main Python file gs://jobs-snap-silver-620503845148/code/silver-v1/build_silver_cloud.py, Python dependency gs://jobs-snap-silver-620503845148/code/silver-v1/build_silver.py, and custom container us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/silver-runtime:v1. Explicitly select service-account workload authentication and jobs-snap-process@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com. Set batch lifetime/TTL to 20 minutes if exposed. Use the four application arguments in chat: the exact BLS and SNAP summary URIs recorded above, --silver-bucket=jobs-snap-silver-620503845148 and --run-id=cloud-silver-001. Learner submits the batch; do not create a persistent cluster or Cloud Run job for this processing step.

Expected observations: parsed BLS 1,488 and SNAP 300, successful Spark state, and complete summary under gs://jobs-snap-silver-620503845148/silver/ingestion_date=<actual UTC execution date>/run_id=cloud-silver-001/summary.json alongside bls_observations/ and snap_state_month/. Date comes from actual execution, not a hard-coded previous capture date. Verify both workload success and complete summary before accepting the slice. If this application has reserved its output and fails, use a new batch ID and output run ID on the next attempt; the current adapter does not resume an interrupted directory. BigQuery and accepted historical facts are not changed by this batch. Submission and results remain pending learner evidence. Console reference: https://docs.cloud.google.com/managed-spark/docs/quickstarts/spark-batch.

### Silver batch form review — network selector discrepancy

Learner screenshots show Standard tier, PySpark/runtime 3.0, correct main/shared Python paths, four separate application arguments and the processing service account. TTL still shows 14400s; change to 1200s. Image field is truncated visually, so verify the complete silver-runtime:v1 image reference. Optional catalog rows/metastore/history server are unnecessary for these Parquet outputs and should remain unconfigured. Network selector reports no local networks, but read-only MCP queries confirm default VPC and its us-central1 default subnet exist (10.128.0.0/20). Private Google Access is currently false; managed Spark documentation states it enables PGA automatically. Select default network and regional default subnet; if selector remains empty, reload the form and re-enter settings as needed. Do not create a duplicate network from this UI symptom. Batch has not yet been observed submitted. Reference: https://docs.cloud.google.com/managed-spark/docs/concepts/network-serverless.

### Network selector still empty — explicit-subnet submission fallback

Learner reports no networks to display. Additional read-only queries confirm Compute Engine API is enabled, default VPC exists with its regional subnet, and the learner account has project Owner. The cause of the console selector failure remains undetermined. Chat provides an equivalent learner-run Cloud Shell submission using the fully qualified us-central1 default subnet, runtime 3.0, SERVICE_ACCOUNT authentication, the dedicated processing account, existing image and uploaded Python files, and 20-minute TTL. All input paths are GCS URIs, so the command works from any Cloud Shell directory. Use this as an alternative to the unsubmitted console form, not as a second execution. No new network, IAM change or agent-run batch was performed; successful submission remains pending learner output. Reference: https://docs.cloud.google.com/sdk/gcloud/reference/dataproc/batches/submit/pyspark.

### First Silver batch failed permission validation — narrow IAM correction

Learner supplied jobs-snap-silver-001 submission followed by FAILED, operation 2a5dfd73-db37-3149-8b31-560646751e3d, missing dataprocrm.nodes.get, dataprocrm.nodes.heartbeat and dataprocrm.nodes.mintOAuthToken on jobs-snap-process. Failure is infrastructure permission validation before application execution, not a Python/parser failure. Read-only role inspection confirms the account retains roles/dataproc.serverlessNode but the live predefined role lacks these three permissions. This corrects earlier guidance that the Node role alone would suffice. Dataproc Worker contains them but also broad project-level Storage permissions, so the proposed correction preserves bucket-specific storage access by adding a project custom role containing only these three missing node permissions.

Learner console instructions: IAM & Admin > Roles > Create role, title Jobs SNAP Spark Node Supplement, ID jobsSnapSparkNodeSupplement, stage General availability; add exactly the three permissions above. In project IAM edit jobs-snap-process and add the custom role while retaining Serverless Node and existing bucket grants. Creation/grant are pending, not agent-executed or verified. After the grant propagates, rerun the prior submission with batch jobs-snap-silver-002 and output run cloud-silver-002. Use a new ID to distinguish this attempt from the failed batch. New submission and successful Silver outputs remain pending. Permission reference: https://docs.cloud.google.com/iam/docs/roles-permissions/dataprocrm.

### Spark node supplement — role and binding verified read-only

Learner reported the custom-role grant complete. Read-only project IAM and custom-role describes confirm jobs-snap-process has both roles/dataproc.serverlessNode and projects/project-4b0f63f3-e441-4289-b42/roles/jobsSnapSparkNodeSupplement. The custom role is GA and includes exactly dataprocrm.nodes.get, dataprocrm.nodes.heartbeat and dataprocrm.nodes.mintOAuthToken. No agent cloud mutation or execution occurred. Learner next retries the same PySpark submission with batch jobs-snap-silver-002 and output run cloud-silver-002. Infrastructure acceptance and application success remain pending that execution.

### Second Silver batch failed at image pull — repository reader required

Learner supplied jobs-snap-silver-002 FAILED with application exit code 1. Read-only driver logs resolve the generic message: container image pull for jobs-snap/silver-runtime:v1 receives Artifact Registry OAuth-token 403 Forbidden. This corrects the preliminary statement that application execution had been reached: Python did not start. Batch configuration verifies runtime workload account jobs-snap-process, explicit regional default subnet, SERVICE_ACCOUNT authentication and 1200-second TTL. Repository IAM currently grants only the build account Artifact Registry Writer. Project IAM confirms service-620503845148@gcp-sa-dataprocrmnode.iam.gserviceaccount.com exists with roles/dataprocrm.nodeServiceAgent. No denied-pull audit entry identifying the requesting principal was available in the queried Artifact Registry audit records.

Current custom-container documentation explicitly requires Artifact Registry Reader on the repository for the Dataproc Resource Manager Node Service Agent in runtime 3.0+, distinct from the application workload identity. Learner next opens Artifact Registry > jobs-snap (us-central1) > Permissions > Grant access, principal service-620503845148@gcp-sa-dataprocrmnode.iam.gserviceaccount.com, role Artifact Registry Reader (roles/artifactregistry.reader), no condition, Save. This is repository-scoped image read access; it does not add Bronze/Silver permissions or permit image writes. Grant, new batch jobs-snap-silver-003/output cloud-silver-003 and actual Python execution remain pending. No agent mutation, source request or ETL execution occurred. Reference: https://docs.cloud.google.com/managed-spark/docs/guides/custom-containers (Step 4, runtime 3.0+ identity requirement).

### Third Silver batch failed at secure-tag setup — Cloud Resource Manager API

Learner first retried existing batch ID jobs-snap-silver-002 and received ALREADY_EXISTS; a failed batch still occupies its ID. The subsequent jobs-snap-silver-003 was submitted but failed during TagKeys.GetNamespacedTagKey with an explicit Cloud Resource Manager API disabled/not-used error for this project. This is a service prerequisite, not an application-code error; it does not prove the earlier image-pull correction succeeded. Learner must open the Cloud Resource Manager API page for project-4b0f63f3-e441-4289-b42, click Enable and allow propagation, then resubmit with jobs-snap-silver-004 and cloud-silver-004. No additional broad IAM role is prescribed by this error. API enablement, new submission and successful processing remain pending; agent made no cloud changes. Error-supplied console URL: https://console.cloud.google.com/apis/library/cloudresourcemanager.googleapis.com?project=project-4b0f63f3-e441-4289-b42.

### Fourth Silver batch — image-pull 403 persists after node-agent grant

Learner screenshot confirms Cloud Resource Manager API Enabled, then learner supplied jobs-snap-silver-004 FAILED/application exit 1. Read-only driver logs show repeated Artifact Registry OAuth-token 403 pulling silver-runtime:v1; Python still did not start. Read-only repository IAM now confirms roles/artifactregistry.reader for service-620503845148@gcp-sa-dataprocrmnode.iam.gserviceaccount.com, so the earlier prescribed node-agent grant is present. Image describe confirms silver-runtime:v1 exists, digest sha256:6f1f3b50106b292ff795a6101ebf040040c47246369f6663d6927b0985846638. The workload identity jobs-snap-process has no direct repository reader binding. Driver logs do not identify the token requester, so the exact pull identity remains unconfirmed despite the documented runtime-3 node-agent rule.

Next narrow correction: learner adds Artifact Registry Reader on the jobs-snap repository to jobs-snap-process@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com as well, retaining the node-agent grant. This covers the explicitly configured workload identity without project-wide repository access or image writes. Verify the saved binding before another submission; next identifiers will be jobs-snap-silver-005 and cloud-silver-005. This grant is proposed/pending; no new batch or cloud IAM mutation was performed by the agent. Successful image pull and Silver processing remain unverified.

### Repository readers verified — fifth Silver attempt ready

Learner reported the workload repository grant complete. Read-only jobs-snap repository IAM confirms roles/artifactregistry.reader includes both jobs-snap-process@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com and service-620503845148@gcp-sa-dataprocrmnode.iam.gserviceaccount.com. Existing build-account Writer binding remains. Chat supplies the full learner-run submission with batch jobs-snap-silver-005/output cloud-silver-005; all other settings and saved source summaries remain as before. Successful image pull and processing are pending actual execution. Agent made no IAM changes and submitted no batch.

### First managed Spark Silver refresh — successful execution and summary verified

Learner supplied successful completion of jobs-snap-silver-005, batch UUID 081ab7b1-ed20-4df1-abd1-e1e91e803557, operation 7642641e-1f87-3ded-9cbb-9ee4b0d3c842. Read-only batch describe independently returns SUCCEEDED. Read-only saved summary gs://jobs-snap-silver-620503845148/silver/ingestion_date=2026-10-26/run_id=cloud-silver-005/summary.json reports complete/monthly_refresh_slice, 1,488 BLS observations across April–September 2026 and 300 SNAP state/month rows across February–July 2026. All 248 BLS series have latest month 202609; SNAP latest month is 202607. Selected BLS source-missing and SNAP benefit-review counts are both zero; older accepted historical anomalies are outside this refresh and remain unchanged. Summary lists versioned bls_observations/ and snap_state_month/ Parquet outputs beside it. Application timestamps are 2026-10-26T06:21:04.195953+00:00 through 06:21:45.248196+00:00. No independent full Parquet scan was performed by the agent; processing/parser checks and summary acceptance ran in the learner-submitted managed batch.

This establishes cloud Bronze-to-Silver refresh processing under the configured service account and packaged dependencies. The two repository-reader grants are retained; successful execution after the workload grant does not independently identify the image-pull token principal. No rebuild, additional ingestion or agent cloud mutation occurred. BigQuery current facts/history, Gold reporting and Scheduler/Workflows automation have not been updated by this slice.

### Next checkpoint — BigQuery staging dataset

Purpose: isolate incoming monthly candidates from accepted Gold facts/history before validation and publication. In BigQuery Explorer, open the project menu > Create dataset, ID jobs_snap_staging, location type Region, region us-central1, other settings default. If the dataset already exists in the correct region, reuse it. Learner creation and permissions are pending. Next work is a cloud publisher reusing monthly_merge semantics, stage validation, and transactional current-fact/history publication; orchestrator/scheduling follow. This step does not authorize or perform any Gold overwrite.

### BigQuery staging dataset — learner-confirmed created

Learner reported the jobs_snap_staging dataset creation checkpoint complete. Requested location is us-central1; dataset metadata was not independently inspected in this turn. Dataset creation does not establish staged rows, merge acceptance or published history.

### Next checkpoint — dedicated BigQuery publisher identity

Purpose: keep warehouse publication permissions separate from source ingestion and Spark parsing. Learner creates jobs-snap-publish in IAM & Admin > Service Accounts, description Publish validated Silver refreshes to BigQuery with revision history. Grant BigQuery Job User (roles/bigquery.jobUser) at project scope. Grant BigQuery Data Editor (roles/bigquery.dataEditor) separately on jobs_snap_staging and jobs_snap_gold through each dataset's Share/Permissions > Add principal controls. Grant Storage Object Viewer (roles/storage.objectViewer) on jobs-snap-silver-620503845148 through bucket Permissions > Grant access. All grants target jobs-snap-publish@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com. Job User permits query/load jobs; dataset roles permit staged candidates and current-fact/history updates; Silver Viewer permits reading accepted Parquet and summaries. These are planned publisher capabilities, not evidence that any publication has executed. No service-account key is needed. Service account, grants, publisher code/deployment, staging validation and transactional publication remain pending. Reference: https://docs.cloud.google.com/bigquery/docs/control-access-to-resources-iam.

### Publisher permissions checkpoint and live schema prerequisite

Learner reported the dataset permission steps complete after guidance through Share > Permissions > Add principal. Screenshot verifies jobs_snap_staging exists in us-central1 with no default table expiration. Dataset grants are learner-confirmed, not independently queried. Read-only project IAM verifies jobs-snap-publish has roles/bigquery.jobUser, and Silver bucket IAM verifies its roles/storage.objectViewer binding. No current facts/history or staging data was changed.

Next learner runs the chat-provided read-only INFORMATION_SCHEMA.COLUMNS query in any BigQuery SQL tab, location us-central1, to return ordered JSON schemas for fact_state_month, fact_state_industry_month and fact_measure_history in jobs_snap_gold. Purpose: match actual warehouse column names/types, including revision metadata and JSON lineage, before supplying the cloud publication implementation. Expected three metadata rows; this query does not read source observations, ingest, stage or publish data. Live schemas and publisher implementation remain pending learner output.

### Live Gold schemas supplied — staging job preparation

Learner returned all three live schemas. Both current facts have required first_loaded_at/last_changed_at TIMESTAMP and revision_count INT64. State/industry keys are STRING and date_key INT64. Jobs, rates and benefit dollars are NUMERIC; SNAP people/households are INT64. History has event/run/source/fact/measure identity, old/new NUMERIC values, statuses/quality flags and JSON lineage. No schema alteration is required by this inspection. Source-grain staging tables can retain the existing Silver schema, then projection/merge code maps to these warehouse columns.

Next chat supplies learner-created code/cloud-publish/stage_refresh.py plus requirements.txt, Dockerfile and cloudbuild.yaml. The job reads the exact complete Silver summary, loads versioned BLS/SNAP Parquet into run-specific native staging tables with WRITE_EMPTY and deterministic load job IDs, validates exact source business keys against the summary and 50-state dimension, and saves a one-row accepted staging manifest after validation. It has no Gold mutation. This staging component is the first publisher component, not yet the transactional fact/history publisher. Learner syntax-checks and packages the four files, uploads/extracts in a separate Cloud Shell directory, and builds us-central1-docker.pkg.dev/project-4b0f63f3-e441-4289-b42/jobs-snap/publish-runtime:v1 using Cloud Build. Build, deployment, staged rows and key validation remain pending learner results; agent supplies code only in chat and does not execute ingestion, ETL or cloud creation. Next deployment will use jobs-snap-publish with the already configured BigQuery/Silver permissions. Reference: https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-parquet.

### Staging image build — learner success and registry image verified

Learner reported successful publish-runtime:v1 build. Read-only Artifact Registry image describe confirms digest sha256:837cb1c8cd6a07f36d40daa685568bb545ef080bbdcee0001569c5899f41b3e9. Build success does not establish staging acceptance or Gold publication.

Next learner creates Cloud Run Job jobs-snap-stage, us-central1, image publish-runtime:v1, one task/parallelism one, 1 vCPU/512 MiB, task timeout 10 minutes, retries zero, runtime identity jobs-snap-publish@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com. Leave container command blank to use the packaged entrypoint. Supply two separate arguments: --silver-summary=gs://jobs-snap-silver-620503845148/silver/ingestion_date=2026-10-26/run_id=cloud-silver-005/summary.json and --refresh-run-id=monthly-20261026-001. No secrets or environment variables are required by this script. After creation learner executes once; expected status staged, BLS 1,488/SNAP 300, and manifest_table in jobs_snap_staging. Save that table ID for the next merge component. Same logical inputs retain the same refresh ID for stage retries so stable BigQuery load IDs can reattach. This ID rule differs from failed Spark output-run IDs, which reserve separate directories. Cloud Run deployment/execution, staging key checks and the accepted manifest remain pending learner evidence. Current Gold/history are not mutated by this component. References: https://docs.cloud.google.com/run/docs/create-jobs and https://docs.cloud.google.com/run/docs/configuring/jobs/containers.

### Cloud staging execution — accepted log verified read-only

Learner reported success. Read-only jobs-snap-stage logs contain status staged, refresh_run_id monthly-20261026-001, 1,488 BLS rows and 300 SNAP rows, followed by Container called exit(0). Manifest table is project-4b0f63f3-e441-4289-b42.jobs_snap_staging.manifest_870992f6162f33782e1c98cb; source tables are bls_870992f6162f33782e1c98cb and snap_870992f6162f33782e1c98cb in the same dataset. This establishes learner-executed staging and the implemented key/count checks; no independent table scan was performed by the agent. Gold facts/history publication remains pending.

### Next checkpoint — publication control and committed-run ledger

Purpose: support concurrent-run detection and idempotent Gold publication. Learner runs the chat-provided setup SQL in BigQuery to create jobs_snap_gold.pipeline_control (pipeline STRING, version INT64, updated_at TIMESTAMP) and jobs_snap_gold.refresh_publications (refresh_run_id STRING, stage_manifest STRING, silver_summary_sha256 STRING, published_at TIMESTAMP, state_rows INT64, industry_rows INT64, history_events INT64, stats JSON). Insert a single jobs_snap_monthly control row at version zero only if absent; assert exactly one such row and display it. This setup does not modify either current fact or measurement history. Expected first setup result is one control row/version zero; a later setup rerun retains its existing version. Execution remains pending learner result.

The forthcoming publisher will read the version with its baseline, update that shared row inside the same BigQuery transaction as current-fact/history changes, assert that the baseline version remains current, and insert a committed refresh ledger row. Concurrent transactions touching the guard row conflict; stale prepared candidates must be recomputed. A committed run with the same refresh ID and input checksum can be recognized on retry. The setup alone provides no concurrency guarantee until that transaction is implemented and executed. Reference: https://docs.cloud.google.com/bigquery/docs/transactions.

### Publication control setup — learner-confirmed success after SQL correction

Initial seed INSERT failed because its SELECT had WHERE NOT EXISTS without a FROM clause. Chat correction added FROM (SELECT 1 AS seed); learner reported successful rerun. The setup is learner-confirmed; exact control row/version output has not been independently queried. Current facts/history remain unchanged by this setup.

### Next checkpoint — preview-capable cloud Gold publisher

Chat supplies learner-created publish_refresh.py in code/cloud-publish, using the existing monthly_merge.py contract and staged source tables. The publisher validates the manifest and frozen Silver summary, verifies source keys, projects measurements into the two current fact schemas, preserves pending-source NULLs for genuinely unpublished months, and stages fact/history candidates. Default preview logs merge counts without changing Gold; --publish enables the transaction. The transaction updates the shared control row only at the expected baseline version, extends monthly dim_date, merges affected fact keys, appends measure history and records the committed run together. Publication retries check the committed-run ledger and input checksum; concurrent/stale preparations fail rather than silently overwriting accepted facts. All warehouse publishers must follow this guard; unrelated manual writes do not advance its version.

Learner adds publish_refresh.py and includes the existing code/monthly_merge.py in a flat ZIP build context, updates Dockerfile to copy the three Python modules and use publish_refresh.py as entrypoint, and builds publish-runtime:v2. The existing jobs-snap-stage image remains v1. New Cloud Run job jobs-snap-publish will first run without --publish against manifest_870992f6162f33782e1c98cb; preview candidate tables are staging artifacts, not accepted Gold. Code/build/deployment/preview/transaction results remain pending. Agent supplies code in chat, edits only documentation, and performs no cloud mutation or ETL execution.

### Publisher v2 image — learner success and registry verification

Learner reported successful build. Read-only image describe confirms publish-runtime:v2 digest sha256:d60e66d22b2aafeb16970ab0afb9f0c010d7d86e1b3988a1f7d51eddd7fc5499. This establishes image availability, not preview or transaction acceptance.

Next learner creates Cloud Run Job jobs-snap-publish in us-central1 using publish-runtime:v2, one task/parallelism one, 1 vCPU, 1 GiB memory, 10-minute task timeout, retries zero and runtime account jobs-snap-publish@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com. Leave Command blank and add a single argument --manifest-table=project-4b0f63f3-e441-4289-b42.jobs_snap_staging.manifest_870992f6162f33782e1c98cb. Do not add --publish for this preview checkpoint. No secrets/environment variables are required. Learner executes once, then supplies final status preview, baseline_version, state_rows, industry_rows, history_events and grouped stats. Expected current row counts are 7,050/20,868 if no new keys were introduced; actual revision/event counts must be observed, not assumed zero. Candidate staging writes are expected; Gold facts/history/control/ledger remain unchanged in preview. Deployment and preview remain pending. Reference: https://docs.cloud.google.com/run/docs/configuring/jobs/containers.

### Cloud publication preview — accepted log inspected read-only

Learner reported preview success. Read-only jobs-snap-publish logs show container exit(0), status preview, refresh_run_id monthly-20261026-001, baseline_version zero, state_rows 7,050, industry_rows 20,868, history_events zero. Grouped merge statistics have zero inserts, revisions, initial observations and status changes; unchanged contributions are 300 jobs, 300 unemployment, 300 SNAP and 888 industry (1,788 total). This is cloud staging/merge preparation evidence, not a committed Gold publication or proof of revision-event insertion. New source lineage may replace older lineage on affected keys during publication while unchanged measurements retain their metadata.

Next learner opens Cloud Run > jobs-snap-publish > View and edit job configuration, retains the existing --manifest-table argument and adds --publish as a second separate argument. Save and execute once. The application recomputes candidates, validates the expected control version, and transactionally merges affected facts, extends dim_date if needed, appends actual events and records monthly-20261026-001 in refresh_publications. Expected successful output is status published with counts 7,050/20,868 and zero history events if inputs/current baseline stay unchanged. baseline_version in the log is the version read before publication (zero), while the committed control version should become one. On successful repeat of the same logical input, already_published should return without another commit. Actual transaction acceptance, warehouse/control/ledger verification and same-run retry acceptance remain pending learner execution. Do not invent revision events for unchanged values.

### First cloud Gold publication — successful completion log verified

Learner reported success after adding --publish. Read-only jobs-snap-publish logs show status published for monthly-20261026-001, baseline_version zero, state_rows 7,050, industry_rows 20,868, history_events zero and container exit(0). The supplied application emits this only after its BigQuery transaction result completes; direct control/ledger/fact queries remain pending learner verification. This establishes the initial cloud publication path for unchanged measurements, not a demonstrated nonzero revision-event publication or scheduled workflow.

Next learner executes jobs-snap-publish again without changing either argument. Expected already_published for the same logical refresh and no second transaction. Then run the chat-provided warehouse verification query: control version one; exactly one ledger row for monthly-20261026-001; current facts 7,050/20,868; total history 55,818; zero events for this unchanged refresh. Expected history total comes from the learner-verified baseline, not a new source release archive. Same-run retry and these direct warehouse results remain pending. Subsequent required work is orchestration parameter handoff, Workflows and the monthly Scheduler trigger.

### Gold publication and retry — warehouse results accepted

Learner supplied direct BigQuery result: control_version 1, publication_rows 1, state_rows 7050, industry_rows 20868, total_history_events 55818, refresh_history_events 0. Read-only latest Cloud Run logs independently show already_published for monthly-20261026-001 and exit(0). Together these establish one committed cloud refresh, preserved fact/history row counts for unchanged measurements, and same-logical-run retry without a duplicate publication. They do not demonstrate a real nonzero revision, concurrent-run rejection, or monthly scheduling.

### Next checkpoint — Workflows execution identity

Purpose: orchestrate the existing four Cloud Run jobs and managed Spark batch using a dedicated identity with data read access. Learner creates jobs-snap-workflow and grants project roles Cloud Run Jobs Executor With Overrides (roles/run.jobsExecutorWithOverrides), Cloud Run Viewer (roles/run.viewer), Dataproc Serverless Editor (roles/dataproc.serverlessEditor), and BigQuery Job User (roles/bigquery.jobUser). Executor-with-overrides permits per-run source environment and stage/publisher argument handoff; Viewer permits execution/operation status polling; Dataproc role permits batch submission/monitoring; BigQuery job role supports manifest/ledger queries.

Grant Service Account User (roles/iam.serviceAccountUser) on jobs-snap-process to jobs-snap-workflow. Grant Storage Object Viewer separately on Bronze and Silver buckets for execution-specific summary discovery/read. Grant BigQuery Data Viewer separately on jobs_snap_staging and jobs_snap_gold for staged-manifest discovery and committed-publication verification. All grants target jobs-snap-workflow@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com. No secret access, data editor, key creation or project Owner role is required. Enable Workflows API and Workflow Executions API through the console if prompted when opening Workflows; Scheduler setup follows after a complete manual workflow execution. Identity/grants, workflow YAML deployment and execution remain pending learner evidence.

Planned handoff reuses existing code: source Cloud Run execution names identify immutable summaries; GCS matchGlob discovers the exact execution/run summary without assuming a local or UTC calendar date; the staging manifest wildcard query resolves the accepted manifest by logical refresh ID. Cloud Run argument overrides pass the fresh manifest into the publisher. Workflow must wait for and verify each stage and stop on failure. Current user-confirmed publication used manually supplied inputs; no orchestration execution has occurred. References: https://docs.cloud.google.com/iam/docs/roles-permissions/run and https://docs.cloud.google.com/workflows/docs/reference/googleapis/storage/v1/objects/list.

### Workflow identity review — correct one service-account role

Learner reported grants complete. Read-only project IAM confirms all four requested project roles for jobs-snap-workflow. Bronze and Silver bucket IAM confirm Storage Object Viewer. Dataset viewer grants remain learner-confirmed. Read-only jobs-snap-process service-account policy instead shows roles/iam.serviceAccountAdmin for the workflow principal; roles/iam.serviceAccountUser is absent. Learner must replace Admin with Service Account User on that service account so the workflow can submit Spark as the processing identity. This is a correction to a saved role selection, not a request for project-wide administrative access. No workflow deployment or execution has occurred. Verify the corrected binding before deploying orchestration.

### Workflow service-account role corrected — verified read-only

Learner reported correction complete. Read-only jobs-snap-process IAM now shows jobs-snap-workflow with roles/iam.serviceAccountUser and no prior Admin binding in the returned policy. Project and bucket grant checks from the preceding checkpoint remain the observed evidence; dataset grants are learner-confirmed.

### Next checkpoint — monthly cloud workflow definition and manual execution

Chat supplies code/workflows/jobs-snap-monthly.yaml for learner insertion and console deployment. Workflow initializes a unique monthly-<workflow-execution-UUID> logical refresh ID and a unique Spark batch ID. It sequentially runs BLS and SNAP Cloud Run capture jobs with REFRESH_RUN_ID environment overrides; waits for successful completion; discovers the exact capture summary by execution ID using GCS matchGlob with pagination; submits runtime-3.0 PySpark with jobs-snap-process and the existing dependency image/shared Python URIs; waits and verifies Spark SUCCEEDED; discovers the versioned Silver summary; invokes stage_refresh with fresh arguments; resolves exactly one accepted staging manifest for the logical ID through a parameterized BigQuery manifest-table wildcard query; invokes publication with the fresh manifest and --publish; and verifies one committed ledger record before returning counts. It does not embed secrets, use local paths or assume source publication months/ingestion dates.

Cloud Run and Dataproc submissions use authenticated REST calls. Long-running operations are polled with bounded waits; idempotent HTTP reads use retry policy, while Cloud Run execution POSTs are not blindly retried. Stage/helper failures propagate and stop downstream work. Source application retries and immutable attempts remain in the existing ingestion components. Publication transaction guard remains responsible for preventing stale concurrent commits; an entire failed workflow is not automatically resumed by this version. Each new workflow execution creates a new logical refresh ID.

Learner opens Workflows in Google Cloud, enables prompted Workflows/Workflow Executions APIs, creates jobs-snap-monthly in us-central1 with jobs-snap-workflow, pastes the YAML, deploys, then manually executes with {}. This execution creates fresh source captures and runs the full cloud refresh through Gold. Expected workflow state SUCCEEDED and returned status complete with its generated refresh ID, accepted manifest and committed counts; actual revision events depend on the newly observed source data. Deployment, execution and scheduled automation remain pending learner evidence. Scheduler configuration follows only after this manual workflow succeeds. Manifest discovery currently queries accepted manifest_* staging tables under the 100-MiB query bound; a consolidated lookup registry is a later scaling improvement. References: https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.jobs/run, https://docs.cloud.google.com/workflows/docs/reference/googleapis/storage/v1/objects/list, and https://docs.cloud.google.com/managed-spark/docs/quickstarts/spark-batch.

### Workflow deployment parse error — empty-map expression correction

Learner supplied deployment parse error at wait_operation.inspect: inline {} in default(map.get(operation.body, "response"), {}) is rejected by the Workflows expression parser. Chat correction initializes empty_response: {} as a YAML assignment in wait_operation.initialize, then uses default(map.get(operation.body, "response"), empty_response). Apply the correction in both the local YAML and console editor. Deployment failed before execution; no workflow runtime acceptance is established. Corrected redeployment remains pending learner evidence.

### Workflow build error — list-valued parameter defaults

Learner supplied deployment build failure: default value for parameter env must be a literal. The provided run_job used list defaults for env and arguments. Chat correction changes both defaults to null and normalizes each to [] inside run_job.initialize before constructing container_override. Existing call sites and runtime override behavior remain the same. Apply to console/local YAML and redeploy; deployment/runtime remain pending. Reference: https://docs.cloud.google.com/workflows/docs/reference/syntax/subworkflows.

### Workflow reserved-variable correction and successful deployment

The next learner deployment failed because env was reassigned as a reserved variable. Chat correction normalized the env and arguments parameters into job_env and job_arguments instead, constructed container_override.env from job_env, and used job_arguments in choose_arguments. Learner reported successful deployment. Local YAML inspection now confirms these corrections and the empty_response assignment are saved. Detailed execution history and error-only call logging were recommended; triggers were deferred until a manual end-to-end run passed.

### First complete cloud workflow — independently verified success and stopping checkpoint

Learner reported workflow completion and asked whether this is a good stopping point. Read-only Workflows API inspection verifies jobs-snap-monthly execution ccac8dac-e4b0-4bfb-9efe-0712144189a9 SUCCEEDED, started 2026-10-26T08:09:44.240614190Z and ended 2026-10-26T08:18:22.039106634Z (about 8 minutes 38 seconds). Returned status complete, logical refresh monthly-ccac8dac-e4b0-4bfb-9efe-0712144189a9, state_rows 7050, industry_rows 20868 and history_events zero. The workflow's final step queries the committed publication ledger, so the returned result establishes its successful commit check, not only child-job completion. Agent did not execute any job or mutate cloud resources.

Accepted artifacts: BLS summary gs://jobs-snap-bronze-620503845148/bls/ingestion_date=2026-10-26/run_id=jobs-snap-bls-ingest-bnkmw/summary.json; SNAP summary gs://jobs-snap-bronze-620503845148/snap/ingestion_date=2026-10-26/run_id=jobs-snap-usda-ingest-gqhd7/summary.json; Silver summary gs://jobs-snap-silver-620503845148/silver/ingestion_date=2026-10-26/run_id=monthly-ccac8dac-e4b0-4bfb-9efe-0712144189a9/summary.json; staging manifest project-4b0f63f3-e441-4289-b42.jobs_snap_staging.manifest_ade7f8177bf429afec468e7d. This establishes a learner-triggered full cloud ingestion/Bronze/Silver/staging/Gold refresh without the local terminal performing pipeline processing. Nonzero revision publication and concurrent-conflict tests remain unobserved.

Stopping state: no further ingestion, publication or scheduling is requested for this turn. Monthly Scheduler setup is not yet completed in this learning sequence. Resume with the Scheduler invocation identity, first-day monthly time/timezone selection, workflow trigger configuration and verification. Billing screenshots around 02:18 local show actual cost $0 and live estimated cost approximately $0 with full $300 trial credit remaining; costs are provisional and should be reviewed after reporting catches up. Do not present this as a confirmed zero-cost pipeline. See gcp-resume-checkpoint.md for the compact handoff.

### Scheduling and dashboard work resumed — preferences and invocation identity

Learner requested scheduling and visualization next. The previous stopping instruction is superseded for this work; learner ownership of cloud changes/code remains. Asked for the first-day execution time/timezone (proposed 08:00 America/Boise or 08:00 UTC) and dashboard tool (Looker Studio or Power BI); answers remain pending. No trigger time or BI tool is accepted solely from those suggested defaults.

Read-only enabled-services listing returns no Cloud Scheduler API entry. First independent setup checkpoint: learner opens Cloud Scheduler and enables its API if prompted, then creates jobs-snap-scheduler with project Workflows Invoker (roles/workflows.invoker), leaving the optional service-account principal fields blank. Its identity will authenticate an OAuth request to the existing jobs-snap-monthly workflow; it is distinct from jobs-snap-workflow, which executes pipeline steps. It needs no Bronze/Silver, BigQuery or BLS-secret grants. API enablement, account creation and grant remain pending learner confirmation; no agent cloud changes or pipeline executions occurred.

Dashboard planning preserves the accepted complete-comparable reporting scope: 50 states for jobs/SNAP comparisons; common 48 states across the three industries for industry comparisons. Monthly job and participant levels must not be summed across months and presented as unique jobs/people. Existing Gold reporting views will be inspected/connected before chart instructions are finalized. Dashboard creation, source connection, chart validation and sharing remain pending. References: https://docs.cloud.google.com/workflows/docs/schedule-workflow and https://docs.cloud.google.com/data-studio/connect-to-google-bigquery.

### Scheduling timezone accepted; dashboard tool tradeoff under discussion

Learner selected UTC to align with pipeline timestamps. First-day monthly frequency remains accepted; 08:00 UTC is the previously proposed hour, not separately confirmed by this response. Learner is familiar with Streamlit from the AWS class project and asked why Looker Studio was recommended versus Power BI and whether Power BI costs money. Tool choice remains open. Current source inspection of ../2.1_Tue_steps.md:293 describes built-in Databricks notebook line charts; this is documentation evidence, not proof of which charts the learner executed.

Current official pricing/platform sources checked: Google describes the browser reporting product on its Data Studio page (the previously supplied Looker Studio URL redirects there), with no-charge self-service reporting and paid Pro features; BigQuery queries can still incur costs. Microsoft lists Power BI Desktop report creation with its free offering, Windows as the Desktop platform, and US Power BI Pro at $14/user/month paid yearly for publishing/sharing features. Existing organization licensing can affect incremental license cost. Streamlit is open-source Python and Community Cloud offers free app hosting; GCP hosting/query costs remain separate. Initial Looker Studio recommendation was based on browser-based use on the learner's Mac and direct BigQuery connectivity; Power BI is a suitable alternative when learning its semantic models/Power Query/DAX and the available Windows/licensing setup justify it. No BI subscription, VM or dashboard was created. References: https://cloud.google.com/data-studio, https://www.microsoft.com/en-us/power-platform/products/power-bi/pricing, https://learn.microsoft.com/en-ie/power-bi/fundamentals/desktop-get-the-desktop, and https://docs.streamlit.io/deploy/streamlit-community-cloud.

### Monthly time and dashboard tool accepted — Scheduler creation checkpoint

Learner accepted proposed 08:00 UTC on the first day of each month and selected Looker Studio. Read-only inspection verifies jobs-snap-scheduler exists, has project roles/workflows.invoker, and cloudscheduler.googleapis.com is enabled. Regional jobs list in us-central1 is empty: no schedule is yet configured there.

Learner opens Cloud Scheduler > Create job, name jobs-snap-monthly-trigger, region us-central1, frequency 0 8 1 * *, timezone UTC. HTTP target POST https://workflowexecutions.googleapis.com/v1/projects/project-4b0f63f3-e441-4289-b42/locations/us-central1/workflows/jobs-snap-monthly/executions, header Content-Type application/json, body {"argument":"{}"}. Choose Add OAuth token, account jobs-snap-scheduler@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com and scope https://www.googleapis.com/auth/cloud-platform. Keep request deadline default; set retry count zero for this initial trigger. Create, inspect the next scheduled time and use Run now once to validate invocation. A successful Scheduler request confirms workflow dispatch, not pipeline completion; separately verify the resulting Workflows execution SUCCEEDED/complete. Creation, invocation and next calendar-triggered firing remain pending learner evidence. Agent did not create or run a job. Reference: https://docs.cloud.google.com/scheduler/docs/tut-workflows.

After scheduling, learner opens Looker Studio (may appear as Data Studio), creates a blank report named U.S. Jobs and SNAP, connects the Google BigQuery connector to project-4b0f63f3-e441-4289-b42 > jobs_snap_gold > v_jobs_snap, and reviews the source fields before creating charts. Use basic reporting; no Pro subscription is needed for this checkpoint. Query charges remain separate. Source connection, live field types, charts and dashboard sharing are pending; industry reporting will use v_industry_month with its common 48-state scope. Reference: https://docs.cloud.google.com/data-studio/connect-to-google-bigquery.

## Presentation preparation — requirements consolidated, October 31, 2026

**Purpose:** Turn the instructor’s repeated presentation instructions into one preparation checklist before drafting slides or rehearsing. **Prerequisites:** Richard supplied four requirement sets and existing notes specified a November 6 deadline and a 10–30-minute presentation. No cloud execution is required for this documentation checkpoint.

**Instructions and expected result:** Use [presentation.md](presentation.md) as the consolidated source. Review the ten requirement IDs, suggested high-level-to-detail order, conditional AI requirement, demonstration options, and preparation checkpoints. Work through checkpoint 1 first: agree the problem, intended user, and opening; then proceed through sources, architecture, components, decisions, checks, demo, dashboard, and conclusion. The 18-minute outline and opening are drafts, not instructor mandates or accepted delivery material.

**Observed evidence and verification:** The supplied requirements were consolidated and the project README links to them. Local static checks cover requirement IDs, deadline/duration retention, local links, and Markdown whitespace/fences. This records preparation progress only. Earlier handoff statuses above are dated records; later conversation screenshots show dashboard work, but no fresh cloud inspection or presentation rehearsal occurred in this checkpoint.

**Remaining work:** Review each preparation checkpoint with Richard, collect/recheck current demonstration evidence, create the actual GCP diagram, select final visuals, choose the delivery medium, and rehearse within the required duration. Confirm submission details and any Azure-specific grading restriction. Do not introduce Bigtable/BNPL interview content or optional AI as implemented public-data pipeline features.

### Introduction accepted and working script created — October 31, 2026

Richard approved the proposed introduction and requested a separate file for what to say and do before transferring content to Google Slides. Created [presentation-script.md](presentation-script.md), separating slide content, speaking drafts/prompts, and demonstration actions. The accepted introduction is the only completed review item; the source explanation is next. Local checks passed for both presentation files’ links, whitespace, and fences, plus the single accepted checklist item. Remaining sections, diagram, exact demo artifacts, slides, and rehearsal remain pending. No cloud execution or new output verification was performed.
