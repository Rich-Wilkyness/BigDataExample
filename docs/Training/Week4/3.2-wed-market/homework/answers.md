# Wednesday homework answers

Assignment: [3.3_Wed_HW.md](../../3.3_Wed_HW.md).

## Part 2 — Inspect the Parquet pipeline

- Why Parquet instead of JSON?
    - Parquet can be compressed better leading to better reads and storage. also stores by column 
- What do the date/hour directories mean?
    - it's a timestamp of when events occured (not processing) and stores them by time in those directories
- Why partition using `exchange_ts` instead of `processed_ts`?
    - group by when the event occured, not processed. there can be delays in processing
- Which hourly partition should contain an event that occurred at 14:59:58 but arrived at 15:00:03, and why?
    - 14, because the timestamp is from when it was produced, not consumed

## Part 3 — Spark Structured Streaming vs. Flink

- What is a Spark microbatch, and what happens with a two-second trigger?
    - it is streaming way to send micro batches. two-second delay is to allow us to comprehend the batching
- How does Flink’s record-at-a-time model differ?
    - mainly lower latency, it is capable of sending 1 message at a time, not just a micro batch
- Why does latency matter differently for weather versus financial events?
    - financial institutions make decisions based on the data much faster. if the weather changes update 1 second to 1 minute slower, the outcome is the same. If the price of a stock moves and our competition is 1 second faster, they have the advantage to make the move
- What are event time and processing time?
    - event time is when the event happened on the producer
    - processing time: engine’s clock time when it handles the event—not necessarily after processing finishes.
- Why put Kafka between the API and processing engines?
    - kafka allows for partitioning the data, replication (fault tolerance), and creating a durrable event log of events to be processed

## Part 4 — Architecture diagram

TODO: Draw your diagram and save it as `architecture.png` beside this file.
containing the market generator, Kafka, Spark Structured Streaming, Flink, Streamlit, and Parquet. Show data flow, then add Snowflake where you think it belongs.

                                                                    Streamlit
                                         Spark Structured Streaming / 
Market Generator -> Producer -->  Kafka --->        OR            ------> other outputs (console, database, etc.)
                                             Apache Flink          \
                                                                    Parquet --> Snowflake


