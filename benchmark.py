"""Noise benchmark (Phase 4): does Scam Sentinel still work on noisy phone audio?

  python benchmark.py             # plan only: what is cached, what would be billed (no credits)
  python benchmark.py --yes       # run it (SPENDS CREDITS for anything not cached), then write the report
  python benchmark.py --report    # rebuild the report from the cache only (no credits)

All calls are SIMULATED: the scripts in corpus.py, spoken by Gnani Timbre at 8 kHz (phone quality),
with white noise mixed in at three levels. Every condition goes through the same path as the app:
split at pauses, Prisma STT (verbatim + word boosting), and the risk tracker replaying the call
utterance by utterance, so the numbers include when an alert would fire, not just the final verdict.

Outputs (results/): benchmark.csv (one row per call and noise level), benchmark.md (tables and
method), benchmark.png (chart for posts).
"""
from __future__ import annotations

import argparse
import array
import csv
import io
import json
import math
import re
import statistics
import sys
import wave
from pathlib import Path

from audio_utils import add_noise, split_on_pauses
from budget import Budget, cost, load_rates
from corpus import CALLS, LANGS, script_text
from gnani_client import CacheMiss, GnaniClient, wav_duration_seconds
from live import RiskTracker
from make_transcripts import speak_call
from tactics import BIAS_WORDS
from taxonomy import normalize

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
NOISE_LEVELS = [("clean", 30), ("medium", 1500), ("heavy", 3500)]   # white-noise amplitude, 16-bit
LANG_NAMES = {"kn": "Kannada", "hi": "Hindi", "en": "English", "hl": "Hinglish"}


# ---- measurements ----------------------------------------------------------------------------
def speech_rms(wav: bytes, window: int = 400, floor: float = 500.0) -> float:
    """RMS of the clean recording over windows that contain speech."""
    with wave.open(io.BytesIO(wav)) as w:
        s = array.array("h", w.readframes(w.getnframes()))
    wins = [math.sqrt(sum(x * x for x in s[i:i + window]) / window) for i in range(0, len(s) - window, window)]
    active = [v for v in wins if v > floor] or wins or [0.0]
    return math.sqrt(sum(v * v for v in active) / len(active))


def snr_db(clean_wav: bytes, noise_amplitude: float) -> float:
    return 20 * math.log10(max(speech_rms(clean_wav), 1.0) / max(noise_amplitude, 1.0))


def _chars(text: str) -> str:
    return re.sub(r"[\s.,!?।:;\"'()\-]", "", normalize(text))


def char_error_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein distance over characters (spaces/punctuation ignored) / reference length.
    Character-level is fairer than word-level across scripts: Prisma writes "ಕೆ ವೈ ಸಿ" for "ಕೆವೈಸಿ"."""
    ref, hyp = _chars(reference), _chars(hypothesis)
    if not ref:
        return 0.0
    prev = list(range(len(hyp) + 1))
    for i, rc in enumerate(ref, 1):
        cur = [i]
        for j, hc in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc)))
        prev = cur
    return prev[-1] / len(ref)


def run_condition(client: GnaniClient, call: dict, clean_wav: bytes, level: str, amplitude: int) -> dict:
    """One call at one noise level, through the app's path. Raises CacheMiss in offline mode."""
    wav = add_noise(clean_wav, amplitude=amplitude)
    stt_lang = LANGS[call["lang"]]["stt"]
    tracker, texts = RiskTracker(), []
    for start, chunk in split_on_pauses(wav):
        text = client.transcribe(chunk, stt_lang, filename="chunk.wav", itn=False, bias_words=BIAS_WORDS)
        texts.append(text)
        tracker.add(text, round(start + (wav_duration_seconds(chunk) or 0), 2))   # alert at end of utterance
    det = tracker.det
    duration = wav_duration_seconds(wav) or 0.0
    transcript = " ".join(t for t in texts if t)
    return {
        "id": call["id"], "lang": call["lang"], "label": call["label"], "level": level,
        "noise_amplitude": amplitude, "snr_db": round(snr_db(clean_wav, amplitude), 1),
        "audio_s": round(duration, 1), "segments": len(texts),
        "cer": round(char_error_rate(script_text(call), transcript), 3),
        "final_level": det.level, "score": round(det.score, 1),
        "flagged": det.level != "low",                      # final verdict medium or high
        "alerted": bool(tracker.first_at),                  # an alert fired at any point in the call
        "tta_medium": tracker.first_at.get("medium"), "tta_high": tracker.first_at.get("high"),
        "tactics": ",".join(sorted(det.tactics)),
        "missed": ",".join(t for t in call.get("expect", []) if t not in det.tactics),
        "transcript": transcript,
    }


# ---- plan / run ------------------------------------------------------------------------------
def collect(client: GnaniClient, calls: list[dict]) -> tuple[list[dict], dict]:
    """Rows for every condition that can be computed; in offline mode, also what is missing."""
    rows, missing = [], {"tts_chars": 0, "stt_seconds": 0.0, "conditions": 0}
    for call in calls:
        try:
            clean = speak_call(client, call)
        except CacheMiss:
            chars = sum(len(t) for _, t in call["lines"])
            missing["tts_chars"] += chars
            missing["stt_seconds"] += chars / 12 * len(NOISE_LEVELS)
            missing["conditions"] += len(NOISE_LEVELS)
            continue
        for level, amp in NOISE_LEVELS:
            try:
                rows.append(run_condition(client, call, clean, level, amp))
            except CacheMiss:
                missing["conditions"] += 1
                missing["stt_seconds"] += _uncached_seconds(client, call, clean, amp)
    return rows, missing


def _uncached_seconds(client: GnaniClient, call: dict, clean: bytes, amp: int) -> float:
    seconds = 0.0
    stt_lang = LANGS[call["lang"]]["stt"]
    for _, chunk in split_on_pauses(add_noise(clean, amplitude=amp)):
        try:
            client.transcribe(chunk, stt_lang, filename="chunk.wav", itn=False, bias_words=BIAS_WORDS)
        except CacheMiss as miss:
            seconds += miss.units
    return seconds


# ---- report ----------------------------------------------------------------------------------
def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d:.0%})" if d else "-"


def _median(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def summarise(rows: list[dict]) -> list[dict]:
    out = []
    for level, _ in NOISE_LEVELS:
        for lang in [*LANG_NAMES, "all"]:
            group = [r for r in rows if r["level"] == level and (lang == "all" or r["lang"] == lang)]
            if not group:
                continue
            scams = [r for r in group if r["label"] == "scam"]
            benign = [r for r in group if r["label"] == "benign"]
            out.append({
                "level": level, "lang": lang,
                "snr_db": round(statistics.median(r["snr_db"] for r in group), 1),
                "cer": round(statistics.mean(r["cer"] for r in group), 3),
                "scams": len(scams), "caught": sum(r["flagged"] for r in scams),
                "caught_high": sum(r["final_level"] == "high" for r in scams),
                "benign": len(benign), "false_alarms": sum(r["flagged"] for r in benign),
                "midcall_false_alarms": sum(r["alerted"] for r in benign),
                "tta_medium": _median([r["tta_medium"] for r in scams]),
                "tta_high": _median([r["tta_high"] for r in scams]),
                "tta_high_pct": _median([r["tta_high"] / r["audio_s"] for r in scams if r["tta_high"]]),
            })
    return out


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def markdown(rows: list[dict], summary: list[dict]) -> str:
    def s(v, fmt="{:.1f}", none="-"):
        return none if v is None else fmt.format(v)

    total = [x for x in summary if x["lang"] == "all"]
    lines = [
        "# Noise benchmark: Scam Sentinel on noisy phone audio",
        "",
        "**All calls are simulated**: scripts written for this project, spoken by Gnani Timbre (two voices,",
        "8 kHz phone quality), with white noise added. No real calls, numbers or people.",
        f"{len({r['id'] for r in rows})} calls ({sum(1 for c in CALLS if c['label'] == 'scam')} scam, "
        f"{sum(1 for c in CALLS if c['label'] == 'benign')} benign incl. bank awareness messages and delivery-OTP calls) "
        f"x {len(NOISE_LEVELS)} noise levels, in Kannada, Hindi, English and Hinglish.",
        "",
        "## Overall",
        "",
        "| Noise | SNR | Speech-to-text char error | Scams caught (high) | False alarms (final) | False alarms (any point) | Median time to high alert |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in total:
        lines.append(f"| {x['level']} | {x['snr_db']:.0f} dB | {x['cer']:.1%} | {_pct(x['caught'], x['scams'])} "
                     f"({x['caught_high']}) | {_pct(x['false_alarms'], x['benign'])} | "
                     f"{_pct(x['midcall_false_alarms'], x['benign'])} | {s(x['tta_high'], '{:.1f} s')} "
                     f"({s(x['tta_high_pct'], '{:.0%}')} into the call) |")
    lines += ["", "## By language", "",
              "| Noise | Language | Char error | Scams caught | False alarms (any point) | Median time to high |",
              "|---|---|---|---|---|---|"]
    for x in summary:
        if x["lang"] != "all":
            lines.append(f"| {x['level']} | {LANG_NAMES[x['lang']]} | {x['cer']:.1%} | {_pct(x['caught'], x['scams'])} | "
                         f"{_pct(x['midcall_false_alarms'], x['benign'])} | {s(x['tta_high'], '{:.1f} s')} |")
    misses = [r for r in rows if (r["label"] == "scam" and not r["flagged"]) or (r["label"] == "benign" and r["alerted"])]
    lines += ["", "## Every miss and false alarm", ""]
    if not misses:
        lines.append("None.")
    for r in misses:
        what = "MISSED scam" if r["label"] == "scam" else "FALSE ALARM"
        lines.append(f"- **{what}** `{r['id']}` at {r['level']} noise ({r['snr_db']:.0f} dB): final {r['final_level']} "
                     f"({r['score']}), tactics: {r['tactics'] or '-'}. Heard: \"{r['transcript'][:160]}\"")
    lines += ["", "## Method", "",
              "- Same path as the app: the call is split at pauses (one utterance per request), transcribed by Gnani",
              "  Prisma (verbatim, word boosting), and the risk tracker replays it utterance by utterance.",
              "- *Scams caught*: final risk medium or high. *False alarms (any point)*: a benign call that triggered",
              "  an alert at any moment, which is what a user would actually hear in live mode.",
              "- *Time to alert*: seconds of call audio until the utterance that crossed the threshold ended",
              "  (Prisma's transcription latency, about 1-2 s live, comes on top).",
              "- *SNR*: speech RMS (clean recording, speech windows only) over the added noise RMS.",
              "- *Char error*: character-level edit distance against the script, spaces and punctuation ignored.",
              "", "## Limits (read before quoting)", "",
              "- Small: 8 scam and 12 benign calls. Percentages move in big steps; treat them as indicative.",
              "- The detector was tuned on the clean and medium transcripts of these same scripts (Phase 2);",
              "  only the heavy level is unseen. Real scam calls are longer and less scripted.",
              "- White noise is a stand-in for phone-line noise; real calls add codecs, echo and background voices.",
              "- Hinglish error rates are inflated by spelling: romanised Hindi has no standard spelling",
              "  (\"main\" vs \"mein\"), so some \"errors\" are the same word written differently.",
              "- In these scripts the OTP or payment request comes near the end, so the high alert also comes late;",
              "  the medium alert is the earlier, gentler warning.",
              ""]
    return "\n".join(lines)


def chart(summary: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    INK, INK2, MUTED, GRID, BASE, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
    SERIES = {"kn": "#2a78d6", "hi": "#eb6834", "en": "#1baf7a", "hl": "#eda100"}   # validated slots 1-4
    MARKERS = {"kn": "o", "hi": "s", "en": "^", "hl": "D"}                           # secondary encoding
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 11})

    total = {x["level"]: x for x in summary if x["lang"] == "all"}
    levels = [lv for lv, _ in NOISE_LEVELS if lv in total]     # --report may cover fewer levels
    xlabels = [f"{lv.capitalize()}\n{total[lv]['snr_db']:.0f} dB SNR" for lv in levels]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4), dpi=200, facecolor=SURFACE)
    for ax in (ax1, ax2):
        ax.set_facecolor(SURFACE)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(BASE)
        ax.tick_params(colors=MUTED, length=0)
        for lab in ax.get_xticklabels() + ax.get_yticklabels():
            lab.set_color(INK2)

    # Left: speech-to-text robustness per language (lines, direct labels at the right end).
    x = list(range(len(levels)))
    for lang, color in SERIES.items():
        ys = [next((s["cer"] * 100 for s in summary if s["level"] == lv and s["lang"] == lang), None) for lv in levels]
        if None in ys:
            continue                     # language not in this run
        ax1.plot(x, ys, color=color, linewidth=2, marker=MARKERS[lang], markersize=8,
                 markeredgecolor=SURFACE, markeredgewidth=2)
        ax1.annotate(LANG_NAMES[lang], (x[-1], ys[-1]), xytext=(10, 0), textcoords="offset points",
                     va="center", color=INK2, fontsize=10)
    ax1.set_xticks(x, xlabels)
    ax1.set_xlim(-0.3, len(levels) - 0.4)
    ax1.set_ylim(0, None)
    ax1.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax1.set_title("Gnani Prisma: character error rate", loc="left", color=INK, fontsize=12.5, pad=12)

    # Right: what the user experiences (grouped bars, values labelled; one 0-100% axis).
    caught = [total[lv]["caught"] / total[lv]["scams"] * 100 for lv in levels]
    falsealarm = [total[lv]["midcall_false_alarms"] / total[lv]["benign"] * 100 for lv in levels]
    width = 0.36
    for offset, vals, color, name in ((-width / 2 - 0.01, caught, "#2a78d6", "Scam calls flagged"),
                                      (width / 2 + 0.01, falsealarm, "#eb6834", "Normal calls with a false alert")):
        bars = ax2.bar([i + offset for i in x], vals, width, color=color, label=name, zorder=2,
                       edgecolor=SURFACE, linewidth=2)          # surface gap between adjacent fills
        for b, v in zip(bars, vals):
            ax2.annotate(f"{v:.0f}%", (b.get_x() + b.get_width() / 2, v), xytext=(0, 4), textcoords="offset points",
                         ha="center", color=INK2, fontsize=10)
    ax2.set_xticks(x, xlabels)
    ax2.set_ylim(0, 112)
    ax2.set_yticks([0, 25, 50, 75, 100])
    ax2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax2.set_title("Scam Sentinel: detection vs false alerts", loc="left", color=INK, fontsize=12.5, pad=12)
    leg = ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False)
    for t in leg.get_texts():
        t.set_color(INK2)

    n_s, n_b = total[levels[0]]["scams"], total[levels[0]]["benign"]
    fig.suptitle("Scam Sentinel on noisy phone audio", x=0.012, ha="left", color=INK, fontsize=15, weight="bold")
    fig.text(0.012, 0.915, f"Simulated calls only (Gnani Timbre voices, 8 kHz, added white noise) · {n_s} scam + "
             f"{n_b} normal calls per noise level · Kannada, Hindi, English, Hinglish",
             color=INK2, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def write_report(rows: list[dict], out_dir: Path = RESULTS) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarise(rows)
    paths = {"csv": out_dir / "benchmark.csv", "md": out_dir / "benchmark.md", "png": out_dir / "benchmark.png",
             "json": out_dir / "benchmark_summary.json"}
    write_csv(rows, paths["csv"])
    paths["md"].write_text(markdown(rows, summary), encoding="utf-8")
    paths["json"].write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    chart(summary, paths["png"])
    return paths


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--yes", action="store_true", help="run, spending credits on anything not cached")
    mode.add_argument("--report", action="store_true", help="rebuild the report from the cache only")
    args = ap.parse_args(argv)

    offline_rows, missing = collect(GnaniClient(offline=True), CALLS)
    rates = load_rates()
    est = (cost("tts", missing["tts_chars"], rates) or 0) + (cost("stt", missing["stt_seconds"], rates) or 0)
    total = len(CALLS) * len(NOISE_LEVELS)
    print(f"{total} conditions ({len(CALLS)} simulated calls x {len(NOISE_LEVELS)} noise levels)")
    print(f"  cached already: {len(offline_rows)}   need real calls: {missing['conditions']}")
    print(f"  to spend: TTS {missing['tts_chars']} chars + STT {missing['stt_seconds']:.0f} s  ->  ~{est:.2f} credits")
    spent, _ = Budget().totals()
    print(f"  estimated balance now {rates['starting_credits'] - spent:.1f}")

    if args.yes and missing["conditions"]:
        client = GnaniClient()
        rows, _ = collect(client, CALLS)
        print(f"Real calls: {client.stats['tts_calls']} TTS, {client.stats['stt_calls']} STT; "
              f"cache hits: {client.stats['cache_hits']}")
    elif args.yes or args.report:
        rows = offline_rows
    else:
        print("\nNothing spent. Rerun with --yes to go ahead, or --report to use the cache only.")
        return
    if not rows:
        raise SystemExit("No results to report.")
    for name, path in write_report(rows).items():
        print(f"wrote {path.relative_to(HERE)}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
