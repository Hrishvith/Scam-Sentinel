"""Spoken "why that was wrong" for the Practice quiz, in Gnani Timbre voices (Kannada, Hindi, English).

When someone answers a quiz line wrongly, the page plays web/audio/practice/<id>-<lang>.mp3: "That's not right.
This was a scam call / a normal call", then why. Each one is synthesized ONCE and saved, so playing it costs
nothing. Existing files are skipped, and the Gnani client also caches by content, so a rerun is free.

  python make_practice_audio.py                 # dry run: what would be made and what it would cost
  python make_practice_audio.py --yes           # make the missing files (SPENDS CREDITS, about 3 per 1,000 chars)
  python make_practice_audio.py --yes --lang kn # only Kannada

Reads GNANI_API_KEY from the environment. Never prints it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from budget import load_rates
from gnani_client import GnaniClient
from pipeline import speak_alert

HERE = Path(__file__).resolve().parent
DATA = HERE / "web" / "practice.json"
OUT = HERE / "web" / "audio" / "practice"
LANG_CODES = {"kn": "kn-IN", "hi": "hi-IN", "en": "en-IN"}
# REVIEW kn/hi with native speakers
OPENING = {
    "en": {True: "That's not right. This was a scam call. ", False: "That's not right. This was a normal call. "},
    "kn": {True: "ಇದು ಸರಿಯಲ್ಲ. ಇದು ಮೋಸದ ಕರೆ. ", False: "ಇದು ಸರಿಯಲ್ಲ. ಇದು ಸಾಮಾನ್ಯ ಕರೆ. "},
    "hi": {True: "यह सही नहीं है। यह धोखाधड़ी की कॉल थी। ", False: "यह सही नहीं है। यह आम कॉल थी। "},
}


def spoken(item: dict, lang: str) -> str:
    """What the voice says after a wrong answer (1930 spaced, so it is read digit by digit)."""
    return (OPENING[lang][item["scam"]] + item["why"][lang]).replace("1930", "1 9 3 0")


def plan(langs: list[str]) -> list[tuple[str, str, str, Path]]:
    """(line id, lang, text, output file) for every explanation that has no audio file yet."""
    items = json.loads(DATA.read_text(encoding="utf-8"))["items"]
    return [(it["id"], lang, spoken(it, lang), OUT / f"{it['id']}-{lang}.mp3")
            for it in items for lang in langs if not (OUT / f"{it['id']}-{lang}.mp3").exists()]


def write_index() -> None:
    """The page reads this to know which explanations exist."""
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(p.stem for p in OUT.glob("*.mp3"))
    (OUT / "index.json").write_text(json.dumps({"files": files}, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="really call Gnani TTS (spends credits)")
    ap.add_argument("--lang", choices=list(LANG_CODES), action="append", help="only these languages")
    args = ap.parse_args()
    todo = plan(args.lang or list(LANG_CODES))
    chars = sum(len(text) for _, _, text, _ in todo)
    rate = load_rates().get("tts_credits_per_1k_chars") or 0
    print(f"{len(todo)} explanation(s) to make, {chars} characters, about {chars * rate / 1000:.1f} credits")
    for line, lang, text, _ in todo:
        print(f"  {line:<15} {lang}  {len(text):>4} chars")
    if not todo:
        write_index()
        return 0
    if not args.yes:
        print("Dry run. Add --yes to make them.")
        return 0
    client = GnaniClient()
    for line, lang, text, out in todo:
        audio, warning = speak_alert(client, text, LANG_CODES[lang])
        if audio is None:
            print(f"  {line} {lang}: skipped ({warning})")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(audio)
        print(f"  {line} {lang}: {len(audio) // 1024} KB")
    write_index()
    print(f"Done. TTS calls: {client.stats['tts_calls']}, cache hits: {client.stats['cache_hits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
