# Interactive Lab Scenario Data Plan

> Status: Proposed shared-data organization derived from [`question-catalog.md`](question-catalog.md)
> Evidence boundary: One isolated DV-E23 technique fixture and contract are verified; reusable multi-question scenario deliveries remain planned

## Design objective

Use a small number of coherent business scenarios to support many exercises without making every question depend on one artificial universal schema. Each scenario owns immutable source deliveries, declared contracts, reusable edge cases, and generated bronze, silver, and gold outputs. Question-specific data should be an overlay only when the canonical scenario cannot express the required boundary case naturally.

## Physical layout

```text
data/
  samples/
    interactive-data-engineering-labs/
      content-platform/
        source/
          batch-001/
          batch-002/
          batch-003-schema-v2/
        reference/
      commerce-subscriptions/
        source/
        reference/
      financial-time-series/
        source/
        reference/
      workforce-operations/
        source/
        reference/
      product-portfolio/
        source/
        reference/
  staged/
    interactive-data-engineering-labs/
  curated/
    interactive-data-engineering-labs/

tests/fixtures/interactive-data-engineering-labs/
  <scenario>/<question-id>/expected/
```

Files under `data/samples/` are small, reviewed, immutable inputs. Bronze and silver outputs belong under ignored `data/staged/`; gold outputs belong under ignored `data/curated/`. Expected outputs should remain small and question-specific so one question does not silently depend on another question having run first.

## Shared delivery pattern

Each core scenario should eventually contain three reusable deliveries:

1. `batch-001` establishes valid baseline entities and events.
2. `batch-002` adds duplicates, late arrival, missing references, malformed values, and a corrected business record.
3. `batch-003-schema-v2` introduces one compatible field addition and one intentionally incompatible record for schema-evolution practice.

Every raw record should have or acquire `source_system`, `source_file`, `source_record_id`, `ingested_at`, `batch_id`, and `contract_version` metadata. These fields are pipeline concerns added by our labs; they need not appear in the source question schemas.

## Content platform data product

| Entity or event | Grain | Candidate source format | Reused by |
| --- | --- | --- | --- |
| Users | One source-system user version | CSV with text-only contact fields | PII masking, identity deduplication, user joins |
| Videos | One synthetic video metadata version; no media binary | CSV initially; JSON Lines for schema-v2 delivery | High engagement, creator portfolio, title/category filters |
| Viewing events | One view attempt | JSON Lines | Self-views, engagement, repeat activity, late data |
| Posts | One post version | JSON Lines | Text correction, yearly post span |
| Messages | One sent message | JSON Lines | Time-bounded sender activity |
| Ratings | One submitted rating event | JSON Lines | Monthly averages, reviewer/title highlights |
| Moderation flags | One submitted flag | JSON Lines with intentionally malformed rows | Validation, quarantine, valid counts |
| Creators and contributors | One creator plus one video-contributor relationship | CSV | Contributor order, creator portfolio metrics |

The bronze layer preserves source payloads and metadata. Silver separates valid typed users, content, and events from quarantined records and resolves deterministic identity. Gold publishes high-engagement videos, activity rankings, rating summaries, creator self-view alerts, and moderation metrics.

## Commerce and subscription data product

| Entity or event | Grain | Candidate source format | Reused by |
| --- | --- | --- | --- |
| Customers | One customer version | CSV from two named source systems | CRM joins, deleted/missing users, regional union |
| Products | One product version | CSV | Orders, ratings, inventory, category metrics |
| Orders | One order header | JSON Lines | First/second/N-th purchase questions |
| Order items | One product line within an order | JSON Lines | Revenue and quantity aggregation |
| Inventory snapshots | One product, warehouse, and snapshot time | CSV | Independent pre-aggregation and zero-activity products |
| Reviews | One submitted product review | JSON Lines | Monthly product rating metrics |
| Subscriptions | One subscription version or status event | JSON Lines | Active exports and as-of-state reasoning |

Bronze retains regional and delivery identity. Silver resolves customers and products, enforces order keys, separates duplicate/conflicting records, and normalizes timestamps and decimals. Gold publishes order summaries, product sales/inventory, repeat-customer measures, second-purchase features, and active subscriptions.

## Financial and time-series data product

| Entity or event | Grain | Candidate source format | Reused by |
| --- | --- | --- | --- |
| Accounts | One account | CSV | Account-status cohort denominator |
| Account status | One account observation per effective date | JSON Lines | Closure transition and snapshot correctness |
| Transactions | One financial transaction | JSON Lines | Latest transaction, positional selection, daily totals |
| Daily revenue | One business date after aggregation | Generated silver fixture | Range, moving windows, and running totals |

This scenario must use decimals rather than binary floating point, explicit reporting time zones, half-open time intervals, and deterministic tie-break keys. Gold outputs should include both human-facing measures and numeric values suitable for downstream calculations.

## Workforce and operational systems data product

| Entity or event | Grain | Candidate source format | Reused by |
| --- | --- | --- | --- |
| Employees | One employee version | CSV | Payroll reconciliation and compensation extrema |
| Departments | One department | CSV | Department benchmarks and missing-reference cases |
| Role history | One employee role interval | CSV | Direct career transitions and temporal validation |
| Support customers | One support customer | CSV | Valid-reference call aggregation |
| Calls | One call | Text-only CSV delivery | Casting, invalid customers, daily staffing metrics |
| Work queue | One ordered work item | JSON Lines | Cumulative capacity admission |
| Device packets | One observed packet | JSON Lines | Half-open windows and nested aggregation |

This scenario can remain combined while small. Split operational telemetry from workforce data if later questions introduce streaming ingestion, high volume, or network-specific contracts that would otherwise distort the employee dataset.

## Product, portfolio, and regulated-data product

| Entity or event | Grain | Candidate source format | Reused by |
| --- | --- | --- | --- |
| Manufacturers | One manufacturer | CSV | Product ownership and risk aggregation |
| Products | One manufactured product or drug | CSV | Sales, costs, quality measurements, rankings |
| Product financials | One product and reporting period | Parquet or CSV source variant | Sales totals, losses, and category ranks |
| Quality measurements | One sample measurement | CSV | Typed decimal qualification and future defect analysis |
| Regional customers | One source-system customer record | Two CSV deliveries | Append semantics, lineage, and cross-source duplicates |
| Asset owners and assets | One owner and one asset | CSV | Portfolio aggregation and missing-owner validation |

Sensitive or regulated fields should be synthetic and labeled as such. The lab should distinguish data classification and access boundaries from transformation correctness.

## Avoiding duplication

1. Reuse canonical base tables within a scenario, not across unrelated scenarios merely because columns have similar names.
2. Express boundary cases through reusable delivery batches before creating question-only files.
3. Keep expected results per question because different business contracts can legitimately interpret the same inputs differently.
4. Centralize schemas and fixture-location helpers in importable Python modules, while keeping pipeline transformations separate by lab.
5. Generate bronze, silver, and gold outputs during execution; do not commit a copy for every question.
6. Give each notebook an isolated output root based on its lab and question ID so reruns and parallel practice cannot overwrite another exercise.
7. Require every notebook to run from a clean kernel and clean generated-output directory without depending on another notebook's state.

## Decisions required before generation

1. Rename the permanent track to `interactive-data-engineering-labs`; confirmed by the user.
2. Treat the source-confirmed `DV-M08` and `DV-M11` inconsistencies as non-authoritative examples and define coherent synthetic contracts when those labs are implemented.
3. Use PySpark as the default implementation and introduce SQL as a parallel solution only when comparison teaches a material relational or planning concept.
4. Build High-Engagement Video Filtering as the first complete Easy technique lab using only synthetic structured metadata.
5. Evaluate that example's lab, solution, data, and test templates before generating the broader content-platform dataset.
