"""
about.py

About view:
Static information page detailing project scope, objectives, technical architecture,
explicit data limitations (cause-list only notice), and platform versioning.
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS, COURT_COLORS  # noqa: E402
from utils.data_loader import load_master_data, COURTS_ORDER  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header, insight_pill  # noqa: E402
from components.charts.donut_chart import futuristic_radial, radial_legend_html  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def render():
    render_top_bar(subtitle="Platform objective, data scope, architecture & institutional disclaimers")

    st.write("")

    # ---------------------------------------------------------------------
    # 1. ABOUT HIGHLIGHT METRICS
    # ---------------------------------------------------------------------
    render_kpi_row([
        {"icon": icon("landmark", size=20, color=COLORS["accent_primary"]), "label": "Jurisdictions", "value": "5 High Courts", "sub": "Sindh, LHC, IHC, PHC, BHC"},
        {"icon": icon("folder", size=20, color=COLORS["accent_secondary"]), "label": "Records Ingested", "value": "339,307", "sub": "Standardized cause-list rows"},
        {"icon": icon("gavel", size=20, color=COLORS["accent_tertiary"]), "label": "Tech Stack", "value": "Streamlit + Plotly", "sub": "Modular architecture"},
        {"icon": icon("info", size=20, color=COLORS["warning"]), "label": "Data Constraint", "value": "Cause-List Only", "sub": "No disposal/status field"},
        {"icon": icon("calendar", size=20, color=COLORS["success"]), "label": "Pipeline Mode", "value": "Full Rebuild", "sub": "Deterministic parquet ETL"},
    ])

    st.write("")

    # ---------------------------------------------------------------------
    # 2. PROJECT MISSION & OVERVIEW
    # ---------------------------------------------------------------------
    with st.container(key="card_ab_1"):
        section_header("Project Mission & System Architecture")

        st.markdown(
            """
            <div style="color:#A9BBDD;font-size:0.92rem;line-height:1.7;">
            The <b>Pakistan High Courts Comparative Analytics Dashboard</b> provides a unified, data-driven analytical portal
            benchmarking daily cause-list listings across 5 Pakistani High Courts:
            <br><br>
            <ol style="margin-left:20px;color:#F3F6FD;">
                <li><b>Lahore High Court (LHC)</b> ~ 266K listings</li>
                <li><b>Peshawar High Court (PHC)</b> ~ 32K listings (excluding Bannu District/Sessions court data)</li>
                <li><b>Sindh High Court (SHC)</b> ~ 22K listings</li>
                <li><b>Islamabad High Court (IHC)</b> ~ 16.7K listings</li>
                <li><b>Balochistan High Court (BHC)</b> ~ 2.1K listings</li>
            </ol>
            <br>
            Due to severe court volume imbalance, the platform offers normalized (percentage) visual comparisons alongside absolute counts
            so smaller jurisdictions remain clearly visible.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")

    # ---------------------------------------------------------------------
    # 2b. LIVE COURT VOLUME BREAKDOWN (real data, visual companion to list above)
    # ---------------------------------------------------------------------
    with st.container(key="card_ab_4"):
        section_header("Current Ingested Volume by Court")

        df = load_master_data()
        vol = df["Court"].value_counts().reindex(COURTS_ORDER).dropna()
        rc1, rc2 = st.columns([1.1, 1])
        with rc1:
            fig = futuristic_radial(vol.index.tolist(), vol.values.tolist(), center_label="Total Listings", center_value=f"{vol.sum():,}", height=260)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        with rc2:
            st.markdown(radial_legend_html(vol.index.tolist(), vol.values.tolist()), unsafe_allow_html=True)

    st.write("")

    # ---------------------------------------------------------------------
    # 3. CRITICAL DATA DISCLAIMER (CAUSE LIST LIMITATION)
    # ---------------------------------------------------------------------
    # NOTE: card_ab_2 gets its amber left-accent border from a dedicated
    # rule in styles/dashboard.css (div[class*="st-key-card_ab_2"]) since
    # st.container(key=...) doesn't accept an inline style attribute the
    # way the old glass-card div did.
    with st.container(key="card_ab_2"):
        section_header("Important Data Limitation & Analytical Disclaimer")

        insight_pill(
            icon("info", size=18, color=COLORS["warning"]),
            "<b>Cause-List Data Only:</b> The underlying dataset represents cause-list scheduled hearings. It does not contain case disposal dates, final outcomes, or current case status (pending vs disposed)."
        )

        st.markdown(
            """
            <div style="color:#A9BBDD;font-size:0.88rem;line-height:1.6;margin-top:10px;">
            To ensure analytical integrity:
            <ul>
                <li>Metrics such as <i>"Pending Cases"</i>, <i>"Disposed Cases"</i>, or <i>"Disposal Rate"</i> are strictly excluded.</li>
                <li>Where delay or workload density proxies are required, <b>Listing Frequency</b> (appearances of a Case_No across hearing dates) is utilized as the sole empirical proxy.</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")

    # ---------------------------------------------------------------------
    # 4. SYSTEM INFORMATION & CREDITS
    # ---------------------------------------------------------------------
    with st.container(key="card_ab_3"):
        section_header("System Metadata & Versioning")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                """
                <div style="color:#A9BBDD;font-size:0.85rem;line-height:1.6;">
                <b>Dashboard Version:</b> 2.0.0 (Modular Architecture)<br>
                <b>Core Framework:</b> Streamlit + Plotly Graph Objects<br>
                <b>Data Engine:</b> PyArrow + Pandas Parquet<br>
                <b>UI Design System:</b> Blue/Navy Glassmorphism Theme
                </div>
                """,
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                """
                <div style="color:#A9BBDD;font-size:0.85rem;line-height:1.6;">
                <b>Unified Schema:</b> 16 Standardized Columns<br>
                <b>Iconography:</b> Custom SVG / Google Material Icons<br>
                <b>Navigation:</b> Custom Button Reroute Router<br>
                <b>Status:</b> Fully Built & Operational
                </div>
                """,
                unsafe_allow_html=True
            )
