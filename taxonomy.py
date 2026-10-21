"""Skills, areas and text normalisation shared by the extractor, matcher and replies."""
from __future__ import annotations

import re
import unicodedata

_KN_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize(text: str, keep_dots: bool = False) -> str:
    """NFC, lowercase, native digits -> ASCII, drop ZWNJ/ZWJ, collapse spaces."""
    t = unicodedata.normalize("NFC", text or "").lower()
    t = t.translate(_KN_DIGITS).translate(_DEV_DIGITS)
    t = t.replace("‌", "").replace("‍", "")
    if not keep_dots:
        t = t.replace(".", " ")
    return re.sub(r"\s+", " ", t).strip()


SKILLS: dict[str, dict] = {
    "electrician": {
        "labels": {"kn": "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "hi": "इलेक्ट्रीशियन", "en": "electrician"},
        "keywords": ["ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "ಎಲೆಕ್ಟ್ರಿಶಿಯನ್", "ಎಲೆಕ್ಟ್ರಿಕಲ್", "ವಿದ್ಯುತ್",
                     "इलेक्ट्रीशियन", "बिजली", "electrician", "electrical", "wireman"],
    },
    "plumber": {
        "labels": {"kn": "ಪ್ಲಂಬರ್", "hi": "प्लंबर", "en": "plumber"},
        "keywords": ["ಪ್ಲಂಬರ್", "ಪ್ಲಂಬಿಂಗ್", "प्लंबर", "plumber", "plumbing"],
    },
    "mason": {
        "labels": {"kn": "ಮೇಸ್ತ್ರಿ", "hi": "राजमिस्त्री", "en": "mason"},
        "keywords": ["ಮೇಸ್ತ್ರಿ", "ಗಾರೆ", "राजमिस्त्री", "मिस्त्री", "mason", "masonry", "mistri"],
    },
    "painter": {
        "labels": {"kn": "ಪೇಂಟರ್", "hi": "पेंटर", "en": "painter"},
        "keywords": ["ಪೇಂಟರ್", "ಪೇಂಟಿಂಗ್", "ಪೈಂಟರ್", "पेंटर", "पेंटिंग", "painter", "painting"],
    },
    "carpenter": {
        "labels": {"kn": "ಬಡಗಿ", "hi": "बढ़ई", "en": "carpenter"},
        "keywords": ["ಬಡಗಿ", "ಕಾರ್ಪೆಂಟರ್", "बढ़ई", "बढई", "कारपेंटर", "carpenter"],
    },
    "welder": {
        "labels": {"kn": "ವೆಲ್ಡರ್", "hi": "वेल्डर", "en": "welder"},
        "keywords": ["ವೆಲ್ಡರ್", "ವೆಲ್ಡಿಂಗ್", "वेल्डर", "welder", "welding"],
    },
    "driver": {
        "labels": {"kn": "ಡ್ರೈವರ್", "hi": "ड्राइवर", "en": "driver"},
        "keywords": ["ಡ್ರೈವರ್", "ಚಾಲಕ", "ड्राइवर", "driver"],
    },
    "security_guard": {
        "labels": {"kn": "ಸೆಕ್ಯುರಿಟಿ ಗಾರ್ಡ್", "hi": "सिक्योरिटी गार्ड", "en": "security guard"},
        "keywords": ["ಸೆಕ್ಯುರಿಟಿ", "ಗಾರ್ಡ್", "ಕಾವಲು", "सिक्योरिटी", "गार्ड", "security", "guard"],
    },
    "helper": {
        "labels": {"kn": "ಹೆಲ್ಪರ್", "hi": "हेल्पर", "en": "helper"},
        "keywords": ["ಹೆಲ್ಪರ್", "ಕೂಲಿ", "ಸಹಾಯಕ", "हेल्पर", "मजदूर", "मज़दूर",
                     "helper", "labour", "labourer", "laborer"],
    },
    "cook": {
        "labels": {"kn": "ಅಡುಗೆಯವರು", "hi": "रसोइया", "en": "cook"},
        "keywords": ["ಅಡುಗೆ", "ಕುಕ್", "रसोइया", "कुक", "cook"],
    },
}

# zone is used for "nearby" scoring: same zone => reachable commute.
AREAS: dict[str, dict] = {
    "peenya": {
        "labels": {"kn": "ಪೀಣ್ಯ", "hi": "पीन्या", "en": "Peenya"}, "zone": "north",
        "keywords": ["ಪೀಣ್ಯ", "पीन्या", "peenya"],
    },
    "yeshwanthpur": {
        "labels": {"kn": "ಯಶವಂತಪುರ", "hi": "यशवंतपुर", "en": "Yeshwanthpur"}, "zone": "north",
        "keywords": ["ಯಶವಂತಪುರ", "यशवंतपुर", "yeshwanthpur", "yeshwantpur"],
    },
    "hebbal": {
        "labels": {"kn": "ಹೆಬ್ಬಾಳ", "hi": "हेब्बल", "en": "Hebbal"}, "zone": "north",
        "keywords": ["ಹೆಬ್ಬಾಳ", "हेब्बल", "हेब्बाल", "hebbal"],
    },
    "malleshwaram": {
        "labels": {"kn": "ಮಲ್ಲೇಶ್ವರ", "hi": "मल्लेश्वरम", "en": "Malleshwaram"}, "zone": "north",
        "keywords": ["ಮಲ್ಲೇಶ್ವರ", "मल्लेश्वरम", "malleshwaram", "malleswaram"],
    },
    "whitefield": {
        "labels": {"kn": "ವೈಟ್‌ಫೀಲ್ಡ್", "hi": "व्हाइटफील्ड", "en": "Whitefield"}, "zone": "east",
        "keywords": ["ವೈಟ್ಫೀಲ್ಡ್", "ವೈಟ್ ಫೀಲ್ಡ್", "व्हाइटफील्ड", "वाइटफील्ड", "व्हाईटफील्ड", "whitefield"],
    },
    "kr_puram": {
        "labels": {"kn": "ಕೆ ಆರ್ ಪುರ", "hi": "के आर पुरम", "en": "KR Puram"}, "zone": "east",
        "keywords": ["ಕೆ ಆರ್ ಪುರ", "ಕೆಆರ್ ಪುರ", "के आर पुरम", "kr puram", "k r puram", "krpuram"],
    },
    "marathahalli": {
        "labels": {"kn": "ಮಾರತ್ತಹಳ್ಳಿ", "hi": "मराठाहल्ली", "en": "Marathahalli"}, "zone": "east",
        "keywords": ["ಮಾರತ್ತಹಳ್ಳಿ", "ಮಾರತಹಳ್ಳಿ", "मराठाहल्ली", "marathahalli", "marathalli"],
    },
    "electronic_city": {
        "labels": {"kn": "ಎಲೆಕ್ಟ್ರಾನಿಕ್ ಸಿಟಿ", "hi": "इलेक्ट्रॉनिक सिटी", "en": "Electronic City"}, "zone": "south",
        "keywords": ["ಎಲೆಕ್ಟ್ರಾನಿಕ್ ಸಿಟಿ", "इलेक्ट्रॉनिक सिटी", "electronic city"],
    },
    "bommasandra": {
        "labels": {"kn": "ಬೊಮ್ಮಸಂದ್ರ", "hi": "बोम्मसंद्रा", "en": "Bommasandra"}, "zone": "south",
        "keywords": ["ಬೊಮ್ಮಸಂದ್ರ", "बोम्मसंद्रा", "bommasandra"],
    },
    "jayanagar": {
        "labels": {"kn": "ಜಯನಗರ", "hi": "जयनगर", "en": "Jayanagar"}, "zone": "south",
        "keywords": ["ಜಯನಗರ", "जयनगर", "jayanagar"],
    },
    "banashankari": {
        "labels": {"kn": "ಬನಶಂಕರಿ", "hi": "बनशंकरी", "en": "Banashankari"}, "zone": "south",
        "keywords": ["ಬನಶಂಕರಿ", "बनशंकरी", "banashankari"],
    },
    "rajajinagar": {
        "labels": {"kn": "ರಾಜಾಜಿನಗರ", "hi": "राजाजीनगर", "en": "Rajajinagar"}, "zone": "west",
        "keywords": ["ರಾಜಾಜಿನಗರ", "राजाजीनगर", "rajajinagar"],
    },
}


def label(kind: dict, key: str | None, lang: str) -> str:
    if not key or key not in kind:
        return ""
    return kind[key]["labels"].get(lang, kind[key]["labels"]["en"])
