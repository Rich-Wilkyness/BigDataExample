import streamlit as st
import pandas as pd

from pymongo import MongoClient


# -------------------------------------------------
# Page
# -------------------------------------------------

st.set_page_config(
    page_title="Real-Time Weather Streaming",
    layout="wide"
)

st.title(
    "Real-Time Weather Streaming Dashboard"
)

st.caption(
    "Open-Meteo → Kafka → Spark → MongoDB → Streamlit"
)


# -------------------------------------------------
# MongoDB
# -------------------------------------------------

client = MongoClient(
    "mongodb://localhost:27017"
)

db = client["streaming_demo"]

collection = db["weather"]


# -------------------------------------------------
# Dashboard fragment
#
# Streamlit reruns this every 2 seconds.
# -------------------------------------------------

@st.fragment(run_every="2s")
def dashboard():

    # ---------------------------------------------
    # Read latest data from MongoDB
    # ---------------------------------------------

    records = list(

        collection.find(
            {},
            {
                "_id": 0
            }
        )

        .sort(
            "processed_at",
            -1
        )

        .limit(500)
    )


    if not records:

        st.warning(
            "Waiting for weather data..."
        )

        return


    df = pd.DataFrame(records)


    # ---------------------------------------------
    # Datetime conversion
    # ---------------------------------------------

    df["processed_at"] = pd.to_datetime(
        df["processed_at"]
    )

    df["event_time"] = pd.to_datetime(
        df["event_time"]
    )


    # ---------------------------------------------
    # Latest observation for each city
    # ---------------------------------------------

    latest = (

        df.sort_values(
            "processed_at"
        )

        .groupby(
            "city"
        )

        .tail(1)

        .sort_values(
            "city"
        )
    )


    # ---------------------------------------------
    # Top-level metrics
    # ---------------------------------------------

    total_events = collection.count_documents({})

    city_count = latest["city"].nunique()

    avg_temperature = latest[
        "temperature"
    ].mean()

    avg_humidity = latest[
        "humidity"
    ].mean()


    col1, col2, col3, col4 = st.columns(4)


    col1.metric(
        "Kafka Events",
        f"{total_events:,}"
    )


    col2.metric(
        "Cities",
        city_count
    )


    col3.metric(
        "Average Temperature",
        f"{avg_temperature:.1f} °C"
    )


    col4.metric(
        "Average Humidity",
        f"{avg_humidity:.0f}%"
    )


    # ---------------------------------------------
    # Current weather
    # ---------------------------------------------

    st.subheader(
        "Current Weather"
    )


    current_weather = latest[[
        "city",
        "temperature",
        "temperature_f",
        "feels_like",
        "humidity",
        "wind_speed",
        "cloud_cover",
        "pressure"
    ]]


    st.dataframe(
        current_weather,
        use_container_width=True,
        hide_index=True
    )


    # ---------------------------------------------
    # Temperature over time
    # ---------------------------------------------

    st.subheader(
        "Temperature Over Time"
    )


    temperature_chart = (

        df.pivot_table(
            index="processed_at",
            columns="city",
            values="temperature",
            aggfunc="mean"
        )

        .sort_index()
    )


    st.line_chart(
        temperature_chart
    )


    # ---------------------------------------------
    # Current humidity
    # ---------------------------------------------

    st.subheader(
        "Current Humidity"
    )


    humidity_chart = (

        latest[[
            "city",
            "humidity"
        ]]

        .set_index(
            "city"
        )
    )


    st.bar_chart(
        humidity_chart
    )


    # ---------------------------------------------
    # Current wind speed
    # ---------------------------------------------

    st.subheader(
        "Current Wind Speed"
    )


    wind_chart = (

        latest[[
            "city",
            "wind_speed"
        ]]

        .set_index(
            "city"
        )
    )


    st.bar_chart(
        wind_chart
    )


    # ---------------------------------------------
    # Kafka information
    # ---------------------------------------------

    st.subheader(
        "Kafka Stream"
    )


    kafka_df = df[[

        "processed_at",
        "city",
        "kafka_key",
        "kafka_partition",
        "kafka_offset",
        "temperature",
        "humidity"

    ]].sort_values(

        "processed_at",
        ascending=False

    ).head(20)


    st.dataframe(
        kafka_df,
        use_container_width=True,
        hide_index=True
    )


dashboard()