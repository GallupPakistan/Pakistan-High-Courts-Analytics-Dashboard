"""
litigant_classifier.py

Heuristic classification of a party (Petitioner/Respondent) name as
"Government / Public Sector" vs "Private / Individual", based on common
patterns seen in Pakistani cause-list party names (e.g. "The State",
"Federation of Pakistan", "Province of Punjab", statutory bodies like
NADRA/FBR/WAPDA, judicial/police/revenue officer designations, etc.).

This is a keyword/abbreviation heuristic, not an authoritative legal
classification — abbreviations for government offices in Pakistani legal
documents are extremely varied, so some genuinely-government parties will
still fall into "Private / Individual" or "Unknown" here. Treat charts
built on this as an approximate picture, not an exact count.
"""

import re
import pandas as pd

_GOVT_KEYWORDS = [
    r"\bState\b", r"Federation of Pakistan", r"\bFOP\b", r"Province of", r"Govt\.?\s*of",
    r"Government of", r"\bGOP\b", r"\bGOK\b", r"\bGOB\b", r"\bGOS\b", r"Secretary",
    r"Chief Secretary", r"NADRA", r"\bFBR\b", r"\bNAB\b", r"District Judge", r"A\.?\s*D\.?\s*J\b",
    r"Sessions Judge", r"A\.?\s*S\.?\s*J\b", r"Inspector General", r"\bIG\b", r"\bSSP\b", r"\bDPO\b",
    r"S\.?\s*H\.?\s*O\.?", r"Station House Officer", r"Collector", r"Commissioner",
    r"Deputy Commissioner", r"\bDC\b", r"\bD\.?J\b", r"WAPDA", r"PESCO", r"QESCO", r"SEPCO",
    r"IESCO", r"HESCO", r"MEPCO", r"GEPCO", r"LESCO", r"FESCO", r"Cantonment Board",
    r"Pakistan Railway", r"\bPIA\b", r"Registrar", r"Election Commission", r"Chairman NAB",
    r"Directorate", r"Anti[- ]Corruption", r"Police", r"Customs", r"University",
    r"Pakistan through", r"Ministry of", r"Prosecutor General", r"Attorney General",
    r"Development Authority", r"\bLDA\b", r"\bCDA\b", r"\bBOR\b", r"Board of Revenue",
    r"\bMBR\b", r"Member Board", r"Revenue Authority", r"\bPRA\b", r"Family Court", r"\bJFC\b",
    r"Judicial Magistrate", r"Civil Judge", r"\bWASA\b", r"\bTMA\b", r"Union Council",
    r"Local Government",
]
_PATTERN = re.compile("|".join(_GOVT_KEYWORDS), re.IGNORECASE)


def classify_litigant(name) -> str:
    """Return 'Government / Public Sector', 'Private / Individual', or
    'Unknown' (blank/missing name) for a single party-name string."""
    if pd.isna(name) or not str(name).strip():
        return "Unknown"
    return "Government / Public Sector" if _PATTERN.search(str(name)) else "Private / Individual"


def add_litigant_type(df: pd.DataFrame, source_col: str = "Respondent", target_col: str = "Respondent_Type") -> pd.DataFrame:
    """Add a classified litigant-type column, vectorized over a dataframe."""
    df[target_col] = df[source_col].apply(classify_litigant)
    return df
