"""Family-voice warning (Phase 5a): the high-risk warning spoken in YOUR OWN cloned voice.

Idea: an elderly parent is far more likely to hang up when their son or daughter says "this is a
scam, cut the call" than when an app does. Only ever clone your own voice, with your consent; the
app always labels the warning as an AI clone. Everything stays in voice/ (gitignored).

  python family_voice.py record [--lang en|kn] [--seconds 20]   # free: record a clean reference
  python family_voice.py enroll --name "Your name" --i-am-the-speaker   # SPENDS: one embedding call
  python family_voice.py preview --lang kn                      # SPENDS: the warning in your voice
  python family_voice.py delete                                 # remove your voice data everywhere

Gnani docs: POST /api/v1/tts/voice-clone/embeddings (5-30 s of clean audio) returns an embedding
that is stored locally and sent with every synthesis (model vachana-vc-v1). Cloned-voice language
support and pricing are not documented, so preview each language before relying on it.
"""
from __future__ import annotations

import argparse
import array
import io
import json
import math
import sys
import wave
from datetime import datetime
from pathlib import Path

from alerts import FAMILY_WARNINGS, lang_key
from gnani_client import GnaniClient, GnaniError

HERE = Path(__file__).resolve().parent
VOICE_DIR = HERE / "voice"
REFERENCE = VOICE_DIR / "reference.wav"
PROFILE = VOICE_DIR / "profile.json"
RATE = 16000

PASSAGES = {
    "en": ("Hello, this is my own voice, recorded with my consent for the Scam Sentinel project. "
           "Today the weather is pleasant, and I am planning to visit the market in the evening. "
           "I like reading books, listening to music, and spending time with my family."),
    "kn": ("ನಮಸ್ಕಾರ, ಇದು ನನ್ನದೇ ಧ್ವನಿ, ಸ್ಕ್ಯಾಮ್ ಸೆಂಟಿನೆಲ್ ಯೋಜನೆಗಾಗಿ ನನ್ನ ಒಪ್ಪಿಗೆಯೊಂದಿಗೆ ರೆಕಾರ್ಡ್ ಮಾಡಲಾಗಿದೆ. "
           "ಇಂದು ಹವಾಮಾನ ಚೆನ್ನಾಗಿದೆ, ಸಂಜೆ ಮಾರುಕಟ್ಟೆಗೆ ಹೋಗಬೇಕೆಂದಿದ್ದೇನೆ. "
           "ನನಗೆ ಪುಸ್ತಕ ಓದುವುದು, ಸಂಗೀತ ಕೇಳುವುದು ಮತ್ತು ಕುಟುಂಬದೊಂದಿಗೆ ಸಮಯ ಕಳೆಯುವುದು ಇಷ್ಟ."),
}


# ---- reference quality ---------------------------------------------------------------------
def _wav(samples: array.array, rate: int = RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


def check_reference(samples: array.array, rate: int = RATE) -> tuple[array.array, dict, list[str]]:
    """Trim leading/trailing silence and judge the take. Returns (trimmed, stats, problems)."""
    win = rate // 20                                              # 50 ms windows
    rms = [math.sqrt(sum(x * x for x in samples[i:i + win]) / win) for i in range(0, len(samples) - win + 1, win)]
    if not rms:
        return samples, {"seconds": 0.0}, ["No audio was recorded."]
    floor = sorted(rms)[len(rms) // 10]
    loud = sorted(rms)[int(len(rms) * 0.9)]
    voiced = [i for i, r in enumerate(rms) if r > max(4 * floor, 300)]
    start, end = (max(0, voiced[0] - 6), min(len(rms), voiced[-1] + 7)) if voiced else (0, len(rms))
    trimmed = samples[start * win:end * win]
    peak = max((abs(x) for x in trimmed), default=0)
    clipped = sum(1 for x in trimmed if abs(x) >= 32000) / max(1, len(trimmed))
    stats = {"seconds": round(len(trimmed) / rate, 1), "peak": peak, "noise_rms": round(floor),
             "snr_db": round(20 * math.log10(max(loud, 1) / max(floor, 1)), 1),
             "speech_share": round(len(voiced) / max(1, end - start), 2), "clipped": round(clipped, 4)}
    problems = []
    if stats["seconds"] < 5:
        problems.append("Too short: Gnani needs 5-30 s of speech. Read the whole passage.")
    if stats["seconds"] > 30:
        problems.append("Too long: keep it under 30 s.")
    if peak < 3000:
        problems.append("Too quiet: move closer to the microphone or speak up.")
    if clipped > 0.001:
        problems.append("Distorted (clipping): move back a little or speak a bit softer.")
    if stats["snr_db"] < 20:
        problems.append("Too much background noise: find a quieter room (fans, TV and traffic off).")
    return trimmed, stats, problems


# ---- commands ------------------------------------------------------------------------------
def cmd_record(args) -> None:
    import sounddevice as sd

    print("Read this aloud, clearly and at a normal pace, in a quiet room:\n")
    print("   " + PASSAGES[args.lang] + "\n")
    input("Press Enter, then start reading straight away... ")
    print(f"Recording {args.seconds} s ...")
    data = sd.rec(int(args.seconds * RATE), samplerate=RATE, channels=1, dtype="int16")
    sd.wait()
    trimmed, stats, problems = check_reference(array.array("h", data.tobytes()))
    print(f"\n{stats['seconds']} s of speech · peak {stats['peak']} · noise floor {stats['noise_rms']} · "
          f"speech-to-noise {stats['snr_db']} dB · clipping {stats['clipped']:.2%}")
    if problems:
        print("Not saved. " + " ".join(problems) + " Run `record` again.")
        sys.exit(1)
    VOICE_DIR.mkdir(exist_ok=True)
    REFERENCE.write_bytes(_wav(trimmed))
    print(f"Good take, saved to {REFERENCE.relative_to(HERE)} (local only, never committed).")
    print("Listen to it if you like, then run: python family_voice.py enroll --name \"Your name\" --i-am-the-speaker")


def cmd_enroll(args) -> None:
    if not args.i_am_the_speaker:
        raise SystemExit("Only clone your own voice. Re-run with --i-am-the-speaker to confirm the "
                         "reference recording is you and that you consent to an AI copy of your voice.")
    if not REFERENCE.is_file():
        raise SystemExit("No reference yet: run `python family_voice.py record` first.")
    emb = GnaniClient().voice_embedding(REFERENCE.read_bytes())
    profile = {"name": args.name, "created": datetime.now().isoformat(timespec="seconds"),
               "consent": "Speaker confirmed this is their own voice and consented to an AI clone (--i-am-the-speaker).",
               **emb}
    PROFILE.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(f"Voice profile for {args.name} saved to {PROFILE.relative_to(HERE)} (local only). "
          f"Embedding shape {emb['shape']}, {emb['dtype']}.")


def load_profile() -> dict | None:
    return json.loads(PROFILE.read_text(encoding="utf-8")) if PROFILE.is_file() else None


def family_warning_audio(client: GnaniClient, profile: dict, lang: str) -> bytes:
    return client.synthesize_cloned(FAMILY_WARNINGS[lang_key(lang)], profile, container="wav", sample_rate=16000)


def cmd_preview(args) -> None:
    profile = load_profile()
    if not profile:
        raise SystemExit("No voice profile yet: run `record` and `enroll` first.")
    audio = family_warning_audio(GnaniClient(), profile, args.lang)
    out = VOICE_DIR / f"preview_{lang_key(args.lang)}.wav"
    out.write_bytes(audio)
    print(f"[AI clone of {profile['name']}'s voice] {FAMILY_WARNINGS[lang_key(args.lang)]}")
    print(f"Saved {out.relative_to(HERE)}; playing it now.")
    import winsound
    winsound.PlaySound(audio, winsound.SND_MEMORY)


def cmd_delete(args) -> None:
    removed = 0
    for path in list(VOICE_DIR.glob("*")) if VOICE_DIR.is_dir() else []:
        path.unlink()
        removed += 1
    cache = HERE / ".cache"
    for path in list(cache.glob("vcemb-*")) + list(cache.glob("vctts-*")) if cache.is_dir() else []:
        path.unlink()
        removed += 1
    print(f"Removed {removed} file(s): reference recording, voice profile and cloned audio. "
          "(Gnani keeps no server-side voice id according to its docs.)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="record a clean reference of your voice (free)")
    r.add_argument("--lang", choices=list(PASSAGES), default="en")
    r.add_argument("--seconds", type=int, default=22)
    e = sub.add_parser("enroll", help="create your voice profile (one API call)")
    e.add_argument("--name", required=True, help="shown on the label, e.g. your first name")
    e.add_argument("--i-am-the-speaker", action="store_true")
    p = sub.add_parser("preview", help="speak the family warning in your cloned voice")
    p.add_argument("--lang", default="kn-IN")
    sub.add_parser("delete", help="delete your voice data")
    args = ap.parse_args(argv)
    try:
        {"record": cmd_record, "enroll": cmd_enroll, "preview": cmd_preview, "delete": cmd_delete}[args.cmd](args)
    except GnaniError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
