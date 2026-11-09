"""137 scam lines and 115 everyday or caution lines in English, Hindi/Hinglish and Kannada/Kanglish
(tests/stress_calls.py): every scam must at least raise "suspicious", and no everyday line may alert, neither as a
whole nor while it is being heard (pieces at pauses, or 6-word pieces when there is no punctuation)."""
import re

import pytest

from detector import detect_rules
from live import RiskTracker
from stress_calls import (FRESH_NORMAL, FRESH_SCAMS, TRANSCRIPT_STYLE_NORMAL, TRANSCRIPT_STYLE_SCAMS, TUNING_NORMAL,
                          TUNING_SCAMS)

GROUPS_SCAM = (TUNING_SCAMS, FRESH_SCAMS, TRANSCRIPT_STYLE_SCAMS)
GROUPS_NORMAL = (TUNING_NORMAL, FRESH_NORMAL, TRANSCRIPT_STYLE_NORMAL)
SCAMS = [(lang, t) for group in GROUPS_SCAM for lang, lines in group.items() for t in lines]
NORMAL = [(lang, t) for group in GROUPS_NORMAL for lang, lines in group.items() for t in lines]


def pieces(text: str) -> list[str]:
    parts = [p for p in re.split(r"(?<=[.,:?।])\s+", text) if p.strip()]
    if len(parts) == 1:                                # no punctuation: speech recognition cuts at pauses
        words = text.split()
        parts = [" ".join(words[i:i + 6]) for i in range(0, len(words), 6)]
    return parts


def heard(text: str) -> RiskTracker:
    tracker = RiskTracker()
    for i, piece in enumerate(pieces(text)):
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
    for group in GROUPS_SCAM + GROUPS_NORMAL:
        assert set(group) == {"en", "hi", "kn"} and all(len(v) >= 8 for v in group.values())
