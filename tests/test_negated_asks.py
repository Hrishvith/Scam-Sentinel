"""Bank safety messages ("we will NEVER ask you to transfer money / share your OTP") must not raise a scam alert,
while scams that also use "don't" ("don't worry, just transfer the money") must still be caught."""
import pytest

from detector import detect_rules
from live import RiskTracker

SAFETY_MESSAGES = [
    "Your bank will never ask you to transfer money or share OTP. If anyone asks, hang up and call 1930.",
    "we will never ask you to download anydesk or share your otp",
    "dear customer beware of fraud calls never share your otp or card details we will never ask you to transfer money "
    "stay safe thank you",
    "आपका बैंक कभी भी आपसे पैसे ट्रांसफर करने को नहीं कहेगा। अपना ओटीपी किसी को न बताएं।",
    "किसी को भी पैसे ट्रांसफर मत कीजिए और ओटीपी किसी को मत बताइए",
    "ಯಾರಿಗೂ ಹಣ ಟ್ರಾನ್ಸ್‌ಫರ್ ಮಾಡಬೇಡಿ, ಒಟಿಪಿ ಹಂಚಿಕೊಳ್ಳಬೇಡಿ",
    "do not install any app if a caller asks you to and never share your otp",
]

SCAMS = [
    "dont tell anyone send money to this account immediately we are from the police",
    "don't panic sir, transfer five lakh rupees now or you will be arrested",
    "पुलिस बोल रहा हूँ, घबराइए मत, पैसे ट्रांसफर कीजिए नहीं तो गिरफ्तार हो जाएंगे",     # "otherwise arrested"
    "ನಾವು ಪೊಲೀಸ್, ಭಯಪಡಬೇಡಿ, ಹಣ ಟ್ರಾನ್ಸ್‌ಫರ್ ಮಾಡಿ ಇಲ್ಲದಿದ್ದರೆ ಅರೆಸ್ಟ್",                  # "otherwise arrest"
    "I will never ask for your money just download anydesk and tell me the otp",   # "just" starts a new instruction
    "sir I am from cyber crime branch do not disconnect the call download anydesk now",
]


@pytest.mark.parametrize("text", SAFETY_MESSAGES)
def test_bank_safety_message_is_not_a_scam(text):
    det = detect_rules(text)
    assert det.level == "low", (det.score, det.tactics)
    assert not det.tactics.keys() & {"payment", "remote_access", "otp_request"}


@pytest.mark.parametrize("text", SCAMS)
def test_scam_using_dont_is_still_caught(text):
    assert detect_rules(text).level != "low"


def test_spoken_bank_caution_never_alerts_in_the_live_tracker():
    """The live mode scores the speech-to-text pieces as they arrive (lowercase, no punctuation)."""
    tracker = RiskTracker()
    lines = ["dear customer beware of fraud calls", "never share your otp or card details",
             "we will never ask you to transfer money", "stay safe thank you"]
    alerts = [tracker.add(line, i * 3.0) for i, line in enumerate(lines)]
    assert alerts == [None] * 4 and tracker.det.level == "low"
