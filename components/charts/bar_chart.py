"""
bar_chart.py

Futuristic bar chart: gradient-filled bars (via a manual per-bar color ramp,
not Plotly's built-in colorscale — colorscale auto-attaches a colorbar with
a title placeholder, which is what was rendering as stray "undefined" text)
with a glowing outline, instead of flat single-color Plotly bars.
"""

import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "styles"))
from theme import COLORS, CHART_COLORWAY, get_plotly_layout_defaults  # noqa: E402


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _ramp(base_hex, n, start_alpha=0.45, end_alpha=1.0):
    """Return n colors ramping from a faded to full-strength version of base_hex."""
    r, g, b = _hex_to_rgb(base_hex)
    if n <= 1:
        return [f"rgba({r},{g},{b},{end_alpha})"]
    return [
        f"rgba({r},{g},{b},{start_alpha + (end_alpha - start_alpha) * i / (n - 1):.2f})"
        for i in range(n)
    ]


def _multicolor(n, palette=None):
    """Cycle through the shared CHART_COLORWAY palette so each bar gets a
    visually distinct color, instead of one hue ramped by opacity."""
    palette = palette or CHART_COLORWAY
    return [palette[i % len(palette)] for i in range(n)]


def gradient_bar(x_labels, values, color=None, orientation="v", value_suffix="", height=340, multicolor=True):
    if multicolor:
        # Cycle the shared multi-hue palette across bars (same colors used by
        # the donut charts) instead of one hue ramped by opacity. `color` is
        # ignored for the fill in this mode; pass multicolor=False to opt a
        # chart back into the single-hue ramp.
        bar_colors = _multicolor(len(values))
        line_color = COLORS["border_glass"]
    else:
        color = color or COLORS["accent_primary"]
        bar_colors = _ramp(color, len(values))
        line_color = color

    common = dict(
        marker=dict(color=bar_colors, line=dict(color=line_color, width=1.2)),
        text=[f"{v:,.0f}{value_suffix}" for v in values],
        textposition="outside",
        textfont=dict(color=COLORS["text_primary"], size=12),
        cliponaxis=False,
    )

    if orientation == "v":
        fig = go.Figure(
            go.Bar(
                x=x_labels, y=values,
                hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>",
                **common,
            )
        )
    else:
        fig = go.Figure(
            go.Bar(
                y=x_labels, x=values, orientation="h",
                hovertemplate="<b>%{y}</b><br>%{x:,}<extra></extra>",
                **common,
            )
        )

    layout = get_plotly_layout_defaults()
    layout["height"] = height
    if orientation == "h" and values:
        layout["xaxis"] = {**layout.get("xaxis", {}), "range": [0, max(values) * 1.18]}
        layout["margin"] = {**layout.get("margin", {}), "r": 60}
    fig.update_layout(**layout)
    return fig


def grouped_bar(categories, series: dict, colors: dict = None, height=380):
    """
    categories: x-axis labels
    series: {series_name: [values]}
    colors: {series_name: color} optional, else falls back to CHART_COLORWAY
    """
    fig = go.Figure()
    for name, values in series.items():
        c = (colors or {}).get(name)
        fig.add_trace(
            go.Bar(
                name=name,
                x=categories,
                y=values,
                marker=dict(color=c, line=dict(width=0)),
                hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
            )
        )
    layout = get_plotly_layout_defaults()
    layout["height"] = height
    layout["barmode"] = "group"
    layout["bargap"] = 0.25
    layout["bargroupgap"] = 0.08
    layout["xaxis"] = {**layout.get("xaxis", {}), "tickangle": -20, "automargin": True}
    fig.update_layout(**layout)
    return fig
