# AWS Advanced, Part 2: Citi Bike Gold Layer and Star Schema

> Level: Beginner to intermediate  
> Applies to: Dimensional modeling, Amazon Redshift, SQL analytics, AWS networking  
> Example status: Conceptual walkthrough with illustrative SQL expressions; star-schema implementation remains learner-owned  
> Evidence status: Saved artifacts reviewed; no AWS jobs or Redshift SQL executed during this revision  
> Last reviewed: 2026-10-11

## Overview

Friday's lesson extends the Citi Bike pipeline from loading cleaned data into Redshift to organizing it for analysis. A **star schema** connects observations and measurements in a central fact table to dimensions that describe those observations.

These notes explain the lesson and the intent behind the captured SQL. Unfinished statements are described rather than completed, so you can choose your grain and write your own SQL. Added explanations are study guidance, not a reconstruction of everything the teacher said.

## Learning objectives and study route

- Explain how the existing Gold summary differs from a star schema.
- Define what one row represents before choosing columns and keys.
- Distinguish facts, dimensions, business keys, and surrogate keys.
- Explain dimension-first loading, deduplication, and referential integrity.
- Choose between `WHERE`, `HAVING`, and `QUALIFY`.
- Extract calendar attributes, format labels, cast types, bucket time, and handle nulls using Redshift SQL.
- Translate a natural-language question into an analytical plan and explain the result's limits.

Review the [Thursday Glue and Redshift notes](4_Thur_AWS_Glue.md) for the existing pipeline. For hands-on work, you need your learner Redshift workgroup/database and permission to inspect the source and create Gold objects. Read sections 1–3 first, write your grain statement in section 11, then return to loading and validation. Section 9 is a networking refresher.

## 1. Where this lesson fits in the pipeline

```text
Citi Bike API → Lambda → S3 Bronze JSON
                             ↓ EMR or Glue / Spark
                        S3 Silver Parquet
                             ↓ existing Glue loader
               Redshift: public.citibike_station_snapshot
                             ↓ your Redshift transformations
               Gold dimensions + Gold fact table
                             ↓ analytical queries / reporting views
                        Answers to business questions
```

| Dataset | Responsibility | Meaning of one row |
| --- | --- | --- |
| S3 Bronze | Preserve captured source responses | Raw API records inside captured responses |
| S3 Silver | Clean and structure station observations | A station at a captured snapshot |
| `public.citibike_station_snapshot` | Retain cleaned station detail in Redshift | A station at a captured snapshot |
| `gold.station_availability_summary` | Summarize operational stations | One captured snapshot across operational stations |
| Proposed Gold star | Organize observations and descriptive context | To be specified by your design |

The saved [Silver-to-Redshift loader](4.1_EMR_citibike/richard-citibike-silver-to-redshift.py) checks missing and duplicate station/snapshot keys, loads staging, and merges into `public.citibike_station_snapshot`. It does not create the star tables. Keep this loader as it is for this redesign: the next transformation boundary is inside Redshift.

The existing [Gold SQL](4.1_EMR_citibike/gold-station-availability-summary.sql) defines a reporting **view**. Gold describes a business-ready layer; views, summaries, and dimensional models can all serve that purpose. The new requirement changes how Gold is organized.

Build the star from the detail table. The current summary has aggregated away station identity and cannot supply that detail. Keep the view while designing and validating the star; later, decide whether to retain it or recreate equivalent reporting over the star.

## 2. Understand the star before building it

The teacher proposed `gold.dim_station`, `gold.dim_date`, and `gold.fact_station_snapshot`. These names communicate roles; they do not replace a written grain definition.

```text
gold.dim_station ────── gold.fact_station_snapshot ────── gold.dim_date
station description       observations and measures        date attributes
```

| Term | Meaning | Question to ask |
| --- | --- | --- |
| Grain | The precise meaning of one row | What does this record represent? |
| Fact table | Observations/events at a declared grain, with measures and dimension references | What was observed, in which context? |
| Dimension | Descriptive context for labeling, filtering, and grouping facts | Which station? Which date? |
| Measure | A recorded or calculated value for analysis | What count, quantity, or percentage was observed? |
| Business key | Identity supplied by the source or business | Does the source station ID identify the station? |
| Surrogate key | Identity assigned by the warehouse | Do I need a warehouse key to distinguish versions? |
| Foreign key | A reference to a dimension's key | Which dimension row describes this fact? |
| Referential integrity | Required references resolve to their intended rows | Are facts missing station or date context? |

### Grain comes first

- Start with the business question and meaning of one row.
- Identify which values make that row unique.
- Check that every measurement belongs at that grain.
- Decide how dimensions describe the observation and connect through keys.
- Choose types and write SQL after those decisions are clear.

Snapshot data records state at an observation time. It does not record individual trips. The pasted `fact_trips`, trip-duration, and start-station examples referred to another dataset; those facts are unavailable here. Kimball's [fact-table guidance](https://www.kimballgroup.com/2008/11/fact-tables/) explains why grain is the starting point for dimensional design.

### Why use a star schema?

- Keep measurements at a consistent grain so analysts know what they are counting or averaging.
- Store shared descriptions in dimensions rather than repeating every attribute in every fact row.
- Make joins understandable: facts connect to station and date context.
- Reuse descriptive context across analytical questions.

The schema alone does not correct duplicates, enforce relationships, or guarantee faster queries. Those require validation and, at larger scale, measured query behavior.

## 3. Decisions behind the classroom tables

### Station dimension: current or historical descriptions?

The captured station statement tried to choose the latest observation per station, including its name and capacity.

- **Current state:** keep one current description per station. Updating attributes in place is the idea behind slowly changing dimension **Type 1**. Old facts joined to that dimension display current descriptions.
- **History:** retain versions and connect each fact to the appropriate version. This is the idea behind **Type 2**; it needs version identity and validity rules.
- Names and capacities can change. Decide whether historical observations should display current or historical attributes.
- A percentage stored in an old fact may have used a different capacity from the one now displayed by a current-state dimension.

The teacher's latest-row approach points toward current-state descriptions. It does not establish a complete historical-dimension design.

### Date dimension: calendar context

The captured date statement derived dates, years, months, days, and days of week from snapshot timestamps.

- A date dimension gives reports consistent calendar attributes.
- Distinct dates derived from observations include only dates that appear in the source.
- A complete calendar can include dates without observations, making gaps visible.
- A date key identifies a day; it cannot distinguish observations within that day.
- Choose a reporting time zone before deriving dates. UTC and New York local dates can differ for the same instant.

The teacher used an integer encoded as `YYYYMMDD`. That is a design choice, not a star-schema requirement. Redshift's [datetime formats](https://docs.aws.amazon.com/redshift/latest/dg/r_FORMAT_strings.html).

### Fact table: measures and relationships

The captured fact statement included station/date references, a snapshot timestamp, availability counts, utilization, and status flags. Check those ingredients against your own grain.

- Dimension references supply context; the timestamp preserves detail a date key loses.
- Availability counts describe state at a moment. Adding the same station's bike count across times does not count unique bikes or trips.
- Utilization needs a stated formula and weighting rule. The saved Silver script computes bikes available divided by positive capacity, multiplied by 100; other cases produce null.
- Adding percentages is generally not meaningful. Averaging station percentages and dividing total bikes by total capacity produce different weightings.
- Flags support counts of observations meeting conditions. Decide how unknown/null values should be reported.

## 4. Follow the classroom work in Redshift

### Connect and inspect

1. Open Amazon Redshift → Query editor v2 and select your learner workgroup.
2. The recorded choice was **Other ways to connect → Federated user**, database `dev`. Use it if available and authorized for your identity; it obtains temporary credentials. See AWS's [connection guide](https://docs.aws.amazon.com/redshift/latest/mgmt/query-editor-v2-connecting.html).
3. Confirm database, schema, and object names before running anything.
4. Inspect detail-table columns/types, sample rows, total rows, and timestamp range.
5. Inspect the Gold view separately: its count represents snapshots, whereas detail-table counts represent station observations.
6. Check missing keys and duplicate source identities. Loader validation does not prove every other writer preserved the same rules.

The captured `DESCRIBE gold.dim_date` was shorthand for inspecting columns. Use the object browser or Redshift's documented [SHOW COLUMNS](https://docs.aws.amazon.com/redshift/latest/dg/r_SHOW_COLUMNS.html) command when writing your inspection statement.

### Why create and populate dimensions before facts?

- **Create first:** referenced dimension objects and keys exist when defining fact relationships.
- **Populate first:** dimension rows are available for fact key lookup, especially with warehouse-generated keys.
- **Validate first:** duplicate dimension keys can multiply facts in joins; missing keys can remove facts from inner-join reports.
- **Load facts next:** confirm required station and date references resolve.

This is dependency order, not proof that Redshift rejects invalid references. Primary-key, unique, and foreign-key constraints are informational in Redshift; `NOT NULL` is enforced. The pipeline must uphold declared key relationships. Invalid declarations can affect query results because the optimizer trusts them. See AWS's [table-constraint documentation](https://docs.aws.amazon.com/redshift/latest/dg/t_Defining_constraints.html).

| Stage | Your task | Evidence before continuing |
| --- | --- | --- |
| Inspect | Understand the source | Types, samples, date range, missing-key and duplicate findings |
| Design | Write grain, keys, measures, and history rules | A contract you can explain |
| Dimensions | Create and populate descriptions | Unique populated keys and expected attributes |
| Facts | Load observations at the declared grain | Expected counts and unique identities |
| Relationships | Check station and date references | No unexplained orphans or join multiplication |
| Analytics | Answer business questions | Output with units, time range, and observation counts |
| Replay | Repeat deliberately | Unchanged input does not introduce duplicate observations |

## 5. SQL concepts from the lecture

### `WHERE`, `HAVING`, and `QUALIFY`

| Clause | What it filters | Intent in this lesson |
| --- | --- | --- |
| `WHERE` | Input rows before aggregation/window calculations | Exclude missing required keys |
| `HAVING` | Grouped results after aggregation | Keep stations with enough observations, or groups revealing duplicate keys |
| `QUALIFY` | Rows based on window-function results | Keep selected ranked rows within a station group |

A useful logical sequence here is: source/joins → row filtering → grouping/aggregates → group filtering → window calculations → window-result filtering → final ordering/limit. The optimizer may use a different physical plan. See Redshift's [WHERE](https://docs.aws.amazon.com/redshift/latest/dg/r_WHERE_clause.html), [HAVING](https://docs.aws.amazon.com/redshift/latest/dg/r_HAVING_clause.html), and [QUALIFY](https://docs.aws.amazon.com/redshift/latest/dg/r_QUALIFY_clause.html) references.

### What `ROW_NUMBER()` was doing

- `PARTITION BY` defines competing groups, such as observations belonging to one station.
- The window's `ORDER BY` ranks rows within each group; descending timestamps put newer observations first.
- `ROW_NUMBER()` assigns positions. It does not remove rows by itself.
- `QUALIFY` needs a comparison stating which positions survive. That comparison was missing from the captured station statement.
- Tie-breakers need documented rules. Sorting by name/capacity may make a choice repeatable without proving it authoritative.

Redshift documents nondeterministic numbering when ordering is not unique. Decide how conflicting tied rows should be resolved; see [ROW_NUMBER](https://docs.aws.amazon.com/redshift/latest/dg/r_WF_ROW_NUMBER.html).

### `DISTINCT`, `CASE`, and `NULLIF`

- `DISTINCT` removes duplicate combinations of selected values. It suits repeated calendar dates; it does not select the newest station version.
- `CASE` supplies conditional values, such as contributing to a count when an observation is empty.
- Conditional aggregation totals those contributions within groups.
- A percentage needs a numerator, denominator, division, and percentage units.
- `NULLIF` can turn a zero denominator into null so division does not fail. Decide how reports display undefined results.
- Treating unknown status flags as false can hide data-quality problems; choose your denominator deliberately.

### Redshift transformation reference: practice before building the star

The following small `SELECT` examples use literal values so you can explore the functions without creating or changing tables. Expected values are illustrative, checked against documentation, and have not been executed in Redshift during this edit. Apply each idea to your source columns after you understand its input, output type, and effect on grain.

#### Start with your date-dimension attempt

Your approach is correct: derive calendar attributes from the source timestamp. Separate these tasks:

- **Define structure:** `CREATE TABLE` declares columns, types, and constraints.
- **Preview transformations:** `SELECT` computes values but does not store them in a table.
- **Populate an existing table:** `INSERT INTO … (target columns) SELECT …` maps selected values into the listed target columns by position, not by alias name.
- **Create from query results:** `CREATE TABLE … AS SELECT …` (CTAS) creates and populates a new table, deriving column types from the query. Its optional column-name list is not a typed column/constraint definition.

Redshift does not support `CREATE OR REPLACE TABLE`. `CREATE TABLE IF NOT EXISTS` skips creation when the table already exists; it does not replace its definition or refresh its data. Choose table creation and loading as separate decisions. See [CREATE TABLE](https://docs.aws.amazon.com/redshift/latest/dg/r_CREATE_TABLE_NEW.html) and [CTAS](https://docs.aws.amazon.com/redshift/latest/dg/r_CREATE_TABLE_AS.html).

Specific corrections to your attempt:

- Use `EXTRACT` for numeric calendar parts; use `TO_CHAR` for text formatting rather than `format(...)`.
- `DOW` is a date part used by extraction functions, not the intended `TO_CHAR` formatting token.
- A plain `SELECT` after a column definition does not populate that table; choose a loading form.
- Your declared `date_id` needs a corresponding selected value when loading it. A `PRIMARY KEY` declaration does not generate IDs or enforce uniqueness in Redshift.
- Prefer clear names such as `year_number`, `month_number`, and `day_number` to distinguish stored attributes from SQL date-part keywords.
- Include a real `calendar_date` if you want straightforward date comparisons and joins; separate year/month/day attributes do not replace the usefulness of a `DATE` value.
- Many station observations share a day. Decide how your date-loading process yields one row per intended date and avoids reinserting those dates on a rerun.

#### Numeric date parts: `EXTRACT`

```sql
SELECT
    EXTRACT(YEAR FROM TIMESTAMP '2026-10-09 14:35:20') AS year_number,
    EXTRACT(MONTH FROM TIMESTAMP '2026-10-09 14:35:20') AS month_number,
    EXTRACT(DAY FROM TIMESTAMP '2026-10-09 14:35:20') AS day_number,
    EXTRACT(HOUR FROM TIMESTAMP '2026-10-09 14:35:20') AS hour_number;
```

Expected values: `2026`, `10`, `9`, `14`. `YEAR`, `MONTH`, and `DAY` are function date-part arguments; aliases after `AS` are names you choose. For `TIMESTAMP` inputs, Redshift returns an integer; for `TIMESTAMPTZ`, it returns double precision, so cast explicitly if your target contract requires integers. See [EXTRACT](https://docs.aws.amazon.com/redshift/latest/dg/r_EXTRACT_function.html).

#### Text formatting: `TO_CHAR`

```sql
SELECT
    TO_CHAR(TIMESTAMP '2026-10-09 14:35:20', 'YYYY-MM-DD') AS date_label,
    TO_CHAR(TIMESTAMP '2026-10-09 14:35:20', 'MM') AS month_label;
```

Expected values: text `'2026-10-09'` and `'10'`. Formatting changes the representation into text; it does not change the stored source timestamp. See [TO_CHAR](https://docs.aws.amazon.com/redshift/latest/dg/r_TO_CHAR.html).

| Format token | Meaning | Example for October 9, 2026 |
| --- | --- | --- |
| `YYYY` | Four-digit year | `'2026'` |
| `MM` | Two-digit month | `'10'` |
| `DD` | Two-digit day of month | `'09'` |
| `DY` | Abbreviated day name | `'FRI'` |
| `HH24` | Hour on a 24-hour clock | `'14'` |
| `MI` | Minutes; `MM` means month | `'35'` |
| `D` | Sunday-based weekday number as text | `'6'` for Friday |
| `ID` | ISO weekday number as text, Monday = 1 | `'5'` for Friday |

See Redshift's [datetime format reference](https://docs.aws.amazon.com/redshift/latest/dg/r_FORMAT_strings.html). Some long name formats are space-padded; use `TRIM` when you want an unpadded label.

#### Day-of-week numbering: choose and document the convention

```sql
SELECT
    EXTRACT(DOW FROM TIMESTAMP '2026-10-09 14:35:20') AS sunday_zero,
    CAST(TO_CHAR(TIMESTAMP '2026-10-09 14:35:20', 'ID') AS INTEGER) AS monday_one;
```

Expected values: `5` and `5`, because this date is a Friday. They happen to agree on Friday; they differ on Sunday. [Redshift date parts](https://docs.aws.amazon.com/redshift/latest/dg/r_Dateparts_for_datetime_functions.html) define `DOW` as Sunday = 0 through Saturday = 6.

| Convention | Monday | Friday | Sunday |
| --- | --- | --- | --- |
| `EXTRACT(DOW ...)` | 1 | 5 | 0 |
| `TO_CHAR(..., 'D')` | `'2'` | `'6'` | `'1'` |
| `TO_CHAR(..., 'ID')` | `'1'` | `'5'` | `'7'` |
| ISO weekday cast to integer, then minus one | 0 | 4 | 6 |

#### Type conversion and a date-key building block: `CAST`

```sql
SELECT
    CAST(TIMESTAMP '2026-10-09 14:35:20' AS DATE) AS calendar_date,
    CAST(TO_CHAR(TIMESTAMP '2026-10-09 14:35:20', 'YYYYMMDD') AS INTEGER) AS encoded_date;
```

Expected values: date `2026-10-09` and integer `20261009`. `CAST` changes a value's type. The integer is a possible date-key encoding, not a date type or automatically generated identity. You still need a consistent derivation rule in both dimension and fact loading. See [CAST](https://docs.aws.amazon.com/redshift/latest/dg/r_CAST_function.html).

#### Time buckets: `DATE_TRUNC`

```sql
SELECT
    DATE_TRUNC('hour', TIMESTAMP '2026-10-09 14:35:20') AS hour_start,
    DATE_TRUNC('month', TIMESTAMP '2026-10-09 14:35:20') AS month_start;
```

Expected values: timestamps `2026-10-09 14:00:00` and `2026-10-01 00:00:00`. Truncation keeps a timestamp type and moves it to a period boundary. Unlike extracting hour `14`, the hourly bucket retains the actual date. Redshift truncates weeks to Monday. See [DATE_TRUNC](https://docs.aws.amazon.com/redshift/latest/dg/r_DATE_TRUNC.html).

#### Convert time zone before deriving local dates

```sql
SELECT
    CONVERT_TIMEZONE(
        'UTC',
        'America/New_York',
        TIMESTAMP '2026-10-09 02:30:00'
    ) AS local_timestamp;
```

Assuming the input represents UTC, the expected New York timestamp is `2026-10-08 22:30:00`: a different calendar day. Named zones account for daylight saving time. Confirm source type and time-zone meaning before applying this to a column; use the same reporting convention for dimension dates and fact references. See [CONVERT_TIMEZONE](https://docs.aws.amazon.com/redshift/latest/dg/CONVERT_TIMEZONE.html).

#### Clean descriptive text: `TRIM`, `NULLIF`, and `COALESCE`

```sql
SELECT
    TRIM('  Example Station  ') AS cleaned_name,
    NULLIF(TRIM('   '), '') AS blank_as_null,
    COALESCE(NULLIF(TRIM('   '), ''), 'Unknown') AS display_name;
```

Expected values: `'Example Station'`, null, and `'Unknown'`.

- `TRIM` removes surrounding spaces.
- `NULLIF(value, other)` returns null when the two values are equal.
- `COALESCE` chooses the first non-null argument; arguments need compatible types.
- A fallback display label does not repair a missing station key. Do not replace every missing measure with zero: unknown availability differs from observed zero availability.

See [TRIM](https://docs.aws.amazon.com/redshift/latest/dg/r_TRIM.html), [NULLIF](https://docs.aws.amazon.com/redshift/latest/dg/r_NULLIF_function.html), and [COALESCE](https://docs.aws.amazon.com/redshift/latest/dg/r_NVL_function.html).

#### Derive categories: `CASE`

```sql
SELECT CASE
    WHEN CAST(NULL AS INTEGER) IS NULL THEN 'Unknown'
    WHEN CAST(NULL AS INTEGER) = 0 THEN 'Empty'
    ELSE 'Has bikes'
END AS availability_label;
```

Expected value: `'Unknown'`. Change both null inputs to the same test count to explore other branches. `CASE` uses the first matching branch, so order matters. In a column expression, check null explicitly rather than comparing it with `= NULL`. See [CASE](https://docs.aws.amazon.com/redshift/latest/dg/r_CASE_function.html).

#### Compute ratios without integer truncation or division by zero

```sql
SELECT
    ROUND(100.0 * 3 / NULLIF(8, 0), 2) AS example_pct,
    ROUND(100.0 * 3 / NULLIF(0, 0), 2) AS undefined_pct;
```

Expected values: `37.50` and null. The decimal factor keeps fractional arithmetic; `NULLIF` protects the denominator. For availability measures, also decide how to handle invalid negative capacity and null inputs. Do not round away needed precision early in a pipeline.

#### Assemble transformations into a model deliberately

| Need | SQL building block | Decision you still own |
| --- | --- | --- |
| One row per observed date | Date conversion and `DISTINCT` | Reporting time zone, full calendar versus observed dates, rerun behavior |
| One selected station description | `ROW_NUMBER` and `QUALIFY` | History policy, ranking and conflict rules |
| Fact-to-dimension mapping | Join on the intended business/version key | Unique matches and missing-member policy |
| Missing-reference check | Left join and unmatched-key filter | Which references are required and what happens to failures |
| Conditional counts | `SUM` with `CASE` | Eligible observations and unknown-status handling |
| Reusable transformation stages | CTEs | Each stage's input/output grain and validation |

These expressions are building blocks. Combining them into your dimension definitions, inserts, and fact load remains your next design exercise.

## 6. `DELETE`, `TRUNCATE`, and `DROP`

| Operation | Effect on rows | Structure | Main distinction |
| --- | --- | --- | --- |
| `DELETE` | Removes matching rows; all rows without a filter | Retained | Can target a subset and participates in transaction control |
| `TRUNCATE` | Removes all rows | Retained | Efficient full clearing; commits its transaction in Redshift |
| `DROP TABLE` | Removes table and data | Removed | Removes the object itself |

In Redshift, `TRUNCATE` cannot be rolled back and may commit other work in the transaction. Several truncate/reload steps do not form an atomic rebuild. See AWS's [TRUNCATE reference](https://docs.aws.amazon.com/redshift/latest/dg/r_TRUNCATE.html).

- Rebuilding dimensions must preserve or deliberately remap the keys facts reference.
- Deterministic calendar keys can stay stable if derivation/time-zone rules stay consistent. Regenerated surrogate keys are not automatically stable.
- A failed dimension reload after clearing leaves existing facts without context.
- Write rebuild/recovery order before clearing anything. Later, consider incremental updates or staged publication to avoid exposing partial refreshes.

## 7. Validate before trusting reports

| Check | Why it matters | Expected outcome |
| --- | --- | --- |
| Missing required keys | Records cannot be identified/joined reliably | No unexplained missing keys |
| Duplicate dimension keys | One fact can join to multiple descriptions | One dimension match per intended reference |
| Duplicate fact identity | Reruns or joins may double-count observations | One row per declared grain |
| Station/date orphans | Facts lack descriptive context | No unexplained unmatched references |
| Source-to-fact counts | Filtering/joins may lose or multiply rows | Counts reconcile with documented exclusions |
| Measure agreement | Transformations may change values incorrectly | Selected facts agree with source observations |
| Replay | Reprocessing can duplicate facts/change key mappings | Stable results for unchanged input |

The captured orphan check covered only stations. Check dates too. A left join retaining unmatched facts helps find missing references; an inner join can hide them.

Zero duplicate groups means no violating groups were returned. It does not mean zero source rows or prove completeness. Record total rows and time coverage separately.

## 8. Analytical questions: plan before querying

### Which stations have the most bikes available on average?

- Join station context, group by station identity/description, and average bike availability.
- Include observation counts and reporting time range.
- Distinguish absolute availability from utilization: bigger stations may have more bikes but a smaller occupied fraction of capacity.
- The teacher's minimum of two observations is a classroom filter; it does not establish representative coverage.

### Which stations are empty most often in our observations?

- Compare empty observations with eligible observations per station; report both counts alongside the percentage.
- Decide whether to include all observations or only operational ones.
- This measures a percentage of observations. Interpreting it as a percentage of time requires suitable sampling and coverage.

### How does availability change by hour?

- Derive hours in the intended time zone, then group and average observations.
- Grouping by hour alone pools that hour across included days; it produces a daily pattern rather than a chronological hourly series.
- Uneven sampling gives more weight to stations/periods with more observations.
- One snapshot cannot establish an hourly trend. Check that the warehouse contains sufficient history.

### Which stations may have operational problems?

- Compare non-operational observations with eligible observations per station.
- Choose a ranking rule and distinguish null/unknown from explicit false.
- The saved Silver definition combines installed, renting, and returning flags. A false result signals those source conditions; it does not explain the cause.

### How does availability compare across days?

- Join date context and group by calendar date.
- Count distinct observed stations separately from total observations.
- Compare measures with sampling coverage in view. A date without observations indicates missing coverage, not automatically zero availability.

### Corrections to make when revisiting the captured SQL

These pointers identify unfinished lecture fragments without supplying replacement statements:

- Station selection: missing comparison after the `ROW_NUMBER()` expression.
- Date encoding: `YYYMMDD` should use the intended four-digit-year format.
- Fact deduplication: unfinished ordering rule. Decide whether deduplication is needed after source validation and how conflicts should be handled.
- Percentage expressions: missing division before `NULLIF`.
- Empty-station query: `s_station_name` does not match the captured alias/column reference.
- Operational query: missing comma after observation count; unfinished final ordering.
- Daily comparison: missing source/join, grouping, and ordering clauses.
- Table-creation and truncate fragments: incomplete; not runnable setup instructions.

## 9. AWS networking refresher

| Concept | Beginner explanation | Pipeline connection |
| --- | --- | --- |
| VPC | A logically isolated AWS network | Contains network paths used by Glue and Redshift |
| Subnet | An IP-address range within one Availability Zone | Places service network interfaces in the VPC |
| Route table | Rules selecting where traffic goes | Directs traffic toward local resources, gateways, or endpoints |
| Internet gateway | A VPC attachment supporting internet connectivity | A public route alone does not give every resource internet access |
| Public NAT gateway | Outbound internet connectivity for private IPv4 resources through a public subnet | An option for private workloads needing internet destinations |
| VPC endpoint | Private access to supported services/resources | An S3 gateway endpoint can supply Glue's S3 route |
| Security group | A stateful set of allow rules | Controls permitted database connections and other traffic |

AWS documents the [VPC model](https://docs.aws.amazon.com/vpc/latest/userguide/how-it-works.html), [NAT connectivity types](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html), [endpoint types](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html), and [security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html).

Diagnose the load through three separate checks:

- **Network:** can Glue reach Redshift and required S3 locations? An S3 endpoint supplies access to S3, not general internet access.
- **AWS permissions:** can service roles perform required AWS operations? A route does not grant permission.
- **Database permissions:** can the database identity access/modify intended tables? AWS access does not automatically grant SQL privileges.

The star redesign begins after the warehouse load. Changing Gold's table layout does not itself require a networking redesign.

![AWS networking screenshot captured during class](<Screenshot 2026-10-09 at 11.40.42 AM.png>)

## 10. Reusable SQL and data-modeling patterns

SQL is declarative: describe the result, and the engine plans how to obtain it. Useful recurring patterns here concern identity, relationships, transformation, and publication.

| Pattern | Purpose in this lesson |
| --- | --- |
| Star schema | Organize Gold measurements and descriptions |
| Window-based selection | Rank observations and choose station descriptions |
| Conditional aggregation | Count empty/non-operational observations |
| Anti-join | Find missing dimension members or orphaned facts |
| CTE decomposition | Name steps within a statement, such as filtering and ranking |
| Reporting view | Expose reusable analysis over the star |
| Type 1 / Type 2 dimensions | Choose current descriptions or attribute history |
| Incremental processing / `MERGE` | Apply new or changed data |
| Idempotent loading | Keep retries from introducing unintended changes |
| Audit columns | Record when and how data was processed |
| Bridge table | Represent many-to-many relationships when the model requires them |

The original OOP comparisons are loose analogies: a view can act as a facade, `CASE` selects conditional values, and CTEs express named transformation steps. They are not exact implementations of Factory, Strategy, Observer, or Template Method. Check engine support before transferring features such as triggers or table-valued functions to Redshift.

## 11. Your next checkpoint: write the model contract

Before table definitions, complete these prompts in your own words:

- **Business question:** The first question my model should answer is ______.
- **Fact grain:** One row in my fact table represents ______.
- **Identity:** Two rows represent the same observation when ______.
- **Measures:** Values recorded at that grain are ______, with units/formulas ______.
- **Station context:** My dimension describes ______; when attributes change, I will ______.
- **Calendar context:** I use ______ time zone and include ______ dates.
- **Relationships:** Each fact finds its station/date context through ______.
- **Missing references:** If a required dimension member is absent, I will ______.
- **Replay/recovery:** The same input should ______; if refresh fails, I will ______.

The classroom table names give you vocabulary. Your contract determines whether the model is correct.

## Knowledge check

- If a station appears in several snapshots, which tables gain rows under your design, and why?
- What happens to historical reports when a station changes name and the dimension keeps only its latest description?
- How can duplicate dimension keys inflate observation counts or distort averages?
- Why can a Redshift fact load succeed with an unmatched station reference?
- What does empty-observation percentage measure with irregular sampling?
- How would you distinguish a missing capture, failed load, filtered rows, and an incorrect reporting join?

## Weekend assignment and completion checklist

Original assignment:

> Homework for the weekend: Develop the pipeline that you have built on your side to the full extent that it was in class - should have the ingestion job able to run in Lambda, which will get the data into S3, EMR and Glue jobs to get the data from bronze to silver, then silver to gold (if you only do this in one or the other that's fine) - then once it's in gold, make sure that it's in a Star Schema, and then do some basic analytical queries on it in order to answer natural language questions about what the data can tell us

For the current implementation, the existing loader gets Silver detail into Redshift; your Redshift transformations create the Gold star.

- [ ] Confirm ingestion, Bronze, Silver, and warehouse loading using saved evidence.
- [ ] Write and explain the model contract before SQL.
- [ ] Implement dimensions and facts in your own SQL.
- [ ] Validate keys, references, counts, measures, and replay.
- [ ] Answer analytical questions and explain coverage/sampling limitations.
- [ ] Record actual results and remaining gaps; saved scripts alone are not execution evidence.

## Instructor references and evidence limits

- [Main classroom star-schema conversation](https://chatgpt.com/share/6ac953f4-5df0-83e9-aba7-ecb21e655b4c).
- [Why dimensions come before facts](https://chatgpt.com/share/6ac95459-c224-83e9-80d6-ff6275018291).
- [Networking: VPCs and subnets](https://chatgpt.com/share/6ac95491-4858-83e8-b501-9f81e57688e4).

The shared conversations could not be retrieved during this revision. Explanations use the captured notes, saved artifacts, and linked primary documentation reviewed on 2026-10-11. No shared-conversation contents, newly created star tables, SQL results, or cloud runtime behavior are claimed as verified.
