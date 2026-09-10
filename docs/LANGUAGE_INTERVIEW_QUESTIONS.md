# Python and SQL interview questions

> Status: Complete for the current Language ready queue; 97 questions across 17 topics
> Scope: Python language/runtime and SQL language/query semantics  
> Version baseline: Python 3.14; NumPy and pandas stable documentation; PostgreSQL 18 where SQL behavior is dialect-specific
> Last reviewed: 2026-09

Questions are completed through
[`INTERVIEW_PREP_WORKFLOW.md`](INTERVIEW_PREP_WORKFLOW.md) using the canonical
[`INTERVIEW_QUESTION_TEMPLATE.md`](INTERVIEW_QUESTION_TEMPLATE.md).

Questions are grouped by durable topic. Numbering restarts at `1` within each
topical section.

## Topical guide

- [Python data model and core collections](#python-data-model-and-core-collections)
- [Python functions and scope](#python-functions-and-scope)
- [Python object-oriented design](#python-object-oriented-design)
- [Python iteration and resource management](#python-iteration-and-resource-management)
- [Python memory and runtime](#python-memory-and-runtime)
- [Python concurrency and async](#python-concurrency-and-async)
- [Python typing, errors, and testing](#python-typing-errors-and-testing)
- [Python algorithms and data transformations](#python-algorithms-and-data-transformations)
- [Python packaging and configuration](#python-packaging-and-configuration)
- [NumPy and Pandas](#numpy-and-pandas)
- [SQL filtering, aggregation, and set operations](#sql-filtering-aggregation-and-set-operations)
- [SQL joins and subqueries](#sql-joins-and-subqueries)
- [SQL window functions and analytical patterns](#sql-window-functions-and-analytical-patterns)
- [SQL recursive queries and temporal logic](#sql-recursive-queries-and-temporal-logic)
- [SQL transactions and concurrency](#sql-transactions-and-concurrency)
- [SQL query plans and performance](#sql-query-plans-and-performance)
- [Relational design and correctness](#relational-design-and-correctness)

## Python data model and core collections

### 1. How do Python's list, tuple, set, and dictionary types differ, and when would you choose each?

**Interview answer**

A `list` is an ordered, mutable sequence; choose it when position, duplicates, and updates matter. A `tuple` is an ordered, immutable sequence; choose it for a fixed record-like grouping or a hashable composite key when every element is hashable. A `set` stores unique hashable values and is optimized for membership and set algebra, but it provides no sequence indexing or meaningful iteration order. A `dict` maps unique hashable keys to values and preserves insertion order. Lists and tuples have linear membership tests, while sets and dictionaries normally provide average constant-time membership or key lookup. The choice should follow semantics first, then access pattern and scale.

**Tradeoffs and pitfalls**

- Do not use a set when output order is part of the contract.
- Dictionary insertion order is guaranteed, but it is not sorted order.
- A tuple can still refer to mutable objects, so tuple immutability is shallow.

**Source provenance**

- S005, S002

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

### 2. What does dynamic typing mean in Python's object-and-name model?

**Interview answer**

Python is dynamically typed because a name is not permanently declared as one type: a name is bound to an object, and the object carries its type. Rebinding `value` from an `int` to a `str` changes which object the name refers to; it does not mutate an integer into a string. Operations are checked against the runtime object's protocol, so failure occurs when code executes an unsupported operation unless a static checker catches it earlier. This gives flexible polymorphism, but boundaries still benefit from type hints, validation, and tests.

**Example**

```python
value = 42
value = "42"       # The name now refers to a different object.
print(value.upper())
```

**Tradeoffs and pitfalls**

Dynamic typing is different from weak typing: Python generally does not silently coerce unrelated types just because an operation was requested.

**Source provenance**

- S005

**Related curriculum**

- [`01-python-runtime-types-and-kotlin-comparisons.md`](02-python-for-data-engineering/01-python-runtime-types-and-kotlin-comparisons.md)

### 3. When do `==` and `is` produce different results?

**Interview answer**

`==` asks whether two objects have equal values, normally through `__eq__`; `is` asks whether both references identify the exact same object. Two separately created lists can therefore be equal without being identical. Use `is` for identity-sensitive sentinels, especially `x is None`, and use `==` for values. Never depend on interning or caching of strings and small integers: implementations may reuse immutable objects, so an identity test can appear to work and then fail elsewhere.

**Example**

```python
left = [1, 2]
right = [1, 2]

assert left == right
assert left is not right
assert None is None
```

**Source provenance**

- S005

**Related curriculum**

- [`01-python-runtime-types-and-kotlin-comparisons.md`](02-python-for-data-engineering/01-python-runtime-types-and-kotlin-comparisons.md)

### 4. How do mutable and immutable objects behave when passed to functions?

**Interview answer**

Python passes an object reference by assignment: the parameter becomes another local name for the same object. If a function mutates a passed mutable object, such as appending to a list, the caller observes that mutation. If the function rebinds its parameter, the caller's name is unchanged. Operations on immutable objects such as integers and strings create or select another object and rebind the local parameter, so they cannot change the caller's object in place. A clear API either returns a new value or documents intentional mutation.

**Example**

```python
def update(items: list[int], count: int) -> None:
    items.append(3)  # visible to caller
    count += 1       # only rebinds the local name

items = [1, 2]
count = 0
update(items, count)
assert items == [1, 2, 3]
assert count == 0
```

**Tradeoffs and pitfalls**

Avoid mutable default arguments unless shared state across calls is explicitly intended; defaults are evaluated once when the function is defined.

**Source provenance**

- S005

**Related curriculum**

- [`01-python-runtime-types-and-kotlin-comparisons.md`](02-python-for-data-engineering/01-python-runtime-types-and-kotlin-comparisons.md)

### 5. When does a list comprehension improve code, and when does it harm readability or memory use?

**Interview answer**

A list comprehension is a good fit for a small, side-effect-free transformation or filter whose result really must be a list. It keeps the data flow visible: expression, source, then optional predicates. It becomes a liability when it nests several loops, embeds complex branching, performs side effects, or hides domain decisions; a named loop or helper is then easier to test and explain. A comprehension eagerly materializes the entire output, so for a large or unbounded input use a generator expression or an explicit streaming loop unless later code needs random access or repeated traversal.

**Example**

```python
valid_ids = [row["id"] for row in rows if row.get("id") is not None]

# For one-pass consumption of a large source:
valid_ids_iter = (row["id"] for row in rows if row.get("id") is not None)
```

**Source provenance**

- S005

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

### 6. What behavioral difference separates `list.append()` from `list.extend()`?

**Interview answer**

`append(x)` adds `x` as one new list element. `extend(iterable)` iterates its argument and adds each yielded element. Thus `items.append([2, 3])` produces a nested list, while `items.extend([2, 3])` adds two peers. Both mutate the original list and return `None`, so assigning their result is a common bug. The distinction is about one object versus the contents of an iterable, not merely one value versus many values.

**Example**

```python
a = [1]
a.append([2, 3])   # [1, [2, 3]]

b = [1]
b.extend([2, 3])   # [1, 2, 3]
```

**Source provenance**

- S005

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

### 7. How do shallow and deep copies behave with nested mutable objects?

**Interview answer**

A shallow copy creates a new outer container but reuses references to its children. Mutating the outer structure is independent, but mutating a shared nested list or dictionary is visible through both copies. `copy.deepcopy` recursively copies reachable components and uses a memo to preserve shared relationships and handle cycles. Deep copying is not automatically safer: it may be expensive, may duplicate objects that should remain shared, and custom or resource-owning objects may need explicit copy behavior. Prefer constructing the exact independent state the operation requires.

**Example**

```python
from copy import copy, deepcopy

original = {"tags": ["raw"]}
shallow = copy(original)
deep = deepcopy(original)

original["tags"].append("verified")
assert shallow["tags"] == ["raw", "verified"]
assert deep["tags"] == ["raw"]
```

**Source provenance**

- S005

**Related curriculum**

- [`01-python-runtime-types-and-kotlin-comparisons.md`](02-python-for-data-engineering/01-python-runtime-types-and-kotlin-comparisons.md)

### 8. How do Python dictionaries implement average constant-time lookup?

**Interview answer**

A Python dictionary is a hash table. It hashes the key to choose a candidate location, then uses equality to distinguish keys that land in the same collision path. With a well-distributed, stable hash and a table that maintains spare capacity, lookup, insertion, and deletion are average `O(1)`; they are not worst-case constant-time guarantees. Resizing occasionally costs `O(n)` but is amortized across insertions. At the language level, rely on mapping semantics and insertion order; layout, probing, and compact-memory details are CPython implementation details.

**Tradeoffs and pitfalls**

- Poor custom hashes create collisions and degrade performance.
- Keys whose equality or hash changes after insertion can become unreachable in the table.
- A dictionary's memory overhead can dominate when storing many tiny records.

**Source provenance**

- S005

**Verification note**

- Reviewed against the Python 3.14 [data model](https://docs.python.org/3.14/reference/datamodel.html) and [mapping types](https://docs.python.org/3.14/library/stdtypes.html#mapping-types-dict) on 2026-09-09. Average-case complexity is the durable hash-table expectation; concrete layout is implementation-specific.

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

### 9. Why must dictionary keys be hashable, and what makes a value safely hashable?

**Interview answer**

A dictionary uses a key's hash to locate it, then equality to confirm a match. Hashability therefore requires a hash value that remains stable for the object's lifetime and the invariant that equal objects have equal hashes. Built-in immutable values are often hashable, but immutability alone is not sufficient: a tuple containing a list is unhashable. For a custom value object, base `__eq__` and `__hash__` on the same immutable fields. A mutable value-based object should normally be unhashable, because changing it after insertion would put it in the wrong hash bucket.

**Example**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PartitionKey:
    region: str
    day: str
```

**Source provenance**

- S005

**Related curriculum**

- [`01-python-runtime-types-and-kotlin-comparisons.md`](02-python-for-data-engineering/01-python-runtime-types-and-kotlin-comparisons.md)

### 10. What guarantees and performance characteristics matter when using Python's stable sort?

**Interview answer**

Python sorting is stable: records with equal sort keys retain their original relative order. That allows deliberate multi-pass sorting and preserves earlier ordering within ties. `sorted(iterable)` returns a new list, while `list.sort()` mutates a list and returns `None`. Prefer a `key` function over a comparison function; the key is computed once per input item, and sorting then compares those derived keys. General sorting is `O(n log n)` in the worst case, while Python's adaptive implementation can exploit existing runs. Define a deterministic tie-breaker when reproducible output must not depend on input arrival order.

**Example**

```python
# Stable two-pass sort: department primary, salary descending secondary.
employees.sort(key=lambda employee: employee.salary, reverse=True)
employees.sort(key=lambda employee: employee.department)
```

**Tradeoffs and pitfalls**

Mixed values without a common ordering can raise `TypeError`; normalize them or return comparable keys. For only the smallest `k` items, a heap-based selection can avoid a full sort.

**Source provenance**

- S005

**Verification note**

- Reviewed against the Python 3.14 [Sorting HOWTO](https://docs.python.org/3.14/howto/sorting.html) on 2026-09-09.

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

### 11. How should repeated string concatenation be implemented efficiently?

**Interview answer**

For many fragments, collect them and call `separator.join(fragments)`, or write incrementally to `io.StringIO` when the producer naturally emits pieces. Strings are immutable, so repeated `result += piece` may repeatedly allocate and copy growing intermediate strings; some implementations optimize cases, but portable code should not depend on that. For a few fixed expressions, an f-string or `+` is clearer and the performance distinction is irrelevant. For byte data, use bytes-oriented buffers rather than converting through text.

**Example**

```python
line = ",".join(str(value) for value in values)
```

**Source provenance**

- S005

**Verification note**

- Reviewed against Python 3.14 [sequence-type guidance](https://docs.python.org/3.14/library/stdtypes.html#common-sequence-operations) on 2026-09-09.

**Related curriculum**

- [`08-testing-profiling-memory-and-python-performance.md`](02-python-for-data-engineering/08-testing-profiling-memory-and-python-performance.md)

## Python functions and scope

### 1. How do positional, keyword, default, `*args`, and `**kwargs` arguments interact?

**Interview answer**

At a call, positional arguments fill eligible parameters from left to right; keyword arguments bind by name; omitted parameters use their defaults. A parameter cannot receive two values. In a definition, `/` ends positional-only parameters and `*` starts keyword-only parameters. `*args` collects unmatched positional arguments into a tuple, and `**kwargs` collects unmatched keyword arguments into a new dictionary. Defaults are evaluated once when the definition executes, so mutable defaults can leak state across calls. Use these features to make a stable, intentional API—not to accept arbitrary arguments that hide mistakes.

**Example**

```python
def load(source, /, *columns, limit=100, **reader_options):
    ...

load("events.json", "id", "time", limit=500, encoding="utf-8")
```

**Source provenance**

- S005

**Verification note**

- Reviewed against Python 3.14 [function definitions](https://docs.python.org/3.14/reference/compound_stmts.html#function-definitions) and [calls](https://docs.python.org/3.14/reference/expressions.html#calls) on 2026-09-09.

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

### 2. How does Python resolve names through local, enclosing, global, and built-in scopes?

**Interview answer**

For an ordinary function reference, Python searches local, then lexically enclosing function scopes, then the module global scope, then built-ins—the LEGB shorthand. Binding a name anywhere in a function normally makes it local throughout that block, which can cause `UnboundLocalError` if it is read before assignment. `nonlocal` targets an existing binding in the nearest enclosing function scope; `global` targets the module namespace. Prefer explicit parameters and return values over hidden global mutation. LEGB is a useful interview model, but class bodies, comprehensions, and Python 3.14 annotation scopes have special rules.

**Example**

```python
def counter():
    count = 0

    def increment():
        nonlocal count
        count += 1
        return count

    return increment
```

**Source provenance**

- S005

**Verification note**

- Reviewed against Python 3.14 [naming and binding](https://docs.python.org/3.14/reference/executionmodel.html#naming-and-binding) on 2026-09-09; Python 3.14 uses annotation scopes for annotations.

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

### 3. How do decorators use first-class functions and closures to add behavior?

**Interview answer**

Functions are objects, so a decorator can receive a function and return another callable. A decorator factory can also close over configuration. `@decorate` is essentially rebinding the function name to `decorate(original)` when the definition executes; stacked decorators compose from the bottom upward. The wrapper usually forwards `*args` and `**kwargs`, adds behavior before or after the call, and returns the original result. Use `functools.wraps` so tooling sees the original name, documentation, annotations, and `__wrapped__` link.

**Example**

```python
from functools import wraps

def audit(event: str):
    def decorate(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            print(event)
            return function(*args, **kwargs)
        return wrapper
    return decorate
```

**Tradeoffs and pitfalls**

Decorators can obscure control flow and signatures. Keep cross-cutting behavior narrow, preserve metadata, and do not silently change exception or return-value contracts.

**Source provenance**

- S005

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

### 4. Where are lambda expressions appropriate, and when should a named function replace one?

**Interview answer**

A lambda is appropriate for a short, local, single-expression callable when naming it would add little—commonly a sort key or a tiny adapter. It has the same first-class function behavior and lexical name lookup as a `def`, but its body is limited to one expression. Use `def` when logic needs statements, annotations, documentation, reuse, direct unit tests, meaningful stack traces, or a domain name. Dense nested lambdas save lines but usually increase review and debugging cost.

**Example**

```python
rows.sort(key=lambda row: (row["region"], row["event_time"]))
```

**Source provenance**

- S005

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

### 5. How do closures capture enclosing state, and what late-binding surprises can occur?

**Interview answer**

A closure is a nested function that retains access to free variables from its enclosing function after that outer call returns. It captures bindings, not frozen snapshots of their current values. Therefore callbacks created in a loop can all observe the loop variable's final value when invoked later. Bind the current value explicitly—often as a default parameter—or use a factory that creates a fresh enclosing scope. Use `nonlocal` only when intentional shared mutable closure state is clearer than an object.

**Example**

```python
bad = [lambda: i for i in range(3)]
assert [f() for f in bad] == [2, 2, 2]

good = [lambda i=i: i for i in range(3)]
assert [f() for f in good] == [0, 1, 2]
```

**Source provenance**

- S005

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

### 6. How would you write a timing decorator without losing the wrapped function's metadata?

**Interview answer**

Wrap the callable with `functools.wraps`, measure elapsed duration with a monotonic performance clock, and put reporting in `finally` so failed calls are timed too. Return the original result and let the original exception propagate. In production, emit duration and outcome to an injected metrics interface rather than printing, and take care not to record sensitive arguments. A normal wrapper times synchronous execution only; an async function needs an `async def` wrapper that awaits it.

**Example**

```python
from functools import wraps
from time import perf_counter

def timed(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        started = perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            print(f"{function.__qualname__}: {perf_counter() - started:.3f}s")
    return wrapper
```

**Source provenance**

- S002

**Verification note**

- Reviewed against Python 3.14 [`functools.wraps`](https://docs.python.org/3.14/library/functools.html#functools.wraps) and [`time.perf_counter`](https://docs.python.org/3.14/library/time.html#time.perf_counter) on 2026-09-09.

**Related curriculum**

- [`08-testing-profiling-memory-and-python-performance.md`](02-python-for-data-engineering/08-testing-profiling-memory-and-python-performance.md)

### 7. How would you implement a throttle around a callable while keeping it testable?

**Interview answer**

First define the contract: fixed spacing, fixed or sliding window, or token bucket; burst behavior; whether callers block, fail, or queue; and whether the limit is per process or shared. For a simple synchronous fixed-spacing throttle, store the next permitted monotonic time, serialize that state with a lock, and inject the clock and sleeper so tests advance fake time instead of sleeping. Preserve the callable's metadata. A process-local decorator cannot enforce a fleet-wide API quota; that requires coordinated state or a gateway, and retries need to respect server backoff signals.

**How it works**

The lock must cover reservation of the next slot, not necessarily the throttled call itself. Otherwise concurrent callers can all observe the same availability and exceed the rate. Decide explicitly whether failed calls consume quota.

**Tradeoffs and pitfalls**

- Wall-clock adjustments can break elapsed-time calculations; use a monotonic clock.
- Sleeping worker threads may reduce throughput; asynchronous code needs an awaitable limiter.
- Holding a lock while sleeping creates head-of-line blocking; reserving slots can be fairer but needs careful cancellation handling.

**Source provenance**

- S002

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

## Python object-oriented design

### 1. How do instance methods, class methods, and static methods bind and differ in purpose?

**Interview answer**

An ordinary function accessed through an instance becomes a bound method and receives that instance as its first argument, conventionally `self`; use it for behavior involving instance state. A `classmethod` receives the actual class as `cls`, whether accessed through the class or an instance; it is useful for polymorphic alternate constructors or class-wide behavior. A `staticmethod` receives no implicit argument; it is a namespaced utility related to the class but independent of instance and class state. If no class namespace is needed, a module-level function is often simpler.

**Example**

```python
class Job:
    def run(self): ...

    @classmethod
    def from_config(cls, config):
        return cls()

    @staticmethod
    def valid_name(name):
        return bool(name.strip())
```

**Source provenance**

- S005

**Verification note**

- Reviewed against Python 3.14's [descriptor guide](https://docs.python.org/3.14/howto/descriptor.html#kinds-of-methods) on 2026-09-09.

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

### 2. How does Python inheritance work, and when is composition preferable?

**Interview answer**

Inheritance lets a subclass reuse and specialize behavior from base classes; attribute lookup follows the class's method resolution order, and cooperative overrides delegate with `super()`. It is appropriate for a genuine substitutable "is-a" relationship with a stable shared contract. Composition gives an object collaborators and delegates to them; prefer it for "has-a" relationships, independently replaceable policies, runtime configuration, and avoiding tight coupling to base-class internals. Python's protocols and duck typing often let composition provide polymorphism without a nominal hierarchy.

**Tradeoffs and pitfalls**

Deep hierarchies make initialization, state ownership, and override interactions hard to reason about. Composition adds forwarding code but usually makes dependencies and tests more explicit.

**Source provenance**

- S005

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

### 3. How does method resolution order make multiple inheritance deterministic?

**Interview answer**

Every class has a linear method resolution order available as `Class.__mro__`. Python computes it with C3 linearization, preserving local base order, putting a class before its parents, and maintaining a consistent ordering inherited from parent classes; an inconsistent hierarchy is rejected at class creation. Attribute lookup follows that single order. Zero-argument `super()` means "continue after the current class in this instance's MRO," not simply "call my named parent." Cooperative multiple inheritance therefore requires compatible method signatures and every participant to call `super()` exactly as its contract expects.

**Example**

```python
class A: ...
class B(A): ...
class C(A): ...
class D(B, C): ...

assert D.__mro__ == (D, B, C, A, object)
```

**Source provenance**

- S005

**Verification note**

- Reviewed against the Python 3.14 [MRO HOWTO](https://docs.python.org/3.14/howto/mro.html) and [`super`](https://docs.python.org/3.14/library/functions.html#super) on 2026-09-09.

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

### 4. What distinct purposes do `__init__`, `__str__`, and `__repr__` serve?

**Interview answer**

`__init__` initializes an already created instance and must return `None`; object allocation is handled by `__new__`. `__str__` returns a readable user-facing representation used by `str()` and normally by `print()`. `__repr__` returns a developer-facing, unambiguous representation used by `repr()`, containers, and debugging; when practical it resembles valid reconstruction code. If `__str__` is absent, `object.__str__` delegates to `__repr__`. Never expose secrets in either representation, because they commonly appear in logs and tracebacks.

**Example**

```python
class Dataset:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Dataset(name={self.name!r})"
```

**Source provenance**

- S005

**Verification note**

- Reviewed against Python 3.14 [basic customization](https://docs.python.org/3.14/reference/datamodel.html#basic-customization) on 2026-09-09.

**Related curriculum**

- [`03-functions-classes-dataclasses-protocols-and-modules.md`](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)

## Python iteration and resource management

### 1. How do generators suspend execution, and why can they process large inputs with bounded memory?

**Interview answer**

Calling a generator function returns a generator iterator without running the body. Each `next()` resumes execution until `yield`, returns that value, and suspends the frame with its instruction position and live local state; exhaustion raises `StopIteration`. Because values can be produced and consumed one at a time, memory depends on retained generator state and buffering rather than total input size. That is only a bounded-memory guarantee if each stage remains streaming: `list(generator)`, an unbounded sort or group-by, `tee`, or an accumulating consumer can still materialize the dataset.

**Example**

```python
def valid_rows(lines):
    for line in lines:
        row = parse(line)
        if row.is_valid:
            yield row
```

**Tradeoffs and pitfalls**

Generators are normally one-shot and preserve resources and referenced objects while suspended. Use an explicit context manager for deterministic resource ownership rather than depending on generator finalization.

**Source provenance**

- S005, S006

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

### 2. What is the difference between an iterable, an iterator, and a generator?

**Interview answer**

An iterable can produce an iterator, usually through `iter(obj)`; containers such as lists are iterable and can usually be traversed repeatedly by producing a fresh iterator. An iterator is the stateful one-pass cursor: `iter(iterator)` returns itself and `next(iterator)` yields the next item or raises `StopIteration`. A generator is a convenient kind of iterator created by a generator function or generator expression; it implements the iterator protocol while Python manages suspended execution state. Code should accept an `Iterable` when it can start traversal, and an `Iterator` when ownership of an already-started stream matters.

**Example**

```python
values = [10, 20]       # iterable
cursor = iter(values)   # iterator
squares = (x * x for x in values)  # generator iterator
```

**Tradeoffs and pitfalls**

Calling `iter()` twice on a list creates independent cursors; calling it twice on the same iterator returns the same cursor. Accidentally iterating an iterator once for logging can consume data needed later.

**Source provenance**

- S005

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

### 3. How does the context-manager protocol guarantee resource cleanup, and how would you implement it for a transactional database connection?

**Interview answer**

`with` calls a context manager's `__enter__`, runs the body, then calls `__exit__` on both normal and exceptional exits. `__exit__` receives exception details and may suppress the exception only by returning a truthy value. Put release logic in `finally`; for a transaction, commit only after successful work, roll back on any exception, and always close or return the connection to its pool. The exact transaction and connection behavior belongs to the database driver, so a custom manager should make those semantics explicit instead of assuming every connection context manager closes the resource.

**Example**

```python
from contextlib import contextmanager

@contextmanager
def transaction(connect):
    connection = connect()
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
```

**Tradeoffs and pitfalls**

- If `commit()` fails, attempt rollback while preserving useful diagnostics.
- Some pools require `connection.close()` to return a connection rather than close a socket.
- Nested transactions and savepoints are driver-specific.
- Do not catch only `Exception` if the resource must be cleaned up for all non-local exits; `finally` remains the cleanup boundary.

**Source provenance**

- S005, S006

**Verification note**

- Reviewed against Python 3.14's [`with` statement](https://docs.python.org/3.14/reference/compound_stmts.html#the-with-statement), [`contextlib.contextmanager`](https://docs.python.org/3.14/library/contextlib.html#contextlib.contextmanager), and the [`sqlite3` connection context manager](https://docs.python.org/3.14/library/sqlite3.html#how-to-use-the-connection-context-manager) on 2026-09-09. SQLite's own connection context commits or rolls back but does not close the connection.

**Related curriculum**

- [`04-errors-context-managers-and-resource-lifetime.md`](02-python-for-data-engineering/04-errors-context-managers-and-resource-lifetime.md)

### 4. How would you stream-process input larger than memory, including bounded aggregation and partitioned output?

**Interview answer**

Read incrementally from an iterator or chunked reader, validate each record, transform it, and write bounded batches instead of accumulating all rows. Every stateful operation needs an explicit bound: aggregate a fixed key space or time window, evict completed state, approximate when acceptable, or spill/partition to disk and perform later merge passes. Route records to deterministic output partitions, keep only a bounded number of writers open, and publish completed files atomically so retries do not expose partial output. Track counts and rejected records, and make restart checkpoints align with durable output commits.

**Mental walkthrough**

1. The reader owns a small input buffer and yields one record or chunk.
2. Validation separates accepted and rejected records with attributable diagnostics.
3. Stateful aggregation is bounded by key cardinality, a window, or spill partitions.
4. The writer rolls files by size, closes handles, and publishes a manifest or atomic rename only after success.
5. A retry resumes from a checkpoint or rewrites deterministic partitions without duplicating committed output.

**Tradeoffs and pitfalls**

A generator alone does not make sorting, exact distinct counting, or unrestricted group-by bounded. Those operations need external algorithms, partitioning, approximate structures, or a distributed engine. Partitioning also trades smaller working sets for extra I/O and skew risk.

**Source provenance**

- S005, S006, S002

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)
- [`02-python-file-pipelines-and-chunked-processing.md`](07-batch-processing-and-etl-elt/02-python-file-pipelines-and-chunked-processing.md)

### 5. How would you partition an iterator into bounded batches while preserving a final partial batch?

**Interview answer**

Consume at most `batch_size` items per iteration and emit the batch whenever it is non-empty. Do not calculate the source length, slice the source, or convert it to a list, because a general iterator may be one-shot or unbounded. Python 3.12+ provides `itertools.batched`, which lazily yields tuples and preserves a shorter final batch by default. In older versions, use `itertools.islice` in a small loop. Reject non-positive batch sizes, and decide whether the batch must be copied before downstream asynchronous work can retain it.

**Example**

```python
from itertools import islice

def batches(source, size):
    if size < 1:
        raise ValueError("size must be at least one")
    iterator = iter(source)
    while batch := tuple(islice(iterator, size)):
        yield batch

assert list(batches(range(7), 3)) == [(0, 1, 2), (3, 4, 5), (6,)]
```

**Tradeoffs and pitfalls**

The batch bounds application memory only if downstream releases each batch. A strict full-batch contract should reject the last partial batch rather than silently drop it; `itertools.batched(..., strict=True)` provides that behavior in Python 3.13+.

**Source provenance**

- S002

**Verification note**

- Reviewed against Python 3.14 [`itertools.batched`](https://docs.python.org/3.14/library/itertools.html#itertools.batched) on 2026-09-09. `batched` was added in 3.12 and its `strict` option in 3.13.

**Related curriculum**

- [`02-collections-iteration-generators-and-bounded-memory.md`](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

## Python memory and runtime

### 1. How does CPython allocate objects and manage references on its private heap?

**Interview answer**

In CPython, Python objects and internal data structures live in a private heap managed by the interpreter. Allocation APIs are layered: the raw domain is close to the system allocator, the memory domain serves interpreter-managed buffers, and the object domain serves Python objects and may use specialized small-object allocators. Every object includes runtime metadata such as its type and, for most objects, a reference count. Creating or storing a strong reference increments that count; releasing one decrements it, and reaching zero normally finalizes and deallocates the object immediately. This is a CPython implementation model, not a portable promise of the Python language, so application correctness must never depend on prompt destruction. Use context managers for deterministic release of files, sockets, and transactions.

**Tradeoffs and pitfalls**

Resident process memory need not fall when objects are freed: an allocator can retain arenas for reuse, and fragmentation or live objects can keep an arena allocated. Measure object retention separately from OS-visible RSS before calling behavior a leak.

**Related curriculum**

- [Python runtime, types, and Kotlin comparisons](02-python-for-data-engineering/01-python-runtime-types-and-kotlin-comparisons.md)
- [Testing, profiling, memory, and Python performance](02-python-for-data-engineering/08-testing-profiling-memory-and-python-performance.md)

**Source provenance**

- S005

**Verification note**

- CPython-specific allocation details were checked against the [Python 3.14 memory-management documentation](https://docs.python.org/3/c-api/memory.html) in 2026-09.

### 2. Why is cyclic garbage collection needed in addition to reference counting?

**Interview answer**

Reference counting reclaims an object when its strong-reference count reaches zero, but a dead cycle can keep every member's count above zero. For example, two unreachable objects that reference each other still each have an incoming reference. CPython's cyclic garbage collector supplements reference counting by tracing tracked container objects, finding unreachable cycles, and collecting them. The distinction matters operationally: most acyclic objects are reclaimed promptly, while cyclic cleanup is periodic and adds work. Neither mechanism is a resource-lifetime API; a `with` block should close external resources at a known boundary.

**Example**

```python
class Node:
    pass

left = Node()
right = Node()
left.peer = right
right.peer = left
del left, right  # reference counting alone cannot identify this dead cycle
```

**Related curriculum**

- [Testing, profiling, memory, and Python performance](02-python-for-data-engineering/08-testing-profiling-memory-and-python-performance.md)

**Source provenance**

- S005

**Verification note**

- The collector's role as a supplement to reference counting was checked against the [Python 3.14 `gc` documentation](https://docs.python.org/3/library/gc.html) in 2026-09.

## Python concurrency and async

### 1. What is the Global Interpreter Lock, how does it affect CPU-bound and I/O-bound code, and which workloads does it constrain?

**Interview answer**

In a normal GIL-enabled CPython build, the Global Interpreter Lock allows only one thread at a time to execute Python bytecode in a process. Threads can still overlap blocking I/O because the interpreter and many extensions release the GIL while waiting, so they work well for network and file concurrency. Pure-Python CPU-bound threads usually do not scale across cores; use processes, native code that releases the GIL, or a deliberately tested free-threaded build. The GIL does not make compound application operations atomic or remove the need for locks around shared invariants.

**Tradeoffs and pitfalls**

CPython has supported optional free-threaded builds since 3.13, but that is not the default execution mode and extension compatibility can cause the GIL to be enabled. State the interpreter/build assumption rather than claiming that Python threads can never execute in parallel.

**Related curriculum**

- [Threads, asyncio, processes, and parallel data work](02-python-for-data-engineering/07-threads-asyncio-processes-and-parallel-data-work.md)

**Source provenance**

- S005, S006

**Verification note**

- GIL and free-threaded-build behavior was checked against the [Python 3.14 `threading` documentation](https://docs.python.org/3/library/threading.html) and [free-threading guide](https://docs.python.org/3/howto/free-threading-python.html) in 2026-09.

### 2. How would you choose among threads, processes, and `asyncio` for a Python workload?

**Interview answer**

Choose from the workload and library boundary. Threads fit blocking I/O when the client libraries are synchronous and the task count is moderate; they share memory, so coordination is easy but races are possible. `asyncio` fits high-concurrency I/O when the full call path has non-blocking APIs; one event-loop thread can manage many waiting operations with low per-task overhead, but blocking work stalls the loop. Processes fit CPU-heavy Python because separate interpreters can use multiple cores, at the cost of startup, serialization, duplicated memory, and harder state sharing. Benchmark the actual unit of work, bound concurrency, propagate cancellation and errors, and define ownership of shared resources.

**Tradeoffs and pitfalls**

Do not choose `asyncio` merely because it is newer, or processes merely because input is large. Large data passed between processes can erase parallel gains through serialization and copying; partition by file or key and return compact results when possible.

**Related curriculum**

- [Threads, asyncio, processes, and parallel data work](02-python-for-data-engineering/07-threads-asyncio-processes-and-parallel-data-work.md)

**Source provenance**

- S005

**Verification note**

- The selection assumptions were checked against the [Python 3.14 `threading` documentation](https://docs.python.org/3/library/threading.html), [`multiprocessing` documentation](https://docs.python.org/3/library/multiprocessing.html), and [`asyncio` documentation](https://docs.python.org/3/library/asyncio.html) in 2026-09.

### 3. How do `async`, `await`, coroutines, and the event loop cooperate?

**Interview answer**

`async def` defines a coroutine function; calling it creates a coroutine object but does not by itself run it. A task schedules that coroutine on an event loop. The loop runs a task until it completes or reaches an `await` whose result is not ready, then runs another ready task. When the awaited I/O or future completes, the task becomes runnable and resumes after the `await`. This is cooperative concurrency: useful overlap occurs only when code yields control, so blocking I/O or long CPU loops inside a coroutine block every task on that loop.

**Example**

```python
import asyncio

async def fetch(name: str) -> str:
    await asyncio.sleep(0.01)  # stands in for non-blocking I/O
    return name

async def main() -> list[str]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(fetch(name)) for name in ("a", "b")]
    return [task.result() for task in tasks]

results = asyncio.run(main())
```

**Tradeoffs and pitfalls**

Keep strong references to independently created tasks, design cancellation-safe cleanup with `try/finally`, and use structured concurrency such as `TaskGroup` when sibling failures should cancel the group.

**Related curriculum**

- [Threads, asyncio, processes, and parallel data work](02-python-for-data-engineering/07-threads-asyncio-processes-and-parallel-data-work.md)

**Source provenance**

- S005

**Verification note**

- Coroutine scheduling and `TaskGroup` behavior was checked against the [Python 3.14 coroutines and tasks documentation](https://docs.python.org/3/library/asyncio-task.html) in 2026-09.

## Python typing, errors, and testing

### 1. What do type hints provide if Python does not enforce them at runtime?

**Interview answer**

Type hints are machine-readable contracts for people and tools: static checkers can catch inconsistent calls before execution, IDEs can navigate and complete code better, and API boundaries become explicit. Python normally stores annotations but does not validate arguments or return values, so untrusted JSON, CSV, and database rows still require runtime parsing and validation. Prefer types that express behavior and domain shape—such as `Protocol`, `TypedDict`, and precise unions—over pervasive `Any`. Treat hints like Kotlin compile-time types only as a limited analogy: Python's checker is optional, gradual typing permits untyped escape hatches, and runtime objects are unchanged unless a library explicitly inspects annotations.

**Tradeoffs and pitfalls**

Typing has the highest payoff at module and data boundaries. Overly clever generic types can cost more comprehension than they save; an accurate broad type is better than a precise-looking false contract.

**Related curriculum**

- [Functions, classes, dataclasses, protocols, and modules](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)
- [Type hints, validation, and untrusted data](02-python-for-data-engineering/05-type-hints-validation-and-untrusted-data.md)

**Source provenance**

- S005

**Verification note**

- Runtime non-enforcement was checked against the [Python 3.14 `typing` documentation](https://docs.python.org/3/library/typing.html) in 2026-09.

### 2. How do `try`, `except`, `else`, and `finally` divide error-handling responsibilities?

**Interview answer**

Put only the operation expected to fail in `try`; catch specific recoverable exception types in `except`; put success-only work in `else`; and put unconditional cleanup in `finally`. `else` prevents an unrelated error in success-path code from being mistaken for the protected failure. `finally` runs whether the block returns, succeeds, or propagates an exception, but resource-specific context managers are usually clearer. Catch at the layer that can add context or recover, and otherwise let the exception propagate.

**Example**

```python
def load_count(path):
    handle = open(path, encoding="utf-8")
    try:
        raw = handle.read()
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}") from exc
    else:
        return int(raw)
    finally:
        handle.close()
```

**Tradeoffs and pitfalls**

Avoid bare `except`, silent `pass`, returning from `finally`, and wrapping an exception without `raise ... from exc`; all can hide the original failure or traceback.

**Related curriculum**

- [Errors, context managers, and resource lifetime](02-python-for-data-engineering/04-errors-context-managers-and-resource-lifetime.md)

**Source provenance**

- S006

### 3. How should record-level exceptions be handled without hiding a systemic pipeline failure?

**Interview answer**

First classify failures. A known data defect in one independent record can be captured with the raw-record identity, stage, reason code, and exception chain, then sent to a bounded quarantine while good records continue. A systemic defect—bad schema, expired credential, unavailable dependency, invariant violation, or an excessive reject rate—must fail the batch or trip a threshold. Publish accepted output and reject evidence under one run identity, report counts and rates, redact sensitive values, and make replay idempotent. This preserves partial progress without turning `except Exception: continue` into silent data loss.

**Mental walkthrough**

1. Parse and validate one record at the narrowest boundary.
2. Convert only expected data exceptions into a structured rejection.
3. Propagate unexpected exceptions and enforce absolute/rate thresholds.
4. Atomically publish success only after count and reconciliation checks pass.

**Related curriculum**

- [Type hints, validation, and untrusted data](02-python-for-data-engineering/05-type-hints-validation-and-untrusted-data.md)
- [Validation, quarantine, and schema evolution](06-data-ingestion-and-source-integration/07-validation-quarantine-and-schema-evolution.md)

**Source provenance**

- S006

### 4. How would you test Python transformation code and its failure paths with `pytest`?

**Interview answer**

Keep the transformation as a deterministic function from explicit input to output, then test representative rows, boundaries, empty input, duplicates, missing values, and invariants. Use `@pytest.mark.parametrize` for input/output cases, fixtures for reusable resources, and `pytest.raises` with a specific exception and message match for failure contracts. Add integration tests at serialization or database boundaries, and reconcile counts or totals for pipeline-level correctness. Mock only nondeterministic external boundaries; excessive mocking can prove the implementation calls its collaborators without proving the transformation works.

**Example**

```python
import pytest

@pytest.mark.parametrize(
    ("raw", "expected"),
    [(" 42 ", 42), ("0", 0)],
)
def test_parse_count(raw, expected):
    assert parse_count(raw) == expected

def test_parse_count_rejects_negative():
    with pytest.raises(ValueError, match="non-negative"):
        parse_count("-1")
```

**Related curriculum**

- [Testing, profiling, memory, and Python performance](02-python-for-data-engineering/08-testing-profiling-memory-and-python-performance.md)
- [Unit, property, and SQL transformation testing](13-data-quality-contracts-and-testing/03-unit-property-and-sql-transformation-testing.md)

**Source provenance**

- S006

**Verification note**

- Test idioms were checked against the current pytest documentation for [parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html), [fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html), and [exception assertions](https://docs.pytest.org/en/stable/how-to/assert.html#assertions-about-expected-exceptions) on 2026-09-09.

### 5. How would you design an exception wrapper that preserves success, failure, and diagnostic information?

**Interview answer**

Use an explicit result type only where failure is expected data, especially in a batch that must retain per-record outcomes. Model success and failure as distinct variants so they cannot be populated simultaneously. A failure should carry a stable reason code and safe operational context such as record ID and stage; preserve the original exception through chaining or as an in-process cause for diagnostics. Keep tracebacks in internal telemetry, but do not serialize arbitrary exceptions or sensitive raw data into durable output. Unexpected programming or infrastructure errors should still propagate rather than becoming ordinary rejected records.

**Example**

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass(frozen=True)
class Success(Generic[T]):
    value: T

@dataclass(frozen=True)
class Failure:
    error_code: str
    detail: str
    cause: Exception | None = None
```

**Tradeoffs and pitfalls**

Do not replace exception chaining with a string-only message. Catch an error only where code can recover, classify it, or add meaningful context; otherwise let it propagate with its traceback intact.

**Related curriculum**

- [Errors, context managers, and resource lifetime](02-python-for-data-engineering/04-errors-context-managers-and-resource-lifetime.md)
- [Type hints, validation, and untrusted data](02-python-for-data-engineering/05-type-hints-validation-and-untrusted-data.md)

**Source provenance**

- S002

**Verification note**

- Explicit exception chaining and traceback preservation were checked against the current Python [`raise` statement documentation](https://docs.python.org/3/reference/simple_stmts.html#the-raise-statement) on 2026-09-09.

## Python algorithms and data transformations

### 1. How would you find consecutive runs in an unsorted collection efficiently?

**Interview answer**

If values fit in memory and duplicates do not matter, put them in a set. A value starts a run only when `value - 1` is absent; from each start, advance until the next value is missing. Every distinct value is visited at most a constant number of times, so expected time is `O(n)` and extra space is `O(n)`. If results must be ordered, sort the runs afterward. If memory is constrained, sort the input and scan instead: `O(n log n)` time but potentially external-sortable. Clarify whether duplicates, gaps, and integer-only input are allowed before coding.

**Example**

```python
def consecutive_runs(values: list[int]) -> list[tuple[int, int]]:
    unique = set(values)
    runs = []
    for start in unique:
        if start - 1 in unique:
            continue
        end = start
        while end + 1 in unique:
            end += 1
        runs.append((start, end))
    return sorted(runs)
```

**Related curriculum**

- [Collections, iteration, generators, and bounded memory](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

**Source provenance**

- S002

### 2. How would you implement and reason about an eviction policy in Python?

**Interview answer**

Start by naming the policy and invariant. For an LRU cache, a hash map gives `O(1)` lookup and an ordered structure tracks recency; each read or update moves the key to the most-recent end, and an insert over capacity removes the least-recent end. Define capacity in entries or bytes, whether updates change weight, and what happens at capacity zero. Production concerns include thread safety, expensive cleanup, TTL versus recency, cache stampedes, observability, and whether eviction loses authoritative data. Python's `OrderedDict` makes the mechanics clear; `functools.lru_cache` is preferable when its function-result cache semantics fit.

**Example**

```python
from collections import OrderedDict

class LruCache:
    def __init__(self, capacity: int):
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self.capacity = capacity
        self.items = OrderedDict()

    def get(self, key):
        value = self.items.pop(key)
        self.items[key] = value
        return value

    def put(self, key, value):
        self.items.pop(key, None)
        self.items[key] = value
        if len(self.items) > self.capacity:
            self.items.popitem(last=False)
```

**Related curriculum**

- [Collections, iteration, generators, and bounded memory](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

**Source provenance**

- S002

**Verification note**

- Ordered-map operations were checked against the [Python 3.14 `OrderedDict` documentation](https://docs.python.org/3/library/collections.html#ordereddict-objects) in 2026-09.

### 3. How would you build a hierarchy or file tree from flat parent-child or path records?

**Interview answer**

For parent-child records, first create one node per unique ID, then make a second pass to attach each node to its parent. That supports children appearing before parents and runs in `O(n)` expected time. Reject duplicate IDs, self-parenting, missing parents unless explicit placeholders are allowed, and cycles; determine roots explicitly rather than assuming the first row. For file paths, normalize separators and dot segments under a declared platform policy, reject traversal outside the root, and insert path components into a trie. Keep payload ownership separate from child links so repeated input can be handled idempotently.

**Tradeoffs and pitfalls**

A tree requires at most one parent per node. If multiple parents are legal, the result is a DAG and needs different traversal and cycle rules. Deep recursive traversal can hit Python's recursion limit, so use an explicit stack for untrusted depth.

**Related curriculum**

- [Collections, iteration, generators, and bounded memory](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)
- [DAGs, workflows, tasks, and dependency design](12-workflow-orchestration-and-transformation-management/01-dags-workflows-tasks-and-dependency-design.md)

**Source provenance**

- S002

### 4. How would you compute cumulative sums over an incoming sequence?

**Interview answer**

Maintain one running accumulator and emit it after each input, which is `O(n)` time and `O(1)` working memory beyond output. A generator keeps the operation streaming and applies backpressure naturally: it reads the next value only when the consumer asks. Define the numeric type, starting value, overflow or precision expectations, and missing-value policy. Python integers do not overflow, but floating-point sums can accumulate rounding error and fixed-width NumPy or database types can overflow.

**Example**

```python
from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")

def cumulative(values: Iterable[T], start: T) -> Iterator[T]:
    total = start
    for value in values:
        total += value
        yield total
```

For ordinary numeric iterables, `itertools.accumulate(values, initial=...)` already supplies this behavior; be clear whether the initial value itself should be emitted.

**Related curriculum**

- [Collections, iteration, generators, and bounded memory](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)

**Source provenance**

- S002

**Verification note**

- Standard-library behavior was checked against [`itertools.accumulate`](https://docs.python.org/3/library/itertools.html#itertools.accumulate) in Python 3.14 in 2026-09.

### 5. How would you implement reusable group-by aggregation over Python records without repeatedly scanning the input?

**Interview answer**

Make key extraction and accumulator behavior explicit, then update one accumulator per key in a single pass. A `dict` maps keys to mutable aggregation state; a finalization function converts that state to output. This is expected `O(n)` time and `O(k)` state for `k` groups. Reusability comes from separating `key(record)`, `update(state, record)`, and `finish(state)`, not from rescanning once per metric or group. Decide how missing keys, invalid measures, ordering, and empty groups behave, and use mergeable accumulator states if partial results may later be combined in parallel.

**Example**

```python
from collections import defaultdict

def totals_by(records, key, value):
    totals = defaultdict(float)
    for record in records:
        totals[key(record)] += value(record)
    return dict(totals)
```

**Tradeoffs and pitfalls**

High-cardinality keys make state unbounded. Spill partitions, use an external engine, or require sorted input when groups cannot fit in memory. Never rely on arbitrary group order as a correctness property.

**Related curriculum**

- [Python file pipelines and chunked processing](07-batch-processing-and-etl-elt/02-python-file-pipelines-and-chunked-processing.md)

**Source provenance**

- S002

### 6. How would you count null-like values when inputs contain more than one missing-value representation?

**Interview answer**

Define the missingness contract before counting. `None`, IEEE `NaN`, an empty string, whitespace, `"NULL"`, and a domain sentinel such as `-999` are not inherently equivalent. Normalize only the representations declared missing for that field and retain invalid-but-present values as a separate category. Be careful that `NaN != NaN`, truthiness confuses zero with missingness, and library sentinels such as `pd.NA` can have ambiguous boolean behavior. A scalar predicate with explicit branches makes the policy testable; then count in one pass and report missing counts by reason when the distinction affects quality work.

**Example**

```python
import math

def is_missing(value: object) -> bool:
    return value is None or (
        isinstance(value, float) and math.isnan(value)
    )

missing_count = sum(is_missing(value) for value in values)
```

Extend the predicate per schema rather than globally treating falsy values as null.

**Related curriculum**

- [Type hints, validation, and untrusted data](02-python-for-data-engineering/05-type-hints-validation-and-untrusted-data.md)
- [Data quality dimensions, requirements, and ownership](13-data-quality-contracts-and-testing/01-data-quality-dimensions-requirements-and-ownership.md)

**Source provenance**

- S002

### 7. How would you compute a running distinct count over an event stream?

**Interview answer**

For exact counts, maintain a set of canonical identities. For each event, normalize its key, add it to the set, and emit `len(seen)`; average update time is `O(1)`, but memory grows with distinct cardinality. Define whether the count is all-time, per partition, or windowed, and how late events and state recovery work. For a bounded time window, retain enough timestamped state to expire keys correctly; a plain set cannot handle repeated keys leaving the window. At very high cardinality, use an approximate mergeable sketch such as HyperLogLog when a stated error bound is acceptable.

**Example**

```python
def running_distinct(events):
    seen = set()
    for event in events:
        seen.add(event.user_id)
        yield len(seen)
```

**Tradeoffs and pitfalls**

In distributed processing, local sets do not produce a global distinct count without repartitioning or merging state. Checkpoint state and define key canonicalization so retries and formatting variants do not inflate the count.

**Related curriculum**

- [Stateful stream processing, checkpoints, and replay](10-messaging-streaming-and-change-data-capture/06-stateful-stream-processing-checkpoints-and-replay.md)

**Source provenance**

- S002

### 8. How would you parse a log line defensively and represent malformed input?

**Interview answer**

Use the parser for the declared format—JSON, CSV, or a documented grammar—rather than splitting on a convenient delimiter. Bound line size, decode under an explicit encoding policy, parse timestamps with timezone rules, validate required fields and types, and distinguish malformed syntax from schema-invalid content. Return either a typed record or a structured rejection containing line/source identity, stage, stable reason code, and a redacted excerpt. Unexpected I/O or programming failures should propagate. Track reject rates and fail the job when a threshold indicates systemic corruption.

**Example**

```python
import json
from dataclasses import dataclass

@dataclass(frozen=True)
class RejectedLine:
    line_number: int
    reason: str

def parse_json_line(raw: str, line_number: int):
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return RejectedLine(line_number, "invalid_json")
    if not isinstance(value, dict) or "event_id" not in value:
        return RejectedLine(line_number, "invalid_schema")
    return value
```

**Related curriculum**

- [Bytes, text, encodings, and record boundaries](04-data-storage-files-and-serialization/01-bytes-text-encodings-and-record-boundaries.md)
- [CSV, JSON, and JSON Lines](04-data-storage-files-and-serialization/02-csv-json-and-json-lines.md)

**Source provenance**

- S002

### 9. How would you merge overlapping time intervals correctly at boundary conditions?

**Interview answer**

First declare interval semantics. For closed intervals, `[a, b]` and `[b, c]` overlap; for half-open intervals, `[a, b)` and `[b, c)` merely touch. Validate `start <= end`, normalize time zones, sort by start then end, and scan once. If the next start overlaps the current interval under the chosen rule, extend the end to the maximum; otherwise emit the current interval and start another. Sorting costs `O(n log n)` and the scan is `O(n)`.

**Example**

```python
def merge_half_open(intervals):
    merged = []
    for start, end in sorted(intervals):
        if start > end:
            raise ValueError("start after end")
        if merged and start < merged[-1][1]:  # touching is not overlap
            old_start, old_end = merged[-1]
            merged[-1] = (old_start, max(old_end, end))
        else:
            merged.append((start, end))
    return merged
```

**Tradeoffs and pitfalls**

Whether empty intervals are retained and whether adjacency should coalesce are business rules, not implementation details. DST-local timestamps should be resolved before comparison.

**Related curriculum**

- [Window functions, time series, and analytical patterns](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

**Source provenance**

- S002

### 10. How would you compare two schema manifests and report compatible and breaking differences?

**Interview answer**

Parse both manifests into one canonical internal model keyed by full field path, with type, nullability, required/default status, and format-specific attributes. Diff added, removed, and changed fields, then classify each change under an explicit producer/consumer compatibility policy. Adding an optional field is often backward-compatible; removing a required field, narrowing a type, or making a nullable field required is often breaking—but the serialization format and reader behavior decide the real answer. Produce stable machine-readable findings with path, old/new definitions, severity, and rationale, plus a human summary. Validate duplicate paths and malformed schemas before comparison.

**Tradeoffs and pitfalls**

Text diff is insufficient because field order or formatting may be semantically irrelevant. Compatibility is directional: "new reader reads old data" and "old reader reads new data" are separate questions. References, unions, defaults, and logical types require format-aware resolution.

**Related curriculum**

- [Metadata, catalogs, schema, and partition evolution](04-data-storage-files-and-serialization/08-metadata-catalogs-schema-and-partition-evolution.md)
- [Schema, data, and consumer contracts](13-data-quality-contracts-and-testing/02-schema-data-and-consumer-contracts.md)

**Source provenance**

- S002

### 11. How would you reconcile two record streams when keys match but field values disagree?

**Interview answer**

Define each stream's grain and key uniqueness before comparing; duplicate keys are a separate cardinality defect. Canonicalize only agreed representations such as time zone, decimal scale, case, or null sentinels. Perform a full outer match by key and classify records as left-only, right-only, equal, or mismatched. For mismatches, emit field-level old/new values, applying tolerances only where the business contract permits them. Aggregate counts and important measures so a comparison bug cannot silently drop rows. Do not auto-pick a winner unless source authority and conflict rules are explicit.

**Tradeoffs and pitfalls**

An in-memory dictionary is simple when one side fits. If neither stream fits, partition both by a stable hash or externally sort both by key and merge them. Preserve run IDs and protected mismatch evidence so reconciliation is repeatable and auditable.

**Related curriculum**

- [Idempotency, deduplication, late data, and reconciliation](06-data-ingestion-and-source-integration/08-idempotency-deduplication-late-data-and-reconciliation.md)
- [Reconciliation, freshness, volume, and distribution checks](13-data-quality-contracts-and-testing/06-reconciliation-freshness-volume-and-distribution-checks.md)

**Source provenance**

- S002

### 12. How would you resolve dependencies while detecting missing inputs and cycles?

**Interview answer**

Represent dependencies as a directed graph, validate that every referenced node exists, and topologically sort it. With Kahn's algorithm, compute each node's in-degree, queue all zero-in-degree nodes, repeatedly emit one, and decrement its dependents. If fewer nodes are emitted than exist, the remaining subgraph contains a cycle. This runs in `O(V + E)` time and space. Return a deterministic order by using a stable or priority queue when reproducible plans matter, and report an actual cycle path if operators must diagnose it.

**Example**

```python
from collections import defaultdict, deque

def dependency_order(requires: dict[str, set[str]]) -> list[str]:
    nodes = set(requires)
    missing = set().union(*requires.values()) - nodes if requires else set()
    if missing:
        raise ValueError(f"missing dependencies: {sorted(missing)}")
    dependents = defaultdict(list)
    indegree = {node: len(deps) for node, deps in requires.items()}
    for node, deps in requires.items():
        for dep in deps:
            dependents[dep].append(node)
    ready = deque(node for node, degree in indegree.items() if degree == 0)
    order = []
    while ready:
        node = ready.popleft()
        order.append(node)
        for dependent in dependents[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if len(order) != len(nodes):
        raise ValueError("dependency cycle")
    return order
```

**Related curriculum**

- [DAGs, workflows, tasks, and dependency design](12-workflow-orchestration-and-transformation-management/01-dags-workflows-tasks-and-dependency-design.md)

**Source provenance**

- S002

### 13. How would you compose reusable column transformations while making failures attributable?

**Interview answer**

Represent each transformation as a named stage with declared input columns, output column, and callable. Validate the initial schema and dependency order, then apply stages in sequence to a new record or frame rather than hiding mutation. At the narrow boundary around each stage, add stage, column, and record/run identity while preserving the original exception chain. Expected record defects can become structured rejects; unexpected code or infrastructure failures should stop the operation. Keep stages deterministic when possible so they are independently testable, reusable, and safe to replay.

**Example**

```python
from collections.abc import Callable
from dataclasses import dataclass

@dataclass(frozen=True)
class Transform:
    name: str
    output: str
    apply: Callable[[dict], object]

def run(record: dict, stages: list[Transform]) -> dict:
    result = dict(record)
    for stage in stages:
        try:
            result[stage.output] = stage.apply(result)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"transform {stage.name!r} failed") from exc
    return result
```

**Tradeoffs and pitfalls**

Avoid row-wise Python callbacks in Pandas hot paths when vectorized expressions exist. For independent columns, a DAG is more accurate than a simple list; detect cycles and prevent two stages from silently owning the same output.

**Related curriculum**

- [Functions, classes, dataclasses, protocols, and modules](02-python-for-data-engineering/03-functions-classes-dataclasses-protocols-and-modules.md)
- [Python file pipelines and chunked processing](07-batch-processing-and-etl-elt/02-python-file-pipelines-and-chunked-processing.md)

**Source provenance**

- S002

**Verification note**

- Clause behavior was checked against the [Python 3.14 language reference for `try`](https://docs.python.org/3/reference/compound_stmts.html#the-try-statement) in 2026-09.

## Python packaging and configuration

### 1. How should a Python application obtain secrets and environment-specific configuration?

**Interview answer**

Keep configuration outside code and build artifacts. Read non-secret settings from an explicit configuration layer—commonly environment variables or a deployment-provided file—and obtain secrets from the platform's secret manager through short-lived identity when possible. Parse all raw strings once at startup into a typed settings object, validate required values and ranges, and fail fast with a useful message. Define precedence deliberately, such as command-line override over environment over a safe default. Never commit secrets, bake them into images, print them in logs, or silently use a production-dangerous default. Rotation should not require rebuilding the application; whether it requires restart depends on the secret client and operational design.

**Tradeoffs and pitfalls**

Environment variables are a delivery mechanism, not a secret store: they may be visible to process inspection, dumps, or accidental logging. Prefer a managed secret reference or mounted secret where the runtime supports it, and redact values from exceptions and telemetry.

**Related curriculum**

- [Environments, packaging, dependencies, and reproducibility](02-python-for-data-engineering/06-environments-packaging-dependencies-and-reproducibility.md)
- [Encryption, secrets, keys, and credential lifecycle](14-governance-security-privacy-and-data-lifecycle/04-encryption-secrets-keys-and-credential-lifecycle.md)

**Source provenance**

- S005

**Verification note**

- Python environment access was checked against the [Python 3.14 `os.environ` documentation](https://docs.python.org/3/library/os.html#os.environ) in 2026-09; secret storage and rotation remain deployment-platform concerns.

### 2. How do virtual environments, dependency pinning, and lock files support reproducible Python jobs?

**Interview answer**

A virtual environment isolates one job's installed distributions from other projects, but isolation alone does not make an environment reproducible. Project metadata should declare direct dependency ranges and the supported Python version. A generated lock file resolves direct and transitive dependencies to concrete artifacts for a target platform; hashes and a controlled package index further reduce supply-chain and drift risk. CI and production should install from that reviewed lock into a clean environment, while an automated process deliberately refreshes and retests it. Also pin the interpreter and relevant native/system libraries or use an immutable image, because the same Python packages can behave differently across runtimes and operating systems.

**Tradeoffs and pitfalls**

`pip freeze` captures everything installed, including accidental packages, and may be platform-specific. Prefer a declared-input-plus-generated-lock workflow. A lock is a repeatability snapshot, not proof of correctness or security; retain tests and vulnerability review.

**Related curriculum**

- [Environments, packaging, dependencies, and reproducibility](02-python-for-data-engineering/06-environments-packaging-dependencies-and-reproducibility.md)

**Source provenance**

- S006

**Verification note**

- Isolation and locking claims were checked against the Python Packaging User Guide on [virtual environments](https://packaging.python.org/en/latest/specifications/virtual-environments/), [requirements versus project dependencies](https://packaging.python.org/en/latest/discussions/install-requires-vs-requirements/), and the standardized [`pylock.toml` format](https://packaging.python.org/en/latest/specifications/pylock-toml/) in 2026-09. Lock-tool behavior remains tool-specific.

## NumPy and Pandas

### 1. Why do NumPy arrays and vectorized operations usually outperform Python lists and element-by-element loops for numeric work?

**Interview answer**

A Python list stores references to Python objects, so a numeric loop repeatedly dispatches bytecode, follows pointers, and handles dynamic types. A NumPy `ndarray` has a homogeneous dtype and a compact strided data buffer. Vectorized ufuncs move the loop into compiled code, amortize interpreter overhead, improve cache locality, and can use optimized native routines. That often makes numeric work faster and smaller, but it is not automatic: object dtype loses many benefits, temporary arrays consume memory, noncontiguous access hurts locality, and a vectorized expression that materializes a huge intermediate may be worse than chunking or a compiled loop.

**Tradeoffs and pitfalls**

Measure representative data with a profiler. "Vectorized" should mean the hot loop runs in optimized native array operations; `numpy.vectorize` is primarily a convenience wrapper and does not by itself provide that speedup.

**Related curriculum**

- [Testing, profiling, memory, and Python performance](02-python-for-data-engineering/08-testing-profiling-memory-and-python-performance.md)
- [Arrow and in-memory columnar data](04-data-storage-files-and-serialization/05-arrow-and-in-memory-columnar-data.md)

**Source provenance**

- S005, S006

**Verification note**

- Array layout was checked against the [NumPy array-object documentation](https://numpy.org/doc/stable/reference/arrays.html) and vectorized execution against the [NumPy broadcasting guide](https://numpy.org/doc/stable/user/basics.broadcasting.html) in 2026-09.

### 2. How do a Pandas `Series` and `DataFrame` differ?

**Interview answer**

A `Series` is a one-dimensional labeled array: each value has one index label and one dtype. A `DataFrame` is a two-dimensional labeled table whose columns are `Series` sharing a row index; different columns can have different dtypes. Selecting one column normally returns a `Series`, while selecting a list of columns returns a `DataFrame`. Both align operations by labels, not merely by physical position, which is powerful but can introduce missing values or reorder results when indexes differ. Choose a `Series` for one named vector and a `DataFrame` when records have multiple fields, while keeping explicit keys as columns when their business meaning should not be hidden in the index.

**Related curriculum**

- [Collections, iteration, generators, and bounded memory](02-python-for-data-engineering/02-collections-iteration-generators-and-bounded-memory.md)
- [Arrow and in-memory columnar data](04-data-storage-files-and-serialization/05-arrow-and-in-memory-columnar-data.md)

**Source provenance**

- S005

**Verification note**

- Definitions and current APIs were checked against the pandas 3.0 documentation for [`Series`](https://pandas.pydata.org/docs/reference/api/pandas.Series.html) and [`DataFrame`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) in 2026-09.

### 3. How should missing values be treated in Pandas when the correct choice depends on business meaning?

**Interview answer**

First distinguish meanings: unknown, not applicable, not yet observed, intentionally redacted, and source error are different states even if all arrive as a missing marker. Profile missingness by column, source, and time; normalize source sentinels such as empty strings or `-999`; and preserve a reason flag when the distinction matters. Then choose a rule per field: reject a required key, retain a nullable measure, impute only with a defensible model, forward-fill only when the domain says the prior value remains valid, or exclude from a calculation with an explicit denominator policy. Validate the output dtype and record counts because `NaN`, `NaT`, `None`, and `pd.NA` interact differently with dtypes and operations.

**Tradeoffs and pitfalls**

Blanket `dropna()` silently changes population and can bias results; blanket zero-fill converts "unknown" into a real measurement. Record the policy and test it against business invariants.

**Related curriculum**

- [Type hints, validation, and untrusted data](02-python-for-data-engineering/05-type-hints-validation-and-untrusted-data.md)
- [Data quality dimensions, requirements, and ownership](13-data-quality-contracts-and-testing/01-data-quality-dimensions-requirements-and-ownership.md)

**Source provenance**

- S005

**Verification note**

- Current missing-value behavior was checked against the [pandas missing-data guide](https://pandas.pydata.org/docs/user_guide/missing_data.html) in 2026-09.

### 4. When would you use Pandas `merge()`, `join()`, or `concat()`?

**Interview answer**

Use `merge` for database-style matching on named columns or indexes and make the expected cardinality explicit with `validate`. Use `DataFrame.join` mainly as convenient index-based joining, including joining several frames to one index. Use `concat` to stack or align whole objects along rows or columns; it does not perform relational key matching. Before a merge, assert key uniqueness at the intended grain and decide how unmatched rows should appear. Afterward, reconcile row counts and use `indicator=True` when diagnosing matches.

**Example**

```python
result = orders.merge(
    customers,
    on="customer_id",
    how="left",
    validate="many_to_one",
    indicator=True,
)
```

**Tradeoffs and pitfalls**

Duplicate keys can multiply rows. Also, pandas matches null keys to each other in `merge`, unlike usual SQL null-key semantics, so filter or reject null keys when that match is invalid.

**Related curriculum**

- [Joins, cardinality, and missing matches](03-sql-and-analytical-querying/03-joins-cardinality-and-missing-matches.md)

**Source provenance**

- S005

**Verification note**

- Selection criteria and null-key behavior were checked against pandas 3.0 documentation for [`merge`](https://pandas.pydata.org/docs/reference/api/pandas.merge.html), [`DataFrame.join`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.join.html), and [`concat`](https://pandas.pydata.org/docs/reference/api/pandas.concat.html) in 2026-09.

### 5. What makes a Python data-cleaning workflow reproducible rather than a one-off notebook procedure?

**Interview answer**

A reproducible cleaning workflow has versioned inputs or snapshots, explicit schemas and business rules, deterministic code, pinned runtime dependencies, and a callable entry point outside notebook cell state. Separate I/O from pure transformations; parameterize environment-specific paths; validate row counts, keys, nulls, and accepted domains; and publish output atomically with run metadata, code version, input identity, and reject evidence. Tests should cover representative and malformed records, while CI reruns them in a clean environment. A notebook can remain an exploration or presentation layer, but the production transformation should run from top to bottom without hidden variables, manual edits, or dependence on execution order.

**Tradeoffs and pitfalls**

Bit-for-bit reproducibility may also require stable ordering, fixed random seeds, pinned native libraries, and controlled time zones. Record where exact reproduction ends and semantic reconciliation begins.

**Related curriculum**

- [Environments, packaging, dependencies, and reproducibility](02-python-for-data-engineering/06-environments-packaging-dependencies-and-reproducibility.md)
- [Python file pipelines and chunked processing](07-batch-processing-and-etl-elt/02-python-file-pipelines-and-chunked-processing.md)

**Source provenance**

- S005

### 6. How does NumPy broadcasting combine arrays with compatible but different shapes?

**Interview answer**

NumPy compares shapes from the trailing dimensions. Two dimensions are compatible when they are equal or either one is `1`; missing leading dimensions behave as size `1`. The result uses the maximum size on each compatible axis, and the size-one operand is conceptually repeated without necessarily copying its data. For example, a `(100, 3)` matrix plus a `(3,)` vector produces `(100, 3)`. Incompatible dimensions raise `ValueError`. Broadcasting is concise and usually efficient, but always reason about the result shape first because two small inputs can imply a very large output or temporary.

**Example**

```python
import numpy as np

rows = np.array([[1, 2, 3], [4, 5, 6]])  # (2, 3)
offset = np.array([10, 20, 30])           # (3,)
adjusted = rows + offset                   # (2, 3)
```

**Related curriculum**

- [Testing, profiling, memory, and Python performance](02-python-for-data-engineering/08-testing-profiling-memory-and-python-performance.md)

**Source provenance**

- S006

**Verification note**

- Shape rules and the no-needless-copy qualification were checked against the [NumPy broadcasting guide](https://numpy.org/doc/stable/user/basics.broadcasting.html) in 2026-09.

### 7. Given orders by product and region, how would you return the top three products per region in Pandas?

**Interview answer**

First define the grain and ranking metric: if input rows are orders, aggregate revenue to one row per `(region, product)` before ranking. Then sort by region, descending revenue, and a stable tie-breaker such as product ID; select the first three rows per region. State the tie policy: exactly three rows requires a deterministic tie-breaker, while "include all ties" needs rank semantics and may return more than three. Validate that revenue has the intended currency and refund treatment before ranking.

**Example**

```python
top_three = (
    orders.groupby(["region", "product_id"], as_index=False, dropna=False)
          .agg(revenue=("revenue", "sum"))
          .sort_values(
              ["region", "revenue", "product_id"],
              ascending=[True, False, True],
          )
          .groupby("region", group_keys=False, dropna=False)
          .head(3)
)
```

**Related curriculum**

- [Aggregation, grouping, and set operations](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)
- [Window functions, time series, and analytical patterns](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

**Source provenance**

- S006

**Verification note**

- Current group-by operations were checked against the [pandas group-by guide](https://pandas.pydata.org/docs/user_guide/groupby.html) in 2026-09.

### 8. How would you normalize inconsistently formatted phone values while rejecting invalid records?

**Interview answer**

Treat normalization and validation as separate stages. Preserve the raw value and source, normalize Unicode and whitespace, parse with a region assumption supplied by the record or business context, and emit one canonical representation such as E.164 only if the number is valid under an authoritative numbering library and policy. Reject ambiguous country codes, impossible lengths, extensions that cannot be represented, and non-phone placeholders with stable reason codes. Do not write a universal regex: formatting and numbering plans vary. Track accepted, rejected, and missing counts, redact phone values in logs, and retain enough protected evidence for correction and replay.

**Example**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PhoneResult:
    normalized: str | None
    error_code: str | None

# The adapter should call a maintained numbering-plan library and return
# either an E.164 string or a stable rejection code.
```

**Related curriculum**

- [Type hints, validation, and untrusted data](02-python-for-data-engineering/05-type-hints-validation-and-untrusted-data.md)
- [Validation, quarantine, and schema evolution](06-data-ingestion-and-source-integration/07-validation-quarantine-and-schema-evolution.md)

**Source provenance**

- S006

## SQL filtering, aggregation, and set operations

### 1. How do `WHERE` and `HAVING` differ when filtering rows versus aggregate groups?

**Interview answer**

`WHERE` removes input rows before grouping and aggregation; `HAVING` removes groups after aggregates have been calculated. Put row predicates in `WHERE` both for meaning and to reduce the work entering the aggregate. Use `HAVING` when the condition depends on the group, such as `SUM(amount) > 1000`. A grouped column can appear in either clause, but `WHERE` is normally clearer when it is genuinely a row-level restriction.

**Example**

```sql
-- PostgreSQL; portable SQL.
SELECT customer_id, SUM(amount) AS paid_total
FROM payments
WHERE status = 'settled'
GROUP BY customer_id
HAVING SUM(amount) > 1000
ORDER BY customer_id;
```

**Tradeoffs and pitfalls**

Moving `status = 'settled'` into `HAVING` either is invalid when it is not grouped or changes the meaning if rewritten as an aggregate condition. The key question is whether a condition selects source rows or completed groups.

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

**Source provenance**

- S001

**Verification note**

- PostgreSQL 18/current documents `WHERE` before grouping and `HAVING` after grouping in [Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html).

### 2. Why do `COUNT(*)`, `COUNT(column)`, and `COUNT(DISTINCT column)` differ in the presence of `NULL`?

**Interview answer**

`COUNT(*)` counts input rows, including rows whose columns are all `NULL`. `COUNT(column)` counts only rows where that expression is non-null. `COUNT(DISTINCT column)` first considers distinct non-null values and counts those. The choice must follow the metric's grain: row count, known-value count, or unique known-value count. If missingness matters, report it separately rather than silently treating `NULL` as a value.

**Example**

```sql
-- PostgreSQL; portable semantics.
SELECT
    COUNT(*) AS rows_seen,
    COUNT(email) AS rows_with_email,
    COUNT(DISTINCT email) AS distinct_known_emails,
    COUNT(*) - COUNT(email) AS missing_emails
FROM users;
```

**Related curriculum**

- [`01-relations-sets-bags-keys-and-null.md`](03-sql-and-analytical-querying/01-relations-sets-bags-keys-and-null.md)
- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

**Source provenance**

- S001

**Verification note**

- PostgreSQL 18/current defines `count(*)` as the number of input rows and `count(any)` as the number whose expression is non-null in [Aggregate Functions](https://www.postgresql.org/docs/current/functions-aggregate.html).

### 3. How would you return duplicate email values with their occurrence counts in deterministic order?

**Interview answer**

Group at the exact duplicate key, retain only groups with more than one row, and add an explicit total ordering. First decide whether normalization such as trimming or lowercasing belongs in the business definition. Grouping on a transformed value can find logical duplicates, but preserve the original values elsewhere if remediation needs them.

**Example**

```sql
-- PostgreSQL; lower() is portable, expression-index details are not.
SELECT lower(trim(email)) AS normalized_email,
       COUNT(*) AS occurrence_count
FROM users
WHERE email IS NOT NULL
GROUP BY lower(trim(email))
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC, normalized_email ASC;
```

**Tradeoffs and pitfalls**

An `ORDER BY` on count alone is not deterministic when counts tie. Whether case, surrounding whitespace, Unicode normalization, or provider-specific aliases are equivalent is a data-contract decision, not merely a SQL trick.

**Source provenance**

- S001

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

### 4. How would you compute spending by account status using grouped and conditional aggregation?

**Interview answer**

Choose the output grain first. For one row per account status, group by status and sum the qualifying monetary rows. For multiple status measures on one row, use conditional aggregation. PostgreSQL's `FILTER` clause is especially readable; `SUM(CASE WHEN ... THEN amount ELSE 0 END)` is the more widely portable form. Define treatment of refunds, unsettled charges, missing statuses, and empty groups explicitly.

**Example**

```sql
-- PostgreSQL.
SELECT account_id,
       COALESCE(SUM(amount) FILTER (WHERE status = 'settled'), 0) AS settled_spend,
       COALESCE(SUM(amount) FILTER (WHERE status = 'pending'), 0) AS pending_spend
FROM payments
GROUP BY account_id
ORDER BY account_id;
```

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

**Source provenance**

- S002

**Verification note**

- PostgreSQL's aggregate `FILTER` syntax is specified in [Aggregate Expressions](https://www.postgresql.org/docs/current/sql-expressions.html#SYNTAX-AGGREGATES).

### 5. How would you identify power users from session-activity thresholds?

**Interview answer**

Translate "power user" into a stable contract: observation window, event or session grain, qualifying activity, distinctness, and threshold. Filter qualifying source rows, aggregate once per user, then apply the threshold in `HAVING`. Count sessions only if session identifiers are trustworthy; otherwise define sessionization before this query.

**Example**

```sql
-- PostgreSQL. Parameters make the half-open reporting window explicit.
SELECT user_id,
       COUNT(DISTINCT session_id) AS session_count,
       SUM(active_seconds) AS active_seconds
FROM sessions
WHERE started_at >= :window_start
  AND started_at <  :window_end
GROUP BY user_id
HAVING COUNT(DISTINCT session_id) >= 10
   AND SUM(active_seconds) >= 3600
ORDER BY active_seconds DESC, user_id;
```

**Tradeoffs and pitfalls**

Do not count event rows as sessions, and do not use an inclusive upper timestamp bound for adjacent windows. Late-arriving sessions may require a maturity delay or recomputation policy.

**Source provenance**

- S002

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

### 6. How would you calculate a daily rate when the numerator and denominator require different filters?

**Interview answer**

Aggregate both populations at the same day grain, express each condition independently, and divide only after aggregation. In PostgreSQL, aggregate `FILTER` avoids accidentally restricting the denominator in `WHERE`. Cast to a non-integer type and protect a zero denominator with `NULLIF`; returning `NULL` usually communicates "undefined" better than inventing zero.

**Example**

```sql
-- PostgreSQL.
SELECT occurred_at::date AS activity_date,
       COUNT(*) FILTER (WHERE is_eligible AND outcome = 'success')::numeric
       / NULLIF(COUNT(*) FILTER (WHERE is_eligible), 0) AS success_rate
FROM attempts
WHERE occurred_at >= :start_at
  AND occurred_at <  :end_at
GROUP BY occurred_at::date
ORDER BY activity_date;
```

**Tradeoffs and pitfalls**

The example assumes the stored timestamp is already in the reporting zone. For `timestamptz`, derive the business date in an explicit named zone before grouping.

**Source provenance**

- S002

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)
- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

### 7. How would you compute each bucket's fraction of all API calls without integer-division errors?

**Interview answer**

First count calls per bucket, then divide each count by the total of those counts. A window aggregate over grouped results avoids a second scan. Make at least one operand a decimal type and use `NULLIF` if an empty input can reach the division. Confirm whether "all calls" means the filtered report population or the unfiltered table.

**Example**

```sql
-- PostgreSQL.
WITH bucket_counts AS (
    SELECT status_class, COUNT(*) AS call_count
    FROM api_calls
    WHERE called_at >= :start_at AND called_at < :end_at
    GROUP BY status_class
)
SELECT status_class,
       call_count,
       call_count::numeric / NULLIF(SUM(call_count) OVER (), 0) AS call_fraction
FROM bucket_counts
ORDER BY status_class;
```

**Source provenance**

- S002

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)
- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

### 8. How would you measure active-user penetration while avoiding duplicate-user inflation?

**Interview answer**

Define the denominator population and the activity window, then reduce both numerator and denominator to one row per user before counting. Event joins are dangerous because a user with many events can be counted many times. A semi-join via `EXISTS`, or separate distinct-user sets, preserves user grain. Decide whether ineligible, deleted, or newly registered users belong in the denominator.

**Example**

```sql
-- PostgreSQL; portable SQL.
SELECT COUNT(*) FILTER (
           WHERE EXISTS (
               SELECT 1
               FROM events e
               WHERE e.user_id = u.user_id
                 AND e.occurred_at >= :start_at
                 AND e.occurred_at <  :end_at
           )
       )::numeric / NULLIF(COUNT(*), 0) AS active_user_penetration
FROM users u
WHERE u.is_eligible;
```

**Source provenance**

- S002

**Related curriculum**

- [`03-joins-cardinality-and-missing-matches.md`](03-sql-and-analytical-querying/03-joins-cardinality-and-missing-matches.md)
- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

### 9. When do `DISTINCT` and `GROUP BY` express the same result, and when do they not?

**Interview answer**

`SELECT DISTINCT a, b` and `SELECT a, b GROUP BY a, b` express the same duplicate-eliminated projection when there are no aggregates or grouping extensions. `GROUP BY` additionally defines groups so aggregates, `HAVING`, grouping sets, rollups, and cubes can operate. `DISTINCT` applies to the final selected expressions; `DISTINCT ON` is a PostgreSQL-specific row-selection feature with ordering rules, not ordinary SQL `DISTINCT`.

**Example**

```sql
-- These two are equivalent for their result values.
SELECT DISTINCT country, plan FROM accounts;

SELECT country, plan
FROM accounts
GROUP BY country, plan;
```

**Tradeoffs and pitfalls**

Choose based on intent, not an assumed performance difference: use `DISTINCT` for duplicate elimination and `GROUP BY` for aggregation. Neither promises output order without `ORDER BY`.

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

**Source provenance**

- S002

**Verification note**

- PostgreSQL 18/current notes that grouping without aggregates can calculate the same distinct values in [Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html), while final duplicate elimination is described in [`SELECT`](https://www.postgresql.org/docs/current/sql-select.html#SQL-DISTINCT).

### 10. How do `UNION`, `UNION ALL`, `INTERSECT`, and `EXCEPT` differ in semantics and duplicate handling?

**Interview answer**

All four combine union-compatible query results: the same number of columns with compatible corresponding types. `UNION ALL` concatenates both bags and preserves duplicates. `UNION` returns the union with duplicates removed. `INTERSECT` returns rows present in both inputs, and `EXCEPT` returns rows from the left input absent from the right; both remove duplicates unless `ALL` is specified. Set operations do not guarantee output order.

**Tradeoffs and pitfalls**

Prefer `UNION ALL` when deduplication is not required because duplicate removal adds work and may conceal an upstream grain bug. Parenthesize mixed operations: PostgreSQL binds `INTERSECT` more tightly, while `UNION` and `EXCEPT` associate left-to-right.

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

**Source provenance**

- S002

**Verification note**

- Semantics, compatibility, duplicate handling, and precedence are documented in PostgreSQL 18/current [Combining Queries](https://www.postgresql.org/docs/current/queries-union.html).

### 11. How would you pivot experiment conversions or status values using conditional aggregation?

**Interview answer**

Use one output group per reporting entity and one filtered aggregate per known category. For conversion rates, keep assignment grain and conversion grain explicit so repeated events do not inflate participants. Static conditional aggregation is portable and reviewable; a dynamic pivot is appropriate only when the output schema is intentionally data-driven and its consumers can handle changing columns.

**Example**

```sql
-- PostgreSQL. assignments has one row per experiment and user.
SELECT experiment_id,
       COUNT(*) FILTER (WHERE variant = 'control') AS control_users,
       COUNT(*) FILTER (WHERE variant = 'treatment') AS treatment_users,
       COUNT(*) FILTER (WHERE variant = 'control' AND converted) AS control_converters,
       COUNT(*) FILTER (WHERE variant = 'treatment' AND converted) AS treatment_converters
FROM assignments
GROUP BY experiment_id
ORDER BY experiment_id;
```

**Tradeoffs and pitfalls**

Joining raw conversions directly to assignments creates one-to-many multiplication. Pre-aggregate conversions to one row per experiment-user or use `EXISTS` before pivoting.

**Source provenance**

- S002

**Related curriculum**

- [`04-aggregation-grouping-and-set-operations.md`](03-sql-and-analytical-querying/04-aggregation-grouping-and-set-operations.md)

### 12. How would you reconcile two churn queries that disagree because their filters and distinct-count semantics differ?

**Interview answer**

Do not compare only the final rates. Write down the metric contract—entity grain, eligible population, observation and outcome windows, time zone, churn event, reactivation policy, and `NULL` policy—then materialize each query's intermediate user-level classification. Full-join those classifications by stable user key and label disagreements such as denominator-only, numerator-only, duplicate inflation, or boundary mismatch. Reconcile counts at every stage before choosing a canonical definition.

**Mental walkthrough**

1. Freeze the same source snapshot and parameters for both queries.
2. Produce one row per user with eligibility and churn flags from each implementation.
3. Compare set differences and representative records, then trace the first stage where counts diverge.
4. Turn the agreed contract and edge cases into tests.

**Tradeoffs and pitfalls**

Adding `DISTINCT` to make totals agree can hide an incorrect join. Fix the grain or join relationship and retain diagnostics for late data, missing keys, and date boundaries.

**Source provenance**

- S019

**Related curriculum**

- [`03-joins-cardinality-and-missing-matches.md`](03-sql-and-analytical-querying/03-joins-cardinality-and-missing-matches.md)
- [`03-unit-property-and-sql-transformation-testing.md`](13-data-quality-contracts-and-testing/03-unit-property-and-sql-transformation-testing.md)

## SQL joins and subqueries

### 1. How can a predicate on the right side of a `LEFT JOIN` accidentally turn it into inner-join behavior?

**Interview answer**

A `LEFT JOIN` preserves an unmatched left row by producing `NULL` for every right-side column. A later `WHERE right_col = value` evaluates to unknown for that synthetic row, so `WHERE` removes it. Put the right-table qualification in `ON` when it controls which right rows may match while preserving every left row. Keep it in `WHERE` only when removing unmatched rows is intended.

**Example**

```sql
-- PostgreSQL; portable SQL.
SELECT c.customer_id, o.order_id
FROM customers c
LEFT JOIN orders o
  ON o.customer_id = c.customer_id
 AND o.status = 'open';
```

**Tradeoffs and pitfalls**

`WHERE o.status = 'open' OR o.order_id IS NULL` is not generally equivalent: a customer with only closed orders has matched rows, but none passes the filter, so the customer disappears. Predicate placement must reflect match semantics.

**Related curriculum**

- [`03-joins-cardinality-and-missing-matches.md`](03-sql-and-analytical-querying/03-joins-cardinality-and-missing-matches.md)

**Source provenance**

- S001

**Verification note**

- PostgreSQL 18/current explains that `ON` is processed before outer-join unmatched rows are added, whereas `WHERE` is applied afterward, in [Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html#QUERIES-FROM).

### 2. When can a correlated subquery become a scalability problem compared with a join or pre-aggregation?

**Interview answer**

A correlated subquery refers to the current outer row. It becomes risky when the plan executes substantial inner work once per outer row, especially with many outer rows, poor indexes, or repeated aggregation. It is not automatically slow: PostgreSQL can transform some subqueries or use efficient parameterized index scans. Inspect the actual plan and `loops`; if repeated work dominates, pre-aggregate once and join, or use a semi-join such as `EXISTS` when only existence matters.

**Example**

```sql
-- PostgreSQL; pre-aggregate once instead of summing per customer.
WITH order_totals AS (
    SELECT customer_id, SUM(amount) AS total_amount
    FROM orders
    GROUP BY customer_id
)
SELECT c.customer_id, COALESCE(o.total_amount, 0) AS total_amount
FROM customers c
LEFT JOIN order_totals o USING (customer_id);
```

**Tradeoffs and pitfalls**

A rewrite can change cardinality or `NULL` behavior. Verify results first, then compare `EXPLAIN (ANALYZE, BUFFERS)` on realistic data rather than assuming one syntax forces one algorithm.

**Related curriculum**

- [`05-subqueries-common-table-expressions-and-recursion.md`](03-sql-and-analytical-querying/05-subqueries-common-table-expressions-and-recursion.md)
- [`08-query-plans-indexes-statistics-and-optimization.md`](03-sql-and-analytical-querying/08-query-plans-indexes-statistics-and-optimization.md)

**Source provenance**

- S001

**Verification note**

- PostgreSQL shows parameterized nested-loop and subplan behavior in [Using `EXPLAIN`](https://www.postgresql.org/docs/current/using-explain.html); subquery truth semantics are in [Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html).

### 3. How would you implement a recommendation query using joins, anti-joins, or `EXISTS`?

**Interview answer**

Start by declaring the recommendation grain, for example one candidate item per user. Generate candidates from a meaningful relationship, score or aggregate them at that grain, then exclude items the user already owns with `NOT EXISTS`. A semi- or anti-join expresses membership without multiplying output rows. Use a stable tie-breaker so a top-N result is reproducible.

**Example**

```sql
-- PostgreSQL: recommend products bought by similar-category peers,
-- excluding products the target user already bought.
WITH target_categories AS (
    SELECT DISTINCT category_id
    FROM purchases
    WHERE user_id = :user_id
)
SELECT p.product_id, COUNT(*) AS peer_purchases
FROM target_categories tc
JOIN purchases p USING (category_id)
WHERE p.user_id <> :user_id
  AND NOT EXISTS (
      SELECT 1
      FROM purchases owned
      WHERE owned.user_id = :user_id
        AND owned.product_id = p.product_id
  )
GROUP BY p.product_id
ORDER BY peer_purchases DESC, p.product_id
LIMIT 20;
```

**Tradeoffs and pitfalls**

`NOT IN (subquery)` can produce no true matches when its result contains `NULL`; `NOT EXISTS` is usually safer. Production recommenders also need eligibility, freshness, diversity, and leakage rules that are outside this relational candidate-generation example.

**Related curriculum**

- [`03-joins-cardinality-and-missing-matches.md`](03-sql-and-analytical-querying/03-joins-cardinality-and-missing-matches.md)
- [`05-subqueries-common-table-expressions-and-recursion.md`](03-sql-and-analytical-querying/05-subqueries-common-table-expressions-and-recursion.md)

**Source provenance**

- S002

**Verification note**

- PostgreSQL documents `EXISTS`, `IN`, `NOT IN`, and their `NULL` behavior in [Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html).

### 4. How should SQL joins treat nullable keys when `NULL` represents an unknown value?

**Interview answer**

Under SQL three-valued logic, `NULL = NULL` is unknown, not true, so a normal equality join does not match two missing keys. That is usually correct when `NULL` means "identity unknown": matching all unknowns would invent relationships and can create a many-to-many explosion. If the business contract deliberately treats two nulls as the same category, say so and use `IS NOT DISTINCT FROM`; do not casually replace `NULL` with a sentinel that might collide with real data.

**Example**

```sql
-- PostgreSQL; IS NOT DISTINCT FROM supplies null-safe equality.
SELECT a.record_id, b.record_id
FROM source_a a
JOIN source_b b
  ON a.external_key IS NOT DISTINCT FROM b.external_key;
```

**Tradeoffs and pitfalls**

Null-safe equality is appropriate for value comparison, not automatically for entity identity. Prefer non-null stable keys, and measure missing-key rates before deciding how unmatched records should flow.

**Related curriculum**

- [`01-relations-sets-bags-keys-and-null.md`](03-sql-and-analytical-querying/01-relations-sets-bags-keys-and-null.md)
- [`03-joins-cardinality-and-missing-matches.md`](03-sql-and-analytical-querying/03-joins-cardinality-and-missing-matches.md)

**Source provenance**

- S002

**Verification note**

- PostgreSQL's ordinary comparison and null-safe predicates are documented in [Comparison Functions and Operators](https://www.postgresql.org/docs/current/functions-comparison.html).

### 5. How would you detect and prevent silent metric inflation caused by joining to a non-unique dimension key?

**Interview answer**

State the expected relationship and grain before joining: if facts are many-to-one with a dimension, the dimension join key must be unique for the relevant effective-time rule. Compare fact row counts and additive control totals before and after the join, profile dimension key counts, and isolate keys with `COUNT(*) > 1`. Prevent recurrence with a unique constraint when the model permits it, or resolve multiple versions explicitly with effective dates or deterministic deduplication before the join.

**Example**

```sql
-- PostgreSQL: expose violations before joining.
SELECT customer_key, COUNT(*) AS dimension_rows
FROM dim_customer
GROUP BY customer_key
HAVING COUNT(*) > 1
ORDER BY dimension_rows DESC, customer_key;
```

**Tradeoffs and pitfalls**

`SUM(DISTINCT fact_amount)` is not a repair: two valid facts can share the same amount. Aggregate or constrain at the relationship boundary. For a Type 2 dimension, join on business key plus the fact timestamp's effective interval and verify intervals do not overlap.

**Source provenance**

- S019

**Related curriculum**

- [`03-joins-cardinality-and-missing-matches.md`](03-sql-and-analytical-querying/03-joins-cardinality-and-missing-matches.md)
- [`02-relational-modeling-normalization-and-integrity.md`](05-data-modeling-and-business-semantics/02-relational-modeling-normalization-and-integrity.md)

## SQL window functions and analytical patterns

### 1. How would you calculate first-day retention from event records?

**Interview answer**

Define day zero and retention first. A common contract assigns each user to the date of their first qualifying event, then marks them retained if they have at least one qualifying event on the next calendar date in the reporting zone. Reduce events to distinct user-dates before joining, so repeated events do not inflate users. Report retained users divided by cohort users, with a policy for cohorts whose day-one observation window is incomplete.

**Example**

```sql
-- PostgreSQL. event_date is assumed already derived in the business zone.
WITH user_days AS (
    SELECT DISTINCT user_id, event_date FROM activity
), cohorts AS (
    SELECT user_id, MIN(event_date) AS cohort_date
    FROM user_days
    GROUP BY user_id
)
SELECT c.cohort_date,
       COUNT(*) AS cohort_users,
       COUNT(d.user_id) AS retained_users,
       COUNT(d.user_id)::numeric / NULLIF(COUNT(*), 0) AS day_1_retention
FROM cohorts c
LEFT JOIN user_days d
  ON d.user_id = c.user_id
 AND d.event_date = c.cohort_date + 1
GROUP BY c.cohort_date
ORDER BY c.cohort_date;
```

**Source provenance**

- S002, S009

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

### 2. How would you deduplicate records while retaining the latest row under a deterministic tie-breaker?

**Interview answer**

Define the duplicate key, order candidates newest first, and add a unique final tie-breaker such as ingestion sequence or record ID. Use `ROW_NUMBER()` per duplicate key and retain rank one. Without a total order, two rows sharing the same business timestamp can be selected nondeterministically. Also decide whether this is query-time presentation or a controlled physical deletion with audit and retry guarantees.

**Example**

```sql
-- PostgreSQL; portable window syntax.
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (
               PARTITION BY natural_key
               ORDER BY updated_at DESC, ingested_at DESC, record_id DESC
           ) AS rn
    FROM raw_records r
)
SELECT *
FROM ranked
WHERE rn = 1;
```

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

**Source provenance**

- S002

**Verification note**

- PostgreSQL defines `row_number` and ordering peers in [Window Functions](https://www.postgresql.org/docs/current/functions-window.html).

### 3. How would you calculate a rolling average with an explicit window frame?

**Interview answer**

Partition by the independent series, order by the time key, and state whether the window means a fixed number of rows or a real time interval. `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` is a seven-observation average; it is not necessarily seven calendar days if dates are missing or duplicated. For a seven-day time range in PostgreSQL, aggregate to one row per day and use an interval-based `RANGE` frame.

**Example**

```sql
-- PostgreSQL; daily_sales has one row per account and calendar date.
SELECT account_id, sales_date, amount,
       AVG(amount) OVER (
           PARTITION BY account_id
           ORDER BY sales_date
           RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
       ) AS trailing_7_day_avg
FROM daily_sales;
```

**Tradeoffs and pitfalls**

Specify whether absent dates contribute no observation or a zero; create a date spine when zero-filled calendar days are required. Add a deterministic order for `ROWS` frames when timestamps can tie.

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

**Source provenance**

- S002

**Verification note**

- PostgreSQL 18/current frame modes and offset rules are documented in [Window Function Calls](https://www.postgresql.org/docs/current/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS).

### 4. How would you find the longest consecutive activity streak with a gaps-and-islands technique?

**Interview answer**

First collapse activity to one row per user-date. Order those dates per user and subtract the row number from each date; consecutive dates then share the same shifted value, which identifies an island. Aggregate each island for its start, end, and length, then rank islands per user with a deterministic tie-breaker.

**Example**

```sql
-- PostgreSQL.
WITH user_days AS (
    SELECT DISTINCT user_id, occurred_at::date AS activity_date
    FROM events
), marked AS (
    SELECT user_id, activity_date,
           activity_date - ROW_NUMBER() OVER (
               PARTITION BY user_id ORDER BY activity_date
           )::integer AS island_key
    FROM user_days
), streaks AS (
    SELECT user_id, MIN(activity_date) AS streak_start,
           MAX(activity_date) AS streak_end, COUNT(*) AS streak_days
    FROM marked
    GROUP BY user_id, island_key
), ranked AS (
    SELECT streaks.*,
           ROW_NUMBER() OVER (
               PARTITION BY user_id
               ORDER BY streak_days DESC, streak_end DESC, streak_start DESC
           ) AS rn
    FROM streaks
)
SELECT user_id, streak_start, streak_end, streak_days
FROM ranked
WHERE rn = 1;
```

**Tradeoffs and pitfalls**

Consecutive must be a business definition: calendar days, business days, or expected event intervals require different adjacency logic and an explicit reporting time zone.

**Source provenance**

- S002, S009

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

### 5. How would you compare today's top service with the previous day's winner using window functions?

**Interview answer**

Aggregate to one row per day-service, rank services within each day using a declared tie policy, retain one daily winner, then use `LAG` across winner rows ordered by day. This separates two different windows: ranking within a day and comparing across days. Add a deterministic service tie-breaker, or return all co-winners if ties are meaningful.

**Example**

```sql
-- PostgreSQL.
WITH daily AS (
    SELECT event_date, service_id, COUNT(*) AS request_count
    FROM requests
    GROUP BY event_date, service_id
), ranked AS (
    SELECT daily.*,
           ROW_NUMBER() OVER (
               PARTITION BY event_date
               ORDER BY request_count DESC, service_id
           ) AS rn
    FROM daily
), winners AS (
    SELECT event_date, service_id, request_count
    FROM ranked
    WHERE rn = 1
)
SELECT *,
       LAG(service_id) OVER (ORDER BY event_date) AS previous_winner
FROM winners
ORDER BY event_date;
```

**Tradeoffs and pitfalls**

`LAG` means previous available winner row, not necessarily previous calendar day. Join to a date spine if missing dates must remain visible.

**Source provenance**

- S002

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

### 6. How would you calculate cumulative sales per customer while preserving row-level detail?

**Interview answer**

Use `SUM` as a window aggregate rather than a grouped aggregate: partition by customer, order transactions chronologically, and specify a frame from the partition start through the current row. Include a unique tie-breaker and use `ROWS` when every transaction should advance the running total independently.

**Example**

```sql
-- PostgreSQL; portable window syntax.
SELECT customer_id, sold_at, sale_id, amount,
       SUM(amount) OVER (
           PARTITION BY customer_id
           ORDER BY sold_at, sale_id
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS cumulative_sales
FROM sales
ORDER BY customer_id, sold_at, sale_id;
```

**Tradeoffs and pitfalls**

The default PostgreSQL frame with `ORDER BY` is peer-aware `RANGE`, so tied order values may advance together. An explicit `ROWS` frame plus total order makes transaction-by-transaction behavior clear.

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

**Source provenance**

- S002

**Verification note**

- PostgreSQL explains aggregate window functions and the default frame in [Window Functions](https://www.postgresql.org/docs/current/functions-window.html).

### 7. How would you calculate monthly cohort retention with stable cohort definitions?

**Interview answer**

Assign each user exactly once to a cohort using a durable event such as first activation, derive one row per user-active-month, then calculate integer month age from cohort month. Count distinct retained users at each cohort and age, and divide by the fixed cohort size. Freeze the reporting time zone, qualifying events, reactivation rule, and incomplete-period policy so reruns do not move users between cohorts.

**Example**

```sql
-- PostgreSQL. activity_month and cohort_month are month-start dates.
WITH user_months AS (
    SELECT DISTINCT user_id,
           date_trunc('month', occurred_at AT TIME ZONE 'America/Denver')::date
               AS activity_month
    FROM activity
), cohorts AS (
    SELECT user_id, MIN(activity_month) AS cohort_month
    FROM user_months
    GROUP BY user_id
), retained AS (
    SELECT c.cohort_month, u.activity_month, u.user_id,
           (EXTRACT(YEAR FROM age(u.activity_month, c.cohort_month)) * 12
            + EXTRACT(MONTH FROM age(u.activity_month, c.cohort_month)))::integer
               AS month_number
    FROM cohorts c
    JOIN user_months u USING (user_id)
), sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_users
    FROM cohorts
    GROUP BY cohort_month
)
SELECT r.cohort_month, r.month_number,
       COUNT(*) AS retained_users, s.cohort_users,
       COUNT(*)::numeric / s.cohort_users AS retention_rate
FROM retained r
JOIN sizes s USING (cohort_month)
GROUP BY r.cohort_month, r.month_number, s.cohort_users
ORDER BY r.cohort_month, r.month_number;
```

**Source provenance**

- S002

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

### 8. What alternatives would you test when a large `ROW_NUMBER` deduplication spills to disk?

**Interview answer**

Confirm the spill in `EXPLAIN (ANALYZE, BUFFERS)` and preserve the exact "latest row" contract before changing syntax. Reduce rows and columns before sorting, provide an index ordered by `(dedup_key, recency DESC, tie_breaker DESC)`, and test PostgreSQL `DISTINCT ON` with the same total order. For recurring workloads, deduplicate incrementally at ingestion or maintain a current-state table. Increasing `work_mem` can help, but it is per operation and concurrent queries can multiply memory demand.

**Example**

```sql
-- PostgreSQL-specific DISTINCT ON alternative.
SELECT DISTINCT ON (natural_key) *
FROM records
WHERE ingested_at >= :relevant_start
ORDER BY natural_key, updated_at DESC, record_id DESC;
```

**Tradeoffs and pitfalls**

Partitioning helps only when pruning removes data or partitions align with independent work; it does not inherently eliminate the global ordering requirement. Benchmark equivalent results on realistic skew and concurrency.

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)
- [`08-query-plans-indexes-statistics-and-optimization.md`](03-sql-and-analytical-querying/08-query-plans-indexes-statistics-and-optimization.md)

**Source provenance**

- S019

**Verification note**

- PostgreSQL reports in-memory versus on-disk sort methods in [Using `EXPLAIN`](https://www.postgresql.org/docs/current/using-explain.html); `DISTINCT ON` ordering requirements are in [`SELECT`](https://www.postgresql.org/docs/current/sql-select.html#SQL-DISTINCT).

## SQL recursive queries and temporal logic

### 1. How would you write date-window logic that remains correct across time zones and daylight-saving transitions?

**Interview answer**

Store event instants as `timestamptz`, keep the reporting zone as part of the metric contract, and define local calendar boundaries in a named IANA zone. Convert those boundaries to instants, then use a half-open interval `[start, end)`. Do not assume a local day is always 24 hours or replace a zone with a fixed UTC offset; daylight-saving and political rule changes break those assumptions.

**Example**

```sql
-- PostgreSQL: events in the America/Denver local calendar day.
SELECT *
FROM events
WHERE occurred_at >= (:local_day::timestamp AT TIME ZONE 'America/Denver')
  AND occurred_at <  ((:local_day::date + 1)::timestamp
                      AT TIME ZONE 'America/Denver');
```

**Tradeoffs and pitfalls**

Applying `AT TIME ZONE` to every stored event can make ordinary indexes less useful; converting the two boundary values preserves a direct range predicate on `occurred_at`. Ambiguous or nonexistent local input times need an ingestion policy.

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

**Source provenance**

- S002

**Verification note**

- PostgreSQL 18/current time-zone storage and named-zone behavior are documented in [Date/Time Types](https://www.postgresql.org/docs/current/datatype-datetime.html) and [`AT TIME ZONE`](https://www.postgresql.org/docs/current/functions-datetime.html#FUNCTIONS-DATETIME-ZONECONVERT).

### 2. How would you flatten an organizational hierarchy with a recursive CTE and prevent infinite recursion?

**Interview answer**

Use a recursive CTE with an anchor for roots and a recursive term that joins each discovered employee to direct reports. Carry depth and path information so the result is explainable. Real organization data can contain cycles, so enforce acyclicity on writes where possible and detect cycles during traversal. PostgreSQL 18 supports the SQL `CYCLE` clause; on engines without it, maintain a visited-key collection and reject already visited nodes.

**Example**

```sql
-- PostgreSQL 18.
WITH RECURSIVE org(employee_id, manager_id, depth) AS (
    SELECT employee_id, manager_id, 0
    FROM employees
    WHERE employee_id = :root_employee_id
  UNION ALL
    SELECT e.employee_id, e.manager_id, org.depth + 1
    FROM employees e
    JOIN org ON e.manager_id = org.employee_id
) CYCLE employee_id SET is_cycle USING path
SELECT employee_id, manager_id, depth, path
FROM org
WHERE NOT is_cycle
ORDER BY path;
```

**Tradeoffs and pitfalls**

`UNION` removes duplicate complete rows but is not a general cycle guard when depth or path differs. Define behavior for multiple parents, disconnected components, maximum depth, and malformed roots.

**Related curriculum**

- [`05-subqueries-common-table-expressions-and-recursion.md`](03-sql-and-analytical-querying/05-subqueries-common-table-expressions-and-recursion.md)

**Source provenance**

- S002

**Verification note**

- Recursive evaluation, path tracking, and `CYCLE` are documented in PostgreSQL 18/current [`WITH` Queries](https://www.postgresql.org/docs/current/queries-with.html#QUERIES-WITH-RECURSIVE).

### 3. How would you express a multi-step conversion funnel using CTEs?

**Interview answer**

Define one qualifying event per user for each ordered step. Build staged CTEs so each later step occurs at or after the prior step, then count users at each stage from those user-grain relations. This makes ordering and eligibility auditable and prevents repeated event rows from inflating conversions. State the attribution window and whether users may restart or complete the funnel more than once.

**Example**

```sql
-- PostgreSQL; first completion of signup -> verify -> purchase.
WITH signup AS (
    SELECT user_id, MIN(occurred_at) AS signup_at
    FROM events WHERE event_name = 'signup' GROUP BY user_id
), verified AS (
    SELECT s.user_id, s.signup_at, MIN(e.occurred_at) AS verified_at
    FROM signup s
    JOIN events e ON e.user_id = s.user_id
                 AND e.event_name = 'verify'
                 AND e.occurred_at >= s.signup_at
    GROUP BY s.user_id, s.signup_at
), purchased AS (
    SELECT v.user_id, MIN(e.occurred_at) AS purchased_at
    FROM verified v
    JOIN events e ON e.user_id = v.user_id
                 AND e.event_name = 'purchase'
                 AND e.occurred_at >= v.verified_at
    GROUP BY v.user_id
)
SELECT (SELECT COUNT(*) FROM signup) AS signed_up,
       (SELECT COUNT(*) FROM verified) AS verified,
       (SELECT COUNT(*) FROM purchased) AS purchased;
```

**Tradeoffs and pitfalls**

This is a user-level first-conversion funnel. Session funnels, repeated journeys, strict step deadlines, and event-time corrections require an explicit journey identifier or more detailed sequence logic.

**Source provenance**

- S002

**Related curriculum**

- [`05-subqueries-common-table-expressions-and-recursion.md`](03-sql-and-analytical-querying/05-subqueries-common-table-expressions-and-recursion.md)
- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

### 4. Given user session intervals, how would you find users with overlapping sessions and define boundary behavior?

**Interview answer**

First choose interval semantics. With half-open intervals `[start_at, end_at)`, two sessions overlap when each starts before the other ends; touching boundaries do not overlap. Self-join on user, compare each pair only once with a stable session ID, and decide how to treat null ends, zero-length sessions, and invalid reversed bounds.

**Example**

```sql
-- PostgreSQL; half-open interval semantics.
SELECT a.user_id,
       a.session_id AS first_session,
       b.session_id AS second_session
FROM sessions a
JOIN sessions b
  ON b.user_id = a.user_id
 AND a.session_id < b.session_id
 AND a.start_at < b.end_at
 AND b.start_at < a.end_at
ORDER BY a.user_id, a.session_id, b.session_id;
```

**Tradeoffs and pitfalls**

Use `<=` only if touching closed intervals count as overlap. A self-join may be expensive for users with many sessions; a sorted `LAG` approach can flag overlap with the prior maximum end, but finding every overlapping pair needs more care. PostgreSQL range types and exclusion constraints are a dialect-specific option for preventing overlaps.

**Related curriculum**

- [`06-window-functions-time-series-and-analytical-patterns.md`](03-sql-and-analytical-querying/06-window-functions-time-series-and-analytical-patterns.md)

**Source provenance**

- S021

**Verification note**

- PostgreSQL's built-in range types define inclusive/exclusive bounds and overlap operators in [Range Types](https://www.postgresql.org/docs/current/rangetypes.html).

## SQL transactions and concurrency

### 1. How do transaction isolation levels change the possibility of dirty, non-repeatable, and phantom reads?

**Interview answer**

Isolation controls which outcomes of concurrent transactions may become visible. In the SQL model, Read Uncommitted may allow dirty, non-repeatable, and phantom reads; Read Committed forbids dirty reads; Repeatable Read also forbids non-repeatable reads; Serializable requires an outcome equivalent to some serial execution. Engines may provide stronger behavior. In PostgreSQL 18, Read Uncommitted behaves as Read Committed, Repeatable Read also prevents phantom reads, and Serializable can abort a transaction with a serialization failure that the application must retry in full.

**Tradeoffs and pitfalls**

Higher isolation reduces allowable anomalies but can add blocking, conflict detection, and retries. Isolation alone does not replace constraints or correct transaction boundaries, and a retry must include every read and write whose decisions formed the transaction.

**Related curriculum**

- [`07-ddl-constraints-transactions-and-concurrent-change.md`](03-sql-and-analytical-querying/07-ddl-constraints-transactions-and-concurrent-change.md)

**Source provenance**

- S001

**Verification note**

- The standard phenomena and PostgreSQL-specific guarantees are summarized in PostgreSQL 18/current [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html).

### 2. What conditions create a database deadlock, and how should an application respond?

**Interview answer**

A deadlock is a wait cycle: transaction A holds a lock B needs while B holds a lock A needs, so neither can progress. PostgreSQL detects the cycle and aborts one transaction. The application should roll back and retry the entire transaction with bounded backoff, while preserving idempotency. Reduce deadlocks by acquiring shared resources in a consistent order, keeping transactions short, locking only what is needed, and indexing predicates so updates do not touch avoidable rows.

**Mental walkthrough**

1. Transaction A locks account 1, then requests account 2.
2. Transaction B has locked account 2, then requests account 1.
3. PostgreSQL aborts one participant; its partial work is rolled back.
4. The application retries from the beginning, because earlier reads may no longer be valid.

**Tradeoffs and pitfalls**

Long waits are not necessarily deadlocks, and a lock timeout is not proof of a cycle. Capture the deadlock report and transaction statements; blind retries without diagnosis can amplify load.

**Related curriculum**

- [`07-ddl-constraints-transactions-and-concurrent-change.md`](03-sql-and-analytical-querying/07-ddl-constraints-transactions-and-concurrent-change.md)

**Source provenance**

- S001

**Verification note**

- PostgreSQL deadlock detection and consistent lock ordering are described in [Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-DEADLOCKS).

## SQL query plans and performance

### 1. What can estimated versus actual rows in `EXPLAIN ANALYZE` reveal about a slow query?

**Interview answer**

Compare estimated and actual rows at every plan node, accounting for `loops`. A large divergence near the bottom often means poor selectivity estimates from stale statistics, skew, correlated columns, or predicates the planner cannot estimate well. That error propagates upward and can make a nested loop, join order, aggregation strategy, or scan look cheap when it is not. Also inspect actual time, loops, rows removed, buffer I/O, sort spill, and hash batches; row-estimate error identifies a likely cause, not the whole diagnosis.

**Tradeoffs and pitfalls**

`EXPLAIN ANALYZE` executes the statement and adds instrumentation overhead. Use a transaction that is rolled back for write statements when safe, and avoid production experiments whose actual execution is risky. Planner "cost" is an internal estimate, not milliseconds.

**Related curriculum**

- [`08-query-plans-indexes-statistics-and-optimization.md`](03-sql-and-analytical-querying/08-query-plans-indexes-statistics-and-optimization.md)

**Source provenance**

- S001

**Verification note**

- PostgreSQL 18/current defines estimated rows, actual rows, loops, sort methods, and buffers in [Using `EXPLAIN`](https://www.postgresql.org/docs/current/using-explain.html).

### 2. When can a covering index enable an index-only scan, and what write costs does it add?

**Interview answer**

An index covers a query when the index type can return all referenced columns and every needed column is stored in that index, possibly as PostgreSQL `INCLUDE` payload columns. PostgreSQL can then use an index-only scan, but it may still visit the heap unless the visibility map says the heap page is all-visible. It helps most on selective, relatively stable tables. Extra columns enlarge the index, increase cache and storage pressure, and add work to inserts, updates, vacuuming, and replication.

**Example**

```sql
-- PostgreSQL.
CREATE INDEX orders_customer_created_cover
    ON orders (customer_id, created_at DESC)
    INCLUDE (status, total_amount);
```

**Tradeoffs and pitfalls**

Payload columns do not become search keys, and wide values can exceed index tuple limits. Verify `Index Only Scan` and `Heap Fetches` with the real query; "covering" does not guarantee the planner will choose it.

**Related curriculum**

- [`08-query-plans-indexes-statistics-and-optimization.md`](03-sql-and-analytical-querying/08-query-plans-indexes-statistics-and-optimization.md)

**Source provenance**

- S001

**Verification note**

- PostgreSQL 18/current requirements, visibility-map behavior, and `INCLUDE` tradeoffs are documented in [Index-Only Scans and Covering Indexes](https://www.postgresql.org/docs/current/indexes-index-only-scans.html).

### 3. A nightly rollup slowed from minutes to hours after volume tripled; how would you use its plan to choose among indexing, partitioning, and join changes?

**Interview answer**

Capture the exact SQL, parameters, row counts, runtime, and `EXPLAIN (ANALYZE, BUFFERS)` on representative data. Find the first node where actual rows, loops, time, I/O, spill, or hash batches explode. Choose the remedy from evidence: an index for selective access or useful ordering; partitioning when a stable predicate can prune most data or lifecycle operations justify it; join changes when cardinality, skew, repeated inner scans, or pre-aggregation dominates. Refresh statistics before redesigning storage and validate output totals after every rewrite.

**Mental walkthrough**

1. Separate the threefold expected work increase from the much larger regression.
2. Check scan pruning and filters, then estimate-versus-actual rows.
3. Trace join input/output cardinality and repeated loops.
4. Inspect sort/hash spills and buffer reads.
5. Benchmark one hypothesis at a time under realistic concurrency.

**Tradeoffs and pitfalls**

Partitioning is not a universal speed feature, and new indexes add write and maintenance costs. Forced planner settings are diagnostic experiments, not durable fixes.

**Related curriculum**

- [`08-query-plans-indexes-statistics-and-optimization.md`](03-sql-and-analytical-querying/08-query-plans-indexes-statistics-and-optimization.md)

**Source provenance**

- S019

**Verification note**

- Plan interpretation is documented in [Using `EXPLAIN`](https://www.postgresql.org/docs/current/using-explain.html); partition pruning is PostgreSQL-specific and documented in [Table Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html#DDL-PARTITION-PRUNING).

### 4. How would you decompose and debug a very large SQL statement that is wrong for only one slice of data?

**Interview answer**

Freeze the inputs and turn the failing slice into the smallest reproducible case. State the intended row grain and invariants at each logical stage, then expose stages with CTEs or temporary diagnostic queries and count rows, keys, nulls, and control totals after each filter, join, and aggregate. Compare failing and passing slices to locate the first divergence. Inspect join multiplicity and boundary conditions before adding `DISTINCT`, because duplicate removal can hide the defect.

**Tradeoffs and pitfalls**

CTEs improve observability, but PostgreSQL may fold a side-effect-free CTE into the parent or materialize it depending on references and directives; do not infer runtime boundaries from formatting alone. Preserve the original snapshot so concurrent source changes do not masquerade as query differences.

**Related curriculum**

- [`05-subqueries-common-table-expressions-and-recursion.md`](03-sql-and-analytical-querying/05-subqueries-common-table-expressions-and-recursion.md)
- [`03-unit-property-and-sql-transformation-testing.md`](13-data-quality-contracts-and-testing/03-unit-property-and-sql-transformation-testing.md)

**Source provenance**

- S019

**Verification note**

- PostgreSQL 18/current CTE folding and `MATERIALIZED`/`NOT MATERIALIZED` behavior are documented in [`WITH` Query Materialization](https://www.postgresql.org/docs/current/queries-with.html#QUERIES-WITH-CTE-MATERIALIZATION).

### 5. How would you diagnose and mitigate a bad join plan caused by stale optimizer statistics?

**Interview answer**

Look for a large estimated-versus-actual row mismatch before or at the join, then check when the tables and relevant columns were last analyzed and whether recent loads changed size or distribution. Run `ANALYZE` and compare the new plan. If estimates remain poor, increase per-column statistics targets for skewed data, create extended statistics for correlated columns or multi-column distinctness, and ensure expressions and data types let the planner use those statistics. Fix the maintenance cadence rather than relying on a one-off analyze.

**Tradeoffs and pitfalls**

Refreshing statistics is not proof that the chosen plan is wrong; cost settings, cache behavior, parameter sensitivity, and data skew can also matter. More statistics improve estimates at the cost of analyze time, catalog space, and planning work. Benchmark the corrected plan and preserve result equivalence.

**Related curriculum**

- [`08-query-plans-indexes-statistics-and-optimization.md`](03-sql-and-analytical-querying/08-query-plans-indexes-statistics-and-optimization.md)

**Source provenance**

- S019

**Verification note**

- PostgreSQL 18/current sample statistics, statistics targets, and extended statistics are documented in [Statistics Used by the Planner](https://www.postgresql.org/docs/current/planner-stats.html); operational collection is covered by [Routine Vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html#VACUUM-FOR-STATISTICS).

## Relational design and correctness

### 1. How would you identify a normal-form violation and decide whether denormalization is justified?

**Interview answer**

Start from the relation's declared grain, candidate keys, and functional dependencies. A violation appears when a fact depends on only part of a composite key, on another non-key attribute, or when repeating/multivalued groups force mixed grains. Those designs create update, insert, and delete anomalies. Decompose into relations where each fact is owned once, preserve dependencies where practical, and enforce keys and references. Denormalize only for a measured workload need, with a canonical owner and a reliable rule for refreshing redundant values.

**Mental walkthrough**

If `order_line(order_id, product_id, product_name, quantity)` is keyed by `(order_id, product_id)` and `product_id -> product_name`, the name depends on only part of the key. Move product attributes to `product(product_id, product_name)` and reference it from the line. Duplicate the name into a serving table only if a measured read requirement justifies its consistency cost.

**Tradeoffs and pitfalls**

Normalization is a correctness tool, not a demand to maximize table count. Historical snapshots, dimensional models, and precomputed serving tables may intentionally repeat data, but their grain, ownership, and refresh guarantees must be explicit.

**Related curriculum**

- [`02-relational-modeling-normalization-and-integrity.md`](05-data-modeling-and-business-semantics/02-relational-modeling-normalization-and-integrity.md)

**Source provenance**

- S001

**Verification note**

- Constraint mechanisms used to enforce the resulting model are documented in PostgreSQL 18/current [Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html). Normal-form reasoning itself is relational theory and is not PostgreSQL-specific.
