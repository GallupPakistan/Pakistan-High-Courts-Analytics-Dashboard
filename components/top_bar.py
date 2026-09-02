"""
top_bar.py

Renders the shared dark navy page header banner for every page.
Even though the main content area is now light grey, the top banner
stays dark navy — matching the reference design where only the header
block retains the dark treatment, with everything below it on the light
grey surface.

All HTML is built as single concatenated strings with no leading
indentation — Streamlit's markdown renderer treats 4+ leading spaces
as a code block and prints raw tags instead of rendering them.
"""

import streamlit as st
from components.icons import icon


def render_top_bar(
    subtitle: str = "Cross-court cause list analytics for Pakistan's High Courts",
    info_chips: list[dict] = None,
    courts: list[str] = None,
):
    # Dark navy banner — explicit inline styles so it overrides the light page bg
    banner_style = (
        "background:linear-gradient(135deg,#0B1E3D 0%,#0F2447 55%,#0B2558 100%);"
        "border-radius:16px;"
        "padding:22px 28px 18px 28px;"
        "margin-bottom:24px;"
        "border:1px solid rgba(59,130,246,0.18);"
        "box-shadow:0 4px 24px rgba(11,30,61,0.18);"
    )

    if courts is None:
        courts = [
            "Lahore High Court",
            "Sindh High Court",
            "Peshawar High Court",
            "Balochistan High Court",
            "Islamabad High Court",
        ]
    courts_html = ""
    if courts:
        chip_parts = "".join(
            '<span style="background:rgba(59,130,246,0.10);border:1px solid rgba(59,130,246,0.22);'
            'border-radius:999px;padding:4px 12px;color:#CBD8F0;font-size:0.74rem;font-weight:500;">'
            f'{c}</span>'
            for c in courts
        )
        courts_html = (
            '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;padding-left:62px;">'
            + chip_parts
            + '</div>'
        )

    header_html = (
        f'<div style="{banner_style}">'
        '<div style="display:flex;align-items:center;gap:14px;">'
        '<div style="width:48px;height:48px;border-radius:14px;'
        'background:linear-gradient(135deg,rgba(59,130,246,0.30),rgba(34,211,238,0.18));'
        'border:1px solid rgba(59,130,246,0.4);'
        'display:flex;align-items:center;justify-content:center;'
        f'box-shadow:0 0 20px rgba(59,130,246,0.25);">{icon("scale", size=24, color="#3B82F6")}</div>'
        '<div>'
        '<div class="dash-title" style="font-size:1.5rem;line-height:1.2;">'
        'Pakistan High Courts Analytics Dashboard'
        '</div>'
        f'<div class="dash-subtitle">{subtitle}</div>'
        '</div>'
        '</div>'
        f'{courts_html}'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    if info_chips:
        chip_parts = []
        for chip in info_chips:
            chip_html = (
                '<div style="display:flex;align-items:center;gap:6px;'
                'background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.18);'
                'border-radius:999px;padding:6px 14px;">'
                f'{icon(chip.get("icon", "info"), size=14, color="#22D3EE")}'
                f'<span style="color:#A9BBDD;font-size:0.78rem;">{chip["label"]}</span>'
                f'<span style="color:#F3F6FD;font-size:0.78rem;font-weight:600;">{chip["value"]}</span>'
                '</div>'
            )
            chip_parts.append(chip_html)
        chips_row = (
            '<div style="display:flex;gap:10px;flex-wrap:wrap;padding-bottom:10px;">'
            + "".join(chip_parts)
            + '</div>'
        )
        st.markdown(chips_row, unsafe_allow_html=True)