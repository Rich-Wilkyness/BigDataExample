# Thursday lecture: Snowflake, cloud storage, and dbt

> Status: Learning guide with a locally verified PostgreSQL/dbt practice project; Snowflake execution remains illustrative.
> Evidence: PostgreSQL customer build and documentation generation verified on 2026-10-02; see the project guide for code and checks.

## Prerequisites and learning path

Use [Wednesday's Snowflake foundations](3.4_Wed_Snowflake.md) for storage/compute/cloud services, virtual warehouses, databases and schemas, stages, `COPY INTO`, Snowpipe, and Snowpipe Streaming. This guide builds on those foundations with cloud storage concepts, a staged PostgreSQL/dbt customer pipeline, Snowflake performance/recovery features, and the path from raw files to analytical tables.

## Study route and learning objectives

- [dbt setup checkpoints](#dbt-setup-understand-the-tools-before-connecting): select the interpreter, prepare PostgreSQL, enter connection settings, and verify a minimal build.
- [dbt model checkpoints](#dbt-models-source--bronze--silver--gold): choose an inspectable dataset, follow `source()`/`ref()`, test Silver, publish Gold, and inspect documentation.
- [Snowflake performance, recovery, and sharing](#snowflake-performance-recovery-and-sharing): distinguish scaling, pruning, caches, historical reads, cloning, and governed sharing.
- [Data loading and transformations](#data-loading-and-transformations-raw-file--bronze--silver): explain each data boundary and how to validate loaded and transformed data.

## Snowflake as a unified data platform

- **Core idea:** bring data from different sources into a common environment for storage, processing, analysis, and sharing.
- The data warehouse is a central capability; the platform also supports data engineering, AI, and applications.
- Snowflake runs on public cloud infrastructure: AWS, Azure, or Google Cloud. Snowflake manages the underlying infrastructure for its service.
- **Unified** means teams can work through common platform capabilities instead of building a separate analytical system for every source. Source access and ingestion still need configuration.

### Does Snowflake store the data, or just its metadata?

- **Standard Snowflake tables:** Snowflake stores and manages the actual table data in its optimized cloud storage, along with metadata.
- **External tables:** data files remain in your external cloud storage; Snowflake maintains metadata that lets you query those files.
- **Schema on read:** interpreting data according to a structure when reading it. This is useful context for querying external files, but it does not describe every Snowflake table.
- You do **not** need to create your own cloud bucket to use standard Snowflake tables. A bucket you manage becomes relevant when using external storage or a file-ingestion path based on it.

Sources: [Snowflake architecture](https://docs.snowflake.com/en/user-guide/intro-key-concepts) and [External tables](https://docs.snowflake.com/en/user-guide/tables-external-intro).

## Cloud storage: objects, virtual machines, and disks

### Is an object store a file system in the cloud?

It is a useful first analogy: you upload data and retrieve it later. The underlying organization and operations differ from a local file system.

| Cloud | Object storage | Virtual machine service |
| --- | --- | --- |
| AWS | Amazon S3 | Amazon EC2 |
| Azure | Azure Blob Storage; ADLS Gen2 adds data-lake capabilities | Azure Virtual Machines |
| Google Cloud | Google Cloud Storage (GCS) | Compute Engine |

- **Object:** stored content plus metadata, identified by a key/name.
- **Bucket or container:** groups stored objects. AWS and GCS use buckets; Azure Blob Storage uses containers.
- **S3 example:** `bronze/customers/part-001.parquet` is an object key. The slashes let tools present a folder-like view; S3's object namespace is flat.
- **ADLS Gen2:** when its hierarchical namespace is enabled, it supports directory semantics rather than only a folder-like display.
- Upload and download through the provider's web interface, CLI, or SDK.

Sources: [S3 object keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html) and [ADLS hierarchical namespace](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-namespace).

### Virtual machines versus Docker containers

- A **remote instance / virtual machine** is a cloud-hosted machine with an operating system and selectable compute resources.
- A **container** packages an application's runtime and shares the host's kernel. It is not a full virtual machine.
- The useful connection to Docker is that compute and persistent storage have separate lifecycles.
- Google **Compute Engine** is the direct VM comparison; Google App Engine is a managed application platform.

### Does the disk disappear when a VM stops?

It depends on the storage type and lifecycle settings.

- **EC2 instance store:** temporary storage tied to the instance; data is lost on stop or termination.
- **EBS — Elastic Block Store:** persistent block storage attached to EC2. An EBS-backed instance can stop and restart while retaining its EBS data; termination behavior depends on the volume's deletion setting.
- **Object storage:** persists independently of a particular VM, making it useful for shared datasets, ingestion files, and longer-term storage.
- **Docker analogy:** an EBS volume is conceptually similar to a named volume because data can outlive compute. Attachment and deletion rules differ between the platforms.

Sources: [EC2 instance-store persistence](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-store-lifetime.html) and [EC2 termination behavior](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/how-ec2-instance-termination-works.html).

## Serverless: who manages the servers?

- **Serverless** means the provider manages the underlying servers rather than requiring you to provision and maintain individual machines.
- Servers still exist. You work with the service's APIs and configuration instead of administering its operating system.
- Object storage follows this managed-service model: configure buckets/containers and access, then upload or retrieve objects.
- **AWS Lambda** is a familiar example for compute: functions execute without you managing a VM.
- Pricing depends on the service and its usage dimensions. “Serverless” does not mean free, and object storage is billed differently from function execution.

Source: [AWS serverless overview](https://aws.amazon.com/serverless/).

## CoCo: Snowflake's AI coding assistant

- **CoCo** refers to **Cortex Code**, Snowflake's AI coding agent.
- It assists with data and AI development, including SQL and dbt work.
- Review generated SQL and its results before adopting a suggested transformation.

Source: [Snowflake CoCo foundations](https://www.snowflake.com/en/developers/guides/coco-foundations/).

## dbt setup: understand the tools before connecting

**dbt — data build tool** — organizes transformation models, dependencies, tests, and documentation. Begin with the [PostgreSQL customer project](dbt_test/README.md): a two-row dataset makes it easy to inspect every boundary before transferring the same concepts to Snowflake.

In an **ELT** flow, another process extracts and loads source data, then dbt transforms it inside the target database. **ETL** transforms before loading into that destination. Bronze/Silver/Gold are organizational conventions, not mandatory dbt layers. Source: [dbt SQL models](https://docs.getdbt.com/docs/build/sql-models).

### What runs where?

```text
Your Mac                                 PostgreSQL container
────────                                 ────────────────────
dbt reads project + profile
    resolves source()/ref()
    submits generated SQL ─────────────→ executes transformations
                                         stores tables/views
```

| Tool or file | Responsibility |
| --- | --- |
| `dbt` + `dbt-postgres` | Local transformation framework and PostgreSQL adapter |
| `dbt_project.yml` | Project name, profile selection, model paths, and model configuration |
| `~/.dbt/profiles.yml` | Connection targets and authentication settings |
| `models/*.yml` | Sources, descriptions, and generic data tests |
| `tests/*.sql` | Custom data tests that return invalid rows |
| `snow` | Separate Snowflake CLI; not required for the PostgreSQL project |
| `~/.snowflake/config.toml` | Snowflake CLI configuration; does not configure dbt |
| Snowsight | Snowflake browser interface for SQL, objects, and file uploads |

**Keep two questions separate:** “Where will dbt connect?” is answered by the profile; “What records will the models read?” is answered by loaded source tables and source declarations. `dbt init` sets up files and connection configuration. It does not create the PostgreSQL database or load customer data.

### Checkpoint 1: select the environment containing dbt

Run Python/dbt commands on the **Mac**, not inside the PostgreSQL container. For the installed pyenv Python used by this project:

```bash
export PYENV_VERSION=3.11.16
python --version
dbt --version
```

- If a virtual environment is active, its commands can take precedence; `deactivate` returns to the surrounding shell before selecting pyenv.
- A `.venv` prompt alone does not tell you which Python is running dbt. Inspect the Python path in `dbt debug`.
- If dbt is missing from the selected environment, install `dbt-core` and `dbt-postgres` there with `python -m pip install dbt-core dbt-postgres`.
- The Snowflake adapter is needed when targeting Snowflake, not for this PostgreSQL sequence.
- **Checkpoint:** the selected interpreter can run dbt, and the PostgreSQL adapter is listed.

Sources: [dbt installation](https://docs.getdbt.com/docs/local/install-dbt) and [Python compatibility](https://docs.getdbt.com/faqs/Core/install-python-compatibility).

### Checkpoint 2: prepare the database and distinguish input from output

The practice project uses these names deliberately:

| Name | Meaning | Who creates or supplies it? |
| --- | --- | --- |
| `dbt_test` project folder | Local SQL/YAML project | `dbt init` |
| `dbt_test` profile | Named connection configuration | `dbt init` or profile editing |
| `dbt_test` PostgreSQL database | Database containing source and output schemas | SQL setup |
| `bronze` schema | Namespace for the externally loaded source table | SQL setup |
| `dbt_dev` schema | Destination for dbt-built models | SQL setup or dbt with suitable privileges |
| `bronze.customers` | Raw customer records | SQL setup/loading |

Matching project and database names is convenient, but they are different objects. Creating a folder named `dbt_test` does not create a PostgreSQL database named `dbt_test`.

From the **Mac**, connect to the container's existing maintenance database:

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d bigdata
```

Inside psql, inspect databases with `\l`. For a fresh setup, create `dbt_test`, connect with `\c dbt_test`, and create the source/output schemas. [The project guide contains the SQL](dbt_test/README.md#prepare-the-postgresql-database-and-source-data). If the database already exists, connect to it and inspect it rather than recreating it.

- **Checkpoint:** `\conninfo` reports database `dbt_test` and user `bigdata`; `\dn` includes `bronze` and `dbt_dev` once setup is complete.
- `psql -U bigdata -d bigdata` is valid inside the container, but it selects `bigdata`, not `dbt_test`.
- Inside the container, psql can use a local Unix socket. dbt on the Mac uses the published TCP port; these are different connection paths.
- Exit psql with `\q`. Exit the container shell too if you entered one, then run dbt on the Mac.

### Checkpoint 3: initialize the project with explicit connection values

For a new project, start in `docs/Training/Week4` on the Mac:

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample/docs/Training/Week4
dbt init dbt_test
cd dbt_test
```

The repository already contains this practice project. To use it, enter its directory and configure the matching profile instead of creating another project over it.

Use the following values when prompted for PostgreSQL connection settings. Prompt wording can vary by adapter version:

| Field | Value for this setup | Why |
| --- | --- | --- |
| Adapter/database type | `postgres` | dbt executes against our PostgreSQL container |
| Host | `127.0.0.1` | dbt runs on the Mac and reaches the published container port |
| Port | `5432` | Current published PostgreSQL port; match Compose if changed |
| User | `bigdata` | PostgreSQL login supplied by the container configuration |
| Password | Existing `POSTGRES_PASSWORD` value from `infra/postgres/.env` | Authenticate the PostgreSQL user; do not invent a new password during dbt init |
| Database / `dbname` | `dbt_test` | Database created in the previous checkpoint |
| Schema | `dbt_dev` | Output location for dbt models, not the raw source schema |
| Threads | `1` | Keep execution serial and easy to follow for this small project |
| Target label | `dev` | Name of the development output; if not prompted, inspect the generated profile |

Do not enter customer names, a CSV filename, a Snowflake account identifier, or the logical source name `raw_shop` into these prompts. They ask for connection settings, not dataset values.

**Checkpoint:** `dbt_project.yml` selects `profile: dbt_test`, and `profiles.yml` has a top-level `dbt_test` entry whose `target: dev` matches an output named `dev`. A target label is author-chosen; if you choose another label, use it consistently.

Sources: [dbt init](https://docs.getdbt.com/reference/commands/init), [PostgreSQL profile fields](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup), and [profiles](https://docs.getdbt.com/docs/local/profiles.yml).

### Passwords and environment variables

The local PostgreSQL password already belongs to the container setup in `infra/postgres/.env`. A dbt profile can reference it through an environment variable instead of repeating a literal password:

```yaml
password: "{{ env_var('DBT_ENV_SECRET_PG_PASSWORD') }}"
```

From any working directory on the Mac, load the existing file and map its variable to the name used by the profile:

```bash
source /Users/richardwilkerson/VSCodeProjects/BigDataExample/infra/postgres/.env
export DBT_ENV_SECRET_PG_PASSWORD="$POSTGRES_PASSWORD"
```

- `source` loads the file into this shell; `export` makes the mapped value available to dbt launched from it.
- `DBT_ENV_SECRET_PG_PASSWORD` is our chosen variable name. It must exactly match the name inside `env_var()`.
- Initialization may generate the PostgreSQL password alias `pass`; use the installed adapter's supported field and avoid leaving a conflicting literal password beside an environment reference.
- dbt Core 1.12 can load a `.env` in its current working directory. It does not automatically discover `infra/postgres/.env` elsewhere in the repository; the explicit commands above make that relationship clear.
- This environment reference works only after the variable has a value in the environment available to dbt. Open a new terminal and repeat the setup when needed.

Source: [dbt environment variables](https://docs.getdbt.com/reference/dbt-jinja-functions/env_var).

### Checkpoint 4: verify connectivity, then verify a minimal build

From the directory containing `dbt_project.yml`:

```bash
dbt debug --target dev
```

**Checkpoint:** valid project/profile files and `Connection test: OK connection ok`. Inspect the reported host, database, schema, adapter, and Python path as well as the final success message.

Connectivity does not prove that dbt can create models. The [connection-check model](dbt_test/models/bronze/connection_check.sql) selects literal values and materializes a tiny table; it needs no customer data:

```bash
dbt run --select connection_check
```

Inside psql connected to `dbt_test`:

```sql
SELECT * FROM dbt_dev.connection_check;
```

**Checkpoint:** one stored row containing `id = 1` and `message = 'dbt is connected'`. This isolates client → database → created table before introducing source-data dependencies.

Source: [dbt debug](https://docs.getdbt.com/reference/commands/debug).

## dbt models: source → Bronze → Silver → Gold

### Checkpoint 5: load an inspectable source dataset

Use the two-column customer dataset in [the project setup](dbt_test/README.md#prepare-the-postgresql-database-and-source-data):

| customer_id | Raw name |
| --- | --- |
| 1 | `'  alice  '` |
| 2 | `'BOB'` |

- **Grain:** one source row represents one customer. `customer_id` is the intended identity; a name is not a unique identifier.
- The spaces and capitalization are deliberate: they let you see exactly what Silver changes.
- Load these rows into **`dbt_test` → `bronze` → `customers`**. `dbt_dev` is the model output schema and should not be substituted for the raw source schema.
- If this source already exists, inspect its contents first. Repeating the sample insert would duplicate the rows.
- **Checkpoint:** `SELECT * FROM bronze.customers ORDER BY customer_id;` returns the two raw rows before dbt reads them.

The source is created/loaded outside dbt. Declaring it in YAML describes an existing table; it does not perform ingestion.

### Checkpoint 6: follow `source()` into Bronze and `ref()` into Silver

Use the existing [source declaration](dbt_test/models/sources.yml), [Bronze model](dbt_test/models/bronze/bronze_customers.sql), and [Silver model](dbt_test/models/silver/silver_customers.sql).

| Reference | Meaning |
| --- | --- |
| `source('raw_shop', 'customers')` | Look up logical source `raw_shop`, then its declared `customers` table; the YAML maps it to physical `bronze.customers` |
| `ref('bronze_customers')` | Resolve a dbt model's output relation and record an upstream dependency |
| `{{ ... }}` | Jinja evaluated by dbt before the rendered SQL is submitted |
| `config(materialized='table')` | Request a table rather than a view for this model |

**Thought process:** preserve the raw values in Bronze, then normalize names in Silver with `INITCAP(TRIM(name))`. Keep the customer ID unchanged so the transformed record can still be traced to its source.

Run from the Mac project directory:

```bash
dbt run --select bronze_customers
dbt run --select +silver_customers
```

- The leading `+` includes upstream model dependencies; it does not create or load an external source table.
- **Checkpoint:** `dbt_dev.bronze_customers` is a view of the raw rows. `dbt_dev.silver_customers` is a table with `(1, 'Alice')` and `(2, 'Bob')`, ordered by ID when inspected.
- Code folders such as `models/silver/` do not create corresponding database schemas. All these model outputs use `dbt_dev` in the current profile.

Sources: [dbt sources](https://docs.getdbt.com/docs/build/sources) and [ref](https://docs.getdbt.com/reference/dbt-jinja-functions/ref).

### Materialization: decide what persists

| Materialization | Behavior | Practical consequence |
| --- | --- | --- |
| `view` | Stores a query definition | Reads underlying data when consumers query it |
| `table` | Stores computed rows at build time | Must be rebuilt to reflect changed source data |
| `incremental` | Updates a stored relation through an incremental strategy | Requires identity, changed-row selection, and rerun rules |
| `ephemeral` | Inlines the model into downstream SQL | No standalone relation for consumers to query |

SQL models normally default to views unless configuration changes that. This project's [folder configuration](dbt_test/dbt_project.yml) selects Bronze views and Silver/Gold tables; inline model configuration can override it. A custom `+schema: silver` normally yields `<target_schema>_silver` under dbt's default schema naming, rather than automatically producing an exact schema named `silver`.

Sources: [materializations](https://docs.getdbt.com/docs/build/materializations) and [custom schema naming](https://docs.getdbt.com/docs/build/custom-schemas).

### Checkpoint 7: test the contract before publishing Gold

Follow [the data-test explanation](dbt_test/README.md#custom-data-test-reject-blank-customer-names) and [Silver's YAML properties](dbt_test/models/silver/silver_customers.yml).

- A successful SQL statement proves execution, not valid customer data.
- `not_null` and `unique` on `customer_id` express the intended one-row-per-customer identity.
- `not_null` on the name still permits `''`. The [custom SQL test](dbt_test/tests/assert_customer_names_present.sql) also rejects empty or ordinary-space-only names.
- Generic tests are declared in YAML; singular tests are SQL files under `tests/`. Both look for violations, and zero violations passes under their default configuration.
- Tests detect problems. They do not repair data or add PostgreSQL constraints.

The [Gold summary](dbt_test/README.md#gold-summary-change-the-grain-deliberately) changes grain from one customer per row to one overall summary row. Its `COUNT(*)` represents customers only if Silver's identity contract holds.

```bash
dbt build --select +gold_customer_summary
```

**Checkpoint:** three selected models and four tests pass, then `SELECT * FROM dbt_dev.gold_customer_summary;` returns `total_customers = 2` for this fixture. Silver's tests run before the dependent Gold model; failure can skip Gold, but does not undo all previously built tables.

Useful distinction: without `GROUP BY`, an overall count produces one summary row even for empty input, with a value of zero. A passing uniqueness test or a count of zero does not prove source completeness; reconcile expected inputs too.

Sources: [data tests](https://docs.getdbt.com/docs/build/data-tests) and [dbt build](https://docs.getdbt.com/reference/commands/build).

### Checkpoint 8: document the model and inspect lineage

Follow [the documentation walkthrough](dbt_test/README.md#generate-and-explore-documentation):

```bash
dbt docs generate
dbt docs serve --port 8080
```

Visit `http://localhost:8080` and inspect descriptions, columns, tests, and lineage. Stop the local server with **Ctrl+C**.

- **Checkpoint:** follow `raw_shop.customers` → `bronze_customers` → `silver_customers` → `gold_customer_summary` in the lineage graph.
- Descriptions explain what a dataset means; `source()` and `ref()` record how it depends on other data.
- Documentation generation compiles models and retrieves metadata. It does not build or refresh the model tables.
- The generated site is a snapshot; regenerate it after changes. YAML descriptions do not automatically become database comments.

Source: [dbt documentation commands](https://docs.getdbt.com/reference/commands/cmd-docs).

### Choose the command for the question

| Command | Question it answers | What it does not prove |
| --- | --- | --- |
| `dbt debug` | Can the configured client connect? | Transformation correctness |
| `dbt parse` | Can dbt read the project and resolve resources? | Source existence or database SQL validity |
| `dbt compile --select silver_customers` | What SQL is generated? | Successful materialization; compilation may query metadata |
| `dbt run --select silver_customers` | Can the selected model be built? | Passing data tests; upstream models are not included without selection modifiers |
| `dbt test --select silver_customers` | Does the existing model data satisfy declared rules? | Freshness of the last build |
| `dbt build --select +gold_customer_summary` | Can the selected pipeline build and pass its tests? | Production scale, complete inputs, or whole-pipeline rollback |

Generated SQL is under `target/compiled/`; inspect it and the database error when parsing succeeds but execution fails. Sources: [parse](https://docs.getdbt.com/reference/commands/parse), [compile](https://docs.getdbt.com/reference/commands/compile), and [build](https://docs.getdbt.com/reference/commands/build).

### Transfer the same project ideas to Snowflake

Keep the project, source/model dependencies, tests, and documentation concepts. Change the adapter and connection target, map the source to its Snowflake database/schema/table, and review SQL dialect differences. PostgreSQL credentials and host settings do not become Snowflake credentials.

| Snowflake field | Value to identify |
| --- | --- |
| `type` | `snowflake`, with the Snowflake adapter installed |
| `account` | Identifier copied from account details, normally organization-account form |
| `user` | Snowflake username |
| Authentication | Supported method configured for that account, such as interactive browser authentication where available |
| `role` | Assigned role able to read sources and build intended outputs; `ACCOUNTADMIN` is not required |
| `warehouse` | Existing virtual warehouse the role can use |
| `database`, `schema` | Intended model destination |

- Add a separately named output such as `snowflake_dev` beneath the existing profile's `outputs`, then check it with `dbt debug --target snowflake_dev`.
- The organization segment alone in an `app.snowflake.com/<organization>/<account>/...` URL is not a complete account identifier.
- `snow connection add` configures the separate Snowflake CLI. A working `snow` connection does not establish a working dbt target.
- `dbt init` initializes a local dbt project; `snow init` bootstraps a chosen Snowflake CLI template project.
- Snowflake uses `USE DATABASE`; PostgreSQL psql uses `\c` to reconnect. Run SQL in the appropriate client, not directly in zsh.
- For date calculations, PostgreSQL date subtraction and Snowflake `DATEDIFF` have different expressions; inspect source types and null/error behavior before transferring a transformation.

Sources: [dbt Snowflake setup](https://docs.getdbt.com/docs/local/connect-data-platform/snowflake-setup), [account identifiers](https://docs.snowflake.com/en/user-guide/admin-account-identifier), [CLI connections](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-connections), and [snow init](https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/bootstrap-commands/init).

### Optional Snowflake CLI installation on macOS

`pip` installs packages into the selected Python environment. `pipx` installs command-line applications into isolated environments and exposes their commands on `PATH`.

```bash
brew install pipx
pipx ensurepath
```

Open a new terminal, then:

```bash
pipx install snowflake-cli
snow --version
snow --help
```

The package is `snowflake-cli`; the executable is `snow`. These commands are independent of the PostgreSQL/dbt checkpoints. Sources: [pipx installation](https://pipx.pypa.io/latest/how-to/install-pipx.html) and [Snowflake CLI installation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation).

## Snowflake performance, recovery, and sharing

### Storage and compute separation: behavior and cost

Warehouse lifecycle and table lifecycle are independent:

```text
BI warehouse ────────┐
Loading warehouse ───┼──→ the same persistent Snowflake tables
dbt warehouse ───────┘
```

- A virtual warehouse is compute, not the database or its stored tables.
- Suspending it releases warehouse compute and its local data cache; tables remain stored.
- Separate warehouses isolate compute resources for different workloads. They still access shared table state and permissions.
- Auto-suspend reduces idle warehouse compute charges. It does not eliminate storage, managed-service, or other platform charges.
- Snowflake distributes work across compute nodes (MPP). PostgreSQL on one VM commonly couples its server compute and attached storage more closely; adding replicas or changing the architecture is separate work.
- Managed optimization reduces administration, but query shape, data layout, permissions, and costs still need attention.

Sources: [warehouse considerations](https://docs.snowflake.com/en/user-guide/warehouses-considerations) and [Snowflake cost categories](https://docs.snowflake.com/en/user-guide/cost-understanding-overall).

### Scale up versus scale out

| Choice | What changes | Main purpose |
| --- | --- | --- |
| Scale up | Larger warehouse size | More resources for a workload; benefit depends on the query |
| Scale out | More clusters in a multi-cluster warehouse | More concurrent queries and less queueing |

Multi-cluster warehouses require Enterprise Edition or higher. More clusters do not mean one query automatically runs across all clusters. Start by inspecting query duration and queueing rather than assuming every slow query needs more compute. Source: [Multi-cluster warehouses](https://docs.snowflake.com/en/user-guide/warehouses-multicluster).

### Micro-partitions, pruning, and clustering

- Snowflake automatically organizes standard table data into compressed, columnar **micro-partitions**.
- It tracks metadata such as column value ranges and uses it to skip partitions that cannot match a filter: **partition pruning**.
- For `WHERE order_date = '2003-04-01'`, a partition containing only January dates can be skipped. A partition spanning March–April may need reading.
- This is different from manually creating Spark/Hive directory partitions such as `event_date=...`.
- Micro-partitions are immutable; updates change the underlying partition versions rather than modifying bytes in place.
- Very large tables can benefit from clustering keys that improve pruning for frequent filters. Measure the benefit against maintenance cost.
- Standard analytical Snowflake tables do not need PostgreSQL-style vacuum/index maintenance. Other Snowflake table types have different behavior; “no indexes anywhere in Snowflake” is too broad.

Sources: [Micro-partitions and pruning](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions) and [Clustering keys](https://docs.snowflake.com/en/user-guide/tables-clustering-keys).

### Three performance mechanisms: avoid confusing them

| Mechanism | Question it answers | Effect | Warehouse suspension |
| --- | --- | --- | --- |
| Persisted result cache | Have we already calculated this answer? | Eligible queries can reuse stored results without re-executing the query | Independent of that warehouse's local cache |
| Warehouse data cache | Have these compute nodes recently read this data? | Can reduce reads from remote table storage; the query still executes | Cache is lost |
| Micro-partition metadata | Can this partition contain matching rows? | Pruning avoids unnecessary scans | Persistent table metadata remains |

- Result reuse depends on conditions including query text, unchanged underlying data, valid cached results, and access privileges; repeating a query does not guarantee reuse.
- Metadata/pruning is not the same kind of cache as a stored result or local data copy.
- If a query drops from 30 seconds to 2 seconds, inspect result reuse, warehouse cache, scanned partitions, and query profile before claiming the SQL became more efficient.
- For a benchmark, `ALTER SESSION SET USE_CACHED_RESULT = FALSE;` disables persisted result reuse; it does not clear the warehouse's local data cache. Restore the setting afterward if appropriate.

Sources: [Persisted results](https://docs.snowflake.com/en/user-guide/querying-persisted-results) and [Warehouse caching](https://docs.snowflake.com/en/user-guide/warehouses-considerations).

### Time Travel: read an earlier state

**Time Travel** accesses historical table states within the configured retention period. Standard Snowflake tables support it; **Iceberg or Delta is not required**. Open table formats have their own versioning mechanisms and product-specific integration rules.

```sql
-- Illustrative: requires the table and retained history at this point in time.
SELECT *
FROM lecture_db.bronze.orders AT (OFFSET => -60);
```

- `-60` means 60 seconds before the current time, not “the previous version.”
- Record a timestamp or the change statement's query ID for a controlled experiment. `BEFORE (STATEMENT => '<change_query_id>')` can refer to the state before a known change.
- Retention depends on table type, configuration, and edition; a historical query fails if the requested state is unavailable.
- Fail-safe is a separate Snowflake recovery facility, not another historical SQL query window.

Source: [Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel).

### Zero-copy cloning: a separate object sharing initial storage

```sql
-- Illustrative: assumes the source exists and the clone name is available.
CREATE TABLE lecture_db.bronze.orders_clone
CLONE lecture_db.bronze.orders;
```

- A clone is an independent table object that initially references the same underlying data, avoiding an immediate full physical copy.
- Changing the clone does not change the original's logical data. New/changed partition data and retained history can increase storage.
- “Zero-copy” does not mean all future edits consume zero storage, or that every clone query is faster.
- A historical clone combines the features: `CREATE TABLE sales_yesterday CLONE sales AT (OFFSET => -86400);` requires the source to have retained history from one day earlier.
- **Distinction:** Time Travel selects a historical state; cloning creates another independently usable object.

Sources: [Cloning considerations](https://docs.snowflake.com/en/user-guide/object-clone) and [Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel).

### Semi-structured data and `VARIANT`

- `VARIANT` holds values such as JSON objects without forcing every attribute into a separate relational column at ingestion.
- `OBJECT` and `ARRAY` represent structured collections within that data.
- Assuming a table has a `payload VARIANT` column containing order JSON, `SELECT payload:country::STRING AS country FROM json_orders;` extracts a named attribute and casts it for SQL use.
- Schema flexibility does not remove the need to validate required fields, types, missing values, and business meaning.

Source: [Semi-structured data](https://docs.snowflake.com/en/user-guide/semistructured-intro).

### Secure Data Sharing and RBAC

- **Secure Data Sharing:** a provider exposes selected supported objects to a consumer account; ordinary direct sharing gives read-only access without exporting a separate data copy. The consumer ordinarily uses its own compute.
- Reader accounts can serve consumers without their own full Snowflake account, with different provider responsibilities and costs.
- Cross-region/cloud distribution has additional replication and cost considerations; do not generalize the direct-sharing no-copy model to every topology.
- Sharing is not inherently an Enterprise-only feature. Individual sharing capabilities have their own requirements.
- **RBAC:** privileges are granted to roles, and roles are assigned to users or inherited by other roles. Database/schema access, table access, and warehouse usage are distinct permissions.
- A connection that authenticates successfully can still fail a model build because its active role cannot read the source or create the destination.

Sources: [Secure Data Sharing](https://docs.snowflake.com/en/user-guide/data-sharing-intro) and [Access control](https://docs.snowflake.com/en/user-guide/security-access-control-overview).

## Data loading and transformations: raw file → Bronze → Silver

A file becomes useful analytical data through distinct steps: transferring its bytes, parsing records into a typed Bronze table, then transforming those records into a Silver dataset. Each step has a different success condition.

### Environment and context

- A database groups schemas, a schema groups objects, and a virtual warehouse provides compute. An X-Small warehouse with auto-suspend/auto-resume is a useful starting point for a small learning dataset.
- `USE WAREHOUSE`, `USE DATABASE`, and `USE SCHEMA` select session context; fully qualified names make destinations explicit.
- Check `CURRENT_DATABASE()`, `CURRENT_SCHEMA()`, `CURRENT_WAREHOUSE()`, `CURRENT_REGION()`, and the active role before interpreting results.
- Record the hosting provider/region. It identifies where the account runs, not where the CSV began.

Illustrative SQL for a new practice environment, assuming the active role has creation privileges:

```sql
CREATE DATABASE lecture_db;
CREATE SCHEMA lecture_db.bronze;
CREATE SCHEMA lecture_db.silver;

CREATE WAREHOUSE lecture_wh
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;

USE WAREHOUSE lecture_wh;
USE DATABASE lecture_db;
USE SCHEMA bronze;

SELECT CURRENT_DATABASE(), CURRENT_SCHEMA(),
       CURRENT_WAREHOUSE(), CURRENT_REGION(), CURRENT_ROLE();
```

`AUTO_SUSPEND = 60` sets the idle threshold in seconds; `AUTO_RESUME = TRUE` allows eligible work to resume a suspended warehouse. Creating these objects establishes namespaces and compute, but does not create or load an orders table.

### Loading a CSV through an internal stage

```text
Your CSV → Snowsight upload → internal stage → COPY INTO → Bronze table
                                               ↓
                                    load result + row reconciliation
```

- Begin with a small CSV whose values and expected record count you can inspect. A header describes columns and is not a data row.
- Name the record grain before loading: for example, one row per order versus one row per order line. Choose columns and keys that match it.
- A **stage contains files**; a **table contains rows**. `LIST @lecture_stage` checks upload visibility, not successful loading.
- Declare Bronze column types that match your CSV. Positional CSV loading depends on field order; the header does not automatically map arbitrary names to table columns.
- For a headered CSV, recognize `TYPE = CSV`, `SKIP_HEADER = 1`, and `FIELD_OPTIONALLY_ENCLOSED_BY = '"'` in the file-format settings. Date formats, null markers, delimiters, and quoting must agree with the actual file.
- `COPY INTO <table>` bulk-loads staged files using the chosen parsing rules; it provides a repeatable load boundary without generating thousands of hand-written inserts.
- Inspect the load result and reconcile the expected row count with `COUNT(*)`. Check representative values and types as well as counts.
- File tracking helps avoid some repeated loads, but it is not business-key deduplication. Forced reloads or the same events in differently named files can create duplicate rows.

For command syntax and the detailed stage/load distinction, use [Wednesday's stages and loading walkthrough](3.4_Wed_Snowflake.md#copy-into-staged-files-become-table-rows) and [Snowflake CSV loading options](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table).

### SQL analysis and a stored Silver transformation

- Use `WHERE` to select rows, `ORDER BY` to order results, `GROUP BY` to define aggregate groups, and `COUNT`, `SUM`, or `AVG` to summarize them. Transformation expressions change values or derive columns.
- Filtering changes which records are included; grouping changes the output grain. An aggregate grouped by country produces one row per country, not one row per order.
- A Silver schema separates cleaned datasets from raw Bronze input. `CREATE TABLE ... AS SELECT ...` stores a transformation's output at creation time; it is not automatically refreshed when Bronze changes.
- Choose transformations that suit your data: text normalization, date conversion, null handling, deduplication, or calculated columns.
- Define duplicate identity and null handling before discarding rows. Reconcile accepted, removed, and rejected records rather than assuming every lower count is correct.
- The loader owns Bronze input; transformation SQL owns derived Silver state. dbt could later manage the same transformation, dependencies, and tests.

### Observe feature behavior with controlled experiments

| Experiment | Prepare | Evidence to capture | Common mistake |
| --- | --- | --- | --- |
| Time Travel | Record a timestamp or change query ID, then make a bounded change in the practice table | Earlier state versus current state | Requesting history outside retention or before table creation |
| Zero-copy clone | Clone the practice table under a separate name | A clone modification and a comparison showing the original is unchanged | Treating a clone as a live view of future source changes |
| `VARIANT` | Create/load a small JSON file into a compatible target | Attribute extraction and values/types | Treating missing attributes and malformed types as automatically valid |
| Warehouse auto-resume | Confirm auto-resume, suspend the practice warehouse, then execute a query requiring warehouse compute | Suspended/resumed status and query result | Using a cached query result or metadata-only operation that does not need compute |

Use a small practice dataset and compare the state before and after each operation. Observed values and warehouse status distinguish actual behavior from assumptions about what a command should do.

## Next-step data-engineering topics

| Topic | Concept to understand now | Connection to our pipeline |
| --- | --- | --- |
| Streams | Track table changes since a transactional offset; not a copy of the table or a Kafka topic | Identify changed Bronze rows for incremental work |
| Tasks | Run SQL/procedural work on a schedule or supported trigger | Apply changes and publish downstream results |
| Dynamic Tables | Declare a query and desired freshness; Snowflake manages refresh | Maintain derived Silver/Gold results declaratively |
| Snowpipe | Ingest continuously arriving staged files using managed compute | Replace repeated manual file-load requests |
| Snowpipe Streaming | Ingest rows through supported clients/integrations | A direct event path instead of writing staged files first |
| Snowpark | Python/Java/Scala APIs whose supported data operations run in Snowflake | Programmatic transformations without downloading the whole dataset |
| dbt with Snowflake | Transfer sources, models, dependencies, and tests through the adapter | Change the target connection while reviewing SQL dialect compatibility |
| Cortex AI | AI functions, search, and agents integrated with the data platform | Analyze text or build retrieval/assistant workflows later |
| Marketplace/listings | Discover and distribute data products or applications | Consume governed shared data rather than inventing a manual export pipeline |

- Reading a Stream with `SELECT` alone does not advance its offset. Consuming it through a committed DML transaction does; recovery and consumption design matter.
- A Task executes work; a Stream describes changed data. Together they can drive incremental processing, but you must define the transformation and handle failures.
- Dynamic Table `TARGET_LAG` is a freshness target relative to source data, not a literal cron interval or guaranteed deadline for every refresh.
- Snowpark resembles Spark's DataFrame style, but it is a different API and execution system. Calling `collect()` brings results back to the client and changes the data-transfer boundary.
- Cortex Code/CoCo is the coding agent discussed in lecture; Cortex AI also includes functions, Cortex Search, and Cortex Agents for broader application/data workflows.

Sources: [Streams](https://docs.snowflake.com/en/user-guide/streams-intro), [Tasks](https://docs.snowflake.com/en/user-guide/tasks-intro), [Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables/overview), [Snowpark](https://docs.snowflake.com/en/developer-guide/snowpark/index), [AI features](https://docs.snowflake.com/en/guides-overview-ai-features), and [Marketplace](https://docs.snowflake.com/en/user-guide/data-marketplace). See [Wednesday's ingestion comparison](3.4_Wed_Snowflake.md#choose-the-path-by-the-input-boundary) for Snowpipe versus Streaming.

## Troubleshooting dbt by the failing boundary

| Symptom | Boundary to check | Next step |
| --- | --- | --- |
| `pipx` or `snow` not found | Shell installation/`PATH` | Check installation, run `ensurepath`, and open a new terminal |
| pyenv says dbt exists only in 3.11.16 | Interpreter selection | Select that interpreter; recheck Python and dbt versions |
| No `dbt_project.yml` found | Working directory | Enter the actual dbt project root |
| Profile not found | Project-to-profile link | Match `profile:` with the YAML top-level profile key |
| Required environment variable missing | Profile rendering | Set that variable in the same shell before running dbt |
| Authentication or connection failure | Host/account, user, auth method, network | Run `dbt debug` for the intended target; follow the selected authentication setup |
| Source relation does not exist | YAML source and actual database state | Inspect database/schema/table and confirm loading happened |
| Model created in an unexpected schema | Target/custom schema naming | Inspect target output and dbt's reported relation name |
| View created when a table was expected | Materialization configuration | Inspect model/folder/project settings and set `materialized='table'` deliberately |
| `parse` passes but `run` fails | Database execution | Inspect permissions, rendered SQL, column types, and the database error |

A working connection proves connectivity, not loaded data or transformation correctness. For later automated runs, record source versions, target context, dbt/adapter versions, accepted/rejected counts, and build/test results. Schedule ingestion before dependent builds and define rerun behavior before adopting incremental models.

## Knowledge check

Check that you can explain the mechanisms and trace their effects on data:

- Why `snow` and `dbt` use different connection files.
- How `profile`, `target`, and `outputs` select the execution destination.
- Why `source()` assumes an existing loaded table while `ref()` declares a dbt dependency.
- Why `parse`, `debug`, `run`, and `build` prove different things.
- Why a view does not fulfill a requirement for a stored Silver table.
- Why a warm query might be faster without any SQL change.
- How file upload, `COPY INTO`, and a Silver transformation change the data's location and representation.
- Why row counts, types, nulls, duplicate identities, and aggregates all matter when checking a load.
- How historical queries and independent clones solve different problems.
- How warehouse usage, table access, and model creation depend on separate role privileges.

**Evidence:** the two-row PostgreSQL/dbt customer project passed its selected three-model/four-test build and documentation generation on 2026-10-02. The project guide links the source, models, tests, and generated documentation workflow. This guide's Markdown, local links, YAML, and shell syntax were checked; the Snowflake SQL and cloud examples have not been executed. Browser rendering, invalid-data/recovery experiments, and production-scale behavior remain unverified.
