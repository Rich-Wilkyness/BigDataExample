# Tuesday: Schema Evolution in Data Pipelines

> Status: Guided lecture notes
>
> Level: Beginner to intermediate
>
> Applies to: Third-party APIs, Kafka events, batch files, analytical tables, and NoSQL source systems
>
> Evidence: Concepts checked against official Apache, MongoDB, AWS, Protocol Buffers, JSON Schema, and Delta Lake documentation; nine instructor scripts copied byte-for-byte and parsed for Python syntax; no Kafka, Spark, MongoDB, API, or dashboard runtime was exercised
>
> Last reviewed: 2026-09

## Overview

A **schema** describes the expected shape of data: field names, types, whether fields may be absent or null, and sometimes additional rules. **Schema evolution** is the process of changing that contract while old data and old software may still exist.

This matters whenever a third party changes an API response, an event producer deploys before its consumers, or a table gains a column. A change that looks harmless to the producer can break a consumer, especially when the consumer replays historical records. This lesson builds on [Monday's Kafka and Spark guide](1_Mon_Streaming.md), where a producer writes JSON bytes and Spark parses them with a declared schema. The [Tuesday instructor examples](2.1_Tue_Kafka_RTD/README.md) show the full classroom path from Kafka through Spark and MongoDB to a Streamlit dashboard.

After this lesson, you should be able to identify the owner of a data contract, predict which readers may break after a schema change, plan a rollout that handles both old and new records, and recognize how document, key-value, wide-column, and graph databases shape incoming data.

## 1. One event, several contracts

Suppose a third-party order API originally sends:

```json
{"order_id":"A-104","total_cents":2599}
```

Later, it begins sending:

```json
{"order_id":"A-105","total_cents":2599,"currency":"USD"}
```

The provider owns the source response. Your ingestion job owns how that response is validated and preserved. Your curated table owns the contract promised to downstream analysts. Those contracts can change at different times.

```text
third-party API -> raw response -> validated event -> curated table -> dashboard
   source owner      your copy       your contract     your schema     consumer
```

Keep enough of the original response and its source metadata to investigate a rejected record or replay it under a revised parser. Do not silently turn an unrecognized record into a successful one with missing values.

## 2. What can change?

| Change | Example | Likely effect to investigate |
| --- | --- | --- |
| Add an optional field | Add `currency` | An older reader may ignore it, but a reader that rejects unknown fields can fail. |
| Add a required field | Require `currency` | Historical records lack it; new readers need a default or an explicit migration rule. |
| Remove a field | Stop sending `total_cents` | Existing consumers that require it can fail or produce null results. |
| Rename a field | `total_cents` becomes `amount_cents` | Often behaves like removing one field and adding another unless a format or mapping explicitly supports aliases. |
| Change a type | `total_cents` changes from integer to string | Parsing, calculations, and storage writes may fail or coerce values unexpectedly. |
| Change meaning without changing type | `total_cents` starts including tax | Structural validation may pass while business results become wrong. |

An added column is therefore not automatically safe. The answer depends on the writer, the reader, the validation policy, and the older records that remain in files or Kafka retention.

### Missing, null, and default are different

In a JSON record, a missing `currency` key differs from `"currency": null`. A default such as `"USD"` is a business assumption, not a fact recovered from the missing record. If older orders could be in multiple currencies, inventing `USD` would corrupt revenue reporting. A safer rule might be to leave the value unknown and reject the record from currency-specific totals until the source can supply it.

## 3. Compatibility is about readers and writers

The **writer schema** describes what the producer writes; the **reader schema** describes what a consumer expects. You must test the pair in both directions that your rollout and replay actually require.

| Question | Why it matters |
| --- | --- |
| Can the new reader read old records? | A new deployment may replay historical data. |
| Can the old reader read new records? | Producers and consumers may run at different versions during rollout. |
| Can both readers produce the same business meaning? | Successful parsing does not guarantee correct totals or units. |

Some registries call the first direction **backward compatibility** and the second **forward compatibility**. Always state the actual reader/writer direction; the label alone is easy to misread.

For the order example, a safe additive rollout might be:

1. Agree that `currency` may be absent in older records and define how those records are handled.
2. Test the new reader on both versions of the event and test the existing reader on the new event.
3. Deploy consumers that tolerate the new field, then deploy the producer.
4. Monitor parse failures, rejected records, null rates, and downstream totals.
5. Require `currency` only after all relevant producers, consumers, and historical replay paths can meet that requirement.

If old consumers reject unknown fields, step 2 will expose the problem before the producer changes. If a later change removes `total_cents`, the team needs a planned migration, potentially supporting both names for a transition period.

## 4. JSON, Avro, Protocol Buffers, and Delta Lake

These names do not all refer to the same layer.

| Technology | Role here | Evolution point |
| --- | --- | --- |
| JSON | Text representation of an event or API response | JSON itself does not enforce a schema. A validator or consumer decides what fields and types it accepts. |
| JSON Schema | A way to describe and validate JSON documents | `required` and rules for additional properties change whether added or missing fields are accepted. |
| Avro | Schema-based serialization format | Reading can resolve a writer schema against a reader schema; a reader default can supply a field absent from older written records. |
| Protocol Buffers | Schema-based serialization format with numbered fields | Binary messages identify fields by number; adding a field is generally wire-safe, while reusing an old number can corrupt interpretation. |
| Delta Lake | Table format for files in a data lake | A table can enforce its schema or evolve it during a write when explicitly configured; this does not make an upstream event change safe for every consumer. |

For example, a Spark job might read a JSON event from Kafka, validate it, and write accepted rows to a Delta table. The JSON event contract governs the incoming message. The Delta table schema governs the stored rows. Updating the table schema cannot repair an event that the Spark parser never understood.

Avro and Protocol Buffers provide format-specific compatibility mechanisms, but neither can decide whether changing the meaning of `total_cents` is acceptable to finance. That decision belongs in the data contract and its consumer tests.

### What do Avro and Protocol Buffers schemas look like?

An Avro schema is commonly written as JSON. This example declares a record with a required string identifier and a nullable `currency` field whose reader default is `null`:

```json
{
  "type": "record",
  "name": "Order",
  "fields": [
    {"name": "order_id", "type": "string"},
    {"name": "currency", "type": ["null", "string"], "default": null}
  ]
}
```

The schema is JSON text; the event written with Avro's binary encoding is not simply a JSON object pasted after it. A reader needs the writer schema, or a reliable way to retrieve it, to interpret those bytes. Avro's writer/reader schema resolution is useful when data is stored for later batch processing or replay.

A Protocol Buffers schema uses a `.proto` definition. Field numbers are part of the binary wire contract:

```proto
syntax = "proto3";

message Order {
  string order_id = 1;
  string currency = 2;
}
```

An older binary reader can generally skip a newly added field, but a field number must not be reassigned to a different meaning. Neither format is universally “for big data” or “for applications”: Avro is common in data pipelines, while Protocol Buffers is common in service APIs, yet both can be used in either setting. Choose based on the systems that must read the data, compatibility needs, tooling, and operating constraints.

An `.avsc` file is a way to store an Avro schema definition separately. An Avro object-container file stores its writer schema in the file header; a bare Kafka value encoded as Avro needs an agreed method, such as a schema identifier and registry, to find the writer schema. Avro can read generic records using a schema without generating a class for every record type. A `.proto` file defines Protocol Buffers message types and field numbers; `protoc` generates code for the chosen language. After adding a field, old binary readers can generally ignore it, while applications that need to access the new field must use updated generated code.

### Schema enforcement and evolution in a Delta table

**Schema enforcement** checks whether incoming columns and types fit the table's current schema. **Schema evolution** changes the table schema through an authorized write or table operation. For example, an append with a new `currency` column can use a write-level `mergeSchema` option when supported; older rows then have no original currency value. `overwriteSchema` is different: it accompanies an overwrite that replaces the table data and schema, such as an intentional rename or type change. An overwrite can remove data and must not be used as a casual fix for an incoming API change. Delta Lake's support varies by version and operation, so check the selected runtime and test old readers before changing a table.

### Worked example: a field disappears between Kafka and MongoDB

The instructor's [weather producer](2.1_Tue_Kafka_RTD/weather_producer.py) includes `weather_code` in each JSON event. The [Spark consumer](2.1_Tue_Kafka_RTD/weather_consumer.py) declares a JSON schema without `weather_code` and selects only the parsed fields. As a result, the MongoDB document and [dashboard](2.1_Tue_Kafka_RTD/weather_dashboard.py) do not receive that field even though Kafka received it.

| Boundary | What happens to `weather_code` in the supplied scripts? | Where to verify |
| --- | --- | --- |
| API to producer | The producer reads `weather_code` from the API response. | Inspect `current["weather_code"]` in `weather_producer.py`. |
| Producer to Kafka | The serialized JSON message contains `weather_code`. | Inspect one produced message. |
| Kafka to Spark | `from_json` parses only fields in `json_schema`. | Compare the Kafka JSON with the parsed DataFrame schema. |
| Spark to MongoDB | The write uses the selected DataFrame fields. | Query a recent `streaming_demo.weather` document. |
| MongoDB to dashboard | The dashboard can only display fields present in its queried documents. | Inspect the dashboard's DataFrame columns. |

To introduce that field deliberately, first decide its type and meaning with the source owner. Then add it to the Spark parsing schema and selected output, test new events and old events that lack it, and decide whether the dashboard should display it. MongoDB can hold documents with different fields, but that flexibility does not add a field that Spark discarded. Keep the raw Kafka value or another replayable copy if you may need to recover fields omitted by an earlier parser.

The same exercise applies when a weather provider changes a number from Celsius to Fahrenheit without changing its JSON type: the parser may succeed while the dashboard is wrong. Record the unit, observation timestamp, and field definition in the contract; test meaning as well as shape.

## 5. Kafka message size is a configuration boundary

The phrase “1 MB maximum message” is a useful reminder that events should stay reasonably small, but it is not an absolute Kafka limit. Kafka 4.3's default broker `message.max.bytes` is about 1 MiB for a **record batch after compression**; a topic can override it with `max.message.bytes`. Producer, consumer, and replica fetch settings must also be compatible with the sizes you permit.

For a large image or file, a common design is to store the object elsewhere and put an identifier and location in Kafka. This avoids turning the event log into a bulk-file transfer path. Before changing a size limit, measure actual encoded record sizes and understand the effect on throughput, memory, replication, and recovery.

## 6. Recognize legacy Spark Streaming

Monday's examples use **Structured Streaming**, where Spark represents the stream as a DataFrame and runs an incremental query. Older Spark Streaming code uses **DStreams**, sequences of RDD-based micro-batches. You may encounter DStreams in an existing codebase or interview, but new coursework here uses Structured Streaming. These are different APIs; a DStream example cannot be copied directly into a `readStream`/`writeStream` query.

## 7. NoSQL databases as upstream sources

**NoSQL** is a broad label for data models other than the conventional relational model. It does not mean “no queries” or “no schema.” These systems can still define validation rules, indexes, keys, and consistency behavior. Their data can flow into Kafka, files, Spark, and analytical tables, where you must decide how to handle changing fields and relationships.

| Model | Examples | Useful mental model | Data-engineering consideration |
| --- | --- | --- | --- |
| Document | MongoDB, Amazon DocumentDB | Store related fields in one document; documents may vary in shape. | Preserve source document identity and validate fields before mapping them to a stable analytical schema. |
| Key-value and document | Amazon DynamoDB | Read items by primary key or an alternate key through a global secondary index (GSI). | Design access patterns around keys; a GSI is an index with its own key, not a relational join. |
| Wide-column | Apache HBase, Apache Cassandra | Organize large, distributed datasets around row or partition keys and columns. | Understand the key and data model before extracting rows; Cassandra's CQL resembles SQL syntax but does not make Cassandra a relational database. |
| Graph | Neo4j, Amazon Neptune | Represent entities and relationships for connected-data queries. | Exporting nodes and edges into tables requires preserving relationship identity and direction. |

MongoDB stores BSON documents and allows flexible document shapes; it can also enforce schema validation rules. A database contains collections, a collection contains documents, and each document has an `_id`. A single-field index supports queries on one field; a compound index can support queries using its leading fields, with field order affecting which queries it helps. Indexes speed selected reads but add write and storage work, so choose them for the queries the application actually runs. MongoDB also supports joining collections with the aggregation `$lookup` stage, so “MongoDB has no joins” is incorrect. Whether that join performs well depends on the query, indexes, and data distribution. Likewise, no database family is automatically faster than SQL databases: compare the actual workload and query plan.

These categories explain the source's structure, not a ranking of which product matters most. An operational document or key-value store may serve an application well while a separate analytical warehouse handles cross-entity reporting. In a historical example, [Pinterest Engineering described](https://medium.com/pinterest-engineering/sharding-pinterest-how-we-scaled-our-mysql-fleet-3f341e96ca6f) moving away from several newer storage technologies, including MongoDB, and scaling MySQL for its needs at the time. That experience illustrates how workload and operational maturity influence a choice; it does not establish that MongoDB cannot scale today.

## 8. The classroom real-time pipeline

The instructor examples show two paths. The first sends Chuck Norris jokes to the `test-topic` topic and either prints parsed events or writes them to MongoDB. The second sends weather observations to a separate `weather` topic; Spark parses and transforms them, writes micro-batches to `streaming_demo.weather`, and Streamlit queries that collection for charts. The standalone `real_time_dashboard.py` generates random data to demonstrate Streamlit controls; it is not connected to Kafka.

```text
Open-Meteo API -> weather_producer.py -> Kafka weather topic
                                         -> weather_consumer.py (Spark)
                                         -> MongoDB streaming_demo.weather
                                         -> weather_dashboard.py (Streamlit)
```

The separate topic prevents the weather consumer from trying to parse joke records. Kafka retains the transport event; MongoDB holds the processed serving copy; Streamlit reads MongoDB rather than Kafka directly. The dashboard refreshes its fragment every two seconds while the session is active. Its event-count metric is a MongoDB document count, and its “latest” city record is selected by processing time, so describe those metrics accurately when interpreting a chart.

MongoDB queries and indexes are part of making the dashboard useful. Query recent documents by `processed_at`, filter by `city`, and inspect existing indexes before adding one for a repeated query. The [instructor-code guide](2.1_Tue_Kafka_RTD/README.md) gives exact read-only `mongosh` examples and host-side launch commands.

Streamlit suits this small Python classroom app. Other dashboard approaches include Grafana connected to an appropriate data source for operational time series, or a custom web app when interaction and serving behavior need more control. The choice depends on which store is queried, refresh needs, access controls, and who will maintain the UI; the dashboard should not make an unbounded scan of every historical event on each refresh.

The supplied `watermarking-demo-*` pair is a separate event-time illustration. It creates some deliberately late records and prints a watermark decision. Its local state file and Kafka offset commits do not form one atomic checkpoint, so use it to understand the idea of lateness, not as proof of fault-tolerant exactly-once processing.

## 9. A small contract exercise

You receive both example order events above from the same source. Your dashboard needs totals grouped by currency.

1. Mark which fields are present in both versions and which field exists only in the newer version.
2. Decide whether a missing `currency` may be defaulted, rejected, or recorded as unknown. Explain what evidence you would need from the provider.
3. Write one accepted-record rule and one rejected-record rule for the ingestion job.
4. Describe what an old dashboard would do if the provider renamed `total_cents` without warning.
5. Describe how you would test a new parser against both historical and current records before deployment.
6. Explain why changing a Delta table schema would not fix a JSON event that failed parsing before the table write.
7. If an event grows beyond Kafka's configured batch-size limit, what would you measure or change before increasing that limit?
8. Name one difference between MongoDB's document model and DynamoDB's key-based access model, and explain which source detail your ingestion job must preserve.
9. Find the field sent by the weather producer but absent from the Spark schema. Trace exactly where it stops appearing and state how you would test an updated consumer on older events.
10. Explain why the weather dashboard's document count and “latest” row may differ from Kafka's event count and the source's most recent observation.

There is no single universal default for the old currency field. The point is to make the assumption explicit, testable, and visible to consumers.

## 10. Operational checklist

Before accepting a schema change, record the producer and consumer owners, sample records from every version still in use, and the expected behavior for missing, null, extra, and malformed fields. Test both deployment overlap and historical replay. Keep rejected records and reasons available for inspection without exposing sensitive data. After rollout, monitor rejection counts and business-level results, not only successful parses.

## References

- [Apache Avro specification: schema resolution](https://avro.apache.org/docs/1.12.0/specification/)
- [Protocol Buffers: updating a message type](https://protobuf.dev/programming-guides/proto3/#updating)
- [JSON Schema: object properties and required fields](https://json-schema.org/understanding-json-schema/reference/object)
- [Delta Lake: schema enforcement and evolution](https://docs.delta.io/delta-batch/)
- [Apache Kafka 4.3 broker configuration: `message.max.bytes`](https://kafka.apache.org/43/configuration/broker-configs/#brokerconfigs_message.max.bytes)
- [Apache Spark 4.2: legacy Spark Streaming API](https://spark.apache.org/docs/4.2.0/api/python/reference/pyspark.streaming.html)
- [MongoDB: schema validation](https://www.mongodb.com/docs/manual/core/schema-validation/) and [`$lookup`](https://www.mongodb.com/docs/manual/reference/operator/aggregation/lookup/)
- [Amazon DynamoDB: data models](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html) and [global secondary indexes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)
- [Apache HBase data model](https://hbase.apache.org/docs/datamodel/) and [Apache Cassandra overview](https://cassandra.apache.org/doc/stable/cassandra/architecture/overview.html)
- [Neo4j graph database concepts](https://neo4j.com/docs/getting-started/graph-database/)
- [Pinterest Engineering: sharding the MySQL fleet](https://medium.com/pinterest-engineering/sharding-pinterest-how-we-scaled-our-mysql-fleet-3f341e96ca6f)
- [MongoDB indexes](https://www.mongodb.com/docs/manual/core/indexes/create-index/) and [compound indexes](https://www.mongodb.com/docs/manual/core/indexes/index-types/index-compound/create-compound-index/)
- [Streamlit fragments and automatic reruns](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)
- [Grafana dashboards and refresh](https://grafana.com/docs/grafana/latest/visualizations/dashboards/use-dashboards/)
