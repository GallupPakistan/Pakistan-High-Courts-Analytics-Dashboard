"""
data_quality.py

Detects per-court data-coverage gaps in the currently filtered dataframe so
trend/volume pages can warn the user instead of silently plotting a
"Growth %" or "Peak Month" that is actually just an artifact of the scraper
having run for some courts in some months and not others.

This is computed live from whatever data is on screen (not hardcoded month
numbers), so it stays correct as new scrapes extend the coverage window.
"""

import pandas as pd


def find_coverage_gaps(df: pd.DataFrame, courts_order: list) -> list[str]:
    """
    For every court present in `courts_order`, find months within the
    dataset's overall Year_Month span that have ZERO listings for that
    court, while at least one other court has data that month. Returns a
    list of short "Court: missing Mon YYYY, Mon YYYY, ..." strings, one
    per affected court, ordered by how many months are missing (worst
    first). Empty list if coverage looks complete.
    """
    if df.empty or "Year_Month" not in df.columns:
        return []

    all_months = sorted(df["Year_Month"].dropna().unique().tolist())
    if len(all_months) < 2:
        return []

    pivot = (
        df.dropna(subset=["Year_Month"])
        .groupby(["Year_Month", "Court"]).size()
        .unstack(fill_value=0)
        .reindex(all_months, fill_value=0)
    )

    warnings = []
    for court in courts_order:
        if court not in pivot.columns:
            continue
        missing_months = [m for m in all_months if pivot.loc[m, court] == 0]
        # Only flag it as a genuine gap (not just "this court has no data
        # at all in the current filter", which the page's own empty-state
        # already communicates) — i.e. some months present, some missing.
        if missing_months and len(missing_months) < len(all_months):
            label = ", ".join(
                pd.Period(m, freq="M").strftime("%b %Y") for m in missing_months
            )
            warnings.append((len(missing_months), f"**{court}**: no listings recorded for {label}"))

    warnings.sort(key=lambda x: -x[0])
    return [w for _, w in warnings]
