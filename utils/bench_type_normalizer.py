"""
bench_type_normalizer.py

Normalizes the messy, court-specific `Bench_Type` strings in the master
dataset into a small set of consistent, human-readable buckets so that
"Top Bench Types" charts and the "Total Bench Types" KPI are actually
meaningful.

WHY THIS EXISTS
----------------
Same root problem as `Case_Category` (see utils/category_normalizer.py),
applied to `Bench_Type`. Each court records the same real-world bench
configuration in its own format. In the raw data, a plain Single Bench
alone appears as all of:
    "Single Bench", "SB", "Single_Bench_S_B_", "Single Bench (Regular)",
    "Single_Bench_Deleted_Cases", "Single_Bench_Supplementary_S_B_Supplementary_"
and Division Bench similarly splits across "Divisional Bench", "Division
Bench", "DB", "Division_Bench_D_B_", "Division Bench (Regular)",
"Division_Bench_Deleted_Cases_Deleted_D_B_",
"Divisional_Bench_Supplementary_D_B_Supplementary_".

Left raw, this:
  - inflates the "Total Bench Types" KPI (21 distinct raw values counted,
    vs. a true handful of real configurations)
  - fragments "Top Bench Types" bar/donut charts, so the true #1 bench
    type (Single Bench) shows several times under different labels
    instead of once with its full combined count
  - can silently drop a court's actual top bench type out of a
    `.value_counts().head(N)` cut just because its volume is split across
    look-alike spellings

This module maps every raw `Bench_Type` string onto one normalized
`Bench_Type_Group`.

HOW IT WORKS
------------
Same approach as `category_normalizer.py`: an ordered list of
(bucket_name, [regex patterns]) is checked top to bottom; the first
pattern that matches (case-insensitive, matched anywhere in the string)
wins. Administrative/procedural labels (Election Tribunal, Additional
Registrar, Company Bench) are checked before the generic Single/Division
patterns so they don't get absorbed into the wrong bucket.

The raw value "AB" is intentionally NOT guessed at — its expansion isn't
documented anywhere in the source data, and misclassifying it would be
worse than leaving it visible. It falls into "Other / Unspecified" along
with anything else unmatched, exactly like `category_normalizer.py`
routes unmatched values to "Other / Uncategorized" rather than guessing.

USAGE
-----
    from utils.bench_type_normalizer import add_normalized_bench_type

    df = add_normalized_bench_type(df)   # adds df["Bench_Type_Group"]
"""

import re
import pandas as pd
from functools import lru_cache

# ---------------------------------------------------------------------------
# ORDERED RULES: (bucket_name, [regex patterns]) — first match wins.
# Patterns are matched case-insensitively, anywhere in the raw string.
# ---------------------------------------------------------------------------
BENCH_TYPE_RULES = [

    # --- Administrative / non-bench labels (checked first) -----------------
    ("Election Tribunal", [
        r"election",
    ]),
    ("Company Bench", [
        r"company",
    ]),
    ("Administrative / Registrar", [
        r"registrar",
    ]),

    # --- Larger-than-two-judge formations (checked before generic Division) 
    ("Special Division Bench", [
        r"special.*division",
    ]),
    ("Full / Larger Bench", [
        r"\bfull\b", r"\blarger\b",
    ]),

    # --- Core bench sizes ----------------------------------------------------
    # Note: no trailing \b — raw values join words with underscores (e.g.
    # "Division_Bench_D_B_"), and underscore counts as a word character so
    # a trailing \b would fail to match right after "division"/"single".
    ("Division Bench", [
        r"divisi?on(al)?", r"\bdb\b",
    ]),
    ("Single Bench", [
        r"single", r"\bsb\b",
    ]),
]

# Fallback bucket for anything not matched by the rules above (e.g. "AB",
# whose expansion is not documented in the source data).
_OTHER_BUCKET = "Other / Unspecified"

# Precompile all patterns for speed.
_COMPILED_RULES = [
    (bucket, re.compile("|".join(patterns), re.IGNORECASE))
    for bucket, patterns in BENCH_TYPE_RULES
]


@lru_cache(maxsize=256)
def normalize_bench_type(raw_bench_type) -> str:
    """
    Map a single raw Bench_Type string to its normalized Bench_Type_Group.
    Cached (per-process) since the dataset has only ~20 distinct raw values
    repeated across ~340,000 rows.
    """
    if raw_bench_type is None or (isinstance(raw_bench_type, float) and pd.isna(raw_bench_type)):
        return _OTHER_BUCKET
    text = str(raw_bench_type).strip()
    if not text:
        return _OTHER_BUCKET
    for bucket, pattern in _COMPILED_RULES:
        if pattern.search(text):
            return bucket
    return _OTHER_BUCKET


def add_normalized_bench_type(df: pd.DataFrame, source_col: str = "Bench_Type",
                               target_col: str = "Bench_Type_Group") -> pd.DataFrame:
    """
    Adds a `Bench_Type_Group` column to df, computed by applying
    normalize_bench_type() to every unique value in `source_col` once
    (via a mapping dict), then broadcasting — much faster than calling
    .apply() row-by-row on 300k+ rows.
    """
    unique_vals = df[source_col].dropna().unique()
    mapping = {v: normalize_bench_type(v) for v in unique_vals}
    df[target_col] = df[source_col].map(mapping).fillna(_OTHER_BUCKET)
    return df


def normalization_coverage_report(df: pd.DataFrame, source_col: str = "Bench_Type",
                                   target_col: str = "Bench_Type_Group") -> pd.DataFrame:
    """
    Returns a small summary dataframe: for each normalized bucket, how many
    distinct raw bench types and how many total rows fall into it. Useful
    for auditing how much volume ends up in 'Other / Unspecified' and
    where to extend the rules next.
    """
    if target_col not in df.columns:
        df = add_normalized_bench_type(df, source_col, target_col)
    g = df.groupby(target_col).agg(
        distinct_raw_bench_types=(source_col, "nunique"),
        total_rows=(source_col, "size"),
    ).sort_values("total_rows", ascending=False)
    g["pct_of_total"] = (g["total_rows"] / len(df) * 100).round(2)
    return g.reset_index()
