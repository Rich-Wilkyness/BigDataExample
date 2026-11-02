# Source schemas: jobs, SNAP, and optional GDP

## Scope and evidence

The accepted project compares states and industries over a January 2015–December 2025 historical baseline, followed by catch-up and ongoing monthly refreshes. Read the active state-source plan below alongside the [data model](data-model.md) and [workflow architecture](architecture.md). A schema describes the fields and their types; grain describes what one record represents. The two accepted fact grains are state/month and state/industry/month, both referencing a monthly `dim_date`. Implementation and physical source-measure types remain pending.

The earlier national FRED and SNAP inspection is retained below as reference evidence. It does not establish state coverage and must not be mistaken for the active state-level acquisition plan.

**October 20 state verification:** See [source verification](source-verification.md) for actual public API responses, all 84 regional SNAP sheets, exact candidate series IDs, units, and exceptions. State/month presence has now been checked; source completeness is qualified by the October 2025 unemployment gap, two unsupported construction series, and a Wyoming negative benefit amount. Earlier national evidence remains a separate snapshot.

## Active state-source plan

| Required data | Planned source | Source identity needed | Destination |
|---|---|---|---|
| State unemployment rate | [BLS LAUS](https://www.bls.gov/lau/data.htm) | State + unemployment-rate measure + seasonal adjustment | `fact_state_month` |
| State total nonfarm payroll jobs | [BLS CES State and Area](https://www.bls.gov/sae/data/) | Statewide geography + total nonfarm + all employees + seasonal adjustment | `fact_state_month` |
| State industry payroll jobs | [BLS CES published series](https://www.bls.gov/sae/additional-resources/list-of-published-state-and-metropolitan-area-series/home.htm) | Statewide geography + selected industry + all employees + seasonal adjustment | `fact_state_industry_month` |
| State SNAP persons, households, benefit cost | USDA fiscal-year workbooks, state sections on regional sheets | State label + fiscal-year file + monthly label + report definition | `fact_state_month` |

Working geography: the 50 states, excluding DC, territories, metros, and aggregate areas. Seasonally adjusted BLS candidates have been tested via API and recorded in [series evidence](evidence/state-series-verification.json). Manufacturing and retail trade have complete numeric histories in all 50 states; standalone construction has 48-state coverage. The learner accepted manufacturing/retail for all 50 states and construction for its supported 48 on October 24, 2026.

### BLS JSON source fields

The planned [BLS API v2](https://www.bls.gov/developers/api_signature_v2.htm) uses `https://api.bls.gov/publicAPI/v2/timeseries/data/`. Select the desired series with the POST body's `seriesid` list and date range with `startyear`/`endyear`. These request parameters select data; state and industry names are not separate endpoint paths. Register for a BLS key using the [BLS API instructions](https://www.bls.gov/developers/api_faqs.htm); a FRED key cannot be used for BLS.

The inspected API responses return status/message information and a `Results` object containing a `series` array with IDs and observations. Actual response inspection now backs the documented fields below; two unsupported series return messages and empty data, despite the request-level `REQUEST_SUCCEEDED` status.

| Source field | Documented raw type | Meaning |
|---|---|---|
| `seriesID` on each returned series | String | Identity used to look up state, industry, measure, units, and adjustment |
| `data` on each series | Array | Observations for that series |
| `year` on an observation | String | Four-digit reporting year |
| `period` | String | Monthly code such as `M01`; keep `M01`–`M12` and exclude annual averages such as `M13` |
| `periodName` | String | Readable period name |
| `value` | String | Measurement text; inspected LAUS October 2025 values are `-`, a missing marker, not a negative rate or zero |
| `footnotes` | Array of objects | Source qualifications; objects can contain `code` and `text`, or be empty |

State and industry come from the source series definition, not from guessing based on the observation's numeric value. The [tested candidate inventory](evidence/state-series-verification.json) records IDs, state, program/measure, industry where applicable, units, adjustment, and observed coverage. BLS publication pages and the API confirm the identity/availability findings; direct command-line lookup-file downloads returned 403, as recorded in [verification](source-verification.md). The accepted selection explicitly excludes unsupported Delaware/Hawaii standalone construction series from requested/expected supported records while retaining their coverage exceptions.

At source level, one BLS record represents one series during one reporting period in the downloaded snapshot. After the series lookup, CES industry observations can be identified by state/industry/month, and LAUS/total-CES observations by state/month. Enforce uniqueness only after fixing the measure and seasonal-adjustment variant; otherwise two valid source series could collide in the target.

### USDA state sections: inspected layout and remaining interpretation checks

The same FY2015–FY2026 archive contains regional sheets named `NERO`, `MARO`, `SERO`, `MWRO`, `SWRO`, `MPRO`, and `WRO`. Those are workbook groupings containing state sections, not seven state observations. Carry the state label from its section header down to each monthly record. Exclude regional totals, national totals, annual `Total` rows, and non-state areas from the 50-state facts.

Inspection of all 84 regional sheets confirms A–F hold period, households, persons, benefit cost, cost per household, and cost per person, with matching header meanings. Source section labels identify each state. Do not assume national monthly row numbers 9–20 apply throughout a regional sheet with multiple state sections.

The October 20 snapshot contains 132 months for each selected state and 6,600 distinct state/month combinations, without duplicate or absent baseline keys. All measure cells in those records are numeric; Wyoming August 2022 has negative benefit cost and per-recipient dollar values requiring review. Preserve report-specific footnotes, dates, units, and labels. The recent-summary discrepancy remains unresolved; row presence is not a full measure reconciliation. See [state SNAP evidence](evidence/snap-state-verification.json).

### Optional state GDP

Use [BEA GDP by state](https://www.bea.gov/data/gdp/gdp-state) and [regional tables](https://apps.bea.gov/iTable/?reqid=99&step=1) to select a quarterly real GDP level for each state. Table/line identity, API schema, units, source coverage, and retrieval are pending. The national FRED `GDPC1` schema below is reference material only and cannot establish state GDP coverage.

Inspected on October 19, 2026:

- **FRED:** Official observations and series-metadata API documentation, plus the selected series pages. The JSON schema is documentation-backed; no authenticated API request was made, and the three series' historical row counts have not been verified.
- **USDA:** Downloaded the historical ZIP and recent national summary workbook. Read the `US Summary` sheet in every fiscal-year file from FY2015 through FY2026, including both `.xls` and `.xlsx` formats. Source files were inspected in temporary local storage without alteration.
- **Saved evidence:** [Source hashes, workbook headers, footnotes, and inspection results](evidence/source-schema-inspection.json). The JSON contains schema/profile evidence, not a transformed analytical dataset. Raw downloads are temporary and must be reacquired and retained for ingestion.

## Reference only: national FRED observations schema

`UNRATE`, `PAYEMS`, and optional `GDPC1` use the same [series observations endpoint](https://fred.stlouisfed.org/docs/api/fred/series_observations.html). The following describes JSON with `output_type=1`, native frequency, and `units=lin` (no requested value transformation).
- TODO: what do you mean by series observations endpoint? they all use the same api but with different minor endpoints like /api/fred/unrate and /api/fred/payems?

Clarification: all three use the same path, `/fred/series/observations`; the query parameter changes, for example `series_id=UNRATE` or `series_id=PAYEMS`. There is no separate `/fred/unrate` path. These national series are no longer core inputs to the accepted state model.

### Response envelope

| Source field | JSON type | Meaning |
|---|---|---|
| `realtime_start`, `realtime_end` | String | Dates delimiting the real-time information window; distinct from the economic observation period |
| `observation_start`, `observation_end` | String | Observation-date boundaries |
| `units` | String | Requested transformation code; `lin` means untransformed levels, not the measurement unit such as percent |
| `output_type` | Integer | Output layout selection; this document uses `1` |
| `file_type` | String | `json` |
| `order_by`, `sort_order` | String | Ordering metadata |
| `count` | Integer | Number of matching observations |
| `offset`, `limit` | Integer | Pagination metadata; one page need not contain all matching observations |
| `observations` | Array of objects | The economic observations |

### Each object in `observations`

| Exact source field | Raw JSON type | Interpretation / parsing consideration |
|---|---|---|
| `date` | String | Observation period label in `YYYY-MM-DD` form; parse as a date while retaining frequency |
| `value` | String | Numeric text, even for numeric measurements; `.` can represent a missing value and must not become zero |
| `realtime_start` | String | Real-time start date associated with the observation |
| `realtime_end` | String | Real-time end date associated with the observation |

**`series_id` is a request parameter, not a field inside each observation object.** The ingestion process will need to retain which series was requested. Retrieval timestamp, request parameters, source URL, and file identity are also ingestion metadata we would add, rather than fields supplied on every source observation.

A monthly date such as `2015-01-01` labels January, not a daily measurement on January 1. For quarterly GDP, dates label the quarter's first day: January 1, April 1, July 1, or October 1. Real-time dates describe the information window and must not replace these economic-period labels.

### What `value` means for each selected series

| Series | Native frequency | Meaning of `value` | Measurement unit | Seasonal adjustment |
|---|---|---|---|---|
| [`UNRATE`](https://fred.stlouisfed.org/series/UNRATE) | Monthly | Unemployment rate | Percent; a reported `5.7` means 5.7%, not 570% | Seasonally adjusted |
| [`PAYEMS`](https://fred.stlouisfed.org/series/PAYEMS) | Monthly | Total nonfarm payroll employment level | Thousands; multiply by 1,000 to express the level or its changes in individual jobs | Seasonally adjusted |
| [`GDPC1`](https://fred.stlouisfed.org/series/GDPC1) | Quarterly | Inflation-adjusted GDP level, expressed at an annual rate | Billions of chained 2017 dollars | Seasonally adjusted annual rate |

The expected window sizes are 132 observations per monthly series and 44 quarterly GDP observations. These are targets, not API retrieval results. Payroll jobs are not unique employed people, and unemployment comes from a different survey.

### Companion series metadata

The separate [series metadata endpoint](https://fred.stlouisfed.org/docs/api/fred/series.html) returns a `seriess` array (that spelling is the API field name). Its documented objects include:

| Fields | Raw JSON type | Purpose |
|---|---|---|
| `id`, `title` | String | Series identity and description |
| `frequency`, `frequency_short` | String | Native reporting frequency |
| `units`, `units_short` | String | Actual measurement units; distinct from the observations endpoint's transformation code |
| `seasonal_adjustment`, `seasonal_adjustment_short` | String | Seasonal-adjustment labels |
| `observation_start`, `observation_end` | String | Series coverage dates |
| `realtime_start`, `realtime_end` | String | Real-time information window |
| `last_updated` | String | Series update timestamp, with time-zone offset |
| `popularity` | Integer | FRED popularity score; not an analytical measure for this project |
| `notes` | String, when supplied | Definitions and qualifications worth preserving |

## USDA SNAP: historical fiscal-year workbooks

Source: [SNAP data tables](https://fns-prod.azureedge.us/pd/supplemental-nutrition-assistance-program-snap), historical archive under national/state monthly/annual data. The [inspected archive](https://fns-prod.azureedge.us/sites/default/files/resource-files/snap-zip-fy69tocurrent-9.zip) is a dated source snapshot identified by its SHA-256 hash in the evidence file. Attachment names can change.

### Workbook structure actually observed

| Fiscal years needed | Archive members | Inspected sheet | Header area | Monthly rows | Other rows |
|---|---|---|---|---|---|
| FY2015–FY2019 | `FY15.xls` through `FY19.xls` | `US Summary` | Rows 5–7 | Rows 9–20 | Title, report date, totals, footnotes |
| FY2020–FY2026 | `FY20.xlsx` through `FY26.xlsx` | `US Summary` | Rows 5–7 | Rows 9–20 | Title, report date, totals, footnotes |

All 12 workbooks contain `NERO`, `MARO`, `SERO`, `MWRO`, `SWRO`, `MPRO`, `WRO`, and `US Summary` sheets. The regional sheets contain multiple state sections; this inspection establishes the national sheet schema, not a complete state-level contract. Do not append those regional sections to national totals.

These are formatted reports with multirow headers, not ready-made tables with a single header row. The monthly header meanings match across all 12 files after normalizing empty header cells (`''` in the `.xls` reader and `None` in the `.xlsx` reader).

### Actual national monthly columns

The names in the last column are readable labels for discussion. They are not existing database columns or an approved target schema.

| Excel column | Source header assembled from rows 6–7 | Observed monthly cell type | Meaning and unit | Possible readable label |
|---|---|---|---|---|
| A | `Fiscal Year and Month` | Text | Month/year label, sometimes followed by a footnote marker | `source_period_label` |
| B | `Participation 1/` → `Household` | Numeric for the project window | Participating households, unscaled counts | `snap_households` |
| C | `Participation 1/` → `Persons` | Numeric for the project window | Participating persons, unscaled counts | `snap_persons` |
| D | `Cost` | Numeric for the project window | Monthly benefit cost, unscaled U.S. dollars | `snap_benefit_cost_usd` |
| E | `Cost Per` → `Household` | Numeric for the project window | Dollars per participating household | `snap_benefit_per_household_usd` |
| F | `Cost Per` → `Persons` | Numeric for the project window | Dollars per participating person | `snap_benefit_per_person_usd` |

Participants (C) and benefits (D) are therefore two measures on the **same source row**, not two separate files that need a join. Households and per-recipient amounts are already present if we later choose to retain them. Counts can use integer types after validation; dollar amounts and per-recipient values can use decimal types. Raw Excel numeric storage alone does not define the final Spark types or decimal precision.

One actual FY2015 row illustrates the layout: `A12 = Jan 2015`, `B12 = 22,615,696`, `C12 = 46,028,930`, `D12 = 5,828,983,683`, `E12 = 257.7406`, `F12 = 126.6374`. These are observed source values from this archive snapshot, not invented sample data or independently audited benefit records.

### Metadata and exceptional rows

- `A2`: Report title containing the fiscal year. From FY2020 onward the inspected titles explicitly say `P-EBT/Other Excluded`.
- `F1`: Source report date. Across inspected files it appears as an Excel date or text such as `05/07/2021`. It is not the month of the observations and is not our retrieval timestamp. Different fiscal-year workbooks have different source report dates.
- `A8`: `US Summary`, the section label providing national reporting context; geography is not repeated as a column on every monthly row. Exact comparability of territorial coverage with BLS/BEA remains to be checked before interpreting combined results.
- Row 21: `Total`. For complete fiscal years, B/C are average monthly participation, while D is the annual benefit total. This is not a thirteenth monthly record, and the measures do not share one aggregation rule.
- Rows 23 onward: Footnotes and revision statements. Participation definitions and exclusions change in wording across fiscal years; preserve the source-specific notes.
- Missing periods: FY2026 contains `--` text in B–F for July–September 2026. Those months are outside the project window but demonstrate that the raw source columns can contain text sentinels as well as numbers.
- Footnoted periods: FY2019 contains `Jan 2019 /2` and `Feb 2019 /2`. Extract the month while retaining the original label and footnote association. The note says most February benefits were issued in January because of the partial federal shutdown. Do not interpret these movements as ordinary enrollment or economic changes without the note.

### Window coverage actually checked

Reading FY2015 through FY2026 and selecting calendar months in 2015–2025 found **132 monthly rows and 132 distinct months**, with no missing or duplicate months. All five monthly measure cells B–F were numeric and nonnegative in that window. This verifies period presence and basic cell validity, not full statistical or financial correctness.

## USDA SNAP: recent summary is a different report layout

The separately inspected [recent summary workbook](https://fns-prod.azureedge.us/sites/default/files/resource-files/snap-4fymonthly-9.xlsx) has one sheet, `Sheet1`, and six populated data columns. Its stored worksheet extent includes empty formatted columns beyond F; those are not additional data fields.

| Column | Exact row 3 header | Meaning |
|---|---|---|
| A | `Fiscal Year` | Mixed fiscal-year labels, monthly labels, and section headings |
| B | `Participation Persons` | Persons; note that this is C in the historical workbooks |
| C | `Participation Households` | Households; note that this is B in the historical workbooks |
| D | `Benefit Costs` | Benefit dollars |
| E | `Average Monthly Benefit Per Person` | Dollars per person; different order from the historical sheet |
| F | `Average Monthly Benefit Per Household` | Dollars per household |

Rows 4–8 are the annual summary section; row 9 introduces monthly data; fiscal-year heading rows also occur among the monthly records. Do not treat every nonblank row as a month. This report covers FY2023–FY2026, so it cannot supply the full project history.

**Observed consistency issue:** Across 39 overlapping target-window months (October 2022–December 2025), 36 months differ between the two reports on at least one of persons, households, or benefit costs. For October 2022, the historical `US Summary` sheet has 42,336,750 persons and $10,665,259,184 in benefits; the recent summary has 51,694,100 persons and $13,402,758,874. These are source observations, not corrections to either report.

The historical report title explicitly excludes P-EBT/Other; the recent report's note allows disaster assistance. That alone does not establish the cause of all differences. Keep the archive as the working historical candidate and do not splice in the recent summary automatically. Confirm reporting scope and the desired SNAP definition before accepting a combined analytical dataset.

## Decisions accepted and checks still pending

| Topic | Accepted decision or remaining check |
|---|---|
| Core grain | Accepted: state/month fact and separate state/industry/month fact with shared dimensions |
| Core measures | State unemployment rate, total payroll jobs, SNAP persons/households/benefits; industry payroll jobs in the industry fact |
| Geography | State-level sources replace national core inputs; working scope is 50 states |
| Industry coverage | Manufacturing/retail numeric histories verified for 50 states; construction for 48. All three selected with those scopes on October 24, 2026 |
| USDA definitions and revisions | All state/month keys verified; negative Wyoming benefits and cross-report definition discrepancy remain for review |
| GDP | Optional state/quarter dataset, outside both monthly facts |
| Date dimension | Monthly `dim_date` with `date_key`, `year`, `quarter`, `month_number`, `month_name` |
| Incremental processing | Initial backfill/catch-up, then only a six-month rolling refresh; no automatic older corrections or annual reconciliation; retain replay/change metadata |
| Execution and learning | Monthly on day 1, one orchestrating pipeline with `concurrency=1`, and learner-executed CLI/console/Terraform checkpoints documented in [steps](steps.md) |

The [data model](data-model.md) records accepted grains, dimension relationships, join rules, and aggregation limitations. Actual state-source validation and implementation remain the next checkpoint.
