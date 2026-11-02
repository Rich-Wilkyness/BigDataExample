# BigQuery presentation queries

**Learner update — November 1, 2026:** Richard reports that he checked the November 1 run and executed all four queries (the three main queries and his Alabama outlier query). Their complete current results were not supplied here. The Idaho output and saved-source follow-up established the October 2025 unemployment source gap. Richard subsequently ran query 5 and reported all zeros, establishing no duplicate business-key groups, extra duplicate rows, or NULL-key rows in either fact table at the time of that check. This is learner-reported BigQuery execution evidence, not an agent-executed cloud query.

Run these three read-only GoogleSQL statements separately in the BigQuery editor, using processing location `us-central1`. They use the current Gold schema and event types checked in the saved publication/merge code. They have not been executed against BigQuery as part of preparing this document; inspect actual results before using them as presentation evidence. Query processing can incur normal BigQuery charges; retain the project's query-byte limit.

## 1. Show the latest comparable jobs and SNAP records for Idaho

This selects the latest 12 available state/month records for which jobs and SNAP persons are both marked available. It does not assume that all other measures are present or that these 12 records are consecutive months. Unemployment may remain NULL. The dimension joins add labels without copying those labels into the fact.

```sql
SELECT
  s.state_name,
  f.date_key,
  d.month_name,
  f.total_nonfarm_jobs,
  f.unemployment_rate_pct,
  f.snap_persons,
  f.snap_households,
  f.jobs_status,
  f.snap_persons_status
FROM `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.fact_state_month` AS f
JOIN `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.dim_state` AS s
  ON f.state_key = s.state_key
JOIN `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.dim_date` AS d
  ON f.date_key = d.date_key
WHERE s.state_name = 'Idaho'
  AND f.jobs_status = 'available'
  AND f.snap_persons_status = 'available'
ORDER BY f.date_key DESC
LIMIT 12;
```

**What to say:** “These are current accepted measurements at one row per state/month. The reporting month comes from the data, not the date the pipeline ran.”

## 2. Show Idaho industry jobs and same-month year-over-year changes

This selects Idaho's latest available industry reporting month, then matches each industry to the exact same month one year earlier. Subtracting 100 from a `YYYYMM` key moves to the same month in the preceding year; it is not a general month-arithmetic operation. The prior-year join includes both state and industry keys. The percent column is multiplied by 100 for readable SQL output.

```sql
WITH industry_data AS (
  SELECT *
  FROM `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.fact_state_industry_month`
  WHERE state_key = '16'
    AND jobs_status = 'available'
)
SELECT
  s.state_name,
  i.industry_name,
  c.date_key,
  c.industry_nonfarm_jobs AS current_jobs,
  p.industry_nonfarm_jobs AS prior_year_jobs,
  c.industry_nonfarm_jobs - p.industry_nonfarm_jobs AS jobs_change,
  ROUND(
    100 * SAFE_DIVIDE(
      c.industry_nonfarm_jobs - p.industry_nonfarm_jobs,
      p.industry_nonfarm_jobs
    ),
    2
  ) AS yoy_change_pct
FROM industry_data AS c
LEFT JOIN industry_data AS p
  ON c.state_key = p.state_key
  AND c.industry_key = p.industry_key
  AND p.date_key = c.date_key - 100
JOIN `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.dim_state` AS s
  ON c.state_key = s.state_key
JOIN `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.dim_industry` AS i
  ON c.industry_key = i.industry_key
WHERE c.date_key = (SELECT MAX(date_key) FROM industry_data)
ORDER BY i.industry_name;
```

**What to say:** “This fact has a different grain: state, industry, and month. We compare the same industry and calendar month across years. For this query, `2.5` means 2.5 percent, not a fraction to format again as percent.”

The latest-month filter does not force every industry to have data; inspect that all three Idaho industries appear. NULL prior-year values or a zero denominator produce a NULL growth rate rather than a fabricated zero.

## 3. Check recent committed publications and actual revision events

This shows the latest 10 committed refreshes, their saved fact counts, and history event types associated with each refresh. The join uses `refresh_run_id`. It preserves committed runs with zero history events. It does not list failed or still-running executions, which have no committed publication record.

```sql
SELECT
  p.published_at,
  p.refresh_run_id,
  p.state_rows,
  p.industry_rows,
  p.history_events AS recorded_history_events,
  COUNT(h.event_id) AS matched_history_events,
  COUNTIF(h.event_type = 'initial_observation') AS initial_observations,
  COUNTIF(h.event_type = 'revision') AS revisions,
  COUNTIF(h.event_type = 'status_change') AS status_changes,
  MAX(IF(h.event_type = 'revision', h.detected_at, NULL))
    AS latest_revision_detected_at
FROM `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.refresh_publications` AS p
LEFT JOIN `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.fact_measure_history` AS h
  ON p.refresh_run_id = h.refresh_run_id
GROUP BY
  p.published_at,
  p.refresh_run_id,
  p.state_rows,
  p.industry_rows,
  p.history_events
ORDER BY p.published_at DESC
LIMIT 10;
```

**How to read the revision result:** `revision` means an already observed measurement changed. `initial_observation` means a measurement was first received; `status_change` is distinct from a value revision. Do not count every history event as a revision. A zero revision count is valid if the refreshed inputs did not change. A NULL latest-revision timestamp means there were no revision events for that run.

Compare `recorded_history_events` with `matched_history_events` for each publication; they should agree. Their equality is a focused ledger/history consistency check, not proof of all publication invariants or duplicate-free facts. Fact counts record the counts at that publication, not necessarily the current counts after later runs. Zero revisions alone does not establish that nothing changed: inspect initial observations and status changes as well. For the November 1 demonstration, correlate the returned run ID and timestamp with the scheduled invocation and workflow execution; a date alone does not establish scheduler provenance. Investigate any mismatch instead of presenting it as a pass.

The initial historical measurement-history baseline can have a different run identifier and therefore does not have to appear in these recent publication rows. This query checks the listed committed runs, not an all-time revision total. To inspect actual old/new revision details, use the run IDs returned here as the next read-only investigation checkpoint if revisions are nonzero.

## Optional challenge query: investigate Alabama SNAP growth outliers

Richard supplied this query for the chart-scaling challenge. It complements the three main demo queries and is preserved as supplied. Run with the project selected in BigQuery; the dataset reference uses that default project.

```sql
SELECT
    date_key,
    snap_persons,
    prior_year_snap_persons,
    snap_persons_change,
    snap_yoy_growth_rate,
    jobs_yoy_growth_rate
FROM `jobs_snap_gold.v_jobs_snap_growth`
WHERE state_name = 'Alabama'
    AND snap_yoy_growth_rate IS NOT NULL
ORDER BY ABS(snap_yoy_growth_rate) DESC
LIMIT 10;
```

Sorting by absolute growth places the largest positive or negative percentage changes first. The current and prior-year participant counts help distinguish a large current measurement from a small prior-year denominator. `snap_yoy_growth_rate` and `jobs_yoy_growth_rate` are fractions: `0.10` represents 10%, while `178.518` represents approximately 17,851.8%. Ranking by percentage change is different from ranking by the largest change in participant counts.

Use the returned date to locate the point in the Looker Studio chart, then explain your investigation and chosen presentation treatment. This query identifies candidates to investigate; it does not establish that a value is erroneous, that COVID caused it, or that the pipeline revised it. Measurement revisions are checked separately in query 3. Richard's explanation of resolution remains his own preparation task.

## 5. Validate fact-key uniqueness

Suggested BigQuery tab title: **05 — Fact Key Validation**. This checks the complete current facts, rather than only the sample rows selected for the demo. It checks duplicate business keys and NULL key fields. Expected result: two rows with zeros in all three check columns. Richard reported all zeros on November 1, 2026; the focused check passed from learner-supplied evidence.

```sql
WITH state_keys AS (
  SELECT state_key, date_key, COUNT(*) AS row_count
  FROM `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.fact_state_month`
  GROUP BY state_key, date_key
),
industry_keys AS (
  SELECT state_key, industry_key, date_key, COUNT(*) AS row_count
  FROM `project-4b0f63f3-e441-4289-b42.jobs_snap_gold.fact_state_industry_month`
  GROUP BY state_key, industry_key, date_key
)
SELECT
  'fact_state_month' AS table_name,
  COUNTIF(row_count > 1) AS duplicate_key_groups,
  COALESCE(SUM(row_count - 1), 0) AS extra_duplicate_rows,
  COALESCE(SUM(IF(
    state_key IS NULL OR date_key IS NULL, row_count, 0
  )), 0) AS rows_with_null_keys
FROM state_keys
UNION ALL
SELECT
  'fact_state_industry_month',
  COUNTIF(row_count > 1),
  COALESCE(SUM(row_count - 1), 0),
  COALESCE(SUM(IF(
    state_key IS NULL OR industry_key IS NULL OR date_key IS NULL,
    row_count, 0
  )), 0)
FROM industry_keys
ORDER BY table_name;
```

`duplicate_key_groups` counts keys that occur more than once; `extra_duplicate_rows` counts the rows beyond the one allowed for each key. `rows_with_null_keys` checks required identifiers, not missing measurements such as the legitimate NULL unemployment rate. Zeros establish key uniqueness and absence of NULL keys for the current tables; they do not establish expected row coverage, dimension relationships, numerical correctness, or successful history deduplication. An empty table also produces zeros, so interpret this together with the populated sample queries and publication counts.
