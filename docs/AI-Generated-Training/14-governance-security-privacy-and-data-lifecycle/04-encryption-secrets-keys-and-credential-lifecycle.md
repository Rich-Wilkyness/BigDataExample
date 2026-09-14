# Encryption, Secrets, Keys, and Credential Lifecycle

> Status: Documentation complete  
> Level: Intermediate to Senior  
> Applies to: Storage / Network / Data platforms / Batch / Streaming  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Encryption protects confidentiality and, with authenticated modes/protocols,
integrity across stated boundaries. A key-management system controls creation,
protection, use, rotation, revocation, archival, and destruction of keys. Secrets
and credentials authorize or bootstrap access and need an equally explicit
lifecycle. Encryption does not decide whether an authenticated consumer should
see plaintext.

This guide teaches architecture and verification, not custom cryptographic
implementation. Use reviewed libraries, protocols, managed key boundaries, and
qualified security guidance for concrete algorithm and parameter selection.

## Learning objectives

- Map plaintext and credential exposure across transit, storage, compute, logs, and recovery.
- Distinguish data-encryption keys, key-encryption keys, secrets, tokens, and identities.
- Design envelope encryption and rotation without rewriting every byte immediately.
- Verify revocation, recovery, and least-privilege key use.
- Diagnose secret leakage, wrong-key failures, downgrade, and ambiguous rotation.

## Prerequisites

- [Identity and least privilege](03-identity-rbac-abac-and-least-privilege.md).
- Planned local metadata model plus a real test key/secret service for integration evidence.

## Mental model and terminology

An Android Keystore analogy helps: application code requests a protected key
operation rather than shipping raw key material. The analogy stops at distributed
data: many workers, replicas, backups, regions, tenants, and historical files
must agree on key identifiers and rotation state.

```text
plaintext --encrypt with DEK--> ciphertext + algorithm/context/key_id
                    |
             DEK wrapped by KEK
                    |
          key service controls unwrap
```

| Term | Meaning |
| --- | --- |
| DEK | Data-encryption key used for data or a bounded group of objects |
| KEK | Key-encryption key that wraps/protects DEKs |
| Envelope encryption | Data encrypted by a DEK; DEK stored only in wrapped form |
| Secret | Sensitive value such as API credential, password, or signing material |
| Rotation | Introducing new key/credential use while retiring old use safely |
| Revocation | Preventing further authorized use before normal expiry |
| Crypto-shredding | Destroying key access so ciphertext is infeasible to decrypt; scope/proof must be explicit |

## Requirements, scale assumptions, and invariants

Inventory data class, plaintext locations, transit hops, cryptographic context,
key hierarchy, principal, region, rotation/revocation objective, recovery need,
and audit requirement. Assume 3 GiB/day, 35 hot days, 100 tenants, 200 workloads,
and millions of objects. Measure request rate, caching, provider quotas, latency,
and rewrite cost.

Invariants:

- No primary secret, private key, access token, or plaintext credential enters source, images, logs, lineage, or ordinary data tables.
- Data is protected in transit and at rest at every declared boundary, including staging, spill, backups, and exports.
- Ciphertext binds required context and detects unauthorized modification where the selected construction promises it.
- Key use is attributable and separated from ciphertext administration where risk requires.
- New writes use the active version; old reads follow an explicit bounded migration policy.
- Backup/restore includes key dependencies without creating an uncontrolled second key store.

## Data flow, ownership, and trust boundaries

| Boundary | Contract | Owner | Failure behavior | Trust |
| --- | --- | --- | --- | --- |
| Secret delivery | Workload identity, secret reference/version | Platform/security | No plaintext fallback | Privileged control plane |
| Key service | Key ID, operation, context, caller | Security/key owner | Bounded retry; never log material | High-value dependency |
| Worker memory | Plaintext/DEK lifetime | Workload owner | Clear references/buffers where feasible | Exposed compute boundary |
| Ciphertext store | Ciphertext, wrapped DEK, metadata | Storage owner | Reject corrupt/incomplete envelope | Untrusted for confidentiality |
| TLS endpoint | Peer identity, protocol, certificate | Network/service owners | Fail closed on verification | External boundary |

## Protection and lifecycle design

Prefer workload identity and short-lived tokens over distributed static secrets.
When a static credential is unavoidable, store only a reference in configuration,
deliver at runtime, limit audience and permissions, rotate, revoke, and scan for
exposure. A secret manager reduces distribution risk but cannot prevent an
authorized workload from leaking a retrieved value.

Envelope encryption limits key-service calls and supports rewrapping DEKs under a
new KEK without re-encrypting all data. Per-tenant or per-domain key separation
can narrow blast radius and support scoped destruction, but increases quotas,
metadata, recovery, and operational complexity.

### Metadata model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CiphertextEnvelope:
    key_id: str
    key_version: int
    algorithm_suite: str
    wrapped_dek: bytes
    nonce: bytes
    ciphertext: bytes
    context_version: int
```

This deliberately contains no implementation. Nonce uniqueness, algorithm
selection, authenticated context, error behavior, buffer lifetime, and key API
semantics must come from the selected reviewed construction and provider.

### SQL inventory model

```sql
SELECT key_id, key_version, COUNT(*) AS object_count,
       MIN(created_at_utc) AS oldest_object
FROM encrypted_object_inventory
GROUP BY key_id, key_version;
```

This supports rotation planning; it does not prove ciphertext correctness or that
inventory is complete. Reconcile with object storage and successful decrypt samples.

## Record, file, job, and key lifecycle

Create keys under approved policy; enable for scoped operations; rotate via
expand/migrate/contract; revoke on compromise; retain old decrypt authority only
as long as required; destroy after holds, recovery, and evidence requirements are
resolved. Jobs capture key version/context with output commits. Retries reuse the
same logical record identity but obey the library's nonce requirements; never
infer that deterministic retry permits nonce reuse.

Secret versions overlap briefly: deploy consumers able to use new material,
activate new producers, observe, revoke old, then prove no old use remains. Define
rollback before revocation because some credential rotations are not reversible.

## Failure model and recovery

| Failure | Detection/containment | Recovery and convergence |
| --- | --- | --- |
| Secret committed/logged | Scanner/alert; revoke immediately | Rotate, remove exposure, assess history and consumers |
| Key service outage/throttle | Dependency metrics; bounded cache and backoff | Restore; prove no plaintext fallback or partial publish |
| Wrong key/context/version | Authenticated-decrypt failure, quarantine | Repair metadata only from authority; never guess |
| Rotation leaves old writers | Version-use metrics and inventory | Fence old deployment; rewrite/rewrap; zero new old-version writes |
| Key destroyed too early | Restore/decrypt drill fails | Recover only from approved escrow if designed; otherwise data loss |
| Certificate validation disabled | Configuration/test gate | Restore verification; rotate exposed credentials; assess interception |
| Worker/core dump leaks plaintext | Hardened runtime and incident signal | Revoke affected authority; restrict dump; forensic review |

## Security, privacy, and governance

Threat-model storage operators, network attackers, compromised workloads,
administrators, snapshots, telemetry, and vendors. Least-privilege key operations
are preferable to broad key export. Separate key policy administrators from data
readers where feasible. Encryption can preserve sensitive data longer, so
retention and deletion still apply to ciphertext and key metadata.

## Data quality, testing, and evidence

| Evidence | Environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Known-answer/round-trip | Pinned reviewed library | Planned deterministic test vectors where supported | Compatible encrypt/decrypt and tamper failure | Pending |
| Negative secret scan | Repository/artifact/log fixture | Planned scanner rules | Seeded secrets found; safe refs allowed | Pending |
| Rotation | Real test key/secret service | Planned overlap/revoke drill | New writes/read compatibility; old use stops | Pending |
| Restore | Encrypted backup fixture | Planned restore with key dependency | Authorized restore succeeds; forbidden identity fails | Pending |
| Load/outage | Test service and workers | Quota/latency/fault test | Bounded behavior without unsafe fallback | Pending |

## Debugging guide

Use safe identifiers: object, dataset, tenant, key ID/version, algorithm suite,
context version, workload, deployment, request/correlation, provider error class,
and rotation phase. Never log secret values, plaintext, DEKs, non-redacted tokens,
or full envelopes. Distinguish authorization, provider availability, metadata
corruption, and cryptographic verification failures. Preserve ciphertext before repair.

## Common pitfalls

### Pitfall: encryption means authorized

Any workload with decrypt authority can misuse plaintext. Enforce identity,
purpose, row/column/tenant scope, and audit separately.

### Pitfall: one long-lived secret for every job

Compromise has platform-wide duration and scope. Use unique workload identities
and short-lived, audience-bound credentials.

### Pitfall: rotate by editing a value in place

Workers and historical objects disagree with no version or rollback. Use versioned
overlap, adoption telemetry, fencing, and explicit retirement.

## Performance, observability, and cost

Measure encrypt/decrypt throughput, key-service request latency/error/throttle,
cache lifetime/hit rate, ciphertext expansion, per-object metadata, rewrite/
rewrap bytes, rotation age, old-version writes, secret age, and certificate expiry.
Batch or locally generate DEKs only within the security design; never trade nonce
or key safety for throughput. Provider calls and per-tenant keys can dominate cost.

## Compatibility, migration, and delivery

Store algorithm suite, key ID/version, envelope/context version, and creation time
with ciphertext. Readers expand first, writers migrate second, historical data is
rewrapped/re-encrypted and reconciled, then old authority contracts. Algorithm or
provider migration needs cross-implementation fixtures and restore rehearsal.
Rollback cannot resurrect revoked compromised credentials.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Provider-managed keys | Operational simplicity | Provider/admin trust | Isolation/control requires customer-managed hierarchy |
| Per-domain/tenant keys | Blast-radius separation | Key count/quota/recovery | Risk is uniform and scale dominates |
| Rewrap DEK | KEK rotation only | Old data cipher unchanged | Algorithm/DEK compromise requires re-encryption |
| Short cache | Fast revocation | Key-service load | Outage objectives require bounded longer cache |

## Working example

- Models: Planned envelope/key inventory under `src/big_data_example/security/`
- Tests: Planned metadata, tamper, scanner, rotation, revoke, outage, and restore cases
- Integration: Planned real test key and secret service; no custom cipher code
- Expected result: Versioned rotation converges and forbidden/tampered use fails safely
- Scale represented: Local metadata fixture and production estimate
- Remaining risk: Provider semantics, memory exposure, quotas, cross-region recovery, and compromise response

## Knowledge check

1. Explain DEK, KEK, envelope encryption, secret, and credential.
2. Predict reads/writes during a two-version rotation.
3. Diagnose an authenticated-decrypt failure without logging sensitive material.
4. Design unique credentials for 200 workloads across dev/prod.
5. Estimate key-service requests with and without bounded DEK caching.
6. Plan provider migration including restore and rollback constraints.
7. Add an old-version writer detection check.

## Key takeaways

- Map plaintext, key, secret, and credential lifetime across every copy and boundary.
- Encryption complements rather than replaces authorization, purpose, and deletion.
- Versioned expand/migrate/contract makes rotation observable and recoverable.
- Unique short-lived workload identity reduces secret scope and duration.
- Recovery and revocation must be tested with the real key/secret boundary.

## Resources

- [NIST SP 800-57 Part 1 Rev. 5: Key Management](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final) (reviewed 2026-09; concrete cryptographic choices require current qualified review)
- [NIST Cryptographic Standards and Guidelines](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines) (reviewed 2026-09)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html) (reviewed 2026-09; implementation guidance)

## Related topics

- [Identity and least privilege](03-identity-rbac-abac-and-least-privilege.md)
- [Retention and deletion](06-retention-deletion-legal-holds-and-data-subject-workflows.md)
- [Audit evidence](07-audit-policy-enforcement-and-compliance-evidence.md)

## Completion checklist

- [x] Encryption, secrets, key hierarchy, identity, lifecycle, failure, recovery, scale, and migration covered
- [x] No unsafe custom cryptographic implementation presented
- [x] Working example accurately marked Planned
- [ ] Library, key/secret service, rotation, revocation, outage, load, restore, and production evidence executed

