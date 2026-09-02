"""
lightbulb_chart.py

"Category Details" lightbulb visualization: a center donut chart shaped
like a lightbulb (idea/insight framing) surrounded by up to 4 category
detail cards, each carrying an icon, percentage share, and a short
description. Built as pure inline SVG + HTML so it matches the dashboard's
existing icon/theme system with no external chart library involved.

Usage:
    from components.charts.lightbulb_chart import lightbulb_category_chart
    st.markdown(
        lightbulb_category_chart(
            categories=[
                {"label": "Civil Appeals", "value": 43, "count": 12500,
                 "desc": "Largest category, dominated by property disputes.",
                 "icon": "gavel"},
                {"label": "Banking & Finance", "value": 28, "count": 8100,
                 "desc": "Steady growth over the last 3 years.", "icon": "landmark"},
                {"label": "Family Law", "value": 20, "count": 5800,
                 "desc": "Concentrated in Lahore and Sindh.", "icon": "users"},
                {"label": "Tax & Revenue", "value": 9, "count": 2600,
                 "desc": "Smallest share, mostly single-bench.", "icon": "file-bar-chart"},
            ],
            center_label="Total Cases",
            center_value="29,000",
        ),
        unsafe_allow_html=True,
    )
"""

from styles.theme import COLORS, CHART_COLORWAY
from components.icons import icon as _icon


def _donut_arcs(values, colors, cx=100, cy=100, r_outer=78, r_inner=46):
    """Build SVG <path> wedges for a donut chart (no plotly dependency,
    since this needs to sit centered inside the lightbulb glass shape)."""
    import math

    total = sum(values) or 1
    paths = []
    start_angle = -90.0  # 12 o'clock start, clockwise
    for v, color in zip(values, colors):
        frac = v / total
        sweep = frac * 360.0
        end_angle = start_angle + sweep

        def pt(angle, r):
            rad = math.radians(angle)
            return cx + r * math.cos(rad), cy + r * math.sin(rad)

        x1o, y1o = pt(start_angle, r_outer)
        x2o, y2o = pt(end_angle, r_outer)
        x1i, y1i = pt(end_angle, r_inner)
        x2i, y2i = pt(start_angle, r_inner)
        large_arc = 1 if sweep > 180 else 0

        d = (
            f"M {x1o:.2f} {y1o:.2f} "
            f"A {r_outer} {r_outer} 0 {large_arc} 1 {x2o:.2f} {y2o:.2f} "
            f"L {x1i:.2f} {y1i:.2f} "
            f"A {r_inner} {r_inner} 0 {large_arc} 0 {x2i:.2f} {y2i:.2f} Z"
        )
        paths.append(f'<path d="{d}" fill="{color}" stroke="{COLORS["bg_card"]}" stroke-width="2"/>')

        # % label at mid-arc
        mid_angle = start_angle + sweep / 2
        lx, ly = pt(mid_angle, (r_outer + r_inner) / 2)
        if frac > 0.03:
            paths.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="12" font-weight="700" '
                f'fill="#FFFFFF" font-family="{_font_family()}">{frac*100:.0f}%</text>'
            )

        start_angle = end_angle

    return "".join(paths)


def _font_family():
    return "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def _lightbulb_svg(categories, colors, center_label, center_value):
    values = [c["value"] for c in categories]
    arcs = _donut_arcs(values, colors, cx=100, cy=82, r_outer=54, r_inner=30)

    return f"""
<svg viewBox="0 0 200 210" width="220" height="230" style="display:block;margin:0 auto;overflow:visible;">
  <defs>
    <filter id="lb-shadow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.10"/>
    </filter>
  </defs>

  <!-- Lightbulb glass outline: round top (circle arc) tapering to a neck -->
  <path d="M 46 82
           A 54 54 0 1 1 154 82
           C 154 102 145 114 136 124
           C 128 132 124 140 124 152
           L 76 152
           C 76 140 72 132 64 124
           C 55 114 46 102 46 82
           Z"
        fill="none" stroke="{COLORS['text_muted']}" stroke-width="2.5" stroke-linejoin="round"/>

  <!-- Donut chart centered in the glass -->
  <g filter="url(#lb-shadow)">{arcs}</g>

  <!-- Center hole label -->
  <text x="100" y="77" text-anchor="middle" font-size="9" fill="{COLORS['text_secondary']}"
        font-family="{_font_family()}">{center_label}</text>
  <text x="100" y="92" text-anchor="middle" font-size="15" font-weight="800" fill="{COLORS['text_primary']}"
        font-family="{_font_family()}">{center_value}</text>

  <!-- Screw base -->
  <rect x="79" y="152" width="42" height="9" rx="2" fill="none" stroke="{COLORS['text_muted']}" stroke-width="2.5"/>
  <line x1="82" y1="163" x2="118" y2="163" stroke="{COLORS['text_muted']}" stroke-width="2.5"/>
  <line x1="86" y1="172" x2="114" y2="172" stroke="{COLORS['text_muted']}" stroke-width="2.5"/>
  <path d="M 91 181 Q 100 186 109 181" fill="none" stroke="{COLORS['text_muted']}" stroke-width="2.5" stroke-linecap="round"/>
</svg>
"""


def _detail_card(cat, color, align="left"):
    pct = cat["value"]
    label = cat["label"]
    desc = cat.get("desc", "")
    count = cat.get("count")
    sub = f'{count:,} cases &middot; {pct:.0f}%' if count is not None else f'{pct:.0f}%'
    ic = _icon(cat.get("icon", "info"), size=18, color=color)

    text_align = "right" if align == "right" else "left"
    flex_dir = "row-reverse" if align == "right" else "row"

    return f"""
<div style="border:1.5px solid {color}33;background:{COLORS['bg_card']};border-radius:10px;
            padding:14px 16px;height:100%;box-shadow:0 1px 3px rgba(16,24,40,0.06);">
  <div style="display:flex;flex-direction:{flex_dir};align-items:center;gap:8px;margin-bottom:6px;">
    <span style="display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;
                 border-radius:8px;background:{color}1A;flex-shrink:0;">{ic}</span>
    <span style="font-size:0.78rem;font-weight:700;letter-spacing:0.02em;color:{color};text-align:{text_align};">
      {label.upper()}
    </span>
  </div>
  <div style="font-size:0.82rem;font-weight:600;color:{COLORS['text_primary']};text-align:{text_align};margin-bottom:2px;">
    {sub}
  </div>
  <div style="font-size:0.78rem;color:{COLORS['text_secondary']};line-height:1.4;text-align:{text_align};">
    {desc}
  </div>
</div>
"""


def lightbulb_category_chart(categories, center_label="Total", center_value="", colors=None):
    """
    categories: list of up to 4 dicts, each with:
        label (str), value (float, %), desc (str), icon (str, lucide name),
        count (int, optional)
    center_label / center_value: text shown in the donut hole.
    colors: optional list of hex colors (defaults to CHART_COLORWAY).
    """
    categories = categories[:4]
    palette = colors or CHART_COLORWAY
    cat_colors = [palette[i % len(palette)] for i in range(len(categories))]

    top_left = categories[0] if len(categories) > 0 else None
    bottom_left = categories[2] if len(categories) > 2 else None
    top_right = categories[1] if len(categories) > 1 else None
    bottom_right = categories[3] if len(categories) > 3 else None

    def cell(cat, color, align):
        if cat is None:
            return "<div></div>"
        return _detail_card(cat, color, align)

    svg = _lightbulb_svg(categories, cat_colors, center_label, center_value)

    body = f"""
<div style="font-family:{_font_family()};display:grid;grid-template-columns:1fr 1.05fr 1fr;grid-template-rows:auto auto;
            gap:14px;align-items:center;padding:8px 4px;box-sizing:border-box;">
  <div style="grid-column:1;grid-row:1;">{cell(top_left, cat_colors[0] if len(cat_colors) > 0 else COLORS['accent_primary'], 'left')}</div>
  <div style="grid-column:3;grid-row:1;">{cell(top_right, cat_colors[1] if len(cat_colors) > 1 else COLORS['accent_secondary'], 'right')}</div>
  <div style="grid-column:1;grid-row:2;">{cell(bottom_left, cat_colors[2] if len(cat_colors) > 2 else COLORS['accent_tertiary'], 'left')}</div>
  <div style="grid-column:3;grid-row:2;">{cell(bottom_right, cat_colors[3] if len(cat_colors) > 3 else COLORS['warning'], 'right')}</div>
  <div style="grid-column:2;grid-row:1 / span 2;display:flex;align-items:center;justify-content:center;">
    {svg}
  </div>
</div>
"""
    # Full standalone HTML doc — rendered via components.v1.html (iframe),
    # NOT st.markdown. st.markdown/rehype strips or mis-lays-out nested
    # inline <svg><path filter=...> content in some Streamlit versions,
    # which is why only the <text> labels were showing and the bulb/donut
    # paths were invisible. An iframe renders the raw DOM exactly as written.
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><style>
  html,body {{ margin:0; padding:0; background:transparent; }}
  * {{ box-sizing:border-box; }}
</style></head>
<body>{body}</body></html>"""