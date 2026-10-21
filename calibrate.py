"""Measure Gnani credit rates with ONE small real call at a time. SPENDS CREDITS.

Gnani does not publish prices, so we make one tiny call, read the drop on the dashboard
Usage page, and turn it into a rate with usage_report.py.

  1. Note the balance on app.gnani.ai -> Monitor -> Usage.
  2. python calibrate.py tts     # ~100 characters of Timbre TTS, saved as a 16 kHz WAV
  3. Read the new balance:  python usage_report.py --calibrate tts --drop <credits> --write
  4. python calibrate.py stt     # transcribes that WAV (~6-8 s of speech) with Prisma
  5. Read the new balance:  python usage_report.py --calibrate stt --drop <credits> --write

Calls go through the normal budget guard with GNANI_CALIBRATION=1, so they are capped by
rates.json calibration_max_*. A cached result costs nothing and measures nothing.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from gnani_client import GnaniClient, wav_duration_seconds

HERE = Path(__file__).resolve().parent
SAMPLE_WAV = HERE / "demo_calls" / "calibration_en.wav"
# Synthetic, generic text: no numbers, names or account details.
SAMPLE_TEXT = ("This is a short test sentence for measuring speech credits. "
               "It is simulated and contains no personal details.")


def main(step: str) -> None:
    os.environ["GNANI_CALIBRATION"] = "1"
    client = GnaniClient()
    if step == "tts":
        audio = client.synthesize(SAMPLE_TEXT, language="en-IN", voice="Kaveri", model="timbre-v2.5",
                                  container="wav", sample_rate=16000)
        SAMPLE_WAV.parent.mkdir(parents=True, exist_ok=True)
        SAMPLE_WAV.write_bytes(audio)
        print(f"TTS: {len(SAMPLE_TEXT)} characters -> {SAMPLE_WAV.name} "
              f"({wav_duration_seconds(audio) or 0:.1f} s). Real calls: {client.stats['tts_calls']}")
    elif step == "stt":
        if not SAMPLE_WAV.is_file():
            raise SystemExit("Run `python calibrate.py tts` first; it creates the audio to transcribe.")
        audio = SAMPLE_WAV.read_bytes()
        text = client.transcribe(audio, "en-IN", itn=False)
        print(f"STT: {wav_duration_seconds(audio) or 0:.1f} s -> {text!r}. Real calls: {client.stats['stt_calls']}")
    else:
        raise SystemExit("usage: python calibrate.py tts|stt")
    if client.stats["cache_hits"]:
        print("That was a cache hit: nothing was spent and nothing can be measured.")
    else:
        print("Now read the drop on the dashboard Usage page and run usage_report.py --calibrate.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1] if len(sys.argv) > 1 else "")
