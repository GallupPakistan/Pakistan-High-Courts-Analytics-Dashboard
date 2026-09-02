import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from components.charts.map_chart import build_bench_location_map

st.set_page_config(layout="wide")
df = pd.DataFrame({
    "Bench_Location": ["Lahore", "Karachi", "Multan"],
    "Court": ["Lahore", "Sindh", "Lahore"],
})
fig = build_bench_location_map(df)
st.write("Testing map render...")
st.plotly_chart(
    fig, width="stretch", config={"displayModeBar": False},
    on_select="rerun", selection_mode=["points"], key="test_map_select",
)
st.write("Done")
