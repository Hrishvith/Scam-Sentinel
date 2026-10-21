import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_RATES = {"starting_credits": 1000, "reserve_fraction": 0.2,
              "stt_credits_per_audio_second": 0.1, "tts_credits_per_1k_chars": 1.0,
              "calibration_max_audio_seconds": 120, "calibration_max_chars": 1000}


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    """Every test gets its own rates.json and ledger; the real ones are never touched."""
    rates = tmp_path / "rates.json"
    ledger = tmp_path / "usage_ledger.jsonl"
    rates.write_text(json.dumps(TEST_RATES), encoding="utf-8")
    monkeypatch.setenv("GNANI_RATES", str(rates))
    monkeypatch.setenv("GNANI_LEDGER", str(ledger))
    monkeypatch.delenv("GNANI_CALIBRATION", raising=False)
    return SimpleNamespace(rates=rates, ledger=ledger)
