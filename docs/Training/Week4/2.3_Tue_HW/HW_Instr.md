# Homework: Schema Evolution, MongoDB, Kafka, and Real-Time Dashboards

## Objective

This assignment reinforces the topics covered in class:

- Schema evolution
- Delta Lake schema evolution
- Avro schemas and serialization
- Protocol Buffers (Protobuf)
- NoSQL database concepts
- MongoDB
- Kafka consumers
- Spark Structured Streaming
- Writing streaming data to MongoDB
- Querying MongoDB
- Building a real-time Streamlit dashboard

You will complete both a **reading/research assignment** and a **technical assignment**.

---

# Part 1 – Reading and Research

Research the following topics. You should be prepared to discuss your answers in class.

### 1. Schema Evolution

Explain what **schema evolution** means and why it is important in a production data pipeline.

Research:

- Adding a new field
- Removing a field
- Changing a field's data type
- Renaming a field
- Backward compatibility
- Forward compatibility

Consider what might happen when a producer begins sending a new version of a schema while consumers are still expecting the old version.

**Answer:**

- **Schema evolution:** The controlled change of a data contract over time while producers, consumers, and stored data may use different versions. It matters because a change can break parsing or silently change the meaning of reports and applications.
- **Adding a new field:** Often manageable when it is optional, old readers tolerate unknown fields, and new readers tolerate older records where the field is missing.
- **Removing a field:** Can break consumers that still expect the field. Historical records may continue to contain it while newer records do not.
- **Changing a field's data type:** Can make parsing and calculations fail or produce unexpected conversions. Test how every reader handles the new type.
- **Renaming a field:** Usually acts like removing the old field and adding a new one. Support both names during a transition if old and new producers will overlap.
- **Backward compatibility:** Commonly means a newer reader can read data written with an older schema.
- **Forward compatibility:** Commonly means an older reader can read data written with a newer schema.
- **Producer and consumer versions:** Test the actual version combinations that will run. Define missing-value behavior and deploy consumers that tolerate the change before producers when needed.

### 2. Delta Lake

Research how Delta Lake handles schema changes.

In particular, explain:

- Schema enforcement
- Schema evolution
- `mergeSchema`
- `overwriteSchema`

What is the difference between **schema enforcement** and **schema evolution**?

**Answer:**

- **Schema enforcement:** Checks incoming data against the table's current schema and rejects incompatible writes.
- **Schema evolution:** Intentionally changes the table schema as the data changes.
- **`mergeSchema`:** Commonly used on a write to merge compatible new columns into the table schema. Older rows have no source value for a column that did not exist when they were written.
- **`overwriteSchema`:** Used with an overwrite operation to replace the existing table schema, such as during a planned schema replacement. Since an overwrite can replace table data, use it only when that replacement is intended.
- **Difference:** Enforcement checks data against the current contract; evolution changes the contract. Exact options and behavior depend on the Delta Lake version and operation.

### 3. Avro

Research how Avro stores and manages schemas.

Answer the following:

- Where is the Avro schema stored?
- What is an `.avsc` file?
- Does Avro require generated/compiled classes?
- How does Avro handle adding a new optional field?
- What are default values used for?
- Why is Avro commonly used with Kafka?

**Answer:**

- **Where the schema is stored:** It may be kept separately, embedded in an Avro object-container file, or retrieved for Kafka messages using a schema registry or another agreed method.
- **`.avsc` file:** A JSON file that describes an Avro schema, including record names, fields, and field types.
- **Generated vs. compiled classes:** Avro does not require generated classes. An application can read a schema at runtime and work with generic records. Code generation is an option: a tool generates source-code classes from the schema, and a language compiler then compiles that source into a form the program can run. “Generated” describes where the source came from; “compiled” describes turning source code into executable code.
- **Adding an optional field:** Add the field to the reader schema as a union that allows `null`, and give it a default such as `null`. When that reader reads an older record that has no such field, Avro's schema resolution supplies the default.
- **Default values:** Let a reader handle a field missing from older records. The default is supplied during schema resolution; it does not recover a value that was never written.
- **Avro schema vocabulary:** `type`, `name`, `fields`, and `items` are schema keywords with defined meanings. Values such as `record`, `array`, `string`, and `int` identify Avro types. Names such as `UserList`, `User`, `users`, `name`, and `age` are chosen for this example; they are not special Avro words.
- **Why Avro is used with Kafka:** It provides compact binary records and writer/reader schema resolution. A registry can help producers and consumers coordinate schema versions.

**Example:** This Avro schema describes a `users` array. Each item has a `name` string, an `age` integer, and an optional `email`. The `.avsc` schema is JSON; the second block is event data that follows the schema.

```json
{
  "type": "record",
  "name": "UserList",
  "fields": [
    {
      "name": "users",
      "type": {
        "type": "array",
        "items": {
          "type": "record",
          "name": "User",
          "fields": [
            { "name": "name", "type": "string" },
            { "name": "age", "type": "int" },
            {
              "name": "email",
              "type": ["null", "string"],
              "default": null
            }
          ]
        }
      }
    }
  ]
}
```

```json
{
  "users": [
    { "name": "Jason", "age": 40, "email": "jason@example.com" }
  ]
}
```

**Default value example:** Imagine an older writer used a schema with only `name` and `age`, and wrote this record:

```json
{
  "users": [
    { "name": "Jason", "age": 40 }
  ]
}
```

The newer reader schema above includes `email` with a `null` default. When Avro reads that old record using the newer reader schema, the resolved record has `email: null`:

```json
{
  "users": [
    { "name": "Jason", "age": 40, "email": null }
  ]
}
```

The default provides a value for the reader; it does not mean Jason's original email was known to the older writer.

### 4. Protocol Buffers

Research Protocol Buffers and `.proto` files.

Answer:

- What information is contained in a `.proto` file?
- What does `protoc` do?
- Why are Protobuf schemas normally compiled?
- What are field numbers?
- Why should an existing field number not be reused?
- How can Protobuf support schema evolution even though generated code may need to be regenerated?

**Answer:**

- **Information in a `.proto` file:** Message types, field names, field types, and unique field numbers.
- **`protoc`:** Compiles a `.proto` definition into language-specific code.
- **Generated vs. compiled code:** `protoc` generates source-code classes from the `.proto` file. A language compiler then compiles those generated classes into a form the program can run. 
- **Field numbers:** Identifiers for fields in the binary wire format. They are part of the message contract.
- **Why numbers should not be reused:** A reader could interpret old data as a different field. Reserve numbers from removed fields instead.
- **Adding an optional field:** In this proto3 example, `optional string email = 3;` allows the message to carry an email while tracking whether it was set. Older messages can omit the field; newer readers can still read them.
- **Default values:** Protobuf does not let you declare an arbitrary default for a proto3 field. An unset string reads as `""` (the empty string), an unset number as `0`, and an unset boolean as `false`. With `optional`, generated code also tracks whether the field was present, so the application can distinguish “not provided” from “provided as an empty string.”
- **Protobuf schema vocabulary:** `syntax`, `message`, `optional`, `repeated`, and type names such as `string` and `int32` are built-in Protobuf syntax. Names such as `User`, `UserList`, `users`, `name`, `age`, and `email` are chosen for this example. The field numbers (`1`, `2`, and `3`) are also chosen by the schema author, and must remain stable and unique within their message.
- **Schema evolution:** Adding a field with a new number is generally compatible because old readers can skip unknown fields. Updated application code must be generated to access the new field. Compatibility depends on the change and readers, so follow Protobuf's field and type rules.

**Example:** This `.proto` file defines a `UserList` message containing a repeated list of `User` messages. Each user has a name, age, and optional email. The text-format examples represent message values; applications encode these messages in Protobuf's binary wire format when sending them.

```proto
syntax = "proto3";

message User {
  string name = 1;
  int32 age = 2;
  optional string email = 3;
}

message UserList {
  repeated User users = 1;
}
```

```text
users {
  name: "Jason"
  age: 40
  email: "jason@example.com"
}
```

**Default value example:** An older message written before `email` was added contains only `name` and `age`:

```text
users {
  name: "Jason"
  age: 40
}
```

The newer reader can parse it. Its generated API reports that `email` is not present (`has_email` is false in languages with that accessor); reading the string value returns the default empty string, `""`. Because the field is `optional`, the application can distinguish this absent email from an email explicitly set to an empty string. Protobuf does not automatically fill in a custom value such as `"unknown@example.com"`.

### 5. Avro vs. Protobuf

Create a small comparison covering schema definition, compilation, schema evolution, human readability, Kafka usage, advantages, and disadvantages.

Be prepared to explain which format you would choose for a data engineering pipeline and **why**.

There is not necessarily one correct choice.

- **Schema definition:** Avro uses JSON in an `.avsc` file. Protobuf uses a `.proto` definition with numbered fields.
- **Compilation:** Avro generic records can use a schema at runtime without generated classes. Protobuf normally uses `protoc` to generate language-specific classes.
- **Schema evolution:** Avro resolves writer and reader schemas; reader defaults can handle fields missing in older data. Protobuf preserves field identity with numbers; use new numbers for added fields and reserve removed numbers.
- **Human-readable data:** Avro's schema is readable JSON, while its encoded records are usually binary. Protobuf's `.proto` file is readable text, while encoded messages are binary.
- **Typical Kafka usage:** Avro is common in data pipelines, often with a schema registry. Protobuf is common in service and event APIs and can also be used with Kafka.
- **Advantages:** Avro supports runtime schema resolution and convenient generic records. Protobuf provides generated types and broad language support. Both offer compact binary encoding.
- **Disadvantages:** Avro consumers need access to the writer schema, and registry tooling adds operational work. Protobuf requires code generation and careful field-number management; binary payloads are not directly readable.
- **Choice:** For an analytics pipeline with many consumers and retained events that may be replayed, I would consider Avro with a schema registry because writer/reader resolution fits that use. For a service ecosystem already using generated Protobuf APIs, Protobuf may be the simpler consistent choice. The team's tools, compatibility policy, and consumer requirements should decide; neither format is always best.

---

# Part 2 – NoSQL and MongoDB

Research the difference between relational and NoSQL databases.

Understand the following NoSQL categories:

- Document databases
- Key-value databases
- Wide-column databases
- Graph databases

For MongoDB specifically, explain:

- Database
- Collection
- Document
- `_id`
- BSON
- Index
- Compound index

Answer the following question:

> Why might a streaming application store processed events in MongoDB instead of immediately inserting them into a traditional relational database?

Consider scalability, schema flexibility, query patterns, and application requirements.

**Answer:**

- **Document databases:** Store related fields together in documents. This can fit an application that retrieves or displays each event as a whole.
- **Key-value databases:** Store values looked up by a key; useful when the application's access pattern is mainly a direct key lookup.
- **Wide-column databases:** Organize data around row or partition keys and columns; useful for some large, distributed workloads when queries are designed around those keys.
- **Graph databases:** Represent entities and their relationships; useful when queries need to traverse connections.
- **MongoDB and schema flexibility:** Documents in one collection can have different fields, which can make evolving events easier to ingest. Validation rules can still enforce a contract.
- **MongoDB and queries:** Indexes can support frequent lookups and sorts. Indexes add storage and write work, so choose them for actual query patterns.
- **Scalability:** MongoDB can scale through deployment designs suited to the workload, but it does not automatically scale better than a relational database.
- **When relational may fit better:** Applications that depend on transactions across related tables, relational constraints, or joins may be better served by a relational database.
- **Decision factors:** Consider event volume, consistency needs, query patterns, operational skills, and reporting requirements. Flexible schema does not remove the need to validate data.

**MongoDB terms:**

- **Database:** Groups collections.
- **Collection:** Groups documents.
- **Document:** A BSON record made of field/value pairs; fields can contain nested objects or arrays.
- **`_id`:** A unique identifier on every document. MongoDB generates one when an insert does not provide it.
- **BSON:** MongoDB's binary representation of JSON-like documents, with support for additional data types.
- **Index:** A data structure that helps MongoDB find or sort documents without scanning the entire collection; it uses storage and adds write work.
- **Compound index:** An index containing multiple fields in a defined order. Field order affects which query filters and sort patterns it can support efficiently.

---

# Part 3 – Technical Assignment

## Scenario

You have been asked to build a small real-time monitoring system.

Your architecture will be:

```text
Data Producer
      |
      v
    Kafka
      |
      v
Spark Structured Streaming
      |
      v
   MongoDB
      |
      v
  Streamlit
```

You may use the code from class as a starting point, but your final solution must make changes to the data being processed and the dashboard.

---

## Task 1 – Produce Streaming Data

Create or modify a Kafka producer that continuously sends JSON events.

You may use:

- A public API
- Weather data
- Financial/market data
- Transportation data
- Sports data
- Simulated IoT data
- Simulated application activity
- Another instructor-approved source

Real data is preferred where practical.

Each event must contain **at least five fields**.

For example:

```json
{
    "device_id": "machine-04",
    "temperature": 84.2,
    "pressure": 1013.4,
    "status": "running",
    "event_time": "2026-09-29T15:42:10"
}
```

At least one field should be useful as the **Kafka message key**.

---

## Task 2 – Kafka → Spark → MongoDB

Create a Spark Structured Streaming consumer.

Your program must:

1. Connect to Kafka.
2. Subscribe to your topic.
3. Parse the JSON message using a defined Spark schema.
4. Perform at least **one transformation** on the data.
5. Add a processing timestamp.
6. Write the processed records to MongoDB.

Examples of transformations include:

- Celsius → Fahrenheit
- Calculate total price
- Categorize a measurement
- Calculate message length
- Normalize a string
- Create an alert/status field
- Filter invalid records

Your MongoDB documents should retain the following Kafka information:

```text
key
partition
offset
```

along with the actual event data.

---

## Task 3 – Query MongoDB

Using `mongosh`, demonstrate that your streaming data was successfully stored.

Perform at least **three different queries**.

Your queries must include:

1. Retrieve recent documents.
2. Filter documents based on one of your fields.
3. Sort or limit the results.

Create at least **one index** appropriate for one of your queries.

Use:

```javascript
db.collection.getIndexes()
```

to verify that the index exists.

### Bonus

Use:

```javascript
.explain("executionStats")
```

to demonstrate whether MongoDB performs a:

```text
COLLSCAN
```

or:

```text
IXSCAN
```

for one of your queries.

---

# Part 4 – Real-Time Streamlit Dashboard

Create a Streamlit dashboard that reads from your MongoDB collection.

The dashboard must automatically refresh so that new Kafka events become visible without manually restarting the application.

Your dashboard must contain:

### Metrics

At least **three current metrics**.

Examples:

- Total events
- Average temperature
- Current price
- Number of active devices
- Average response time
- Maximum measurement

### Visualization

At least **two charts**.

At least one chart must show a measurement changing **over time**.

Examples:

```text
Temperature over time
Events per minute
Price over time
CPU utilization over time
Requests per minute
```

### Recent Events

Include a table showing recent events.

The table should contain relevant application data plus at least one Kafka field such as:

```text
partition
offset
```

---

# Part 5 – Schema Evolution Exercise

After your pipeline is working, modify the schema.

Add **one new field** to the events produced by your Kafka producer.

For example, change:

```json
{
    "device_id": "machine-04",
    "temperature": 84.2
}
```

to:

```json
{
    "device_id": "machine-04",
    "temperature": 84.2,
    "battery_level": 87
}
```

Update your consumer so the new field is recognized.

Then answer:

1. What happened to MongoDB documents created before the field existed?
2. Did MongoDB require you to alter the collection schema?
3. What would happen if the Spark schema were **not** updated?
4. How would this change be handled differently with Avro?
5. How would this change be handled differently with Protobuf?
6. How would a similar schema change be handled when writing to a Delta table?

---

# Deliverables

Submit **one ZIP file** containing:

```text
lastname_streaming_homework.zip

├── producer.py
├── consumer.py
├── dashboard.py
├── README.md
└── screenshots/
    ├── mongodb.png
    └── dashboard.png
```

### `README.md`

Include:

- Your Kafka topic name
- Description of your data source
- Description of your Kafka key
- Description of your Spark transformation
- MongoDB database and collection names
- Index you created and why
- Answers to the six schema-evolution questions from Part 5
- Your Avro vs. Protobuf comparison from Part 1

### `mongodb.png`

Provide a screenshot showing `mongosh` successfully querying records written by your Kafka/Spark pipeline.

The screenshot should clearly show multiple documents.

### `dashboard.png`

Provide a screenshot of your running Streamlit dashboard showing:

- At least three metrics
- At least two charts
- Recent event data

The screenshot must contain actual data produced by your pipeline.

---

# Minimum Success Criteria

A successful submission demonstrates the complete flow:

```text
Producer
   ↓
Kafka
   ↓
Spark Structured Streaming
   ↓
MongoDB
   ↓
Streamlit Dashboard
```

Your code does not need to be production-ready. The goal is to demonstrate that you understand how the components interact and can modify the examples from class rather than simply running them unchanged.
