"""
court_details.py — Single-court drill-down.
Uses st.container(key="card_cd_N") for card sections.
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS, COURT_COLORS  # noqa: E402
from utils.data_loader import load_master_data, apply_filters, COURTS_ORDER  # noqa: E402
from components.filters import render_filter_bar  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header, insight_pill, simple_kpi_card  # noqa: E402
from components.charts.bar_chart import gradient_bar  # noqa: E402
from components.charts.donut_chart import futuristic_radial, radial_legend_html  # noqa: E402
from components.charts.trend_line import glow_trend  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402
from utils.formatting import clean_judge_label  # noqa: E402


def render():
    render_top_bar(subtitle="Single-court deep dive & localized statistics")

    df_all  = load_master_data()
    filters = render_filter_bar(df_all, key_prefix="cd", show_court=True)

    sel_court = filters["court"]  # "All Courts" now shows combined data instead of defaulting to Lahore

    df = apply_filters(df_all, **filters)

    st.write("")

    total_cases  = len(df)
    total_judges = df["Judge"].nunique()          if total_cases else 0
    total_benches = df["Bench_Location"].nunique() if total_cases else 0
    total_cats    = df["Case_Category"].nunique()  if total_cases else 0
    pct_of_all    = (total_cases / len(df_all) * 100) if len(df_all) else 0
    court_color   = COURT_COLORS.get(sel_court, COLORS["accent_primary"])
    selected_sub  = "All 5 courts combined" if sel_court == "All Courts" else f"{pct_of_all:.1f}% of nationwide"

    render_kpi_row([
        {"icon": icon("landmark",  size=20, color=court_color),             "label": "Selected Court",  "value": sel_court,            "sub": selected_sub},
        {"icon": icon("folder",    size=20, color=COLORS["accent_primary"]), "label": "Cases Listed",    "value": f"{total_cases:,}",   "sub": "Total records"},
        {"icon": icon("gavel",     size=20, color=COLORS["accent_secondary"]),"label": "Judges",         "value": f"{total_judges:,}",  "sub": "Active on record"},
        {"icon": icon("map-pin",   size=20, color=COLORS["accent_tertiary"]),"label": "Bench Locations", "value": f"{total_benches:,}", "sub": "Seats / divisions"},
        {"icon": icon("tags",      size=20, color=COLORS["warning"]),        "label": "Categories",      "value": f"{total_cats:,}",    "sub": "Case categories"},
    ])

    st.write("")

    c1, c2 = st.columns(2)

    with c1:
        with st.container(key="card_cd_2"):
            section_header(f"Bench Locations — {sel_court}")
            if total_cases:
                b_counts = df["Bench_Location"].value_counts().head(8)
                fig = gradient_bar(b_counts.index.tolist(), b_counts.values.tolist(), color=court_color, orientation="h")
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    with c2:
        with st.container(key="card_cd_3"):
            section_header("Top Case Categories")
            if total_cases:
                top_cats  = df["Case_Category"].value_counts().head(5)
                other_cnt = df["Case_Category"].value_counts().iloc[5:].sum()
                labels    = top_cats.index.tolist() + (["Others"] if other_cnt > 0 else [])
                vals      = top_cats.values.tolist() + ([other_cnt] if other_cnt > 0 else [])
                rc1, rc2  = st.columns([1.1, 1])
                with rc1:
                    fig = futuristic_radial(labels, vals, center_label="Court Total", center_value=f"{total_cases:,}", height=240)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                with rc2:
                    st.markdown(radial_legend_html(labels, vals), unsafe_allow_html=True)
            else:
                st.info("No data for current filters.")

    st.write("")

    with st.container(key="card_cd_4"):
        section_header(f"Top 10 Most Active Judges — {sel_court}")
        if total_cases:
            top_j = df["Judge"].value_counts().dropna().head(10)
            judge_labels = [clean_judge_label(j) for j in top_j.index.tolist()]
            fig   = gradient_bar(judge_labels, top_j.values.tolist(), color=COLORS["accent_secondary"], orientation="h", height=420)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    with st.container(key="card_cd_5"):
        section_header("Bench Type Mix")
        if total_cases:
            bt = df["Bench_Type_Group"].value_counts().head(5)
            rc1, rc2 = st.columns([1.1, 1])
            with rc1:
                fig = futuristic_radial(bt.index.tolist(), bt.values.tolist(), center_label="Formations", center_value=f"{bt.sum():,}", height=240)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with rc2:
                st.markdown(radial_legend_html(bt.index.tolist(), bt.values.tolist()), unsafe_allow_html=True)
        else:
            st.info("No data for current filters.")

    st.write("")

    with st.container(key="card_cd_7"):
        section_header(f"Monthly Cause-List Trend — {sel_court}")
        if total_cases:
            monthly = (df.dropna(subset=["Year_Month"]).groupby("Year_Month").size()
                       .reset_index(name="Listings").sort_values("Year_Month"))
            fig = glow_trend(monthly["Year_Month"].tolist(),
                             {sel_court: monthly["Listings"].tolist()},
                             colors={sel_court: court_color}, height=320)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    with st.container(key="card_cd_8"):
        section_header(f"Insights — {sel_court} High Court")
        if total_cases:
            top_b  = df["Bench_Location"].value_counts().idxmax()
            top_b_cnt = df["Bench_Location"].value_counts().max()
            insight_pill(icon("map-pin", size=16, color=COLORS["accent_primary"]),
                         f"Principal seat: <b>{top_b}</b> with {top_b_cnt:,} listed cases.")
            top_c  = df["Case_Category"].value_counts().idxmax()
            insight_pill(icon("tags", size=16, color=COLORS["warning"]),
                         f"Dominant category: <b>{top_c}</b> ({df['Case_Category'].value_counts().max():,} listings).")
            top_j  = df["Judge"].value_counts().dropna().idxmax()
            insight_pill(icon("gavel", size=16, color=COLORS["accent_secondary"]),
                         f"Most-listed judge: <b>{clean_judge_label(top_j)}</b> ({df['Judge'].value_counts().dropna().max():,} listings).")
        else:
            st.info("No data for current filters.")