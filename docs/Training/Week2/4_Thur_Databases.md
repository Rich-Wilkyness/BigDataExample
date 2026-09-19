# Thursday: Databases, OLAP, and Data Warehouses

This guide combines the data warehouse preparation material with the notes from Thursday's lecture. It starts with the difference between operational and analytical databases, builds a small dimensional model, and then connects those ideas to modern analytical platforms.

## Learning goals

By the end of this lesson, you should be able to:

- Explain the difference between OLTP and OLAP workloads.
- Describe why organizations build data warehouses.
- Identify the grain, facts, and dimensions in a business process.
- Compare star, snowflake, and galaxy schemas.
- Explain normalization through 1NF, 2NF, 3NF, and BCNF.
- Explain surrogate keys and Slowly Changing Dimension Types 0, 1, and 2.
- Trace data through Bronze, Silver, and Gold layers.
- Compare ETL with ELT and explain where data-quality failures belong.
- Describe when PostgreSQL is enough and why specialized analytical systems exist.
- Distinguish object storage, a query engine, a table format, a data warehouse, and a lakehouse platform.

---

## 1. What is a data warehouse?

A **data warehouse** is a data system designed primarily for analysis rather than for running day-to-day application transactions.

The simplest distinction is:

> **Application database:** What is happening right now?
>
> **Data warehouse:** What has happened over time, and what can we learn from it?

Imagine an online store. Its application database might contain:

```text
customers
orders
order_details
products
payments
```

The application often needs a small, targeted query:

```sql
SELECT *
FROM orders
WHERE order_number = 10401;
```

An analyst might instead ask:

> For each product category, what was our monthly revenue for the last three years, compared with the previous month and the previous year?

That question may require millions or billions of rows to be joined, scanned, aggregated, and sorted. A data warehouse is designed for this kind of workload.

### OLTP and OLAP

**OLTP** means **Online Transaction Processing**. **OLAP** means **Online Analytical Processing**.

| Concern | OLTP: operational system | OLAP: analytical system |
| --- | --- | --- |
| Main purpose | Run the business | Analyze the business |
| Typical operation | Insert or update a few rows | Scan and aggregate many rows |
| Typical question | Did order 10401 ship? | How did monthly revenue change by region? |
| Data | Current, detailed application state | Historical data from one or more systems |
| Design priority | Fast, reliable transactions | Fast analytical reads and calculations |
| Common modeling style | More normalized | Often dimensional and intentionally denormalized |

OLAP systems are not simply "slower databases." They are usually less focused on frequent row-by-row transactions and more focused on reading many rows efficiently for reporting, mathematical analysis, data science, and machine learning.

### Data-driven decisions

A **data-driven decision** uses collected and analyzed evidence instead of relying only on intuition or personal experience. Reliable data does not make a decision automatically, but it makes the assumptions and tradeoffs easier to explain, test, and defend.

---

## 2. Where does warehouse data come from?

Warehouse data usually comes from several operational systems:

```text
PostgreSQL application DB ──┐
                            │
Salesforce ─────────────────┤
                            │
Website / mobile events ────┼──> ETL / ELT ──> DATA WAREHOUSE ──> BI / Analytics
                            │
CSV / Excel files ──────────┤
                            │
APIs ───────────────────────┘
```

The warehouse becomes a central analytical repository:

```text
                    ┌─────────────────────┐
                    │   DATA WAREHOUSE    │
                    │                     │
                    │  fact_sales         │
                    │  dim_customer       │
                    │  dim_product        │
                    │  dim_date           │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
          Power BI          Tableau          Python
```

This is why joins, aggregations, CTEs, window functions, indexing, and query plans matter to data engineers: analytical workloads use them constantly.

### From warehouse tables to charts

The warehouse prepares consistent data; a visualization tool helps people explore and communicate it. A dashboard normally queries an analytical table or view instead of rebuilding business rules from raw source data every time it refreshes.

Common choices include:

| Tool | Best fit | Data-engineering connection |
| --- | --- | --- |
| Matplotlib | Detailed static charts in Python | Low-level control over labels, axes, and layout |
| Seaborn | Statistical charts from pandas DataFrames | Convenient defaults for grouped and distribution-based charts |
| Plotly | Interactive Python charts and web-based exploration | Hover, filter, and drill-down interactions |
| Power BI | Business dashboards and governed reporting | Connects to warehouse tables, views, and semantic models |
| Tableau | Interactive business analysis and dashboards | Connects to analytical sources and supports visual exploration |

For a data engineer, the important boundary is not which chart library is most attractive. It is whether the dataset behind the chart has a defined grain, stable business meaning, known freshness, and tested quality.

---

## 3. Dimensional modeling

**Dimensional modeling** organizes analytical data around measurable business events and the context needed to understand them. Ralph Kimball and Margy Ross's *The Data Warehouse Toolkit* is a foundational reference for this approach.

Before designing tables, state the **grain**:

> The grain describes exactly what one row in the fact table represents.

For a sales model, a useful grain is:

> One row represents one product line on one completed order.

Choosing the grain first prevents a table from mixing incompatible levels of detail, such as one row per order and one row per product.

A **fine-grained** table keeps detailed events, such as one row per product line on an order. A **coarse-grained** table stores summaries, such as one row per product category per month. Fine grain preserves more ways to analyze the data, while coarse grain can make a known reporting workload faster and smaller. Warehouses commonly preserve detailed facts and publish additional aggregate tables for repeated high-level queries.

```sql
  -- Fine-grained table
  -- Grain: one row per product line within an order
  CREATE TABLE fact_order_lines (
      order_id TEXT,
      line_number INTEGER,
      order_date DATE,
      product_id TEXT,
      customer_id TEXT,
      quantity INTEGER,
      unit_price NUMERIC(10, 2),
      sales_amount NUMERIC(12, 2),

      PRIMARY KEY (order_id, line_number)
  );


  -- Coarse-grained table
  -- Grain: one row per product category per month
  CREATE TABLE monthly_category_sales (
      sales_year INTEGER,
      sales_month INTEGER,
      product_category TEXT,
      total_quantity INTEGER,
      total_sales_amount NUMERIC(14, 2),

      PRIMARY KEY (sales_year, sales_month, product_category)
  );

  -- The key difference is the identifying columns:
  -- fact_order_lines: order_id + line_number identifies one detailed event.
  -- monthly_category_sales: year + month + category identifies one summarized period.

  -- The coarse table would normally be populated from the fine-grained table using an aggregation query.
```

### Fact tables

A **fact table** records measurable business events. It usually contains:

- Foreign keys that connect the event to dimensions.
- Numeric measurements such as quantity, price, cost, or revenue.
- Many rows because events continue to accumulate.

The values recorded at the chosen grain are sometimes called **atomic** or **elementary facts**.

### Dimension tables

A **dimension table** describes the people, products, places, dates, and other context surrounding a fact.

For a widget sale, common dimensions include:

- **Customer:** Who purchased the widget?
- **Product:** What was purchased?
- **Date:** When was it purchased?
- **Employee:** Who helped make the sale?
- **Store:** Where was it sold?

Connecting these dimensions to a sales fact table lets analysts compare revenue by customer demographics, employee, location, product category, or time period.

### Business keys and surrogate keys

A **business key** comes from a source or business process, such as `customer_number`. A **surrogate key** is a warehouse-generated identifier, such as `customer_key = 1042`, with no business meaning of its own.

Surrogate keys help when several source systems use different identifiers for the same entity. They are also important when a dimension must keep multiple historical versions of one business entity.

### Slowly changing dimensions

Dimension values can change more slowly than facts arrive. A customer changes address, a product changes category, or an employee changes department. A **Slowly Changing Dimension**, or **SCD**, defines how the warehouse represents that change.

| Type | Behavior | Historical result |
| --- | --- | --- |
| Type 0 | Keep the original value and reject or ignore later changes | Original value remains |
| Type 1 | Update the existing dimension row | Old value is overwritten |
| Type 2 | End-date the current row and insert a new row with a new surrogate key | Both versions remain queryable |

An SCD Type 2 customer dimension often includes:

```text
customer_key | customer_number | city   | valid_from | valid_to   | is_current
101          | C-42            | Boston | 2022-01-01 | 2024-06-30 | false
208          | C-42            | Dallas | 2024-07-01 | null       | true
```

Facts created while the customer lived in Boston keep `customer_key = 101`; later facts use `customer_key = 208`. This preserves what the warehouse knew for each effective time period. Corrections to bad data may follow a different policy from genuine historical changes, so the business rule must be explicit.

### Star schema

A **star schema** has a central fact table connected directly to denormalized dimension tables.

```text
                    dim_customer
                         |
                         |
dim_date -------- fact_sales -------- dim_product
                         |
                         |
                    dim_employee
```

The star is usually easy for analysts to understand and often requires fewer joins.

### Snowflake schema

A **snowflake schema** normalizes one or more dimensions into related tables. For example, `dim_product` might reference separate category and department tables.

This can reduce repeated dimension values and improve consistency, but queries usually need more joins. "Snowflake schema" is a modeling pattern; it is not the same thing as the Snowflake cloud platform.

### Galaxy schema

A **galaxy schema**, also called a **fact constellation**, contains multiple fact tables that share dimensions. For example, `fact_sales` and `fact_inventory` could both connect to `dim_product`, `dim_store`, and `dim_date`.

In an interview, describe the actual arrangement—multiple business processes sharing conformed dimensions—rather than relying only on the less-common term "galaxy schema."

![Star schema compared with snowflake schema](<Screenshot 2026-09-17 at 11.29.25 AM.png>)

---

## 4. Building a small warehouse in PostgreSQL

PostgreSQL can be used as a data warehouse, especially while learning or when the data and concurrency requirements are moderate.

Suppose the operational database contains:

```text
customers
orders
orderdetails
products
payments
employees
```

Rather than making every analyst reconstruct the business logic from those tables, create a warehouse schema and publish analysis-ready tables.

### Step 1: Create the schema

```sql
CREATE SCHEMA warehouse;
```

### Step 2: Create dimensions

```sql
CREATE TABLE warehouse.dim_customer (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100)
);

CREATE TABLE warehouse.dim_product (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(200),
    product_category VARCHAR(100),
    product_line VARCHAR(100)
);

CREATE TABLE warehouse.dim_date (
    date_id INT PRIMARY KEY,
    full_date DATE UNIQUE NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day_of_week VARCHAR(20) NOT NULL
);
```

### Step 3: Create the fact table

The grain of this table is one product line on one order.

```sql
CREATE TABLE warehouse.fact_sales (
    sale_id BIGSERIAL PRIMARY KEY,
    order_number INT NOT NULL,
    order_line_number INT NOT NULL,
    customer_id INT NOT NULL REFERENCES warehouse.dim_customer(customer_id),
    product_id INT NOT NULL REFERENCES warehouse.dim_product(product_id),
    date_id INT NOT NULL REFERENCES warehouse.dim_date(date_id),
    quantity INT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    revenue NUMERIC(12, 2) NOT NULL,
    UNIQUE (order_number, order_line_number)
);
```

A row might look like:

```text
order   line   customer   product   date       quantity   price    revenue
10401   1      381        27        20260916   4          25.00    100.00
```

### Step 4: Query the model

```sql
SELECT
    d.year,
    d.month,
    p.product_category,
    SUM(f.revenue) AS revenue
FROM warehouse.fact_sales AS f
JOIN warehouse.dim_date AS d
    ON f.date_id = d.date_id
JOIN warehouse.dim_product AS p
    ON f.product_id = p.product_id
GROUP BY
    d.year,
    d.month,
    p.product_category
ORDER BY
    d.year,
    d.month,
    revenue DESC;
```

The model organizes historical data so analytical questions are easier and more consistent to answer.

---

## 5. Normalization

**Normalization** organizes relational tables to reduce unnecessary duplication and prevent update, insert, and delete anomalies. Edgar F. Codd introduced the relational model and the early normal forms.

A quick memory aid is:

- **1NF:** one value per cell.
- **2NF:** depend on the whole key.
- **3NF:** depend on nothing but the key.
- **BCNF:** every determinant must be a candidate key.

Another common summary is: **the key, the whole key, and nothing but the key.**

### Starting example

Imagine one table with this composite primary key: `(order_id, product_id)`.

```text
order_id | order_date | customer_id | customer_name | customer_city | product_id | product_name | quantity
```

This table mixes order, customer, product, and order-line information. That causes repeated values and makes changes harder to manage.

### First Normal Form: 1NF

**Rule:** Each column contains one atomic value, and each row can be uniquely identified.

Do not store several products in one value:

```text
products = "Widget, Cable, Battery"
```

Store one order-product combination per row instead:

```text
order_id | product_id | quantity
101      | 7          | 2
101      | 9          | 1
```

**Remember:** one value per cell.

### Second Normal Form: 2NF

**Rule:** The table is in 1NF, and every non-key column depends on the entire primary key—not just part of a composite key.

With the key `(order_id, product_id)`:

- `order_date` depends only on `order_id`.
- `product_name` depends only on `product_id`.
- `quantity` depends on the complete order-product combination.

Move the partial dependencies into their own tables:

```text
orders(order_id, order_date, customer_id)
products(product_id, product_name)
order_lines(order_id, product_id, quantity)
```

**Remember:** every detail must describe the whole key. This rule matters most when a table has a composite key.

### Third Normal Form: 3NF

**Rule:** The table is in 2NF, and a non-key column does not depend on another non-key column.

If `orders` contains:

```text
order_id | customer_id | customer_name | customer_city
```

then `customer_name` and `customer_city` describe `customer_id`, not the order itself. Move them into a customer table:

```text
orders(order_id, order_date, customer_id)
customers(customer_id, customer_name, customer_city)
```

**Remember:** non-key columns describe the key, not another non-key column.

3NF is especially common in interview discussions, but understanding 1NF and 2NF makes the 3NF rule much easier to explain.

### Boyce-Codd Normal Form: BCNF

**Rule:** For every dependency `X -> Y`, `X` must be a candidate key. A **determinant** is the column or group of columns on the left side of that dependency.

Consider:

```text
student | course | instructor
```

Assume each student has one instructor per course, and each instructor teaches only one course. The pair `(student, course)` identifies the instructor, but `instructor -> course` also holds. Because `instructor` determines `course` without being a candidate key for the original table, the design violates BCNF.

It can be split into:

```text
instructor_courses(instructor, course)
student_instructors(student, instructor)
```

BCNF handles dependency patterns that 3NF can still permit. For a beginner, the important idea is that any column or combination of columns that determines another value must be a candidate key.

### Normalization versus dimensional models

Normalization is not automatically better in every database. It is a design tradeoff.

| More normalized | More denormalized |
| --- | --- |
| Less repeated data | Fewer joins for common queries |
| Central place to update a value | Simpler analytical model |
| Stronger consistency boundaries | Often faster and easier for BI queries |
| More tables and joins | More storage and duplication |

Operational OLTP databases are commonly normalized to protect transactional consistency. Analytical OLAP models often denormalize dimensions deliberately to make large read queries simpler and faster. The duplication still has to be managed by reliable data pipelines.

### Kimball and Inmon warehouse architectures

Normalization and dimensional modeling also appear in two classic warehouse approaches:

| Approach | Starting point | Typical model | Main advantage | Main tradeoff |
| --- | --- | --- | --- | --- |
| Kimball | Deliver business-process data marts and connect them with conformed dimensions | Dimensional star schemas | Produces useful analytical models incrementally | Requires strong coordination so independently built marts do not disagree |
| Inmon | Build an integrated enterprise warehouse before downstream data marts | Normalized enterprise model, then dimensional marts | Establishes enterprise-wide integration centrally | Usually takes more upfront design, time, and specialist effort |

These are architecture strategies, not rival SQL dialects. Many modern platforms borrow from both: they maintain integrated, reusable data and also publish dimensional models for specific analytical consumers. Choose based on organizational scope, delivery needs, source complexity, governance, and team capacity rather than treating either approach as universally correct.


### Reading

- [Database normalization](https://en.wikipedia.org/wiki/Database_normalization) — homework overview.
- [Edgar F. Codd](https://en.wikipedia.org/wiki/Edgar_F._Codd) — background on the relational model.

---

## 6. How does data get into a warehouse?

### ETL and ELT

Both patterns move data from producers to analytical consumers:

- **ETL: Extract, Transform, Load.** Transform data before loading it into the final analytical store.
- **ELT: Extract, Load, Transform.** Land source-shaped data first, then use the target platform's compute to transform it.

The labels describe the order of major stages, not the quality of the pipeline. Warehouses and lakehouses can use either pattern, and one end-to-end pipeline may use both. For example, it can validate a file before loading it, preserve a raw copy, and then run larger transformations inside the analytical platform.

A small ETL pipeline could look like this:

```text
PostgreSQL operational tables
          │
          │ Extract
          ▼
       pandas
          │
          │ Transform
          ▼
Clean / calculate / validate
          │
          │ Load
          ▼
PostgreSQL warehouse tables
```

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://student:password@localhost/sample_database"
)

orders = pd.read_sql("SELECT * FROM orders", engine)
order_details = pd.read_sql("SELECT * FROM orderdetails", engine)

sales = order_details.merge(
    orders,
    on="order_number",
    validate="many_to_one",
)

sales["revenue"] = sales["quantity_ordered"] * sales["price_each"]

# A production pipeline would load dimensions first, map their keys,
# validate the fact-table grain, and then load the fact rows.
sales.to_sql(
    "fact_sales",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False,
)
```

This is a primitive ETL pipeline. A production pipeline also needs repeatable loads, key management, data-quality checks, error handling, monitoring, and a strategy for changes to dimension values.

### Bronze, Silver, and Gold

The **medallion architecture** gives each transformation stage a clear responsibility:

```text
Sources
  │
  ▼
Bronze: source-shaped, traceable data
  │ validate, standardize, deduplicate
  ▼
Silver: clean, typed, reusable data
  │ apply business rules and dimensional modeling
  ▼
Gold: consumer-ready facts, dimensions, and aggregates
  │
  ├──> BI dashboards
  ├──> analytical SQL
  └──> data science and machine learning
```

The layer names are conventions, not products. They can be implemented as PostgreSQL schemas for a learning exercise or as governed tables in object storage for a distributed lakehouse. A layer does not require its own storage bucket, and Gold does not always have to be a star schema.

#### Bronze: preserve and trace

Bronze keeps the source fields and ingestion context needed to diagnose or replay a load. Useful metadata includes the source file or system, ingestion timestamp, batch ID, and source record identifier. Bronze data is not automatically trustworthy merely because it was stored successfully.

#### Silver: standardize and validate

Silver resolves technical quality problems and publishes reusable records. For the sales exercise, this includes:

1. Trimming whitespace and standardizing capitalization.
2. Parsing dates and numeric values instead of leaving them as arbitrary text.
3. Rejecting impossible values such as a negative quantity.
4. Converting supported currencies with an explicit rate and date, or rejecting unsupported currencies.
5. Detecting duplicate `transaction_id` values according to a stated rule.
6. Calculating `sales_amount = quantity * unit_price` only after both inputs are valid.

Do not silently discard bad records. Store rejected rows with a reason and enough source identity to investigate, correct, and replay them.

#### Gold: apply business meaning

Gold publishes data with a stable analytical contract. Loading the sales star schema requires the pipeline to:

1. Look up or create the appropriate product, customer, and date dimension rows.
2. Resolve their warehouse surrogate keys.
3. Verify that one output row still represents the declared fact grain.
4. Insert or upsert the fact without duplicating a transaction during a retry.
5. Reconcile Gold counts and totals with accepted Silver records.

Blindly using `if_exists="append"` is not enough for a rerunnable production load. The pipeline needs a stable record identity, a transaction or atomic publication boundary, and a defined correction policy.

---

## 7. Why not use PostgreSQL for everything?

For a small organization, PostgreSQL may be enough. It is mature, reliable, and capable. Millions or tens of millions of rows may work well with appropriate modeling, indexes, partitioning, hardware, and queries.

The requirements change when users need to scan a large portion of a table:

```sql
SELECT
    country,
    product_category,
    DATE_TRUNC('month', order_date) AS order_month,
    SUM(revenue) AS total_revenue
FROM enormous_sales_table
GROUP BY
    country,
    product_category,
    DATE_TRUNC('month', order_date);
```

If the table contains billions of rows, an index may not avoid most of the work because the query actually needs to process a large share of the data. That is fundamentally different from retrieving one customer by ID.

Modern analytical systems make architectural choices for large scans, aggregations, distributed processing, and many simultaneous users.

---

## 8. Row-oriented and column-oriented storage

Consider this table:

```text
customer | country | product | quantity | price
------------------------------------------------
Alice    | USA     | Laptop  | 1        | 1200
Bob      | Canada  | Mouse   | 4        | 25
Carol    | USA     | Monitor | 2        | 300
```

Row-oriented storage conceptually keeps each record together:

```text
Alice, USA, Laptop, 1, 1200
Bob, Canada, Mouse, 4, 25
Carol, USA, Monitor, 2, 300
```

Column-oriented storage conceptually keeps values from the same column together:

```text
customer: Alice, Bob, Carol
country:  USA, Canada, USA
product:  Laptop, Mouse, Monitor
quantity: 1, 4, 2
price:    1200, 25, 300
```

For this query:

```sql
SELECT SUM(price)
FROM sales;
```

a columnar engine can focus primarily on the `price` data instead of reading every column. Values of the same type also tend to compress well. Across billions of rows, reading less data can make a major difference.

[Amazon Redshift's architecture documentation](https://docs.aws.amazon.com/redshift/latest/dg/c_redshift_system_overview.html) describes its combination of columnar storage, compression, and massively parallel processing.

---

## 9. Analytical technologies: do not mix up the layers

These names do not all describe the same kind of thing:

| Technology | What it is | Useful beginner mental model |
| --- | --- | --- |
| PostgreSQL | General-purpose relational database | Start here for SQL, transactions, and a small warehouse |
| [Apache Hive](https://hive.apache.org/docs/latest/introduction-to-apache-hive/) | Distributed SQL data warehouse software in the Hadoop ecosystem | Historically important SQL-on-Hadoop system that is still maintained and used |
| [DuckDB](https://duckdb.org/docs/current/data/data_sources) | Embedded analytical database engine | Local OLAP engine that can store tables or query sources such as CSV, Parquet, databases, and Iceberg |
| [Apache Iceberg](https://iceberg.apache.org/) | Open table format | Metadata and rules for managing large analytical tables in object storage |
| [Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/c_redshift_system_overview.html) | AWS cloud data warehouse | Distributed, columnar analytical database |
| [Azure Synapse Analytics](https://learn.microsoft.com/en-us/azure/synapse-analytics/overview-what-is) | Microsoft analytics service | SQL warehousing, Spark, and data integration in Azure |
| [Google BigQuery](https://docs.cloud.google.com/bigquery/docs/introduction) | Fully managed serverless data warehouse and analytics platform | Run large analytical queries without managing database servers |
| [Snowflake](https://docs.snowflake.com/en/user-guide/intro-key-concepts) | Cloud data platform | Managed analytical platform with separate storage and compute layers |
| [Delta Lake](https://docs.databricks.com/aws/en/delta) | Open-source storage layer and table format | Adds transactions, schema controls, and a log to Parquet-based lake tables |
| [Databricks SQL](https://docs.databricks.com/aws/en/sql) | Cloud data warehouse on the Databricks lakehouse | SQL warehouse that operates directly on lakehouse data |
| Databricks | Data and AI platform | Spark-based lakehouse platform for engineering, SQL, data science, and ML |

DuckDB does **not** require Iceberg. It can store data in a DuckDB database and query many file formats and external systems. Iceberg is one supported option.

Snowflake is an independent company whose managed service runs on AWS, Azure, or Google Cloud infrastructure. The customer chooses a supported cloud and region; Snowflake manages the service.

Databricks does provide analytical SQL warehouses. Delta Lake is the storage layer underneath many lakehouse tables; Databricks SQL is the warehouse experience that queries those tables.

### On-premises or local examples

- PostgreSQL for a modest relational warehouse.
- DuckDB for embedded or local analytical work.
- Apache Hive for SQL over distributed storage in the Hadoop ecosystem.

### Cloud examples

- **AWS:** Amazon Redshift.
- **Microsoft Azure:** Azure Synapse Analytics and Databricks.
- **Google Cloud:** BigQuery and Databricks.
- **Multi-cloud services:** Snowflake and Databricks are available on multiple major cloud providers.

---

## 10. Warehouses and lakehouses

Snowflake helped popularize an architecture in which persistent storage and query compute scale independently:

```text
                 STORAGE
              Company data
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   Warehouse A   Warehouse B   Warehouse C

   Analysts      Data Eng.       Finance
   compute       compute         compute
```

If finance needs more compute at month end, its compute can be increased without rebuilding the storage layer. When it is not needed, that compute can be reduced or suspended. Snowflake documents three major layers: database storage, compute, and cloud services.

### Data lakes and object storage

A **data lake** stores large amounts of structured, semi-structured, and unstructured data, often before every future use is known. The underlying storage is commonly an **object store**. Instead of updating blocks in a mounted filesystem, applications address whole objects by a key inside a bucket or container.

Common cloud object stores include Amazon S3, Azure Data Lake Storage Gen2, and Google Cloud Storage. Azure Data Lake Storage Gen2 is built on Azure Blob Storage with a hierarchical namespace and data-lake capabilities. MinIO and Apache Ozone are examples of systems that can provide object-storage interfaces in self-managed environments.

An object store holds files and their metadata; it does not by itself provide table transactions, SQL semantics, or a business model. It is also different from Delta Lake: Delta Lake is a table/storage layer that manages table metadata and transactions over data files, commonly stored in an object store.

PostgreSQL is not normally the storage foundation for a lakehouse. It is a relational database with a database-managed storage engine. It can store binary values, but large media files are usually kept in object storage while PostgreSQL stores identifiers, locations, and descriptive metadata.

### What a lakehouse adds

A **lakehouse** combines the flexible, scalable storage associated with data lakes with warehouse-like table management and analytical behavior. It commonly adds schema enforcement, transactional table updates, metadata, governance, and support for several compute engines over data in object storage.

On Databricks, data commonly lives in cloud object storage and is managed in Delta tables, while different compute engines serve SQL, Spark, data engineering, data science, and machine-learning workloads. Delta Lake, Apache Iceberg, and Apache Hudi are table-format or table-layer choices; Spark, Trino, and DuckDB are examples of engines that can process data, subject to each engine's format support.

```text
             Object storage
           S3 / ADLS / GCS
                  │
                  ▼
          Delta or Iceberg tables
                  │
       ┌──────────┼───────────┐
       ▼          ▼           ▼
      SQL       Spark         ML
   analytics     ETL          AI
```

Spark can distribute a large calculation across workers:

```text
                   Query
                     │
          ┌──────────┴──────────┐
          │                     │
       Worker 1              Worker 2
     one partition          another partition
          │                     │
          └──────────┬──────────┘
                     │
                   Result
```

Real systems are more sophisticated, but the key idea is that storage, metadata, and compute can be separate components that scale differently.

### Medallion layers in a lakehouse

Bronze, Silver, and Gold are logical data-quality and consumer-readiness boundaries. One lakehouse might store every layer as managed tables in one object store. Another architecture might keep Bronze and Silver in object storage and publish Gold into a dedicated SQL warehouse. The right boundary depends on workload, governance, latency, interoperability, and cost—not the layer's color.

---

## 11. Learning progression

```text
PostgreSQL
    ↓
SQL fundamentals
    ↓
Joins and aggregations
    ↓
CTEs and window functions
    ↓
Indexes and query plans
    ↓
Normalization and dimensional modeling
    ↓
Fact and dimension tables
    ↓
ETL / ELT
    ↓
Data warehouse
    ↓
Columnar and distributed systems
    ↓
Cloud warehouses and lakehouses
```

The underlying problem remains consistent:

> Take data from different places, organize it reliably, and make large amounts of it easy and fast to analyze.

---

## 12. Homework PostgreSQL setup

The questions are in [`4.2_Thur_HW.md`](4.2_Thur_HW.md). The homework uses a separate PostgreSQL database named `week3_hw`. This keeps the homework tables isolated from the `bigdata` learning database and from the future notebook-based Bronze → Silver → Gold lab.

The database contains:

- `bronze.sales_transactions`: 11 raw rows with deliberate quality problems.
- `silver.sales_transactions`: 6 cleaned and validated rows.
- `silver.rejected_sales`: 5 rejected rows with reasons.
- `gold.dim_product`, `gold.dim_date`, and `gold.dim_customer`: dimensions for the homework concepts.
- `gold.fact_sales`: 6 sales facts at the grain of one product line per transaction.

Connect from the repository root with:

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d week3_hw
```

Then inspect the schemas and tables:

```text
\dn
\dt bronze.*
\dt silver.*
\dt gold.*
```

The reproducible setup, verification, and reset commands are documented in [`sql/week3-homework/README.md`](../../../sql/week3-homework/README.md). Resetting this homework rebuilds only the three schemas inside `week3_hw`; it does not delete the PostgreSQL Docker volume.

The future lab will remain separate from the homework. It will use generated data in a notebook and teach Bronze → Silver and Silver → Gold one stage at a time, including a safe PostgreSQL cleanup/reset procedure.


## 13. Video resources and transcript summaries

These summaries condense the main concepts from each video's transcript. Use them to decide which video to watch in full; they do not replace the demonstrations and diagrams in the original videos.

### 13.1 [What is a Data Warehouse? — IBM Technology](https://www.youtube.com/watch?v=k4tK2ttdSDg)

**Transcript summary:** The video presents an enterprise data warehouse as a central system that receives data from several business applications and prepares it for analysis. ETL processes extract source data, transform it into a consistent and useful form, and load it into the warehouse. The warehouse then serves analysts, data scientists, data engineers, BI tools, and predictive or machine-learning workloads. It also distinguishes the enterprise warehouse from a data mart, which serves a narrower department or subject area, and discusses on-premises, cloud, and hybrid deployment choices.

**Important takeaways:**

- A warehouse creates a shared analytical source, but it still depends on well-designed ingestion, transformation, quality, and governance.
- A data mart is a focused analytical subset, not a replacement term for every warehouse.
- Deployment location is separate from data modeling: a warehouse can be on-premises, cloud-based, or hybrid.
- The main engineering value is consistent, reusable data for many consumers instead of separate manual preparation for every report.

### 13.2 [Database vs. Data Warehouse vs. Data Lake — Alex The Analyst](https://www.youtube.com/watch?v=-bSkREem8dM)

**Transcript summary:** The video compares three storage concepts at a beginner level. An operational database supports current application activity and frequent record-level changes. A data warehouse combines structured data, often from multiple systems, and organizes historical information for reporting and analysis. A data lake keeps large volumes of data in many forms, including raw or unstructured data, so it can support exploration and later processing.

**Important takeaways:**

- Choose a system from workload and data requirements, not from which name sounds newest.
- Databases, warehouses, and lakes can coexist because they solve different problems.
- A data lake's flexibility does not remove the need for catalogs, security, quality rules, and ownership.
- The comparison is a mental model; real products increasingly overlap, so verify their actual guarantees and interfaces.

### 13.3 [SQL Data Warehouse from Scratch — Data with Baraa](https://www.youtube.com/watch?v=9GVqKuTVANE)

**Transcript summary:** This long hands-on project moves from requirements to a working SQL Server warehouse. It integrates CRM and ERP data supplied as CSV files, plans the repository and naming conventions, and uses Bronze, Silver, and Gold layers. Bronze preserves source-shaped data, Silver cleans and standardizes it, and Gold publishes a dimensional model for analytics. The walkthrough also covers full versus incremental extraction, transformation techniques, load strategies, data quality, star-schema design, procedures, logging, testing, documentation, lineage, and analytical queries.

**Important takeaways:**

- Start with business requirements, source contracts, history needs, and consumer expectations before writing DDL.
- Treat Bronze, Silver, and Gold as responsibilities with explicit rules, not merely schema names.
- Document mappings and lineage so a Gold value can be traced to its source and transformation.
- Add observability and tests to the load process; table creation alone is not a completed warehouse.
- The video uses SQL Server, so adapt its DDL, procedures, bulk loading, and administration syntax before using it in this repository's PostgreSQL environment.

### 13.4 [Kimball and Inmon Data Warehouse Architectures — nullQueries](https://www.youtube.com/watch?v=Tff34jj_V-0)

**Transcript summary:** The video contrasts Kimball's bottom-up delivery of dimensional data marts with Inmon's top-down enterprise data warehouse. Kimball starts with business processes and star schemas, then integrates them through shared or conformed dimensions. Inmon first creates a normalized enterprise model that integrates data across the organization, then supplies departmental analytical models from it. The comparison emphasizes delivery speed and business focus on one side, and centralized integration and longer-term enterprise consistency on the other.

**Important takeaways:**

- Kimball is usually associated with dimensional models and incremental business value.
- Inmon is usually associated with a normalized enterprise warehouse followed by downstream marts.
- Faster initial delivery can create inconsistent marts if conformed dimensions and governance are weak.
- Central enterprise design can improve consistency but requires more time, coordination, and specialized modeling.
- Modern architectures often combine ideas from both rather than following either approach mechanically.

### 13.5 [Data Lakehouses Explained — IBM Technology](https://www.youtube.com/watch?v=Enu-EH7RHHM)

**Transcript summary:** The video uses a farm-to-table and commercial-kitchen analogy to trace data from raw arrival through storage, preparation, and consumption. A lake accepts varied raw ingredients at scale, while a warehouse organizes prepared data for predictable analysis. A lakehouse aims to keep flexible, scalable storage while adding warehouse-like organization, governance, reliability, and analytical access. The goal is to reduce unnecessary movement and duplication while serving BI, analytics, data science, and AI.

**Important takeaways:**

- Cheap storage does not make raw data usable; metadata, quality, security, and processing remain necessary.
- Warehouse-like controls are what keep a data lake from becoming an untrusted data swamp.
- A lakehouse is an architecture made from storage, metadata, table management, governance, and compute—not one file type or one product.
- Separating storage from compute lets different workloads scale independently, but it also creates more interfaces to operate and observe.

### 13.6 [Intro to Data Lakehouse — Databricks](https://www.youtube.com/watch?v=myLiFw9AUKY)

**Transcript summary:** The video explains the historical progression from relational systems and warehouses to data lakes and then lakehouses. Warehouses provided clean schemas and reliable BI but were less suited to rapidly growing semi-structured and unstructured data. Data lakes added flexible, lower-cost storage but often lacked transactions, consistent quality, fast BI performance, and unified governance. Running a lake, a warehouse, and several specialized systems also duplicated data and separated teams. The lakehouse is presented as an open architecture that adds ACID transactions, schema enforcement, governance, independent storage and compute, and support for SQL, streaming, data science, and machine learning over a shared data foundation.

**Important takeaways:**

- The lakehouse tries to reduce copies and silos by supporting several workloads over shared governed data.
- ACID transactions and schema controls make file-backed analytical tables more reliable under concurrent reads and writes.
- Open columnar files and table metadata allow several compatible engines to work with the same data, although compatibility must be tested.
- Decoupled storage and compute can scale independently, but cost, performance, maintenance, and governance still require deliberate design.
- Databricks is presenting its own platform perspective; treat the architectural claims as design goals and verify them against the chosen table format, catalog, engine, and workload.
