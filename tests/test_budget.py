import json

import pytest

import usage_report
from budget import Budget, read_ledger
from gnani_client import BudgetExceeded
from pipeline import analyze_call, analyze_transcripts
from test_sentinel import SCAMS, FakeResp, make_client, wav_bytes


def stt_ok(url, kw, n):
    return FakeResp(json_body={"success": True, "request_id": f"r{n}", "transcript": "hello"})


def set_rates(isolated_budget, **changes):
    data = json.loads(isolated_budget.rates.read_text(encoding="utf-8"))
    data.update(changes)
    isolated_budget.rates.write_text(json.dumps(data), encoding="utf-8")


def test_real_calls_and_cache_hits_are_logged(tmp_path, isolated_budget):
    client, calls = make_client(tmp_path, stt_ok)
    audio = wav_bytes(10)
    client.transcribe(audio, "kn-IN")
    client.transcribe(audio, "kn-IN")  # cache hit
    rows = read_ledger(isolated_budget.ledger)
    assert len(calls) == 1 and [r["cache_hit"] for r in rows] == [False, True]
    assert rows[0]["kind"] == "stt" and rows[0]["audio_seconds"] == 10.0
    assert rows[0]["language"] == "kn-IN" and rows[0]["request_id"] == "r1"
    spent, _ = client.budget.totals()
    assert spent == pytest.approx(1.0)  # 10 s * 0.1, the cache hit is free


def test_tts_logs_characters_and_model(tmp_path, isolated_budget):
    client, _ = make_client(tmp_path, lambda url, kw, n: FakeResp(content=b"audio"))
    client.synthesize("a" * 500, language="hi-IN", voice="Chetana", model="timbre-v3.0")
    (row,) = read_ledger(isolated_budget.ledger)
    assert row["kind"] == "tts" and row["chars"] == 500 and row["model"] == "timbre-v3.0"
    assert client.budget.totals()[0] == pytest.approx(0.5)


def test_unmeasured_rate_refuses_without_calling_the_api(tmp_path, isolated_budget):
    set_rates(isolated_budget, stt_credits_per_audio_second=None)
    client, calls = make_client(tmp_path, stt_ok)
    with pytest.raises(BudgetExceeded, match="not measured"):
        client.transcribe(wav_bytes(5), "en-IN")
    assert calls == [] and read_ledger(isolated_budget.ledger) == []


def test_calibration_allowance_is_capped(tmp_path, isolated_budget, monkeypatch):
    set_rates(isolated_budget, tts_credits_per_1k_chars=None, calibration_max_chars=150)
    monkeypatch.setenv("GNANI_CALIBRATION", "1")
    client, calls = make_client(tmp_path, lambda url, kw, n: FakeResp(content=b"audio"))
    client.synthesize("x" * 100)
    with pytest.raises(BudgetExceeded, match="allowance"):
        client.synthesize("y" * 100)  # 100 + 100 > 150
    assert len(calls) == 1


def test_call_that_would_dip_into_reserve_is_refused(tmp_path, isolated_budget):
    # 1000 credits, 200 reserve, 10 credits per second: 50 s would leave 500, 30 s more leaves 200
    set_rates(isolated_budget, stt_credits_per_audio_second=10.0)
    client, calls = make_client(tmp_path, stt_ok)
    client.transcribe(wav_bytes(50, fills=(1,)), "en-IN")
    client.transcribe(wav_bytes(30, fills=(2,)), "en-IN")  # lands exactly on the reserve: allowed
    with pytest.raises(BudgetExceeded, match="reserve"):
        client.transcribe(wav_bytes(1, fills=(3,)), "en-IN")
    assert len(calls) == 2


def test_estimate_is_printed_before_a_real_call(tmp_path, capsys):
    client, _ = make_client(tmp_path, stt_ok)
    client.transcribe(wav_bytes(20), "en-IN")
    err = capsys.readouterr().err
    assert "[budget] stt 20.0 audio seconds -> ~2.00 credits" in err and "OK" in err


def test_non_wav_audio_is_budgeted_at_the_60s_maximum(tmp_path, isolated_budget):
    client, _ = make_client(tmp_path, stt_ok)
    client.transcribe(b"ID3 not really an mp3", "en-IN", filename="call.mp3")
    (row,) = read_ledger(isolated_budget.ledger)
    assert row["audio_seconds"] == 60.0 and row["units_estimated"] is True


def test_budget_refusal_stops_a_call_analysis_at_once(tmp_path, isolated_budget):
    set_rates(isolated_budget, stt_credits_per_audio_second=None)
    client, calls = make_client(tmp_path, stt_ok)
    with pytest.raises(BudgetExceeded):
        analyze_call(wav_bytes(75, fills=(1, 2, 3)), "en-IN", client, chunk_seconds=25)
    assert calls == []


def test_budget_refusal_skips_spoken_alert_without_trying_fallback_voice(tmp_path, isolated_budget):
    set_rates(isolated_budget, tts_credits_per_1k_chars=None)
    client, calls = make_client(tmp_path, lambda url, kw, n: FakeResp(content=b"audio"))
    res = analyze_transcripts([SCAMS["en"]], "en-IN", client=client)
    assert res.final.level == "high" and res.alert_audio is None and res.alert_text
    assert calls == [] and "Budget guard" in res.warnings[0]


def test_usage_report_and_calibration(tmp_path, isolated_budget, capsys):
    set_rates(isolated_budget, tts_credits_per_1k_chars=None)
    budget = Budget()
    budget.record("tts", 200, language="en-IN", model="timbre-v2.5", cache_hit=False)
    budget.record("stt", 30, language="en-IN", model="prisma-stt-v3", cache_hit=False)

    usage_report.main([])
    out = capsys.readouterr().out
    assert "estimated spent           3.0" in out and "Unmeasured rates: tts" in out

    usage_report.main(["--calibrate", "tts", "--drop", "0.5", "--write"])
    assert "tts_credits_per_1k_chars = 2.5" in capsys.readouterr().out
    assert json.loads(isolated_budget.rates.read_text(encoding="utf-8"))["tts_credits_per_1k_chars"] == 2.5
    assert budget.totals()[0] == pytest.approx(3.5)  # rate now applies to the logged 200 chars
