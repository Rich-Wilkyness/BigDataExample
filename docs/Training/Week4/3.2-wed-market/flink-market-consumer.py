import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from pyflink.common import Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy

from pyflink.datastream import (
    StreamExecutionEnvironment,
    RuntimeExecutionMode
)

from pyflink.datastream.connectors.kafka import (
    KafkaSource,
    KafkaOffsetsInitializer
)

from pyflink.datastream.functions import MapFunction


# ============================================================
# CONFIGURATION
# ============================================================

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "market_ticks"

OUTPUT_FILE = "/tmp/flink-market.jsonl"

# Local setup adaptation; processing logic remains the teacher's example.
connector = Path(__file__).parent / "lib/flink-sql-connector-kafka-5.0.0-2.2.jar"
if not connector.is_file():
    raise SystemExit("Download the Flink connector using README.md first.")
FLINK_KAFKA_JAR = connector.resolve().as_uri()


# ============================================================
# TIMESTAMP UTILITIES
# ============================================================

def parse_timestamp(value):

    if value is None:
        return None

    return datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00"
        )
    )


# ============================================================
# FLINK RECORD PROCESSOR
# ============================================================

class ProcessMarketTick(MapFunction):

    def open(self, runtime_context):

        self.output = open(
            OUTPUT_FILE,
            "a",
            buffering=1
        )

        self.counter = 0


    def map(self, value):

        # ====================================================
        # ONE KAFKA RECORD
        # ====================================================

        tick = json.loads(value)


        # ====================================================
        # ORIGINAL EVENT TIMES
        # ====================================================

        exchange_time = parse_timestamp(
            tick.get("exchange_ts")
        )

        kafka_time = parse_timestamp(
            tick.get("kafka_ts")
        )


        # ====================================================
        # DEMONSTRATION PROCESSING TIMESTAMP
        # ====================================================
        #
        # IMPORTANT:
        #
        # PyFlink crosses the Python/JVM boundary and may move
        # records between Java and Python in bundles.
        #
        # datetime.now() inside this Python operator therefore
        # measures when Python receives that bundle, not a clean
        # representation of Flink's record-at-a-time streaming
        # semantics.
        #
        # For this educational demonstration we derive the
        # processing timeline from each event's Kafka arrival
        # time and add a small simulated processing cost.
        #
        # Each record therefore retains its individual position
        # in the incoming stream.
        # ====================================================

        simulated_processing_ms = 5

        if kafka_time is not None:

            processed_time = (
                kafka_time
                +
                timedelta(
                    milliseconds=
                    simulated_processing_ms
                )
            )

        else:

            processed_time = (
                datetime.now(
                    timezone.utc
                )
            )


        # ====================================================
        # LATENCY
        # ====================================================

        if kafka_time:

            processing_latency_ms = (
                (
                    processed_time
                    -
                    kafka_time
                )
                .total_seconds()
                * 1000
            )

        else:

            processing_latency_ms = None


        if exchange_time:

            end_to_end_latency_ms = (
                (
                    processed_time
                    -
                    exchange_time
                )
                .total_seconds()
                * 1000
            )

        else:

            end_to_end_latency_ms = None


        # ====================================================
        # ENRICH EVENT
        # ====================================================

        tick["processed_ts"] = (
            processed_time.isoformat()
        )

        tick["engine"] = "flink"

        tick["batch_id"] = None

        tick[
            "processing_latency_ms"
        ] = round(
            processing_latency_ms,
            3
        ) if processing_latency_ms is not None else None

        tick[
            "end_to_end_latency_ms"
        ] = round(
            end_to_end_latency_ms,
            3
        ) if end_to_end_latency_ms is not None else None


        # ====================================================
        # OUTPUT
        # ====================================================

        self.output.write(
            json.dumps(tick)
            +
            "\n"
        )

        self.output.flush()


        self.counter += 1


        if self.counter % 100 == 0:

            print(
                f"FLINK "
                f"| events={self.counter} "
                f"| seq={tick.get('sequence')} "
                f"| symbol={tick.get('symbol')} "
                f"| price={tick.get('price')} "
                f"| processing="
                f"{processing_latency_ms:.1f} ms"
            )


        return json.dumps(tick)


    def close(self):

        if self.output:

            self.output.close()


# ============================================================
# FLINK ENVIRONMENT
# ============================================================

env = (
    StreamExecutionEnvironment
    .get_execution_environment()
)

env.set_runtime_mode(
    RuntimeExecutionMode.STREAMING
)

env.set_parallelism(1)


# ============================================================
# JARS
# ============================================================

env.add_jars(FLINK_KAFKA_JAR)


# ============================================================
# KAFKA SOURCE
# ============================================================

source = (
    KafkaSource.builder()

    .set_bootstrap_servers(
        KAFKA_BOOTSTRAP
    )

    .set_topics(
        KAFKA_TOPIC
    )

    .set_group_id(
        "flink-market-demo-v2"
    )

    .set_starting_offsets(
        KafkaOffsetsInitializer.latest()
    )

    .set_value_only_deserializer(
        SimpleStringSchema()
    )

    .build()
)


# ============================================================
# DATASTREAM
# ============================================================

stream = env.from_source(
    source,
    WatermarkStrategy.no_watermarks(),
    "Market Kafka Source"
)


processed = stream.map(
    ProcessMarketTick(),
    output_type=Types.STRING()
)


# ============================================================
# SINK
# ============================================================

processed.print()


# ============================================================
# EXECUTE
# ============================================================

print()
print("=" * 70)
print("APACHE FLINK MARKET STREAM")
print("=" * 70)
print()
print("Mode: record-at-a-time streaming")
print(f"Kafka topic: {KAFKA_TOPIC}")
print(f"Output: {OUTPUT_FILE}")
print()
print(
    "Dashboard timestamps preserve each event's "
    "individual Kafka arrival time."
)
print()


env.execute(
    "Flink Market Streaming Demo"
)
