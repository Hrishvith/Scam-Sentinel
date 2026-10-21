import array
import io
import math
import wave

import pytest

import eval_detector
from audio_utils import split_on_pauses
from corpus import CALLS, LANGS, script_text
from detector import detect_rules


def speechlike(pattern: list[tuple[str, float]], rate: int = 8000, noise: int = 0) -> bytes:
    """'s' = loud 300 Hz tone (speech stand-in), 'q' = quiet; optional constant noise floor."""
    out = array.array("h")
    n = 0
    for kind, seconds in pattern:
        for _ in range(int(rate * seconds)):
            tone = 8000 * math.sin(2 * math.pi * 300 * n / rate) if kind == "s" else 0
            out.append(int(tone + (noise if n % 2 else -noise)))
            n += 1
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(out.tobytes())
    return buf.getvalue()


# ---- segmentation ------------------------------------------------------------------
@pytest.mark.parametrize("noise", [0, 1500])
def test_split_on_pauses_cuts_between_utterances_and_drops_silence(noise):
    wav = speechlike([("q", 1.0), ("s", 2.0), ("q", 0.6), ("s", 3.0), ("q", 0.2), ("s", 1.0), ("q", 1.0)], noise=noise)
    segs = split_on_pauses(wav)
    starts = [round(s, 1) for s, _ in segs]
    assert starts == [0.5, 3.3]           # leading silence dropped; the 0.2 s gap is not a cut
    assert len(segs) == 2


def test_split_on_pauses_caps_long_utterances():
    segs = split_on_pauses(speechlike([("s", 30.0)]), max_seconds=12)
    assert [round(s) for s, _ in segs] == [0, 12, 24]


def test_split_on_pauses_falls_back_without_level_contrast():
    flat = speechlike([("q", 5.0)], noise=3)  # nothing speech-like: plain fixed-size chunks
    assert [s for s, _ in split_on_pauses(flat, max_seconds=2)] == [0.0, 2.0, 4.0]


# ---- detector regressions from the Phase 2 evaluation --------------------------------
@pytest.mark.parametrize("call", [c for c in CALLS if c["label"] == "benign"], ids=lambda c: c["id"])
def test_benign_corpus_calls_stay_low(call):
    assert detect_rules(script_text(call)).level == "low"


@pytest.mark.parametrize("call", [c for c in CALLS if c["label"] == "scam"], ids=lambda c: c["id"])
def test_scam_corpus_calls_are_high_with_expected_tactics(call):
    det = detect_rules(script_text(call))
    assert det.level == "high" and set(call["expect"]) <= det.tactics.keys(), det.to_dict()


def test_hinglish_awareness_survives_share_mat_heard_as_share_mark():
    text = ("ye aapke bank ki taraf se ek zaruri message hai apna otp pin your password kabhi bhee kisi ke saath "
            "share mark kijiye koi maange toh cyber crime helpline pay complaint")  # real Prisma output
    assert detect_rules(text).level == "low"


def test_scammer_saying_dont_share_is_not_discounted():
    det = detect_rules("Your account will be blocked today. Tell me the OTP now and do not share it with anyone else.")
    assert det.level == "high" and not any("awareness" in n for n in det.notes)


def test_delivery_otp_with_payment_pressure_is_still_flagged():
    det = detect_rules("I am from the courier. Tell me the delivery OTP and send money by UPI immediately.")
    assert det.level == "high"


@pytest.mark.parametrize("text,tactic", [
    ("ನಿಮ್ಮ ಫೋನಿಗೆ ಬಂದಿರುವ ಒ ಟಿ ಪಿ ಹೇಳಿ", "credentials"),     # Prisma spells acronyms letter by letter
    ("ನಿಮ್ಮ ಕೆ ವೈ ಸಿ ಅವಧಿ ಮುಗಿದಿದೆ", "lure"),
    ("abhi any desk app download karo", "remote_access"),
    ("call khat mat karna aur kisi ko mat bataana", "secrecy"),  # observed ASR spellings
    ("aaj raat aapka account block ho jayega", "threat"),
    ("ಈಗಲೇ ಎನಿಡೆಸ್ ಆ್ಯಪ್ ಡೌನ್ ಲೋಡ್ ಮಾಡಿ", "remote_access"),   # clipped brand + split word (noisy kn)
    ("ನಿಮ್ಮ ಪಾಸ್ ವರ್ಡ್ ಹೇಳಿ", "credentials"),                    # spaces are optional in Indic keywords
    ("मैं साइबर क्राइम से इंस्पेक्टर बोल रहा हूँ", "authority"),
])
def test_observed_prisma_spellings_are_matched(text, tactic):
    assert tactic in detect_rules(text).tactics


def test_everyday_now_and_minutes_are_not_urgency():
    for text in ["Okay, I am coming in two minutes.", "अच्छा, मैं अभी नीचे आती हूँ।", "main abhi neeche aati hoon"]:
        assert "urgency" not in detect_rules(text).tactics


# ---- corpus and eval ---------------------------------------------------------------
def test_corpus_is_consistent():
    ids = [c["id"] for c in CALLS]
    assert len(ids) == len(set(ids))
    for c in CALLS:
        assert c["lang"] in LANGS and c["label"] in {"scam", "benign"} and c["id"].startswith(c["lang"] + "_")
        assert all(who in LANGS[c["lang"]]["voices"] for who, _ in c["lines"])
        assert (c["label"] == "scam") == bool(c.get("expect"))


def test_eval_reads_saved_and_pasted_transcripts(tmp_path):
    tmp_path = tmp_path / "real_transcripts"
    tmp_path.mkdir()
    (tmp_path / "kn_scam_kyc_noisy.json").write_text(
        '{"id": "kn_scam_kyc", "lang": "kn", "label": "scam", "condition": "noisy", '
        '"transcript": "ನಿಮ್ಮ ಖಾತೆ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ ಒ ಟಿ ಪಿ ತಕ್ಷಣ ಹೇಳಿ"}', encoding="utf-8")
    (tmp_path / "en_benign_pasted_call.txt").write_text("See you at lunch tomorrow.", encoding="utf-8")
    rows, groups = eval_detector.evaluate(eval_detector.load_samples(tmp_path))
    assert groups[("noisy", "kn")]["tp"] == 1 and groups[("pasted", "en")]["tn"] == 1
    m = eval_detector.metrics(groups[("all", "all")])
    assert m["recall"] == 1.0 and m["false_alarm_rate"] == 0.0
