"""Collect demo 08 predictions; persist each event before committing its offset."""

import json
import os

from kafka import KafkaConsumer
from kafka.structs import OffsetAndMetadata, TopicPartition

from storage import database_path, initialize, save_prediction


# This small function accepts a consumer-like object, so commit ordering
# can be tested offline without opening a real broker connection.
def collect(consumer, path):
    for message in consumer:
        # Invalid events or database errors stop processing without committing
        # this message. Fix the input before resuming; do not silently skip it.
        # The storage context commits SQLite before this call returns. A duplicate
        # returns False but still needs its Kafka offset committed to make progress.
        inserted = save_prediction(path, message.value)
        # Commit only this partition and offset+1: Kafka stores the next position
        # to read. A crash before this commit replays the event, which SQLite
        # deduplicates. There is no distributed SQLite/Kafka atomic transaction.
        consumer.commit({
            TopicPartition(message.topic, message.partition):
                OffsetAndMetadata(message.offset + 1, "")
        })
        if inserted:
            print("Stored:", message.value["transaction_id"], flush=True)


# Create the database, then connect to Kafka only when this script is run.
# The dashboard is a separate process reading the same database file.
def main():
    path = database_path()
    initialize(path)
    # Use a group independent of training/inference/monitoring. For a fresh
    # group, latest avoids replaying old featureless classroom messages.
    # A saved group offset takes precedence over that initial-position setting.
    consumer = KafkaConsumer(
        "fraud-predictions",
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        group_id=os.getenv("FRAUD_COLLECTOR_GROUP", "fraud-flask-collector-v2"),
        auto_offset_reset="latest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    print(f"Collecting fraud-predictions into {path}", flush=True)
    try:
        collect(consumer, path)
    except KeyboardInterrupt:
        print("Stopping collector.")
    # Close the consumer even if decoding, validation, or persistence fails.
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
