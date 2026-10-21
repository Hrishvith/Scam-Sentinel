"""Turn the SIMULATED corpus into real Prisma transcripts. SPENDS CREDITS (only with --yes).

  python make_transcripts.py            # show the plan and estimated credit cost, spend nothing
  python make_transcripts.py --yes      # synthesize (Timbre), add noise, transcribe (Prisma)
  python make_transcripts.py --yes --only kn_scam_kyc

Each call is spoken line by line with Timbre at 8 kHz (phone quality), joined, and saved as
demo_calls/corpus/<id>_<condition>.wav. Each condition is split at pauses and transcribed in verbatim
mode with word boosting, exactly as the app does, and saved to data/real_transcripts/<id>_<condition>.json
for eval_detector.py. Everything is cached, so a rerun costs nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from audio_utils import add_noise, concat_wavs, split_on_pauses
from budget import KINDS, Budget, cost, load_rates
from corpus import CALLS, LANGS
from gnani_client import BudgetExceeded, GnaniClient, GnaniError, wav_duration_seconds
from tactics import BIAS_WORDS

HERE = Path(__file__).resolve().parent
AUDIO_DIR = HERE / "demo_calls" / "corpus"
OUT_DIR = HERE / "data" / "real_transcripts"
# White-noise amplitude (16-bit; speech peaks are ~10-20k). "clean" still gets an inaudible
# floor (~ -60 dBFS): Prisma dropped speech after digitally perfect silence, which real lines never have.
CONDITIONS = {"clean": 30, "noisy": 1500}
SAMPLE_RATE = 8000
CHARS_PER_SECOND = 12                      # rough speaking rate, only for the estimate


def plan(calls: list[dict]) -> dict:
    chars = sum(len(text) for c in calls for _, text in c["lines"])
    seconds = sum(len(text) for c in calls for _, text in c["lines"]) / CHARS_PER_SECOND * len(CONDITIONS)
    rates = load_rates()
    return {"calls": len(calls), "tts_chars": chars, "stt_seconds": seconds,
            "tts_credits": cost("tts", chars, rates), "stt_credits": cost("stt", seconds, rates)}


def speak_call(client: GnaniClient, call: dict) -> bytes:
    spec = LANGS[call["lang"]]
    parts = []
    for who, text in call["lines"]:
        voice = spec["voices"][who]
        try:
            audio = client.synthesize(text, language=spec["tts"], voice=voice, model=spec["model"],
                                      container="wav", sample_rate=SAMPLE_RATE)
        except BudgetExceeded:
            raise
        except GnaniError:
            if "fallback_voice" not in spec or voice == spec["fallback_voice"]:
                raise
            print(f"  voice {voice} rejected for {spec['tts']}, using {spec['fallback_voice']}", file=sys.stderr)
            audio = client.synthesize(text, language=spec["tts"], voice=spec["fallback_voice"],
                                      model=spec["model"], container="wav", sample_rate=SAMPLE_RATE)
        parts.append(audio)
    return concat_wavs(parts)


def transcribe_call(client: GnaniClient, wav: bytes, stt_lang: str) -> list[str]:
    """Same segmentation as pipeline.analyze_call: one utterance per request."""
    return [client.transcribe(chunk, stt_lang, filename="chunk.wav", itn=False, bias_words=BIAS_WORDS)
            for _, chunk in split_on_pauses(wav)]


def run(calls: list[dict]) -> None:
    client = GnaniClient()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for call in calls:
        clean = speak_call(client, call)
        for condition, amplitude in CONDITIONS.items():
            wav = add_noise(clean, amplitude=amplitude)
            (AUDIO_DIR / f"{call['id']}_{condition}.wav").write_bytes(wav)
            chunks = transcribe_call(client, wav, LANGS[call["lang"]]["stt"])
            record = {"id": call["id"], "lang": call["lang"], "label": call["label"], "condition": condition,
                      "simulated": True, "stt_language": LANGS[call["lang"]]["stt"],
                      "noise_amplitude": amplitude, "audio_seconds": round(wav_duration_seconds(wav) or 0, 2),
                      "chunks": chunks, "transcript": " ".join(chunks)}
            (OUT_DIR / f"{call['id']}_{condition}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{call['id']:<22} {condition:<6} {record['audio_seconds']:5.1f}s  {record['transcript'][:70]}")
    print(f"\nReal calls: {client.stats['tts_calls']} TTS, {client.stats['stt_calls']} STT; "
          f"cache hits: {client.stats['cache_hits']}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="actually spend credits")
    ap.add_argument("--only", nargs="*", help="call ids to run (default: all)")
    args = ap.parse_args(argv)
    calls = [c for c in CALLS if not args.only or c["id"] in args.only]
    p = plan(calls)
    print(f"{p['calls']} simulated calls x {len(CONDITIONS)} conditions ({', '.join(CONDITIONS)})")
    print(f"  TTS  {p['tts_chars']:>6} chars      ~{p['tts_credits'] or 0:.1f} credits (upper bound; cached lines are free)")
    print(f"  STT  {p['stt_seconds']:>6.0f} s audio    ~{p['stt_credits'] or 0:.1f} credits")
    spent, _ = Budget().totals()
    print(f"  estimated balance now {load_rates()['starting_credits'] - spent:.1f}")
    if not args.yes:
        print("\nNothing spent. Rerun with --yes to go ahead.")
        return
    run(calls)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
