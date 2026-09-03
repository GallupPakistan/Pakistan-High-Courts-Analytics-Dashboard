"""
data_loader.py

Loads the combined dashboard master file (parquet) once and caches it via
Streamlit's cache so every page shares the same in-memory dataframe without
re-reading from disk.
"""

import streamlit as st
import pandas as pd
import os
import re

from utils.category_normalizer import add_normalized_category
from utils.bench_type_normalizer import add_normalized_bench_type

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "combined_dashboard_master.parquet")

COURTS_ORDER = ["Sindh", "Lahore", "Islamabad", "Peshawar", "Balochistan"]


@st.cache_data(show_spinner="Loading court data...")
def load_master_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df["Hearing_Date"] = pd.to_datetime(df["Hearing_Date"], errors="coerce")
    df["Year_Month"] = df["Hearing_Date"].dt.to_period("M").astype(str)
    df["Year"] = df["Hearing_Date"].dt.year

    # Restrict the dashboard to 2026 data only (2025 and any other years excluded).
    df = df[df["Year"] == 2026].reset_index(drop=True)

    # The source scrape occasionally contains fully identical rows (same
    # court, case, hearing date, judge, parties — every column matches).
    # These are pure duplicate records, not two different listings, and
    # were inflating every count-based KPI/chart in the dashboard by a
    # small but real margin. Drop them here, once, so every page downstream
    # sees a clean row count.
    df = df.drop_duplicates().reset_index(drop=True)

    # Case_No is NOT a globally unique case identifier — the same number
    # (e.g. "CP-44/2026") is independently re-used across different bench
    # locations within the same court (Sibi Bench vs Khuzdar Bench, for
    # example), since each bench/registry runs its own numbering. A proper
    # case-identity key therefore needs Court + Bench_Location + Case_No
    # together. This powers a "Unique Cases" metric that is distinct from
    # "Total Listings" (= row count = every hearing/cause-list appearance,
    # since the same case is typically listed multiple times over the
    # period). Never use plain len(df) as a stand-in for "number of cases".
    df["Case_UID"] = (
        df["Court"].astype(str) + "||" +
        df["Bench_Location"].fillna("").astype(str) + "||" +
        df["Case_No"].astype(str)
    )
    # For ~60% of Islamabad's rows, Case_No is actually the cause-list
    # serial/position number for that day (e.g. "1", "2", "3") rather than
    # the case's real registration number, and Islamabad has no
    # Bench_Location to help disambiguate — so unrelated cases collide
    # under the same Case_UID. Fold in Case_Title for these bare-number
    # rows so genuinely different cases aren't merged into one.
    _bare_case_no = df["Case_No"].astype(str).str.match(r"^\d{1,3}$")
    df.loc[_bare_case_no, "Case_UID"] = (
        df.loc[_bare_case_no, "Case_UID"] + "||" + df.loc[_bare_case_no, "Case_Title"].fillna("").astype(str)
    )

    # Dashboard scope is High Court benches only — Services/Customs/Election
    # Tribunals attached to a High Court are separate quasi-judicial forums,
    # not part of the High Court's own case docket, and were excluded by
    # design decision. A small number of tribunal rows leaked into the raw
    # scrape (e.g. "Election Tribunal, Quetta" in Bench_Location, and an
    # "Election_Tribunal_" Bench_Type at Peshawar) — drop them here so they
    # never silently reappear in a count/chart.
    _tribunal_mask = (
        df["Bench_Location"].astype(str).str.contains("Tribunal", case=False, na=False) |
        df["Bench_Type"].astype(str).str.contains("Tribunal", case=False, na=False)
    )
    df = df[~_tribunal_mask].reset_index(drop=True)

    # Each court records Case_Category in its own free-text format, so the
    # same subject matter (e.g. banking litigation) can appear as dozens of
    # different raw strings across courts ("BANKING", "Civil - COS(B) -
    # Banking", "Writ - Banking & Finance - Miscellaneous", ...). Add a
    # normalized Category_Group column so cross-court category comparisons
    # aggregate correctly. See utils/category_normalizer.py for the mapping
    # rules and utils/audit_category_mapping.py to review coverage.
    df = add_normalized_category(df, source_col="Case_Category", target_col="Category_Group")

    # Each court also records Bench_Type in its own free-text format, so the
    # same real bench configuration (e.g. a Single Bench) can appear as
    # several different raw strings ("SB", "Single Bench", "Single_Bench_S_B_",
    # ...). Add a normalized Bench_Type_Group column so "Top Bench Types"
    # charts and KPIs aggregate correctly instead of splitting one bench
    # type's volume across look-alike labels. See
    # utils/bench_type_normalizer.py for the mapping rules.
    df = add_normalized_bench_type(df, source_col="Bench_Type", target_col="Bench_Type_Group")

    # The raw "Judge" field is not always a single judge's name — for
    # Division/Full/Larger Bench sittings, the cause-list header lists every
    # judge on that bench joined together in one string, e.g.
    # "Mr. Justice X | Mr. Justice Y | [ Justice ... Block - Court 3 ]".
    # ~17% of listings (55k+ rows) are such combined strings. Treating the
    # whole string as "one judge" both undercounts the true number of
    # distinct judges and misattributes workload (a 2-judge listing should
    # count toward both judges' caseload, not neither/one). Judge_List
    # splits the courtroom/block tag off and parses out the individual
    # judge name(s) as a list, for accurate per-judge workload analysis.
    # Use df.explode("Judge_List") wherever counting listings *per judge*;
    # keep using the original "Judge" column/row count for Total Listings.
    def _parse_judges(raw):
        if pd.isna(raw):
            return []
        judges_part = re.split(r"\s*\[", str(raw))[0]
        names = re.split(r"\s*\|\s*|\s+&\s+|\s*,?\s*;\s*", judges_part)
        return [n.strip() for n in names if n.strip()]

    df["Judge_List"] = df["Judge"].apply(_parse_judges)

    return df


def apply_filters(df: pd.DataFrame, court=None, bench_location=None, case_category=None, date_range=None) -> pd.DataFrame:
    out = df
    if court and court != "All Courts":
        out = out[out["Court"] == court]
    if bench_location and bench_location != "All":
        out = out[out["Bench_Location"] == bench_location]
    if case_category and case_category != "All":
        out = out[out["Case_Category"] == case_category]
    if date_range:
        start, end = date_range
        out = out[(out["Hearing_Date"] >= pd.Timestamp(start)) & (out["Hearing_Date"] <= pd.Timestamp(end))]
    return out
