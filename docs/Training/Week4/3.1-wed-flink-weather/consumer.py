"""Local Flink SQL stream with a small client-side MongoDB materializer."""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from pyflink.table import EnvironmentSettings, TableEnvironment
from pymongo import MongoClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sink', choices=['console', 'mongodb'], default='mongodb')
    args = parser.parse_args()
    jar = Path(__file__).parent / 'lib/flink-sql-connector-kafka-5.0.0-2.2.jar'
    if not jar.exists():
        raise SystemExit('Download the Kafka connector JAR using the lecture setup commands first.')

    table_env = TableEnvironment.create(EnvironmentSettings.in_streaming_mode())
    config = table_env.get_config().get_configuration()
    config.set_string('pipeline.jars', jar.resolve().as_uri())
    config.set_string('parallelism.default', '1')
    config.set_string('table.local-time-zone', 'UTC')
    table_env.execute_sql("""
        CREATE TABLE weather_source (
            kafka_key STRING,
            topic STRING METADATA VIRTUAL,
            kafka_partition INT METADATA FROM 'partition' VIRTUAL,
            kafka_offset BIGINT METADATA FROM 'offset' VIRTUAL,
            city STRING, latitude DOUBLE, longitude DOUBLE,
            temperature DOUBLE, feels_like DOUBLE, humidity INT,
            precipitation DOUBLE, cloud_cover INT, pressure DOUBLE,
            wind_speed DOUBLE, wind_direction INT, weather_code INT,
            event_time STRING
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'homework-weather',
            'properties.bootstrap.servers' = 'localhost:9092',
            'properties.group.id' = 'lecture-flink-weather',
            'scan.startup.mode' = 'earliest-offset',
            'key.format' = 'raw',
            'key.fields' = 'kafka_key',
            'value.format' = 'json',
            'value.fields-include' = 'EXCEPT_KEY',
            'value.json.fail-on-missing-field' = 'false',
            'value.json.ignore-parse-errors' = 'false'
        )
    """)
    # SQL executes inside Flink's JVM operators; Python receives the results.
    result = table_env.execute_sql("""
        SELECT *, ROUND(temperature * 9.0 / 5.0 + 32.0, 1) AS temperature_f,
            CASE WHEN temperature < 20.0 THEN 'cold' ELSE 'warm' END AS weather_status
        FROM weather_source
        WHERE city IS NOT NULL AND temperature IS NOT NULL
            AND humidity BETWEEN 0 AND 100
    """)
    client = None
    try:
        collection = None
        if args.sink == 'mongodb':
            client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            collection = client['flink_streaming']['weather']
            collection.create_index([('processed_at', -1)])
        print(f'Started Flink stream → {args.sink}; reading retained Kafka records.', flush=True)
        with result.collect() as rows:
            for row in rows:
                document = row.as_dict()
                # Stable Kafka record identity makes replay overwrite the same document.
                document['_id'] = f"{document['topic']}:{document['kafka_partition']}:{document['kafka_offset']}"
                document['processed_at'] = datetime.now(timezone.utc)
                if collection is not None:
                    collection.replace_one({'_id': document['_id']}, document, upsert=True)
                print(document, flush=True)
    finally:
        if client is not None:
            client.close()
        job = result.get_job_client()
        if job is not None:
            job.cancel()


if __name__ == '__main__':
    main()
