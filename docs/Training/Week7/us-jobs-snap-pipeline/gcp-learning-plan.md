# Jobs/SNAP Capstone — GCP Learning Plan and Checkpoints

> Status: CLI/login and MCP project read verified; monthly budget and per-query limit configured by learner; daily quota nonadjustable; billing inconsistency deferred; BigQuery/storage orientation and one local BLS capture with manifest verified; historical inventory expansion is current
> Theory and costs: [AWS/Azure → GCP guide](../gcp-data-engineering-scope.md)
> Shared contracts: [data model](data-model.md), [source schemas](source-schemas.md), [source verification](source-verification.md)
> Reviewed: 2026-10-25 local / 2026-10-26 UTC

## How to use this plan

Work in the order below. The first checkpoint has concrete account/console instructions; later implementation checkpoints specify actions and acceptance evidence. Add the exact commands, configuration, and observed output as you reach each checkpoint. The learner writes transformations and executes cloud changes. This roadmap is not a completed pipeline or a request to deploy every service now.

The Azure [architecture](architecture.md), [proposal](proposal.md), and [learning record](steps.md) remain the instructor-project baseline. This document owns the proposed GCP physical adaptation. It reuses the business questions and logical/source contracts without replacing Azure Data Factory with a second undeclared orchestrator in the Azure design.

## Proposed technology decisions

| Decision | Recommended starting point | Reason / later change |
| --- | --- | --- |
| Personal spending | Aim for $0 out of pocket until a limit is selected | Sandbox/local preparation, then an eligible non-upgraded trial |
| Project location | `us-central1` for owned bucket, datasets, and later regional compute | One colocated region; do not substitute BigQuery `US` multi-region accidentally |
| Source capture | Shared Python helpers; final hosted choice open between source-deployed function and container Job | A Job runtime check passed; compare both interfaces using the [presentation tradeoff reference](gcp-ingestion-functions-vs-jobs.md) before selecting the final ingestion deployment |
| Bronze | Cloud Storage, private Standard flat-namespace bucket | Local retained copy supports preparation and recovery |
| Silver | Local PySpark → Parquet; managed serverless Spark will write to jobs-snap-silver-620503845148 | Bucket us-central1/Standard/Uniform/private verified read-only; use dedicated jobs-snap-process workload identity for proposed runtime 3.x |
| Warehouse | BigQuery native tables and GoogleSQL | Staging → candidate dimensions/facts → accepted reporting |
| Quality | Explicit contract checks and recorded acceptance | Add dbt/Great Expectations after the first working slice |
| Orchestration | Cloud Workflows is the required GCP target; local replay is preparation | Coordinate ingestion, managed Spark, BigQuery validation/publication and failures; no Composer deployment initially |
| Schedule | Monthly Cloud Scheduler trigger for Workflows after an accepted cloud test | First-day schedule; exact time/time zone selected during setup; no laptop dependency |
| Industry scope | Accepted: manufacturing + retail (50 states each), construction (48 supported states) | Industry remains a category in the shared fact; three-industry comparisons use the common supported 48-state scope |

The proposed hosted end state is Cloud Run ingestion → Cloud Storage Bronze → managed Spark → Cloud Storage Silver → BigQuery staging/Gold → accepted reporting, coordinated by Workflows. Completing a local Spark + cloud warehouse milestone is useful even before that automation exists; describe its runtime boundary accurately.

## 1. Account and billing choice

**Purpose:** Establish a personally controlled learning environment before consuming trial time or deploying services.

**Prerequisites:** A personal Google Account you control, browser access, and a decision about whether to start with sandbox. No employer/school identity or paid Google Workspace subscription is needed for the personal route. Use **No organization** where offered for a personal account. Do not enter card details, passwords, source API keys, or tokens in this file or chat.

### 1.1 First session: sandbox orientation

1. Sign in with your personal account at [BigQuery Studio](https://console.cloud.google.com/bigquery).
2. Complete the displayed country/terms prompts if this is your first visit. Create a project through the project selector if needed. Suggested display name: **Jobs SNAP Learning**; choose an available project ID and record it privately or in a nonsecret project configuration.
3. Select that project in the console header and confirm BigQuery identifies the experience as sandbox when no billing account is attached.
4. Record account type, project ID, project number, and observed billing state. These are distinct from a chosen bucket/dataset region.
5. Do the tiny query in Checkpoint 2. Do not activate a billing trial solely to remove a prompt during an orientation exercise.

**Expected observation:** The selected personal project can run a small BigQuery query with no billing account attached. Sandbox restrictions are documented in the [current sandbox guide](https://docs.cloud.google.com/bigquery/docs/sandbox).

### 1.2 When ready for Cloud Storage and incremental SQL

Use the [official Free Trial signup](https://cloud.google.com/free) if eligible. Read the offer and payment-verification terms displayed for your account before accepting. Confirm **Free Trial**, remaining credit, and end date in **Billing**. The guide's $0 plan does not require selecting **Activate/Upgrade** for a paid billing account. If the account is already paid or ineligible for a trial, stay with sandbox/local practice until a paid limit is deliberately chosen.

Link the intended capstone project to the intended trial billing account through **Billing → My projects** or the equivalent project billing action. Verify the project selector afterward. Do not create duplicate billing accounts just because signup also created a default project.

**Expected observation:** The capstone project has the intended trial relationship, not an unexplained paid upgrade. Account eligibility and displayed billing state are evidence supplied by the learner, not assumed from a successful console login.

### 1.3 Set cost controls before using paid-capable services

1. In **Billing → Budgets & alerts**, create an alerts-only budget scoped to this project. Suggested **gross usage monitoring** target: $5/month, with 20%, 50%, 80%, and 100% actual thresholds plus a forecast alert where offered. This is an alert target, not a spending authorization or hard cap.
2. Inspect credit treatment. Excluding credits makes credit-funded resource use visible to the alert; also review net costs/remaining trial credit separately.
3. Confirm your own email receives alerts. Billing data and notifications can lag.
4. In BigQuery query settings, choose on-demand learning behavior without purchasing reservations. Set maximum bytes billed for each table-reading query; a suggested first tiny-data ceiling is **100 MiB = 104857600 bytes**. If a query is rejected, inspect its estimate rather than automatically raising the limit.
5. Before regular querying, configure a conservative project/user daily query quota where supported; a proposed learning target is **1 GiB/day**, using the console's displayed units. This limits query processing, not all project charges.
6. Keep managed Spark and any hosted job manual until you have measured a run. No active schedule, permanent cluster, managed Airflow environment, or paid capacity reservation is required for setup.

References: [budget configuration](https://docs.cloud.google.com/billing/docs/how-to/budgets), [BigQuery query cost controls](https://docs.cloud.google.com/bigquery/docs/best-practices-costs), and [custom query quotas](https://docs.cloud.google.com/bigquery/docs/custom-quotas). Service-specific spend caps exist for eligible services, but are not an all-project cap; see the [current coverage list](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

**Verification before Checkpoint 3:** You can identify the selected project, billing mode, trial end date if applicable, alert scope/credit treatment, and query-byte controls. Record errors or ineligibility rather than trying another paid service to work around them.

### 1.4 Local CLI and MCP preparation

**Purpose:** Establish local tooling and then authenticated inspection before creating capstone resources. Installing a CLI, authenticating, registering MCP, verifying MCP connectivity, and configuring cloud cost controls are separate checkpoints.

**Learner report:** Trial signup completed with a credit card and a requested $30 payment, still pending at the time of the report. The exact billing mode, posted balance, trial activation, and refund eligibility have not been inspected. Do not treat an anticipated refund as confirmed. [Google's refund guidance](https://docs.cloud.google.com/billing/docs/how-to/resolve-issues) describes account-specific eligibility and requests.

**Observed local prerequisites, 2026-10-23:** Apple-silicon macOS (`arm64`); Homebrew at `/opt/homebrew/bin/brew`; Node.js `v24.11.1`; npm `11.6.2`; `npx` and Codex available. `gcloud` was not on PATH and no Google Cloud CLI appeared in the installed Homebrew cask list. No installation, Google login, MCP registration, or cloud API call was performed in this prerequisite check.

**Installation commands, completed by the learner:**

```bash
brew install --cask gcloud-cli
gcloud version
```

Homebrew installs Google's CLI locally; `gcloud version` verifies the executable can start. It does not establish authentication, a selected project, billing activation, or resource deployment. If the second command is not found, retain the installation output so PATH guidance can be matched to the actual installation. See [Google's Homebrew installation instructions](https://docs.cloud.google.com/sdk/docs/downloads-homebrew).

**Learner-supplied installation evidence:** `gcloud version` returned Google Cloud SDK `590.0.0`, `bq 2.1.40`, bundled Python `3.14.8`, core `2026.10.16`, `gcloud-crc32c 1.0.0`, and `gsutil 5.37`. The installation notice recommends adding `/opt/homebrew/share/google-cloud-sdk/bin` to PATH for additional components. The supplied version output establishes that `gcloud` already resolves in the learner's current terminal; no shell startup file was edited by the agent.

**CLI authentication commands, completed by the learner**, using the personal Google Account:

```bash
gcloud auth login
gcloud auth list
```

The first command opens browser-based Google authentication and stores CLI credentials locally. After completion, the second lists CLI accounts and marks the active one. Expected evidence is a login-success message and the intended active account. The learner may redact the email address when reporting output; do not share login codes, tokens, or browser authorization URLs. See [Google's CLI authentication instructions](https://docs.cloud.google.com/sdk/docs/authenticate).

**Learner-supplied authentication evidence:** `gcloud auth list` showed one credentialed personal account marked active with `*`. This establishes the CLI active login from supplied output; no token or email address needs to be saved here. It does not establish the capstone project, billing mode, or cost controls.

**Project discovery command, completed by the learner**, without creating or changing one:

```bash
gcloud projects list --format="table(projectId,name,projectNumber)"
```

The expected output identifies project IDs, display names, and numeric project numbers visible to the active account. Share the result before selecting or creating a project. Project listing is not verification of its linked billing account. See [gcloud projects list](https://docs.cloud.google.com/sdk/gcloud/reference/projects/list). Project/billing inspection, scoped MCP connection with verified read access, and native GCP guardrails remain subsequent checkpoints.

**Learner-supplied project discovery:** The listing returned one accessible project: ID `project-4b0f63f3-e441-4289-b42`, display name `My First Project`, number `620503845148`. These identifiers come from supplied CLI output; billing linkage and active CLI project have not yet been verified. Reuse this project initially rather than create a duplicate solely for naming.

**Next action: select the local CLI default and inspect billing linkage:**

```bash
gcloud config set project project-4b0f63f3-e441-4289-b42
gcloud billing projects describe project-4b0f63f3-e441-4289-b42
```

The first command changes the local CLI default, not the project name or its billing relationship. The second reads the project's billing metadata. Inspect `billingEnabled` and `billingAccountName`; this response alone does not distinguish trial credit from paid billing, verify a pending payment, or establish refund eligibility. Account-level billing inspection and MCP setup follow after this output is reviewed. See [billing project description](https://docs.cloud.google.com/sdk/gcloud/reference/billing/projects/describe).

**Learner-supplied billing-linkage evidence:** `gcloud billing projects describe` returned `billingEnabled: true` and `billingAccountName: billingAccounts/015F57-0F7452-F7D2B5` for the project. This confirms the reported project/account link, not trial-versus-paid mode, remaining credit, payment settlement, or cost controls. No separate output confirming the local CLI default selection was supplied.

**Next action: inspect account mode in the console.** Open [this billing account's overview](https://console.cloud.google.com/billing/015F57-0F7452-F7D2B5/overview). Locate the account-type label, which Google documents as **Free trial account** or **Paid account**, and record any remaining trial credit/days. View the status without choosing Activate/Upgrade. Remaining promotional credit alone does not prove the account is still in non-billable trial mode. See [Google's account-mode check](https://docs.cloud.google.com/free/docs/free-cloud-features#am-i-going-to-be-billed).

**Learner-supplied billing screenshot:** The main overview shows **Free trial account**, **$300 out of $300**, and **90 days remaining**, ending **January 22, 2027**. The same page's top banner says the free trial is over. Record this inconsistency rather than treating the account as paid or assuming its trial activation is fully reconciled. Do not click Upgrade. No screenshot establishes settlement/refund of the requested $30 payment.

**Next action: register a local Google Cloud MCP server in Codex.** This configures a local stdio process, not a hosted Cloud Run server or paid compute deployment:

```bash
codex mcp add gcp \
  --env CLOUDSDK_CORE_PROJECT=project-4b0f63f3-e441-4289-b42 \
  -- /usr/local/bin/npx -y @google-cloud/gcloud-mcp

codex mcp get gcp
```

The absolute `npx` path was verified in the prerequisite check. On first launch, `npx` may download the Google-maintained package. The environment variable selects the default project for this server; it is not an IAM restriction preventing access to other projects. The server inherits the active gcloud credentials/permissions, so initial verification uses read operations only. Limited IAM access and persistent GCP cost controls remain separate tasks.

Expected registration evidence is a configured server named `gcp` with the intended command, arguments, and project environment. Configuration is weaker than a connected server or a successful authenticated tool call. After registration, refresh/restart the client's MCP connection and verify a harmless project read before changing any resource or cost configuration. No separate service-account JSON key is needed for the gcloud CLI-based connection. References: [Google-maintained server setup and permissions](https://github.com/googleapis/gcloud-mcp) and [Codex MCP configuration](https://developers.openai.com/codex/mcp).

**Learner-supplied MCP registration evidence:** `codex mcp get gcp` reports `enabled: true`, stdio transport, command `/usr/local/bin/npx`, arguments `-y @google-cloud/gcloud-mcp`, and a configured `CLOUDSDK_CORE_PROJECT` environment value (masked by the CLI). This confirms saved registration; no runtime connection or Google API request is established. The agent's available-tool discovery in the current session contains no GCP/gcloud tool yet.

**Next connection checkpoint:** Reload the client's MCP servers where supported, or restart the Codex client, then check MCP status for `gcp`. In Codex CLI, `/mcp` shows server status. Return to this conversation after reload; the agent can rediscover the server and perform a harmless project-description read when its tool is available. Preserve any startup error for troubleshooting rather than repeating cloud login or changing permissions without evidence.

### 1.5 Setup and cost-control results — October 23, 2026

This dated update supersedes the earlier pending connection/payment statements while preserving the setup history above. Evidence is identified as agent-observed or learner-supplied; the learner executed all cloud configuration changes.

| Checkpoint | Actions / configuration | Observed evidence and limits |
| --- | --- | --- |
| MCP authenticated read | After client restart, discover `mcp__gcp__run_gcloud_command`; run `gcloud projects describe project-4b0f63f3-e441-4289-b42 --format="json(projectId,projectNumber,name,lifecycleState)"` through MCP | Agent-observed response: project ID matches, number `620503845148`, name `My First Project`, lifecycle `ACTIVE`. Establishes authenticated project read, not unrestricted IAM or pipeline runtime. |
| Monthly budget | Billing → Budgets & caps → Create new; alerts-only budget named `jobs-snap-monthly-alert`, Monthly, $5, All projects (1), All services | Learner screenshot confirms saved budget, $0.00 / $5.00, and spend cap Not applicable. Learner reported the UI would not allow selecting just the sole project. Scope includes any additional projects linked later. |
| Credit treatment | In Scope, uncheck Savings programs and Other savings so selected credits do not reduce tracked usage costs | Learner confirmed both unchecked. These budget settings do not decline actual billing credits or discounts. |
| Alert rules and recipients | Actual thresholds 20%, 50%, 90%, 100%; additional 100% Forecasted; email billing admins/users enabled; no Monitoring channels or Pub/Sub integration | Screenshot confirms percentages; learner confirmed the forecast rule after review. The retained 90% threshold is $4.50, differing from the earlier proposed 80%/$4.00. Recipient delivery has not been tested. Alerts can lag and do not stop spending. |
| Per-query bytes | BigQuery SQL editor → Edit → Query settings → Advanced options → Maximum bytes billed → `104857600` → Save | Learner reported saved: 100 MiB per query using that configuration. No runtime rejection test or project-wide default established; check the setting in later query tabs/clients. |
| Daily query quota | IAM & Admin → Quotas & System Limits; filter Service = BigQuery API, Name = Query usage per day; inspect edit availability | Screenshot shows 209,715,200 MiB (200 TiB), 0 MiB usage, Adjustable = No; learner confirmed quota is not adjustable. Proposed 1 GiB/day was not applied; no cause established. |
| Trial/account inspection | Billing Overview and Manage billing account | Screenshots show Free trial account, $300 remaining, 90 days remaining, end January 22, 2027, $0.00 displayed costs; contradictory trial-over banner persists. Account management shows Direct and the intended linked project; this does not reconcile activation status. |
| Manual payment | Billing transaction history → payment entry | Screenshot shows a $30 manual payment and ending balance −$30, plus a separate declined attempt contributing $0. Learner opened the payment and reported Completed. Google-side payment completion is recorded; bank settlement, refund eligibility, and why signup requested payment remain unverified. Payment/card/receipt identifiers are intentionally omitted. |

Remaining work: billing-support clarification is deferred at the learner's request; do not upgrade billing or make another payment to work around the banner. The tiny orientation query subsequently completed with learner-supplied evidence (see Checkpoint 2 and steps.md); practice dataset creation subsequently completed in `us-central1` (see steps.md), while storage-bucket setup remains pending. No capstone datasets, buckets, ingestion, managed compute, or schedules have been established by these setup checks.

References checked during this walkthrough: [budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets), [maximum bytes billed](https://docs.cloud.google.com/bigquery/docs/best-practices-costs#restrict_the_number_of_bytes_billed_per_query), [custom query quotas](https://docs.cloud.google.com/bigquery/docs/custom-quotas), and [payment history](https://docs.cloud.google.com/billing/docs/how-to/view-history).

## 2. Learn BigQuery's object model with a tiny exercise

**Purpose:** Learn project → dataset → table/view and query-job behavior without implementing the capstone transformations.

In BigQuery's SQL editor, run this deliberately invented one-row result:

```sql
SELECT
  'ID' AS state_abbreviation,
  202401 AS date_key,
  'orientation_only' AS record_kind;
```

**Expected:** One row, not a BLS/USDA observation. Inspect the query job details and selected processing location; a query without a table does not teach realistic table-scan cost. Do not save it as a project fact.

In Explorer, open the selected project's menu and **Create dataset**. Suggested dataset: `jobs_snap_practice`, location **`us-central1`**. Review the location explicitly. A billed-project practice dataset can have a short default table expiration, such as seven days, if you accept automatic cleanup; keep original inputs locally. Sandbox enforces its own expirations and other restrictions.

Next, upload a tiny clearly labeled local practice CSV using **Create table → Upload**, inspect its schema, and use Preview. Choose explicit types rather than assuming autodetection establishes the intended source contract. Write your own SELECT/filter/aggregate and inspect estimated/processed bytes with the query limit configured. Do not use a large public dataset just to see a result.

**Verification:** Explain the difference between an ADF dataset and a BigQuery dataset, point to a table schema and job ID, and distinguish previewing rows from querying data. No capstone implementation is claimed.

References: [create datasets](https://docs.cloud.google.com/bigquery/docs/datasets) and [batch-load overview](https://docs.cloud.google.com/bigquery/docs/batch-loading-data).

## 3. Establish the GCP storage boundary

**Purpose:** Learn cloud object storage before building many transformations. Requires the deliberate billing/access decision from Checkpoint 1.

In **Cloud Storage → Buckets → Create**, use a globally unique bucket name, single region **`us-central1`**, Standard storage, uniform bucket-level access, and public access prevention. Keep hierarchical namespace disabled for this simple first bucket. Inspect retention, soft-delete, and versioning settings before accepting them: recoverability and stored-byte cost are tradeoffs. Do not lock a retention policy during a disposable lab.

Upload one small nonsecret file and verify its name, byte size, and `gs://` URI. Keep original source captures distinguishable from synthetic practice data. Enable only the APIs required for this checkpoint; postpone Spark, workflow, and hosting configuration until needed.

**Verification:** Identify the bucket location, access mode, size, and object path. Explain why successful console upload does not yet establish a later service account's access. Reference: [create a bucket](https://docs.cloud.google.com/storage/docs/creating-buckets).

## 4. Build one explainable source-to-Bronze slice

**Purpose:** Preserve a trustworthy input before writing Silver transformations.

Start with the proposed Idaho 2024 development slice, or an explicitly selected equivalent. Reuse the verified source inventory rather than rediscovering every series. Choose one BLS response first, then one USDA workbook/member. Read the existing [source schema](source-schemas.md) before parsing.

Write bounded local ingestion for that small scope. Save original bytes and a manifest with source URL/identity, retrieval time, reporting window, content hash, and run/attempt IDs. Upload to a new immutable Bronze path. No external API calls should occur independently in unbounded Spark executor tasks.

**Verification:** Open one capture and trace one reporting period to its source and manifest. Distinguish the API's HTTP/request status from whether its requested series actually returned data. The checkpoint supplies evidence of capture, not accepted facts. Exact code remains the learner's work.

## 5. Build and validate source-grain Silver locally

**Purpose:** Apply existing PySpark knowledge to a new deployment target while controlling cost.

Use the repository's existing `.venv` and installed Spark tooling after checking compatibility. From the repository root, clear the previously conflicting `SPARK_HOME` setting for the local PySpark path if necessary. Do not install another global Spark/Python setup as a default.

Read saved Bronze inputs. Normalize state/month/industry identity and numeric units, preserve metadata/status, and write Parquet to a separate Silver output. Keep the source tables separate until their own keys are validated. Compare schema, rows, keys, missing markers, and source values before uploading the output.

**Verification:** The selected state/month and state/industry/month keys are unique; state codes retain leading zeros; legitimate missing measures are NULL/status-aware; originals remain recoverable. The negative Wyoming amount and October 2025 gap stay in the full-scope test plan even if this slice does not contain them. Local success is recorded as local evidence.

## 6. Load BigQuery staging and build the two facts

**Purpose:** Learn the warehouse boundary separately from parsing source files. Use trial/billing-enabled BigQuery for later DML, not sandbox's unsupported MERGE path.

Upload the validated Parquet to Cloud Storage Silver. Create `jobs_snap_staging` and `jobs_snap_gold` datasets in the same selected region. Batch-load source-grain tables from the exact Silver paths, with reviewed types. Compare source/Silver/loaded keys and measures using load-job and data-quality evidence.

Implement the [shared logical model](data-model.md): `dim_state`, five-field monthly `dim_date`, `dim_industry`, `fact_state_month`, and `fact_state_industry_month`. Use GoogleSQL to build candidate outputs. Tests must establish dimensional uniqueness, valid references, fact-key uniqueness, source reconciliation, and report-specific coverage before the outputs are accepted.

**Verification:** A single state/month can be traced across both facts and shared dimensions without repeating SNAP as industry-specific data. Candidate checks pass before default reporting views expose the new result. The exact publication/transaction mechanism is designed and verified here, not assumed to be atomic merely because several SQL statements succeeded.

## 7. Prove replay, revision, and failure behavior

**Purpose:** Demonstrate the difference between one successful run and a dependable pipeline.

Run the same saved input twice and compare current facts and revision records. Apply a clearly labeled test revision to a copied development input, verify only the intended business keys change, and retain old/new evidence. Keep published raw data untouched. Add a controlled invalid key/schema case and establish that it blocks affected acceptance without damaging the previously accepted output.

Implement the accepted backfill/catch-up/six-reporting-month-window rules. Define the single-writer guard for manual and future scheduled runs. Do not automatically broaden the refresh window to hide older gaps.

**Verification:** No duplicate current keys or false revisions from unchanged reruns; intended revision tracked; failed candidate not published. Complete-only reports still distinguish legitimate missing source values from technical failure.

## 8. Repeat a proven Spark slice as one managed batch

**Purpose:** Gain actual GCP Spark experience without funding an idle cluster.

Estimate a bounded standard-tier serverless batch using the [current pricing](https://cloud.google.com/products/managed-service-for-apache-spark/pricing). Configure the necessary managed Spark API, runtime identity, input/output access, network prerequisites, compatible runtime/dependencies, bounded resources, and execution time. Exact IAM/network commands are added after inspecting the project's actual setup; a service name alone is not sufficient configuration.

Submit only the already-tested small transformation. Use a unique output run path, observe completion, compare it with the local result, and review usage. Stop/cancel unexpectedly long work. No persistent cluster or interactive session is required for this batch milestone.

**Verification:** Capture job ID, runtime, terminal state, input/output contract, reconciliation, and observed billable usage. A submitted batch or success icon alone is insufficient. Record retained script/output/log storage and any cleanup work separately from compute completion.

## 9. Add cloud ingestion and orchestration only after the manual path works

**Purpose:** Reuse Week 6 orchestration knowledge to make the pipeline repeatable.

Package bounded ingestion as a Cloud Run job with an attached runtime service account. Introduce Secret Manager if hosted ingestion uses a source API key. Review build/image storage, logging, job retry/timeout settings, and IAM.

Define a Workflows sequence that starts ingestion, observes successful completion, starts Spark, waits for its result, loads staging, runs modeling/validation, and publishes only accepted outputs. Pass a run ID, frozen config version, and source reporting windows through each stage. Separate request retries from whole-job retries. Implement the single-writer strategy from Checkpoint 7; a monthly schedule alone does not prevent manual overlap.

After a successful manual workflow and failure/recovery exercise, optionally create **one** Cloud Scheduler trigger for day 1. The existing proposed time is 06:00 UTC; it remains a configurable default until selected. Disable/pause it when not actively practicing.

**Verification:** The execution graph shows waiting/dependency behavior, downstream failure handling, one writer, and accepted-output preservation. Cloud automation is its own milestone, not something implied by the earlier local/cloud hybrid result.

## 10. Expand, explain results, and close the cost loop

Expand the same verified logic to the accepted historical scope and initial catch-up after industry/exception choices are recorded. Build the two analytical comparisons using complete comparable records. Keep units, seasonal adjustment, SNAP footnotes, and the distinction between correlation and causation visible.

Save architecture, source manifests, representative lineage, validation/revision evidence, query results, and limitations. Add a lightweight chart only after the SQL result is understood. Warehouse queries issued by dashboards also consume resources.

Review **Billing → Reports** by project/service, including usage before promotional credits and remaining trial credit. Compare actual usage with your forecast. Export needed results/code locally before trial expiry. Inventory schedules, jobs/sessions, retained objects/images/logs, and tables before choosing cleanup. Resource deletion and billing changes are learner-executed decisions; this document performs neither.

**Verification:** You can explain which parts ran locally, which ran in GCP, what remains manual, what an observed run cost, and what it would take to operate monthly. No production-scale or employer-experience claim follows from a small training lab.

## Execution record

| Checkpoint | Status | Observed evidence |
| --- | --- | --- |
| 1. Account and cost controls | Partially complete; limitations recorded | CLI/login confirmed; agent-observed authenticated MCP project read; learner-created $5 monthly budget and saved 100 MiB per-query limit; daily quota nonadjustable; Google-side $30 payment completed per learner; conflicting trial banner/refund eligibility unresolved, further billing investigation deferred |
| 2. BigQuery orientation | Sufficient to advance; extra SQL drill skipped by learner | Learner result and Job information confirm one invented row, successful constant-only job, location US, 185 ms, 0 B processed/billed, temporary result; practice dataset verified in us-central1; seven-day default table expiration subsequently confirmed by learner; orientation_practice created with Preview matching all three invented rows; saved schema/location/three-row count/seven-day expiration confirmed by learner; SELECT * LIMIT 1000 succeeded with three rows, editor estimate 114 B and visible 100 MiB ceiling; extra filter/order drill skipped by learner; actual table-query job bytes/location and ceiling rejection remain unverified |
| 3. Cloud Storage boundary | Bucket and practice object verified | Learner Configuration screenshot verifies jobs-snap-bronze-620503845148, us-central1, Standard, flat namespace, Uniform access, enforced public access prevention, Not public, Soft Delete header; practice/orientation-practice.csv verified at 151 B, Standard, Not public; exact saved recovery settings and content-hash reconciliation remain unverified |
| 4. Bronze source slice | Both local historical Bronze captures complete | Learner run 7882c36124674a5cbe44f04a8b32c715: five registered batches, 248 series, 32,736 baseline monthly observations including 50 source-missing markers; saved raw checksums verified offline. SNAP archive run a4a640c086d74c21b472f08f84306277 accepted with twelve FY2015–FY2026 workbooks; historical Bronze cloud uploads subsequently learner-confirmed; catch-up/refresh pending; implementation code supplied in chat for learner execution |
| 5. Local Silver | Complete for the 2015–2025 baseline | Learner-run version 7282829984ac46e1912d2edc0622daf0: 32,736 BLS observations, 6,600 SNAP rows, 50 source-missing BLS values and one flagged SNAP benefit value; saved summary confirmed. Local Gold subsequently completed; cloud loading pending |
| 6. Warehouse/model | Local historical Gold complete; BigQuery loads learner-confirmed | Learner run 9b11e5713cbe4ba6abc45d7cdd2b622e: dimensions 50/132/3; facts 6,600/19,536; reporting outputs 6,600/19,008. Saved summary confirmed; Gold dataset learner-confirmed created in us-central1; all five native table loads learner-confirmed; learner-supplied warehouse query passed all five count/key/relationship checks; reporting views learner-confirmed created; exact cloud view counts not supplied |
| 7. Replay/revision/failure | Initial catch-up Bronze/Silver complete; monthly refresh and revision merge pending | BLS catch-up run 43e4e0749e4349ceb1f92122acfc26a6 accepted 2,232 new rows through September 2026; saved SNAP archive reused through July. Learner-run combined Silver 4a67bce75c5d4c5680b158119930c6ec has 34,968 BLS and 6,950 SNAP rows. Catch-up Gold 6efac951e42245c389eb7659d92a8fa4 completed with facts 7,050/20,868 and reports 6,950/20,304; BigQuery catch-up acceptance passed from learner results: 141 dates, facts 7,050/20,868, views 6,950/20,304, cutoffs September/July 2026, 100 correctly pending SNAP rows, 50 missing rates and one benefit review. Local merge contract and unchanged replay passed (1,788 contributions); BigQuery baseline history learner-verified at 55,818 unique events. Live monthly fact/history publication pending |
| 8. Managed Spark batch | Not started | None supplied |
| 9. Hosted automation | Required GCP end state; not deployed | Learner clarified monthly execution must run in GCP, with console resource creation owned by learner. Local replay validates shared logic before Workflows/Scheduler integration |
| 10. Expanded analysis and cost review | Not started | None supplied |

For each executed checkpoint, add the date, purpose, configuration/actions, expected versus observed result, verification, errors/resolution, and remaining work. Do not mark it complete from documentation, parser checks, or a billing offer alone.


## Required GCP automation target — learner clarification October 25, 2026

The monthly pipeline must run in GCP without a local terminal or laptop. Local scripts/replay validate shared parsing, six-month selection, idempotent updates and revision rules before deployment; they are not the final operational workflow. Cloud Scheduler triggers Cloud Workflows monthly. Workflows coordinates bounded Cloud Run ingestion, immutable Cloud Storage Bronze, managed Spark Silver processing, BigQuery staging/validation and revision-aware publication. Use Secret Manager for the BLS credential and service accounts for cloud permissions; do not carry local personal CLI authentication or absolute Mac paths into scheduled execution. Add a single-writer guard, retries that preserve attempts, clear failure status and logs before enabling the recurring trigger. Verify one manually triggered cloud execution, then enable the schedule. User creates resources/deploys via guided console steps; agent supplies code/configuration in chat and edits documentation only. No automation resources or cloud processing executions are established by this design.


### Monthly replay acceptance

Learner-supplied results establish the pure merge contract checks and one unchanged-data replay: 1,788 source contributions unchanged, zero inserts/revisions/events, final facts 7,050/20,868, metadata preserved and no outputs written. This validates local change-detection semantics only. The next cloud checkpoint is the durable measurement-history baseline; live monthly source discovery, staging, atomic fact/history publication, single-writer control, managed runtime and Scheduler/Workflows execution remain pending.


### Cloud image build evidence

Learner supplied successful managed build 936e6aab-b346-44c8-b98e-788574b9693e (us-central1) and runtime-check image digest sha256:f13edc1447e0498ceb024c0fdbc123325c82edb66d4f2a7f5e2f82f20020e80b. Cloud Shell direct Docker pushes had failed with TCP refusal; managed build succeeded after the identified build account received guided source-bucket/image-repository permissions. The build account still lacks Cloud Logging write permission according to its nonfatal notice. Cloud Run runtime-check screenshot subsequently verified nonsecret object-created log, exit(0) and completed execution w6nz6; nonempty secret injection/create-only bucket write passed. Live source ingestion remains pending.


### Live BLS cloud capture evidence

Read-only MCP inspection verifies completed execution jobs-snap-bls-ingest-6zgpx and its complete Cloud Storage summary: five batches, 1,488 selected six-month observations, zero selected missing values, and September 2026 latest month for all 248 series. Live SNAP cloud capture, managed Spark processing, fact/history publication and monthly orchestration remain pending. The hosted ingestion-interface decision remains open; this is evidence for the container candidate.


### Live SNAP cloud capture evidence

Learner screenshot and read-only MCP summary inspection confirm jobs-snap-usda-ingest-2dxln preserved the archive and selected February–July 2026 from page metadata (required FY2026). The 300 state/month count is an expected parsing target, not an observed Silver row count. Both source capture candidates now execute in Cloud Run and save cloud Bronze. Cloud processing, current-fact/history publication and monthly orchestration remain pending. Next learner setup is a private processing/artifact bucket in us-central1.

### Live managed Spark Silver evidence — October 26, 2026

This checkpoint supersedes the pending cloud-Silver status in earlier chronological entries. Learner-submitted jobs-snap-silver-005 independently reports SUCCEEDED. Its complete summary at gs://jobs-snap-silver-620503845148/silver/ingestion_date=2026-10-26/run_id=cloud-silver-005/summary.json records 1,488 BLS observations (April–September 2026) and 300 SNAP state/month rows (February–July 2026), with zero selected missing BLS values and zero selected SNAP benefit-review rows. Runtime 3.0 uses the custom dependency image and uploaded shared parsers; outputs are versioned Parquet refresh slices. See steps.md for the observed node permissions, repository-reader grants and Cloud Resource Manager API prerequisite resolved during setup. BigQuery staging, revision-aware current-fact/history publication, Workflows and Scheduler remain pending. The next learner checkpoint is jobs_snap_staging in us-central1.

### Live cloud publication and retry evidence — October 26, 2026

This supersedes earlier pending staging/publication notes. Cloud Run staging logs verify 1,488 BLS/300 SNAP rows and accepted manifest_870992f6162f33782e1c98cb. Publisher preview found 1,788 unchanged source contributions and zero inserted/revised/history events. The learner then executed publication for monthly-20261026-001; read-only logs show published and exit(0). Learner BigQuery results verify control version 1, exactly one committed-run ledger row, facts 7,050/20,868, unchanged total history 55,818 and zero events for this refresh. Same-input retry logs show already_published/exit(0). This demonstrates the cloud refresh components and unchanged-input transaction/retry path, not real nonzero revision insertion, concurrent conflict handling or scheduled operation. The next checkpoint is jobs-snap-workflow identity/permissions, followed by one complete manually triggered Workflows execution and the monthly Scheduler configuration.

### Full cloud workflow accepted — stopping checkpoint October 26, 2026

This supersedes earlier pending manual Workflows execution notes. Read-only API inspection confirms jobs-snap-monthly execution ccac8dac-e4b0-4bfb-9efe-0712144189a9 SUCCEEDED in about 8 minutes 38 seconds. Returned status complete, state facts 7,050, industry facts 20,868, zero new history events and accepted staging manifest_ade7f8177bf429afec468e7d. The learner-triggered workflow ran fresh ingestion through committed Gold verification entirely in GCP. Cloud Scheduler/monthly trigger setup remains pending. Billing currently reports $0 actual/approximately $0 live estimate; final gross cost is not yet established. See [the resume checkpoint](gcp-resume-checkpoint.md) for exact state, next work and ownership boundaries. Agent performed read-only verification and documentation edits, not cloud deployment or ETL execution.
