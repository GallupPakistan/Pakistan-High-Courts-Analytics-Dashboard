"""
kpi_cards.py

Renders KPI cards for the light-theme dashboard.

LIGHT THEME CHANGES:
  - Icon badge is a soft pastel-tinted rounded square (not a bold dark gradient).
  - Each badge background is inferred from the icon's accent colour by mapping
    to one of the pre-defined badge_* tint tokens in COLORS.
  - min-height on .kpi-card is enforced via CSS so all cards in a row are
    the same height regardless of content length.

IMPORTANT: every HTML string is built as a single concatenated line with
NO leading whitespace — Streamlit's markdown renderer treats 4+ leading
spaces as a code block and would print raw tags instead of rendering them.
"""

import streamlit as st
from styles.theme import COLORS


# Maps known accent hex colours → their pastel badge background token
_BADGE_TINT_MAP = {
    COLORS["accent_primary"]:   COLORS["badge_blue"],
    COLORS["accent_secondary"]: COLORS["badge_cyan"],
    COLORS["accent_tertiary"]:  COLORS["badge_indigo"],
    COLORS["warning"]:          COLORS["badge_amber"],
    COLORS["success"]:          COLORS["badge_green"],
    COLORS["danger"]:           COLORS["badge_rose"],
}

_DEFAULT_BADGE_BG = COLORS["badge_blue"]


def _badge_bg(icon_str: str) -> str:
    """Extract badge background tint from the icon HTML (which embeds the stroke color)."""
    for hex_col, tint in _BADGE_TINT_MAP.items():
        if hex_col.lower() in icon_str.lower():
            return tint
    return _DEFAULT_BADGE_BG


def render_kpi_row(kpis: list[dict]):
    """
    kpis: list of dicts, each with:
        icon      (str) — SVG/HTML from components/icons.icon()
        label     (str)
        value     (str, already formatted e.g. "339,307")
        sub       (str, optional small caption under the value)
        delta     (str, optional e.g. "+18.6%")
        delta_dir ("up" | "down", optional)
    """
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        icon_html = kpi.get("icon", "")
        badge_bg  = _badge_bg(icon_html)

        delta_html = ""
        if kpi.get("delta"):
            cls   = "kpi-delta-up" if kpi.get("delta_dir", "up") == "up" else "kpi-delta-down"
            arrow = "▲" if kpi.get("delta_dir", "up") == "up" else "▼"
            delta_html = f'<div class="{cls}">{arrow} {kpi["delta"]}</div>'

        sub_html = f'<div class="kpi-sub">{kpi["sub"]}</div>' if kpi.get("sub") else ""

        html = (
            f'<div class="kpi-card">'
            f'<div class="kpi-icon" style="background:{badge_bg};">{icon_html}</div>'
            f'<div class="kpi-label">{kpi["label"]}</div>'
            f'<div class="kpi-value">{kpi["value"]}</div>'
            f'{delta_html}{sub_html}'
            f'</div>'
        )
        with col:
            st.markdown(html, unsafe_allow_html=True)


def section_header(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def insight_pill(icon: str, text_html: str):
    html = f'<div class="insight-pill"><span>{icon}</span><span>{text_html}</span></div>'
    st.markdown(html, unsafe_allow_html=True)


def simple_kpi_card(label: str, value: str, sub: str = ""):
    """Standalone KPI card (used outside render_kpi_row, e.g. workload stats).
    No icon badge on this variant — keeps it compact for use in 3-column rows."""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    html = (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{sub_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)