# Interview prep workflow

> Status: Workflow and question-ingestion queue  
> Language scope: Python language/runtime and SQL language/query semantics  
> Platform scope: Data engineering, storage, processing, distributed systems, streaming, orchestration, governance, and operations  
> Completed language guide: [`LANGUAGE_INTERVIEW_QUESTIONS.md`](LANGUAGE_INTERVIEW_QUESTIONS.md)  
> Completed platform guide: [`PLATFORM_INTERVIEW_QUESTIONS.md`](PLATFORM_INTERVIEW_QUESTIONS.md)

This file owns source discovery, question ingestion, reusable stage prompts, and
the active queues. It does not hold completed interview answers. The canonical
answer structure lives in
[`INTERVIEW_QUESTION_TEMPLATE.md`](INTERVIEW_QUESTION_TEMPLATE.md).

You can add a bare question to either `Captured` queue at any time. Source and
context notes are optional for questions supplied directly by the user.

There is no fixed question limit. Prefer broad coverage during capture, careful
consolidation before answering, and durable understanding over trivia. If a
stage prompt does not specify `Language`, `Platform`, or `both`, process both.

> **Answer quality:** Lead with the durable, version-independent concept. Add
> engine-, product-, dialect-, or version-specific behavior only when it changes
> the answer. State the assumption and verify it with current primary
> documentation. Treat third-party interview lists as discovery sources rather
> than answer authorities: consolidate overlaps, paraphrase appropriately, and
> write original answers.

## Scope rules

- **Language** covers Python semantics and runtime behavior plus portable SQL and
  relational-query reasoning. Examples include Python typing, iteration, memory,
  concurrency, testing, SQL `NULL`, joins, aggregation, windows, transactions,
  and query semantics.
- **Platform** covers data-system architecture and operation. Examples include
  file formats, modeling, ingestion, ETL/ELT, Spark, Kafka, streaming, CDC,
  warehouses, lakes, lakehouses, orchestration, quality, governance, security,
  reliability, performance, cost, and senior system design.
- When a question crosses both scopes, place it where the interviewer's primary
  evaluation belongs. Avoid maintaining duplicate answers.
- Product-specific syntax belongs only when it exposes an enduring concept or is
  common enough to be an explicit interview expectation.

## Workflow at a glance

```text
Capture -> To Add / Captured
    -> Consolidate -> To Add / Ready to complete
    -> Complete -> LANGUAGE_INTERVIEW_QUESTIONS.md
                or PLATFORM_INTERVIEW_QUESTIONS.md
```

Run only one stage per request. This preserves the broad discovery inventory
before editorial decisions and keeps answer research separate from collection.

## Source registry

Register a source once and refer to its ID from captured questions. A source may
cover language questions, platform questions, or both.

Assign IDs sequentially as `S001`, `S002`, and so on. IDs are permanent: never
renumber or reuse an assigned ID. Remove the placeholder row when registering the
first source.

| ID | Scope | Source | Access | Last checked | Notes |
| --- | --- | --- | --- | --- | --- |
| S001 | Language | [Tarmac: Databases & SQL interview questions](https://gettarmac.com/interview-questions/databases-sql-interview-questions) | Public | 2026-09-09 | Inspected the public topic overview and ten visible practice-question families. |
| S002 | Both | [DataDriven 75: Awesome Data Engineering Interviews](https://github.com/datadriven-io/awesome-data-engineering-interviews) | Public | 2026-09-09 | Inspected the complete public 75-question index spanning SQL, Python/PySpark, modeling, and pipelines. |
| S003 | Platform | [OBenner data-engineering-interview-questions index](https://github.com/OBenner/data-engineering-interview-questions) | Public | 2026-09-09 | Inspected as a source-family index; topic files actually used are registered separately. |
| S004 | Platform | [Coursera: 14 Data Engineer Interview Questions](https://www.coursera.org/articles/data-engineer-interview-questions) | Public | 2026-09-09 | Inspected technical, project, and role questions visible without authentication. |
| S005 | Language | [Udacity: Python Interview Questions and Answers (2026)](https://www.udacity.com/blog/top-python-interview-questions-for-your-next-job-opportunity/) | Public | 2026-09-09 | Inspected core-language, runtime, concurrency, data-structure, and data-workload questions. |
| S006 | Both | [Dataquest: Python Interview Questions for Data Roles (2026)](https://www.dataquest.io/blog/python-interview-questions-and-answers/) | Public | 2026-09-09 | Inspected Python/runtime questions and practical data-engineering pipeline scenarios. |
| S007 | Platform | [Capco Digital: Data Engineering Interview Questions](https://github.com/capcodigital/interview-questions/blob/main/data-engineering.md) | Public | 2026-09-09 | Inspected the public hiring-assessment coverage rubric; it supplied coverage families rather than verbatim prompts. |
| S008 | Platform | [Educative: Data Engineer System Design Interview Questions](https://www.educative.io/blog/data-engineer-system-design-interview-questions) | Public | 2026-09-09 | Inspected end-to-end streaming, batch, warehouse/lakehouse, feature-store, metrics-platform, and CDC design families. |
| S009 | Both | [Reddit: Recent Senior Data Engineer interview](https://www.reddit.com/r/dataengineersindia/comments/1u8cubu/recently_interviewed_for_a_senior_data_engineer/) | Public | 2026-09-09 | Inspected the original interview report and its disclosed SQL and production-design prompts. |
| S010 | Platform | [OBenner: Apache Airflow questions](https://github.com/OBenner/data-engineering-interview-questions/blob/master/content/airflow.md) | Public | 2026-09-09 | Inspected the public question list and supporting page. |
| S011 | Platform | [OBenner: Apache Kafka questions](https://github.com/OBenner/data-engineering-interview-questions/blob/master/content/kafka.md) | Public | 2026-09-09 | Inspected the public question list and supporting page. |
| S012 | Platform | [OBenner: Apache Spark questions](https://github.com/OBenner/data-engineering-interview-questions/blob/master/content/spark.md) | Public | 2026-09-09 | Inspected the public question index; captured durable and operational families visible in the inspected portions. |
| S013 | Platform | [OBenner: Change Data Capture questions](https://github.com/OBenner/data-engineering-interview-questions/blob/master/content/cdc.md) | Public | 2026-09-09 | Inspected the complete public question list. |
| S014 | Platform | [OBenner: Data Quality questions](https://github.com/OBenner/data-engineering-interview-questions/blob/master/content/data-quality.md) | Public | 2026-09-09 | Inspected the complete public question list. |
| S015 | Platform | [OBenner: Data Observability questions](https://github.com/OBenner/data-engineering-interview-questions/blob/master/content/observability.md) | Public | 2026-09-09 | Inspected the complete public question list. |
| S016 | Platform | [OBenner: Data Governance questions](https://github.com/OBenner/data-engineering-interview-questions/blob/master/content/data-governance.md) | Public | 2026-09-09 | Inspected the complete public question list. |
| S017 | Platform | [OBenner: Data System Design questions](https://github.com/OBenner/data-engineering-interview-questions/blob/master/content/system-design.md) | Public | 2026-09-09 | Inspected the complete public question list. |
| S018 | Platform | [Interview Questions to Learn: Parquet vs ORC vs Avro](https://www.interviewquestionstolearn.com/) | Public | 2026-09-09 | Inspected the public file-format comparison and scenario-question section. |
| S019 | Both | [HikeCatalyst: 200 Scenario-Based Data Engineer Questions](https://www.hikecatalyst.com/interview-questions/data-engineer/) | Public | 2026-09-09 | Inspected the public scenario bank and representative questions across its topic filters. |
| S020 | Platform | [DataDriven: Senior Data Engineer Mock Interview](https://datadriven.io/mock-interview/senior-data-engineer) | Public | 2026-09-09 | Inspected senior/staff governance, build-versus-buy, cost, cross-team influence, mentoring, and architecture prompts. |
| S021 | Both | [DojoPrep: Senior Data Engineer Interview Questions](https://dojoprep.com/interview-questions/senior-data-engineer) | Public | 2026-09-09 | Inspected all twelve public senior questions; the SQL coding prompt is queued as Language. |
| S022 | Platform | [Coursera: 8 PySpark Interview Questions](https://www.coursera.org/in/articles/pyspark-interview-questions) | Public | 2026-09-09 | Inspected the public PySpark question list. |
| S023 | Language | [Real Python: Python Career learning path](https://realpython.com/tutorials/career/page/1/) | Manual review | 2026-09-09 | Reliable public title and URL were discovered, but automated page retrieval returned an internal error; no questions were derived from it. |
| S024 | Platform | [NAILDD: Data Mesh interview deep dive](https://www.naildd.com/blog/data-mesh-data-engineering-interview) | Manual review | 2026-09-09 | Search discovery identified the public title and URL, but direct retrieval returned a cache-miss error; no questions were derived from it. |
| S025 | Platform | [Frontier Engineering: AI-focused Data Engineer questions](https://www.frontierengg.com/learn/interview-prep/data-engineer-ai) | Manual review | 2026-09-09 | Search discovery identified the public title and URL, but direct retrieval returned a cache-miss error; no questions were derived from it. |
| S026 | Platform | [PracHub: Design a Data Service for Downstream Consumers](https://prachub.com/interview-questions/design-a-data-service-for-downstream-consumers) | Public | 2026-09-09 | Inspected the complete public system-design prompt and follow-up questions. |

Use these access values:

- **Public:** the source was opened and inspected normally.
- **Manual review:** discovery found a reliable title and URL, but automated
  retrieval was unavailable. Do not derive questions from uninspected content.
- **User provided:** the user supplied the question or source material directly.
- **Unavailable:** the source could not be inspected or identified reliably. Do
  not derive questions from it.

Use ISO dates (`YYYY-MM-DD`) and descriptive links. Prefer sources with clear
ownership and licensing. Never bypass authentication, paywalls, robots controls,
or other access restrictions.

## Capture

Capture is intentionally expansive. Identify relevant source families, register
the sources that were actually inspected, and gather questions without answering
or consolidating them. Preserve meaningful wording variants for the later
consolidation pass; exact duplicates from the same source need only one item.

Useful discovery families include:

- Python language, runtime, typing, packaging, concurrency, testing, memory, and
  performance interviews.
- SQL fundamentals, analytical SQL, query plans, indexing, transactions, and data
  modeling interviews.
- General data-engineering and data-platform interviews.
- Batch, ETL/ELT, ingestion, CDC, and orchestration interviews.
- Spark, distributed processing, Kafka, and stream-processing interviews.
- Warehouse, lake, lakehouse, table-format, and serving-system interviews.
- Data quality, contracts, governance, privacy, security, reliability,
  observability, performance, capacity, and cost interviews.
- Senior data architecture, migration, incident, delivery, mentoring, and
  leadership scenarios.

Public question banks, interview-prep sites, engineering blogs, public hiring
rubrics, and practitioner publications are useful discovery sources. Official
language, SQL-engine, Apache-project, format, protocol, and vendor documentation
is preferred later for validating completed answers.

Continue until registered sources have been examined and additional search
variations produce few materially new question families. Record sources that
could not be inspected accurately instead of implying their contents were used.

### Capture prompt

```text
Read docs/INTERVIEW_PREP_WORKFLOW.md completely. Execute only the `Capture`
stage for [Language / Platform / both]. Register every inspected source, add the
discovered questions to the appropriate Captured queue, and do not consolidate
questions or write answers.
```

### Capture format

```markdown
- [ ] **Question to research and organize?**
  - Sources: S001, S002 (optional)
  - Context: What it may evaluate or why the variant matters. (optional)
```

When capture finishes, report:

- Sources successfully inspected.
- Manual-review and unavailable sources, with reasons.
- Language and platform question counts.
- Discovery areas that may still need another pass.

Do not research answers, merge questions, or create completed topical sections
during this stage.

## Consolidate

Consolidation turns captured questions into a clean inventory ready for answer
research. It remains separate from completion.

### Consolidate prompt

```text
Read docs/INTERVIEW_PREP_WORKFLOW.md and the existing completed question guides.
Execute only the `Consolidate` stage for every item currently under Captured for
[Language / Platform / both]. Do not execute the Complete stage.
```

During consolidation:

1. Check completed guides so an existing answered question is not queued again.
2. Merge duplicate and substantially overlapping questions while preserving all
   useful source IDs.
3. Normalize awkward wording and split compound questions only when their parts
   test meaningfully different concepts.
4. Classify each retained question as language or platform.
5. Choose an existing topical section or assign a concise proposed topic.
6. Place cross-scope questions according to the interviewer's primary evaluation.
7. Remove only questions that are irrelevant, obsolete without enduring value,
   proprietary, or incapable of testing useful understanding.
8. Move each retained item from `Captured` to `Ready to complete`.

### Ready format

```markdown
- [ ] **Normalized and consolidated question?**
  - Sources: S001, S002 (optional)
  - Proposed topic: Topic name
  - Level: Beginner / Intermediate / Senior / Staff
  - Context: Interview intent or retained source context. (optional)
```

When consolidation finishes, report before-and-after counts, duplicate families
merged, scope changes, topical coverage, and visible gaps. Do not research or
write answers during this stage.

## Complete

Completion researches and answers consolidated questions, then moves them into
the appropriate completed guide.

### Complete prompt

```text
Read docs/INTERVIEW_PREP_WORKFLOW.md,
docs/INTERVIEW_QUESTION_TEMPLATE.md, and the relevant completed question guide.
Execute only the `Complete` stage for questions under Ready to complete for
[Language / Platform / both].
```

During completion:

1. Check once more for an existing answer before adding a question.
2. Validate technical claims with current primary documentation, especially for
   Python, SQL dialects, engines, distributed guarantees, and versioned products.
3. Use `INTERVIEW_QUESTION_TEMPLATE.md` as the canonical answer contract. Include
   only optional blocks that materially improve the spoken answer.
4. Move the completed question into the best topical section in the language or
   platform guide, creating the section when necessary.
5. Remove its queue item, update the completed guide's topic index, and renumber
   questions starting at `1` inside every affected topical section.
6. Link the relevant curriculum guide, example, query, test, or evidence when it exists.
7. State SQL dialect, engine, version, scale, or consistency assumptions whenever
   the answer changes under another assumption.

If the ready inventory is too large for one pass, complete a coherent topical
batch and leave all other queue items unchanged. Report what was completed, what
remains, and anything deferred because authoritative verification was unavailable.

## Completed-guide organization

Each completed guide should contain:

1. A brief scope statement distinguishing it from the other guide.
2. A topic index linked to its completed sections.
3. Topical sections organized by durable concepts rather than source order.
4. Questions numbered from `1` within each topical section.
5. Original answers following `INTERVIEW_QUESTION_TEMPLATE.md`.

Do not copy source ordering, copy lengthy source answers, or force every optional
template block into every question.

## Review and maintenance

Periodically review completed banks for:

- Duplicate answers created under different wording.
- Stale Python, SQL dialect, Spark, Kafka, Airflow, warehouse, table-format, or
  cloud-product behavior.
- Questions that test product trivia without an enduring concept.
- Missing beginner foundations or senior production scenarios.
- Broken curriculum and primary-source links.
- Answers too long to deliver clearly in an interview.

Retain source IDs even when a source later disappears. Update its access note and
date rather than recycling the ID.

## To Add

### Language

#### Captured

<!-- Add newly discovered Python and SQL questions here. -->

#### Ready to complete

<!-- Consolidated language questions waiting for answer research. -->

### Platform

#### Captured

<!-- Add newly discovered data-engineering platform questions here. -->

#### Ready to complete

<!-- Consolidated platform questions waiting for answer research. -->

- [ ] **How would you model customer address history with stable keys and effective dates?**
  - Sources: S002
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **How would you model the entities and relationships of a social platform?**
  - Sources: S002
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **How would you choose keys and grain for a ride-sharing platform schema?**
  - Sources: S002
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **How would you design an online-retail star schema and defend its fact-table grain?**
  - Sources: S002
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **How would you model point-of-sale facts and conformed dimensions for a warehouse?**
  - Sources: S002
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **How would you support movie-streaming analytics with facts, dimensions, and event data?**
  - Sources: S002
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **How would you design an end-to-end batch analytics pipeline with quality gates, idempotent retries, and failure recovery?**
  - Sources: S002, S008, S017
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **How would you replicate a database while normalizing its schema downstream?**
  - Sources: S002
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **How do latency, correctness, cost, and operational complexity drive a batch-versus-streaming decision?**
  - Sources: S002, S017
  - Proposed topic: Batch and streaming architecture
  - Level: Intermediate
- [ ] **What tradeoffs distinguish log-, trigger-, and timestamp-based change capture?**
  - Sources: S002, S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **How would you autoscale a cloud pipeline whose input volume varies sharply?**
  - Sources: S002
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **How would you design a city-wide bicycle-demand data pipeline?**
  - Sources: S002
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **What responsibilities distinguish a data engineer's role from adjacent data roles?**
  - Sources: S004
  - Proposed topic: Data engineering foundations
  - Level: Beginner
- [ ] **Describe a difficult unstructured-data problem and how you made the result usable downstream.**
  - Sources: S004
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **Walk through a data project from acquisition through cleaning, storage, and delivery.**
  - Sources: S004
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **How did you choose the tools and algorithms used in a data project, and what alternatives did you reject?**
  - Sources: S004
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **What is data modeling, and how do conceptual, logical, and physical models differ?**
  - Sources: S004
  - Proposed topic: Data modeling and dimensional design
  - Level: Beginner
- [ ] **How do structured and unstructured data differ in storage and processing needs?**
  - Sources: S004
  - Proposed topic: Data engineering foundations
  - Level: Beginner
- [ ] **When would you use a star schema rather than a snowflake schema?**
  - Sources: S004
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **What do volume, velocity, variety, and veracity change about system design?**
  - Sources: S004
  - Proposed topic: Data engineering foundations
  - Level: Beginner
- [ ] **What enduring capabilities did Hadoop introduce for distributed storage and processing?**
  - Sources: S004
  - Proposed topic: Data engineering foundations
  - Level: Beginner
- [ ] **How does an analytical warehouse differ from an operational database?**
  - Sources: S004
  - Proposed topic: Data modeling and dimensional design
  - Level: Beginner
- [ ] **How do ETL and ELT differ, and what constraints drive the choice?**
  - Sources: S006
  - Proposed topic: Pipeline architecture and reliability
  - Level: Intermediate
- [ ] **How would you design near-real-time ingestion with durable replay and materialized serving views?**
  - Sources: S008, S017
  - Proposed topic: Batch and streaming architecture
  - Level: Senior
- [ ] **How would you choose between a warehouse, lake, and lakehouse for a new analytics platform?**
  - Sources: S008
  - Proposed topic: Warehouses, lakes, and lakehouses
  - Level: Senior
- [ ] **How would you design and operate a feature store for machine-learning consumers?**
  - Sources: S008
  - Proposed topic: ML data platforms
  - Level: Senior
- [ ] **How would you design a governed metrics platform that prevents definition drift?**
  - Sources: S008
  - Proposed topic: Metrics and semantic layers
  - Level: Senior
- [ ] **How would you build a CDC pipeline with bootstrap, ordering, replay, and schema evolution?**
  - Sources: S008
  - Proposed topic: Change data capture
  - Level: Senior
- [ ] **How would you repair incorrect history in a large fact table while ingestion and user queries continue?**
  - Sources: S009
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **How would you migrate a very large live dataset and cut over without downtime while new data keeps arriving?**
  - Sources: S009
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **What problem does Airflow solve that a collection of cron jobs does not?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Beginner
- [ ] **How are workflows represented as DAGs, and why must tasks commonly be idempotent?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Intermediate
- [ ] **What roles do Airflow's scheduler, executor, workers, webserver, and metadata database play?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Beginner
- [ ] **How do Airflow's Sequential, Local, Celery, and Kubernetes executors differ, and when is each appropriate?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Intermediate
- [ ] **How do you define task dependencies and scheduling behavior in an Airflow DAG?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Intermediate
- [ ] **How should custom Python dependencies be packaged for Airflow running under Docker Compose?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Intermediate
- [ ] **How do cron expressions, presets, start dates, catchup, and timetables affect Airflow scheduling?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Intermediate
- [ ] **How do Airflow XCom push/pull, task return values, and data-size constraints interact?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Intermediate
- [ ] **How are Jinja templates evaluated in Airflow, and what risks come with templated SQL?**
  - Sources: S010
  - Proposed topic: Orchestration and Airflow
  - Level: Intermediate
- [ ] **How would you design Airflow retries, timeouts, callbacks, and dead-letter handling?**
  - Sources: S008
  - Proposed topic: Orchestration and Airflow
  - Level: Senior
- [ ] **How would you make an Airflow backfill safe for downstream consumers?**
  - Sources: S015
  - Proposed topic: Orchestration and Airflow
  - Level: Senior
- [ ] **What is Kafka's core abstraction, and how does it combine queue and publish-subscribe behavior?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Beginner
- [ ] **What roles do brokers, topics, partitions, replicas, producers, and consumers play?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Beginner
- [ ] **How do consumer groups divide work and rebalance partitions?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Intermediate
- [ ] **How would you improve consumer throughput without violating ordering requirements?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Senior
- [ ] **What delivery guarantees can a Kafka pipeline provide, and where can duplicates still arise?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Intermediate
- [ ] **How do idempotent producers and transactions contribute to exactly-once processing?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Intermediate
- [ ] **What is a Kafka in-sync replica set, and how would you diagnose sustained ISR shrinkage or a preferred leader outside it?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Senior
- [ ] **How do replication factor and acknowledgment settings trade latency for durability?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Intermediate
- [ ] **What does a Kafka offset represent, and who should commit it when processing has side effects?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Intermediate
- [ ] **How should a partition key be chosen to balance ordering, distribution, and hotspot risk?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Intermediate
- [ ] **When can producer buffering fill, and how should backpressure be handled?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Intermediate
- [ ] **How does modern Kafka metadata management differ from ZooKeeper-based operation?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Intermediate
  - Context: Version-sensitive behavior must be verified during completion.
- [ ] **When should Kafka be paired with a stream processor such as Flink rather than treated as the processor itself?**
  - Sources: S011
  - Proposed topic: Kafka and event streaming
  - Level: Senior
- [ ] **What are Spark's driver, executors, cluster manager, jobs, stages, and tasks?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Beginner
- [ ] **What makes a Spark RDD resilient and distributed, and how does lineage support fault recovery?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How do transformations and actions differ, and how does lazy evaluation connect them?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **Which Spark operations cause shuffles, and why are shuffles expensive?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How do RDDs, DataFrames, and Datasets differ in optimization and type guarantees?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **What role does Catalyst play in planning Spark SQL queries?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **When should a Spark application use `cache()`, `persist()` with different storage levels, checkpointing, or none of them?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How do Spark partitions distribute work, and how would you select partition counts and keys?**
  - Sources: S012, S022
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **What is the difference between `repartition` and `coalesce`, including when increasing partitions is valid?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How do broadcast variables differ from broadcast joins and accumulators?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How would you minimize data transfer and serialization overhead in Spark?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How do client and cluster deployment modes change driver placement and failure behavior?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How would you monitor a Spark application and diagnose a slow stage?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Senior
- [ ] **How would you tune executor memory and distinguish heap pressure from shuffle or serialization pressure?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Senior
- [ ] **How does data skew appear in Spark metrics, and what mitigation strategies would you test?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **When is a broadcast join appropriate, and what can make broadcasting unsafe?**
  - Sources: S021
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How does Spark Structured Streaming differ from legacy DStreams?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How do event time, watermarks, state stores, output modes, and checkpoints interact in Structured Streaming?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How should corrupt JSON records and explicit schemas be handled during Spark ingestion?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **Why is Parquet well suited to Spark analytics, and which optimizations can use its metadata?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How does Spark compare with Hadoop MapReduce for iterative and general data processing?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **Does Spark require HDFS, and what storage systems can it use instead?**
  - Sources: S012
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **What distinguishes PySpark's architecture and Python-JVM boundary costs from Spark's other language interfaces?**
  - Sources: S022
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **What is `SparkContext`, and how has its direct use changed with higher-level Spark APIs?**
  - Sources: S022
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **When would you use MLlib through PySpark?**
  - Sources: S022
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **When should CDC replace periodic batch extraction?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **How do an initial snapshot and incremental change stream form a consistent CDC bootstrap?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **How do at-most-once, at-least-once, and exactly-once claims apply across a CDC pipeline?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **How would you make CDC application idempotent at the destination?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Senior
- [ ] **How should inserts, updates, and deletes be represented and applied downstream?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **How can partial row images be turned into correct downstream state?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **Why is global ordering difficult in CDC, and which ordering guarantee is actually required?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **Where should CDC offsets or watermarks be stored relative to destination writes?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **How should a CDC pipeline respond to additive and breaking schema changes?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Senior
- [ ] **What problem does the transactional outbox pattern solve?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Intermediate
- [ ] **How would you measure CDC lag and isolate whether it originates at capture, transport, processing, or apply?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Senior
- [ ] **How would you run a large CDC backfill without racing or duplicating the live stream?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Senior
- [ ] **Which CDC failure modes can silently lose, reorder, or duplicate changes?**
  - Sources: S013
  - Proposed topic: Change data capture
  - Level: Senior
- [ ] **What does it mean for data to be fit for its intended use, and how do completeness, validity, accuracy, consistency, freshness, and uniqueness differ?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **How should freshness be measured for datasets with different expected cadences?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **How do validation and reconciliation differ?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **When should a quality check operate at row level versus aggregate level?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **How would you design quality checks for an incremental pipeline?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Senior
- [ ] **How should quality rules account for late-arriving data?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **How would you detect schema drift and decide whether a change is breaking?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Senior
- [ ] **What belongs in a data contract, and who owns its evolution?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **How would you reduce false positives and alert fatigue in data-quality monitoring?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Senior
- [ ] **When is statistical anomaly detection useful compared with deterministic validation?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **How would you quarantine bad records without unnecessarily blocking good data?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **How would you test transformations at unit, integration, and data-reconciliation levels?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **What minimum checks should every production table have, and how would those checks vary by use case?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **What are common systemic data-quality failure modes?**
  - Sources: S014
  - Proposed topic: Data quality and contracts
  - Level: Intermediate
- [ ] **What is data observability, and what outcomes should it improve?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Beginner
- [ ] **How does observing dataset health differ from observing request-response services?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Intermediate
- [ ] **Which freshness, volume, schema, quality, runtime, and cost signals should a pipeline expose?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Intermediate
- [ ] **How would you define and measure an end-to-end data SLA from source event to consumer availability?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Senior
- [ ] **What inputs, outputs, checkpoints, resource metrics, warnings, and quality results should each run log?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Intermediate
- [ ] **How can a data pipeline fail silently even when every scheduled task reports success?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Senior
- [ ] **How does lineage accelerate impact analysis and root-cause investigation?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Intermediate
- [ ] **How would you trace a broken BI metric through models, pipelines, and sources?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Senior
- [ ] **How should alerts be routed and deduplicated so owners receive actionable signals?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Senior
- [ ] **What should a data-incident runbook contain?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Intermediate
- [ ] **Which incident patterns recur in data platforms, and how would you detect them earlier?**
  - Sources: S015
  - Proposed topic: Observability and incident response
  - Level: Senior
- [ ] **What is data governance, and how can it enable rather than obstruct self-service?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Beginner
- [ ] **How do governance and security overlap, and where do their responsibilities differ?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Intermediate
- [ ] **What accountability belongs to data owners, stewards, and custodians?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Intermediate
- [ ] **What metadata, ownership, lineage, classification, and SLA information belongs in a data catalog?**
  - Sources: S016
  - Proposed topic: Observability and incident response
  - Level: Intermediate
- [ ] **How does a business glossary differ from technical metadata?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Intermediate
- [ ] **When should access control use roles, attributes, or both?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Intermediate
- [ ] **How do row- and column-level security affect query design, performance, and access at large user counts?**
  - Sources: S016, S019
  - Proposed topic: Governance, privacy, and security
  - Level: Senior
- [ ] **How should personally identifiable or protected health data be classified and handled in analytics systems?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Intermediate
- [ ] **When should sensitive values be masked, tokenized, encrypted, or removed?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Intermediate
- [ ] **How would you make data access and administrative changes auditable?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Senior
- [ ] **How would you satisfy deletion rights across warehouse tables, lakehouse snapshots, backups, and derived aggregates?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Senior
- [ ] **How are retention policies expressed, enforced, and proven?**
  - Sources: S016
  - Proposed topic: Governance, privacy, and security
  - Level: Intermediate
- [ ] **Which idempotency patterns make retries safe across ingestion, transformation, and publication?**
  - Sources: S017
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **How should late events and historical backfills update derived outputs deterministically?**
  - Sources: S017
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **What responsibilities belong in raw, cleaned, and business-ready data layers?**
  - Sources: S017
  - Proposed topic: Pipeline architecture and reliability
  - Level: Intermediate
- [ ] **How would you isolate workloads and ownership on a multi-tenant data platform?**
  - Sources: S017
  - Proposed topic: Platform architecture, performance, and cost
  - Level: Staff
- [ ] **How would you design end-to-end schema evolution across producers, storage, transforms, and consumers?**
  - Sources: S017
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **What retry, replay, checkpoint, atomic-publication, and disaster-recovery patterns improve pipeline reliability?**
  - Sources: S017
  - Proposed topic: Pipeline architecture and reliability
  - Level: Intermediate
- [ ] **How would you design observability as a platform capability rather than a per-pipeline add-on?**
  - Sources: S017
  - Proposed topic: Observability and incident response
  - Level: Staff
- [ ] **How would you reduce platform cost while continuing to meet consumer SLAs?**
  - Sources: S017
  - Proposed topic: Platform architecture, performance, and cost
  - Level: Senior
- [ ] **When should data use a row-oriented format such as Avro versus a columnar format such as Parquet or ORC?**
  - Sources: S018
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **How do column pruning, predicate pushdown, row-group statistics, and encoding affect analytical reads?**
  - Sources: S018
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **How would you choose between Parquet and ORC based on engines and workloads rather than brand preference?**
  - Sources: S018
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **How does Avro schema evolution support event-stream compatibility?**
  - Sources: S018
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **How do compression-codec choices trade CPU, storage, and scan throughput?**
  - Sources: S018
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **What causes the small-files problem, and how would you measure and correct it?**
  - Sources: S018
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **For an object-store data lake queried analytically, how would you choose format, compression, and partitioning?**
  - Sources: S018
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **What is the difference between a data file format, an open table format, and object storage?**
  - Sources: S019
  - Proposed topic: Storage and table formats
  - Level: Beginner
- [ ] **When do Delta Lake, Iceberg, or Hudi add enough value over plain Parquet to justify their metadata layer?**
  - Sources: S019
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **How do compaction, snapshot retention, and vacuuming trade query performance, cost, and time travel?**
  - Sources: S019
  - Proposed topic: Storage and table formats
  - Level: Intermediate
- [ ] **How should optimistic commit conflicts between concurrent table writers be diagnosed and reduced?**
  - Sources: S019
  - Proposed topic: Storage and table formats
  - Level: Senior
- [ ] **How would you migrate a live plain-Parquet dataset to a transactional table format after partial writes caused duplicate reads?**
  - Sources: S019
  - Proposed topic: Storage and table formats
  - Level: Senior
- [ ] **How would you remodel amended, refunded, and split orders whose current fact table mixes incompatible grains?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **How would you introduce conformed dimensions when user attributes are duplicated inside events?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **How would you unify acquired order systems whose lifecycles, currencies, and customer identities differ?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **When should shipment-grain analysis use a second fact table versus an accumulating snapshot?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **How would you migrate a heavily used wide denormalized table toward dimensional models without breaking dashboards?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **How should late-arriving dimension members be represented and reconciled?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **How would you model a changing organizational hierarchy without rewriting historical reports after each reorganization?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **How do allocation factors prevent double counting through many-to-many bridge tables?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **How would you model uncertain identity matches and expose match confidence downstream?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **How would you cut warehouse spending materially without violating SLAs, and what evidence would prove the savings?**
  - Sources: S019
  - Proposed topic: Platform architecture, performance, and cost
  - Level: Senior
- [ ] **How would you consolidate two warehouses after a merger while controlling egress, duplicate datasets, and contract drift?**
  - Sources: S019
  - Proposed topic: Warehouses, lakes, and lakehouses
  - Level: Staff
- [ ] **How would you enforce shared data-quality standards across fifteen autonomous producer teams?**
  - Sources: S020
  - Proposed topic: Data quality and contracts
  - Level: Staff
- [ ] **How would you decide whether to build or buy a feature store?**
  - Sources: S020
  - Proposed topic: ML data platforms
  - Level: Staff
- [ ] **How would you reduce an expensive managed-compute pipeline's monthly cost without sacrificing its SLA?**
  - Sources: S020
  - Proposed topic: Platform architecture, performance, and cost
  - Level: Senior
- [ ] **How would you standardize orchestration across teams using Airflow, Prefect, and custom cron jobs without blocking their roadmaps?**
  - Sources: S020
  - Proposed topic: Orchestration and Airflow
  - Level: Staff
- [ ] **Describe a time you grew another engineer's ability to design and own data systems.**
  - Sources: S020
  - Proposed topic: Leadership and collaboration
  - Level: Senior
- [ ] **How do you conduct data-engineering code and design reviews that teach rather than merely gate changes?**
  - Sources: S020
  - Proposed topic: Leadership and collaboration
  - Level: Senior
- [ ] **Describe a technical decision you influenced across teams without direct authority.**
  - Sources: S020
  - Proposed topic: Leadership and collaboration
  - Level: Staff
- [ ] **Describe a platform failure you owned and the durable changes that followed.**
  - Sources: S020
  - Proposed topic: Observability and incident response
  - Level: Senior
- [ ] **How would you justify Spark versus Flink for a specific workload using latency, state, skills, and operational complexity?**
  - Sources: S020
  - Proposed topic: Batch and streaming architecture
  - Level: Senior
- [ ] **When should a frequently repeated analytical query be precomputed in a pipeline rather than optimized in place?**
  - Sources: S020
  - Proposed topic: Platform architecture, performance, and cost
  - Level: Senior
- [ ] **Design a clickstream pipeline for 100,000 events per second with dashboard metrics available within one minute.**
  - Sources: S021
  - Proposed topic: Batch and streaming architecture
  - Level: Senior
- [ ] **A 200-terabyte warehouse now has six-hour dbt runs; how would you diagnose and shorten the critical path?**
  - Sources: S021
  - Proposed topic: Warehouses, lakes, and lakehouses
  - Level: Senior
- [ ] **How would you model a warehouse for both stable operational reporting and ad hoc slicing across many dimensions?**
  - Sources: S021
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
- [ ] **A Spark job joins 10 TB of Parquet to a 500 MB lookup and exhausts executor memory; how would you diagnose and fix it?**
  - Sources: S021
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How would you design data-quality controls for regulated financial reporting?**
  - Sources: S021
  - Proposed topic: Data quality and contracts
  - Level: Senior
- [ ] **How would you compare Airflow, Prefect, and Dagster for 500 dynamic tasks and data-aware scheduling?**
  - Sources: S021
  - Proposed topic: Orchestration and Airflow
  - Level: Senior
- [ ] **How would you handle late events in hourly streaming revenue aggregates, including correction and reconciliation?**
  - Sources: S021
  - Proposed topic: Batch and streaming architecture
  - Level: Senior
- [ ] **Describe a significant data-quality issue you detected before consumers did and the systemic prevention you added.**
  - Sources: S021
  - Proposed topic: Data quality and contracts
  - Level: Senior
- [ ] **Describe a time you pushed back when a stakeholder requested data faster than the team could deliver it reliably.**
  - Sources: S021
  - Proposed topic: Leadership and collaboration
  - Level: Senior
- [ ] **When would you use slowly changing dimension Types 1, 2, or 6 in a B2B analytics model?**
  - Sources: S021
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **When, if ever, is an entity-attribute-value schema justified in a columnar analytical warehouse?**
  - Sources: S021
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **Which PySpark applications benefit from distributed execution, and which should remain local?**
  - Sources: S022
  - Proposed topic: Spark and PySpark
  - Level: Intermediate
- [ ] **How do graph databases model nodes and edges, and which access patterns justify them?**
  - Sources: S007
  - Proposed topic: Data modeling and dimensional design
  - Level: Intermediate
- [ ] **What design constraints determine whether a transformation should run as a serverless function?**
  - Sources: S007
  - Proposed topic: Platform architecture, performance, and cost
  - Level: Intermediate
- [ ] **How would you choose between a managed cloud data service and a self-managed open-source system?**
  - Sources: S007
  - Proposed topic: Platform architecture, performance, and cost
  - Level: Senior
- [ ] **How should BI tools such as Power BI or Looker consume governed semantic models rather than raw tables?**
  - Sources: S007
  - Proposed topic: Metrics and semantic layers
  - Level: Intermediate
- [ ] **How do encryption in transit, encryption at rest, secret management, and least privilege fit together on a data platform?**
  - Sources: S007
  - Proposed topic: Governance, privacy, and security
  - Level: Intermediate
- [ ] **How would you design CI checks and deployment automation for data pipelines and schemas?**
  - Sources: S007
  - Proposed topic: Pipeline architecture and reliability
  - Level: Senior
- [ ] **How should a platform team evaluate a pipeline architecture quantitatively before selecting technologies?**
  - Sources: S008
  - Proposed topic: Platform architecture, performance, and cost
  - Level: Staff
- [ ] **How would you design a unified analytics platform that shares trustworthy data across BI and ML workloads?**
  - Sources: S008
  - Proposed topic: Warehouses, lakes, and lakehouses
  - Level: Staff
- [ ] **How would you expose governed warehouse data to applications without allowing arbitrary interactive warehouse queries?**
  - Sources: S026
  - Proposed topic: Data serving and contracts
  - Level: Senior
- [ ] **How would a client export ten million rows without holding one long database transaction?**
  - Sources: S026
  - Proposed topic: Data serving and contracts
  - Level: Senior
- [ ] **What should a governed data service return when its serving projection is stale?**
  - Sources: S026
  - Proposed topic: Data serving and contracts
  - Level: Senior
- [ ] **How would you remove a field from a data-service contract without silently breaking consumers?**
  - Sources: S026
  - Proposed topic: Data serving and contracts
  - Level: Senior
- [ ] **How would you support point-in-time reporting when the source table currently overwrites history?**
  - Sources: S019
  - Proposed topic: Data modeling and dimensional design
  - Level: Senior
