"""Paraphrases the rules were not written from, including the two cases an independent audit (9 Nov 2026)
typed into the public Practice page: a reworded OTP request that scored low, and police safety advice that
scored as a likely scam. Every scam here must at least raise "suspicious"; no safety message may."""
import re

import pytest

from detector import detect_rules
from live import RiskTracker

SCAMS = [
    # audit case 1: "verification code" instead of "OTP"
    "I am your bank relationship manager. Read the six digit verification code that just arrived so I can approve "
    "the refund.",
    "Sir please tell me the code you received on your phone, it is for your KYC update.",
    "Your son has met with an accident, he is in the hospital. Send money immediately to this UPI.",
    "To receive your refund just scan this QR code and enter your UPI PIN.",
    "I have sent a collect request, approve it now or your account will be blocked.",
    "Don't worry madam, just transfer the money to the safe account and you will be fine.",
    "I will never ask for money, just download AnyDesk so I can help you.",
    "Read me the OTP quickly, the police are coming.",
    "आपका केवाईसी खत्म हो गया है, जो वेरिफिकेशन कोड आया है वो बताइए",
    "ನಿಮ್ಮ ಖಾತೆ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ, ಬಂದಿರುವ ಒಟಿಪಿ ತಿಳಿಸಿ",
]

SAFE = [
    # audit case 2: repeated "never" and the phrase "safe account" in police safety advice
    "I am a police officer. Never share your OTP, never transfer money to a safe account, never install AnyDesk.",
    "Police advisory: never send money to anyone claiming to be from CBI over a video call.",
    "Never scan a QR code to receive money, you only scan to pay.",
    "RBI says do not share your PIN or CVV with anyone.",
    "Hi, this is the delivery person, please tell me the delivery OTP to hand over the parcel.",
    "Mom, I reached the hospital for my checkup, everything is fine.",
    "कभी भी किसी को अपना ओटीपी शेयर मत करें, बैंक कभी नहीं मांगता",
    "ಯಾರಿಗೂ ನಿಮ್ಮ ಒಟಿಪಿ ಹಂಚಿಕೊಳ್ಳಬೇಡಿ",
]


# Kannada / Hindi caution calls that raised scam alerts on the live site (reported 10 Nov 2026). They must stay
# quiet as a whole AND as live speech arrives, one pause-separated piece at a time.
CAUTIONS = [
    "ನಮಸ್ಕಾರ, ನಿಮ್ಮ ಒಟಿಪಿಯನ್ನು ಯಾರಿಗೂ ಹೇಳಬೇಡಿ. ಬ್ಯಾಂಕ್ ಯಾವತ್ತೂ ಒಟಿಪಿ ಕೇಳುವುದಿಲ್ಲ.",
    "ಪೊಲೀಸ್ ಇಲಾಖೆಯ ಸೂಚನೆ: ಒಟಿಪಿ ಯಾರಿಗೂ ಹೇಳಬೇಡಿ, ಹಣ ಕಳುಹಿಸಬೇಡಿ, ಎನಿಡೆಸ್ಕ್ ಆ್ಯಪ್ ಇನ್ಸ್ಟಾಲ್ ಮಾಡಬೇಡಿ.",
    "ಆರ್‌ಬಿಐ ಸೂಚನೆ. ನಿಮ್ಮ ಒಟಿಪಿ, ಪಿನ್, ಸಿವಿವಿ ಯಾರಿಗೂ ಕೊಡಬೇಡಿ. ಅನುಮಾನ ಬಂದರೆ 1930 ಗೆ ಕರೆ ಮಾಡಿ.",
    "ಯಾರಾದರೂ ಕರೆ ಮಾಡಿ ಒಟಿಪಿ ಕೇಳಿದರೆ ಹೇಳಬೇಡಿ, ಅದು ಮೋಸ. ಕರೆ ಕಟ್ ಮಾಡಿ.",
    "ಸೈಬರ್ ಕ್ರೈಮ್ ಪೊಲೀಸರಿಂದ ಎಚ್ಚರಿಕೆ: ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್ ಎಂಬುದು ಇಲ್ಲ. ಯಾರಿಗೂ ಒಟಿಪಿ ಅಥವಾ ಹಣ ಕೊಡಬೇಡಿ.",
    "ಇದು ನಿಮ್ಮ ಬ್ಯಾಂಕಿನಿಂದ ಒಂದು ಮುಖ್ಯ ಸೂಚನೆ. ನಿಮ್ಮ ಒಟಿಪಿ, ಪಿನ್ ಅಥವಾ ಪಾಸ್ವರ್ಡ್ ಅನ್ನು ಯಾರೊಂದಿಗೂ ಹಂಚಿಕೊಳ್ಳಬೇಡಿ.",
    "नमस्ते, अपना ओटीपी किसी को मत बताइए। बैंक कभी भी ओटीपी नहीं मांगता।",
    "पुलिस की चेतावनी: ओटीपी किसी को न बताएं, पैसे ट्रांसफर न करें, एनीडेस्क ऐप इंस्टॉल न करें।",
    "आरबीआई की सलाह। अपना ओटीपी, पिन, सीवीवी किसी को मत दीजिए। शक हो तो 1930 पर कॉल करें।",
    "अगर कोई फ़ोन करके ओटीपी मांगे तो मत बताइए, यह धोखा है। कॉल काट दीजिए।",
    "साइबर क्राइम पुलिस की चेतावनी: डिजिटल अरेस्ट जैसा कुछ नहीं होता। किसी को ओटीपी या पैसे मत दीजिए।",
    "ओटीपी किसी को भी नहीं बताना है, बैंक वाले को भी नहीं।",
    "RBI says: do not give your OTP, PIN or CVV to anyone.",
    "Cyber crime police warning: there is no such thing as digital arrest. Never send money to anyone.",
]


@pytest.mark.parametrize("text", CAUTIONS)
def test_caution_call_never_alerts_even_as_it_is_being_heard(text):
    assert detect_rules(text).level == "low", text
    tracker = RiskTracker()
    for i, piece in enumerate(re.split(r"(?<=[.,:।])\s+", text)):   # the way live speech arrives, at pauses
        tracker.add(piece, float(i))
    assert tracker.first_at == {}, (text, tracker.det)


def test_scams_that_use_the_same_words_are_still_caught():
    assert detect_rules("ಪೊಲೀಸ್ ಮಾತನಾಡುತ್ತಿದ್ದೇವೆ, ಯಾರಿಗೂ ಹೇಳಬೇಡಿ, ನಿಮ್ಮ ಒಟಿಪಿ ಹೇಳಿ").level == "high"
    assert detect_rules("पुलिस बोल रहा हूँ, किसी को मत बताइए, अपना ओटीपी बताइए").level == "high"
    assert detect_rules("Read me the OTP quickly, the police are coming.").level == "high"


@pytest.mark.parametrize("text", SCAMS)
def test_reworded_scam_is_flagged(text):
    assert detect_rules(text).level != "low", text


@pytest.mark.parametrize("text", SAFE)
def test_safety_advice_and_normal_calls_stay_quiet(text):
    assert detect_rules(text).level == "low", text


def test_the_reworded_otp_request_is_named_as_one():
    det = detect_rules(SCAMS[0])
    assert det.level == "high" and "otp_request" in det.tactics
    assert det.scam_type == "otp_theft"                    # not "fake prize": the advice must fit the trick
