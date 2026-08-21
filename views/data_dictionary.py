"""
data_dictionary.py

Data Dictionary view:
Reference page documenting all 16 unified schema columns, descriptions, data types,
sample values, and source court mapping details.
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS  # noqa: E402
from utils.data_loader import load_master_data  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header  # noqa: E402
from components.charts.bar_chart import gradient_bar  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402

SCHEMA_DICTIONARY = [
    {
        "Column": "Court",
        "Type": "Categorical (String)",
        "Description": "High Court institution name (Sindh, Lahore, Islamabad, Peshawar, Balochistan).",
        "Source Mapping": "Standardized court identifier derived from source file provenance.",
        "Sample": "Lahore, Sindh, Peshawar",
    },
    {
        "Column": "Bench_Location",
        "Type": "Categorical (String)",
        "Description": "Physical seat or bench location where the cause list was issued.",
        "Source Mapping": "Mapped from Bench/Seat/Location column across source court files.",
        "Sample": "Principal Seat, Multan, Rawalpindi, Sukkur",
    },
    {
        "Column": "Court_Room",
        "Type": "Categorical (String)",
        "Description": "Designated courtroom number or chamber identifier.",
        "Source Mapping": "Mapped from Court No / Room No / Chamber field.",
        "Sample": "Court Room No 1, DB-II, SB-IV",
    },
    {
        "Column": "Judge",
        "Type": "Categorical (String)",
        "Description": "Honorable Judge or bench composition presiding over the listed matter.",
        "Source Mapping": "Unified judge name field across single and division benches.",
        "Sample": "Mr. Justice X, Division Bench-I",
    },
    {
        "Column": "Bench_Type",
        "Type": "Categorical (String)",
        "Description": "Structure of judicial bench (Single Bench, Division Bench, Full Bench).",
        "Source Mapping": "Mapped from Bench Type / Bench Code column.",
        "Sample": "Single Bench, Division Bench",
    },
    {
        "Column": "Bench_Type_Group",
        "Type": "Categorical (String), Derived",
        "Description": "Normalized Bench_Type: each court records the same bench configuration under different raw labels (e.g. \"SB\", \"Single Bench\", \"Single_Bench_S_B_\" all mean the same thing), so this groups them into one consistent bucket per real configuration. Used for all bench-type charts and KPIs instead of the raw column. See utils/bench_type_normalizer.py.",
        "Source Mapping": "Computed from Bench_Type via utils/bench_type_normalizer.py.",
        "Sample": "Single Bench, Division Bench, Full / Larger Bench, Other / Unspecified",
    },
    {
        "Column": "Case_No",
        "Type": "String / Identifier",
        "Description": "Official case registration number or cause list item identifier.",
        "Source Mapping": "Mapped from Case No / Filing No across court files.",
        "Sample": "W.P. 1234/2023, C.M.A. 567/2022",
    },
    {
        "Column": "Case_Year",
        "Type": "Numeric / Integer",
        "Description": "Year of case institution or registration.",
        "Source Mapping": "Extracted from Case No suffix or dedicated Year field.",
        "Sample": "2021, 2022, 2023",
    },
    {
        "Column": "Case_Category",
        "Type": "Categorical (String)",
        "Description": "Standardized category of legal filing (Writ Petition, Civil Revision, Tax, Criminal, etc.).",
        "Source Mapping": "Unified from Case Type / Category / Filing Nature across 5 courts.",
        "Sample": "Writ Petition, Civil Appeal, Criminal Revision",
    },
    {
        "Column": "Case_Stage",
        "Type": "Categorical (String)",
        "Description": "Listing stage or proceeding nature as shown on the daily cause list.",
        "Source Mapping": "Mapped from Stage / Fixed For / Proceeding Type.",
        "Sample": "For Hearing, Arguments, Orders, Pre-admission",
    },
    {
        "Column": "Section",
        "Type": "Categorical (String)",
        "Description": "Statutory provision, act section, or constitutional article cited.",
        "Source Mapping": "Mapped from Section / Act / Law Provision column.",
        "Sample": "Art 199, Sec 497 CrPC, Sec 115 CPC",
    },
    {
        "Column": "Petitioner",
        "Type": "Text (String)",
        "Description": "Name of the initiating party, applicant, or appellant.",
        "Source Mapping": "Mapped from Petitioner / Plaintiff / Appellant field.",
        "Sample": "M/s Saba Power Co. Ltd., Muhammad Ali",
    },
    {
        "Column": "Respondent",
        "Type": "Text (String)",
        "Description": "Name of the opposing party, state, or defense respondent.",
        "Source Mapping": "Mapped from Respondent / Defendant / Appellee field.",
        "Sample": "Federation of Pakistan, Province of Punjab",
    },
    {
        "Column": "Petitioner_Advocate",
        "Type": "Text (String)",
        "Description": "Legal counsel representing petitioner(s).",
        "Source Mapping": "Mapped from Petitioner Counsel / Advocate Name.",
        "Sample": "Ahmad Raza Advocate, Barrister XYZ",
    },
    {
        "Column": "Respondent_Advocate",
        "Type": "Text (String)",
        "Description": "Legal counsel representing respondent(s) or State/AAG.",
        "Source Mapping": "Mapped from Respondent Counsel / DAG / AAG Name.",
        "Sample": "Prosecutor General, Deputy Attorney General",
    },
    {
        "Column": "Hearing_Date",
        "Type": "Datetime (YYYY-MM-DD)",
        "Description": "Date of cause list placement / hearing occurrence.",
        "Source Mapping": "Parsed datetime from Cause List Date / Roster Date.",
        "Sample": "2023-05-15, 2023-11-20",
    },
    {
        "Column": "Case_Title",
        "Type": "Text (String)",
        "Description": "Full cause title of the matter ('Petitioner VS Respondent').",
        "Source Mapping": "Concatenated or mapped directly from Case Title field.",
        "Sample": "John Doe VS Federation of Pakistan",
    },
]


def render():
    render_top_bar(subtitle="Unified 16-column schema documentation, definitions & data lineage")

    st.write("")

    # ---------------------------------------------------------------------
    # 1. DICTIONARY OVERVIEW KPI ROW
    # ---------------------------------------------------------------------
    render_kpi_row([
        {"icon": icon("menu_book", size=20, color=COLORS["accent_primary"]), "label": "Unified Schema", "value": "16 Columns", "sub": "Standardized attributes"},
        {"icon": icon("landmark", size=20, color=COLORS["accent_secondary"]), "label": "Courts Integrated", "value": "5 High Courts", "sub": "Sindh, LHC, IHC, PHC, BHC"},
        {"icon": icon("folder", size=20, color=COLORS["accent_tertiary"]), "label": "Master Dataset", "value": "~339,000 Rows", "sub": "Parquet cause-list master"},
        {"icon": icon("gavel", size=20, color=COLORS["warning"]), "label": "Pipeline Mode", "value": "Full Rebuild", "sub": "Deterministic pipeline"},
        {"icon": icon("info", size=20, color=COLORS["success"]), "label": "Data Type", "value": "Cause-List Only", "sub": "No status/disposal fields"},
    ])

    st.write("")

    # ---------------------------------------------------------------------
    # 2. SCHEMA TABLE
    # ---------------------------------------------------------------------
    with st.container(key="card_dd_1"):
        section_header("Complete 16-Column Unified Schema Reference")

        dict_df = pd.DataFrame(SCHEMA_DICTIONARY)
        st.dataframe(
            dict_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Column": st.column_config.TextColumn("Column Name", width="medium"),
                "Type": st.column_config.TextColumn("Data Type", width="small"),
                "Description": st.column_config.TextColumn("Field Description", width="large"),
                "Source Mapping": st.column_config.TextColumn("Source Court Mapping", width="medium"),
                "Sample": st.column_config.TextColumn("Sample Values", width="medium"),
            }
        )

    st.write("")

    # ---------------------------------------------------------------------
    # 3. COLUMN COMPLETENESS & CARDINALITY (real master-dataset stats)
    # ---------------------------------------------------------------------
    df = load_master_data()
    completeness = (df.notna().mean() * 100).round(1).sort_values()

    dc1, dc2 = st.columns([1.2, 1])

    with dc1:
        with st.container(key="card_dd_3"):
            section_header("Column Completeness (% Populated)")
            fig = gradient_bar(completeness.index.tolist(), completeness.values.tolist(), color=COLORS["accent_primary"], orientation="h", value_suffix="%", height=460)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with dc2:
        with st.container(key="card_dd_4"):
            section_header("Distinct Values — Key Categorical Fields")
            card_cols = ["Court", "Bench_Location", "Bench_Type", "Court_Room", "Judge"]
            card_cols = [c for c in card_cols if c in df.columns]
            distinct_counts = pd.Series({c: df[c].nunique() for c in card_cols}).sort_values()
            fig = gradient_bar(distinct_counts.index.tolist(), distinct_counts.values.tolist(), color=COLORS["accent_secondary"], orientation="h", height=460)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.caption("Case_Category, Section, Case_No, Petitioner and Respondent are excluded here — free-text fields with thousands of distinct values that would dwarf this scale.")

    st.write("")

    # ---------------------------------------------------------------------
    # 4. PIPELINE & INTEGRATION NOTES
    # ---------------------------------------------------------------------
    with st.container(key="card_dd_2"):
        section_header("Data Pipeline & Standardization Methodology")

        st.markdown(
            """
            <div style="color:#A9BBDD;font-size:0.9rem;line-height:1.6;">
            <ul>
                <li><b>Source Provenance:</b> Data is ingested from official cause lists of 5 High Courts — Sindh High Court, Lahore High Court, Islamabad High Court, Peshawar High Court, and Balochistan High Court.</li>
                <li><b>Bannu Exclusion:</b> Bannu Bench data was excluded from Peshawar High Court as it contained District/Sessions Court records with corrupted Petitioner/Respondent fields.</li>
                <li><b>Unified Schema Mapping:</b> Each court's heterogeneous column names were mapped into this single 16-column specification.</li>
                <li><b>Rebuild Guarantee:</b> The Python ETL script performs a clean full rebuild (never append) directly to <code>combined_dashboard_master.parquet</code>.</li>
                <li><b>Listing-Based Proxy:</b> Because cause lists do not track case disposal dates or pending case outcomes, listing frequency (appearances across dates) is used as the sole proxy for judicial activity and backlog.</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
