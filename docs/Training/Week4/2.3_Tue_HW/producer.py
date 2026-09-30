# Adapted from the class weather producer. TODO: choose your locations/data changes.
from kafka import KafkaProducer
from datetime import datetime, timezone
import requests
import json
import time

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    key_serializer=lambda k: k.encode("utf-8"),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

cities = {
    "Boise": {
        "latitude": 43.6150,
        "longitude": -116.2023
    },
    "New York": {
        "latitude": 40.7128,
        "longitude": -74.0060
    },
    "London": {
        "latitude": 51.5074,
        "longitude": -0.1278
    },
    "Tokyo": {
        "latitude": 35.6762,
        "longitude": 139.6503
    },
    "Sydney": {
        "latitude": -33.8688,
        "longitude": 151.2093
    }
}

url = "https://api.open-meteo.com/v1/forecast"

while True:

    for city, coordinates in cities.items():

        params = {
            "latitude": coordinates["latitude"],
            "longitude": coordinates["longitude"],
            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "weather_code",
                "cloud_cover",
                "pressure_msl",
                "wind_speed_10m",
                "wind_direction_10m"
            ])
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=10
            )

            response.raise_for_status()

            current = response.json()["current"]

            message = {
                "city": city,
                "latitude": coordinates["latitude"],
                "longitude": coordinates["longitude"],

                "temperature": current["temperature_2m"],
                "feels_like": current["apparent_temperature"],
                "humidity": current["relative_humidity_2m"],
                "precipitation": current["precipitation"],
                "cloud_cover": current["cloud_cover"],
                "pressure": current["pressure_msl"],
                "wind_speed": current["wind_speed_10m"],
                "wind_direction": current["wind_direction_10m"],
                "weather_code": current["weather_code"],

                "event_time": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            producer.send(
                "homework-weather",
                key=city,
                value=message
            )

            print(message)

        except Exception as e:
            print(f"Error retrieving {city}: {e}")

    producer.flush()

    time.sleep(60)
