"""The number check: every number in AI text must come from the input data."""
import pytest

from app.services.ai.number_check import extract_numbers, unverified_numbers, verify

FACTS = {
    "top_rules": [{
        "if_bought": "GREEN REGENCY TEACUP AND SAUCER",
        "then_also_bought": "ROSES REGENCY TEACUP AND SAUCER",
        "confidence": 0.786,
        "support": 0.1834,
        "lift": 20.126,
    }],
    "revenue": 750092.05,
    "product": "15CM CHRISTMAS GLASS BALL 20 LIGHTS",
    "date_to": "2011-12-09",
    "suggested_discount_options_pct": [5, 10, 15],
    "bundle_id": "B001",
}


@pytest.mark.parametrize("text", [
    "Teacups are bought together in 18% of baskets.",          # 0.1834 -> 18%
    "They appear together in 18.3% of baskets.",               # 0.1834 -> 18.3%
    "Confidence is 78.6% and lift is 20.1.",                   # fraction -> percent, rounding
    "Confidence is 79%, lift about 20.",                       # coarser rounding
    "Confidence 0.79.",                                         # rounded fraction
    "Revenue was $750,092 in total.",                          # currency + thousands separator
    "Revenue was 750,092.05.",
    "Revenue was about 750k.",                                  # k suffix
    "Revenue was 0.75m.",                                       # m suffix
    "Try a bundle at 10% off.",                                 # discount option from the data
    "The 15CM glass ball with 20 lights sells well.",           # numbers inside product names
    "Data runs to December 2011.",                              # year from a date string
    "Bundle B001 is the strongest.",                            # ids inside words are ignored
    "1. First point\n2. Second point",                          # list markers are ignored
    "No numbers here at all.",
])
def test_accepts_numbers_from_the_data(text):
    ok, bad = verify(text, FACTS)
    assert ok, bad


@pytest.mark.parametrize("text, invented", [
    ("Teacups are bought together in 25% of baskets.", "25%"),
    ("Revenue grew by 12% last month.", "12%"),
    ("Try a bundle at 20% off.", "20%"),
    ("Revenue was $812,400.", "$812,400"),
    ("Lift is 21.5.", "21.5"),
    ("Confidence is 1.", "1"),                                  # a whole number must not round 0.786
    ("This could add 4,000 in sales.", "4,000"),
])
def test_rejects_invented_numbers(text, invented):
    ok, bad = verify(text, FACTS)
    assert not ok
    assert invented in bad


def test_checks_every_text_in_a_list():
    ok, bad = verify(["Lift is 20.1.", "Revenue rose 7%."], FACTS)
    assert not ok and bad == ["7%"]


def test_extract_numbers_parses_formats():
    nums = {raw: (value, mult, pct) for raw, value, _, mult, pct in extract_numbers("$4.5k, 18%, 1,234.5 and 3m")}
    assert nums["$4.5k"][:2] == (4.5, 1000.0)
    assert nums["18%"][2] is True
    assert nums["1,234.5"][0] == 1234.5
    assert nums["3m"][1] == 1_000_000


def test_evidence_can_be_a_list_of_sources():
    assert unverified_numbers("You asked about the top 5; the first has 42 orders.", ["top 5 products", {"orders": 42}]) == []


def test_numbers_spelled_out_in_words_are_flagged():
    facts = {"support_pct": 10.6, "confidence_pct": 62.4}
    ok, bad = verify("Tea is bought with biscuits in sixty two point four percent of baskets.", facts)
    assert not ok and bad
    assert not verify("About eighty six customers are champions.", facts)[0]
    assert not verify("Revenue share is twenty-two percent.", facts)[0]
    assert not verify("Support is ten percent.", facts)[0]


def test_small_counts_in_words_are_still_allowed():
    facts = {"support_pct": 10.6}
    assert verify("Two products sell together in 10.6% of baskets, one of them is tea.", facts)[0]
