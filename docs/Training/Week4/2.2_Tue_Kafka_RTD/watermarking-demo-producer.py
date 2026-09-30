from kafka import KafkaProducer
import requests
import json
from datetime import datetime
import math
import time
import random

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

while True:
    now_ms = int(datetime.utcnow().timestamp() * 1000)

    # Occasionally emit late events (5–10 seconds old)
    if random.random() < 0.2:
        event_time = now_ms - random.randint(5_000, 10_000)
    else:
        event_time = now_ms

    res = requests.get("https://api.chucknorris.io/jokes/random").json()

    message = {
        "joke": res["value"],
        "event_time": event_time
    }

    producer.send("test-topic", message)
    producer.flush()
    time.sleep(1)