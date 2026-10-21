"""Generate a SIMULATED scam call for demos: two Timbre voices, 8 kHz phone-quality WAV, plus line noise.

    python make_demo_call.py en     # or: hi, kn
    -> demo_calls/call_en.wav

Label it "simulated" in your demo post. Never use a real person's voice or a real call.
Costs a few TTS calls once; results are cached in .cache/.
"""
from __future__ import annotations

import sys
from pathlib import Path

from audio_utils import add_noise, concat_wavs
from gnani_client import GnaniClient

# (speaker, text). Speaker "S" is the scammer, "V" is the victim.
SCRIPTS = {
    "en": {
        "language": "en-IN", "voices": {"S": "Pranav", "V": "Kaveri"},
        "lines": [
            ("S", "Hello, this is Inspector Rao from the cyber crime branch. A parcel in your name has been caught by customs."),
            ("V", "What? I did not send any parcel."),
            ("S", "There is an arrest warrant against you. This is a digital arrest. Do not disconnect this call and do not tell anyone."),
            ("V", "Please, what should I do?"),
            ("S", "Install the app AnyDesk right now and tell me the OTP on your phone. Then transfer the verification amount to a safe account immediately."),
        ],
    },
    "hi": {
        "language": "hi-IN", "voices": {"S": "Deepak", "V": "Nalini"},
        "lines": [
            ("S", "नमस्ते, मैं साइबर क्राइम से इंस्पेक्टर बोल रहा हूँ। आपके नाम का एक पार्सल कस्टम ने पकड़ा है।"),
            ("V", "क्या? मैंने तो कोई पार्सल नहीं भेजा।"),
            ("S", "आपके खिलाफ़ गिरफ्तारी वारंट है। यह डिजिटल अरेस्ट है। कॉल कट मत करना और किसी को मत बताना।"),
            ("V", "मुझे क्या करना होगा?"),
            ("S", "अभी एनीडेस्क ऐप डाउनलोड करें और अपना ओटीपी बताएं। फिर तुरंत सुरक्षित खाते में पैसे भेजें।"),
        ],
    },
    "kn": {
        "language": "kn-IN", "voices": {"S": "Kavin", "V": "Saanvi"},
        "lines": [
            ("S", "ನಮಸ್ಕಾರ, ನಾನು ಸೈಬರ್ ಕ್ರೈಮ್ ಇನ್ಸ್ಪೆಕ್ಟರ್ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ. ನಿಮ್ಮ ಹೆಸರಿನ ಪಾರ್ಸೆಲ್ ಅನ್ನು ಕಸ್ಟಮ್ಸ್ ಹಿಡಿದಿದೆ."),
            ("V", "ಏನು? ನಾನು ಯಾವ ಪಾರ್ಸೆಲ್ ಕೂಡ ಕಳುಹಿಸಿಲ್ಲ."),
            ("S", "ನಿಮ್ಮ ವಿರುದ್ಧ ಅರೆಸ್ಟ್ ವಾರೆಂಟ್ ಇದೆ. ಇದು ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್. ಕರೆ ಕಟ್ ಮಾಡಬೇಡಿ, ಯಾರಿಗೂ ಹೇಳಬೇಡಿ."),
            ("V", "ನಾನು ಏನು ಮಾಡಬೇಕು?"),
            ("S", "ಈಗಲೇ ಎನಿಡೆಸ್ಕ್ ಆ್ಯಪ್ ಡೌನ್ಲೋಡ್ ಮಾಡಿ, ನಿಮ್ಮ ಒಟಿಪಿ ಹೇಳಿ. ತಕ್ಷಣ ಸುರಕ್ಷಿತ ಖಾತೆಗೆ ಹಣ ಕಳುಹಿಸಿ."),
        ],
    },
}


def build(lang_key: str, out_dir: str = "demo_calls", noise: int = 400) -> Path:
    spec = SCRIPTS[lang_key]
    client = GnaniClient()
    parts = [client.synthesize(text, language=spec["language"], voice=spec["voices"][who],
                               model="timbre-v2.5", container="wav", sample_rate=8000)
             for who, text in spec["lines"]]
    wav = add_noise(concat_wavs(parts), amplitude=noise)
    path = Path(out_dir)
    path.mkdir(exist_ok=True)
    out = path / f"call_{lang_key}.wav"
    out.write_bytes(wav)
    return out


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "en"
    if key not in SCRIPTS:
        sys.exit(f"Choose one of: {', '.join(SCRIPTS)}")
    print("Wrote", build(key))
