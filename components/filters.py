"""
filters.py

Renders the shared top filter bar (Court, Bench/Division, Case Category,
Date Range) used identically across pages.
"""

import streamlit as st
import pandas as pd


def render_filter_bar(df: pd.DataFrame, key_prefix: str, show_court=True):
    cols = st.columns([1.2, 1.2, 1.4, 1.6, 0.6] if show_court else [1.2, 1.4, 1.6, 0.6])
    idx = 0

    court = "All Courts"
    if show_court:
        with cols[idx]:
            court = st.selectbox(
                "Court", ["All Courts"] + sorted(df["Court"].dropna().unique().tolist()),
                key=f"{key_prefix}_court"
            )
        idx += 1

    bench_pool = df if court == "All Courts" else df[df["Court"] == court]
    with cols[idx]:
        bench_location = st.selectbox(
            "Bench / Division", ["All"] + sorted(bench_pool["Bench_Location"].dropna().unique().tolist()),
            key=f"{key_prefix}_bench"
        )
    idx += 1

    with cols[idx]:
        case_category = st.selectbox(
            "Case Category", ["All"] + sorted(df["Case_Category"].dropna().unique().tolist()),
            key=f"{key_prefix}_category"
        )
    idx += 1

    min_date = df["Hearing_Date"].min()
    max_date = df["Hearing_Date"].max()
    with cols[idx]:
        date_range = st.date_input(
            "Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date,
            key=f"{key_prefix}_dates"
        )
    idx += 1

    with cols[idx]:
        st.write("")
        clear = st.button("Clear", key=f"{key_prefix}_clear", width='stretch')

    if clear:
        # _map_select isn't created by this function (a page's map, if it
        # has one, owns that key) — included here so "Clear" also forgets
        # a map-marker click; harmless no-op on pages without a map.
        for k in [f"{key_prefix}_court", f"{key_prefix}_bench", f"{key_prefix}_category",
                  f"{key_prefix}_dates", f"{key_prefix}_map_select", f"{key_prefix}_map_applied"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    return {
        "court": court,
        "bench_location": bench_location,
        "case_category": case_category,
        "date_range": date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_date, max_date),
    }
