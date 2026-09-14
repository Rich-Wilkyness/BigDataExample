# Relational Modeling, Normalization, and Integrity

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Relational databases / SQL / Transactional authority  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Relational modeling represents facts as relations and uses keys, dependencies,
constraints, and transactions to keep authoritative state consistent.
Normalization separates facts that change for different reasons; integrity rules
reject states the business says are impossible.

This guide focuses on current operational product/order authority and the path
from functional dependencies to a normalized design. It does not claim that a
normalized write model is the best analytical serving model.

## Learning objectives

- Derive candidate keys and functional dependencies from business rules.
- Explain insertion, update, and deletion anomalies caused by mixed facts.
- Apply 1NF, 2NF, 3NF, and BCNF as reasoning tools rather than rituals.
- Place domain, entity, and relationship rules in appropriate constraints.
- Plan a safe normalization migration and prove preservation/reconciliation.

## Prerequisites

- [Requirements, grain, entities, and relationships](01-requirements-grain-entities-and-relationships.md)
- SQL keys, `NULL`, constraints, transactions, and concurrent change from area 03

## Mental model

A functional dependency `X -> Y` means that within the modeled business scope,
one value of X determines at most one value of Y. If product attributes and
category attributes are repeated in an order-line row, several independently
changing facts have been packed into one record. Normalization gives each fact
one authoritative place.

This resembles separating Room entities instead of embedding mutable profile
data into every transaction. The analogy stops because database constraints act
across concurrent writers and historical analytical copies may intentionally
denormalize after leaving the source-of-truth boundary.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Candidate key | Minimal attributes that uniquely identify a tuple |
| Functional dependency | Constraint that one attribute set determines another |
| Determinant | Left side of a functional dependency |
| Normal form | A structural condition that removes particular dependency anomalies |
| Referential integrity | Rule that a referencing value identifies an allowed parent row |
| Transactional authority | System that accepts/rejects current-state mutations atomically |

## Requirements and invariants

- A tenant's product SKU determines one current product, not a global product.
- An order line belongs to exactly one order and references one product captured
  under the order's tenant.
- Money uses an exact decimal amount plus currency; cross-currency totals require
  an explicit conversion contract.
- Quantity is positive for purchase lines; returns are separately typed business
  events rather than unexplained negative purchases.
- Database constraints are the final concurrency-safe enforcement point for
  invariants expressible within that authority.
- Analytical replicas may lag and cannot enforce source write integrity.

## Dependencies and normal forms

Suppose a draft row has key `(tenant_id, order_id, line_number)` and contains
`order_time`, `customer_id`, `product_sku`, `product_name`, `category_code`, and
`category_name`.

```text
(tenant_id, order_id) -> order_time, customer_id
(tenant_id, order_id, line_number) -> product_sku, quantity, unit_price
(tenant_id, product_sku) -> product_name
(tenant_id, category_code) -> category_name
```

Order attributes depend on only part of the composite line key; product and
category attributes depend on different determinants. Repetition permits one
order to acquire conflicting times or one SKU to acquire several current names.

- **1NF** requires scalar attributes from declared domains, not encoded lists or
  repeating column groups.
- **2NF** removes non-key attributes dependent on only part of a candidate key.
- **3NF** removes non-key facts transitively dependent on a key through another
  non-key fact.
- **BCNF** requires every nontrivial determinant to be a candidate key.

Higher normal form is not a score. Decomposition must be lossless, and important
dependencies should remain enforceable without unsafe application-only checks.

## SQL model sketch

PostgreSQL-style DDL; unexecuted. `NULL` means unknown/not present only where the
business contract allows it.

```sql
CREATE TABLE product (
    tenant_id     bigint NOT NULL,
    product_id    bigint GENERATED ALWAYS AS IDENTITY,
    product_sku   text NOT NULL,
    product_name  text NOT NULL,
    is_active     boolean NOT NULL DEFAULT true,
    PRIMARY KEY (tenant_id, product_id),
    UNIQUE (tenant_id, product_sku)
);

CREATE TABLE customer_order (
    tenant_id      bigint NOT NULL,
    order_id       text NOT NULL,
    customer_id    bigint,
    ordered_at     timestamptz NOT NULL,
    currency_code  text NOT NULL CHECK (currency_code ~ '^[A-Z]{3}$'),
    PRIMARY KEY (tenant_id, order_id)
);

CREATE TABLE order_line (
    tenant_id    bigint NOT NULL,
    order_id     text NOT NULL,
    line_number  integer NOT NULL CHECK (line_number > 0),
    product_id   bigint NOT NULL,
    quantity     bigint NOT NULL CHECK (quantity > 0),
    unit_price   numeric(19,4) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (tenant_id, order_id, line_number),
    FOREIGN KEY (tenant_id, order_id)
      REFERENCES customer_order (tenant_id, order_id),
    FOREIGN KEY (tenant_id, product_id)
      REFERENCES product (tenant_id, product_id)
);
```

Composite foreign keys prevent cross-tenant references. A `CHECK` constraint
cannot safely validate arbitrary other rows in PostgreSQL; cross-row rules need
keys, foreign keys, exclusion constraints, carefully owned triggers, or a
transactional workflow appropriate to the database.

## Integrity and transaction boundaries

| Rule | Preferred enforcement | Why |
| --- | --- | --- |
| Required scalar/domain | `NOT NULL`, type, `CHECK` | Applies to every writer |
| Candidate key | `UNIQUE`/`PRIMARY KEY` | Arbitrates concurrent claims |
| Parent relationship | Composite `FOREIGN KEY` | Prevents missing/cross-scope parent |
| Multi-row temporal exclusion | Engine-supported exclusion/range rule | Needs concurrency-safe arbitration |
| External-system policy | Transactional service plus reconciliation | Database lacks authoritative context |

Application validation improves error messages but does not replace database
integrity when multiple writers race. Conversely, the database cannot determine
whether an external identifier was assigned to the correct real person.

## Data flow and ownership

The catalog owns current product mutation; order authority owns committed orders
and lines. Change capture and analytical pipelines are consumers. They preserve
source keys and versions, quarantine impossible states, and reconcile rather than
“repairing” authority privately. Denormalized facts/dimensions are derived outputs
with their own versioned publication boundary.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Concurrent duplicate SKU | Unique violation | Return conflict; caller rereads authority |
| Cross-tenant line reference | Composite FK violation | Reject transaction and correct input |
| Orphan after disabled checks/import | Anti-join integrity audit | Quarantine export; repair authority then re-extract |
| Partial normalization migration | Old/new count or checksum mismatch | Keep old readers; resume idempotent backfill |
| Cascade deletes required history | Audit/reconciliation gap | Restore; replace destructive cascade with lifecycle policy |

Unknown transaction outcome requires reading by idempotency/business key before
retry. Recovery evidence includes constraint state, transaction outcome, row-count
and amount reconciliation, and successful old/new reader behavior.

## Security, privacy, and governance

Grant mutation by owning aggregate/table, not blanket schema access. Keep tenant
scope in keys and access policies. Tokenize or separate customer identifiers,
audit privileged relationship changes, and define deletion versus legally retained
transaction facts. Constraints can prevent cross-tenant foreign keys but do not
alone provide row-level authorization.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Constraint fixture | Null, duplicate, domain, and orphan mutations fail | Pending |
| Concurrent key claim | Exactly one transaction owns a tenant SKU | Pending |
| Lossless decomposition | Rejoin reproduces the intended source relation | Pending |
| Dependency mutation | Conflicting product/order attributes cannot persist | Pending |
| Migration reconciliation | Counts, keys, and monetary totals match old model | Pending |

## Common pitfalls

### Pitfall: normalizing values without modeling meaning

Moving status strings to a lookup table does not solve an unclear state machine.
Define allowed transitions, owners, and history requirements first.

### Pitfall: replacing composite scope with an unscoped foreign key

A globally unique surrogate may hide a tenant-isolation bug. Preserve scope in
constraints or prove and govern the global namespace.

### Pitfall: denormalizing authority for read speed prematurely

Repeated current attributes drift under concurrent updates. Measure the query,
then add a derived projection with refresh and reconciliation contracts.

## Performance, operations, and migration

Constraints add indexes, locking, and write cost; missing constraints transfer
cost to every consumer and repair. Measure key width, index bytes, write latency,
lock waits, cascade impact, query plans, and orphan/duplicate scans at realistic
cardinality.

Normalize with expand/migrate/contract: create new tables and constraints, dual-
read or controlled dual-write if necessary, backfill in bounded chunks, validate
dependencies and totals, switch readers, stop old writes, then remove old columns.
Rollback must account for writes accepted only by the new representation.

## Working example

- SQL/tests: planned PostgreSQL-compatible product/order DDL and anomaly fixtures
- Expected result: invalid states rejected and normalized rejoin reconciled
- Scale represented: none yet; database concurrency and plans unverified
- Remaining risk: engine-specific locking, online DDL, and source semantics

## Knowledge check

1. Derive the functional dependencies in the draft order-line relation.
2. Predict which anomalies remain after extracting only `product`.
3. Design a composite foreign key that prevents cross-tenant order lines.
4. Explain why application pre-check then insert cannot guarantee uniqueness.
5. Plan a lossless, rollback-aware migration to the sketched tables.
6. Add product aliases and decide their grain, key, and authority.

## Key takeaways

- Normalization separates facts with different determinants and lifecycles.
- Keys and constraints make business invariants executable at the authority.
- Tenant scope and exact money semantics belong in the key/domain contract.
- Operational normalized models and analytical models optimize different needs.
- Safe decomposition and migration require reconciliation, concurrency, and rollback evidence.

## Resources

- [PostgreSQL documentation: Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) (reviewed 2026-09)
- [PostgreSQL documentation: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09)

## Related topics

- [Requirements, grain, entities, and relationships](01-requirements-grain-entities-and-relationships.md)
- [Dimensional modeling: facts, dimensions, and stars](03-dimensional-modeling-facts-dimensions-and-stars.md)

## Completion checklist

- [x] Dependencies, normal forms, constraints, concurrency, and authority explained
- [x] Failure, security, performance, and migration boundaries addressed
- [ ] DDL, anomaly, concurrency, decomposition, and migration evidence run
