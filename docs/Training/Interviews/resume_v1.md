Richard Wilkerson 

Principal Data Engineer | Payments & Cloud Warehousing 

(14+ Years of Expertise in Scalable, Secure & High-Performance Data Platforms) 

Email: richardchristianwilkerson@gmail.com; Phone: (214) 329-1138 

 

 

Profile Summary 

 

Data engineer with over 14 years of experience across the Hadoop, Spark, and cloud-lakehouse ecosystem, and a strong track record of delivering secure, scalable, and high-throughput data platforms for payments, luxury retail, banking, automotive, airline, and SaaS organizations. Experience spans batch and streaming ingestion, dimensional and lakehouse modeling, orchestration, and the governance controls that regulated industries demand. 

 

Architected and launched end-to-end data solutions, leading teams through the entire delivery cycle — from source-system discovery and data contracts through modeling, pipeline construction, optimization, and production support. Consolidated fragmented reporting estates onto governed cloud warehouses, migrated legacy Hadoop and Teradata workloads onto Spark, Databricks, and Snowflake, and reduced data latency from overnight batch to near real time. 

 

Core Competencies: 

Data Pipeline Architecture & Development: Deep expertise in Apache Spark, PySpark, Scala, SQL, and modern frameworks like Delta Lake, Apache Iceberg, and dbt for building high-quality batch and streaming pipelines. 

Multi-Cloud Data Engineering: Proven success in delivering unified data platforms using AWS, Azure, and GCP, improving portability and reducing time-to-insight. 

Data Modeling Principles: Strong command of medallion architecture and Kimball dimensional modeling,  adhering to normalization and slowly changing dimension discipline for maintainable and testable data products. 

Team Leadership & Mentorship: Experienced in leading agile data teams, conducting code reviews, defining SQL and PySpark standards, and nurturing engineers toward technical mastery. 

Performance & Cost Optimization: Skilled in diagnosing and resolving shuffle skew, small-file pressure, and runaway warehouse spend to ensure predictable pipeline performance and budget. 

Security & Compliance: Hands-on experience implementing encryption at rest and in transit, tokenization, RBAC, and column-level masking, ensuring compliance with PCI DSS, SOX, GDPR, and CCPA standards. 

Ingestion & Change Data Capture: Proficient in Kafka, Kinesis, Debezium, and API-based ingestion, as well as incremental loading through watermarking, CDC, and SCD Type-2 processing. 

Data Quality & Observability: Adept in unit (PyTest, dbt tests), integration, and expectation-based testing (Great Expectations) frameworks to maintain accuracy and reliability. 

Agile Delivery: Deep understanding of Agile and Scrum methodologies, contributing to iterative development, continuous feedback, and efficient project execution. 

 

Technical Skills 

 

Programming Languages: Python, Scala, SQL, Java, Bash/Shell, PL/SQL  

Big Data & Processing: HBase, Impala, Presto/Trino, Sqoop, Oozie, Pig, Cloudera CDH, Hortonworks HDP, Databricks, Delta Lake, Delta Live Tables, Unity Catalog, Apache Iceberg, Apache Hudi, Apache Spark (PySpark, Spark SQL, Structured Streaming), Hadoop (HDFS, YARN, MapReduce), Hive 

Streaming & Messaging: Azure Event Hubs, GCP Pub/Sub, Debezium CDC, Apache Kafka, Confluent Platform, Schema Registry, ksqlDB, Apache Flink, AWS Kinesis (Streams, Firehose) 

Cloud Platforms: Azure (ADF, Databricks, Synapse Analytics, ADLS Gen2, Event Hubs, Key Vault, Purview, Monitor), GCP (BigQuery, Dataflow, Dataproc, Pub/Sub, Cloud Composer, Cloud Storage, Vertex AI), AWS (S3, EMR, Glue, Lambda, Step Functions, Redshift, Athena, MSK, Kinesis, DynamoDB, Lake Formation, IAM, KMS, CloudWatch, SageMaker) 

Warehousing & Modeling: Teradata, Medallion Architecture, Kimball Dimensional Modeling, SCD Type-1/2, Star & Snowflake Schemas, Snowflake (Snowpipe, Snowpark, Streams & Tasks, Time Travel), Amazon Redshift, Google BigQuery, Azure Synapse 

Orchestration & Transformation: Apache Airflow (MWAA, Cloud Composer), dbt, Azure Data Factory, AWS Step Functions, Databricks Workflows, Apache NiFi 

DevOps & IaC: Jenkins, GitHub Actions, GitLab CI, Azure DevOps, AWS CodePipeline, Terraform, CloudFormation, ARM Templates, Docker, Kubernetes (EKS, AKS, GKE) 

Data Quality, Governance & Observability: Datadog, Prometheus, Grafana, Splunk, CloudWatch, Great Expectations, dbt tests, Apache Ranger, AWS Lake Formation, Azure Purview, AWS Macie, Kerberos 

Databases: Google Cloud Bigtable, Elasticsearch, Redis, PostgreSQL, Oracle, SQL Server, MySQL, MongoDB, Cassandra 

BI & Visualization: Looker, Amazon QuickSight, Superset, Power BI, Tableau 

Methodologies: Kanban, DataOps, Test-Driven Data Development, Agile, Scrum 

 

 

Professional Experience 

 

PayPal, San Jose, CA 									Mar 2026 – Present  

Lead Data Engineer  

 

Led the development and enhancement of Buy Now Pay Later (BNPL) acquisition and servicing data products within PayPal's consumer credit analytics estate, working on the BigQuery consumption layer the company standardized on after moving roughly 400 PB of analytical data off its on-premises Hadoop platform. 

 

Led data pipeline development using Python, PySpark, and BigQuery SQL following medallion architecture principles across raw, curated, and semantic layers. 

Designed, implemented, and maintained scalable Buy Now Pay Later (BNPL) acquisition and servicing datasets in Google BigQuery covering applications, approvals, disbursements, repayments, and delinquency. 

Architected and enhanced a pipeline kill-switch and circuit-breaker framework using country configuration, feature flags, and Airflow sensors to halt downstream propagation when upstream quality thresholds were breached. 

Developed and maintained comprehensive dbt tests and Great Expectations suites to ensure data quality and release readiness. 

Integrated GraphQL and REST source APIs into PySpark ingestion pipelines on Cloud Dataproc, applying functional transformation patterns. 

Implemented and managed configuration-driven pipeline enablement in Cloud Composer (Airflow) for controlled rollouts and experimentation across markets. 

Configured and maintained environment-specific build variants with Terraform and GitHub Actions to support dev, staging, and production datasets with market-specific behavior. 

Utilized BigQuery query plans, INFORMATION_SCHEMA, and Dataproc job history for debugging, staging validation, and issue resolution throughout the development lifecycle. 

Published curated BNPL datasets as Apache Iceberg tables through BigLake, giving Spark on Dataproc and BigQuery consumers a shared open table format with snapshot-based time travel. 

Leveraged Datadog and internal analytics tooling for monitoring, metric validation, and production troubleshooting of streaming and batch jobs. 

Refactored error handling across PySpark and Airflow pipelines to support differentiated retry, quarantine, partial-load, and full-failure semantics across pipeline stages. 

Reviewed batch and streaming implementations to maintain consistency between the Kafka/Flink real-time path and the BigQuery batch path. 

Partnered closely with Product and Risk teams to deliver partner-driven data feeds across international markets through Pub/Sub and Cloud Storage landing zones into BigQuery. 

Performed code reviews of PySpark, dbt, and BigQuery SQL code, along with technical mentoring and architectural refactoring to improve maintainability and engineering standards. 

Collaborated within an Agile Scrum cross-functional team of data engineers, analytics engineers, backend engineers, product managers, and analysts, tracking delivery in Jira. 

Participated in sprint planning, technical design discussions, backlog refinement, estimation, and release planning for the BigQuery and Dataproc data platform. 

Continuously improved pipeline performance, maintainability, and scalability through proactive refactoring and BigQuery partitioning and clustering strategy tuning. 

 

Tools: Python, PySpark, Google BigQuery, Cloud Dataproc, Google Cloud Bigtable, Apache Kafka, Apache Flink, Gimel, Apache Hive, HDFS, Elasticsearch, Cloud Composer (Airflow), dbt, Pub/Sub, Cloud Storage, Looker, Terraform, GitHub Actions, Great Expectations, Apache Iceberg, BigLake, Datadog, Jira, Agile Scrum 

Neiman Marcus, Dallas, TX								Oct 2023 – Feb 2026 

Lead Data Engineer  

 

Led the data engineering team at Neiman Marcus, driving luxury retail analytics through a governed Snowflake estate that unified customer, clienteling, merchandising, and fulfillment data. Owned the ingestion, modeling, and security architecture behind personalization and inventory visibility across the luxury customer journey. 

 

Designed and implemented a modular, scalable data platform architecture leveraging medallion layering and dimensional modeling on Snowflake, enabling independent evolution of ingestion, transformation, and serving. 

Pioneered the adoption of dbt to deliver refined, well-documented, and version-controlled transformation models aligned with Neiman Marcus business definitions. 

Integrated payment and order data into Snowflake while enforcing robust security measures — including tokenization, Snowflake column-level masking policies, and role-based access control — to protect cardholder and customer PII. 

Collaborated with global backend teams to integrate real-time inventory, order tracking, and localized content feeds into Snowflake through Snowpipe Streaming, Kafka, and API-based ingestion. 

Performed deep performance profiling and optimization, cutting critical pipeline runtimes by 25% and improving Tableau dashboard responsiveness through Snowflake clustering keys and result caching. 

Designed and implemented the shared transformation logic layer as reusable dbt macros and PySpark libraries, enabling code reuse across merchandising, marketing, and supply-chain domains. 

Developed curated Gold-layer marts in Snowflake with dbt and integrated them with the shared semantic layer, ensuring consistent metric definitions across Tableau and Power BI. 

Implemented secure API and CDC-based ingestion with Fivetran, AWS Lambda, and Kafka for real-time inventory tracking, asset management, and customer identity resolution. 

Optimized Snowflake warehouse sizing, auto-suspend policies, and workload isolation, reducing compute spend while ensuring smooth operation for both batch and interactive workloads. 

Established a robust testing framework for the shared transformation codebase and integrated it into a CI/CD pipeline using GitLab CI. 

Mentored a team of four data engineers, conducting thorough code reviews, promoting clean SQL and PySpark standards, and elevating overall delivery quality. 

Implemented CI/CD pipelines via GitLab CI, automating build, test, and deployment of dbt projects and Airflow DAGs, which accelerated release cadence. 

 

Tools: Snowflake, dbt, Python, PySpark, SQL, Apache Kafka, Apache Airflow, Fivetran, AWS (S3, Glue, Lambda), Azure Data Factory, Terraform, GitLab CI, Great Expectations, Tableau, Power BI, Data Masking & Tokenization, PCI DSS, Docker, Jira, Confluence 

 

Ally Bank, Detroit, MI									Apr 2021 – Sep 2023 

Senior Data Engineer  

 

Played a key role in building and enhancing the enterprise data platform at Ally Bank, a branchless, digital-first bank, delivering trustworthy deposit, auto-lending, and customer datasets. Because Ally operates entirely through digital channels, every risk, servicing, and marketing decision depends on the data platform, so reliability and regulatory traceability drove every design choice. 

 

Designed and implemented critical banking data domains, including deposit account balances, fund transfers, auto loan originations and servicing, and transaction history, in Delta Lake on Databricks with full SCD Type-2 history for audit. 

Integrated advanced security measures such as field-level encryption, tokenization of account and SSN attributes, KMS-managed keys, and fine-grained RBAC enforced through Unity Catalog to protect sensitive customer financial data. 

Built the bank's lakehouse on Databricks, landing CDC feeds into Delta Lake bronze, silver, and gold tables with MERGE-based SCD Type-2 upserts and publishing curated marts to Tableau and self-service SQL. 

Worked closely with backend engineering teams to integrate Debezium CDC through Kafka (Amazon MSK) and REST-based ingestion for real-time account updates, payment events, and servicing activity. 

Tuned Databricks jobs and Delta tables with OPTIMIZE, Z-ORDER, and auto-compaction, alongside Spark shuffle and incremental-load tuning, keeping batch windows predictable. 

Actively participated in code reviews, enforced SQL and PySpark coding standards, and refactored legacy Teradata stored-procedure ETL into dbt models, improving transparency and testability. 

Ensured all development adhered to strict financial industry regulations, including FDIC, CFPB, BSA/AML, and SOX reporting requirements, with immutable audit logging in Delta Lake and lineage documentation in Unity Catalog. 

Developed and maintained comprehensive unit, integration, and reconciliation tests using PyTest, dbt tests, and Great Expectations to do constraint checks on Spark DataFrames, significantly reducing production data defects. 

 

Tools: Python, PySpark, SQL, Snowflake, AWS (S3, Glue, EMR, Lambda, Step Functions, Redshift, MSK), Apache Kafka, Debezium, Apache Airflow, dbt, Databricks, Delta Lake, Unity Catalog, Teradata, Terraform, Jenkins, Great Expectations, PyDeequ, Tableau, KMS, IAM/RBAC 

 

Zoom Video Communications, San Jose, CA						Jul 2019 – Mar 2021 

Senior Data Engineer  

 

Contributed to the development, enhancement, and scaling of the telemetry and analytics platform at Zoom, delivering the meeting-quality, usage, and reliability datasets the business ran on. The role spanned the extraordinary 2020 growth in concurrent meeting participants, which required a re-architecture of the ingestion and aggregation layers to handle orders-of-magnitude higher event volume; tracked implementation decisions and acceptance criteria in Jira. 

 

Led the development of major platform data domains with Spark on Amazon EMR, including user and account provisioning, meeting session facts, and engagement feeds published to Snowflake for product and customer success teams. 

Engineered and optimized real-time processing of call-quality telemetry such as audio/video bitrate, jitter, packet loss, and screen-share events using Kafka and Spark Structured Streaming. 

Collaborated with analytics and product teams to implement well-documented semantic models in Snowflake and low-latency rollups in Apache Druid, keeping metric definitions consistent across dashboards. 

Utilized idempotent, checkpoint-based Spark Structured Streaming jobs with checkpoints on Amazon S3 for predictable state management, maintaining data consistency across high-volume Kafka partitions. 

Integrated internal service APIs and Avro-encoded event schemas into the Kafka ingestion layer for account provisioning, meeting lifecycle, cloud recording, and licensing analytics. 

Implemented Spark Structured Streaming backpressure and Kubernetes-based autoscaling of ingestion services, maintaining throughput across unpredictable load spikes during peak pandemic-era growth. 

Optimized Spark performance on Amazon EMR, addressing shuffle bottlenecks, late-arriving events through watermarking, and small-file inefficiencies through Parquet compaction in the Amazon S3 data lake. 

Conducted end-to-end testing, debugging, and performance profiling with Prometheus and Grafana to ensure stability, Avro schema compatibility, and correctness of published metrics. 

Contributed to platform security and compliance, integrating Amazon S3 encryption, secure data storage, and role-based access in Snowflake for meeting metadata subject to privacy commitments. 

 

Tools: Apache Kafka, Apache Spark (PySpark, Structured Streaming), Scala, Python, SQL, AWS (S3, EMR, Kinesis, Redshift, Athena, Lambda), Snowflake, Apache Airflow, Apache Druid, ClickHouse, Parquet, Avro, Kubernetes, Docker, Terraform, Grafana, Prometheus 

 

American Honda Motor Co., Inc., Torrance, CA					Jan 2018 – Jun 2019 

Senior Big Data Engineer 

 

Built connected-vehicle data pipelines on AWS for the telematics and vehicle-health analytics platform at Honda. Honda has run its connected-car data collection and storage platforms on AWS since 2014; this work supported the transition of that estate from EC2-hosted services toward a serverless, event-driven architecture deployed across multiple regions. 

 

Designed and developed core ingestion pipelines for Honda's connected-vehicle telemetry, including navigation, trip, and diagnostic event streams landing into Amazon S3 through Kinesis. 

Modeled decoded CAN bus and OBD-II signal data into normalized Parquet schemas catalogued in AWS Glue, suited to fleet-scale analysis with Spark on Amazon EMR. 

Implemented serverless processing components using AWS Lambda and Step Functions for enrichment, validation, and routing of high-frequency vehicle events. 

Developed curated Amazon Redshift and DynamoDB datasets exposing real-time vehicle metrics such as fuel efficiency, tire pressure, battery state, and maintenance-due indicators for downstream services and dealer reporting. 

Collaborated closely with embedded and platform engineers to ensure seamless integration between vehicle telematics units, AWS IoT ingestion, and the analytics estate. 

Adhered to stringent automotive data-handling standards and implemented secure practices — AWS KMS encryption, VIN pseudonymization, and least-privilege AWS IAM — to ensure reliability and privacy of vehicle data. 

Worked with analytics stakeholders to create aggregate models in Amazon Redshift and Tableau dashboards, optimized for fleet-health and quality-engineering use cases. 

 

Tools: AWS (Kinesis, Kinesis Firehose, IoT Core, Lambda, Step Functions, S3, EMR, Glue, Redshift, DynamoDB, KMS, IAM, CloudFormation, CloudWatch), Apache Spark (PySpark), Apache Hive, Python, Scala, SQL, Parquet, Apache Airflow, Terraform, Docker, Tableau, CAN Bus / OBD-II signal decoding 

 

Hawaiian Airlines, Honolulu, HI							Oct 2016 – Dec 2017 

Data Engineer  

 

Contributed to the transition of Hawaiian Airlines from on-premises reporting to a cloud data warehouse, helping stand up the Snowflake estate that continues to hold Hawaiian customer data today. Hawaiian's network of long-haul Pacific and inter-island routes creates unusual scheduling and demand patterns, so the work focused on booking, revenue, and operations datasets that could support both. 

 

Developed core data domains in Snowflake for the enterprise analytics platform, including passenger reservations, ancillary purchases, fare classes, and loyalty accrual and redemption. 

Collaborated with the BI team to craft dimensional models in Snowflake for Tableau reporting, using conformed date, route, and aircraft dimensions across subject areas. 

Integrated AWS IAM authentication, Amazon S3 staging storage, and scheduled Sqoop synchronization between on-premises SQL Server and Oracle source systems and Snowflake. 

Implemented incremental and CDC-based loading with Spark on AWS EMR, enabling near real-time refresh of operational datasets without full reloads. 

Integrated third-party distribution and payment data feeds through Amazon S3 into Snowflake to support revenue accounting and channel profitability analysis. 

Advised the airline's internal team on cloud warehouse architecture, workload management, and cost governance as the Snowflake footprint grew. 

Developed and maintained Spark and Hive pipelines on Amazon EMR for flight operations analytics, enabling on-time performance, turn-time, and irregular operations reporting. 

Implemented and optimized Snowflake datasets supporting booking funnel analysis, online check-in, mobile boarding pass adoption, and disruption recovery. 

Integrated multiple backend airline systems and third-party APIs for real-time flight data, passenger information, and weather feeds, using Python ingestion jobs that landed Parquet files in Amazon S3. 

Optimized Snowflake query performance, reducing load times and keeping the Tableau dashboards used by operations control responsive. 

Utilized orchestration with Apache Airflow for predictable scheduling, maintaining data consistency across complex multi-source travel workflows. 

Conducted extensive SQL-based testing and reconciliation against SQL Server and Oracle source systems to ensure parity and address discrepancies before publication. 

Participated in peer code reviews through Git, with Jenkins builds validating changes, promoting clean modeling, modular design, and SQL best practices. 

 

Tools: Snowflake, Amazon S3, Amazon EMR, Apache Spark, Apache Hive, Sqoop, Python, SQL, Apache Airflow, SQL Server, Oracle, Parquet, Tableau, AWS IAM, Git, Jenkins, Dimensional Modeling 

 

 

Coach, New York City, NY								Sep 2014 – Sep 2016 

Data Engineer  

 

Developed and enhanced the retail and e-commerce data platform at Coach, delivering reliable merchandising, customer, and transaction datasets. The work sat on the Amazon Redshift and Amazon EMR foundation the parent group used to model customer, product, and enterprise data, running Spark, Hive, and Presto workloads over a large daily operational data store. 

 

Designed and implemented core e-commerce data domains with Spark on Amazon EMR and Amazon Redshift, including product catalogue, advanced search behavior, cart and checkout events, and order fulfillment. 

Collaborated with analytics stakeholders to create Tableau reporting models over Amazon Redshift supporting merchandising, planning, and allocation decisions. 

Integrated payment gateway and shipping carrier feeds into Amazon Redshift, enabling accurate transaction and delivery performance reporting. 

Optimized Parquet file layout, Hive partitioning, and Presto query patterns on Amazon S3 to ensure quick response times for product and sales reporting over multi-year history. 

Implemented Spark (Scala) datasets on Amazon EMR supporting personalized product recommendations based on browsing history and purchase patterns. 

Integrated JSON web analytics feeds into Hive tables on Amazon EMR to track user behavior, product views, and purchase funnels, providing insight into digital conversion. 

Debugged and resolved Spark and Hive pipeline issues, ensuring the stability and reliability of daily reporting. 

 

Tools: Amazon EMR, Amazon Redshift, Amazon S3, Apache Spark, Apache Hive, Presto, Sqoop, Hadoop (HDFS), Python, Scala, SQL, Parquet, JSON, Tableau, Dimensional Modeling 

 

Mobisoft Infotech, Houston, TX							Jan 2012 – Aug 2014 

Data Engineer  

 

Built a foundation in data integration and reporting at Mobisoft Infotech across a consultancy client base. Because engagements rotated across industries, the role involved delivering ETL and warehouse solutions against a wide variety of source systems and tight client timelines. 

 

Developed and maintained SSIS ETL processes for clients across different industries, including utilities, logistics, healthcare, and retail. 

Implemented star-schema data marts in SQL Server and Oracle with Tableau reporting layers, focusing on designs that performed well across varying data volumes. 

Integrated RESTful APIs and flat-file feeds to connect warehouses with client backend services, handling JSON and XML parsing in Python and Java, validation, and load. 

Utilized SQL Server and MySQL for staging and warehouse storage, implementing incremental load and merge logic for reliable refreshes. 

Built early Hadoop batch pipelines using Hive and Sqoop for clients beginning to move large transactional datasets off relational systems. 

Debugged, tested, and resolved issues across SSIS packages, SQL stored procedures, and Crontab-scheduled shell scripts to ensure the stability and correctness of delivered reporting. 

Continuously learned and applied new data engineering techniques, staying updated with the evolving Hadoop and ETL ecosystem. 

 

Tools: SQL Server, MySQL, Oracle, SQL, Python, Java, SSIS, Hadoop (HDFS), Apache Hive, Sqoop, RESTful APIs, JSON, XML, Shell Scripting, Crontab, Tableau, Data Warehousing, ETL, Agile 

 

Education 

 

Bachelor of Science in Applied Technology  
Brigham Young University–Idaho, Rexburg, ID, USA 