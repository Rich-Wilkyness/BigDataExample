"""Classify Kafka events and publish predictions with server-reported identity."""

import json
from datetime import datetime, timezone

import requests
from kafka import KafkaConsumer, KafkaProducer
from kafka.structs import OffsetAndMetadata, TopicPartition

FEATURES = ["amount", "hour", "distance_from_home", "new_device", "transactions_last_hour"]
BASE_URL = "http://127.0.0.1:5001"


def predict_event(transaction, identity, session):
    """Reject a model swap instead of emitting predictions with stale labels."""
    features = {name: transaction[name] for name in FEATURES}
    response = session.post(f"{BASE_URL}/invocations", json={"dataframe_records": [features]}, timeout=15)
    response.raise_for_status()
    body = response.json()
    if body["model"] != identity:
        raise RuntimeError("Model server changed. Restart the inference consumer to accept its new identity.")
    predicted = int(body["predictions"][0])
    actual = int(transaction["is_fraud"])
    return {
        "transaction_id": transaction["transaction_id"], "event_time": transaction["event_time"],
        "prediction_time": datetime.now(timezone.utc).isoformat(),
        "predicted_fraud": predicted, "actual_fraud": actual, "correct": predicted == actual,
        "model_version": identity["model_version"], "model_uri": identity["model_uri"],
        "source_run_id": identity["source_run_id"], "features": features,
    }


def main():
    with requests.Session() as session:
        response = session.get(f"{BASE_URL}/metadata", timeout=15)
        response.raise_for_status()
        identity = response.json()
        print("Using server-reported model:", identity["model_uri"])
        consumer = KafkaConsumer(
            "fraud-transactions", bootstrap_servers="localhost:9092",
            group_id="fraud-live-inference", auto_offset_reset="latest",
            enable_auto_commit=False,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        producer = KafkaProducer(bootstrap_servers="localhost:9092", acks="all",
                                 value_serializer=lambda value: json.dumps(value).encode("utf-8"))
        total = correct = 0
        try:
            for message in consumer:
                result = predict_event(message.value, identity, session)
                # Wait for the output acknowledgement, then commit exactly this
                # processed input's next offset. A crash here can still replay output.
                producer.send("fraud-predictions", key=result["transaction_id"].encode("utf-8"), value=result).get(timeout=10)
                consumer.commit({TopicPartition(message.topic, message.partition): OffsetAndMetadata(message.offset + 1, "")})
                total += 1
                correct += int(result["correct"])
                print(f"Predicted={result['predicted_fraud']} actual={result['actual_fraud']} "
                      f"model={identity['model_version']} cumulative_accuracy={correct / total:.1%} processed={total}")
        except KeyboardInterrupt:
            print("Stopping inference consumer.")
        finally:
            producer.flush()
            producer.close()
            consumer.close()


if __name__ == "__main__":
    main()
