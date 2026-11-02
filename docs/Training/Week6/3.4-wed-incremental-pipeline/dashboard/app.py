import os
from datetime import datetime, timezone
import pandas as pd
import requests
import streamlit as st
import pydeck as pdk

st.set_page_config(page_title='Citi Bike Live | NYC', layout='wide')
st.title('NYC Citi Bike | Live Station Dashboard')
st.caption('Live data: Citi Bike GBFS. Historical data: AWS Redshift (optional).')

BASE = 'https://gbfs.citibikenyc.com/gbfs/en'
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'CitiBikeClassDashboard/1.0'})

@st.cache_data(ttl=60, show_spinner=False)
def get_json(url):
    response = SESSION.get(url, timeout=20)
    response.raise_for_status()
    return response.json()

@st.cache_data(ttl=60, show_spinner=False)
def load_stations():
    # GBFS v2 endpoints. Fallback to autodiscovery for deployments using alternate feed URLs.
    try:
        info = get_json(f'{BASE}/station_information.json')
        status = get_json(f'{BASE}/station_status.json')
    except (requests.RequestException, ValueError):
        manifest = get_json(f'{BASE}/gbfs.json')
        feeds = manifest.get('data', {}).get('en', {}).get('feeds', [])
        if not feeds:
            feeds = manifest.get('data', {}).get('feeds', [])
        urls = {f['name']: f['url'] for f in feeds}
        info = get_json(urls['station_information'])
        status = get_json(urls['station_status'])
    i = pd.DataFrame(info['data']['stations'])
    s = pd.DataFrame(status['data']['stations'])
    df = i.merge(s, on='station_id', suffixes=('', '_status'))
    for col in ('num_bikes_available', 'num_docks_available', 'num_bikes_disabled', 'capacity'):
        if col not in df:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    def ebikes(types):
        if not isinstance(types, list):
            return 0
        return sum(int(x.get('count', 0) or 0) for x in types if 'electric' in str(x.get('vehicle_type_id', '')).lower() or 'ebike' in str(x.get('vehicle_type_id', '')).lower())
    df['electric_bikes'] = df.get('vehicle_types_available', pd.Series([None]*len(df))).apply(ebikes)
    df['utilization_pct'] = (100 * df.num_bikes_available / df.capacity.replace(0, float('nan'))).fillna(0).clip(0, 100)
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    return df.dropna(subset=['lat', 'lon']), status.get('last_updated')

metric = st.sidebar.selectbox('Map metric', ['Available bikes', 'Available docks', 'Electric bikes', 'Station utilization (%)'])
metric_col = {'Available bikes':'num_bikes_available', 'Available docks':'num_docks_available', 'Electric bikes':'electric_bikes', 'Station utilization (%)':'utilization_pct'}[metric]
min_value = st.sidebar.slider('Minimum selected metric', 0, 100, 0)
show_only_renting = st.sidebar.checkbox('Only stations currently renting', value=True)
st.sidebar.caption('Data cached for 60 seconds. Press R or use the menu to refresh.')
try:
    df, last_updated = load_stations()
except Exception as exc:
    st.error(f'Unable to fetch live GBFS data: {exc}')
    st.stop()
if show_only_renting and 'is_renting' in df:
    df = df[df.is_renting.astype(str).str.lower().isin(['1', 'true'])]
df = df[df[metric_col] >= min_value].copy()
if df.empty:
    st.warning('No stations match the filters.')
    st.stop()

c1,c2,c3,c4 = st.columns(4)
c1.metric('Stations displayed', f'{len(df):,}')
c2.metric('Bikes available', f'{df.num_bikes_available.sum():,.0f}')
c3.metric('Docks available', f'{df.num_docks_available.sum():,.0f}')
c4.metric('Electric bikes (reported)', f'{df.electric_bikes.sum():,.0f}')
if last_updated:
    st.caption('GBFS last updated: ' + datetime.fromtimestamp(int(last_updated), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))

# Color buckets: low red, medium orange, high green; utilization is percentage based.
thresholds = (20, 60) if metric_col == 'utilization_pct' else (3, 10)
def color(v):
    return [210, 54, 63, 190] if v < thresholds[0] else ([245, 166, 35, 190] if v < thresholds[1] else [29, 156, 92, 190])
df['color'] = df[metric_col].apply(color)
df['radius'] = 50
st.markdown(f'**Map: {metric}** · Red: < {thresholds[0]} · Orange: {thresholds[0]}–{thresholds[1]-1} · Green: ≥ {thresholds[1]}')
layer = pdk.Layer('ScatterplotLayer', data=df, get_position='[lon, lat]', get_fill_color='color', get_radius='radius', radius_min_pixels=4, radius_max_pixels=13, pickable=True)
st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=pdk.ViewState(latitude=40.735, longitude=-73.985, zoom=11), tooltip={'html':'<b>{name}</b><br/>Bikes: {num_bikes_available}<br/>Docks: {num_docks_available}<br/>Electric bikes: {electric_bikes}<br/>Capacity: {capacity}<br/>Utilization: {utilization_pct}%'}), use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader('Top stations')
    st.dataframe(df[['name','num_bikes_available','num_docks_available','electric_bikes','utilization_pct']].sort_values(metric_col, ascending=False).head(20), hide_index=True, use_container_width=True)
with right:
    st.subheader('Availability distribution')
    st.bar_chart(df[metric_col].value_counts(bins=12, sort=False).sort_index().rename('stations'))

st.subheader('Historical snapshots from Redshift')
st.caption('Optional: enable the Redshift Data API with the EC2 instance role. This uses aggregated canonical snapshot counts.')
if st.button('Load Redshift history'):
    try:
        import boto3
        client = boto3.client('redshift-data', region_name=os.getenv('AWS_REGION','us-east-2'))
        args = {'WorkgroupName': os.getenv('REDSHIFT_WORKGROUP','richard-citibike-wg'), 'Database': os.getenv('REDSHIFT_DATABASE','dev'), 'Sql': "SELECT DATE_TRUNC('hour', snapshot_timestamp) AS hour_utc, COUNT(*) AS observations, COUNT(DISTINCT station_id) AS stations FROM gold.incremental_fact_station_snapshot WHERE snapshot_timestamp >= DATEADD(day, -2, GETDATE()) GROUP BY 1 ORDER BY 1 DESC LIMIT 100"}
        import time
        sid = client.execute_statement(**args)['Id']
        for _ in range(30):
            state = client.describe_statement(Id=sid)
            if state['Status'] in ('FINISHED','FAILED','ABORTED'):
                break
            time.sleep(1)
        if state['Status'] != 'FINISHED':
            raise RuntimeError(state.get('Error', state['Status']))
        result = client.get_statement_result(Id=sid)
        records = result['Records']
        while result.get('NextToken'):
            result = client.get_statement_result(Id=sid, NextToken=result['NextToken'])
            records.extend(result['Records'])
        values = [[next(iter(cell.values()), None) for cell in row] for row in records]
        history = pd.DataFrame(values, columns=['hour_utc','observations','stations'])
        if history.empty:
            st.info('No observations in the last two days.')
        else:
            history['hour_utc'] = pd.to_datetime(history.hour_utc)
            history['observations'] = pd.to_numeric(history.observations)
            history['stations'] = pd.to_numeric(history.stations)
            st.line_chart(history.sort_values('hour_utc').set_index('hour_utc')[['observations','stations']])
    except Exception as exc:
        st.error(f'Redshift query unavailable: {exc}')
