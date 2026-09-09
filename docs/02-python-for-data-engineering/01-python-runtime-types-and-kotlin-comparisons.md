# Python Runtime, Types, and Kotlin Comparisons

> Status: Documentation complete  
> Level: Beginner data engineering / experienced Kotlin engineer  
> Applies to: Python 3.12+; CPython details are labeled  
> Data scale: Local record examples with production implications  
> Example status: Design snippets complete; executable lesson planned  
> Evidence status: Documentation review; runtime evidence pending  
> Last reviewed: 2026-09

## Overview

Python names refer to objects; a name does not declare a storage slot with a
permanent runtime type. Operations are resolved from the objects encountered at
runtime. This flexibility is useful at heterogeneous data boundaries, but it
makes explicit validation, mutation control, and tests part of correctness.

This guide covers identity, equality, mutability, truth testing, numeric behavior,
and absence. It does not teach basic control-flow syntax or claim that all Python
implementations share CPython's memory-management details.

## Learning objectives

After completing this guide, you should be able to:

- Predict aliasing, equality, truthiness, and mutation results.
- Separate a runtime object from a name and from a type hint.
- Model missing, null, empty, zero, and invalid data as different states.
- Identify language guarantees versus CPython implementation behavior.
- Prevent shared mutation from making a transform order-dependent.

## Prerequisites

Know Kotlin references, nullable types, data classes, collections, and the Area 01
concepts of record grain and identity. Python 3.12 is required only for future
executable exercises.

## Mental model

```text
name ----references----> object: value + runtime type + behavior
  |                         ^
another name ---------------|   alias

is  asks: same object?
==  asks: values compare equal under their protocols?
```

A Kotlin `val` prevents rebinding but not mutation of the referenced object.
Python has no direct local-name equivalent of `val`; conventions and APIs must
control rebinding and mutation. Python `==` is closer to Kotlin structural
equality, and `is` to referential equality, but Python classes can implement
comparison with richer dispatch and even non-Boolean intermediate results.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Name | Identifier bound to an object in a namespace |
| Identity | Whether two references designate the same object; tested with `is` |
| Equality | Value relation implemented by comparison protocols; tested with `==` |
| Mutability | Whether an object's observable state can change in place |
| Truthiness | Conversion of an object to a Boolean condition |
| Sentinel | Unique object representing a state that ordinary data cannot represent |

## Requirements, boundaries, and invariants

One reference input is an untrusted mapping representing one delivered event.
The producer owns the meaning and stable `event_id`; the parser owns conversion,
not the source mapping. It must not mutate caller-owned input, confuse missing
with explicit null, or use truthiness where zero or empty text is valid.

```python
MISSING = object()

def read_attempts(record: dict[str, object]) -> int:
    raw = record.get("attempts", MISSING)
    if raw is MISSING:
        raise ValueError("attempts is missing")
    if raw is None:
        raise ValueError("attempts cannot be null")
    if type(raw) is not int or raw < 0:
        raise ValueError("attempts must be a non-negative integer")
    return raw
```

`if not raw` would collapse missing-like, null, zero, empty, and false values.
The exact `type` check also intentionally rejects `bool`, which is a subclass of
`int`; boundary policy must decide whether that distinction matters.

## Runtime behavior that changes data results

### Mutation and aliasing

Assignment does not copy. If two names refer to one list or nested mapping, an
in-place update through either name changes the shared object. A shallow copy
duplicates only the outer container. Transformation functions should prefer new
output values or document ownership transfer explicitly.

Mutable default arguments are created when the function is defined, not anew per
call. Use `None` as a construction signal only when `None` cannot be valid data,
or use a private sentinel.

### Equality, hashing, and keys

Dictionary and set keys require stable hashing and compatible equality. Mutating
state that participates in equality after key insertion breaks lookup reasoning;
built-in mutable containers are therefore unhashable. Data-engineering keys
should be immutable canonical values, not display labels or mutable models.

Numeric equality can cross types: `1 == 1.0` and `True == 1`. That does not make
their source semantics interchangeable. Validate before deduplication so a
convenient runtime equality relation does not redefine business identity.

### Numbers and time

Python integers have arbitrary precision at the language level, unlike Kotlin
`Long`; external files, databases, Arrow types, and engines remain bounded.
Binary floating-point cannot exactly represent many decimal fractions. Use an
owned integer unit or decimal model for money and other exact quantities. Use
timezone-aware instants and explicit UTC boundaries for events; never let local
host time define dataset membership implicitly.

## Data flow and trust boundaries

| Boundary | Authority | Risk | Required behavior |
| --- | --- | --- | --- |
| Mapping from parser/client | External producer | Wrong types, aliases, hostile objects | Treat as untrusted; bound and validate |
| Normalized immutable model | Transformation library | Incorrect coercion or shared mutation | Construct new value; preserve identity/time semantics |
| Serialized output | Publication owner | Type narrowing, precision loss | Check target schema and range before commit |

The normalized object is authoritative only for the named validation and
normalization result, not for the original observation or durable publication.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Missing/null/empty collapsed | Boundary tests and reconciliation | Restore distinct states; reprocess immutable input |
| Input mutated | Before/after fixture or property test | Make output construction non-mutating; rerun |
| Unstable key/equality | Duplicate or lookup anomaly | Canonicalize immutable key before state insertion |
| Numeric overflow at sink | Range/schema check | Reject before publication or migrate target type |
| Naive/local timestamp | Time-zone test around DST | Parse zone explicitly; republish corrected interval |

Retries are owned by the caller. The transform must be deterministic and free of
external side effects so rerunning fixed input does not amplify damage.

## Security, quality, and evidence

Do not evaluate input as Python, dynamically import a producer-provided name, or
deserialize trusted object graphs from untrusted bytes. Bound text, integers,
nested depth, and collection length before expensive operations. Errors identify
field and rule, not raw sensitive value.

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Semantic table review | Predict missing/null/zero/false/empty cases | Each has intentional outcome | Reviewed in guide |
| Unit and property tests | Future repository tests | No input mutation; stable classification | Pending |
| Sink range integration | Future real serializer/database | Out-of-range values rejected safely | Pending |

## Debugging guide and pitfalls

1. Capture runtime type with a safe summary, rule version, event reference, and
   first affected dataset version; never dump the full record by default.
2. Check whether mutation happened before validation and whether two fields alias.
3. Reproduce with minimal values including `None`, `False`, `0`, empty containers,
   large integers, NaN, and timezone transitions.
4. Compare counts before and after canonicalization; repair from immutable input.

Avoid `is` for strings or numbers; implementation interning is not a value
contract. Avoid `if value` when the contract means “present.” Avoid catching a
broad exception and substituting null: that converts defects and overload into
apparently valid data.

## Production considerations and tradeoffs

Immutable boundary models allocate more than mutating pooled dictionaries, but
they greatly reduce aliasing and retry risk. Coercion accepts more producer drift
but can silently change meaning; strict validation gives clearer contracts but
requires explicit compatibility rollout. Optimize only after profiling the
representative record mix and target serialization boundary.

Operational metrics should count outcomes by bounded rule identifiers and schema
versions, never by event ID or input value. Schema evolution follows
expand/migrate/contract: accept old and new shapes intentionally, normalize to a
versioned internal model, backfill from retained input, reconcile, then retire.

## Working example

- Python source and tests: Planned for the bounded event parser
- Current activity: Predict the `read_attempts` result for missing, null, false,
  zero, positive integer, negative integer, string, and very large integer
- Evidence represented: Language-level design review only
- Remaining risk: Runtime, type-check, serializer, memory, and production evidence

## Knowledge check

1. Predict the result when two names share a nested dictionary and one mutates it.
2. Design a representation that distinguishes absent, explicit null, and empty.
3. Explain why `event_id == 1` may accidentally match `True` after weak parsing.
4. Specify tests proving a transform does not mutate caller-owned records.
5. Design a target-type migration when valid identifiers exceed signed 64-bit range.

## Key takeaways

- Python binds names to runtime objects; assignment does not copy.
- Identity, equality, and business identity are three separate contracts.
- Truthiness is concise control flow, not a missing-data model.
- Validation must precede deduplication, arithmetic, and serialization.
- Interpreter details are not portable data guarantees.

## Resources

- [Python 3.12 data model](https://docs.python.org/3.12/reference/datamodel.html)
- [Python 3.12 expressions](https://docs.python.org/3.12/reference/expressions.html)
- [Python 3.12 built-in types](https://docs.python.org/3.12/library/stdtypes.html)

## Related topics

- [Area README](README.md)
- [Type hints, validation, and untrusted data](05-type-hints-validation-and-untrusted-data.md)
- [Collections, iteration, generators, and bounded memory](02-collections-iteration-generators-and-bounded-memory.md)

## Completion checklist

- [x] Runtime model, Kotlin comparison, grain, authority, and invariants explained
- [x] Identity, equality, mutation, truthiness, numbers, absence, and time covered
- [x] Failure, security, quality, operations, compatibility, and tradeoffs addressed
- [x] Example and evidence limits explicit
- [ ] Executable examples and boundary tests implemented
- [ ] Serializer/database range behavior verified

