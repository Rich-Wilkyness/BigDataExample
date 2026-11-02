"""Publish synthetic labeled transactions for training and live inference."""

import json
import time
import uuid
import argparse
from datetime import datetime, timezone

import numpy as np
from kafka import KafkaProducer

# --rate is a command-line setting in transactions per second. Use a
# positive value, such as --rate 10, so the sleep interval below is valid.
parser = argparse.ArgumentParser()
parser.add_argument("--rate", type=float, default=5)
args = parser.parse_args()

# No fixed seed is supplied: this process generates a fresh random stream
# each time. It is a controlled simulation, not actual financial records.
rng = np.random.default_rng()

# Kafka transports bytes. value_serializer converts a Python dictionary
# into JSON text and then UTF-8 bytes. acks=all waits for the in-sync
# replicas; with one broker this still means only one stored replica.
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    acks="all"
)

count = 0

print(f"Generating {args.rate} transactions per second")

try:
    while True:
        # Generate the label first, then sample different feature distributions
        # for each class. About 8% of events are labeled fraud by construction.
        # The model will learn these synthetic differences, not real-world rules.
        is_fraud = int(rng.random() < 0.08)

        # Fraud-labeled examples tend toward larger amounts, unusual hours,
        # greater distance, new devices, and more recent transactions. The two
        # classes still overlap, so labels are not perfectly obvious from amount.
        if is_fraud:
            amount = rng.lognormal(5.5, 0.8)
            hour = int(rng.choice([0, 1, 2, 3, 4, 22, 23]))
            distance = rng.exponential(150)
            new_device = int(rng.random() < 0.75)
            velocity = int(rng.poisson(7))
        else:
            amount = rng.lognormal(3.5, 0.9)
            hour = int(rng.integers(0, 24))
            distance = rng.exponential(25)
            new_device = int(rng.random() < 0.15)
            velocity = int(rng.poisson(2))

        # Use a stable event identity for downstream replay/deduplication. Convert
        # NumPy scalars to native Python numbers so json.dumps can serialize them.
        # is_fraud is supervised ground truth; inference must exclude it from X.
        transaction = {
            "transaction_id": str(uuid.uuid4()),
            "event_time": datetime.now(timezone.utc).isoformat(),
            "amount": round(float(amount), 2),
            "hour": hour,
            "distance_from_home": round(float(distance), 2),
            "new_device": new_device,
            "transactions_last_hour": velocity,
            "is_fraud": is_fraud
        }

        # A transaction ID key gives consistent partition routing for that key.
        # The demo uses one partition; ordering is partition-scoped, not global
        # across an arbitrary multi-partition deployment. send() queues a write.
        producer.send(
            "fraud-transactions",
            key=transaction["transaction_id"].encode("utf-8"),
            value=transaction
        )

        count += 1

        # Periodically wait for pending sends instead of flushing every record.
        # This is a simple classroom producer, not an application-level retry log.
        if count % 50 == 0:
            producer.flush()
            print(f"Produced {count} transactions")

        # Throttle the generator. Processing time adds overhead, so the requested
        # rate is approximate; this is not a throughput benchmark.
        time.sleep(1 / args.rate)

except KeyboardInterrupt:
    print("\nStopping producer...")
# When Ctrl+C stops the loop, wait for pending sends and close resources.
finally:
    producer.flush()
    producer.close()
