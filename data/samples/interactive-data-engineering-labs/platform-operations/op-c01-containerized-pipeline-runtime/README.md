# OP-C01 source delivery

| Contract field | Value |
| --- | --- |
| Delivery ID | `op-c01-sales-batch-001` |
| Source system | Synthetic retail point-of-sale export |
| Format | UTF-8 CSV with a header row |
| Record grain | One product transaction per `transaction_id` |
| Schema version | `1` |
| Expected counts | 8 received, 8 accepted, 0 rejected, 2 report categories |
| Intentional edge cases | None; data transformation is supplied because runtime setup is the exercise |
| Mutability | Immutable lab fixture |
| Origin and generation | Manually authored synthetic rows derived from the Week 2 weekend-project scenario |
| License | Repository-authored training fixture under the repository's license |
| Privacy | No real customer, transaction, or personal data |
| SHA-256 | `a8bf4c9a9d4d40781861d935aab28625041783bdf34632193a2ec79fe873b369` |

The learner must not modify this fixture during OP-C01. The file remains outside the pipeline image and enters its one-shot container through a read-only bind mount.
