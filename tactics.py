"""Scam tactics (Kannada / Hindi / English) used by the detector.

Each keyword is matched on normalised text. ASCII keywords match on word
boundaries (so "pin" never fires inside "spinning"); keywords starting with
"re:" are raw regexes. Prisma may emit English loan words in Latin or in the
local script, so both are listed. Tune this file against real transcripts.

Observed in Prisma transcripts (Phase 2): acronyms often come back letter by letter
("ಒ ಟಿ ಪಿ", "ಕೆ ವೈ ಸಿ"), brand names split ("any desk"), and Hinglish is lowercase Latin.
"""
from __future__ import annotations

TACTICS: dict[str, dict] = {
    "authority": {
        "weight": 1.5,
        "labels": {"kn": "ಪೊಲೀಸ್ ಅಥವಾ ಅಧಿಕಾರಿಯಂತೆ ನಟನೆ", "hi": "पुलिस या अफ़सर बनकर बात करना",
                   "en": "pretending to be police or an official"},
        # Courier companies are NOT authority (real delivery calls are common); they are under "lure".
        "keywords": ["ಪೊಲೀಸ್", "ಸಿಬಿಐ", "ಸಿ ಬಿ ಐ", "ಕಸ್ಟಮ್ಸ್", "ಟ್ರಾಯ್", "ಆರ್ಬಿಐ", "ಆರ್ ಬಿ ಐ", "ಸೈಬರ್ ಕ್ರೈಮ್", "ಸೈಬರ್ ಕ್ರೈಂ",
                     "ಇನ್ಸ್ಪೆಕ್ಟರ್", "ಆದಾಯ ತೆರಿಗೆ",
                     "पुलिस", "सीबीआई", "सी बी आई", "कस्टम", "ट्राई", "आरबीआई", "आर बी आई", "साइबर क्राइम",
                     "इंस्पेक्टर", "नारकोटिक्स", "इनकम टैक्स",
                     "police", "cbi", "c b i", "customs", "trai", "rbi", "r b i", "cyber crime", "cybercrime",
                     "narcotics", "income tax", "enforcement directorate", "inspector"],
    },
    "threat": {
        "weight": 2.5,
        "labels": {"kn": "ಬಂಧನ ಅಥವಾ ಕೇಸ್‌ನ ಬೆದರಿಕೆ", "hi": "गिरफ़्तारी या केस की धमकी",
                   "en": "threat of arrest or legal case"},
        "keywords": ["ಅರೆಸ್ಟ್", "ಬಂಧನ", "ವಾರೆಂಟ್", "ಜೈಲು", "ಕೇಸ್ ದಾಖಲ", "ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್", "ಖಾತೆ ಬ್ಲಾಕ್", "ಬ್ಲಾಕ್ ಆಗುತ್ತ",
                     "गिरफ्तार", "गिरफ़्तार", "अरेस्ट", "वारंट", "जेल", "केस दर्ज", "डिजिटल अरेस्ट", "खाता बंद",
                     "ब्लॉक हो जाएगा",
                     "arrest", "arrested", "warrant", "jail", "digital arrest", "case registered", "case has been",
                     "account will be blocked", "sim will be blocked", "legal action",
                     # Hinglish (Latin-script Hindi)
                     "account block", "block ho jayega", "block ho jaega", "giraftar", "giraftari"],
    },
    "urgency": {
        "weight": 1.0,
        "labels": {"kn": "ತುರ್ತು ಒತ್ತಡ", "hi": "जल्दबाज़ी का दबाव", "en": "urgent pressure"},
        # Bare "now" (अभी / abhi) and "in two minutes" are everyday speech, so they are not listed.
        "keywords": ["ತಕ್ಷಣ", "ಈಗಲೇ", "ಇಲ್ಲದಿದ್ದರೆ", "ಅರ್ಧ ಗಂಟೆ",
                     "तुरंत", "अभी के अभी", "वरना", "जल्दी", "घंटे के अंदर", "घंटे में",
                     "immediately", "right now", "urgent", "urgently", "or else",
                     "re:(within|in the next)\\s+(\\w+\\s+){0,2}(minutes|minute|hours|hour)",
                     # Hinglish
                     "turant", "jaldi", "abhi ke abhi", "fauran", "foran", "warna"],
    },
    "secrecy": {
        "weight": 2.0,
        "labels": {"kn": "ಯಾರಿಗೂ ಹೇಳಬೇಡಿ ಎನ್ನುವ ಒತ್ತಡ", "hi": "किसी को न बताने का दबाव",
                   "en": "asking you to keep it secret or stay on the line"},
        "keywords": ["ಯಾರಿಗೂ ಹೇಳ", "ಕರೆ ಕಟ್ ಮಾಡಬೇಡಿ", "ಲೈನ್‌ನಲ್ಲೇ ಇರಿ", "ಗೌಪ್ಯ",
                     "किसी को मत बताना", "किसी को न बताएं", "किसी को नहीं बताना", "कॉल कट मत", "लाइन पर बने रहें",
                     "वीडियो कॉल पर रहें", "गोपनीय",
                     "don't tell anyone", "do not tell anyone", "dont tell anyone", "stay on the line",
                     "do not disconnect", "don't disconnect", "keep this confidential", "keep it secret",
                     # Hinglish
                     "re:kisi\\s+ko\\s+(mat|matt|na|nahi|nahin)\\s+bat",   # batana / bataana / batao
                     "re:(call|phone)\\s+(cut|kat|khat|kaat)\\s+mat"],
    },
    "credentials": {
        "weight": 3.0,
        "labels": {"kn": "ಒಟಿಪಿ ಅಥವಾ ಪಿನ್ ಕೇಳುವುದು", "hi": "ओटीपी या पिन माँगना",
                   "en": "asking for OTP, PIN or passwords"},
        "keywords": ["ಒಟಿಪಿ", "ಓಟಿಪಿ", "ಒ ಟಿ ಪಿ", "ಓ ಟಿ ಪಿ", "ಪಿನ್", "ಸಿವಿವಿ", "ಸಿ ವಿ ವಿ", "ಆಧಾರ್ ಸಂಖ್ಯೆ",
                     "ಪಾಸ್ವರ್ಡ್", "ಕಾರ್ಡ್ ನಂಬರ್",
                     "ओटीपी", "ओ टी पी", "पिन", "सीवीवी", "सी वी वी", "आधार नंबर", "पासवर्ड", "कार्ड नंबर",
                     "otp", "o t p", "pin", "cvv", "c v v", "password", "aadhaar number", "aadhar number",
                     "card number"],
    },
    "payment": {
        "weight": 3.0,
        "labels": {"kn": "ಹಣ ವರ್ಗಾಯಿಸಲು ಒತ್ತಾಯ", "hi": "पैसे ट्रांसफ़र करने का दबाव",
                   "en": "pushing you to transfer money"},
        "keywords": ["ಹಣ ಕಳುಹಿಸಿ", "ಹಣ ಹಾಕಿ", "ಟ್ರಾನ್ಸ್ಫರ್", "ಯುಪಿಐ", "ಯು ಪಿ ಐ", "ಸುರಕ್ಷಿತ ಖಾತೆ", "ಗಿಫ್ಟ್ ಕಾರ್ಡ್",
                     "पैसे भेज", "रुपये भेज", "ट्रांसफर", "यूपीआई", "यू पी आई", "सुरक्षित खाते", "गिफ्ट कार्ड",
                     "वेरिफिकेशन राशि",
                     "transfer money", "send money", "transfer the amount", "safe account", "verification amount",
                     "upi", "u p i", "gift card", "bitcoin", "pay immediately",
                     # Hinglish
                     "paise transfer", "paise bhejo", "paise bhej do", "paisa transfer"],
    },
    "remote_access": {
        "weight": 3.0,
        "labels": {"kn": "ಅಪರಿಚಿತ ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಲು ಹೇಳುವುದು", "hi": "अनजान ऐप इंस्टॉल करवाना",
                   "en": "asking you to install a remote-control app"},
        "keywords": ["ಎನಿಡೆಸ",  # also matches the clipped "ಎನಿಡೆಸ್" heard on noisy lines
                     "ಟೀಮ್ ವ್ಯೂವರ್", "ಆ್ಯಪ್ ಡೌನ್ಲೋಡ್", "ಅಪ್ಲಿಕೇಶನ್ ಇನ್ಸ್ಟಾಲ್",
                     "एनीडेस्क", "एनी डेस्क", "टीम व्यूअर", "ऐप डाउनलोड", "ऐप इंस्टॉल", "ऐप्लिकेशन डाउनलोड",
                     "anydesk", "any desk", "teamviewer", "team viewer", "quicksupport", "quick support",
                     "download the app", "install the app", "screen share",
                     # Hinglish
                     "app download karo", "app download kijiye", "app install karo"],
    },
    "lure": {
        "weight": 1.0,
        "labels": {"kn": "ಬಹುಮಾನ ಅಥವಾ ಕೆವೈಸಿ ಆಮಿಷ", "hi": "इनाम या केवाईसी का लालच",
                   "en": "prize, refund or KYC lure"},
        "keywords": ["ಲಾಟರಿ", "ಬಹುಮಾನ", "ಕೆವೈಸಿ", "ಕೆ ವೈ ಸಿ", "ರಿಫಂಡ್", "ಪಾರ್ಸೆಲ್", "ಕೊರಿಯರ್",
                     "लॉटरी", "इनाम", "केवाईसी", "के वाई सी", "रिफंड", "पार्सल", "कूरियर", "बिजली कट",
                     "lottery", "prize", "kyc", "k y c", "refund", "parcel", "courier", "fedex",
                     "electricity will be disconnected"],
    },
}

# Tactics that turn a request into pressure. When none of them is present, an OTP mention in an
# awareness message or a delivery hand-over is treated as context, not as an attack.
ESCALATION = {"threat", "secrecy", "payment", "remote_access"}

# Legitimate "tell me the OTP" situations: a delivery agent confirming a hand-over.
DELIVERY_PHRASES = [
    "delivery otp", "delivery o t p", "delivery code", "otp for delivery", "otp for the delivery",
    "डिलीवरी ओटीपी", "डिलीवरी वाला ओटीपी", "डिलीवरी का ओटीपी", "डिलीवरी ओ टी पी", "डिलीवरी वाला ओ टी पी",
    "ಡೆಲಿವರಿ ಒಟಿಪಿ", "ಡೆಲಿವರಿ ಓಟಿಪಿ", "ಡೆಲಿವರಿ ಒ ಟಿ ಪಿ", "ಡೆಲಿವರಿ ಓ ಟಿ ಪಿ",
]

# Awareness messages ("never share your OTP") should not read as a request for the OTP.
SAFETY_PHRASES = [
    "never share", "do not share", "don't share", "dont share", "never ask for",
    "ಹಂಚಿಕೊಳ್ಳಬೇಡಿ", "ಹಂಚಿಕೊಳ್ಳಬಾರದು",
    "साझा न करें", "साझा ना करें", "कभी न बताएं", "किसी को न दें",
    "re:share\\s+(mat|matt|mark|na|nahi|nahin)\\b",   # "share mat" is often heard as "share mark"
]

# One-word list for Prisma word boosting (letters only, one word per entry, per the docs).
BIAS_WORDS = ["OTP", "CBI", "arrest", "warrant", "police", "courier", "customs", "AnyDesk", "TeamViewer",
              "Aadhaar", "UPI", "KYC", "parcel", "digital", "ओटीपी", "सीबीआई", "वारंट", "अरेस्ट", "पुलिस",
              "ಒಟಿಪಿ", "ಸಿಬಿಐ", "ವಾರೆಂಟ್", "ಅರೆಸ್ಟ್", "ಪೊಲೀಸ್"]
