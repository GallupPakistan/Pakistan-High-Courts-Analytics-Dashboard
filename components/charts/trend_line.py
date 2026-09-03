"""
trend_line.py

Futuristic multi-line trend chart: glowing lines (double-trace glow effect)
with soft area fill under each, instead of plain Plotly scatter lines.
"""

import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "styles"))
from theme import COLORS, get_plotly_layout_defaults  # noqa: E402


def _hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def glow_trend(x, series: dict, colors: dict = None, height=380, fill=True):
    """
    x: shared x-axis values (dates/labels)
    series: {series_name: [y_values]}
    colors: {series_name: hex_color}
    """
    fig = go.Figure()

    for name, y in series.items():
        color = (colors or {}).get(name, COLORS["accent_primary"])

        # Soft glow underlay (wider, more transparent line)
        fig.add_trace(
            go.Scatter(
                x=x, y=y, mode="lines",
                line=dict(color=_hex_to_rgba(color, 0.25), width=8),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Main crisp line + optional area fill
        fig.add_trace(
            go.Scatter(
                x=x, y=y, mode="lines",
                name=name,
                line=dict(color=color, width=2.4, shape="spline", smoothing=0.4),
                fill="tozeroy" if fill else None,
                fillcolor=_hex_to_rgba(color, 0.06) if fill else None,
                hovertemplate=f"<b>{name}</b><br>%{{x}}<br>%{{y:,}}<extra></extra>",
            )
        )

    layout = get_plotly_layout_defaults()
    layout["height"] = height
    layout["hovermode"] = "x unified"
    layout["xaxis"] = {**layout.get("xaxis", {}), "type": "category"}
    fig.update_layout(**layout)
    return fig


def sparkline(x, y, color=None, height=70):
    color = color or COLORS["accent_secondary"]
    fig = go.Figure(
        go.Scatter(
            x=x, y=y, mode="lines",
            line=dict(color=color, width=2, shape="spline", smoothing=0.5),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(color, 0.12),
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig
