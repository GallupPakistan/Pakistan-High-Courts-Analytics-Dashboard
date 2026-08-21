"""
workload_analysis.py

Workload Analysis view:
1. Judicial Workload KPI row (Total judges, mean listings, max/min workload)
2. Top 15 Most Active Judges Leaderboard
3. Judge Workload Distribution Histogram / Bucket Analysis
4. Average Listings per Judge per Court
5. Advocate Activity Leaderboard (Petitioner & Respondent Advocates)
6. Case Recurrence / Listing Frequency Analysis (backlog proxy)
7. Workload Insights
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
from components.charts.bar_chart import gradient_bar  # noqa: E402
from components.charts.trend_line import glow_trend  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def _short_judge_label(raw, max_chars=28):
    """Judge index values are long combined strings like
    'Mr. Justice X | Mr. Justice Y | [ Some Block - Court N ]'.
    Keep just the first judge name and truncate it so bar-chart
    labels stay readable and leave room for the value/percentage.
    """
    name = str(raw).split("|")[0].strip()
    if len(name) > max_chars:
        name = name[: max_chars - 1].rstrip() + "…"
    return name


def _labels_with_share(index_values, counts, total, max_chars=28):
    """Build short 'Name (xx.x%)' labels for a bar chart's category axis."""
    labels = []
    for raw, cnt in zip(index_values, counts):
        short = _short_judge_label(raw, max_chars=max_chars)
        pct = (cnt / total * 100) if total else 0
        labels.append(f"{short} ({pct:.1f}%)")
    return labels


def render():
    render_top_bar(subtitle="Judicial listing distribution & legal counsel activity analytics")

    df_all = load_master_data()
    filters = render_filter_bar(df_all, key_prefix="wa")
    df = apply_filters(df_all, **filters)

    st.write("")

    # ---------------------------------------------------------------------
    # 1. JUDICIAL WORKLOAD KPI ROW
    # ---------------------------------------------------------------------
    total_cases = len(df)
    j_counts = df["Judge"].value_counts().dropna()
    total_judges = len(j_counts)
    avg_load = j_counts.mean() if total_judges else 0
    median_load = j_counts.median() if total_judges else 0
    max_load = j_counts.max() if total_judges else 0
    busiest_j = j_counts.idxmax() if total_judges else "N/A"

    render_kpi_row([
        {"icon": icon("gavel", size=20, color=COLORS["accent_primary"]), "label": "Active Judges", "value": f"{total_judges:,}", "sub": "Distinct judge names"},
        {"icon": icon("users", size=20, color=COLORS["accent_secondary"]), "label": "Avg Listings / Judge", "value": f"{avg_load:,.0f}", "sub": f"Median: {median_load:,.0f}"},
        {"icon": icon("trending-up", size=20, color=COLORS["accent_tertiary"]), "label": "Busiest Judge", "value": f"{busiest_j}", "sub": f"{max_load:,} listings"},
        {"icon": icon("folder", size=20, color=COLORS["warning"]), "label": "Petitioner Advocates", "value": f"{df['Petitioner_Advocate'].nunique():,}" if total_cases else "0", "sub": "Distinct counsel"},
        {"icon": icon("folder", size=20, color=COLORS["success"]), "label": "Respondent Advocates", "value": f"{df['Respondent_Advocate'].nunique():,}" if total_cases else "0", "sub": "Distinct counsel"},
    ])

    st.write("")

    # ---------------------------------------------------------------------
    # 2 & 3. TOP JUDGES LEADERBOARD & WORKLOAD BUCKETS
    # ---------------------------------------------------------------------
    c1, c2 = st.columns([1.3, 1])

    with c1:
        with st.container(key="card_wa_1"):
            section_header("Top 15 Judges by Total Cause-List Listings")
            if total_judges:
                top_15_j = j_counts.head(15)
                top_15_labels = _labels_with_share(top_15_j.index.tolist(), top_15_j.values.tolist(), total_cases)
                fig = gradient_bar(top_15_labels, top_15_j.values.tolist(), color=COLORS["accent_primary"], orientation="h")
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No judge data available for current filters.")

    with c2:
        with st.container(key="card_wa_2"):
            section_header("Judicial Workload Distribution Buckets")
            if total_judges:
                # Create workload tier buckets
                buckets = pd.cut(
                    j_counts,
                    bins=[0, 100, 500, 1000, 5000, 100000],
                    labels=["<100", "100-500", "501-1k", "1k-5k", ">5k"]
                ).value_counts().sort_index()
                fig = gradient_bar(buckets.index.tolist(), buckets.values.tolist(), color=COLORS["accent_secondary"])
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 3b. LEAST ACTIVE JUDGES (full width — long judge/court labels need room)
    # ---------------------------------------------------------------------
    with st.container(key="card_wa_8"):
        section_header("Bottom 10 Judges by Listing Volume")
        if total_judges >= 10:
            bottom_10_j = j_counts.tail(10).sort_values()
            bottom_10_labels = _labels_with_share(bottom_10_j.index.tolist(), bottom_10_j.values.tolist(), total_cases)
            fig = gradient_bar(bottom_10_labels, bottom_10_j.values.tolist(), color=COLORS["accent_secondary"], orientation="h")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Not enough distinct judges for a bottom-10 view.")

    st.write("")

    # ---------------------------------------------------------------------
    # 3c. TOP-JUDGE MONTHLY TREND (full width — separated from bucket above)
    # ---------------------------------------------------------------------
    with st.container(key="card_wa_9"):
        section_header("Top 5 Judges — Monthly Listing Trend")
        if total_judges:
            top_5_j = j_counts.head(5).index.tolist()
            j_trend = (
                df[df["Judge"].isin(top_5_j)]
                .dropna(subset=["Year_Month"])
                .groupby(["Year_Month", "Judge"]).size().reset_index(name="Listings")
            )
            pivot_j = j_trend.pivot(index="Year_Month", columns="Judge", values="Listings").fillna(0).sort_index()
            # Use short, de-duplicated labels for the legend instead of the
            # full combined judge/court strings (which run very long).
            short_names = {}
            for c in top_5_j:
                base = _short_judge_label(c, max_chars=30)
                name = base
                n = 2
                while name in short_names.values():
                    name = f"{base} ({n})"
                    n += 1
                short_names[c] = name
            series = {short_names[c]: pivot_j[c].tolist() for c in top_5_j if c in pivot_j.columns}
            # glow_trend colors every line the same accent_primary unless a
            # per-series color map is supplied — build one so each judge
            # gets a visually distinct line.
            palette = [
                COLORS["accent_primary"],
                COLORS["accent_secondary"],
                COLORS["accent_tertiary"],
                COLORS["warning"],
                COLORS["success"],
            ]
            trend_colors = {
                short_names[c]: palette[i % len(palette)]
                for i, c in enumerate(top_5_j) if c in pivot_j.columns
            }
            fig = glow_trend(pivot_j.index.tolist(), series, colors=trend_colors, height=420)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 4. AVERAGE LISTINGS PER JUDGE PER COURT
    # ---------------------------------------------------------------------
    with st.container(key="card_wa_3"):
        section_header("Average Judicial Listing Load by Court")

        if total_cases:
            j_court_stats = []
            for court in COURTS_ORDER:
                cdf = df[df["Court"] == court]
                if len(cdf):
                    j_cnt = cdf["Judge"].nunique()
                    total_l = len(cdf)
                    avg_l = total_l / j_cnt if j_cnt else 0
                    max_j = cdf["Judge"].value_counts().max() if j_cnt else 0
                    busiest = cdf["Judge"].value_counts().idxmax() if j_cnt else "N/A"
                    j_court_stats.append({
                        "Court": court,
                        "Active Judges": j_cnt,
                        "Total Listings": total_l,
                        "Avg Listings / Judge": f"{avg_l:,.0f}",
                        "Max Single Judge Load": f"{max_j:,}",
                        "Busiest Judge": busiest,
                    })
            st.dataframe(pd.DataFrame(j_court_stats), use_container_width=True, hide_index=True)
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 5. ADVOCATE ACTIVITY LEADERBOARDS
    # ---------------------------------------------------------------------
    c3, c4 = st.columns(2)

    with c3:
        with st.container(key="card_wa_4"):
            section_header("Top Petitioner Advocates")
            if total_cases:
                top_p_adv = df["Petitioner_Advocate"].value_counts().dropna().head(10)
                fig = gradient_bar(top_p_adv.index.tolist(), top_p_adv.values.tolist(), color=COLORS["accent_primary"], orientation="h")
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    with c4:
        with st.container(key="card_wa_5"):
            section_header("Top Respondent Advocates")
            if total_cases:
                top_r_adv = df["Respondent_Advocate"].value_counts().dropna().head(10)
                fig = gradient_bar(top_r_adv.index.tolist(), top_r_adv.values.tolist(), color=COLORS["accent_tertiary"], orientation="h")
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 6. CASE RECURRENCE / LISTING FREQUENCY ANALYSIS (backlog proxy)
    # ---------------------------------------------------------------------
    # Cause lists don't record disposal dates, so how many times the same
    # Case_No re-appears across hearing dates is the dashboard's proxy for
    # backlog / case churn (see views/about.py). This section makes that
    # metric visible instead of only stating it as a methodology note.
    case_counts = df["Case_No"].value_counts().dropna()
    total_unique_cases = len(case_counts)
    avg_listings_per_case = case_counts.mean() if total_unique_cases else 0
    repeat_cases = case_counts[case_counts > 1]
    repeat_pct = (len(repeat_cases) / total_unique_cases * 100) if total_unique_cases else 0
    heavy_repeat_cases = case_counts[case_counts >= 5]
    most_recurring_val = case_counts.max() if total_unique_cases else 0
    most_recurring_case = case_counts.idxmax() if total_unique_cases else "N/A"

    with st.container(key="card_wa_6"):
        section_header("Case Recurrence & Backlog Proxy Analysis")
        st.markdown(
            f"<div style='color:{COLORS['text_secondary']};font-size:0.84rem;margin-bottom:12px;'>"
            "How many times the same case is re-listed across hearing dates — used here as a proxy "
            "for backlog / case churn, since cause-list data doesn't include disposal status.</div>",
            unsafe_allow_html=True
        )

        if total_unique_cases:
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                simple_kpi_card("Unique Cases", f"{total_unique_cases:,}", "Distinct Case_No")
            with rc2:
                simple_kpi_card("Avg Listings / Case", f"{avg_listings_per_case:,.1f}", "Across all cases")
            with rc3:
                simple_kpi_card("Re-listed Cases", f"{repeat_pct:.1f}%", f"{len(repeat_cases):,} cases listed 2+ times")
            with rc4:
                simple_kpi_card("Most Recurring Case", f"{most_recurring_val:,} listings", most_recurring_case)

            st.write("")

            fc1, fc2 = st.columns([1, 1.2])
            with fc1:
                st.markdown(f"<div style='font-size:0.88rem;font-weight:600;color:{COLORS['text_primary']};margin-bottom:8px;'>Listing Frequency Distribution</div>", unsafe_allow_html=True)
                buckets = pd.cut(
                    case_counts,
                    bins=[0, 1, 3, 10, float("inf")],
                    labels=["1x", "2-3x", "4-10x", "10+x"]
                ).value_counts().sort_index()
                fig = gradient_bar(buckets.index.tolist(), buckets.values.tolist(), color=COLORS["accent_tertiary"])
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with fc2:
                st.markdown(f"<div style='font-size:0.88rem;font-weight:600;color:{COLORS['text_primary']};margin-bottom:8px;'>Top 10 Most Re-Listed Cases</div>", unsafe_allow_html=True)
                top_recurring = (
                    df.dropna(subset=["Case_No"])
                    .groupby("Case_No")
                    .agg(
                        Court=("Court", "first"),
                        Case_Title=("Case_Title", "first"),
                        Listings=("Case_No", "size"),
                    )
                    .reset_index()
                    .sort_values("Listings", ascending=False)
                    .head(10)
                )
                st.dataframe(top_recurring, use_container_width=True, hide_index=True)
        else:
            st.info("No data for current filters.")

    st.write("")

    # ---------------------------------------------------------------------
    # 7. WORKLOAD INSIGHTS
    # ---------------------------------------------------------------------
    with st.container(key="card_wa_7"):
        section_header("Workload & Counsel Insights")

        if total_judges:
            insight_pill(icon("gavel", size=16, color=COLORS["accent_primary"]), f"The busiest judge on record in current selection is <b>{busiest_j}</b> with {max_load:,} listed appearances.")
            insight_pill(icon("users", size=16, color=COLORS["accent_secondary"]), f"Overall mean judicial load is <b>{avg_load:,.0f} listings per judge</b>.")
        if total_unique_cases:
            insight_pill(icon("trending-up", size=16, color=COLORS["accent_tertiary"]), f"<b>{repeat_pct:.1f}%</b> of cases ({len(repeat_cases):,} of {total_unique_cases:,}) were re-listed more than once, and <b>{len(heavy_repeat_cases):,}</b> cases were listed 5 or more times — a possible backlog signal.")
        if not total_judges and not total_unique_cases:
            st.info("No data for current filters.")