# U.S. Jobs and SNAP: presentation requirements and preparation

## Purpose and source of requirements

For slide assembly, use the [slide-by-slide outline](presentation-slide-outline.md) alongside the [speaking script](presentation-script.md). The outline is a starting point for Richard to edit, not an assembled or rehearsed deck.

This checklist consolidates the four instructor requirement sets supplied by Richard on October 31, 2026, and the original notes in this file. It is a preparation document, not a completed slide deck or verification of current cloud operation.

The recurring priority is a working, understandable pipeline that Richard can demonstrate and explain. Start with the high-level purpose, then introduce technical detail. A smaller reliable demonstration is preferable to unnecessary complexity. Explain the work rather than only showing screenshots.

## Deadline, duration, and format

| Item | Requirement |
| --- | --- |
| Due date | November 6, retained from the original notes. Exact submission time, time zone, and delivery method were not supplied. |
| Duration | Minimum 10 minutes; up to 30 minutes. |
| Presentation medium | Live walkthrough, or PowerPoint, Google Slides, or another presentation tool with a smaller demonstration. |
| Demonstration | Show functioning components stable enough to demonstrate, including actual data, queries, transformations, or analytical results. A fresh full-pipeline run is not explicitly required. |
| AI/ML/RAG | Demonstrate how it functions if included. The supplied requirements do not make AI/ML/RAG mandatory. |

The instructor wording mentions Azure and Databricks; the working adaptation discussed in this project uses GCP. Present the services actually used. Confirm any cloud-specific grading requirement rather than assuming an Azure deployment is mandatory or automatically waived.

## Consolidated requirements

Source numbers refer to Richard’s supplied sets: 1 = development priorities; 2 = presentation subjects; 3 = data sources, medallion processing, and demonstration; 4 = presentation order, duration, dashboard, and conditional AI demonstration.

| ID | Requirement | What to explain or demonstrate | Source sets |
| --- | --- | --- | --- |
| R1 | Project overview and objective | The problem, intended user, meaning of the data, and questions the project explores. | 2, 3, 4 |
| R2 | Data sources and scope | Publishers, access methods/formats, measures, units, geography, and reporting periods. | 3, 4 |
| R3 | Architecture overview | A simple diagram of major services, connections, and end-to-end data flow, before individual component details. | 1, 2, 3, 4 |
| R4 | Pipeline and component explanations | How ingestion, transformation, validation, storage, and analytics work; how Bronze/Silver/Gold contribute; how components exchange data correctly. | 1, 2, 3, 4 |
| R5 | Technical decisions | Why the selected technologies fit and what alternatives were considered. | 2, 3 |
| R6 | Testing and troubleshooting | How expected results were checked, problems diagnosed and resolved, and important limitations identified. | 1, 2 |
| R7 | Working demonstration | Actual functioning parts and what their outputs establish. Explain the demonstration rather than just opening screens. | 1, 2, 3, 4 |
| R8 | Dashboard results | Show charts and controls, explain metrics, and interpret results and limitations. | 1, 4 |
| R9 | Challenges, lessons, and conclusion | Concrete challenges and responses, lessons learned, main functionality delivered, and concluding remarks. | 2, 4 |
| R10 | AI/ML/RAG, if included | Its purpose and a functioning demonstration. Conditional, not currently mandatory. | 4 |

Continue refining pipeline development and integration while preparing the presentation. Individual job success does not, by itself, establish end-to-end integration or data correctness.

## Proposed presentation order

This suggested 18-minute structure fits the required 10–30-minute range. Allocations are preparation suggestions, not instructor requirements. Explain technical choices and troubleshooting alongside the components where useful.

| Order | Section | Requirements | Suggested time |
| --- | --- | --- | --- |
| 1 | General introduction, objective, data meaning, and sources | R1, R2 | 2 minutes |
| 2 | High-level architecture and end-to-end flow | R3 | 2 minutes |
| 3 | Individual components, layers, integration, and technology choices | R4, R5 | 4 minutes |
| 4 | Stable working demonstration and selected correctness checks | R6, R7 | 4 minutes |
| 5 | Dashboard results and chart interpretation | R8 | 3 minutes |
| 6 | Challenges and lessons learned | R6, R9 | 2 minutes |
| 7 | Concluding remarks | R9 | 1 minute |

If AI/ML/RAG is deliberately included later, allocate demonstration time explicitly without exceeding the duration. Do not add it merely to fill a conditional requirement.

## Project-specific preparation prompts

These prompts connect the requirements to this project; they are not additional instructor obligations or claims that every check is currently verified.

### Overview, sources, and analytical meaning

- Explain the question: how did employment and SNAP participation change across states during periods of job loss and recovery, and how did selected industries differ?
- Introduce BLS employment/unemployment data and USDA SNAP workbooks as aggregate monthly statistics, not individual worker or recipient records.
- Explain the January 2015–December 2025 baseline, subsequent catch-up, and source-specific publication lags. Check actual latest reporting months before presenting.
- Explain the 50-state core scope and construction’s 48-state availability. Industry comparison reports use a common 48-state scope.
- Distinguish jobs, unemployment rates, participants, households, and benefit dollars. Explain units/conversions; monthly participant counts cannot be summed and described as unique people over time.
- Describe associations without claiming that job growth caused changes in SNAP participation.

### Actual GCP architecture and component responsibilities

- Cloud Scheduler triggers Workflows, which coordinates the execution steps.
- Python ingestion runs in Docker containers through Cloud Run Jobs. Cloud Build builds images; Artifact Registry stores them. Packaging and execution are different responsibilities.
- Cloud Storage Bronze retains original source captures, manifests, hashes, and lineage.
- PySpark on serverless Dataproc batches, displayed as Managed Apache Spark in the learner’s console, performs Silver processing. This project does not use Dataflow for Silver.
- Staging/publishing jobs load and merge BigQuery Gold facts/dimensions and retain measurement history; reporting views feed Data Studio, formerly Looker Studio.
- Distinguish control flow from data flow and show where data persists.
- Explain historical loading versus monthly six-reporting-month refresh, insert/update behavior, revisions, safe reruns, and the limit on automatic older corrections.
- Discuss selected tradeoffs, including Cloud Run Jobs versus source-deployed functions, managed Spark versus local processing, and direct BigQuery reporting views versus copied dashboard extracts.
- Keep the public-data project separate from the hypothetical PayPal/BNPL interview playbook. Bigtable and that playbook’s architecture are not implemented features of this pipeline.

### Testing, demonstration, and troubleshooting

- Choose a stable path: a completed workflow plus a raw capture, Silver output, BigQuery query, and dashboard may show the main functionality without waiting for a fresh full run.
- Trace one example from input through transformation/check to published result, using source IDs and lineage where practical.
- Select a few meaningful checks: business-key uniqueness, row coverage, missing-value handling, revision/idempotency behavior, or comparable report scope. Identify which actually ran.
- Distinguish successful Scheduler dispatch, workflow completion, and correct published output; each proves a different part of the system.
- Recheck saved evidence before presenting; label earlier counts/screenshots with their dates rather than treating them as current automatically.
- Prepare backup screenshots/results for service failures, labeling them as saved evidence rather than a successful live run.
- Select two or three challenges and explain problem → diagnosis → resolution → verification. Candidates include BLS busy responses, cloud IAM/dependency failures, and source exceptions affecting chart scales.
- Avoid displaying secret values during the demonstration.

### Dashboard interpretation and conclusion

- Choose the final jobs/SNAP trends, industry comparisons, growth charts, and scatter/trendline views to demonstrate.
- Explain state/industry/date controls, report geography, and whether each chart shows levels, rates, averages, or sums. Averaging state growth rates is not growth in combined employment.
- Label summed positive/negative monthly YoY rates as percentage-point months, not overall employment growth or jobs added. Results depend on selected dates and states.
- Explain the January–February 2019 SNAP early-issuance exception and its effect on following-year comparisons; disclose intentional date exclusions.
- Explain relevant missing unemployment, different latest BLS/SNAP months, unavailable construction series, and flagged benefits if those measures appear in the demonstration.
- Close with the delivered functionality, main lesson, and remaining work. Do not claim unimplemented capabilities or unmeasured performance/cost results.

## Requirement-by-requirement working checklist

These statuses track presentation preparation, not whether pipeline implementation has succeeded. Complete each checkpoint after its content and evidence are reviewed together.

| Checkpoint | Deliverable | Preparation status |
| --- | --- | --- |
| 1 | Agree objective, intended user, and opening explanation | Introduction approved October 31; script file created |
| 2 | Explain sources, grain, measures, units, reporting dates, and coverage | Source and historical coverage/refresh wording approved November 1; units and report-specific scope to explain in component/dashboard sections |
| 3 | Review a simple diagram of the actual GCP deployment | Simplified GCP architecture diagram reviewed and accepted November 1 |
| 4 | Explain each component and trace Bronze → Silver → Gold | Ingestion, Bronze, Silver, and Gold explanations approved; actual historical layer examples and fact-constellation visual accepted |
| 5 | Select technology decisions and alternatives | Stage-specific comparisons prepared; core runtime choices reviewed; dashboard rationale and view/caching notes added |
| 6 | Select checks, troubleshooting examples, and evidence | Three demo SQL statements and Richard's outlier query prepared; current publication/revision results and duplicate-key evidence still to check; Richard will supply challenge resolutions |
| 7 | Script and rehearse the stable demo and backup path | Walkthrough prepared; November 1 scheduled-run correlation, matching artifacts, backups, and rehearsal pending |
| 8 | Choose visuals and explain their results/limitations | Architecture, layer examples, and data-model visuals accepted; Richard will explain dashboard charts independently; final demo settings/results to check |
| 9 | Draft conclusion and rehearse within the required duration | Conclusion approved; slide assembly and timed rehearsal pending |
| Conditional | Explain and demonstrate AI/ML/RAG if included | Not currently included in this plan |

### Checkpoint 1: objective and accepted introduction

**Problem statement draft:** Employment and food-assistance statistics are published separately, in different formats, and can be revised. This project brings them into a repeatable state-by-month pipeline so users can compare employment, selected industries, and SNAP participation using traceable data and consistent reporting periods.

**Intended-user draft:** A community-services planner or analyst exploring employment and food-assistance trends. This is a potential audience, not a claim of an actual customer.

**Approved introduction:** “My project brings together U.S. employment data from the Bureau of Labor Statistics and SNAP participation data from USDA. I wanted to make it easier to compare how jobs and food-assistance participation changed across states over time. The pipeline preserves the original data, transforms it into consistent monthly datasets, and publishes results to an interactive dashboard.”

Richard approved this introduction on October 31, 2026. The accepted opening and the next sections’ drafts/action cues are in [the presentation script](presentation-script.md). Continue reviewing the source explanation before advancing through the other preparation checkpoints.

## Supporting documents

- [Speaking script and demonstration cues](presentation-script.md)
- [Project objective, sources, and scope](README.md)
- [Data model](data-model.md)
- [Implementation and observed evidence](steps.md)
- [GCP learning plan](gcp-learning-plan.md)
- [GCP resume checkpoint](gcp-resume-checkpoint.md): dated handoff, not proof of today’s state.
- [Functions versus container jobs](gcp-ingestion-functions-vs-jobs.md): background for the packaging/execution decision.
- [Original Azure architecture](architecture.md): instructor-project baseline, not the diagram of the demonstrated GCP deployment.

## Remaining administrative details

- Confirm the exact November 6 submission time, delivery method, and whether Q&A counts toward the duration.
- Confirm any grading requirement tied specifically to Azure versus the working GCP adaptation.
- Choose presentation medium and target rehearsal length after agreeing the outline.
- Add further instructor requirements as supplied; distinguish new obligations from optional improvements.
