"""SIMULATED calls for detector tuning (Phase 2) and the noise benchmark (Phase 4).

Every call is synthetic: written here, spoken by Timbre, never a real recording. No real
names, numbers or account details. Scam lines use generic tactic wording only.

Speaker "A" places the call, speaker "B" answers. `expect` lists the tactics a scam call
should trigger; benign calls (including awareness messages) should stay below medium.

REVIEW: every Kannada (kn) and Hindi (hi) line needs a native-speaker check before the
benchmark is published. Hinglish (hl) is written in Latin script, as people type it.
"""
from __future__ import annotations

# Per language: TTS language/model/voices and the STT language code.
# Hinglish is transcribed with en-IN, which accepts Hindi-English mixed audio (Latin output).
LANGS: dict[str, dict] = {
    "kn": {"tts": "kn-IN", "stt": "kn-IN", "model": "timbre-v2.5", "voices": {"A": "Kavin", "B": "Saanvi"}},
    "hi": {"tts": "hi-IN", "stt": "hi-IN", "model": "timbre-v2.5", "voices": {"A": "Deepak", "B": "Nalini"}},
    "en": {"tts": "en-IN", "stt": "en-IN", "model": "timbre-v2.5", "voices": {"A": "Pranav", "B": "Kaveri"}},
    "hl": {"tts": "hi-en", "stt": "en-IN", "model": "timbre-v2.5", "voices": {"A": "Deepak", "B": "Poorvi"},
           "fallback_voice": "Poorvi"},  # Poorvi is the only documented v2.5 Hinglish voice
}

CALLS: list[dict] = [
    # ---- English ----------------------------------------------------------------------
    {"id": "en_scam_arrest", "lang": "en", "label": "scam",
     "expect": ["authority", "threat", "secrecy", "credentials", "remote_access", "payment"],
     "lines": [
         ("A", "Hello, this is Inspector Rao from the cyber crime branch. A parcel in your name has been caught by customs."),
         ("B", "What? I did not send any parcel."),
         ("A", "There is an arrest warrant against you. This is a digital arrest. Do not disconnect this call and do not tell anyone."),
         ("B", "Please, what should I do?"),
         ("A", "Install the app AnyDesk right now and tell me the OTP on your phone. Then transfer the verification amount to a safe account immediately."),
     ]},
    {"id": "en_scam_kyc", "lang": "en", "label": "scam",
     "expect": ["lure", "threat", "urgency", "credentials"],
     "lines": [
         ("A", "Good morning madam, I am calling from your bank's KYC department."),
         ("B", "Yes, what is it about?"),
         ("A", "Your KYC has expired and your account will be blocked today. You must update it immediately."),
         ("B", "Oh no. How do I update it?"),
         ("A", "I have sent a code to your phone. Tell me the OTP right now and I will complete the update. Do not share this with anyone else."),
     ]},
    {"id": "en_benign_delivery", "lang": "en", "label": "benign",
     "lines": [
         ("A", "Hello, I am the delivery person from the courier company. I am outside your building with your parcel."),
         ("B", "Oh great, I will come down."),
         ("A", "Please tell me the delivery OTP when you collect it."),
         ("B", "Okay, I am coming in two minutes."),
     ]},
    {"id": "en_benign_friend", "lang": "en", "label": "benign",
     "lines": [
         ("A", "Hey, are we still meeting for lunch on Saturday?"),
         ("B", "Yes, one o'clock at the usual place."),
         ("A", "Great, I will book a table. Tell your brother to come too."),
         ("B", "Sure, see you then."),
     ]},
    {"id": "en_awareness", "lang": "en", "label": "benign",
     "lines": [
         ("A", "This is an important message from your bank. Never share your OTP, PIN or password with anyone, "
               "including bank staff. If someone asks for it, report it to the cyber crime helpline."),
     ]},

    # ---- Hindi (REVIEW) ---------------------------------------------------------------
    {"id": "hi_scam_arrest", "lang": "hi", "label": "scam",
     "expect": ["authority", "threat", "secrecy", "credentials", "remote_access", "payment"],
     "lines": [
         ("A", "नमस्ते, मैं साइबर क्राइम से इंस्पेक्टर बोल रहा हूँ। आपके नाम का एक पार्सल कस्टम ने पकड़ा है।"),
         ("B", "क्या? मैंने तो कोई पार्सल नहीं भेजा।"),
         ("A", "आपके खिलाफ़ गिरफ्तारी वारंट है। यह डिजिटल अरेस्ट है। कॉल कट मत करना और किसी को मत बताना।"),
         ("B", "मुझे क्या करना होगा?"),
         ("A", "अभी एनीडेस्क ऐप डाउनलोड करें और अपना ओटीपी बताएं। फिर तुरंत सुरक्षित खाते में पैसे भेजें।"),
     ]},
    {"id": "hi_scam_electricity", "lang": "hi", "label": "scam",
     "expect": ["lure", "urgency", "remote_access", "credentials"],
     "lines": [
         ("A", "नमस्ते, मैं बिजली विभाग से बोल रहा हूँ। आपका बिजली का बिल बकाया है।"),
         ("B", "लेकिन मैंने तो बिल भर दिया था।"),
         ("A", "आज रात आपकी बिजली कट जाएगी। अभी यह ऐप डाउनलोड करें और छोटा सा भुगतान करें।"),
         ("B", "ठीक है, फिर क्या करना है?"),
         ("A", "फिर आपके फ़ोन पर जो ओटीपी आएगा, वह मुझे तुरंत बताइए।"),
     ]},
    {"id": "hi_benign_delivery", "lang": "hi", "label": "benign",
     "lines": [
         ("A", "नमस्ते, मैं कूरियर से बोल रहा हूँ। आपका पार्सल लेकर घर के बाहर खड़ा हूँ।"),
         ("B", "अच्छा, मैं अभी नीचे आती हूँ।"),
         ("A", "पार्सल लेते समय डिलीवरी वाला ओटीपी बता दीजिएगा।"),
         ("B", "ठीक है, दो मिनट में आती हूँ।"),
     ]},
    {"id": "hi_benign_family", "lang": "hi", "label": "benign",
     "lines": [
         ("A", "हैलो माँ, मैं शाम को घर आ रहा हूँ।"),
         ("B", "अच्छा बेटा, खाने में क्या बनाऊँ?"),
         ("A", "राजमा चावल बना दो, बहुत दिन हो गए।"),
         ("B", "ठीक है, जल्दी आना।"),
     ]},
    {"id": "hi_awareness", "lang": "hi", "label": "benign",
     "lines": [
         ("A", "यह आपके बैंक की ओर से एक ज़रूरी सूचना है। अपना ओटीपी, पिन या पासवर्ड कभी भी किसी के साथ साझा न करें, "
               "बैंक कर्मचारी के साथ भी नहीं। कोई माँगे तो साइबर क्राइम हेल्पलाइन पर शिकायत करें।"),
     ]},

    # ---- Kannada (REVIEW) -------------------------------------------------------------
    {"id": "kn_scam_arrest", "lang": "kn", "label": "scam",
     "expect": ["authority", "threat", "secrecy", "credentials", "remote_access", "payment"],
     "lines": [
         ("A", "ನಮಸ್ಕಾರ, ನಾನು ಸೈಬರ್ ಕ್ರೈಮ್ ಇನ್ಸ್ಪೆಕ್ಟರ್ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ. ನಿಮ್ಮ ಹೆಸರಿನ ಪಾರ್ಸೆಲ್ ಅನ್ನು ಕಸ್ಟಮ್ಸ್ ಹಿಡಿದಿದೆ."),
         ("B", "ಏನು? ನಾನು ಯಾವ ಪಾರ್ಸೆಲ್ ಕೂಡ ಕಳುಹಿಸಿಲ್ಲ."),
         ("A", "ನಿಮ್ಮ ವಿರುದ್ಧ ಅರೆಸ್ಟ್ ವಾರೆಂಟ್ ಇದೆ. ಇದು ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್. ಕರೆ ಕಟ್ ಮಾಡಬೇಡಿ, ಯಾರಿಗೂ ಹೇಳಬೇಡಿ."),
         ("B", "ನಾನು ಏನು ಮಾಡಬೇಕು?"),
         ("A", "ಈಗಲೇ ಎನಿಡೆಸ್ಕ್ ಆ್ಯಪ್ ಡೌನ್ಲೋಡ್ ಮಾಡಿ, ನಿಮ್ಮ ಒಟಿಪಿ ಹೇಳಿ. ತಕ್ಷಣ ಸುರಕ್ಷಿತ ಖಾತೆಗೆ ಹಣ ಕಳುಹಿಸಿ."),
     ]},
    {"id": "kn_scam_kyc", "lang": "kn", "label": "scam",
     "expect": ["lure", "threat", "urgency", "credentials"],
     "lines": [
         ("A", "ನಮಸ್ಕಾರ ಮೇಡಂ, ನಾನು ನಿಮ್ಮ ಬ್ಯಾಂಕಿನ ಕೆವೈಸಿ ವಿಭಾಗದಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ."),
         ("B", "ಹೌದಾ, ಏನು ವಿಷಯ?"),
         ("A", "ನಿಮ್ಮ ಕೆವೈಸಿ ಅವಧಿ ಮುಗಿದಿದೆ. ಇಂದೇ ನಿಮ್ಮ ಖಾತೆ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ."),
         ("B", "ಅಯ್ಯೋ, ಈಗ ಏನು ಮಾಡಬೇಕು?"),
         ("A", "ನಿಮ್ಮ ಫೋನಿಗೆ ಬಂದಿರುವ ಒಟಿಪಿ ತಕ್ಷಣ ಹೇಳಿ, ನಾನು ಈಗಲೇ ಅಪ್ಡೇಟ್ ಮಾಡುತ್ತೇನೆ."),
     ]},
    {"id": "kn_benign_delivery", "lang": "kn", "label": "benign",
     "lines": [
         ("A", "ನಮಸ್ಕಾರ, ನಾನು ಕೊರಿಯರ್ ಡೆಲಿವರಿಯಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ. ನಿಮ್ಮ ಪಾರ್ಸೆಲ್ ತಂದಿದ್ದೇನೆ, ಮನೆಯ ಹೊರಗೆ ಇದ್ದೇನೆ."),
         ("B", "ಸರಿ, ಈಗ ಬರುತ್ತೇನೆ."),
         ("A", "ಪಾರ್ಸೆಲ್ ತೆಗೆದುಕೊಳ್ಳುವಾಗ ಡೆಲಿವರಿ ಒಟಿಪಿ ಹೇಳಿ."),
         ("B", "ಸರಿ, ಎರಡು ನಿಮಿಷದಲ್ಲಿ ಬರುತ್ತೇನೆ."),
     ]},
    {"id": "kn_benign_family", "lang": "kn", "label": "benign",
     "lines": [
         ("A", "ಹಲೋ ಅಮ್ಮ, ಸಂಜೆ ಮನೆಗೆ ಬರುತ್ತೇನೆ."),
         ("B", "ಸರಿ ಮಗನೇ, ಊಟಕ್ಕೆ ಏನು ಮಾಡಲಿ?"),
         ("A", "ಬಿಸಿಬೇಳೆಬಾತ್ ಮಾಡು, ತುಂಬಾ ದಿನ ಆಯ್ತು."),
         ("B", "ಸರಿ, ಬೇಗ ಬಾ."),
     ]},
    {"id": "kn_awareness", "lang": "kn", "label": "benign",
     "lines": [
         ("A", "ಇದು ನಿಮ್ಮ ಬ್ಯಾಂಕಿನಿಂದ ಒಂದು ಮುಖ್ಯ ಸೂಚನೆ. ನಿಮ್ಮ ಒಟಿಪಿ, ಪಿನ್ ಅಥವಾ ಪಾಸ್ವರ್ಡ್ ಅನ್ನು ಯಾರೊಂದಿಗೂ ಹಂಚಿಕೊಳ್ಳಬೇಡಿ, "
               "ಬ್ಯಾಂಕ್ ಸಿಬ್ಬಂದಿಯೊಂದಿಗೂ ಸಹ. ಯಾರಾದರೂ ಕೇಳಿದರೆ ಸೈಬರ್ ಕ್ರೈಮ್ ಸಹಾಯವಾಣಿಗೆ ದೂರು ನೀಡಿ."),
     ]},

    # ---- Hinglish ---------------------------------------------------------------------
    {"id": "hl_scam_arrest", "lang": "hl", "label": "scam",
     "expect": ["authority", "threat", "secrecy", "credentials", "remote_access", "payment"],
     "lines": [
         ("A", "Hello, main cyber crime branch se Inspector Sharma bol raha hoon. Aapke naam ka ek parcel customs ne pakda hai."),
         ("B", "Kya? Maine toh koi parcel nahi bheja."),
         ("A", "Aapke against arrest warrant nikla hai. Yeh digital arrest hai, call cut mat karna aur kisi ko mat batana."),
         ("B", "Main kya karoon?"),
         ("A", "Abhi AnyDesk app download karo aur phone pe aaya OTP batao. Phir turant safe account mein paise transfer karo."),
     ]},
    {"id": "hl_scam_kyc", "lang": "hl", "label": "scam",
     "expect": ["lure", "threat", "urgency", "credentials"],
     "lines": [
         ("A", "Hello sir, main aapke bank ke KYC department se bol rahi hoon."),
         ("B", "Haan boliye."),
         ("A", "Aapka KYC expire ho gaya hai, aaj raat aapka account block ho jayega."),
         ("B", "Arre, ab kya karna hoga?"),
         ("A", "Aapke phone pe ek OTP aaya hoga, woh jaldi se bata dijiye, main abhi update kar deti hoon."),
     ]},
    {"id": "hl_benign_delivery", "lang": "hl", "label": "benign",
     "lines": [
         ("A", "Hello, main courier se bol raha hoon, aapka parcel lekar gate pe khada hoon."),
         ("B", "Achha, main abhi neeche aati hoon."),
         ("A", "Parcel lete time delivery OTP bata dena."),
         ("B", "Theek hai, do minute mein aati hoon."),
     ]},
    {"id": "hl_benign_friend", "lang": "hl", "label": "benign",
     "lines": [
         ("A", "Arre yaar, Saturday ko movie chalein?"),
         ("B", "Haan bilkul, shaam ka show book kar de."),
         ("A", "Done, main tickets book karta hoon, tu popcorn le aana."),
         ("B", "Pakka, milte hain."),
     ]},
    {"id": "hl_awareness", "lang": "hl", "label": "benign",
     "lines": [
         ("A", "Yeh aapke bank ki taraf se ek zaroori message hai. Apna OTP, PIN ya password kabhi bhi kisi ke saath "
               "share mat kijiye, bank staff ke saath bhi nahi. Koi maange toh cyber crime helpline pe complaint kijiye."),
     ]},
]


def script_text(call: dict) -> str:
    return " ".join(text for _, text in call["lines"])
