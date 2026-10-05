# Wednesday market pipeline — starting point

This folder organizes the classroom market demonstration so you can start [Wednesday's homework](../3.3_Wed_HW.md). The aggregation, written answers, and architecture diagram remain yours to create. Choose **either Spark or Flink** for Part 1; you do not need to implement both or build another dashboard.

## Files and ownership

| File | Role | Source |
| --- | --- | --- |
| `market-api.py` | Simulates stock trades through `GET /tick` | Supplied replacement plumbing; original API was absent from the pasted chat |
| `market-producer.py` | Fetches ticks and publishes JSON to Kafka topic `market_ticks`, keyed by symbol | Supplied replacement plumbing; original producer was absent |
| `spark-market-consumer.py` | Writes Spark microbatch records to `/tmp/spark-market.jsonl` | First Python block in [teacher chat](../chatgpt.md), copied unchanged |
| `flink-market-consumer.py` | Writes the classroom Flink demonstration to `/tmp/flink-market.jsonl` | Third Python block, with only the import and connector setup adapted for a local JAR |
| `market-dashboard.py` | Streamlit comparison dashboard reading those two JSONL files | Second Python block, copied unchanged |
| `spark-market-parquet.py` | Writes unaggregated ticks to partitioned Parquet for Part 2 | Supplied replacement plumbing; original Parquet writer was absent |
| `requirements.txt` | Main environment dependencies | Setup |
| `requirements-flink.txt` | Separate PyFlink environment dependency | Setup |
| `homework/market_aggregation_spark.py` | Your new consumer; currently TODOs only | Learner workspace; replace with a Flink file if you choose Flink |
| `homework/answers.md` | Empty response outline | Learner workspace |

The copied [shared chat](https://chatgpt.com/share/6abc125f-7fb0-83e9-9c4e-61d1dc8255ae) could not be fetched during setup. The local pasted chat is the source of the extracted code, and it remains unchanged. The supplied replacements are not claimed to reproduce the missing instructor files exactly.

## How the components connect

The API creates events. The producer moves them into Kafka. Spark and Flink independently consume the same topic; you do not connect Spark to Flink. The dashboard reads the consumers' local files, rather than reading Kafka itself. The Parquet writer is another independent consumer.

```text
market-api.py → market-producer.py → Kafka: market_ticks
                                     ├→ Spark consumer → JSONL ┐
                                     ├→ Flink consumer → JSONL ┴→ Streamlit
                                     ├→ Spark Parquet writer → Parquet files
                                     └→ YOUR aggregation consumer → updated statistics
```

All Python processes in this setup run on your Mac. `localhost:9092` must reach your existing Kafka broker through its published listener. Keep the Kafka setup you already use for the weather exercise. MongoDB is not used by this market example.

## First checkpoint: one market event

Start at the repository root. These instructions reuse its `.venv`; they do not install anything until you run the commands. The existing environment had all seven main packages importable during setup.

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample
source .venv/bin/activate
unset SPARK_HOME
cd docs/Training/Week4/3.2-wed-market
python -m uvicorn market-api:app --host 127.0.0.1 --port 8001
```

In another terminal, request a single event:

```bash
curl --fail http://127.0.0.1:8001/tick
```

You should see `sequence`, `symbol`, `price`, `size`, `side`, `exchange_ts`, and `api_ts`. Stop here first and identify what each field means. No Kafka, Spark, or Flink process is needed for this checkpoint. The API uses one worker; its sequence and simulated prices restart when it restarts.

If a main dependency is missing, run these commands from the repository root:

```bash
.venv/bin/python -m pip install -r docs/Training/Week4/3.2-wed-market/requirements.txt
.venv/bin/python -m pip install -e '.[spark-notebook]'
```

## Next checkpoints: Kafka, then Spark

For each main-environment terminal below, first repeat:

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample
source .venv/bin/activate
unset SPARK_HOME
cd docs/Training/Week4/3.2-wed-market
```

Keep the API running. Confirm your existing broker is running and `market_ticks` exists; use your existing Kafka topic-management command to create it if necessary. Broker topic auto-creation is configuration dependent. Do not format Kafka storage to add this topic.

Start the Spark demonstration in its own terminal:

```bash
spark-submit --version
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0 spark-market-consumer.py
```

The connector command matches the repository's pinned PySpark 4.2.0 environment. Check that `spark-submit --version` reports that version before running; a different Spark installation needs its matching Kafka connector. The first launch may download JVM dependencies.

Once Spark is listening, start the producer in another terminal:

```bash
python market-producer.py --rate 50
```

The rate is a target, limited by HTTP and Kafka acknowledgement time. The producer adds `kafka_ts` just before sending; this payload field is a producer timestamp, not the broker's confirmed arrival time. Expect producer output every 100 events and Spark's `SPARK MICRO-BATCH` messages. Confirm that `/tmp/spark-market.jsonl` receives records before proceeding.

Launch the supplied dashboard in another terminal:

```bash
python -m streamlit run market-dashboard.py --server.port 8503
```

Open `http://localhost:8503`. It can display Spark before you start Flink. Spark and Flink use latest offsets on a fresh start, so keep the producer running as each consumer starts. Spark reuses its checkpoint on restart. All JSONL feeds and checkpoint paths are local demonstration data under `/tmp`; old records can remain from earlier runs.

## Add Flink when you are ready

Use the separate environment from the [Wednesday Flink setup](../3_Wed_Flink.md#install-a-compatible-python-environment), rather than installing PyFlink into the main repository environment. That example pins PyFlink 2.2.1. Apache documents [its Python installation requirements](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/dev/python/installation/) and the [Kafka connector](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/table/kafka/). The `5.0.0-2.2` connector matches this Flink release; the SQL connector JAR packages dependencies for this local setup.

From the repository root, download the connector into this market folder:

```bash
mkdir -p docs/Training/Week4/3.2-wed-market/lib
curl -L --fail --show-error \
  https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/5.0.0-2.2/flink-sql-connector-kafka-5.0.0-2.2.jar \
  -o docs/Training/Week4/3.2-wed-market/lib/flink-sql-connector-kafka-5.0.0-2.2.jar
```

If you created the weather example's environment as that lesson describes, reuse it:

```bash
unset FLINK_HOME
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
export PATH="$JAVA_HOME/bin:$PATH"
export PYFLINK_CLIENT_EXECUTABLE="$PWD/docs/Training/Week4/3.1-wed-flink-weather/.venv/bin/python"
export PYFLINK_PYTHON="$PYFLINK_CLIENT_EXECUTABLE"
docs/Training/Week4/3.1-wed-flink-weather/.venv/bin/python docs/Training/Week4/3.2-wed-market/flink-market-consumer.py
```

If that environment does not exist, complete the linked setup first. A pip requirement alone does not supply the Java runtime or Kafka connector. Flink startup, connector loading, and native PyFlink installation on this Mac remain unverified.

**Read the teacher's timestamp comments before interpreting the dashboard.** The final Flink example sets `processed_ts` to `kafka_ts + 5 ms`; Spark uses a wall-clock timestamp at the beginning of its batch callback. Their plotted latency values therefore measure different things. The Flink chart illustrates a simulated processing timeline, and its file writes are demo side effects rather than a checkpoint-coordinated sink. Keep these limitations in mind when describing your observations.

## Part 2 infrastructure: Parquet

The pasted notes did not include a Parquet writer. This supplied baseline stores events without doing your aggregation. Use the main environment and market working directory from the earlier checkpoint, with the API and producer still running:

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0 spark-market-parquet.py
```

After events arrive, locate its files:

```bash
find /tmp/market-lake/spark/market_ticks -name '*.parquet'
```

Keep your observations and explanations in `homework/answers.md`. This baseline uses UTC and its own checkpoint, separate from the dashboard consumer. It derives directory fields from `exchange_ts` and skips records whose event timestamp cannot be parsed. It has not been run against Kafka yet.

## Your homework starts here

Open [`homework/market_aggregation_spark.py`](homework/market_aggregation_spark.py). It contains no completed transformation. Use the teacher's Spark setup and JSON schema as references, then implement the assignment's parsing, grouping, statistics, and continuously updated output yourself. The supplied consumers and producer are setup material; your new aggregation consumer is the Part 1 deliverable.

If you choose Flink instead, create `homework/market_aggregation_flink.py` and submit that file in place of the Spark starter. Complete your written responses and draw `homework/architecture.png` yourself. Snowflake configuration is not needed for today's starting point.

## Verification scope

All seven Python files passed syntax parsing. The simulated API returned schema-valid ticks in a direct in-process smoke check; the producer serialized a tick with the expected Kafka topic and key in an isolated check using fake HTTP/Kafka clients. The Spark and dashboard files match their source blocks exactly. No dependencies were installed and no background services were launched during setup. HTTP server execution, Kafka publishing, Spark/Flink execution, Parquet creation, and dashboard rendering remain pending.
