# U.S. Jobs and SNAP Participation Pipeline

## Business problem

Community-services planners need to understand how state employment conditions and food-assistance participation change over time. This project will combine monthly employment and Supplemental Nutrition Assistance Program (SNAP) data to answer two questions: **How do changes in state payroll employment compare with changes in SNAP participation?** And **which selected industries gained or lost the most jobs in each state?** The analysis will describe relationships, without claiming that employment changes caused changes in SNAP participation.

## Data sources and scope

The historical baseline is January 2015–December 2025, targeting the 50 U.S. states. [BLS LAUS](https://www.bls.gov/lau/data.htm) will provide state unemployment rates, and [BLS CES State and Area](https://www.bls.gov/sae/data/) will provide total and selected-industry payroll employment through the BLS JSON API. [USDA SNAP historical workbooks](https://fns-prod.azureedge.us/pd/supplemental-nutrition-assistance-program-snap) will provide state participants, households, and benefit costs as Excel files in a ZIP archive. Source checks confirm manufacturing/retail for all states; construction is supported for 48. Final industry scope and documented source exceptions remain under review.

## Planned architecture

**Sources → Azure Functions → ADLS Gen2 Bronze → Azure Databricks/PySpark Silver → Gold Delta tables → Spark SQL results and charts.** Azure Data Factory will orchestrate the stages. Bronze will preserve raw captures by source, ingestion date, run, and attempt. Initial loading will establish the baseline and catch up to available data; subsequent runs will execute monthly on day 1 and process only each source's latest six reporting months. Request retries, one concurrent pipeline run, revision metadata, and replayable inputs will support reliable operation.

## Transformations and data quality

- Normalize fiscal-year/month labels into calendar months and cast values to explicit numeric/date types, identifying failed conversions.
- Standardize state/industry identifiers and measurement units before combining sources.
- Detect absent reporting periods, NULL values, invalid measurements, and duplicate business keys. Retain legitimate partial data with availability status; distinguish revised source values from duplicate records.
- Build a fact constellation with shared `dim_state` and monthly `dim_date`, plus `dim_industry`. Keep one fact per state/month and another per state/industry/month to avoid repeating SNAP measures across industries.
- Calculate payroll job gains/losses and year-over-year employment and SNAP participation changes. Validate dimension references, uniqueness, coverage, and source-to-output counts.

## Final output

Gold will contain three dimensions and two business-ready fact tables stored as Delta tables and queried using Spark SQL. Results and charts will compare state jobs with SNAP participation and rank selected industries by job gains/losses over clearly stated periods. Reporting views will expose complete comparable records/months only, with the latest complete reporting period identified. The final presentation will include a live demonstration of raw storage, Spark processing, data-quality handling, and analytical results. Implementation remains pending; optional GDP is outside the initial deliverable.
