# Presentation data examples

These examples were read from saved local project artifacts on November 1, 2026. They show Idaho in January 2015 from the October 25 historical snapshot. They are not a fresh BigQuery query or evidence of the November 1 scheduled execution. Selected fields and decimal display are simplified for readability; source files remain unchanged.

## Slide visuals

- [Simplified fact constellation — PNG](presentation-assets/gold-fact-constellation-simple.png) · [editable SVG](presentation-assets/gold-fact-constellation-simple.svg): a plain-language alternative created November 2, 2026. It preserves both fact grains and the correct shared dimensions, with actual saved Idaho January 2015 example values. The detailed schema image remains available below.

- [Bronze-to-Silver before/after — PNG](presentation-assets/bronze-to-silver-transformations.png) · [editable SVG](presentation-assets/bronze-to-silver-transformations.svg): a simplified alternative for nontechnical viewers, created November 2, 2026. Employment conversion and month alignment use January 2015; the missing-unemployment example uses October 2025. All examples concern Idaho. “January 2015” is the reader-friendly month label; the actual shared Silver key is `201501`.

- [Bronze, Silver, and Gold examples — PNG](presentation-assets/bronze-silver-gold-examples.png) · [editable SVG](presentation-assets/bronze-silver-gold-examples.svg)
- [Gold fact constellation — PNG](presentation-assets/gold-fact-constellation.png) · [editable SVG](presentation-assets/gold-fact-constellation.svg)

## Bronze: retained JSON and workbook rows

Bronze is not a newly modeled table. The table below presents selected fields from the retained BLS JSON response. Labels are supplied from the series inventory for explanation.

| Series ID | Meaning | year | period | Raw value string | Source units |
|---|---|---|---|---|---|
| SMS16000000000000001 | Idaho total nonfarm jobs | 2015 | M01 | `"662.6"` | Thousands of jobs |
| SMS16000002000000001 | Idaho construction jobs | 2015 | M01 | `"37.5"` | Thousands of jobs |
| LASST160000000000003 | Idaho unemployment rate | 2015 | M01 | `"3.9"` | Percent |

The USDA archive's `FY15.xls`, sheet `WRO`, row 89 contains the following values in the Idaho section. This fiscal-year workbook contains January 2015 as a calendar reporting month.

| Source month label | Households | Persons | Benefit cost USD |
|---|---|---|---|
| Jan 2015 | 85070.0 | 199944.0 | 23069123.0 |

## Silver: typed and standardized records

Selected `bls_observations` fields:

| state_fips | date_key | measure | industry_code | source_value | value | value_units | value_status |
|---|---|---|---|---|---|---|---|
| `16` | 201501 | all_employees | `00000000` | `662.6` | 662600 | jobs | available |
| `16` | 201501 | all_employees | `20000000` | `37.5` | 37500 | jobs | available |
| `16` | 201501 | unemployment_rate | NULL | `3.9` | 3.9 | percent | available |

Selected `snap_state_month` fields:

| state_fips | date_key | snap_persons | snap_households | snap_benefit_cost_usd | persons_status | benefit_review_required |
|---|---|---|---|---|---|---|
| `16` | 201501 | 199944 | 85070 | 23069123.00 | available | false |

The saved schemas also retain raw values, source statuses, footnotes, source file/sheet/row where applicable, manifests, checksums, and capture timestamps. The visual's shorter measure names are display labels, not renamed schema fields.

## Gold: facts at two different grains

Selected `fact_state_month` fields, one row per state/month:

| state_key | date_key | total_nonfarm_jobs | unemployment_rate_pct | snap_persons | snap_households | snap_benefit_cost_usd |
|---|---|---|---|---|---|---|
| `16` | 201501 | 662600 | 3.9 | 199944 | 85070 | 23069123.00 |

Selected `fact_state_industry_month` fields, one row per state/industry/month:

| state_key | industry_key | date_key | industry_nonfarm_jobs |
|---|---|---|---|
| `16` | `20000000` | 201501 | 37500 |
| `16` | `30000000` | 201501 | 62100 |
| `16` | `42000000` | 201501 | 81300 |

Both facts also carry statuses, lineage, and revision metadata. `revision_count` is zero for these saved initial-load examples. These three industries are a selected subset and do not sum to total nonfarm employment.

## Shared dimensions

| dim_state.state_key | state_fips | state_abbreviation | state_name |
|---|---|---|---|
| `16` | `16` | ID | Idaho |

| dim_date.date_key | year | quarter | month_number | month_name |
|---|---|---|---|---|
| 201501 | 2015 | 1 | 1 | January |

| dim_industry.industry_key | ces_industry_code | industry_name |
|---|---|---|
| `20000000` | `20000000` | Construction |
| `30000000` | `30000000` | Manufacturing |
| `42000000` | `42000000` | Retail trade |

Each fact and its dimensions form a star. Together they are a fact constellation because they share `dim_state` and `dim_date`. The industry dimension connects only to the industry fact. The diagram shows logical one-to-many relationships, not evidence that foreign-key constraints are declared or enforced. State keys and industry codes are strings; the monthly date key is an integer. SNAP stays in the state/month fact so an industry join does not accidentally multiply participant totals.

`dim_date` has exactly five business fields, shown above, with one row per month. Historical Parquet reads can expose ingestion-date/run-ID path-partition metadata; these are not extra monthly date-dimension business fields. The visual intentionally omits technical metadata and separate history/control/publication tables to focus on the analytical stars.

## Provenance and checks

The simplified visual's October 2025 example uses the saved BLS record `LASST160000000000003`, year `2025`, period `M10`, whose source value is `"-"` and whose footnote explains unavailability during the 2025 lapse in appropriations. The Silver parser retains it as NULL with `value_status = 'source_missing'`. Its matching Gold field is `unemployment_status`, as explained in the speaking script. This example is a different month from the January 2015 table excerpts below the visual links.

- BLS Bronze: [saved JSON response](data/bronze/bls/ingestion_date=2026-10-25/run_id=7882c36124674a5cbe44f04a8b32c715/batch_id=002/attempt_id=001/response.json).
- SNAP Bronze: [saved archive](data/bronze/snap/ingestion_date=2026-10-25/run_id=a4a640c086d74c21b472f08f84306277/attempt_id=001/archive.zip), `FY15.xls` → `WRO` → row 89 (one-based).
- Silver: [historical run summary](data/silver/ingestion_date=2026-10-25/run_id=7282829984ac46e1912d2edc0622daf0/summary.json) and the matching `bls_observations` and `snap_state_month` Parquet directories.
- Gold: [historical run summary](data/gold/ingestion_date=2026-10-25/run_id=9b11e5713cbe4ba6abc45d7cdd2b622e/summary.json) and its dimension/fact Parquet directories.

Read-only inspection confirmed the selected BLS source values, the original USDA workbook row, and matching Silver/Gold values. PNGs were visually inspected for fit and readability. This inspection did not execute ingestion, transformation, publication, or any cloud query.
