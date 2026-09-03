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


# Raw Court_Room values come in a few different raw shapes, e.g.:
#   "Court No: 2"
#   "Court No. [ 1 ]"
#   "[ Chief Justice Block - Court 1 ]"
#   "[ Justice A.S. Salam Block - Court 30 ]"
# This produces a short, readable "Court N" or "Court N (Block Name)" label
# for charts — display only, the raw value is still what's grouped/counted.
_COURT_ROOM_PLAIN = re.compile(r"Court\s*No[.:]?\s*\[?\s*(\d+)\s*\]?", re.IGNORECASE)
_COURT_ROOM_BLOCK = re.compile(
    r"\[\s*(?:Justice\s+|Chief\s+Justice\s*)?(?P<block>.*?)\s*Block\s*-\s*Court\s*(?P<num>\d+)\s*\]",
    re.IGNORECASE,
)


def clean_court_room_label(name) -> str:
    """Shorten a raw Court_Room value to 'Court N' or 'Court N (Block)'."""
    if name is None:
        return ""
    text = str(name).strip()
    m = _COURT_ROOM_BLOCK.search(text)
    if m:
        block = m.group("block").strip()
        num = m.group("num")
        return f"Court {num} ({block})" if block else f"Court {num}"
    m = _COURT_ROOM_PLAIN.search(text)
    if m:
        return f"Court {m.group(1)}"
    return text
