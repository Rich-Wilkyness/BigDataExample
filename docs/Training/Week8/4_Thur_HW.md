# GCP Day 2 — Homework Assignment
**Topics: Apache Beam, Dataflow, Dataproc, BigQuery Analytics, and Data Studio**

## Main Assignment: Prepare Your Final Presentation

**Your primary homework is to continue working on your final project and presentation.** Prioritize getting your demonstration working and preparing to explain your architecture and technical decisions.

Your presentation should cover:

- **Project overview:** What problem are you solving?
- **Architecture:** Which cloud services and technologies are you using, and how do they connect?
- **Data pipeline:** How does data move from ingestion through processing and storage?
- **Demonstration:** Show the working components of your project.
- **Technical decisions:** Explain why you selected your tools and what alternatives you considered.
- **Challenges and lessons learned:** Describe problems you encountered and how you addressed them.

Be prepared to explain your work, not just show screenshots.

## Supplemental Homework — Day 2 Review

Keep the reading brief. Spend approximately **20–30 minutes** reviewing the following concepts.

### 1. Apache Beam and Google Cloud Dataflow

Review how Apache Beam defines data-processing pipelines and how Dataflow executes them on Google Cloud.

**Questions:**
- What is the difference between Apache Beam and Dataflow?
- What are `PCollection` and `PTransform`?
- How do batch and streaming pipelines differ?

Reading: [Apache Beam Programming Guide](https://beam.apache.org/documentation/programming-guide/) — focus on the introductory concepts.

### 2. Google Cloud Dataproc

Review Dataproc's role in running Apache Spark and Hadoop workloads.

**Questions:**
- When would you choose Dataproc instead of Dataflow?
- Why might a company migrate an existing Spark application to Dataproc?

Reading: [Dataproc Overview](https://cloud.google.com/dataproc/docs/concepts/overview)

### 3. BigQuery and Analytics

Review how processed data can be organized into fact tables, dimension tables, and analytical views.

**Questions:**
- What is the purpose of a fact table versus a dimension table?
- Why might we create a BigQuery view for a dashboard instead of querying raw data directly?
- How do partitioning and clustering improve BigQuery performance?

Reading: [Introduction to Partitioned Tables](https://cloud.google.com/bigquery/docs/partitioned-tables-intro) — skim the overview.

### 4. Google Data Studio (formerly Looker Studio)

Review how Data Studio connects to BigQuery and presents analytical information.

**Questions:**
- What is the difference between a dimension and a metric?
- What types of visualizations are useful for geographic data?
- Why is it important to verify dashboard numbers against the source data?

Reading: [Data Studio Documentation](https://cloud.google.com/looker/docs/studio) — review the introductory material.

## Optional Hands-On Practice

If your final presentation is already progressing well, choose **one** activity:

- Create a simple BigQuery analytical view and connect it to a Data Studio report.
- Add a scorecard, table, or time-series chart to an existing dashboard.
- Draw an architecture diagram comparing Dataflow and Dataproc for a data-processing use case.

## Submission Expectations

**Required:** Make meaningful progress on your final project and presentation. Be ready to demonstrate your work and discuss your architectural choices.

**Supplemental:** Review the four topics above and be prepared to discuss the questions in class. Written answers are not required.

**Priority:** Final presentation first. The reading and optional exercises are intended to reinforce today's material, not distract from your final project.