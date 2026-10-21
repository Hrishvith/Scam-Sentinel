"""Spoken warnings. Digits in the helpline number are spaced so TTS reads them one by one."""
from __future__ import annotations

from detector import Detection
from tactics import TACTICS

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
