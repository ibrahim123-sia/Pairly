"""Check that every number in AI-written text comes from the data we gave it.

The analytics code computes all numbers. The LLM only explains them, so any
number in its output must match a number in its input. A match allows the
usual ways people write numbers:

- rounding to the shown precision: 0.786 -> "0.79"; 20.126 -> "20"
- fractions as percentages: confidence 0.786 -> "78.6%" or "79%"
- thousands separators and currency symbols: 4512.3 -> "$4,512"
- k / m suffixes: 4512.3 -> "4.5k"

And it blocks the easy ways to slip a number through:

- a percentage only matches a fraction or a percentage value, so "20%" does
  not match a lift of 20 or the "20" in a product name
- a whole number only matches values of at least 1, so "1" does not match 0.786

Numbers inside words (bundle ids like "B001") are ignored, and so are leading
list markers ("1. ") in chat answers.
"""
import math
import re

# A number not glued to a letter/digit before it: optional sign/currency,
# digits with optional thousands separators and decimals, optional %, k, m.
_NUMBER = re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"(?P<sign>[-+−])?\s?(?:[$£€])?\s?"
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?P<suffix>\s?%|\s?[kK](?![A-Za-z])|\s?[mM](?![A-Za-z])|\s?bn(?![A-Za-z]))?"
)
_LIST_MARKER = re.compile(r"(?m)^\s*\d{1,2}[.)]\s+")
_PCT_KEY = re.compile(r"pct|percent|share|rate", re.I)
_MULTIPLIER = {"k": 1e3, "m": 1e6, "bn": 1e9}


def extract_numbers(text):
    """Return [(raw_text, value, decimals, multiplier, is_percent)] for each number in text."""
    if not text:
        return []
    text = _LIST_MARKER.sub("", str(text))
    out = []
    for m in _NUMBER.finditer(text):
        raw = m.group(0).strip()
        num = m.group("num").replace(",", "")
        decimals = len(num.split(".")[1]) if "." in num else 0
        suffix = (m.group("suffix") or "").strip().lower()
        out.append((raw, float(num), decimals, _MULTIPLIER.get(suffix, 1.0), suffix == "%"))
    return out


def collect_values(data):
    """Every number in a JSON-like structure as (value, is_percent_source).

    Numbers inside strings count too (product names such as
    "15CM CHRISTMAS GLASS BALL 20 LIGHTS", dates). A value is a percent source
    when its key looks like a percentage (..._pct, share, rate) or a string
    already wrote it with a % sign.
    """
    values = []

    def walk(x, pct_key=False):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            if math.isfinite(x):
                values.append((abs(float(x)), pct_key))
        elif isinstance(x, str):
            for _, v, _, mult, is_pct in extract_numbers(x):
                values.append((abs(v * mult), is_pct))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(k)
                walk(v, bool(_PCT_KEY.search(str(k))))
        elif isinstance(x, (list, tuple, set)):
            for v in x:
                walk(v, pct_key)

    walk(data)
    return values


def _matches(value, decimals, mult, is_pct, candidates):
    shown = value * mult
    tol = 0.5 * (10 ** -decimals) * mult + 1e-9
    for v, v_is_pct in candidates:
        targets = []
        if v <= 1:
            targets.append(v * 100)  # a fraction written as a percentage
        if not is_pct or v_is_pct:
            targets.append(v)
        for target in targets:
            if abs(shown - target) <= tol:
                if decimals == 0 and mult == 1 and target < 1 and shown != target:
                    continue  # "1" must not round 0.786
                return True
    return False


def unverified_numbers(text, data):
    """Numbers in text that cannot be traced to data. Empty list means the text passes."""
    candidates = collect_values(data)
    return [
        raw
        for raw, value, decimals, mult, is_pct in extract_numbers(text)
        if not _matches(value, decimals, mult, is_pct, candidates)
    ]


def verify(texts, data):
    """(ok, unmatched) for one string or a list of strings."""
    if isinstance(texts, str):
        texts = [texts]
    bad = []
    for t in texts:
        bad.extend(unverified_numbers(t, data))
    return (not bad), bad
