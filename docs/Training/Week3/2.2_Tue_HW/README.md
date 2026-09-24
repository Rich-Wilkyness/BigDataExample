# Homework Assignment: Build a Basic PySpark ETL Pipeline

## Objective

Build and demonstrate a basic **ETL (Extract, Transform, Load) pipeline using PySpark**.

Your pipeline must extract data from PostgreSQL, perform meaningful data-cleaning transformations, and load the resulting data into Hive.

The goal is to produce a repeatable pipeline that demonstrates:

```text
PostgreSQL
    |
    | Extract
    v
PySpark
    |
    | Clean / Transform
    v
Hive
```

## Requirements

### 1. Extract Data from PostgreSQL

Create a PySpark application that:

* Connects to PostgreSQL using JDBC.
* Reads at least one source table into a Spark DataFrame.
* Successfully retrieves the source data.
* Displays or otherwise verifies the source data and schema.

Do not hard-code passwords directly into the Python source code.

### 2. Inspect the Source Data

Identify potential data-quality problems in the source data.

Examples include:

* Duplicate records
* NULL values
* Missing identifiers
* Inconsistent capitalization
* Leading or trailing whitespace
* Incorrect data types
* Invalid dates
* Negative or impossible numeric values
* Inconsistent categorical values

### 3. Clean and Transform the Data

Use PySpark to perform at least **four meaningful data-cleaning or transformation operations**.

Your pipeline should demonstrate techniques such as:

* Removing duplicate records
* Handling or removing NULL values
* Standardizing text values
* Converting columns to appropriate data types
* Validating numeric values
* Handling invalid dates
* Filtering invalid records

For example, values such as:

```text
usa
USA
USA
Usa
```

could be standardized to:

```text
USA
```

### 4. Add a Derived or ETL Column

Create at least one useful column that did not exist in the original data.

Examples include:

```text
total_amount = quantity * unit_price
```

or:

```text
processed_at = ETL processing timestamp
```

### 5. Load the Result into Hive

Write the transformed DataFrame into a Hive table.

For example:

```text
PostgreSQL bronze.sales
        |
        v
      PySpark
        |
        v
Hive silver.sales
```

The resulting Hive table must be independently queryable through Hive/Beeline.

### 6. Validate the Pipeline

Demonstrate that the transformation actually changed or improved the source data.

At minimum, compare:

```text
Source row count
        vs.
Cleaned row count
```

Also verify at least two additional data-quality improvements, such as:

* Duplicates were removed.
* Required fields no longer contain NULLs.
* Invalid quantities were removed.
* Text values are consistently formatted.
* Dates have been converted correctly.
* Derived values were calculated correctly.

---

# Formal Deliverable

Submit **one ZIP file containing screenshots demonstrating your completed ETL pipeline**.

Name the file:

```text
firstname_lastname_etl_evidence.zip
```

The ZIP should contain screenshots showing the following:

### PostgreSQL Evidence

Include screenshot(s) showing:

* The source PostgreSQL table.
* A sample of the source records.
* The source row count.

For example:

```sql
SELECT * FROM bronze.sales;
SELECT COUNT(*) FROM bronze.sales;
```

### Spark Evidence

Include screenshot(s) showing:

* Your PySpark ETL job executing successfully.
* The source DataFrame being read.
* The cleaned/transformed DataFrame.
* Source and destination row counts where appropriate.
* Evidence that the Hive write completed successfully.

Your screenshots should make it possible to see that Spark actually performed transformations rather than simply copying the data.

### Hive Evidence

Include screenshot(s) from Hive/Beeline showing that the resulting table exists and can be queried.

For example:

```sql
USE silver;

SHOW TABLES;

DESCRIBE sales;

SELECT COUNT(*) FROM sales;

SELECT * FROM sales;
```

The Hive results should visibly demonstrate the effects of your Spark transformations.

---

# Live Demonstration

Be prepared to demonstrate your pipeline during class.

You may be asked to:

1. Show the original PostgreSQL data.
2. Explain the transformations in your PySpark job.
3. Run the ETL pipeline.
4. Show the resulting Hive table.
5. Compare the PostgreSQL source with the Hive result.
6. Identify records that were removed or changed and explain why.
7. Explain how duplicate, NULL, malformed, or otherwise invalid records are handled.

The pipeline should be repeatable. Running the ETL job again should not accidentally produce duplicate copies of existing data.

---

# Submission

Submit:

**`firstname_lastname_etl_evidence.zip`**

The ZIP should contain **screenshots only**. You do not need to submit your source code as part of the ZIP.

Your screenshots must provide sufficient evidence to demonstrate:

```text
PostgreSQL source
        ↓
PySpark extraction
        ↓
Data cleaning / transformation
        ↓
Hive load
        ↓
Successful Hive query
```

Your actual code and environment must remain available on your machine for the **live demonstration**.