"""Re-enacted scam calls for the Real scams page: two Gnani Timbre voices act out each scam, then
Scam Sentinel's real warning cuts in and the person hangs up.

  S  the scammer         v2.5 Kavin (kn) / Deepak (hi) / Pranav (en)
  V  the person called   v2.5 Saanvi (kn) / Nalini (hi) / Kaveri (en)
  W  Scam Sentinel       the same spoken warning the protected phone plays, for the level the detector reaches

Every line is synthesized ONCE and saved as web/audio/scenes/<id>-<lang>-<n>.mp3; the page plays the saved
files, so listening costs nothing. Lines already made (or already in the Gnani cache) are free.

  python make_scene_audio.py                 # dry run: what is missing and what it would cost
  python make_scene_audio.py --yes           # make it (SPENDS CREDITS, about 3 per 1,000 characters)
  python make_scene_audio.py --yes --lang kn # only Kannada

Reads GNANI_API_KEY from the environment. Never prints it. All dialogue is synthetic; no real voices.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from alerts import alert_text
from budget import load_rates
from detector import detect_rules
from gnani_client import BudgetExceeded, CacheMiss, GnaniClient, GnaniError
from pipeline import ALERT_VOICES

HERE = Path(__file__).resolve().parent
DATA = HERE / "web" / "scams.json"
OUT = HERE / "web" / "audio" / "scenes"
LANG_CODES = {"kn": "kn-IN", "hi": "hi-IN", "en": "en-IN"}
VOICES = {"S": {"kn": "Kavin", "hi": "Deepak", "en": "Pranav"}, "V": {"kn": "Saanvi", "hi": "Nalini", "en": "Kaveri"}}


def lines(langs: list[str]) -> list[dict]:
    """Every line of every scene: what to say, in which voice, and where its audio goes."""
    out = []
    for s in json.loads(DATA.read_text(encoding="utf-8"))["scams"]:
        for lang in langs:
            scene = s["scene"][lang]
            said = [t for who, t in scene[:scene.index(["W", ""])] if who == "S"]
            for n, (who, text) in enumerate(scene):
                if who == "W":                      # the warning for the level the scammer's words reached
                    text = alert_text(LANG_CODES[lang], detect_rules(" ".join(said)))
                out.append({"scene": f"{s['id']}-{lang}", "who": who, "lang": lang, "text": text,
                            "file": OUT / f"{s['id']}-{lang}-{n}.mp3"})
    return out


def synthesize(client: GnaniClient, line: dict) -> bytes:
    lang = LANG_CODES[line["lang"]]
    if line["who"] in VOICES:
        return client.synthesize(line["text"], language=lang, voice=VOICES[line["who"]][line["lang"]], model="timbre-v2.5")
    last = None
    for model, voice in ALERT_VOICES:              # Timbre v3.0 first, v2.5 if it fails (like the live warnings)
        try:
            return client.synthesize(line["text"], language=lang, model=model,
                                     voice=voice if isinstance(voice, str) else voice.get(lang, "Kaveri"))
        except (BudgetExceeded, CacheMiss):
            raise
        except GnaniError as exc:
            last = exc
    raise last


def write_index() -> None:
    """The page reads this to know which scenes have audio (all their lines present)."""
    OUT.mkdir(parents=True, exist_ok=True)
    scenes: dict[str, bool] = {}
    for line in lines(list(LANG_CODES)):
        scenes[line["scene"]] = scenes.get(line["scene"], True) and line["file"].exists()
    (OUT / "index.json").write_text(json.dumps({"scenes": sorted(k for k, ok in scenes.items() if ok)}, indent=1) + "\n",
                                    encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="really call Gnani TTS (spends credits)")
    ap.add_argument("--lang", choices=list(LANG_CODES), action="append", help="only these languages")
    args = ap.parse_args()
    todo = [line for line in lines(args.lang or list(LANG_CODES)) if not line["file"].exists()]
    cached = GnaniClient(offline=True)
    paid, seen = [], set()
    for line in todo:                               # cached lines are free; a repeated warning is paid once
        voice = (line["who"], line["lang"], line["text"])
        if voice in seen:
            continue
        seen.add(voice)
        try:
            synthesize(cached, line)
        except CacheMiss:
            paid.append(line)
    chars = sum(len(line["text"]) for line in paid)
    rate = load_rates().get("tts_credits_per_1k_chars") or 0
    print(f"{len(todo)} line(s) to save, {len(paid)} need Gnani TTS: {chars} characters, about {chars * rate / 1000:.1f} credits")
    if not todo:
        write_index()
        return 0
    if not args.yes:
        print("Dry run. Add --yes to make them.")
        return 0
    client = GnaniClient()
    for line in todo:
        try:
            audio = synthesize(client, line)
        except BudgetExceeded as exc:
            print(f"Stopped: {exc}")
            break
        line["file"].parent.mkdir(parents=True, exist_ok=True)
        line["file"].write_bytes(audio)
    write_index()
    print(f"Done. TTS calls: {client.stats['tts_calls']}, cache hits: {client.stats['cache_hits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
