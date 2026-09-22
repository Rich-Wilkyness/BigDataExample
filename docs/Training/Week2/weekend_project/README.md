## Weekend Project: Containerized Sales Report Pipeline

### Objective

Build a small **containerized data pipeline** that takes a raw CSV file containing sales transactions and produces **one final deliverable: `sales_report.csv`**.

The project should demonstrate:

**Docker + Python + Pandas + SQL + Bash**

Expected completion time: **1–3 hours**.

### Scenario

A company sends you a raw sales file containing:

```text
transaction_id
transaction_date
customer
product
category
quantity
unit_price
```

Example:

```csv
transaction_id,transaction_date,customer,product,category,quantity,unit_price
T001,2026-09-01,Alice,Laptop,Electronics,1,1200
T002,2026-09-01,Bob,Mouse,Electronics,3,25
T003,2026-09-02,Alice,Desk,Furniture,1,450
T004,2026-09-02,Carol,Chair,Furniture,4,125
T005,2026-09-03,David,Monitor,Electronics,2,300
T006,2026-09-03,Alice,Keyboard,Electronics,2,75
T007,2026-09-04,Bob,Desk,Furniture,1,450
T008,2026-09-04,Carol,Laptop,Electronics,1,1200
```

Your job is to build a pipeline that processes this data and creates a business report.

### Required architecture

The finished system should operate approximately like this:

```text
sales.csv
    │
    ▼
Bash Script
    │
    ▼
Docker
    │
    ▼
Python + Pandas
    │
    ├── Clean/transform data
    │
    ▼
PostgreSQL
    │
    ├── Store processed transactions
    │
    ├── Execute SQL analytics
    │
    ▼
Python
    │
    ▼
sales_report.csv
```

### Requirements

**1. Docker**

Use Docker Compose to run at least:

```text
PostgreSQL
```

The database must be accessible to the Python pipeline.

Your `docker-compose.yml` should configure the database, credentials, port, and a persistent volume.

**2. Bash**

Create:

```text
run_pipeline.sh
```

The instructor should be able to run:

```bash
./run_pipeline.sh
```

and have the pipeline execute.

The Bash script should perform at least basic tasks such as starting the Docker environment and running the Python program.

**3. Python/Pandas**

Your Python program must:

```text
Read sales.csv
        ↓
Clean/validate the data
        ↓
Create sales_amount
        ↓
Load the processed data into PostgreSQL
```

Calculate:

```text
sales_amount = quantity * unit_price
```

At least one Pandas operation other than reading the CSV must be demonstrated, such as:

```python
df["category"] = df["category"].str.strip().str.title()
```

or filtering invalid records.

**4. SQL**

Store the processed transactions in a PostgreSQL table.

Your final report must be generated using a SQL query containing:

* `GROUP BY`
* `SUM()`
* `ORDER BY`

The report should show total sales by category.

For example:

```text
category       total_units    total_revenue
Electronics    9              3225.00
Furniture      6              1400.00
```

Do not hard-code these results.

**5. Final deliverable**

The pipeline must generate:

```text
output/sales_report.csv
```

This is the **single artifact submitted for grading**.

It should contain:

```csv
category,total_units,total_revenue
Electronics,9,3225.00
Furniture,6,1400.00
```

Your exact results will depend on your input data.

### Suggested project structure

```text
weekend_project/
│
├── sales.csv
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run_pipeline.sh
├── pipeline.py
│
└── output/
    └── sales_report.csv
```

The Python application itself should also be containerized, so the student should ultimately have something resembling:

```text
┌──────────────────────────────┐
│ Docker Compose               │
│                              │
│   ┌───────────────┐          │
│   │ Python/Pandas │          │
│   │ pipeline      │          │
│   └───────┬───────┘          │
│           │                   │
│           ▼                   │
│   ┌───────────────┐          │
│   │ PostgreSQL    │          │
│   └───────────────┘          │
└──────────────────────────────┘
             │
             ▼
    output/sales_report.csv
```

### Live demonstration

Students should be prepared to demonstrate the project without modifying it beforehand.

The instructor may ask them to:

1. Delete `output/sales_report.csv`.
2. Run `./run_pipeline.sh`.
3. Show the running Docker containers.
4. Connect to PostgreSQL and show the loaded table. 
    -> docker compose exec postgres psql -U pipeline -d sales
    -> docker exec -it <container> bash -> psql -U pipeline -d sales
5. Show several rows using `SELECT`.
6. Explain the Pandas transformation.
7. Show the SQL aggregation that creates the report.
8. Open the newly generated `sales_report.csv`.
9. Modify or add one transaction to `sales.csv`.
10. Run the pipeline again and demonstrate that the report changes appropriately.

The last step is particularly useful for verifying the project actually works end-to-end rather than the submitted CSV simply being manually created.

### Submission

Submit only:

```text
sales_report.csv
```

However, **retain the complete project on your machine**. You may be asked to demonstrate the pipeline live and explain any part of the implementation.

The essential success criterion is:

```text
Raw CSV
   ↓
Bash
   ↓
Dockerized Python/Pandas
   ↓
PostgreSQL
   ↓
SQL aggregation
   ↓
sales_report.csv
```

A successful project therefore demonstrates that the student can connect several of the technologies from the course into **one functioning data-engineering pipeline**, rather than completing five unrelated exercises.