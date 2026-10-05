"""Display Flink's materialized output; Streamlit does not consume Kafka."""
import pandas as pd
import streamlit as st
from pymongo import MongoClient
from pymongo.errors import PyMongoError

st.set_page_config(page_title='Flink Weather', layout='wide')
st.title('Flink Weather Dashboard')
st.caption('Open-Meteo → existing Kafka → Flink SQL → MongoDB → Streamlit')


@st.cache_resource
def mongo_client():
    return MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000, tz_aware=True)


@st.fragment(run_every='2s')
def dashboard():
    try:
        collection = mongo_client()['flink_streaming']['weather']
        records = list(collection.find({}, {'_id': 0}).sort('processed_at', -1).limit(500))
        count = collection.count_documents({})
    except PyMongoError as error:
        st.error(f'MongoDB is unavailable: {error}')
        return
    if not records:
        st.info('Waiting for Flink output. Start consumer.py and your existing weather producer.')
        return
    df = pd.DataFrame(records)
    df['processed_at'] = pd.to_datetime(df['processed_at'], utc=True)
    df['event_time'] = pd.to_datetime(df['event_time'], utc=True, errors='coerce')
    # Latest producer fetch per city within the fetched 500-document sample.
    latest = df.sort_values(['event_time', 'processed_at']).groupby('city').tail(1)
    first, second, third = st.columns(3)
    first.metric('Stored Kafka records', count)
    second.metric('Cities in recent sample', latest['city'].nunique())
    third.metric('Latest mean temperature', f"{latest['temperature'].mean():.1f} °C")
    st.caption(f"Most recent materialization: {df['processed_at'].max().isoformat()}. Charts use up to 500 records.")
    st.subheader('Temperature by producer fetch time (UTC)')
    chart = df.pivot_table(index='event_time', columns='city', values='temperature', aggfunc='mean').sort_index()
    st.line_chart(chart)
    st.subheader('Latest humidity by city')
    st.bar_chart(latest.set_index('city')[['humidity']])
    st.subheader('Recent Flink results')
    st.dataframe(df[['city', 'temperature', 'temperature_f', 'weather_status', 'humidity',
                     'event_time', 'processed_at', 'kafka_key', 'kafka_partition', 'kafka_offset']].head(20),
                 hide_index=True)


dashboard()
