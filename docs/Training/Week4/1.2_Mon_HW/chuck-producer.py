import json
import time
from datetime import datetime, timezone

import requests
from kafka import KafkaProducer


producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    key_serializer=lambda key: key.encode("utf-8"),
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    acks="all",
)

try:
    while True:
        response = requests.get(
            "https://api.chucknorris.io/jokes/random",
            timeout=10,
        )
        response.raise_for_status()
        joke = response.json()

        event = {
            "joke_id": joke["id"],
            "joke": joke["value"],
            "length": len(joke["value"]),
            "event_time": datetime.now(timezone.utc).isoformat(),
        }

        metadata = producer.send(
            "jokes",
            key=event["joke_id"],
            value=event,
        ).get(timeout=10)

        print(
            f"sent partition={metadata.partition} "
            f"offset={metadata.offset} joke_id={event['joke_id']}"
        )
        time.sleep(1)
except KeyboardInterrupt:
    print("producer stopped")
finally:
    producer.flush()
    producer.close()
