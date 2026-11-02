# Week 7 — Azure and Databricks

Read each lecture for concepts, then its steps guide for the instructor follow-along. The `.2` files retain the original homework, learner responses, and existing feedback.

| Day | Lecture: theory and knowledge | Steps: console and notebook workflow | Homework |
| --- | --- | --- | --- |
| Monday | [Azure foundations](1_Mon_Azure.md) | [ADLS setup and CSV upload](1.1_Mon_Steps.md) | [Monday homework](1.2_Mon_HW.md) |
| Tuesday | [ADF, Spark, Delta, and governance](2_Tue_Azure_Adv.md) | [S3 → ADLS → Bronze/Silver/Gold](2.1_Tue_steps.md) | [Tuesday homework](2.2_Tue_HW.md) |
| Wednesday | [Declarative pipelines](3_Wed_Azure_Adv2.md) | [Lakeflow pipeline](3.1-wed-steps.md) | [Wednesday homework](3.2_Wed_HW.md) |
| Thursday | [Delta changes, ingestion, Jobs, and MLflow](4_Thur_Databricks.md) | [Thursday demonstrations](4.1_Thur_steps.md) | [Thursday homework](4.2_Thur_HW.md) |

Monday establishes storage and identity. Tuesday connects movement, processing, and governance. Wednesday expresses transformations as a managed data dependency graph. Thursday adds incremental ingestion, keyed updates, recovery, task orchestration, and a model lifecycle.

The Azure portal manages Azure resources. Data Factory Studio authors ADF pipelines. The Databricks workspace contains notebooks, Catalog, Jobs & Pipelines, and Experiments. Each steps guide identifies which interface to use.

## Evidence and reconstruction

**Captured procedure** means a sequence or configuration present in the original notes. **Reconstructed example** means missing details supplied from the captured intent and official documentation; suggested names are not recovered instructor resources. **Learner-reported result** means previously supplied output. **Expected result** means an unexecuted example's intended behavior.

The October 22, 2026 reorganization changes documentation only. Tuesday retains its October 20 learner-reported results. New examples have not been run in Azure or Databricks. Portal labels, compute capabilities, and library versions can differ from the classroom demonstration.

## Separate project material

[U.S. Jobs and SNAP pipeline](us-jobs-snap-pipeline/README.md) is the independent weekly project. [GCP foundations and scope](gcp-data-engineering-scope.md) teaches the AWS/Azure connections and personally funded technology choices; its [GCP project checkpoints](us-jobs-snap-pipeline/gcp-learning-plan.md) begin with account and cost setup. Neither is required for the daily Citi Bike demonstrations.
