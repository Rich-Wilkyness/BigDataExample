# U.S. Jobs and SNAP: slide outline

This is an editable starting point for Richard's PowerPoint or Google Slides deck, not a generated slide file. Use the short on-slide text on the slides and keep the speaking notes off the canvas. The fuller approved explanations and technical Q&A remain in [presentation-script.md](presentation-script.md). Richard owns the dashboard interpretation and challenge-resolution answers.

Suggested format: 14 main slides, approximately 20 minutes including the live demo, before questions. The required range is 10–30 minutes. Rehearse to adjust the allocations; the suggested schedule is not a measured rehearsal. Extra technical comparisons belong in optional appendix slides.

## Slide 1 — U.S. Jobs and SNAP Participation Pipeline

**Time:** 45 seconds.

**What to say:** “My project brings together U.S. employment data from the Bureau of Labor Statistics and SNAP participation data from USDA. I wanted to make it easier to compare how jobs and food-assistance participation changed across states over time.” Explain that an analyst or community-services planner could use these comparisons.


## Slide 2 — Data sources and scope

**Time:** 60 seconds.

**What to say:** The sources publish independently and may have different latest months. Explain that jobs and SNAP participants describe different populations. Construction is available for 48 states in our selected series set; manufacturing and retail trade cover 50. Avoid quoting a latest reporting month until checking the current query results.

## Slide 3 — End-to-end GCP architecture

**Time:** 90 seconds.

**What to say:** Follow the data path once: Cloud Run ingestion → Cloud Storage Bronze → serverless Dataproc/PySpark → Cloud Storage Silver → staging/publication jobs → BigQuery Gold → Looker Studio. Explain that Cloud Scheduler triggers Workflows, which coordinates execution rather than carrying the bulk data.

## Slide 4 — Scheduling and orchestration

**Time:** 60 seconds.

**What to say:** Workflows fits the monthly sequence of cloud jobs without a dedicated Airflow environment between runs. Composer becomes attractive for a broader platform with many related pipelines, scheduling/backfill needs, and useful operators. If using Composer, use its built-in scheduling instead of adding Scheduler for the same purpose. Daily versus hourly execution alone does not decide the choice.

## Slide 5 — Ingestion and immutable Bronze captures

**Time:** 60 seconds.

**What to say:** Jobs fit a bounded capture that runs to completion. Functions could also handle the ingestion through a handler; this is an execution-model choice, not a claim of superior measured performance. Cloud Build and Artifact Registry support image deployment. Explain traceability: identify exactly which captured input produced an output. Checksums validate captured bytes, not the economic correctness of a statistic.

## Slide 6 — Historical loading and the six-month refresh

**Time:** 60 seconds.

**What to say:** Six months is our policy, not a publisher requirement or a guarantee of capturing every revision. The download may contain more than six months: BLS responds for requested years, and USDA provides a historical archive. Processing selects the intended reporting window. Keep the stored history as the window moves forward.

## Slide 7 — Silver transformations and validation

**Time:** 90 seconds.

**What to say:** Use actual Idaho January 2015 examples: `662.6` thousand jobs becomes `662,600` jobs; unemployment `3.9` stays 3.9 percent. SNAP calendar months are extracted from fiscal-year workbooks. Missing values stay NULL; `AVG()` excludes them, while substituting zero would distort an average. Coverage still matters. Published negative benefit amounts remain flagged rather than silently corrected.

Explain the runtime choice briefly: managed Spark without maintaining a cluster between monthly runs. Cloud Run processing or parsing-plus-BigQuery SQL could also fit this small dataset. Source parsing runs in the driver; do not describe all parsing as distributed Spark work.

## Slide 8 — Gold facts and shared dimensions

**Time:** 90 seconds.

**What to say:** Both facts share state and month dimensions; the industry fact also uses the industry dimension. Each fact and its dimensions form a star; together they form a constellation. SNAP remains at state/month grain so it is not repeated and accidentally summed for every industry. BigQuery supports the analytical joins and comparisons needed here.

## Slide 9 — Publication, reruns, and reporting views

**Time:** 60 seconds.

**What to say:** Unchanged input does not create duplicate current facts or fabricated revisions. A committed-run ledger recognizes retries of the same refresh. Explain that tables store data while logical views store reusable SQL, avoiding a separate copied-report refresh step. Views do not inherently make queries faster; eligible results can still be cached. Show current revision results honestly rather than promising a nonzero revision example.

## Slide 10 — How did the workflow go?

**Time:** 3 minutes.

**On the slide:**

1. Look at the executions
2. Check GCS for new folders/files
3. Go through each pre-built BigQuery
4. Check Looker visuals

Buckets:
- We batch because BLS limits each registered API request to 50 series. A series is one measurement over time—for example, Idaho construction employment. Our 248 configured series require five requests: 50 + 50 + 50 + 50 + 48. Batching also lets us identify which request failed and retry it separately
- Checksums help us verify that we’re processing the same files we captured. They check file integrity—not whether the source’s unemployment rate or participant count is correct.

| manifest.json | Details about that capture: request parameters, retrieval time, checksum, and validation results |
| inventory.json | The saved list of series we intended to collect, including their states, measures, industries, and units |
| summary.json | The overall ingestion result: status, completed batches, reporting windows, and links to their manifests |



## Slide 11 — Challenges and lessons learned

**Time:** 2 minutes.

**On the slide:**

| Challenge | Your investigation and response |
|---|---|
| API responses versus fiscal-year spreadsheets | Richard to complete |
| Extreme SNAP growth compressed the chart | Richard to complete |

**What to say:** Explain the source-format and chart-scaling challenges in your own words: what happened, how you investigated, what you changed, and what verified the result. These answers intentionally remain yours to write.

**What to do:** Use the Looker Studio page identified as **U.S. Jobs and SNAP** and, if useful, **04 — Alabama SNAP: Growth Outlier Investigation**. Prepare the relevant chart and period rather than browsing for it during the talk. The previously investigated February 2020 SNAP spike had a very small February 2019 denominator; do not attribute that extreme spike to COVID. COVID-era employment changes are a separate context.

**Visual:** Screenshot of the chart showing the spike and compressed scale. Optional second screenshot shows your chosen presentation treatment, with date exclusions clearly identified. Do not replace the source value just to improve appearance.

## Slide 12 — Conclusion and questions

**Time:** 45 seconds.

