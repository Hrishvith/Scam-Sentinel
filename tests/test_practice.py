"""Practice page: the quiz answers agree with the detector, and the free checker endpoint works."""
import json
from pathlib import Path

import pytest

from alerts import SCAM_TIPS, scam_tip, tricks
from detector import detect_rules
from tactics import SCAM_TYPES
from test_phone_relay import KEY, run

ITEMS = json.loads((Path(__file__).resolve().parents[1] / "web" / "practice.json").read_text(encoding="utf-8"))["items"]


@pytest.mark.parametrize("item", ITEMS, ids=lambda i: i["en"][:30])
@pytest.mark.parametrize("lang", ["en", "kn", "hi"])
def test_quiz_answer_matches_the_detector(item, lang):
    level = detect_rules(item[lang]).level
    assert (level != "low") == item["scam"], f"{lang}: detector says {level}"


@pytest.mark.parametrize("text", [
    "ಇದು ನಿಮ್ಮ ಬ್ಯಾಂಕಿನ ಸಂದೇಶ: ನಾವು ಎಂದಿಗೂ ನಿಮ್ಮ ಒಟಿಪಿ ಅಥವಾ ಪಿನ್ ಕೇಳುವುದಿಲ್ಲ. ಅದನ್ನು ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.",
    "हम कभी आपका ओटीपी या पिन नहीं मांगते। इसे किसी को न बताएं।",
])
def test_tell_nobody_your_otp_is_advice_not_secrecy(text):
    assert detect_rules(text).level == "low"


@pytest.mark.parametrize("text", [
    "ನಾನು ಪೊಲೀಸ್. ನಿಮ್ಮ ಒಟಿಪಿ ಯಾರಿಗೂ ಹಂಚಿಕೊಳ್ಳಬೇಡಿ. ಈ ಕರೆ ಬಗ್ಗೆ ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.",
    "I am from the police. Never share your OTP. Do not tell anyone about this.",
    "मैं पुलिस से हूँ। ओटीपी किसी को न बताएं। इस बारे में किसी को मत बताना।",
])
def test_keep_this_call_secret_is_still_secrecy(text):
    det = detect_rules(text)
    assert "secrecy" in det.tactics and det.level == "high"


def test_transfer_a_sum_in_english_is_a_payment_demand():
    assert "payment" in detect_rules("Transfer five lakh rupees now.").tactics
    assert "payment" not in detect_rules("I transferred to the Pune office last year.").tactics


def test_every_scam_type_has_a_tip_in_every_language():
    for kind in [*SCAM_TYPES, None]:
        assert all(SCAM_TIPS[kind][lang] for lang in ("kn", "hi", "en"))
    assert scam_tip("kn-IN", "unknown") == SCAM_TIPS[None]["kn"]


def test_tricks_are_ranked_and_labelled():
    t = tricks("en-IN", ["urgency", "authority", "payment"])
    assert [x["id"] for x in t][0] in ("authority", "payment") and all(x["label"] for x in t)


def test_checker_scores_typed_words_for_free(tmp_path):
    async def body(http, fake, _):
        assert "Spot the scam" in await (await http.get("/practice")).text()
        assert (await http.post("/api/check", json={"text": "hi"})).status == 200   # free check: no key needed
        res = await (await http.post("/api/check", json={
            "text": "This is the police. We have arrested your son. Transfer five lakh rupees now.", "lang": "en-IN"})).json()
        assert res["level"] == "high" and res["scam_type"] == "family_emergency"
        assert res["tip"].startswith("Police never ask") and any(t["id"] == "authority" for t in res["tricks"])
        safe = await (await http.post(f"/api/check?key={KEY}", json={"text": "See you at dinner", "lang": "kn-IN"})).json()
        assert safe["level"] == "low" and safe["tip"] is None and safe["tricks"] == []
        assert fake.connections == []                                   # no Gnani stream, no credits
    run(body, tmp_path)
