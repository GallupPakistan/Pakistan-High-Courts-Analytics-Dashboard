"""
gauge_chart.py

Half-donut gauge chart: colored zones (red/amber/green), a needle pointing
to the current value, an optional target marker, and a big percentage
readout — styled after the classic "Customer Satisfaction Score" gauge
layout. Pure inline SVG so it matches the dashboard's existing
icon/theme system with no external chart library.

Usage:
    from components.charts.gauge_chart import gauge_chart
    html = gauge_chart(value=71, title="Section Citation Coverage", target=85)
    st.components.v1.html(html, height=300, scrolling=False)
"""

import math
from styles.theme import COLORS


def _pt(cx, cy, r, angle_deg):
    rad = math.radians(angle_deg)
    return cx + r * math.cos(rad), cy - r * math.sin(rad)


def _zone_path(cx, cy, r_outer, r_inner, start_pct, end_pct):
    """Zone spans a percent range of the 0-100 gauge, mapped onto the
    180deg semicircle (180deg = 0%, 0deg = 100%, sweeping left-to-right)."""
    start_angle = 180 - (start_pct / 100.0) * 180
    end_angle = 180 - (end_pct / 100.0) * 180
    x1o, y1o = _pt(cx, cy, r_outer, start_angle)
    x2o, y2o = _pt(cx, cy, r_outer, end_angle)
    x1i, y1i = _pt(cx, cy, r_inner, end_angle)
    x2i, y2i = _pt(cx, cy, r_inner, start_angle)
    large_arc = 1 if (start_angle - end_angle) > 180 else 0
    return (
        f"M {x1o:.2f} {y1o:.2f} "
        f"A {r_outer} {r_outer} 0 {large_arc} 1 {x2o:.2f} {y2o:.2f} "
        f"L {x1i:.2f} {y1i:.2f} "
        f"A {r_inner} {r_inner} 0 {large_arc} 0 {x2i:.2f} {y2i:.2f} Z"
    )


def _font_family():
    return "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def gauge_chart(value, title="", target=None, zones=None, value_suffix="%",
                 low_color=None, mid_color=None, high_color=None):
    """
    value: current value, 0-100.
    title: chart title shown above the gauge.
    target: optional 0-100 marker shown as a red arrow + "Target" label.
    zones: optional list of (start_pct, end_pct) tuples; defaults to
        three even bands (0-50 red, 50-75 amber, 75-100 green).
    """
    value = max(0, min(100, value))
    low = low_color or COLORS["danger"]
    mid = mid_color or COLORS["warning"]
    high = high_color or COLORS["success"]

    if zones is None:
        zones = [(0, 50, low), (50, 75, mid), (75, 100, high)]
    else:
        # user passed (start,end) pairs only -> attach default colors cyclically
        palette = [low, mid, high]
        zones = [(s, e, palette[i % len(palette)]) for i, (s, e) in enumerate(zones)]

    cx, cy = 170, 185
    r_outer, r_inner = 122, 78

    zone_paths = "".join(
        f'<path d="{_zone_path(cx, cy, r_outer, r_inner, s, e)}" fill="{c}"/>'
        for s, e, c in zones
    )

    # Tick labels at 0/25/50/75/100
    ticks_html = ""
    for pct in (0, 25, 50, 75, 100):
        angle = 180 - (pct / 100.0) * 180
        tx, ty = _pt(cx, cy, r_outer + 22, angle)
        ticks_html += (
            f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="13" fill="{COLORS["text_muted"]}" '
            f'font-family="{_font_family()}">{pct}%</text>'
        )
        mx1, my1 = _pt(cx, cy, r_outer, angle)
        mx2, my2 = _pt(cx, cy, r_outer + 8, angle)
        ticks_html += f'<line x1="{mx1:.1f}" y1="{my1:.1f}" x2="{mx2:.1f}" y2="{my2:.1f}" stroke="{COLORS["text_muted"]}" stroke-width="2"/>'

    # Needle
    needle_angle = 180 - (value / 100.0) * 180
    ntx, nty = _pt(cx, cy, r_inner - 14, needle_angle)
    perp1 = needle_angle + 90
    perp2 = needle_angle - 90
    bx1, by1 = _pt(cx, cy, 7, perp1)
    bx2, by2 = _pt(cx, cy, 7, perp2)
    needle_html = (
        f'<path d="M {bx1:.1f} {by1:.1f} L {ntx:.1f} {nty:.1f} L {bx2:.1f} {by2:.1f} Z" '
        f'fill="#101828"/>'
        f'<circle cx="{cx}" cy="{cy}" r="9" fill="#101828"/>'
    )

    # Target marker
    target_html = ""
    if target is not None:
        t_angle = 180 - (target / 100.0) * 180
        tip_x, tip_y = _pt(cx, cy, r_outer - 4, t_angle)
        tail_x, tail_y = _pt(cx, cy, r_inner + 10, t_angle)
        label_x, label_y = _pt(cx, cy, r_outer + 26, t_angle)
        target_html = (
            f'<line x1="{tail_x:.1f}" y1="{tail_y:.1f}" x2="{tip_x:.1f}" y2="{tip_y:.1f}" '
            f'stroke="{COLORS["danger"]}" stroke-width="2"/>'
            f'<circle cx="{tip_x:.1f}" cy="{tip_y:.1f}" r="5" fill="{COLORS["danger"]}"/>'
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" font-size="12" '
            f'font-weight="700" fill="{COLORS["danger"]}" font-family="{_font_family()}">Target</text>'
        )

    svg = f"""
<svg viewBox="0 0 340 260" width="100%" height="270" style="display:block;margin:0 auto;overflow:visible;">
  {f'<text x="170" y="20" text-anchor="middle" font-size="17" font-weight="700" fill="{COLORS["text_primary"]}" font-family="{_font_family()}">{title}</text>' if title else ''}
  <g>{zone_paths}</g>
  {ticks_html}
  {target_html}
  {needle_html}
  <text x="170" y="248" text-anchor="middle" font-size="26" font-weight="800" fill="{COLORS['text_primary']}"
        font-family="{_font_family()}">{value:.0f}{value_suffix}</text>
</svg>
"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><style>
  html,body {{ margin:0; padding:0; background:transparent; }}
  * {{ box-sizing:border-box; }}
</style></head>
<body>{svg}</body></html>"""