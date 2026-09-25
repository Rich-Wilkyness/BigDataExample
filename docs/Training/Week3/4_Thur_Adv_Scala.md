# Thursday: Advanced Scala for Data Engineering

> Status: Draft
>
> Level: Intermediate
>
> Applies to: Scala 2.13.8, Apache Spark SQL 3.5.9, and JVM data pipelines
>
> Example status: Focused reference examples; runtime verification pending
>
> Last reviewed: 2026-09

## Overview

This guide builds on [Wednesday's Scala foundations](./3_Wed_Scala.md) instead of reteaching Kotlin-familiar object-oriented syntax. The goal is to explain the Scala features that materially affect Spark jobs: typed records, encoders, SQL nulls, implicit resolution, serialized closures, composable transformations, and driver-side concurrency.

The most important distinction is between ordinary Scala code and Spark execution. Scala gives you language features and JVM types. Spark builds lazy query plans, partitions data, serializes work, runs tasks on executors, and may retry those tasks. A language feature is useful only when you also understand which process owns it and whether Spark can inspect or optimize it.

## Learning objectives

After completing this guide, you should be able to:

1. Choose between a typed `Dataset[T]` and a `DataFrame` without assuming that one is always better.
2. Explain what an encoder and `import spark.implicits._` provide.
3. Distinguish `Nil`, `null`, `Null`, `Nothing`, `None`, and `Unit`, especially at Spark SQL boundaries.
4. Use traits and sealed types to model pipeline contracts and explicit outcomes.
5. Explain why a Spark closure must be small, serializable, and free of unsafe external side effects.
6. Build configured `DataFrame => DataFrame` transformations and chain them with `transform`.
7. Distinguish a Scala `Future` from Spark's distributed task execution.

## Prerequisites

- [Wednesday: Scala Foundations for Big Data](./3_Wed_Scala.md), including case classes, `Option`, pattern matching, traits, companions, and immutable collections.
- [Wednesday: Scala Spark DataFrame API](./3.2_Wed_Scala_Spark_API.md), including columns, transformations, actions, joins, and aggregations.
- [Monday: Apache Spark Architecture, Execution, and Performance](./1_Mon_Spark.md), including drivers, executors, lazy evaluation, partitions, and shuffles.
- Familiarity with Kotlin data classes, sealed classes, interfaces, lambdas, and nullable types.

## 1. What Thursday adds

| Concept | Wednesday foundation | Thursday focus | Data-engineering consequence |
| --- | --- | --- | --- |
| Case class | Immutable typed record | `Dataset[T]` and encoders | Types can catch some mistakes before submission, but they do not validate external data |
| `Option` | `Some` or `None` | Boundary with Spark SQL `NULL` | Typed missingness and SQL three-valued logic are related but not identical |
| Trait | Contract with optional behavior | Pipeline-stage interface | Small contracts help compose and test transformations |
| Sealed type | Exhaustive pattern matching | Accepted and rejected outcomes | Invalid data remains explicit instead of disappearing |
| Implicit | Compiler-supplied behavior | `spark.implicits._` and encoders | Methods and type evidence can appear through imports and scope |
| Closure | Function captures outside values | Driver-to-executor serialization | Captured state is copied, serialized, and possibly executed again after retry |
| Currying | Multiple parameter lists | Configure a transformation before applying data | Reusable functions fit `DataFrame.transform` pipelines |
| `Future` | Asynchronous value | Driver-local concurrency | It does not replace Spark partitions or executor tasks |

## 2. The execution mental model

```text
Scala code in main
        |
        | runs in the Spark driver JVM
        v
DataFrame and Dataset transformations
        |
        | build a lazy logical plan
        v
Spark action
        |
        | creates jobs, stages, and tasks
        v
Serialized task closures run in executor JVMs
        |
        | produce distributed partitions
        v
Write results or return a deliberately bounded value to the driver
```

This model answers several questions that language syntax alone cannot:

- A case class exists in Scala source, but an encoder maps its fields to Spark's internal representation.
- A closure is written in the driver, but Spark may serialize it and run copies on many executors.
- A `Future` schedules work through a JVM `ExecutionContext`; it does not create Spark partitions.
- A `DataFrame` transformation returns immediately because it normally adds to a plan rather than processing every row at that moment.

## 3. Typed `Dataset[T]` versus `DataFrame`

### 3.1 The relationship

In the Scala API, a DataFrame is a `Dataset[Row]`. Both use Spark SQL's structured execution engine:

```text
Dataset[Sale]   typed JVM-facing record
Dataset[Row]    DataFrame with named columns
```

A typed Dataset needs an `Encoder[T]`. The encoder maps between a JVM value such as `Sale` and Spark's internal SQL representation.

```scala
import org.apache.spark.sql.{Dataset, SparkSession}

object TypedSalesExample {
  case class Sale(
    orderId: Long,
    amount: BigDecimal,
    shippedDate: Option[String]
  )

  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("Typed sales example")
      .getOrCreate()

    import spark.implicits._

    val sales: Dataset[Sale] = Seq(
      Sale(1001L, BigDecimal("125.50"), Some("2026-09-24")),
      Sale(1002L, BigDecimal("42.00"), None)
    ).toDS()

    val largeSales: Dataset[Sale] =
      sales.filter(sale => sale.amount >= BigDecimal("100.00"))

    largeSales.show()
    spark.stop()
  }
}
```

The compiler knows that a `Sale` has an `amount` field. A typo such as `sale.ammount` cannot compile. This is useful, but it is narrower than saying “Datasets catch errors early.”

### 3.2 What typing catches—and what it does not

| Problem | Typed Dataset help? | Why |
| --- | --- | --- |
| Misspelled case-class member in a typed lambda | Yes | The Scala compiler checks `sale.amount` against `Sale` |
| Returning the wrong Scala type from a method | Yes | The compiler checks the declared return type |
| Missing encoder | Yes | Compilation fails when Spark cannot find the required `Encoder[T]` |
| Misspelled column inside a SQL string | No | The string is not a typed Scala member access |
| Source file contains malformed values | No | The JVM type does not prove that external data conforms |
| Division by zero or data-dependent parsing error | No | The error depends on runtime values |
| Join duplicates rows unexpectedly | No | Cardinality is a data-contract problem, not a Scala type error |
| Executor runs out of memory after a shuffle | No | Resource behavior is discovered during distributed execution |

An unresolved DataFrame column may be rejected during Spark analysis, often before a long job runs. Other failures are genuinely data-dependent and may appear only when an action reaches the affected partition. Typed code reduces one class of mistakes; schema validation, small-fixture tests, plan inspection, data-quality checks, and reconciliation handle the others.

### 3.3 Choosing the API

| Prefer | When it helps | Tradeoff |
| --- | --- | --- |
| `Dataset[T]` | Domain records, type-safe member access, typed library boundaries, and Scala/Java-only logic | Typed lambdas may require object encoding and can hide logic from Spark's SQL optimizer |
| `DataFrame` | SQL-style projections, joins, aggregations, built-in functions, cross-language teams, and table-shaped pipelines | Column names and row shapes are not ordinary Scala member types |
| A mix | Read and transform tabular data as DataFrames, then use typed records at a boundary where the type adds real value | Conversions and ownership boundaries must remain explicit |

Do not adopt “always prefer Dataset” as a rule. For most analytical ETL, built-in DataFrame expressions are concise, optimizer-visible, and interoperable. Use a typed Dataset where compile-time domain types provide enough value to justify the additional encoding and API complexity.

## 4. Missingness: `Nil`, `null`, `Null`, `Nothing`, `None`, and `Unit`

These names sound similar but occupy different roles:

| Name | Kind | Meaning | Data-engineering relevance |
| --- | --- | --- | --- |
| `Nil` | Value | The empty immutable `List` | A collection exists and contains zero elements |
| `null` | Value | JVM null reference | Common at Java and SQL boundaries; unsafe to dereference |
| `Null` | Type | Scala 2 type whose practical value is `null` | Mostly type-system knowledge; rarely written in pipeline code |
| `Nothing` | Type | Bottom type with no values | Lets `Nil` work as a `List` of any element type and represents expressions such as `throw` that never return normally |
| `None` | Value | An `Option` with no contained value | Explicit absence in typed Scala code |
| `Unit` | Type | A completed computation with no meaningful result; its value is `()` | Common return type for logging, writing, or lifecycle methods |

### 4.1 Scala `Option` and Spark SQL `NULL`

Use `Option[T]` when a Scala API or typed record intentionally models an optional value:

```scala
case class Customer(customerId: Long, email: Option[String])

val normalizedEmail: Option[String] =
  customer.email.map(_.trim.toLowerCase)
```

`map` runs only for `Some`; `None` stays `None`.

Use SQL column expressions when working with a DataFrame:

```scala
import org.apache.spark.sql.functions.{coalesce, col, lit}

val normalized = customers
  .withColumn("email", coalesce(col("email"), lit("unknown")))
  .filter(col("customer_id").isNotNull)
```

SQL `NULL` follows SQL null semantics. For example, `col("email") === "a@example.com"` is not true when `email` is null, and comparisons involving null can produce an unknown result. Do not mechanically translate every DataFrame null into a driver-side `Option`, and do not use `None` as permission to silently drop invalid records.

## 5. Traits, abstract classes, overloading, and overriding

Wednesday introduced the constructs. Here the useful question is where each one belongs in a data pipeline.

### 5.1 Trait versus abstract class

| Use | Prefer a trait | Prefer an abstract class |
| --- | --- | --- |
| Main purpose | A capability or contract that different classes can mix in | A closely related family with shared constructor state or implementation |
| Inheritance | A class can mix in multiple traits | A class can extend only one superclass |
| Data-pipeline example | A standard `DataFrame => DataFrame` stage | A framework base class that owns shared lifecycle state |
| Default choice | Small interfaces and composition | Only when shared base state or protected implementation is genuinely useful |

Scala supports one superclass plus multiple trait mixins. This is more precise than saying Scala permits unrestricted multiple class inheritance.

```scala
import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions.{col, lit}

trait DataFrameStep extends (DataFrame => DataFrame) {
  def name: String
}

final case class MinimumAmount(minimum: BigDecimal) extends DataFrameStep {
  override val name: String = "minimum-amount"

  override def apply(df: DataFrame): DataFrame =
    df.filter(col("sales_amount") >= lit(minimum.bigDecimal))
}
```

`MinimumAmount` is now both a named pipeline stage and a normal function from `DataFrame` to `DataFrame`. It has no mutable state, so it is straightforward to test and reuse.

### 5.2 Overloading versus overriding

| Concept | Meaning | Resolution | Typical relevance |
| --- | --- | --- | --- |
| Overloading | Same method name with different parameter lists | Compile time | Convenience APIs such as `read(path)` and `read(paths)` |
| Overriding | Child class or trait implementation replaces inherited behavior | Runtime dispatch | Implementing a pipeline-stage contract |

```scala
trait Validator {
  def validate(value: String): Boolean
}

final class NonEmptyValidator extends Validator {
  override def validate(value: String): Boolean = value.trim.nonEmpty
}

object Parse {
  def read(value: String): String = value.trim
  def read(values: List[String]): List[String] = values.map(_.trim)
}
```

Use `override` deliberately so the compiler confirms that a parent member actually exists. Avoid deep inheritance trees in ETL code; small transformations and explicit composition usually make execution and testing easier to follow.

## 6. Sealed types for explicit pipeline outcomes

A sealed trait is similar to a Kotlin sealed interface. All direct implementations are known within the permitted source scope, so the compiler can check a pattern match for missing cases.

```scala
sealed trait ParseResult

final case class Accepted(sale: CleanSale) extends ParseResult
final case class Rejected(rawLine: String, reason: String) extends ParseResult

final case class CleanSale(orderId: Long, amount: BigDecimal)

def describe(result: ParseResult): String = result match {
  case Accepted(sale)      => s"accepted order ${sale.orderId}"
  case Rejected(_, reason) => s"rejected: $reason"
}
```

If a new result such as `Duplicate` is added, an incomplete match normally produces an exhaustivity warning. It may not appear as an IntelliJ error, and the build still succeeds unless warnings are configured as fatal. The safety comes from compiler diagnostics plus build settings, not from the IDE alone.

### Data-engineering use

A sealed result makes “accepted or rejected” explicit in local parsing and library code. It prevents this dangerous pattern:

```scala
// Dangerous when completeness matters: invalid rows disappear.
val acceptedOnly = rawLines.flatMap(parseToOption)
```

For a tabular Spark pipeline, the durable output is often clearer as explicit columns or separate datasets:

```text
record_status       ACCEPTED or REJECTED
rejection_reason    nullable explanation
raw_payload         original input for repair
```

Arbitrary trait hierarchies do not always map cleanly to one Spark SQL schema. Use sealed types for code-level outcomes; use explicit columns, schemas, counts, and quarantine tables for durable distributed data.

## 7. Implicits without the mystery

The shortest useful mental model is:

> An implicit is a value or conversion that the compiler may supply after searching the allowed scope for a compatible type.

Scala 2 uses implicits for three patterns you will encounter in Spark code:

1. Supplying contextual type evidence such as an `Encoder[T]`.
2. Enriching a type with syntax such as `.toDS()`.
3. Converting convenient syntax such as `$"amount"` into a Spark `Column`.

### 7.1 What `spark.implicits._` does

```scala
val spark = SparkSession.builder()
  .appName("Implicit example")
  .getOrCreate()

import spark.implicits._

val numbers = Seq(1, 2, 3).toDS()
val doubled = numbers.select(($"value" * 2).as("doubled"))
```

The import appears after `spark` exists because `implicits` belongs to that `SparkSession` instance. It brings Spark's Dataset conversions, column syntax, and common encoders into scope.

Conceptually, `.toDS()` needs two things:

```text
Seq[Sale]
   |
   | syntax that adds toDS()
   | plus an Encoder[Sale]
   v
Dataset[Sale]
```

The compiler is not searching every object in the application. It follows implicit-resolution rules involving local definitions, imports, and relevant type companions. If it finds no eligible value, compilation fails. If it finds multiple equally suitable values, compilation fails as ambiguous rather than guessing.

### 7.2 Practical rules

- Keep implicit imports close to the code that needs them.
- Prefer specific types such as `Encoder[Sale]` over generic contextual values such as an implicit `String`.
- When a method appears “magically,” inspect imports and the required implicit types.
- Do not create an implicit conversion merely to hide an unsafe parse or surprising behavior.
- Expect Scala 3 code to use `given`, `using`, and extension methods; Spark 3.5.9 Scala examples and existing Scala 2.13 code still commonly use `implicit` and wildcard imports.

## 8. Closures and executor serialization

A closure is a function that captures a value from its surrounding scope:

```scala
val minimum = BigDecimal("100.00")

val isLarge: Sale => Boolean =
  sale => sale.amount >= minimum
```

The function parameter is `sale`; `minimum` is captured. With a local `List`, both live in one JVM. With a Spark transformation, Spark may serialize the function and the captured value, ship copies to executors, and run the function again if a task is retried.

```scala
val largeSales = salesDataset.filter(isLarge)
```

### 8.1 Capture decisions

| Captured value | Guidance | Reason |
| --- | --- | --- |
| Small immutable number or string | Usually reasonable | Small and serializable |
| Small immutable configuration case class | Usually reasonable | Makes task behavior explicit |
| Large lookup map | Consider a Spark broadcast variable or a join | Shipping a copy with tasks wastes memory and network |
| `SparkSession` or `DataFrame` inside row logic | Avoid | Driver-owned planning objects do not belong in executor row code |
| Open JDBC connection, client, stream, or file handle | Avoid | Commonly non-serializable and unsafe across processes or retries |
| Mutable driver counter | Never use for a result | Executors receive copies; retries can also repeat updates |

This is incorrect distributed aggregation:

```scala
var total = BigDecimal(0)

salesDataset.foreach { sale =>
  total += sale.amount
}

println(total) // Not a valid distributed result.
```

Use a Spark aggregation instead:

```scala
import org.apache.spark.sql.functions.{col, sum}

val totals = salesDataset
  .agg(sum(col("amount")).as("total_amount"))
```

Accumulators are useful for limited metrics and debugging, but a retry-aware DataFrame aggregation or durable output should own business results.

### 8.2 Prefer optimizer-visible expressions

A typed closure can be appropriate for domain logic, but Spark cannot inspect arbitrary Scala code as deeply as a built-in column expression. When the operation already exists in Spark SQL, prefer the built-in form:

```scala
import org.apache.spark.sql.functions.{col, lit}

val largeSales = salesDataset
  .filter(col("amount") >= lit(BigDecimal("100.00").bigDecimal))
```

This keeps the expression visible to Catalyst and avoids introducing custom per-row JVM logic unnecessarily.

## 9. Currying, partial application, and composable ETL

These terms are related but not identical:

| Term | Meaning |
| --- | --- |
| Multiple parameter lists | Scala syntax such as `def f(config)(data)` |
| Currying | Representing a multi-argument function as a chain of one-argument functions |
| Partial application | Supplying some arguments now and receiving a function for the remaining arguments |

The practical data-engineering use is separating configuration from the DataFrame being transformed:

```scala
import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions.{col, lit}

def countryEquals(country: String)(df: DataFrame): DataFrame =
  df.filter(col("country") === lit(country))

def minimumAmount(minimum: BigDecimal)(df: DataFrame): DataFrame =
  df.filter(col("sales_amount") >= lit(minimum.bigDecimal))

def selectColumns(names: String*)(df: DataFrame): DataFrame =
  df.select(names.map(col): _*)
```

Supplying only the configuration creates reusable functions:

```scala
val usaOnly: DataFrame => DataFrame = countryEquals("USA")
val atLeast1000: DataFrame => DataFrame = minimumAmount(BigDecimal("1000.00"))
```

Each function now has the same shape:

```text
DataFrame => DataFrame
```

Spark's `transform` method chains that shape directly:

```scala
val goldSales = rawSales
  .transform(usaOnly)
  .transform(atLeast1000)
  .transform(selectColumns("order_id", "customer_id", "sales_amount"))
```

These calls still build one lazy logical plan. Currying does not make the work distributed or faster by itself; it makes configuration and composition clearer.

### When to use this pattern

Use it when several pipelines share transformations with different configuration. A named transformation is easy to unit test and chain. Skip it when direct DataFrame code is already shorter and clearer.

Do not use currying as a reason to construct SQL by interpolating untrusted table names or values. Prefer Spark column expressions, parameterized database APIs, and validated identifiers.

## 10. `Future` is driver-local concurrency

A `Future[T]` represents a value that may complete later. An `ExecutionContext` decides where its computation runs, normally on threads within the current JVM process.

```scala
import scala.concurrent.{ExecutionContext, Future}

implicit val ec: ExecutionContext = ExecutionContext.global

def checkCatalog(tableName: String): Future[Boolean] = Future {
  catalogClient.tableExists(tableName) // Placeholder for a driver-side client call.
}

val customerCheck: Future[Boolean] = checkCatalog("gold.dim_customer")

val message: Future[String] = customerCheck.map { exists =>
  if (exists) "table exists" else "table is missing"
}
```

`map` registers what to do when the future succeeds. A failed computation produces a failed `Future`; it does not silently become `None`.

### `Future` versus Spark

| `Future` | Spark job execution |
| --- | --- |
| Schedules asynchronous work through an `ExecutionContext` | Schedules distributed tasks through Spark's driver and cluster scheduler |
| Usually uses threads in one JVM | Uses partitions across executor processes and possibly machines |
| Represents one eventual result | Represents distributed transformations and actions |
| Useful for bounded driver-side service or metadata calls | Useful for scalable data processing |

Do not wrap every row in a `Future`; Spark already owns row and partition parallelism. Also avoid unbounded concurrent Spark actions or blocking calls on the global execution context. If a driver truly needs concurrent blocking I/O, use a deliberately sized execution context, timeouts, rate limits, and explicit shutdown ownership.

`Await.result` blocks a thread. Reserve it for a controlled application boundary with a timeout, not for row processing or a repeated pipeline step.

## 11. Concept priority for a Scala data engineer

| Priority | Concepts | Why |
| --- | --- | --- |
| Essential now | DataFrame expressions, functions, collections, `Option`, case classes, pattern matching, closures, and serialization | These appear directly in ordinary Spark code and failure diagnosis |
| Important | Encoders, implicits, traits, sealed outcomes, and higher-order transformations | These explain typed APIs and reusable pipeline design |
| Useful design technique | Multiple parameter lists, currying, and partial application | Helpful for configurable transformation libraries |
| Occasional | Futures, overloading, and inheritance details | Often appear in libraries, orchestration code, or interviews but are not the core of distributed ETL |

The ranking is about daily data-engineering value, not language sophistication.

## 12. Common pitfalls

### “A Dataset always fails at compile time”

Only statically visible type errors fail during Scala compilation. External schemas, SQL strings, bad records, join cardinality, executor memory, and side effects remain runtime concerns.

### “A Dataset is always safer, so prefer it everywhere”

Datasets and DataFrames solve different interface problems. DataFrames are often the clearer choice for relational transformations and optimizer-visible built-in expressions.

### Treating `Option` and SQL `NULL` as interchangeable

`Option` is a Scala container. SQL null behavior belongs to Spark SQL expressions and three-valued logic. Convert intentionally at a typed boundary.

### Capturing a service inside executor code

Database connections, API clients, and driver objects may fail serialization, overload dependencies, or repeat side effects when tasks retry.

### Updating driver variables from tasks

Executors operate on serialized copies. Use Spark aggregations for results and retry-aware metrics for observability.

### Using a `Future` for distributed row processing

Futures create local asynchronous computations. Spark controls distributed parallelism through partitions, stages, tasks, and executors.

### Making every helper implicit

Implicit behavior can hide where values or methods come from. Use it for established library patterns and keep scope narrow.

### Building a transformation framework too early

A curried helper or trait is valuable when it removes repeated pipeline logic. If it only renames one DataFrame call, direct code is easier to read.

## 13. Practice

### Exercise 1: choose the boundary

For each operation, choose `Dataset[T]`, DataFrame, or a mix, and explain why:

1. Read a Parquet fact table, join three dimensions, and aggregate revenue.
2. Validate a small driver-side list of strongly typed job configurations.
3. Apply a domain method to a typed event and then write a tabular result.

### Exercise 2: preserve rejected records

Create a sealed `ParseResult` with `Accepted` and `Rejected`. Parse five local strings, then prove that accepted count plus rejected count equals input count.

### Exercise 3: inspect an implicit dependency

Remove `import spark.implicits._` from a small `.toDS()` example. Read the compiler error, restore the import, and identify both the added syntax and required encoder.

### Exercise 4: shrink a closure

Find a Spark transformation that captures an outer object. Rewrite it so the closure captures only the small immutable values it needs, or replace the closure with built-in column expressions.

### Exercise 5: compose transformations

Write three configured `DataFrame => DataFrame` functions and chain them with `transform`. Call `explain(true)` and confirm that the functions produced one Spark plan rather than three separate jobs.

### Exercise 6: identify concurrency ownership

For each task, decide whether it belongs to a local function, `Future`, a Spark transformation, or an orchestrator:

1. Normalize every row in a billion-row table.
2. Check two independent catalog endpoints before submission.
3. Retry a failed daily pipeline tomorrow.
4. Convert one configuration string to a validated enum.

## 14. Knowledge check

1. Why is a DataFrame described as `Dataset[Row]` in Scala?
2. What does an encoder do?
3. Which errors can a typed Dataset catch before a Spark job runs, and which remain runtime errors?
4. Why is a DataFrame often preferable for joins and aggregations?
5. What is the difference between `None` and SQL `NULL`?
6. Why can an incomplete match over a sealed trait compile even though it is unsafe?
7. What does `import spark.implicits._` make available?
8. Why does updating a captured driver variable from an executor task not produce a valid total?
9. When should a large lookup use a broadcast variable or join instead of an ordinary captured map?
10. How does partial application produce a `DataFrame => DataFrame` transformation?
11. Does chaining three calls to `transform` execute three Spark jobs? Why or why not?
12. Why is a Scala `Future` not a replacement for Spark distributed execution?

## Key takeaways

- Advanced Scala matters when it clarifies Spark boundaries, not when it merely adds clever syntax.
- A typed Dataset catches Scala type errors, while DataFrame plans remain a strong default for relational ETL and built-in Spark SQL expressions.
- `Option` models typed absence; DataFrames use SQL null semantics.
- Traits and sealed types help make code contracts explicit, while durable data still needs explicit schemas, status columns, quarantine records, and reconciliation.
- `spark.implicits._` supplies Dataset-related syntax and type evidence through Scala's implicit-resolution system.
- Spark serializes closures from the driver to executors, so captured values should be small, immutable, serializable, and safe to repeat.
- Configured `DataFrame => DataFrame` functions are a practical use of partial application and work naturally with `transform`.
- Futures provide concurrency inside a JVM; Spark provides distributed data processing.

## Resources

- [Wednesday: Scala Foundations for Big Data](./3_Wed_Scala.md)
- [Wednesday: Scala Spark DataFrame API](./3.2_Wed_Scala_Spark_API.md)
- [Apache Spark 3.5.9: SQL, DataFrames, and Datasets](https://spark.apache.org/docs/3.5.9/sql-getting-started.html)
- [Apache Spark 3.5.9: RDD programming guide and closures](https://spark.apache.org/docs/3.5.9/rdd-programming-guide.html#understanding-closures)
- [Apache Spark 3.5.9 Scala API: `Dataset`](https://spark.apache.org/docs/3.5.9/api/scala/org/apache/spark/sql/Dataset.html)
- [Tour of Scala: class composition with mixins](https://docs.scala-lang.org/tour/mixin-class-composition.html)
- [Tour of Scala: contextual parameters](https://docs.scala-lang.org/tour/implicit-parameters.html)
- [Tour of Scala: multiple parameter lists](https://docs.scala-lang.org/tour/multiple-parameter-lists.html)
- [Scala Futures and Promises](https://docs.scala-lang.org/overviews/core/futures.html)
