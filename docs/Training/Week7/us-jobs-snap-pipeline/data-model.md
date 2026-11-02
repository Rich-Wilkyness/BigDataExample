# Data model: state trends and industry jobs

## The decision

Keep two fact tables because the measures describe different things. A fact table contains measurements; a dimension contains the labels used to identify and group those measurements. Grain means what one row represents.

| Fact table | One row represents | Unique combination |
|---|---|---|
| `fact_state_month` | One state during one calendar month | State + month |
| `fact_state_industry_month` | One selected industry in one state during one calendar month | State + industry + month |

Both tables use the same state and date dimensions. `dim_date` has monthly grain: one row per calendar month, not per day. The industry fact also uses an industry dimension. Each fact forms a star with its dimensions; together they are a fact constellation. This is the accepted logical design, not implemented tables or completed homework SQL. The [workflow architecture](architecture.md) records backfill, monthly refresh, revision history, and publication rules.

## Dimensions: how we label the facts

| Table | One row represents | Planned fields |
|---|---|---|
| `dim_state` | One of the 50 U.S. states | `state_key`, two-character `state_fips`, `state_abbreviation`, `state_name` |
| `dim_date` | One calendar month | `date_key` (such as `201501`), `year`, `quarter`, `month_number`, `month_name` |
| `dim_industry` | One selected CES industry category | `industry_key`, `ces_industry_code`, `industry_name`, source classification/level and any documented NAICS mapping |

Keys connect the tables. For example, both facts use the same `state_key` for Idaho and the same `date_key` (`201501`) for January 2015. Source fiscal-year labels remain in Silver/lineage rather than adding columns to the agreed five-field date dimension. Source state codes remain strings so leading zeros survive. CES industry codes are source identifiers; do not assume every code is a standard NAICS code.

Use a fixed, nonoverlapping industry set across the reporting window where coverage allows. [Source verification](source-verification.md) confirms manufacturing and retail trade for all 50 states, and standalone construction for 48. Accepted October 24, 2026: include manufacturing and retail trade for all 50 states and construction for its supported 48 states. Reports requiring all three categories use their common supported 48-state scope; reports requiring only manufacturing/retail may use 50 states. If a classification change alters meaning, resolve the mapping before treating different periods as the same industry.

## Fact table: state and month

| Planned field | Meaning | Source |
|---|---|---|
| `state_key`, `date_key` | References to the state and monthly date dimensions | Validated state/period mapping |
| `total_nonfarm_jobs` | Total payroll job level, normalized to jobs with source precision preserved | State CES total-nonfarm all-employees series |
| `unemployment_rate_pct` | Unemployed residents as a percent of the resident labor force | State LAUS unemployment-rate series |
| `snap_persons` | People participating during the month | USDA state section |
| `snap_households` | Households participating during the month | Same USDA row |
| `snap_benefit_cost_usd` | Benefit cost in U.S. dollars during the month | Same USDA row |

The three core sources must each have at most one accepted record per state/month before combining them. Start from the expected state/month calendar and expose missing source values instead of losing months in an inner join or replacing missing values with zero. Rates and decimal precision will be specified after state samples are inspected.

NULL can represent a missing measurement, but an entirely absent source row requires checking the expected state/month keys first. Preserve source-level coverage/status so NULL does not hide the reason. The accepted approach processes valid available records and retains legitimate partial facts while the default Gold reporting views/visuals show only complete comparable records/months. For an all-state total, all required states must be present; filtering to fewer states must not masquerade as a complete total. Technical failures must not erase already accepted measurements. See [missing-data policy](architecture.md#null-values-and-missing-records-are-different).

For 50 states over 132 months, the target is **6,600 rows**, assuming complete coverage. This is a validation target, not an observed count. The table describes the latest accepted source snapshot; revisions replace the accepted measurement at that key rather than create unexplained duplicate rows. Preserve raw historical snapshots and source lineage separately.

## Fact table: state, industry, and month

| Planned field | Meaning | Source |
|---|---|---|
| `state_key`, `industry_key`, `date_key` | References to the three dimensions | Validated CES series inventory |
| `industry_nonfarm_jobs` | Payroll job level in the selected industry, normalized to jobs with source precision preserved | State CES industry all-employees series |

The accepted historical industry-fact target is **19,536 supported state/industry/month keys**: 13,200 for manufacturing/retail across 50 states plus 6,336 for construction across 48 states. The original 19,800-row estimate assumed three categories in every state and is not supported by the checked source. These are source-supported target counts, not built fact counts. Keep total-nonfarm jobs in the state/month fact, not as another industry to sum alongside its components. A selected subset of industries does not sum to the whole state economy.

## How the facts can be compared

To compare manufacturing jobs and SNAP in Idaho, filter the industry fact to manufacturing and Idaho, then match it with the Idaho state fact using both state and month. Each side then has one row per state/month.

To compare several industries, chart their job trends alongside the state's SNAP context. Do not sum SNAP after repeating it across industries. SNAP data does not identify the industry of participating people.

When aggregating industries first, add job levels only across nonoverlapping selected industries, label that subtotal accurately, and then join the subtotal to the state/month fact. Do not recalculate total state jobs from an incomplete industry subset.

## Rules for totals and changes

- SNAP benefit costs can be summed over months to describe benefits over the period, subject to source footnotes. Participant/household counts and payroll job levels cannot be summed over months and called unique people, households, or jobs; use averages, selected month levels, or changes instead.
- Do not sum or take an unqualified average of state unemployment rates to claim the national rate. A combined rate needs compatible unemployed and labor-force counts, which are not currently selected core measures.
- Job growth is a change between job levels, not the level itself. Preserve original units and seasonal-adjustment metadata in Silver and use one accepted variant in each fact.
- CES describes workplaces; LAUS and SNAP describe residents/participants. Their shared state/month key makes comparison possible but does not make them the same population or prove causation.
- Preserve the FY2019 shutdown/early-issuance note and investigate the USDA report discrepancies before accepting the state data.
- Keep source series ID, report/file identity, source-as-of information, retrieval timestamp, and notes in Silver or linked lineage records. Any fact output must be traceable to its accepted input snapshot.

## Revision tracking

The current facts keep one accepted row per business key. Add `first_loaded_at`, `last_changed_at`, and `revision_count` to distinguish first load from later content changes. Keep source-specific capture/processing lineage and old/new values in linked Silver records and a revision log. Re-reading identical values is not a revision. See [revision metadata and acceptance](architecture.md) for the proposed fields and six-month refresh policy.

### Queryable observed revision history

Keep the two current facts at their accepted unique business keys and persist a separate source-specific change history. Use reporting date_key independently from observed/detected timestamps. The historical claim is first observed by this pipeline, not the publisher's first release; revisions before capture and intermediate publisher revisions between runs are unknown. The six-month refresh scope also limits subsequent observation of older reporting months.

History publication must distinguish initial_observation (including a previously pending source measurement arriving on an existing state/month row), revision of an already observed measurement, and status-only changes. Initial observations and unchanged reruns must not inflate counts of measurement revisions. Retain baseline observations durably so first-observed versus current comparisons include records that have never changed. Revision events need stable IDs, fact/source/business-key identity, refresh-run reference, reporting month, detected time, changed fields, exact old/new values and source-specific old/new lineage. An analytical view can expose measure-level old/new differences and adjustment counts from those events. Publish current facts and their history together with a single-writer guard and idempotent retry handling. Merely returning Python revision dictionaries is not durable history.

The current monthly_merge exercise detects changes but does not yet implement that full history lifecycle: initial-observation/revision/status classification and local replay are now learner-verified, and the BigQuery baseline contains 55,818 unique events. Live idempotent fact/event publication remains pending. Dimension SCD2 is not required for this measurement-history requirement.

## Optional quarterly GDP

If added, state real GDP belongs in a separate state/quarter dataset with its own quarter key. Aggregate monthly facts to state/quarter using the appropriate rule for each measure before comparing them with GDP. Do not copy a national GDP value to every state, repeat quarterly GDP across months, or create monthly GDP values by interpolation for this assignment.

## What still needs verification

- Industry selection is accepted; implementation must enforce the tested 50-state manufacturing/retail and 48-state construction membership. October 2025 unemployment is source-missing in every state; do not invent values.
- USDA Wyoming August 2022 negative dollars and cross-report definition differences. All 50 states' 132 monthly rows have now been inspected, but measure reconciliation is not complete.
- The accepted source snapshot, final physical types, missing-data reporting, dimension mappings, and source-to-output reconciliation.
- Implementation in ADLS/Databricks, Delta tables, and analytical results. No pipeline execution is established by this document.
