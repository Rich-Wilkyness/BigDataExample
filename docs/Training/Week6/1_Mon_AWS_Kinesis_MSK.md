
# Lecture Notes

MSK (Managed streaming for kafka)
- less to configure 
- 

AWS Kinesis
- not kafka, but very similar
- similar idea with producers, consumers, broker (called stream instead)



Kinesis Data Streams
- is a serverless equivalent of Kafka
Kinesis Firehose
- is a message delivery system which takes the place of a consumer within a delivery pipeline
- used to connect kafka pipeline with an endpoint (redshift, s3, etc.)
- originally it did not allow for transformations
    - today it allows for transformations, but doesn't allow for spark code, can use pandas
    - serverless and not distributed, so not great for spark
    - if you need spark we use spark streaming services 

streaming processing options on AWS
1. kinesis firehose
2. Spark Structured Streaming consumer running an EMR cluster
3. glue streaming consumer
4. managed streaming for apache flink
5. lambda functions
    - only good solution in rare cases
    - example simplicity for demonstration, can include spark as a dependency
