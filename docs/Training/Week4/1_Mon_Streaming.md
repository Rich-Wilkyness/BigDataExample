# Monday: Streaming Data with Apache Kafka and Spark

> Status: Guided lecture notes
>
> Level: Beginner to intermediate
>
> Applies to: Event streaming, Apache Kafka, Python producers, and Spark Structured Streaming consumers
>
> Evidence: Technical claims were checked against Apache Kafka 4.3 and Apache Spark 4.2.0 documentation; four submitted videos had their identities, durations, and English caption-track availability checked; code syntax was checked, but no Kafka broker, Python producer, Spark query, connector download, failure test, or performance test was run
>
> Last reviewed: 2026-09

## Overview

Batch processing works with a bounded collection of data, such as yesterday's files or all orders created before midnight. Streaming processing works with data that can continue arriving while the application is running.

Streaming does not mean that every record must be processed instantly. It means the input is treated as an ongoing sequence and processed incrementally according to a latency target. A system might process each event immediately, collect small micro-batches every few seconds, or continuously update a result as new records arrive.

This lesson focuses on six practical questions:

1. What roles do producers, Kafka brokers, topics, and consumers play?
2. How do partitions, keys, offsets, and consumer groups affect ordering and parallelism?
3. How do replication, partition leadership, KRaft controllers, and rebalancing support distributed operation?
4. Why must records be serialized before Kafka can transport and store them?
5. How does Spark Structured Streaming read Kafka records and turn their bytes into typed columns?
6. What can fail, and what information allows a pipeline to recover safely?

## Learning objectives

After completing this guide, you should be able to:

- Distinguish batch processing from streaming processing.
- Trace an event from a producer through Kafka to a consumer and an output sink.
- Explain the purpose of a topic, partition, key, offset, broker, replica, leader, controller, and consumer group.
- State Kafka's ordering guarantee without implying global ordering across a topic.
- Explain why one consumer can own several partitions while extra consumers in the same group can be idle.
- Predict what causes a consumer-group rebalance and what work must transfer safely.
- Distinguish serialization from schema parsing and validation.
- Explain how Spark decodes Kafka's binary `key` and `value` columns and parses JSON with an explicit schema.
- Compare at-most-once, at-least-once, and exactly-once effects without treating them as broker-only guarantees.
- Describe how retention, offsets, checkpoints, retries, duplicates, lag, and backpressure affect recovery.
- Place Kafka appropriately in an IoT or global media architecture.
- Recognize which demo settings are unsafe or incomplete for production.

## Prerequisites

- Basic Python and JSON.
- Basic Spark DataFrame transformations and schemas.
- Basic understanding of distributed partitions from [Monday: Apache Spark Architecture, Execution, and Performance](../Week3/1_Mon_Spark.md).
- Docker Desktop for the recommended local broker path, or Java 17 or newer for the downloaded Kafka 4.3 distribution.
- A Kafka broker is required only for the live demo.

---

## 1. Streaming mental model

An event is a record of something that happened, such as an order being placed, a sensor reporting a temperature, or a customer viewing a product. A streaming pipeline keeps accepting new events instead of waiting for a complete dataset to exist.

```text
event source -> producer -> Kafka topic -> stream processor -> output sink
 mobile app      writes       retains        transforms       table, API,
 database        events       events          events           or another topic
 sensor
```

| Concept | Meaning |
| --- | --- |
| Bounded data | A dataset with a known end, such as one CSV file or one day's transactions |
| Unbounded data | A logical dataset that may continue receiving records |
| Event | A record describing something that happened |
| Producer | A client application that writes events to Kafka |
| Broker | A Kafka server that accepts, stores, and serves events |
| Consumer | A client application that reads events from Kafka |
| Stream processor | An application or engine that transforms, aggregates, joins, or routes events |
| Sink | The system that receives the processed result |

The words **real time** and **streaming** do not define a latency guarantee by themselves. A useful design states a measurable target, such as “95% of valid events are visible in the dashboard within 30 seconds.”

### Batch and streaming are complementary

| Question | Batch example | Streaming example |
| --- | --- | --- |
| When is input processed? | Every night at 1:00 a.m. | As new events become available |
| What is one unit of work? | A bounded dataset or time range | One event or a bounded micro-batch |
| Typical latency | Minutes to hours | Milliseconds to minutes |
| Recovery approach | Rerun a batch from a known boundary | Resume or replay from offsets and checkpoints |
| Common use | Daily reports and backfills | Monitoring, alerts, CDC, and live metrics |

Many production systems use both: streaming keeps results fresh, while batch backfills or reconciliations verify and repair historical results.

## 2. Choose the tool by responsibility

Several technologies appear in streaming architectures, but they do not all solve the same problem.

| Category | Examples | Primary responsibility |
| --- | --- | --- |
| Distributed event log and broker | Apache Kafka | Durably receive, partition, retain, and serve event records |
| Stream-processing engine or library | Spark Structured Streaming, Apache Flink, Kafka Streams | Transform, join, aggregate, and manage processing state |
| Managed Kafka service | Amazon MSK | Operate Kafka as a managed cloud service |
| Managed event or streaming service | Amazon Kinesis, Azure Event Hubs, Google Cloud Pub/Sub | Cloud-managed event ingestion and delivery with product-specific contracts |
| Message queue or broker | Amazon SQS, RabbitMQ | Deliver messages according to queue- or routing-oriented semantics |
| Messaging protocol | MQTT | Define lightweight publish/subscribe communication, commonly for IoT devices |

Do not classify SQS, RabbitMQ, or MQTT as merely “small Kafka.” They have different APIs, delivery models, routing behavior, retention contracts, and operational tradeoffs. The required guarantee should drive the choice.

## 3. Kafka's core components

### 3.1 Producer

A producer is application code that publishes events to Kafka. The producer chooses a topic and may provide a key that influences which partition receives the event.

The producer must decide:

- What one event represents.
- Which schema and serialization format to use.
- Which key preserves the required ordering or locality.
- What acknowledgement is required before a send counts as successful.
- How retries avoid or tolerate duplicate logical events.

### 3.2 Broker and cluster

A broker is one Kafka server. A production Kafka cluster normally contains multiple brokers so partitions can be distributed and replicated.

```text
Kafka cluster

Broker 1                 Broker 2                 Broker 3
P0 leader                P1 leader                P2 leader
P1 follower              P2 follower              P0 follower
```

Kafka is not merely an in-memory cache. It stores events in durable partition logs and can retain them independently of whether a consumer has read them. Retention is configured by time, size, or compaction policy; it is not only temporary storage for consumer failures.
- NOTE: the cache is serialized, so it's not directly queryable like a database

Kafka also is not a replacement for every database. Its native abstraction is an ordered partition log, not a relational table that supports arbitrary SQL queries, constraints, and transactional row updates. Kafka and databases commonly work together.


### 3.3 Topic and partition

A topic is a named stream of related events, such as `orders-created` or `sensor-readings`.

Each topic is divided into one or more partitions. A partition is an ordered, append-only log. Partitioning allows storage and processing to be distributed, but Kafka guarantees record order only within one topic-partition, not across every partition in the topic.

```text
topic: orders-created

partition 0: [offset 0] [offset 1] [offset 2]
partition 1: [offset 0] [offset 1]
partition 2: [offset 0] [offset 1] [offset 2] [offset 3]
```

An offset identifies a record's position within one partition. The pair `(topic, partition, offset)` identifies one Kafka record occurrence. It is not automatically the event's business identity: a retry may place the same logical event at another offset.
- TODO: please describe an offset in clearer terms

### 3.4 Consumer and consumer group

A consumer reads events from one or more topic partitions. Consumers normally join a consumer group so Kafka can divide partitions among the group's active members.

Within one consumer group:

- Each assigned partition has at most one active consumer owner at a time.
- One consumer can own multiple partitions.
- The number of actively useful consumers cannot exceed the number of partitions being consumed.
- If membership or subscriptions change, Kafka reassigns partitions in a process called a **rebalance**.

With 10 partitions, a group does **not** require exactly 10 consumers. One consumer could own all 10, five consumers could own two each, or 10 consumers could own one each. An 11th consumer in the same group would normally be idle for that subscription.

Different consumer groups maintain independent progress and can read the same events for different purposes:

```text
                         analytics group
                       / consumer A: partitions 0 and 1
orders-created topic --
                       \ consumer B: partition 2

                         fraud group
                       / consumer C: partitions 0, 1, and 2
```

If consumer B fails, its partitions must move to surviving consumers. Rebalancing provides fault tolerance and scaling, but assignment changes can pause or disrupt work. A dependable consumer must safely stop work for revoked partitions, preserve proven progress, transfer or restore state, and reject stale owners from writing after ownership changes.

Kafka 4.x supports both the newer consumer rebalance protocol and the earlier classic protocol. The exact timing and assignment behavior depend on the chosen client and protocol, so production designs should measure rebalance duration rather than assuming every rebalance is a full stop-the-world event.

### 3.5 Replicas, leaders, followers, and controllers

A replication factor states how many broker replicas Kafka should maintain for each partition. With a replication factor of three, one replica is the leader and the others follow its log.

```text
Producer and consumers
          |
          v
Broker 1: P0 leader
          |\
          | +------> Broker 3: P0 follower
          +--------> Broker 2: P0 follower
```

Producers send writes to the broker leading the relevant partition. Consumers normally fetch from the leader, although an explicitly configured replica-selection policy can support preferred read replicas. Followers copy the leader's log. Kafka tracks which replicas are sufficiently caught up in the in-sync replica set, or ISR. If the leader fails, the controller can elect an eligible replica as the new leader.

Replication improves availability and durability only when the complete configuration supports the claim. Replication factor, `acks`, minimum in-sync replicas, unclean leader election policy, failure count, and replica state all matter. A three-replica diagram alone does not prove that no acknowledged record can be lost.

In modern Kafka, **KRaft controllers** manage cluster metadata and partition leadership through Kafka's own metadata quorum. Brokers handle data requests; controllers handle metadata coordination. Kafka 4.x no longer requires an external ZooKeeper cluster.

## 4. Kafka, PostgreSQL, and Spark are different layers

The earlier PostgreSQL work provides a useful comparison, but the products are not direct equivalents.

| System | Main abstraction | Typical responsibility |
| --- | --- | --- |
| PostgreSQL | Tables and transactions | Store and query relational state |
| Kafka | Partitioned event logs | Retain and deliver ordered event records |
| Spark | Distributed computation and incremental tables | Read, transform, aggregate, and write data |

Spark Structured Streaming can consume records from Kafka, process them, and write to a sink such as a database, table, filesystem, console, or another Kafka topic. Kafka stores transport history; Spark performs computation; the sink serves or stores the processed result.

## 5. Keys, ordering, and parallelism

The producer's key is important because records with the same key are normally routed to the same partition under a stable partitioning configuration. This allows a consumer to observe those records in partition order.

For example, using `customer_id` as the key can keep one customer's order events together:

```text
customer 101 -> partition 2 -> order-created -> order-paid -> order-shipped
customer 205 -> partition 0 -> order-created -> order-cancelled
```

Keys may represent a vehicle, customer, account, device, order, or another entity whose events require locality or relative order.

Important limits:

- Kafka does not provide one global order across all partitions.
- A poor key can create a hot partition that receives much more traffic than the others.
- Adding partitions can change future key-to-partition routing.
- Partition order does not guarantee that event time is increasing; events may arrive late or out of order.
- A consumer can still create out-of-order external effects if it processes records concurrently without preserving the required key boundary.

Partitions therefore control both useful parallelism and the scope of ordering.

## 6. Serialization, deserialization, and schema

Kafka transports keys and values as bytes. Application objects must be converted to bytes before they are sent and reconstructed after they are read.

```text
Python dictionary
      |
      | JSON serialization + UTF-8 encoding
      v
Kafka bytes
      |
      | UTF-8 decoding + JSON parsing with a schema
      v
Spark columns
```

| Step | Example | Responsibility |
| --- | --- | --- |
| Serialize | Dictionary to JSON text | Define the wire representation |
| Encode | JSON text to UTF-8 bytes | Produce bytes for transport and storage |
| Decode | UTF-8 bytes to text | Recover a string from bytes |
| Parse | JSON text to typed fields | Apply the declared schema |
| Validate | Check required IDs, times, ranges, and versions | Decide whether the event is acceptable |

Serialization is similar to agreeing on a code for transmission, but it also requires an explicit schema contract. Two applications can both receive the same bytes and still disagree about field names, types, time zones, nullable fields, or schema versions.

Common formats include JSON, Avro, and Protocol Buffers. JSON is readable and convenient for a first demo; schema-aware binary formats can provide stronger compatibility controls and smaller encoded records. Organizations may use a schema registry to publish schema versions, compatibility rules, and identifiers, but a registry does not replace thoughtful producer/consumer rollout testing.

## 7. Progress, delivery, and recovery

Kafka retaining an event does not prove that the complete pipeline processed it exactly once.

```text
producer send -> broker append -> consumer read -> transformation -> sink write -> progress commit
```

Each arrow can fail independently. For example, a sink write may succeed just before the consumer crashes and records its progress. After restart, the event may be processed again. Production consumers therefore need stable event identity and idempotent or transactional sink behavior where duplicate effects are unacceptable.

| Concern | Question to answer |
| --- | --- |
| Acknowledgement | What does a successful producer send prove about broker storage and replication? |
| Offset | Which partition position has the consumer read or committed? |
| Checkpoint | Which source progress and processing state can the stream processor restore? |
| Retention | Will the required events still exist when a failed or slow consumer returns? |
| Consumer lag | How far is processing behind the end of each partition? |
| Backpressure | What happens when events arrive faster than the consumer or sink can process them? |
| Duplicate | Which stable event ID lets the sink recognize a retry? |
| Late event | Does the result update, reject, or ignore an event that arrives after its expected time window? |

For Spark Structured Streaming, the Kafka source exposes `key` and `value` as binary columns plus metadata such as topic, partition, offset, and timestamp. Spark tracks streaming progress in its checkpoint rather than relying on ordinary Kafka consumer offset commits. A checkpoint must have a stable, query-specific location and should not be casually deleted to fix a startup error.

### 7.1 Delivery semantics

| Term | Meaning | Main risk |
| --- | --- | --- |
| At-most-once | An event's effect occurs zero or one time | A failure can lose work |
| At-least-once | Work is retried so an event should not be lost | The event's effect can occur more than once |
| Exactly-once effect | The final observable effect converges as though each logical event were applied once | Requires compatible guarantees across identity, processing, progress, state, and sink commits |

“Kafka does not send duplicates” is not a valid explanation of exactly-once behavior. Producer retries, broker acknowledgement ambiguity, consumer restarts, offset or checkpoint commits, processing state, transactions, and the downstream sink all participate in the outcome. Kafka transactions can provide strong guarantees within supported Kafka read-process-write boundaries; an arbitrary database or external API side effect remains a separate commit boundary.

### 7.2 Backpressure and consumer lag

If Kafka receives 100,000 events per second while consumers complete only 70,000, the backlog grows by roughly 30,000 events per second. The difference between a partition's current log end and the consumer's proven position is commonly measured as consumer lag.

Growing lag is a symptom, not a root cause. Investigate:

- Whether incoming traffic or record size changed.
- Which partitions are behind and whether one key is hot.
- Whether consumer CPU, memory, garbage collection, or network is saturated.
- Whether a database, API, state store, or other sink is slow.
- Whether rebalances or failures repeatedly interrupt progress.
- Whether more consumers would help or would simply move the bottleneck downstream.
- Whether retention provides enough time to recover and catch up.

Lag in record count should be paired with event-time or ingestion-time age. Ten large or expensive records may be more serious than thousands of tiny records, and zero lag does not prove that the sink published correct results.

## 8. Local Kafka command-line demo

These commands use Apache Kafka 4.3.1 and KRaft. Choose either the Docker path or the downloaded-distribution path; do not start both on port `9092`.

A classroom demonstration that starts ZooKeeper first is using an older Kafka 3.x-era configuration. Kafka 3.9 was the final major release that included deprecated ZooKeeper mode. Kafka 4.x supports KRaft only.

### 8.1 Start one local broker with Docker

The official Kafka image provides the shortest setup for this lesson:

```bash
docker pull apache/kafka:4.3.1

docker run -d \
  --name kafka \
  -p 9092:9092 \
  apache/kafka:4.3.1

docker ps
```

This is a single broker with local container storage. It demonstrates client connectivity, topics, partitions, and records; it does not demonstrate multi-broker replication or durable recovery after the container is removed.

### 8.2 Alternative: start the downloaded Kafka distribution

Run these commands from the extracted Kafka directory. The `.sh` scripts work in Unix-like shells, including macOS and Linux; Kafka supplies Windows scripts separately.

The formatting command initializes local broker metadata and storage. Run it only when creating the local Kafka environment, not every time an already-formatted broker restarts.

```bash
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
bin/kafka-storage.sh format --standalone -t "$KAFKA_CLUSTER_ID" -c config/server.properties
bin/kafka-server-start.sh config/server.properties
```

The server occupies that terminal until it is stopped. Open another terminal for client commands.

### 8.3 Create and inspect a topic

This learning topic uses three partitions and a replication factor of one because only one local broker is running. A replication factor of one does not demonstrate broker-failure tolerance.

For Docker:

```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh \
  --create \
  --topic jokes \
  --partitions 3 \
  --replication-factor 1 \
  --bootstrap-server localhost:9092

docker exec kafka /opt/kafka/bin/kafka-topics.sh \
  --describe \
  --topic jokes \
  --bootstrap-server localhost:9092
```

For a downloaded distribution, run the same commands with `bin/kafka-topics.sh` instead of `docker exec kafka /opt/kafka/bin/kafka-topics.sh`.

`--bootstrap-server` supplies an initial broker address so the client can discover the cluster. Kafka clients use Kafka's network protocol over TCP; this is not an HTTP or WebSocket URL.

### 8.4 Test with the console clients

Start the Docker consumer in one terminal:

```bash
docker exec -it kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic jokes \
  --from-beginning
```

Start the Docker producer in another terminal:

```bash
docker exec -it kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic jokes
```

Each line typed into the producer becomes an event, and the consumer prints the events it reads. Stop either client with `Ctrl-C`. For a downloaded distribution, replace the Docker command prefixes with the corresponding `bin/...` scripts.

## 9. Illustrative Python producer

This example fetches a record from an HTTP API, adds an ingestion timestamp, serializes the dictionary as JSON, and sends it to Kafka once per second.

The repository does not currently declare `kafka-python` or `requests` as dependencies. If this demonstration becomes a runnable repository artifact, add pinned versions to a dedicated optional dependency group instead of installing untracked global packages.

```python
import json
import time
from datetime import datetime, timezone

import requests
from kafka import KafkaProducer


producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    key_serializer=lambda key: key.encode("utf-8"),
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    acks="all",
)

try:
    while True:
        response = requests.get(
            "https://api.chucknorris.io/jokes/random",
            timeout=10,
        )
        response.raise_for_status()
        joke = response.json()

        event = {
            "joke_id": joke["id"],
            "joke": joke["value"],
            "event_time": datetime.now(timezone.utc).isoformat(),
        }

        metadata = producer.send(
            "jokes",
            key=event["joke_id"],
            value=event,
        ).get(timeout=10)

        print(
            f"sent partition={metadata.partition} "
            f"offset={metadata.offset} joke_id={event['joke_id']}"
        )
        time.sleep(1)
except KeyboardInterrupt:
    print("producer stopped")
finally:
    producer.flush()
    producer.close()
```

The HTTP request retrieves the source data; it is not how the producer connects to Kafka. `bootstrap_servers` identifies the Kafka broker. Calling `.get(timeout=10)` waits for the send result so an error is visible during the demo. A production producer would also define bounded retry, rate, schema, security, and error-handling policies.

## 10. Illustrative Spark Structured Streaming consumer

Spark reads Kafka records as rows containing binary `key` and `value` columns plus Kafka metadata. Casting a binary value to `STRING` decodes the bytes. `from_json()` then parses that string according to the declared schema.

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T


spark = SparkSession.builder.appName("week4-kafka-jokes").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

json_schema = T.StructType(
    [
        T.StructField("joke_id", T.StringType(), nullable=False),
        T.StructField("joke", T.StringType(), nullable=False),
        T.StructField("event_time", T.StringType(), nullable=False),
    ]
)

raw_events = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "jokes")
    .option("startingOffsets", "earliest")
    .load()
)

decoded_events = raw_events.select(
    "topic",
    "partition",
    "offset",
    F.col("key").cast("string").alias("event_key"),
    F.col("value").cast("string").alias("value_json"),
)

events = (
    decoded_events
    .withColumn("event", F.from_json("value_json", json_schema))
    .select(
        "topic",
        "partition",
        "offset",
        "event_key",
        F.col("event.joke_id").alias("joke_id"),
        F.col("event.joke").alias("joke"),
        F.to_timestamp("event.event_time").alias("event_time"),
    )
    .withColumn(
        "is_valid",
        F.col("joke_id").isNotNull()
        & F.col("joke").isNotNull()
        & F.col("event_time").isNotNull(),
    )
)

query = (
    events.writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", "false")
    .option("checkpointLocation", "data/checkpoints/week4-jokes-console")
    .start()
)

try:
    query.awaitTermination()
finally:
    query.stop()
    spark.stop()
```

The console sink is for learning and debugging, not durable production output. This example marks invalid rows but does not yet publish them to a protected rejection sink. It also does not prove end-to-end exactly-once behavior.

For the repository's pinned Spark 4.2.0 and Scala 2.13 runtime, save the code as a Python file and include the matching Kafka connector at submission time:

```bash
spark-submit \
  --master 'local[2]' \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0 \
  path/to/stream_consumer.py
```

The connector version must match the Spark and Scala runtime. Mixing a Spark 3.5 connector with this repository's Spark 4.2.0 environment can produce dependency or binary-compatibility failures.

`startingOffsets="earliest"` applies when a new query starts. After a compatible checkpoint exists, Spark resumes from checkpointed progress. Use a new checkpoint path when intentionally starting a separate query; do not let unrelated queries share one.

## 11. Recommended demo startup order

1. Start the Kafka broker and leave it running.
2. Create and describe the `jokes` topic.
3. Use the console producer and consumer to prove the broker and topic work.
4. Start the Spark consumer with the matching connector.
5. Start the Python producer.
6. Confirm that Spark prints the parsed event and Kafka metadata.
7. Stop the producer with `Ctrl-C`, then stop Spark, then stop the broker.

If the demo fails, test one boundary at a time. First prove the broker is reachable, then the topic exists, then console clients work, then the Python producer works, and finally the Spark connector and query work.

## 12. Common pitfalls

### Pitfall: treating Kafka as a cache that stores records only until consumption

Kafka retention is independent of a particular consumer read. Consumers can replay retained records, and separate groups can read the same records independently.

### Pitfall: saying one partition requires one dedicated consumer

One active consumer in a group may own several partitions. The important limit is that one partition is assigned to at most one active consumer in the same group at a time.

### Pitfall: expecting global ordering

Kafka ordering is partition-scoped. Select a key that puts records requiring relative order into the same partition, then account for hot-key risk.

### Pitfall: treating an offset as a business event ID

An offset identifies a Kafka record occurrence within a partition. Preserve a stable event ID to detect logical duplicates across retries and replays.

### Pitfall: assuming replication factor alone proves durability

Replica count is only one part of the write contract. Test producer acknowledgements, minimum in-sync replicas, leader failure, and recovery with the selected configuration.

### Pitfall: hiding malformed input by dropping null parsed rows

Preserve topic, partition, offset, safe raw metadata, and a rejection reason in a controlled error path. Silent drops make reconciliation and repair difficult.

### Pitfall: deleting a Spark checkpoint to fix a query

The checkpoint contains recovery progress and may contain state. Preserve it for diagnosis, then start an intentional rebuild with an isolated checkpoint and output if compatibility cannot be restored.

### Pitfall: measuring only input records per second

A stream can read quickly while the sink is stale or incorrect. Monitor source lag, processing latency, invalid records, state size, checkpoint health, sink progress, and end-to-end freshness.

## 13. Production architecture examples

### 13.1 Automobile factory IoT

An automobile factory may contain thousands of robots, motors, and other machines that emit temperature, vibration, pressure, voltage, RPM, position, and error events.

```json
{
  "machine_id": "robot-187",
  "factory": "mexico-02",
  "temperature": 81.7,
  "vibration": 4.2,
  "event_time": "2026-09-28T20:30:00Z"
}
```

```text
factory floor                                  cloud or data center

sensor -> PLC/edge controller -> gateway -> regional ingestion -> Kafka
   |             |                                            /     \
   |             +-> immediate safety action        alert consumer   Spark/Flink
   |                                                                 /       \
   +------------------------------------------------ telemetry ----> metrics   data lake
```

The edge controller owns immediate machine-safety decisions because a robot cannot depend on a distant cloud round trip. Kafka carries telemetry for broader alerting, operational metrics, long-term analytics, and machine-learning datasets.

Using `machine_id` as the key can preserve order for one machine, but engineers must measure whether a small number of machines produce hot partitions. Separate consumer groups can independently alert operators, compute aggregates, and archive raw events.

### 13.2 Global video streaming service

Kafka normally carries **events about playback**, not the video bytes themselves. A content delivery network, or CDN, serves the video near the viewer, while application infrastructure publishes play, pause, buffering, search, and quality events.

```json
{
  "user_id": "98217",
  "video_id": "movie-551",
  "event_type": "buffering",
  "device": "smart_tv",
  "country": "BR",
  "duration_ms": 1800,
  "event_time": "2026-09-28T20:30:00Z"
}
```

```text
viewer device --------> nearby CDN ------------------------> video bytes
      |
      +---------------> regional API -> regional Kafka ---> playback events
                                                    |-----> operations alerts
                                                    |-----> warehouse metrics
                                                    |-----> recommendation features
                                                    +-----> security analysis
```

A global service may use regional ingestion and Kafka clusters instead of sending every event across the planet to one cluster. Cross-region aggregation or replication must respect latency, availability, cost, privacy, residency, and disaster-recovery requirements.

The producer publishes one governed event contract without knowing every downstream implementation. Consumer groups let operations, analytics, machine-learning, and security pipelines read independently at their own pace.

## 14. Production considerations

A production design should define:

- Stable event identity and a versioned schema.
- Topic ownership, access control, encryption, and secret handling.
- Partition key, count, replication, and expected skew.
- Producer acknowledgement, retry, timeout, and duplicate policy.
- Consumer-group ownership, offset or checkpoint policy, and rebalance behavior.
- Retention long enough to cover outages, catch-up, replay, and recovery.
- Event-time, late-data, window, and correction behavior.
- Idempotent or transactional sink behavior where duplicate effects matter.
- Backpressure limits for the broker, processor, state, and sink.
- Metrics and alerts for lag, throughput, failures, invalid records, checkpoints, and freshness.
- A tested replay, restore, reconciliation, schema-migration, and rollback procedure.

## 15. Homework: extend the streaming application

The coding portion is intentionally small. Adding one derived field requires a change at the producer's serialization boundary, the consumer's schema boundary, and the Spark transformation boundary without turning the assignment into another environment-setup exercise.

### 15.1 Starting pipeline

```text
REST API -> Python producer -> Kafka `jokes` topic -> Spark Structured Streaming -> console
```

Use the existing class `producer.py`, `consumer.py`, Kafka container, and topic. Do not create a new topic or redesign the pipeline. This assignment follows the instructor's class files, whose payload uses `joke` and `time`; do not rename those fields to match the illustrative examples in Sections 9 and 10 unless the instructor changes the contract.

### 15.2 Task

Modify the producer so every event contains a derived integer field named `joke_length`. Calculate it from the joke returned by the API; do not hard-code it.

The event should retain its existing fields and add the new one:

```json
{
  "joke": "Chuck Norris can divide by zero.",
  "time": 1790628000,
  "joke_length": 32
}
```

Then modify the Spark consumer so it:

1. Adds `joke_length` to the declared JSON schema.
2. Selects the new field with the existing fields.
3. Filters for jokes whose `joke_length` is greater than 100.
4. Displays `joke`, `time`, and `joke_length` in the console output.

### 15.3 Run and submit

Start the existing Kafka container if needed, then submit the consumer with the repository's matching connector:

```bash
docker start kafka

spark-submit \
  --master 'local[2]' \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0 \
  consumer.py
```

Submit the modified `producer.py` and `consumer.py`. Be prepared to explain where serialization, byte decoding, JSON parsing, schema application, and filtering occur. The lesson intentionally does not include the completed transformation.

## 16. Knowledge check

1. Why is Kafka better described as a durable partitioned log than as a cache?
2. With 10 partitions and 4 consumers in one group, how might partitions be assigned?
3. What happens to an 11th consumer in that same group?
4. What must happen when a consumer that owns a partition fails?
5. Can two different consumer groups read the same event? Explain why.
6. What is the strongest ordering guarantee you can make for a three-partition topic?
7. Why is `(topic, partition, offset)` not a replacement for `event_id`?
8. What are the roles of a partition leader, follower, and KRaft controller?
9. Why does a replication factor of three not prove an end-to-end no-loss guarantee by itself?
10. In the Spark example, which operation decodes bytes and which operation parses JSON?
11. What could happen if a sink write succeeds but the application fails before progress is recorded?
12. Why must Kafka retention exceed the time required to detect an outage and catch up?
13. Which measurements would distinguish a hot partition from a generally slow sink?
14. Why should a factory robot's emergency stop remain local instead of waiting for cloud streaming analytics?
15. Why should video bytes use a CDN while playback events may use Kafka?

## 17. Video review

Video identities and English caption-track availability were checked in 2026-09. All three retained videos exposed auto-generated English captions, but full transcript text was not reviewed, so their summaries below are based on publisher descriptions and chapter metadata. The unretained one-minute introduction exposed creator-provided English captions.

### 17.1 [What is Apache Kafka? — Confluent](https://www.youtube.com/watch?v=06iRM1Ghr1k)

This 11-minute overview introduces Kafka as a durable, scalable event-streaming platform and connects publish/subscribe, retained events, stream processing, metrics, log aggregation, and event sourcing. It is a concise conceptual companion to Sections 1–4.

**Important takeaway:** Kafka combines messaging with durable partition logs, so independent consumers can process or replay the same event history rather than requiring the producer to call every downstream system directly.

### 17.2 [Kafka Tutorial for Beginners — TechWorld with Nana](https://www.youtube.com/watch?v=QkdkLdMBuL0)

This beginner walkthrough uses an application-services example to motivate a broker, then covers Kafka's core concepts, partitions, consumer groups, brokers, message-broker comparisons, and the ZooKeeper-to-KRaft transition. Use it to reinforce the architecture in Sections 3–8.

**Important takeaway:** Kafka decouples producers from a growing set of consumers, but scaling and ordering still depend on deliberate partition keys, partition counts, and consumer-group design. Treat any setup commands in a video as version-specific and use this lesson's Kafka 4.3 commands for the current environment.

### 17.3 [Apache Kafka: What It Is and Where It's Going — Confluent Developer](https://www.youtube.com/watch?v=9CrlA0Wasvk)

This recent high-level overview places Kafka in modern data and application architectures. It is most useful after the factory and global-media examples because it emphasizes Kafka as shared event infrastructure rather than only a queue between two programs.

**Important takeaway:** A central event backbone can serve operational applications, analytical pipelines, and machine-learning consumers, but product vision does not replace exact evidence for retention, delivery, security, recovery, or cost guarantees.

The submitted [one-minute Apache Kafka Fundamentals introduction](https://www.youtube.com/watch?v=-DyWhcX3Dpc&list=PLa7VYi0yPIH2PelhRHoFR5iQgflg-y6JA) was not retained as a standalone lesson resource because it is a course introduction rather than substantive instruction. The surrounding playlist may still be useful for extended study.

## Key takeaways

- Streaming processes an ongoing sequence incrementally; it does not promise zero latency.
- Kafka producers write events, brokers retain partition logs, and consumers read those logs independently.
- Topics organize events; partitions provide parallelism and partition-scoped ordering; offsets track positions.
- Keys influence locality and ordering, while poor keys can create hot partitions.
- Replicas copy partition logs, leaders serve client data requests, and KRaft controllers manage cluster metadata and leadership.
- A consumer can own several partitions, extra consumers beyond the partition count are idle within the same group, and assignment changes require a safe rebalance.
- Kafka stores bytes, so producers serialize and consumers decode, parse, and validate against a schema.
- Kafka retention and Spark checkpoints make replay and recovery possible, but they do not automatically make external sink effects exactly once.
- Stable identity, idempotent writes, bounded capacity, observability, and tested recovery turn a demo into a dependable pipeline.
- Production architecture keeps time-critical control near its owner and uses Kafka to distribute governed events to independent consumers.

## Resources

- [Apache Kafka 4.3 introduction](https://kafka.apache.org/intro/) (reviewed 2026-09)
- [Apache Kafka 4.3 quickstart](https://kafka.apache.org/43/getting-started/quickstart/) (reviewed 2026-09)
- [Apache Kafka 4.3 design](https://kafka.apache.org/43/design/design/) (reviewed 2026-09)
- [Apache Kafka 4.3 topic configuration](https://kafka.apache.org/43/generated/topic_config.html) (reviewed 2026-09)
- [Apache Kafka 4.3 basic operations](https://kafka.apache.org/43/operations/basic-kafka-operations/) (reviewed 2026-09)
- [Apache Kafka 4.3 consumer rebalance protocol](https://kafka.apache.org/43/operations/consumer-rebalance-protocol/) (reviewed 2026-09)
- [Apache Kafka: KRaft and ZooKeeper differences](https://kafka.apache.org/43/getting-started/zk2kraft/) (reviewed 2026-09)
- [Spark 4.2.0 Structured Streaming programming guide](https://spark.apache.org/docs/4.2.0/streaming/index.html) (reviewed 2026-09)
- [Spark 4.2.0 Structured Streaming and Kafka integration](https://spark.apache.org/docs/4.2.0/streaming/structured-streaming-kafka-integration.html) (reviewed 2026-09)
- [Deeper curriculum: Kafka topics, partitions, offsets, and consumer groups](../../AI-Generated-Training/10-messaging-streaming-and-change-data-capture/02-kafka-topics-partitions-offsets-and-consumer-groups.md)
- [Deeper curriculum: delivery semantics, ordering, idempotency, and transactions](../../AI-Generated-Training/10-messaging-streaming-and-change-data-capture/04-delivery-semantics-ordering-idempotency-and-transactions.md)
- [Deeper curriculum: Spark Structured Streaming sources, sinks, and triggers](../../AI-Generated-Training/10-messaging-streaming-and-change-data-capture/07-spark-structured-streaming-sources-sinks-and-triggers.md)

## Completion checklist

- [ ] Explain the producer, broker, topic, partition, replica, leader, controller, consumer, processor, and sink roles.
- [ ] Predict consumer-group assignments for several partition and consumer counts.
- [ ] Explain serialization, decoding, parsing, and validation as separate steps.
- [ ] Compare delivery semantics across source progress and sink effects.
- [ ] Run the console producer and consumer against the local broker.
- [ ] Run the Python producer and confirm broker acknowledgements.
- [ ] Run the Spark consumer and identify key, value, topic, partition, and offset.
- [ ] Complete the `joke_length` homework without changing the topic or copying a completed transformation.
- [ ] Stop and restart the Spark query to inspect checkpoint recovery.
- [ ] Send malformed JSON and design a safe rejection path.
- [ ] Explain the different Kafka roles in the factory and global-video architectures.
- [ ] Explain what the local single-broker console demo does not prove about production durability, security, correctness, scale, or recovery.
