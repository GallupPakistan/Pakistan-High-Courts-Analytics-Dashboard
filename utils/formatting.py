"""
formatting.py

Small display-only text helpers. These clean up how raw data values are
shown in charts/tables without altering the underlying dataframe used for
filtering, grouping, or aggregation.
"""

import re

# The raw `Judge` field sometimes has a courtroom/block reference appended
# at the end, e.g.:
#   "Mr. Justice Khalid Ishaq | [ Justice S.A. Rahman Block - Court 39 ]"
# This strips that trailing "| [ ... ]" segment for display purposes only.
_JUDGE_BRACKET_SUFFIX = re.compile(r"\s*\|\s*\[[^\]]*\]\s*$")


def clean_judge_label(name) -> str:
    """Return the judge name with any trailing '| [ ... ]' block/courtroom
    reference removed, for use as a chart/table label."""
    if name is None:
        return ""
    text = str(name)
    return _JUDGE_BRACKET_SUFFIX.sub("", text).strip()
