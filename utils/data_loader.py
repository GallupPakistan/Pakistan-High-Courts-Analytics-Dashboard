"""
data_loader.py

Loads the combined dashboard master file (parquet) once and caches it via
Streamlit's cache so every page shares the same in-memory dataframe without
re-reading from disk.
"""

import streamlit as st
import pandas as pd
import os

from utils.category_normalizer import add_normalized_category
from utils.bench_type_normalizer import add_normalized_bench_type

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "combined_dashboard_master.parquet")

COURTS_ORDER = ["Sindh", "Lahore", "Islamabad", "Peshawar", "Balochistan"]


@st.cache_data(show_spinner="Loading court data...")
def load_master_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df["Hearing_Date"] = pd.to_datetime(df["Hearing_Date"], errors="coerce")
    df["Year_Month"] = df["Hearing_Date"].dt.to_period("M").astype(str)
    df["Year"] = df["Hearing_Date"].dt.year

    # Restrict the dashboard to 2026 data only (2025 and any other years excluded).
    df = df[df["Year"] == 2026].reset_index(drop=True)

    # Each court records Case_Category in its own free-text format, so the
    # same subject matter (e.g. banking litigation) can appear as dozens of
    # different raw strings across courts ("BANKING", "Civil - COS(B) -
    # Banking", "Writ - Banking & Finance - Miscellaneous", ...). Add a
    # normalized Category_Group column so cross-court category comparisons
    # aggregate correctly. See utils/category_normalizer.py for the mapping
    # rules and utils/audit_category_mapping.py to review coverage.
    df = add_normalized_category(df, source_col="Case_Category", target_col="Category_Group")

    # Each court also records Bench_Type in its own free-text format, so the
    # same real bench configuration (e.g. a Single Bench) can appear as
    # several different raw strings ("SB", "Single Bench", "Single_Bench_S_B_",
    # ...). Add a normalized Bench_Type_Group column so "Top Bench Types"
    # charts and KPIs aggregate correctly instead of splitting one bench
    # type's volume across look-alike labels. See
    # utils/bench_type_normalizer.py for the mapping rules.
    df = add_normalized_bench_type(df, source_col="Bench_Type", target_col="Bench_Type_Group")

    return df


def apply_filters(df: pd.DataFrame, court=None, bench_location=None, case_category=None, date_range=None) -> pd.DataFrame:
    out = df
    if court and court != "All Courts":
        out = out[out["Court"] == court]
    if bench_location and bench_location != "All":
        out = out[out["Bench_Location"] == bench_location]
    if case_category and case_category != "All":
        out = out[out["Case_Category"] == case_category]
    if date_range:
        start, end = date_range
        out = out[(out["Hearing_Date"] >= pd.Timestamp(start)) & (out["Hearing_Date"] <= pd.Timestamp(end))]
    return out
