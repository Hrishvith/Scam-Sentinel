"""Scam tactics (Kannada / Hindi / English) used by the detector.

Each keyword is matched on normalised text. ASCII keywords match on word
boundaries (so "pin" never fires inside "spinning"); keywords starting with
"re:" are raw regexes. Prisma may emit English loan words in Latin or in the
local script, so both are listed. Tune this file against real transcripts.
"""
from __future__ import annotations

TACTICS: dict[str, dict] = {
    "authority": {
        "weight": 1.5,
        "labels": {"kn": "ಪೊಲೀಸ್ ಅಥವಾ ಅಧಿಕಾರಿಯಂತೆ ನಟನೆ", "hi": "पुलिस या अफ़सर बनकर बात करना",
                   "en": "pretending to be police or an official"},
        "keywords": ["ಪೊಲೀಸ್", "ಸಿಬಿಐ", "ಕಸ್ಟಮ್ಸ್", "ಕೊರಿಯರ್", "ಟ್ರಾಯ್", "ಆರ್ಬಿಐ", "ಸೈಬರ್ ಕ್ರೈಮ್", "ಆದಾಯ ತೆರಿಗೆ",
                     "पुलिस", "सीबीआई", "कस्टम", "कूरियर", "ट्राई", "आरबीआई", "साइबर क्राइम", "नारकोटिक्स", "इनकम टैक्स",
                     "police", "cbi", "customs", "courier", "fedex", "trai", "rbi", "cyber crime", "cybercrime",
                     "narcotics", "income tax", "enforcement directorate", "inspector"],
    },
    "threat": {
        "weight": 2.5,
        "labels": {"kn": "ಬಂಧನ ಅಥವಾ ಕೇಸ್‌ನ ಬೆದರಿಕೆ", "hi": "गिरफ़्तारी या केस की धमकी",
                   "en": "threat of arrest or legal case"},
        "keywords": ["ಅರೆಸ್ಟ್", "ಬಂಧನ", "ವಾರೆಂಟ್", "ಜೈಲು", "ಕೇಸ್ ದಾಖಲ", "ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್",
                     "गिरफ्तार", "गिरफ़्तार", "अरेस्ट", "वारंट", "जेल", "केस दर्ज", "डिजिटल अरेस्ट", "खाता बंद",
                     "arrest", "arrested", "warrant", "jail", "digital arrest", "case registered", "case has been",
                     "account will be blocked", "sim will be blocked", "legal action"],
    },
    "urgency": {
        "weight": 1.0,
        "labels": {"kn": "ತುರ್ತು ಒತ್ತಡ", "hi": "जल्दबाज़ी का दबाव", "en": "urgent pressure"},
        "keywords": ["ತಕ್ಷಣ", "ಈಗಲೇ", "ಇಲ್ಲದಿದ್ದರೆ", "ಅರ್ಧ ಗಂಟೆ",
                     "तुरंत", "अभी के अभी", "अभी", "वरना", "जल्दी", "घंटे के अंदर", "घंटे में",
                     "immediately", "right now", "urgent", "urgently", "or else",
                     "re:(within|in)\\s+(\\w+\\s+){0,2}(minutes|minute|hours|hour)"],
    },
    "secrecy": {
        "weight": 2.0,
        "labels": {"kn": "ಯಾರಿಗೂ ಹೇಳಬೇಡಿ ಎನ್ನುವ ಒತ್ತಡ", "hi": "किसी को न बताने का दबाव",
                   "en": "asking you to keep it secret or stay on the line"},
        "keywords": ["ಯಾರಿಗೂ ಹೇಳ", "ಕರೆ ಕಟ್ ಮಾಡಬೇಡಿ", "ಲೈನ್‌ನಲ್ಲೇ ಇರಿ", "ಗೌಪ್ಯ",
                     "किसी को मत बताना", "किसी को न बताएं", "किसी को नहीं बताना", "कॉल कट मत", "लाइन पर बने रहें",
                     "वीडियो कॉल पर रहें", "गोपनीय",
                     "don't tell anyone", "do not tell anyone", "dont tell anyone", "stay on the line",
                     "do not disconnect", "don't disconnect", "keep this confidential", "keep it secret"],
    },
    "credentials": {
        "weight": 3.0,
        "labels": {"kn": "ಒಟಿಪಿ ಅಥವಾ ಪಿನ್ ಕೇಳುವುದು", "hi": "ओटीपी या पिन माँगना",
                   "en": "asking for OTP, PIN or passwords"},
        "keywords": ["ಒಟಿಪಿ", "ಓಟಿಪಿ", "ಪಿನ್", "ಸಿವಿವಿ", "ಆಧಾರ್ ಸಂಖ್ಯೆ", "ಪಾಸ್ವರ್ಡ್", "ಕಾರ್ಡ್ ನಂಬರ್",
                     "ओटीपी", "पिन", "सीवीवी", "आधार नंबर", "पासवर्ड", "कार्ड नंबर",
                     "otp", "pin", "cvv", "password", "aadhaar number", "aadhar number", "card number"],
    },
    "payment": {
        "weight": 3.0,
        "labels": {"kn": "ಹಣ ವರ್ಗಾಯಿಸಲು ಒತ್ತಾಯ", "hi": "पैसे ट्रांसफ़र करने का दबाव",
                   "en": "pushing you to transfer money"},
        "keywords": ["ಹಣ ಕಳುಹಿಸಿ", "ಹಣ ಹಾಕಿ", "ಟ್ರಾನ್ಸ್ಫರ್", "ಯುಪಿಐ", "ಸುರಕ್ಷಿತ ಖಾತೆ", "ಗಿಫ್ಟ್ ಕಾರ್ಡ್",
                     "पैसे भेज", "रुपये भेज", "ट्रांसफर", "यूपीआई", "सुरक्षित खाते", "गिफ्ट कार्ड", "वेरिफिकेशन राशि",
                     "transfer money", "send money", "transfer the amount", "safe account", "verification amount",
                     "upi", "gift card", "bitcoin", "pay immediately"],
    },
    "remote_access": {
        "weight": 3.0,
        "labels": {"kn": "ಅಪರಿಚಿತ ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಲು ಹೇಳುವುದು", "hi": "अनजान ऐप इंस्टॉल करवाना",
                   "en": "asking you to install a remote-control app"},
        "keywords": ["ಎನಿಡೆಸ್ಕ್", "ಟೀಮ್ ವ್ಯೂವರ್", "ಆ್ಯಪ್ ಡೌನ್ಲೋಡ್", "ಅಪ್ಲಿಕೇಶನ್ ಇನ್ಸ್ಟಾಲ್",
                     "एनीडेस्क", "टीम व्यूअर", "ऐप डाउनलोड", "ऐप इंस्टॉल", "ऐप्लिकेशन डाउनलोड",
                     "anydesk", "teamviewer", "quicksupport", "download the app", "install the app", "screen share"],
    },
    "lure": {
        "weight": 1.0,
        "labels": {"kn": "ಬಹುಮಾನ ಅಥವಾ ಕೆವೈಸಿ ಆಮಿಷ", "hi": "इनाम या केवाईसी का लालच",
                   "en": "prize, refund or KYC lure"},
        "keywords": ["ಲಾಟರಿ", "ಬಹುಮಾನ", "ಕೆವೈಸಿ", "ರಿಫಂಡ್", "ಪಾರ್ಸೆಲ್",
                     "लॉटरी", "इनाम", "केवाईसी", "रिफंड", "पार्सल", "बिजली कट",
                     "lottery", "prize", "kyc", "refund", "parcel", "electricity will be disconnected"],
    },
}

# Awareness messages ("never share your OTP") should not read as a request for the OTP.
SAFETY_PHRASES = [
    "never share", "do not share", "don't share", "dont share", "never ask for",
    "ಹಂಚಿಕೊಳ್ಳಬೇಡಿ", "ಹಂಚಿಕೊಳ್ಳಬಾರದು",
    "साझा न करें", "साझा ना करें", "कभी न बताएं", "किसी को न दें",
]

# One-word list for Prisma word boosting (letters only, one word per entry, per the docs).
BIAS_WORDS = ["OTP", "CBI", "arrest", "warrant", "police", "courier", "customs", "AnyDesk", "TeamViewer",
              "Aadhaar", "UPI", "KYC", "parcel", "digital", "ओटीपी", "सीबीआई", "वारंट", "अरेस्ट", "पुलिस",
              "ಒಟಿಪಿ", "ಸಿಬಿಐ", "ವಾರೆಂಟ್", "ಅರೆಸ್ಟ್", "ಪೊಲೀಸ್"]
