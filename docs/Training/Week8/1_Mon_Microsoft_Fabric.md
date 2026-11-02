
# Lecture Notes

Topics to cover:
Microsoft Fabric Day 1:
1. OneLake
2. Lakehouse
3. Data warehouse
4. Data Factory
5. overall Fabric Architecture


Microsoft Fabric Day 2:
1. Direct Lake 
2. mirroring
3. governance/integration patterns 
4. deep hands-on application (step by step comparing to what we did on AWS, Azure, or GCP)

Going to simulate building Fabric using:
Azure Data Factory 
bronze - 
silver - 
gold - Databricks
dashboard - power bi


Notice that everything that exists in Fabric has an equivalent with Azure (excpet Power BI). So we don't need to pay for Fabric to get experience we the architecture and ideas.





Direct Lake in Power BI

It's a form of making data available to Power BI that's unique to Fabric

It should be contrasted with the other two ways to make data available, which are:
- Import = basically means what it sounds like - you select a data file and bring it in to the Power BI environment
- Direct Query = is a way of passing data directly to Power BI if you are NOT using MS Fabric
    - basically uses the SQL engine of a database in order to query a subset of the data that is stored in it and make that data available to Power BI
- Direct Lake = uses the unified platform features of OneLake to make OneLake data directly available to Power BI without needing to clone it, query it, or import any of directly into Power BI - the data stays where it is, and Power BI can simply access it

Azure SQL Mirroring
- a way to continuously replicate data from an Azure SQL Database into Microsoft Fabric's OneLake without building or scheduling a traditional ETL pipeline.

Azure EventHubs
- basically Azure's version of AWS Kinesis
- Producers and consumers for Event Hubs can use native Kafka code in order to function
    - this allows you to easily port kafka into EventHubs with little friction
    - Just like Kinesis, Event hubs replaces the broker with a distributed serverless stream


he's planning on using eventhubs to create a stream for Azure and that can also stream in data to Fabric


