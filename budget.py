"""Credit ledger and budget guard for the Gnani API.

Every call that reaches the API is appended to usage_ledger.jsonl; cache hits are logged
too, at zero cost. Before a real call the guard estimates its cost from rates.json and
refuses it if it would dip into the reserve (20% of the starting credits by default).

Gnani does not publish per-unit prices, so rates.json starts with nulls. Until a rate is
measured, calls of that kind are refused unless GNANI_CALIBRATION=1 is set, and even then
only a small calibration allowance (rates.json: calibration_max_*) may be used.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

DEFAULT_RATES = {
    "starting_credits": 5000,
    "reserve_fraction": 0.20,
    "stt_credits_per_audio_second": None,
    "tts_credits_per_1k_chars": None,
    "stt_stream_credits_per_audio_second": None,  # None: billed like REST STT, per streamed second
    "calibration_max_audio_seconds": 120,
    "calibration_max_chars": 1000,
}

# kind -> (ledger unit field, rates.json key, units per rate unit, calibration cap key)
KINDS = {
    "stt": ("audio_seconds", "stt_credits_per_audio_second", 1.0, "calibration_max_audio_seconds"),
    "tts": ("chars", "tts_credits_per_1k_chars", 1000.0, "calibration_max_chars"),
    # Realtime STT: units are seconds streamed (silence included), the conservative assumption.
    "stt_stream": ("audio_seconds", "stt_stream_credits_per_audio_second", 1.0, "calibration_max_audio_seconds"),
    # Voice cloning: prices undocumented. Until measured, enrolment is estimated like STT on the
    # reference audio and cloned speech like standard TTS (assumptions, replaced once measured).
    "vc_embed": ("audio_seconds", "vc_embed_credits_per_audio_second", 1.0, "calibration_max_audio_seconds"),
    "tts_vc": ("chars", "tts_vc_credits_per_1k_chars", 1000.0, "calibration_max_chars"),
}
# A kind whose own rate is unmeasured borrows this one's rate.
FALLBACK_RATE = {"stt_stream": "stt", "vc_embed": "stt", "tts_vc": "tts"}


def rates_path() -> Path:
    return Path(os.getenv("GNANI_RATES", HERE / "rates.json"))


def ledger_path() -> Path:
    return Path(os.getenv("GNANI_LEDGER", HERE / "usage_ledger.jsonl"))


def load_rates(path: Path | None = None) -> dict:
    path = path or rates_path()
    rates = dict(DEFAULT_RATES)
    if path.is_file():
        rates.update({k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items()
                      if not k.startswith("_")})
    return rates


def read_ledger(path: Path | None = None) -> list[dict]:
    path = path or ledger_path()
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def cost(kind: str, units: float, rates: dict) -> float | None:
    """Credits for `units` of `kind`, or None while the rate is unmeasured."""
    _, key, per, _ = KINDS[kind]
    rate = rates.get(key)
    if rate is None and kind in FALLBACK_RATE:
        return cost(FALLBACK_RATE[kind], units, rates)
    return None if rate is None else units / per * float(rate)


@dataclass
class Estimate:
    kind: str
    units: float
    credits: float | None
    spent: float
    remaining: float
    reserve: float
    ok: bool
    reason: str = ""

    def line(self) -> str:
        unit = KINDS[self.kind][0].replace("_", " ")
        price = "unmeasured" if self.credits is None else f"~{self.credits:.2f} credits"
        status = "OK" if self.ok else f"REFUSED: {self.reason}"
        return (f"[budget] {self.kind} {self.units:.1f} {unit} -> {price}; "
                f"est. remaining {self.remaining:.1f} (reserve {self.reserve:.0f}) {status}")


class Budget:
    def __init__(self, rates_file: Path | None = None, ledger_file: Path | None = None):
        self.rates_file = rates_file or rates_path()
        self.ledger_file = ledger_file or ledger_path()

    def totals(self) -> tuple[float, dict[str, float]]:
        """(estimated credits spent, units used per kind whose rate is still unmeasured)."""
        rates = load_rates(self.rates_file)
        spent, unmeasured = 0.0, {k: 0.0 for k in KINDS}
        for row in read_ledger(self.ledger_file):
            if row.get("cache_hit") or row.get("kind") not in KINDS:
                continue
            units = float(row.get(KINDS[row["kind"]][0]) or 0)
            c = cost(row["kind"], units, rates)
            if c is None:
                unmeasured[row["kind"]] += units
            else:
                spent += c
        return spent, unmeasured

    def check(self, kind: str, units: float) -> Estimate:
        rates = load_rates(self.rates_file)  # re-read so edits to rates.json apply at once
        start = float(rates["starting_credits"])
        reserve = start * float(rates["reserve_fraction"])
        spent, unmeasured = self.totals()
        credits = cost(kind, units, rates)
        est = Estimate(kind, units, credits, spent, start - spent - (credits or 0), reserve, True)
        if credits is None:
            cap = float(rates[KINDS[kind][3]])
            if os.getenv("GNANI_CALIBRATION") != "1":
                est.ok, est.reason = False, (f"the {kind} rate is not measured yet (rates.json); "
                                             "run calibrate.py to measure it")
            elif unmeasured[kind] + units > cap:
                est.ok, est.reason = False, (f"calibration allowance for {kind} used up "
                                             f"({unmeasured[kind]:.0f} + {units:.0f} > {cap:.0f})")
        elif est.remaining < reserve:
            est.ok, est.reason = False, f"would dip into the {rates['reserve_fraction']:.0%} reserve"
        return est

    def record(self, kind: str, units: float, *, language: str, model: str, cache_hit: bool,
               request_id: str | None = None, units_estimated: bool = False, **extra) -> None:
        row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": kind,
               KINDS[kind][0]: round(units, 3), "language": language, "model": model,
               "cache_hit": cache_hit}
        if request_id:
            row["request_id"] = request_id
        if units_estimated:
            row["units_estimated"] = True
        row.update(extra)
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
