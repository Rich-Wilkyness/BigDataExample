import streamlit as st
import pandas as pd
import time
from datetime import datetime
import random

st.set_page_config(
    page_title="Streaming Dashboard",
    layout="wide"
)

st.title("Real-Time Kafka Streaming Dashboard")

placeholder = st.empty()

data = []

while True:

    data.append({
        "time": datetime.now(),
        "events": random.randint(10, 100)
    })

    df = pd.DataFrame(data[-30:])

    with placeholder.container():

        col1, col2 = st.columns(2)

        col1.metric(
            "Total Events",
            len(data)
        )

        col2.metric(
            "Latest Event Count",
            df.iloc[-1]["events"]
        )

        st.line_chart(
            df,
            x="time",
            y="events"
        )

        st.dataframe(
            df.tail(10),
            use_container_width=True
        )

    time.sleep(1)