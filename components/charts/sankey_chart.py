"""
sankey_chart.py

Three-column flow diagram: Court -> Bench_Type_Group -> Category_Group.
Unlike every other Overview chart (bar, donut, line, map), which each show
one dimension's distribution on its own, this shows how the dimensions
relate — e.g. whether a court's Division Bench volume skews toward Civil
or Criminal matters. That relationship isn't visible anywhere else on the
page.

CARDINALITY
-----------
Court has 5 values and Bench_Type_Group has 7 (both fine as-is). Category_Group
has ~32 — plotted directly, a Sankey with that many rightmost nodes turns to
visual noise. So, same pattern as the Overview donut chart: keep the top
`top_n_categories` by overall volume, fold everything else into "Other".

COLOR
-----
Court nodes use the dashboard's COURT_COLORS (same court = same color as
every other chart/map on the page). Bench-type and category nodes cycle
through CHART_COLORWAY. Links inherit their source node's color — at a
high enough opacity to actually read as that color against the white
card (a first pass at low opacity looked identically pale-blue for every
court, which defeats the point of color-coding by court at all).
"""

import pandas as pd
import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "styles"))
from theme import COLORS, COURT_COLORS, CHART_COLORWAY, FONT_BODY  # noqa: E402


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def build_court_flow_sankey(df: pd.DataFrame, top_n_categories: int = 7, height: int = 620) -> go.Figure:
    work = df[["Court", "Bench_Type_Group", "Category_Group"]].dropna(
        subset=["Court", "Bench_Type_Group", "Category_Group"]
    )

    if work.empty:
        fig = go.Figure()
        fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)")
        return fig

    # Fold long-tail categories into "Other" — keep the top N by overall volume.
    cat_totals = work["Category_Group"].value_counts()
    top_categories = cat_totals.head(top_n_categories).index.tolist()
    work = work.copy()
    work["Category_Grouped"] = work["Category_Group"].where(
        work["Category_Group"].isin(top_categories), "Other"
    )

    # Node ordering: courts by descending total volume (so bar heights read
    # largest-to-smallest top-to-bottom, same convention as the other two
    # columns) — not raw appearance order, which was arbitrary.
    courts      = work["Court"].value_counts().index.tolist()
    bench_types = work["Bench_Type_Group"].value_counts().index.tolist()
    categories  = [c for c in top_categories if c in work["Category_Grouped"].unique()]
    if "Other" in work["Category_Grouped"].unique():
        categories.append("Other")

    court_idx = {name: i for i, name in enumerate(courts)}
    bench_idx = {name: i + len(courts) for i, name in enumerate(bench_types)}
    cat_idx   = {name: i + len(courts) + len(bench_types) for i, name in enumerate(categories)}

    fallback_colorway = CHART_COLORWAY
    court_colors = [COURT_COLORS.get(c, fallback_colorway[0]) for c in courts]
    bench_colors = [fallback_colorway[i % len(fallback_colorway)] for i in range(len(bench_types))]
    cat_colors   = [
        (COLORS["text_muted"] if name == "Other" else fallback_colorway[i % len(fallback_colorway)])
        for i, name in enumerate(categories)
    ]

    node_labels = [f"<b>{label}</b>" for label in (courts + bench_types + categories)]
    node_colors = court_colors + bench_colors + cat_colors

    # Link set 1: Court -> Bench Type
    link1 = work.groupby(["Court", "Bench_Type_Group"]).size().reset_index(name="Cases")
    # Link set 2: Bench Type -> Category (grouped)
    link2 = work.groupby(["Bench_Type_Group", "Category_Grouped"]).size().reset_index(name="Cases")

    sources, targets, values, link_colors = [], [], [], []

    # Opacity high enough that each court's own hue is actually legible
    # against the white card — this was the main readability problem.
    for _, row in link1.iterrows():
        src = court_idx[row["Court"]]
        sources.append(src)
        targets.append(bench_idx[row["Bench_Type_Group"]])
        values.append(row["Cases"])
        link_colors.append(_hex_to_rgba(node_colors[src], 0.55))

    for _, row in link2.iterrows():
        src = bench_idx[row["Bench_Type_Group"]]
        sources.append(src)
        targets.append(cat_idx[row["Category_Grouped"]])
        values.append(row["Cases"])
        link_colors.append(_hex_to_rgba(node_colors[src], 0.45))

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=node_labels,
                color=node_colors,
                pad=22,
                thickness=20,
                line=dict(color="rgba(16,24,40,0.18)", width=0.75),
                hovertemplate="<b>%{label}</b><br>%{value:,} cases<extra></extra>",
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=link_colors,
                hovertemplate="<b>%{source.label} → %{target.label}</b><br>%{value:,} cases<extra></extra>",
            ),
            textfont=dict(family=FONT_BODY, color=COLORS["text_primary"], size=13),
        )
    )

    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(family=FONT_BODY, color=COLORS["text_primary"], size=13),
    )
    return fig