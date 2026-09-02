"""
donut_chart.py

A "futuristic" radial distribution chart — replaces the generic flat Plotly
donut. Ring built from a Pie trace with a large hole, plus a thin accent
outline ring and a glass center readout.

Updated for the light theme:
  - Pie slice separator uses white (#FFFFFF, the card bg) instead of old dark bg
  - Center annotation text uses light-theme text colours (dark on white card)
  - radial_legend_html() uses dark text colours on the white card surface
"""

import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "styles"))
from theme import COLORS, CHART_COLORWAY, FONT_DISPLAY, FONT_BODY  # noqa: E402


def futuristic_radial(labels, values, center_label="Total", center_value=None, height=300):
    total = sum(values)
    if center_value is None:
        center_value = f"{total:,}"

    colors = (CHART_COLORWAY * (len(labels) // len(CHART_COLORWAY) + 1))[: len(labels)]

    fig = go.Figure()

    # Main donut ring
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.72,
            marker=dict(
                colors=colors,
                line=dict(color="#FFFFFF", width=3),   # white separator line (card bg)
            ),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>",
            sort=False,
            rotation=90,
            showlegend=False,
        )
    )

    # Thin accent glow outline ring
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.86,
            marker=dict(
                colors=["rgba(0,0,0,0)"] * len(labels),
                line=dict(color=COLORS["accent_secondary"], width=1),
            ),
            textinfo="none",
            hoverinfo="skip",
            sort=False,
            rotation=90,
            showlegend=False,
        )
    )

    fig.update_layout(
        height=height,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        annotations=[
            dict(
                text=(
                    f"<span style='font-family:{FONT_DISPLAY};font-size:22px;"
                    f"color:{COLORS['text_primary']};font-weight:700;'>{center_value}</span>"
                    f"<br><span style='font-family:{FONT_BODY};font-size:10px;"
                    f"color:{COLORS['text_secondary']};letter-spacing:1px;'>{center_label.upper()}</span>"
                ),
                x=0.5, y=0.5,
                showarrow=False,
                align="center",
                font=dict(color=COLORS["text_primary"]),
            )
        ],
    )
    return fig


def radial_legend_html(labels, values, colors=None, max_label_len=28) -> str:
    """Compact custom legend (single-line HTML per row, zero leading indentation).
    Uses dark text colours for the light card surface."""
    total  = sum(values) or 1
    colors = colors or (CHART_COLORWAY * (len(labels) // len(CHART_COLORWAY) + 1))[: len(labels)]

    rows = []
    for label, value, color in zip(labels, values, colors):
        pct          = value / total * 100
        display_label = (label[:max_label_len].rstrip() + "…") if len(label) > max_label_len else label
        row = (
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:6px 0;border-bottom:1px solid {COLORS["border_glass"]};" title="{label}">'
            f'<div style="display:flex;align-items:center;gap:8px;min-width:0;">'
            f'<span style="width:9px;height:9px;border-radius:50%;background:{color};'
            f'display:inline-block;flex-shrink:0;"></span>'
            f'<span style="color:{COLORS["text_secondary"]};font-size:0.8rem;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;">{display_label}</span>'
            f'</div>'
            f'<span style="color:{COLORS["text_primary"]};font-weight:600;font-size:0.8rem;'
            f'flex-shrink:0;padding-left:8px;">{pct:.1f}%</span>'
            f'</div>'
        )
        rows.append(row)

    return f'<div style="padding-top:4px;">{"".join(rows)}</div>'
