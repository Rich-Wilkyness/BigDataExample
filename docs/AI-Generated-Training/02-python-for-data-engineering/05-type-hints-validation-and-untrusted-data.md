# Type Hints, Validation, and Untrusted Data

> Status: Documentation complete  
> Level: Intermediate  
> Applies to: Python / Data contracts / Ingestion boundaries  
> Data scale: Bounded event records  
> Example status: Boundary model designed; implementation planned  
> Evidence status: Documentation review; static and contract evidence pending  
> Last reviewed: 2026-09

## Overview

Type hints describe intended program values for developers and static tools;
Python does not enforce most annotations when a function is called. Runtime
validation establishes whether untrusted bytes or objects satisfy a versioned
data contract. These are complementary layers: hints improve code reasoning after
validation, while validation protects the producer/consumer boundary.

This guide uses standard-library models and manual validation so the distinction
is visible. Validation frameworks and schema formats are later implementation
choices, not substitutes for owned semantics.

## Learning objectives

- Separate static typing, runtime type inspection, parsing, and semantic validation.
- Model missing, explicit null, unions, constrained values, and schema versions.
- Design safe errors/quarantine without retaining excessive sensitive data.
- Evolve producer and consumer types through mixed-version operation.
- Define contract, mutation, and reconciliation evidence.

## Prerequisites

Complete guides 01–04. Know the shared event grain, sentinel pattern, dataclasses,
pure core, and recovery boundary.

## Mental model

```text
untrusted bytes/object
      |
size + syntax + structural validation
      |
semantic validation + normalization       static checker
      |                                  verifies code paths
typed internal value ---------------------------^
      |
explicit versioned serialization
```

Kotlin's compiler and runtime enforce more of a declared JVM boundary, though
deserialized Kotlin data still needs validation. Python hints are closer to a
compile-time linted design contract: they may not exist in a consuming tool and
do not make an incoming dictionary safe.

## Terminology

| Term | Meaning |
| --- | --- |
| Type hint | Annotation consumed primarily by static tools and readers |
| Parsing | Converting a representation into candidate runtime values |
| Structural validation | Checking required fields, types, shape, and version |
| Semantic validation | Checking domain rules and cross-field meaning |
| Normalization | Intentional, versioned conversion to a canonical form |
| Compatibility | Whether producers and consumers can coexist across versions |

## Contract, scale, and invariants

One input mapping is one delivered event envelope. It is untrusted until bounded
and validated. A successful parse returns exactly one immutable `Event`; a known
data failure returns one safe `Rejection`; unexpected defects and system failures
propagate and fail the owned batch. Missing and explicit null remain distinct.

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias, TypedDict

class EventV1Input(TypedDict):
    schema_version: Literal[1]
    event_id: str
    screen_name: str
    event_time: str

@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    screen_name: str
    event_time: datetime

@dataclass(frozen=True, slots=True)
class Rejection:
    rule: str
    event_ref: str | None

ParseResult: TypeAlias = Event | Rejection
```

`TypedDict` tells a checker the expected mapping shape; constructing an ordinary
dictionary at runtime performs no validation. `Literal[1]` likewise helps static
reasoning but must be checked in the parser.

Limits include maximum encoded bytes, object depth, field count/length, accepted
schema versions, timestamp range, and records per batch. Normalization cannot
invent a missing identity or silently substitute current time.

## Validation pipeline

1. Authenticate/authorize the source and bound encoded/decompressed size.
2. Parse using a safe data parser; reject trailing or malformed content per contract.
3. Require a supported schema version before version-specific interpretation.
4. Check exact structure and distinguish absent from explicit null.
5. Check semantic constraints: stable identity, screen vocabulary, UTC instant,
   permitted range, and cross-field rules.
6. Normalize only through documented mappings; preserve original version/lineage.
7. Return a typed value or safe rejection and update reconciliation counts.

Coercing `"1"` to integer or local time to UTC may aid compatibility, but it is a
business rule that must be versioned, observable, tested, and reversible where
required. “Parse what you can” commonly creates multiple meanings for one field.

## Ownership and trust boundaries

| Boundary | Owner/authority | Guarantee and limit |
| --- | --- | --- |
| Producer schema | Producer plus contract owner | Shape and meaning promised; delivery remains untrusted |
| Raw accepted bytes | Ingestion | Authoritative receipt/version; not semantic validity |
| Validator/rule set | Data pipeline owner | Classification under named rule version |
| Typed internal `Event` | Transformation library | Safe for declared internal operations only |
| Published schema | Data-product owner | Consumer-facing types/semantics at dataset version |

Validation should occur once at each trust transition, not be assumed forever.
Stored data can mix historical versions or become corrupt, and sinks may narrow
types or represent null/time differently.

## Failure model and recovery

| Failure | Detection | Behavior and recovery |
| --- | --- | --- |
| Unsupported version | Version gate | Quarantine/reject safely; deploy compatible reader before replay |
| Missing/null/invalid field | Named rule | Classify record; no partial normalized event |
| Oversized/deep input | Pre-parse/parser bound | Reject early; protect worker capacity |
| Validator defect | Unexpected exception/invariant | Fail batch; fix versioned code and replay raw input |
| Schema drift passes weak model | Contract/distribution test | Hold publication, add rule, assess and backfill |
| Type hint/code mismatch | Static check | Fix before delivery; runtime data unaffected until run |
| Quarantine unavailable | Dependency failure | Fail or apply explicit reject-only policy; never silently drop |

Retrying deterministic invalid data is wasteful. Reprocessing becomes useful only
after rule/schema/code changes, and it writes a new derived dataset version with
reconciliation against the old one.

## Security, privacy, and governance

Never use `eval`, unsafe object deserialization, or producer-selected imports.
Protect against parser bombs, extreme numeric/text values, Unicode/path surprises,
and unexpectedly expensive validation. Allowlist semantic values where the domain
owns a finite vocabulary.

Quarantine is a restricted dataset, not an ordinary log. Store the minimal safe
reference, schema/rule version, reason code, and authorized replay pointer. Apply
retention, deletion, encryption, access, lineage, and audit policies to raw,
rejected, valid, logs, metrics, and backups.

## Testing and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Static type check | Package source | Public/internal mismatches reported | Pending; tool not selected |
| Table tests | Each missing/null/type/range/version case | Exact value or stable rejection | Pending |
| Property tests | Generated Unicode, sizes, times, numbers | Parser never silently drops/mutates | Pending |
| Contract/mutation tests | Producer/consumer schema versions | Supported matrix behaves as documented | Pending |
| Fuzz/resource test | Bounded hostile inputs | Time/memory remain within budget | Pending |
| Reconciliation | Deterministic fixture | input identities = valid + rejected/deferred | Pending |

Mocks cannot prove actual JSON/parser limits, database type mapping, or consumer
compatibility. These require real boundary integration.

## Debugging guide and pitfalls

Record schema/rule/code versions, safe event reference, reason code, source and
dataset version, first affected time, and counts. Compare raw shape distributions
and rejection rates by bounded version/rule. Reproduce with the exact retained
bytes in an authorized environment, then replay a bounded interval and reconcile.

Pitfalls include believing annotations validate dictionaries, conflating
`Optional[T]` with an optional key, returning null for every parse failure,
unversioned coercion, overly permissive unions, logging invalid payloads, and
letting unknown fields silently alter behavior. Strictness is a contract choice:
rejecting every additive field can harm evolution, while ignoring every unknown
field can hide producer mistakes.

## Performance, operations, and compatibility

Measure validation latency percentiles, records/bytes per second, allocations,
largest accepted/rejected record, rejection distribution, quarantine backlog, and
cost. Validate cheap bounds before expensive parsing or cross-field work. Cache
only immutable bounded policy data with explicit refresh/version semantics.

Evolve with an explicit compatibility matrix: deploy readers accepting v1 and v2,
observe producers, normalize with recorded source version, backfill if semantics
change, migrate consumers, and retire v1 only after its retention/support window.
Rollback must preserve the ability to read data produced by the new writer.

## Working example

- Planned source: Typed boundary values and total parser returning event/rejection
- Planned tests: Table, property, mutation, compatibility, and resource-limit cases
- Expected result: Every bounded input is classified; unexpected defects fail visibly
- Remaining risk: Tool selection, parser integration, fuzzing, consumer compatibility

## Knowledge check

1. Explain why `TypedDict` does not protect a JSON boundary at runtime.
2. Model a field that may be absent but, when present, may not be null.
3. Decide whether trimming screen names is validation or normalization and who owns it.
4. Design a v1/v2 rollout that adds a nullable producer field but requires a
   non-null curated value later.
5. Specify safe rejection information for a sensitive malformed record.

## Key takeaways

- Static hints protect code reasoning; runtime validation protects data boundaries.
- Missing, null, invalid, and empty are separate states.
- Coercion and normalization are versioned semantic policies.
- Quarantine needs the same governance discipline as source data.
- Compatibility requires mixed-version tests and replay evidence.

## Resources

- [Python typing specification](https://typing.python.org/en/latest/spec/)
- [Python 3.12 typing module](https://docs.python.org/3.12/library/typing.html)
- [Python 3.12 JSON module](https://docs.python.org/3.12/library/json.html)
- [Python 3.12 security considerations](https://docs.python.org/3.12/library/security_warnings.html)

## Related topics

- [Area README](README.md)
- [Python runtime, types, and Kotlin comparisons](01-python-runtime-types-and-kotlin-comparisons.md)
- [Environments, packaging, dependencies, and reproducibility](06-environments-packaging-dependencies-and-reproducibility.md)

## Completion checklist

- [x] Static/runtime distinction, trust, schemas, absence, validation, and evolution covered
- [x] Security, governance, failure, evidence, operations, and replay explicit
- [ ] Parser/models and static check implemented
- [ ] Property, fuzz, compatibility, and integration evidence executed
