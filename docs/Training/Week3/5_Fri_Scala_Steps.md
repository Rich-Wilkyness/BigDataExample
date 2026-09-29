# Original Friday Scala notes

> The structured two-part lab built from these notes is now the [WH-M02 interactive notebook](../../../notebooks/interactive-data-engineering-labs/retail-sales/wh-m02-scala-spark-postgres-to-hive.ipynb). The original notes and instructor example remain below as source material.

goal of the weekend homework is to take our bronze postgres and use scala spark to move it to hive silver. then upgrade the silver to gold, just like we did with python


keep track of invalid records and add them to a new table i think, so we can inspect them and figure out what needs to be cleaned and transformed

left anti join of bronze postgres and silver hive
- check what is in bronze and does not exist in hive yet


perform silver transformations
- withcolumn customer_name
- clean/trim
    - bad dates
    - bad quantity
    - bad unit_price
    - duplicate orders
- withcolumn country

- take clean data and append to silver.sales

normalize transaction_id

deal with duplications



what he has done so far:

In my live demo, I was able to build an ETL job that appended data from Bronze in Postgres into Silver in Hive - BUT it led to duplicate data. 


Your homework is to:
If your postgres -> hive pipeline is not working right now, make it fully functional
Fix the issue with deduplication - you should be able to run generate_sales.py, then run the spark job, then select from the silver table in Hive, and note that the row count has increased AND that no duplicate records have been added


```scala
import org.apache.spark.sql.{SparkSession,DataFrame}
import org.apache.spark.sql.functions._
import java.util.Properties

object HelloWorld {
  def main(args: Array[String]): Unit = {
    val spark = SparkSession
      .builder
      .master("local[*]")
      .appName("Test Scala App")
      .config(
        "hive.metastore.uris",
        "thrift://localhost:9083"
      )
      .config(
        "spark.sql.hive.metastore.version",
        "3.1.3"
      )
      .config(
        "spark.sql.hive.metastore.jars",
        "maven"
      )
      .enableHiveSupport()
      .getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")

    val JDBC_URL = "jdbc:postgresql://localhost:5432/sample_database"

    val jdbcProperties = new Properties()

    jdbcProperties.setProperty("user", "evan")
    jdbcProperties.setProperty("password", sys.env("PG_PASSWORD"))
    jdbcProperties.setProperty("driver", "org.postgresql.Driver")

    def readPostgres(table: String): DataFrame = {
      spark.read.jdbc(
        JDBC_URL,
        table,
        jdbcProperties
      )
    }

    val bronze = readPostgres("bronze.sales")
    val silver = readPostgres("silver.sales")

    val customerTable = readPostgres("gold.dim_customer")
    val dateTable = readPostgres("gold.dim_date")
    val departmentTable = readPostgres("gold.dim_department")
    val employeeTable = readPostgres("gold.dim_employee")
    val officeTable = readPostgres("gold.dim_office")
    val productTable = readPostgres("gold.dim_product")
    val factPaymentTable = readPostgres("gold.fact_payment")
    val factSalesTable = readPostgres("gold.fact_sales")

//    bronze.show()
//    silver.show()
//    customerTable.show()
//    dateTable.show()
//    departmentTable.show()
//    employeeTable.show()
//    officeTable.show()
//    productTable.show()
//    factPaymentTable.show()
//    factSalesTable.show()

    val silverHive = spark.table("silver.sales")


    val newRecords =
      bronze.join(
        silverHive.select("transaction_id"),
        Seq("transaction_id"),
        "left_anti"
      )

    println("New records in Bronze:")
    newRecords.show(false)

    println(" ")

    println(
      s"New transactions: ${newRecords.count()}"
    )



//    val newRecords = bronze
//
//    println("Initial Bronze records:")
//    newRecords.show(false)
//
//    println(
//      s"Records before cleaning: ${newRecords.count()}"
//    )
//
//    println(" ")


//    val standardized =
//      bronze.withColumn(
//        "transaction_id",
//        when(
//          col("transaction_id").rlike("^[0-9]+$"),
//          concat(
//            lit("T"),
//            lpad(col("transaction_id"), 3, "0")
//          )
//        ).otherwise(col("transaction_id"))
//      )

    val standardized =
      newRecords.withColumn(
        "transaction_id",
        when(
          col("transaction_id").rlike("^[0-9]+$"),
          concat(
            lit("T"),
            lpad(col("transaction_id"), 3, "0")
          )
        ).otherwise(col("transaction_id"))
      )

//    println("Standardized ID table")
//    standardized.show()


    val deduplicated =
      standardized.dropDuplicates("transaction_id")

//    println("Deduplicated Table")
//    deduplicated.show()

    val cleaned =
      deduplicated
        .withColumn(
          "category",
          initcap(trim(col("category")))
        )
        .withColumn(
          "country",
          upper(trim(col("country")))
        )
        .withColumn(
          "customer_name",
          trim(col("customer_name"))
        )
        .withColumn(
          "product",
          trim(col("product"))
        )

        // Temporary validation column
        .withColumn(
          "parsed_date",
          to_date(
            col("transaction_date"),
            "yyyy-MM-dd"
          )
        )

        // Use Double instead of Decimal for this test
        .withColumn(
          "parsed_price",
          col("unit_price").cast("double")
        )

        .withColumn(
          "quantity",
          col("quantity").cast("int")
        )

    val invalidRecords =
      cleaned.filter(
        col("transaction_date").isNull ||
          col("unit_price").isNull ||
          col("quantity").isNull ||
          col("quantity") <= 0 ||
          col("unit_price") <= 0
      )

//    println("Invalid records:")
//    invalidRecords.show(false)


    val validRecords =
      cleaned
        .filter(
          col("parsed_date").isNotNull &&
            col("parsed_price").isNotNull &&
            col("quantity").isNotNull &&
            col("quantity") > 0 &&
            col("parsed_price") > 0
        )

        // Keep the original date as STRING
        .drop("parsed_date")

        // Replace original string price with numeric price
        .drop("unit_price")
        .withColumnRenamed(
          "parsed_price",
          "unit_price"
        )


    println("Valid records for Silver:")
    validRecords.show(false)

    println("Schema being written:")
    validRecords.printSchema()

    println("Records being written:")
    validRecords.show(false)

    println(s"Count: ${validRecords.count()}")


//    validRecords.write
//      .mode("overwrite")
//      .parquet("/tmp/silver_sales_test")

    val testRead =
      spark.read.parquet("/tmp/silver_sales_test")

    println("Spark reading its own Parquet:")
    testRead.show(false)
    testRead.printSchema()

    validRecords.write
      .mode("append")
      .format("parquet")
      .saveAsTable("silver.sales")







    // Code to identify duplicates - commented out because none at the moment
//    val exactDuplicates =
//      deduplicated
//        .groupBy(bronze.columns.map(col): _*)
//        .count()
//        .filter(col("count") > 1)
//
//    println("Exact Duplicates Table:")
//    exactDuplicates.show(false)




//    bronze.write
//  .mode("overwrite")
//  .saveAsTable("bronze.sales")
//
//
//    silver.write
//  .mode("overwrite")
//  .saveAsTable("silver.sales")

//    customerTable.write
//  .mode("overwrite")
//  .saveAsTable("gold.dim_customer")
//
//    dateTable.write
//  .mode("overwrite")
//  .saveAsTable("gold.dim_date")
//    departmentTable.write
//  .mode("overwrite")
//  .saveAsTable("gold.dim_department")
//    employeeTable.write
//  .mode("overwrite")
//  .saveAsTable("gold.dim_employee")
//    officeTable.write
//  .mode("overwrite")
//  .saveAsTable("gold.dim_office")
//    productTable.write
//  .mode("overwrite")
//  .saveAsTable("gold.dim_product")
//    factPaymentTable.write
//  .mode("overwrite")
//  .saveAsTable("gold.fact_payment")
//    factSalesTable.write
//  .mode("overwrite")
//  .saveAsTable("gold.fact_sales")

    spark.stop()
  }
}


```
