HW is to get a free account for tomorrow
https://signup.snowflake.com/


# Lecture Notes


he started up his kafka, but had issues:
bin/kafka-server-start.sh config/server.properties

to format a kafka cluster:

bin/kafka-storage.sh format
--standalone
-t "$KAFKA_CLUSTER_ID"
-c config/server.properties

before the above, get a new cluster id:
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
echo $KAFKA_CLUSTER_ID


get weather producer and consumer running

run streamlit


Now we will get into Flink


Flink vs Spark Structured Streaming
- Flink is closer to true real time (message by message), latency is significantly less than SSS
- SSS is micro batching

pip install apache-flink

Add flink weather with the Week4/2.3_Tue_HW Producer
- one message at a time / not a batch
create a new dashboard based on flink instead of mongo?


watermark strategy is what?

difference between virtual environment vs virtual machine
(.venv) - allows you to setup dependencies for that environment that you don't want to be global




## Follow-along setup: existing Kafka → Flink → dashboard

The class notes above capture the instructor's sequence. The following setup supplies the missing consumer and dashboard code. Your existing Kafka broker, `homework-weather` topic, and [Tuesday producer](2.3_Tue_HW/producer.py) are sufficient. Do not reformat an existing Kafka cluster: storage formatting is a cluster initialization operation and is not needed to add a consumer.

### What we are building

```text
Existing weather producer (Mac)
    → Kafka localhost:9092 (Docker)
    → Flink SQL job (local JVM, launched by PyFlink on Mac)
    → Python result iterator → MongoDB flink_streaming.weather (Docker)
    → Streamlit dashboard (Mac)
```

Flink is a processing engine. The dashboard still needs a queryable serving store; this example uses your existing MongoDB service with a separate database. Files are in [`3.1-wed-flink-weather/`](3.1-wed-flink-weather/). This is supplied follow-along code, not a claim to reproduce the instructor's unshared implementation.

The SQL job reads the existing JSON fields, preserves the actual Kafka key and topic/partition/offset, converts Celsius to Fahrenheit, categorizes temperature as `cold` below 20°C or `warm` otherwise, and filters rows missing city/temperature or having humidity outside 0–100. This example displays both cold and warm records; your Tuesday Spark filter remains a separate exercise. One output document represents one accepted Kafka record occurrence.

### Install a compatible Python environment

The repository's current `.venv` uses Python 3.14.5. Flink 2.2 documents Python 3.9–3.12 support, so installing `apache-flink` directly into that environment is not the route for this example. Use Python 3.11 in an environment inside the Flink example folder. Flink 2.2.1 and the Kafka SQL connector `5.0.0-2.2` are pinned as a documented compatible pair, not claimed as the latest releases. Java 17 is used for this local setup.

From the repository root on your Apple silicon Mac:

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample
brew install python@3.11
"$(brew --prefix python@3.11)/bin/python3.11" -m venv docs/Training/Week4/3.1-wed-flink-weather/.venv
docs/Training/Week4/3.1-wed-flink-weather/.venv/bin/python -m pip install --upgrade pip
docs/Training/Week4/3.1-wed-flink-weather/.venv/bin/python -m pip install -r docs/Training/Week4/3.1-wed-flink-weather/requirements.txt
java -version
```

If Python 3.11 is already installed, skip the Homebrew install and use its interpreter to create the environment. PyFlink dependencies can require native builds on Apple silicon; if installation fails, keep the actual pip error for diagnosis rather than changing versions at random. If Java 17 is not selected, use your existing Java 17 installation or install it with `brew install openjdk@17`, then set it for the consumer terminal:

```bash
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
```

The Kafka connector is a JVM JAR, separate from the Python pip package. Download it once:

```bash
mkdir -p docs/Training/Week4/3.1-wed-flink-weather/lib
curl -L --fail --show-error \
  https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/5.0.0-2.2/flink-sql-connector-kafka-5.0.0-2.2.jar \
  -o docs/Training/Week4/3.1-wed-flink-weather/lib/flink-sql-connector-kafka-5.0.0-2.2.jar
```

No separate Flink Docker container is needed for this local embedded job. Because the consumer runs on the Mac, `localhost:9092` reaches your already working broker. A containerized Flink deployment would need reachable advertised broker addresses; changing only the bootstrap address is not sufficient if Kafka returns unreachable listener addresses.

### Run in stages

Keep Kafka and MongoDB running. Use separate terminals, all starting at the repository root. The dedicated Python executable below selects the Flink environment without changing your main `.venv`.

First inspect Flink's output in the console:

```bash
unset FLINK_HOME
docs/Training/Week4/3.1-wed-flink-weather/.venv/bin/python docs/Training/Week4/3.1-wed-flink-weather/consumer.py --sink console
```

The job reads retained records from the beginning, so existing events may appear immediately. For fresh events, keep your existing producer running in another terminal:

```bash
.venv/bin/python docs/Training/Week4/2.3_Tue_HW/producer.py
```

The producer sleeps for 60 seconds between complete rounds of API calls. A faster processing engine does not make the weather API produce observations faster. Expect a JVM startup delay, then output records containing `temperature_f`, `weather_status`, and Kafka metadata. Stop the console job with Ctrl-C, then run the MongoDB path:

```bash
unset FLINK_HOME
docs/Training/Week4/3.1-wed-flink-weather/.venv/bin/python docs/Training/Week4/3.1-wed-flink-weather/consumer.py --sink mongodb
```

This creates a `processed_at` descending index and upserts into `flink_streaming.weather`. Inspect it in your existing MongoDB shell:

```bash
docker exec -it week4-mongo mongosh
```

```javascript
use flink_streaming
db.weather.countDocuments()
db.weather.find({}, { _id: 0 }).sort({ processed_at: -1 }).limit(5)
db.weather.getIndexes()
```

Run the dashboard with your main repository environment, which already has Streamlit, pandas, and PyMongo:

```bash
.venv/bin/python -m streamlit run docs/Training/Week4/3.1-wed-flink-weather/dashboard.py --server.port 8502
```

Open `http://localhost:8502`. This separate port lets your Tuesday dashboard remain available on 8501. The page refreshes every two seconds while the session is active, displays three metrics, temperature over time, humidity by city, and recent records with Kafka metadata. Charts and city metrics use the most recent 500 materialized records; the total count covers the collection. The chart uses the producer's fetch timestamp, not the weather observation timestamp. The materialization timestamp shows when Python wrote the record after receiving it from Flink.

### Flink APIs used in this example

| API or option | What it does | Connection to your Spark experience |
| --- | --- | --- |
| `EnvironmentSettings.in_streaming_mode()` | Select streaming execution for an unbounded input | Similar intent to using `readStream` rather than a batch read |
| `TableEnvironment.create(...)` | Create the entry point for Flink tables and SQL | Similar role to the SQL interface on a Spark session |
| `get_config().get_configuration()` | Access job configuration | Comparable to setting engine options |
| `pipeline.jars` | Load the Kafka JVM connector from its file URI | Similar purpose to supplying connector packages to Spark |
| `parallelism.default` | Set the default number of parallel operator instances | Not the same thing as Kafka partition count |
| `execute_sql("CREATE TABLE ...")` | Register the source schema, formats, and connector settings | Declares how Kafka bytes become typed columns |
| `STRING`, `DOUBLE`, `INT`, `BIGINT` | Define SQL field types | Comparable to your Spark `StructType` fields |
| `METADATA ... VIRTUAL` | Expose Kafka topic, partition, and offset as columns without treating them as JSON fields | Comparable to preserving metadata from Spark's Kafka source |
| `key.format = raw` | Decode your producer's plain UTF-8 city key | The key is not a JSON object |
| `value.format = json` | Decode the JSON event value using declared types | Comparable to `from_json` with a schema |
| `value.fields-include = EXCEPT_KEY` | Keep the key-only column out of the JSON value schema | The producer's key lives outside the JSON value |
| `sql_query(...)` | Build a table query without executing it yet | Similar to constructing a transformation plan |
| `execute_sql("SELECT ...")` | Submit a continuous SQL query and return a `TableResult` | Starts the query; it does not wait for an infinite stream to finish |
| `ROUND(...)`, `CASE ...`, `WHERE` | Transform and filter inside Flink's JVM SQL operators | Comparable to `withColumn` and `filter` |
| `TableResult.collect()` | Return a closeable iterator over arriving result rows | A local client bridge, not a scalable distributed sink |
| `row.as_dict()` | Convert a result row to a Python dictionary | Prepares values for the MongoDB client |
| `get_job_client().cancel()` | Request cancellation of the submitted job | Cleanup when the local consumer exits |

The script does not use a Python UDF for the arithmetic: Python declares SQL and the Flink JVM executes the transformation. The Python iterator receives results afterward. At scale, repeatedly sending all results back to one Python client creates a throughput bottleneck.

### Other Flink APIs you will encounter

Flink offers Table API/SQL for declarative relational operations and DataStream APIs for explicit per-record logic, keyed state, timers, and custom operators. Learn which API an example is using before copying calls between examples.

| DataStream concept/API | Purpose |
| --- | --- |
| `StreamExecutionEnvironment.get_execution_environment()` | Create a DataStream execution environment |
| `KafkaSource.builder()` | Configure a Kafka source with topics, group, starting offsets, and deserialization |
| `env.from_source(...)` | Attach a source and watermark strategy to the graph |
| `map(...)` | Transform each record |
| `filter(...)` | Keep records that satisfy a condition |
| `key_by(...)` | Partition downstream work by a business key so keyed state is associated with that key |
| `process(...)` | Implement logic that can access context, state, and timers |
| `WatermarkStrategy.for_bounded_out_of_orderness(...)` | Define an event-time progress policy that tolerates a chosen amount of disorder |
| `with_timestamp_assigner(...)` | Extract each record's event timestamp |
| `with_idleness(...)` | Stop silent source partitions from indefinitely holding back watermark progress |
| `env.enable_checkpointing(...)` | Enable periodic coordinated snapshots of engine/source state |
| `env.execute(...)` | Submit a DataStream job |

A Kafka message key determines Kafka partition routing. Flink `key_by(city)` determines downstream keyed operator routing. These are different stages, even if both use the same city value.

## Flink versus Spark Structured Streaming

Flink is designed around pipelined stream processing: operators can process records as they arrive rather than waiting for the next scheduled micro-batch. Spark Structured Streaming commonly uses micro-batches. That makes Flink a useful choice for low latency stateful applications, but "one message at a time" does not mean there is no network buffering, connector buffering, parallel processing, or sink batching. Actual latency depends on the whole pipeline. Your dashboard's two-second refresh and producer's one-minute polling can dominate what you see on screen.

Choose an engine based on event-time semantics, state size, recovery requirements, supported connectors, team skills, and measured throughput/latency. This lab does not establish a performance comparison between engines.

## Watermark strategy: what does it mean?

Event time is when an event happened according to its source. Processing time is when an operator processes it. Arrival order can differ from event-time order. A watermark is the engine's estimate of event-time progress: it tells downstream operators when they can consider an event-time interval sufficiently complete under the configured policy.

For example, after observing a maximum event timestamp of 10:00:20, a bounded disorder policy of five seconds can advance a watermark to approximately 10:00:15. A window ending at 10:00:10 may then be eligible to emit its result. This is an assumption about tolerated disorder, not a guarantee that older events cannot arrive. Late-event behavior depends on the window/operator and its configuration.

Across active input partitions, downstream watermarks generally follow the slowest input. A partition with no assigned cities may hold progress back; idleness detection lets the engine exclude a silent input after a configured period. Choose that period with your 60-second polling interval in mind. A watermark does not create records, make API calls faster, commit MongoDB writes, or act as a checkpoint.

The supplied consumer performs per-record transformations without event-time windows, so it intentionally needs no watermark strategy. Add timestamps and watermarks when you introduce event-time windows or temporal operations. Example SQL shape for a future exercise, not an extra table executed by this script:

```sql
-- Existing producer emits UTC ISO timestamps, e.g. 2026-09-30T15:51:23.159240+00:00.
-- This expression uses the UTC calendar portion and truncates to whole seconds.
event_ts AS TO_TIMESTAMP(REPLACE(SUBSTRING(event_time, 1, 19), 'T', ' ')),
WATERMARK FOR event_ts AS event_ts - INTERVAL '5' SECOND
```

The expression assumes the producer keeps emitting UTC; it is not a general parser for arbitrary offsets. For a production contract, prefer an unambiguous timestamp representation such as epoch milliseconds converted with `TO_TIMESTAMP_LTZ(..., 3)` and an explicit time-zone policy. Open-Meteo's observation timestamp and this producer's fetch timestamp describe different facts.

## Failure model, replay, and delivery guarantees

This local example uses `earliest-offset` on every new launch. It reprocesses all retained Kafka records; it does not restore a durable Flink checkpoint or resume from MongoDB. Kafka retention bounds what can be replayed. The distinct group name prevents this consumer from sharing assignment with another Flink instance using the same group; your Spark pipeline can read the same topic independently.

MongoDB `_id` is `topic:partition:offset`. `replace_one(..., upsert=True)` inserts a new record or replaces the document with that identity. Replaying the same Kafka occurrence therefore does not increase the collection count. `processed_at` changes on replay, which is why the dashboard orders its temperature chart by producer fetch time. This identity does not deduplicate two separate Kafka records containing the same business event. Topic deletion/recreation can also reuse offsets; use a topic generation or durable business event ID for that lifecycle.

The Python MongoDB writer sits outside Flink's checkpoint protocol. This is not an end-to-end exactly-once sink. A client crash stops materialization; restart replays retained data. Invalid JSON fails the job rather than being silently ignored, while the SQL validity filter drops missing/invalid measurement rows without quarantine. Production ingestion should retain raw events or route rejected records to a dead-letter stream with reason and provenance.

The current query is append-only. If you add an unbounded `GROUP BY`, results can become a changelog containing updates and deletions rather than independent inserts. A simple result-row upsert keyed by Kafka offset is then insufficient; design aggregate identity and handling of row kinds, or use a compatible changelog sink.

## Data engineer considerations

- **State and scale:** Keyed aggregates, joins, deduplication, and windows retain state. Bound retention and measure state growth. Hot city/tenant keys can concentrate work even with many partitions.
- **Backpressure:** A slow MongoDB write blocks the single client iterator and can eventually slow the result pipeline. Monitor source lag, operator throughput, sink latency, and backlog rather than assuming "running" means "current".
- **Recovery:** Production Flink jobs need durable checkpoints, explicit restart policies, and a compatible sink. A checkpoint snapshots state and source positions; a savepoint is typically used for planned lifecycle operations such as upgrades. Recovery must restore the intended snapshot, not merely restart a script.
- **Connector compatibility:** Python package, JVM runtime, connector JAR, and Java versions must fit together. Spark's Kafka connector cannot be used as Flink's connector. The published Flink MongoDB connector compatibility should also be checked before selecting a native sink.
- **Serving and retention:** MongoDB is a derived query store here. Define indexes, retention, query limits, and rebuild policy. The 500-record dashboard is a bounded view, not a complete historical report.
- **Observability:** Track incoming/accepted/rejected events, source offsets and lag, end-to-end freshness, restarts, checkpoint failures, watermark lag, and state size. `processed_at` in this script measures materialization time; it does not measure all internal Flink processing latency.
- **Security:** The existing unauthenticated loopback MongoDB configuration is for local coursework. Deployments need authentication, TLS, network controls, and secrets outside source code.

## Virtual environment versus virtual machine

A Python virtual environment isolates Python executables and dependencies for a project. It shares the host OS and kernel and does not isolate Java, Docker, network ports, or system resources. That is why separate environments help with Python compatibility but do not fix a Docker Linux kernel incompatibility.

A virtual machine runs a guest operating system with its own kernel. Docker Desktop on macOS uses a Linux VM; containers run within that Linux environment. Containers share that VM's kernel rather than each having a separate kernel. Your PyFlink environment in this example is on the Mac, and its Kafka/MongoDB services are reached through Docker's published host ports.

## Knowledge check and completion evidence

You should be able to explain where JSON becomes typed rows, where the Fahrenheit calculation runs, why the Kafka key is decoded separately, why the dashboard needs MongoDB, what happens on replay, and when you would need watermarks. For a practical checkpoint, inspect one record's Celsius/Fahrenheit pair, match its Kafka metadata between console and MongoDB, and confirm that another poll becomes visible in the dashboard.

Both Python files passed Python syntax parsing, and the Markdown code fences are balanced. Files and setup instructions have been authored; dependency installation, Flink job execution, MongoDB materialization, dashboard rendering, recovery, and performance have not been validated for this example. Do not interpret this as a production sink or a measured engine comparison.

## Primary references

- [PyFlink 2.2 installation and supported Python versions](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/dev/python/installation/)
- [Flink releases and separately versioned connectors](https://flink.apache.org/downloads/)
- [Flink 2.2 Kafka SQL connector, formats, metadata, and startup offsets](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/table/kafka/)
- [Watermark generation, disorder, and idle inputs](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/dev/datastream/event-time/generating_watermarks/)
- [Flink checkpointing](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/dev/datastream/fault-tolerance/checkpointing/)
- [Streamlit fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)



# continued lecture notes

python -m venv docs/Training/Week4/3.1-wed-flink-weather/.venv
source docs/Training/Week4/3.1-wed-flink-weather/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r docs/Training/Week4/3.1-wed-flink-weather/requirements.txt

we are changing some direction towards a wallstreet money related thing
the teacher provided some code:

```python
import random
import time
from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(title="Synthetic Market Data API")

prices = {
    "AAPL": 225.00,
    "MSFT": 430.00,
    "NVDA": 185.00,
    "AMZN": 220.00,
    "GOOG": 195.00,
    "META": 710.00
}

sequence = 0


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@app.get("/tick")
def get_tick():

    global sequence

    sequence += 1

    symbol = random.choice(list(prices))

    # Random-walk price movement
    change = random.gauss(0, 0.04)

    prices[symbol] = max(
        1,
        prices[symbol] + change
    )

    # Simulate a small amount of exchange/network jitter
    network_delay_ms = random.randint(1, 8)

    exchange_ts = timestamp()

    time.sleep(network_delay_ms / 1000)

    return {
        "sequence": sequence,
        "symbol": symbol,
        "price": round(prices[symbol], 2),
        "size": random.choice([
            100, 100, 100,
            200, 500, 1000
        ]),
        "side": random.choice([
            "BUY",
            "SELL"
        ]),
        "exchange_ts": exchange_ts,
        "api_ts": timestamp(),
        "simulated_network_ms": network_delay_ms
    }
```


create the market topic:
bin/kafka-topics.sh
--bootstrap-server localhost:9092
--create
--topic market_ticks
--partitions 1
--replication-factor 1



```python
# market_consumer_spark.py
import json
import os
import time
from datetime import datetime, timezone

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    to_timestamp,
    current_timestamp,
    lit,
    unix_millis
)
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    StringType,
    DoubleType,
    IntegerType
)


# ============================================================
# Configuration
# ============================================================

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "market_ticks"

OUTPUT_FILE = "/tmp/spark-market.jsonl"
CHECKPOINT_DIR = "/tmp/spark-market-checkpoint"

# Deliberately large enough that students can SEE microbatches.
TRIGGER_INTERVAL = "2 seconds"


# ============================================================
# Spark
# ============================================================

spark = (
    SparkSession.builder
    .master("local[*]")
    .appName("Spark Market Streaming Demo")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")


# ============================================================
# Input schema
# ============================================================

schema = StructType([
    StructField("sequence", LongType(), True),
    StructField("symbol", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("size", IntegerType(), True),
    StructField("side", StringType(), True),

    StructField("exchange_ts", StringType(), True),
    StructField("api_ts", StringType(), True),
    StructField("kafka_ts", StringType(), True),

    StructField("simulated_network_ms", IntegerType(), True)
])


# ============================================================
# Kafka source
# ============================================================

raw = (
    spark.readStream
    .format("kafka")
    .option(
        "kafka.bootstrap.servers",
        KAFKA_BOOTSTRAP
    )
    .option(
        "subscribe",
        KAFKA_TOPIC
    )
    .option(
        "startingOffsets",
        "latest"
    )
    .load()
)


# ============================================================
# Parse Kafka JSON
# ============================================================

ticks = (
    raw
    .select(
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("timestamp").alias("kafka_broker_ts"),
        col("value").cast("string").alias("json")
    )
    .withColumn(
        "data",
        from_json(col("json"), schema)
    )
    .select(
        "kafka_partition",
        "kafka_offset",
        "kafka_broker_ts",
        "data.*"
    )
)


# ============================================================
# Microbatch processing
# ============================================================

def process_batch(batch_df, batch_id):

    if batch_df.isEmpty():
        return

    # --------------------------------------------------------
    # ONE timestamp is deliberately assigned to this batch.
    #
    # This makes the microbatch behavior obvious in the
    # dashboard: many records will acquire approximately the
    # same processing timestamp.
    # --------------------------------------------------------

    batch_processed_ts = datetime.now(timezone.utc)

    processed = (
        batch_df
        .withColumn(
            "processed_ts",
            lit(batch_processed_ts)
        )
        .withColumn(
            "engine",
            lit("spark")
        )
        .withColumn(
            "batch_id",
            lit(int(batch_id))
        )
        .withColumn(
            "exchange_timestamp",
            to_timestamp("exchange_ts")
        )
        .withColumn(
            "kafka_timestamp",
            to_timestamp("kafka_ts")
        )
        .withColumn(
            "processing_latency_ms",
            unix_millis(
                col("processed_ts")
            )
            -
            unix_millis(
                col("kafka_timestamp")
            )
        )
        .withColumn(
            "end_to_end_latency_ms",
            unix_millis(
                col("processed_ts")
            )
            -
            unix_millis(
                col("exchange_timestamp")
            )
        )
    )

    # Sort only for human-readable demo output.
    rows = (
        processed
        .orderBy("sequence")
        .collect()
    )

    # --------------------------------------------------------
    # Append this microbatch to the dashboard feed
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "a",
        buffering=1
    ) as f:

        for row in rows:

            record = row.asDict()

            # Convert Spark/Python datetime objects to strings.

            for field in [
                "kafka_broker_ts",
                "processed_ts",
                "exchange_timestamp",
                "kafka_timestamp"
            ]:

                if record.get(field) is not None:
                    record[field] = (
                        record[field].isoformat()
                    )

            f.write(
                json.dumps(
                    record,
                    default=str
                )
                + "\n"
            )

    count = len(rows)

    if count:

        first_sequence = rows[0]["sequence"]
        last_sequence = rows[-1]["sequence"]

        print(
            f"\n"
            f"SPARK MICRO-BATCH {batch_id}\n"
            f"Records: {count}\n"
            f"Sequence: "
            f"{first_sequence} -> {last_sequence}\n"
            f"Processed: "
            f"{batch_processed_ts.isoformat()}\n"
        )


# ============================================================
# Start streaming
# ============================================================

print()
print("=" * 60)
print("SPARK STRUCTURED STREAMING")
print("=" * 60)
print()
print(f"Kafka topic: {KAFKA_TOPIC}")
print(f"Trigger: {TRIGGER_INTERVAL}")
print(f"Output: {OUTPUT_FILE}")
print()
print(
    "Watch for groups of records appearing every "
    "2 seconds."
)
print()


query = (
    ticks.writeStream
    .foreachBatch(process_batch)
    .option(
        "checkpointLocation",
        CHECKPOINT_DIR
    )
    .trigger(
        processingTime=TRIGGER_INTERVAL
    )
    .start()
)


query.awaitTermination()

```


Now he's looking at how to use snowflake. so creating a snowflake consumer.

- any api related things i need to know about snowflake? like api? setup? how it relates to other technology we have covered so far. add this to a new file called 3.2_Wed_Snowflake.md


