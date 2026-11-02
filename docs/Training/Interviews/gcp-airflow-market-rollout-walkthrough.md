# GCP Console + Airflow: market rollout walkthrough

This small companion to the [interview playbook](richard-wilkerson-interview-playbook.md) demonstrates one idea: deploy the same workflow for two markets, then use configuration to decide which market may publish. The markets and quality results are fictional. Publication writes a log message; it does not create BNPL tables or move money.

## Before you begin

Use a development Cloud Composer environment with **Airflow 2.10 or 2.11** for the supplied [DAG file](market-rollout-demo.py). The imports and UI instructions target Airflow 2; do not upload it unchanged into an Airflow 3 environment. Current Google documentation also uses the name **Managed Service for Apache Airflow** for the service previously called Cloud Composer.

You need access to the environment's Airflow UI, permission to manage Airflow Variables and trigger DAGs, and upload access to its DAG bucket. Reuse a development environment if available. Creating an environment incurs ongoing charges while it exists, including while the DAG is paused. This guide and DAG have not been executed in GCP.

If you have no environment, use GCP Console → search **Cloud Composer** or **Managed Airflow** → **Environments** → **Create environment**. Choose Gen 3, a development name and region, an available Airflow 2 image, the smallest suitable environment size, and a dedicated environment service account with the permissions required by the creation guide. Review the displayed costs, networking, and service-account requirements before selecting **Create**. If no compatible image is available, this specific sample requires adaptation before deployment. Follow the current [environment creation guide](https://docs.cloud.google.com/composer/docs/composer-3/create-environments) for project-specific prerequisites rather than granting broad roles to bypass an error.

## What you are building

```text
interview_rollout_us: market_gate -> quality_gate -> simulate_publish
interview_rollout_uk: market_gate -> quality_gate -> simulate_publish

Airflow Variable: interview_market_rollout       enable/stop each market
Airflow Variable: interview_quality_US_lab-001   result for one market/batch
```

A DAG is a graph of tasks and dependencies. Each market has its own DAG and run status, so a failed UK quality task does not mark a US run failed. They still share environment capacity. A configuration flag changes behavior; it does not deploy another version of the Python code.

## 1. Open the environment and Airflow UI

1. Select your development project in GCP Console.
2. Open **Environments** under Cloud Composer/Managed Airflow and find the development environment.
3. Check the environment's image/Airflow version and confirm it is running.
4. Follow the **Airflow** link in the **Airflow webserver** column and sign in. This opens a separate Airflow UI; sensors are Python tasks, not settings on the GCP environment page.

Reference: [access the Airflow UI](https://docs.cloud.google.com/composer/docs/composer-3/access-airflow-web-interface).

## 2. Add the rollout configuration

In the Airflow 2 UI, open **Admin → Variables**, select **+** to add a Variable, and set its key to `interview_market_rollout`. Paste this JSON into the value field and save:

```json
{
  "version": 1,
  "markets": {
    "US": {"enabled": true, "kill_switch": false},
    "UK": {"enabled": false, "kill_switch": false}
  }
}
```

`enabled` is the rollout flag. `kill_switch` is an operator stop flag. Both must be JSON booleans, not strings such as `"false"`. `version` identifies the configuration revision. A missing key or malformed configuration fails the task; it does not default to enabling every market. These Variables contain no credentials. See [Airflow Variable management](https://airflow.apache.org/docs/apache-airflow/2.10.5/howto/variable.html).

Add two more Variables to simulate batch validation, with plain text values rather than JSON strings:

| Key | Value |
| --- | --- |
| `interview_quality_US_lab-001` | `passed` |
| `interview_quality_UK_lab-001` | `passed` |

The batch suffix prevents yesterday's successful result from approving a different batch. For every new exercise batch, use a new suffix and supply that same `batch_id` when triggering the DAG. A real validation job would persist a result against the exact source manifest, market, batch, and rule version; an editable Variable is only the teaching substitute.

## 3. Upload the DAG file

1. Return to the environment list in GCP Console.
2. In the environment's **DAGs folder** column, click **DAGs** to open its Cloud Storage `dags/` folder.
3. Choose **Upload files** and upload [market-rollout-demo.py](market-rollout-demo.py). Both DAG definitions are in this one file.
4. Return to Airflow and allow several minutes for synchronization. Find `interview_rollout_us` and `interview_rollout_uk`. Check for import errors if either is absent; inspect the image version before changing dependencies.
5. Unpause these two demonstration DAGs. Their schedule is `None`, so runs are manual.

The file creates three tasks per DAG: `market_gate` checks configuration and records the accepted policy in XCom (Airflow's small task-result store); `quality_gate` waits for the batch's simulated result; `simulate_publish` checks that the policy still permits publication and then logs a message. See [uploading DAGs through Console](https://docs.cloud.google.com/composer/docs/composer-3/manage-dags).

## 4. Run only the first market

For each of the two DAGs, open the trigger menu, choose **Trigger DAG w/ config**, and enter:

```json
{"batch_id": "lab-001"}
```

Open each run's **Grid** or **Graph** view and select tasks to inspect their logs.

| DAG | Expected task behavior |
| --- | --- |
| US | All three tasks succeed; the last task logs `SIMULATED publication: market=US batch=lab-001 config_version=1`. |
| UK | `market_gate` is skipped because UK is disabled; downstream tasks are skipped. No publication message is produced. |

A skipped UK run can appear successful overall under Airflow's DAG-run rules. Inspect task states and logs: a green DAG status alone does not establish publication. No BigQuery data is produced by this exercise.

## 5. Enable the second market without changing code

Edit `interview_market_rollout` in **Admin → Variables**: change `version` to `2` and set `UK.enabled` to `true`, leaving US enabled and both kill switches false. Save. Trigger a new UK run with `{"batch_id": "lab-001"}`.

Expected: UK now reaches `simulate_publish` and logs configuration version 2. You changed configuration, not the DAG source. In a real rollout, you would review reconciliation, correctness, freshness, and runtime for the first market before approving this change.

## 6. Block bad data in one market

Create these new Variables:

| Key | Value |
| --- | --- |
| `interview_quality_US_lab-002` | `passed` |
| `interview_quality_UK_lab-002` | `failed` |

Trigger both DAGs with `{"batch_id": "lab-002"}`. US should reach simulated publication; UK should fail in `quality_gate`, leaving `simulate_publish` upstream-failed. This is a quality gate. The sensor raises a terminal failure immediately for `failed`; it does not retry known-invalid data.

Now edit the rollout configuration: set `version` to `3` and `UK.kill_switch` to `true`. A new UK run should skip at `market_gate`. This is the manual stop override. The quality failure did not automatically set that flag; the demo does not implement persistent circuit-breaker states or half-open recovery.

## 7. Watch a sensor wait and then recover the batch

Create `interview_quality_US_lab-003` with value `pending`. Trigger US with `{"batch_id": "lab-003"}`. Its `quality_gate` should enter waiting/reschedule behavior. Change that Variable to `passed` within five minutes; a later check should let the run continue. Leave it pending and the sensor times out after approximately five minutes, with publication blocked. Missing quality Variables also behave as pending until timeout. See [sensor modes](https://airflow.apache.org/docs/apache-airflow/2.8.2/core-concepts/sensors.html).

For UK recovery, first correct or replace the bad input and obtain a new successful validation result. In this simulated exercise, create `interview_quality_UK_lab-004` with value `passed`, set configuration version `4`, and set `UK.kill_switch` back to `false`. Trigger UK with `{"batch_id": "lab-004"}`. Confirm its task logs before considering it recovered. Editing a failed run's result to `passed` would not prove a real source defect was fixed.

## 8. Explain the production boundary

The sample checks flags at entry and again immediately before simulated publication. A flag change does not terminate an already-running task, and a check followed by a log/write is not an atomic publication lock. Real publication needs an enforced commit boundary, versioned policy, a durable batch ledger, idempotent writes, and exact input/validation identities. A full circuit breaker additionally needs persisted open/closed/half-open state and defined recovery ownership.

When UK is blocked, independent US output may proceed. A combined report requiring both markets must wait or disclose missing coverage. The last accepted UK dataset must show its age and blocked-refresh status; silently presenting it as today's complete data would defeat the gate.

## 9. Clean up the exercise

Pause both demonstration DAGs and wait for active runs to finish or stop them deliberately. Remove only `market-rollout-demo.py` from the environment's DAG bucket, then delete the two demonstration DAGs from the Airflow UI if you also want their run metadata removed. Delete the `interview_market_rollout` and `interview_quality_...` Variables you created for this exercise. Removing the source file and removing run metadata are separate actions.

If you created an environment solely for this exercise, delete that environment through GCP Console when finished, then inspect any remaining exercise bucket objects and other resources before removing them. Pausing or deleting a DAG does not stop environment charges. Preserve unrelated resources.

## Evidence

Primary documentation reviewed October 27, 2026. Local Python syntax and gate-function checks are recorded in the repository coverage note. Airflow DAG parsing, UI steps, scheduler/sensor behavior, IAM, cloud execution, publication logs, and billing have not been verified in a live Composer environment. Record your actual environment image, run IDs, observed task states, and cleanup result when you execute the exercise.
