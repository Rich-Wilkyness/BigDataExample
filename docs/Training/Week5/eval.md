## Kafka
1. what is a kafka producer?
    - connects the data being generated with the kafka pipeline, this could come from a csv, avro, parque, sql database, hive, etc.
2. what is a kafka consumer?
    - does some sort of processing as data is being handed to it by the kafka broker and then storing it 
3. what is a topic in kafka?
    - the topic is the name assigned to a kafka pipeline
    - producer publishes to it and consumer subscribes to it
    - it stores the messages, but doesn't know what it is storing
    - topic can be partitioned, not the same as spark, with topic, it is partitioned according to schemas (Schema evolution), happens on the producer level, it can partition in other ways
    - each message is not a partition, we don't wait for messages to accumulate to partition
    - for example we don't want to wait for a single robot in a factory for 1 minute to store up its information, the partition would be more accurate to say, from a region of the factory, we collect all the heat related data and group them together
4. what is serialization? what is deserialization?
    - into bytes to send over some for of networking
    - bytes are 1 step from machine code, allows for sending a form of morse code.
5. what is zookeeper? why is it not used in more recent versions of kafka?
    - older cluster management system
    - not used anymore because the cluster manager is built into kafka called Kraft
6. what is the difference between a leader and a follower? what is the process called to select a new leader? 
    - it is part of fault tolerance. leaders and followers are created as replications on different nodes. the leader is the process we are actively using, but if a node fails for whatever reason a new leader is decided and that is called an election
7. what is the maximum size of a message in kafka? 
    - 1 MB

## Snowflake
8. what does it mean that snowflake is a unified data platform?

9. what is a virtual warehouse in snowflake?
    - resources (specifically the compute layer) that snowflake uses to process your data. the "cloud". 
10. what is the principle of cpu vs storage (he phrased it differently)
    - storage/disk scales independently of cpu/data processing
    - snowflake allows for dynamic scaling up or down of either dependent on pipeline needs
11. what is the role of dbt inside snowflake?
    - ELT
12. what is a model in dbt?
    - 
13. why is there a postgres option for a snowflake environemnt?
    - can use it to migrate data from postgres to snowflake (not what he was looking for, but technically true)
    - OLAP is what snowflake is, OLTP is what postgres is. postgres is used as an option to run certain processes that require OLTP
        - often with customer facing data, since this could be for a web interface 
14. what is time travel in snowflake? what are its advantages? 
    - audit, data recovery, or cloning from a certain time 

15. what is a dynamic table?
    - elt transformations will be reflected in the upstream tables
    - incremental load, 4 times a day, regular schema, 
    - all tables involed need to be marked dynamic
    - works like a cronjob to regularly check if data has changed, 
    - we load data into bronze, and then silver and gold data automatically get handled as well

