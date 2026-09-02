"""
map_chart.py

City-level map of court bench locations. Each marker is a Bench_Location
(the actual physical seat where cases are listed — e.g. "Lahore",
"Multan", "Rawalpindi" all under Lahore High Court), sized by case volume
and colored by parent Court. Uses Plotly's open-street-map style via
go.Scattermap (MapLibre), which needs no Mapbox API key/token.

Real scroll/pinch zoom + pan is native to this widget — clustered cities
(Lahore/Rawalpindi/Multan/Bahawalpur) separate out visually as the user
zooms in, and hovering a marker shows the exact court, city and count.
This does NOT swap in new data at different zoom levels (that needs
custom JS Plotly/Streamlit don't support out of the box) — it's one
static set of markers that a real map viewport lets you zoom into.

WHY BENCH_LOCATION, NOT COURT
------------------------------
`Court` only has 5 values (one per High Court) and Islamabad has no
`Bench_Location` on file (single-seat court) — plotting by Court alone
would just be 5 dots. Plotting by Bench_Location surfaces the real
sub-structure (e.g. Lahore HC's 4 physical benches) that a map is
actually useful for.

COORDINATES
-----------
The dataset has no lat/long column, so bench-location coordinates are
hardcoded below (city-center coordinates, sufficient for a dashboard
marker — not survey-grade). Two raw Bench_Location values are folded
into their parent city before plotting because they're the same physical
seat with an administrative suffix, not a different place:
    "Principal Seat Quetta, Through Video Link" -> "Principal Seat Quetta"
    "Election Tribunal, Quetta"                 -> "Principal Seat Quetta"
Islamabad has no Bench_Location on file at all (single-seat court), so
it's added as its own point keyed directly off Court == "Islamabad".
"""

import pandas as pd
import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "styles"))
from theme import COLORS, COURT_COLORS  # noqa: E402

# City-center coordinates for every bench location in the dataset, plus
# Islamabad (which has no Bench_Location value of its own).
_CITY_COORDS = {
    "Lahore":                 (31.5497, 74.3436),
    "Multan":                 (30.1575, 71.5249),
    "Bahawalpur":             (29.3956, 71.6836),
    "Rawalpindi":             (33.5651, 73.0169),
    "Karachi":                (24.8607, 67.0011),
    "Hyderabad":              (25.3960, 68.3578),
    "Sukkur":                 (27.7052, 68.8574),
    "Larkana":                (27.5590, 68.2123),
    "Mirpurkhas":             (25.5271, 69.0113),
    "Mingora":                (34.7717, 72.3603),
    "Abbottabad":             (34.1688, 73.2215),
    "Principal Seat Quetta":  (30.1798, 66.9750),
    "Islamabad":              (33.6844, 73.0479),
}

# Raw Bench_Location values that are really the same physical seat as
# another entry above, just recorded with an administrative suffix.
_LOCATION_ALIASES = {
    "Principal Seat Quetta, Through Video Link": "Principal Seat Quetta",
    "Election Tribunal, Quetta": "Principal Seat Quetta",
}


def _resolve_location(row):
    """Return the canonical city name to plot for a given row, or None if
    it can't be resolved to a known coordinate."""
    loc = row["Bench_Location"]
    if pd.isna(loc) or not str(loc).strip():
        # Islamabad High Court has no Bench_Location — key off Court instead.
        return "Islamabad" if row["Court"] == "Islamabad" else None
    loc = str(loc).strip()
    return _LOCATION_ALIASES.get(loc, loc)


# Cities where the marker is an aggregate of more than one raw
# Bench_Location string (Quetta) or has no Bench_Location value at all
# (Islamabad). For these, a click should filter by Court only — setting
# Bench_Location to an exact string would under- or over-match. Every
# other city's marker name equals its raw Bench_Location string exactly,
# so it's safe to filter on directly.
_COURT_ONLY_CITIES = {"Principal Seat Quetta", "Islamabad"}


def build_bench_location_map(df: pd.DataFrame, height: int = 480) -> go.Figure:
    """
    Aggregates df to one row per bench-location city (case count + parent
    court), then renders a Scattermap with marker size scaled to volume
    and color keyed to the parent High Court.

    Each marker carries customdata = [city, court, bench_filter_value] so
    a click handler can drive the shared Court / Bench_Location filters
    without recomputing this aggregation. bench_filter_value is None for
    cities in _COURT_ONLY_CITIES (see above) — the click should only set
    Court in that case.
    """
    work = df[["Bench_Location", "Court"]].copy()
    work["City"] = work.apply(_resolve_location, axis=1)
    work = work.dropna(subset=["City"])

    agg = (
        work.groupby(["City", "Court"])
        .size()
        .reset_index(name="Cases")
        .sort_values("Cases", ascending=False)
    )
    # A city could in theory carry rows from more than one Court label; keep
    # only each city's dominant court so one marker = one clear color.
    agg = agg.sort_values("Cases", ascending=False).drop_duplicates("City", keep="first")

    agg["lat"] = agg["City"].map(lambda c: _CITY_COORDS.get(c, (None, None))[0])
    agg["lon"] = agg["City"].map(lambda c: _CITY_COORDS.get(c, (None, None))[1])
    agg = agg.dropna(subset=["lat", "lon"])

    if agg.empty:
        fig = go.Figure()
        fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)")
        return fig

    max_cases = agg["Cases"].max()
    # Marker area scaled (sqrt) so a 10x volume difference doesn't turn into
    # a 10x-radius marker that swallows the map.
    agg["marker_size"] = 14 + (agg["Cases"] / max_cases) ** 0.5 * 40

    fig = go.Figure()
    for court in agg["Court"].unique():
        sub = agg[agg["Court"] == court]
        color = COURT_COLORS.get(court, COLORS["accent_primary"])
        fig.add_trace(
            go.Scattermap(
                lat=sub["lat"], lon=sub["lon"],
                mode="markers",
                marker=dict(size=sub["marker_size"], color=color, opacity=0.85),
                name=court,
                text=[
                    f"<b>{city}</b><br>{court} High Court<br>{cases:,} listings"
                    for city, cases in zip(sub["City"], sub["Cases"])
                ],
                hoverinfo="text",
                customdata=[
                    [city, court, None if city in _COURT_ONLY_CITIES else city]
                    for city in sub["City"]
                ],
            )
        )

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        map=dict(
            style="open-street-map",
            center=dict(lat=30.5, lon=69.5),  # roughly centers on Pakistan
            zoom=4.4,
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=COLORS["border_glass"],
            borderwidth=1,
            font=dict(color=COLORS["text_secondary"], size=11),
        ),
        showlegend=True,
    )
    return fig
