

Questions

Spark
Describe the architecture of Spark

Sparks architecture involves 3 major components, the driver, the executors, and 
the cluster manager.

The driver, also called the driver application, is the application that we write when developing Spark jobs.

The executors are JVM processes the run on Sparks worker nodes. The number of them on each node will depend on the requirements of the job. Their function is to process the data in parallel.

The cluster manager is the component that organizes the other components. It makes decisions about which tasks to send to which executors and how many resources to provide to which part of the cluster. If we are running Spark on a Hadoop system, we use YARN as the cluster manager, but we can use Sparks standalone cluster manager when doing testing, and we can also use Kubernetes for the cluster manager if working on a Kubernetes system.

(Note: do not mention Mesos, nobody uses it)

Difference between RDD and DF

RDDs are the most basic data structure in Spark, which behave like arrays in other 
programming languages. 

DataFrames are the most common data structure used in Spark today, and they resemble SQL tables. They have rows, columns, and a schema.

DataFrames are actually an abstraction over RDDs, so they act as syntactic sugar. Spark's engine interprets them as RDDs for the purposes of data processing.

Transformation vs Action

Transformations and actions are both categories of tasks in Spark's processing engine. 

A transformation is any task that accepts an RDD and returns a modified RDD. Examples include map and filter.

An action is any task that accepts an RDD and returns something other than an RDD. Examples include collect and count.

Narrow transformation vs Wide transformation

A narrow transformation is any kind of transformation which does not shuffle the data, and therefore does not constitute the end of a stage or job. Examples include map and filter.

A wide transformation is any kind of transformation which shuffles the data, and therefore constitutes a shift from one stage to the next. Examples include reduceByKey, groupByKey, and join.

What is lazy evaluation

Lazy evaluation is the principle in Spark tasks are not executed until a shuffle or action is performed. This allows Spark's optimizer to find potential ways of executing the same series of tasks in a more efficient way.

What happens when you submit a spark job

NOTE: The answer to this question is similar to a general question about Spark's archiecture and should be treated as such.

When a Spark job is submitted with spark-submit, the first thing that happens is that the driver application is run. The tasks to be performed are gathered and sent to Spark's optimizer, which constructs a logical plan and a physical plan in for executing them in the most efficient way possible. 

After the plans have been selected, the job is sent to Spark's cluster manager, which divides the data among the executors running on the worker nodes and provisions resources according to the parameters specified in the spark-submit command and/or the Spark config.

The executors then begin processing the data in parallel. When they are finished, they return the data to the cluster manager, which directs them to the output location specified in the driver.

Client mode vs cluster mode

Client mode is a setting in Spark which is used for small-scale experimentation and testing, and is what should be used when developing Spark jobs on a laptop.

Cluster mode is for executing distributed processing jobs on a compute cluster. It is what should be used when executing a Spark job for practical data processing.

Difference between a DF and a DS

DataFrames and DataSets are similar Spark APIs, but which have a few critical differences.

They both look like SQL tables, but DataSets have the additional feature of ensuring type safety at compile time. For this reason, DataSets are only available in Spark Scala, as Python is not a compiled language and therefore doesn't have compile time. Type safety at compile time gives us as developers the ability to catch type errors more quickly because is there is an issue with data types, the compilation will fail and force us to go back and fix any issues before we compile the code.

Note - type safety means the 100% assurance that a piece of data will be of the type that we expect. This is usually enforced by statically typed languages (such as Java), meaning languages that force the developer to explicitly specify data typles. The alternative is dynamically typed languages (such as Python) where data types are determined during the program's excution based on context. Dynamically typed languages cannot be said to be type safe, as there is a small chance that the program will interpret a piece of data as one type when it was intended to be another.

Difference between a Pandas DF and a Spark DF

Pandas was where the concept of the DataFrame originated, and the idea was incorporated into Spark at a later time.

The major difference between them is that Pandas is not a distributed processing framework, so data processing can only ever be performed on one machine, never on a cluster. Spark dataframes, on the other hand, are processed in a distributed way on a compute cluster, making them more suitable for processing extremely large datasets.

They also have different APIs, meaning different commands that are used to perform the same operation.

Coalesce vs repartition

Coalesce and repartition are both ways of changing the sizes of the partitions in your data.

Coalesce will take the partitions that are present on each node of the cluster and combine them together, resulting in larger sized partitions. This is in line with the meaning of the English word coalesce, which means to bring things together into a larger whole (eg, miilitary forces can coalesce when smaller units come together to former a larger fighting force). It is only capable of creating larger partitions, never smaller ones, and it does not guarantee that the output partitions will be equally sized. This is useful when we want larger partitions and do not need for the partitions to be of equal size. 

Repartition is similar, and under the hood the first thing that repartition does is perform a coalesce operation. However, after performing it, it will also do a full shuffle of the data. This means that repartition is able to give us more control over the size of the output partitions, meaning that they can be either larger or smaller than the input partitions. It guarantees equally sized output partitions as well. Because it can guarantee equally sized output partitions, it is one of the best methods for preventing the problem of data skewness.

What’s a shuffle?

A shuffle is an operation that changes the order of the rows in a dataset.

Transformations that do not shuffle the data are called narrow transformations, and multiple of them can be performed in one stage.

Transformations that do shuffle the data are called wide transformations, and executing one of them will transition the spark job from one stage to the next stage.

A classic example of an operation that shuffles the data is a GroupBy, which needs to change the order of the rows by definition because it is arranging similar rows to be next to each other. Another example is when we perform a repartition, which shuffles the data in order to get evenly sized partitions as output.

Shuffling the data is computationally expensive, meaning that it requires a lot of compute power and time to perform. Therefore, to optimize a Spark job, we need to make sure that we are only shuffling the data when it is absolutely necessary to do so.



What is the DAG?

The term DAG stands for Directed Acyclic Graph, a concept in graph theory (a branch of mathematics) that represents an operation where we move from one step of an operation to another in ordered way, with no ability to go backwards. In the graph, the circles are called nodes and the lines are called edges.

In Spark, the concept of the DAG is used  the execution engine in order to plan the execution of the entire program. Collections of transformations are grouped into nodes in the DAG, and a wide transformation represents a transition from one node to the next. 

Note: when the term "node" is used above, it DOES NOT REFER TO A NODE IN THE CLUSTER.

What is a logical plan vs a physical plan?

Both of them are plans for how to execute a data processing job as efficiently as possible.

A logical plan is a high-level representation of what is happening to the data during processing, which aligns with the way we as programmers think about the data operations.

A physical plan is a low-level representation of the operations that the computer will perform in order to implement the logical plan. There are optimizations that can be made at this stage which could not be made from the perspective of logical data operations.

The most efficient plans are selected by the optimizer and submitted to the cluster manager, which uses them to orchestrate the operations to be performed on the cluster.

How is a Spark application divided into jobs, stages, and tasks?

Tasks are individual operations that represent any narrow transformation, wide transformation, or action.

Tasks are grouped into stages, which are divided from each other by wide transformations, which shuffle the data and cause the DAG to move from one stage to the next.

If the program contains more than one action, there are said to be multiple jobs. Jobs are divided from each other by the execution of an action, which results in an output value that is not an RDD.

What is a driver?

The driver application is the program that we write when we are developing a Spark job. It contains the logic that the program will execute when it is submitted. 

What is an executor?

An executor is a JVM process that is part of Spark. It is a software process which serves to perform processing tasks.

Note: AN EXECUTOR AND A NODE ARE NOT THE SAME THING!!!!!!!

Executors are software processes which run on nodes, which are physical machines. There will usually be multiple executors running on a single node. The number of executors running on each node can be specified either in the config section of the part of the program that defines your SparkSession, or in the spark-submit command. 

What are some common spark-submit parameters?

num-executors: specifies how many executors we want to run on our cluster

executor-cores: specifies the number of CPU cores assigned to each executor

executor-memory: specifies the amount of RAM assigned to each executor

driver-memory: specifies the amount of RAM assigned to the driver application

jars: specifies any additional code that will be provided to the Spark execution using a jar file (for example, you need jar files to work with XML or Avro files in Spark)

py-files: specifies any additional code that will be provided to the Spark execution using Python files, which will be zipped in order to pass them to our application

class: If your Spark application is written in Scala, you have to specify which class is the main one, which you do using the class parameter

master: specifies either the master node or the cluster manager that you will be using for your application (for example, when running Spark on a Hadoop cluster, master will most likely be set to YARN)

deploy-mode: specifies whether we are running the application in client mode or cluster mode


What is data skew? How do you fix it?

Data skew, also called data skewness, is a problem that occurs in distributed data processing in which the partition sizes are uneven, and so the executor which receives the largest partition will take a larger amount of time than the rest, and therefore will take more time than the rest, which causes the job to take longer than it should.

If the extra data that the one executor has were instead spread across the cluster, the processing would be more efficient and the job would take less time. So, the solution to this problem will involve doing this. There are three methods for solving this problem:

use a simple repartition operation, which will resize the partitions to approximately equal sizes
use salting, which involves creating a new column with specific values added to every x number of rows, which we then use to repartition the data in order to have finer control over the size of our partitions
If using Spark 3.0 or later, turn on adaptive query execution. One of the optimizations included with AQE is called Dynamic Partition Pruning, or DPP, which can automatically detect unevenly sized partitions and resize themk without additional input from the programmer. This is the most modern solution. 

What is a cluster manager? Which ones have you used?

A cluster manager is a program which organizes and orchestrates Spark jobs, particularly when run on a cluster. There are 3 major options for cluster managers to use:

YARN - this is what we use when running Spark on a Hadoop cluster. It is a part of core Hadoop and also serves as Hadoop's load balancer and as a tool for administering the Hadoop cluster.
Spark's built in cluster manager: this is when we use when running Spark in client mode on a laptop for testing. It is simple to use, but it is not robust enough for use in production.
Kubernetes: If running Spark on a Kubernetes cluster, Kubernetes itself can be used as Spark's cluster manager

DO NOT MENTION APACHE MESOS. In over five years of doing interviews, I have never once heard an interviewer mention this technology.

Difference between SparkContext and SparkSession

SparkContext was the original point of entry for Spark applications. From within a SparkContext, we gain access to the RDD API. It has been obsolete for this purpose since the release of Spark 2.0, but a SparkContext can still be created within a SparkSession if we want to work directly with RDDs in a modern Spark project.

SparkSession is the point of entry for all modern Spark projects. It is part of Spark SQL, which was introduced in Spark version 2.0. It gives us access to the DataFrame API.

How do deal with an out of memory error in Spark?

This is an open-ended question with many possible answers. Some of the best are as follows:

If your cluster has more hardware resources available, you can try giving the job more resources. This is the simplest solution, but it is not always possible due to hardware constraints and the possibility of other teams needing access to the same resources.
Optimize the code to use memory as efficiently as possible. Eliminate any unnecessary processing steps, avoid shuffling the data whenever possible, and make sure that your partitions are evenly sized.
If the above two strategies do not work, you can scale the cluster to have more hardware resources. On the cloud this is simple to do, but carries a cost. On an on premises cluster this is much more complicated, and will likely involve a long process of discussions with stakeholders and business decisions to spend more money on the cluster. This is a last resort, and highly impractical for most situations.

How do you detect duplicate rows?

This can be achieved by performing a groupby operation combined with a count, then filtering the data to only include rows where the value of the count column is greater than 1.

When would you use a broadcast join?

Broadcast joins are useful in a situation where a join needs to be performed between two tables, one of which is much smaller than the other. The definition of what constitutes a "small" table is one that is less than 5 GB, although if your cluster has an unusually high amount of memory it could potentially be larger. 

The join is performed by broadcasting the smaller table to all of the worker nodes, where it is stored in the RAM of each node. Then, the larger table is distributed among the nodes, as normal in Spark. On each node, the partition of the larger table is joined to the entire smaller table. When the partitions are reassembled, the output is logically the same as if the join had been performed in the normal way, but the process will be much more efficient.

The efficiency comes from the fact that the smaller table is stored locally, so nodes have no need to communicate with each other in order to perform the join. This prevents unnecessary traffic on the LAN that connects the cluster nodes together, and saves time that would be wasted in the nodes finding the data that need to be sent to each other.

What is a broadcast variable?

A broadcast variable is one where the data it stores is sent to the worker nodes in the cluster, to be stored on the local memory of each node. This makes them more easily accessible when performing complex tasks, or when the data will be used frequently.

Broadcast variables are typically used to store DataFrames or RDDs.

Spark Streaming vs Structured Streaming

Spark Streaming is the original streaming processing API for Spark, common before the release of Spark 2.0. It processes the data using the RDD API, specifically by using something called a forEachRDD loop. This works similarly to other loops in programming, but the data that it is looping over is a continuous stream which is divided into small chunks called micro-batches. A micro-batch is an RDD that is populated with whichever data is streamed into it during a time window, the length of which you specify in the program. When the time window closes, the accumulated data is then processed as a batch in the same way that Spark does batch processing. When the processing is finished, Spark moves on to the next batch, then the next, and so on for as long ass the program continues to run. This method is called "near-real-time processing" and is approximately as efficient as programs that process streaming data in true real time.

Spark Structured Streaming is the modern way to process streaming data, using the DataFrame API. Instead of a loop, we use something called ReadStreams and WriteStreams. In this method, we declare our DataFrame similarly to how we would in a batch job, but define it as a ReadStream or WriteStream. A ReadStream will continuously read micro-batches of data into the input DataFrame, which will then be processed using the same code that would be used to process an equivalent batch DataFrame. The final DataFrame in the process will be declared as a WriteStream, which is configured to save the processed data to its output location.

What is key salting?

Key salting is a process for preventing data skewness. It is performed by creating a new DataFrame column which is populated with specific values, which change every x number of rows (defined by you as the programmer). This allows us to specify an exact number of rows that will go into each output partition. We then use repartition to partition the dataframe on the salted column, which will result in evenly sized output partitions.

What is Adaptive Query Execution?

Adaptive Query Execution, abbreviated to AQE, is the flagship feature of Spark 3.0. It contains a large number of optimizations which operate under the hood, without needing any input from the programmer other than to activatcxe the features in the config section of the SparkSession. The optimizations include:

Dynamically switching join strategies in order to increase join efficiency
Dynamically coalescing shuffle partitions, which allows us to avoid creating too many small partitions, or too few large partitions
Skew join optimization, which prevents data skew by detecting uneven partition sizes during shuffle operations and resizes the data to make the partitions even

There are others, the list is too extensive to include here.

What is Dynamic Partition Pruning?

Dynamic Partition Pruning is another new feature in Spark 3.0 which dynamically decides which partitions to read when executing a spark application, excluding any that are unnecessary. This improves the overall efficiency of the program by reducing the resources needed.

Why are UDFs less efficient in Pyspark than Spark Scala?

UDFs, or User Defined Functions, are written by the programmer of a Spark application when a task is not able to be completed by Spark's built-in functions. They are written as normal functions, then registered as UDFs by a separate line of code. They are generally not optimized to the standard of Spark's built-in functions, so even when they are executed in Scala they are considered inefficient and should be avoided if not absolutely necessary.

In Python they are less efficient because of Python's nature as a programming language. UDFs are executed in the language they are written in, which means that while Pyspark is ordinarily a wrapper for Scala code, there is no equivalent Scala code in the Spark's codebase for a UDF and do Python must be used.

Python is significantly slower to execute than Scala is. This is because of Python's nature as an interpreted language. Interpreted languages are less efficient than compiled languages because the machine code used to execute the program's commands must be decided in real time during the execution of the program, rather than beforehand as we have in compiled languages.

Because Scala is a compiled language (like all JVM languages), this work is done before the execution begins, which allows the computer's resources to be entirely used in the execution of the code. This results in much faster processing speeds than are possible with any interpreted language.

What does the collect function do?

The collect function will take an RDD and convert it to an ordinary list in whichever programming language you are using to write your Spark job.


Difference between a job, a stage, and a task

A job is the largest unit of work in Spark, a stage is in the middle, and a task is the smallest.

A task in an idividual operation performed by Spark. It can be a narrow transformation, a wide transformation, or an action.

A stage combines one or more transformations together, often multiple narrow transformation and exactly one wide transformation or action. A stage ends when a wide transformation is executed, which shuffles the data and moves the job to the next stage. The job ends when an action is performed and our result is something other than an RDD.

In what situation would it be a bad idea to use collect?

Using collect is a bad idea when the RDD you are collecting is larger than the amount of memory that you have available in your master node. Because collect converts the RDD to a programming language object, it loses its distributed nature and becomes available only on one computer. In order to work on it, that computer must store the RDD in memory. If the RDD is bigger than the available memory, this will produce and out of memory error and the Spark job will fail.

What makes an RDD resilient?

RDDs are resilient due to something called RDD lineage. Lineage is the tracking of progress through the Spark DAG for the application. Because of this, if a Spark job fails, it is able to pick up more or less where it left off before failure when executed again. 

This is in line with the meaning of the English word "resilient", which means able to persevere even when encountered with challenges or pain.




Kafka
What is a producer?

A producer is a program in Kafka which accesses data from one or more sources and ingests them into a Kafka topic. Optionally, the data can be processed before ingestion.

What is a consumer?
A consumer is a program in Kafka which receives data from a topic, optionally processes it, and puts it into a storage location.

What is a broker?

A broker is a process that is running on each node in a Kafka cluster. It is responsible for administration of the Kafka cluster, as well as for containing topics and storing data within them. 

What is a consumer group?

A consumer group is a number of consumers which work together to ingest data from a partitioned topic. One consumer can ingest data from one partition.

What is the role of Zookeeper in Kafka?

Zookeeper acts as the cluster manager in Kafka. It must be run before the broker can be run. It is an implementation of the ZAB consensus algorithm.

In more recent versions of Kafka, there is the option to alter Kafka's configuration to use a different cluster manager called KRaft, which is an implementation of the RAFT algorithm and is built into Kafka, making Zookeeper unnecessary.

What are the 4 major Kafka APIs?

Producer API - for writing producers
Consumer API - for writing consumers
Connect API - for making it simpler to connect Kafka to different data sources
Streams API - for building scalable applications that have Kafka integrated into them

What is an offset?

An offset is an integer that is attached to each message that is streamed through Kafka. Each one is unique, and they are sequential. They represent the order in which messages were streamed, so that if they arrive out of order they can be be reassembled in the order in which they were streamed. It also helps to identify if a message is missing.

What is replication?

Replication is the copying of partitions of data in a topic across the cluster. The default replication factor is 3. This helps to ensure fault tolerance.

What is a topic?

A topic is an element of Kafka which streams and stores messages. The producer sends messages to the topic, where they are stored, partitioned, and replicated. The consumer receives messages from the topic.

What is the default retention period for data stored in a Kafka topic?

7 days. This can be changed in the Kafka configuration.

The reason why it is only 7 days is because Kafka is not a database. Streaming data is retained for the purpose of being received at a later time by a consumer which was not able to receive it when it was first streamed.

What is a partition?

A partition is a sub-section of a topic, which contained a defined amount of messages that have been streamed. Each partition can be replicated across the nodes of the cluster.

What is an in sync replica?

An in sync replica is node in the cluster which stores the exact same messages as the leader. Only in sync replicas are able to be candidates in a leader election.

What is leader election?

A leader election is the process of replacing the leader when it fails. What happens is that as soon as the cluster management program (Zookeeper or KRaft) detects that the leader has failed, messages are sent to the other nodes to declare that a new leader is needed. The in sync replicas in the cluster declare that they are candidates to be the new leader. This is followed by a process of confirmation by the other nodes, called voting. If an in sync replica gains more than 50% of votes from nodes in the cluster, it becomes the new leader. Typically, the first in sync replica to declare itself a candidate will be the new leader, but there are edge cases where it can lose the election and a different node will win.

What is a leader?

The leader is Kafka's equivalent of a master node. It is the node which is responsible for communication with processes that function outside of the cluster, such as producers and consumers, therefor it is this node which actually streams the data.

What is a follower?

Followers are all of the nodes in the Kafka cluster which are not the leader. Each is running a broker, and each is helping to repllicate and store parts of the data on the cluster.

What is serialization

Serialization is the process of converting a text format or other type of format to a bytes-like format. This is for the purposes of transmitting the data over a network, which is much easier and faster to do with bytes-like data. 

De-serialization is the process of converting bytes-like format back to its original format.

When writing Kafka code in Scala or Java, the serializer must be explicitly declared in the producer, and a deserializer must be explicitly declared in the consumer. In Python, this is taken care of under the hood.

What is the max size of a Kafka message

1 MB. For this reason, Kafka is not suitable as a migration tool, but rather is a streaming data tool designed to handle large numbers of small messages.



Hadoop







What is the architecture of Hadoop?

The most important parts of Hadoop's architecture are HDFS, MapReduce, and YARN.

HDFS is the Hadoop Distributed File System. As it's name suggests, it is a file system, not a database. The files stored in HDFS are distributed across the cluster with a default replication factor of 3. This means that as many as two nodes containing the data can fail, but if one remains, then the data remains available to end users.

MapReduce is the original data processing framework for Hadoop. It processes data using mappers and reducers. These are written in a programming language such as Java, Scala, or Python. Processing is distributed across the nodes in the cluster. MapReduce was revolutionary for its ability to process huge amounts of data, but is no longer in common use. It has been replaced by Spark and other similar technologies. It was deprecated in 2022.

YARN is the cluster manager for Hadoop. From the perspective of the user, YARN is used to administer the cluster and ensure that all of the nodes are visible and functioning properly. It also acts as a load balancer, ensuring that each node gets the correct allocation of work and resources. It consists of the ResourceManager and the NodeManager. The ResourceManager is what allocates resources across the cluster. The NodeManager is the process running on each node which identifies that node to YARN and allows it to be controlled.

What is a NameNode?

The NameNode is effectively the master node in the master-slave architecture of Hadoop. It is the node that the user logs in to, and from which the user controls processes on the rest of the cluster.

What is a DataNode?

Datanodes are the slave nodes in Hadoop's master-slave architecture. Each DataNode performs its part of distributed storage on HDFS and distributed processing on MapReduce or whichever processing framework is used.

What is a secondary NameNode?

For the purposes of fault-tolerance, the idea of the secondary NameNode was introduced in Hadoop version 2.0. The secondary NameNode acts as a backup NameNode in case the main one fails, and can take over as the main NameNode in that case.

What is master-slave architecture?

Master-slave architecture describes a distributed system that consists of multiple nodes (at least 3) that are connected together, and only one of which serves as a control center for the user. The node which the user logs into is called the master node, and the nodes which are controlled by the master are called the slaves. 

Because the term master-slave has controversial political implications, some systems replace the name with master-worker or leader-follower. All of those terms refer to the same system architecture.

What is Cloudera?

Cloudera is the largest company offering Hadoop as a paid service, giving customers access to cloud-hosted Hadoop instances and an extended suite of software in addition to core Hadoop, including Hue, Impala, and Kudu.

What is the difference between Cloudera and Hortonworks

Cloudera and Hortonworks were once the two major Enterprise Hadoop companies until Cloudera purchased Hortonworks in 2019. Today Hortonworks is offered as a service by Cloudera but is de-emphasized in favor of their main product.

Hortonworks offers several additions to core Hadoop, including Ambari, Ranger, and a suite of other tools.

What is the default Hadoop block size?
128 MB


What is the small file problem?

The small file problem is an issue that is caused by saving a large number of small files on HDFS. Because the Hadoop block size is 128 MB, any file that is smaller than that will occupy an entire block, which leads to inefficient storage. It also negatively affects data processing times, so a job done on a large number of small files will be slower than a properly partitioned dataset.

Why is mapreduce not used much anymore

MapReduce fell out of favor when Apache Spark was released. Spark is able to process data 100x faster than MapReduce, and because of that, it made MapReduce obsolete.

The reason that Spark is so much faster than MapReduce is that it performs all computations in memory. MapReduce, on the other hand, performs some operations in memory and other operations on disk. It is neither the memory nor the disk that makes it slow, rather is is the transfer of data from the disk to the memory or from the memory to the disk that causes the problem. This is called Disk I/O, meaning disk input and output. The act of needing to transfer the data between different parts of the machine causes a bottleneck, meaning that the flow of data becomes restricted at that point. Because Spark does all computations in memory, it avoids the need to do Disk I/O completely, therefore removing a restriction on processing speed.



What is Sqoop?

Sqoop is a command line tool that can be used to migrate data between a standard SQL database and HDFS. Its name can be understood as "SQL to Hadoop", which describes exactly what it does. 


Clusters
What is a distributed system?

A distributed system is any group of computers that are connected together and which work together on a common task. Examples include clusters, which we use in Hadoop and Spark, as well as peer-to-peer networks (p2p) which includes systems such as SETI (Search for Extraterrestrial Intelligence) and Folding At Home (a distributed program for computing protein folds for biological research), as well as file sharing software such as Bittorrent and Napster.

Many Big Data Engineers with a masters degree have their degree in Distributed Systems.

What is a cluster?

A cluster is a specific type of distributed system in which each node is connected to each other node using a Local Area Network (LAN) connection in which all of the nodes are configured to work together on a common task. 

What is a node?

A node in a cluster refers to a physical computer which makes up one part of a compute cluster.

It is important to remember that a Spark Executor IS NOT A NODE. An executor is a software process that runs on a node. There can be multiple executors running on one node.


General Programming

What is object oriented programming

Object Oriented Programming (OOP) is a method for writing computer programs that models the world based on the concept of objects and them taking actions.
The foundational concepts of OOP are the class, the object, and the method. Because we may want to create many objects that are similar to each other, we usually create them based on a class. The class, sometimes called a "blueprint" for objects, allows us 

What is functional programming
What is a pure function:
What is a programmer API?
What is a RESTful API?
What is a higher order function?
What is the CAP theorem?
What are ACID transactions?
Structured data vs unstructured data vs semistructured data
What Is class inheritance?
What is multiple inheritance?
What does it mean to instantiate a class?
What is a package manager?
What is the SDLC?
What is compilation
What is an interpreted language?
What is Big O Notation
What is JSON format?
What is string interpolation?


String interpolation is the process of putting variables into a string whose value will depend on the context in which the string is used. Examples include f-strings in Python and s-strings in Scala






Scala
Do scala classes support multiple inheritance?

No. Multiple inheritance is not allowed in Scala. This helps us to avoid what is called the diamond problem. The diamond problem is an issue in which there is an ambiguity about which chain of logic should reference a class that is referenced by another class.

So, consider this diagram:

Class A - base class

Class B - Inherits from Class A		Class C - Inherits from Class A

Class D - Inherits form both classes B and C

When a method in class D is called, which is inherited from class A through both classes B and C, there is a problem that the compiler encounters in which it can't decide whether the class should be inheited through the chain of classes D -> B -> A or from D -> C -> A

This is the offical reason given for why multiple inheritance is not supported, but there is a way around this problem, which is the use of a trait

What is a case class

A case class is a special type of class in Scala which has key-value parameters which can be used to specify a number of traits within it.

A basic use of case classes is to define aspects of objects that can be used in a match statement for pattern matching.

The reason why case classes are important to Data Engineers is because case classes can be used to create a number of objects from which the schema can be inferred. Each key-value argument in the case class will be interpreted by Spark as the name and data type of a column in a DataFrame or DataSet, respectively.


What is a trait

A trait is an object that is similar to a class, but which is not a class. We can define methods within it and we can inherit from it. The major difference between a tait and a class is that a class can inherit from multiple traits. Also, the syntax for inheriting from traits is different.

When inheriting from class, we use the "extends" keyword, as in:

class Class_B extends Class_A

Whereas when inheriting from a traits, we can use either "extends" or "with". It's using the "with" keyword that allows us to do multiple inheritance. for example:

class Class_D extends class_A with Class_B with Class_C

Doing this allows us to implement something that is similar to multiple inheritance, but which does not cause the diamond problem.

Traits also cannot be instantiated as objects. They are only used as things to be inherited from.

It's important to remember traits are "mixed in to" classes. Even though we use the "with" keyword in the actual syntax, when we are talking about the code, we say that we are "mixing the trait into the class".

What is an abstract class?

An abstract class is a class which cannot be instantited as an object. That means that the only use for an abstract class is for other classes to inherit from it.

The reason that we have abstract classes is because there are certian classes which are not designed to be used as objects, and which the developers on a team wan to create a rule that disallows other team members from using those classes improperly.

What is the difference between an abstract class and a trait?

Both an abstract class and a trait are used exclusively for inheritance and not for instantiation as objects.

The major difference is that a trait is not a class, and therefore the rules of classes do not apply to a trait. Therefore, because an abstract class is a class, it does not allow multiple inheritance. Whereas a trait allows multiple inheritance, because it is not a class.

What is a singleton


A singleton, also called a singleton object, an an object in Scala that does not have an associted class. It is declared using the object keyword, and it cannot be instantiated more than once. It is self-instantiating and self-executing, so it is a straightforward way to write a simple app.

What is a future class
What is a sealed class
What is an implicit function
What is a closure
What is a companion object?
Nil vs Null vs null vs Nothing vs None vs Unit

Nil - represents an empty list

Null - a trait that represents a null value

null - the standard Java null value

Nothing - represents truly nothing

None - represents an absent value in an option type

Unit - a return type that is equivalent to Java's void, basically returning nothing

What is the difference between overloading and overriding?
What is SBT and how have you used it?

SBT stands for Scala Build Tool, and it is the main package managerr that is specific to Scala. Scala projects can also use Maven or other package managers, but most Scala projects use SBT because it is a simpler interface relative to Maven.

What is currying?


What is an artifact? What is a JAR file?

An artifact in JVM languages is a package of the input files and classes that you use when programming, which are compressed into a single file, which is executable on the command line. It will have the .jar extension, and it can be executed with the command "java -jar <name of your file> <any other command line arguments>"

JAR files are very useful for sharing your code and making it easier to execute your code outside of an IDE. Package management in JVM languages can be difficult if trying to execute your code outside of an IDE, but if you package your code into a JAR file, then the dependencies are included in the JAR, so you don't have to worry about your code failing because you didn't include a dependency. 

What is an option type in Scala

An option is a type of object that has the pattern Option/Some/None. It represents a way of giving us the flexibility for objects in a collection to have either some type of value or no value, to be determined at a later time. 



Python
What is an iterator

An iterator is an object that can traverse a collection.

Iterators are best known to developers by their use in loops. In the convention "for i in my_collection", i represents the iterator. It moves through the collection and is able to access the value of each element, which is necessary for a loop to function.

What is a decorator

A decorator is basically a funciton modifier. It is applied to a function by placing an @ symbol plus the name of the decorator above the name of the function, like so:

@my_decorator
def my_function():
	return

Decorators are implemented as higher order functions. They take the function that they will modify as an argument and return the function with modifications.

What is a generator

Generators are contructions in Python that allow us to traverse a collection without loading the entire collection into memory. When we use a regular loop, the entire collection must be loaded into memory in order to be used, which is a problem with very large datasets, especially datasets that are larger than the computer's available memory. 

Generators allow us to load only one element of the collection into memory at a time. This allows us to iterate through very large datasets in a memory-efficient way.

What is a dictionary

A dictionary is a data object in Python which stores data in key-value pair format, similar to a JSON object. We can use Python's json library to convert dictionaries to json files, and from json files to python dictionaries.

What is a lambda function?

A lambda function is a Python function which can be written on a single line.

A lambda function is also capable of being anonymous, unlike standard Python functions, but this is not its definition. this is because lambda functions are also capable of being named, which you can do if you assign them to a variable.

What is the GIL?

The GIL, which stands for Global Interpreter Lock, is a feature of Python that enforces single-threaded programming globally. This implies that multithreaded programming is not allowed. (multithreaded programming is programming in which two or more processes can execute at the same time, rather than sequentially)

How can you get around the limitations of the GIL?

There are two libraries that allow us to get around the GIL.

The first is called Multithreading. It's part of Python's standard library, so it does not need to be installed with PIP. It allows for multithreaded programming within a single Python environment, which means that it is limited to multithreading on a single machine. This allows you to take advantage of a multi-core processor on one machine by making use of as many as all available cores.

The other is called Multiprocessing. It allows us to do multithreaded programming across multiple Python environments, meaning that it can be programmed to do multithreaded programming across a cluster. This is essential for writing distributed programs on a cluster, which we are highly likely to need to do as data engineers.

List vs tuple

A tuple is immutable, a list is mutable - this is the standard interview answer.

Other details include that lists are declared with square brackets and tuples are declared with parentheses. Also, tuples are often used to represent rows in a dataset, while lists are usually employed when the use of the data is less rigid.

List vs set

A list allows for duplicate values and preserves the order of the elements that are put into it. A set does not allow for duplicates, and it does not preserve the order of the elements.

This means that if you want to remove duplicates from a list and you don't need to worry about the order, you can simply convert it to a set.

Which Python libraries have you used?

Pyspark, Pandas, boto3, multithreading, multiprocessing, matplotlib, seaborn, numpy, plotly, Koalas, Dask, kafka-python, pytest


Java
What is method overloading?
What is the JVM?

The JVM is one of the most important parts of Java and all other languages in the JVM family. Any language called a JVM language can be run on the JVM.

The JVM is very complex, but at its core it is a special kind of combination of compiler and interpreter.

What it does is that it will take your code written in Java, Scala, or any other JVM langauge and it will compile that code to something called Java Bytecode, which is similar to assembly language. 

The reason that we use Jave Bytecode in the JVM is to implement one of the most important features of Java, which is called Write Once, Run Anywhere.

So in compiled languages that were created before Java, one of the issues that teams would have to deal with is that the code would compile to a sequence of 0s and 1s which were designed to be run on the computer on which it was compiled. The problem with this is that if that code was then sent to another computer which runs a different kind of processor, that processor might not use the same sequences of 0s and 1s to do the same thing. So if you would write your C or C++ code on a computer running an Intel processor, and then you tried to send it to another computer which was running an AMD processor, there was a possbility of getting errors that were simply due to the fact that the processor was different. 

The JVM was created in part to solve this problem. Rather than the team having to write multiple versions of its code in order to run it on multiple types of processors, the JVM is designed to be able to run on any commercially available piece of hardware, and there is a team of people at Oracle that make sure that the latest version of the JVM is going to be to able to run on any piece of hardware that you can buy. 

This means that teams of developers who work on a JVM langauge do not need to do that themsselves, which saves a lot of programmer time, and a lot of work that most programmers find unpleasant. 

The way that Write Once, Run Anwhere is achieved is that the written code is compiled to Java bytecode, and the JVM interprets that code, using the specific way that the code is supposed to be run on the specific processor that it's running on. So, if you write your Java code on an Intel X86 processor and then try to run that same code on an ARM chip, you are guaranteed to not have any processor-related errors.

The JVM also manages memory and does other low-level tasks, but write-once-run-anywhere is its most important feature, and it's what orignally made Java into a popular language.

What version of Java is most common today?
What is Maven and how have you used it?
What is Spring Boot?
Is Java strongly or dynamically typed?
What is the difference between the JDK and the JRE?

The JRE is the Java Runtime Environment, which means that it is capable of running Java code, but it does not allow the user to write and compile their own Java code. This is the standard Java installation that comes on machines that have Java installed by default, because most computer uses only need to run Java programs, and they do not need to know how to write them. 

The JDK is the Java Development Kit, which is what you need if you are going to run your own Java code. If you are trying to run Java, Scala, or any other JVM langauge, you need to make sure that you have the JDK and not just the JRE.

SQL
Which SQL distributions have you used?
What is a schema? What properties does a schema have?
What is structured data?
What is T-SQL
What is PL/SQL
What is a window function?
What’s the difference between rank and dense_rank?
What’s an index
Clustered vs non clustered index
What is normalization?
What are the normal forms?
What are ACID transactions?
What are CRUD operations?
What is a primary key?
When to use a materialized view
What is Change Data Capture?
What are slowly changing dimensions - type 1, type 2, type 3

Hive
What is Hive

Hive is a combination of a SQL Query Engine that can work with HDFS data, as well as a Data Warehousing platform that can run on a Hadoop system. It originally used MapReduce as its processing engine, but today we are far more likely to use Tez instead, as it is the default and it has Spark-like processing speeds.

Partitioning vs Bucketing
Internal vs External table


What is the Hive Metastore

HBase
What is HBase
HBase is a NoSQL database that runs on the Hadoop stack. It is a column family type NoSQL database, which means that it uses column families as a substitute for tables. This means that queries can be performed in a way that the columns that are not queried can be completely ignored, which makes for faster query performance.

CI/CD
What CI/CD tool have you used the most
What is CI/CD?
What are integration tests?
Describe your experience with Jenkins

Infrastructure as code
What is Terraform?
What is Cloudformation?
How do you write a Cloudformation template?
How do you write a Terraform job?

AWS/Other Cloud technology

How do you submit a Spark job on EMR?

There are multiple options for how to submit a Spark job on EMR.

use spark-submit from the console while logged into the cluster, in the same way tht you would on a standard Hadoop cluster.
using the AWS CLI with the "aws emr add-steps" command, for example: 
aws emr add-steps --cluster-id j-1234567890EXAMPLE \
--steps Type=Spark,Name="Spark job",ActionOnFailure=CONTINUE,Args=[--class,org.apache.spark.examples.SparkPi,s3://my-bucket/my-spark-job.jar,100]
From the AWS Management Console (the web interface), click on your cluster, go to the "applications" section, click on spark, select "add job flow step" and select your jar or py file that contains the spark job
Using Boto3 a Spark job can be started from a locally running program, using emr_client.add_job_flow_steps

What is EMR?

EMR is essentially a Hadoop cluster that runs on a cluster of EC2 instances on the AWS cloud. It is the preferred method for running Hadoop, Hive, or Spark on AWS.

What is Glue?

AWS Glue is essentially a serverless version of Spark which runs on the AWS cloud. While heavily based on Spark, Glue had a slightly different API, the most notable feature of which is the DynamicFrame API.

Glue jobs are priced based on the number of resources provided to the job and the amount of time that the job runs. Because it is serverless, when a job is not running you are not charged any money.

What is the difference between a DataFrame and a DynamicFrame

A DataFrame is a SQL-like structured data type which is available in Spark. It contains rows, columns, and a schema, like all structured data. One restriction on it is that all rows must have the exact same number of columns.

A DynamicFrame is similar to a DataFrame, but it has a more flexible schema that allows for a dynamic number of columns for each row. This is done so that it can be optimized to work with semi-structured data in JSON format, which is the most common data format on the web.

What is a serverless service?

Any cloud service that can be used without provisioning a virtual machine can be called serverless. Examples include AWS Lambda, AWS Glue, and AWS S3.

Cloud services that require provisioning a virtual machine are NOT serverlesss. Examples include EC2, EMR, and RDS.

Some services, including Redshift, have the option to be used either serverlessly or in a server-based way.

What is AWS Athena?

Athena is a serverless SQL query engine that works with AWS S3

What is AWS Lambda?

Lambda is a serverless service in AWS that allows us to run function code without provisioning infrastructure.

What are some languages that you can use with Lambda?

Available languages include Python, Java, JavaScript, Ruby, and Go. Other JVM languages such as Scala can be used by useing the Java runtime environment, but this requires additional configuration.

How do you include dependencies in Lambda?

To include dependencies in Lambda, we have to package them in a zip file along with our function code, then put the file on S3 and tell Lambda its location.

To do this, create a virtual environment in Python and install all needed dependencies. Then go to the installation directory of the virtual envirronment, copy the dependencies to a working directory with your function code, and zip the files together. After that, copy them to the S3 bucket of your choice, then pass the location to Lambda.

What are AWS Step Functions?

Step functions are a serverless service for orchestration. They are capable of doing scheduling, but their primary purpose is to chain together a series of Lambda functions in order to create serverless algorithmsor full serverless applications.

What is AWS S3?

S3 is a serverless object store on AWS. You can use it to store files for access by other programs. If you store data in it, you can query that data using Athena.

What is used for security in AWS?

There are multiple AWS services used for security. 

The most important is IAM, which is used for Role-Based Access Control (RBAC). IAM allows you to define multiple users within a single AWS account and control which services on that account they have access to.

Another AWS service used for security is VPC, or Virtual Private Cloud. This enables you to create a separate environment only for the cloud services that you are using, which makes it more difficult for bad actors to access your services.

Another AWS service with security implications is Cloudtrail. If you are using Cloudtrail, you are able to access a log of what each user of your AWS account was doing at what time. So, if you discover something wrong, you can use Cloudtrail to determine which user it was and what they did.

How do you do CI/CD on AWS?

CI/CD can be implemented using AWS CodePipeline

What is AWS CodePipeline?

CodePipeline is a fully managed CI/CD service on AWS. It can listen for changes to repositories on Github or AWS CodeCommit (AWS's internal Git repo hosting service), then do automated testing and deployment.

How do you migrate data to AWS?

Data migration to AWS can me done with any migration tool that can access cloud services, but the usual tool to use is AWS Data Migration Service, or DMS

What is AWS DMS?

AWS DMS is their Data Migration Service, used to move data from one database to another. It can connect to databases both on-prem and in the cloud and is capable of migrating that data between either AWS or Non-AWS databases.

What is AWS RDS? What version of SQL did you use with it?

AWS RDS stands for Relational Database Service, and it's essentially an EC2-based Databaser server which can run most major SQL distributions.

Available distributions include MySQL, MariaDB, Postgres, Microsoft SQL Server, and Oracle, among others.

What is EC2?

EC2 is a service for provisioning a virtual server using AWS. This server can be used exactly the ssame was as an on-premises server with a server operating system installed on it, although this means that only the command line interface is available.

EC2 can be used for many purposes, including hosting websites, hosting on premises applications, and for general purpose development and execution of code.

What is Clouformation?

Cloudformation is the Infrastructure As Code (IAC) tool for the AWS Cloud. It allows us to build templates for all the services that we need using either JSON or YAML format, and it allows us to visualize what the environment will look like based on the template before deploying it. When it is deployed, all the services specified in the template will be provisioned and made available for use.

What is Redshift?

Redshift is the Data Warehouse platform available on AWS. Redshift is available in both server-based and serverless modes. When server-based, we provision a Redshift cluster. 

What is Kinesis

Kinesis is a serverless streaming service on AWS. It's similar to Kafka, but in place of a broker we instead have a serverless Kinesis stream. Producers and consumers can be written for Kinesis, but we can also use Kinesis Firehose in place of a consumer. Firehose is a connector program that allows us to move data directly from Kinesis into a data storage location.

What is MSK?

MSK Stands for Managed Service for Apache Kafka, and is AWS's version of Kafka. It is hosted on a cluster of EC2 instances and has many configuration options managed by AWS, which reduces the workload for the team using it. It is the premier option if you insist on using Kafka rather than Kinesis on the AWS cloud.

What is SNS?

SNS, which stands for Simple Notification Service, is a system for providing notifications to users when certain events happen in your AWS environment. These can come in the form of email, SMS texts, or push notifications on your phone. 

What is SQS?

SQS, which stands for Simple Queue Service, is a system for implementing basic streaming capability in your AWS environment. We can configure a source and a destination for streaming data and use it for that purpose. However, it is not scalable - if you plan to stream hundreds or thousands of messages per second, it is better to use a scalable streaming service such as Kafka or Kinesis

What is DynamoDB

DynamoDB is a serverless NoSQL database on AWS. It's a table-based NoSQL database, which means that it is similar to a structured database because it has rows, columns, and a schema. It is NoSQL because it has the ability to have rows with an inconsistent number of columns in a single dataset, which makes it easier to use with semi-structured data.

There are also ways of organizing the data which are not available in regular SQL databases, notably the Global Secondary Index, or GSI. A GSI will allow you to sort the data and query it based on a metric other than the primary key.

Dynamo is highly regarded for its speed, and is currently one of the most performant databases for serving applications.

What is MWAA?

MWAA stands for Managed Workflows for Apache Airflow, and is essentially Apache Airflow running on the AWS cloud

What is Redshift Spectrum

Redshift Spectrum is a query engine for AWS Redshift. It can also used instead of Athena to query data on S3. The advantage of Spectrum over Athena is that while Athena is serverless and has limitations on how much compute power can be provisioned to it, Spectrum is connected to your Redshift cluster and you can give it as much processing power as you have available on that cluster.

What is EventBridge

EventBridge is a service for generating events which are available to your entire AWS environment. They can be used to trigger any service which has an event listener, including Lambda and SNS.

What is Amazon OpenSearch

AWS OpenSearch is basically ElasticSearch running on the AWS Cloud

What is Kinesis Firehose

Firehose is a connector program that allows us to move data directly from Kinesis into a data storage location.

What is AWS Cloudwatch

Cloudwatch is a monitoring tool for the AWS environment that can provide performance metrics for any AWS services being used. It also has the feature of Cloudwatch Logs, which provides loggging for AWS services.

What is AWS Cloudtrail

Cloudtrail is another logging servicec in AWS, slightly different from Cloudwatch Logs in that it tracks user activity on the AWS cluster and can report on who did what at which time.

Azure
What is Azure Data Factory
What is Azure Databricks
What is Azure HDInsight
What is Azure SQL
What is the difference between Auzre Data Lake Service Gen 1 and Gen 2
What is Azure Synapse Analytics
What is Azure Event Hubs



Describe your GCP experience
What’s GCP Dataproc
What’s GCP Dataflow
Difference between Dataproc and Dataflow
What’s GCP Cloud Composer
Describe your experience with GC Storage
What’s Google BigQuery
What’s a federated query in BigQuery
What’s Google BigTable

What is DBT?
What is Snowflake?
What’s a virtual warehouse in Snowflake


Cassandra
What is a column family?
What is peer to peer architecture?
What is ring architecture?

The ring architecture of a feature of the hardware portion of Cassandra which provides us with a leaderless system which is optimized for high availability. In a ring architecture, each node is connected to exactly two other nodes. This can be visualized as a circle of dots connected to each other. This gives us high availability because every node is equal, with no master. If any node in a Cassandra cluster fails, the nodes to either side of the failed node simply connect. That way the ring is preserved.

What is meant by high availability?

MongoDB
What format does MongoDB use?


Monitoring and Alerting
What have you used for monitoring and alerting?
What is Cloudwatch?
What is Grafana?
What is Prometheus?
What is Splunk?

Data Lakes, Warehouses, and Lakehouses
What is a data warehouse?
What is a data lake?
What is a star schema?
What is a snowflake schema?
What is dimensional modeling?
Who is Ralph Kimball?

Git
What is Git?

Which remote repository services have you used?

Good answers include Github, Bitbucket, Gitlab, AWS Code Commit

What are the steps in committing files to a git repo?

Committing files to a Git repo involves the following steps:

Use the command "git add ." or "git add -A" in order to add the files to the shelf
Use the command "git commit -m 'my message here'" to commit the files and add a commit message
Use the command "git push origin my_branch" to push the changes to the branch of your choice

The repository that it will push to is determined by the remote origin settings, which you can configure on the CLI.

How do you move code from one git branch to another?

Use a pull request, featured in the GUI of the repository service that you are using. After you initiate the PR, then you can merge the branches. 

What is a branch?
What is a pull request?

Note: Git and repository services like Github, Gitlab, and Bitbucket are separate things
Note: Git was invented by Linus Torvalds, who is also the inventor of Linux

Testing
What is a unit test?
What unit testing frameworks have you used?

Python: Pytest, Unittest
Scala: Scalatest

What is an integration test?
What is test driven development?

Elasic Stack
What is ElasticSearch

ElasticSearch is a combination of a search engine and a NoSQL database. It is used primarily to build internal search engines for websites. Famously, it is used by Ebay to power their auction search. Data is ingested into Elasticsearch using a REST API command, and must be in JSON format to be accepted. Once it is in the database, it is searchable using a normal text search as you would find on a regular website.

What is Logstash

Logstash is a system that can connect ElasticSearch to other systems, among other features. It got its name from being a repository for ElasticSearch logs, which it still does, but not has other features and extensions. The extensions to logstash are called Beats. Popular beats include FileBeat, MetricBeat, and HeartBeat

What is Kibana

Kibana is a data visualization tool which is built into the Elastic Stack. It is JavaScript-based and runs in a website. It is known for being able to create high quality visualizations with a relatively low amount of input.

What data format does Elasticsearch accept?

JSON

How do you enter data into Elasticsearch?

Data is entered into ElasticSearch using a RESTful API command, which can be done programmatically in any programming language that supports HTTP, or it can be done using CURL

Docker
What is docker?
What is a container?
How do you list your docker containers on the CLI?
How do you list your docker containers on Dockerhub?
What is a docker image?

Kubernetes
What is Kubernetes?
What is a pod?


Apache Airflow
What is airflow?
What is a DAG?
How is an Airflow DAG different from a Spark DAG?
What is an operator?
Which operators have you used?
What are XCOMs?


Databricks
What is databricks?
What is a notebook?
Which languages can you use with Databricks?
What platforms can you use Databricks on?
What is a delta table
What is a delta live table
Describe the features of Delta Format

Delta is a data format that is primariily used in Databricks. It is very similar to Parquet format. It's structured, it's columnar, and it's compressed. One feature that it has which Parquet does not have is called time travel. Time travel allows us to query not just the most current version of the data, but also any past versions of the data

What is DBFS
What is Delta Lake
What’s the medallion architecture
What’s a data lakehouse

Agile
What should you say when asked about agile in an interview?

Data Formats:
What is parquet?
What is ORC
What is Avro

Machine Learning/
What is the K Nearest Neighbors Algorithm
What is linear regression

DevOps
What is DevOps?
What DevOps tools have you used?


What was the data pipeline for your most recent project?
Python code challenge 1 - given a simple function that is missing a return statement, can the FE determine what is wrong with the function?
Python code challenge 2
Scala code challenge 1
Scala code challenge 2


Soft skills questions:
I have one bucket that holds 5 liters, and another bucket that holds 8 liters. How many buckets do I have?
What is your favorite computer operating system and why?
I have data in a csv file and I want to put it into an excel spreadsheet. How would I do that?
What are your career goals?
Name a person who you look up to, and tell me why you look up to them
What is your favorite food, sports team, or tv show, and why?
What is the most interesting thing to you about data?


Project Experience questions:
What is the source of the data?
What is the destination of the data?
What happens to the data between when you obtain it and when you are finished with it?
Talk about a problem you had in a previous project
Tell me about a disagreement that you have had with a colleague and how you resolved it

How did you communicate with stakeholders?

Who were the stakeholders in your last project?

Describe the architecture of your previous project

What's the most interesting project you've worked on?

(for any project that involves streaming data) - how many messages per second were you processing?

A normal number for messages streamed per second in Kafka is between 1,000 and 2,000


aaaaaadaddeasxadassxsaasxsaxasassazSWZAAXXSAssxsaSSWSSasaSsSZaaazazaaAassaaSasSaaAsnjjnjnjkmkmkmkmkmkm
