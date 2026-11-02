"""Airflow 2.10/2.11 teaching DAGs: configuration and simulated quality gates.

Upload this file to a development Composer environment's dags folder.
Publication only writes a log message. See the companion walkthrough.
"""

import logging
from datetime import datetime, timezone

from airflow import DAG
from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor


CONFIG_KEY = "interview_market_rollout"


def read_market_config(market):
    """Reject missing/malformed policy rather than silently enabling a market."""
    config = Variable.get(CONFIG_KEY, deserialize_json=True)
    policy = config["markets"][market]
    if type(config["version"]) is not int:
        raise AirflowFailException("Configuration version must be an integer")
    for field in ("enabled", "kill_switch"):
        if type(policy[field]) is not bool:
            raise AirflowFailException(f"{field} must be a JSON boolean")
    return {"version": config["version"], **policy}


def gate_market(market):
    """Snapshot rollout policy for this market's run in its task result."""
    policy = read_market_config(market)
    if not policy["enabled"] or policy["kill_switch"]:
        raise AirflowSkipException(f"Market {market} is disabled or stopped")
    logging.info("Market %s accepted config version %s", market, policy["version"])
    return policy


def wait_for_quality(market, dag_run, **context):
    """Read a market/run-specific simulated validation result from a Variable."""
    # The manual trigger supplies a unique label for each new batch exercise.
    batch_id = dag_run.conf["batch_id"]
    if not isinstance(batch_id, str) or not batch_id or not all(
        character.isalnum() or character in "-_" for character in batch_id
    ):
        raise AirflowFailException("batch_id must contain only letters, digits, - or _")
    key = f"interview_quality_{market}_{batch_id}"
    status = Variable.get(key, default_var="pending")
    if status == "failed":
        raise AirflowFailException(f"Quality failed for {market}/{batch_id}")
    if status not in ("pending", "passed"):
        raise AirflowFailException(f"Unknown quality status: {status}")
    return status == "passed"


def simulate_publish(market, ti, dag_run, **context):
    """Recheck the current stop policy before logging simulated publication."""
    accepted = ti.xcom_pull(task_ids="market_gate")
    current = read_market_config(market)
    if not current["enabled"] or current["kill_switch"] or current != accepted:
        raise AirflowFailException("Policy changed or stopped; start a reviewed new run")
    logging.info(
        "SIMULATED publication: market=%s batch=%s config_version=%s",
        market, dag_run.conf["batch_id"], accepted["version"],
    )


def make_market_dag(market):
    """Independent DAG runs keep one market's failure out of another's chain."""
    with DAG(
        dag_id=f"interview_rollout_{market.lower()}",
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        schedule=None,
        catchup=False,
        max_active_runs=1,
        default_args={"retries": 0},
        tags=["interview-practice"],
    ) as dag:
        gate = PythonOperator(
            task_id="market_gate", python_callable=gate_market,
            op_kwargs={"market": market},
        )
        quality = PythonSensor(
            task_id="quality_gate", python_callable=wait_for_quality,
            op_kwargs={"market": market}, mode="reschedule",
            poke_interval=30, timeout=300,
        )
        publish = PythonOperator(
            task_id="simulate_publish", python_callable=simulate_publish,
            op_kwargs={"market": market},
        )
        gate >> quality >> publish
    return dag


for market_code in ("US", "UK"):
    globals()[f"interview_rollout_{market_code.lower()}"] = make_market_dag(market_code)
