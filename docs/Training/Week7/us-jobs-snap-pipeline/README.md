# U.S. Jobs and SNAP Participation Pipeline

## Purpose and scope

Explore how employment conditions, industry payroll jobs, and Supplemental Nutrition Assistance Program (SNAP, commonly called food stamps) participation changed across U.S. states from **January 2015 through December 2025, inclusive**, the historical assignment baseline. The operational plan then catches up from January 2026 and continues with monthly refreshes. A potential user is a community-services planner comparing employment conditions with food-assistance participation over time.

Main question: **How did SNAP participation change during periods of job losses and recovery?** The analysis will describe trends and relationships; it will not establish that employment changes caused changes in SNAP participation.

This is the source and scope reference for the [Week 7 Azure homework](../1.2_Mon_HW.md). The accepted design uses two monthly fact tables sharing `dim_state` and `dim_date`, with `dim_industry` for industry employment. `dim_date` has one row per month and exactly five fields: `date_key`, `year`, `quarter`, `month_number`, and `month_name`. See the [data model](data-model.md) for the tables and the [architecture and visual workflow](architecture.md) for scheduling, storage organization, revisions, and safe reruns. The working geography is the 50 states; exclude DC, territories, metro areas, regional totals, and national totals from the core facts. This geographic scope is a planning default, not verified source coverage.

**Status:** State-source verification performed on October 20, 2026. [Verification results](source-verification.md) confirm 50-state total jobs/manufacturing/retail histories and all expected SNAP state/month rows. Standalone construction is unavailable for two states; October 2025 unemployment is source-missing for all 50 states; one Wyoming SNAP benefit amount needs review. Industry scope is now accepted: manufacturing/retail for all 50 states and standalone construction for its supported 48. Source-exception handling and Azure implementation remain pending. These checks do not establish a deployed pipeline.

The [pipeline proposal](proposal.md) summarizes the six homework proposal requirements. The accepted analytical questions are: how do state payroll employment changes compare with SNAP participation changes, and which selected industries gained or lost the most jobs in each state? The customer-file exercise was separate daily classwork, reported completed by the learner; it is not a project input or remaining project task.

## Learning workflow

Follow the [project agent guidance](AGENTS.md) and maintain the [step-by-step learning record](steps.md). Implementation should be explained through CLI commands, console steps, or Terraform guidance that the learner executes, with what/why explanations and verification for each checkpoint. Terraform versus drag-and-drop authoring is still an implementation choice. Documentation edits do not authorize automatic cloud setup or pipeline execution.

### GCP learning companion

Start presentation preparation with the [consolidated instructor requirements and working checklist](presentation.md). For the ingestion technology decision, see [source-deployed functions versus container jobs](gcp-ingestion-functions-vs-jobs.md): AWS comparison, packaging/runtime responsibilities, observed experiment evidence, tradeoffs, and a speaking summary. The demonstrated GCP path uses Cloud Run Jobs; the tradeoff document retains the earlier exploration history.

For the personally funded GCP adaptation, start with [GCP theory through AWS/Azure comparisons](../gcp-data-engineering-scope.md), then use the [GCP learning plan and checkpoint record](gcp-learning-plan.md). It proposes Cloud Storage, PySpark, and native BigQuery tables, with local preparation before a measured managed Spark batch and optional hosted orchestration. The existing Azure architecture/proposal remains the instructor-project baseline. Both paths share the logical data model and source contracts; their physical storage, execution, account setup, and evidence records are distinct. The [dated setup record](gcp-learning-plan.md#15-setup-and-cost-control-results--october-23-2026) now distinguishes verified MCP project access, learner-configured budget/query controls, the nonadjustable daily quota, and unresolved billing-banner/refund questions. The first constant-only BigQuery query completed with learner-supplied result/job evidence (`US`, 0 bytes processed/billed); see the [learning record](steps.md#gcp-checkpoint--first-bigquery-query-job--completed-october-23-2026). The learner-created `jobs_snap_practice` dataset is verified in `us-central1`; its seven-day default table expiration is learner-confirmed. The `orientation_practice` table Preview matches all three invented CSV rows; saved schema/location/row count and seven-day expiration are learner-confirmed. A table-reading SELECT succeeded with all three fixture rows; the extra SQL drill was skipped by learner choice. Actual table-query job-byte details remain unverified. Cloud Storage bucket `jobs-snap-bronze-620503845148` is verified in `us-central1` with Standard storage, Uniform access, and public access prevention; the practice CSV object is verified at `practice/orientation-practice.csv` (151 B, Not public). The first real BLS response is locally captured and checked for Idaho total jobs in 2024 (12 unique monthly observations); a subsequent real capture has a verified matching manifest and persisted retrieval timestamp. The learner deferred real-source cloud upload to expand and validate local BLS/USDA historical ingestion, followed by six-month refresh modes using shared Python modules. The local 2015–2025 historical Bronze captures and Silver processing are complete: 32,736 BLS observations and 6,600 SNAP rows, with source exceptions retained. Local historical Gold is also complete: dimensions 50/132/3 and facts 6,600/19,536, with comparable-scope reporting outputs. All five native Gold table loads into BigQuery are learner-confirmed; learner-supplied warehouse count/key/relationship checks passed for all five tables, and both reporting views are learner-confirmed created (exact cloud view-count results not supplied). Historical BLS and SNAP Bronze cloud copies are learner-confirmed; remote object/hash verification, Silver cloud copies, catch-up, refresh, and hosted scheduling remain pending.

## Core data sources

| Dataset | Original publisher / access provider | Frequency | Units and meaning | Link |
|---|---|---|---|---|
| State unemployment rate | BLS Local Area Unemployment Statistics (LAUS) | Monthly | State resident labor-force unemployment rate, percent; select seasonally adjusted series | [LAUS data access](https://www.bls.gov/lau/data.htm) |
| State total nonfarm payroll employment | BLS Current Employment Statistics (CES), State and Area | Monthly | Jobs at workplaces in the state, usually published in thousands; select all-employees, total-nonfarm, seasonally adjusted series | [CES state data access](https://www.bls.gov/sae/data/) |
| State industry payroll employment | BLS CES, State and Area | Monthly | Payroll jobs by selected industry and state; select all-employees, seasonally adjusted series and verify units | [Published series availability](https://www.bls.gov/sae/additional-resources/list-of-published-state-and-metropolitan-area-series/home.htm) |
| State SNAP participants and benefits | USDA historical fiscal-year workbooks, state sections on regional sheets | Monthly historical data | Participants and benefit cost on the same row; validate state-section units and definitions before loading | [SNAP data tables](https://fns-prod.azureedge.us/pd/supplemental-nutrition-assistance-program-snap) |

These remain aggregate economic statistics, with more detail by state and industry. They are not individual company, worker, or recipient records. CES measures jobs by workplace location; LAUS measures people by residence. Cross-state commuting means the two measures do not describe exactly the same population.

### BLS access and series selection

- Planned access: the free [BLS Public Data API v2](https://www.bls.gov/developers/api_signature_v2.htm), with JSON responses. Register for a BLS key for higher limits and the 11-year request window; this is a separate key from FRED. See [registration and limits](https://www.bls.gov/developers/api_faqs.htm).
- Use the tested seasonally adjusted state LAUS/CES candidates in the [series inventory evidence](evidence/state-series-verification.json). Manufacturing and retail trade cover all 50 states; standalone construction covers 48, and the learner accepted all three with construction explicitly limited to those 48 states. October 2025 unemployment is a source-missing value, not a retrieval error.
- Build a series inventory mapping each source ID to state, measure, industry when applicable, units, seasonal adjustment, and coverage. Source lookup files are available for [CES](https://download.bls.gov/pub/time.series/sm/) and [LAUS](https://download.bls.gov/pub/time.series/la/).
- Request `startyear=2015` and `endyear=2025`; retain monthly periods `M01`–`M12`. Exclude annual-average periods such as `M13`.
- Manufacturing, construction, and retail trade are the accepted starting industries (October 24, 2026), using the verified 50/48/50-state coverage respectively. Use nonoverlapping categories; do not count an industry total together with its component industries.

For 50 states, the state/month fact has 6,600 expected keys. Public API verification found all 132 numeric observations per state for total jobs, manufacturing, and retail trade; unemployment has 132 rows but only 131 numeric values per state. Construction has 132 numeric observations in each of 48 supported states. These are source observations, not loaded fact counts. Preserve raw responses and series metadata because historical values can be revised. The original national FRED series `UNRATE` and `PAYEMS` cannot populate state facts and are no longer core inputs.

### USDA SNAP access

- Access: free public downloads; no API key is needed for the published files.
- Planned raw format: the historical ZIP archive and its source spreadsheets. Use the archive linked under **National and/or State Level Monthly and/or Annual Data** on the [SNAP data tables page](https://fns-prod.azureedge.us/pd/supplemental-nutrition-assistance-program-snap).
- Select state monthly participants, households, and benefits for the project window from state sections on the seven regional sheets. Retain source per-person/per-household benefits in Silver if useful for validation. Do not load the `US Summary` sheet into state facts.
- The recent national summary covers only recent fiscal years. Use the historical archive to obtain the earlier years needed for 2015–2025.
- Federal fiscal years run October through September: FY2015 includes October 2014–September 2015, and FY2026 includes October 2025–September 2026. Inspect FY2015 through FY2026 to cover the requested calendar window, then retain January 2015–December 2025.
- State inspection found all 6,600 target state/month records across 84 regional sheets, with consistent header meanings. One Wyoming benefit-cost record is negative and requires review; presence of every row is not proof that every measure is acceptable. See [SNAP verification](source-verification.md#usda-state-workbook-verification). Match state names to stable two-character state codes, preserving leading zeros.

Use the source landing page to locate the current archive rather than depending on a permanently fixed attachment filename. Retain the downloaded archive, extracted source files, source URL, retrieval timestamp, and relevant footnotes.

## Optional data: state real GDP

| Dataset | Original publisher / access provider | Frequency | Units | Link |
|---|---|---|---|---|
| State real gross domestic product | BEA regional accounts; exact table/line to be selected | Quarterly | Select the real GDP level and preserve its published dollar scale, base year, and annual-rate convention | [GDP by state](https://www.bea.gov/data/gdp/gdp-state), [regional tables](https://apps.bea.gov/iTable/?reqid=99&step=1), [API access](https://apps.bea.gov/api/signup/) |

The optional analysis window is **2015 Q1 through 2025 Q4**, with 44 expected observations per state if complete. State GDP selection, schema, and retrieval remain pending. National FRED `GDPC1` remains a reference only; do not copy one national value into every state. Keep GDP in a separate state/quarter dataset rather than repeating it in monthly facts.

Create a separate quarterly analytical dataset to compare GDP with the monthly measures:

- Average the three monthly employment levels, unemployment rates, and SNAP participant counts within each calendar quarter.
- Sum monthly SNAP benefits to obtain total benefits issued in the quarter.
- Do not sum participant counts and label the result unique people; a person may participate in multiple months.
- Keep the selected GDP units explicit. Do not sum annualized quarterly GDP levels as if they were quarterly dollar flows. Arithmetic average monthly unemployment rates are descriptive quarterly averages, not a newly calculated official quarterly unemployment rate.
- Require three available months for a complete quarterly aggregation, or explicitly mark the quarter incomplete.

## Planned Azure data flow

**Azure Data Factory → Azure Functions ingestion → ADLS Gen2 Bronze → Azure Databricks/PySpark Silver → shared dimensions and two Gold fact tables → Spark SQL results and charts.** Data Factory coordinates the stages; it is not the storage location. See the [architecture diagram](architecture.md#visual-workflow).

| Layer | Planned responsibility |
|---|---|
| Bronze | Preserve raw API responses and USDA downloads under explicit ingestion-date/run/attempt paths, with source and reporting-window metadata in manifests. Keep repeated snapshots immutable. If a spreadsheet is converted to CSV before Spark reads it, retain the original and document that conversion. |
| Silver | Normalize state identities and calendar months, identify industries from series metadata, parse values, retain notes and source identity, and validate each source at its own grain. Aim to use Delta tables as covered in class. |
| Gold | Build `dim_state`, monthly `dim_date`, `dim_industry`, `fact_state_month`, and `fact_state_industry_month` as described in the [data model](data-model.md). Publish only validated output versions. |
| Analytical output | Compare state employment and SNAP trends; compare selected industry job growth with state-level SNAP context without attributing recipients to industries. |

The selected Gold platform is Azure Databricks, using Spark/PySpark for processing, Delta tables for Gold, and SQL queries for analysis. No separate relational warehouse is selected. See [Delta Lake and Spark APIs](https://learn.microsoft.com/en-us/azure/databricks/delta/).

## Historical load and ongoing refresh

- Backfill the 2015–2025 baseline, then catch up from January 2026 to each source's latest available reporting month. Reuse the same parsing and validation logic for backfill and ongoing runs.
- After initial load/catch-up, refresh only six reporting months ending at each source's latest available month. Do not expand the window automatically for older gaps or corrections, and do not perform annual historical reconciliation for this project. Report any known older gaps or stale historical values as limitations.
- Schedule Data Factory monthly on day 1; 06:00 UTC is a proposed configurable time. Process data available at that run; later releases wait for the next monthly run or a manual rerun. The monthly run date is not the reporting month, and different sources can be at different latest months.
- Use one orchestrating pipeline with `concurrency=1`. Teach and verify request-level exponential backoff separately from Data Factory's fixed-interval activity retry policy; see the [architecture explanations](architecture.md).
- Preserve capture metadata, content hashes, change timestamps, revision counts, and old/new values as described in the [architecture](architecture.md). Repeated unchanged inputs must not duplicate facts or create false revisions.
- Keep 2015–2025 analytical views for the assignment while operational facts and the monthly date dimension can extend forward.

## Data quality and interpretation checkpoints

The accepted [missing-data policy](architecture.md#null-values-and-missing-records-are-different) processes valid available records and keeps legitimate partial data with NULLs and source-level status. Default Gold reporting views and visuals show only complete comparable records/months for their required state/industry scope. Detect entirely missing rows as well as missing values, and keep technical failures distinct from normal publication delays.

- Reconcile each state/measure and state/industry series against the 132-month calendar before joining. Identify missing or unavailable combinations rather than silently dropping them or treating them as zero.
- Check state/month uniqueness in `fact_state_month` and state/industry/month uniqueness in `fact_state_industry_month`. Verify every dimension reference resolves.
- Validate dates, numeric parsing, source units, nonnegative counts and benefits, and unemployment rates within 0–100 percent.
- Calculate job growth from changes in the selected CES state series; apply the verified unit multiplier. Distinguish percentage-point changes in unemployment from percent changes.
- Year-over-year comparisons need a prior-year observation. With only 2015–2025 inputs, those results begin in January 2016. An optional 2014 lookback can support 2015 comparisons while final outputs remain within 2015–2025.
- Preserve seasonal-adjustment metadata. The planned BLS selection is seasonally adjusted; verify availability and inspect SNAP's treatment before interpreting short-term movements together.
- Inspect SNAP footnotes for policy changes, pandemic-era benefits, revisions, or coverage changes that may affect interpretation. Benefits are dollar amounts as published; they are not inflation-adjusted merely because optional GDP is real GDP.

## Next checkpoint

Use the accepted manufacturing/retail 50-state and construction 48-state scope in the [verified sources and exceptions](source-verification.md), and decide handling of the Wyoming dollar anomaly before cost-dependent reporting. Then proceed to learner-executed Azure prerequisite and ingestion steps. The two-fact design and Databricks Gold platform are accepted; final physical types, source exception rules, ingestion, and Azure execution remain pending.


## GCP initial catch-up milestone — October 25 local / October 26 UTC, 2026

Learner-executed catch-up and BigQuery publication are accepted from supplied runtime/query evidence: 141 monthly dates, 7,050 state/month facts and 20,868 industry facts. Jobs extend through September 2026; jobs/SNAP comparisons extend through July, with 100 later state/month rows explicitly marked not_yet_published for SNAP. Reporting views contain 6,950 and 20,304 rows. Fifty missing unemployment values and one SNAP benefit review value remain preserved. This updates the earlier historical-only checkpoint records; recurring six-month refresh, revision-aware merging and hosted automation remain pending. Catch-up BLS cloud Bronze copy is the next learner action.
