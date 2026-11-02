# Week 7 Thursday — Delta Changes, Incremental Ingestion, Jobs, and MLflow

> Level: Intermediate
> Prerequisites: [Tuesday's lakehouse foundations](2_Tue_Azure_Adv.md) and [Wednesday's declarative pipelines](3_Wed_Azure_Adv2.md)
> Practical companion: [Thursday demonstrations](4.1_Thur_steps.md)
> Evidence: Conceptual guide; reconstructed examples have not been executed
> Primary documentation reviewed: 2026-10-22

## Overview and learning objectives

A useful pipeline must handle change: new files arrive, existing records are corrected, jobs fail, schemas evolve, and models are retrained. Different kinds of state require different mechanisms. A Delta version records table commits; a streaming checkpoint records processing progress; a business key identifies an observation; an MLflow run records an experiment.

After this lesson, you should be able to explain time travel versus restore, reason about keyed updates and replay, separate CDC from SCD, distinguish file progress from row deduplication, draw task dependencies, and trace an ML model from training data to logged artifact and batch prediction.

## 1. Delta history, time travel, restore, and cleanup

A Delta write commits a new table state. **History** lists operations and versions. **Time travel** reads an earlier retained snapshot without changing the current table. **Restore** makes the contents of an earlier version current through a new commit.

| Operation | Purpose | Changes current table contents? |
| --- | --- | --- |
| `DESCRIBE HISTORY` | Inspect committed operations | No |
| `VERSION AS OF` / `TIMESTAMP AS OF` | Read a retained historical snapshot | No |
| `RESTORE TABLE` | Publish a prior state as the new current state | Yes |
| `MERGE INTO` | Apply keyed insert/update/delete rules | Yes |
| `VACUUM` | Remove eligible unreferenced data files | Removes physical files; can reduce historical readability |

A version number identifies a commit, not a day or an individual row. One commit can affect many rows; one row can be changed by many commits. Inspect history to find actual versions rather than assuming the demonstration is still at version 0, 1, or 2.

Time travel requires the necessary log metadata and data files. A visible history entry does not guarantee all files remain readable. Cleanup and retention settings limit recovery; this is not permanent backup. Restoring does not erase the fact that the bad commit happened, and downstream streams may treat restored data as new changes requiring careful handling. See [table history](https://learn.microsoft.com/en-us/azure/databricks/tables/history).

Time travel compares table states across processing time. A window function such as `LAG` compares rows within a selected query input. They answer different questions; neither replaces the other.

## 2. How `MERGE INTO` works

**Upsert** means update matching records and insert records that are missing. A `MERGE` names a target, provides a source, defines a match condition, and chooses actions for matched/unmatched rows. It is not a generic replacement for every join or union.

```text
Target: ST001 → 10 bikes, ST002 → 15 bikes
Source: ST001 → 20 bikes, ST003 →  8 bikes
Match: station_id
Result: ST001 → 20, ST002 → 15, ST003 → 8
```

The source ST001 matches an existing target key, so its value updates. ST003 is absent and inserts. ST002 has no matching source and remains unchanged in this example. Deletion requires an explicit rule; omission from the source does not automatically delete it.

### Keys and idempotency

Repeating the same deterministic upsert can leave the same logical rows when source/target key assumptions and actions are appropriate. Delta does not make every MERGE idempotent. An update such as `target.count + source.count` applies again on retry. A `current_timestamp()` assignment changes on retry. Source duplicates can insert duplicate new keys or cause ambiguous updates; target uniqueness is not automatically established by the match condition.

For a current-state station table, the key might be `station_id`. For an observation fact, it is `(station_id, snapshot_timestamp)`. Decide the target contract before selecting a match condition. Prevent late older observations from overwriting newer state when maintaining a latest-status table. See [Delta MERGE](https://learn.microsoft.com/en-us/azure/databricks/delta/merge).

## 3. CDC, change data feed, and SCD

| Concept | Purpose | Example |
| --- | --- | --- |
| Change Data Capture (CDC) | Capture source inserts, updates, and deletes for downstream use | Continue replicating source changes during migration |
| Delta Change Data Feed (CDF) | Expose supported row changes from a configured Delta table | Consume inserts and update pre/post images from retained versions |
| Slowly Changing Dimension (SCD) | Model how descriptive business attributes change | Retain historical station capacity or customer address |

CDC describes change capture, not one mandatory history-table layout. CDF is one Delta-specific feature with enablement and retention requirements. SCD is a modeling strategy and can be built from CDC events or snapshots.

**SCD Type 1** overwrites an attribute and retains only the current value in that dimension. **SCD Type 2** retains multiple versions with validity boundaries, often a version key and current-row indicator. Adding only a last-updated timestamp does not make a table Type 2.

Tuesday's station dimension records observed attribute changes with `valid_from`, `valid_to`, and `is_current`. A fact matches the version effective at its snapshot time. The interval is start-inclusive/end-exclusive, and the latest version has no end time. Observation time may differ from the true real-world change time.

## 4. Auto Loader and incremental ingestion

Auto Loader uses the `cloudFiles` source to discover/process new files. JSON remains the payload format selected by `cloudFiles.format`. It can support periodically triggered ingestion or a continuously running workload. An `availableNow=True` trigger processes the available input and stops after completing that backlog.

| State/location | Meaning |
| --- | --- |
| Source path | Files to ingest |
| `cloudFiles.schemaLocation` | Inferred schema and schema evolution metadata |
| `checkpointLocation` | Query progress and recovery state |
| Delta target | Committed output table |

Use persistent metadata paths separate from incoming data and table storage. Give independent streams independent checkpoints. Preserve the same compatible checkpoint when resuming the same query. Deleting or replacing it can cause reprocessing; pointing it at a different logical target is not a safe way to start a new ingestion.

With supported Auto Loader/Delta configurations and retained state, ingestion can resume without appending each already-committed file again. This guarantee is about processing state. Two different files can still contain the same station observation, and the same file can contain duplicates.

### Checkpointing versus deduplication

**Checkpointing** answers “What work has this query already committed, and how does it resume?” **Deduplication** answers “Which records represent the same business event or observation?” Keep both. Neither means arbitrary source mutation or all downstream replay becomes safe.

A batch `distinct()` removes identical rows within its input. Cross-batch event deduplication requires an appropriate state/key strategy, not a one-time distinct over only the latest micro-batch. See [Auto Loader production guidance](https://learn.microsoft.com/en-us/azure/databricks/ingestion/cloud-object-storage/auto-loader/production).

## 5. Schema evolution has several boundaries

Auto Loader's input schema tracking, parsing behavior, and Delta's output schema rules are separate. A new JSON field may require updating the inferred schema and restarting the stream, depending on the configured evolution mode. A sink must also permit the intended schema change. Rescued data can retain unexpected fields/type mismatches for investigation.

Removing a field, renaming it, or changing its meaning is not equivalent to adding a nullable column. Casts and business validations still need review. Avoid assuming `mergeSchema` or Avro solves every schema change. The [schema evolution documentation](https://learn.microsoft.com/en-us/azure/databricks/ingestion/cloud-object-storage/auto-loader/schema) describes mode-specific behavior.

## 6. Lakeflow Jobs: orchestrate execution

A Job coordinates tasks such as notebook execution or a declarative-pipeline update. It defines dependencies, compute, schedules, parameters, retries, and notifications. A declarative pipeline coordinates data definitions; a Job coordinates task execution.

```text
bronze_ingestion → silver_transformation → gold_transformation
```

With the normal **All succeeded** dependency condition, Gold does not run if Silver fails. Other conditions can support cleanup or failure-handling tasks, so inspect the actual configuration before describing behavior. Retrying a task requires safe rerun logic; a transient service error may clear, while invalid data will usually fail again.

A successful Bronze task does not mean Silver or Gold committed. Distinguish a task's run history, a Delta table's history, and a checkpoint's progress. Persist intermediate results between notebooks; Python variables from one notebook are not a dependable cross-task data interface. See [task configuration](https://learn.microsoft.com/en-us/azure/databricks/jobs/configure-task).

## 7. MLflow and the machine-learning lifecycle

MLflow is an open-source project with Databricks integration, not a Databricks-only training algorithm. Frameworks such as scikit-learn, PyTorch, and TensorFlow fit models. MLflow tracks and packages work and supports model lifecycle operations; the surrounding compute runs training and inference.

| Object | Meaning | Citi Bike example |
| --- | --- | --- |
| Experiment | Groups related runs | Availability estimation experiments |
| Run | One tracked execution | A random-forest training/evaluation attempt |
| Parameter | Configuration choice | Tree count or maximum depth |
| Metric | Measured evaluation result | Mean absolute error |
| Artifact | Saved output file/object | Plot, model, environment specification |
| Model signature | Expected input/output structure | Feature names/types and prediction type |
| Registered model/version | Governed, versioned model identity | A model registered under catalog/schema/name |

Logging a model, registering it, and deploying it are separate actions. Registration does not create a serving endpoint. A batch prediction job can load a saved model and score a table without real-time serving. Current MLflow releases also support model tracking/evaluation and tracing for AI applications. Traces expose instrumented calls, inputs/outputs, timing, and errors; they do not reveal an AI's hidden internal reasoning. See [MLflow on Databricks](https://learn.microsoft.com/en-us/azure/databricks/mlflow/).

### Training data and evaluation

A **feature** is an input available at prediction time. A **target** is the value to estimate. Specify the prediction time/horizon: estimating availability for the same observation differs from predicting it one hour ahead. A forecast label must be aligned to future observations without using future information as a feature.

A chronological train/test split helps evaluate temporal generalization. Fit preprocessing on training data only. Ordinary scikit-learn processing is local, so bound Spark-to-pandas conversion. Record the data version, sampling rule, feature definitions, split boundary, and model environment for reproducibility.

**MAE** is the average absolute error in target units. **RMSE** takes the square root of mean squared error and penalizes large errors more heavily. Lower values are preferable when comparing the same target and evaluation population, but neither alone establishes production usefulness. Compare to a simple baseline and check performance across stations/time periods.

Data engineering responsibilities often include ingestion, reliable feature/training datasets, freshness, access, and batch scoring. Data science and platform responsibilities vary by team; do not assume one role always owns all model deployment or cloud architecture.

## 8. Failure model, data quality, and production progression

| Symptom | Evidence to inspect |
| --- | --- |
| Historical read fails | Requested version, retained logs/data, retention and cleanup |
| MERGE fails or duplicates rows | Source match uniqueness, target key contract, deterministic rules |
| Restart duplicates observations | Checkpoint continuity and business duplicates across files |
| Ingestion stops after a new field | Auto Loader evolution mode, restart behavior, Delta sink schema |
| Gold remains old | Task dependencies, upstream failure, committed table versions |
| Model metric seems implausibly good | Leakage, sampling bias, split, baseline, feature availability |
| Model logged but not registered | Registry URI, signature, catalog/schema privileges |

Preserve a clear owner for each state boundary. Recovery may mean resuming a stream, fixing data, rerunning a dependent task, rebuilding a derived table, or restoring a retained table version. These are different operations with different effects on downstream consumers.

## Knowledge check and completion checklist

1. Why does a restore create a new current version rather than erase later commits?
2. Which MERGE actions are unsafe to repeat, and why?
3. How could CDC events feed an SCD Type 2 dimension?
4. What duplicates can remain even with a healthy checkpoint?
5. Which task dependency keeps Gold from running after Silver fails?
6. How do logging, registering, and deploying a model differ?
7. What feature or split decision could leak future information into a training evaluation?

- [ ] I can distinguish table versions, observation history, streaming progress, and experiment history.
- [ ] I can define the key and replay rule before choosing MERGE.
- [ ] I can explain schema and business-quality checks separately.
- [ ] I can trace ingestion → transformation → orchestration → model tracking.
- [ ] I can state which procedures remain unexecuted.

## References

- [Delta history and time travel](https://learn.microsoft.com/en-us/azure/databricks/tables/history)
- [MERGE](https://learn.microsoft.com/en-us/azure/databricks/delta/merge)
- [Change Data Feed](https://learn.microsoft.com/en-us/azure/databricks/delta/delta-change-data-feed)
- [Auto Loader](https://learn.microsoft.com/en-us/azure/databricks/ingestion/cloud-object-storage/auto-loader/)
- [Auto Loader schema evolution](https://learn.microsoft.com/en-us/azure/databricks/ingestion/cloud-object-storage/auto-loader/schema)
- [Lakeflow Jobs](https://learn.microsoft.com/en-us/azure/databricks/jobs/)
- [MLflow on Databricks](https://learn.microsoft.com/en-us/azure/databricks/mlflow/)
- [Models in Unity Catalog](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/manage-model-lifecycle/)
