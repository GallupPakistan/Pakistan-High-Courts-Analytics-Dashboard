"""
overview.py — All-Courts Overview.
Uses st.container(key="card_ov_N") for card sections so Streamlit actually
wraps content inside the container element (unlike the split st.markdown
glass-card pattern which creates always-empty divs).
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
from components.charts.map_chart import build_bench_location_map  # noqa: E402
from components.charts.sankey_chart import build_court_flow_sankey  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def render():
    render_top_bar(subtitle="All 5 High Courts — cross-court snapshot")

    df_all = load_master_data()

    # ------------------------------------------------------------------
    # Apply a map-marker click from the previous run, BEFORE the filter
    # widgets below are instantiated — Streamlit selectboxes read their
    # value from st.session_state[key] at creation time, so this has to
    # land in "ov_court" / "ov_bench" first. st.session_state["ov_map_select"]
    # already holds the click event from the prior run (it's the return
    # value of the st.plotly_chart(key="ov_map_select") call further down),
    # so it's readable here even though that widget hasn't run yet this pass.
    # ------------------------------------------------------------------
    # Only apply a NEW map-marker click — stale selection state persists in
    # session_state across reruns, so replaying it here would undo any manual
    # filter changes the user made via the selectboxes below.
    map_selection = st.session_state.get("ov_map_select")
    if map_selection and map_selection.get("selection", {}).get("points"):
        custom = map_selection["selection"]["points"][0].get("customdata")
        if custom:
            _city, court, bench_value = custom
            bench_value = bench_value if bench_value else "All"
            selection_id = (court, bench_value)
            if st.session_state.get("ov_map_applied") != selection_id:
                st.session_state["ov_court"] = court
                st.session_state["ov_bench"] = bench_value
                st.session_state["ov_map_applied"] = selection_id
                st.rerun()

    filters = render_filter_bar(df_all, key_prefix="ov")
    df = apply_filters(df_all, **filters)

    st.write("")

    # ------------------------------------------------------------------
    # 1. KPI ROW
    # ------------------------------------------------------------------
    total_cases      = len(df)
    total_judges     = df["Judge"].nunique()
    total_benches    = df["Bench_Type_Group"].nunique()
    total_categories = df["Case_Category"].nunique()
    courts_covered   = df["Court"].nunique()

    render_kpi_row([
        {"icon": icon("folder",   size=20, color=COLORS["accent_primary"]),   "label": "Total Cases",      "value": f"{total_cases:,}",      "sub": f"Across {courts_covered} courts"},
        {"icon": icon("gavel",    size=20, color=COLORS["accent_secondary"]), "label": "Judges",           "value": f"{total_judges:,}",     "sub": "On record"},
        {"icon": icon("landmark", size=20, color=COLORS["accent_tertiary"]),  "label": "Bench Types",      "value": f"{total_benches:,}",    "sub": "Single / Division / etc."},
        {"icon": icon("tags",     size=20, color=COLORS["warning"]),          "label": "Categories",       "value": f"{total_categories:,}", "sub": "Listed categories"},
        {"icon": icon("calendar", size=20, color=COLORS["success"]),          "label": "Date Range",
         "value": f"{df['Hearing_Date'].min():%b %Y}" if total_cases else "—",
         "sub":   f"to {df['Hearing_Date'].max():%b %Y}" if total_cases else ""},
    ])

    st.write("")

    # ------------------------------------------------------------------
    # 1b. BENCH LOCATIONS MAP
    # ------------------------------------------------------------------
    with st.container(key="card_ov_map"):
        section_header("Bench Locations Across Pakistan")
        if total_cases:
            fig = build_bench_location_map(df)
            st.plotly_chart(
                fig, width='stretch', config={"displayModeBar": False},
                on_select="rerun", selection_mode=["points"], key="ov_map_select",
            )
            st.caption(
                "Marker size = listing volume at that bench location. Color = parent High Court. "
                "Click a marker to filter the whole page to that court and bench — scroll/pinch "
                "to zoom, hover for exact counts."
            )
        else:
            st.info("No data for current filters.")

    st.write("")

    # ------------------------------------------------------------------
    # 2 & 3. Case Volume by Court  |  Case Category Distribution
    # ------------------------------------------------------------------
    c1, c2 = st.columns([1.2, 1])

    with c1:
        with st.container(key="card_ov_2"):
            section_header("Case Volume by Court")
            vol = df["Court"].value_counts().reindex(COURTS_ORDER).dropna()
            if len(vol):
                fig = gradient_bar(vol.index.tolist(), vol.values.tolist(), color=COLORS["accent_primary"])
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for the current filter selection.")

    with c2:
        with st.container(key="card_ov_3"):
            section_header("Case Category Distribution")
            if total_cases:
                top_cat    = df["Case_Category"].value_counts().head(6)
                other_cnt  = df["Case_Category"].value_counts().iloc[6:].sum()
                labels     = top_cat.index.tolist() + (["Others"] if other_cnt > 0 else [])
                values     = top_cat.values.tolist() + ([other_cnt] if other_cnt > 0 else [])
                rc1, rc2   = st.columns([1.1, 1])
                with rc1:
                    fig = futuristic_radial(labels, values, center_label="Total Cases", center_value=f"{total_cases:,}", height=240)
                    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                with rc2:
                    st.markdown(radial_legend_html(labels, values), unsafe_allow_html=True)
            else:
                st.info("No data for the current filter selection.")

    st.write("")

    # ------------------------------------------------------------------
    # 3b. CASE FLOW — Court -> Bench Type -> Category
    # ------------------------------------------------------------------
    with st.container(key="card_ov_flow"):
        section_header("Case Flow: Court → Bench Type → Category")
        if total_cases:
            fig = build_court_flow_sankey(df)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            st.caption(
                "Ribbon width = case volume along that path. Top 7 categories shown by volume; "
                "the rest are folded into \"Other\"."
            )
        else:
            st.info("No data for the current filter selection.")

    st.write("")

    # ------------------------------------------------------------------
    # 4. Case Trends Over Time
    # ------------------------------------------------------------------
    with st.container(key="card_ov_4"):
        section_header("Case Trends Over Time (Monthly, by Court)")
        if total_cases:
            trend_df = df.dropna(subset=["Year_Month"]).groupby(["Year_Month", "Court"]).size().reset_index(name="Cases")
            pivot    = trend_df.pivot(index="Year_Month", columns="Court", values="Cases").fillna(0).sort_index()
            series   = {c: pivot[c].tolist() for c in COURTS_ORDER if c in pivot.columns}
            fig      = glow_trend(pivot.index.tolist(), series, colors=COURT_COLORS, height=360)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for the current filter selection.")

    st.write("")

    # ------------------------------------------------------------------
    # 5 & 6. Bench Type Distribution  |  Top 5 Benches
    # ------------------------------------------------------------------
    c3, c4 = st.columns([1, 1.2])

    with c3:
        with st.container(key="card_ov_5"):
            section_header("Bench Type Distribution")
            if total_cases:
                bt   = df["Bench_Type_Group"].value_counts().head(6)
                rc1, rc2 = st.columns([1.1, 1])
                with rc1:
                    fig = futuristic_radial(bt.index.tolist(), bt.values.tolist(), center_label="Listings", center_value=f"{bt.sum():,}", height=240)
                    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                with rc2:
                    st.markdown(radial_legend_html(bt.index.tolist(), bt.values.tolist()), unsafe_allow_html=True)
            else:
                st.info("No data for the current filter selection.")

    with c4:
        with st.container(key="card_ov_6"):
            section_header("Top 5 Benches / Divisions by Case Volume")
            if total_cases:
                top_benches = (
                    df.groupby(["Bench_Location", "Court"]).size().reset_index(name="Cases")
                    .sort_values("Cases", ascending=False).head(5)
                )
                top_benches["Bench_Location"] = top_benches["Bench_Location"].fillna("(Unspecified)")
                st.dataframe(
                    top_benches.rename(columns={"Bench_Location": "Bench / Location"}),
                    width='stretch', hide_index=True,
                )
            else:
                st.info("No data for the current filter selection.")

    st.write("")

    # ------------------------------------------------------------------
    # 7. Judge Workload Snapshot
    # ------------------------------------------------------------------
    with st.container(key="card_ov_7"):
        section_header("Judge Workload Snapshot")
        judge_counts    = df["Judge"].value_counts()
        judge_counts    = judge_counts[judge_counts.index.notna()]
        avg_cases       = judge_counts.mean()     if len(judge_counts) else 0
        max_judge_count = judge_counts.max()      if len(judge_counts) else 0
        min_judge_count = judge_counts.min()      if len(judge_counts) else 0

        wc1, wc2, wc3 = st.columns(3)
        with wc1:
            simple_kpi_card("Avg. Listings / Judge", f"{avg_cases:,.0f}")
        with wc2:
            simple_kpi_card("Highest Workload", f"{max_judge_count:,}", "listings, one judge")
        with wc3:
            simple_kpi_card("Lowest Workload",  f"{min_judge_count:,}", "listings, one judge")

    st.write("")

    # ------------------------------------------------------------------
    # 8. Key Insights
    # ------------------------------------------------------------------
    with st.container(key="card_ov_8"):
        section_header("Key Insights")
        if total_cases:
            court_vol = df["Court"].value_counts()
            if len(court_vol):
                top_court     = court_vol.idxmax()
                top_court_pct = court_vol.max() / total_cases * 100
                insight_pill(icon("trending-up", size=16, color=COLORS["success"]),
                             f"<b>{top_court} High Court</b> has the highest volume — {court_vol.max():,} cases ({top_court_pct:.1f}% of total).")

            bench_top = df["Bench_Location"].value_counts()
            if len(bench_top):
                insight_pill(icon("map-pin", size=16, color=COLORS["accent_secondary"]),
                             f"<b>{bench_top.idxmax()}</b> is the busiest bench with {bench_top.max():,} listed cases.")

            cat_top = df["Case_Category"].value_counts()
            if len(cat_top):
                insight_pill(icon("tags", size=16, color=COLORS["warning"]),
                             f"<b>{cat_top.idxmax()}</b> is the most common category ({cat_top.max():,} cases).")

            judge_counts = df["Judge"].value_counts()
            judge_counts = judge_counts[judge_counts.index.notna()]
            if len(judge_counts):
                avg  = judge_counts.mean()
                mn   = judge_counts.min()
                mx   = judge_counts.max()
                insight_pill(icon("users", size=16, color=COLORS["accent_tertiary"]),
                             f"Avg judge carries <b>{avg:,.0f} listings</b>; range {mn:,}–{mx:,}.")
        else:
            st.info("No data for the current filter selection.")
