"""
trends_over_time.py

Trends Over Time view:
1. Time-series summary KPI row (Span, peak month, monthly avg, YoY growth proxy)
2. Main Multi-Line Glowing Trend Chart (Monthly volume by court)
3. Year-over-Year / Yearly Summary Table
4. Month-over-Month Growth Rate %
5. Per-court Small Multiples / Individual Court Trends
6. Temporal Insights
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS, COURT_COLORS  # noqa: E402
from utils.data_loader import load_master_data, apply_filters, COURTS_ORDER  # noqa: E402
from components.filters import render_filter_bar  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header, insight_pill, simple_kpi_card  # noqa: E402
from components.charts.bar_chart import gradient_bar, grouped_bar  # noqa: E402
from components.charts.trend_line import glow_trend  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def render():
    render_top_bar(subtitle="Detailed temporal analysis, monthly growth & multi-year listing patterns")

    df_all = load_master_data()
    filters = render_filter_bar(df_all, key_prefix="tot")
    df = apply_filters(df_all, **filters)

    st.write("")

    # ---------------------------------------------------------------------
    # 1. TEMPORAL KPI ROW
    # ---------------------------------------------------------------------
    total_cases = len(df)
    monthly_counts = df.dropna(subset=["Year_Month"]).groupby("Year_Month").size()
    total_months = len(monthly_counts)
    avg_monthly = monthly_counts.mean() if total_months else 0
    peak_month = monthly_counts.idxmax() if total_months else "N/A"
    peak_vol = monthly_counts.max() if total_months else 0

    render_kpi_row([
        {"icon": icon("calendar", size=20, color=COLORS["accent_primary"]), "label": "Time Horizon", "value": f"{total_months} Mos.", "sub": "Monthly periods"},
        {"icon": icon("trending-up", size=20, color=COLORS["accent_secondary"]), "label": "Peak Month", "value": f"{peak_month}", "sub": f"{peak_vol:,} listings"},
        {"icon": icon("folder", size=20, color=COLORS["accent_tertiary"]), "label": "Avg Monthly Volume", "value": f"{avg_monthly:,.0f}", "sub": "Listings / month"},
        {"icon": icon("landmark", size=20, color=COLORS["warning"]), "label": "Courts Tracked", "value": f"{df['Court'].nunique()}", "sub": "Active in date range"},
        {"icon": icon("tags", size=20, color=COLORS["success"]), "label": "Total Listings", "value": f"{total_cases:,}", "sub": "Selected period"},
    ])

    st.write("")

    # ---------------------------------------------------------------------
    # 2. MAIN GLOWING MULTI-LINE TREND CHART
    # ---------------------------------------------------------------------
    with st.container(key="card_tot_1"):
        section_header("Monthly Cause-List Volume Trend by Court")

        if total_cases:
            trend_df = df.dropna(subset=["Year_Month"]).groupby(["Year_Month", "Court"]).size().reset_index(name="Cases")
            pivot = trend_df.pivot(index="Year_Month", columns="Court", values="Cases").fillna(0).sort_index()
            series = {c: pivot[c].tolist() for c in COURTS_ORDER if c in pivot.columns}
            fig = glow_trend(pivot.index.tolist(), series, colors=COURT_COLORS, height=380)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 2b. CUMULATIVE LISTING VOLUME (running total)
    # ---------------------------------------------------------------------
    with st.container(key="card_tot_6"):
        section_header("Cumulative Listing Volume Over Time")

        if total_cases:
            cum = monthly_counts.sort_index().cumsum()
            fig = glow_trend(cum.index.tolist(), {"Cumulative Listings": cum.values.tolist()}, colors={"Cumulative Listings": COLORS["accent_tertiary"]}, height=300)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 3 & 4. YEARLY SUMMARY TABLE & MONTH-OVER-MONTH GROWTH
    # ---------------------------------------------------------------------
    c1, c2 = st.columns([1, 1.2])

    with c1:
        with st.container(key="card_tot_2"):
            section_header("Yearly Volume Breakdown")
            if total_cases:
                yearly = df.dropna(subset=["Year"]).groupby(["Year", "Court"]).size().unstack(fill_value=0)
                yearly["Total"] = yearly.sum(axis=1)
                yearly.index = yearly.index.astype(int).astype(str)
                st.dataframe(yearly.reset_index(), width='stretch', hide_index=True)
            else:
                st.info("No data for current filters.")

    with c2:
        with st.container(key="card_tot_3"):
            section_header("Month-over-Month Volume Growth (%)")
            if total_months > 1:
                mom_df = pd.DataFrame({"Year_Month": monthly_counts.index, "Listings": monthly_counts.values})
                mom_df["Growth_%"] = mom_df["Listings"].pct_change() * 100
                mom_df["Growth_%"] = mom_df["Growth_%"].fillna(0)
                fig = gradient_bar(mom_df["Year_Month"].tolist(), mom_df["Growth_%"].tolist(), color=COLORS["accent_secondary"], value_suffix="%")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("Insufficient monthly periods to calculate MoM growth.")

    st.write("")

    # ---------------------------------------------------------------------
    # 4b. YEAR-OVER-YEAR VOLUME — VISUAL (grouped bar by court)
    # ---------------------------------------------------------------------
    with st.container(key="card_tot_7"):
        section_header("Year-over-Year Volume by Court")

        yearly_raw = df.dropna(subset=["Year"]).groupby(["Year", "Court"]).size().unstack(fill_value=0)
        if len(yearly_raw):
            years = yearly_raw.index.astype(int).astype(str).tolist()
            series = {c: yearly_raw[c].tolist() for c in COURTS_ORDER if c in yearly_raw.columns}
            fig = grouped_bar(years, series, colors=COURT_COLORS, height=340)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 5. PER-COURT INDIVIDUAL TRENDS (SMALL MULTIPLES)
    # ---------------------------------------------------------------------
    with st.container(key="card_tot_4"):
        section_header("Court-by-Court Individual Listing Trajectories")

        if total_cases:
            court_cols = st.columns(min(len(COURTS_ORDER), 5))
            for idx, court_name in enumerate(COURTS_ORDER):
                with court_cols[idx % len(court_cols)]:
                    cdf = df[df["Court"] == court_name]
                    st.markdown(f"<div style='font-size:0.85rem;font-weight:600;color:#F3F6FD;margin-bottom:4px;'>{court_name}</div>", unsafe_allow_html=True)
                    if len(cdf):
                        c_monthly = cdf.dropna(subset=["Year_Month"]).groupby("Year_Month").size().reset_index(name="Cases").sort_values("Year_Month")
                        fig = glow_trend(c_monthly["Year_Month"].tolist(), {court_name: c_monthly["Cases"].tolist()}, colors={court_name: COURT_COLORS[court_name]}, height=180)
                        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                    else:
                        st.caption("No data")
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 6. DAY-OF-WEEK LISTING DISTRIBUTION
    # ---------------------------------------------------------------------
    with st.container(key="card_tot_8"):
        section_header("Listing Activity by Day of Week")

        if total_cases:
            dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dow_counts = df["Hearing_Date"].dt.day_name().value_counts().reindex(dow_order).dropna()
            fig = gradient_bar(dow_counts.index.tolist(), dow_counts.values.tolist(), multicolor=True)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 7. TEMPORAL INSIGHTS
    # ---------------------------------------------------------------------
    with st.container(key="card_tot_5"):
        section_header("Temporal Insights")

        if total_months:
            insight_pill(icon("calendar", size=16, color=COLORS["accent_primary"]), f"Highest single-month listing activity recorded in <b>{peak_month}</b> with {peak_vol:,} cases.")
            insight_pill(icon("trending-up", size=16, color=COLORS["accent_secondary"]), f"Average monthly throughput across selected courts is <b>{avg_monthly:,.0f} listings</b> per month.")
        else:
            st.info("No data for current filters.")
