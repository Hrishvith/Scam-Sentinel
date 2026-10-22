"""Benchmark logic, offline (fake Gnani client, no credits)."""
import io
import wave

import pytest

import benchmark
from benchmark import char_error_rate, collect, run_condition, snr_db, summarise
from gnani_client import CacheMiss, GnaniClient
from test_phase2 import speechlike
from test_sentinel import FakeResp, make_client

CALL = {"id": "en_scam_x", "lang": "en", "label": "scam", "expect": ["authority", "credentials"],
        "lines": [("A", "This is the CBI, there is an arrest warrant."), ("A", "Tell me the OTP now.")]}
BENIGN = {"id": "en_benign_x", "lang": "en", "label": "benign", "lines": [("A", "See you at lunch.")]}


def test_char_error_rate_ignores_spacing_and_punctuation():
    assert char_error_rate("ಕೆವೈಸಿ ಅವಧಿ.", "ಕೆ ವೈ ಸಿ ಅವಧಿ") == 0.0
    assert char_error_rate("abcd", "abxd") == pytest.approx(0.25)
    assert char_error_rate("abc", "") == 1.0


def test_snr_falls_as_noise_rises():
    clean = speechlike([("s", 1.0), ("q", 0.5), ("s", 1.0)])
    assert snr_db(clean, 30) > snr_db(clean, 1500) > snr_db(clean, 3500)


def test_run_condition_replays_utterances_and_times_the_alert(tmp_path):
    texts = iter(["this is the cbi there is an arrest warrant", "tell me the otp now"])
    client, calls = make_client(tmp_path, lambda url, kw, n: FakeResp(json_body={"success": True,
                                                                                "transcript": next(texts)}))
    clean = speechlike([("q", 0.3), ("s", 2.0), ("q", 0.8), ("s", 1.5), ("q", 0.3)])
    row = run_condition(client, CALL, clean, "medium", 1500)
    assert row["segments"] == 2 and row["final_level"] == "high" and row["flagged"] and row["alerted"]
    assert 0 < row["tta_medium"] < row["tta_high"] <= row["audio_s"]     # medium after utterance 1, high after 2
    assert row["missed"] == "" and row["level"] == "medium" and row["snr_db"] > 0


def test_offline_plan_counts_only_uncached_work(tmp_path, monkeypatch):
    clean = speechlike([("s", 2.0), ("q", 0.8), ("s", 2.0)])
    monkeypatch.setattr(benchmark, "speak_call", lambda client, call: clean)
    offline = GnaniClient("k", cache_dir=tmp_path, offline=True)
    rows, missing = collect(offline, [CALL])
    assert rows == [] and missing["conditions"] == 3 and missing["stt_seconds"] > 0

    online, calls = make_client(tmp_path, lambda url, kw, n: FakeResp(json_body={"success": True, "transcript": "hi"}))
    collect(online, [CALL])                                  # fills the cache
    rows, missing = collect(GnaniClient("k", cache_dir=tmp_path, offline=True), [CALL])
    assert len(rows) == 3 and missing == {"tts_chars": 0, "stt_seconds": 0.0, "conditions": 0}


def test_offline_client_never_calls_the_api(tmp_path):
    client = GnaniClient("k", cache_dir=tmp_path, offline=True)
    client._session.post = lambda *a, **k: pytest.fail("offline client made a request")
    with pytest.raises(CacheMiss):
        client.synthesize("hello")


def test_summary_and_report(tmp_path):
    def row(cid, label, level, flagged, alerted, tta=None):
        return {"id": cid, "lang": "en", "label": label, "level": level, "snr_db": 13.0, "cer": 0.05,
                "audio_s": 20.0, "final_level": "high" if flagged else "low", "score": 9.0 if flagged else 0.0,
                "flagged": flagged, "alerted": alerted, "tta_medium": tta, "tta_high": tta, "tactics": "",
                "missed": "", "transcript": "x", "segments": 3, "noise_amplitude": 1500}
    rows = [row("a", "scam", lv, True, True, 10.0) for lv, _ in benchmark.NOISE_LEVELS] + \
           [row("b", "benign", lv, False, lv == "heavy") for lv, _ in benchmark.NOISE_LEVELS]
    summary = summarise(rows)
    heavy = next(s for s in summary if s["level"] == "heavy" and s["lang"] == "all")
    assert heavy["caught"] == 1 and heavy["false_alarms"] == 0 and heavy["midcall_false_alarms"] == 1
    assert heavy["tta_high_pct"] == pytest.approx(0.5)
    paths = benchmark.write_report(rows, tmp_path)
    assert paths["png"].stat().st_size > 10_000 and "FALSE ALARM" in paths["md"].read_text(encoding="utf-8")
