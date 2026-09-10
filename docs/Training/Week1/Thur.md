# Homework
- setup Windows Subsystem for Linux (WSL) - if using Windows
- turn on hardware virtualization
- install docker (cli or desktop)


# Thursday Training: Computer Hardware Foundations for Big Data

These notes summarize nine Branch Education videos (about 3 hours 35 minutes
total) and connect their computer-hardware explanations to data engineering.
The hardware figures are examples from the videos, not universal specifications;
exact capacity, latency, bandwidth, and architecture vary by device generation.

## Learning goals

By the end of this material, I should be able to:

- explain why a computer needs registers, caches, DRAM, SSDs, and HDDs instead
  of one universal storage technology;
- distinguish capacity, latency, bandwidth, and cost rather than treating
  "speed" as a single property;
- describe how transistors become logic gates and how a CPU executes an
  instruction;
- explain why CPUs and GPUs suit different kinds of workloads;
- connect locality, access patterns, memory pressure, and I/O to pipeline
  performance; and
- explain why one machine eventually gives way to distributed storage and
  parallel computation.

## The main idea: computing is also data movement

A processor can operate only on data that is close enough to its execution
units. Data therefore moves through a hierarchy:

```text
HDD / SSD -> DRAM -> L3/L2/L1 cache -> registers -> CPU or GPU execution units
 large, cheap, persistent                                      tiny, fast, volatile
```

Moving toward the right generally means lower latency and higher bandwidth,
but much less capacity and a much higher cost per byte. Moving toward the left
generally means more capacity and persistence, but slower access. No technology
is best on every dimension, so controllers, operating systems, runtimes, and
applications continually move and reuse data across these layers.

This is the hardware basis for a central data-engineering rule: avoid moving
more data than necessary, and reuse data while it is in the fastest practical
layer.

| Layer | Physical idea | Typical role | Data-engineering consequence |
| --- | --- | --- | --- |
| Registers | Transistor-based flip-flops inside a core | Values being operated on now | The compiler and CPU manage these; capacity is extremely small. |
| CPU cache | SRAM cells close to cores | Recently or predictably used instructions and data | Locality and compact data layouts reduce expensive cache misses. |
| DRAM | One transistor and one capacitor per bit | Active programs, working sets, buffers, hash tables, cached data | Exceeding memory can cause spilling, paging, garbage-collection pressure, or failure. |
| NVMe/SATA SSD | Charge stored in 3D NAND flash cells | Persistent local data and fast spill/shuffle storage | Parallel, sequential I/O is usually much better than many tiny operations; writes have lifecycle costs. |
| HDD | Magnetic domains on rotating platters | Cheap, high-capacity persistent storage | Sequential scans can be reasonable; random seeks are costly. |
| Network/object storage | Remote storage reached through a protocol and network | Durable, scalable datasets shared by many machines | Requests have network latency and per-request overhead; layout and request size matter. |

An Android comparison is cold-starting an app: code and assets begin in
persistent storage and the useful portions are brought into memory before the
CPU can work efficiently. Reusing warm data avoids that loading path. The
analogy stops at the CPU caches and registers, which are mostly managed by
hardware and the compiler rather than Android application code.

## Video transcript summaries

### 1. [How Does Computer Cache, Memory, and Storage Work?](https://www.youtube.com/watch?v=TfhL5kBiQVI) (27:27)

The video introduces the memory hierarchy through four competing properties:
capacity, access latency, bandwidth, and cost. Registers and CPU caches are
small and expensive per byte but extremely close to execution units. DRAM is a
larger, slower working area. SSDs and HDDs are persistent and far larger, but
their access times are orders of magnitude longer. Cloud storage adds network
distance and protocol overhead.

It then ties the trade-offs to physical construction:

- registers use transistor-heavy flip-flops and must be reachable within a
  clock cycle;
- cache uses SRAM, commonly six transistors per bit;
- DRAM uses dense capacitor/transistor cells that must be refreshed;
- SSDs trap different charge levels in 3D NAND cells; and
- HDDs encode data in magnetic domains and mechanically seek to a track.

The final section scales the hierarchy to AI servers. Accelerators are placed
near high-bandwidth memory (HBM), servers add large banks of DDR memory, and
NVMe storage holds far larger datasets. Models and intermediate activations
must be fed through processors at enormous rates, so memory capacity and
bandwidth are as important as raw arithmetic performance.

**Big-data connection:** a faster processor cannot compensate indefinitely for
starved memory or storage. Pipeline design must consider where each dataset is,
how often it moves, and whether it will be reused.

### 2. [How Do Transistors Build into a CPU?](https://www.youtube.com/watch?v=_Pqfjer8-O4) (26:45)

A transistor acts as an electrically controlled switch. Complementary N-type
and P-type transistors are combined in CMOS circuits: when one path conducts,
the complementary path is off. Two transistors can form an inverter; larger
arrangements form NAND, AND, OR, XOR, and other logic gates.

The video uses a useful construction hierarchy:

```text
transistors -> standard cells / logic gates -> macrocells / functional units
            -> cores and accelerators -> complete processor
```

Standard cells are wired into units that add, multiply, compare, route, and
store binary values. Many metal interconnect layers connect billions of
transistors across a chip. The individual operations are simple; the immense
capability comes from composition, extreme speed, and repetition.

**Big-data connection:** distributed systems add another level to the same
composition story. A cluster is powerful because many simple machine-level
operations are coordinated across cores and nodes—not because "big data" uses
a fundamentally different kind of binary computation.

### 3. [How Do SSDs Work?](https://www.youtube.com/watch?v=5Mh3o886qpg) (17:54)

Files ultimately become bits. The video uses an image to show how RGB values
become binary and are stored as different quantities of trapped electrons in
charge-trap flash cells. A cell may represent multiple bits by distinguishing
several charge levels. More bits per cell increase density, but the voltage
levels become harder to distinguish reliably.

Cells are stacked vertically into strings and arranged into pages, blocks, and
planes. Control gates select a layer; bitlines carry values to and from page
buffers. Read and write operations therefore occur at page-oriented
granularity, while erase behavior is associated with larger blocks. Multiple
dies can be stacked in one package to increase capacity.

**Big-data connection:** an SSD is not byte-addressable persistent RAM. Its
page/block organization helps explain why large sequential I/O, batching,
write amplification, compaction, and avoiding excessive tiny writes matter.

### 4. [How Do Hard Disk Drives Work?](https://www.youtube.com/watch?v=wtdnatmVdIg) (15:15)

An HDD stores data in magnetic material on rapidly spinning platters. A voice
coil moves read/write heads across concentric tracks while each platter spins.
Tracks contain sectors with synchronization information, an address, a data
payload, error-correcting information, and spacing tolerance.

The write head changes the orientation of microscopic magnetic domains. The
read head senses transitions between orientations using magnetoresistance.
Because the head must move and wait for the correct sector to rotate under it,
random access has mechanical seek and rotational latency.

The transcript also discusses increasing density. Perpendicular recording uses
the depth of the magnetic material. Shingled magnetic recording (SMR) overlaps
tracks for greater density, but rewriting one track may require reading and
rewriting adjacent valid data. Heat-assisted magnetic recording makes smaller
domains easier to write.

**Big-data connection:** HDDs remain useful for inexpensive capacity and
sequential throughput, but random small reads/writes are a poor match. File
layout, scan order, batching, and append-oriented designs can transform the
same hardware from a bottleneck into an effective storage tier.

### 5. [How Does Computer Hardware Work?](https://www.youtube.com/watch?v=d86ws7mQYIg) (17:12)

This teardown shows the computer as a connected system rather than an isolated
CPU. The CPU package contains a die with cores, caches, memory controllers,
integrated graphics, and I/O logic. The motherboard routes power and data among
the CPU, DRAM, GPU, SSDs, network interfaces, and peripherals. The power supply
converts and distributes voltages, voltage regulators deliver the low voltages
processors require, and cooling removes the heat created by computation.

The CPU connects directly to latency-sensitive devices such as DRAM and often
PCIe/NVMe devices. A platform chipset handles many additional I/O connections.
The GPU has many simpler arithmetic cores, its own caches, and nearby VRAM. The
teardown also compares the storage layers: nanosecond DRAM access,
microsecond-scale SSD access, and millisecond-scale HDD access in the video's
example system.

**Big-data connection:** "the machine" is a set of bounded resources and
interconnects. CPU utilization alone cannot diagnose a slow job; memory
capacity, memory channels, PCIe, storage, networking, power, and thermal limits
may be the actual constraint.

### 6. [How Does Computer Memory Work?](https://www.youtube.com/watch?v=7J7X7aZvMXQ) (35:32)

DRAM is the computer's volatile working memory. A one-transistor/one-capacitor
(1T1C) cell represents a bit using electrical charge. The access transistor
connects a capacitor to a bitline when its wordline is selected. Sense
amplifiers detect and amplify the tiny voltage difference during a read. Write
drivers force the desired new value.

Cells form two-dimensional arrays organized into banks and bank groups. An
address selects a bank, row, and columns. Opening a row connects many cells to
their sense amplifiers. Reusing the open row is a **row hit**; closing it and
opening another row is a more expensive **row miss**. Multiple independent
banks allow operations to overlap and increase the chance that useful rows are
already open.

Charge leaks from the tiny capacitors, so DRAM must periodically refresh every
row. Burst buffers transfer adjacent values efficiently. Subarrays shorten
wordlines and bitlines, improving speed and signal behavior.

**Big-data connection:** access pattern matters even in memory. Contiguous,
compact structures and predictable access usually use caches, DRAM rows, and
burst transfers better than pointer-heavy or randomly scattered access.
Memory capacity is also a hard planning input for joins, sorts, aggregations,
caches, and shuffle buffers.

### 7. [How Does This SSD Store 8 TB of Data?](https://www.youtube.com/watch?v=r-SivgEpA1Q) (9:37)

This video moves up from individual NAND cells to the architecture of a full
SSD. Multiple NAND packages contain stacked dies, planes, blocks, and pages. An
SSD controller coordinates them and presents a simple logical sector address
space to the host computer.

Internally, a flash translation layer maps those logical sector addresses to
physical chip/die/plane/block/page locations. The mapping changes during use,
so an SSD may keep the active translation table in its own DRAM and persist it
to NAND. Large data can be striped across several NAND chips in "super pages,"
allowing the chips and channels to work in parallel. The controller also deals
with wear leveling, garbage collection, and error correction.

**Big-data connection:** parallelism exists inside one device. Queue depth,
request size, concurrency, and access pattern determine whether a workload uses
that parallelism. Logical file operations can also cause very different
physical work because the controller continually remaps and maintains flash.

### 8. [How Do Graphics Cards Work?](https://www.youtube.com/watch?v=h9Z4oGN89MU) (28:30)

A CPU has a smaller number of sophisticated, flexible cores optimized for
low-latency execution and varied control flow. A GPU has thousands of simpler
arithmetic lanes optimized for applying similar operations to large amounts of
data. The transcript describes this as the difference between quickly handling
a small varied load and moving an enormous uniform load in parallel.

GPU work is organized as threads, warps, thread blocks, and grids. The same
instruction sequence is applied to different data elements using SIMD/SIMT-like
execution. Independent vertex transformations are a natural example. When
threads take different conditional branches, **warp divergence** can reduce
efficiency. Tensor cores specialize in fused matrix multiplication/addition,
which is central to neural-network workloads.

GPUs are extremely data-hungry, so they use wide, high-bandwidth VRAM
connections and caches. Host-to-device transfer is an additional boundary;
moving small amounts of work to a GPU may cost more than it saves.

**Big-data connection:** GPUs are valuable for sufficiently large and regular
vector, matrix, ML, and supported analytical workloads. They are not a blanket
replacement for CPUs, especially for branch-heavy work, orchestration, network
I/O, or workloads too small to amortize data-transfer and launch overhead.

### 9. [The Engineering That Runs the Digital World: How Do CPUs Work?](https://www.youtube.com/watch?v=16zrEPOsIcI) (36:23)

The common operational model of a general-purpose CPU is the
**fetch-decode-execute cycle**:

1. **Fetch:** use the program counter to load the next instruction into the
   instruction register.
2. **Decode:** interpret the instruction and generate control signals.
3. **Execute:** route operands to the appropriate functional unit and perform
   the operation.
4. **Memory/writeback when required:** load or store data and retain the result.

The arithmetic logic unit performs arithmetic, bitwise operations, and
comparisons. Registers hold active operands. The program counter normally moves
to the next instruction, while jumps and conditional branches implement loops
and decisions. Modern processors pipeline multiple instructions, predict
branches, use multiple functional units, and contain several cores, but these
optimizations build on the same basic cycle.

The video contrasts instruction-set styles. Arm is historically associated
with RISC: relatively simple instructions and an emphasis on energy efficiency.
x86-64 is historically associated with CISC: a larger, more complex set of
instructions. This is a useful introductory distinction, but modern CPUs blur
the boundary internally; instruction-set label alone does not predict real
workload performance.

ASICs and FPGAs trade general-purpose flexibility for a fixed or configured
data path. They can outperform CPUs for a narrow repetitive task because they
do not perform the same general fetch/decode work for every operation.

**Big-data connection:** CPU performance depends on more than core count or
clock speed. Branching, vectorization, instruction-level parallelism, cache
behavior, memory stalls, and I/O all affect how much useful work a pipeline
actually completes.

## CPU vs. GPU: working model

| Question | CPU | GPU |
| --- | --- | --- |
| Core design | Fewer, more capable cores | Many simpler arithmetic lanes |
| Primary strength | Low-latency, varied, branch-heavy work | High-throughput, regular parallel work |
| Control flow | Handles divergence and general OS/application work well | Divergent threads can waste execution capacity |
| Memory emphasis | Cache hierarchy and relatively low access latency | Very high bandwidth to local VRAM/HBM |
| Data-engineering examples | Parsing, orchestration, compression, general SQL execution, services | Supported ML, matrix operations, vectorized analytics, some accelerated databases |
| Main warning | More cores do not fix I/O or memory bottlenecks | Transfer overhead and irregular work can erase the benefit |

## x86-64 vs. Arm: working model

- **x86-64** is an instruction set used primarily by Intel and AMD server and
  desktop processors. It maintains a long compatibility history and is usually
  introduced as CISC.
- **Arm** is a family of instruction sets widely used in phones and increasingly
  in laptops and servers. It is usually introduced as RISC and has a strong
  performance-per-watt story. Using less power generally produces less heat,
  which is one reason Arm processors have become attractive in data centers.
- **Do not choose a data platform by the RISC/CISC label alone.** Compare the
  actual processor generation, cores, memory bandwidth/capacity, vector and
  accelerator support, storage/networking, software compatibility, workload
  benchmark, energy use, and total cost.
- For a Kotlin analogy, x86-64 and Arm are different machine-level targets in
  the way the JVM and ART can target different underlying devices. The analogy
  stops because JVM bytecode is a virtual instruction set, while x86-64 and Arm
  are hardware-visible instruction set architectures.

## Measurements that should not be collapsed into "fast"

- **Capacity:** how many bytes can be held.
- **Latency:** how long one request takes before its result begins to arrive.
- **Bandwidth/throughput:** how much data can move per unit of time once work is
  flowing.
- **IOPS:** how many I/O operations complete per second; request size and queue
  depth must accompany this number.
- **Parallelism:** how many useful operations can proceed concurrently.
- **Utilization:** what fraction of a resource is busy; high utilization does
  not by itself mean useful or efficient work.
- **Durability:** whether data survives power loss and component failure.
- **Cost per byte and cost per operation:** important when scaling from one
  machine to a fleet.

A highway can have high bandwidth because many cars arrive per minute, while
one car can still experience high latency. The same distinction applies to a
network, storage device, or memory channel.

In data-engineering discussions, **memory** usually means volatile RAM/DRAM,
while **disk** is often used loosely for persistent local storage, including an
HDD or SSD. Object storage is also persistent, but it exposes an object API
rather than a local disk/block-device interface.

## From one computer to big data

Data size is commonly described in decimal units for storage products and
platforms:

- 1 GB = 1,000 MB;
- 1 TB = 1,000 GB;
- 1 PB = 1,000 TB; and
- 1 EB = 1,000 PB.

Binary units are different: 1 GiB = 1,024 MiB, 1 TiB = 1,024 GiB, and so on.
Always check which convention a tool or vendor reports.

Size alone does not define "big data." Data becomes big relative to a workload
when it no longer fits the available time, memory, storage, reliability, or cost
constraints of a single practical system. Volume, arrival velocity, format
variety, required correctness, and required response time all matter.

For scale intuition, reading 1 TB once at a sustained 100 MB/s has a theoretical
minimum of about 2 hours 47 minutes. At 1 GB/s it is still about 16 minutes 40
seconds. Parsing, decompression, computation, contention, remote reads, retries,
and output writes add more time. Repeated full scans therefore become costly
long before the data reaches petabytes.

Distributed systems respond by partitioning data and computation across many
machines. This can raise aggregate CPU, memory, storage, and network bandwidth,
but it also introduces partial failure, serialization, network transfer,
scheduling overhead, skew, coordination, and duplicated data. Parallelism is
not free; work must be large and divisible enough to justify it.

### Distributed-system concepts to learn next

- **Fault tolerance:** continuing or recovering correctly when some components
  fail.
- **Scalability:** handling more work by using resources effectively; adding
  machines helps only when the workload and architecture can use them.
- **Consistency:** the guarantees governing when a read observes a write across
  copies or nodes. It does not always mean every node is instantly identical.
- **Partitioning:** dividing data or work among nodes to increase capacity and
  parallelism.
- **Replication:** keeping multiple copies for availability, read scale, and
  durability.
- **Consensus:** enabling nodes to agree on selected shared state despite
  delays and failures; it is generally used for coordination and metadata, not
  for every byte of bulk data.

### From a LAN to a compute cluster

Three computers connected to the same local area network (LAN) are networked,
but they become a distributed system only when software running on them
coordinates toward a shared result. A compute cluster is a group of machines
managed as a pool of CPU, memory, storage, and network resources.

- **Client-server architecture:** clients request services from designated
  servers. Roles are intentionally different.
- **Peer-to-peer architecture:** peers can act as both clients and servers and
  communicate without routing all work through one central application server.
  Equal protocol roles do not imply equal capacity or identical responsibility
  at every moment.
- **Cluster architecture:** worker nodes execute partitions of a job while a
  coordinator, scheduler, or control plane assigns work and tracks progress.
  This is not normally peer-to-peer, even though workers may exchange data.

Wired Ethernet is typical for cluster networking because it offers predictable
bandwidth and latency, but a physical cable is not part of the definition. A
switch connects devices within a LAN. A router connects networks and often also
provides DHCP, which assigns local IP configuration. SSH is one way to
administer a remote machine, but it also requires an SSH service, credentials,
and permitted firewall/network rules; sharing a router alone is insufficient.

## Practical consequences for data pipelines

- **Filter and project early.** Read only the rows and columns required.
- **Prefer useful locality.** Partition and cluster data around common access
  patterns; avoid needless random reads.
- **Use appropriately sized files and batches.** Tiny files and tiny requests
  spend too much time in metadata, protocol, and scheduling overhead. Extremely
  large files can reduce parallelism and make retries expensive.
- **Know the working set.** A join or aggregation that fits in memory behaves
  very differently from one that spills to SSD or repeatedly fetches remote
  data.
- **Treat shuffles as data movement.** Redistributing records across a cluster
  consumes serialization, network, memory, and disk resources.
- **Exploit parallelism without creating skew.** One hot partition or straggler
  can determine the runtime of an otherwise parallel stage.
- **Cache deliberately.** Cache reused and expensive-to-recompute data, but do
  not crowd out the active working set with data that is used once.
- **Measure the bottleneck.** Observe CPU, memory, garbage collection, cache
  behavior when available, disk throughput/latency, network traffic, spill,
  queueing, and task distribution.
- **Benchmark the real access pattern.** A headline sequential bandwidth number
  does not predict random, concurrent, compressed, or remote workload behavior.
- **Account for failure and durability.** Hardware eventually fails; replicated
  or erasure-coded storage, checkpoints, retries, validation, and backups are
  part of the system rather than optional extras.

## The data lifecycle and data pipelines

A data pipeline is a repeatable set of steps that moves data from where it is
created to where it is needed. Along the way, the pipeline may clean, validate,
reorganize, and store the data. A useful lifecycle is:

```text
produce -> ingest -> land -> validate -> transform/model -> publish/serve
        -> consume -> observe and maintain -> archive or delete
```

- **Produce:** an application, database, device, partner, or user creates data.
- **Ingest:** collect it through files, database extracts, change-data capture,
  APIs, queues, or event streams.
- **Land:** save a copy close to the original input so it can be audited or
  processed again later.
- **Validate:** check schema, required fields, ranges, uniqueness, freshness,
  volume, and other contracts; quarantine bad records when appropriate.
- **Transform and model:** clean, standardize, join, deduplicate, enrich, and
  organize the data for a known purpose.
- **Publish and serve:** place a trustworthy result in a warehouse, lakehouse
  table, API, search index, or another system that consumers can use.
- **Consume:** support analytics, applications, ML, reporting, or RAG.
- **Operate:** monitor jobs, compare source and output counts, rerun old data
  when needed, repair problems, and track where the data came from.
- **Archive or delete:** apply retention, privacy, legal-hold, and deletion
  requirements throughout derived copies—not just at the original source.

The arrows do not have to represent one long program. A production pipeline is
usually several connected jobs with dependencies, retries, and outputs that can
be monitored.

### ETL vs. ELT

Both patterns contain the same logical operations; the distinction is where the
main transformation happens relative to loading into the analytical target.

| Stage | Meaning |
| --- | --- |
| Extract | Read from sources such as databases, APIs, object storage, files, or event systems. Web scraping is a specialized source when permitted and appropriate. |
| Transform | Validate, standardize, filter, deduplicate, join, enrich, aggregate, and model the data. Simply dropping every null or duplicate is not a universal rule; treatment follows the data contract and business semantics. |
| Load | Persist data in the destination or next durable layer and publish it safely for downstream use. |

- **ETL (Extract, Transform, Load):** transformation occurs before loading into
  the primary analytical target. It remains appropriate when the destination
  cannot efficiently transform data, sensitive fields must be removed before
  landing, bandwidth is constrained, or strict write-time contracts are needed.
- **ELT (Extract, Load, Transform):** source-aligned data is loaded first, then
  transformed using warehouse or lakehouse compute. It supports replay and
  multiple downstream models, and is common when storage is relatively cheap
  and the target has scalable compute.
- **Hybrid pipelines are normal.** Light validation, security filtering, or
  format normalization may occur before landing, followed by several
  transformations after loading. Extract and load are conceptually separate
  even when one connector or job performs both.

**Lecture framing:** ETL was presented as the older pattern and ELT as the
modern pattern that became especially common around 2022–2023. That is a useful
way to remember the broad industry shift toward cloud platforms. It is not an
absolute rule: ETL is still used, and many real pipelines mix ETL and ELT.
Newer systems often lean toward ELT because storage is cheaper and the target
warehouse or lakehouse can perform the transformations itself.

## Hadoop, Spark, and Hive

The Hadoop ecosystem established a widely influential model: split large files
and jobs into partitions, place them across commodity machines, schedule work
near the data when practical, and recover from individual failures.

| Component | Responsibility |
| --- | --- |
| Hadoop | An Apache ecosystem for distributed storage, resource management, and processing; it is not one execution engine. |
| HDFS | A distributed file system. A NameNode manages filesystem metadata while DataNodes store replicated file blocks. It is optimized for large files and high-throughput access. |
| YARN | A cluster resource manager and scheduler used by Hadoop applications. |
| MapReduce | Hadoop's batch-processing model and engine. It divides work into map and reduce tasks and commonly materializes intermediate stage output. |
| Apache Spark | A general distributed processing engine whose driver schedules partitioned work on executors. It supports SQL/DataFrames, batch processing, and Structured Streaming and can read from many systems—not only HDFS. |
| Apache Hive | Distributed data-warehouse software that applies table metadata and SQL to data in distributed storage. The Hive Metastore also remains an important metadata component in many ecosystems. |

In the lecture's Hadoop example, Spark reads data from HDFS, applies the
transformation logic, and writes the result to an analytical destination such
as Hive. That is an important pattern, but Spark is not limited to it. Spark can
also read from and write to object storage, databases, warehouses, and
lakehouse tables.

The original Hadoop/MapReduce pattern is less central in many new cloud
architectures, but Hadoop, HDFS, YARN, and Hive are not simply extinct. They
remain in production, and their ideas—partitioned data, data locality,
distributed scheduling, retry, and metadata catalogs—continue in newer systems.

### Work division, failures, and the "narrow highway"

- **Lecture point:** older ETL pipelines can feel like one long job. If a failure
  is not isolated or checkpointed, a large section—or the whole pipeline—may
  need to run again.
- Spark divides work into partitions and tasks. It can retry a failed task and
  rebuild some lost results from the steps that produced them, so a single
  machine failure does not always restart everything.
- Recovery is not automatic for every side effect. If a retried task blindly
  inserts the same rows again, it can create duplicates. This is one reason
  idempotency matters.
- **Lecture analogy:** loading into the destination is like entering a narrow
  highway. Poor organization, too many concurrent writes, or a target that
  cannot keep up can create a bottleneck and force part of the load to run
  again.

For an Android comparison, SQLite is an embedded transactional database suited
to application state and selective reads/writes. Hive and other analytical
systems are designed to distribute scans, joins, and aggregations across much
larger datasets. The analogy stops because modern analytical platforms vary
widely in storage ownership, indexing, transaction support, and serving
latency.

## Warehouses, data lakes, and lakehouses

- **Data warehouse:** a managed analytical system with tables, schemas, query
  optimization, workload management, governance, and SQL-oriented serving. It
  is designed primarily for OLAP rather than request-by-request OLTP traffic.
- **Data lake:** low-cost, scalable storage—commonly object storage—holding data
  in formats such as CSV, JSON, Avro, Parquet, ORC, images, audio, or video. A
  lake may retain source-aligned data as well as curated analytical datasets.
  It still needs ownership, metadata, quality controls, retention, and access
  policy; without them it can become a "data swamp."
- **Data lakehouse:** an architecture that adds table metadata, transactional
  behavior, catalogs, and analytical engines over lake storage, aiming to keep
  the lake's openness and economics while providing warehouse-like management
  and reliability.

MongoDB is an operational document database, not normally a data lake. The
reason is its architectural role and database interface—not merely that its
documents resemble JSON. A system's category depends on how it stores, governs,
and serves data, not just which payload formats it accepts.

### Medallion architecture

Medallion architecture is a multi-layer design pattern in which data becomes
more validated and consumer-oriented as it moves through the pipeline:

| Layer | What normally happens there |
| --- | --- | --- |
| Bronze / raw | Keep the data close to how it arrived so later layers can be rebuilt. Raw data still needs security, ownership, and basic ingestion checks. |
| Silver / cleaned | Fix types, apply quality rules, remove true duplicates, combine sources, and create reusable detailed data. |
| Gold / serving | Build business-ready tables, aggregates, metrics, or other outputs for known consumers. |

Bronze, silver, and gold are example names, not hard rules. A pipeline may have
more or fewer layers. The lecture emphasized open table formats such as Delta
Lake or Apache Iceberg for managed analytical data, especially in later layers,
but a specific format is not required by the medallion pattern.

### Processing technologies and platforms

These names belong to different categories and should not all be called
"processing engines":

| Technology | Category and role |
| --- | --- |
| Apache Spark | Open-source distributed processing engine for SQL/DataFrames, batch, and streaming workloads. |
| AWS Glue | AWS serverless data-integration service with catalog, crawler, orchestration, and managed job capabilities; Glue jobs can use Spark or Ray. |
| Databricks | Managed data and AI platform whose data-engineering workloads commonly use Apache Spark and Delta Lake, alongside Databricks services. |
| Snowflake | Managed cloud data platform with separate managed storage, compute warehouses, and cloud-service coordination; transformations commonly use SQL or Snowpark. |

Spark is a valuable engine to learn because it exposes partitioning, shuffles,
executors, memory pressure, and fault recovery directly. Tool selection should
still follow workload, ecosystem, operational responsibility, skills, and cost.

## File formats vs. open table formats

A **file format** defines how values are encoded inside a file. Examples include
CSV, JSON, Avro, Parquet, and ORC. A **table format** defines how a changing set
of data files forms a table: which files belong to a snapshot, schemas and
partitions, statistics, commit rules, and history.

Open table formats commonly store the actual rows in Parquet or ORC files. They
add metadata that records which files belong to the table, the table's schema,
and the current version. That extra layer makes safer updates, schema changes,
time travel, and multiple readers/writers possible. Spark or another engine
still performs the computation.

- **Apache Iceberg:** an open table format designed for large analytical tables
  and use by several processing engines. **Course focus:** this is the most
  important table format for us to learn first.
- **Delta Lake:** an open-source table format originally developed by
  Databricks. It is strongly associated with the Databricks ecosystem, although
  it can also be used elsewhere. **Course focus:** recognize it and understand
  why a Databricks project is likely to use it.
- **Apache Hudi:** another active open table format, often used when data is
  updated frequently. **Course focus:** we do not need to learn it now.

For this course, the practical order is Iceberg first, Delta Lake second, and
Hudi later if a future project requires it.

## Further introductory videos

- [What Is a Data Pipeline? Why Is It So Popular?](https://www.youtube.com/watch?v=kGT4PcTEPP8)
- [Data Pipelines Explained](https://www.youtube.com/watch?v=6kEGUCrBEU0)
- [ETL vs. ELT: Modern Data Architectures](https://www.youtube.com/watch?v=_Nk0v9qUWk4)

## Additional lecture notes

### OLAP vs. OLTP

- **OLAP (Online Analytical Processing)** is designed for analysis: scanning a
  lot of data, grouping it, calculating totals, and answering complex
  questions. Data warehouses are commonly used for OLAP.
  - Maps, charts, and dashboards are common outputs.
  - The raw dataset may be too large to recalculate every visualization from
    scratch in real time, so pipelines often prepare smaller Gold tables or
    precomputed totals for the dashboard.
- **OLTP (Online Transaction Processing)** is designed for everyday application
  activity: many short reads and writes such as creating an order, updating an
  account, or looking up one user.
  - Familiar examples include Android SQLite databases and operational uses of
    PostgreSQL, MySQL, and MongoDB.
  - OLTP is not only "write-heavy." The defining idea is many small,
    low-latency transactions with correctness under concurrent use.

An Android app normally asks SQLite for a small set of records for one screen.
An OLAP query may scan millions or billions of rows to calculate a trend. That
is the important contrast.

### Batch processing vs. stream processing

#### Batch processing

Batch processing collects a bounded amount of data and processes it as a group,
often on a schedule.

**Lecture example:** a 150 GB delivery arrives once a day at 8:00 a.m. A Spark
job starts after the delivery is complete, may run for hours, and must finish
before the next delivery. The data often arrives as CSV or Parquet files. The
schedule and expected volume make this a predictable job that can be monitored
for progress, resource use, and timely completion.

#### Stream processing

Stream processing handles an ongoing flow of events instead of waiting for a
whole day's data. It is used when the business needs a result quickly.

Lecture examples include:

- live dashboards;
- fraud detection;
- sensors used by robots or industrial equipment;
- Internet of Things (IoT) data; and
- market data used for time-sensitive trading decisions.

A streaming system usually needs two related pieces:

1. A **broker or event service** accepts events from producers, stores or queues
   them, and makes them available to consumers.
2. A **stream processor** reads the events and applies business logic such as
   validation, filtering, joins, windows, or aggregations.

These may be separate products. Kafka can move and retain events, while Kafka
Streams, Spark Structured Streaming, Flink, or another engine performs the
processing.

### Brokers and managed event services

- **Apache Kafka** is a widely used distributed event-streaming platform. It
  stores events in partitioned topics that producers write to and consumers
  read from. Replication and acknowledgements can make delivery durable, but
  reliability still depends on configuration and application design.
  - **Lecture rule of thumb:** Kafka becomes especially relevant when the rate
    reaches thousands of messages per second or when replay, several consumers,
    and long-lived event history are needed. This is not a hard threshold.
  - The difficult parts include partitions, broker failures, replication,
    consumer progress, scaling, security, and operational monitoring.
- **Amazon SQS** is a managed message queue and is often simpler to operate.
  Standard SQS queues can support very high throughput, so the main distinction
  is not simply "SQS is slow." SQS and Kafka provide different queue/log,
  ordering, replay, and consumer models.
- **RabbitMQ** is a message broker with flexible routing and queue behavior.
  The lecture's example of roughly 100 messages per minute describes a possible
  low-volume use case, not a RabbitMQ product limit. RabbitMQ also offers a
  stream type for replay and higher-throughput workloads.
- **Apache Pulsar** is another distributed messaging and streaming option.
- **Amazon Kinesis, Google Cloud Pub/Sub, and Azure Event Hubs** are managed
  cloud services. They cost money, but the provider handles much of the broker
  provisioning, failover, patching, and scaling.

### Two example pipeline paths

The lecture used these simplified paths:

```text
Non-real-time:
producer -> broker -> consumer -> Bronze -> Silver -> Gold

Low-latency serving:
producer -> broker -> stream processor -> OLAP serving system
```

These are examples rather than exclusive choices. One event stream can feed a
low-latency dashboard and also land in Bronze storage so it can be replayed,
audited, and used for later analysis.

### Micro-batch vs. event-at-a-time processing

- **Micro-batch processing** groups newly arrived events into very small
  batches and processes each batch quickly. This gives near-real-time results
  while keeping a batch-like execution model.
  - Spark Structured Streaming commonly uses micro-batches. The interval might
    be seconds, but it is configurable.
  - The instructor estimated that micro-batch systems cover roughly 75–80% of
    streaming use cases. Treat that as a lecture rule of thumb, not a measured
    market statistic.
  - Google Cloud Dataflow and other systems can also support streaming; the
    choice is not limited to Spark.
- **Event-at-a-time or continuous stream processing** handles events as they
  flow through long-running operators. Apache Flink and Apache Storm are
  familiar examples.
  - This can provide lower latency, but it has a steeper learning curve because
    state, late events, failure recovery, and delivery guarantees must be
    handled carefully.
  - "Real time" never means zero time. The required latency might be
    milliseconds, seconds, or minutes depending on the business need.

**Lecture simplification:** the lowest-latency path was shown going directly to
an OLAP system instead of through a lakehouse. In practice, a streaming pipeline
can write to both: an OLAP store for immediate queries and a lakehouse for
durable history and later processing.

### Idempotency

An operation is **idempotent** when repeating it with the same input leaves the
system in the same final state as running it once.

- A broker or processing engine may deliver or process an event again after a
  retry or failure.
- Without idempotency, the retry might create a duplicate payment, order, or
  output row.
- A useful design starts with a stable unique key, such as an event ID or a
  business key plus version. The destination can use that key to recognize work
  it has already applied.
- The goal is not to prevent every repeated computation. The goal is to prevent
  repeated work from producing an incorrect final result.
- Whether idempotency is needed—and how to implement it—depends on the source,
  destination, and business operation.

### Error handling and fault isolation

Handle failures as specifically as possible. A pipeline should explain what
failed, preserve enough information to investigate it, and avoid turning one
bad record into an unexplained failure of an entire delivery.

Common strategies include:

- retrying temporary failures, usually with increasing delays;
- sending failed messages to a dead-letter queue (DLQ);
- moving invalid files or records to a quarantine location;
- alerting an operator when retries are exhausted; and
- recording which inputs succeeded and failed so the correct scope can be run
  again.

Retries must be limited. Retrying a permanent schema error forever wastes
resources and delays other work. Some errors should also stop the whole job—for
example, a missing required column across every input may indicate that the
source contract changed.

The lecture example below isolates failures by file so one missing or malformed
CSV does not immediately stop the other files from being attempted:

```python
import pandas as pd

files = [
    "customers_2026_09_01.csv",
    "customers_2026_09_02.csv",
    "customers_2026_09_03.csv",
]

failures = []

for file in files:
    try:
        print(f"Processing {file}...")

        # Extract
        df = pd.read_csv(file)

        # Validate
        required_columns = ["customer_id", "name", "email"]
        missing = [column for column in required_columns if column not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Transform
        df["email"] = df["email"].str.lower()

        # Load
        output_file = file.replace(".csv", ".parquet")
        df.to_parquet(output_file)
        print(f"Successfully processed {file}")

    except FileNotFoundError as error:
        failures.append((file, str(error)))
        print(f"FILE ERROR: {file} does not exist")

    except pd.errors.ParserError as error:
        failures.append((file, str(error)))
        print(f"CSV ERROR in {file}: {error}")

    except ValueError as error:
        failures.append((file, str(error)))
        print(f"VALIDATION ERROR in {file}: {error}")

    except Exception as error:
        failures.append((file, str(error)))
        print(f"UNEXPECTED ERROR in {file}: {error}")

    finally:
        print(f"Finished attempt for {file}\n")

if failures:
    print(f"Completed with {len(failures)} failed file(s).")
```

The general Python structure is:

```python
try:
    process_data()
except SomeSpecificError as error:
    handle_expected_error(error)
except Exception as error:
    handle_unexpected_error(error)
finally:
    cleanup()
```

In production, use structured logging rather than `print()`. A DLQ fits failed
messages, while a quarantine location is usually clearer for bad files or
records. Catch specific exceptions first and use `except Exception` only as a
final boundary where the failure will be logged, counted, and surfaced. Do not
silently report the whole pipeline as successful when required inputs failed.

## Lecture framing: the data engineer's role

The lecture placed more emphasis on infrastructure—computer hardware, cloud
resources, clusters, and monitoring—than a typical application-development
discussion. That does not mean coding or the data itself is unimportant. It
means a data engineer must also understand where the work runs and why a job is
slow or failing.

When the data is too large or too slow to process on one practical machine, the
work is divided across a distributed system. Data engineers help configure the
processing, allocate resources, schedule tasks, and monitor performance.
Platform, DevOps, or SRE teams may manage the underlying equipment and cloud
services, depending on the organization.

Data scientists often work more directly on analysis and model development.
The data engineer builds the pipeline that makes reliable data available to
them and to other consumers. The exact boundary differs by company.

The lecture highlighted three common uses of prepared data:

- **Visualization:** maps, charts, dashboards, and reports. This may not be the
  largest part of a data engineer's day, but the pipeline must support it.
- **Machine learning:** the data engineer normally prepares and delivers the
  training or inference data; a data scientist or ML engineer may build the
  model.
- **LLM enrichment:** company data can be supplied to an AI application. With
  retrieval-augmented generation (RAG), the system retrieves relevant company
  documents or records and includes them as context for the language model.

## Review questions

### Computer hardware

1. Why can a computer have a fast CPU but still process a large dataset slowly?
2. What is the difference between latency and bandwidth?
3. Why do computers need registers, cache, DRAM, and persistent storage instead
   of using one type of memory for everything?
4. What happens when a job needs more working memory than the available DRAM?
5. Why is sequential access usually better than random access on an HDD?
6. Why can many small writes be difficult for an SSD?
7. What kind of work is a GPU better suited for than a CPU, and what kind of
   work is it worse at?

### Distributed systems and pipelines

8. Why are three computers connected to the same LAN not automatically a
   distributed system?
9. What new problems appear when a job is divided across several machines?
10. In the daily 150 GB example, what should be monitored to make sure the batch
    finishes before the next delivery?
11. What is the main difference between ETL and ELT?
12. Why might a modern system still choose ETL for part of its pipeline?
13. What does the Bronze layer preserve, and why should raw data still have
    ownership and security rules?
14. How do the purposes of the Silver and Gold layers differ?
15. What does an open table format add on top of data files such as Parquet?

### Batch, streaming, and reliability

16. What business requirement would justify stream processing instead of a
    scheduled batch?
17. What is the difference between a message broker and a stream-processing
    engine?
18. How does micro-batch processing differ from event-at-a-time processing?
19. Why might one stream feed both a real-time OLAP system and a Bronze storage
    layer?
20. What does it mean for a data operation to be idempotent?
21. How can a unique event or business key help make retries safe?
22. When should a failed record be retried, quarantined, or sent to a dead-letter
    queue?
23. Why is catching an exception without logging or reporting the failure
    dangerous in a production pipeline?

## Hardware source videos

All videos are from [Branch Education](https://www.youtube.com/@BranchEducation).
The summaries above paraphrase the English caption transcripts; sponsor segments
and channel promotion were omitted.

- [How Does Computer Cache, Memory, and Storage Work?](https://www.youtube.com/watch?v=TfhL5kBiQVI)
- [How Do Transistors Build into a CPU?](https://www.youtube.com/watch?v=_Pqfjer8-O4)
- [How Do SSDs Work?](https://www.youtube.com/watch?v=5Mh3o886qpg)
- [How Do Hard Disk Drives Work?](https://www.youtube.com/watch?v=wtdnatmVdIg)
- [How Does Computer Hardware Work?](https://www.youtube.com/watch?v=d86ws7mQYIg)
- [How Does Computer Memory Work?](https://www.youtube.com/watch?v=7J7X7aZvMXQ)
- [How Does This SSD Store 8 TB of Data?](https://www.youtube.com/watch?v=r-SivgEpA1Q)
- [How Do Graphics Cards Work?](https://www.youtube.com/watch?v=h9Z4oGN89MU)
- [The Engineering That Runs the Digital World: How Do CPUs Work?](https://www.youtube.com/watch?v=16zrEPOsIcI)

### Optional official references

- [Apache Spark cluster-mode overview](https://spark.apache.org/docs/latest/cluster-overview.html)
- [Apache Spark RDD programming guide](https://spark.apache.org/docs/latest/rdd-programming-guide)
- [Apache Spark Structured Streaming guide](https://spark.apache.org/docs/latest/streaming/index.html)
- [Apache Hadoop HDFS architecture](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [Apache Hadoop YARN architecture](https://hadoop.apache.org/docs/current/hadoop-yarn/hadoop-yarn-site/YARN.html)
- [Introduction to Apache Hive](https://hive.apache.org/docs/latest/introduction-to-apache-hive/)
- [Databricks medallion-architecture guide](https://docs.databricks.com/aws/en/lakehouse/medallion)
- [AWS Glue architecture and operation](https://docs.aws.amazon.com/glue/latest/dg/how-it-works.html)
- [Snowflake architecture and key concepts](https://docs.snowflake.com/en/user-guide/intro-key-concepts)
- [Apache Iceberg documentation](https://iceberg.apache.org/docs/latest/)
- [Delta Lake documentation](https://docs.delta.io/)
- [Apache Hudi table and query types](https://hudi.apache.org/docs/table_types/)
- [Apache Kafka introduction](https://kafka.apache.org/documentation/)
- [Amazon SQS queue types](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-types.html)
- [RabbitMQ streams](https://www.rabbitmq.com/docs/streams)
- [Apache Flink fault tolerance](https://nightlies.apache.org/flink/flink-docs-stable/docs/learn-flink/fault_tolerance/)




