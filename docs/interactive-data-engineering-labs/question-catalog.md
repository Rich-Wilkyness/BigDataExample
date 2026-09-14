# Interactive Data Engineering Lab Question Catalog

> Status: Parsed organizational inventory; first worked exercise implemented and verified
> Raw intake: [`question-dump.md`](question-dump.md)
> Scope: Derivative, job-shaped practice labs; not completed interview answers

## Intake summary

The raw intake contains 40 retained entries: 21 labeled Easy, 17 labeled Medium, and 2 labeled Hard. Stable catalog IDs below use the encounter order in the original dump rather than trusting its original numbering. The raw wording remains unchanged except for correcting the duplicate Easy `11`, renumbering the following Easy headings, and removing the former Easy `22` after the user confirmed it duplicated Easy `13`. This catalog summarizes concepts and proposed reuse without answering the questions. High-Engagement Video Filtering is cataloged separately from its existing notebook, bringing the working inventory to 41 exercises.

The user supplied the raw material directly, so a source URL is not required for this private practice workflow. Data Vidhya remains source context rather than the organizing hierarchy for the derivative labs.

## Contract issues to resolve

| Issue | Affected entries | Disposition before implementation |
| --- | --- | --- |
| Expected percentage contradicts its own explanation | `DV-M08` | The user confirmed the paste matches the site. Preserve the raw intake, but use a coherent derivative fixture where 2 of 3 users qualify and the expected result is `66.67`. |
| Expected customer is absent from the supplied inputs | `DV-M11` | The user confirmed the incomplete example is not important. Preserve the raw intake, but use `Alice` as the only qualifying shopper in the derivative fixture and expected result. |
| Title does not match the requested calculation | `DV-H02` | Rename from manufacturing defect rate to category revenue ranking unless a real defect-rate contract is supplied. |
| Execution language conflicts with the planned PySpark track | `DV-H01` and several SQL/Pandas stubs | Normalize the primary exercise mode while preserving intentional SQL-versus-PySpark comparison variants. |
| Encoding artifacts appear in copied prose | Multiple entries | Normalize mojibake such as `â€”`, `â€™`, and `â†’` only in derivative prompts; keep raw intake intact. |
| Vague `Handle NULL values appropriately` requirements | Multiple entries | Replace with explicit field-level null policy, quarantine behavior, or aggregate semantics. |

## Content platform scenario

This scenario can share users, synthetic video metadata, creators, posts, messages, ratings, views, and moderation flags. No video or other media binary is required. The existing high-engagement-video notebook is the proposed first complete example.

| ID | Raw label | Source title | Durable transformation concept | Proposed job-shaped checkpoint |
| --- | --- | --- | --- | --- |
| DV-E01 | Easy 1 | Social Media PII Extraction | Parsing, casting, masking, and privacy boundaries | Produce a privacy-safe silver user dimension from text-only contact records. |
| DV-E02 | Easy 2 | Social Media Text Correction | Deterministic text normalization | Apply a versioned product-name correction while preserving raw post text in bronze. |
| DV-E04 | Easy 4 | Research Paper Citation Analysis | Validating references and row numbering within groups | Adapt authors/papers into creator/video contributors and assign deterministic contributor positions. |
| DV-E07 | Easy 7 | Post Frequency Gap Analysis | Time filtering, cardinality qualification, and date differences | Build a gold user-post-span metric for a closed calendar year. |
| DV-E08 | Easy 8 | Most Active Team Members | Time-bounded aggregation and top-N selection | Rank message senders for a declared reporting interval with deterministic tie handling. |
| DV-E11 | Easy 11a | Duplicate Email Removal | Business-key deduplication with deterministic survivorship | Deduplicate identity records while retaining raw duplicates and recording the survivor rule. |
| DV-E14 | Easy 14 | Self-Viewing Authors Detection | Predicate filtering and distinct entity output | Detect creators viewing their own content without double-counting repeat views. |
| DV-E21 | Easy 21 | Data Cleaning - User Flags Validation | Required-field validation, quarantine, and aggregation | Split valid and rejected moderation flags, then publish valid-flag counts. |
| DV-M04 | Medium 4 | Top Film Reviewer & Best Movie | Independent aggregates, tie-breaking, and shaped union output | Publish reviewer-activity and title-quality highlights from the same ratings fact. |
| DV-M07 | Medium 7 | Longest Customer Visit Streaks | Gaps-and-islands over deduplicated dates | Compute longest consecutive engagement streaks after normalizing multiple same-day events. |
| DV-E23 | Existing notebook | High-Engagement Video Filtering | Typed filtering, exact projection, and deterministic ordering | Implemented and verified as the first guided Easy technique lab with synthetic metadata, reusable code, tests, and a separate explanation. |

## Commerce and subscription scenario

This scenario can share customers, products, orders, order items, inventory snapshots, reviews, and subscriptions.

| ID | Raw label | Source title | Durable transformation concept | Proposed job-shaped checkpoint |
| --- | --- | --- | --- | --- |
| DV-E06 | Easy 6 | Monthly Average Rating Tracker | Calendar derivation, grouping, averages, and decimal rounding | Publish monthly product-rating metrics from review events. |
| DV-E20 | Easy 20 | Active Subscription Amount Summary | Status filtering and decimal derivation | Build a current active-subscription export with an explicitly defined as-of contract. |
| DV-M01 | Medium 1 | CRM Order Summary Report | Multi-table joins and consumer-facing projection | Build a silver order view from customer, order, and product sources. |
| DV-M02 | Medium 2 | F&B Product Sales Summary | Independent pre-aggregation before joining multiple one-to-many facts | Publish product sales and inventory without sales-by-stock fan-out. |
| DV-M10 | Medium 10 | Repeat Customer Identification | First-event comparison and distinct qualification | Publish repeat-purchaser counts using calendar-date semantics. |
| DV-M11 | Medium 11 | Consistent Monthly Shoppers | Conditional period aggregation and multi-period qualification | Identify customers meeting activity thresholds in both reporting years after repairing the fixture. |
| DV-M13 | Medium 13 | Second Purchase Amount and Time Gap | Deterministic event sequencing and lag measurement | Build a second-purchase retention feature with same-day tie handling. |
| DV-M14 | Medium 14 | Deduplication with Composite Key | Composite-key survivorship and integer arithmetic | Deduplicate order records by customer and product before deriving downstream metrics. |
| DV-M15 | Medium 15 | Find N-th Record in Each Group | Positional window selection | Select a configurable N-th transaction per customer and reject invalid N values explicitly. |

## Financial and time-series scenario

This scenario can share accounts, account-status snapshots, transactions, and daily financial aggregates.

| ID | Raw label | Source title | Durable transformation concept | Proposed job-shaped checkpoint |
| --- | --- | --- | --- | --- |
| DV-E19 | Easy 19 | Revenue Range (Max Minus Min) | Global extrema and decimal arithmetic | Publish a daily or monthly revenue-range quality metric. |
| DV-M06 | Medium 6 | Monthly Account Closure Rate | Cohort denominator, state transition, and percentage calculation | Measure next-day closure for accounts open at the prior snapshot boundary. |
| DV-M09 | Medium 9 | Last Transaction of Each Day | Latest-row selection per calendar day | Create an end-of-day transaction marker with deterministic same-timestamp handling. |
| DV-M16 | Medium 16 | Moving Sum vs Moving Average Comparison | Bounded row windows | Publish rolling revenue measures while distinguishing row windows from calendar intervals. |
| DV-M17 | Medium 17 | Correlated Subquery for Running Calculations | Cumulative aggregation | Produce a running financial total and compare window and correlated-query plans. |

## Workforce and operational systems scenario

This scenario can share employees, departments, role history, support customers and calls, capacity queues, and device telemetry. Operational telemetry may ultimately deserve its own scenario if the inventory grows.

| ID | Raw label | Source title | Durable transformation concept | Proposed job-shaped checkpoint |
| --- | --- | --- | --- | --- |
| DV-E03 | Easy 3 | Call Center Performance Metrics | Valid-reference join, text casting, distinct count, and sum | Validate a text-only call feed against the customer dimension and publish daily staffing metrics. |
| DV-E16 | Easy 16 | Department Salary Sum | Global aggregation | Produce a payroll-control total used for source-to-target reconciliation. |
| DV-E17 | Easy 17 | Highest Paid per Department | Group maximum | Publish department compensation benchmarks without returning arbitrary employee rows. |
| DV-E18 | Easy 18 | Sports Match Score Summary | Conditional text derivation | Adapt into a human-readable pipeline-run outcome field or retain as a small standalone expression drill. |
| DV-M03 | Medium 3 | Maximum Boarding Capacity | Ordered cumulative sum and capacity cutoff | Model an ordered work queue that admits records until a batch capacity limit is reached. |
| DV-M05 | Medium 5 | Salary Outlier Detection | Global extrema with all ties retained | Publish all employees at compensation boundaries with deterministic labels. |
| DV-M08 | Medium 8 | Employee Career Progression Tracker | Sequencing, direct transitions, and population percentages | Detect direct role transitions after correcting the contradictory expected result. |
| DV-M12 | Medium 12 | Top Traffic Source Devices | Half-open time filtering and two-level aggregation | Aggregate device packets within an exact capture window and retain the maximum device count per network. |

## Product, portfolio, and regulated-data scenario

This scenario can share manufacturers, products, sales, costs, regional customer feeds, measurable product attributes, and asset portfolios.

| ID | Raw label | Source title | Durable transformation concept | Proposed job-shaped checkpoint |
| --- | --- | --- | --- | --- |
| DV-E05 | Easy 5 | Insurance Customer Data Merge | Append semantics and source consolidation | Union regional customer deliveries with source lineage and duplicate-preservation checks. |
| DV-E09 | Easy 9 | Leading Manufacturer Sales | Aggregation, scaling, rounding, and presentation formatting | Publish manufacturer sales while retaining a numeric metric separately from display text. |
| DV-E10 | Easy 10 | Pharmaceutical Loss Summary | Row-level loss classification and grouped financial aggregation | Build a manufacturer loss-risk mart from product sales and cost facts. |
| DV-E15 | Easy 15 | Wine Selection Filter | Multi-column decimal predicates and boundary behavior | Adapt into product quality qualification using explicitly typed laboratory measurements. |
| DV-H01 | Hard 1 | Property Rental Revenue Analysis | Dimension-to-fact join and portfolio aggregation | Build an asset-owner portfolio mart; reclassify difficulty unless operational requirements are added. |
| DV-H02 | Hard 2 | Manufacturing Defect Rate Analysis | Joined category ranking with ties | Rename to category revenue ranking or redesign around actual manufacturing defects. |

## Reference and standalone drills

These entries do not yet justify dedicated domain datasets. They can be consolidated, adapted into a core scenario, or retained as small isolated drills.

| ID | Raw label | Source title | Durable transformation concept | Proposed disposition |
| --- | --- | --- | --- | --- |
| DV-E12 | Easy 12 | Student Exam Participation Report | Cartesian coverage grid, left join, and zero-filled counts | Retain as the clearest exercise for complete dimensional coverage unless adapted to customers × offered products. |
| DV-E13 | Easy 13 | Large Country Identification | Inclusive OR predicates | Retain as the single inclusive-threshold exercise; adapt to eligible operating markets if included in a core scenario. |

## Cross-cutting skill inventory

| Skill family | Representative entries | Dataset implications |
| --- | --- | --- |
| Ingestion and raw contracts | `DV-E01`, `DV-E03`, `DV-E05`, `DV-E21` | Text-only feeds, source metadata, malformed rows, duplicate deliveries, and quarantine reasons are required. |
| Filtering and projection | `DV-E13`, `DV-E15`, `DV-E20` | Include exact threshold values, nulls, and rows satisfying each individual branch and all branches. |
| Aggregation and reconciliation | `DV-E03`, `DV-E06`, `DV-E09`, `DV-E10`, `DV-E16`, `DV-E19` | Preserve source totals and provide expected control totals at raw, accepted, rejected, and published boundaries. |
| Joins and cardinality | `DV-E03`, `DV-E04`, `DV-E12`, `DV-M01`, `DV-M02`, `DV-H01`, `DV-H02` | Include missing dimensions, duplicate dimension keys, zero-activity entities, and multiple fact rows to expose fan-out. |
| Deduplication and identity | `DV-E11`, `DV-M14` | Include exact duplicates, conflicting duplicates, composite keys, null keys, and deterministic ingestion metadata. |
| Time and sequencing | `DV-E07`, `DV-E08`, `DV-M03`, `DV-M06`, `DV-M09`, `DV-M10`, `DV-M13`, `DV-M15` | Include boundary timestamps, same-time ties, same-day repeats, out-of-order arrival, and multiple delivery dates. |
| Analytical windows | `DV-E04`, `DV-M03`, `DV-M07`, `DV-M08`, `DV-M09`, `DV-M13`, `DV-M15`, `DV-M16`, `DV-M17`, `DV-H02` | Provide stable tie-break keys and enough rows per partition to exercise empty, singleton, tied, and long groups. |
| Privacy and governance | `DV-E01`, `DV-E21` | Separate raw restricted fields from masked analytical fields and make rejected-record access explicit. |
| Pipeline operations | Derivative additions across all scenarios | Add batch identity, source file, ingestion timestamp, contract version, rerun behavior, and publication status beyond the source prompts. |

## Proposed next state

Do not generate all shared datasets directly from the raw examples yet. First resolve the listed contract defects, then use High-Engagement Video Filtering to build and evaluate one complete Easy technique lab. After its template is validated, design the content-platform scenario's canonical entities and delivery batches before scaling to the remaining notebooks, implementation files, or expected outputs.
