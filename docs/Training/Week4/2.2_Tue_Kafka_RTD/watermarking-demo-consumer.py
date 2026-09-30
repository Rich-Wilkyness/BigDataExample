from kafka import KafkaConsumer
import json
from datetime import datetime
import os
import time

TOPIC = "test-topic"
ALLOWED_LATENESS_MS = 5_000
STATE_FILE = "checkpoint_state.json"
CHECKPOINT_EVERY_N_MESSAGES = 5
processed_since_checkpoint = 0
last_checkpoint_time_ms = None

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"max_event_time_seen": None}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


state = load_state()

max_event_time_seen = state["max_event_time_seen"]
current_watermark = (
    max_event_time_seen - ALLOWED_LATENESS_MS
    if max_event_time_seen is not None
    else None
)

consumer = KafkaConsumer(
    "test-topic",
    bootstrap_servers=["localhost:9092"],
    group_id="watermark-demo-v1",  # NEW GROUP
    auto_offset_reset="latest",    # ignore old data
    enable_auto_commit = False,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)


# max_event_time_seen = None
# current_watermark = None

print("Starting consumer with watermarking...\n")

for msg in consumer:
    event = msg.value
    event_time = event["event_time"]
    processing_time = int(datetime.utcnow().timestamp() * 1000)

    if max_event_time_seen is None or event_time > max_event_time_seen:
        max_event_time_seen = event_time
        current_watermark = max_event_time_seen - ALLOWED_LATENESS_MS

    is_late = current_watermark is not None and event_time < current_watermark


    # print(
    #     f"EventTime={event_time} | "
    #     f"ProcTime={processing_time} | "
    #     f"Watermark={current_watermark} | "
    #     f"Late={is_late}"
    # )

    # if is_late:
    #     print("  -> DROPPED or SENT TO LATE SIDE OUTPUT\n")
    # else:
    #     print("  -> PROCESSED\n")

    # save_state({
    #     "max_event_time_seen": max_event_time_seen
    # })

    processed_since_checkpoint += 1

    print("\n--- EVENT --------------------------------")
    print(f"Event time        : {event_time}")
    print(f"Processing time   : {processing_time}")
    print(f"Late event        : {is_late}")

    print("\n--- WATERMARK ----------------------------")
    print(f"Max event time    : {max_event_time_seen}")
    print(f"Current watermark : {current_watermark}")
    print(
        "Watermark action  : "
        + ("DROP (late)" if is_late else "PROCESS")
    )

    # ---- CHECKPOINT SECTION ----
    if processed_since_checkpoint >= CHECKPOINT_EVERY_N_MESSAGES:
        save_state({
            "max_event_time_seen": max_event_time_seen
        })
        consumer.commit()

        last_checkpoint_time_ms = int(time.time() * 1000)

        print("\n--- CHECKPOINT ---------------------------")
        print("Checkpoint written: YES")
        print(f"Checkpoint time   : {last_checkpoint_time_ms}")
        print("Kafka offsets     : COMMITTED")

        processed_since_checkpoint = 0
    else:
        print("\n--- CHECKPOINT ---------------------------")
        print("Checkpoint written: NO")
        print("Kafka offsets     : NOT COMMITTED")

    print("------------------------------------------")

    consumer.commit()