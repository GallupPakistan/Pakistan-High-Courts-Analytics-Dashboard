"""
app.py

Entry point + router for the Pakistan High Courts Comparative Analytics
Dashboard. Uses a custom sidebar (components/sidebar.py — brand header +
st.button nav items tracked via st.session_state) instead of Streamlit's
st.navigation()/st.Page() API, and a plain "views/" folder (NOT named
"pages/") so Streamlit never auto-generates its own multipage nav — only
our custom sidebar controls navigation.

Every view is routed through _render_page(), which catches any error a
view raises (e.g. an empty filter combination that a chart/table wasn't
expecting) and shows a clean "No Data Found" card instead of a raw Python
traceback — while still letting Streamlit's own internal control-flow
exceptions (st.rerun / st.stop) pass through untouched.

Run with: streamlit run app.py
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(__file__))
from styles.theme import get_theme_css, COLORS  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402

st.set_page_config(
    page_title="Pakistan High Courts | Comparative Analytics",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_theme_css(), unsafe_allow_html=True)

# Hide Streamlit's built-in top-right toolbar (Share / Star / Edit / GitHub
# icons) — this is Streamlit Cloud/Community chrome, not part of the app.
st.markdown(
    """
    <style>
    [data-testid="stToolbar"] { visibility: hidden; height: 0; position: fixed; }
    [data-testid="stDecoration"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

active_page = render_sidebar()

# Exception class names that are Streamlit's own internal control flow
# (raised by st.rerun() / st.stop()) — these must always propagate and
# never be swallowed by the fallback below.
_STREAMLIT_CONTROL_FLOW_EXCEPTIONS = {"RerunException", "RerunData", "StopException"}


def _no_data_card(page_label: str):
    """Professional fallback shown instead of a raw traceback whenever a
    view can't produce output for the current filter selection."""
    st.markdown(
        f'''
        <div style="background:{COLORS["bg_card"]};border:1px solid {COLORS["border_glass"]};
        border-left:4px solid {COLORS["warning"]};border-radius:16px;padding:34px 28px;
        margin-top:14px;text-align:center;">
            <div style="font-family:'Cinzel',serif;font-size:1.2rem;font-weight:700;
            color:{COLORS["text_primary"]};margin-bottom:8px;">No Data Found</div>
            <div style="color:{COLORS["text_secondary"]};font-size:0.9rem;line-height:1.7;
            max-width:580px;margin:0 auto;">
                No matching records were found on the <b>{page_label}</b> page for the current
                filter selection. Try widening the Court, Bench / Division, Case Category, or
                Date Range filters and try again.
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def _render_page(render_fn, page_label: str):
    """Runs a view's render() function safely — any unexpected error is
    converted into a clean 'No Data Found' card instead of a raw traceback."""
    try:
        render_fn()
    except Exception as exc:
        if type(exc).__name__ in _STREAMLIT_CONTROL_FLOW_EXCEPTIONS:
            raise
        _no_data_card(page_label)


# ---------------------------------------------------------------------
# Route to the matching view. Add an entry here each time a new view is
# built in /views. Anything not yet listed shows a placeholder.
# ---------------------------------------------------------------------
if active_page == "Overview":
    from views.overview import render as render_overview
    _render_page(render_overview, "Overview")
elif active_page == "Compare Courts":
    from views.compare_courts import render as render_compare_courts
    _render_page(render_compare_courts, "Compare Courts")
elif active_page == "Court Details":
    from views.court_details import render as render_court_details
    _render_page(render_court_details, "Court Details")
elif active_page == "Bench / Division":
    from views.bench_division import render as render_bench_division
    _render_page(render_bench_division, "Bench / Division")
elif active_page == "Case Categories":
    from views.case_categories import render as render_case_categories
    _render_page(render_case_categories, "Case Categories")
elif active_page == "Trends Over Time":
    from views.trends_over_time import render as render_trends_over_time
    _render_page(render_trends_over_time, "Trends Over Time")
elif active_page == "Workload Analysis":
    from views.workload_analysis import render as render_workload_analysis
    _render_page(render_workload_analysis, "Workload Analysis")
elif active_page == "Reports":
    from views.reports import render as render_reports
    _render_page(render_reports, "Reports")
elif active_page == "Data Dictionary":
    from views.data_dictionary import render as render_data_dictionary
    _render_page(render_data_dictionary, "Data Dictionary")
elif active_page == "About":
    from views.about import render as render_about
    _render_page(render_about, "About")
else:
    st.markdown(f'<div class="dash-title" style="font-size:1.3rem;">{active_page}</div>', unsafe_allow_html=True)
    st.info(f"The **{active_page}** page hasn't been built yet — coming soon.")
