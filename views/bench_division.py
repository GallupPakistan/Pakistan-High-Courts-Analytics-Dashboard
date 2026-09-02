"""
bench_division.py

Bench / Division view:
1. Bench summary KPI row
2. Leaderboard: Benches by total case volume
3. Bench Type Breakdown across Benches (Single, Division, Full, etc.)
4. Court Rooms activity / listings distribution
5. Active Judges per Bench Location
6. Bench Insights
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS, COURT_COLORS, CHART_COLORWAY  # noqa: E402
from utils.data_loader import load_master_data, apply_filters, COURTS_ORDER  # noqa: E402
from components.filters import render_filter_bar  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header, insight_pill, simple_kpi_card  # noqa: E402
from components.charts.bar_chart import gradient_bar, grouped_bar  # noqa: E402
from components.charts.donut_chart import futuristic_radial, radial_legend_html  # noqa: E402
from components.charts.trend_line import glow_trend  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def render():
    render_top_bar(subtitle="Bench location & division level comparative analytics")

    df_all = load_master_data()
    filters = render_filter_bar(df_all, key_prefix="bd")
    df = apply_filters(df_all, **filters)

    st.write("")

    # ---------------------------------------------------------------------
    # 1. KPI ROW
    # ---------------------------------------------------------------------
    total_cases = len(df)
    total_benches = df["Bench_Location"].nunique() if total_cases else 0
    total_rooms = df["Court_Room"].nunique() if total_cases else 0
    total_bench_types = df["Bench_Type_Group"].nunique() if total_cases else 0
    busiest_bench = df["Bench_Location"].value_counts().idxmax() if total_benches else "N/A"
    busiest_bench_vol = df["Bench_Location"].value_counts().max() if total_benches else 0

    render_kpi_row([
        {"icon": icon("map-pin", size=20, color=COLORS["accent_primary"]), "label": "Bench Locations", "value": f"{total_benches:,}", "sub": "Distinct seats"},
        {"icon": icon("landmark", size=20, color=COLORS["accent_secondary"]), "label": "Busiest Bench", "value": f"{busiest_bench}", "sub": f"{busiest_bench_vol:,} listings"},
        {"icon": icon("landmark", size=20, color=COLORS["accent_tertiary"]), "label": "Court Rooms", "value": f"{total_rooms:,}", "sub": "Distinct courtrooms"},
        {"icon": icon("gavel", size=20, color=COLORS["warning"]), "label": "Bench Formations", "value": f"{total_bench_types:,}", "sub": "Bench types"},
        {"icon": icon("folder", size=20, color=COLORS["success"]), "label": "Total Volume", "value": f"{total_cases:,}", "sub": "Listings in view"},
    ])

    st.write("")

    # ---------------------------------------------------------------------
    # 2. TOP BENCHES LEADERBOARD & BENCH TYPES
    # ---------------------------------------------------------------------
    c1, c2 = st.columns([1.3, 1])

    with c1:
        with st.container(key="card_bd_1"):
            section_header("Bench Locations by Case Volume")
            if total_cases:
                b_counts = df["Bench_Location"].value_counts().head(10)
                fig = gradient_bar(b_counts.index.tolist(), b_counts.values.tolist(), color=COLORS["accent_primary"], orientation="h")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    with c2:
        with st.container(key="card_bd_2"):
            section_header("Bench Type Formations")
            if total_cases:
                bt = df["Bench_Type_Group"].value_counts().head(5)
                rc1, rc2 = st.columns([1.1, 1])
                with rc1:
                    fig = futuristic_radial(bt.index.tolist(), bt.values.tolist(), center_label="Formations", center_value=f"{bt.sum():,}", height=240)
                    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                with rc2:
                    st.markdown(radial_legend_html(bt.index.tolist(), bt.values.tolist()), unsafe_allow_html=True)
            else:
                st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 3. BENCH TYPE MIX PER COURT
    # ---------------------------------------------------------------------
    with st.container(key="card_bd_3"):
        section_header("Bench Type Distribution Across Courts")

        if total_cases:
            top_bt = df["Bench_Type_Group"].value_counts().head(5).index.tolist()
            bt_pivot = df[df["Bench_Type_Group"].isin(top_bt)].groupby(["Bench_Type_Group", "Court"]).size().unstack(fill_value=0)
            series = {c: bt_pivot[c].tolist() for c in COURTS_ORDER if c in bt_pivot.columns}
            fig = grouped_bar(top_bt, series, colors=COURT_COLORS, height=360)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 4 & 5. COURT ROOMS & BENCH DETAIL TABLE
    # ---------------------------------------------------------------------
    c3, c4 = st.columns([1, 1.2])

    with c3:
        with st.container(key="card_bd_4"):
            section_header("Top Active Court Rooms")
            if total_cases:
                rooms = df["Court_Room"].value_counts().dropna().head(8)
                fig = gradient_bar(rooms.index.tolist(), rooms.values.tolist(), color=COLORS["accent_secondary"])
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    with c4:
        with st.container(key="card_bd_5"):
            section_header("Bench Location Summary Table")
            if total_cases:
                bench_summary = (
                    df.groupby(["Bench_Location", "Court"])
                    .agg(
                        Total_Listings=("Case_No", "count"),
                        Judges=("Judge", "nunique"),
                        Court_Rooms=("Court_Room", "nunique"),
                        Top_Category=("Case_Category", lambda x: x.mode().iloc[0] if not x.empty else "N/A")
                    )
                    .reset_index()
                    .sort_values("Total_Listings", ascending=False)
                    .head(10)
                )
                st.dataframe(bench_summary, width='stretch', hide_index=True)
            else:
                st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 5b. ACTIVE JUDGES PER BENCH LOCATION & TOP BENCH TRENDS
    # ---------------------------------------------------------------------
    c5, c6 = st.columns([1, 1.2])

    with c5:
        with st.container(key="card_bd_7"):
            section_header("Active Judges per Bench Location")
            if total_cases:
                judges_per_bench = df.groupby("Bench_Location")["Judge"].nunique().sort_values(ascending=False).head(10)
                fig = gradient_bar(judges_per_bench.index.tolist(), judges_per_bench.values.tolist(), color=COLORS["accent_tertiary"], orientation="h")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    with c6:
        with st.container(key="card_bd_8"):
            section_header("Top 5 Benches — Listing Trend Over Time")
            if total_cases:
                top_5_benches = df["Bench_Location"].value_counts().head(5).index.tolist()
                bench_trend = (
                    df[df["Bench_Location"].isin(top_5_benches)]
                    .dropna(subset=["Year_Month"])
                    .groupby(["Year_Month", "Bench_Location"]).size().reset_index(name="Listings")
                )
                pivot_bt = bench_trend.pivot(index="Year_Month", columns="Bench_Location", values="Listings").fillna(0).sort_index()
                series = {c: pivot_bt[c].tolist() for c in top_5_benches if c in pivot_bt.columns}
                bench_colors = {c: CHART_COLORWAY[i % len(CHART_COLORWAY)] for i, c in enumerate(series.keys())}
                fig = glow_trend(pivot_bt.index.tolist(), series, colors=bench_colors, height=340)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 6. BENCH INSIGHTS
    # ---------------------------------------------------------------------
    with st.container(key="card_bd_6"):
        section_header("Bench & Division Insights")

        if total_cases:
            top_loc = df["Bench_Location"].value_counts().idxmax()
            top_loc_pct = (df["Bench_Location"].value_counts().max() / total_cases) * 100
            insight_pill(icon("map-pin", size=16, color=COLORS["accent_primary"]), f"The single largest bench location is <b>{top_loc}</b>, accounting for {top_loc_pct:.1f}% of all selected listings.")

            sb_cnt = df[df["Bench_Type_Group"] == "Single Bench"].shape[0]
            sb_pct = (sb_cnt / total_cases) * 100
            insight_pill(icon("gavel", size=16, color=COLORS["accent_secondary"]), f"<b>Single Benches</b> represent {sb_pct:.1f}% of total listings across courts.")
        else:
            st.info("No data for current filters.")
