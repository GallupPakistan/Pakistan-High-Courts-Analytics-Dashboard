"""
reports.py

Reports view:
1. Export KPI summary card & overview
2. Filter bar (dynamically dictates dataset export slice)
3. Filtered Data Preview Table (interactive Dataframe)
4. Export format options (CSV / Excel format download triggers)
5. Dataset Schema & Column Coverage Summary
"""

import streamlit as st
import pandas as pd
import io
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS  # noqa: E402
from utils.data_loader import load_master_data, apply_filters, COURTS_ORDER  # noqa: E402
from utils.data_quality import find_coverage_gaps  # noqa: E402
from components.filters import render_filter_bar  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header, insight_pill  # noqa: E402
from components.charts.bar_chart import gradient_bar  # noqa: E402
from components.charts.trend_line import glow_trend  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def render():
    render_top_bar(subtitle="Custom dataset filtering, tabular preview & report export generator")

    df_all = load_master_data()
    filters = render_filter_bar(df_all, key_prefix="rep")
    df = apply_filters(df_all, **filters)

    # The working dataframe carries several internal/derived columns
    # (Case_UID for de-duplication logic, Judge_List as a Python list
    # object) that aren't meant for an external data export — Judge_List
    # in particular renders as raw Python repr() syntax in CSV
    # ("['Justice X', 'Justice Y']"), which is broken for any real
    # spreadsheet/analysis use. The export/preview/schema-summary below
    # use this curated column set: the 16 original raw fields plus the
    # two normalized enrichment columns (Category_Group, Bench_Type_Group)
    # that are genuinely useful for external analysis.
    _exclude_cols = {"Case_UID", "Judge_List"}
    export_cols = [c for c in df.columns if c not in _exclude_cols]
    df = df[export_cols]

    st.write("")

    # ---------------------------------------------------------------------
    # 1. EXPORT KPI SUMMARY
    # ---------------------------------------------------------------------
    total_cases = len(df)
    total_cols = len(df.columns)
    est_csv_size = (total_cases * 180) / (1024 * 1024) if total_cases else 0

    render_kpi_row([
        {"icon": icon("description", size=20, color=COLORS["accent_primary"]), "label": "Matching Records", "value": f"{total_cases:,}", "sub": f"Out of {len(df_all):,} master rows"},
        {"icon": icon("tags", size=20, color=COLORS["accent_secondary"]), "label": "Columns Included", "value": f"{total_cols}", "sub": "Unified schema fields"},
        {"icon": icon("landmark", size=20, color=COLORS["accent_tertiary"]), "label": "Courts Included", "value": f"{df['Court'].nunique()}", "sub": "Active courts"},
        {"icon": icon("folder", size=20, color=COLORS["warning"]), "label": "Est. Export Size", "value": f"{est_csv_size:.1f} MB", "sub": "CSV uncompressed"},
        {"icon": icon("calendar", size=20, color=COLORS["success"]), "label": "Date Filter", "value": f"{filters['date_range'][0]:%b %d, %Y}", "sub": f"to {filters['date_range'][1]:%b %d, %Y}"},
    ])

    st.write("")

    # ---------------------------------------------------------------------
    # 2. EXPORT SLICE VISUALIZATION — Records by Court & Monthly Volume
    # ---------------------------------------------------------------------
    ec1, ec2 = st.columns([1, 1.2])

    with ec1:
        with st.container(key="card_rep_4"):
            section_header("Matching Records by Court")
            if total_cases:
                court_counts = df["Court"].value_counts()
                fig = gradient_bar(court_counts.index.tolist(), court_counts.values.tolist(), color=COLORS["accent_primary"])
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for the current filter selection.")

    with ec2:
        with st.container(key="card_rep_5"):
            section_header("Matching Records — Monthly Volume")
            gaps = find_coverage_gaps(df, COURTS_ORDER)
            if gaps:
                st.caption(
                    f"⚠️ {len(gaps)} court(s) are missing listings for some months in this selection — "
                    "monthly totals mix courts with different scrape windows. See Trends Over Time for the exact gap."
                )
            month_counts = df.dropna(subset=["Year_Month"]).groupby("Year_Month").size().sort_index()
            if len(month_counts):
                fig = glow_trend(month_counts.index.tolist(), {"Records": month_counts.values.tolist()}, colors={"Records": COLORS["accent_secondary"]}, height=300)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for the current filter selection.")

    st.write("")

    # ---------------------------------------------------------------------
    # 3. DOWNLOAD CONTROLS & EXPORT ACTIONS
    # ---------------------------------------------------------------------
    with st.container(key="card_rep_1"):
        section_header("Data Export Center")

        c1, c2, c3 = st.columns([2, 1, 1])

        with c1:
            st.markdown(
                "<div style='color:#A9BBDD;font-size:0.9rem;line-height:1.5;'>"
                "Export the currently filtered subset of cause-list records in CSV format. "
                f"The download contains all {len(export_cols)} unified schema attributes (including normalized "
                "category and bench-type groupings), suitable for external statistical analysis or Excel processing."
                "</div>",
                unsafe_allow_html=True
            )

        with c2:
            if total_cases > 0:
                # Prepare CSV in memory
                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download CSV Dataset",
                    data=csv_data,
                    file_name="pakistan_high_courts_filtered_export.csv",
                    mime="text/csv",
                    width='stretch',
                    icon=":material/download:",
                )
            else:
                st.button("Download CSV Dataset", disabled=True, width='stretch')

        with c3:
            st.markdown(
                f"<div style='text-align:center;padding:8px;background:rgba(59,130,246,0.1);border-radius:8px;border:1px solid rgba(59,130,246,0.2);color:#F3F6FD;font-size:0.82rem;'>"
                f"<b>{total_cases:,}</b> Rows Ready"
                f"</div>",
                unsafe_allow_html=True
            )

    st.write("")

    # ---------------------------------------------------------------------
    # 4. INTERACTIVE DATA PREVIEW TABLE
    # ---------------------------------------------------------------------
    with st.container(key="card_rep_2"):
        section_header("Filtered Dataset Preview (First 500 Records)")

        if total_cases > 0:
            preview_df = df.head(500)
            st.dataframe(preview_df, width='stretch', hide_index=True)
        else:
            st.info("No matching records found for the current filter criteria.")

    st.write("")

    # ---------------------------------------------------------------------
    # 5. FIELD COVERAGE SUMMARY
    # ---------------------------------------------------------------------
    with st.container(key="card_rep_3"):
        section_header("Exported Schema Column Population Summary")

        if total_cases > 0:
            col_summary = []
            for col in df.columns:
                non_null = df[col].notna().sum()
                null_pct = ((len(df) - non_null) / len(df)) * 100
                dtype = str(df[col].dtype)
                col_summary.append({
                    "Column Name": col,
                    "Data Type": dtype,
                    "Populated Count": f"{non_null:,}",
                    "Null / Missing %": f"{null_pct:.1f}%",
                    "Distinct Values": df[col].nunique(),
                })
            st.dataframe(pd.DataFrame(col_summary), width='stretch', hide_index=True)
        else:
            st.info("No data available.")
