"""
category_normalizer.py

Normalizes the messy, court-specific `Case_Category` strings in the master
dataset into a small set of consistent, human-readable buckets so that
cross-court comparisons (e.g. "how much Banking litigation does each High
Court carry?") are actually meaningful.

WHY THIS EXISTS
----------------
Each of the 5 High Courts records categories in its own format. The exact
same subject matter shows up under dozens of different spellings, e.g.
banking litigation alone appears as all of:
    "BANKING", "BANKING APPEAL", "Civil - COS(B) - Banking",
    "Writ - Banking & Finance - Miscellaneous", "RFA-Under Special Laws-Banking",
    "Criminal - Crl. Misc. - Post-Arrest Bail-Banking Offences Ordinance 1984", ...
Comparing raw `Case_Category` values across courts therefore silently
undercounts real volume and makes "Top Category" / crosstab charts
misleading. This module maps every raw string onto one normalized
`Category_Group`.

HOW IT WORKS
------------
An ordered list of (bucket_name, [regex patterns]) is checked top to bottom;
the first pattern that matches (case-insensitive, matched anywhere in the
string) wins. Order matters: more specific/subject-matter buckets (Banking,
Family, Tax, Contempt, Habeas Corpus...) are checked before generic
procedural buckets (Civil Appeal, Writ - Service...) so that e.g. a banking
bail case lands in "Banking & Finance", not "Criminal - Bail".

Anything that matches nothing falls into "Other / Uncategorized" — this is
reported explicitly (see `normalization_coverage_report`) rather than
silently mis-bucketed, so the mapping can be extended over time.

USAGE
-----
    from utils.category_normalizer import normalize_category, add_normalized_category

    df = add_normalized_category(df)          # adds df["Category_Group"]
    normalize_category("Civil - COS(B) - Banking")   -> "Banking & Finance"
"""

import re
import pandas as pd
from functools import lru_cache

# ---------------------------------------------------------------------------
# ORDERED RULES: (bucket_name, [regex patterns]) — first match wins.
# Patterns are matched case-insensitively, anywhere in the raw string.
# ---------------------------------------------------------------------------
CATEGORY_RULES = [

    # --- Subject-matter buckets (checked first — highest priority) ---------
    ("Banking & Finance", [
        r"bank", r"money\s*land?ing", r"financial\s*institution",
    ]),
    ("Family Law", [
        r"famil", r"dow[ei]r", r"dowry", r"guardian", r"custody",
        r"marriage", r"maintenance", r"jacti?tation", r"hazanat",
    ]),
    ("Tax & Revenue", [
        r"\btax\b", r"sales\s*tax", r"income\s*tax", r"custom", r"excise",
        r"\bitr\b", r"\bstr\b", r"c\.?ref", r"\bptr\b", r"\betr\b",
        r"withholding\s*tax", r"super\s*tax", r"\bcust(oms)?\s*matter\b",
        r"customs\s*tribunal", r"federal\s*excise",
    ]),
    ("Contempt of Court", [
        r"contempt",
    ]),
    ("Habeas Corpus / Missing Persons", [
        r"habeas", r"h\.c\.p", r"missing\s*person", r"detention\s*mpo",
        r"\bdetention\b(?!.*medical\s*board)",
    ]),
    ("Criminal - Bail", [
        r"bail", r"\b497\b", r"\b498\b", r"\b439\b", r"\b435\b",
        r"22\s*[-/]?\s*a[-/]b", r"22-a\b", r"22\s*a\b",
    ]),
    ("Criminal - Appeal", [
        r"crl\.?\s*appeal", r"jail\s*appeal", r"\bpsla\b",
        r"crl\.?\s*org", r"capital\s*sentence\s*reference",
        r"criminal\s*appeal",
    ]),
    ("Criminal - Revision", [
        r"crl\.?\s*revision", r"jail\s*revision",
    ]),
    ("Criminal - Misc / Proceedings", [
        r"crl\.?\s*misc", r"crl\.?\s*original", r"criminal\s*original",
        r"quash", r"registration\s*of\s*case", r"\bfir\b",
        r"investigation", r"discharge", r"remand", r"remission",
        r"superdari", r"haras+ment", r"anti-?terroris", r"\bata\b",
        r"\bnab\b", r"narcotic", r"\bcnsa\b", r"murder\s*reference",
        r"transfer\s*application\s*\(crl", r"anti-?corruption",
        r"\bfia\b", r"criminal\s*proceedings", r"illegal\s*dispossession",
        r"exhumation", r"post\s*mortem", r"sentence", r"sureties",
        r"suo\s*moto", r"\bfree-?will\b", r"non\s*prosecution",
        r"\b491\b", r"\b417\b", r"\b526\b", r"\b561-?a\b",
        r"prosecution", r"death\s*sentence", r"imprisonment", r"\br\.i\b",
        r"t\.?a\.?\s*\(crl", r"arrest\s*of",
    ]),
    ("Civil Revision", [
        r"civil\s*revision", r"115\s*c\.?p\.?c",
    ]),
    ("Civil Appeal (RFA/FAO/RSA)", [
        r"\br\.?f\.?a\b", r"\bf\.?a\.?o\b", r"\br\.?s\.?a\b",
        r"regular\s*first\s*appeal", r"regular\s*second\s*appeal",
        r"first\s*appeal\s*against\s*order", r"\bpla\b",
        r"leave\s*to\s*appeal", r"second\s*appeal",
    ]),
    ("Civil Suit / Execution", [
        r"\bc\.?o\.?s\b", r"civil\s*original\s*suit", r"execution",
        r"\befa\b", r"civil\s*suit",
    ]),
    ("Civil Miscellaneous / Review", [
        r"\bc\.?m\.?\s*\(civil\)", r"12\s*\(?2\)?\s*c\.?p\.?c",
        r"transfer\s*application\s*\(civil", r"review\s*application",
        r"cross\s*objection", r"objection\s*case", r"civil\s*petition",
        r"\breview\b", r"civil\s*misc",
    ]),
    ("Company / Commercial / IP", [
        r"commercial", r"compan(y|ies)", r"intellectual\s*property",
        r"trade\s*mark", r"trademark", r"patent", r"copy\s*right",
        r"arbitration", r"c\.o\.\s*\(commercial", r"registered\s*design",
    ]),
    ("Rent Matters", [
        r"\brent\b",
    ]),
    ("Labor & Employment", [
        r"\blabor\b", r"\blabour\b", r"\bnirc\b", r"\bplat\b", r"\beobi\b",
        r"social\s*security", r"payment\s*of\s*wages", r"labor\s*court",
        r"labour\s*court", r"termination",
    ]),
    ("Election Matters", [
        r"election",
    ]),
    ("Immigration & Citizenship", [
        r"immigration", r"passport", r"exit\s*control", r"citizenship",
        r"identity\s*card", r"c\.?n\.?i\.?c", r"n\.?i\.?c\.",
        r"\be\.?c\.?l\.?\b", r"travel",
    ]),
    ("Educational Institution", [
        r"education", r"university", r"universities", r"examination",
        r"admission", r"higher\s*education\s*commission",
    ]),
    ("Religious & Auqaf Matters", [
        r"religio", r"auqaf", r"\bhajj\b", r"umrah", r"tazia",
    ]),

    # --- Writ / procedural subject buckets ---------------------------------
    ("Writ - Service Matters", [
        r"\bservice\b", r"recruitment", r"promotion", r"seniority",
        r"pension", r"salary", r"posting\b", r"regulariz", r"disciplinary",
        r"dismissal", r"suspension", r"inquir", r"allotment\s*of\s*quarter",
        r"allotment\s*of\s*govt", r"penalty", r"appointment",
        r"retirement", r"deceased.*quota", r"\bquota\b",
    ]),
    ("Writ - Land Matters", [
        r"\bland\b", r"mutation", r"demarcation", r"partition",
        r"allotment\s*of\s*land", r"colonization", r"revenue\s*record",
        r"acquisition", r"lamberdari", r"proprietary", r"propriety",
        r"land\s*revenue\s*act", r"land\s*reform", r"federal\s*land\s*commission",
        r"\bmbr\b", r"property\s*matter",
    ]),
    ("Writ - Local Government", [
        r"local\s*government", r"town\s*municipal", r"\btma\b",
        r"market\s*committee", r"seal(ing)?[-/]?de-?seal", r"cattle\s*market",
        r"petrol\s*pump", r"wheat\s*quota", r"food\s*stuff", r"\bfood\b",
        r"encroachment", r"signboard", r"maps\s*and\s*buildings",
        r"illegal\s*construction", r"\bdemolition\b",
    ]),
    ("Writ - Development Authority", [
        r"\blda\b", r"\bdha\b", r"\bfda\b", r"\brda\b", r"cantonment",
        r"kachi\s*abadi", r"development\s*author", r"\bpgehf\b",
        r"housing\s*&?\s*physical\s*planning",
    ]),
    ("Writ - Regulatory Authorities", [
        r"\bogra\b", r"\bnepra\b", r"\bppsc\b", r"\bsecp\b", r"\bppra\b",
        r"\bpemra\b", r"\bpsqca\b", r"competition\s*com", r"bar\s*council",
        r"\bnha\b", r"co-?operative", r"regulatory\s*author", r"\bperpa\b",
        r"\bnerpa\b", r"national\s*tariff\s*commission", r"stock\s*exchan",
        r"civil\s*aviation", r"text\s*book\s*board", r"\bfpsc\b",
        r"anti[\s-]*dumping", r"\bcoop\.?\b", r"services\s*tribunal",
    ]),
    ("Writ - Utility Services", [
        r"\bwapda\b", r"\bsngpl\b", r"\bwasa\b", r"electricity",
        r"utility\s*service", r"incorrect\s*billing", r"detection\s*bill",
    ]),
    ("Transport Matters", [
        r"transport", r"bus\s*stand", r"route\s*permit", r"motor\s*vehicle",
    ]),
    ("Canal, Environment & Settlement", [
        r"canal", r"drainage", r"environment", r"settlement",
        r"evacuee\s*trust", r"board\s*of\s*revenue", r"rehabilitation",
        r"border\s*area", r"water\s*course", r"watercourse",
        r"distribution\s*of\s*water", r"irrigation", r"supply\s*of\s*water",
    ]),
    ("Writ - Miscellaneous / General", [
        r"public\s*interest\s*litigation", r"\bpil\b", r"ombudsman",
        r"auction", r"policy\s*rules?\s*regulations?", r"payment\s*of\s*dues",
        r"sugar\s*cane", r"mines?\s*and\s*minerals?", r"insurance",
        r"drug\s*(laws|act)", r"licensing", r"tender\b", r"consumer\s*court",
        r"import\s*export", r"foreign\s*exchange", r"stamp\s*act",
        r"electricity\s*duty", r"information\s*&?\s*communication",
        r"telecommunication", r"motion\s*pictures?", r"liquidation\s*board",
        r"quo\s*warranto", r"dummy\s*cat", r"overseas\s*pakistanis",
        r"military\s*law", r"temporary\s*injunction", r"permanent\s*injun",
        r"specific\s*performance", r"stay\b", r"evidence\b", r"possession\b",
        r"declaration\b", r"amendment\b", r"succession\s*certificate",
        r"release\s*of\s*money", r"direction\s*to\s*subordinate",
        r"direction\s*to\s*m\.?b\.?r", r"medical\s*board",
        r"\bwrit\s*petition\b", r"\bwrit\b", r"\bica\b",
    ]),

    # --- Administrative / listing-status labels (not real subject matter) --
    ("Administrative / Listing Status", [
        r"notice\s*cases", r"motion\s*cases", r"pre-?admission",
        r"old\s*cases", r"red\s*cause\s*list", r"fresh\s*cases",
        r"video\s*link", r"principal\s*seat", r"\bbench\b",
        r"non\s*prosecution", r"cases\s*through",
    ]),

    # Short, generic "what happened to the order" labels used mainly by
    # Balochistan HC's terser cause-list format, with no further subject
    # context to classify by.
    ("General Appeal / Revision (Unspecified)", [
        r"against\s*(the\s+)?order", r"against\s*(the\s+)?judge?ment",
        r"against\s*notic", r"against\s*notif", r"impugned",
        r"\bdirection\b", r"interim\s*order", r"office\s*order",
        r"against\s*(the\s+)?(seal|demolition|enquiry|result|decision|letter|construction)",
        r"case\s*transfer", r"transfer\s*of\s*case",
    ]),

    # Fully generic single-word / bare labels with no further context —
    # send to Other rather than guessing.
]

# Fallback bucket for anything not matched by the rules above.
_OTHER_BUCKET = "Other / Uncategorized"

# Precompile all patterns for speed.
_COMPILED_RULES = [
    (bucket, re.compile("|".join(patterns), re.IGNORECASE))
    for bucket, patterns in CATEGORY_RULES
]


@lru_cache(maxsize=4096)
def normalize_category(raw_category) -> str:
    """
    Map a single raw Case_Category string to its normalized Category_Group.
    Cached (per-process) since the dataset has only ~2,000 distinct raw
    values repeated across ~340,000 rows.
    """
    if raw_category is None or (isinstance(raw_category, float) and pd.isna(raw_category)):
        return _OTHER_BUCKET
    text = str(raw_category).strip()
    if not text:
        return _OTHER_BUCKET
    for bucket, pattern in _COMPILED_RULES:
        if pattern.search(text):
            return bucket
    return _OTHER_BUCKET


def add_normalized_category(df: pd.DataFrame, source_col: str = "Case_Category",
                             target_col: str = "Category_Group") -> pd.DataFrame:
    """
    Adds a `Category_Group` column to df, computed by applying
    normalize_category() to every unique value in `source_col` once
    (via a mapping dict), then broadcasting — much faster than calling
    .apply() row-by-row on 300k+ rows.
    """
    unique_vals = df[source_col].dropna().unique()
    mapping = {v: normalize_category(v) for v in unique_vals}
    df[target_col] = df[source_col].map(mapping).fillna(_OTHER_BUCKET)
    return df


def normalization_coverage_report(df: pd.DataFrame, source_col: str = "Case_Category",
                                   target_col: str = "Category_Group") -> pd.DataFrame:
    """
    Returns a small summary dataframe: for each normalized bucket, how many
    distinct raw categories and how many total rows fall into it. Useful for
    auditing how much volume ends up in 'Other / Uncategorized' and where to
    extend the rules next.
    """
    if target_col not in df.columns:
        df = add_normalized_category(df, source_col, target_col)
    g = df.groupby(target_col).agg(
        distinct_raw_categories=(source_col, "nunique"),
        total_rows=(source_col, "size"),
    ).sort_values("total_rows", ascending=False)
    g["pct_of_total"] = (g["total_rows"] / len(df) * 100).round(2)
    return g.reset_index()
