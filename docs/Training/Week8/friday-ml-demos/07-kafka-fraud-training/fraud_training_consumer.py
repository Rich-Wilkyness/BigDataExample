"""Persist complete labeled rows before committing exactly their Kafka offsets."""

import csv
import fcntl
import json
import os

from kafka import KafkaConsumer
from kafka.structs import OffsetAndMetadata, TopicPartition

OUTPUT_FILE = "fraud_training_data.csv"
FIELDS = ["transaction_id", "event_time", "amount", "hour", "distance_from_home",
          "new_device", "transactions_last_hour", "is_fraud"]


def append_message(file, writer, message, consumer):
    # Cooperate with snapshot_csv's shared reader lock. A trainer cannot copy a
    # half-written row, and the collector resumes as soon as the short copy ends.
    fcntl.flock(file, fcntl.LOCK_EX)
    try:
        writer.writerow({name: message.value[name] for name in FIELDS})
        file.flush()
        os.fsync(file.fileno())
    finally:
        fcntl.flock(file, fcntl.LOCK_UN)
    # Kafka stores the NEXT position. Committing fetched-but-unprocessed records
    # would risk skipping them; this mapping names only the row just persisted.
    consumer.commit({TopicPartition(message.topic, message.partition): OffsetAndMetadata(message.offset + 1, "")})


def main():
    consumer = KafkaConsumer(
        "fraud-transactions", bootstrap_servers="localhost:9092",
        group_id="fraud-training-collector", auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    try:
        with open(OUTPUT_FILE, "a+", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            fcntl.flock(file, fcntl.LOCK_EX)
            try:
                file.seek(0, os.SEEK_END)
                if file.tell() == 0:
                    writer.writeheader()
                    file.flush()
                    os.fsync(file.fileno())
            finally:
                fcntl.flock(file, fcntl.LOCK_UN)
            count = 0
            print("Collecting labeled transactions; training is a separate command.")
            for message in consumer:
                append_message(file, writer, message, consumer)
                count += 1
                if count % 100 == 0:
                    print(f"Collected {count} transactions", flush=True)
    except KeyboardInterrupt:
        print("Stopping collector.")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
