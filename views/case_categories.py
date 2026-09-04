"""
case_categories.py

Case Categories view:
1. Category summary KPI row
2. Top Case Categories overall (futuristic radial & bar)
3. Category Distribution across Courts (grouped bar & crosstab matrix)
4. Category listing trends over time
5. Top Cited Legal Sections (Section field, coverage-labeled)
6. Category Insights

Each of the 5 High Courts records Case_Category in its own free-text format,
so the exact same subject matter (e.g. banking litigation) shows up under
dozens of different raw strings across courts. A "Normalized Group" view
mode is offered (default) that rolls those variants up into ~30 consistent
buckets via utils/category_normalizer.py, so cross-court comparisons here
aggregate correctly instead of fragmenting across near-duplicate labels. A
"Detailed Raw Category" mode is still available for drilling into exact
category strings.
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS, COURT_COLORS  # noqa: E402
from utils.data_loader import load_master_data, apply_filters, COURTS_ORDER  # noqa: E402
from utils.data_quality import find_coverage_gaps  # noqa: E402
from components.filters import render_filter_bar  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header, insight_pill, simple_kpi_card  # noqa: E402
from components.charts.bar_chart import gradient_bar, grouped_bar  # noqa: E402
from components.charts.donut_chart import futuristic_radial, radial_legend_html  # noqa: E402
from components.charts.lightbulb_chart import lightbulb_category_chart  # noqa: E402
from components.charts.gauge_chart import gauge_chart  # noqa: E402
from components.charts.trend_line import glow_trend  # noqa: E402
from styles.theme import CHART_COLORWAY  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def render():
    render_top_bar(subtitle="Legal category distribution, crosstab & temporal trend analytics")

    df_all = load_master_data()
    filters = render_filter_bar(df_all, key_prefix="cc")
    df = apply_filters(df_all, **filters)

    st.write("")

    # ---------------------------------------------------------------------
    # 0. CATEGORY VIEW MODE — normalized (default) vs raw/detailed
    # ---------------------------------------------------------------------
    mode_col, note_col = st.columns([1.4, 3])
    with mode_col:
        view_mode = st.radio(
            "Category View",
            ["Normalized Group", "Detailed Raw Category"],
            key="cc_cat_mode",
            horizontal=True,
        )
    cat_col = "Category_Group" if view_mode == "Normalized Group" else "Case_Category"
    cat_label = "Category Group" if cat_col == "Category_Group" else "Raw Category"
    with note_col:
        st.write("")
        if cat_col == "Category_Group":
            st.caption(
                "Showing courts' many raw category spellings rolled up into consistent groups "
                "(e.g. \"BANKING\", \"BANKING APPEAL\" and \"Civil - COS(B) - Banking\" all count as "
                "**Banking & Finance**) — this is the view to use for cross-court comparison."
            )
        else:
            st.caption(
                "Showing exact raw Case_Category strings as recorded by each court — the same "
                "subject matter may be split across many near-duplicate spellings here."
            )

    st.write("")

    # ---------------------------------------------------------------------
    # 1. KPI ROW
    # ---------------------------------------------------------------------
    total_cases = len(df)
    total_cats = df[cat_col].nunique() if total_cases else 0
    top_cat = df[cat_col].value_counts().idxmax() if total_cats else "N/A"
    top_cat_vol = df[cat_col].value_counts().max() if total_cats else 0
    top_cat_pct = (top_cat_vol / total_cases * 100) if total_cases else 0

    render_kpi_row([
        {"icon": icon("tags", size=20, color=COLORS["accent_primary"]), "label": f"Distinct {cat_label}s", "value": f"{total_cats:,}", "sub": "Categories listed"},
        {"icon": icon("folder", size=20, color=COLORS["accent_secondary"]), "label": f"Top {cat_label}", "value": f"{top_cat}", "sub": f"{top_cat_vol:,} listings ({top_cat_pct:.1f}%)"},
        {"icon": icon("landmark", size=20, color=COLORS["accent_tertiary"]), "label": "Courts Covered", "value": f"{df['Court'].nunique()}", "sub": "Courts in view"},
        {"icon": icon("gavel", size=20, color=COLORS["warning"]), "label": "Sections Cited", "value": f"{df['Section'].nunique():,}" if total_cases else "0", "sub": "Distinct law sections"},
        {"icon": icon("calendar", size=20, color=COLORS["success"]), "label": "Total Listings", "value": f"{total_cases:,}", "sub": "Filtered volume"},
    ])

    st.write("")

    # ---------------------------------------------------------------------
    # 1b. TOP 4 CATEGORIES — LIGHTBULB OVERVIEW
    # ---------------------------------------------------------------------
    with st.container(key="card_catg_lightbulb"):
        section_header(f"Top {cat_label}s at a Glance")
        if total_cases:
            vc = df[cat_col].value_counts().head(4)
            top4_share = vc.sum() / total_cases * 100
            icons_cycle = ["gavel", "landmark", "users", "file-bar-chart"]
            lb_categories = []
            for i, (lbl, cnt) in enumerate(vc.items()):
                pct = cnt / total_cases * 100
                lb_categories.append({
                    "label": lbl,
                    "value": pct,
                    "count": int(cnt),
                    "desc": f"{pct:.1f}% of all listings in the current filter selection.",
                    "icon": icons_cycle[i % len(icons_cycle)],
                })
            st.iframe(
                src=lightbulb_category_chart(
                    lb_categories,
                    center_label=f"Top {len(lb_categories)} Share",
                    center_value=f"{top4_share:.0f}%",
                ),
                height=350,
            )
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 2. TOP CATEGORIES OVERALL
    # ---------------------------------------------------------------------
    c1, c2 = st.columns([1.2, 1])

    with c1:
        with st.container(key="card_catg_1"):
            section_header(f"Top 10 {cat_label}s by Volume")
            if total_cases:
                top_10 = df[cat_col].value_counts().head(10)
                fig = gradient_bar(top_10.index.tolist(), top_10.values.tolist(), color=COLORS["accent_primary"], orientation="h")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    with c2:
        with st.container(key="card_catg_2"):
            section_header(f"{cat_label} Volume Share")
            if total_cases:
                top_5 = df[cat_col].value_counts().head(5)
                other_cnt = df[cat_col].value_counts().iloc[5:].sum()
                labels = top_5.index.tolist() + (["Others"] if other_cnt > 0 else [])
                vals = top_5.values.tolist() + ([other_cnt] if other_cnt > 0 else [])
                rc1, rc2 = st.columns([1.1, 1])
                with rc1:
                    fig = futuristic_radial(labels, vals, center_label="Category Total", center_value=f"{total_cases:,}", height=240)
                    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                with rc2:
                    st.markdown(radial_legend_html(labels, vals), unsafe_allow_html=True)
            else:
                st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 3. CATEGORY VS COURT MATRIX & GROUPED BAR
    # ---------------------------------------------------------------------
    with st.container(key="card_catg_3"):
        section_header(f"Top {cat_label}s Distribution Across Courts")

        if total_cases:
            top_cats = df[cat_col].value_counts().head(6).index.tolist()
            cat_court_df = df[df[cat_col].isin(top_cats)].groupby([cat_col, "Court"]).size().unstack(fill_value=0)
            series = {c: cat_court_df[c].tolist() for c in COURTS_ORDER if c in cat_court_df.columns}
            fig = grouped_bar(top_cats, series, colors=COURT_COLORS, height=360)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

            st.write("")
            st.markdown(f"<div style='font-size:0.88rem;font-weight:600;color:#A9BBDD;margin-bottom:8px;'>{cat_label} vs Court Crosstab Matrix</div>", unsafe_allow_html=True)
            crosstab = pd.crosstab(df[cat_col], df["Court"]).reindex(columns=COURTS_ORDER).fillna(0).astype(int)
            crosstab["Total"] = crosstab.sum(axis=1)
            crosstab = crosstab.sort_values("Total", ascending=False).head(10)
            st.dataframe(crosstab.reset_index(), width='stretch', hide_index=True)
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 3b. TOP CATEGORIES BY BENCH TYPE & YEARLY VOLUME
    # ---------------------------------------------------------------------
    c7, c8 = st.columns([1.2, 1])

    with c7:
        with st.container(key="card_catg_7"):
            section_header(f"Top {cat_label}s by Bench Type")
            if total_cases:
                top_cats_bt = df[cat_col].value_counts().head(4).index.tolist()
                top_bts = df["Bench_Type_Group"].value_counts().head(4).index.tolist()
                sub = df[df[cat_col].isin(top_cats_bt) & df["Bench_Type_Group"].isin(top_bts)]
                cat_bt_df = sub.groupby([cat_col, "Bench_Type_Group"]).size().unstack(fill_value=0)
                series = {c: cat_bt_df[c].tolist() for c in top_bts if c in cat_bt_df.columns}
                fig = grouped_bar(top_cats_bt, series, height=360)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    with c8:
        with st.container(key="card_catg_8"):
            section_header(f"Top {cat_label}s — Yearly Volume")
            if total_cases:
                top_4_yr = df[cat_col].value_counts().head(4).index.tolist()
                yr_df = df[df[cat_col].isin(top_4_yr)].dropna(subset=["Year"]).groupby(["Year", cat_col]).size().unstack(fill_value=0)
                years = yr_df.index.astype(int).astype(str).tolist()
                series = {c: yr_df[c].tolist() for c in top_4_yr if c in yr_df.columns}
                fig = grouped_bar(years, series, height=360)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 4. TRENDS FOR TOP CATEGORIES
    # ---------------------------------------------------------------------
    with st.container(key="card_catg_4"):
        section_header(f"Top 4 {cat_label} Listing Trends Over Time")

        if total_cases:
            gaps = find_coverage_gaps(df, COURTS_ORDER)
            if gaps:
                st.caption(
                    f"⚠️ {len(gaps)} court(s) are missing listings for some months in the current "
                    "selection — the trend below mixes courts with different scrape windows, so month-"
                    "to-month shifts may partly reflect *when data was collected*, not real category volume."
                )
            top_4_cats = df[cat_col].value_counts().head(4).index.tolist()
            trend_cat = df[df[cat_col].isin(top_4_cats)].dropna(subset=["Year_Month"]).groupby(["Year_Month", cat_col]).size().reset_index(name="Listings")
            pivot_cat = trend_cat.pivot(index="Year_Month", columns=cat_col, values="Listings").fillna(0).sort_index()
            series_cat = {c: pivot_cat[c].tolist() for c in top_4_cats if c in pivot_cat.columns}
            cat_colors = {c: CHART_COLORWAY[i % len(CHART_COLORWAY)] for i, c in enumerate(series_cat.keys())}
            fig = glow_trend(pivot_cat.index.tolist(), series_cat, colors=cat_colors, height=360)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 5. TOP CITED LEGAL SECTIONS
    # ---------------------------------------------------------------------
    # Section is sparsely populated across the master dataset (most cause-list
    # rows don't carry a statutory provision), so this chart is explicitly
    # scoped to the subset of records that do have a Section on file, with
    # the coverage % surfaced up front rather than presented as if it
    # represents the full filtered dataset.
    # ---------------------------------------------------------------------
    # 4b. SECTION CITATION COVERAGE — GAUGE (standalone)
    # ---------------------------------------------------------------------
    sec_df_gauge = df.dropna(subset=["Section"])
    sec_df_gauge = sec_df_gauge[sec_df_gauge["Section"].astype(str).str.strip() != ""]
    coverage_pct_gauge = (len(sec_df_gauge) / total_cases * 100) if total_cases else 0

    with st.container(key="card_catg_gauge"):
        section_header("Section Citation Coverage")
        if total_cases:
            st.iframe(
                src=gauge_chart(
                    value=coverage_pct_gauge,
                    title="Section Citation Coverage",
                    target=85,
                ),
                height=280,
            )
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 5. TOP CITED LEGAL SECTIONS
    # ---------------------------------------------------------------------
    # Section is sparsely populated across the master dataset (most cause-list
    # rows don't carry a statutory provision), so this chart is explicitly
    # scoped to the subset of records that do have a Section on file, with
    # the coverage % surfaced up front rather than presented as if it
    # represents the full filtered dataset.
    with st.container(key="card_catg_5"):
        section_header("Top Cited Legal Sections")

        sec_df = df.dropna(subset=["Section"])
        sec_df = sec_df[sec_df["Section"].astype(str).str.strip() != ""]
        total_with_section = len(sec_df)
        coverage_pct = (total_with_section / total_cases * 100) if total_cases else 0

        # The raw Section field mixes two very different kinds of content:
        # genuine statutory citations (e.g. "{u/s 302 PPC}") and case-stage /
        # procedural annotations that aren't legal sections at all (e.g.
        # "FOR HEARING OF CASES", "FOR KATCHA PESHI", "FOR FRESH CASES").
        # The latter repeat far more often per case and were dominating this
        # "Top Cited Legal Sections" chart, crowding out actual citations.
        # Keep only rows that look like a real citation (contain "u/s",
        # "section", or "article" followed by a number, or are wrapped in
        # "{...}" — the common raw format for genuine citations here).
        _legal_pattern = r"\{.*u/?s.*\}|section\s*\d|u/s\s*\d|article\s*\d"
        is_legal_citation = sec_df["Section"].astype(str).str.contains(_legal_pattern, case=False, regex=True, na=False)
        sec_df_legal = sec_df[is_legal_citation]

        if total_with_section:
            st.caption(
                f"Based on the **{total_with_section:,} listings ({coverage_pct:.1f}% of the current selection)** "
                "that have a Section / statutory provision on file — most cause-list rows don't record one, "
                "so this is not representative of the full filtered dataset. Of those, only "
                f"**{len(sec_df_legal):,} ({len(sec_df_legal)/total_with_section*100:.1f}%)** look like genuine "
                "statutory citations (e.g. '{u/s 302 PPC}') rather than case-stage notes recorded in the same "
                "field (e.g. 'FOR HEARING OF CASES') — only those are shown below."
            )
            if len(sec_df_legal):
                top_sections = sec_df_legal["Section"].value_counts().head(10)
                fig = gradient_bar(top_sections.index.tolist(), top_sections.values.tolist(), color=COLORS["accent_secondary"], orientation="h")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No genuine statutory citations found in the current filter selection.")
        else:
            st.info("No Section data available for the current filter selection.")

    st.write("")

    # ---------------------------------------------------------------------
    # 5b. LEGAL SECTIONS BY CATEGORY — which statutory citations dominate
    # within each case category (bail applications typically cite specific
    # PPC sections, for example)
    # ---------------------------------------------------------------------
    with st.container(key="card_catg_sections_by_cat"):
        section_header("Top Legal Sections Within Each Category")
        if total_cases and len(sec_df_legal):
            st.caption(
                f"Among the same {len(sec_df_legal):,} genuine statutory citations above, broken down by "
                "which case category they most often appear in."
            )
            top_cats_for_sections = sec_df_legal["Case_Category"].value_counts().head(5).index.tolist()
            for cat in top_cats_for_sections:
                cat_sections = sec_df_legal[sec_df_legal["Case_Category"] == cat]["Section"].value_counts().head(3)
                if len(cat_sections):
                    items = " · ".join(f"**{sec}** ({cnt})" for sec, cnt in cat_sections.items())
                    st.markdown(f"**{cat}**  \n{items}")
        else:
            st.info("Not enough genuine statutory citations in the current selection for a category breakdown.")

    st.write("")

    # ---------------------------------------------------------------------
    # 6. CATEGORY INSIGHTS
    # ---------------------------------------------------------------------
    with st.container(key="card_catg_6"):
        section_header(f"{cat_label} Insights")

        if total_cases:
            top_c = df[cat_col].value_counts().idxmax()
            top_c_val = df[cat_col].value_counts().max()
            insight_pill(icon("tags", size=16, color=COLORS["accent_primary"]), f"The single most prevalent {cat_label.lower()} is <b>{top_c}</b> with {top_c_val:,} listings ({top_cat_pct:.1f}% of total).")

            top_2_share = (df[cat_col].value_counts().head(2).sum() / total_cases) * 100
            insight_pill(icon("trending-up", size=16, color=COLORS["accent_secondary"]), f"The top 2 {cat_label.lower()}s combined represent <b>{top_2_share:.1f}%</b> of the overall cause-list volume.")

            if cat_col == "Case_Category":
                uncategorized_note = df[df["Category_Group"] == "Other / Uncategorized"]
                if len(uncategorized_note):
                    pct_other = len(uncategorized_note) / total_cases * 100
                    insight_pill(icon("folder", size=16, color=COLORS["warning"]), f"<b>{pct_other:.1f}%</b> of listings in the current filter fall outside the normalized mapping's rules (bucketed as \"Other / Uncategorized\" in Normalized Group view) — mostly one-off or terse labels.")

            if len(sec_df_legal):
                top_sec = sec_df_legal["Section"].value_counts().idxmax()
                top_sec_val = sec_df_legal["Section"].value_counts().max()
                insight_pill(icon("gavel", size=16, color=COLORS["accent_tertiary"]), f"Among listings with a genuine statutory citation ({len(sec_df_legal)/total_cases*100:.1f}% of selection), <b>{top_sec}</b> is cited most often ({top_sec_val:,} listings).")
        else:
            st.info("No data for current filters.")
