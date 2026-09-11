# Basic Python Syntax and Standard-Library Quick Reference

> Status: Documentation complete  
> Level: Beginner  
> Applies to: Python 3.12 or newer  
> Data scale: Small local examples; iteration notes apply to larger inputs  
> Example status: Complete  
> Evidence status: Syntax and representative behavior verified locally on Python 3.12.3  
> Last reviewed: 2026-09

## Overview

This is a lookup sheet for the Python syntax and standard-library tools used
throughout the curriculum. It assumes general programming experience and calls
out the places where Kotlin instincts can produce the wrong Python result.

Do not try to memorize the entire standard library. Memorize the core syntax,
truthiness rules, collection behavior, and iterator model. Learn to recognize
the remaining functions and look up their exact signatures when needed.

## Learning objectives

- Read common Python expressions, blocks, functions, type hints, and exceptions.
- Distinguish an iterable from the iterator that advances through it.
- Predict which operations are lazy and which materialize data in memory.
- Choose common built-ins and iterator functions without silently losing data.
- Keep absent, null, false, zero, and empty values distinct at data boundaries.

## What to memorize versus recognize

### Memorize

- Indentation defines blocks after `:`.
- `=` assigns, `==` compares values, `is` compares identity, and `:=` assigns
  inside an expression.
- `None` is Python's null object; test it with `is None`.
- `and`, `or`, and `not` use truthiness and short-circuit.
- `return` finishes a function; `yield` emits a value and pauses a generator.
- `raise` throws an exception; `try` / `except` / `finally` handles failure and cleanup.
- Lists and dictionaries are mutable; tuples and strings are immutable.
- Iterators are stateful and normally one-shot.
- Type hints help tools but do not normally validate runtime input.

### Recognize and look up

- Less common `itertools` combinations.
- Advanced function parameter markers `/`, `*args`, and `**kwargs`.
- Decorators, descriptors, metaclasses, and asynchronous iteration.
- Exact library signatures, version additions, and edge-case behavior.

## The central iterator question: why call `iter(source)`?

`Iterable[T]` and `Iterator[T]` describe different capabilities:

| Concept | Promise | Examples |
| --- | --- | --- |
| `Iterable[T]` | `iter(value)` can produce an iterator | list, tuple, set, dictionary, file, generator |
| `Iterator[T]` | `next(value)` advances one stateful cursor | list iterator, file object, generator |

An iterable is a source from which a cursor can be requested. It is not
necessarily the cursor itself. `iter(source)` does not copy or convert the whole
collection. It asks the source for one iterator and stores that stateful cursor:

```python
values = [10, 20, 30]
cursor = iter(values)

next(cursor)  # 10
next(cursor)  # 20
```

For a normal collection, separate `iter` calls usually create separate cursors:

```python
values = [10, 20, 30]
first = iter(values)
second = iter(values)

next(first)   # 10
next(first)   # 20
next(second)  # 10: this is an independent cursor
```

For an object that is already an iterator, `iter(iterator)` normally returns
that same iterator:

```python
cursor = iter([10, 20, 30])
assert iter(cursor) is cursor
```

This is why batching captures one cursor:

```python
from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TypeVar

T = TypeVar("T")


def batched(source: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    if size <= 0:
        raise ValueError("size must be positive")
    cursor = iter(source)
    while batch := tuple(islice(cursor, size)):
        yield batch
```

Every `islice(cursor, size)` advances the same cursor. Calling
`islice(source, size)` repeatedly would be wrong for a re-iterable collection:
each call could obtain a fresh iterator and repeatedly return the first batch.
It happens to advance correctly when `source` is already a one-shot iterator,
but the annotation intentionally accepts the broader `Iterable[T]` contract.

`islice` itself accepts an iterable and internally obtains an iterator. The
explicit `cursor` is needed because this algorithm makes several separate
`islice` calls that must share one traversal position.

The closest Kotlin shape is calling `source.iterator()` once and repeatedly
advancing that `Iterator`. The analogy stops because a Python `Iterator` is also
an `Iterable`, and `iter(iterator)` commonly returns the same mutable cursor.

Collection-specific behavior still matters:

- A list or tuple iterates values in position order.
- A list used as a stack still iterates in position/insertion order; iteration
  does not call `pop`. A custom stack is accepted only if it implements iteration.
- An `array.array` and most third-party array objects are iterable, although
  third-party objects may define specialized element and mutation behavior.
- A dictionary iterates keys; use `.items()` for key/value pairs and `.values()`
  for values.
- A set iterates unique values with no business-order guarantee.
- A file iterates lines and also owns an external resource.
- A custom iterable may perform I/O or other work during iteration.

## Core syntax

### Names, literals, and comments

```python
# A comment
name = "Ada"                 # str
attempts = 3                 # int
ratio = 0.25                 # float
enabled = True               # bool: capital T/F
missing = None               # null object
items = ["a", "b"]          # mutable list
point = (10, 20)             # immutable tuple
unique_ids = {10, 20}        # mutable set
empty_set = set()            # {} is an empty dictionary, not a set
record = {"id": 10}          # mutable dictionary
```

Python binds names to objects. Assignment does not copy an object:

```python
left = [1, 2]
right = left
right.append(3)
assert left == [1, 2, 3]
```

### Operators worth memorizing

| Syntax | Meaning | Example |
| --- | --- | --- |
| `=` | Assignment | `count = 1` |
| `==`, `!=` | Value equality or inequality | `status == "ok"` |
| `<`, `<=`, `>`, `>=` | Ordering comparison | `0 <= count < 10` |
| `is`, `is not` | Object identity | `value is None` |
| `+`, `-`, `*`, `/` | Arithmetic; `/` always performs division | `5 / 2 == 2.5` |
| `//`, `%`, `**` | Floor division, remainder, exponent | `5 // 2 == 2` |
| `and`, `or`, `not` | Truthy short-circuit operations | `ready and valid` |
| `in`, `not in` | Membership | `"id" in record` |
| `:=` | Assign and return a value within an expression | `while batch := next_batch():` |
| `x if test else y` | Conditional expression | `label = "yes" if ok else "no"` |

Unlike Kotlin's `&&` and `||`, Python uses `and` and `or`. They return one of
their operands, not necessarily a `bool`:

```python
name = "" or "anonymous"     # "anonymous"
limit = 0 or 100             # 100: dangerous if zero is valid
```

### Blocks use `:` and indentation

```python
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
else:
    grade = "C"
```

The `:` announces a suite, and consistent indentation defines its body. This is
the structural role `{ ... }` plays in Kotlin; the `:` itself does not create a
brace or an object.

### Loops

```python
for index, value in enumerate(["a", "b"], start=1):
    print(index, value)

for number in range(3):       # 0, 1, 2; stop is exclusive
    print(number)

while queue:
    item = queue.pop()
    if item is None:
        continue
    if item == "stop":
        break
```

Python `for` iterates values from an iterable; it is not the C/Kotlin
three-expression `for` loop.

### Functions and parameters

```python
def normalize_name(raw: str, *, lowercase: bool = True) -> str:
    """Return a stripped, optionally lowercased name."""
    result = raw.strip()
    return result.lower() if lowercase else result


normalize_name(" Ada ")                    # "ada"
normalize_name(" Ada ", lowercase=False)   # "Ada"
```

- `def` defines a function.
- Parameter and return annotations describe intended types.
- `*` makes following parameters keyword-only.
- A function with no explicit `return` returns `None`.
- Default argument expressions are evaluated once when `def` executes.

Use `*args` to collect extra positional arguments and `**kwargs` to collect
extra named arguments. Prefer explicit parameters for stable application APIs.

```python
def describe(*values: object, **labels: object) -> tuple[tuple[object, ...], dict[str, object]]:
    return values, labels


describe(1, 2, unit="rows")  # ((1, 2), {"unit": "rows"})
```

### `return`, `yield`, and generators

```python
from collections.abc import Iterable, Iterator


def doubled(value: int) -> int:
    return value * 2          # finishes this call


def doubled_all(values: Iterable[int]) -> Iterator[int]:
    for value in values:
        yield value * 2       # emits one value, pauses, then resumes
```

Calling `doubled_all([1, 2])` creates a generator. Its body runs as the generator
is consumed, so work and exceptions may occur later than the call site.

### Imports

```python
import json
from itertools import islice

json.loads('{"ok": true}')
list(islice(range(10), 3))
```

Modules are objects and imports execute module-level code the first time a
module is loaded in a process. Avoid wildcard imports such as `from x import *`.
- because they make it unclear which names are present in the current namespace and can lead to unexpected name collisions. 
- Also more is loaded than necessary, which can increase memory usage and slow down startup time.

### Exceptions and cleanup

```python
def require_positive(value: int) -> int:
    if value <= 0:
        raise ValueError("value must be positive")
    return value


try:
    result = require_positive(-1)
except ValueError as error:
    print(error)
finally:
    print("runs whether the call succeeds or fails")
```

`raise` is the Python equivalent of Kotlin `throw`. Catch the narrow exception
types you can handle; do not translate programmer defects into apparently valid
null data.

Use `with` for deterministic cleanup:

```python
with open("events.jsonl", mode="r", encoding="utf-8") as source:
    first_line = source.readline()
```

This resembles Kotlin `use`, although Python context managers can represent
transactions, locks, temporary state, and other enter/exit protocols—not only
`Closeable` resources.

### Comprehensions

```python
squares = [value * value for value in range(4)]
even_squares = [value * value for value in range(6) if value % 2 == 0]
by_id = {row["id"]: row for row in rows}
unique_ids = {row["id"] for row in rows}
lazy_squares = (value * value for value in range(4))
```

List, dictionary, and set comprehensions materialize collections. A generator
expression, written with parentheses, is lazy and one-shot.

## Truthiness and missing data

Conditions call `bool(value)` conceptually. These common values are falsy:

| Category | Falsy examples |
| --- | --- |
| Null | `None` |
| Boolean | `False` |
| Numeric zero | `0`, `0.0`, `0j` |
| Empty text/bytes | `""`, `b""` |
| Empty collections | `[]`, `()`, `{}`, `set()` |
| Empty range | `range(0)` |

Most other objects are truthy. Notably, the string `"0"`, a non-empty
collection, and floating-point NaN are truthy.

This concise check is correct only when every falsy state has the same meaning:

```python
if not rows:
    print("there are no rows")
```

It is unsafe when absence, null, false, zero, and empty are different data:

```python
raw = record.get("attempts")
if not raw:
    raise ValueError("missing attempts")
```

That condition rejects all of these values:

```python
None, False, 0, 0.0, "", [], {}, set()
```

It also cannot distinguish a missing key from a present key whose value is
`None`, because `dict.get(key)` returns `None` for both by default. Use membership
or a unique sentinel:

```python
MISSING = object()

raw = record.get("attempts", MISSING)
if raw is MISSING:
    raise ValueError("attempts is missing")
if raw is None:
    raise ValueError("attempts cannot be null")
if type(raw) is not int:
    raise ValueError("attempts must be an integer")
if raw < 0:
    raise ValueError("attempts cannot be negative")
```

The exact `type(raw) is int` policy rejects `False` and `True`; this matters
because `bool` is a subclass of `int` in Python. At less strict internal
boundaries, `isinstance(raw, int)` may be the intended check.

Use an explicit test for the state meant by the contract:

| Contract question | Test |
| --- | --- |
| Is the dictionary key absent? | `"attempts" not in record` |
| Is this the sentinel? | `raw is MISSING` |
| Is the value null? | `raw is None` |
| Is the value false? | `raw is False` |
| Is the numeric value zero? | `raw == 0` after type validation |
| Is text empty? | `raw == ""` after type validation |
| Is a collection empty? | `len(rows) == 0`, or `if not rows` when all falsy states mean empty |

## Built-ins used constantly

These names require no import:

| Function | Definition | Small example |
| --- | --- | --- |
| `len(x)` | Number of items | `len([10, 20]) == 2` |
| `range(stop)` | Lazy integer sequence up to exclusive `stop` | `list(range(3)) == [0, 1, 2]` |
| `enumerate(xs, start=0)` | Lazy `(index, value)` pairs | `list(enumerate(["a"], 1)) == [(1, "a")]` |
| `zip(*xs, strict=False)` | Lazy tuples of parallel values | `list(zip([1], ["a"])) == [(1, "a")]` |
| `sorted(xs, key=None, reverse=False)` | New sorted list | `sorted([3, 1]) == [1, 3]` |
| `reversed(x)` | Reverse iterator where supported | `list(reversed([1, 2])) == [2, 1]` |
| `min`, `max` | Smallest/largest item | `max([4, 9, 2]) == 9` |
| `sum(xs, start=0)` | Add items | `sum([1, 2, 3]) == 6` |
| `any(xs)` | True if at least one item is truthy | `any([False, True]) is True` |
| `all(xs)` | True if every item is truthy | `all([True, True]) is True` |
| `iter(x)` | Obtain an iterator | `cursor = iter([1, 2])` |
| `next(it, default)` | Consume the next item or return a default | `next(iter([]), None) is None` |
| `isinstance(x, T)` | Runtime subtype-aware check | `isinstance(3, int)` |
| `type(x)` | Exact runtime type | `type(False) is bool` |
| `repr(x)` | Debug-oriented representation | `repr("a\n") == "'a\\n'"` |
| `list`, `tuple`, `set`, `dict` | Construct or materialize a collection | `tuple(range(2)) == (0, 1)` |
| `str`, `int`, `float`, `bool` | Construct/convert scalar values | `int("42") == 42` |

Useful patterns:

```python
rows = [{"id": 2}, {"id": 1}]
ordered = sorted(rows, key=lambda row: row["id"])

names = ["Ada", "Grace"]
lengths = [3, 5]
paired = list(zip(names, lengths, strict=True))
```

Use `zip(..., strict=True)` when unequal lengths indicate data loss or a bug.
The default `zip` silently stops at the shortest iterable. `any([])` is `False`;
`all([])` is `True`, so decide whether empty input is valid before relying on
either result.

Comprehensions are often clearer than `map` and `filter` for simple Python
expressions. `map(function, iterable)` and `filter(predicate, iterable)` return
lazy iterators.

## Iterator tools from `itertools`

These functions return iterators unless otherwise noted.

### `islice(iterable, stop)` or `islice(iterable, start, stop, step)`

Select positions lazily, similar to sequence slicing but without negative
indices. It advances the underlying iterator as values are requested.

```python
from itertools import islice

list(islice(range(10), 3))             # [0, 1, 2]
list(islice(range(10), 2, 7, 2))       # [2, 4, 6]

cursor = iter(range(6))
list(islice(cursor, 2))                # [0, 1]
list(islice(cursor, 2))                # [2, 3], same cursor continues
```

### `batched(iterable, n)`

Python 3.12 added this standard version of the batching recipe. It lazily emits
tuples of at most `n` items; the last tuple may be shorter.

```python
from itertools import batched

list(batched([1, 2, 3, 4, 5], 2))
# [(1, 2), (3, 4), (5,)]
```

Prefer the standard function when Python 3.12 is guaranteed. Keeping a small
implementation can still be educational or necessary for an older runtime.

### `chain(*iterables)` and `chain.from_iterable(iterable)`

Flatten one level lazily by consuming each input in sequence:

```python
from itertools import chain

list(chain([1, 2], [3]))                    # [1, 2, 3]
list(chain.from_iterable([[1, 2], [3]]))    # [1, 2, 3]
```

### `pairwise(iterable)`

Return overlapping adjacent pairs:

```python
from itertools import pairwise

list(pairwise([10, 15, 13]))  # [(10, 15), (15, 13)]
```

### `takewhile(predicate, iterable)` and `dropwhile(...)`

Take or skip only the leading run for which the predicate is true:

```python
from itertools import dropwhile, takewhile

values = [1, 2, 7, 3]
list(takewhile(lambda x: x < 5, values))  # [1, 2]
list(dropwhile(lambda x: x < 5, values))  # [7, 3]
```

These are not global filters. Once the predicate first fails, `takewhile` stops
and `dropwhile` returns that item plus everything after it.

### `groupby(iterable, key=None)`

Group adjacent items with the same key. Sort by the same key first when the
input is not already grouped:

```python
from itertools import groupby

rows = [("a", 1), ("a", 2), ("b", 3)]
groups = {
    key: list(group)
    for key, group in groupby(rows, key=lambda row: row[0])
}
```

The group iterators share the source and are one-shot. Materialize or fully
consume a group before advancing the outer iterator if it must be retained.

### Infinite iterators: `count`, `cycle`, and `repeat`

```python
from itertools import count, islice, repeat

list(islice(count(10, 5), 3))  # [10, 15, 20]
list(repeat("x", 3))           # ["x", "x", "x"]
```

Always give an infinite iterator a bounded consumer such as `islice` unless the
surrounding process is intentionally long-lived. Use `tee` cautiously: it
creates independent-looking iterators by buffering the gap between consumers.
If one consumer runs far ahead, memory can grow with that gap.

## Small standard-library toolkit for data work

### `collections`

```python
from collections import Counter, defaultdict, deque

counts = Counter(["ok", "bad", "ok"])       # {"ok": 2, "bad": 1}

by_key: defaultdict[str, list[int]] = defaultdict(list)
by_key["a"].append(1)

queue = deque([1, 2])
queue.append(3)
first = queue.popleft()                       # 1
```

- `Counter` counts hashable values.
- `defaultdict(factory)` creates a missing value on indexed access.
- `deque` supports efficient appends and removals at both ends.

Do not let a grouping dictionary or counter grow without a cardinality or
retention bound when processing unbounded data.

### `pathlib`, `json`, and `csv`

```python
import csv
import json
from pathlib import Path

path = Path("events.jsonl")

event = json.loads('{"id": 1}')              # text -> Python objects
text = json.dumps(event)                      # Python objects -> text

with Path("events.csv").open(encoding="utf-8", newline="") as source:
    for row in csv.DictReader(source):
        process(row)
```

`Path.read_text()` and `json.load(file)` materialize their complete result.
For large JSON Lines or CSV files, iterate records and bound record size rather
than reading the entire file into one string or object graph. Standard JSON has
no native datetime or decimal type, and CSV fields initially arrive as strings;
validate and convert explicitly.

## Common pitfalls

### Mutable default arguments

Avoid:

```python
def append_id(value: int, values: list[int] = []) -> list[int]:
    values.append(value)
    return values
```

The one list is shared across calls. Prefer:

```python
def append_id(value: int, values: list[int] | None = None) -> list[int]:
    result = [] if values is None else values
    result.append(value)
    return result
```

This uses `None` as a construction signal, so it is appropriate only when
`None` is not itself meaningful input.

### `is` versus `==`

Use `value is None` for the singleton `None`. Use `left == right` for value
equality. Do not use `is` for strings, numbers, lists, or business identifiers.

### A shallow copy is not a deep copy

```python
original = {"items": [1]}
copied = original.copy()
copied["items"].append(2)
assert original["items"] == [1, 2]
```

Prefer constructing the exact new boundary model you need. `copy.deepcopy` is
not automatically safe or cheap for arbitrary object graphs.

### Repeated mutable values can alias

```python
bad = [[]] * 3
bad[0].append(1)
assert bad == [[1], [1], [1]]

good = [[] for _ in range(3)]
```

### Iterators are consumed

```python
cursor = iter([1, 2])
assert list(cursor) == [1, 2]
assert list(cursor) == []
```

Do not count, log, or sample a one-shot iterator before the real consumer unless
that consumption is part of the design.

### Materialization can defeat laziness

`list(iterator)`, `tuple(iterator)`, `sorted(iterator)`, and grouping all retain
data. A generator earlier in the pipeline does not make a later global sort or
collection bounded.

### Dictionary and set semantics

- Iterating a dictionary yields keys, not key/value pairs.
- `record[key]` raises `KeyError` when absent; `record.get(key)` returns `None`
  unless another default is supplied.
- Dictionary insertion order is a language guarantee, but it is not event-time
  order or a distributed ordering guarantee.
- Set iteration must not define output order or business priority.

### Numeric surprises

- `True == 1` and `False == 0`; validate boolean versus integer at boundaries.
- `/` returns a floating-point result; `//` performs floor division, including
  toward negative infinity for negative values.
- Binary floating point cannot exactly represent many decimal fractions. Use
  integers in an owned unit or `decimal.Decimal` when exact decimal arithmetic
  is required.
- Python integers can grow beyond 64 bits, but databases, file formats, and
  distributed engines commonly have bounded integer types.

### Catching too broadly

Avoid `except:` and be cautious with `except Exception:`. Catch only failures the
current boundary can classify or recover from, preserve the cause when
translating (`raise DomainError(...) from error`), and let cancellation or fatal
conditions reach their owner.

### Type hints are not data validation

```python
def increment(value: int) -> int:
    return value + 1
```

Python does not normally reject `increment("1")` at the call boundary because
of the annotation; execution fails only when the body attempts incompatible
addition. Validate files, API responses, database rows, and messages at runtime.

## Data quality, testing, and evidence

For boundary parsing, test a semantic table containing at least: absent key,
`None`, `False`, `0`, empty string, empty collection, valid value, wrong type,
and oversized value. For iterators, test empty input, one item, exact batch size,
remainder batch, early stop, second traversal, and a source that fails midway.

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Syntax | Compile the Python fences intended as complete snippets | No syntax errors | Verified locally on Python 3.12.3 |
| Iterator/truthiness behavior | Run representative assertions from this reference | Documented cursor and falsy behavior | Verified locally on Python 3.12.3 |
| External I/O examples | Run against real files and malformed/large inputs | Cleanup and bounds hold | Pending; paths are illustrative |
| Type checking | Run a configured static type checker | Annotations are internally consistent | Pending; no checker is configured for this reference |

Local examples do not prove memory, filesystem, serializer, or distributed-engine
behavior at production scale.

## Knowledge check

1. Why does batching call `iter(source)` once even though `islice` accepts an
   iterable?
2. Predict the batches produced from a list if each loop creates a fresh
   `islice(source, 2)` instead of sharing a cursor.
3. Write tests that keep absent, `None`, `False`, `0`, and `""` distinct.
4. Explain why `zip(left, right)` can silently lose records and when to use
   `strict=True`.
5. Find every materialization point in a generator pipeline ending with
   `sorted(...)` and `list(...)`.
6. Explain why two calls to a function with a mutable default can affect one
   another.

## Key takeaways

- An iterable supplies an iterator; an iterator is the stateful cursor.
- Truthiness is a control-flow convenience, not a missing-data model.
- Lazy operations postpone work, while materializing operations retain results.
- Python annotations document contracts for tools; runtime boundaries still need
  validation.
- Prefer explicit semantics when a concise idiom could hide dropped, collapsed,
  reordered, or retained data.

## Resources

- [Python 3.12 built-in functions](https://docs.python.org/3.12/library/functions.html)
- [Python 3.12 `itertools`](https://docs.python.org/3.12/library/itertools.html)
- [Python 3.12 expressions](https://docs.python.org/3.12/reference/expressions.html)
- [Python 3.12 simple statements](https://docs.python.org/3.12/reference/simple_stmts.html)
- [Python 3.12 built-in types](https://docs.python.org/3.12/library/stdtypes.html)

## Related topics

- [Python area README](README.md)
- [Python runtime, types, and Kotlin comparisons](01-python-runtime-types-and-kotlin-comparisons.md)
- [Collections, iteration, generators, and bounded memory](02-collections-iteration-generators-and-bounded-memory.md)
- [Functions, classes, dataclasses, protocols, and modules](03-functions-classes-dataclasses-protocols-and-modules.md)
- [Errors, context managers, and resource lifetime](04-errors-context-managers-and-resource-lifetime.md)
- [Type hints, validation, and untrusted data](05-type-hints-validation-and-untrusted-data.md)

## Completion checklist

- [x] Core syntax and Kotlin differences summarized
- [x] Iterable, iterator, generator, and materialization distinguished
- [x] Truthiness and missing/null/false/zero/empty states separated
- [x] Common built-ins and iterator tools shown with small examples
- [x] Frequent correctness and memory pitfalls documented
- [x] Representative syntax and behavior verified locally
- [ ] File-I/O examples verified against bounded malformed fixtures
- [ ] Static type-check evidence collected
