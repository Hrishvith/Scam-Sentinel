"""Spoken warnings. Digits in the helpline number are spaced so TTS reads them one by one."""
from __future__ import annotations

from detector import Detection
from tactics import SCAM_TYPES, SUSPICIOUS, TACTICS

HELPLINE = "1930"  # India's national cyber crime helpline
SITE = "cybercrime.gov.in"

T = {
    "kn": {
        "high": "ಎಚ್ಚರಿಕೆ! ಇದು ಮೋಸದ ಕರೆಯಂತೆ ಕಾಣುತ್ತಿದೆ. ಈಗಲೇ ಕರೆ ಕಟ್ ಮಾಡಿ. "
                "ಒಟಿಪಿ, ಪಿನ್ ಅಥವಾ ಹಣವನ್ನು ಯಾರಿಗೂ ಕೊಡಬೇಡಿ. "
                "ಸೈಬರ್ ಅಪರಾಧ ಸಹಾಯವಾಣಿ 1 9 3 0 ಗೆ ಕರೆ ಮಾಡಿ.",
        "medium": "ಎಚ್ಚರ! ಈ ಕರೆ ಅನುಮಾನಾಸ್ಪದವಾಗಿದೆ. ಒಟಿಪಿ ಅಥವಾ ಹಣ ಕೊಡುವ ಮೊದಲು ಮನೆಯವರನ್ನು ಕೇಳಿ.",
        "low": "ಈವರೆಗೆ ಮೋಸದ ಲಕ್ಷಣಗಳು ಕಂಡಿಲ್ಲ. ಆದರೂ ಒಟಿಪಿ ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.",
        "why": "ಕಾರಣ: ",
    },
    "hi": {
        "high": "सावधान! यह धोखाधड़ी वाली कॉल लग रही है। अभी कॉल काट दें। "
                "ओटीपी, पिन या पैसे किसी को न दें। "
                "साइबर क्राइम हेल्पलाइन 1 9 3 0 पर कॉल करें।",
        "medium": "सावधान! यह कॉल संदिग्ध है। ओटीपी या पैसे देने से पहले घर वालों से पूछें।",
        "low": "अब तक धोखाधड़ी के संकेत नहीं मिले। फिर भी ओटीपी किसी को न बताएं।",
        "why": "कारण: ",
    },
    "en": {
        "high": "Warning! This looks like a scam call. Hang up now. "
                "Do not share your OTP, PIN or send any money. "
                "Call the cyber crime helpline 1 9 3 0.",
        "medium": "Be careful! This call is suspicious. Before sharing an OTP or sending money, ask your family.",
        "low": "No scam signs so far. Still, never share your OTP with anyone.",
        "why": "Reason: ",
    },
}


# Phase 5a: the high-risk warning spoken in a family member's cloned voice (their own voice, with
# their consent; always labelled as an AI clone). Gender-neutral wording. REVIEW with native speakers.
FAMILY_WARNINGS = {
    "kn": "ಹಲೋ, ಇದು ನಾನು. ಈ ಕರೆ ಮೋಸದ ಕರೆ. ದಯವಿಟ್ಟು ಈಗಲೇ ಫೋನ್ ಕಟ್ ಮಾಡಿ. "
          "ಯಾರಿಗೂ ಒಟಿಪಿ ಅಥವಾ ಹಣ ಕೊಡಬೇಡಿ. ನಾನು ನಿಮಗೆ ಆಮೇಲೆ ಕರೆ ಮಾಡುತ್ತೇನೆ.",
    "hi": "हैलो, ये मैं हूँ। ये कॉल धोखाधड़ी है। प्लीज़ अभी फ़ोन काट दीजिए। "
          "किसी को ओटीपी या पैसे मत दीजिए। आपसे बाद में बात होगी।",
    "en": "Hi, it's me. This call is a scam. Please hang up right now. "
          "Don't give anyone your OTP or any money. I'll call you back.",
}


# Feature: "Stop! Don't say the numbers." Played when the protected person starts reading digits out
# after the caller asked for an OTP or money. REVIEW with native speakers.
GUARD_WARNINGS = {
    "kn": "ನಿಲ್ಲಿಸಿ! ಸಂಖ್ಯೆಗಳನ್ನು ಹೇಳಬೇಡಿ. ಒಟಿಪಿಯನ್ನು ಯಾರಿಗೂ ಹೇಳಬಾರದು.",
    "hi": "रुकिए! नंबर मत बोलिए। ओटीपी किसी को नहीं बताना है।",
    "en": "Stop! Don't say the numbers. Never tell anyone your OTP.",
}


# One line of advice per scam type, shown on the red warning screen. REVIEW with native speakers.
SCAM_TIPS = {
    "family_emergency": {
        "kn": "ಪೊಲೀಸರು ಯಾರನ್ನೂ ಬಿಡಿಸಲು ಹಣ ಕೇಳುವುದಿಲ್ಲ. ಕರೆ ಕಟ್ ಮಾಡಿ, ನಿಮ್ಮ ಮನೆಯವರಿಗೆ ನೀವೇ ಕರೆ ಮಾಡಿ.",
        "hi": "पुलिस किसी को छोड़ने के लिए पैसे नहीं मांगती। कॉल काटें और अपने घरवाले को खुद फ़ोन करें।",
        "en": "Police never ask for money to release anyone. Hang up and call your family member yourself."},
    "digital_arrest": {
        "kn": "'ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್' ಎಂಬುದೇ ಇಲ್ಲ. ನಿಜವಾದ ಪೊಲೀಸರು ಫೋನಿನಲ್ಲಿ ಹಣ ಕೇಳುವುದಿಲ್ಲ.",
        "hi": "'डिजिटल अरेस्ट' जैसा कुछ नहीं होता। असली पुलिस फ़ोन पर पैसे नहीं मांगती।",
        "en": "There is no such thing as a 'digital arrest'. Real police never ask for money on the phone."},
    "remote_access": {
        "kn": "ಯಾರು ಹೇಳಿದರೂ ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಬೇಡಿ. ಅದರಿಂದ ಅವರು ನಿಮ್ಮ ಫೋನನ್ನು ನಿಯಂತ್ರಿಸುತ್ತಾರೆ.",
        "hi": "किसी के कहने पर कोई ऐप इंस्टॉल न करें। इससे वे आपका फ़ोन चला सकते हैं।",
        "en": "Never install an app because a caller asks. It lets them control your phone."},
    "courier": {
        "kn": "ಕೊರಿಯರ್ ಕಂಪನಿಗಳು ಮತ್ತು ಕಸ್ಟಮ್ಸ್ ಫೋನಿನಲ್ಲಿ ದಂಡ ಕೇಳುವುದಿಲ್ಲ.",
        "hi": "कूरियर कंपनी या कस्टम्स फ़ोन पर जुर्माना नहीं मांगते।",
        "en": "Courier companies and customs never collect fines over the phone."},
    "kyc_bank": {
        "kn": "ಬ್ಯಾಂಕ್ ಎಂದಿಗೂ ಒಟಿಪಿ ಅಥವಾ ಪಿನ್ ಕೇಳುವುದಿಲ್ಲ. ಕಾರ್ಡ್ ಹಿಂದಿರುವ ಸಂಖ್ಯೆಗೆ ನೀವೇ ಕರೆ ಮಾಡಿ.",
        "hi": "बैंक कभी ओटीपी या पिन नहीं मांगता। कार्ड के पीछे लिखे नंबर पर खुद कॉल करें।",
        "en": "Your bank never asks for an OTP or PIN. Call the number on the back of your card yourself."},
    "prize": {
        "kn": "ಬಹುಮಾನ ಪಡೆಯಲು ಹಣ ಕಟ್ಟಬೇಕಾಗಿಲ್ಲ. ಇದು ಮೋಸ.",
        "hi": "इनाम पाने के लिए पैसे नहीं देने पड़ते। यह धोखा है।",
        "en": "You never have to pay to receive a prize. This is a scam."},
    "otp_theft": {
        "kn": "ಒಟಿಪಿ ನಿಮಗೆ ಮಾತ್ರ. ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.",
        "hi": "ओटीपी सिर्फ़ आपके लिए है। किसी को न बताएं।",
        "en": "An OTP is only for you. Never tell it to anyone."},
    "money": {
        "kn": "ಫೋನಿನಲ್ಲಿ ಒತ್ತಡ ಹಾಕಿ ಹಣ ಕೇಳಿದರೆ, ಮೊದಲು ಕರೆ ಕಟ್ ಮಾಡಿ, ಮನೆಯವರನ್ನು ಕೇಳಿ.",
        "hi": "फ़ोन पर दबाव डालकर पैसे मांगे जाएँ तो पहले कॉल काटें, घरवालों से पूछें।",
        "en": "If someone pressures you for money on a call, hang up first and ask your family."},
    None: {
        "kn": "ಅನುಮಾನ ಬಂದರೆ ಕರೆ ಕಟ್ ಮಾಡಿ. ನಿಜವಾದ ಸಂಸ್ಥೆಗೆ ನೀವೇ ಕರೆ ಮಾಡಿ.",
        "hi": "शक हो तो कॉल काटें और असली संस्था को खुद फ़ोन करें।",
        "en": "If in doubt, hang up and call the real organisation yourself."},
}


def lang_key(lang_code: str) -> str:
    return lang_code.split("-")[0] if lang_code.split("-")[0] in T else "en"


def alert_text(lang_code: str, det: Detection) -> str:
    """Spoken alert for the detection level. Low risk returns a short reassurance, not a warning."""
    return T[lang_key(lang_code)][det.level]


def top_reasons(lang_code: str, det: Detection, limit: int = 3) -> list[str]:
    """Human-readable tactic labels, heaviest first, in the listener's language."""
    lang = lang_key(lang_code)
    ranked = sorted(det.tactics, key=lambda n: -TACTICS[n]["weight"])[:limit]
    return [TACTICS[n]["labels"][lang] for n in ranked]


def scam_label(lang_code: str, kind: str | None) -> str:
    """Name of the scam type in the listener's language ("Fake police / digital arrest")."""
    lang = lang_key(lang_code)
    return SCAM_TYPES[kind]["labels"][lang] if kind in SCAM_TYPES else SUSPICIOUS[lang]


def scam_tip(lang_code: str, kind: str | None) -> str:
    """One line of advice for this kind of scam ("Police never ask for money to release anyone")."""
    return SCAM_TIPS.get(kind, SCAM_TIPS[None])[lang_key(lang_code)]


def tricks(lang_code: str, tactics) -> list[dict]:
    """Tactics spotted so far, heaviest first, as {id, label} for the live chips on the phone."""
    lang = lang_key(lang_code)
    ranked = sorted(tactics, key=lambda n: -TACTICS[n]["weight"])
    return [{"id": n, "label": TACTICS[n]["labels"][lang]} for n in ranked]
