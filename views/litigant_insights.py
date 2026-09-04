"""
litigant_insights.py

Litigant & Case Insights view:
1. Government / Public Sector vs Private / Individual respondent breakdown
2. Top Government Agencies Sued
3. Case Age Distribution (registration year vs hearing year — a pendency
   proxy, since cause-list data doesn't include disposal status)

The Government/Private split is a keyword-based heuristic (see
utils/litigant_classifier.py) — Pakistani legal documents use very varied
abbreviations for government offices, so treat this as an approximate
picture, not an exact count.
"""

import streamlit as st
import pandas as pd
import re
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS  # noqa: E402
from utils.data_loader import load_master_data, apply_filters  # noqa: E402
from utils.litigant_classifier import add_litigant_type  # noqa: E402
from components.filters import render_filter_bar  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header, insight_pill  # noqa: E402
from components.charts.bar_chart import gradient_bar  # noqa: E402
from components.charts.donut_chart import futuristic_radial, radial_legend_html  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def _extract_case_year(case_no):
    if pd.isna(case_no):
        return None
    m = re.search(r"/(\d{4})\b", str(case_no))
    if m:
        y = int(m.group(1))
        if 1990 <= y <= 2026:
            return y
    return None


def render():
    render_top_bar(subtitle="Government vs private litigants, top agencies sued, and case-age proxy analysis")

    df_all = load_master_data()
    filters = render_filter_bar(df_all, key_prefix="lit")
    df = apply_filters(df_all, **filters)

    st.write("")

    total_cases = len(df)
    df = add_litigant_type(df, source_col="Respondent", target_col="Respondent_Type")

    govt_count = (df["Respondent_Type"] == "Government / Public Sector").sum()
    private_count = (df["Respondent_Type"] == "Private / Individual").sum()
    unknown_count = (df["Respondent_Type"] == "Unknown").sum()
    govt_pct = (govt_count / total_cases * 100) if total_cases else 0

    render_kpi_row([
        {"icon": icon("landmark", size=20, color=COLORS["accent_primary"]), "label": "Govt / Public Sector", "value": f"{govt_pct:.1f}%", "sub": f"{govt_count:,} listings"},
        {"icon": icon("users", size=20, color=COLORS["accent_secondary"]), "label": "Private / Individual", "value": f"{(private_count/total_cases*100) if total_cases else 0:.1f}%", "sub": f"{private_count:,} listings"},
        {"icon": icon("folder", size=20, color=COLORS["warning"]), "label": "Unclassified", "value": f"{(unknown_count/total_cases*100) if total_cases else 0:.1f}%", "sub": "Blank respondent field"},
        {"icon": icon("gavel", size=20, color=COLORS["success"]), "label": "Total Listings", "value": f"{total_cases:,}", "sub": "In current selection"},
    ])
    st.caption(
        "Classification is a keyword-based heuristic on the Respondent field (e.g. \"The State\", "
        "\"Federation of Pakistan\", \"Province of Punjab\", statutory bodies, judicial/police officer "
        "designations) — not an authoritative legal classification. Treat this as an approximate picture."
    )

    st.write("")

    # ---------------------------------------------------------------------
    # GOVT VS PRIVATE DONUT + TOP GOVERNMENT AGENCIES
    # ---------------------------------------------------------------------
    c1, c2 = st.columns([1, 1.3])

    with c1:
        with st.container(key="card_lit_donut"):
            section_header("Respondent Type Breakdown")
            if total_cases:
                vc = df["Respondent_Type"].value_counts()
                fig = futuristic_radial(vc.index.tolist(), vc.values.tolist(), center_label="Listings", center_value=f"{total_cases:,}", height=260)
                rc1, rc2 = st.columns([1.1, 1])
                with rc1:
                    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                with rc2:
                    st.markdown(radial_legend_html(vc.index.tolist(), vc.values.tolist()), unsafe_allow_html=True)
            else:
                st.info("No data for current filters.")

    with c2:
        with st.container(key="card_lit_top_govt"):
            section_header("Top 10 Government Agencies / Offices Sued")
            if total_cases and govt_count:
                govt_df = df[df["Respondent_Type"] == "Government / Public Sector"]
                top_govt = govt_df["Respondent"].value_counts().head(10)
                fig = gradient_bar(top_govt.index.tolist(), top_govt.values.tolist(), color=COLORS["accent_primary"], orientation="h")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                st.caption("Raw respondent text shown as recorded — the same office may appear under several spelling variants.")
            else:
                st.info("No government-classified respondents in current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # CASE AGE DISTRIBUTION
    # ---------------------------------------------------------------------
    with st.container(key="card_lit_age"):
        section_header("Case Age Distribution (Pendency Proxy)")
        st.caption(
            "How old is a case (by its registration year embedded in the Case No.) at the time it's "
            "heard in 2026 — cause-list data doesn't include disposal status, so this is a proxy for "
            "how much older litigation is still active, not a true pendency/backlog measure."
        )
        if total_cases:
            case_year = df["Case_Year"].copy()
            extracted = df["Case_No"].apply(_extract_case_year)
            case_year = case_year.fillna(pd.Series(extracted, index=df.index))
            hearing_year = df["Hearing_Date"].dt.year
            age = hearing_year - case_year
            age = age[(age >= 0) & (age <= 40)]

            coverage_pct = (len(age) / total_cases * 100) if total_cases else 0
            if len(age):
                buckets = pd.cut(
                    age, bins=[-0.1, 0.5, 1, 2, 5, 100],
                    labels=["Same year", "1 year", "1-2 years", "2-5 years", "5+ years"]
                ).value_counts().sort_index()
                fig = gradient_bar(buckets.index.tolist(), buckets.values.tolist(), color=COLORS["accent_tertiary"])
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                st.caption(f"Based on {len(age):,} listings ({coverage_pct:.1f}% of current selection) with a resolvable case year.")

                old_pct = (age >= 2).mean() * 100
                insight_pill(
                    icon("trending-up", size=16, color=COLORS["warning"]),
                    f"<b>{old_pct:.1f}%</b> of listings with a known case year are for cases registered "
                    "**2 or more years** before the 2026 hearing — still-active older litigation."
                )
            else:
                st.info("No listings with a resolvable case year in the current selection.")
        else:
            st.info("No data for current filters.")
