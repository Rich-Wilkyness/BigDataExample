# Integration, Contract, and End-to-End Pipeline Testing

> Status: Documentation complete; executable integration evidence planned  
> Level: Intermediate to Senior  
> Applies to: Databases / Brokers / Object stores / Engines / Orchestrators / Consumers  
> Data scale: Local service fixture; distributed and production estimate  
> Example status: Planned  
> Evidence status: Documentation and primary-source review only  
> Last reviewed: 2026-09

## Overview

Integration tests verify behavior across a real implementation boundary. Contract
tests verify that a provider and consumer still agree on selected interactions.
End-to-end tests verify a critical consumer outcome across a deployed path. The
scopes overlap, but they answer different questions and fail at different costs.

A realistic container or test database improves fidelity only for the boundary
it actually includes. It does not become distributed, failover, security, or
production evidence by resemblance.

## Learning objectives

- Choose the smallest test scope capable of exposing a named risk.
- Verify real SQL, serialization, storage, broker, orchestration, and consumer boundaries.
- Design provider and consumer contract matrices for mixed versions.
- Test ambiguous commits, retries, partial publication, and recovery.
- Build a layered suite with useful diagnostics and bounded runtime.

## Prerequisites

- [Schema, data, and consumer contracts](02-schema-data-and-consumer-contracts.md).
- [Unit, property, and SQL testing](03-unit-property-and-sql-transformation-testing.md).
- Areas 07–12 for batch, failure, streaming, storage, and orchestration boundaries.

## Mental model and terminology

```text
logic test -> one real boundary -> provider/consumer agreement -> critical journey
   cheap          integration             contract                end to end
   precise        boundary fidelity       version matrix          broad outcome
```

| Term | Meaning in this guide |
| --- | --- |
| Integration test | Exercises two or more real components across an implementation boundary |
| Contract test | Verifies an agreed set of provider/consumer inputs, outputs, and failure behavior |
| End-to-end test | Exercises a critical outcome through the deployed pipeline and consumer boundary |
| Test double | Substitute with deliberately narrower behavior than the real dependency |
| Hermetic | Controls all relevant inputs/dependencies for repeatability; degree, not magic label |
| Fault injection | Deliberately creates a failure at a named boundary and observes containment/recovery |

This resembles Android instrumentation versus JVM tests: select fidelity based
on risk. The analogy stops because pipelines may publish durable effects, span
many processes and time intervals, and require cleanup/reconciliation after a
test fails halfway.

## Requirements, scale assumptions, and invariants

- Each test names the exact risk, real boundaries, substituted boundaries, and
  evidence classification.
- Test data and target namespaces are isolated by run ID; parallel tests cannot
  read, overwrite, or certify each other's outputs.
- Set-up and clean-up are idempotent, but cleanup never hides the primary failure.
- A task success state is insufficient: end-to-end success requires the expected
  certified dataset version and consumer-visible values.
- Retry tests inspect durable effects after every crash point, including an
  unknown commit response.
- Provider/consumer matrices include all supported deployed and replay versions.
- Secrets and production records are excluded; least-privilege test identities
  prove negative access as well as allowed access.
- Estimated workload is one bounded interval for integration and a tiny critical
  journey for end-to-end; production is 3 million events/day. Multi-node,
  failover, and production scale require separate environments.

## Scope decision table

| Risk | Preferred first test | Why | Escalate when |
| --- | --- | --- | --- |
| Pure mapping edge | Unit/property | Fast, precise oracle | Engine semantics participate |
| SQL `NULL`/transaction behavior | Real database integration | Double may differ from dialect | Concurrency/failover matters |
| Producer-reader version mismatch | Contract matrix | Targets interface combinations | Broker/wire configuration matters |
| Object publication atomicity | Real object/catalog integration + fault | Exercises conditional write/list/read | Regional consistency/failover matters |
| Workflow produces dashboard result | One end-to-end critical journey | Verifies connected outcome | Scale or rare faults matter |
| Worker loss and replay | Distributed fault test | Needs multiple failure domains | Disaster recovery requires larger rehearsal |

## Reference test architecture

```text
isolated input namespace
       |
       v
real ingestion boundary -> real raw storage -> pinned transform engine
       |                                           |
       v                                           v
rejection assertions                      candidate publication
                                                   |
                                         injected check failure
                                                   |
                                                   v
                                   prior certified version remains
                                                   |
                                           repair and rerun
                                                   v
                                      consumer query assertion
```

An integration test can stop at one arrow. The end-to-end test uses the whole
critical path but keeps inputs tiny and assertions at business grain.

## Contract matrix

| Provider | Consumer | Payload/history | Expected result |
| --- | --- | --- | --- |
| Producer v1 | Ingestion v1 | v1 valid/invalid examples | Accept/reject with v1 reasons |
| Producer v1 | Ingestion v2 | v1 plus old retained messages | Compatible and same semantics |
| Producer v2 | Ingestion v1 | v2 optional extension | Accept only if unknown-field policy promises it |
| Producer v2 | Ingestion v2 | v1/v2 mixed and replayed | Both handled; version recorded |
| Metric old | Dashboard new | prior certified publication | Old definition remains interpretable |
| Metric new | Dashboard old | versioned successor | Old consumer stays on old contract until cutover |

Generated mocks from schemas can help setup but usually verify structural shape,
not consumer semantics. Keep independently reviewed examples for business rules.

## SQL and Python control models

```sql
-- End-to-end oracle at the consumer grain, not internal task state.
select tenant_id, product_id, metric_date, view_count, publication_id
from certified_daily_product_views
where publication_id = :expected_publication_id
order by tenant_id, product_id, metric_date;
```

Use bound parameters and explicit ordering for result presentation. Assert the
prior publication remains visible after a candidate fails quality checks.

```python
from contextlib import contextmanager
from uuid import uuid4

@contextmanager
def isolated_run(create_namespace, drop_namespace):
    run_id = f"quality_test_{uuid4().hex}"
    create_namespace(run_id)
    failure: BaseException | None = None
    try:
        yield run_id
    except BaseException as exc:
        failure = exc
        raise
    finally:
        try:
            drop_namespace(run_id)
        except BaseException:
            if failure is None:
                raise
            # Production test harness records cleanup failure without replacing
            # the original exception and run ID needed for investigation.
```

The harness owner manages namespace lifecycle. A real implementation also
records resources for later janitor cleanup if the test process dies.

## Data flow, ownership, and trust boundaries

| Boundary | Owner | Test assertion | Failure containment |
| --- | --- | --- | --- |
| Fixture to ingestion | Producer/ingestion | Wire bytes and stable outcome | Isolated source/topic/prefix |
| Engine to database/store | Pipeline/platform | Transaction/snapshot and values | Attempt-private target |
| Orchestrator to pipeline | Workflow owner | Interval, config, terminal state | Dedicated run and quotas |
| Quality gate to catalog | Dataset owner | Failed candidate never certifies | Conditional publication |
| Certified data to consumer | Consumer owner | Business-grain value/version | Dedicated consumer target |

## Lifecycle, consistency, identity, and time

Record run ID, fixture version, component versions, contract versions, interval,
clock/time zone, source positions, query/job IDs, candidate publication, and
cleanup disposition. Fixed event and readiness times make the test replayable.
Wait for an authoritative completion condition rather than sleeping; eventual
systems require a deadline and diagnostic polling state.

Parallel runs require unique namespaces and stable idempotency identities.
Reusing business keys is deliberate only when testing conflict or replay.

## Failure model and recovery

| Failure injected | Required observation | Recovery evidence |
| --- | --- | --- |
| Write succeeds, acknowledgement lost | Commit state is ambiguous; no blind duplicate | Inspect ledger/snapshot, retry idempotently |
| Worker dies after partial candidate | No candidate becomes certified | Resume/replace candidate, reconcile |
| Required quality check fails | Prior publication stays visible | Repair input/code and certify new version |
| Broker/database pauses | Bounded retry/backpressure, no test hang | Dependency restore and convergence by deadline |
| Cleanup process dies | Run resources discoverable by labels/ledger | Janitor removes exact expired namespace |
| Consumer unavailable | Data publication policy follows declared coupling | Retry consumer check or hold certification as designed |
| Mixed versions disagree | Compatibility gate blocks rollout | Restore supported pairing; fix and rerun matrix |

## Security, privacy, and governance

Provision short-lived least-privilege identities and test denied writes/reads.
Use synthetic, classified fixtures and isolated nonproduction destinations. Logs,
failure rows, traces, broker payloads, and retained resources follow the same
privacy policy. Container images, drivers, migrations, and fixtures are versioned
dependencies with provenance and vulnerability review.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Database integration | Faulty fixture / pinned real engine | Load, transform, assert, rollback/cleanup | Dialect and transaction behavior match contract | Pending |
| Contract matrix | v1/v2 examples / provider+consumer builds | Run supported pairings | Only declared combinations pass | Pending |
| End-to-end journey | Tiny isolated interval / deployed test stack | Ingest through consumer query | Correct certified outcome | Pending |
| Publication fault | Same stack | Fail required check and writer crash points | Prior version remains visible | Pending |
| Distributed/load | Production-shaped synthetic set | Multi-worker fault/load run | Meets recovery/window budgets | Pending |

## Debugging guide

1. Capture run/namespace, fixture, versions, interval, source positions, query/job IDs, publication, and trace links.
2. Find the first boundary whose authoritative input is correct and output is not.
3. Distinguish assertion failure, dependency failure, timeout, and harness/cleanup failure.
4. Preserve failed isolated resources within bounded retention when safe; do not expose payloads.
5. Reconcile durable state before retrying an ambiguous operation.
6. Repair, rerun the narrow test, then the contract matrix and critical journey.

## Common pitfalls

### Pitfall: mock every dependency in an integration test

The result is a slower unit test. Include the real boundary responsible for the
risk and label every substitute.

### Pitfall: one enormous end-to-end suite

Failures become slow and ambiguous. Keep few critical journeys and put detailed
edge coverage at lower layers.

### Pitfall: sleep until data is probably ready

Tests become slow and flaky. Poll an authoritative frontier or publication with
a deadline and emit the last observed state.

## Performance, capacity, and cost

Track setup, execution, convergence, and cleanup latency; flaky-rate; service
startup; fixture bytes/rows; queries and scans; resource leaks; parallelism; and
environment cost. Reuse shared infrastructure only when per-run data, identity,
and configuration isolation remain provable. Test suite throughput is not data
pipeline throughput.

## Compatibility, migration, and delivery

Pin engines, clients, schemas, migrations, configuration, and images. In CI run
static/unit tests, then affected integrations and contract matrices, then a small
critical journey. Before upgrades, dual-run supported versions and recovery
paths. Production deployment still needs canary quality receipts, rollback, and
post-release reconciliation.

## Working example

- Infrastructure: Planned pinned local database and optional broker/object-store test services
- Harness: Planned under `tests/integration/quality/`
- Fixtures: Planned versioned mobile-event scenarios under `data/fixtures/quality/`
- Try it: Planned repeatable provision/test/cleanup commands
- Expected result: Critical journey certifies exactly one correct publication; injected failures preserve the prior version
- Evidence: Planned service logs, contract matrix, query results, fault timeline, and cleanup ledger
- Scale represented: Local integration first; distributed/production explicitly separate
- Remaining risk: Failover, cloud control planes, multi-node behavior, production security, load, and cost

## Knowledge check

1. Explain which boundary makes a database test an integration test.
2. Predict the durable state after an acknowledgement is lost following commit.
3. Diagnose an end-to-end test that passes by checking only task status.
4. Design a v1/v2 provider-consumer matrix including retained history.
5. Estimate safe parallel namespaces and cleanup cost in CI.
6. Plan a database/engine upgrade evidence sequence and rollback.
7. Add one candidate-publication fault case to the planned harness.

## Key takeaways

- Test scope follows risk, not prestige.
- Real boundaries provide specific fidelity; label what remains simulated.
- Contract matrices make mixed-version promises executable.
- End-to-end success is a consumer-visible certified outcome, not task success.
- Durable effects require isolation, reconciliation, and recovery-aware cleanup.

## Resources

- [Python `unittest`: organizing test code and cleanup](https://docs.python.org/3/library/unittest.html) (reviewed 2026-09)
- [Testcontainers documentation](https://testcontainers.com/guides/) (reviewed 2026-09; optional implementation reference)
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09; engine-specific)

## Related topics

- [Unit, property, and SQL testing](03-unit-property-and-sql-transformation-testing.md)
- [Quality incidents and replay](07-quarantine-repair-replay-and-quality-incidents.md)
- [Area 12 workflow orchestration](../12-workflow-orchestration-and-transformation-management/README.md)

## Completion checklist

- [x] Integration, contract, end-to-end, double, fault, and isolation boundaries defined
- [x] Real service, mixed-version, ambiguous commit, cleanup, security, and recovery covered
- [x] Evidence classes and distributed/production limits explicit
- [x] Working example and executable evidence accurately marked Planned
- [ ] Service, contract, end-to-end, fault, distributed, load, and cleanup evidence executed

