# Unit, Property, and SQL Transformation Testing

> Status: Documentation complete; executable transformation-test evidence planned  
> Level: Beginner to Senior  
> Applies to: Python / SQL / Batch transforms / Analytical models  
> Data scale: Deterministic local fixtures; production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Unit tests verify one bounded behavior; property-based tests search many inputs
for invariant violations; SQL transformation tests compare relations or assert
that violation queries return no rows. Together they give fast evidence about
logic. They do not prove the behavior of a different SQL dialect, distributed
execution, real storage, complete source delivery, or a deployed pipeline.

The central design move is to derive tests from grain and invariants rather than
from implementation lines.

## Learning objectives

- Select example, property, metamorphic, differential, and SQL assertion tests.
- Define invariants for duplicates, `NULL`, order, time boundaries, and reruns.
- Test SQL at relation grain with explicit bag/set and ordering semantics.
- Use mutation tests conceptually to expose weak assertions.
- Keep randomized evidence reproducible without mistaking seeds for coverage.

## Prerequisites

- Area 02 Python functions, iterators, resource ownership, and `unittest`.
- Area 03 SQL `NULL`, grouping, joins, windows, and transactions.
- [Quality requirements](01-data-quality-dimensions-requirements-and-ownership.md) and [contracts](02-schema-data-and-consumer-contracts.md).

## Mental model and terminology

```text
contract invariant
   |-- example: one named edge
   |-- property: generated family of edges
   |-- metamorphic: predictable relation after input change
   |-- differential: compare independent implementations
   `-- SQL assertion: query returns zero violating rows
```

| Term | Meaning in this guide |
| --- | --- |
| Oracle | Mechanism deciding expected behavior; it may itself be defective |
| Property | Statement expected to hold over a defined input domain |
| Shrinking | Reducing a failing generated case while preserving failure |
| Metamorphic test | Checks a known relationship between outputs after a controlled input transformation |
| Differential test | Compares implementations intended to implement the same contract |
| Mutation test | Deliberately changes implementation logic to see whether tests fail |
| Bag semantics | SQL relations may contain duplicates unless constrained or eliminated |

Property-based testing resembles Kotlin generator-based tests, but data tests
must also model relation grain, `NULL`'s three-valued logic, engine-specific
numeric/time behavior, and transformations over historical state.

## Requirements, scale assumptions, and invariants

- Normalization is deterministic for fixed input and rule versions.
- Exact redelivery duplicates never change the certified metric.
- Input permutation does not change order-independent aggregates.
- Splitting and recombining disjoint interval inputs produces the same daily
  totals when keys do not cross the split; the precondition is part of the test.
- A rerun over the same snapshot replaces or reproduces output rather than adds
  another copy.
- Half-open UTC interval boundaries assign an event to exactly one daily window.
- Unknown, empty, and `NULL` values retain distinct meanings where the contract
  distinguishes them.
- Full rebuild and incremental recomputation agree for the declared correction horizon.
- Generated records, key cardinality, timestamp range, and payload size are
  bounded so test execution and shrinking terminate.
- Local fixtures model dozens of records; 100 million retained rows and skew are
  production estimates, not unit-test evidence.

## Python model

```python
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class Event:
    tenant_id: str
    event_id: str
    event_time: datetime
    event_name: str
    product_id: str | None

def product_view_counts(events: Iterable[Event]) -> dict[tuple[str, str, str], int]:
    seen: set[tuple[str, str]] = set()
    result: dict[tuple[str, str, str], int] = {}
    for event in events:
        identity = (event.tenant_id, event.event_id)
        if identity in seen:
            continue
        seen.add(identity)
        if event.event_name != "product_view" or event.product_id is None:
            continue
        if event.event_time.tzinfo is None:
            raise ValueError("event_time must include an offset")
        date = event.event_time.astimezone(timezone.utc).date().isoformat()
        key = (event.tenant_id, event.product_id, date)
        result[key] = result.get(key, 0) + 1
    return result
```

The smallest example tests an empty input, one view, a non-view, a missing
product, a boundary timestamp, and exact redelivery. Useful properties include
permutation invariance and redelivery idempotence. A conflicting duplicate needs
a different oracle: silently “first wins” would make permutation invariance fail
and reveals an underspecified contract.

```python
# Pseudocode using a property-test framework; dependency is not installed.
@given(valid_event_lists())
def test_exact_redelivery_is_idempotent(events):
    assert product_view_counts(events + events) == product_view_counts(events)

@given(valid_event_lists())
def test_result_never_exceeds_unique_eligible_events(events):
    actual = sum(product_view_counts(events).values())
    eligible_ids = {
        (e.tenant_id, e.event_id) for e in events
        if e.event_name == "product_view" and e.product_id is not None
    }
    assert actual <= len(eligible_ids)
```

Generation must include collisions, midnight offsets, Unicode, empty strings,
large but bounded values, and invalid cases routed to the validator. Over-filtered
strategies can make a property vacuously pass.

## SQL model and assertions

```sql
-- Candidate transform. Dialect-neutral sketch.
-- Grain after GROUP BY: tenant_id, product_id, UTC metric_date.
with unique_events as (
  select tenant_id, event_id, event_time, event_name, product_id,
         row_number() over (
           partition by tenant_id, event_id order by ingestion_position
         ) as delivery_rank
  from validated_events
), eligible as (
  select tenant_id, product_id, cast(event_time as date) as metric_date
  from unique_events
  where delivery_rank = 1
    and event_name = 'product_view'
    and product_id is not null
)
select tenant_id, product_id, metric_date, count(*) as view_count
from eligible
group by tenant_id, product_id, metric_date;
```

The cast's time-zone semantics are engine/session dependent; production SQL must
convert explicitly to UTC. The ordering column must be stable and unique or
conflicting duplicates are nondeterministic.

```sql
-- Assertion: candidate grain is unique. Success means zero rows.
select tenant_id, product_id, metric_date, count(*) as copies
from candidate_daily_product_views
group by tenant_id, product_id, metric_date
having count(*) <> 1;

-- Assertion: counts are nonnegative and non-NULL.
select *
from candidate_daily_product_views
where view_count is null or view_count < 0;
```

Compare relations by keyed values, not unspecified row order. `NOT IN` with a
`NULL` can hide differences; prefer null-safe equality or paired `EXCEPT` only
after verifying the dialect's duplicate and `NULL` semantics.

## Test selection table

| Risk | Cheapest useful evidence | Stronger next evidence |
| --- | --- | --- |
| Branch/edge logic | Named unit fixture | Generated property |
| Duplicate/rerun behavior | Metamorphic duplicate injection | Faulted integration retry |
| Full vs incremental drift | Differential fixture | Production-shaped backfill comparison |
| Join fan-out | SQL grain/reconciliation assertion | Real-engine plan and scale test |
| Time boundary | Fixed clock and boundary table | Engine/session time-zone matrix |
| Weak assertions | Deliberate mutation review | Automated mutation suite if cost justifies |

## Data flow, ownership, and trust boundaries

| Boundary | Owner and input | Failure behavior | Trust level |
| --- | --- | --- | --- |
| Pure Python function | Library owner; typed validated events | Raise/classify contract violation | In-process tested logic |
| Test generator | Test owner; declared input domain | Preserve failing case/seed | Test support, not source truth |
| SQL fixture loader | Test owner; explicit rows and schema | Transactionally isolate case | Controlled data |
| SQL engine | Platform/vendor semantics | Record version/session/plan | Real only when pinned engine runs |
| Expected relation | Domain owner | Review independently of query | Test oracle |

## Failure model and recovery

| Failure | Symptom | Repair |
| --- | --- | --- |
| Fixture copies implementation | Both preserve same defect | Derive expected rows from contract; add independent oracle |
| Generated test never produces duplicates | Idempotence property always passes | Measure generator coverage and force collision strategies |
| SQL compares row order | Flaky results | Compare keyed bags/sets with explicit ordering only at presentation |
| `NULL` hides assertion rows | False pass | Add explicit `IS NULL` cases and null-safe comparison |
| Time depends on local session | CI/environment mismatch | Pin clock, time zone, and boundary fixtures |
| Mutation survives | Assertions do not observe requirement | Strengthen outcome/property or remove meaningless test |
| Giant generated case stalls shrink | Slow/flaky CI | Bound size and separate load tests |

## Security, privacy, and governance

Use synthetic or minimized fixtures by default. Generated strings still test
injection, Unicode, path, and serialization boundaries without production data.
Never persist sensitive shrunk counterexamples or query failure rows into public
CI artifacts. Pin and review test dependencies because generators and database
drivers execute code in CI.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Unit edge suite | Planned hand-authored events / Python | Run standard-library unit tests | Exact expected counts/errors | Pending |
| Property suite | Planned bounded generators / pinned framework | Run properties with recorded settings | Invariants hold; failures shrink reproducibly | Pending |
| SQL assertions | Planned fixture / pinned real SQL engine | Build and query candidate relation | All violation queries return zero rows | Pending |
| Incremental differential | Late/update fixture / real engine | Compare incremental output to clean rebuild | Keyed relations equivalent | Pending |
| Mutation review | Selected validator/transform mutations | Flip boundary/dedupe/filter logic | Relevant tests fail | Pending |

## Debugging guide

1. Save the smallest failing input, seed/settings, code/rule version, engine version, SQL, session time zone, and schema.
2. Restate the invariant and preconditions; detect vacuous or overbroad properties.
3. Compare Python and SQL results by declared grain with explicit `NULL` semantics.
4. Minimize the relation while preserving the defect; inspect duplicate keys and boundary times.
5. Repair the contract or implementation, add the counterexample as a named regression, then rerun broader properties.

## Common pitfalls

### Pitfall: count executed tests instead of risks covered

Thousands of generated examples can repeat one narrow domain. Track invariants,
partitions of input space, and mutations detected.

### Pitfall: assert only row count

Equal counts can contain wrong keys and values. Compare at grain and reconcile
important measures.

### Pitfall: use production scale in unit tests

It makes fast logic evidence unstable without proving distributed capacity. Keep
unit domains bounded and run separate load/engine evidence.

## Performance, capacity, and cost

Budget unit and property suites for fast feedback; record examples, shrink time,
fixture rows, SQL scans, setup time, and CI wall time. Selective test execution
must follow a reliable dependency map. Expensive assertions can run on changed
partitions or maintained profiles only if periodic full checks test that
optimization itself.

## Compatibility, migration, and delivery

Run old tests against new code and new tests against representative old data.
Store regression cases without sensitive payloads. When changing SQL engines,
dual-run fixtures covering `NULL`, decimal, collation, timestamps, windows, and
set operations before relying on differential equivalence. A test-suite version
travels with each quality receipt.

## Working example

- Python: Planned transform and validators under `src/big_data_example/quality/`
- SQL: Planned transform/assertions under `sql/quality/`
- Tests: Planned unit/property/differential suite under `tests/quality/`
- Fixtures: Planned deterministic edge and faulty cases under `data/fixtures/quality/`
- Try it: Planned `python -m unittest discover -s tests` and pinned SQL procedure
- Expected result: Duplicate, order, `NULL`, time-boundary, and incremental mutations are detected
- Evidence: Planned failing-case corpus, SQL result, mutation table, and runtime
- Scale represented: Local bounded fixture only when implemented
- Remaining risk: Real-engine semantics, distributed behavior, integration, production scale, and cost

## Knowledge check

1. Explain the difference among an example, property, and metamorphic test.
2. Predict why “append the input twice” exposes a non-idempotent transform.
3. Diagnose a SQL relation comparison that passes despite a `NULL` mismatch.
4. Design generators for event identity and UTC-day boundaries.
5. Estimate why 100 million rows belong in load evidence, not a unit suite.
6. Plan an engine migration differential test.
7. Implement one mutation-resistant grain assertion in the planned suite.

## Key takeaways

- Tests come from contracts and invariants, not implementation shape.
- Properties explore domains; examples explain important named cases.
- SQL tests require explicit grain, bag, `NULL`, order, and time semantics.
- Differential tests need sufficiently independent oracles.
- Fast local evidence and real-engine/scale evidence answer different questions.

## Resources

- [Python `unittest` documentation](https://docs.python.org/3/library/unittest.html) (reviewed 2026-09)
- [Hypothesis introduction](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html) (reviewed 2026-09)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) (reviewed 2026-09; behavior is engine-specific)

## Related topics

- [Fixtures, sampling, and determinism](05-fixtures-golden-datasets-sampling-and-determinism.md)
- [Integration and end-to-end testing](04-integration-contract-and-end-to-end-pipeline-testing.md)
- [Area 03 SQL and analytical querying](../03-sql-and-analytical-querying/README.md)

## Completion checklist

- [x] Unit, property, metamorphic, differential, SQL, and mutation evidence explained
- [x] Identity, `NULL`, order, time, failure, privacy, performance, and migration covered
- [x] Local evidence limits separated from real-engine and distributed evidence
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Unit, property, SQL, mutation, differential, engine, and load evidence executed
