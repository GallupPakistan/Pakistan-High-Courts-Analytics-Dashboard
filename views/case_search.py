"""
case_search.py

Case Search view: look up a specific case by Case No, party name
(petitioner/respondent), or advocate name — and see its full hearing
timeline (every listing found for that case, chronologically), instead of
only aggregate/summary charts elsewhere in the dashboard.
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS, COURT_COLORS  # noqa: E402
from utils.data_loader import load_master_data, COURTS_ORDER  # noqa: E402
from utils.formatting import clean_judge_label  # noqa: E402
from components.kpi_cards import section_header, simple_kpi_card  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def render():
    render_top_bar(subtitle="Look up a specific case by number, party, or advocate")

    df_all = load_master_data()

    st.write("")

    with st.container(key="card_search_bar"):
        section_header("Search")
        c1, c2, c3 = st.columns([1.3, 2.3, 1])
        with c1:
            search_type = st.radio(
                "Search by",
                ["Case Number", "Party Name", "Advocate"],
                key="search_type",
            )
        with c2:
            placeholder = {
                "Case Number": "e.g. W.P 5406/2025 or CP-829/2021",
                "Party Name": "e.g. Muhammad Aslam, or part of a name",
                "Advocate": "e.g. Khalid Ishaq, or part of a name",
            }[search_type]
            query = st.text_input("Search term", placeholder=placeholder, key="search_query")
        with c3:
            court_filter = st.selectbox("Court (optional)", ["All Courts"] + COURTS_ORDER, key="search_court")

    st.write("")

    if not query or not query.strip():
        st.info("Enter a search term above to look up a case, party, or advocate.")
        return

    query = query.strip()
    df = df_all if court_filter == "All Courts" else df_all[df_all["Court"] == court_filter]

    if search_type == "Case Number":
        mask = df["Case_No"].astype(str).str.contains(query, case=False, na=False, regex=False)
    elif search_type == "Party Name":
        mask = (
            df["Petitioner"].astype(str).str.contains(query, case=False, na=False, regex=False)
            | df["Respondent"].astype(str).str.contains(query, case=False, na=False, regex=False)
        )
    else:  # Advocate
        mask = (
            df["Petitioner_Advocate"].astype(str).str.contains(query, case=False, na=False, regex=False)
            | df["Respondent_Advocate"].astype(str).str.contains(query, case=False, na=False, regex=False)
        )

    results = df[mask].sort_values("Hearing_Date", ascending=False)

    if results.empty:
        st.warning(f"No matches found for **\"{query}\"** in {search_type}. Try a shorter or different term.")
        return

    # ---------------------------------------------------------------------
    # RESULTS SUMMARY
    # ---------------------------------------------------------------------
    n_listings = len(results)
    n_cases = results["Case_UID"].nunique()
    n_courts = results["Court"].nunique()

    k1, k2, k3 = st.columns(3)
    with k1:
        simple_kpi_card("Matching Listings", f"{n_listings:,}", f"For \"{query}\"")
    with k2:
        simple_kpi_card("Distinct Cases", f"{n_cases:,}", "Grouped by case identity")
    with k3:
        simple_kpi_card("Courts Involved", f"{n_courts}", "Across selection")

    st.write("")

    # ---------------------------------------------------------------------
    # If the match resolves to exactly ONE case, show its full timeline
    # ---------------------------------------------------------------------
    if n_cases == 1 and search_type == "Case Number":
        with st.container(key="card_search_timeline"):
            case_title = results["Case_Title"].dropna().iloc[0] if results["Case_Title"].notna().any() else "N/A"
            section_header(f"Case Timeline — {case_title}")
            st.caption(
                f"**{results['Case_No'].iloc[0]}** · {results['Court'].iloc[0]} High Court"
                + (f" ({results['Bench_Location'].iloc[0]})" if pd.notna(results['Bench_Location'].iloc[0]) else "")
            )
            timeline = results.sort_values("Hearing_Date")[
                ["Hearing_Date", "Judge", "Bench_Type", "Case_Category", "Court_Room"]
            ].copy()
            timeline["Judge"] = timeline["Judge"].apply(clean_judge_label)
            timeline.columns = ["Hearing Date", "Judge(s)", "Bench Type", "Category", "Court Room"]
            st.dataframe(timeline, width='stretch', hide_index=True)
            st.caption(f"This case was listed **{len(timeline)} time(s)** in the current dataset.")
        st.write("")

    # ---------------------------------------------------------------------
    # FULL RESULTS TABLE
    # ---------------------------------------------------------------------
    with st.container(key="card_search_results"):
        section_header(f"All Matching Listings ({n_listings:,})")
        display_cols = [
            "Hearing_Date", "Court", "Bench_Location", "Case_No", "Case_Title",
            "Judge", "Case_Category", "Petitioner", "Respondent",
            "Petitioner_Advocate", "Respondent_Advocate",
        ]
        display_df = results[display_cols].head(500).copy()
        display_df["Judge"] = display_df["Judge"].apply(clean_judge_label)
        st.dataframe(display_df, width='stretch', hide_index=True)
        if n_listings > 500:
            st.caption(f"Showing first 500 of {n_listings:,} matching rows. Narrow your search or add a Court filter to see more precisely.")
