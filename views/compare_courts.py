"""
compare_courts.py — Side-by-side comparison + head-to-head two-court panel.
Uses st.container(key="card_cc_N") for card sections.
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from styles.theme import COLORS, COURT_COLORS  # noqa: E402
from utils.data_loader import load_master_data, apply_filters, COURTS_ORDER  # noqa: E402
from utils.data_quality import find_coverage_gaps  # noqa: E402
from components.kpi_cards import render_kpi_row, section_header, insight_pill, simple_kpi_card  # noqa: E402
from components.charts.bar_chart import gradient_bar, grouped_bar  # noqa: E402
from components.charts.trend_line import glow_trend  # noqa: E402
from components.top_bar import render_top_bar  # noqa: E402
from components.icons import icon  # noqa: E402


def _court_kpi_col(col, court_name: str, cdf: pd.DataFrame, total_all: int, card_key: str, active_judges: int, cat_col: str = "Category_Group", cat_label: str = "Category Group"):
    """Render a compact metrics stack for one court inside the given column."""
    with col:
        with st.container(key=card_key):
            court_color = COURT_COLORS.get(court_name, COLORS["accent_primary"])
            header_html = (
                f'<div style="background:{court_color};border-radius:10px;'
                f'padding:9px 14px;margin-bottom:14px;text-align:center;">'
                f'<span style="color:#FFFFFF;font-family:\'Cinzel\',serif;font-weight:700;'
                f'font-size:0.9rem;">{court_name} High Court</span></div>'
            )
            st.markdown(header_html, unsafe_allow_html=True)

            c_total    = len(cdf)
            c_pct      = (c_total / total_all * 100) if total_all else 0
            metrics    = [
                ("Total Listings",  f"{c_total:,}",                f"{c_pct:.1f}% of selection"),
                ("Active Judges",   f"{active_judges:,}",  "Distinct on record"),
                ("Bench Locations", f"{cdf['Bench_Location'].nunique():,}", "Seats / divisions"),
                (f"Top {cat_label}", cdf[cat_col].value_counts().idxmax() if c_total else "N/A", "Most-listed"),
                ("Busiest Bench",   cdf["Bench_Location"].value_counts().idxmax() if cdf["Bench_Location"].nunique() else "N/A", "Highest-volume seat"),
            ]
            for label, value, sub in metrics:
                row_html = (
                    f'<div style="padding:7px 0;border-bottom:1px solid {COLORS["border_glass"]};">'
                    f'<div style="font-size:0.67rem;text-transform:uppercase;letter-spacing:0.8px;'
                    f'color:{COLORS["text_secondary"]};font-weight:600;">{label}</div>'
                    f'<div style="font-family:\'Cinzel\',serif;font-size:1.05rem;font-weight:700;'
                    f'color:{COLORS["text_primary"]};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{value}</div>'
                    f'<div style="font-size:0.72rem;color:{COLORS["text_muted"]};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{sub}</div>'
                    f'</div>'
                )
                st.markdown(row_html, unsafe_allow_html=True)


def render():
    render_top_bar(subtitle="Dual-court head-to-head comparison & full multi-court analytics")

    df_all  = load_master_data()

    st.write("")

    # ==========================================================================
    # SECTION A — HEAD-TO-HEAD TWO-COURT COMPARISON  (moved to top)
    # ==========================================================================
    with st.container(key="card_cc_h2h_intro"):
        section_header("Head-to-Head Court Comparison")
        st.markdown(
            f'<div style="color:{COLORS["text_secondary"]};font-size:0.84rem;margin-bottom:12px;">'
            'Select any two courts to compare directly — KPIs, shared categories, and monthly trends.</div>',
            unsafe_allow_html=True
        )
        # Always offer all 5 courts here, independent of the active Date filter —
        # otherwise a narrow filter shrinks the option list and both selectors
        # collapse onto the same court.
        available_courts = COURTS_ORDER

        if not available_courts:
            st.info("No court data is available for the current filter selection.")
            return

        if "h2h_a" not in st.session_state:
            st.session_state["h2h_a"] = available_courts[1] if len(available_courts) > 1 else available_courts[0]
        if "h2h_b" not in st.session_state:
            st.session_state["h2h_b"] = available_courts[0]

        sel_col1, sel_col2 = st.columns(2)
        with sel_col1:
            court_a = st.selectbox("Court A", available_courts, key="h2h_a")
        with sel_col2:
            court_b = st.selectbox("Court B", available_courts, key="h2h_b")

        # Never allow both selectors to land on the same court — auto-switch
        # Court B to the next available different court and rerun immediately,
        # so the two panels never silently show identical data.
        if court_a == court_b:
            alt = next((c for c in available_courts if c != court_a), court_a)
            st.session_state["h2h_b"] = alt
            st.rerun()

        # Date Range control (moved here from the old top filter bar).
        min_date = df_all["Hearing_Date"].min()
        max_date = df_all["Hearing_Date"].max()
        date_range = st.date_input(
            "Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date,
            key="cmp_dates"
        )
        if not (isinstance(date_range, tuple) and len(date_range) == 2):
            date_range = (min_date, max_date)

        fair_mode = st.toggle(
            "Fair comparison — match period to both courts' overlap",
            value=False,
            key="cmp_fair_mode",
            help=(
                "When on, both courts are restricted to only the months where "
                "BOTH have recorded data, computed dynamically for whichever two "
                "courts are selected above — so 'X% more' claims aren't skewed by "
                "one court simply having a longer scrape history than the other."
            ),
        )

    df = apply_filters(df_all, date_range=date_range)

    # Explode combined-bench Judge_List ONCE for this render and reuse it
    # everywhere below — avoids repeatedly exploding a 300k+-row dataframe
    # in a per-court loop (was happening 5+ times per render before).
    df_jx = df.explode("Judge_List")
    df_jx["Judge_List"] = df_jx["Judge_List"].replace("", pd.NA)

    st.write("")

    # Every category comparison on this page is cross-court by definition, and
    # each court records Case_Category in its own free-text format (the same
    # subject matter — e.g. banking litigation — can appear as dozens of raw
    # strings). So category breakdowns here always use the normalized
    # Category_Group (see utils/category_normalizer.py) rather than the raw
    # column, unless the user opts into raw detail.
    cat_mode = st.radio(
        "Category comparisons use:",
        ["Normalized Group (recommended)", "Detailed Raw Category"],
        key="cmp_cat_mode",
        horizontal=True,
    )
    cat_col = "Category_Group" if cat_mode.startswith("Normalized") else "Case_Category"
    cat_label = "Category Group" if cat_col == "Category_Group" else "Raw Category"

    st.write("")

    df_a = df[df["Court"] == court_a]
    df_b = df[df["Court"] == court_b]

    fair_window_note = None
    if fair_mode:
        months_a = set(df_a["Year_Month"].dropna())
        months_b = set(df_b["Year_Month"].dropna())
        overlap_months = sorted(months_a & months_b)
        if overlap_months:
            df_a = df_a[df_a["Year_Month"].isin(overlap_months)]
            df_b = df_b[df_b["Year_Month"].isin(overlap_months)]
            fair_window_note = f"{overlap_months[0]} to {overlap_months[-1]}"
        else:
            st.warning(
                f"⚠️ **{court_a} and {court_b} have no overlapping months** in the current "
                "date range — fair comparison isn't possible for this pair. Showing no data "
                "below; turn off fair comparison to see the full, uneven-coverage figures."
            )
            df_a = df_a.iloc[0:0]
            df_b = df_b.iloc[0:0]

    if fair_window_note:
        st.info(
            f"✅ **Fair comparison active** — both courts restricted to their shared coverage "
            f"window (**{fair_window_note}**), so the figures below compare like-for-like periods."
        )
    else:
        h2h_gaps = find_coverage_gaps(df[df["Court"].isin([court_a, court_b])], [court_a, court_b])
        if h2h_gaps:
            st.warning(
                f"⚠️ **{court_a} and {court_b} don't have the same data coverage window** — "
                "the volume difference and trend below partly reflect *when each court's "
                "listings were scraped*, not only real case-volume differences:\n\n"
                + "\n".join(f"- {g}" for g in h2h_gaps)
            )

    total_sel = len(df)
    judges_a = df_a.explode("Judge_List")["Judge_List"].replace("", pd.NA).nunique()
    judges_b = df_b.explode("Judge_List")["Judge_List"].replace("", pd.NA).nunique()

    # Mirrored KPI columns
    ka, kb = st.columns(2)
    if len(df_a):
        _court_kpi_col(ka, court_a, df_a, total_sel, "card_cc_h2h_a", judges_a, cat_col=cat_col, cat_label=cat_label)
    else:
        with ka:
            st.info(f"No data for {court_a} in the current filter period.")
    if len(df_b):
        _court_kpi_col(kb, court_b, df_b, total_sel, "card_cc_h2h_b", judges_b, cat_col=cat_col, cat_label=cat_label)
    else:
        with kb:
            st.info(f"No data for {court_b} in the current filter period.")

    st.write("")

    # Shared category bar + trend (only when both courts have data)
    if len(df_a) and len(df_b):
        shared_cats_df = (
            pd.concat([
                df_a[cat_col].value_counts().head(8).rename("a"),
                df_b[cat_col].value_counts().head(8).rename("b"),
            ], axis=1).fillna(0)
        )
        shared_cats_df["total"] = shared_cats_df["a"] + shared_cats_df["b"]
        top_cats = shared_cats_df.sort_values("total", ascending=False).head(6).index.tolist()

        h2h_c1, h2h_c2 = st.columns(2)
        with h2h_c1:
            with st.container(key="card_cc_h2h_bar"):
                section_header(f"Top Shared {cat_label}s — {court_a} vs {court_b}")
                series_h2h = {
                    court_a: [int(df_a[df_a[cat_col] == c].shape[0]) for c in top_cats],
                    court_b: [int(df_b[df_b[cat_col] == c].shape[0]) for c in top_cats],
                }
                fig = grouped_bar(top_cats, series_h2h,
                                  colors={court_a: COURT_COLORS[court_a], court_b: COURT_COLORS[court_b]},
                                  height=320)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

        with h2h_c2:
            with st.container(key="card_cc_h2h_trend"):
                section_header(f"Monthly Trend — {court_a} vs {court_b}")
                df_h2h  = pd.concat([df_a, df_b]).dropna(subset=["Year_Month"])
                trend_h2h = df_h2h.groupby(["Year_Month", "Court"]).size().reset_index(name="Cases")
                pivot_h2h = trend_h2h.pivot(index="Year_Month", columns="Court", values="Cases").fillna(0).sort_index()
                series_t  = {c: pivot_h2h[c].tolist() for c in [court_a, court_b] if c in pivot_h2h.columns}
                fig = glow_trend(pivot_h2h.index.tolist(), series_t,
                                 colors={court_a: COURT_COLORS[court_a], court_b: COURT_COLORS[court_b]},
                                 height=320)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

        # Delta insight
        with st.container(key="card_cc_h2h_delta"):
            vol_a, vol_b = len(df_a), len(df_b)
            if vol_a > 0 and vol_b > 0:
                if vol_a >= vol_b:
                    bigger_court, smaller_court, bigger_vol, smaller_vol = court_a, court_b, vol_a, vol_b
                else:
                    bigger_court, smaller_court, bigger_vol, smaller_vol = court_b, court_a, vol_b, vol_a
                pct_diff = (bigger_vol - smaller_vol) / smaller_vol * 100
                insight_pill(
                    icon("trending-up", size=16, color=COLORS["accent_primary"]),
                    f"<b>{bigger_court} High Court</b> has <b>{pct_diff:.1f}% more</b> listings than "
                    f"<b>{smaller_court} High Court</b> ({bigger_vol:,} vs {smaller_vol:,})."
                )

        st.write("")

    # ==========================================================================
    # SECTION B — ALL-5-COURTS OVERVIEW
    # ==========================================================================
    with st.container(key="card_cc_b_intro"):
        section_header("All Courts Overview")
        st.markdown(
            f'<div style="color:{COLORS["text_secondary"]};font-size:0.84rem;">'
            'National aggregate across all 5 courts in the selected date range.</div>',
            unsafe_allow_html=True
        )

    st.write("")

    # Same toggle as the head-to-head panel above, but the "fair" window here
    # is necessarily different: it's the single window where ALL 5 courts
    # have data simultaneously, which is usually much narrower than any one
    # pair's overlap (e.g. two courts might share 7 months while all five
    # together only share 2) — so it's computed and labeled separately.
    df_b_section = df
    if fair_mode:
        courts_here = [c for c in COURTS_ORDER if c in df["Court"].unique()]
        starts = df.groupby("Court")["Year_Month"].min()
        ends = df.groupby("Court")["Year_Month"].max()
        relevant = [c for c in courts_here if c in starts.index]
        if relevant:
            common_start = max(starts[c] for c in relevant)
            common_end = min(ends[c] for c in relevant)
            if common_start <= common_end:
                df_b_section = df[(df["Year_Month"] >= common_start) & (df["Year_Month"] <= common_end)]
                st.info(
                    f"✅ **Fair comparison active** — all 5 courts restricted to their shared "
                    f"coverage window (**{common_start} to {common_end}**). This window is "
                    "narrower than the pairwise one above because it must fit every court "
                    "at once, not just the two selected in the head-to-head panel."
                )
            else:
                st.warning("⚠️ No single window has data for all 5 courts — showing full data instead.")
        df_jx_section = df_b_section.explode("Judge_List")
        df_jx_section["Judge_List"] = df_jx_section["Judge_List"].replace("", pd.NA)
    else:
        df_jx_section = df_jx

    total_cases = len(df_b_section)
    active_courts = df_b_section["Court"].nunique() if total_cases else 0
    top_court = df_b_section["Court"].value_counts().idxmax() if total_cases else "N/A"
    top_court_cases = df_b_section["Court"].value_counts().max() if total_cases else 0
    avg_per_court = total_cases / active_courts if active_courts else 0

    # From here on, every remaining chart/table in this section should use
    # the (possibly fair_mode-restricted) data — reassign df/df_jx once so
    # the rest of Section B below needs no further changes.
    df = df_b_section
    df_jx = df_jx_section

    render_kpi_row([
        {"icon": icon("landmark",    size=20, color=COLORS["accent_primary"]),   "label": "Active Courts",   "value": f"{active_courts}",          "sub": "In selection"},
        {"icon": icon("folder",      size=20, color=COLORS["accent_secondary"]), "label": "Total Listings",  "value": f"{total_cases:,}",          "sub": f"Avg {avg_per_court:,.0f} / court"},
        {"icon": icon("trending-up", size=20, color=COLORS["accent_tertiary"]),  "label": "Largest Volume",  "value": f"{top_court}",              "sub": f"{top_court_cases:,} listings"},
        {"icon": icon("gavel",       size=20, color=COLORS["warning"]),           "label": "Total Judges",    "value": f"{df_jx_section['Judge_List'].nunique():,}" if total_cases else "0", "sub": "Across courts"},
        {"icon": icon("tags",        size=20, color=COLORS["success"]),           "label": f"{cat_label}s",   "value": f"{df_b_section[cat_col].nunique():,}" if total_cases else "0", "sub": "Listed"},
    ])

    st.write("")

    # Volume comparison toggle
    with st.container(key="card_cc_vol"):
        hc = st.columns([3, 1])
        with hc[0]:
            section_header("Case Volume Comparison — All Courts")
        with hc[1]:
            norm_mode = st.radio("", ["Raw Count", "% Share"], horizontal=True, key="cmp_norm_mode")
        if total_cases:
            vol_df = df["Court"].value_counts().reindex(COURTS_ORDER).fillna(0)
            if norm_mode == "% Share":
                display_vals = (vol_df / total_cases * 100).tolist()
                fig = gradient_bar(vol_df.index.tolist(), display_vals, color=COLORS["accent_primary"], value_suffix="%")
            else:
                fig = gradient_bar(vol_df.index.tolist(), vol_df.values.tolist(), color=COLORS["accent_primary"])
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for the current filter selection.")

    st.write("")

    # Category mix & bench type
    c1, c2 = st.columns(2)
    with c1:
        with st.container(key="card_cc_catmix"):
            section_header(f"Top 5 {cat_label} Mix by Court")
            if total_cases:
                top_5_cats = df[cat_col].value_counts().head(5).index.tolist()
                cat_court  = df[df[cat_col].isin(top_5_cats)].groupby([cat_col, "Court"]).size().unstack(fill_value=0)
                series = {}
                for court in COURTS_ORDER:
                    if court in cat_court.columns:
                        ct = df[df["Court"] == court].shape[0]
                        series[court] = ((cat_court[court] / ct * 100).tolist() if (norm_mode == "% Share" and ct > 0) else cat_court[court].tolist())
                fig = grouped_bar(top_5_cats, series, colors=COURT_COLORS, height=320)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for the current filter selection.")

    with c2:
        with st.container(key="card_cc_benchmix"):
            section_header("Bench Type Distribution by Court")
            if total_cases:
                top_bt     = df["Bench_Type_Group"].value_counts().head(4).index.tolist()
                bench_court = df[df["Bench_Type_Group"].isin(top_bt)].groupby(["Bench_Type_Group", "Court"]).size().unstack(fill_value=0)
                series = {}
                for court in COURTS_ORDER:
                    if court in bench_court.columns:
                        ct = df[df["Court"] == court].shape[0]
                        series[court] = ((bench_court[court] / ct * 100).tolist() if (norm_mode == "% Share" and ct > 0) else bench_court[court].tolist())
                fig = grouped_bar(top_bt, series, colors=COURT_COLORS, height=320)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.info("No data for the current filter selection.")

    st.write("")

    # Judicial capacity table
    with st.container(key="card_cc_jcap"):
        section_header("Judicial Capacity & Average Listings per Court")
        if total_cases:
            court_summary = []
            for court in COURTS_ORDER:
                cdf = df[df["Court"] == court]
                if len(cdf):
                    j   = df_jx.loc[df_jx["Court"] == court, "Judge_List"].nunique()
                    avg = len(cdf) / j if j else 0
                    court_summary.append({
                        "Court": court, "Total Listings": len(cdf),
                        "Share": f"{len(cdf)/total_cases*100:.1f}%",
                        "Judges": j, "Avg / Judge": f"{avg:,.0f}",
                        "Benches": cdf["Bench_Location"].nunique(),
                        cat_label + "s": cdf[cat_col].nunique(),
                    })
            st.dataframe(pd.DataFrame(court_summary), width='stretch', hide_index=True)
        else:
            st.info("No data for the current filter selection.")

    st.write("")

    # All-5 monthly trend
    with st.container(key="card_cc_trend"):
        section_header("Comparative Listing Trends — All Courts")
        if total_cases:
            trend_df = df.dropna(subset=["Year_Month"]).groupby(["Year_Month", "Court"]).size().reset_index(name="Cases")
            pivot    = trend_df.pivot(index="Year_Month", columns="Court", values="Cases").fillna(0).sort_index()
            series   = {c: pivot[c].tolist() for c in COURTS_ORDER if c in pivot.columns}
            fig      = glow_trend(pivot.index.tolist(), series, colors=COURT_COLORS, height=340)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("No data for the current filter selection.")

    st.write("")

    # Insights
    with st.container(key="card_cc_insights"):
        section_header("Comparative Insights")
        if total_cases:
            vol_counts = df["Court"].value_counts()
            if len(vol_counts) > 1:
                mx, mn = vol_counts.idxmax(), vol_counts.idxmin()
                ratio  = vol_counts.max() / vol_counts.min() if vol_counts.min() > 0 else 0
                insight_pill(icon("trending-up", size=16, color=COLORS["accent_primary"]),
                             f"Volume gap: <b>{mx}</b> has {ratio:.1f}x more listings than <b>{mn}</b>.")
            j_loads = {c: len(df[df["Court"]==c]) / max(df_jx.loc[df_jx["Court"]==c, "Judge_List"].nunique(), 1)
                       for c in COURTS_ORDER if len(df[df["Court"]==c]) > 0}
            if j_loads:
                hj = max(j_loads, key=j_loads.get)
                insight_pill(icon("gavel", size=16, color=COLORS["warning"]),
                             f"Highest judicial density: <b>{hj} High Court</b> ({j_loads[hj]:,.0f} listings / judge).")
        else:
            st.info("No data for the current filter selection.")
