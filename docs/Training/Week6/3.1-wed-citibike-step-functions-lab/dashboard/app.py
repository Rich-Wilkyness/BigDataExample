"""Follow-along dashboard: demo first; query Richard's accepted Gold view on demand."""
import importlib.util
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("redshift_reader", ROOT / "redshift-reader.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

st.set_page_config(page_title="Citi Bike station availability", layout="wide")
st.title("Citi Bike station availability")
st.caption("Reporting reads accepted snapshots. Refreshing this page does not run the ETL pipeline.")
source = st.sidebar.radio("Data source", ["Sample data", "Richard Redshift"])
if source == "Sample data":
    st.info("Synthetic sample data for learning the dashboard; these are not AWS results.")
    frame = pd.read_csv(ROOT / "sample-summary.csv")
else:
    workgroup = st.sidebar.text_input("Redshift workgroup", "richard-citibike-wg")
    st.sidebar.caption("Database dev; Region us-east-2; requires SELECT grants and local AWS credentials.")
    if st.sidebar.button("Load accepted snapshots"):
        try:
            with st.spinner("Reading the accepted summary view"):
                rows, statement_id = reader.read_summary("us-east-2", workgroup, "dev")
            st.session_state["summary"] = rows
            st.session_state["statement_id"] = statement_id
            st.session_state["workgroup"] = workgroup
        except Exception as error:
            # UI boundary: surface the actual query/authentication error to the learner.
            st.error(str(error))
    if st.session_state.get("workgroup") != workgroup:
        st.info("Load snapshots for the selected workgroup.")
        st.stop()
    frame = pd.DataFrame(st.session_state.get("summary", []))
    st.caption(f"Statement ID: {st.session_state.get('statement_id', '')}")

if frame.empty:
    st.info("No accepted operational-station summaries to display.")
    st.stop()
frame["snapshot_timestamp"] = pd.to_datetime(frame["snapshot_timestamp"], utc=True)
frame = frame.sort_values("snapshot_timestamp")
latest = frame.iloc[-1]
st.caption(f"Latest capture: {latest['snapshot_timestamp']} | Showing at most 1,000 snapshots")
columns = st.columns(3)
columns[0].metric("Operational stations", int(latest["operational_stations"]))
columns[1].metric("Available bikes", int(latest["bikes_available"]))
columns[2].metric("Available docks", int(latest["docks_available"]))
st.line_chart(frame.set_index("snapshot_timestamp")[["bikes_available", "docks_available"]])
st.dataframe(frame, hide_index=True)
