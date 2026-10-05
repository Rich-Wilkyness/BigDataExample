"""Supplied setup: fetch simulated ticks and publish them to market_ticks."""
import argparse
import json
import time
from datetime import datetime, timezone

import requests
from kafka import KafkaProducer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=float, default=50, help="Target events per second")
    args = parser.parse_args()
    if args.rate <= 0:
        parser.error("--rate must be positive")

    producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        acks="all",
        key_serializer=lambda key: key.encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    try:
        with requests.Session() as session:
            while True:
                started = time.monotonic()
                response = session.get("http://127.0.0.1:8001/tick", timeout=5)
                response.raise_for_status()
                tick = response.json()
                # Producer-side send time; this is not a broker acknowledgement timestamp.
                tick["kafka_ts"] = datetime.now(timezone.utc).isoformat()
                producer.send("market_ticks", key=tick["symbol"], value=tick).get(timeout=10)
                if tick["sequence"] % 100 == 0:
                    print(tick, flush=True)
                time.sleep(max(0, 1 / args.rate - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        producer.close(timeout=10)


if __name__ == "__main__":
    main()
