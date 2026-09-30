# Tuesday instructor examples: Kafka, MongoDB, and real-time dashboards

These nine scripts were copied unchanged from the instructor's `kafka-rtd` download. They are reference material for [Tuesday's lesson](../2_Tue_.md) and [the Tuesday homework](../2.3_Tue_HW.md). Keep them separate from your own homework solution so the transformations and dashboard changes remain yours.

## Which scripts belong together?

| Demo | Producer | Consumer | Output |
| --- | --- | --- | --- |
| Chuck Norris console stream | `producer.py` | `consumer.py` | Spark console; Kafka topic `test-topic` |
| Chuck Norris to MongoDB | `producer.py` | `mongodb_consumer.py` | MongoDB `streaming_demo.jokes` |
| Event-time and watermark illustration | `watermarking-demo-producer.py` | `watermarking-demo-consumer.py` | Terminal output and local `checkpoint_state.json`; uses `test-topic` |
| Weather dashboard | `weather_producer.py` | `weather_consumer.py` and `weather_dashboard.py` | Kafka topic `weather`, MongoDB `streaming_demo.weather`, Streamlit page |
| Standalone dashboard sketch | None | `real_time_dashboard.py` | Randomly generated chart data; it does not read Kafka or MongoDB |

Run one producer/consumer pair at a time when using `test-topic`. The ordinary joke events contain `time`; the watermark demo expects `event_time`. Mixing those records can make the watermark consumer fail when it encounters an event without `event_time`.

## Environment and launch order

The scripts use `localhost:9092` for Kafka and `localhost:27017` for MongoDB. Run them on the Mac host when those services publish their ports to the host. The weather producer also needs access to the Open-Meteo API. Start Kafka and MongoDB before the Spark consumer, then start the producer, then the dashboard. Check the [Monday guide](../1_Mon_Streaming.md) for the local Kafka setup.

If MongoDB is not already running on host port `27017`, this local Docker example publishes the port only to the host and stores data in a named volume. Run these commands in a Mac terminal, not inside a container. Keep an existing MongoDB service instead if one is already listening on that port.

```bash
docker run -d --name week4-mongo -p 127.0.0.1:27017:27017 -v week4-mongo-data:/data/db mongo:8.0
docker exec -it week4-mongo mongosh
```

The first command starts the database; the second opens `mongosh` inside that container. Type `exit` to return to the Mac terminal. The instructor scripts still run on the Mac and reach MongoDB through the published host port.

If you used Monday's Docker broker named `kafka`, create the separate weather topic once and then describe it. If it already exists, skip the create command. The single local broker supports only replication factor one in this example.

```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --create --topic weather --partitions 3 --replication-factor 1 --bootstrap-server localhost:9092
docker exec kafka /opt/kafka/bin/kafka-topics.sh --describe --topic weather --bootstrap-server localhost:9092
```

From the repository root (`/Users/richardwilkerson/VSCodeProjects/BigDataExample`), activate the repository virtual environment and check that `spark-submit --version` reports PySpark 4.2.0. If an older standalone Spark installation is selected, `unset SPARK_HOME` before running `spark-submit`. The host-side Python scripts need `requests`, `kafka-python`, `pymongo`, `pandas`, and `streamlit`; the Spark consumer also needs the Kafka and MongoDB JVM connectors. Install missing Python packages into the chosen environment with `python -m pip install requests kafka-python pymongo pandas streamlit`.

For the weather path, use separate terminals after the environment is active in each one:

```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0,org.mongodb.spark:mongo-spark-connector_2.13:11.1.0 \
  docs/Training/Week4/2.1_Tue_Kafka_RTD/weather_consumer.py
```

```bash
python docs/Training/Week4/2.1_Tue_Kafka_RTD/weather_producer.py
```

```bash
streamlit run docs/Training/Week4/2.1_Tue_Kafka_RTD/weather_dashboard.py
```

MongoDB's [Spark connector compatibility table](https://www.mongodb.com/docs/spark-connector/current/) lists connector 11.1.0 for Spark 4.0 or later; its [getting-started guide](https://www.mongodb.com/docs/spark-connector/current/getting-started/) shows the Scala 2.13 artifact. The Kafka connector version matches this repository's PySpark 4.2.0 runtime. These launch commands have been checked against documentation, but the complete local pipeline has not yet been run here.

## Inspect MongoDB data

At a `mongosh` prompt connected to `localhost:27017`, choose the database and inspect the collection. These examples are read-only:

```javascript
use streaming_demo
db.weather.find({}, { _id: 0 }).sort({ processed_at: -1 }).limit(5)
db.weather.find({ city: "London" }, { _id: 0 }).sort({ processed_at: -1 }).limit(5)
db.weather.getIndexes()
```

The dashboard sorts recent weather records by `processed_at`. If you decide to create an index for that query, inspect existing indexes first and then use `db.weather.createIndex({ processed_at: -1 })`. Index creation changes MongoDB state and is intentionally left to the learner's exercise.

## Read these examples critically

- `weather_producer.py` fetches weather fields and includes `weather_code`, but `weather_consumer.py` does not declare `weather_code` in its Spark JSON schema; that field does not reach MongoDB. This is a concrete schema-evolution exercise.
- The weather producer labels its request time as `event_time`. The API's observation time, if available, is a different fact. Choose which one your dashboard should represent.
- The weather dashboard's “Kafka Events” metric counts MongoDB documents, not broker events. The dashboard selects the latest record per city by `processed_at`, which may differ from the latest weather observation time.
- The MongoDB consumers append each `foreachBatch` result. A retry or replay can insert duplicate logical events unless the sink uses a stable identity and idempotent write policy. Checkpoints track Spark progress; they do not make arbitrary MongoDB writes exactly once.
- `watermarking-demo-consumer.py` prints a checkpoint message every five records, but it also calls `consumer.commit()` for every record. Its local state-file write and Kafka offset commit are separate operations, so the script is a teaching illustration, not a reliable recovery protocol.
- `real_time_dashboard.py` uses random values and an infinite loop. It is a UI sketch; `weather_dashboard.py` is the script that queries MongoDB and refreshes with a Streamlit fragment.

The instructor files are preserved as supplied. Any improvement or homework adaptation should be made in a separate learner-owned copy.
