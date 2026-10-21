"""Evaluate the scam detector offline (no credits).

  python eval_detector.py              # summary table
  python eval_detector.py --details    # every call: level, score, tactics, missed tactics

Sources:
  script      the corpus text itself (a perfect transcript)
  clean/noisy Prisma transcripts saved by make_transcripts.py in data/real_transcripts/*.json
  pasted      your own transcripts in data/real_transcripts/*.txt; the file name must start
              with the language (kn_, hi_, en_, hl_) and contain "scam" or "benign"

A call counts as flagged when the detector says medium or high.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from corpus import CALLS, script_text
from detector import detect_rules

HERE = Path(__file__).resolve().parent
TRANSCRIPTS = HERE / "data" / "real_transcripts"


def load_samples(transcripts_dir: Path = TRANSCRIPTS) -> list[dict]:
    samples = [{"id": c["id"], "lang": c["lang"], "label": c["label"], "source": "script",
                "expect": c.get("expect", []), "text": script_text(c)} for c in CALLS]
    expect = {c["id"]: c.get("expect", []) for c in CALLS}
    for path in sorted(transcripts_dir.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        samples.append({"id": d["id"], "lang": d["lang"], "label": d["label"], "source": d["condition"],
                        "expect": expect.get(d["id"], []), "text": d["transcript"]})
    for path in sorted(transcripts_dir.glob("*.txt")):
        name = path.stem.lower()
        label = "scam" if "scam" in name else "benign" if "benign" in name or "awareness" in name else None
        if label:
            samples.append({"id": path.stem, "lang": name.split("_")[0], "label": label, "source": "pasted",
                            "expect": [], "text": path.read_text(encoding="utf-8")})
    return samples


def evaluate(samples: list[dict]) -> tuple[list[dict], dict]:
    rows, groups = [], defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0, "tn": 0})
    for s in samples:
        det = detect_rules(s["text"])
        flagged = det.level != "low"
        outcome = ("tp" if flagged else "fn") if s["label"] == "scam" else ("fp" if flagged else "tn")
        for key in [(s["source"], s["lang"]), (s["source"], "all"), ("all", "all")]:
            groups[key][outcome] += 1
        rows.append({**s, "level": det.level, "score": round(det.score, 2), "outcome": outcome,
                     "found": sorted(det.tactics), "missed": [t for t in s["expect"] if t not in det.tactics],
                     "evidence": det.tactics})
    return rows, dict(groups)


def metrics(g: dict) -> dict:
    flagged = g["tp"] + g["fp"]
    return {"recall": g["tp"] / (g["tp"] + g["fn"]) if g["tp"] + g["fn"] else None,
            "precision": g["tp"] / flagged if flagged else None,
            "false_alarm_rate": g["fp"] / (g["fp"] + g["tn"]) if g["fp"] + g["tn"] else None}


def _pct(x: float | None) -> str:
    return "  -  " if x is None else f"{x:5.0%}"


def summary(groups: dict) -> str:
    lines = [f"{'source':<8} {'lang':<5} {'scams caught':>13} {'false alarms':>13} "
             f"{'recall':>7} {'precision':>9} {'FA rate':>8}"]
    order = {"script": 0, "clean": 1, "noisy": 2, "pasted": 3, "all": 9}
    for (src, lang), g in sorted(groups.items(), key=lambda kv: (order.get(kv[0][0], 5), kv[0][1] == "all", kv[0][1])):
        m = metrics(g)
        lines.append(f"{src:<8} {lang:<5} {g['tp']:>6}/{g['tp'] + g['fn']:<6} {g['fp']:>6}/{g['fp'] + g['tn']:<6} "
                     f"{_pct(m['recall']):>7} {_pct(m['precision']):>9} {_pct(m['false_alarm_rate']):>8}")
    return "\n".join(lines)


def details(rows: list[dict]) -> str:
    out = []
    for r in rows:
        mark = {"tp": "ok  ", "tn": "ok  ", "fn": "MISS", "fp": "FA  "}[r["outcome"]]
        out.append(f"{mark} {r['source']:<7} {r['id']:<22} {r['level']:<6} {r['score']:>5}  "
                   f"found={','.join(r['found']) or '-'}" + (f"  missed={','.join(r['missed'])}" if r["missed"] else ""))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--details", action="store_true")
    args = ap.parse_args(argv)
    rows, groups = evaluate(load_samples())
    print(summary(groups))
    if args.details:
        print()
        print(details(rows))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
