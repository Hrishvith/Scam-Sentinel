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
                     "पुलिस", "सीबीआई", "सी बी आई", "re:कस्टम(?!\\s?र)", "ट्राई", "आरबीआई", "आर बी आई", "साइबर क्राइम",
                     # (कस्टम = customs, but not inside कस्टमर = customer)
                     "इंस्पेक्टर", "नारकोटिक्स", "इनकम टैक्स",
                     "police", "cbi", "c b i", "customs", "trai", "rbi", "r b i", "cyber crime", "cybercrime",
                     "narcotics", "income tax", "enforcement directorate", "inspector", "telecom regulatory",
                     "ನಾರ್ಕೋಟಿಕ್ಸ್"],
    },
    "threat": {
        "weight": 2.5,
        "labels": {"kn": "ಬಂಧನ, ಕೇಸ್ ಅಥವಾ ಸೇವೆ ಕಡಿತದ ಬೆದರಿಕೆ", "hi": "गिरफ़्तारी, केस या सेवा बंद करने की धमकी",
                   "en": "threat of arrest, a case or a cut-off"},
        "keywords": ["ಅರೆಸ್ಟ್", "ಬಂಧನ", "ವಾರೆಂಟ್", "ಜೈಲು", "ಕೇಸ್ ದಾಖಲ", "ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್", "ಖಾತೆ ಬ್ಲಾಕ್", "ಬ್ಲಾಕ್ ಆಗುತ್ತ",
                     "ಕಸ್ಟಡಿ",
                     "गिरफ्तार", "गिरफ़्तार", "अरेस्ट", "वारंट", "जेल", "केस दर्ज", "डिजिटल अरेस्ट", "खाता बंद",
                     "ब्लॉक हो जाएगा", "हिरासत", "कस्टडी",
                     "arrest", "arrested", "warrant", "jail", "digital arrest", "case registered", "case has been",
                     "custody",
                     "account will be blocked", "sim will be blocked", "legal action",
                     # Hinglish (Latin-script Hindi)
                     "account block", "block ho jayega", "block ho jaega", "giraftar", "giraftari",
                     # cut-off threats and "your parcel / Aadhaar is in a crime" stories (10 Nov 2026)
                     "ಅಕ್ರಮ ಚಟುವಟಿಕೆ", "ಡ್ರಗ್ಸ್", "ಮನಿ ಲಾಂಡರಿಂಗ್", "ಸಿಮ್ ಬ್ಲಾಕ್", "re:ಕನೆಕ್ಷನ್.{0,25}ಕಟ್",
                     "re:ಕರೆಂಟ್.{0,25}ಕಟ್", "re:ಸಿಮ್.{0,25}ಬ್ಲಾಕ್",
                     "गैरकानूनी", "गैर कानूनी", "ड्रग्स", "मनी लॉन्ड्रिंग",
                     "re:(सिम|बिजली|कनेक्शन).{0,40}(बंद|कट|काट)", "re:(खाता|अकाउंट).{0,20}(फ्रीज|फ़्रीज)",
                     "re:(बंद|ब्लॉक|कट)\\s?(हो|कर)\\s?(जाएगा|जाएगी|जाएंगे|दिया जाएगा|दी जाएगी)",
                     "re:(कार्ड|खाता|अकाउंट|सिम|नंबर).{0,15}ब्लॉक", "re:(ಕಾರ್ಡ್|ಸಿಮ್|ನಂಬರ್|ಖಾತೆ).{0,15}ಬ್ಲಾಕ್",
                     "illegal activity", "illegal activities", "drugs", "money laundering", "fake passports",
                     "re:(sim|connection|electricity|power|account|card|number)\\s+(\\w+\\s+){0,3}(will be|is being|is going to be|is|has been|got)"
                     "\\s+(deactivated|blocked|disconnected|cut|suspended|frozen|closed)"],
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
                     "re:(call|phone)\\s+(cut|kat|khat|kaat)\\s+mat",
                     "re:(don't|do not|dont)\\s+tell\\s+(your\\s+)?(dad|mom|father|mother|family|husband|wife|parents)",
                     "re:(पापा|मम्मी|पिताजी|घरवालों|घर पर|परिवार)\\s?(को|में|पर)?\\s?(किसी\\s?को\\s?)?(मत|न|ना)\\s?बता",
                     "वीडियो कॉल पर रहिए", "re:(ಅಪ್ಪ|ಅಮ್ಮ|ಮನೆಯವರ)\\S*\\s?(ಯಾರಿಗೂ\\s?)?ಹೇಳಬೇಡ", "re:ವಿಡಿಯೋ\\s?ಕಾಲ್\\S*\\s?ಇರಿ"],
    },
    "credentials": {
        "weight": 3.0,
        "labels": {"kn": "ಒಟಿಪಿ ಅಥವಾ ಪಿನ್ ಕೇಳುವುದು", "hi": "ओटीपी या पिन माँगना",
                   "en": "asking for OTP, PIN or passwords"},
        "keywords": ["ಒಟಿಪಿ", "ಓಟಿಪಿ", "ಒ ಟಿ ಪಿ", "ಓ ಟಿ ಪಿ", "ಪಿನ್", "ಸಿವಿವಿ", "ಸಿ ವಿ ವಿ", "ಆಧಾರ್ ಸಂಖ್ಯೆ",
                     "ಪಾಸ್ವರ್ಡ್", "ಕಾರ್ಡ್ ನಂಬರ್",
                     "ओटीपी", "ओ टी पी", "पिन", "सीवीवी", "सी वी वी", "आधार नंबर", "पासवर्ड", "कार्ड नंबर",
                     "वेरिफिकेशन कोड", "ವೆರಿಫಿಕೇಶನ್ ಕೋಡ್",
                     "otp", "o t p", "pin", "cvv", "c v v", "password", "aadhaar number", "aadhar number",
                     "card number", "one time password", "verification code", "security code", "otp code",
                     # "read me the six digit code that just came": a paraphrased OTP request (audit, 9 Nov 2026)
                     "re:(six|6|four|4)[ -]?digit\\s+(code|number)",
                     "re:code\\s+(that\\s+|which\\s+)?(just\\s+)?(arrived|came|you\\s+(got|received))",
                     "re:code\\s+(that\\s+)?(we|i)\\s+(just\\s+)?(sent|have sent)", "card details", "net banking",
                     "कार्ड की डिटेल", "कार्ड डिटेल", "नेट बैंकिंग", "re:(आया|आयी|आए)\\s?(हुआ\\s?)?कोड", "re:कोड\\s?(जो|आया)",
                     "ಕಾರ್ಡ್ ವಿವರ", "ನೆಟ್ ಬ್ಯಾಂಕಿಂಗ್", "re:(ಬಂದ|ಬಂದಿರುವ|ಬಂದಿರೋ)\\s?ಕೋಡ್",
                     "re:(छह|छः|6|चार|4)\\s?(अंकों|अंक|डिजिट)\\s?(का|के|वाला|वाले)?\\s?(नंबर|कोड)",
                     "re:(ಆರು|6|ನಾಲ್ಕು|4)\\s?(ಅಂಕಿಯ|ಅಂಕೆಯ|ಡಿಜಿಟ್)\\s?(ನಂಬರ್|ಕೋಡ್)"],
    },
    "otp_request": {
        "weight": 3.0,
        # REVIEW kn/hi labels with a native speaker.
        "labels": {"kn": "ಒಟಿಪಿಯನ್ನು ನೇರವಾಗಿ ಹೇಳಿ ಎಂದು ಕೇಳುವುದು", "hi": "सीधे ओटीपी बताने को कहना",
                   "en": "directly asking you to tell them the OTP"},
        # Found by the detector, not by keywords: an ASK_PHRASES match close to a credentials word.
        "keywords": [],
    },
    "payment": {
        "weight": 3.0,
        "labels": {"kn": "ಹಣ ವರ್ಗಾಯಿಸಲು ಒತ್ತಾಯ", "hi": "पैसे ट्रांसफ़र करने का दबाव",
                   "en": "pushing you to transfer money"},
        "keywords": ["ಹಣ ಕಳುಹಿಸಿ", "ಹಣ ಹಾಕಿ", "ಟ್ರಾನ್ಸ್ಫರ್", "re:ಯು\\s?ಪಿ\\s?ಐ(?!\\s?ಪಿನ್)", "ಸುರಕ್ಷಿತ ಖಾತೆ", "ಗಿಫ್ಟ್ ಕಾರ್ಡ್",
                     "पैसे भेज", "रुपये भेज", "ट्रांसफर", "re:यू\\s?पी\\s?आई(?!\\s?पिन)", "सुरक्षित खाते", "गिफ्ट कार्ड",
                     "वेरिफिकेशन राशि",
                     "transfer money", "send money", "transfer the amount", "safe account", "verification amount",
                     "re:\\bu\\s?p\\s?i\\b(?!\\s?pin)", "gift card", "bitcoin", "pay immediately", "collect request",
                     "re:scan\\s+(the\\s+|this\\s+|my\\s+)?qr", "क्यूआर कोड स्कैन", "ಕ್ಯೂಆರ್ ಕೋಡ್ ಸ್ಕ್ಯಾನ್",
                     "re:\\b(transfer|send|pay)\\s+(\\w+\\s+){0,5}(rupees|lakh|lakhs|thousand|crore)\\b",
                     # Hinglish
                     "paise transfer", "paise bhejo", "paise bhej do", "paisa transfer",
                     # "pay a fee first" and "send N thousand to this UPI" (10 Nov 2026)
                     "processing fee", "registration fee",
                     "re:\\bpay\\s+(a\\s+|the\\s+|an\\s+)?([\\w,]+\\s+){0,3}(fee|charge|charges|deposit)\\b", "security deposit",
                     "सिक्योरिटी डिपॉज़िट", "सिक्योरिटी डिपॉजिट", "ಸೆಕ್ಯುರಿಟಿ ಡೆಪಾಸಿಟ್",
                     "re:\\b(thousand|lakh|lakhs|rupees|crore)\\b[^.?!]{0,40}(?<!not )(?<!never )(?<!don't )(?<!dont )\\b(send|transfer)\\b",
                     "re:\\b(send|pay|transfer)\\s+(\\w+\\s+){0,3}(to\\s+)?(this|my)\\s+(upi|account|number)",
                     "प्रोसेसिंग फीस", "रजिस्ट्रेशन फीस", "re:फीस\\s?(भर|भेज|जमा)", "पेमेंट कीजिए", "पेमेंट करें", "पेमेंट करो",
                     "re:(हज़ार|हजार|लाख|रुपये|रुपए)[^।?.]{0,40}(?<!मत )(?<!न )(?<!ना )(?<!नहीं )(भेज|ट्रांसफर)",
                     "re:इस\\s?(यूपीआई|खाते|नंबर)\\s?(पर|में)\\s?(पैसे\\s?)?(भेज|ट्रांसफर|पेमेंट)",
                     "ಪ್ರೊಸೆಸಿಂಗ್ ಫೀಸ್", "ನೋಂದಣಿ ಶುಲ್ಕ", "re:(ಫೀಸ್|ಶುಲ್ಕ)\\s?(ಕಟ್ಟಿ|ಕಳುಹಿಸಿ|ಪಾವತಿಸಿ)", "ಹಣ ಕಟ್ಟಿ",
                     "re:(ಸಾವಿರ|ಲಕ್ಷ|ರೂಪಾಯಿ)[^.?।]{0,40}(ಕಳುಹಿಸ|ಟ್ರಾನ್ಸ್ಫರ್|ವರ್ಗಾಯಿಸ)", "ಖಾತೆಗೆ ವರ್ಗಾಯಿಸಿ"],
    },
    "remote_access": {
        "weight": 3.0,
        "labels": {"kn": "ಅಪರಿಚಿತ ಆ್ಯಪ್ ಅಥವಾ ಲಿಂಕ್ ತೆರೆಯಲು ಹೇಳುವುದು", "hi": "अनजान ऐप या लिंक खुलवाना",
                   "en": "asking you to install an app or open a link"},
        "keywords": ["ಎನಿಡೆಸ",  # also matches the clipped "ಎನಿಡೆಸ್" heard on noisy lines
                     "ಟೀಮ್ ವ್ಯೂವರ್", "ಆ್ಯಪ್ ಡೌನ್ಲೋಡ್", "ಅಪ್ಲಿಕೇಶನ್ ಇನ್ಸ್ಟಾಲ್",
                     "एनीडेस्क", "एनी डेस्क", "टीम व्यूअर", "ऐप डाउनलोड", "ऐप इंस्टॉल", "ऐप्लिकेशन डाउनलोड",
                     "anydesk", "any desk", "teamviewer", "team viewer", "quicksupport", "quick support",
                     "download the app", "install the app", "screen share",
                     # Hinglish
                     "app download karo", "app download kijiye", "app install karo",
                     "click the link", "click on the link", "link i sent", "link we sent", "open the link", "loan app",
                     "download our app", "re:ऐप.{0,25}डाउनलोड", "लिंक पर क्लिक", "लिंक खोल", "re:लिंक.{0,15}क्लिक", "ಲಿಂಕ್ ಒತ್ತಿ", "ಲಿಂಕ್ ಕ್ಲಿಕ್",
                     "ಲಿಂಕ್ ಓಪನ್"],
    },
    "lure": {
        "weight": 1.0,
        "labels": {"kn": "ಬಹುಮಾನ, ರಿಫಂಡ್, ಕೆಲಸ, ಸಾಲ ಅಥವಾ ಕೆವೈಸಿ ಆಮಿಷ", "hi": "इनाम, रिफंड, नौकरी, लोन या केवाईसी का लालच",
                   "en": "prize, refund, job, loan or KYC lure"},
        "keywords": ["ಲಾಟರಿ", "ಬಹುಮಾನ", "ಕೆವೈಸಿ", "ಕೆ ವೈ ಸಿ", "ರಿಫಂಡ್", "ಪಾರ್ಸೆಲ್", "ಕೊರಿಯರ್",
                     "लॉटरी", "इनाम", "केवाईसी", "के वाई सी", "रिफंड", "पार्सल", "कूरियर", "बिजली कट",
                     "lottery", "prize", "kyc", "k y c", "refund", "parcel", "courier", "fedex",
                     "electricity will be disconnected",
                     "lucky draw", "you have won", "kbc", "part time job", "work from home", "double returns",
                     "double your money", "guaranteed profit", "guaranteed returns", "loan is approved", "loan approved",
                     "reward points", "वर्क फ्रॉम होम", "लकी ड्रॉ", "जीते हैं", "केबीसी", "पार्ट टाइम जॉब", "घर बैठे", "डबल", "मुनाफा",
                     "लोन मंजूर", "रिवॉर्ड पॉइंट", "ಲಕ್ಕಿ ಡ್ರಾ", "ಗೆದ್ದಿದ್ದೀರಿ", "ಪಾರ್ಟ್ ಟೈಮ್", "ಮನೆಯಿಂದಲೇ", "ಡಬಲ್",
                     "ಗ್ಯಾರಂಟಿ ಲಾಭ", "ಲೋನ್ ಮಂಜೂರು", "ರಿವಾರ್ಡ್ ಪಾಯಿಂಟ್"],
    },
    "emergency": {
        "weight": 1.5,
        # REVIEW kn/hi labels with a native speaker.
        "labels": {"kn": "ಕುಟುಂಬದ ಹಠಾತ್ ತುರ್ತು", "hi": "परिवार की अचानक इमरजेंसी", "en": "a sudden family emergency"},
        "keywords": ["accident", "in the hospital", "in hospital", "in trouble", "lost my phone", "friend's number",
                     "friends number", "friend's phone", "new number", "bail", "ज़मानत", "जमानत", "ಜಾಮೀನ",
                     "एक्सीडेंट", "अस्पताल में", "हॉस्पिटल में", "मुसीबत में", "फोन खो गया", "दोस्त का नंबर", "दोस्त के फोन",
                     "ಆಕ್ಸಿಡೆಂಟ್", "ಅಪಘಾತ", "ಆಸ್ಪತ್ರೆಯಲ್ಲಿ", "ತೊಂದರೆಯಲ್ಲಿ", "ಫೋನ್ ಕಳೆದು", "ಸ್ನೇಹಿತನ ನಂಬರ್", "ಸ್ನೇಹಿತನ ಫೋನ್"],
    },
}

# ---- Words people mix in from English, in every script they reach us in (10 Nov 2026) -------------------------
# Speech recognition writes the same word in Latin, Kannada or Devanagari letters depending on the model and the
# speaker, often with digits for amounts and without punctuation. Each entry lists every spelling we expect.
# REVIEW kn/hi spellings with native speakers.
_APPS = r"(google\s?pay|gpay|g\s?pay|phone\s?pe|paytm|bhim|ಗೂಗಲ್\s?ಪೇ|ಜಿ\s?ಪೇ|ಫೋನ್\s?ಪೇ|ಪೇಟಿಎಂ|गूगल\s?पे|जी\s?पे|फ़?ोन\s?पे|पेटीएम)"
_SEND_KN = r"(ಕಳುಹಿಸ|ಕಳಿಸ|ಕಳ್ಸ|ಟ್ರಾನ್ಸ್ಫರ್|ವರ್ಗಾಯಿಸ|ಡೆಪಾಸಿಟ್|ಪೇ\s?ಮಾಡಿ|ಹಾಕಿ|kalis|kals|kalus|transfer|deposit|haaki)"
_SEND_HI = r"(भेज|ट्रांसफर|जमा\s?कर|पेमेंट|डिपॉज़?िट|bhej|transfer|jama\s?kar|payment|deposit)"
LOANWORDS: dict[str, list[str]] = {
    "payment": [
        # a payment app plus "do it / an amount": "google pay 15000", "phonepe kar do", "ಗೂಗಲ್ ಪೇ ಮಾಡಿ"
        rf"re:{_APPS}\s?(me\s+|to\s+)?(\d|rs|rupees|it\b|kar|कर|ಮಾಡಿ|ಮಾಡು|maadi|madi|maadu)",
        rf"re:\d{{3,}}\s?(rs|rupees|rupaye|रुपये|रुपए|ರೂಪಾಯಿ)?\s?(on\s+|to\s+)?{_APPS}",
        # an amount in digits next to "send / pay / transfer" (Prisma writes 10000, not "ten thousand")
        r"re:\b(send|transfer|pay|deposit)\s+(\w+\s+){0,3}(rs\.?\s*|₹\s*)?\d{3,}",
        r"re:\d{3,}\s*(rs|rupees)?\s*[^.?!\d]{0,25}(?<!not )(?<!never )(?<!don't )\b(send|transfer|deposit)\b",
        rf"re:\d{{3,}}\s?(रुपये|रुपए|rupaye|rs|हज़ार|हजार|hazaar|hazar)?\s?(?<!मत )(?<!न )(?<!mat )\S*\s?{_SEND_HI}",
        rf"re:\d{{3,}}\s?(ರೂಪಾಯಿ|rupayi|saavira|ಸಾವಿರ)?\s?\S*\s?{_SEND_KN}",
        rf"re:(ಸಾವಿರ|ಲಕ್ಷ|ರೂಪಾಯಿ)[^.?।]{{0,40}}{_SEND_KN}",
        # pay first / fees and charges in every spelling
        r"re:\bfirst\s+(deposit|pay|send|transfer)", r"re:\b(deposit|pay|send)\s+(\w+\s+){0,2}first\b",
        r"re:\bpay\s+(a\s+|the\s+|an\s+)?([\w,]+\s+){0,3}(penalty|fine|gst|tax|clearance|settlement)\b",
        r"re:(processing|registration|file|joining)\s+(fee|fees|charge|charges)",
        r"re:(पहले|pehle).{0,25}(जमा|भेज|पेमेंट|jama|bhej|payment|pay)",
        r"re:(प्रोसेसिंग|रजिस्ट्रेशन|फाइल|फ़ाइल|जॉइनिंग)\s?(फीस|फ़ीस|फी|चार्ज)",
        r"re:ಮೊದಲು.{0,25}(ಡೆಪಾಸಿಟ್|ಕಟ್ಟಿ|ಕಳುಹಿಸಿ|ಕಳಿಸಿ|ಪಾವತಿ|ಪೇ\s?ಮಾಡಿ|ಹಾಕಿ)",
        r"re:(ಪ್ರೊಸೆಸಿಂಗ್|ರಿಜಿಸ್ಟ್ರೇಶನ್|ಫೈಲ್|ಜಾಯಿನಿಂಗ್)\s?(ಫೀ|ಫೀಸ್|ಚಾರ್ಜ್)",
        # Kanglish / Hinglish
        "duddu kalisi", "duddu kalsi", "payment karo", "payment kar do", "payment kijiye", "pay karo",
        "पेमेंट कर दो", "ಪೇಮೆಂಟ್ ಮಾಡಿ", "payment maadi", "pay maadi", "duddu transfer", "hana kalisi", "paisa bhejo", "paise bhejiye",
        "re:(processing|registration)\\s+fee\\s+\\d+\\s+(kalsi|kalisi|bhej)",
    ],
    "credentials": [
        "ಡೀಟೇಲ್ಸ್", "card details", "re:(card|bank|account)\\s+details",
    ],
    "remote_access": [
        "ಕ್ವಿಕ್ ಸಪೋರ್ಟ್", "ಟೀಂ ವ್ಯೂವರ್", "ಟೀಮ್ ವ್ಯೂವರ್", "ಎನಿ ಡೆಸ್ಕ್", "क्विक सपोर्ट", "re:(ಆ್ಯಪ್|ಆಪ್).{0,15}(ಇನ್ಸ್ಟಾಲ್|ಡೌನ್\\s?ಲೋಡ್)",
        "re:\\b(download|install)\\s+(the\\s+|this\\s+|our\\s+)?(\\w+\\s+){0,3}app\\b",
        "re:link\\s+(pe|par|par\\s+|mein)?\\s*click", "re:link\\s+(click|open)\\s+(maadi|karo|kijiye|kar)",
    ],
    "authority": ["cyber cell", "ಸೈಬರ್ ಸೆಲ್", "साइबर सेल", "narcotics control bureau", "ncb"],
    "threat": [
        "police will come", "पुलिस घर आएगी", "re:ಪೊಲೀಸ್.{0,10}ಮನೆಗೆ\\s?ಬರ", "police station aana padega",
        "under investigation", "re:complaint\\s+against\\s+(you|your)", "re:केस\\s?(है|हुआ|दर्ज|बना)",
        "re:ಕೇಸ್\\s?(ಆಗಿದೆ|ದಾಖಲ|ಹಾಕ)", "case agide", "case aagide",
        "re:(meter|line|light)\\s+(\\w+\\s+){0,3}(will be|is going to be)\\s+(disconnected|cut)",
        "re:(मीटर|लाइट|लाइन).{0,30}(कट|काट|बंद)",
        "re:(ಮೀಟರ್|ಲೈನ್|ಕರೆಂಟ್).{0,20}ಕಟ್",
        "re:(line|light|bijli|connection|meter|sim)\\s+(\\w+\\s+){0,2}(kat|cut|band)\\s+(ho\\s+)?(jayegi|jayega|jaegi|jaega|hogi|hoga)",
        "re:(line|current|meter|sim|account|card)\\s+(\\w+\\s+){0,2}(cut|block|band)\\s+(aagutte|agutte|aagide|agide|aagatte)",
        "re:(wallet|account)\\s+block\\b",
    ],
    "urgency": ["suspicious transaction", "suspicious login", "account was hacked", "account has been hacked",
                "ತುರ್ತಾಗಿ", "ಬೇಗ", "bega", "jaldi se"],
    "secrecy": ["re:(skype|video)\\s+call\\s+with\\s+(the\\s+)?(officer|police|inspector)",
                "re:(stay|be)\\s+on\\s+(this|the)\\s+video\\s+call", "re:join\\s+(a\\s+|the\\s+)?skype",
                "स्काइप कॉल", "re:ಸ್ಕೈಪ್\\s?ಕಾಲ್", "skype call"],
    "lure": ["cashback", "cash back", "you won", "won a car", "like and earn", "task", "bonus", "subsidy", "loan pass",
             "लोन पास", "टास्क", "कैशबैक", "ಕ್ಯಾಶ್ ಬ್ಯಾಕ್", "ಲೋನ್ ಅಪ್ರೂವ್", "ಟಾಸ್ಕ್", "ಲಾಟರಿ ಬಂದಿದೆ", "lottery"],
    "emergency": ["phone is broken", "colleague's phone", "phone kharab", "mera phone", "ಫೋನ್ ಹಾಳಾಗಿದೆ", "ಮೊಬೈಲ್ ಹಾಳಾಗಿದೆ",
                  "ಫ್ರೆಂಡ್ ನಂಬರ್", "friend number", "dost ka number", "in custody", "phone haalagide"],
}
LOANWORDS["payment"] += [
    # "move all your money / balance to our account": the core of digital-arrest and ED scams
    r"re:\b(transfer|move|send)\s+(all\s+)?(of\s+)?(your\s+)?(balance|savings|money|funds)\s+(\w+\s+){0,2}to\b",
    r"re:(सारी|पूरी)\s?(रकम|बचत|जमा\s?पूंजी)", r"re:(हमारे|बताए)\s?.{0,12}खाते\s?में\s?(डाल|भेज|ट्रांसफर)",
    r"re:(ಎಲ್ಲಾ|ಎಲ್ಲ)\s?(ಹಣ|ಉಳಿತಾಯ)", r"re:ನಾವು\s?(ಹೇಳುವ|ಕೊಡುವ)\s?ಖಾತೆಗೆ",
    # charges to receive a prize / parcel, and bribes to "settle the case"
    r"re:(delivery|handling|shipping)\s+charges?", "डिलीवरी चार्ज", "ಡೆಲಿವರಿ ಚಾರ್ಜ್",
    "settle the case", "case settle", "केस सेटल", "ಕೇಸ್ ಸೆಟಲ್",
]
LOANWORDS["lure"] += ["scratch card", "iphone", "बोनस", "ಬೋನಸ್", "जीता है", "jeeta", "jeeti", "inaam", "won"]
LOANWORDS["threat"] += ["hawala", "हवाला", "ಹವಾಲಾ",
                        r"re:(sim|account|number|card)\s+(\w+\s+){0,2}close\s+(aagutte|agutte|ho\s+jayega)"]
LOANWORDS["authority"] += ["ईडी", "ಇಡಿ ಆಫೀಸರ್", r"re:\bed\s+(officer|office|department)"]
LOANWORDS["secrecy"] += ["dont inform anyone", "don't inform anyone", "do not inform anyone"]
LOANWORDS["urgency"] += [r"re:account\s+(\w+\s+){0,2}hack", "हैक हो गया", "ಹ್ಯಾಕ್ ಆಗಿದೆ"]
for _name, _words in LOANWORDS.items():
    TACTICS[_name]["keywords"].extend(w for w in _words if w not in TACTICS[_name]["keywords"])

# The kind of scam, named on the warning screens ("Fake police / digital arrest"): people trust a
# warning that names the trick. Checked in order; the first match wins. `needs`: at least one of these
# tactics; `evidence`: at least one of these matched keywords (or `words`, matched on their own).
# REVIEW kn/hi labels and words with a native speaker.
SCAM_TYPES: dict[str, dict] = {
    "family_emergency": {
        "labels": {"kn": "ಕುಟುಂಬದವರ ಹೆಸರಿನಲ್ಲಿ ಸುಳ್ಳು ತುರ್ತು", "hi": "परिवार के नाम पर झूठी इमरजेंसी",
                   "en": "Fake family emergency"},
        "needs": {"payment", "threat", "authority", "credentials"},
        "words": ["ನಿಮ್ಮ ಮಗ", "ನಿಮ್ಮ ಮಗಳ", "ನಿಮ್ಮ ಗಂಡ", "ನಿಮ್ಮ ಹೆಂಡತಿ", "ಆಕ್ಸಿಡೆಂಟ್", "ಅಪಘಾತ", "ಆಸ್ಪತ್ರೆ",
                  "आपका बेटा", "आपके बेटे", "आपकी बेटी", "आपके पति", "आपकी पत्नी", "एक्सीडेंट", "अस्पताल",
                  "हॉस्पिटल",
                  "your son", "your daughter", "your husband", "your wife", "your grandson", "accident",
                  "hospital", "aapka beta", "aapki beti", "aapke bete", "bete ko", "lost my phone", "friend's number", "in trouble", "bail",
                  "फोन खो गया", "दोस्त का नंबर", "मुसीबत में", "ज़मानत", "जमानत", "ಫೋನ್ ಕಳೆದು", "ಸ್ನೇಹಿತನ ನಂಬರ್",
                  "ತೊಂದರೆಯಲ್ಲಿ", "ಜಾಮೀನ"],
    },
    # Before digital_arrest: the parcel story usually turns into a fake-police threat, and the parcel is what
    # people recognise. A customs mention alone is not enough (it is in many digital-arrest calls).
    "courier": {
        "labels": {"kn": "ನಕಲಿ ಕೊರಿಯರ್ / ಪಾರ್ಸೆಲ್ ಮೋಸ", "hi": "नकली कूरियर / पार्सल धोखा",
                   "en": "Fake courier / customs parcel"},
        "evidence": {"ಪಾರ್ಸೆಲ್", "ಕೊರಿಯರ್", "पार्सल", "कूरियर", "parcel", "courier", "fedex"},
        "needs": {"threat", "payment", "authority"},
    },
    "digital_arrest": {
        "labels": {"kn": "ನಕಲಿ ಪೊಲೀಸ್ / ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್", "hi": "नकली पुलिस / डिजिटल अरेस्ट",
                   "en": "Fake police / digital arrest"},
        "needs": {"threat"},
        "all": {"authority"},
        "evidence": set(),        # filled below: every threat keyword except the cut-off ones
    },
    "job_investment": {
        "labels": {"kn": "ನಕಲಿ ಕೆಲಸ / ಸಾಲ / ಹೂಡಿಕೆ", "hi": "नकली नौकरी / लोन / निवेश", "en": "Fake job / loan / investment"},
        "needs": {"payment", "remote_access", "credentials"},
        "evidence": {"part time job", "work from home", "double returns", "double your money", "guaranteed profit",
                     "guaranteed returns", "loan is approved", "loan approved", "loan app", "पार्ट टाइम जॉब", "घर बैठे",
                     "वर्क फ्रॉम होम", "डबल", "मुनाफा", "लोन मंजूर", "ಪಾರ್ಟ್ ಟೈಮ್", "ಮನೆಯಿಂದಲೇ", "ಡಬಲ್", "ಗ್ಯಾರಂಟಿ ಲಾಭ",
                     "ಲೋನ್ ಮಂಜೂರು"},
    },
    "remote_access": {
        "labels": {"kn": "ರಿಮೋಟ್ ಆ್ಯಪ್ ಮೋಸ", "hi": "रिमोट ऐप वाला धोखा", "en": "Remote-control app scam"},
        "needs": {"remote_access"},
    },
    "kyc_bank": {
        "labels": {"kn": "ನಕಲಿ ಬ್ಯಾಂಕ್ / ಕೆವೈಸಿ ಮೋಸ", "hi": "नकली बैंक / केवाईसी धोखा", "en": "Fake bank / KYC update"},
        "evidence": {"ಕೆವೈಸಿ", "ಕೆ ವೈ ಸಿ", "ಆರ್ಬಿಐ", "ಆರ್ ಬಿ ಐ", "केवाईसी", "के वाई सी", "आरबीआई", "आर बी आई",
                     "kyc", "k y c", "rbi", "r b i"},
    },
    "prize": {
        "labels": {"kn": "ನಕಲಿ ಬಹುಮಾನ / ರಿಫಂಡ್", "hi": "नकली इनाम / रिफंड", "en": "Fake prize / refund"},
        "evidence": {"ಲಾಟರಿ", "ಬಹುಮಾನ", "ರಿಫಂಡ್", "लॉटरी", "इनाम", "रिफंड", "lottery", "prize", "refund"},
        "unless": {"otp_request"},     # "read me the code so I can approve the refund" is OTP theft
    },
    "otp_theft": {
        "labels": {"kn": "ಒಟಿಪಿ ಕಳ್ಳತನ", "hi": "ओटीपी चोरी", "en": "OTP theft"},
        "needs": {"credentials", "otp_request"},
    },
    "cutoff": {
        "labels": {"kn": "ನಕಲಿ ಸಿಮ್ / ಕರೆಂಟ್ / ಖಾತೆ ಕಡಿತದ ಬೆದರಿಕೆ", "hi": "नकली सिम / बिजली / खाता बंद होने की धमकी",
                   "en": "Fake SIM / power / account cut-off"},
        "needs": {"threat"},
        "evidence": set(),        # filled below: the cut-off threat keywords
    },
    "money": {
        "labels": {"kn": "ಹಣ ವರ್ಗಾವಣೆ ಒತ್ತಡ", "hi": "पैसे भेजने का दबाव", "en": "Money transfer pressure"},
        "needs": {"payment"},
    },
}
_CUTOFF = {kw for kw in TACTICS["threat"]["keywords"]
           if any(w in kw for w in ("sim", "connection", "electricity", "power", "card", "number", "account", "block",
                                    "सिम", "बिजली", "कनेक्शन", "खाता", "अकाउंट", "बंद", "ब्लॉक", "कट",
                                    "ಸಿಮ್", "ಕರೆಂಟ್", "ಕನೆಕ್ಷನ್", "ಖಾತೆ", "ಬ್ಲಾಕ್", "ಕಾರ್ಡ್"))}
SCAM_TYPES["cutoff"]["evidence"] = _CUTOFF
SCAM_TYPES["digital_arrest"]["evidence"] = set(TACTICS["threat"]["keywords"]) - _CUTOFF

SUSPICIOUS = {"kn": "ಅನುಮಾನಾಸ್ಪದ ಕರೆ", "hi": "संदिग्ध कॉल", "en": "Suspicious call"}

# Tactics that turn a request into pressure. When none of them is present, an OTP mention in an
# awareness message or a delivery hand-over is treated as context, not as an attack.
ESCALATION = {"threat", "secrecy", "payment", "remote_access"}

# Legitimate "tell me the OTP" situations: a delivery agent confirming a hand-over.
DELIVERY_PHRASES = [
    "delivery otp", "delivery o t p", "delivery code", "otp for delivery", "otp for the delivery",
    "डिलीवरी ओटीपी", "डिलीवरी वाला ओटीपी", "डिलीवरी का ओटीपी", "डिलीवरी ओ टी पी", "डिलीवरी वाला ओ टी पी",
    "ಡೆಲಿವರಿ ಒಟಿಪಿ", "ಡೆಲಿವರಿ ಓಟಿಪಿ", "ಡೆಲಿವರಿ ಒ ಟಿ ಪಿ", "ಡೆಲಿವರಿ ಓ ಟಿ ಪಿ",
]

# "Tell me / give / share" said right next to an OTP or PIN word is a direct request for it, even when the
# caller said "don't share" earlier (seen in a real test call). Kannada/Hindi entries match whole words
# only, so "ಹೇಳಿ" does not fire inside "ಹೇಳಿದ್ದೇನೆ". REVIEW kn/hi entries with a native speaker.
ASK_PHRASES = [
    "tell me", "tell us", "give me", "give us", "give the", "give your", "share the", "share your",
    "share it", "read out", "read the", "send me", "send the", "send your", "provide", "please tell",
    "can you tell", "forward the", "read me", "read it", "say the", "say it", "tell the", "type the",
    "enter the", "enter your", "bhej", "bhejo", "ಕಳಿಸು", "डालिए", "डाल दीजिए", "डाल दो", "daaliye", "dal do", "ಹಾಕಿ", "haaki", "confirm the", "verify the", "confirm it", "confirm karo", "confirm kijiye", "confirm maadi",
    "verify karo", "heli", "helri", "kodi", "tilisi", "batao", "bata dijiye", "कन्फर्म कीजिए", "कन्फर्म करो",
    "re:कन्फर्म\\s?करने", "वेरिफाई कीजिए", "ಕನ್ಫರ್ಮ್ ಮಾಡಿ", "re:ಕನ್ಫರ್ಮ್\\s?ಮಾಡಲು", "ವೆರಿಫೈ ಮಾಡಿ",
    # English as the kn-IN / hi-IN models write it
    "ಟೆಲ್ ಮಿ", "ಟೆಲ್ ಮೀ", "re:ಗಿ\\s?ವ", "ಶೇರ್ ಯುವರ್", "ಶೇರ್ ದ", "ಸೆಂಡ್", "ರೀಡ್ ಔಟ್",
    "टेल मी", "re:गि\\s?व", "शेयर योर", "सेंड",
    # Kannada
    "ತಿಳಿಸಿ", "ತಿಳಿಸುವಿರಾ", "ತಿಳಿಸ್ತೀರಾ", "ಹೇಳಿ", "ಹೇಳ್ತೀರಾ", "ಹೇಳುವಿರಾ", "ಹೇಳ್ಬಿಡಿ", "ಕೊಡಿ", "ಕೊಡ್ತೀರಾ",
    "ಕೊಡುವಿರಾ", "ಕಳುಹಿಸಿ", "ಕಳಿಸಿ", "ಓದಿ", "ಹಂಚಿಕೊಳ್ಳಿ", "ಶೇರ್ ಮಾಡಿ", "ಶೇರ್ ಮಾಡ್ತೀರಾ", "ಹೇಳ್ರಿ", "ಹೇಳಿಬಿಡಿ",
    # Hindi
    "बताइए", "बताइये", "बताओ", "बता दीजिए", "बता दो", "बता दें", "दीजिए", "दे दो", "भेजिए", "भेज दो",
    "शेयर करो", "शेयर कीजिए", "शेयर कर दो", "पढ़कर सुनाइए", "बोलिए", "बोलो", "बोल दीजिए", "बोल दो",
    # Hinglish
    "batao", "bataiye", "bata do", "bata dijiye", "de do", "dijiye", "share karo", "share kijiye",
    "share kar do", "bhej do",
]

# "There is no such thing as a digital arrest": police awareness, not a threat. A threat keyword inside one of
# these is not counted. REVIEW kn/hi with a native speaker.
DEBUNK_PHRASES = [
    "re:(no such thing as (a )?|there is no |there's no |theres no )digital arrest",
    "re:digital arrest (is not|isn't|isnt|does not|doesn't|doesnt) (real|exist|happen)",
    "re:digital arrest (is|are) (a |an )?(fake|scam|fraud|myth)",
    "re:डिजिटल\\s?अरेस्ट\\s?(जैसा|नाम का|नाम की)?\\s?(कुछ|कोई)?\\s?(भी\\s?)?(नहीं|फ़र्ज़ी|फर्जी|धोखा)",
    "re:ಡಿಜಿಟಲ್\\s?ಅರೆಸ್ಟ್\\s?(ಎಂಬುದು|ಅನ್ನೋದು|ಎನ್ನುವುದು|ಎಂಬುದೇ)?\\s?(ಇಲ್ಲ|ಇರುವುದಿಲ್ಲ|ಸುಳ್ಳು|ಮೋಸ)",
]

# Awareness messages ("never share your OTP") should not read as a request for the OTP.
SAFETY_PHRASES = [
    "never share", "do not share", "don't share", "dont share", "never ask for", "shouldn't share",
    "should not share", "must not share",
    "ಹಂಚಿಕೊಳ್ಳಬೇಡಿ", "ಹಂಚಿಕೊಳ್ಳಬಾರದು",
    # Code-mixed: the English word "share" in Kannada script (everyday speech, and what the kn-IN
    # model writes when it hears English). REVIEW with a native speaker.
    "ಶೇರ್ ಮಾಡಬೇಡಿ", "ಶೇರ್ ಮಾಡ್ಬೇಡಿ", "ಶೇರ್ ಮಾಡಬಾರದು", "ನೆವರ್ ಶೇರ್", "ಡೋಂಟ್ ಶೇರ್", "ಡು ನಾಟ್ ಶೇರ್",
    "ಶುಡ್ಡಂಟ್ ಶೇರ್", "ಶುಡಂಟ್ ಶೇರ್", "ಶುಡ್ ನಾಟ್ ಶೇರ್",
    "साझा न करें", "साझा ना करें", "कभी न बताएं", "किसी को न दें",
    # Code-mixed Hindi: "share" in Devanagari. REVIEW with a native speaker.
    "शेयर न करें", "शेयर ना करें", "शेयर मत करें", "शेयर मत कीजिए", "शेयर मत करना", "नेवर शेयर", "डोंट शेयर",
    "re:share\\s+(mat|matt|mark|na|nahi|nahin)\\b",   # "share mat" is often heard as "share mark"
    "re:शेयर\\s?(मार्ट|मार्क|मॉर्ट|मॉर्क)\\s?(कीजिए|करें|करो|करना)",   # the same mishearing in Devanagari (live test, 10 Nov 2026)
    # "We will never ask for your OTP" (the bank's own safety message). REVIEW with a native speaker.
    "re:ಎಂದಿಗೂ.{0,40}ಕೇಳುವುದಿಲ್ಲ", "re:ಯಾವತ್ತೂ.{0,40}ಕೇಳುವುದಿಲ್ಲ",
    "re:कभी.{0,40}नहीं\\s?(मांगते|मांगता|माँगते|माँगता|पूछते|पूछता)",
    # Every everyday way of saying "don't tell / give / send it" (found missing on 10 Nov 2026: Kannada
    # "ಒಟಿಪಿ ಯಾರಿಗೂ ಹೇಳಬೇಡಿ / ಕೊಡಬೇಡಿ" and Hindi "मत दीजिए" caution calls raised scam alerts).
    "re:(ಹೇಳ|ಕೊಡ|ತಿಳಿಸ|ಕಳುಹಿಸ|ಕಳಿಸ|ನೀಡ|ಹಂಚಿಕೊಳ್ಳ|ಶೇರ್\\s?ಮಾಡ)\\s?(ಬೇಡಿ|ಬೇಡ|ಬಾರದು)",
    "re:(?<!\\S)(मत|न|ना|नहीं)\\s+(बता|दे|दें|दी|शेयर|भेज|साझा)",
    "re:(?<!\\S)(बता|दे|दी|भेज)\\S*\\s+(मत|नहीं)(?!\\S)(?!\\s*तो)",
    "re:(mat|na|nahi|nahin)\\s+(batana|batao|bataiye|dena|do|dijiye|bhejo|bhejna)",
    "re:(?<![a-z])(never|do not|don't|dont|not to|must not|should not)\\s+(give|tell|say|send|read out|reveal|disclose)"
    "\\s+(\\w+\\s+){0,3}(otp|o t p|pin|cvv|password|code)",
    *DEBUNK_PHRASES,
    "re:(?<!\\S)(मत|न|ना)\\s+(कन्फर्म|वेरिफाई|पेमेंट|जमा|डाउनलोड|इंस्टॉल|क्लिक)",
    "re:(ಕನ್ಫರ್ಮ್|ಪೇ|ಕ್ಲಿಕ್|ಡೌನ್\\s?ಲೋಡ್|ಇನ್ಸ್ಟಾಲ್)\\s?ಮಾಡ(ಬೇಡಿ|ಬೇಡ|ಬಾರದು)",
    "re:(heli|hel|kod|kalis|kals|share\\s?maad|maad)\\s?bed(i|a)\\b",
]

# Caution messages often name the trick without any OTP in them ("fake calls asking you to join a video call with
# police"). With one of these and no positive request for money, an app or the OTP, the call is awareness.
AWARE_PHRASES = [
    "beware of", "fake call", "fake calls", "it is a scam", "it is a fraud", "this is a scam", "hang up and call 1930",
    "call 1930", "फर्जी कॉल", "फ़र्ज़ी कॉल", "धोखा है", "सावधान", "1930 पर कॉल", "ನಕಲಿ ಕರೆ", "ಅದು ಮೋಸ",
    "1930 ಗೆ ಕರೆ", "ಹೆದರಬೇಡಿ", "डरिए मत", "don't be afraid", "do not be afraid",
]

# One-word list for Prisma word boosting (letters only, one word per entry, per the docs).
BIAS_WORDS = ["OTP", "CBI", "arrest", "warrant", "police", "courier", "customs", "AnyDesk", "TeamViewer",
              "Aadhaar", "UPI", "KYC", "parcel", "digital", "ओटीपी", "सीबीआई", "वारंट", "अरेस्ट", "पुलिस",
              "ಒಟಿಪಿ", "ಸಿಬಿಐ", "ವಾರೆಂಟ್", "ಅರೆಸ್ಟ್", "ಪೊಲೀಸ್"]
