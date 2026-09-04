"""
sidebar.py

Renders the sidebar: brand header at the top (always above the nav, since
we control the render order completely), then grouped navigation buttons
with icons and section labels.

This replaces the earlier st.navigation()/st.Page() approach, which kept
failing to render the nav list reliably. Instead this uses the same
pattern as your other working dashboards: st.button() with Streamlit's
built-in icon=":material/<name>:" parameter, and st.session_state to track
which page is active. No Streamlit "pages/" folder is used at all, so
there's no automatic nav to conflict with this custom one.

Each section is (section_label_or_None, [(label, material_icon_name), ...]).
Only pages that exist in views/ will actually render content — the rest
show a "coming soon" placeholder in app.py until built.
"""

import streamlit as st
from components.icons import icon

NAV_SECTIONS = [
    (None, [
        ("Overview", "space_dashboard"),
        ("Case Search", "search"),
    ]),
    ("COMPARISON", [
        ("Compare Courts", "compare_arrows"),
        ("Court Details", "account_balance"),
    ]),
    ("ANALYSIS", [
        ("Bench / Division", "gavel"),
        ("Case Categories", "sell"),
        ("Trends Over Time", "trending_up"),
        ("Workload Analysis", "groups"),
        ("Litigant Insights", "account_balance"),
    ]),
    ("OTHERS", [
        ("Reports", "description"),
        ("Data Dictionary", "menu_book"),
        ("About", "info"),
    ]),
]


def render_sidebar() -> str:
    """Renders the sidebar and returns the currently selected page name."""

    if "active_page" not in st.session_state:
        st.session_state.active_page = "Overview"

    with st.sidebar:
        header_html = (
            '<div style="display:flex;align-items:center;gap:10px;'
            'padding:6px 4px 14px 4px;border-bottom:1px solid rgba(96,165,250,0.18);'
            'margin-bottom:12px;">'
            '<div style="width:38px;height:38px;border-radius:9px;'
            'background:linear-gradient(135deg, rgba(59,130,246,0.35), rgba(34,211,238,0.20));'
            'border:1px solid rgba(59,130,246,0.45);'
            f'display:flex;align-items:center;justify-content:center;flex-shrink:0;">{icon("landmark", size=19, color="#22D3EE")}</div>'
            '<div>'
            '<div style="font-family:\'Cinzel\',serif;font-weight:700;font-size:0.98rem;color:#F3F6FD;line-height:1.2;">PHC Analytics</div>'
            '<div style="font-size:0.68rem;color:#7C8FB8;letter-spacing:0.5px;">Pakistan High Courts</div>'
            '</div>'
            '</div>'
        )
        st.markdown(header_html, unsafe_allow_html=True)

        nav_button_css = (
            '<style>'
            'section[data-testid="stSidebar"] .stButton button{'
            'justify-content:flex-start !important;'
            'background:transparent !important;'
            'border:1px solid transparent !important;'
            'color:#A9BBDD !important;'
            'font-weight:500 !important;'
            'border-radius:10px !important;'
            'box-shadow:none !important;'
            'padding:8px 12px !important;'
            '}'
            'section[data-testid="stSidebar"] .stButton button:hover{'
            'background:rgba(59,130,246,0.10) !important;'
            'color:#F3F6FD !important;'
            '}'
            'section[data-testid="stSidebar"] .nav-active .stButton button{'
            'background:linear-gradient(90deg, rgba(59,130,246,0.30), rgba(34,211,238,0.16)) !important;'
            'border:1px solid rgba(59,130,246,0.45) !important;'
            'color:#F3F6FD !important;'
            'font-weight:600 !important;'
            '}'
            '.nav-section-label{'
            'font-size:0.68rem;font-weight:700;letter-spacing:1px;'
            'color:#5A6B8C;text-transform:uppercase;'
            'padding:14px 10px 4px 10px;'
            '}'
            '</style>'
        )
        st.markdown(nav_button_css, unsafe_allow_html=True)

        for section_label, items in NAV_SECTIONS:
            if section_label:
                st.markdown(f'<div class="nav-section-label">{section_label}</div>', unsafe_allow_html=True)
            for label, mat_icon in items:
                is_active = st.session_state.active_page == label
                wrapper_class = "nav-active" if is_active else ""
                st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
                if st.button(label, key=f"nav_{label}", width='stretch', icon=f":material/{mat_icon}:"):
                    st.session_state.active_page = label
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state.active_page
