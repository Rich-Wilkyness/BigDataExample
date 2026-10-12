# Monday lecture: dbt models, dependencies, and data quality

> Status: Organized lecture guide with illustrative Snowflake examples; no Snowflake commands or dbt builds were executed for this revision.
> Level: Beginner moving into practical data engineering.
> Last reviewed: 2026-10-05 against official dbt and Snowflake documentation.

## Overview and learning objectives

A warehouse can contain successfully loaded data that is still difficult to trust or use. Data engineers need repeatable transformations, explicit dependencies, agreed business rules, and checks that detect when those rules stop holding. **dbt — data build tool —** brings those transformations, tests, and documentation into a versioned project.

This lesson follows the path from a loaded source to a useful analytical dataset. Snowflake supplies the database execution and storage; dbt manages the transformation project and submits SQL through its adapter.

After studying, you should be able to:

- Distinguish a dbt dependency graph from Spark's execution graph and an Airflow workflow.
- Separate Snowflake CLI, Python connector, and dbt connection settings.
- Trace `source()` and `ref()` through Bronze, Silver, and Gold models.
- Define grain before counting records or calculating shipping metrics.
- Choose a materialization and select the intended model dependencies.
- Write generic and singular data tests, predict a failure, and explain recovery.
- Explain pipeline ownership and your own contribution clearly.

## Prerequisites and study route

- Review [Week 4 Thursday's dbt foundations](../Week4/4_Thur_Snowflake.md#dbt-setup-understand-the-tools-before-connecting) for project initialization, profiles, targets, and the small PostgreSQL customer pipeline.
- Review [Week 4 Friday's Snowflake pipeline](../Week4/5_Fri_Snowflake_Adv.md#mental-model-where-each-step-runs) for warehouses, databases, schemas, stages, and loading.
- For a smaller starting example, use the existing [PostgreSQL/dbt customer project](../Week4/dbt_test/README.md). It has its own setup instructions and evidence; it is separate from the illustrative Snowflake shipping example below.
- To run the Snowflake examples, you need an installed `dbt-snowflake` adapter, an approved authentication method, a usable role/warehouse, a loaded source table, and a development output schema.

Study in this order: understand the graph → verify the connection → establish the input contract → build models → test the contract → inspect documentation → reason about operation and ownership.

## Mental model: what runs where?

```text
Source application / files
    │ extraction and loading owned by an ingestion process
    ▼
Snowflake RAW table
    │ source() connects the loaded table to the dbt project
    ▼
Bronze model → Silver model → Gold model → analyst / dashboard
    ▲               ▲              ▲
    └──── dbt resolves references, submits SQL, and runs checks ────┘
                  Snowflake executes SQL and stores results
```

- **ELT:** extract and load first, then transform in the destination platform.
- **SQL model:** a named SQL transformation, usually a `SELECT` in a `.sql` file. It is not a machine-learning model.
- **Adapter:** the integration that lets dbt work with a particular data platform and its SQL/materialization behavior.
- **Materialization:** how a model becomes a view, stored table, or another supported form.
- **Grain:** what one row represents at a particular boundary.
- **Lineage:** the recorded path from upstream sources through derived datasets.

Loading RAW rows remains a separate step. A source declaration tells dbt where data exists; it does not extract records or upload a CSV. Sources: [SQL models](https://docs.getdbt.com/docs/build/sql-models) and [source function](https://docs.getdbt.com/reference/dbt-jinja-functions/source).

## DAGs: the same graph concept, different responsibilities

**DAG** means **directed acyclic graph**:

- **Directed:** edges have a direction, such as upstream → downstream.
- **Acyclic:** following dependencies cannot lead back to the starting node.
- **Graph:** nodes and edges represent work or relationships.

| System | What the graph describes | Example | Responsibility |
| --- | --- | --- | --- |
| Spark | Computation dependencies; its scheduler divides work into stages and tasks, with shuffle boundaries between stages | Read → filter → join → aggregate | Execute distributed computation |
| Airflow | Task dependencies in a broader workflow | Load source → invoke dbt → notify a consumer | Schedule and coordinate work across systems |
| dbt | Dependencies among transformation resources, including models and sources | RAW orders → Bronze orders → Silver orders → Gold shipping summary | Resolve resource dependencies and build selected transformations in order |

The distinction is the **unit of work**. A dbt model is a dataset transformation; a Spark task processes a partition within distributed execution; an Airflow task can invoke an entire dbt build. These tools can cooperate in one pipeline.

### Bronze, Silver, and Gold are design conventions

- **Bronze:** expose source records with minimal changes and clear lineage.
- **Silver:** normalize and validate records at a defined business grain.
- **Gold:** produce datasets and metrics for a consumer's question.
- dbt does not automatically assign these meanings. Teams may instead use names such as `staging`, `intermediate`, and `marts`.
- Folder names organize code. Dependencies come from references, and physical output locations come from configuration.
- A circular reference, such as Silver depending on Gold while Gold depends on Silver, prevents a valid build order. Move genuinely shared logic into an upstream model.

Sources: [ref and dependencies](https://docs.getdbt.com/reference/dbt-jinja-functions/ref) and [dbt workflow conventions](https://docs.getdbt.com/best-practices/best-practice-workflows).

## Checkpoint 1: distinguish the three connection paths

A connection has two separate concerns: **authentication** establishes who you are; **authorization** determines which objects and operations your role can use.

| Client | Configuration | What a successful check establishes |
| --- | --- | --- |
| Snowflake CLI, `snow` | Snowflake CLI `config.toml` | That CLI connection can authenticate and perform the tested operation |
| Python connector | Arguments passed to `snowflake.connector.connect()` or its supported configuration | That Python connection can perform the tested operation |
| dbt | Project `profile:` plus an output in `profiles.yml` | That the selected dbt target can connect when `dbt debug` succeeds |

### Locate the correct settings

- dbt normally reads `~/.dbt/profiles.yml`; a profile-directory override can change that.
- For Snowflake CLI on macOS, the default is `~/.snowflake/config.toml` if `~/.snowflake` exists; otherwise it uses `~/Library/Application Support/snowflake/config.toml`. Overrides can change the location.
- Do not assume the captured `~/.config/snowflake/config.toml` path is your active macOS configuration.
- Editing a CLI configuration does not update dbt's profile.

Sources: [dbt profiles](https://docs.getdbt.com/docs/local/profiles.yml) and [Snowflake CLI connections](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-connections).

### Start with the dbt target you intend to use

The examples below use the Python-based **dbt Core + dbt-snowflake** workflow. Check `dbt --version` and select the matching version in the documentation; authentication behavior and available settings can differ across dbt engines and adapter releases.

Run from the directory containing the intended `dbt_project.yml`, using the Python environment that contains dbt:

```bash
dbt --version
dbt debug --target dev
```

For an existing project, configure its profile rather than initializing over it. For a new project, `dbt init` can scaffold the files, but it does not load the source data.

The following profile illustrates interactive browser authentication **where supported by your installed adapter and account**. Supply the referenced environment variables in your shell before running dbt; use your assigned account objects.

```yaml
# ~/.dbt/profiles.yml
shipping_analytics:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      authenticator: externalbrowser
      role: "{{ env_var('SNOWFLAKE_ROLE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      database: DE_CLASS
      schema: DBT_DEV
      threads: 1
```

- `shipping_analytics` and `dev` are author-chosen names. The project's `profile: shipping_analytics` must match the top-level profile name.
- `type`, `account`, `schema`, and `authenticator` are adapter configuration fields.
- `DE_CLASS` and `DBT_DEV` are illustrative object names. Match the actual database and development schema you are permitted to use.
- Use the Snowflake account identifier from account details, not an AWS account number or only the organization segment of a browser URL.
- The role needs access to the warehouse, source database/schema/table, and appropriate privileges to create or replace its output objects.

**Checkpoint:** `dbt debug --target dev` reports a successful connection. A small model build is still needed to verify output permissions; source access must also be checked. Source: [dbt Snowflake setup](https://docs.getdbt.com/docs/local/connect-data-platform/snowflake-setup).

### Optional Python MFA connection check

The Python connector can help isolate a connection issue. It is not a required pre-login step for every dbt run. If your account supports password-plus-MFA with token caching, the captured approach can be expressed without embedding credentials in source code:

```bash
python -m pip install "snowflake-connector-python[secure-local-storage]"
```

```python
import os
from getpass import getpass

import snowflake.connector

with snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    password=getpass("Snowflake password: "),
    authenticator="username_password_mfa",
    passcode=getpass("Current authenticator code: "),
    client_request_mfa_token=True,
) as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE()")
        print(cursor.fetchone())
```

- Use a current one-time code if your configured MFA method supports this flow; an expired code can fail authentication.
- MFA caching also requires account-side enablement and compatible local credential storage. A local install alone does not enable server-side caching.
- Successful Python authentication does not guarantee dbt uses the same settings or can reuse a cached token. Check dbt's own target afterward.
- Keep passwords and one-time codes outside committed files. For scheduled jobs, use an approved unattended method, such as key-pair authentication or OAuth, instead of relying on a person to enter codes.

Sources: [Python connector authentication](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect) and [connector parameters](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-api).

## Checkpoint 2: define the shipping data contract

The shipping fields in the notes are `order_number`, `shipping_date`, `status`, and `days_to_ship`. The example below uses only those fields. **The physical source table, types, valid statuses, and sample values below are teaching assumptions; inspect the actual source before using them.**

| Field | Assumed meaning and type | Rule to confirm |
| --- | --- | --- |
| `order_number` | Text identifier for an order | Present and unique if one row represents one order |
| `shipping_date` | DATE; nullable until shipment | Required for an order marked `SHIPPED` |
| `status` | Text such as `PENDING` or `SHIPPED` | Normalize case/spacing; agree the full allowed vocabulary |
| `days_to_ship` | Numeric duration supplied by the source | Nonnegative; required for shipped orders; NULL for pending orders |

- **Source grain assumption:** one current row per order. If the source contains order lines, shipment events, or history, this assumption fails; define the appropriate key and reduction rule first.
- **Silver grain:** one normalized row per order, provided the source identity tests pass. Normalization alone does not remove duplicates.
- **Gold grain:** one row per status.
- `days_to_ship` is read from the source here. Calculating it yourself would require an agreed start date, end date, unit, and calendar rule; those extra inputs are not supplied in the captured notes.
- `customer_sales` is another possible consumer dataset. A customer sales aggregation requires customer identity and sales measures that are not specified here; define that separate contract before implementing it.

Illustrative fixture:

| order_number | shipping_date | Raw status | days_to_ship |
| --- | --- | --- | --- |
| A100 | 2026-10-02 | `' shipped '` | 2 |
| A101 | 2026-10-03 | `'SHIPPED'` | 4 |
| A102 | NULL | `'pending'` | NULL |

The ingestion owner must load these records into the assumed `DE_CLASS.RAW.ORDERS` table before dbt runs. Check source counts, types, and rejected loads; a transformation cannot recover records that never reached its input.

## Checkpoint 3: trace source → Bronze → Silver → Gold

This is an illustrative project layout, not an existing Week 5 runtime project. The following snippets show the files you would place in a configured development project:

```text
shipping-analytics/
├── dbt_project.yml
├── models/
│   ├── sources.yml
│   ├── bronze/
│   │   └── bronze_orders.sql
│   ├── silver/
│   │   ├── silver_orders.sql
│   │   └── silver_orders.yml
│   └── gold/
│       └── gold_shipping_performance.sql
└── tests/
    └── assert_shipping_rules.sql
```

### Project configuration

```yaml
# dbt_project.yml
name: shipping_analytics
version: '1.0.0'
config-version: 2
profile: shipping_analytics
model-paths: [models]
test-paths: [tests]

models:
  shipping_analytics:
    bronze:
      +materialized: view
    silver:
      +materialized: table
    gold:
      +materialized: table
```

Here, `shipping_analytics` beneath `models:` matches the project `name`, while `profile:` selects the connection profile. This example writes all model outputs to the target schema `DBT_DEV`; the three code folders do not automatically create three Snowflake schemas.

With default schema naming, adding `+schema: silver` usually produces `<target_schema>_silver`, such as `DBT_DEV_silver`. Inspect schema-generation configuration before expecting an exact `SILVER` schema. Sources: [materialization configuration](https://docs.getdbt.com/reference/resource-configs/materialized) and [schema configuration](https://docs.getdbt.com/reference/resource-configs/schema).

### Declare the loaded source

```yaml
# models/sources.yml
version: 2
sources:
  - name: raw_shop
    database: DE_CLASS
    schema: RAW
    tables:
      - name: orders
        identifier: ORDERS
        description: "Loaded current order records; assumed one row per order."
```

`raw_shop` is a logical source name. `orders` is the logical table name used by dbt; `identifier: ORDERS` maps it to the physical table. `source('raw_shop', 'orders')` resolves that declaration and records source lineage. Source: [source function](https://docs.getdbt.com/reference/dbt-jinja-functions/source).

### Bronze: expose the input

```sql
-- models/bronze/bronze_orders.sql
select
    order_number,
    shipping_date,
    status,
    days_to_ship
from {{ source('raw_shop', 'orders') }}
```

Bronze exposes the four fields without silently filtering or changing their values. A view does not archive a historical copy of the source; ingestion retention is a separate responsibility.

### Silver: normalize with an explicit rule

```sql
-- models/silver/silver_orders.sql
select
    nullif(trim(order_number), '') as order_number,
    shipping_date,
    nullif(upper(trim(status)), '') as status,
    days_to_ship
from {{ ref('bronze_orders') }}
```

- `{{ ... }}` is Jinja syntax evaluated by dbt before it submits SQL.
- `ref('bronze_orders')` names the upstream dbt model and resolves its configured relation.
- `TRIM` removes ordinary surrounding spaces; `UPPER` standardizes status case.
- `NULLIF(..., '')` turns empty normalized values into NULL so missing identifiers/statuses are detectable by `not_null` tests.
- The assumed source already has DATE/numeric types. If it contains raw text, define safe parsing and rejected-record handling before adding casts.
- The model preserves rows. Duplicate IDs and invalid durations are exposed to tests rather than silently removed.

**Checkpoint:** the fixture yields statuses `SHIPPED`, `SHIPPED`, and `PENDING`, with unchanged order identities and durations. Source: [ref function](https://docs.getdbt.com/reference/dbt-jinja-functions/ref).

### Gold: change the grain deliberately

```sql
-- models/gold/gold_shipping_performance.sql
select
    status,
    count(*) as order_count,
    count(days_to_ship) as orders_with_duration,
    avg(days_to_ship) as avg_days_to_ship
from {{ ref('silver_orders') }}
group by status
```

Expected result for the fixture, when inspected with `ORDER BY status`:

| status | order_count | orders_with_duration | avg_days_to_ship |
| --- | --- | --- | --- |
| PENDING | 1 | 0 | NULL |
| SHIPPED | 2 | 2 | 3 |

- `COUNT(*)` counts rows. It represents orders only when the one-row-per-order contract holds.
- `COUNT(days_to_ship)` counts non-NULL durations; `AVG` also excludes NULL durations. The explicit count exposes the denominator.
- A shipped order missing a duration could make the average look acceptable while omitting that order; the test below detects this.
- An empty Silver input produces no groups and therefore no Gold rows. Passing key tests on empty input does not prove a complete load.
- SQL results have no guaranteed display order without an explicit `ORDER BY` in the inspection query.

## Checkpoint 4: choose how results persist

| Materialization | What it creates | Use and tradeoff |
| --- | --- | --- |
| `view` | A stored query definition | Useful for light transformations; query cost remains at read time, and freshness follows its inputs |
| `table` | Stored results rebuilt by ordinary runs | Useful for reusable outputs; data remains at its last successful build until refreshed |
| `incremental` | A table maintained through the configured strategy | Can reduce repeated work; requires changed-row selection, key/update rules, and handling for late corrections |
| `ephemeral` | Logic embedded into dependent SQL as a CTE | Useful for small reusable steps; no standalone relation to inspect |

These are four common choices, not an exhaustive list of adapter capabilities. Bronze/Silver/Gold do not mandate particular materializations. The example chooses views for exposure and tables for inspectable cleaned/aggregated results. Source: [dbt materializations](https://docs.getdbt.com/docs/build/materializations).

## Checkpoint 5: select the intended graph

Run these commands from the configured project directory. Preview the selected models before building:

```bash
# Preview the target model and upstream models.
dbt ls --select +gold_shipping_performance --resource-type model

# Build the target model and its upstream models; this does not run data tests.
dbt run --select +gold_shipping_performance

# Build the selected graph and run applicable tests.
dbt build --select +gold_shipping_performance
```

| Selector | Meaning |
| --- | --- |
| `gold_shipping_performance` | Select that named model |
| `+gold_shipping_performance` | Include its ancestors |
| `silver_orders+` | Include its descendants |
| `+silver_orders+` | Include ancestors and descendants |
| `path:models/gold` | Select resources by their code path |

The captured `dbt run --select +gold` relies on how `gold` matches project resources. Use an explicit model name for this example. To select the Gold folder and its ancestors, preview `dbt ls --select +path:models/gold --resource-type model`, then use that selector with `run` or `build`.

The leading `+` includes existing resource dependencies; it does not extract or load external source rows. Source: [graph operators](https://docs.getdbt.com/reference/node-selection/graph-operators).

## Checkpoint 6: test the data contract

A query can succeed while producing wrong business results. **Data tests** check the records produced by a model or present in a source. Under default thresholds, zero violating rows means a pass.

### Generic tests: reusable assertions declared in YAML

```yaml
# models/silver/silver_orders.yml
version: 2
models:
  - name: silver_orders
    description: "Normalized current orders; one row per order when identity checks pass."
    columns:
      - name: order_number
        description: "Normalized order identifier."
        data_tests:
          - not_null
          - unique
      - name: status
        description: "Normalized shipping status."
        data_tests:
          - not_null
          - accepted_values:
              arguments:
                values: ['PENDING', 'SHIPPED']
```

- `not_null` finds missing values; on a raw text column it does not reject empty strings. Silver's normalization makes ordinary blank values NULL.
- `unique` detects repeated non-NULL values; pair it with `not_null` to enforce a required identity.
- `accepted_values` checks the agreed vocabulary. The two values here belong to the fixture, not a universal shipping standard.
- `relationships` can check that a foreign key references an existing parent key when that parent dataset exists.

This uses current `data_tests:` syntax and nested `arguments:` supported in dbt Core 1.10.5 and later. Match the documentation to your installed version; older projects may use the `tests:` alias and arguments directly under the test name. Source: [data test properties and syntax](https://docs.getdbt.com/reference/resource-properties/data-tests).

### Singular test: return rows that violate shipping rules

```sql
-- tests/assert_shipping_rules.sql
select
    order_number,
    status,
    shipping_date,
    days_to_ship
from {{ ref('silver_orders') }}
where days_to_ship < 0
   or (
       status = 'SHIPPED'
       and (shipping_date is null or days_to_ship is null)
   )
   or (
       status = 'PENDING'
       and (shipping_date is not null or days_to_ship is not null)
   )
```

The query selects **bad rows**, not good rows. `days_to_ship < 0` alone would miss NULL durations because comparisons with NULL are unknown; explicit `IS NULL` checks enforce completeness for shipped orders. Adapt the pending-order rule if your source contains planned shipment dates or estimated durations.

The test detects violations; it does not repair them, delete records, or create warehouse constraints. Source: [dbt data tests](https://docs.getdbt.com/docs/build/data-tests).

### Demonstrate a failure before repairing it

Use a disposable development fixture, with the ingestion method that owns that fixture. The following outcomes are predictions, not recorded executions:

1. Build the three valid sample orders. Expect all declared checks to pass and the shipped average to equal 3.
2. Add another row with `order_number = 'A100'`. Expect `unique` to fail; counting rows now overstates the number of orders.
3. Restore the valid fixture, then change A100's duration to `-2`. Expect the singular test to fail.
4. Restore the valid fixture, then set A101's duration to NULL. Expect the shipped completeness rule to fail even though an average could still be calculated from A100.
5. Restore the valid fixture, then use status `LOST`. Expect `accepted_values` to fail under the two-status contract.
6. Remove all fixture rows. Predict which tests still pass, and explain why reconciliation or a minimum-volume rule is needed to detect an unexpected empty load.
7. Repair the responsible source or transformation rule and rerun the same selected build. Check both test results and Gold values.

```bash
# Check an already-built Silver relation.
dbt test --select silver_orders

# Rebuild and test the selected source-to-Gold graph.
dbt build --select +gold_shipping_performance
```

With default error severity, an upstream test failure in `dbt build` can skip dependent downstream resources. This is not whole-pipeline rollback: models already built remain, and a skipped Gold table may still contain its previous results. Multi-parent tests have dependency-specific skipping rules. Check run results and consumer freshness before declaring publication successful. Source: [dbt build behavior](https://docs.getdbt.com/reference/commands/build).

## Checkpoint 7: inspect generated SQL, documentation, and lineage

| Command | Purpose | Limit |
| --- | --- | --- |
| `dbt debug --target dev` | Check configuration and connectivity | Does not prove model correctness or all object permissions |
| `dbt parse` | Read the project and resolve its resources | Does not validate every SQL statement against the database |
| `dbt compile --select silver_orders` | Render Jinja into SQL | Does not materialize the model; compilation can access warehouse metadata |
| `dbt run --select silver_orders` | Build the selected model | Does not automatically include ancestors or run data tests |
| `dbt test --select silver_orders` | Check existing model data | Does not refresh that model |
| `dbt build --select +gold_shipping_performance` | Build and test the selected graph | Does not establish source completeness or production reliability |

Sources: [debug](https://docs.getdbt.com/reference/commands/debug), [compile](https://docs.getdbt.com/reference/commands/compile), and [build](https://docs.getdbt.com/reference/commands/build).

Inspect generated SQL in `target/compiled/` when a reference or expression does not resolve as expected. Then generate the project's documentation:

```bash
dbt docs generate
dbt docs serve --port 8080
```

- Open `http://localhost:8080`; stop the server with **Ctrl+C**.
- Trace `raw_shop.orders` → `bronze_orders` → `silver_orders` → `gold_shipping_performance`.
- Explain grain, allowed statuses, the average's denominator, ownership, and refresh expectations in descriptions.
- Documentation generation creates metadata artifacts; it does not refresh model tables. Regenerate documentation after project changes.

Source: [dbt documentation commands](https://docs.getdbt.com/reference/commands/cmd-docs).

## Troubleshooting by the failing boundary

| Symptom | Likely boundary | Next check |
| --- | --- | --- |
| `dbt` missing or Snowflake adapter unavailable | Python environment / installation | Selected executable and `dbt --version`; compare with the environment used for installation |
| Python connects but `dbt debug` fails | dbt profile or authentication | Profile name, target, account, authentication method, environment variables, and adapter version |
| Missing environment variable | Profile rendering | Exact variable name and whether it is available to the current shell process |
| Login succeeds but model creation fails | Authorization | Active role, warehouse access, source access, and destination privileges |
| Source not found | Ingestion / source mapping | Physical database/schema/table and whether the load completed |
| `ref()` cannot resolve a model | Project graph | Model filename, enabled resources, and exact reference name |
| Expected `SILVER` schema is missing | Output configuration | Target schema and custom schema-generation rules |
| Gold counts too many orders | Grain / identity | Duplicate Silver keys and source records that actually represent lines or events |
| Gold average looks reasonable but excludes orders | Metric completeness | Non-NULL duration count and shipped completeness test |
| Gold is skipped or stale | Quality failure / publication | First error-severity upstream failure, run results, and last successful Gold build |

Investigate the first meaningful failure before treating every downstream skip as a separate defect. Repair the owner of the failing rule, rebuild the affected dependency graph, and reconcile the resulting data.

## Production considerations: move beyond a successful demo

The three-row fixture teaches model behavior; it does not measure warehouse cost, throughput, concurrency, or recovery. Define actual volume, freshness, build window, and consumer requirements before optimizing.

- **Ownership:** ingestion owns loaded-record completeness; transformation owners own cleaning, grain, tests, and metrics; consumers agree the output meaning and freshness expectations.
- **Freshness:** a table can pass all quality checks while being stale. Track load completion and successful model refresh separately.
- **Publication:** if several tables must become visible consistently, design a publication gate or cutover procedure. Do not assume one dbt build atomically publishes the whole graph.
- **Reruns:** the example rebuilds tables from current inputs. Incremental pipelines additionally need stable keys, late-data and update/delete rules, backfills, and comparison with full-build results.
- **Performance and cost:** inspect query history, scanned data, expensive joins, repeated view computations, and build duration. Increase threads or warehouse size only after identifying the limiting work.
- **Delivery:** version SQL/YAML, review changes, use isolated development outputs, and validate before promoting to production.
- **Operations:** retain appropriate logs, `manifest.json`, and `run_results.json`; record owners and recovery steps. Apply access/retention rules because artifacts may contain query or object metadata.
- **Security:** grant the required privileges through assigned roles, keep credentials out of models, and use an approved authentication method for automated execution.

A practical readiness question is: “If Silver fails tonight, what do dashboard users see tomorrow, who notices, and how do we restore a complete and current Gold dataset?”

## Explain the architecture and your role

### Describe dbt and the execution platform together

- Name both the transformation framework and the platform: for example, “dbt models running on Snowflake.”
- dbt supports multiple platforms through adapters, including Snowflake, PostgreSQL, BigQuery, Redshift, Databricks, and Spark. Snowflake and Redshift are not the only choices.
- Match the explanation to systems you have used. A usage percentage without a named, dated source is not a useful architectural justification.

Source: [supported data platforms](https://docs.getdbt.com/docs/supported-data-platforms).

### Use a source → ingest → process → serve explanation

| Question | What to explain |
| --- | --- |
| Where did records originate? | Source application, database, files, or event stream; intended record identity |
| How did they arrive? | Extraction/loading mechanism, batch or streaming cadence, and load validation |
| What changed during processing? | Normalization, joins, grain changes, business rules, and quality checks |
| Where did results go? | Gold datasets, dashboards, downstream applications, or exports |
| What did you own? | Specific models, tests, loads, monitoring, debugging, or operational improvements |
| How did you know it worked? | Observed results, reconciliation, tests, freshness, and measured performance where available |

An illustrative role description is: “The ingestion process loaded order data into Snowflake RAW. I owned the Silver normalization and Gold shipping summary in dbt. I defined the one-row-per-order contract, added identity and shipping-rule tests, and checked that the Gold count and average matched the input.” Use that wording only for work you actually performed.

You can explain the full architecture while being precise about your contribution and collaborators' responsibilities. Practice the architecture and failure story alongside SQL, Python, Spark, and dbt mechanics; technical details become easier to explain when their purpose is clear.

## Knowledge check

1. Why can an Airflow task invoke dbt while Snowflake executes the resulting SQL?
2. What do `source()` and `ref()` each resolve, and why do folders alone fail to define a DAG?
3. Why does a successful Python MFA login fail to establish that the dbt target is configured correctly?
4. Predict the models selected by `+gold_shipping_performance` and by `silver_orders+`.
5. If an order appears on three line-item rows, why is `COUNT(*)` an incorrect order total? What grain must you establish first?
6. Why pair `unique` with `not_null`, and why might both pass on an empty dataset?
7. What happens to the Gold average if a shipped order has NULL `days_to_ship`? Which test should detect it?
8. What can remain in the warehouse after an upstream data test fails during `dbt build`?
9. If table data is correct but yesterday's, which guarantee is missing?
10. Describe one transformation you own, its consumer, its most important invariant, and its recovery procedure.

## Key takeaways

- Define record meaning and ownership before building a transformation.
- dbt manages transformation dependencies; the selected data platform executes them.
- `source()` references externally loaded data; `ref()` connects dbt resources.
- Bronze/Silver/Gold are design conventions, and folder names are separate from database schemas.
- Connectivity, execution, data quality, completeness, and freshness require different evidence.
- A useful pipeline explanation connects architecture, personal responsibility, and observed results.

## Completion and evidence checklist

- [ ] Explain the DAG comparison and trace the source-to-Gold graph.
- [ ] Verify the intended dbt target and permissions in a development environment.
- [ ] Confirm actual source fields, types, identity, statuses, and shipping rules.
- [ ] Preview selection, build the graph, and reconcile fixture outputs.
- [ ] Demonstrate invalid and empty input, repair the cause, and verify recovery.
- [ ] Inspect documentation and identify freshness/publication ownership.

**Evidence for this guide:** official documentation was reviewed and the embedded examples received static checks during editing. Snowflake login, dbt parse/compile/build, invalid-data demonstrations, browser documentation rendering, and operational/performance checks remain pending. The linked Week 4 PostgreSQL project has separate local evidence; it does not validate this Snowflake example.
