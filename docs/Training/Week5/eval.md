## Kafka
1. what is a kafka producer?
    - connects the data being generated with the kafka pipeline, this could come from a csv, avro, parque, sql database, hive, etc.
2. what is a kafka consumer?
    - does some sort of processing as data is being handed to it by the kafka broker and then storing it 
3. what is a topic in kafka?
    - the topic is the name assigned to a kafka pipeline
    - producer publishes to it and consumer subscribes to it
    - it stores the messages, but doesn't know what it is storing
    - topic can be partitioned, not the same as spark, with topic, it is partitioned according to schemas (Schema evolution), happens on the producer level, it can partition in other ways
    - each message is not a partition, we don't wait for messages to accumulate to partition
    - for example we don't want to wait for a single robot in a factory for 1 minute to store up its information, the partition would be more accurate to say, from a region of the factory, we collect all the heat related data and group them together
4. what is serialization? what is deserialization?
    - into bytes to send over some for of networking
    - bytes are 1 step from machine code, allows for sending a form of morse code.
5. what is zookeeper? why is it not used in more recent versions of kafka?
    - older cluster management system
    - not used anymore because the cluster manager is built into kafka called Kraft
6. what is the difference between a leader and a follower? what is the process called to select a new leader? 
    - it is part of fault tolerance. leaders and followers are created as replications on different nodes. the leader is the process we are actively using, but if a node fails for whatever reason a new leader is decided and that is called an election
7. what is the maximum size of a message in kafka? 
    - 1 MB

## Snowflake
8. what does it mean that snowflake is a unified data platform?

9. what is a virtual warehouse in snowflake?
    - resources (specifically the compute layer) that snowflake uses to process your data. the "cloud". 
10. what is the principle of cpu vs storage (he phrased it differently)
    - storage/disk scales independently of cpu/data processing
    - snowflake allows for dynamic scaling up or down of either dependent on pipeline needs
11. what is the role of dbt inside snowflake?
    - ELT
12. what is a model in dbt?
    - 
13. why is there a postgres option for a snowflake environemnt?
    - can use it to migrate data from postgres to snowflake (not what he was looking for, but technically true)
    - OLAP is what snowflake is, OLTP is what postgres is. postgres is used as an option to run certain processes that require OLTP
        - often with customer facing data, since this could be for a web interface 
14. what is time travel in snowflake? what are its advantages? 
    - audit, data recovery, or cloning from a certain time 

15. what is a dynamic table?
    - elt transformations will be reflected in the upstream tables
    - incremental load, 4 times a day, regular schema, 
    - all tables involed need to be marked dynamic
    - works like a cronjob to regularly check if data has changed, 
    - we load data into bronze, and then silver and gold data automatically get handled as well



# Main Eval

difference between list, set, dict, tuple

how does python garbage collection work?

shallow copy vs copy

decorators and generators, and when would you use them in relation to python

def findDuplicate(myList: list[str]) -> set[str]:
    seen = set()
    duplicate = set()

    for value in myList:
        if value in seen:
            duplicate.add(value)
        else:
            seen.add(value)

    return duplicate

map, flatMap, and foreach

val, var, and lazy val

case classes

pattern matching (match / case)

tell me about Hadoop high level
- YARN, HDFS, MapReduce

NameNode and DataNode

RDDs, DataFrames, and Datasets

narrow vs wide transformations.

difference between cache and persistence 

---

# Interview-ready answers

Your original questions, answers, and code above are preserved. Study the answers below; the original notes contain misconceptions corrected here. Each **Interview answer** is written to say aloud, while **corrections** and examples prepare you for follow-ups. The Main Eval prompts are numbered here in their original order.

Reviewed against primary documentation on 2026-10-12. Python memory answers assume CPython; collection operations assume Scala/Spark where indicated. Examples are illustrative unless the verification note says they were executed.

## Kafka answers

### 1. What is a Kafka producer?

**Interview answer**

A producer is a client application that publishes records to Kafka topics. It serializes record keys and values into bytes and sends records to a selected partition. A sensor application could publish temperature events to a `factory-temperature` topic.

**corrections**

- CSV, Avro, and Parquet are formats; databases and sensors are possible sources. A producer is the application publishing records, rather than the source or format itself.

### 2. What is a Kafka consumer?

**Interview answer**

A consumer is a client application that reads records from Kafka topics and tracks its position using partition offsets. It may process, store, or forward records. In a standard consumer group, consumers divide partitions between themselves; separate groups can independently read the same events.

**Likely follow-up**

- Committing an offset records progress; it does not delete the event. Kafka retention controls how long records remain available.

### 3. What is a topic in Kafka?

**Interview answer**

A topic is a named stream of records divided into partitions. Each partition is an ordered log that supports storage and parallel consumption. Ordering is guaranteed within a partition, not across the whole topic. Producers commonly use a key, such as `robot_id`, to route related events to the same partition.

**corrections**

- A topic is one part of a pipeline, rather than the name of the entire pipeline.
- Partitioning and schema evolution solve different problems: partitioning distributes records; schema evolution changes record structure compatibly.
- Partitions already exist when records arrive. Every record is assigned to a partition; a record is not itself a partition.
- With a stable key-based partitioning strategy and partition count, events for one robot go to the same partition. Changing the partition count can change that mapping.

Sources for questions 1–3: [Kafka introduction](https://kafka.apache.org/43/getting-started/introduction/) and [partition distribution](https://kafka.apache.org/43/implementation/distribution/).

### 4. What are serialization and deserialization?

**Interview answer**

Serialization converts an in-memory value into a byte representation suitable for transmission or storage. Deserialization interprets those bytes to reconstruct a usable value. Kafka producers serialize keys and values, and consumers deserialize them using a compatible format, such as JSON, Avro, or Protobuf.

**corrections**

- Bytes are units of data, not a stage before machine code. Serialized bytes usually represent data rather than executable instructions.
- Serialization is separate from compression and encryption.

**Example**

```python
import json

event = {"robot_id": "r1", "temperature": 72}
payload = json.dumps(event).encode("utf-8")
restored = json.loads(payload.decode("utf-8"))
assert restored == event
```

Source: [Python JSON encoding and decoding](https://docs.python.org/3/library/json.html).

### 5. What is ZooKeeper, and why do newer Kafka versions use KRaft?

**Interview answer**

ZooKeeper is a separate distributed coordination service that older Kafka clusters used for metadata and controller coordination. KRaft moves metadata management into Kafka using a Raft-based controller quorum. This removes the external ZooKeeper dependency and simplifies cluster operation. Kafka 4.0 and later require KRaft; ZooKeeper mode was removed.

**Likely follow-up**

- The controller quorum manages cluster metadata. It is separate from the leader and followers that replicate a topic partition's records.

Source: [Kafka 4.0 upgrade requirements](https://kafka.apache.org/40/getting-started/upgrade/).

### 6. What is the difference between a leader and a follower? How is a new leader selected?

**Interview answer**

Leadership belongs to each partition. One replica is its leader, which handles writes and normally serves reads; follower replicas copy its log. If the leader fails, the controller coordinates a partition leader election. Normally an eligible in-sync replica becomes leader, preserving committed data. Allowing an out-of-sync replica to lead can restore availability at the risk of data loss.

**corrections**

- A broker can lead some partitions and follow others. There is no single data leader for the whole Kafka cluster.
- Replicas are copies of partition logs on brokers, rather than copies of the entire application process.

Sources: [Kafka replication and design](https://kafka.apache.org/43/design/design/) and [unclean leader election configuration](https://kafka.apache.org/43/configuration/topic-configs/).

### 7. What is the maximum size of a Kafka message?

**Interview answer**

Kafka does not have a universal fixed 1 MB message limit. The default allowed record batch is roughly 1 MiB, but limits are configurable. Effective limits depend on producer request settings and broker or topic batch settings, with compatible consumer and replication fetch settings. For very large payloads, I would consider external object storage and publish a reference in Kafka.

**corrections**

- In Kafka 4.3, topic `max.message.bytes` defaults to `1,048,588` bytes and applies to a record batch after compression when enabled. That is not an exact maximum for an individual application's payload.
- Relevant settings include producer `max.request.size`, broker `message.max.bytes`, and topic `max.message.bytes`. Raising only one may leave another limit in place.

Sources: [Kafka topic limits](https://kafka.apache.org/43/configuration/topic-configs/) and [producer configuration](https://kafka.apache.org/43/configuration/producer-configs/).

## Snowflake and dbt answers

### 8. What does it mean that Snowflake is a unified data platform?

**Interview answer**

Snowflake brings data storage, processing, governance, and sharing into one managed platform. Teams can use shared, governed data for analytics and other workloads while assigning separate compute resources to different tasks. The benefit is less movement between disconnected systems and more consistent access control and data management.

**Likely follow-up**

- Unified does not mean every workload uses one database engine or one warehouse. Snowflake offers different capabilities for different access patterns.

Source: [Snowflake concepts and architecture](https://docs.snowflake.com/en/user-guide/intro-key-concepts).

### 9. What is a virtual warehouse in Snowflake?

**Interview answer**

A virtual warehouse is a compute cluster that executes queries and operations such as data loading. It provides CPU, memory, and local resources while persistent table storage is managed separately. Warehouses can be resized, suspended, and resumed, and separate warehouses help isolate workloads such as ingestion and reporting.

**corrections**

- A warehouse is a specific compute resource within Snowflake, rather than another name for the cloud or stored database.

**Likely follow-up**

- Scaling up increases a warehouse's size. Multi-cluster scaling adds clusters primarily to handle concurrent workloads; it does not automatically speed up one query.

Source: [Snowflake warehouses](https://docs.snowflake.com/en/user-guide/warehouses-overview).

### 10. What does separating compute and storage mean?

**Interview answer**

Separating compute and storage means the resources executing queries are independent from persistent data storage. In Snowflake, I can resize or suspend a warehouse without removing its tables. Multiple warehouses can query the same stored data, letting teams adjust compute capacity and isolate workloads without maintaining a separate copy for each warehouse.

**corrections**

- Storage grows with retained data; warehouse resizing changes compute capacity. Do not describe both as the same autoscaling mechanism.
- Suspending compute does not eliminate the cost of retained storage.

Source: [Snowflake architecture](https://docs.snowflake.com/en/user-guide/intro-key-concepts).

### 11. What is dbt's role when working with Snowflake?

**Interview answer**

dbt manages the transformation part of ELT. After data is loaded into Snowflake, dbt compiles models and executes transformations using Snowflake compute. It also manages dependencies, tests, and documentation, helping turn raw data into reliable analytical datasets. dbt defines and coordinates the transformation logic; Snowflake performs the database work.

**corrections**

- dbt is typically not the component extracting data from source systems or loading raw data into Snowflake.

### 12. What is a model in dbt?

**Interview answer**

A dbt model defines a dataset transformation. A SQL model is typically a `.sql` file containing a `SELECT` statement; dbt builds its result using a materialization such as a view, table, or incremental table. Using `ref()` to reference another model establishes a dependency so dbt can build models in the right order.

**Example**

```sql
-- Illustrative dbt SQL model: models/active_customers.sql
select customer_id, customer_name
from {{ ref('stg_customers') }}
where is_active = true
```

**Likely follow-up**

- `source()` references externally loaded source data; `ref()` references another dbt resource. A model is not necessarily a physical table, because its materialization determines how its result is represented.

Source for questions 11–12: [dbt SQL models](https://docs.getdbt.com/docs/build/sql-models).

### 13. Why is there a PostgreSQL option in a Snowflake environment?

**Interview answer**

If the question refers to Snowflake Postgres, it provides managed PostgreSQL for operational applications that need low-latency, concurrent transactional reads and writes. Snowflake's analytical warehouse serves a different access pattern: large scans and aggregations. A customer application might use Postgres for individual orders while the warehouse analyzes sales across all orders.

**corrections**

- The likely distinction is OLTP versus OLAP, rather than migration alone. PostgreSQL is general purpose and can also run analytics; these labels describe workload strengths.
- Snowflake Postgres is a separate managed PostgreSQL instance, not a mode of a virtual warehouse. Snowflake hybrid tables are another transactional feature, not PostgreSQL.
- If the interviewer means the PostgreSQL option in `dbt init`, that selects the database adapter dbt will target. It does not automatically provision Postgres or migrate data into Snowflake. Clarify which option they mean.

Sources: [Snowflake Postgres](https://docs.snowflake.com/en/user-guide/snowflake-postgres/about), [hybrid tables](https://docs.snowflake.com/en/user-guide/tables-hybrid), and [dbt adapters](https://docs.getdbt.com/docs/supported-data-platforms).

### 14. What is Time Travel in Snowflake, and what are its advantages?

**Interview answer**

Time Travel lets me query supported objects as they existed at an earlier point within their configured retention period. I can investigate changes, compare historical results, recover eligible dropped objects, and clone supported objects from an earlier state. It is useful for recovering from accidental changes and reproducing past analysis.

**corrections**

- Retention depends on edition, object type, and configuration; historical access is not unlimited.
- Historical data helps investigate changes, but Time Travel alone is not a complete audit trail of who performed each action.
- Time Travel differs from Fail-safe, which is a separate Snowflake-managed recovery mechanism rather than a user-queryable history feature.

Source: [Snowflake Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel).

### 15. What is a dynamic table?

**Interview answer**

A dynamic table stores the result of a query and lets Snowflake manage refreshes to pursue a configured freshness target, called target lag. Dynamic tables can depend on ordinary tables or other dynamic tables. This supports a pipeline where Bronze changes are reflected in downstream Silver and Gold results without writing every refresh step manually.

**corrections**

- Changes flow from upstream inputs to downstream derived results. Dynamic tables do not write transformations back into their upstream tables.
- Source tables do not all need to be dynamic tables.
- Target lag is a freshness goal, not an exact cron schedule or a guarantee of four refreshes per day; actual lag can exceed the target.
- Refreshes can be incremental or full, depending on the definition and refresh configuration. Incremental refresh is not guaranteed for every query.

**Likely follow-up**

- A view evaluates its query when read; a dynamic table stores a result refreshed separately. Fresher results usually require more refresh work and compute.

Source: [Snowflake dynamic tables](https://docs.snowflake.com/en/user-guide/dynamic-tables/overview).

## Main Eval answers

### 1. What is the difference between a list, set, dictionary, and tuple in Python?

**Interview answer**

A list is a mutable ordered sequence that permits duplicates. A tuple is an immutable ordered sequence that also permits duplicates. A set stores unique hashable elements and supports membership tests and set operations. A dictionary maps unique hashable keys to values and preserves insertion order. I choose based on whether I need positions, uniqueness, named lookup, or an immutable sequence.

| Type | Mutable? | Order | Typical use |
| --- | --- | --- | --- |
| `list` | Yes | Positional | Growing collection of records |
| `tuple` | No | Positional | Fixed group of values |
| `set` | Yes | No guaranteed positional order | Uniqueness and membership |
| `dict` | Yes | Insertion order | Lookup by key |

**Likely follow-up**

- A tuple can contain a mutable object. The tuple's references cannot be replaced, but the contained object can still change.
- Set membership and dictionary key lookup are average O(1); list membership is O(n). Hash-table worst cases can be worse.

Sources: [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Python complexity reference](https://wiki.python.org/moin/TimeComplexity).

### 2. How does Python garbage collection work?

**Interview answer**

In CPython, reference counting handles most object reclamation: an object generally becomes reclaimable when no references remain. A cyclic garbage collector also finds unreachable groups of objects that reference each other. `del` removes a reference or binding; it does not guarantee that the object is destroyed or that memory is immediately returned to the operating system.

**Likely follow-up**

- Two containers can reference each other after the application stops using them. Reference counts alone cannot reclaim that unreachable cycle.
- Use context managers such as `with open(...)` for predictable resource cleanup rather than relying on garbage collection.
- Other Python implementations can manage memory differently. Collector internals also vary by CPython version and build.

Sources: [Python data model](https://docs.python.org/3/reference/datamodel.html) and [cyclic garbage collector](https://docs.python.org/3/library/gc.html).

### 3. What is the difference between assignment, a shallow copy, and a deep copy?

**Interview answer**

Assignment gives another name to the same object. A shallow copy creates a new outer container but shares its nested objects. A deep copy recursively copies nested objects, subject to their copy behavior. I use a shallow copy when sharing nested values is acceptable, and a deep copy when nested mutable state needs independence, accepting the additional cost.

**Example**

```python
import copy

original = [[1, 2], [3]]
alias = original
shallow = copy.copy(original)
deep = copy.deepcopy(original)

original[0].append(9)
assert alias is original
assert shallow is not original
assert shallow == [[1, 2, 9], [3]]
assert deep == [[1, 2], [3]]
```

**corrections**

- Python's `copy.copy()` is a shallow copy. The useful comparison is shallow versus deep copy, plus assignment for contrast.

Source: [Python copy operations](https://docs.python.org/3/library/copy.html).

### 4. What are decorators and generators, and when would you use them?

**Interview answer**

A decorator takes a function or class and returns a replacement, often wrapping it to add reusable behavior such as logging, timing, or authorization. A generator produces values lazily and preserves its execution state between values. I use decorators for reusable behavior around calls, and generators to process records incrementally without building the entire result in memory.

**Examples**

```python
from functools import wraps

def log_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_call
def normalize(value):
    return value.strip().lower()

assert normalize("  ACTIVE  ") == "active"
```

```python
def normalized_rows(rows):
    for row in rows:
        yield row.strip().lower()

rows = normalized_rows([" ACTIVE ", " PENDING "])
assert next(rows) == "active"
assert list(rows) == ["pending"]
assert list(rows) == []  # This generator is exhausted.
```

**Likely follow-up**

- `@log_call` is equivalent to assigning `normalize = log_call(normalize)` after defining the original function.
- Calling a generator function returns a generator; its body runs as it is iterated. A generator does not make an already-loaded input list disappear from memory.

Sources: [Python decorators](https://docs.python.org/3/glossary.html#term-decorator), [generators](https://docs.python.org/3/tutorial/classes.html#generators), and [`functools.wraps`](https://docs.python.org/3/library/functools.html#functools.wraps).

### 5. Explain the `findDuplicate` function.

**Interview answer**

The function returns the unique strings that occur more than once. `seen` tracks values already encountered, and `duplicate` records repeated values. Each input is examined once; hash-set operations give average O(n) time and O(n) additional space in the worst case. The returned set does not preserve encounter order or count repetitions.

**correct**

Your original algorithm is correct for the stated `list[str]` input and `set[str]` output.

**Example**

```python
# Uses your function from the original notes.
assert findDuplicate(["a", "b", "a", "a", "c", "b"]) == {"a", "b"}
assert findDuplicate([]) == set()
assert findDuplicate(["a", "b"]) == set()
```

**Likely follow-up**

- Type hints do not enforce runtime validation. Generalizing this algorithm requires hashable values; lists cannot be inserted into a set.
- If ordered duplicates are required, use an output list plus a set tracking duplicates already emitted. If frequencies are required, use counts instead.

### 6. What is the difference between `map`, `flatMap`, and `foreach`?

**Interview answer**

For Scala collections or Spark RDDs, `map` transforms each input into one output. `flatMap` transforms each input into zero or more outputs and flattens one level. `foreach` runs a function for side effects and does not produce a transformed collection. In Spark, `map` and `flatMap` are lazy transformations, while `foreach` is an action.

**Example — local Scala collections**

```scala
val lines = List("red blue", "green")
val nested = lines.map(_.split(" ").toList)
// List(List("red", "blue"), List("green"))
val words = lines.flatMap(_.split(" ").toList)
// List("red", "blue", "green")
words.foreach(println) // Returns Unit.
```

**Likely follow-up**

- Spark `foreach` executes on workers. Tasks can be retried, so external writes need idempotency or another duplicate-handling strategy; side effects are not automatically exactly once.
- Python's built-in `map()` returns a lazy iterator. The language and API matter.

Sources: [RDD map](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.RDD.map.html), [RDD flatMap](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.RDD.flatMap.html), [RDD foreach](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.RDD.foreach.html), and [Scala collections](https://docs.scala-lang.org/overviews/collections-2.13/overview.html).

### 7. What is the difference between `val`, `var`, and `lazy val` in Scala?

**Interview answer**

A `val` is a binding that cannot be reassigned. A `var` can be reassigned. A `lazy val` delays evaluating its initializer until first access and retains the successfully initialized value for later accesses. I prefer `val` by default, use `var` when changing state is necessary, and use `lazy val` for initialization that may never be needed.

**Example**

```scala
val name = "orders"
var attempts = 0
attempts += 1
lazy val description = {
  println("initializing")
  "orders dataset"
}
println(description) // Initializes and prints the value.
println(description) // Reuses the value.
```

**Likely follow-up**

- A `val` pointing to a mutable collection prevents reassignment of the reference; it does not make the collection immutable.
- A `lazy val` defers initialization of one value. Spark laziness defers execution of a distributed computation plan.

Source: [Scala values, variables, and definitions](https://docs.scala-lang.org/tour/basics.html) and [Scala lazy values](https://docs.scala-lang.org/scala3/reference/changed-features/lazy-vals-init.html).

### 8. What is a case class in Scala?

**Interview answer**

A case class is a concise way to represent structured data. Scala supplies value-based equality, useful string representation, pattern matching support, and a `copy` method. Constructor parameters are `val` by default. In Spark's Scala API, case classes are commonly used to describe records in typed Datasets.

**Example**

```scala
case class Order(orderId: String, amount: Double)
val first = Order("o1", 10.0)
val updated = first.copy(amount = 12.0)
assert(first == Order("o1", 10.0))
assert(updated.amount == 12.0)
```

**Likely follow-up**

- `copy` is shallow: mutable nested objects can still be shared. Default `val` fields do not guarantee deep immutability.

Source: [Scala case classes](https://docs.scala-lang.org/tour/case-classes.html).

### 9. What is pattern matching with `match` and `case`?

**Interview answer**

Scala pattern matching selects behavior based on a value's shape, type, or contents. It can destructure case classes and use guards for additional conditions. A `match` is an expression, so it returns a value. I use it when handling several structured alternatives more clearly than a chain of conditional checks.

**Example**

```scala
val result = Option(12) match {
  case Some(value) if value > 0 => s"positive: $value"
  case Some(_) => "zero or negative"
  case None => "missing"
}
assert(result == "positive: 12")
```

**Likely follow-up**

- `_` is a wildcard. Missing a possible runtime case can cause `MatchError`; sealed hierarchies help the compiler check exhaustiveness.
- Python also has structural `match`/`case`, but the syntax and matching rules differ. This answer assumes Scala because of the surrounding questions.

Source: [Scala pattern matching](https://docs.scala-lang.org/tour/pattern-matching.html).

### 10. Explain Hadoop at a high level.

**Interview answer**

Hadoop provides components for storing and processing large datasets across a cluster. HDFS distributes file storage, YARN allocates resources and coordinates applications, and MapReduce executes batch computations through map and reduce stages. Hadoop Common supplies shared utilities. These responsibilities are separate: Spark can run on YARN and read HDFS without using MapReduce as its execution engine.

**Remember the responsibilities**

- **HDFS:** Where distributed files live.
- **YARN:** How applications receive cluster resources.
- **MapReduce:** How a particular batch processing engine executes work.

Sources: [Hadoop project overview](https://hadoop.apache.org/), [HDFS architecture](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html), and [YARN architecture](https://hadoop.apache.org/docs/stable/hadoop-yarn/hadoop-yarn-site/YARN.html).

### 11. What is the difference between a NameNode and a DataNode?

**Interview answer**

In HDFS, the NameNode manages filesystem metadata, including paths, permissions, and file-to-block mappings. DataNodes store the actual blocks and serve reads and writes. A client asks the NameNode where blocks are located, then transfers data directly with DataNodes. DataNodes report their status and blocks so the NameNode can coordinate replication and recovery.

**Likely follow-up**

- A block is a piece of a file, rather than necessarily one row or record.
- NameNode high availability uses active and standby roles. Keeping replicated data blocks does not by itself make metadata management highly available.

Source: [HDFS architecture](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html).

### 12. What is the difference between RDDs, DataFrames, and Datasets?

**Interview answer**

An RDD is Spark's lower-level distributed collection, giving direct control over element transformations. A DataFrame organizes data into named columns with a schema and exposes relational operations that Spark can optimize. A typed Dataset combines structured execution with JVM type information. In Scala, a DataFrame is a `Dataset[Row]`; PySpark provides DataFrames but not the typed JVM Dataset API.

| Abstraction | Strength | Typical choice |
| --- | --- | --- |
| RDD | Low-level element and partition control | Processing that needs RDD-specific control |
| DataFrame | Schema, SQL expressions, query optimization | Most structured ETL and analytics |
| Typed Dataset | Typed JVM records plus structured operations | Scala/Java applications benefiting from typed records |

**Likely follow-up**

- A PySpark DataFrame has a schema even though Python is dynamically typed. Schema and compile-time application types are different concepts.
- Prefer built-in DataFrame expressions where practical; opaque user functions can reduce optimization opportunities.

Source: [Spark SQL, DataFrames, and Datasets](https://spark.apache.org/docs/latest/sql-programming-guide.html).

### 13. What are narrow and wide transformations in Spark?

**Interview answer**

A narrow dependency means each parent partition contributes to at most one child partition, allowing operations such as `map` and `filter` to be pipelined. A wide dependency can distribute one parent's records across multiple child partitions, typically through a shuffle. Grouping and repartitioning commonly introduce wide dependencies, adding network, serialization, and possible disk costs and creating stage boundaries.

**Likely follow-up**

- `groupByKey`, a shuffled aggregation, and `repartition` are common shuffle examples.
- `coalesce` without shuffling can merge multiple parent partitions into one child and still be narrow. Narrow does not require a one-to-one partition mapping.
- Join behavior depends on the physical plan: broadcast and shuffled joins distribute work differently. Existing partitioning can also avoid a new shuffle.
- Narrow does not mean free. Expensive functions or skewed partitions can still make narrow operations slow.

Source: [Spark dependencies and shuffle operations](https://spark.apache.org/docs/latest/rdd-programming-guide.html).

### 14. What is the difference between caching and persistence in Spark?

**Interview answer**

Both let Spark retain computed partitions for reuse across actions, avoiding repeated computation. `cache()` is a convenience form of persistence using the API's default storage level; `persist()` lets me choose a storage level. Data is populated as actions compute it. I use persistence for expensive intermediate results that will be reused, then call `unpersist()` when they are no longer needed.

**corrections**

- Cache is not always memory-only. In Spark 4.2, PySpark `RDD.cache()` uses `MEMORY_ONLY`, while `DataFrame.cache()` uses `MEMORY_AND_DISK_DESER`.
- Persistence is not durable storage or checkpointing. Lost cached partitions can be recomputed from lineage when their inputs remain available.
- Caching a dataset used once can add overhead without providing a benefit.

Sources: [PySpark RDD cache](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.RDD.cache.html) and [PySpark DataFrame cache](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.cache.html).

## Practice route

- Start with the **Interview answer** for each question. Explain it aloud without reading.
- Add one example and one tradeoff when asked to go deeper.
- Revisit Kafka partitions versus schemas, configurable message limits, compute versus storage, dynamic-table dependency direction, shallow copies, and Spark cache defaults first.
- Trace your duplicate function on `["a", "b", "a", "a"]`, explaining both sets after each iteration.
- For an ambiguous question, state the context: “Assuming CPython…”, “For Spark RDDs…”, or “If you mean Snowflake Postgres…”.

## Verification note

Primary documentation was reviewed on 2026-10-12. Local checks passed for 29 answer headings and answer blocks, 10 balanced fenced examples, and no added trailing whitespace. All five Python snippets executed successfully, including duplicate-function assertions for repeated, empty, and unique inputs. The original notes were retained above the appended section. Scala, Spark, Kafka, Snowflake, and dbt examples were not executed; service behavior and performance are not runtime-verified by this document.
