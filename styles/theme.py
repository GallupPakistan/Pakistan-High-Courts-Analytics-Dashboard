"""
theme.py

Central visual theme for the Pakistan High Courts Comparative Analytics
Dashboard. Colors/fonts live here (Python) because Plotly charts need them
as plain values. All actual CSS styling lives in styles/dashboard.css —
this file just loads that CSS and injects the color palette as CSS custom
properties (--bg-primary, --accent-primary, etc.) so the .css file never
has to hardcode a color.

LIGHT THEME:
  - Main body: light neutral grey (#EFF1F5)
  - Sidebar: deep navy blue (stays dark, always)
  - Top banner header: dark navy gradient (stays dark, always)
  - Cards: solid white (#FFFFFF) with light-grey border + drop shadow
  - Text on cards: near-black navy (#101828)
  - Accents / charts: blue/cyan/indigo family (unchanged)
  - KPI icon badges: soft pastel tints of each accent color

Import get_theme_css() and inject it once at the top of app.py / every page
via st.markdown(get_theme_css(), unsafe_allow_html=True).
"""

import os

# ---------------------------------------------------------------------------
# COLOR PALETTE  —  LIGHT THEME
# ---------------------------------------------------------------------------
COLORS = {
    # --- Page body / surface ---
    "bg_primary":     "#EFF1F5",          # light neutral grey page background
    "bg_secondary":   "#0B1E3D",          # deep navy sidebar (stays dark)
    "bg_card":        "#FFFFFF",          # white card surface
    "border_glass":   "#E2E5EB",          # light grey card border

    # --- Accent / interactive ---
    "accent_primary":   "#3B82F6",        # electric blue  (charts, active nav, links)
    "accent_secondary": "#0EA5E9",        # sky blue        (secondary charts)
    "accent_tertiary":  "#818CF8",        # indigo/violet   (tertiary charts)
    "accent_gold":      "#F59E0B",        # amber           (sparing highlight only)

    # --- Text on light cards ---
    "text_primary":   "#101828",          # near-black navy
    "text_secondary": "#667085",          # mid grey
    "text_muted":     "#9BA8BF",          # lighter grey

    # --- Semantic colours ---
    "success": "#10B981",                 # emerald green
    "warning": "#F59E0B",                 # amber
    "danger":  "#EF4444",                 # red

    # --- Plotly helpers ---
    "grid_line": "rgba(203,213,225,0.70)",  # light grey gridlines for light bg

    # --- Pastel badge tints (for KPI icon backgrounds) ---
    "badge_blue":   "rgba(59,130,246,0.10)",
    "badge_cyan":   "rgba(14,165,233,0.10)",
    "badge_indigo": "rgba(129,140,248,0.10)",
    "badge_amber":  "rgba(245,158,11,0.12)",
    "badge_green":  "rgba(16,185,129,0.10)",
    "badge_rose":   "rgba(244,63,94,0.10)",
}

# Sequential palette — court → color IDENTICAL across every page
# NOTE: Sindh (#3B82F6 electric blue) and Lahore (#0EA5E9 sky blue) used to
# sit right next to each other on the color wheel and were hard to tell
# apart in charts/legends. Re-picked so all 5 courts read as clearly
# distinct hues (blue / pink / indigo / amber / green) at a glance.
COURT_COLORS = {
    "Lahore":      "#3B82F6",   # electric blue
    "Sindh":       "#EC4899",   # pink/magenta
    "Islamabad":   "#818CF8",   # indigo
    "Peshawar":    "#F59E0B",   # amber
    "Balochistan": "#10B981",   # emerald green
}

CHART_COLORWAY = [
    COLORS["accent_primary"],
    COLORS["accent_secondary"],
    COLORS["accent_tertiary"],
    COLORS["warning"],
    COLORS["success"],
    "#EC4899",
    "#A78BFA",
]

FONT_DISPLAY = "'Cinzel', serif"
FONT_BODY    = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

# Path to the static CSS file, relative to this file's location.
_CSS_PATH = os.path.join(os.path.dirname(__file__), "dashboard.css")


def _load_css_file() -> str:
    with open(_CSS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def get_theme_css() -> str:
    """Return the full <style> block for the dashboard: CSS variables
    (derived from COLORS/fonts) + the static dashboard.css content."""
    root_vars = f"""
:root {{
    --bg-primary:      {COLORS["bg_primary"]};
    --bg-secondary:    {COLORS["bg_secondary"]};
    --bg-card:         {COLORS["bg_card"]};
    --border-glass:    {COLORS["border_glass"]};
    --accent-primary:  {COLORS["accent_primary"]};
    --accent-secondary:{COLORS["accent_secondary"]};
    --accent-tertiary: {COLORS["accent_tertiary"]};
    --accent-gold:     {COLORS["accent_gold"]};
    --text-primary:    {COLORS["text_primary"]};
    --text-secondary:  {COLORS["text_secondary"]};
    --text-muted:      {COLORS["text_muted"]};
    --success:         {COLORS["success"]};
    --warning:         {COLORS["warning"]};
    --danger:          {COLORS["danger"]};
    --grid-line:       {COLORS["grid_line"]};
    --font-display:    {FONT_DISPLAY};
    --font-body:       {FONT_BODY};
}}
"""
    css_file_content = _load_css_file()
    return f"<style>{root_vars}\n{css_file_content}</style>"


def get_plotly_layout_defaults() -> dict:
    """Shared Plotly layout kwargs — tuned for the light-grey card surface."""
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_BODY, color=COLORS["text_secondary"], size=12),
        legend=dict(
            bgcolor="rgba(255,255,255,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(color=COLORS["text_secondary"], size=11),
        ),
        xaxis=dict(
            gridcolor=COLORS["grid_line"],
            zerolinecolor=COLORS["grid_line"],
            color=COLORS["text_secondary"],
            linecolor=COLORS["border_glass"],
        ),
        yaxis=dict(
            gridcolor=COLORS["grid_line"],
            zerolinecolor=COLORS["grid_line"],
            color=COLORS["text_secondary"],
            linecolor=COLORS["border_glass"],
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        colorway=CHART_COLORWAY,
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor=COLORS["border_glass"],
            font=dict(color=COLORS["text_primary"], family=FONT_BODY),
        ),
    )