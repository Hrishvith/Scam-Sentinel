"""77 scam lines and 60 everyday lines in English, Hindi and Kannada (tests/stress_calls.py): every scam must
at least raise "suspicious", and no everyday line may alert, neither as a whole nor while it is being heard."""
import re

import pytest

from detector import detect_rules
from live import RiskTracker
from stress_calls import FRESH_NORMAL, FRESH_SCAMS, TUNING_NORMAL, TUNING_SCAMS

SCAMS = [(lang, t) for group in (TUNING_SCAMS, FRESH_SCAMS) for lang, lines in group.items() for t in lines]
NORMAL = [(lang, t) for group in (TUNING_NORMAL, FRESH_NORMAL) for lang, lines in group.items() for t in lines]


def heard(text: str) -> RiskTracker:
    tracker = RiskTracker()
    for i, piece in enumerate(p for p in re.split(r"(?<=[.,:?।])\s+", text) if p.strip()):
        tracker.add(piece, float(i))
    return tracker


@pytest.mark.parametrize("lang,text", SCAMS)
def test_scam_line_is_flagged(lang, text):
    det = detect_rules(text)
    assert det.level != "low", (lang, text, det)
    assert det.scam_type, (lang, text)                  # the warning can name the kind of scam


@pytest.mark.parametrize("lang,text", NORMAL)
def test_everyday_line_stays_quiet(lang, text):
    assert detect_rules(text).level == "low", (lang, text)
    assert heard(text).first_at == {}, (lang, text)


def test_every_language_is_covered():
    for group in (TUNING_SCAMS, FRESH_SCAMS, TUNING_NORMAL, FRESH_NORMAL):
        assert set(group) == {"en", "hi", "kn"} and all(len(v) >= 8 for v in group.values())
