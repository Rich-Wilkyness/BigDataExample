# Shared setup

[Demo index](README.md)

## Working directory and Python

Run this first command from the repository root, `/Users/richardwilkerson/VSCodeProjects/BigDataExample`. The conversations used Python 3.11.6 on Linux; the guides use macOS-compatible paths and shell commands. Dependency versions are not fully captured, so the supplied requirements files are dependency lists, not a reproduced environment lock.

```bash
cd docs/Training/Week8/friday-ml-demos
python3 -m venv .venv
source .venv/bin/activate
```

Each demo's commands start from this `friday-ml-demos` directory unless stated otherwise. In another terminal, navigate to the same directory and activate `.venv` again. Install the selected demo’s requirements, as its guide shows. For one environment containing every demo dependency, use `python -m pip install -r requirements-local.txt`; its primary package versions match the local verification environment. AWS export support is optional: `python -m pip install boto3`. Use Ctrl+C to stop a foreground process.

## Local Citi Bike files: demos 01–05

No SQL database is required. The [data preparation guide](data-preparation.md) describes the verified AWS export and how to refresh it. On this workspace, the exported snapshot is already under the repository's `data/raw/week8-friday-citibike/` directory:

- `stations.csv`: 2,519 station-information rows.
- `station-status.csv`: 2,519 availability rows from the matching saved capture.
- `provenance.json`: source hashes, feed update times, schema version, and export hashes.

The shared reader locates these files relative to its source location, so every demo can use the same export. CSV is the supplied default. If you use a different local CSV or Parquet export, set an absolute path:

```bash
export CITIBIKE_STATIONS_PATH='/absolute/path/to/stations.csv'
export CITIBIKE_STATUS_PATH='/absolute/path/to/station-status.csv'
```

The data is Git-ignored working data, not a bundled public dataset. A different checkout must create its own local export. After export, Python reads local files without AWS credentials. The retained `station-view.sql` files are historical references only; do not run them for the current lessons. Demo 02 joins the saved availability snapshot by default. Its optional `--live` mode needs internet, with no API key, and depends on the public feed's current contract.

## MLflow: demos 05 and 07–10

Install MLflow using the selected demo's requirements, then run this from `friday-ml-demos` in a dedicated terminal:

```bash
source .venv/bin/activate
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --host 127.0.0.1 \
  --port 5000
```

Keep that process running. Open `http://127.0.0.1:5000` for experiments, registry versions, and traces. Keep the same server working directory so the SQLite tracking database stays in the same place.

The capacity model uses the generic MLflow serving CLI on port 5001. The fraud model uses `08-kafka-fraud-inference/serve-model.py` on that port: it loads a numbered MLflow artifact and reports its identity with predictions. The two services use the same port at different stages. Stop the capacity serving process before starting fraud serving. Port 5000 is the tracking UI; port 5001 accepts prediction requests at `/invocations`; port 5050 is the later Flask dashboard.

## Kafka: demos 07–10

The current guide uses **Apache Kafka 4.4.0 in KRaft mode**. Apache's downloads and quickstart list 4.4.0 as of October 31, 2026. Kafka 4.x uses KRaft for cluster metadata; ZooKeeper support was removed in 4.0. A Python Kafka client still connects to the broker on port 9092; it does not connect directly to a controller. [Apache quickstart](https://kafka.apache.org/quickstart/), [downloads](https://kafka.apache.org/community/downloads/), and [4.0 upgrade notes](https://kafka.apache.org/40/getting-started/upgrade/).

This is a fresh local lab using its own storage. It does not migrate an existing ZooKeeper cluster or alter its data. If you already have a working Kafka 4.x KRaft broker on `localhost:9092`, reuse it and skip formatting/startup below. Run one broker on that port at a time.

### 1. Select the Kafka binary distribution and Java

Download `kafka_2.13-4.4.0.tgz` from the official downloads page. For a download saved in `~/Downloads`, these commands extract it to `~/Applications`:

```bash
mkdir -p "$HOME/Applications"
tar -xzf "$HOME/Downloads/kafka_2.13-4.4.0.tgz" -C "$HOME/Applications"
export KAFKA_HOME="$HOME/Applications/kafka_2.13-4.4.0"
java -version
"$KAFKA_HOME/bin/kafka-topics.sh" --version
```

The Apache quickstart requires Java 17 or newer. Use your existing compatible JDK; no Java installation or system change is performed by this guide. `2.13` is the Scala build suffix in the Kafka archive, not the Kafka version. `kafka-python` is the separate Python client package, with its own version numbers.

### 2. Initialize this lab's KRaft storage once

From `friday-ml-demos`, with no broker for this lab running:

```bash
# Only for first-time initialization of this lab's fresh kafka-data directory.
# Keep the same working directory for formatting and all future broker starts.
KAFKA_CLUSTER_ID="$("$KAFKA_HOME/bin/kafka-storage.sh" random-uuid)"
"$KAFKA_HOME/bin/kafka-storage.sh" format \
  --standalone \
  -t "$KAFKA_CLUSTER_ID" \
  -c kafka-server.properties
```

The commented [configuration](kafka-server.properties) runs broker and controller roles together in one JVM. `--standalone` initializes a one-controller quorum; formatting creates the cluster metadata in `./kafka-data`. Run this initialization only for new storage. Normal restarts reuse that directory and do not generate another cluster ID or reformat it. One node has no failover protection and is appropriate for this local learning demo.

### 3. Start Kafka and check the broker

From `friday-ml-demos`, keep this terminal running:

```bash
export KAFKA_HOME="$HOME/Applications/kafka_2.13-4.4.0"
"$KAFKA_HOME/bin/kafka-server-start.sh" kafka-server.properties
```

In another terminal, set the same installation path and check that the broker answers:

```bash
export KAFKA_HOME="$HOME/Applications/kafka_2.13-4.4.0"
"$KAFKA_HOME/bin/kafka-topics.sh" --bootstrap-server localhost:9092 --list
```

A successful empty listing is normal before any topics are created. Continue with demo 07 to create `fraud-transactions`, and demo 08 to create `fraud-predictions`. Each terminal running a Kafka CLI command needs `KAFKA_HOME` set. Python processes use `localhost:9092` directly and do not need that variable.

### 4. Stop and restart

Stop the producer and consumers, then stop the broker with Ctrl+C in its terminal. To resume, run only the server-start command from the same working directory with the same configuration. Existing Kafka topic data and group offsets remain in `kafka-data`; SQLite and training CSV state are separate. No ZooKeeper terminal is part of this setup.

The installation, storage-format command, and broker startup are documented from current primary sources; they were not executed during this guide update. See the [KRaft diagram](visuals/README.md#kraft-and-event-processing) for the distinction between metadata and transaction data.

## OpenAI: demo 09

Use your own API account and an available model. Export `OPENAI_API_KEY` in the terminal that starts Flask; set `OPENAI_MODEL` to the model you intend to use. The source used `gpt-4.1-mini` as an example. No model availability or API access was checked in this cleanup.
