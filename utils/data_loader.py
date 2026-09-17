"""
data_loader.py

Loads the combined dashboard master file (parquet) once and caches it via
Streamlit's cache so every page shares the same in-memory dataframe without
re-reading from disk.

--------------------------------------------------------------------------
SCHEMA BRIDGE (added — see README "Schema mismatch fix")
--------------------------------------------------------------------------
The parquet file actually produced by build_parquet.py / the live scrape
only carries 13 raw columns:

    Court, Date, Year, Month, Day, Case_No, Section, Judges, Petitioner,
    Respondent, Petitioner_Advocate, Respondent_Advocate, Source_File

...but every view in this dashboard is written against the richer
16-column "unified schema" documented in views/data_dictionary.py
(Hearing_Date, Bench_Location, Bench_Type, Case_Category, Judge,
Case_Title, Court_Room, ...). Loading the raw file directly used to raise
a KeyError the first time a view touched "Hearing_Date", which app.py's
safety net silently turned into a generic "No Data Found" card.

This module now derives every one of those missing columns from the raw
13, per-court, before the rest of the pipeline (dedup, Case_UID,
normalizers, Judge_List) runs unchanged. Nothing downstream had to change.

Per-court derivation notes:
  - Court: "Peshawar High Court - Abbottabad" etc. is split into
    Court="Peshawar" + Bench_Location="Abbottabad"; the other 4 courts'
    " High Court" suffix is simply dropped.
  - Bench_Location: Sindh's own Source_File column already holds the
    bench city name (Karachi/Hyderabad/Sukkur/Larkana/Mirpurkhas) — reused
    directly. Balochistan is a single physical seat -> "Principal Seat
    Quetta" for every row. Lahore and Islamabad carry no bench-location
    signal in the raw data at all, so it's left blank for them (same
    "single-seat court" handling the map/filters already had for
    Islamabad).
  - Hearing_Date: each court stamps its date in a different raw shape
    (see _parse_hearing_dates) — parsed per-court, then combined. Main
    Peshawar-seat rows (no city suffix) only carry a bare registration
    Year in this scrape (no month/day), so Hearing_Date is NaT for them;
    they still count in yearly KPIs/"Total Listings" via the Year
    fallback below, but drop out of month-level trend/heatmap charts
    (which already dropna on Year_Month) and don't get a calendar date in
    Case Search. This is a genuine gap in the source scrape, not
    something recoverable from this file — flagged in data_dictionary.py.
  - Judge / Court_Room: the raw "Judges" field already has the exact
    "<judge name(s)> | [ <block> - Court <n> ]" shape the rest of the app
    expects for "Judge" — it's kept as-is. The trailing "[ ... ]" segment
    is additionally split off into its own Court_Room column.
  - Bench_Type: there's no raw bench-type label at all in this scrape, so
    it's inferred from how many individual judges Judge_List resolves to
    (1 -> Single Bench, 2 -> Division Bench, 3+ -> Full / Larger Bench),
    using the exact label strings utils/bench_type_normalizer.py already
    recognizes.
  - Case_Category: the raw "Section" field is reused directly — it's the
    only free-text field carrying this kind of information across all 5
    courts, and utils/category_normalizer.py's rules already recognize
    both genuine subject-matter strings (e.g. "Civil - Civil Revision...")
    and administrative/listing-status strings (e.g. "NOTICE CASES") that
    appear in it.
  - Case_Title: built as "<Petitioner> VS <Respondent>" (falls back to
    just Petitioner when Respondent is blank).
  - Case_Year: left unset (NaN) — views/litigant_insights.py already
    falls back to extracting it from Case_No when this column is empty.
"""

import os
import re

import numpy as np
import pandas as pd
import streamlit as st
from pymongo import MongoClient

from utils.category_normalizer import add_normalized_category
from utils.bench_type_normalizer import add_normalized_bench_type

# ---------------------------------------------------------------------
# MongoDB connection
# ---------------------------------------------------------------------
# Connection details come from Streamlit secrets (.streamlit/secrets.toml,
# gitignored) so nothing sensitive lives in source control. Falls back to
# environment variables so this also works outside Streamlit Cloud (e.g.
# a plain "python build_something.py" run) if secrets.toml isn't present.


def _get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, default)


MONGO_URI = _get_secret("MONGO_URI")
MONGO_DB = _get_secret("MONGO_DB", "PakistanCourtDB")
MONGO_COLLECTION = _get_secret("MONGO_COLLECTION", "cases")


@st.cache_resource(show_spinner=False)
def _get_mongo_collection():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB][MONGO_COLLECTION]

COURTS_ORDER = ["Sindh", "Lahore", "Islamabad", "Peshawar", "Balochistan"]

# ---------------------------------------------------------------------
# Raw -> unified schema bridge helpers
# ---------------------------------------------------------------------

_BRACKET_SUFFIX = re.compile(r"(\[[^\]]*\])\s*$")


def _split_court(raw_court):
    """'Peshawar High Court - Abbottabad' -> ('Peshawar', 'Abbottabad').
    Every other court's ' High Court' suffix is simply dropped."""
    text = str(raw_court).strip()
    if text.startswith("Peshawar High Court"):
        rest = text[len("Peshawar High Court"):].strip(" -")
        return "Peshawar", (rest if rest else None)
    return text.replace(" High Court", "").strip(), None


def _parse_hearing_dates(df: pd.DataFrame) -> pd.Series:
    """Per-court raw-date parsing -> a single Hearing_Date datetime series."""
    out = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

    # Balochistan: "20 Jul 2026 Monday 09:00 AM" -> keep the "DD Mon YYYY" head.
    m = df["Court"] == "Balochistan"
    heads = df.loc[m, "Date"].astype(str).str.extract(r"^(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})")[0]
    out[m] = pd.to_datetime(heads, format="%d %b %Y", errors="coerce")

    # Islamabad: already ISO "YYYY-MM-DD".
    m = df["Court"] == "Islamabad"
    out[m] = pd.to_datetime(df.loc[m, "Date"], format="%Y-%m-%d", errors="coerce")

    # Lahore: "DD-MM-YYYY".
    m = df["Court"] == "Lahore"
    out[m] = pd.to_datetime(df.loc[m, "Date"], format="%d-%m-%Y", errors="coerce")

    # Peshawar - D.I.Khan: "DD-MON-YY".
    m = (df["Court"] == "Peshawar") & (df["Bench_Location"] == "D.I.Khan")
    out[m] = pd.to_datetime(df.loc[m, "Date"], format="%d-%b-%y", errors="coerce")

    # Peshawar - Abbottabad / Bannu: numeric Day + Month name + Year, three
    # separate columns instead of one Date string.
    m = (df["Court"] == "Peshawar") & (df["Bench_Location"].isin(["Abbottabad", "Bannu"]))
    combo = (
        df.loc[m, "Day"].astype(str).str.strip() + " "
        + df.loc[m, "Month"].astype(str).str.strip() + " "
        + df.loc[m, "Year"].astype(str).str.strip()
    )
    out[m] = pd.to_datetime(combo, format="%d %B %Y", errors="coerce")

    # Sindh: Year + Month name + numeric Day, same three-column shape.
    m = df["Court"] == "Sindh"
    combo = (
        df.loc[m, "Day"].astype(str).str.strip() + " "
        + df.loc[m, "Month"].astype(str).str.strip() + " "
        + df.loc[m, "Year"].astype(str).str.strip()
    )
    out[m] = pd.to_datetime(combo, format="%d %B %Y", errors="coerce")

    # Main Peshawar seat (no city suffix) and Peshawar - Mingora: this scrape
    # only has a bare weekday name / nothing at all -> stays NaT. Handled via
    # the raw-Year fallback in load_master_data() for the yearly-scope filter.
    return out


def _parse_judges(raw):
    if pd.isna(raw):
        return []
    judges_part = re.split(r"\s*\[", str(raw))[0]
    names = re.split(r"\s*\|\s*|\s+&\s+|\s*,?\s*;\s*", judges_part)
    return [n.strip() for n in names if n.strip()]


@st.cache_data(show_spinner="Loading court data...")
def load_master_data() -> pd.DataFrame:
    coll = _get_mongo_collection()
    # _id is Mongo's own ObjectId and carries no meaning for this app —
    # exclude it at the query level rather than dropping it afterward.
    df = pd.DataFrame(list(coll.find({}, {"_id": 0})))

    # ------------------------------------------------------------------
    # SCHEMA BRIDGE: raw 13-column scrape -> the 16-column unified schema
    # every view below is written against. See module docstring for the
    # full reasoning behind each derivation.
    # ------------------------------------------------------------------
    split_res = df["Court"].apply(_split_court)
    df["Bench_Location"] = split_res.apply(lambda t: t[1])
    df["Court"] = split_res.apply(lambda t: t[0])

    sindh_mask = df["Court"] == "Sindh"
    df.loc[sindh_mask, "Bench_Location"] = df.loc[sindh_mask, "Source_File"]
    df.loc[df["Court"] == "Balochistan", "Bench_Location"] = "Principal Seat Quetta"

    df["Hearing_Date"] = _parse_hearing_dates(df)
    df["Year_Month"] = df["Hearing_Date"].dt.to_period("M").astype(str)
    df["Year_Month"] = df["Year_Month"].where(df["Hearing_Date"].notna())

    # Effective year: prefer the parsed Hearing_Date; for rows where this
    # scrape has no day/month at all (bare-Year Peshawar-seat rows), fall
    # back to the raw Year field so they aren't dropped from the year-scope
    # filter just because they lack month/day granularity.
    df["Year"] = df["Hearing_Date"].dt.year.fillna(pd.to_numeric(df["Year"], errors="coerce"))

    # (Previously restricted to Year == 2026 only — removed so all years show.)

    # Judge / Court_Room split off the raw "Judges" field's trailing
    # "[ block - Court n ]" tag (kept together for clean_judge_label /
    # clean_court_room_label in utils/formatting.py to format for display).
    bracket = df["Judges"].astype(str).str.extract(_BRACKET_SUFFIX)[0]
    df["Judge"] = df["Judges"]
    df["Court_Room"] = bracket.where(df["Judges"].notna())

    df["Case_Category"] = df["Section"]
    # The raw "Section" scrape field is blank (empty string) for ~76k rows
    # and NaN for another ~27k, and both were flowing straight through as
    # a literal empty Case_Category value. Category_Group already bucketed
    # these into "Other / Uncategorized" via category_normalizer.py, but
    # every chart/KPI/filter on this page reads the raw Case_Category
    # column directly (Top Case Categories donut, category filter dropdown,
    # "Categories" KPI count, "Dominant category" callout, etc.) — so the
    # blank value was rendering as an unlabeled legend row (just a bare
    # percentage, no text) instead of disappearing or reading sensibly.
    # Give it one explicit, readable label instead so it displays properly
    # everywhere Case_Category is used, without touching Category_Group.
    _blank_category = df["Case_Category"].isna() | (df["Case_Category"].astype(str).str.strip() == "")
    df.loc[_blank_category, "Case_Category"] = "Category Not Assigned"

    resp = df["Respondent"].astype(str).str.strip()
    df["Case_Title"] = np.where(
        resp.replace("nan", "") != "",
        df["Petitioner"].astype(str) + " VS " + df["Respondent"].astype(str),
        df["Petitioner"].astype(str),
    )
    df["Case_Year"] = np.nan

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
    # scrape (e.g. "Election Tribunal, Quetta" in Bench_Location) — drop
    # them here so they never silently reappear in a count/chart.
    _tribunal_mask = (
        df["Bench_Location"].astype(str).str.contains("Tribunal", case=False, na=False) |
        df["Case_Category"].astype(str).str.contains("Tribunal", case=False, na=False)
    )
    df = df[~_tribunal_mask].reset_index(drop=True)

    # Free the raw columns that were only ever inputs to the derivations
    # above (dedup and Case_UID are already computed, so it's safe now).
    # Every downstream view (checked across views/*.py) reads the derived
    # columns instead (Hearing_Date, Judge, Court_Room, Case_Category,
    # Bench_Location, ...) — these raw ones are never touched again.
    # Together they were ~120MB of the cached dataframe's resident memory
    # (Judges alone ~64MB, Source_File ~23MB, Date/Month/Day ~35MB
    # combined) for zero further use — a meaningful chunk of what was
    # pushing this cache over Streamlit Cloud's free-tier memory ceiling.
    df = df.drop(columns=["Date", "Month", "Day", "Judges", "Source_File"])

    # Each court records Case_Category in its own free-text format, so the
    # same subject matter (e.g. banking litigation) can appear as dozens of
    # different raw strings across courts ("BANKING", "Civil - COS(B) -
    # Banking", "Writ - Banking & Finance - Miscellaneous", ...). Add a
    # normalized Category_Group column so cross-court category comparisons
    # aggregate correctly. See utils/category_normalizer.py for the mapping
    # rules.
    df = add_normalized_category(df, source_col="Case_Category", target_col="Category_Group")

    # The raw "Judge" field is not always a single judge's name — for
    # Division/Full/Larger Bench sittings, the cause-list header lists every
    # judge on that bench joined together in one string, e.g.
    # "Mr. Justice X | Mr. Justice Y | [ Justice ... Block - Court 3 ]".
    # Treating the whole string as "one judge" both undercounts the true
    # number of distinct judges and misattributes workload (a 2-judge
    # listing should count toward both judges' caseload, not neither/one).
    # Judge_List splits the courtroom/block tag off and parses out the
    # individual judge name(s) as a list, for accurate per-judge workload
    # analysis. Use df.explode("Judge_List") wherever counting listings
    # *per judge*; keep using the original "Judge" column/row count for
    # Total Listings.
    df["Judge_List"] = df["Judge"].apply(_parse_judges)

    # Bench_Type: this scrape has no raw bench-configuration label at all,
    # so it's inferred from how many individual judges Judge_List resolves
    # to for that row — using the exact label strings
    # utils/bench_type_normalizer.py already recognizes, so Bench_Type_Group
    # (below) comes out correctly without any extra mapping.
    _n_judges = df["Judge_List"].apply(len)
    df["Bench_Type"] = np.select(
        [_n_judges == 0, _n_judges == 1, _n_judges == 2],
        ["Other / Unspecified", "Single Bench", "Division Bench"],
        default="Full / Larger Bench",
    )

    # Each court also records Bench_Type in its own free-text format, so the
    # same real bench configuration (e.g. a Single Bench) can appear as
    # several different raw strings ("SB", "Single Bench", "Single_Bench_S_B_",
    # ...). Add a normalized Bench_Type_Group column so "Top Bench Types"
    # charts and KPIs aggregate correctly instead of splitting one bench
    # type's volume across look-alike labels. See
    # utils/bench_type_normalizer.py for the mapping rules.
    df = add_normalized_bench_type(df, source_col="Bench_Type", target_col="Bench_Type_Group")

    # Memory optimization — this dataframe is cached for the app's entire
    # lifetime (@st.cache_data), so its resident size directly affects
    # whether the app stays under Streamlit Cloud's memory ceiling. These
    # columns repeat the same small set of values across hundreds of
    # thousands of rows (Court: 5 values, Judge: ~360, Court_Room: ~80,
    # etc.) — category dtype stores each row as a small integer code
    # instead of repeating the full string, cutting overall memory by
    # roughly a third with no behavior change (groupby/value_counts/
    # str.contains all work the same on category dtype).
    for _cat_col in ["Court", "Bench_Location", "Bench_Type", "Case_Category",
                      "Category_Group", "Bench_Type_Group", "Court_Room",
                      "Case_Stage", "Section", "Judge", "Year_Month"]:
        if _cat_col in df.columns:
            df[_cat_col] = df[_cat_col].astype("category")

    # Year / Case_Year only ever hold small whole numbers (or NaN) — no
    # need for 64-bit floats.
    for _num_col in ["Year", "Case_Year"]:
        if _num_col in df.columns:
            df[_num_col] = df[_num_col].astype("float32")

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
        # Rows with no parsed Hearing_Date (NaT) must stay in — they still
        # count toward Total Listings (see load_master_data docstring); a
        # NaT vs Timestamp comparison is always False, so without this
        # explicit carve-out the default (min,max) date filter silently
        # drops every undated row instead of behaving like "no filter".
        out = out[
            out["Hearing_Date"].isna()
            | ((out["Hearing_Date"] >= pd.Timestamp(start)) & (out["Hearing_Date"] <= pd.Timestamp(end)))
        ]
    return out
