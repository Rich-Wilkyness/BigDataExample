# SQL and PostgreSQL for Data Engineering

> Status: Guided introduction
>
> Level: Beginner, with production context
>
> Applies to: PostgreSQL, relational data, batch validation, and analytical queries
>
> Dataset: [`data.csv`](data.csv), one row per employee
>
> Evidence: Setup and lesson SQL verified against local PostgreSQL 18.6 on 2026-09-16

## Overview

SQL is a declarative language for defining, reading, changing, and controlling relational data. You describe the result you want; the database validates the statement, chooses an execution plan, coordinates concurrent work, and returns or persists the result.

For a data engineer, SQL is used for more than looking up rows. It defines schemas and constraints, validates deliveries, joins datasets, calculates aggregates, builds warehouse models, supports incremental pipelines, and provides evidence about data quality and performance.

This lesson uses PostgreSQL in Docker Desktop and the employee dataset from Monday’s Python lesson. The examples are intentionally small enough to inspect, but the relational reasoning—grain, keys, cardinality, `NULL`, transactions, and deterministic results—also applies to warehouses and distributed SQL engines. Product-specific syntax and performance behavior can differ.

## Learning objectives

After completing this guide, you should be able to:

- Initialize, start, inspect, connect to, and stop a PostgreSQL container.
- Explain databases, schemas, tables, rows, columns, keys, constraints, and grain.
- Create tables whose constraints enforce a declared data contract.
- Load CSV data into PostgreSQL and verify the load.
- Use `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`, `GROUP BY`, `HAVING`, and joins.
- Handle `NULL` using SQL’s three-valued logic.
- Use a transaction to test a change and choose `COMMIT` or `ROLLBACK`.
- Diagnose whether a failure belongs to Docker, PostgreSQL, SQL syntax, or the data contract.
- Read a basic query plan without assuming that every sequential scan is bad.

## Prerequisites

- Docker Desktop is running.
- The repository includes a [local PostgreSQL configuration](../../../infra/postgres/README.md); Part 1 creates your ignored local `.env` file.
- Run commands from the repository root unless the guide says you are inside `psql`.
- Monday’s [Python and pandas lesson](1_Mon_Python.md) is helpful context but is not required.

## Part 1: PostgreSQL in Docker

### Git repository, image, container, volume, and database

These objects solve different problems:

| Object | Purpose | Persists when the container is removed? |
| --- | --- | --- |
| Repository files | Version the Compose definition, documentation, and safe example configuration. | Yes, through Git. |
| Docker image | Read-only template containing PostgreSQL and its operating-system dependencies. | Yes, until the image is removed. |
| Docker container | Running PostgreSQL process created from the image. | No; containers are replaceable. |
| Docker volume | Stores PostgreSQL database files outside the replaceable container. | Yes, until the volume is explicitly removed. |
| PostgreSQL database | Logical collection of schemas and database objects managed by PostgreSQL. | Yes, because its files are in the volume. |

The container is compute; the named volume owns the durable local database state.

### Installation choices

The official PostgreSQL image is documented at [Docker Hub](https://hub.docker.com/_/postgres).

This repository uses Docker Compose, so you do not need to install PostgreSQL directly on your Mac. On a Debian or Ubuntu machine where a native server is intentionally required, the equivalent APT commands are:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
```

Do not run those APT commands on macOS, and do not install a second server when the Docker service already supplies PostgreSQL.

### Standalone container versus repository setup

PostgreSQL does not have to be tied to a Git repository. These are two valid ways to create the same kind of local service:

| Approach | Where the setup is recorded | Best fit |
| --- | --- | --- |
| `docker run` or Docker Desktop fields | Terminal history, personal notes, or Docker Desktop | A quick personal exercise or an instructor-led demonstration. |
| Docker Compose in the repository | A tracked YAML file plus an ignored local `.env` file | A repeatable project environment that teammates can recreate. |

The repository setup does not store the running container or database in Git. Git tracks the Compose recipe and safe example configuration; Docker Desktop manages the container, network, and volume outside the repository. The local `.env` password and the database rows are not committed.

Downloading the image with `docker pull` is also optional. Both `docker run` and `docker compose up` pull a missing image automatically.

This standalone command shows the settings that Compose supplies for this repository:

```bash
docker run \
  --name postgres-practice \
  -e POSTGRES_USER=bigdata \
  -e POSTGRES_PASSWORD='choose-a-local-password' \
  -e POSTGRES_DB=bigdata \
  -p 127.0.0.1:5432:5432 \
  -v postgres-practice-data:/var/lib/postgresql \
  -d postgres:18.6
```

Do not run that example while another PostgreSQL container is already using host port `5432`. It is an alternative to the repository’s Compose service, not an additional required container.

| Setting | Object it names or controls |
| --- | --- |
| `postgres-practice` | Docker container name. |
| `POSTGRES_USER=bigdata` | PostgreSQL login role; for this local exercise it is the initial database superuser. |
| `POSTGRES_PASSWORD=...` | Password assigned to that PostgreSQL role during first initialization. |
| `POSTGRES_DB=bigdata` | Initial PostgreSQL database. |
| `postgres-practice-data` | Docker volume containing the persistent database files. |
| `postgres:18.6` | Image and version used to create the container. |

The `bigdata` role is not your macOS account and is not the container’s Linux `root` user. Docker container names, operating-system users, PostgreSQL roles, and PostgreSQL databases are separate identities even when some names happen to match.

### First-time repository setup

On a fresh clone, create the ignored local environment file once:

```bash
cp infra/postgres/.env.example infra/postgres/.env
```

Open `infra/postgres/.env` and replace the example password with a local password. Keep the variable names intact:

```dotenv
POSTGRES_USER=bigdata
POSTGRES_PASSWORD=choose-a-local-password
POSTGRES_DB=bigdata
POSTGRES_PORT=5432
```

The first startup follows this sequence:

```text
image + environment settings + empty volume
                    |
                    v
       entrypoint runs initdb automatically
                    |
                    v
       role and initial database are created
                    |
                    v
            PostgreSQL starts
```

There is no separate initialization command in this workflow. The official image performs initialization automatically when it finds an empty data directory.

### Start the service

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml up -d
```

What the important flags mean:

| Argument | Meaning |
| --- | --- |
| `--env-file infra/postgres/.env` | Supplies the ignored local user, password, database, and port settings. |
| `-f infra/postgres/compose.yml` | Selects this repository’s PostgreSQL service definition. |
| `up` | Creates or reuses the network, volume, and container, then starts the service. |
| `-d` | Runs the container in the background. |

Check status:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml ps
```

Do not connect until the status is `healthy`.

### Inspect Docker state

```bash
docker ps
docker ps -a
docker images
docker volume ls
```

```text
docker ps      -> running containers
docker ps -a   -> running and stopped containers
docker images  -> downloaded or locally built image templates
docker volume ls -> Docker-managed persistent volumes
```

If startup fails, inspect logs before changing configuration:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml logs postgres
```

### Why `POSTGRES_PASSWORD` was required

The official image initializes PostgreSQL only when its data directory is empty. During that first initialization, `POSTGRES_PASSWORD` supplies the password for the user named by `POSTGRES_USER`. Using `POSTGRES_HOST_AUTH_METHOD=trust` would disable password checks for host connections and is not appropriate for this setup.

If a newly created container exits with `Database is uninitialized and superuser password is not specified`, inspect it with `docker ps -a` and `docker logs CONTAINER_NAME`. Because environment settings belong to the container configuration, merely restarting that container will repeat the failure. If it was a disposable first attempt with no data to preserve, remove it and create a replacement using either the complete `docker run` command above or the repository’s Compose command.

Changing `POSTGRES_PASSWORD` in `.env` after the named volume has been initialized does not change the password already stored inside PostgreSQL. At that point, use SQL such as `ALTER ROLE`, or deliberately remove the local training volume and reinitialize it if no data must be retained.

### Connect with `psql`

Connect directly to the database:

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d bigdata
```

You can also open a shell inside the container and launch `psql` separately:

```bash
docker exec -it big-data-example-postgres bash
psql -U bigdata -d bigdata
```

The direct form is faster when the goal is SQL practice.

### SQL statements versus `psql` commands

At a prompt such as `bigdata=#`, you can enter SQL and `psql` meta-commands:

```text
SELECT version();  -- SQL statement; ends with a semicolon
\conninfo          -- psql command; begins with a backslash
\l                 -- list databases
\dn                -- list schemas
\dt training.*     -- list tables in the training schema
\d training.employees
\q                 -- leave psql
```

`psql` commands control the client and are not sent as SQL statements. They do not end with semicolons.

### Beginner `psql` and SQL cheat sheet

#### Connection command

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d bigdata
```

| Part | Meaning |
| --- | --- |
| `docker exec` | Run a command inside an existing container. |
| `-i` | Keep input open so you can type. |
| `-t` | Provide an interactive terminal. |
| `big-data-example-postgres` | Container in which the command runs. |
| `psql` | PostgreSQL command-line client. |
| `-U bigdata` | Connect as PostgreSQL role `bigdata`; `-U` does not mean password. |
| `-d bigdata` | Connect to PostgreSQL database `bigdata`. |

The container’s Linux user and PostgreSQL roles are separate identities. Opening Bash makes you Linux user `root`, but this database has no PostgreSQL role named `root`. Plain `psql` therefore tries the wrong default role; use `psql -U bigdata -d bigdata`.

#### Navigation and help

Enter these only after the prompt changes to `bigdata=#`:

| Command | Purpose |
| --- | --- |
| `\?` | Show help for `psql` commands. |
| `\h` | Show help for SQL commands. |
| `\h SELECT` | Show PostgreSQL help for `SELECT`. |
| `\conninfo` | Show the current server, database, user, and connection method. |
| `\l` | List databases. |
| `\c bigdata` | Connect to database `bigdata`. |
| `\dn` | List schemas. |
| `\dt` | List tables in the current search path. |
| `\dt training.*` | List tables in schema `training`. |
| `\d training.employees` | Show table columns, types, indexes, and constraints. |
| `\d+ training.employees` | Show extended table details. |
| `\du` | List PostgreSQL roles and their attributes. |
| `\q` | Exit `psql`. |

Recommended first exploration:

```text
\conninfo
\l
\du
\dn
\dt training.*
\d training.employees
```

#### Understand the prompt

| Prompt | Meaning | What to do |
| --- | --- | --- |
| `bigdata=#` | Ready for a new command. | Enter SQL or a `psql` command. |
| `bigdata-#` | The SQL statement is unfinished, often because its semicolon is missing. | Finish with `;`, or press `Ctrl+C` to cancel the unfinished statement. |
| `bigdata=*#` | An explicit transaction is active. | Continue, then finish with `COMMIT;` or `ROLLBACK;`. |
| `bigdata=!#` | A statement failed inside the current transaction. | Enter `ROLLBACK;` before continuing. |

SQL statements end with a semicolon. Backslash commands do not:

```text
SELECT COUNT(*) FROM training.employees;
\dt training.*
```

#### Core SQL patterns

```sql
-- Preview rows.
SELECT employee_id, name, department, salary
FROM training.employees
LIMIT 5;

-- Filter and sort rows.
SELECT employee_id, name, salary
FROM training.employees
WHERE department = 'Engineering'
  AND active
ORDER BY salary DESC, employee_id;

-- Return unique values.
SELECT DISTINCT department
FROM training.employees
ORDER BY department;

-- Summarize groups.
SELECT department,
       COUNT(*) AS employee_count,
       ROUND(AVG(salary), 2) AS average_salary
FROM training.employees
GROUP BY department
ORDER BY average_salary DESC;

-- Test a change without keeping it.
BEGIN;
UPDATE training.employees
SET salary = salary * 1.05
WHERE employee_id = 1;
ROLLBACK;
```

Before running `UPDATE` or `DELETE`, use the same `WHERE` clause in a `SELECT` and confirm the affected keys and row count.

### Required database-list screenshot

If your assignment asks for a screenshot like the instructor’s example, connect to `psql` and enter lowercase backslash-L:

```text
\l
```

Capture the terminal showing the `List of databases` result. Your prompt and database list will contain `bigdata` rather than the instructor’s `mydatabase`; that difference is expected because this repository uses `bigdata` as its configured database name.

## Part 2: The relational mental model

### Database hierarchy

```text
PostgreSQL server
└── database: bigdata
    └── schema: training
        ├── table: departments
        └── table: employees
```

| Term | Meaning in this lesson |
| --- | --- |
| Database | Connection and catalog boundary containing schemas and objects. |
| Schema | Namespace used to group related tables and other objects. |
| Table | Relation-like structure with declared columns and constraints. |
| Row | One occurrence at the table’s declared grain. |
| Column | One named attribute with a database type. |
| Primary key | Column or columns that uniquely identify one row. |
| Foreign key | Constraint requiring a value to match a key in another table. |
| Constraint | Rule the database enforces for every accepted table state. |
| Grain | What exactly one row represents. |

The grain of `training.employees` is one current employee. The grain of `training.departments` is one department. State the grain before writing joins or aggregates because a query can silently duplicate rows when table relationships are misunderstood.

### SQL command families

| Family | Purpose | Examples |
| --- | --- | --- |
| DDL | Define database objects and constraints. | `CREATE`, `ALTER`, `DROP` |
| DML | Insert, update, or delete rows. | `INSERT`, `UPDATE`, `DELETE` |
| Query | Read and derive results. | `SELECT` |
| Transaction control | Choose the atomic commit boundary. | `BEGIN`, `COMMIT`, `ROLLBACK` |
| Access control | Grant or remove privileges. | `GRANT`, `REVOKE` |

These labels are useful vocabulary, but the more important question is what state a statement reads or changes and whether that change is safely recoverable.

## Part 3: Create and load the training tables

### Copy the CSV into the container

Exit `psql` with `\q`, then run this from the repository root:

```bash
docker cp docs/Training/Week2/data.csv big-data-example-postgres:/tmp/employees.csv
```

This copies a disposable input file into the container. The original CSV remains the versioned source fixture.

Reconnect:

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d bigdata
```

### Create the schema and tables

The first line deliberately resets only the local `training` schema so the exercise is rerunnable. Do not copy that reset pattern into an environment containing valuable objects.

```sql
DROP SCHEMA IF EXISTS training CASCADE;
CREATE SCHEMA training;

CREATE TABLE training.departments (
    department_name text PRIMARY KEY,
    office_location text NOT NULL
);

INSERT INTO training.departments (department_name, office_location)
VALUES
    ('Engineering', 'Boise'),
    ('Finance', 'New York'),
    ('HR', 'Boise'),
    ('Marketing', 'Chicago'),
    ('Sales', 'Denver');

CREATE TABLE training.employees (
    employee_id integer PRIMARY KEY,
    name text NOT NULL,
    department text NOT NULL REFERENCES training.departments (department_name),
    salary numeric(12, 2) NOT NULL CHECK (salary >= 0),
    years_experience integer NOT NULL CHECK (years_experience >= 0),
    active boolean NOT NULL
);
```

What these constraints guarantee:

- `PRIMARY KEY` prevents missing or duplicate employee identifiers.
- `NOT NULL` rejects missing required values.
- `REFERENCES` rejects departments that do not exist in `training.departments`.
- `CHECK` rejects negative salaries and experience values.
- `numeric(12, 2)` stores exact decimal values at the declared precision and scale.

Constraints protect every writer, including scripts, notebooks, applications, and concurrent sessions. Python validation can improve error messages, but it does not replace database enforcement.

### Load the employee CSV

From inside `psql`:

```text
\copy training.employees FROM '/tmp/employees.csv' WITH (FORMAT csv, HEADER true)
```

`\copy` is a `psql` client command. The client reads the file and sends rows to PostgreSQL. In this setup the `psql` client is running inside the container, so the path `/tmp/employees.csv` refers to the copy inside that container.

### Reconcile the load

Never treat “the command did not error” as sufficient evidence. Check row count, key uniqueness, missing required fields, and domain values:

```sql
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT employee_id) AS distinct_employee_ids,
       COUNT(*) FILTER (WHERE active) AS active_employees,
       MIN(salary) AS minimum_salary,
       MAX(salary) AS maximum_salary
FROM training.employees;
```

Example result for the current fixture:

```text
row_count | distinct_employee_ids | active_employees | minimum_salary | maximum_salary
----------+-----------------------+------------------+----------------+---------------
100       | 100                   | 91               | 62000.00       | 120000.00
```

Confirm that every expected department appears:

```sql
SELECT department, COUNT(*) AS employee_count
FROM training.employees
GROUP BY department
ORDER BY department;
```

## Part 4: Query rows

### Select explicit columns

```sql
SELECT employee_id, name, department, salary
FROM training.employees
ORDER BY employee_id
LIMIT 5;
```

Prefer explicit columns in durable pipelines and interfaces. `SELECT *` is convenient for exploration, but it couples consumers to every column and can scan unnecessary data.

### Filter rows with `WHERE`

```sql
SELECT employee_id, name, department, salary
FROM training.employees
WHERE active
  AND salary >= 100000
ORDER BY salary DESC, employee_id;
```

The second sort key makes the ordering deterministic when employees have equal salaries.

Common predicates:

```sql
WHERE department = 'Engineering'
WHERE department IN ('Engineering', 'Finance')
WHERE salary BETWEEN 80000 AND 100000
WHERE name LIKE 'A%'
WHERE NOT active
```

`BETWEEN` includes both boundaries. Text comparison and pattern matching depend on collation and database-specific behavior.

### Logical query-processing order

SQL is written in one order but reasoned about approximately in this order:

```text
FROM and JOIN
WHERE
GROUP BY
HAVING
SELECT
ORDER BY
LIMIT
```

This explains why a `SELECT` alias is generally unavailable in `WHERE`: filtering occurs before the result expression is named.

## Part 5: Missing values and `NULL`

`NULL` means missing or unknown at the database boundary. It is not zero, an empty string, or the Boolean value `false`.

```sql
SELECT NULL = NULL AS equality_result,
       NULL IS NULL AS null_test;
```

Example result:

```text
equality_result | null_test
----------------+----------
(blank)         | t
```

The blank is how `psql` displays SQL `NULL` by default; `t` means true. Comparisons with `NULL` normally produce `UNKNOWN`, represented as `NULL`. A `WHERE` clause retains only rows for which its condition is `TRUE`.

```sql
-- Avoid: this never identifies NULL values.
WHERE some_column = NULL

-- Prefer:
WHERE some_column IS NULL
WHERE some_column IS NOT NULL
```

Useful `NULL` tools include:

```sql
COALESCE(optional_bonus, 0)
NULLIF(denominator, 0)
value IS DISTINCT FROM other_value
```

Define what missingness means for each column. Replacing every `NULL` with zero can convert “unknown” into an incorrect business fact.

## Part 6: Aggregate and group

### One result row per department

```sql
SELECT department,
       COUNT(*) AS employee_count,
       COUNT(*) FILTER (WHERE active) AS active_count,
       ROUND(AVG(salary), 2) AS average_salary,
       MIN(salary) AS minimum_salary,
       MAX(salary) AS maximum_salary
FROM training.employees
GROUP BY department
ORDER BY average_salary DESC;
```

The input grain is one employee; the output grain is one department. Every selected expression must either define the group or aggregate values within the group.

### Filter groups with `HAVING`

```sql
SELECT department, COUNT(*) AS employee_count
FROM training.employees
WHERE active
GROUP BY department
HAVING COUNT(*) >= 10
ORDER BY employee_count DESC, department;
```

`WHERE` filters employee rows before grouping. `HAVING` filters department groups after aggregation.

### SQL and pandas comparison

| Goal | SQL | pandas |
| --- | --- | --- |
| Select columns | `SELECT name, salary` | `employees[["name", "salary"]]` |
| Filter rows | `WHERE active` | `employees.loc[employees["active"]]` |
| Sort rows | `ORDER BY salary DESC` | `.sort_values("salary", ascending=False)` |
| Group summaries | `GROUP BY department` with aggregates | `.groupby("department").agg(...)` |
| Join tables | `JOIN ... ON ...` | `.merge(..., on=...)` |

SQL operates on relations managed by an engine; pandas operates on in-process DataFrames. Similar expressions do not imply the same execution, memory, concurrency, transaction, or persistence behavior.

## Part 7: Join tables without changing the intended grain

```sql
SELECT e.employee_id,
       e.name,
       e.department,
       d.office_location
FROM training.employees AS e
JOIN training.departments AS d
  ON d.department_name = e.department
ORDER BY e.employee_id
LIMIT 10;
```

Because `department_name` is unique, each employee matches at most one department and the result remains one row per employee.

Before trusting a join, ask:

1. What is the grain of each input?
2. Is the join key unique on either side?
3. Should unmatched rows be discarded or retained?
4. Can one input row match several rows and multiply the result?
5. How will input and output counts be reconciled?

Use a `LEFT JOIN` when every left-side row must remain visible even without a match:

```sql
SELECT d.department_name,
       COUNT(e.employee_id) AS employee_count
FROM training.departments AS d
LEFT JOIN training.employees AS e
  ON e.department = d.department_name
GROUP BY d.department_name
ORDER BY d.department_name;
```

`COUNT(e.employee_id)` returns zero for a department without employees. `COUNT(*)` would count the placeholder row produced by the outer join and incorrectly return one.

## Part 8: CTEs and window functions

A common table expression names an intermediate query result. A window function calculates across related rows without collapsing them into one group row.

```sql
WITH ranked_employees AS (
    SELECT employee_id,
           name,
           department,
           salary,
           DENSE_RANK() OVER (
               PARTITION BY department
               ORDER BY salary DESC
           ) AS salary_rank
    FROM training.employees
    WHERE active
)
SELECT employee_id,
       name,
       department,
       salary,
       salary_rank
FROM ranked_employees
WHERE salary_rank <= 3
ORDER BY department, salary_rank, employee_id;
```

The window partitions employees by department, orders each partition by salary, and assigns a rank while preserving one result row per employee. `DENSE_RANK` includes every employee tied at one of the top three salary values; it may therefore return more than three employees for a department.

## Part 9: Change data safely with transactions

Run this block as one unit inside `psql`:

```sql
BEGIN;

INSERT INTO training.employees (
    employee_id,
    name,
    department,
    salary,
    years_experience,
    active
)
VALUES (1001, 'Test Employee', 'Engineering', 70000, 2, true);

UPDATE training.employees
SET salary = salary * 1.05
WHERE employee_id = 1001;

SELECT employee_id, name, salary
FROM training.employees
WHERE employee_id = 1001;

ROLLBACK;
```

`BEGIN` starts an explicit transaction. `ROLLBACK` removes all changes made by this transaction, so employee `1001` will not remain. Replace `ROLLBACK` with `COMMIT` only when the entire change is correct and should become durable.

For an `UPDATE` or `DELETE`:

1. Write the intended `WHERE` predicate as a `SELECT` first.
2. Check the selected keys and row count.
3. Run the change inside a transaction.
4. Re-query and reconcile the result.
5. Commit only after verification; otherwise roll back.

A transaction protects database changes inside its boundary. It does not automatically undo files written, API calls made, or messages published elsewhere.

## Part 10: Query plans and indexes

Ask PostgreSQL how it plans and executes a query:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT employee_id, name, salary
FROM training.employees
WHERE department = 'Engineering'
  AND active;
```

`EXPLAIN ANALYZE` actually executes the statement. Use it carefully with modifying statements because it will perform the write unless protected by a transaction that is rolled back.

This 100-row table will probably use a sequential scan, and that is reasonable: reading a tiny table can cost less than navigating an index. Do not create an index merely because a query uses a sequential scan. Measure realistic cardinality, selectivity, concurrency, and latency first.

An index becomes a candidate when a real workload repeatedly benefits from locating a small subset, enforcing uniqueness, supporting a join, or avoiding an expensive sort. Indexes consume storage and add work to inserts, updates, deletes, vacuuming, backups, and migrations.

## Part 11: Data-engineering concerns

### Idempotency and reruns

A data pipeline is idempotent within a stated boundary when retrying the same logical input converges on the intended state instead of duplicating or compounding effects.

Examples:

- A plain `INSERT` retried with the same primary key fails instead of duplicating the row.
- `INSERT ... ON CONFLICT` can implement an upsert, but the conflict key and update semantics must represent business identity correctly.
- Replacing a complete partition can be rerunnable when the replacement is staged, validated, and published atomically.
- Adding 5% to the current salary is not idempotent; every retry adds another raise.

Do not “fix” duplicate-key failures by dropping the key. Determine whether the incoming row is a duplicate delivery, correction, conflict, or genuinely new entity.

### Parameterized SQL

Application code should send untrusted values as parameters through its database driver. Do not build SQL by concatenating user input:

```python
# Conceptual Python DB-API example; placeholder syntax depends on the driver.
cursor.execute(
    "SELECT employee_id, name FROM training.employees WHERE department = %s",
    (department_name,),
)
```

Parameters separate data values from SQL structure and reduce injection risk. Table or column names require controlled allowlists or database-specific identifier composition; ordinary value parameters do not represent identifiers.

### Production evolution

The local container proves basic PostgreSQL behavior on one machine. It does not prove production availability, backup recovery, concurrency, security, capacity, or query performance.

A production change may additionally require:

- A migration reviewed separately from application code.
- Backward compatibility while old and new jobs run concurrently.
- An expand, migrate, and contract sequence for schemas.
- A backup and tested restore procedure.
- Least-privileged application roles instead of a superuser.
- Connection pooling, timeouts, retry limits, and cancellation.
- Query-plan review with realistic statistics and data volume.
- Monitoring for connections, locks, replication, storage, latency, and failed jobs.

## Troubleshooting

| Symptom | Likely layer | First check |
| --- | --- | --- |
| `POSTGRES_PASSWORD` is not specified | First container initialization | Confirm `infra/postgres/.env` exists and Compose uses `--env-file`. |
| Container is exited | Docker or PostgreSQL startup | `docker compose ... logs postgres` |
| `connection refused` | Container health or port mapping | `docker compose ... ps` and wait for `healthy` |
| `password authentication failed` | Credential mismatch | Confirm the stored role password; changing `.env` alone does not update an initialized volume. |
| `database "..." does not exist` | Wrong connection target | Verify `-d bigdata` or list databases with `\l`. |
| `relation does not exist` | Wrong schema/database or table not created | Check `\conninfo`, `\dn`, and `\dt training.*`. |
| `duplicate key value violates unique constraint` | Repeated identity | Inspect the primary key and decide whether the input is duplicate, corrected, or new. |
| Foreign-key violation | Missing parent key or wrong load order | Load and verify departments before employees. |
| Query returns duplicated employees after a join | Join cardinality | Check uniqueness and match counts on both sides of the join. |
| Query appears stuck | Lock, resource use, or expensive plan | Inspect active sessions, blockers, and the query plan before retrying. |

## Stop and preserve the database

Exit `psql` with `\q`, then stop the Compose project:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml down
```

This removes the container and network but preserves `big-data-example-postgres-data`. Starting the service again reuses the database.

Do not add `--volumes` unless you intentionally want to erase the entire local PostgreSQL database.

## Knowledge check

1. What is the grain of `training.employees` and its primary key?
2. Why does the named Docker volume matter if containers are replaceable?
3. What is the difference between `WHERE` and `HAVING`?
4. Why must `NULL` be tested with `IS NULL` instead of `= NULL`?
5. Which constraint prevents loading an employee with an unknown department?
6. Why does the employee-to-department join preserve one row per employee?
7. Why can a `LEFT JOIN` plus `COUNT(*)` report one employee for an empty department?
8. What is the difference between `ROLLBACK` and `COMMIT`?
9. Why is applying `salary = salary * 1.05` unsafe to retry blindly?
10. Why might a sequential scan be correct for the current employee table?

## Practice exercises

1. Return active Finance employees ordered by salary from highest to lowest.
2. Find every department’s active employee count and average salary.
3. Return departments whose average salary is at least `85000`.
4. Join employees to departments and count employees by office location.
5. Use a window function to return the highest-paid active employee in each department, including ties.
6. Begin a transaction, insert an invalid department name, observe the foreign-key error, and roll back.
7. Predict the output grain and maximum possible row count before running each query.
8. Run `EXPLAIN (ANALYZE, BUFFERS)` for one filter and identify the scan type, estimated rows, actual rows, and execution time.

## Key takeaways

- Start with table grain, identity, ownership, and required constraints.
- SQL describes a result; the database chooses and executes the plan.
- Keys and constraints enforce invariants across every writer.
- `NULL` introduces `UNKNOWN`, so ordinary equality is insufficient.
- Grouping changes result grain; joins can multiply it.
- Transactions make database changes atomic within their boundary, not across external systems.
- Reconciliation is evidence: count, uniqueness, validity, and relationship checks must support the claim that a load succeeded.
- A local PostgreSQL container is useful integration evidence, but it is not production evidence.

## Primary resources

- [PostgreSQL 18 documentation](https://www.postgresql.org/docs/18/)
- [PostgreSQL `SELECT`](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL transaction control](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [PostgreSQL `EXPLAIN`](https://www.postgresql.org/docs/18/using-explain.html)
- [Official PostgreSQL Docker image](https://hub.docker.com/_/postgres)

## Completion checklist

- [ ] PostgreSQL reports `healthy` in Docker Compose.
- [ ] I can connect to database `bigdata` using `psql`.
- [ ] I created and loaded both training tables.
- [ ] I reconciled row count, key uniqueness, active count, and salary bounds.
- [ ] I can filter, sort, group, join, and rank rows.
- [ ] I can explain `NULL` and use `IS NULL` correctly.
- [ ] I tested a write inside a transaction and rolled it back.
- [ ] I inspected one real PostgreSQL query plan.
- [ ] I can state why local evidence does not prove production behavior.



# Additional notes from lecture

- `EXPLAIN` is a command that shows how the database will execute a query, including the steps it will take and the estimated cost of each step. It can help identify performance issues and optimize queries.
    - this is called a query plan
    - used a lot in big data pipelines to optimize queries, not relavant for job interviews
- Order of operations in SQL is important to understand, as it affects how queries are executed and how results are returned. The order is: FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY, LIMIT.
- Written order: SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT
- SQL is declarative, meaning you specify what you want, not how to get it. The database engine decides the best way to execute the query.

## Step by Step with Teacher
Note most sql commands require ending commands with ";"

1. create sample database `CREATE DATABASE sample_database;`
2. `\l` check it was created
3. `\c sample_database;` -> connect to database
4. `\dt` check the tables -> none should exist yet
5. `CREATE TABLE departments (department_id INTEGER PRIMARY KEY, department_name VARCHAR(50));`
- VARCHAR is used instead of CHAR because VARCHAR allows you to constrain in a range(0-50), CHAR(50) means every value, must be 50 exactly.
6. `\dt` -> now shows the table
7. 
```sql
CREATE TABLE employee_demo (
    employee_id INTEGER PRIMARY KEY,
    employee_name VARCHAR(100),
    department_id INTEGER,
    salary DECIMAL(10,2),
    hire_date DATE,
    active BOOLEAN,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);
```
8. now we can query these tables as one would with `SELECT`
9. we can also add to the tables with `INSERT INTO <table> VALUES(<col>,<col>), (<col>, <col>)
```sql
INSERT INTO departments VALUES
    (1, 'Engineering'),
    (2, 'Sales'),
    (3, 'Finance'),
    (4, 'Marketing'),
    (5, 'HR');
```
- NOTE, SQL is sensitive to ' vs "
    - Single quotes represent text values: `'Engineering'`.
    - Double quotes represent database identifiers: `"department_name"`
```sql
INSERT INTO employee_demo VALUES
    (101, 'Alice Johnson', 2, 73000, '2023-01-11', TRUE),
    (102, 'Bob Smith', 2, 72000.00, '2023-07-01', TRUE),
    (103, 'Carol Williams',1, 105000.00, '2020-11-20', TRUE),
    (104, 'David Brown', 3, 88000.00, '2021-05-10', TRUE),
    (105, 'Emma Davis', 2, 68000.00, '2024-01-08', FALSE),
    (106, 'Frank Miller', 1, 82000.00, '2023-02-14', TRUE);
```
10. using `WHERE` to filter, `SELECT * FROM employee_demo WHERE active = TRUE;`
11. using `ORDER BY` -> sort by col, `SELECT * FROM employee_demo ORDER BY salary ASC;`
- `ASC` vs `DEC`
12. using `GROUP BY` -> aggregate by selected group, 
```sql
     SELECT
          department_id,
          COUNT(*) AS employee_count,
          ROUND(AVG(salary), 2) AS average_salary
      FROM employee_demo
      GROUP BY department_id
      ORDER BY department_id;
```
- must have an aggregate function (COUNT, AVG, etc.)

13. using `HAVING` -> filter after aggregation, 
```sql
SELECT
    department_id,
    COUNT(*) AS employee_count,
    ROUND(AVG(salary), 2) AS average_salary
FROM employee_demo
GROUP BY department_id
HAVING COUNT(*) >= 2
ORDER BY department_id;
```
14. using `JOIN` -> combine tables, 
```sql
SELECT e.employee_id, e.employee_name, d.department_name
FROM employee_demo AS e 
JOIN departments AS d
    ON e.department_id = d.department_id
ORDER BY e.employee_id;
```
- Left table = From, Right table = Join (think reading left to right)
- `JOIN` is an inner join by default, meaning only rows that match on both sides are returned.
- `LEFT JOIN` returns all rows from the left table, and matching rows from the right table. If there is no match, NULL values are returned for columns from the right table.
- `RIGHT JOIN` returns all rows from the right table, and matching rows from the left table. If there is no match, NULL values are returned for columns from the left table.
- `FULL OUTER JOIN` returns all rows when there is a match in either left or right table. If there is no match, NULL values are returned for columns from the table without a match.
- `CROSS JOIN` returns the Cartesian product of both tables, meaning every row from the left table is combined with every row from the right table.
- `SELF JOIN` is a regular join, but the table is joined with itself. This can be useful for hierarchical data or comparing rows within the same table.
- `NATURAL JOIN` automatically joins tables based on columns with the same name and compatible data types. It eliminates the need to specify the join condition explicitly, but it can lead to unexpected results if there are unintended matching columns.
- `USING` clause is used in joins to specify the column(s) that should be used for the join condition. It simplifies the syntax when both tables have a column with the same name.
- `HASH JOIN` is a join algorithm that uses a hash table to match rows from two tables. It is efficient for large datasets, especially when the join condition is an equality comparison. The hash table is built for one of the tables, and then the other table is scanned to find matching rows.
    - HASH -> encryption algorithm, not super relavent, it uses a hash (encryption) to check equality of joins. O(1) time complexity, very fast lookup like an index.


### Importing CSV data into PostgreSQL
1. Copy the CSV file into the container:
- from the root of the repository, run:
```bash
docker cp docs/Training/Week2/sample_warehouse big-data-example-postgres:/tmp/
```
the container will now have:
     /tmp/sample_warehouse/customers.csv
     /tmp/sample_warehouse/employees.csv
     /tmp/sample_warehouse/offices.csv
     /tmp/sample_warehouse/orderdetails.csv
     /tmp/sample_warehouse/orders.csv
     /tmp/sample_warehouse/payments.csv
     /tmp/sample_warehouse/products.csv
2. Connect to the PostgreSQL container:
```bash
docker exec -it big-data-example-postgres psql -U bigdata -d bigdata
```
3. Create the table(s) to hold the CSV data:
```sql
CREATE TABLE customers (
      id integer PRIMARY KEY,
      company text NOT NULL,
      last_name text NOT NULL,
      first_name text NOT NULL,
      phone text NOT NULL,
      address text NOT NULL,
      city_and_state text NOT NULL,
      postal_code text NOT NULL,
      country text NOT NULL
  );
```

4. Load the CSV data into the table:
```sql
\copy employees FROM '/tmp/sample_warehouse/employees.csv' WITH (FORMAT csv, HEADER true)
``` 

  \copy customers FROM '/tmp/sample_warehouse/customers.csv' WITH (FORMAT csv, HEADER true)

- The `\copy` command is a `psql` client command that reads the CSV file and sends the data to PostgreSQL. 
- The `FROM` clause specifies the path to the CSV file inside the container.
- The `WITH` clause specifies options for the copy operation:
    - `HEADER true`, the first row of the CSV file is treated as column names and is not loaded into the table. 
    - `FORMAT csv` specifies that the file is in CSV format.


### Subqueries, CTEs, Window Functions, and Partitioning
- Subqueries are queries nested inside another query. They can be used in the SELECT, FROM, or WHERE clauses. Subqueries can return a single value, a single row, or multiple rows

```sql
SELECT employee_id, name, salary
FROM employees
WHERE salary > (SELECT AVG(salary)
FROM employees);
```

- CTEs (Common Table Expressions) are temporary result sets that can be referenced within a SELECT, INSERT, UPDATE, or DELETE statement. They are defined using the WITH clause and can improve query readability and organization.

```sql
WITH high_salary_employees AS (
    SELECT employee_id, name, salary
    FROM employees
    WHERE salary > (SELECT AVG(salary)
    FROM employees)
)
SELECT *
FROM high_salary_employees
ORDER BY salary DESC;
```

- Window functions perform calculations across a set of table rows that are somehow related to the current row. They are often used for ranking, running totals, and moving averages.
    - uses the `OVER` clause to define the window of rows for the function to operate on. The window can be defined by partitioning the data into groups and ordering the rows within each group.

```sql
SELECT employee_id, name, salary,
       RANK() OVER (ORDER BY salary DESC) AS salary_rank
FROM employees;
```

- Partitioning in window functions allows you to divide the result set into partitions and perform calculations within each partition. This is useful for calculating rankings or aggregates within specific groups.

```sql
SELECT employee_id, name, department, salary,
       RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank
FROM employees;
```

COMMON INTERVIEW QUESTION:

Write a query to find out what the third highest salary per department is in an employee table

```sql
WITH ranked_employees AS (
    SELECT employee_id, name, department, salary,
           DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank
    FROM employees
)
SELECT employee_id, name, department, salary
FROM ranked_employees
WHERE salary_rank = 3
ORDER BY department, salary_rank, employee_id;
```

RANK, DENSE_RANK, and ROW_NUMBER are all window functions that assign a unique rank to each row within a partition of a result set. The difference between them is how they handle ties:
- RANK: Assigns the same rank to tied rows, but leaves gaps in the ranking sequence. For example, if two employees have the highest salary, they both get rank 1, and the next employee gets rank 3.
- DENSE_RANK: Assigns the same rank to tied rows, but does not leave gaps in the ranking sequence. For example, if two employees have the highest salary, they both get rank 1, and the next employee gets rank 2.
- ROW_NUMBER: Assigns a unique sequential number to each row within a partition, regardless of ties. For example, if two employees have the highest salary, one will get row number 1 and the other will get row number 2.


### Indexes

Indexes are database objects that improve the speed of data retrieval operations on a table. They are created on one or more columns of a table and can significantly enhance query performance, especially for large datasets.
- NOTE do not use an index on a table you write to frequently, as it will slow down writes. Indexes are best for tables that are read frequently and written to infrequently.

```sql
CREATE INDEX idx_employee_salary ON employees(salary);
```

This creates an index named `idx_employee_salary` on the `salary` column of the `employees` table.