"""Paraphrases the rules were not written from, including the two cases an independent audit (9 Nov 2026)
typed into the public Practice page: a reworded OTP request that scored low, and police safety advice that
scored as a likely scam. Every scam here must at least raise "suspicious"; no safety message may."""
import pytest

from detector import detect_rules

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
