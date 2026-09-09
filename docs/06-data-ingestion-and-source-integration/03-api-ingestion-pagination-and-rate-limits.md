# API Ingestion, Pagination, and Rate Limits

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate  
> Applies to: HTTP APIs / Batch and incremental ingestion  
> Data scale: Local test double; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

API ingestion converts a remote, mutable, rate-limited view into a durable local
history. Correctness depends on the API's snapshot, ordering, pagination, retry,
and deletion semantics—not on how quickly a client can issue requests.

This guide covers authentication, cursors, page traversal, quotas, retries,
incremental state, and ambiguous responses. General HTTP implementation and
downstream modeling are outside scope.

## Learning objectives

- State what population and consistency point a paginated run represents.
- Choose cursor, keyset, offset, or time-window traversal from source guarantees.
- Bound requests, memory, concurrency, and retry amplification.
- Commit incremental state only after durable page receipt.
- Detect missed, duplicated, changed, and deleted resources by reconciliation.

## Prerequisites

- [Ingestion contracts and raw-data ownership](01-ingestion-contracts-and-raw-data-ownership.md)
- SQL ordering/keyset concepts from area 03 and identity concepts from area 05

## Mental model and terminology

Pagination is iteration over a remote collection whose contents may change while
you read it. It resembles paging a Room query only if a transaction pins a
snapshot. Most APIs do not give that guarantee; inserts and deletes can shift
offsets between requests.

| Term | Meaning in this guide |
| --- | --- |
| Cursor | Opaque server-issued continuation state; its lifetime and snapshot semantics are contractual |
| Keyset | Resume predicate over a stable total order, such as `(updated_at, id)` |
| Watermark | Committed boundary through which the declared source scope was acquired |
| Retry budget | Bound on attempts, elapsed time, and amplified requests/bytes |
| Ambiguous outcome | Timeout/disconnect where the client cannot tell whether the server completed an operation |

## Requirements, assumptions, and invariants

Reference API: 100,000 catalog resources, up to 1,000 per page, 600 requests/minute,
15-minute freshness, UTC update timestamps, and a seven-day overlap/replay window.
The provider must document stable identity, ordering, cursor expiration, update
and delete visibility, quota scopes, and authentication lifecycle.

Invariants:

- A page token or next key advances only after page bytes and request metadata are durable.
- Traversal uses a documented stable order with a unique tie-breaker.
- Retries preserve the same logical request and remain within a bounded budget.
- `429`/throttling signals and server retry guidance constrain admission globally for the credential/quota scope.
- Incremental overlap may create duplicates; identity-based merge/reconciliation removes delivery effects.
- Secrets and sensitive response bodies never enter routine logs.

## Pagination and incremental strategies

| Source behavior | Strategy | Main risk |
| --- | --- | --- |
| Snapshot cursor with adequate lifetime | Follow opaque cursor; persist each response/token | Cursor expiry or undocumented snapshot loss |
| Stable total order and filter | Keyset `(updated_at, id) > (?, ?)` | Late/backdated changes outside overlap |
| Offset only over mutable set | Snapshot/export endpoint if possible | Shift causes skips or repeats |
| Updated-since without unique order | Overlap windows plus identity/version reconciliation | Equal timestamps and clock precision |
| Full listing is bounded | Periodic full snapshot and diff | Cost and delete semantics |

```python
while checkpoint.next_request is not None:
    response = client.fetch(checkpoint.next_request)
    receipt = raw_store.persist(response.body, request=response.request_meta)
    checkpoint = state.compare_and_advance(
        expected=checkpoint,
        next_request=response.next_request,
        receipt_id=receipt.id,
    )
```

The planned client streams bounded bodies, sets connect/read/total deadlines,
validates media type and status, honors server retry guidance, refreshes credentials
without duplicating work, and reads current state after an unknown checkpoint write.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Provider API | Versioned resource/page semantics | Provider | Throttle, error, expire cursor, or change data | External/untrusted |
| Credential/quota | Scoped token and shared limit | Security/provider | Refresh once; coordinate admission | Sensitive control state |
| Raw response | Request, status, headers subset, body, receipt | Ingestion owner | Persist before continuation | Receipt evidence |
| Checkpoint | Cursor/key/window after durable receipt | Ingestion owner | Conditional advance | Trusted control state |
| Accepted resource | One source ID/version | Contract owner | Validate, deduplicate, quarantine | Validated for declared use |

## Consistency, identity, time, and deletes

Capture request start/end, server date/version headers when useful, ingestion time,
source `updated_at`, resource version/ETag, and resource ID separately. A total
keyset order needs a unique tie-breaker; timestamps alone are insufficient.

Deletes require tombstones, an audit endpoint, or periodic full reconciliation.
Absence from one page is not deletion. For mutable listings, reread an overlap
behind the watermark and deduplicate by resource identity/version. Record the
coverage interval and the source consistency guarantee attached to it.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Cursor expires mid-run | Documented error/status | Restart pinned snapshot or bounded scope; do not splice incompatible scans |
| `429` or quota exhaustion | Status plus retry metadata | Pause shared limiter, add jitter, preserve checkpoint |
| `5xx`/timeout before response | Deadline/transport error | Retry idempotent read within budget; retain attempt lineage |
| Auth expires | `401`/token lifetime | Refresh once through credential owner; avoid infinite loops |
| Mutable offset shifts | Reconciliation/duplicate and missing IDs | Replace with snapshot/keyset or periodic full diff |
| Page persisted, checkpoint write unknown | Receipt exists but state uncertain | Read state, compare receipt/token, then advance or replay |
| Poison oversized response | Size/media/schema gate | Stop or quarantine under contract; never exhaust memory |

Recovery is complete when a declared source scope closes, pages and records
reconcile, and any tolerated source inconsistency is measured and documented.

## Security, privacy, and governance

Use TLS verification, allowlisted hosts and redirects, least-privilege short-lived
tokens, secret rotation, and safe proxy configuration. Prevent SSRF by keeping
continuation URLs within the approved origin and validating schemes/hosts. Bound
headers and bodies, reject unexpected content types, redact tokens/query PII, and
control raw/quarantine access and retention. Provider terms may constrain storage,
replay, and deletion.

## Data quality, testing, and evidence

| Evidence | Test-double scenario | Expected result | Result |
| --- | --- | --- | --- |
| Pagination | Empty, one page, ties, insert/delete between pages | Declared strategy has explained coverage | Pending |
| Restart | Fail after response persistence and state write | Replay or resume without unexplained loss | Pending |
| Rate limit | `429`, shared quota, jittered retry | Request rate remains bounded | Pending |
| Transport | Timeout, truncation, `5xx`, expired auth/cursor | Bounded classified recovery | Pending |
| Reconciliation | Full snapshot versus incremental output | Missing/extra/version differences reported | Pending |

A test double proves client logic, not provider behavior. Contract tests against a
sandbox and a production-safe reconciliation remain required.

## Common pitfalls

### Pitfall: `page += 1` over a mutable collection

Rows shift between offsets, causing gaps or repeats. Prefer provider snapshot
cursors, stable keyset traversal, or a full export.

### Pitfall: retrying every status immediately

Permanent validation/auth errors become a retry storm. Classify errors, cap the
budget, honor provider guidance, and coordinate the limiter across workers.

### Pitfall: setting the watermark to wall-clock now

Updates committed or indexed just behind that time may be missed. Advance only to
a proven source boundary and reread a measured overlap where needed.

## Performance, capacity, cost, and operations

At 1,000 records/page, 100,000 resources require at least 100 data requests plus
retries and metadata calls. Measure page/body-size distributions, latency
percentiles, records/request, quota remaining, retry amplification, auth refreshes,
ingestion lag, overlap duplicates, cursor age, checkpoint age, and reconciliation
differences. Limit concurrency by the narrowest provider, credential, network,
memory, and destination budget.

Runbooks distinguish provider outage, client defect, credential failure, and
poison response; pause safely, retain the checkpoint/receipts, and resume only
after estimating cursor lifetime and backlog drain rate.

## Compatibility, migration, and tradeoffs

Pin API/media/schema versions where offered. During migration, dual-read a bounded
scope, compare identities, versions, deletes, and values, cut over checkpoint
ownership atomically, and retain the old client for rollback until replay closes.

| Requirement | Prefer | Tradeoff |
| --- | --- | --- |
| Consistent large export | Provider snapshot/export job | Higher latency and job lifecycle |
| Low-latency incremental | Stable keyset/change endpoint | More state and late-change handling |
| Strong quota protection | Central token-bucket/admission control | Coordination dependency |
| Provider offers webhooks only | Treat webhook as hint; fetch/reconcile state | Extra reads but recoverable loss |

## Working example

- Python/tests: planned scripted HTTP double, durable page receipts, checkpoint store, and reconciliation report
- Expected result: inserts, throttles, timeouts, and restarts have explicit outcomes
- Scale represented: none yet; production estimate only
- Remaining risk: provider-specific consistency, quota, auth, and deletion behavior

## Knowledge check

1. Explain why `(updated_at, id)` is safer than `updated_at` alone.
2. Predict offset pagination after an item is inserted at the front.
3. Diagnose a persisted final page with an unchanged checkpoint.
4. Design a deletion strategy for an API that emits no tombstones.
5. Compute the minimum request count and quota time for the reference full scan.
6. Propose a v1-to-v2 dual-read and rollback plan.

## Key takeaways

- Pagination correctness comes from source snapshot and ordering guarantees.
- Persist page evidence before continuation state.
- Rate limiting is shared admission control, not just per-request sleep.
- Overlap plus identity handles retries; reconciliation detects omissions and deletes.
- A test double cannot certify a provider's real contract.

## Resources

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) (reviewed 2026-09)
- [RFC 6585: Additional HTTP Status Codes](https://www.rfc-editor.org/rfc/rfc6585) (reviewed 2026-09)

## Related topics

- [Database snapshots and incremental extracts](04-database-snapshots-and-incremental-extracts.md)
- [Validation, quarantine, and schema evolution](07-validation-quarantine-and-schema-evolution.md)
- [Idempotency, deduplication, late data, and reconciliation](08-idempotency-deduplication-late-data-and-reconciliation.md)

## Completion checklist

- [x] Pagination, rate limits, auth, incremental state, deletes, and ambiguity explained
- [x] Failure, security, capacity, observability, migration, and evidence addressed
- [ ] HTTP double, provider contract, restart, quota, and reconciliation evidence run
