# Wednesday: Scala Foundations for Big Data

> Status: Draft  
> Level: Beginner  
> Applies to: Scala, sbt, JVM applications, and Apache Spark  
> Example status: Complete local examples; `HelloWorld` JAR verified with Spark 3.5.9 `spark-submit`  
> Last reviewed: 2026-09

## Overview

Scala is a statically typed JVM language that combines object-oriented and functional programming. For a Kotlin developer, the basic syntax and JVM concepts are familiar. The biggest adjustment is learning Scala's expression-oriented style, immutable collections, `Option`, pattern matching, and function-heavy APIs.

Scala matters in big data because Apache Spark is implemented in Scala and provides a native Scala API. Learning Scala also makes Spark documentation, JVM stack traces, library coordinates, and typed `Dataset` examples easier to understand.

This guide distinguishes the project build from the separately installed Spark command-line runtime:

- The `/Users/richardwilkerson/IdeaProjects/HelloWorld` project targets Scala 2.13.8 and Spark SQL 3.5.9.
- The shell `PATH` is configured so `spark-submit` uses Spark 3.5.9 with Scala 2.13.8. The separately installed PySpark 4.2.0 launcher is still present, but it is no longer the default.

A packaged Spark application must use the Scala binary version expected by its target Spark runtime. Matching the Spark minor version is also important because Scala binary compatibility does not guarantee compatibility between Spark 3.5.9 and Spark 4.2.0 APIs or internals.

## Learning objectives

After completing this guide, you should be able to:

1. Explain how Scala source, sbt, JVM bytecode, and Spark relate.
2. Read and write Scala variables, methods, functions, collections, classes, singleton objects, and case classes.
3. Translate familiar Kotlin constructs into basic Scala.
4. Use immutable collection transformations to model a small ETL flow.
5. Represent a possibly missing value with `Option` instead of immediately using `null`.
6. Explain where a local Scala collection analogy stops matching a distributed Spark DataFrame.
7. Choose the correct Scala binary version for a Spark application.

## Prerequisites

- Familiarity with Kotlin and basic JVM terminology.
- IntelliJ IDEA with the Scala plugin.
- The existing `HelloWorld` sbt project.
- Basic Spark concepts from [Monday's Spark guide](1_Mon_Spark.md).

## 1. The mental model

```text
Scala source (.scala)
        |
        | scalac, normally coordinated by sbt
        v
JVM bytecode (.class files in target/)
        |
        | java / sbt run / spark-submit
        v
JVM process
```

For a normal Scala application, the JVM process runs your `main` method. For a Spark application, the submitted JVM application becomes the Spark driver. The driver builds a distributed execution plan and coordinates work on executors.

The Scala language does not make a program distributed. Spark supplies the distributed execution engine.

## 2. Your `HelloWorld` project

The important project paths are:

```text
HelloWorld/
|-- build.sbt
|-- project/
|   `-- build.properties
|-- src/
|   `-- main/
|       `-- scala/
|           `-- HelloWorld.scala
`-- target/
```

### What each path owns

| Path | Purpose | Kotlin/Gradle comparison |
| --- | --- | --- |
| `build.sbt` | Project name, Scala version, dependencies, and build settings | `build.gradle.kts` |
| `project/build.properties` | Selects the sbt version used to load the build | Gradle wrapper version, conceptually |
| `src/main/scala/` | Application source code | `src/main/kotlin/` |
| `src/test/scala/` | Test source code when added | `src/test/kotlin/` |
| `target/` | Generated classes, JARs, reports, and caches | `build/` |

Do not edit or submit generated files under `target/`. sbt or IntelliJ can recreate them from the source and build definition.

Your current `build.sbt` selects the Scala version used by Spark 3.5.9's official Scala 2.13 build, adds Spark SQL to the local runtime classpath, and supplies the Java 17 module option needed by this local Spark version:

```scala
scalaVersion := "2.13.8"

lazy val root = rootProject
  .settings(
    name := "HelloWorld",
    libraryDependencies ++= Seq(
      "org.apache.spark" %% "spark-sql" % "3.5.9"
    ),
    Compile / run / fork := true,
    Compile / run / javaOptions += "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED"
  )
```

Your current `project/build.properties` selects sbt 2.0.9:

```properties
sbt.version = 2.0.9
```

### Common sbt tasks

Run these in IntelliJ's sbt tool window or in a terminal where `sbt` is installed:

```text
compile          Compile main source code
run              Run a discovered main class
run one two      Pass arguments to the main class
test             Compile and run tests
package          Build a JAR under target/
clean            Delete generated build outputs
```

These are sbt task names, not Scala statements.

## 3. Your first entry point

Here is a corrected version of the current program:

```scala
object HelloWorld {
  def main(args: Array[String]): Unit = {
    println("Hello, Scala!")
    println(s"Arguments: ${args.mkString(", ")}")
  }
}
```

### Why use an `object`?

An `object` defines exactly one singleton instance. This is very close to Kotlin's `object` declaration.

An object is not automatically self-running. It is runnable here because it contains the recognized JVM entry point:

```scala
def main(args: Array[String]): Unit
```

The launcher calls `HelloWorld.main(...)`. A normal `class` can contain methods and state, but the launcher would first need an instance before it could call an instance method. Keeping `main` in an object avoids that extra construction.

Scala 3 also supports `@main`, but it is not available in this Scala 2.13 project. The explicit object-and-main form is worth learning because it is common in Spark applications and works across Scala 2.13 and Scala 3:

```scala
@main def hello(name: String): Unit = {
  println(s"Hello, $name!")
}
```

### What the signature means

| Part | Meaning |
| --- | --- |
| `def` | Declares a method |
| `main` | Method name recognized as the entry point |
| `args` | Parameter name |
| `Array[String]` | Ordered JVM command-line arguments |
| `Unit` | No meaningful result is returned; comparable to Kotlin `Unit` and Java `void` |
| `=` | Separates the declaration from the method body |

`Unit` technically has one value, written `()`. Saying “nothing useful is returned” is more precise than saying no value exists.

## 4. Kotlin-to-Scala quick map

| Intent | Kotlin | Scala |
| --- | --- | --- |
| Read-only reference | `val count = 3` | `val count = 3` |
| Reassignable reference | `var count = 3` | `var count = 3` |
| Function or method | `fun total(qty: Int): Int` | `def total(qty: Int): Int` |
| String template | `"Rows: $count"` | `s"Rows: $count"` |
| Singleton | `object Job` | `object Job` |
| Data holder | `data class Sale(...)` | `case class Sale(...)` |
| Interface with behavior | `interface` | `trait` |
| Conditional expression | `if (...) a else b` | `if (...) a else b` |
| Branch by value/type | `when` | `match` |
| Nullable value | `String?` | Commonly `Option[String]` |
| Generic type | `List<Sale>` | `List[Sale]` |
| Lambda | `{ sale -> sale.total }` | `sale => sale.total` |
| Nothing meaningful returned | `Unit` | `Unit` |

The similarities help you start quickly, but the languages are not interchangeable. Scala APIs make heavier use of higher-order functions, pattern matching, implicits or givens, and immutable collection operations.

## 5. Values, variables, and type inference

Use `val` by default:

```scala
val sourceName = "postgres"
val rowCount = 2803
val unitPrice: BigDecimal = BigDecimal("19.95")

var retryCount = 0
retryCount += 1
```

Scala does not require an explicit type everywhere. It inferred `String` for `sourceName` and `Int` for `rowCount`.

Add explicit types when they communicate an important boundary:

- Public method parameters and return values.
- Data models and schemas.
- Numeric values where precision matters.
- Places where inference selects a type broader or narrower than intended.

For money, prefer `BigDecimal` over `Double` when exact decimal behavior matters:

```scala
val unsafeForExactMoney = 0.1 + 0.2
val exactDecimal = BigDecimal("0.1") + BigDecimal("0.2")
```

## 6. Common Scala types

| Scala type | Typical use |
| --- | --- |
| `String` | Text |
| `Int` | 32-bit integer |
| `Long` | 64-bit integer, often used for large counts and identifiers |
| `Double` | Approximate floating-point measurement |
| `BigDecimal` | Decimal values such as money |
| `Boolean` | `true` or `false` |
| `Unit` | No meaningful return value |
| `Array[T]` | Mutable fixed-size JVM array; command-line arguments use `Array[String]` |
| `List[T]` | Immutable linked sequence |
| `Vector[T]` | Immutable indexed sequence |
| `Set[T]` | Unique values |
| `Map[K, V]` | Key-value associations |
| `Option[T]` | Either `Some(value)` or `None` |

Scala also has broad types such as `Any`, `AnyVal`, and `AnyRef`, plus the bottom type `Nothing`. You do not need to master the full type hierarchy before writing useful data transformations.

## 7. Methods, functions, and expressions

### A method declared with `def`

```scala
def calculateSalesAmount(quantity: Int, unitPrice: BigDecimal): BigDecimal = {
  quantity * unitPrice
}
```

Scala returns the last expression in a block. An explicit `return` is usually unnecessary.

```scala
val amount = calculateSalesAmount(2, BigDecimal("19.95"))
println(amount) // 39.90
```

### A function stored as a value

```scala
val isPositiveQuantity: Int => Boolean = quantity => quantity > 0

println(isPositiveQuantity(4))  // true
println(isPositiveQuantity(-1)) // false
```

`Int => Boolean` means “a function that accepts an `Int` and produces a `Boolean`.” Passing functions to `map`, `filter`, and other transformations is central to Scala and Spark.

### `if` is an expression

```scala
val qualityLabel = if (rowCount > 0) "non-empty" else "empty"
```

The `if` expression produces a value, so a separate mutable variable is unnecessary.

## 8. Case classes: Scala's data records

A case class is similar to a Kotlin data class:

```scala
case class Sale(
  orderNumber: Int,
  productNumber: String,
  quantity: Int,
  unitPrice: BigDecimal
) {
  def salesAmount: BigDecimal = quantity * unitPrice
}
```

Create and use a value:

```scala
val sale = Sale(1001, "S10_1678", 2, BigDecimal("19.95"))

println(sale.productNumber)
println(sale.salesAmount)
```

Case classes provide useful data-oriented behavior:

- Constructor parameters are public immutable fields by default.
- Equality compares field values.
- `toString` is useful for inspection.
- `copy` creates a modified copy without mutating the original.
- Pattern matching can extract their fields.

```scala
val corrected = sale.copy(quantity = 3)

println(sale.quantity)      // 2
println(corrected.quantity) // 3
```

Case classes are useful for typed records, but a case class alone does not validate data, distribute computation, or define a durable table schema.

## 9. Immutable collections and ETL-style transformations

```scala
val quantities = List(2, 0, 4, -1, 3)

val validQuantities = quantities.filter(_ > 0)
val doubledQuantities = validQuantities.map(_ * 2)

println(quantities)          // List(2, 0, 4, -1, 3)
println(validQuantities)     // List(2, 4, 3)
println(doubledQuantities)   // List(4, 8, 6)
```

The original list is unchanged. Each transformation returns another collection.

### Common collection operations

| Operation | Purpose | Possible data-engineering interpretation |
| --- | --- | --- |
| `map` | Convert every input element into one output element | Normalize or derive a field |
| `filter` | Keep elements that satisfy a predicate | Retain valid rows |
| `flatMap` | Produce zero, one, or many outputs per input | Parse optional rows or explode nested values |
| `groupBy` | Build groups by a key | Prepare for aggregation |
| `foldLeft` | Accumulate values into one result | Total or build state |
| `distinctBy` | Keep one element for each derived key | Simple local deduplication |
| `sortBy` | Order a local collection | Produce deterministic display output |

Strict Scala collections such as `List` perform these transformations locally in the current JVM. That is not the same execution model as a lazy, partitioned Spark DataFrame.

## 10. `Option`: an explicit missing value

Kotlin commonly represents a missing string as `String?`. Idiomatic Scala application code often uses `Option[String]`:

```scala
val shippingDate: Option[String] = Some("2026-09-23")
val missingShippingDate: Option[String] = None
```

Transform an existing value only when it is present:

```scala
val normalizedDate = shippingDate.map(_.trim)
```

Supply a fallback:

```scala
val displayDate = missingShippingDate.getOrElse("not shipped")
```

Avoid calling `.get` because it throws when the value is `None`:

```scala
// Avoid: fails when the Option is None.
val unsafeDate = missingShippingDate.get

// Prefer: choose explicit behavior for the missing case.
val safeDate = missingShippingDate.getOrElse("not shipped")
```

String parsing methods can produce an `Option`:

```scala
val validQuantity = "12".toIntOption        // Some(12)
val invalidQuantity = "twelve".toIntOption // None
```

`Option` is not a universal replacement for SQL `NULL`. Spark DataFrames follow SQL null semantics, so DataFrame code normally uses column expressions such as `isNull`, `isNotNull`, and `coalesce`. A typed Spark `Dataset` may use `Option` in its record type.

## 11. Pattern matching

Pattern matching is Scala's more powerful counterpart to Kotlin `when`:

```scala
def describeQuantity(quantity: Int): String = quantity match {
  case value if value < 0 => "invalid"
  case 0                  => "empty"
  case 1                  => "single item"
  case _                  => "multiple items"
}
```

Match an `Option`:

```scala
def displayCustomer(customerId: Option[Int]): String = customerId match {
  case Some(id) => s"customer=$id"
  case None     => "customer is missing"
}
```

The compiler can help check whether matches over sealed types and enums cover every possible case.

## 12. Classes, objects, traits, and companion objects

| Construct | Meaning | Common use |
| --- | --- | --- |
| `class` | Blueprint for multiple instances | Stateful service or domain behavior |
| `case class` | Value-oriented class with generated data behavior | Immutable records |
| `object` | One singleton instance | Entry point, constants, stateless helpers |
| `trait` | Reusable contract and optional behavior | Interface or capability |

Example class and trait:

```scala
trait Formatter {
  def format(value: BigDecimal): String
}

class CurrencyFormatter(symbol: String) extends Formatter {
  override def format(value: BigDecimal): String = s"$symbol$value"
}
```

A class and object may share a name. The object is then called the class's companion object and can hold construction or validation helpers:

```scala
case class CustomerId(value: Int)

object CustomerId {
  def from(raw: String): Option[CustomerId] = {
    raw.trim.toIntOption
      .filter(_ > 0)
      .map(CustomerId.apply)
  }
}
```

Companions can access private members of each other, but they are still different things: the class describes instances, while the object is the singleton companion.

## 13. A small local sales-cleaning pipeline

This example practices Scala syntax with a small in-memory collection. It does not use Spark yet.

```scala
import scala.util.Try

object SalesCleaning {
  case class RawSale(
    orderNumber: String,
    productNumber: String,
    orderStatus: String,
    quantity: String,
    unitPrice: String
  )

  case class CleanSale(
    orderNumber: Int,
    productNumber: String,
    orderStatus: String,
    quantity: Int,
    unitPrice: BigDecimal
  ) {
    def salesAmount: BigDecimal = quantity * unitPrice
  }

  def parsePositiveInt(raw: String): Option[Int] = {
    raw.trim.toIntOption.filter(_ > 0)
  }

  def parsePositiveMoney(raw: String): Option[BigDecimal] = {
    Try(BigDecimal(raw.trim)).toOption.filter(_ > 0)
  }

  def normalizeStatus(raw: String): String = {
    raw.trim.toLowerCase.capitalize
  }

  def clean(raw: RawSale): Option[CleanSale] = {
    for {
      orderNumber <- raw.orderNumber.trim.toIntOption
      quantity <- parsePositiveInt(raw.quantity)
      unitPrice <- parsePositiveMoney(raw.unitPrice)
      productNumber = raw.productNumber.trim
      if productNumber.nonEmpty
    } yield CleanSale(
      orderNumber = orderNumber,
      productNumber = productNumber,
      orderStatus = normalizeStatus(raw.orderStatus),
      quantity = quantity,
      unitPrice = unitPrice
    )
  }

  def main(args: Array[String]): Unit = {
    val rawSales = List(
      RawSale("1001", "S10_1678", " shipped ", "2", "19.95"),
      RawSale("1001", "S10_1678", "SHIPPED", "2", "19.95"),
      RawSale("1002", "S10_1949", "cancelled", "1", "10.00"),
      RawSale("1003", "S12_1099", "shipped", "bad", "5.00"),
      RawSale("1004", " ", "shipped", "3", "8.50")
    )

    val attempted = rawSales.map(raw => (raw, clean(raw)))
    val validBeforeDedup = attempted.flatMap { case (_, result) => result }
    val rejected = attempted.collect { case (raw, None) => raw }
    val cleaned = validBeforeDedup.distinctBy(sale => (sale.orderNumber, sale.productNumber))
    val duplicateCount = validBeforeDedup.size - cleaned.size

    val totalsByStatus = cleaned
      .groupBy(_.orderStatus)
      .map { case (status, rows) =>
        status -> rows.map(_.salesAmount).sum
      }

    println(s"Source rows:    ${rawSales.size}")
    println(s"Cleaned rows:   ${cleaned.size}")
    println(s"Rejected rows:  ${rejected.size}")
    println(s"Duplicate rows: $duplicateCount")

    totalsByStatus.toSeq.sortBy(_._1).foreach { case (status, total) =>
      println(s"$status -> $total")
    }

    require(rawSales.size == cleaned.size + rejected.size + duplicateCount)
  }
}
```

Expected summary:

```text
Source rows:    5
Cleaned rows:   2
Rejected rows:  2
Duplicate rows: 1
Cancelled -> 10.00
Shipped -> 39.90
```

### Trace the data flow

1. `rawSales` owns five untrusted input records.
2. `map` attempts to clean each input while retaining the original beside the result.
3. `flatMap` keeps the successful `Some(CleanSale)` values and removes the `None` wrappers.
4. `collect` uses a partial function to retain the rejected raw rows.
5. `distinctBy` performs local deduplication using `(orderNumber, productNumber)` as the candidate grain.
6. `groupBy` and `map` calculate totals by normalized status.
7. `require` checks the reconciliation invariant: every input became a cleaned row, rejected row, or duplicate.

This example retains rejected records in memory, but it does not explain why each row failed. A production design would attach a reason such as `INVALID_QUANTITY` or `MISSING_PRODUCT_NUMBER` and publish rejected records to a durable quarantine dataset.

### Important `collect` warning

The word `collect` is overloaded:

- On a local Scala collection, `collect { case ... => ... }` filters and transforms values with a partial function.
- On a Spark Dataset or DataFrame, `collect()` is an action that transfers all result rows to the driver.

Calling Spark `collect()` on a large dataset can exhaust driver memory. Similar names do not guarantee similar execution behavior.

## 14. Local Scala collections versus Spark

The syntax can look similar while the execution model is completely different.

| Question | Local `List[Sale]` | Spark DataFrame or Dataset |
| --- | --- | --- |
| Where is the data? | Current JVM heap | Partitioned across executors |
| When does `map` or `filter` run? | Immediately for a strict collection | Lazily after an action requests work |
| Who schedules work? | Current thread/application | Spark driver schedules tasks |
| What happens during `groupBy`? | Builds local in-memory groups | Usually causes a distributed shuffle |
| What does failure mean? | Local exception normally stops the operation | Tasks may be retried on another executor |
| Can a closure use surrounding state freely? | It remains in the same JVM | Captured state must be serialized and sent to executors |
| How is ordering handled? | A sequence has local element order | Global ordering requires explicit distributed work |
| What limits result size? | Process memory | Executor memory, network, shuffle, storage, and driver limits |

Functional transformations are a useful conceptual bridge to Spark, but do not infer cost, ordering, retry, or memory behavior from a local collection.

## 15. From a Scala method to a Spark column expression

Local Scala code executes normal JVM operations on a value:

```scala
val amount = sale.quantity * sale.unitPrice
```

Spark DataFrame code builds an expression in a lazy query plan:

```scala
import org.apache.spark.sql.functions.col

val cleaned = source
  .filter(col("quantity") > 0)
  .withColumn("sales_amount", col("quantity") * col("unit_price"))
```

`col("quantity") * col("unit_price")` does not immediately multiply one pair of Scala values. It describes work for Spark to execute later across partitions.

Typed Dataset code can look more like local Scala:

```scala
case class Sale(quantity: Int, unitPrice: BigDecimal)

val validSales = salesDataset.filter(sale => sale.quantity > 0)
```

The lambda still runs as distributed executor work after an action. It is not an ordinary local collection filter.

Prefer built-in DataFrame functions for most Spark transformations because Spark can inspect and optimize those expressions. Use typed methods when their type safety and domain modeling provide a clear benefit.

## 16. Scala and Spark version compatibility

Scala libraries encode the Scala binary version in their artifact names. For example:

```text
spark-sql_2.13
```

The `_2.13` suffix means the artifact was built for Scala 2.13 binary compatibility. Spark 3.5.9's official Scala 2.13 profile uses Scala 2.13.8, so this project pins the same compiler version.

The installed versions on this machine are:

```text
HelloWorld Scala: 2.13.8
HelloWorld Spark SQL dependency: 3.5.9
Shell spark-submit runtime: Spark 3.5.9 with Scala 2.13.8
Java: 17.0.16
```

The essential settings for this Spark 3.5.9 project are:

```scala
ThisBuild / scalaVersion := "2.13.8"

val sparkVersion = "3.5.9"

lazy val root = (project in file("."))
  .settings(
    name := "scala-spark-intro",
    libraryDependencies += "org.apache.spark" %% "spark-sql" % sparkVersion,
    Compile / run / fork := true,
    Compile / run / javaOptions += "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED"
  )
```

In an sbt dependency:

```text
"organization" %% "artifact" % "version"
```

`%%` appends the project's Scala binary version to the artifact name. With Scala 2.13, `spark-sql` resolves as `spark-sql_2.13`.

The dependency has no `Provided` scope because this project runs Spark locally through IntelliJ or `sbt run`. Adding `% Provided` removes Spark from that runtime classpath and causes `NoClassDefFoundError: org/apache/spark/sql/SparkSession$`. Use `Provided` later only when a matching Spark installation or cluster supplies Spark while running the packaged JAR.

The forked JVM receives `--add-opens=java.base/sun.nio.ch=ALL-UNNAMED` so Spark 3.5.9 can start under Java 17. The sbt setting applies to `sbt run`; a direct IntelliJ Application run configuration needs the same value in its VM options.

Always check the target Spark runtime before selecting `scalaVersion` and dependency coordinates:

```bash
spark-submit --version
```

## 17. Shape of a packaged Scala Spark job

This is a later-step skeleton that can be added to the Scala 2.13 project after the language exercises:

```scala
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.{col, trim}

object SalesJob {
  def main(args: Array[String]): Unit = {
    require(args.length == 2, "Usage: SalesJob <input-path> <output-path>")

    val inputPath = args(0)
    val outputPath = args(1)

    val spark = SparkSession.builder()
      .appName("SalesJob")
      .getOrCreate()

    try {
      val source = spark.read
        .option("header", "true")
        .csv(inputPath)

      val cleaned = source
        .withColumn("product_number", trim(col("product_number")))
        .withColumn("quantity", col("quantity").cast("int"))
        .withColumn("unit_price", col("unit_price").cast("decimal(12,2)"))
        .filter(
          col("product_number").isNotNull &&
          col("product_number") =!= "" &&
          col("quantity") > 0 &&
          col("unit_price") > 0
        )
        .withColumn("sales_amount", col("quantity") * col("unit_price"))

      cleaned.write
        .mode("overwrite")
        .parquet(outputPath)
    } finally {
      spark.stop()
    }
  }
}
```

The `HelloWorld` homework project is packaged with sbt and then launched with the matching Spark 3.5.9 / Scala 2.13 `spark-submit`. Because that installation is on the shell `PATH`, the submission command has the usual form your instructor uses.

```bash
cd /Users/richardwilkerson/IdeaProjects/HelloWorld

# In IntelliJ's sbt task window, run clean and then package first.

source .env

spark-submit \
  --class HelloWorld \
  --master "local[*]" \
  --packages org.postgresql:postgresql:42.7.7 \
  target/out/jvm/scala-2.13.8/helloworld/helloworld_2.13-0.1.0-SNAPSHOT.jar
```

`sbt package` creates a thin application JAR. The matching `spark-submit` supplies Spark's own runtime libraries, while `--packages` adds the PostgreSQL JDBC driver to the driver and executor classpaths. In a production job, let the submission command or cluster configuration select the master instead of hard-coding `local[*]` in application source.

The project `.env` selects the Spark 3.5.9 installation, adds its `bin` directory to `PATH`, loads the existing local PostgreSQL configuration, and explicitly exports `POSTGRES_PASSWORD` for the child `spark-submit` process. It is listed in the project's `.gitignore`, so machine-specific configuration cannot be committed accidentally.

This exact local submission was verified on 2026-09-24 with Spark 3.5.9, Scala 2.13.8, Java 17.0.16, and PostgreSQL JDBC 42.7.7. The process read all ten migration tables, completed the homework filters, joins, aggregations, and median analysis, and exited with code 0.

## 18. Big-data design habits Scala should reinforce

### Prefer immutable input-to-output transformations

Spark may retry tasks. A transformation that only derives an output value from its input is easier to retry and reason about than code that mutates shared state or performs an external side effect.

### Model records explicitly

Case classes can document typed record boundaries. Spark schemas and external table contracts still need their own validation because JVM types do not prove that a CSV, Parquet file, JDBC source, or catalog table actually conforms.

### Preserve invalid records

`Option` and `flatMap` make it easy to drop failed parses. That convenience can hide data loss. Count and preserve rejected records with a reason when completeness matters.

### Treat numeric types as business decisions

Choose integer widths and decimal precision from the data contract. Do not use `Double` for exact currency simply because multiplication is easy.

### Keep executor code self-contained

A Spark closure may be serialized and executed in a different JVM. Avoid capturing non-serializable services, open database connections, large driver objects, or mutable state.

### Verify distributed behavior with evidence

Local collection output proves language logic on a bounded fixture. It does not prove Spark partitioning, shuffle behavior, executor memory safety, fault recovery, or production performance.

## 19. Common pitfalls

### Saying Scala always requires explicit types

Scala performs type inference. Use explicit types where they clarify public or data boundaries, not as mandatory noise on every local value.

### Using `var` for every intermediate result

Prefer `val` plus transformations. Immutability makes lineage and retry behavior easier to reason about.

### Mixing the Spark 3.5.9 project with the Spark 4.2.0 command-line runtime

Both use the Scala 2.13 binary line, but they are different Spark versions. Compile and submit against the same Spark version to avoid API, linkage, serialization, or behavior mismatches.

### Treating `Option` as permission to silently lose rows

Turning an invalid record into `None` and calling `flatMap` removes it. Reconcile counts and retain rejected records when the data contract requires completeness.

### Treating local `groupBy` as evidence about a Spark `groupBy`

The local operation builds groups in one JVM. Spark normally redistributes keys across a network shuffle.

### Calling Spark `collect()` for large output

Spark `collect()` sends every result row to the driver. Use bounded inspection such as `show()` or write the distributed result to an appropriate sink.

### Printing inside executor transformations

Output from executor-side `println` calls appears in executor logs, may repeat after task retries, and is not a reliable result sink.

### Editing `target/`

Generated outputs will be overwritten. Make changes in `src/`, `build.sbt`, or `project/` as appropriate.

## 20. Practice in `HelloWorld`

Complete these in order. Keep the project on Scala 2.13.8 so the exercises and later Spark 3.5.9 work use one consistent compiler.

### Exercise 2: case class and derived value

Create a `Sale` case class with `quantity`, `unitPrice`, and a calculated `salesAmount` method.

### Exercise 3: immutable transformations

Create a list of sales, remove nonpositive quantities, calculate amounts, and sum the result.

### Exercise 4: safe parsing

Convert a list of quantity strings with `toIntOption`. Count both valid and rejected values.

### Exercise 5: local ETL

Run the complete `SalesCleaning` example. Add one new malformed row and predict which count changes before running it.

### Exercise 6: preserve rejection reasons

Replace `Option[CleanSale]` with a result that retains a reason. A useful next type is:

```scala
Either[String, CleanSale]
```

Use `Left(reason)` for rejection and `Right(cleanSale)` for success.

## 21. Knowledge check

1. What is the difference between `val` and `var`?
2. When can Scala infer a type, and when is an explicit type still useful?
3. Why is `HelloWorld` an object, and what actually makes it runnable?
4. How is a case class similar to a Kotlin data class?
5. What is the difference between a method declared with `def` and a function stored in a `val`?
6. Why is `Option` safer than immediately dereferencing a nullable value?
7. What information is lost when invalid inputs become `None` and are removed with `flatMap`?
8. Why can a local `List.groupBy` not predict the cost of Spark `groupBy`?
9. What is the difference between collection `collect { case ... }` and Spark `collect()`?
10. Why should a Spark 3.5.9 project use both the matching Scala binary line and a matching Spark 3.5.9 runtime?
11. What does `%%` do in an sbt dependency?
12. Why should Spark executor transformations avoid external side effects?

## Key takeaways

- Scala should feel familiar from Kotlin, but its functional and expression-oriented APIs deserve deliberate practice.
- Scala infers many types; explicit types remain valuable at public, schema, and numeric boundaries.
- An `object` is a singleton, while `main` is the entry point that makes the object runnable.
- `val`, immutable collections, case classes, functions, `Option`, and pattern matching form the most useful beginner foundation.
- Local collection transformations help explain data flow, but Spark adds lazy plans, partitions, shuffles, serialization, retries, and distributed failure.
- A Spark application must match the Scala binary version of its Spark runtime.
- Safe parsing is incomplete unless valid, rejected, and duplicate counts reconcile.

## Resources

- [Wednesday: Scala Spark DataFrame API](./3.2_Wed_Scala_Spark_API.md)
- [Scala 3 Book and learning resources](https://docs.scala-lang.org/)
- [Tour of Scala: basics](https://docs.scala-lang.org/tour/basics.html)
- [Tour of Scala: case classes](https://docs.scala-lang.org/tour/case-classes.html)
- [sbt build definition basics](https://www.scala-sbt.org/2.x/docs/en/guide/build-definition-basics.html)
- [Apache Spark 3.5.9 documentation](https://spark.apache.org/docs/3.5.9/)
- [Apache Spark 3.5.9 Scala API](https://spark.apache.org/docs/3.5.9/api/scala/org/apache/spark/)



# Continued Lecture Notes

creating a jar file to be executed anywhere

what is an artifact?
- asset is more or less the same thing
- build artifacts 
    - file -> project structure -> artifacts -> click the plus -> then select JAR -> from modules with dependencies -> opens Create JAR from Modules screen
    - specify module (select module with the main entry point), main class (entry point), manifest.MF (tells JVM what is needed for the project to build)
    - click apply -> ok
    - then go to build menu -> build artifact -> select the artifact you just created -> this will then create an `out/` dir.
    - now we can go to the root of the jar in our terminal to run the file: `java -jar HelloWorld.main.jar`
- you will need to rebuild the jar when changes are made



dependencies
- build.sbt
- go to maven repository, this is where we can find dependencies
    - note do not use Spark Core -> use Spark SQL. stick with v 3.5, 4 is still getting compatibility figured out. click the version that matches your scala version
    - get the SBT -> copy and then paste it in the build.sbt
    - then click the sbt on the ide right sidebar -> sync all sbt projects
    - if you get a build error, a typical first step is removing the "provided" at the end of the dependency is what the instructor said. 
