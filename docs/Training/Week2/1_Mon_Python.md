# Monday Training: Python for Data Engineering

> Status: Draft  
> Level: Beginner  
> Applies to: Python / Batch ETL / Record transformations  
> Data scale: Local fixture; production and distributed-system implications identified  
> Example status: Complete standard-library walkthrough  
> Evidence status: Standard-library worked example executed locally with Python 3.14.5 on 2026-09-14; pandas example review-only  
> Last reviewed: 2026-09

## Overview

Python is widely used in data engineering for ingestion, validation, transformation, orchestration, automation, and interacting with data platforms. Its value is not that Python alone makes a workload "big data." A Python process is still bounded by one machine unless a separate execution engine or distributed architecture divides the work.

This lesson develops three ideas that remain important when moving from a local script to Spark or another distributed system:

- records should have an explicit meaning and schema;
- transformations should make input, output, and failure behavior clear; and
- memory use depends on when data is materialized, not only on how concise the code looks.

The running example reads employee records from CSV, validates and converts their fields, filters eligible records, applies a transformation, and calculates aggregates. The data is intentionally tiny so the behavior can be inspected. The final sections explain what changes when the same logical work runs across partitions and machines.

## Learning objectives

After completing this lesson, you should be able to:

- describe Python's execution model without reducing it to "interpreted line by line";
- distinguish type hints, static type checking, and runtime data validation;
- explain the difference between an iterable, an iterator, and a materialized collection;
- use `map()`, `filter()`, generator expressions, and `functools.reduce()` correctly;
- recognize when a named function or comprehension is clearer than a lambda;
- build a small extract-transform-aggregate pipeline that records rejected inputs; and
- implement the same logical pipeline with pandas column operations;
- distinguish row-oriented, columnar, file, table, and partition concepts; and
- explain why local higher-order functions are conceptually related to, but operationally different from, distributed transformations.

## Python's role in a data system

Python can participate in both the control plane and the data plane of a pipeline.

| Role | Examples | Main concern |
| --- | --- | --- |
| Control plane | Scheduling jobs, submitting queries, moving metadata, calling APIs | Reliability, retries, configuration, and observability |
| Local data plane | Parsing a file, validating records, transforming a bounded batch | CPU, memory, I/O, and malformed inputs |
| Distributed client | Defining a Spark DataFrame query or submitting work to a remote warehouse | Understanding which work stays in Python and which work runs remotely |
| Distributed worker code | Python UDFs or partition functions executed by workers | Serialization, process boundaries, retries, and per-record overhead |

PySpark is not simply Python translated into equivalent Scala source code. A PySpark program uses Python APIs to define work for Spark. Built-in DataFrame expressions become a logical plan that Spark can optimize and execute across the cluster. Python user-defined functions execute Python code in worker processes and require data to cross a language/process boundary; their cost model differs from built-in expressions.

## Execution model: more than compiled versus interpreted

"Compiled" and "interpreted" describe implementation strategies, not a clean division between languages. A Python implementation may compile source into an intermediate representation and then execute it with a virtual machine. CPython, the most common implementation, compiles source to Python bytecode before its evaluation loop executes that bytecode.

The practical consequences for data engineering are:

- syntax and compile-time rule violations are found before the affected module begins normal execution;
- many type and data-shape errors are still discovered only when a path executes;
- import time, interpreter startup, serialization, and object allocation can matter in jobs containing many short tasks; and
- performance must be measured at the actual bottleneck—CPU, memory, storage, network, database, or distributed shuffle—rather than blamed on "interpretation" by default.

Python source is portable at the language level, but cached bytecode and implementation details are not the deployment artifact contract. Reproducible jobs should declare a supported Python version and their dependencies.

## Type hints and runtime validation

Python includes annotation syntax and the `typing` module. The Python runtime does not enforce most annotations by itself. A static checker such as mypy or pyright can analyze annotations before deployment, while a runtime validation library such as Pydantic can validate untrusted values as the program runs.

These are separate boundaries:

| Mechanism | Question it answers | Example |
| --- | --- | --- |
| Type hint | What type does the developer intend here? | `salary: Decimal` |
| Static checker | Is the source code internally consistent with its annotations? | Reject adding a `str` to a `Decimal` before execution |
| Runtime validation | Does this delivered record actually satisfy the contract? | Reject `salary=not_available` while ingesting CSV |

`TypedDict` describes the expected keys and value types of a dictionary to static tooling; it does not validate a dictionary at runtime. External data must still be parsed and checked at an ingestion boundary.

```python
from decimal import Decimal
from typing import TypedDict


class EmployeeInput(TypedDict):
    employee_id: str
    salary: str


def parse_salary(row: EmployeeInput) -> Decimal:
    return Decimal(row["salary"])
```

The annotation helps tools and readers. `Decimal(...)` performs the runtime conversion and can still fail for malformed input.

## Iterables, iterators, and materialization

An **iterable** is an object that can produce an iterator, such as a list or an open CSV reader. An **iterator** produces one item at a time and is exhausted after one pass. A **materialized collection**, such as a list, holds all of its items in memory at once.

In Python 3, `map()` and `filter()` return lazy iterators. They accept iterables; they do not require lists and they do not return lists.

```python
numbers = [1, 2, 3, 4, 5]

squared = map(lambda value: value**2, numbers)
evens = filter(lambda value: value % 2 == 0, numbers)

print(squared)       # A map iterator, not its values
print(list(squared)) # [1, 4, 9, 16, 25]
print(list(squared)) # []; the iterator was already consumed
print(list(evens))   # [2, 4]
```

Laziness can keep a pipeline's in-flight working set small, but only if downstream code also processes incrementally. Calling `list(...)`, sorting globally, grouping every distinct key, or retaining every result materializes state and may become the real memory boundary.

For readable Python, a comprehension or generator expression is often preferable to `map()` or `filter()`:

```python
squared_list = [value**2 for value in numbers]
even_iterator = (value for value in numbers if value % 2 == 0)
```

The list comprehension materializes its output. The generator expression remains lazy.

## Functions, lambdas, and higher-order operations

A higher-order function accepts a function, returns a function, or both. `map()`, `filter()`, and `reduce()` are common examples.

### `map()`: one output per input

`map(function, iterable)` applies the function to each item and returns an iterator of results. It accepts named functions and lambdas equally.

```python
def double(value: int) -> int:
    return value * 2


numbers = [1, 2, 3]

print(list(map(double, numbers)))                  # [2, 4, 6]
print(list(map(lambda value: value * 2, numbers))) # [2, 4, 6]
```

A lambda is limited to one expression. Assigning a lambda to a variable is valid, but a named `def` is usually clearer when the behavior deserves a name, annotations, a docstring, multiple statements, or focused tests.

### `filter()`: zero or one output per input

`filter(predicate, iterable)` keeps each item for which the predicate is truthy. A predicate need not literally return `True` or `False`, although an explicit boolean result is usually clearest.

```python
def is_even(value: int) -> bool:
    return value % 2 == 0


print(list(filter(is_even, [1, 2, 3, 4, 5]))) # [2, 4]
```

### `flatMap`: zero or more outputs per input

Python has no `flatMap()` built-in, but the concept appears frequently in distributed data APIs. It transforms each input into an iterable of outputs and then flattens those iterables into one record stream. In standard-library Python, `itertools.chain.from_iterable()` can express the flattening step.

```python
from itertools import chain

sentences = ["data systems scale", "records need contracts"]
words = chain.from_iterable(sentence.split() for sentence in sentences)

print(list(words))
# ['data', 'systems', 'scale', 'records', 'need', 'contracts']
```

`flatMap` can change record grain and cardinality: one input may produce no outputs, one output, or many outputs. Define the output grain before using it in a pipeline.

### `reduce()`: many inputs to one result

`functools.reduce(function, iterable, initial)` repeatedly combines the accumulator with the next value and returns one final result. `functools` is part of the Python standard library, so it needs an import but no package installation.

```python
from functools import reduce

total = reduce(lambda accumulator, value: accumulator + value, [1, 2, 3, 4, 5], 0)
print(total) # 15
```

For a simple total, `sum()` communicates intent better:

```python
print(sum([1, 2, 3, 4, 5])) # 15
```

Use `reduce()` when the combine operation or accumulator structure is the lesson. Avoid mutating an accumulator inside `reduce()` unless the ownership and side effects are deliberately understood; an explicit loop is often easier to review.

## Worked example: a CSV transformation pipeline

The grain of the input is one employee record from [`data.csv`](data.csv). The pipeline accepts valid records, rejects malformed records with a safe reason, selects active employees earning at least $70,000, applies a 5% raise, and aggregates the results.

The example uses `Decimal` rather than binary floating-point for money. That does not define a complete financial rounding policy, but it avoids introducing avoidable binary representation error into the lesson.

```python
from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from functools import reduce


@dataclass(frozen=True)
class Employee:
    employee_id: int
    name: str
    department: str
    salary: Decimal
    years_experience: int
    active: bool
    old_salary: Decimal | None = None


@dataclass(frozen=True)
class ParseResult:
    employee: Employee | None
    error: str | None


@dataclass(frozen=True)
class PayrollSummary:
    total: Decimal
    count: int


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError("unsupported boolean representation")


def parse_employee(item: tuple[int, dict[str, str]]) -> ParseResult:
    row_number, row = item
    try:
        employee = Employee(
            employee_id=int(row["employee_id"]),
            name=row["name"].strip(),
            department=row["department"].strip(),
            salary=Decimal(row["salary"]),
            years_experience=int(row["years_experience"]),
            active=parse_boolean(row["active"]),
        )
        if not employee.name or not employee.department:
            raise ValueError("required text field is empty")
        return ParseResult(employee=employee, error=None)
    except (KeyError, ValueError, InvalidOperation) as error:
        safe_reason = type(error).__name__
        return ParseResult(employee=None, error=f"row {row_number}: {safe_reason}")


def is_raise_eligible(employee: Employee) -> bool:
    return employee.active and employee.salary >= Decimal("70000")


def give_raise(employee: Employee) -> Employee:
    new_salary = (employee.salary * Decimal("1.05")).quantize(Decimal("0.01"))
    return replace(employee, old_salary=employee.salary, salary=new_salary)


def to_summary(employee: Employee) -> PayrollSummary:
    return PayrollSummary(total=employee.salary, count=1)


def combine_summaries(left: PayrollSummary, right: PayrollSummary) -> PayrollSummary:
    return PayrollSummary(total=left.total + right.total, count=left.count + right.count)


employees: list[Employee] = []
rejected_rows: list[str] = []

# Keep the file open while its lazy reader and map iterator are consumed.
with open("data.csv", mode="r", encoding="utf-8", newline="") as csv_file:
    reader = csv.DictReader(csv_file)
    parsed_results = map(parse_employee, enumerate(reader, start=2))

    # Branch accepted and rejected outcomes in one pass because parsed_results is single-use.
    for result in parsed_results:
        if result.employee is not None:
            employees.append(result.employee)
        else:
            rejected_rows.append(result.error or "unknown parse error")

eligible_employees = filter(is_raise_eligible, employees)
employees_with_raise = list(map(give_raise, eligible_employees))

summary = reduce(
    combine_summaries,
    map(to_summary, employees_with_raise),
    PayrollSummary(total=Decimal("0"), count=0),
)

payroll_by_department: dict[str, Decimal] = {}
for employee in employees_with_raise:
    payroll_by_department[employee.department] = (
        payroll_by_department.get(employee.department, Decimal("0")) + employee.salary
    )

average_salary = summary.total / summary.count if summary.count else None

print(f"valid={len(employees)} rejected={len(rejected_rows)} eligible={summary.count}")
print("rejections:", rejected_rows)
print(f"total payroll after raises: ${summary.total:,.2f}")
print(f"average salary after raises: ${average_salary:,.2f}" if average_salary else "no eligible employees")

for department, payroll in sorted(payroll_by_department.items()):
    print(f"{department}: ${payroll:,.2f}")
```

Expected output:

```text
valid=100 rejected=0 eligible=80
rejections: []
total payroll after raises: $7,386,750.00
average salary after raises: $92,334.38
Engineering: $3,019,800.00
Finance: $1,730,400.00
HR: $532,350.00
Marketing: $869,400.00
Sales: $1,234,800.00
```

### Pipeline review

The example makes several boundaries visible:

- **Extract:** `csv.DictReader` yields dictionaries lazily, but every CSV field initially remains text.
- **Validate and convert:** `parse_employee` converts types and produces either an accepted record or a rejection. It does not silently discard bad data.
- **Transform:** `filter` selects records and `map` creates new immutable `Employee` values with the raise applied.
- **Aggregate:** `reduce` creates a mergeable `(total, count)` summary, while the department dictionary holds one entry per distinct department.
- **Observe:** accepted, rejected, and eligible counts make silent record loss detectable.

The class dataset is clean, so this run has no rejections, but the parser still defines its malformed-record path. The safe rejection reason intentionally omits the raw row. Production error handling should use stable reason codes and avoid placing sensitive source values in logs. A real pipeline must also define where rejected records are stored, who can inspect them, and how corrected records are replayed.

## What changes at big-data scale

Python's local operations and distributed operations may share names, but their execution semantics differ.

| Operation | Local Python | Distributed engine |
| --- | --- | --- |
| `map` | Calls a function sequentially as an iterator advances | Runs tasks over partitions, possibly on many workers |
| `filter` | Tests local values one at a time | Tests records in each partition; usually avoids moving records between workers by itself |
| `reduce` | Combines values in a deterministic left-to-right call sequence | Usually combines partial results in a tree whose grouping and arrival order can vary |
| Aggregate by key | Keeps a local dictionary or similar state | Usually repartitions data by key, causing a network, serialization, memory, and disk-intensive shuffle |
| Materialize | `list(...)` puts all results in one process | `collect()`-style operations can move all results to a driver and exhaust its memory |

For a distributed reduction, the combine function should normally be associative and commutative so partial results can be merged safely in different groupings and orders. Integer addition satisfies this mathematical requirement. Floating-point addition is not exactly associative because rounding changes with grouping, so reproducibility and numeric error deserve explicit treatment.

The `PayrollSummary` accumulator is more useful than reducing directly to an average. Two partitions can independently produce `(total, count)` and merge those summaries. Averaging partition averages would be wrong when partitions contain different record counts.

Distributed workers may retry a failed task. A transformation that sends an email, charges an account, or inserts a row as an unguarded side effect may therefore execute more than once. Prefer pure transformations, then publish through an idempotent or transactional boundary designed for retries.

## Bounded processing is not distributed processing

A lazy iterator can process a file larger than memory when each record is consumed and released. That is valuable, but the work still uses one Python process unless concurrency or a distributed engine is introduced.

Memory can still grow with:

- `list(...)` or another full materialization;
- a dictionary whose number of keys grows with the dataset;
- an exact global sort;
- a join that retains a large lookup side; or
- buffering caused by a slow downstream sink.

Before choosing a distributed engine, first determine the constraint. A database query, columnar file scan, incremental iterator, larger machine, or partitioned batch may be simpler and cheaper. Distribution adds scheduling, serialization, shuffle, skew, retries, and operational failure modes.

## Long-running streams

An unbounded source may involve a long-running loop, but `while True` is not a streaming architecture by itself.

```python
while not shutdown_requested():
    batch = source.read_batch(max_records=1_000)
    publish(process(batch))
    checkpoint(batch)
```

A production stream also needs defined behavior for backpressure, empty reads, cancellation, retries, duplicate delivery, ordering, checkpoint recovery, poison records, schema evolution, and safe publication. The example is only a control-flow sketch; the methods are placeholders rather than runnable APIs.

## Exercises

1. Add an input row with an empty department. Confirm that the accepted and rejected counts still reconcile to the total input count.
2. Replace the `map()` and `filter()` calls with a generator expression. Identify which values remain lazy and where materialization occurs.
3. Extend `PayrollSummary` with minimum and maximum salary. Keep `combine_summaries` associative.
4. Add `rejection_reason` codes instead of exception class names, then count rejections by reason.
5. Explain why computing an average salary per partition and then averaging those averages can be incorrect.
6. Estimate the memory risk if `department` is replaced by a nearly unique key such as `employee_id` in `payroll_by_department`.
7. Describe how task retries could corrupt an external system if `give_raise` directly updated a database row.

## Operational Python, pandas, and data formats

This section extends the earlier pipeline with local concurrency, file handling, operational error reporting, pandas, and storage formats. These tools do not change the central scale boundary: local concurrency can use one machine more effectively, while Spark and similar engines coordinate partitions across workers.

### Threading and multiprocessing

Python code is sequential within one thread, but a program can coordinate multiple threads or processes. Choosing between them depends on what limits the workload.

| Model | Memory and execution | Typical fit | Important cost |
| --- | --- | --- | --- |
| Threads | Share one process and its memory | Overlapping I/O waits such as API calls or independent file reads | Shared-state synchronization and the default CPython GIL for Python bytecode |
| Processes | Have separate interpreters and memory spaces | CPU-bound Python work that can be divided into independent units | Process startup, serialization, inter-process communication, and copied state |
| Spark tasks | Run partition work under a distributed scheduler | Data already partitioned across a cluster or too large for one machine | Scheduling, serialization, shuffle, skew, retries, and cluster operations |

In the default CPython build, the global interpreter lock (GIL) generally prevents multiple threads from executing Python bytecode simultaneously. Threads can still improve throughput for I/O-bound work because another thread can run while one waits. Processes can use multiple CPU cores for Python code, but every process has its own memory and data must be serialized or otherwise shared explicitly. Free-threaded CPython builds exist, so the GIL is an implementation and deployment detail rather than a universal Python-language rule.

For many Spark pipelines, Spark should own partition-level parallelism. Adding threads or child processes inside a Spark task can oversubscribe worker CPUs, complicate memory accounting, and create failure behavior the scheduler cannot manage well.

```python
import multiprocessing
import os
import threading
import time


def thread_worker(worker_id: int) -> None:
    print(
        f"thread={worker_id} event=start "
        f"pid={os.getpid()} thread_id={threading.get_ident()}"
    )
    time.sleep(2)
    print(f"thread={worker_id} event=finish")


def threading_demo() -> None:
    workers = [
        threading.Thread(target=thread_worker, args=(worker_id,))
        for worker_id in range(3)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()


def process_worker(worker_id: int) -> None:
    print(f"process={worker_id} event=start pid={os.getpid()}")
    time.sleep(2)
    print(f"process={worker_id} event=finish")


def multiprocessing_demo() -> None:
    workers = [
        multiprocessing.Process(target=process_worker, args=(worker_id,))
        for worker_id in range(3)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    print(f"main_pid={os.getpid()}")

    started_at = time.perf_counter()
    threading_demo()
    print(f"threading_seconds={time.perf_counter() - started_at:.2f}")

    started_at = time.perf_counter()
    multiprocessing_demo()
    print(f"multiprocessing_seconds={time.perf_counter() - started_at:.2f}")
```

Run this example as a `.py` file. The `if __name__ == "__main__"` guard prevents child processes from recursively starting more children on platforms that start a fresh interpreter. Output order is nondeterministic. Because each worker only sleeps, the example demonstrates concurrent waiting rather than CPU performance; it is not a benchmark proving one model is faster.

### Working with CSV files

The second argument to `open()` is the file mode, and the variable after `as` is the file object.

| Mode | Meaning | Data risk |
| --- | --- | --- |
| `"r"` | Read an existing file | Fails if the file does not exist |
| `"w"` | Write from the beginning | Truncates an existing file immediately |
| `"a"` | Append at the end | Preserves existing bytes, but does not make concurrent writes or a multi-step publication atomic |

Open CSV files with `newline=""` so the `csv` module controls newline handling, and specify an encoding rather than relying on the machine default. `csv.reader` yields positional lists; `csv.DictReader` uses the header to yield mappings. Choose one reader for a pass through the file because an open file iterator advances and is not automatically rewound.

```python
import csv
from decimal import Decimal, InvalidOperation


active_employees: list[dict[str, object]] = []
rejected_rows: list[str] = []

with open("data.csv", mode="r", encoding="utf-8", newline="") as csv_file:
    reader = csv.DictReader(csv_file)

    for row_number, row in enumerate(reader, start=2):
        try:
            employee_id = int(row["employee_id"])
            salary = Decimal(row["salary"])
            active = parse_boolean(row["active"])
        except (KeyError, ValueError, InvalidOperation) as error:
            rejected_rows.append(f"row {row_number}: {type(error).__name__}")
            continue

        if active:
            active_employees.append(
                {
                    "employee_id": employee_id,
                    "name": row["name"].strip(),
                    "department": row["department"].strip(),
                    "salary": salary,
                    "active": active,
                }
            )
```

This example reuses `parse_boolean()` from the worked pipeline. It deliberately materializes active employees and rejection messages for teaching. At larger scale, send each accepted or rejected outcome to a bounded downstream batch or sink instead of retaining every record in a list.

### Exception handling

An exception interrupts the current control path until a matching handler catches it. Handling an exception does not necessarily mean continuing: code may transform it into a rejected-record result, retry a transient operation, add context and re-raise it, or fail the job.

```python
def calculate_ratio(numerator: str, denominator: str) -> float | None:
    try:
        result = float(numerator) / float(denominator)
    except ValueError:
        print("rejected reason=not_numeric")
        return None
    except ZeroDivisionError:
        print("rejected reason=zero_denominator")
        return None
    else:
        return result
    finally:
        print("calculation_attempt_finished")
```

Catch the narrowest exceptions whose meaning is understood. `except Exception` is useful at some job or request boundaries, but catching it and silently continuing can publish incomplete data as if the run succeeded. `finally` is intended for cleanup that must occur whether the operation succeeds or raises; it cannot protect against every abrupt process or machine failure.

In a worker thread or process, an unhandled exception terminates that worker's control path. The parent or scheduler still needs an explicit mechanism to observe the failure and decide whether the overall job should retry or fail.

### Logging

Logging records operational events; it is not a substitute for handling an error. Useful pipeline logs identify the run, operation, dataset or partition, outcome, and safe reason without copying sensitive records into messages.

```python
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger(__name__)

logger.info("pipeline_started run_id=%s input=%s", "run-42", "data.csv")

try:
    result = 10 / 0
except ZeroDivisionError:
    logger.exception("calculation_failed run_id=%s operation=%s", "run-42", "ratio")
```

`logger.exception()` records the stack trace when called inside an exception handler. That is useful for unexpected failures. High-volume expected rejections should usually be counted by stable reason code, with only a bounded sample logged, or one bad value can flood the logging system. A production application also needs externally managed handlers, retention, rotation, and access controls rather than relying only on `basicConfig()`.

### Pandas DataFrames

pandas provides `Series` for one-dimensional labeled data and `DataFrame` for two-dimensional tabular data with labeled rows and columns. A DataFrame can resemble a spreadsheet or relational table, but it is an object in a Python process rather than a durable database table.

Every DataFrame has an `index` that labels rows and `columns` that label its Series. Selecting one column normally returns a `Series`; selecting multiple columns returns another `DataFrame`.

#### Practical pandas API guide

Choose an operation by the shape of the result you need. Ask whether the result should retain the original rows, select fewer rows or columns, collapse rows into summaries, or combine separate tables.

The object before the dot identifies who owns an operation:

- `pd.function(...)` calls a function from the pandas library. These functions commonly create, read, combine, categorize, or convert pandas objects.
- `df.method(...)` calls a method on one particular DataFrame. These methods inspect, transform, group, join, or publish that table.
- `series.method(...)` calls a method on one-dimensional Series, such as `df["salary"]`. These methods clean, transform, or summarize that column.

Writing is owned by the object being written, so use `df.to_csv(...)` and `df.to_sql(...)`, not `pd.to_csv(...)` or `pd.to_sql(...)`.

##### pandas library functions: `pd.function(...)`

| Goal | pandas function | Result shape and when to use it | Homework connection |
| --- | --- | --- | --- |
| Construct a DataFrame | `pd.DataFrame(data)` | Creates a DataFrame from records, mappings, Series, or other supported data | Small examples and setup |
| Read a CSV | `pd.read_csv(path, usecols=..., dtype=...)` | Creates a DataFrame; select only required columns and declare expected types | All questions |
| Read a SQL query | `pd.read_sql(query, connection)` | Executes a query through a database connection and creates a DataFrame from the result | Database ingestion |
| Read JSON or JSON Lines | `pd.read_json(path, lines=...)` | Creates a DataFrame; `lines=True` reads one JSON object per line | File ingestion |
| Read Parquet | `pd.read_parquet(path, columns=...)` | Creates a DataFrame from a columnar file and can project selected columns | File ingestion |
| Convert values to numbers | `pd.to_numeric(series, errors=...)` | Returns a numeric Series or array-like result; `errors="coerce"` changes invalid values to missing values | Setup and ingestion |
| Convert values to dates or timestamps | `pd.to_datetime(series, errors=...)` | Returns datetime-like values; choose whether invalid text should raise or become missing | Setup and ingestion |
| Build ordered ranges | `pd.cut(series, bins=..., labels=...)` | Converts numeric values into categorical intervals using explicit boundaries | 3, 9 |
| Stack compatible objects | `pd.concat([first, second], ignore_index=True)` | Combines DataFrames or Series along rows by default; it is not a key-based join | General ingestion |

##### DataFrame methods: `df.method(...)`

| Goal | DataFrame method | Result shape and when to use it | Homework connection |
| --- | --- | --- | --- |
| Preview records | `df.head(n)`, `df.tail(n)` | Returns the first or last `n` rows for inspection, not validation | All questions |
| Inspect structure | `df.info()` | Prints column types, non-null counts, and memory information; use the attributes in the later syntax table for programmatic inspection | Setup and debugging |
| Summarize distributions | `df.describe()` | Returns common descriptive statistics for selected columns | 1, 7, 10 |
| Sort rows | `df.sort_values(columns, ascending=...)` | Reorders rows without changing their values | 1, 2, 5, 10 |
| Create columns in a chain | `df.assign(new=lambda current: expression)` | Returns a new DataFrame with derived columns | 2, 8 |
| Remove rows with missing values | `df.dropna(subset=[...])` | Returns a DataFrame without rows that are missing required values in the selected columns | 7, 9, 10 |
| Remove duplicate rows | `df.drop_duplicates(subset=[...])` | Returns a DataFrame with duplicate identities removed according to the chosen columns | Pipeline validation |
| Split rows into groups | `df.groupby(keys)` | Creates a GroupBy object; a following operation determines the output shape | 1–7, 9, 10 |
| Join related tables | `df.merge(right, on=..., how=..., validate=...)` | Returns a DataFrame with columns or rows matched by keys; output cardinality depends on key uniqueness | 6 |
| Reshape grouped results | `df.pivot_table(...)`, `df.unstack()`, `df.reset_index()` | Moves values between rows, columns, and index levels for analysis or presentation | 3, 9 |
| Apply a custom element function | `df.map(function)` | Returns a same-shaped DataFrame after applying Python logic to each element; prefer vectorized expressions when available | Occasional custom rules |
| Make an independent DataFrame | `df.copy()` | Copies the current DataFrame; commonly used after filtering when the result will be modified independently | Filtering and cleaning |
| Write a CSV | `df.to_csv(path, index=False)` | Publishes the current DataFrame as CSV; decide whether the index is data | 10 |
| Write to a SQL table | `df.to_sql(name, connection, schema=..., index=False)` | Writes the DataFrame through a database connection; table design and load policy must already be understood | Database loading |

##### Series methods: `series.method(...)`

| Goal | Series method | Result shape and when to use it | Homework connection |
| --- | --- | --- | --- |
| Convert to a known dtype | `series.astype(dtype)` | Returns a converted Series; invalid values normally raise instead of becoming missing | Setup and ingestion |
| Detect missing or present values | `series.isna()`, `series.notna()` | Returns a same-length Boolean Series suitable for filtering or validation | 7, 9, 10 |
| Replace or remove missing values | `series.fillna(value)`, `series.dropna()` | Returns a Series with missing values replaced or removed | 7, 9, 10 |
| Count values or distinct values | `series.value_counts()`, `series.nunique()` | Returns frequency counts or one scalar distinct count | 3, 4 |
| Detect or remove duplicate values | `series.duplicated()`, `series.drop_duplicates()` | Returns a Boolean Series or a Series containing unique occurrences | Pipeline validation |
| Apply string operations | `series.str.strip()`, `series.str.lower()`, `series.str.upper()`, `series.str.split()`, `series.str.contains()` | Returns row-aligned string results through the `.str` accessor | Cleaning and parsing |
| Choose values conditionally | `series.where(...)`, `series.mask(...)` | Returns a same-length Series with values kept or replaced according to a condition | 8 |
| Calculate one overall statistic | `series.sum()`, `series.mean()`, `series.median()`, `series.min()`, `series.max()`, `series.std()`, `series.count()` | Reduces a Series to one scalar summary | 1, 7, 8, 10 |
| Find the row label of an extreme | `series.idxmax()`, `series.idxmin()` | Returns the index label holding the maximum or minimum value | 10 |
| Rank values | `series.rank(...)` | Returns one rank for each original value | 5 |
| Apply a custom element function | `series.map(function)` | Returns a same-length Series after applying Python logic to each value; prefer vectorized expressions when available | Occasional custom rules |

##### Related DataFrame attributes and selection patterns

Not every useful pandas operation is a function or method. Attributes do not use parentheses, bracket selection chooses columns, and `.loc[]` or `.iloc[]` are indexers that use square brackets.

| Goal | Attribute or selection pattern | Result shape and when to use it | Homework connection |
| --- | --- | --- | --- |
| Inspect dimensions, labels, or types | `df.shape`, `df.columns`, `df.index`, `df.dtypes` | Returns metadata about the DataFrame; these are attributes, so they do not use `()` | Setup and debugging |
| Select one column | `df["salary"]` | Returns a Series | Most questions |
| Select several columns | `df[["name", "salary"]]` | Returns a DataFrame with columns in the listed order | 2, 5, 7, 10 |
| Select rows and columns by labels | `df.loc[row_mask, ["name", "salary"]]` | Returns selected rows and columns using labels or a Boolean mask | 2, 4, 5, 7 |
| Select by integer position | `df.iloc[row_positions, column_positions]` | Returns selected positions; useful for exploration but fragile for schema-driven pipelines | Exploration |
| Create or replace a column directly | `df["new"] = expression` | Mutates the DataFrame by assigning one aligned value per row | 3, 5, 8, 9 |

The most important GroupBy distinction is output shape:

| Operation | Question it answers | Typical row count |
| --- | --- | --- |
| `agg()` | What is the summary for each group? | One row per group |
| `transform()` | What group-derived value belongs beside each original row? | Same as the input |
| `filter()` | Which complete groups should remain? | Zero to all input rows |
| `apply()` | What custom result should each group produce? | Depends on the function |

#### Homework API map

| Exercise | Start with | Concept to practice |
| --- | --- | --- |
| 1. Department statistics | `groupby().agg()`, `sort_values()` | One summary row per department |
| 2. Above-department-average employees | `groupby().transform()`, boolean mask, `.loc[]` | Compare each row with a group statistic |
| 3. Salary bands | `pd.cut()`, `groupby().size()` | Categorize rows, then count combinations |
| 4. Experienced but underpaid | Boolean mask, `groupby().size()`, `sort_values()` | Filter first, then count by department |
| 5. Department ranking | `groupby()["salary"].rank()` | Same-row-count group transformation |
| 6. Join department information | `merge()`, then `groupby().mean()` | Key cardinality and adding lookup attributes |
| 7. Salary outliers | Two `transform()` results plus a boolean mask | Compare each salary with group mean and standard deviation |
| 8. Compensation adjustment | Column expressions with `where()`, `mask()`, or explicit boolean masks | Conditional row-aligned calculations |
| 9. Experience versus compensation | `pd.cut()`, multi-key `groupby().agg()`, reshape if helpful | Aggregate across two grouping dimensions |
| 10. Mini ETL | `groupby().agg()`, `idxmax()`, `merge()` or indexed selection, `to_csv()` | Build, verify, and publish a department-grain result |

This map identifies the operation family, not the completed answer. Before coding, state the intended output grain and whether the row count should stay the same, shrink, or expand.

`read_csv()` parses a file and normally materializes a DataFrame in memory. The class dataset is stored in [`data.csv`](data.csv). Declare the columns and types that the pipeline expects instead of assuming inference produced the intended schema.

```python
import pandas as pd


employees = pd.read_csv(
    "data.csv",
    usecols=[
        "employee_id",
        "name",
        "department",
        "salary",
        "years_experience",
        "active",
    ],
    dtype={
        "employee_id": "Int64",
        "name": "string",
        "department": "string",
        "salary": "Float64",
        "years_experience": "Int64",
        "active": "boolean",
    },
    true_values=["true", "TRUE"],
    false_values=["false", "FALSE"],
)

print(employees.head())
print(employees.dtypes)
print(employees.index)
print(employees.columns)

# Split once at the first space. This rule fits the fixture but is not a universal model for names.
name_parts = employees["name"].str.split(n=1, expand=True)
employees["first_name"] = name_parts[0]
employees["last_name"] = name_parts[1]

eligible_employees = employees.loc[
    employees["active"].fillna(False) & employees["salary"].ge(70_000)
].copy()

eligible_employees["old_salary"] = eligible_employees["salary"]
eligible_employees["salary_after_raise"] = (
    eligible_employees["salary"] * 1.05
).round(2)

total_payroll = eligible_employees["salary_after_raise"].sum()
average_salary = eligible_employees["salary_after_raise"].mean()

department_summary = (
    eligible_employees.groupby("department", as_index=False)
    .agg(
        employee_count=("employee_id", "count"),
        total_payroll=("salary_after_raise", "sum"),
        average_salary=("salary_after_raise", "mean"),
    )
    .sort_values("total_payroll", ascending=False)
)

print(eligible_employees[["name", "department", "old_salary", "salary_after_raise"]].head(10))
print(f"Total payroll after raises: ${total_payroll:,.2f}")
print(f"Average salary after raises: ${average_salary:,.2f}")
print(department_summary)

eligible_employees.to_csv("processed-employees.csv", index=False)
```

The boolean expression creates a mask aligned to the DataFrame's index. `.loc[...]` selects the matching rows, and `.copy()` creates an independent result that can be modified without ambiguous chained assignment. The arithmetic and aggregations operate on Series rather than explicit Python row loops.

The relationship to the earlier record pipeline is:

| Pure Python | pandas |
| --- | --- |
| `csv.DictReader()` | `pd.read_csv()` |
| `map(convert_employee, ...)` | declared dtypes and column operations |
| `filter(predicate, ...)` | boolean mask with `.loc[...]` |
| `map(give_raise, ...)` | `df["salary"] * 1.05` |
| `reduce(... total ...)` | `Series.sum()` |
| custom grouped reduction | `DataFrame.groupby().agg()` |
| total divided by count | `Series.mean()` |

`Series.map()` applies a function to each Series element, and modern pandas also has `DataFrame.map()` for elementwise DataFrame operations. That does not mean either is the best expression for every transformation. For simple numeric arithmetic, prefer the direct column expression:

```python
# Valid, but invokes a Python callable for this elementwise transformation.
raised_with_map = employees["salary"].map(lambda salary: salary * 1.05)

# Preferred here: communicates array arithmetic directly.
raised_as_column_expression = employees["salary"] * 1.05
```

Methods such as `.sum()` and `.mean()` aggregate values; they do not filter rows. A filter produces a boolean mask first, while an aggregation reduces the selected Series to a smaller result.

This column-oriented style is usually clearer and lets pandas use optimized array operations, but "vectorized" does not mean distributed and does not guarantee that every operation avoids Python or temporary copies. The progression is:

```text
plain Python record processing
        -> pandas DataFrames and vectorized operations on one machine
        -> Spark DataFrames and distributed transformations across partitions
```

The example uses pandas' nullable `Float64` dtype for introductory analysis. Binary floating-point is not an exact financial representation; a production payroll contract should use integer minor units or a deliberately selected and tested decimal representation with an explicit rounding policy.

#### The limited SQL comparison for this lesson

The useful connection here is the shape of the operation, not PostgreSQL setup or connection mechanics. Those belong in the SQL lecture.

| Intent | SQL form | pandas form |
| --- | --- | --- |
| Choose columns | `SELECT employee_id, salary` | `df[["employee_id", "salary"]]` |
| Filter rows | `WHERE active = TRUE` | `df.loc[df["active"]]` |
| Aggregate by key | `GROUP BY department` | `df.groupby("department")` |
| Join related data | `JOIN ... ON employee_id` | `df.merge(..., on="employee_id")` |

A database executes a query near managed data and provides persistence, concurrency control, transactions, permissions, and indexes. pandas loads data into the Python process for analysis and transformation. If the source is a database, push selective filters, projections, joins, and aggregations into it when that safely reduces the data transferred to Python.

#### pandas and big-data boundaries

pandas is primarily an in-memory, single-machine tool. It can process larger-than-memory inputs in chunks when the computation needs little coordination between chunks, but some operations require global state or create large intermediate copies.

Before scaling a pandas workflow, ask:

- Can `usecols` or source-side filtering load fewer columns or rows?
- Are column dtypes appropriate, especially strings and low-cardinality values?
- Can each input chunk produce a small mergeable summary?
- Does a join, global sort, or high-cardinality `groupby` require state that grows with the data?
- Is the result small enough to materialize safely?
- Has the workload outgrown one machine and justified a database, analytical engine, or distributed system?

These operations establish the pandas foundation: inspection, selection, calculated columns, aggregation, grouping, vectorization, and explicit output. Missing values, joins, reshaping, time series, and deeper memory measurement remain natural follow-on topics.

### JSON and JSON Lines

JSON represents strings, numbers, booleans, nulls, arrays, and objects. It is commonly called semi-structured because records can vary in shape and nest objects or arrays, but a trustworthy pipeline still defines and validates the expected schema.

A standard JSON document may contain one object, an array of objects, or another valid JSON value. JSON Lines, also called newline-delimited JSON or NDJSON, stores one complete JSON value per line. JSON Lines is the better match for incremental record processing because a reader does not need to parse one enclosing array before reaching individual records.

```json
{"employee_id": 1, "name": "Alice Johnson", "active": true}
{"employee_id": 2, "name": "Bob Smith", "active": true}
```

```python
import pandas as pd


events = pd.read_json("employees.jsonl", lines=True)
print(events.head())
```

CSV normally declares column names once in its header and locates each field by position. A JSON object carries keys with each record and can represent nested values. That flexibility is not free: missing keys may become nulls, extra keys may introduce columns, and conflicting value types may force coercion or an object-like dtype. Treat those outcomes as schema decisions rather than assuming shape changes cause no issues.

For deeply nested JSON, flattening into a DataFrame changes the record model and may multiply rows when arrays are expanded. Define the output grain before normalizing nested data.

### File formats beyond CSV and JSON

CSV and JSON are excellent interchange and inspection formats, but analytical systems often use formats with explicit schemas, binary encoding, column statistics, and splittable blocks.

| Format | Physical organization | Useful characteristics | Important boundary |
| --- | --- | --- | --- |
| CSV | Row-oriented text | Ubiquitous, human-readable, easy to exchange | Weak type information, repeated parsing, limited nested-data support |
| JSON Lines | One JSON value per line | Self-describing field names, nested values, incremental records | Verbose; record shapes and types can drift |
| Avro object container | Row-oriented binary blocks with a writer schema | Compact record serialization, schema resolution, splittable blocks | Readers need compatible schema semantics; not optimized for selecting a few analytical columns |
| Parquet | Columnar files divided into row groups, column chunks, and pages | Column projection, encodings, compression, and metadata for analytical scans | Individual files are immutable artifacts; a directory of files needs dataset or table-level coordination |
| ORC | Type-aware columnar files divided into stripes with indexes | Column projection, compression, and predicate pushdown for large scans | Like Parquet, the file format alone does not provide table transactions |

Avro is often used for serialized event records and appears in Kafka ecosystems, but Kafka does not require Avro. Producer and consumer serialization plus schema management are separate design choices.

Parquet is not merely a compressed CSV. It stores values by column within row groups and can apply different encodings and compression to data pages. A Parquet path may name one file or a dataset directory containing many files; that directory behavior comes from the dataset layout and reader, not from one Parquet file behaving like a folder.

ORC originated in the Hive ecosystem and remains an active Apache columnar format. Whether ORC or Parquet is appropriate depends on engine support, interoperability, data types, workload, and operational standards—not only on which project first introduced the format.

```python
import pandas as pd


employees = pd.read_parquet("employees.parquet")
print(employees.head())
```

`read_parquet()` requires a compatible parquet engine such as PyArrow or fastparquet. No parquet dependency is installed or verified by this lesson.

### File formats, table formats, and partitions

A **file format** defines how bytes, records, columns, encodings, and metadata are arranged inside data files. An **open table format** coordinates a collection of data files as one logical table and adds metadata for snapshots, schema evolution, partition evolution, concurrent commits, and file discovery.

- Apache Iceberg is an open table format that can track data files in formats including Parquet, ORC, and Avro. Its metadata hierarchy is more than “Parquet plus JSON”; it includes table metadata, snapshots, manifest lists, and manifests.
- Delta Lake is an open-source table format originally associated with Databricks and now governed as a Linux Foundation project. Delta tables commonly store data in versioned Parquet files and use a transaction log to define which files belong to each table version.

A **dataset partition** groups records by one or more partition values or transforms, often causing related records to be written into separate files or directory prefixes. A partition is not simply any piece of a Parquet, Iceberg, or Delta file. Inside a Parquet file, the analogous physical unit is a row group.

For a table partitioned by event date, a query restricted to one date can use partition metadata to avoid scanning files from unrelated dates. This is partition pruning:

```text
events/
|-- event_date=2026-09-13/
|   `-- part-000.parquet
`-- event_date=2026-09-14/
    `-- part-001.parquet
```

Partitioning improves pruning and parallelism only when it matches query patterns and produces sensible file sizes. Partitioning by a high-cardinality value can create many tiny partitions and files, increasing metadata, scheduling, and storage-request overhead.

Converting CSV or JSON into Avro, Parquet, or a managed table is not merely “compression.” The pipeline must parse values, validate schema, define null and numeric semantics, choose partitioning and file sizes, write the candidate data, verify it, and publish it through the table or dataset's commit boundary.

## Key takeaways

- Python is a core data-engineering language, but a Python script is not automatically a big-data system.
- Type hints improve source contracts; runtime validation protects the ingestion boundary.
- `map()` and `filter()` are lazy, single-use iterators in Python 3; `reduce()` returns one accumulated result.
- Named functions are valid inputs to all three operations and are often clearer than lambdas.
- pandas expresses many record transformations as column operations, but remains an in-memory, single-machine tool by default.
- Laziness can bound record flow, while grouping and materialization still create state proportional to data volume or key cardinality.
- JSON Lines supports incremental records; Parquet and ORC organize analytical data by column; Avro provides schema-based row serialization.
- A file format organizes individual files, while a table format coordinates files, snapshots, schemas, partitions, and commits.
- Partition pruning can avoid unnecessary files, but excessive partition cardinality creates metadata and small-file costs.
- Distributed execution adds partitions, shuffles, serialization, retries, and nondeterministic combine order.
- A trustworthy pipeline accounts for accepted, rejected, and published records instead of silently dropping malformed data.

## Homework and further practice

Use [`data.csv`](data.csv) for the separate [Monday pandas homework notebook](1.2_Mon_HW.ipynb). Keeping the exercise bank outside this lesson lets the guide explain concepts without mixing the answers or assignment checklist into the lecture narrative.

Additional instructor-recommended resources:

- [Python standard library reference](https://docs.python.org/3/library/)
- [pandas API reference](https://pandas.pydata.org/docs/reference/)
- [pandas introductory tutorials](https://pandas.pydata.org/docs/getting_started/intro_tutorials/)
- [Automate the Boring Stuff with Python, third edition](https://automatetheboringstuff.com/3e/), especially the chapters on functions and files
- [CSV import video](https://www.youtube.com/watch?v=q5uM4VKywbA)
- [Python overview video](https://www.youtube.com/watch?v=mRMmlo_Uqcs)

## References

- [Python Functional Programming HOWTO](https://docs.python.org/3/howto/functional.html)
- [Python `typing` documentation](https://docs.python.org/3/library/typing.html)
- [Python threading documentation](https://docs.python.org/3/library/threading.html)
- [Python CSV documentation](https://docs.python.org/3/library/csv.html)
- [Python logging documentation](https://docs.python.org/3/library/logging.html)
- [pandas introduction to DataFrames](https://pandas.pydata.org/docs/getting_started/intro_tutorials/01_table_oriented.html)
- [pandas `DataFrame.map()` documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.map.html)
- [pandas `read_json()` documentation](https://pandas.pydata.org/docs/reference/api/pandas.read_json.html)
- [pandas comparison with SQL](https://pandas.pydata.org/docs/getting_started/comparison/comparison_with_sql.html)
- [pandas GroupBy guide](https://pandas.pydata.org/docs/user_guide/groupby.html)
- [pandas combining-data tutorial](https://pandas.pydata.org/docs/getting_started/intro_tutorials/08_combine_dataframes.html)
- [pandas scaling guide](https://pandas.pydata.org/docs/user_guide/scale.html)
- [Apache Avro documentation](https://avro.apache.org/docs/1.11.2/)
- [Apache Parquet concepts](https://parquet.apache.org/docs/concepts/)
- [Apache ORC documentation](https://orc.apache.org/docs/)
- [Apache Iceberg documentation](https://iceberg.apache.org/docs/latest/)
- [Delta Lake documentation](https://docs.delta.io/)
- [Apache Spark RDD Programming Guide](https://spark.apache.org/docs/latest/rdd-programming-guide.html)
- [Apache Arrow in PySpark](https://spark.apache.org/docs/latest/api/python/tutorial/sql/arrow_pandas.html)
