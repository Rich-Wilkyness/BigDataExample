# State and industry source verification

## What was checked

On October 20, 2026, public-source inspection checked the proposed 50-state scope against the January 2015–December 2025 baseline. This is source verification, not execution of the Azure ingestion pipeline or completion of Silver/Gold transformations. The learner does not need to manually repeat every check; the findings and evidence below support the next learning checkpoint.

| Data | Checked scope | Observed result |
|---|---|---|
| CES total nonfarm jobs, seasonally adjusted | 50 states × 132 months | All 6,600 values numeric, with no missing or duplicate target months |
| CES manufacturing jobs, seasonally adjusted | 50 states × 132 months | All 6,600 values numeric, with no missing or duplicate target months |
| CES retail-trade jobs, seasonally adjusted | 50 states × 132 months | All 6,600 values numeric, with no missing or duplicate target months |
| CES construction jobs, seasonally adjusted | Requested 50 states × 132 months | 48 states supported, with 6,336 numeric observations; separate construction series unavailable for Delaware and Hawaii |
| LAUS unemployment rate, seasonally adjusted | 50 states × 132 months | All 6,600 period rows present; 6,550 numeric values plus 50 missing-value markers for October 2025 |
| USDA SNAP state records | 12 fiscal-year files, 84 regional sheets | All 6,600 distinct state/month records present, no missing/duplicate target keys; one state/month has negative dollar measures requiring review |

All returned BLS series with observations reached September 2026 in the responses inspected. The USDA landing page listed July 2026 as its latest month on October 20. These are separate source freshness observations, not proof of accepted 2026 state coverage in our pipeline. The row checks above apply to the 2015–2025 baseline.

## BLS access, units, and series identities

The [BLS public API](https://www.bls.gov/developers/api_signature_v2.htm) was queried in 20 unregistered POST requests, each with 25 series and either 2015–2024 or 2025–2026. A separate initial Idaho manufacturing GET checked access. No API key was used or searched for. For this verification, the 11-year baseline was split into allowed shorter requests; a registered BLS key remains useful for the planned application and its higher limits. See [API limits](https://www.bls.gov/developers/api_faqs.htm).

Direct command-line bulk-file downloads returned HTTP 403 even outside the sandbox; the API succeeded. This establishes a working public API route for source inspection, not that every future deployed Function will have identical network access. The BLS series catalog and publication pages were also consulted. Exact tested IDs and request/response hashes are saved in [BLS verification evidence](evidence/state-series-verification.json).

| Measure | Idaho example ID, verified through API | Interpretation |
|---|---|---|
| Total nonfarm jobs | `SMS16000000000000001` | CES all employees, thousands, seasonally adjusted |
| Manufacturing jobs | `SMS16000003000000001` | CES industry `30000000`, thousands, seasonally adjusted |
| Retail-trade jobs | `SMS16000004200000001` | CES industry `42000000`, thousands, seasonally adjusted |
| Construction jobs | `SMS16000002000000001` | CES industry `20000000`, thousands, seasonally adjusted |
| Unemployment rate | `LASST160000000000003` | LAUS unemployment rate, percent, seasonally adjusted |

The full evidence includes state FIPS/name, series ID, industry where applicable, units, adjustment, observed months, missing markers, and sample first/last observations. It is a tested candidate inventory, not a configured ingestion job. CES measurement type `01` means all employees in thousands; see [BLS data types](https://download.bls.gov/pub/time.series/sm/sm.data_type) and [Idaho publication structure](https://www.bls.gov/sae/additional-resources/list-of-published-state-and-metropolitan-area-series/idaho.htm).

For example, a payroll level of `75.5` means approximately 75,500 jobs, whereas an unemployment value of `3.5` means 3.5 percent. Preserve the source unit and convert intentionally before joining or charting.

## Industry decision: construction exceptions

The API reports no series for `SMS10000002000000001` (Delaware) and `SMS15000002000000001` (Hawaii). Their publication pages instead list the broader **Mining, Logging and Construction** category. Do not substitute that category while labeling it construction; it has a different definition. See [Delaware](https://www.bls.gov/sae/additional-resources/list-of-published-state-and-metropolitan-area-series/delaware.htm) and [Hawaii](https://www.bls.gov/sae/additional-resources/list-of-published-state-and-metropolitan-area-series/hawaii.htm).

Two options are available for the learner's scope decision:

- Use manufacturing and retail trade consistently across all 50 states: 13,200 expected historical industry-fact records.
- Keep those two categories plus construction where supported: 19,536 expected records, with construction explicitly limited to 48 states. Do not create zero construction values for the other two states or claim an all-50-state construction total.

Decision accepted October 24, 2026: use manufacturing and retail trade across all 50 states, plus construction across its supported 48 states (19,536 supported historical industry keys). The dated verification evidence preserves all 250 candidate series unchanged, including the two unsupported construction candidates. Operational BLS inventory should therefore contain 248 supported series: 50 total nonfarm, 50 unemployment, 50 manufacturing, 50 retail, and 48 construction. This is a scope/inventory count, not a freshly executed historical backload.

## Source-missing unemployment values

Every checked state unemployment series contains October 2025 with `value="-"`. This is a missing-value marker, not a negative unemployment rate, zero, or absent JSON row. There are 131 numeric baseline months per state for this measure.

BLS documents that household survey data were not collected for October 2025 during the federal shutdown and were not collected retroactively. See the [BLS state employment release](https://www.bls.gov/news.release/archives/laus_01072026.htm). Preserve a source-gap reason and NULL measurement; do not fill the value or repeatedly retry expecting a normal publication delay.

A report requiring unemployment excludes that month under our complete-only reporting policy. A jobs-versus-SNAP report does not automatically exclude it if all of its own required measures are valid and present. Completeness depends on what the report uses, not every column anywhere in the project.

## USDA state workbook verification

Downloaded the archive currently linked from the [USDA SNAP tables](https://fns-prod.azureedge.us/pd/supplemental-nutrition-assistance-program-snap), [archive attachment inspected](https://fns-prod.azureedge.us/sites/default/files/resource-files/snap-zip-fy69tocurrent-10.zip). Its name differs from the earlier October 19 snapshot; keep the prior national evidence separately. Current archive/member hashes, sheet headers, state-section locations, report dates, footnotes, and per-state coverage are saved in [SNAP state evidence](evidence/snap-state-verification.json).

Read FY2015–FY2019 `.xls` members and FY2020–FY2026 `.xlsx` members. Each fiscal-year file has seven regional sheets containing multiple state sections. All 84 regional sheets have matching header meanings after normalizing blank cells:

| Column | Verified role |
|---|---|
| A | Source reporting month, sometimes with a footnote marker |
| B | Participating households, unscaled counts |
| C | Participating persons, unscaled counts |
| D | Benefit cost, unscaled U.S. dollars |
| E | Dollars per household |
| F | Dollars per person |

State identity comes from the section label above the monthly rows. Annual totals, regional/national totals, DC, territories, and other non-state sections were excluded from the 50-state coverage check. A missing-value marker must not become zero, and monthly row numbers differ by state section. The repeated national-row offsets from earlier notes are not a regional-sheet parsing rule.

### Wyoming benefit-cost review flag

In `FY22.xlsx`, sheet `MPRO`, row 124 (`Aug 2022`, Wyoming), the source reports households `13,718`, persons `28,615`, benefit cost **-$1,250,130**, cost per household `-91.1306`, and cost per person `-43.6879`.

These three negative cells belong to one state/month record. They are numeric source values, not proven extraction errors. The inspection did not establish whether they represent an accounting adjustment or a publication error. Preserve the raw values and flag them for review; do not change the sign, replace them with zero, or claim the entire SNAP dataset is clean. Dollar-dependent reporting needs a documented handling decision before including this observation. Participant-only comparisons can be evaluated independently, since their required count values are present and nonnegative.

The earlier discrepancy between USDA's recent national summary and historical national sheets remains a separate reporting-definition issue. This verification uses one historical archive's state sections consistently and does not splice in recent-summary values. Exact cross-report reconciliation and official explanation of the Wyoming amount remain pending.

## Learner checkpoint

You do not need to inspect 250 series manually. The useful learning check is to explain why: (a) 132 rows do not guarantee 132 usable values; (b) the two unsupported construction series cannot be replaced with zero; and (c) a negative published amount needs review before calling it an error.

Industry scope is now selected. Next review source exceptions and build the operational BLS inventory; the separate GCP steps record guides local historical expansion, while Azure prerequisites remain separate. Actual Azure deployment, Databricks access, acceptance logic, physical types, and analytical results are still pending. The confirmed destination remains Azure Databricks Gold Delta tables with SQL queries; no separate warehouse is added.
