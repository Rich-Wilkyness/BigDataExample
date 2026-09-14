# Functions, Classes, Dataclasses, Protocols, and Modules

> Status: Documentation complete  
> Level: Intermediate  
> Applies to: Python / Transformation libraries  
> Data scale: Local bounded records  
> Example status: API design complete; executable library planned  
> Evidence status: Documentation review; unit and type evidence pending  
> Last reviewed: 2026-09

## Overview

Data code needs boundaries that reveal record meaning, dependencies, side effects,
and ownership. Pure functions are the default for local transformations; immutable
dataclasses express internal records; protocols describe the smallest collaborator
behavior; modules own related policy. Classes are valuable when they protect a
real lifecycle or invariant, not merely to imitate a service-layer hierarchy.

This guide does not prescribe a universal architecture or hide engine APIs behind
generic repositories. Distributed engines optimize expression graphs, so a local
object abstraction can become the wrong boundary later.

## Learning objectives

- Design pure transformation cores with explicit impure shells.
- Choose mapping, dataclass, protocol, function, class, or module deliberately.
- Model dependencies and configuration without ambient mutable globals.
- Preserve stable public contracts while evolving record schemas.
- Identify serialization, copying, and process-boundary consequences.

## Prerequisites

Complete guides 01 and 02. Understand producer identity, normalized-event grain,
and iterator ownership.

## Mental model

```text
impure adapter              pure policy                 impure publisher
read + parse -> validated value -> normalize/transform -> stage + commit
 owns resource       no hidden I/O or clock             owns transaction
```

This resembles Kotlin functional core/imperative shell and interface-driven
dependencies. Python protocols are structurally satisfied—similar in spirit to
duck typing with static verification—not runtime-declared JVM interfaces. A
protocol also supplies no runtime validation for incoming data.

## Terminology

| Term | Meaning |
| --- | --- |
| Pure function | Result depends only on arguments and has no externally visible side effect |
| Dataclass | Class-generation facility for record-like Python objects |
| Protocol | Static structural interface describing required members |
| Adapter | Boundary translating an external resource or representation |
| Policy | Owned business/data rule independent of transport and storage |
| Module | Importable namespace and deployment/versioning unit in a package |

## Requirements and invariants

One normalized value represents one valid event identity. Transformation must be
deterministic for a supplied configuration and clock/cutoff, must not perform
publication, and must preserve source identity and event time. External readers
and writers remain caller-owned.

```python
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    screen_name: str
    event_time: datetime

class RejectionSink(Protocol):
    def record(self, *, rule: str, event_ref: str | None) -> None: ...

def normalize(events: Iterable[Event], aliases: dict[str, str]) -> Iterator[Event]:
    for event in events:
        yield Event(
            event_id=event.event_id,
            screen_name=aliases.get(event.screen_name, event.screen_name),
            event_time=event.event_time,
        )
```

`frozen=True` prevents ordinary field assignment; it does not recursively freeze
referenced objects or make instances safe across all concurrency. `slots=True`
can reduce per-instance overhead but is an implementation choice to measure, not
a data correctness guarantee.

## Choosing a boundary

| Need | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Stateless record transform | Function | Dependencies and effects stay visible | Several operations protect shared lifecycle/state |
| Named internal record | Frozen dataclass | Readable equality and construction | Boundary input still needs runtime validation |
| Small collaborator contract | Protocol | Structural and easy to fake | Runtime plugin discovery needs explicit checks |
| Resource/transaction lifecycle | Context-managing class | State transitions can be enforced | A function plus context manager is clearer |
| Related policies | Module | Simple namespace and packaging unit | Independent deployment/version ownership emerges |

A raw mapping is appropriate at an untrusted parsing boundary. Convert it once to
a validated internal representation. Do not pass schema-less dictionaries through
every module, but also do not create a class for each pipeline verb.

## Architecture and dependency direction

Policy modules depend on internal value types and small protocols. File, API,
database, and framework adapters depend inward on policy, not the reverse.
Configuration and time/cutoff are values passed into the operation. Import-time
environment reads, network clients, and mutable caches make tests and worker
startup nondeterministic.

Keep modules cohesive around data contracts: parsing, validation, normalization,
and publication are different failure and ownership boundaries. A public package
API should be smaller than its internal module graph. Avoid circular imports;
they often signal unclear ownership rather than a mere import-order inconvenience.

## Lifecycle, serialization, and process boundaries

Dataclass equality compares declared fields by default, which may not match
business identity. Deduplication should use an explicit `event_id`, not entire
object equality. Field order and Python pickle layout are not durable cross-system
schemas. Serialize using an explicit versioned format at a boundary.

Functions sent to worker processes and their arguments must meet the selected
start method and serializer constraints. Nested functions, captured clients, and
open handles are poor process tasks. Pass small immutable configuration and open
resources inside the owning worker lifecycle.

## Failure model and recovery

| Failure | Detection | Containment/recovery |
| --- | --- | --- |
| Hidden clock/config changes result | Determinism test | Pass cutoff/config explicitly; version and rerun |
| Shared mutable dependency leaks state | Order/randomized tests | Scope dependency per run or synchronize owned state |
| Import performs I/O/fails | Clean-process import test | Move work to explicit entry point |
| Dataclass equality used as identity | Reconciliation mismatch | Deduplicate by named stable key; backfill |
| Adapter exception leaks partial output | Missing commit marker | Abort staging; retry from immutable input |
| Process cannot serialize task | Worker startup/task error | Use top-level callable and serializable values |

The orchestration shell owns retry. Pure policy can be retried freely; adapters
must declare whether operations are idempotent and where commits occur.

## Security, quality, and observability

Protocols should expose narrow capabilities: a reader need not receive delete or
administrative credentials. Never load a class or module name directly from
untrusted data. Treat plugin discovery and dynamic imports as code execution and
control their allowlist and supply chain.

Tests cover pure rules with tables/properties, adapters with real boundary
integration, and dependency direction with import/static checks where useful.
Operational events belong in the impure shell and carry run, dataset, schema, and
bounded rule identifiers—not raw payloads or per-event metric labels.

| Evidence | Expected result | Result |
| --- | --- | --- |
| Pure transform unit/property tests | Deterministic, identity-preserving, non-mutating | Pending |
| Static type check | Protocol and public API mismatches rejected | Pending |
| Clean-process package import | No I/O or configuration side effect | Package smoke test only |
| Real adapter fault test | Partial staging hidden and replay converges | Pending |

## Debugging and production considerations

Trace an incorrect value from publisher to pure policy to adapter, recording code,
configuration, schema, and dataset versions. Reproduce the policy with a minimal
value before replaying I/O. If behavior depends on test order or worker count,
inspect globals, default arguments, caches, and shared dependencies.

Small records may be dominated by Python object overhead and allocation. Measure
before adding `slots`, pooling, caching, or vectorization. Abstractions have a
runtime and cognitive cost; retain one when it enforces a contract or isolates a
real boundary. Deploy additive public API/schema changes first, support mixed
versions through retention, backfill with versioned policy, then remove old paths.

## Working example

- Planned modules: parser, models, validation, normalization, and publication ports
- Current artifact: The boundary and `Event`/`normalize` design above
- Expected result: Same values for fixed inputs/configuration with no input mutation
- Remaining risk: Implementation, type checker, adapter, serialization, and scale evidence

## Knowledge check

1. Decide whether a timestamp normalizer should be a function, class, or protocol.
2. Explain why a frozen dataclass containing a list is not deeply immutable.
3. Refactor a transform that reads environment and current time inside its loop.
4. Design a protocol granting a publisher only stage, commit, and abort capabilities.
5. Plan an additive model-field rollout across old and new workers.

## Key takeaways

- Pure transformations make reruns, tests, and repair easier to reason about.
- Use classes for protected invariants/lifecycles, not ceremonial layering.
- Protocols describe developer contracts; validation protects data boundaries.
- Business identity must be explicit even when records provide value equality.
- Modules and public APIs are compatibility and ownership boundaries.

## Resources

- [Python 3.12 functions](https://docs.python.org/3.12/tutorial/controlflow.html#defining-functions)
- [Python 3.12 dataclasses](https://docs.python.org/3.12/library/dataclasses.html)
- [Python typing protocols](https://typing.python.org/en/latest/spec/protocol.html)
- [Python 3.12 import system](https://docs.python.org/3.12/reference/import.html)

## Related topics

- [Area README](README.md)
- [Type hints, validation, and untrusted data](05-type-hints-validation-and-untrusted-data.md)
- [Errors, context managers, and resource lifetime](04-errors-context-managers-and-resource-lifetime.md)

## Completion checklist

- [x] Boundary choices, dependency direction, ownership, lifecycle, and failure covered
- [x] Kotlin analogy and limits, security, evidence, operations, and evolution included
- [ ] Reference modules and tests implemented
- [ ] Static, adapter, and process-boundary evidence executed

