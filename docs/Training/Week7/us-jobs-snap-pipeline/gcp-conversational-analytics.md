# Conversational analytics over BigQuery

## Purpose and current status

Optional extension, started by Richard on November 2, 2026: ask natural-language questions over existing Gold reporting views through BigQuery conversational analytics. This uses Google's managed data-agent feature rather than a custom RAG application or a newly trained model. It is separate from the monthly ingestion/publication workflow.

Richard performed the console setup and supplied screenshots and three responses. The three narrow tests below passed against previously supplied SQL results and reviewed arithmetic; publication, sharing, broad answer accuracy, conversation logging, and a Looker Studio chat integration are not established. Saving verified query examples is the next checkpoint.

## Setup checkpoint

**Prerequisites:** Existing BigQuery Gold views and a user with the required API/data permissions. Use the current project `project-4b0f63f3-e441-4289-b42`. Billing and query execution charges remain applicable; no new billing upgrade or paid subscription was performed by the assistant.

**Console path:** BigQuery → Agents → Agent catalog → create data agent. Richard enabled the Data Analytics API with Gemini and Gemini for Google Cloud API through the console, then opened the agent editor.

**Configuration supplied:** Name `U.S. Jobs and SNAP Explorer`; knowledge sources `jobs_snap_gold.v_jobs_snap_growth` and `jobs_snap_gold.v_industry_month_growth`. Instructions define each source grain, units, percentage fractions, missing-value handling, reporting periods, scope limitations, and the prohibition against repeating state-level SNAP across industry rows. They request read-only queries and SQL visibility; instructions are guidance rather than an IAM authorization boundary.

**Model/settings:** Screenshot confirms GA-only model selection, conversation logging off, and Google-managed encryption. The instructed maximum bytes billed is numeric `104857600` (100 MiB per query). Richard initially included explanatory text in that field, producing a numeric validation error; guidance was to enter digits only. The subsequent successful response demonstrates an operational preview, but a saved numeric-setting screenshot has not been supplied. A per-query byte limit does not cap total agent/model spending across repeated requests.

**Expected observation:** Agent saves and answers a narrow question using the selected view, with results and SQL available for review. Previewing does not establish that the agent has been published.

## Test 1 — Idaho construction, January 2025

**Question:** “For Idaho construction in January 2025, show current jobs, prior-year jobs, the numerical change, and the year-over-year percentage change. Show the SQL used.”

**Learner-supplied response:**

| State | Industry | Month | Current jobs | Prior-year jobs | Change | YoY percent |
|---|---|---|---|---|---|---|
| Idaho | Construction | 2025-01-01 | 73600 | 69700 | 3900 | 5.6 |

**SQL returned by the agent, preserved as supplied:**

```sql
SELECT
  state_name,
  industry_name,
  reporting_month,
  current_jobs,
  prior_year_jobs,
  jobs_change,
  ROUND(yoy_growth_rate * 100, 2) AS yoy_growth_percentage
FROM
  `project-4b0f63f3-e441-4289-b42`.`jobs_snap_gold`.`v_industry_month_growth`
WHERE
  LOWER(state_name) = 'idaho'
  AND LOWER(industry_name) LIKE '%construction%'
  AND reporting_month = '2025-01-01'
```

**Review:** Correct selected view, state, industry, and month; no cross-grain join. Arithmetic agrees: 73600 − 69700 = 3900, and 3900 / 69700 × 100 ≈ 5.5954%, rounded to 5.60%. Values match Richard's earlier supplied Idaho construction comparison. The month string is implicitly coerced by BigQuery; a verified example could use `DATE '2025-01-01'` explicitly. The single returned construction category is appropriate here; exact equality is clearer than substring matching when storing a fixed verified example.

**Evidence boundary:** This is a passed narrow test based on Richard's returned answer/SQL and prior comparison results, with arithmetic reviewed locally by reasoning. The assistant did not execute the cloud query. One passing response does not establish accuracy for other states, dates, aggregates, or joins. No verified-query entry has yet been demonstrated saved.

## Test 2 — source anomaly and denominator interpretation

Ask: “For Alabama in February 2020, show SNAP participants, prior-year SNAP participants, the numerical change, and the year-over-year percentage change. Explain how the prior-year value affects the percentage. Show the SQL used.”

**Learner-supplied result:** Alabama, `2020-02-01`: 704788 SNAP participants; 3926 prior-year participants; +700862 persons; +17851.81%. Returned SQL reads only `v_jobs_snap_growth`, filters Alabama and the exact reporting month, and rounds `snap_yoy_growth_rate * 100` to two decimal places.

**Review:** Matches Richard's earlier outlier-query results. Arithmetic agrees: `(704788 − 3926) / 3926 × 100 ≈ 17851.80846%`. The response correctly explains amplification from the small prior-year denominator, does not replace the source value, and does not claim COVID caused it. Core numerical and denominator interpretation test passed from learner-supplied evidence on November 2, 2026. The additional phrase “typical statewide baseline (~700k participants)” is not established by the single-row SQL shown; substantiate it using broader-period data or omit it. This is not a verified explanation of why the source published 3926.

## Test 3 — latest comparable reporting month

Ask: “What is the latest reporting month available for both total nonfarm jobs and SNAP participation in Idaho? Show that month, the job count, the SNAP participant count, and the SQL used.”

**Learner-supplied result:** Idaho, July 2026 (`2026-07-01`), 887900 total nonfarm jobs, and 119890 SNAP participants. Returned SQL reads only `v_jobs_snap_growth`, filters Idaho and non-NULL jobs/participants, orders `reporting_month DESC`, and limits the result to one row.

**Review:** Correctly selects a common available reporting month rather than today's calendar month or the latest jobs-only month. The values match Richard's earlier **01 — Idaho Jobs and SNAP: Latest 12 Months** output. Passed from learner-supplied result/SQL evidence on November 2, 2026. The check is for jobs and SNAP persons, not completeness of every other measurement or every state.

## Next checkpoint — save verified examples and decide on publication

In the editor's **Verified queries** section, select **Add query** and review the required fields. Add the three tested question/SQL pairs, then save and retest before deciding whether to publish or include the optional AI demonstration in the slides. Verified examples improve guidance but do not guarantee that other responses are correct. Keep the existing non-AI demo as a fallback. No verified examples have been demonstrated saved yet.

## References

- [Enable the APIs](https://docs.cloud.google.com/gemini/data-agents/conversational-analytics-api/enable-the-api)
- [Create and configure data agents](https://docs.cloud.google.com/bigquery/docs/create-data-agents)
- [BigQuery conversational analytics overview](https://docs.cloud.google.com/bigquery/docs/conversational-analytics)

Official instructions were reviewed November 2, 2026 during the walkthrough. Console labels and model availability can change.
