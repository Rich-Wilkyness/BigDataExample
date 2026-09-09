# Fixtures, Golden Datasets, Sampling, and Determinism

> Status: Documentation complete; executable fixture evidence planned  
> Level: Beginner to Senior  
> Applies to: Python / SQL / Batch / Streaming / Test and diagnostic data  
> Data scale: Tiny deterministic fixtures; sampled and production estimates  
> Example status: Planned  
> Evidence status: Documentation and primary-source review only  
> Last reviewed: 2026-09

## Overview

A fixture is a controlled input with known provenance and expected behavior. A
golden dataset is a reviewed input/output corpus used as a regression oracle.
Sampling selects a subset for inspection or approximate monitoring. Determinism
means that fixed inputs and execution context produce reproducible results.

These tools reduce evidence cost, but each loses information. A golden file can
preserve a bug, a random sample can miss rare harm, and a fixed seed cannot make
an order-dependent distributed transform deterministic.

## Learning objectives

- Design a small portfolio covering representative and adversarial cases.
- Maintain golden outputs without rubber-stamp regeneration.
- Choose deterministic, stratified, reservoir, or hash-based samples deliberately.
- Control clocks, order, randomness, locale, engine, and reference snapshots.
- Protect privacy and provenance throughout fixture lifecycle.

## Prerequisites

- [Unit, property, and SQL testing](03-unit-property-and-sql-transformation-testing.md).
- [Integration and end-to-end testing](04-integration-contract-and-end-to-end-pipeline-testing.md).
- Area 04 file/serialization boundaries and Area 05 grain/identity.

## Mental model and terminology

```text
contract risks
   |-- minimal named fixture: explain one edge
   |-- generated cases: search a bounded domain
   |-- golden corpus: detect reviewed output drift
   |-- deterministic sample: inspect stable production-shaped slice
   `-- full/runtime checks: cover what subsets cannot
```

| Term | Meaning in this guide |
| --- | --- |
| Fixture | Versioned controlled test input plus provenance and intended assertions |
| Golden dataset | Reviewed input and expected output used as a regression oracle |
| Snapshot test | Compares a produced artifact with an approved stored representation |
| Deterministic sample | Membership is stable for a dataset/key and sampling version |
| Stratified sample | Samples separately within important segments |
| Reservoir sample | Maintains a bounded sample from a stream of unknown length |
| Seed | Initial random-generator state; only one part of reproducibility |

An Android screenshot golden is analogous to a dataset golden: it catches broad
changes cheaply but needs human review to distinguish intended change from
regression. Data goldens additionally require relational grain, ordering,
precision, time, and privacy decisions.

## Requirements, scale assumptions, and invariants

- Each fixture records an ID, contract/rule version, creation method, intended
  risk, classification, expected disposition, and review owner.
- The minimal portfolio includes empty input, one valid event, structural and
  semantic invalidity, exact and conflicting duplicates, `NULL` versus empty,
  Unicode, boundary offsets, late/out-of-order arrival, missing source segment,
  join fan-out, skew, partial publication, and replay.
- Golden relations state grain, column order, row comparison order, time zone,
  decimal precision, `NULL` representation, and serialization format.
- Golden regeneration is a reviewed semantic change; generated output never
  approves itself.
- Samples state population, unit, method, probability/rate, strata, seed/hash,
  version, and known blind spots.
- Sampling is never used to enforce zero-tolerance identity or privacy rules.
- Synthetic fixtures are preferred; any derived production example has recorded
  authorization, minimization, irreversible treatment where feasible, retention,
  and deletion lineage.
- Tiny fixtures prove logic only. The estimated production population is 3
  million events/day with rare errors below 0.1% and 35% tenant skew.

## Fixture portfolio

| Fixture | Purpose | Expected outcome | Limit |
| --- | --- | --- | --- |
| `minimal-valid-v1` | Smallest accepted product view | One validated event and metric increment | No multi-row behavior |
| `identity-failures-v1` | Missing/empty tenant/event IDs | Stable rejection reasons | Not completeness evidence |
| `duplicate-exact-and-conflict-v1` | Distinguish redelivery from contradiction | Exact copy deduped; conflict quarantined | Needs stable payload canonicalization |
| `utc-boundaries-v1` | Offset and half-open date assignment | Each event enters exactly one UTC date | Engine time-zone matrix still needed |
| `late-and-out-of-order-v1` | Arrival permutation/correction | Same final result within correction policy | Streaming watermark needs real engine |
| `missing-tenant-control-v1` | Global total hides tenant outage | Segmented reconciliation fails | Control authority is synthetic |
| `join-fanout-v1` | Nonunique dimension multiplies facts | Grain/reconciliation rules fail | Query plan/scale untested |
| `publication-failure-v1` | Candidate partially written | Prior certified version remains | Storage integration required |

## Golden dataset design

Store human-readable inputs and expected keyed relations when small. Separate
semantic goldens from incidental serialization: a changed file order should not
fail a relational oracle, while a file-format test should inspect bytes and
metadata intentionally.

```text
case directory
|-- manifest.json        # ID, purpose, versions, classification, provenance
|-- input-events.jsonl   # explicit input order when order is relevant
|-- expected-valid.jsonl
|-- expected-rejected.jsonl
`-- expected-metrics.csv # canonical column/row order for review
```

A review compares semantic diffs by business key and value. Wholesale
“update snapshots” after a failure destroys the oracle.

## Sampling models

```sql
-- Stable key-based diagnostic sample; hash syntax/range is engine-specific.
-- Sampling unit is logical event identity, preserving exact redeliveries together.
select *
from validated_events
where metric_date = :metric_date
  and mod(abs(stable_hash(tenant_id || ':' || event_id || ':sample-v1')), 1000) < 10;
```

This approximates a 1% stable sample if the hash is suitably uniform. Test hash
portability and the minimum signed value edge. Stratify by tenant, event type,
client/contract version, and rejection status when rare segments matter; weight
estimates when strata have different sampling probabilities.

For an independent Bernoulli sample with event probability `p`, the chance of
missing all `k` bad events is `(1-p)^k`. Rare or clustered failures can therefore
escape a seemingly large sample. Hash sampling by the wrong unit can also split
related records and hide duplicates.

```python
from hashlib import sha256

def in_stable_sample(tenant_id: str, event_id: str, per_million: int) -> bool:
    if not 0 <= per_million <= 1_000_000:
        raise ValueError("per_million out of range")
    key = f"sample-v1\0{tenant_id}\0{event_id}".encode("utf-8")
    bucket = int.from_bytes(sha256(key).digest()[:8], "big") % 1_000_000
    return bucket < per_million
```

This implementation is reproducible for the stated encoding and algorithm. It
is not a security anonymization mechanism; low-entropy IDs may be guessed.

## Determinism checklist

| Source of variation | Control or expose |
| --- | --- |
| Current time | Inject fixed clock and readiness frontier |
| Time zone/locale | Set explicitly and retain original offset where needed |
| Input/listing order | Sort by stable total key or define order independence |
| Duplicate tie | Use deterministic policy; quarantine unresolved conflict |
| Randomness | Record algorithm, seed, generator version, and parameters |
| Parallel floating aggregation | Use appropriate numeric semantics/tolerance and test partition changes |
| Reference data | Pin snapshot/version |
| Engine/library | Pin version and configuration; record plan where relevant |
| External service | Capture immutable response fixture only when contract permits; otherwise use integration evidence |

## Data flow, ownership, and trust boundaries

| Boundary | Authority/owner | Failure behavior | Trust level |
| --- | --- | --- | --- |
| Synthetic fixture source | Test/domain owner | Review generator and intent | Controlled, not real distribution |
| Sanitized example | Data owner/privacy reviewer | Reject unsafe derivation | Sensitive until proven otherwise |
| Golden expected output | Domain reviewer | Block unreviewed regeneration | Oracle with fallibility |
| Sample manifest | Dataset/quality owner | Treat missing method/version as invalid evidence | Derived diagnostic data |
| CI artifact store | Build/platform owner | Retain minimally and delete on schedule | Operational boundary |

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Golden contains old defect | Independent contract review/new oracle | Correct golden with reviewed explanation and regression |
| Fixture lacks rare segment | Incident/coverage inventory exposes gap | Add minimized synthetic case and track provenance |
| Sample drifts each run | Membership diff despite unchanged population | Pin stable method/version and keys |
| Seed replay differs | Dependency/algorithm/context changed | Record entire reproduction context and preserve minimized case |
| Snapshot diff is only ordering | Keyed relational comparison | Canonicalize presentation; test order separately |
| Production sample leaks PII | Classification/access scan | Revoke access, delete copies, report, replace synthetically |
| Test clock crosses midnight | Flaky date assertion | Inject time and use boundary fixtures |

## Security, privacy, and governance

“Test data” is not a lower classification. Avoid copying production payloads;
masking can retain linkability and rare combinations. Track provenance and
derived copies, restrict access, encrypt, expire, and honor source erasure where
applicable. Goldens and CI artifacts undergo secret scanning and review. Never
place raw quarantine records in a fixture bug report.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Manifest lint | Planned fixture portfolio / local | Validate IDs, purpose, versions, classification | Every case has complete provenance | Pending |
| Golden regression | Planned inputs/expected relations | Run reference transform and semantic diff | Exact reviewed outcomes | Pending |
| Deterministic rerun | Same fixture/context | Repeat and vary input partition/order as contract allows | Stable output or bounded expected variance | Pending |
| Sampling distribution | Synthetic skew/rare cases | Evaluate membership and weighted estimates | Declared strata represented; bias understood | Pending |
| Privacy review | Fixture/artifact inventory | Scan and trace provenance/deletion | No unauthorized sensitive data | Pending |

## Debugging guide

1. Capture fixture/sample ID, manifest, hash/generator version, seed, clock, engine, and reference snapshot.
2. Distinguish semantic output difference from row/file ordering or formatting.
3. Reproduce from immutable input, then minimize while preserving grain and failure.
4. Check whether the oracle, implementation, contract, or execution context changed.
5. Do not regenerate the golden until an owner approves the semantic diff.
6. Add the repaired counterexample and rerun determinism and privacy checks.

## Common pitfalls

### Pitfall: use one happy-path golden

It locks format but misses failure behavior. Maintain a small risk-indexed
portfolio with one reason for every case.

### Pitfall: call a random sample representative

Representativeness is relative to segments and outcomes. State selection
probabilities and test important rare strata deliberately.

### Pitfall: fixed seed means deterministic pipeline

Clock, order, engine, floating reduction, and reference state can still vary.
Record and control the full execution context.

## Performance, capacity, and cost

Track fixture bytes/rows, suite runtime, golden diff size, artifact retention,
sample scan cost, sample stability, segment coverage, and generator/shrink time.
Use tiny cases for logic, production-shaped synthetic distributions for plans and
capacity, and runtime checks for full populations when the risk requires them.

## Compatibility, migration, and delivery

Version fixtures with the contract they test. During migration run old data
through new readers and new data through supported old readers. Preserve old
goldens for retained history; add successor outputs for intentional semantics.
Review changes to hashing, serialization, clock, precision, and ordering as
evidence migrations, not cosmetic updates.

## Working example

- Fixtures/goldens: Planned under `data/fixtures/quality/mobile-events/`
- Manifest validation/sample helpers: Planned under `src/big_data_example/quality/`
- Tests: Planned under `tests/quality/`
- Try it: Planned standard-library deterministic fixture and sample suite
- Expected result: Named faults remain stable; sampling and reruns are reproducible
- Evidence: Planned semantic diffs, sample-distribution report, and privacy review
- Scale represented: Tiny local fixture plus synthetic distribution when implemented
- Remaining risk: Real production distribution, engine nondeterminism, privacy residual risk, and scale

## Knowledge check

1. Explain when a golden dataset is an oracle and when it merely copies behavior.
2. Predict why sampling rows instead of event identities can hide duplicates.
3. Diagnose a fixed-seed test that changes across time zones.
4. Design the minimum fixture for a conflicting duplicate.
5. Estimate the chance a 1% independent sample misses ten bad events.
6. Plan a semantic golden migration with retained v1 history.
7. Add a fixture manifest for the missing-tenant control case.

## Key takeaways

- A fixture portfolio is indexed by risks, not by volume.
- Golden updates require semantic review independent of generated output.
- Sampling always names population, unit, method, version, and blind spots.
- Reproducibility controls much more than a random seed.
- Test data retains privacy, provenance, retention, and deletion obligations.

## Resources

- [Python `random` reproducibility notes](https://docs.python.org/3/library/random.html#notes-on-reproducibility) (reviewed 2026-09)
- [NIST/SEMATECH e-Handbook: random sampling](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm) (reviewed 2026-09)
- [RFC 3339 timestamps](https://www.rfc-editor.org/rfc/rfc3339) (reviewed 2026-09)

## Related topics

- [Unit, property, and SQL testing](03-unit-property-and-sql-transformation-testing.md)
- [Reconciliation and distribution checks](06-reconciliation-freshness-volume-and-distribution-checks.md)
- [Area 04 storage and serialization](../04-data-storage-files-and-serialization/README.md)

## Completion checklist

- [x] Fixtures, goldens, snapshot review, sampling, determinism, and provenance explained
- [x] Identity, time, ordering, privacy, failure, scale, and migration covered
- [x] Sampling limitations and local-versus-production evidence explicit
- [x] Working example and executable evidence accurately marked Planned
- [ ] Fixture, golden, deterministic, sampling, privacy, engine, and scale evidence executed
