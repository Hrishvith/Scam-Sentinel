"""Live mode against a local fake of the realtime STT server (no network, no credits)."""
import asyncio
import json
import wave

import pytest
from websockets.asyncio.server import serve

from budget import read_ledger
from detector import Detection
from gnani_client import BudgetExceeded
from live import FRAME_BYTES, LiveSession, RiskTracker, file_frames, read_wav_pcm, to_frames

SCRIPT = ["this is the cyber crime branch",
          "there is an arrest warrant against you",            # authority + threat -> medium
          "do not tell anyone, install anydesk and tell me the otp"]  # -> high


class FakeGnani:
    """Speaks the documented protocol: connected, then processing + transcript every N frames."""

    def __init__(self, script=SCRIPT, frames_per_segment=15, drop_first_after=None, error_after=None):
        self.script = list(script)
        self.fps, self.drop_first_after, self.error_after = frames_per_segment, drop_first_after, error_after
        self.connections = []
        self.segment = 0

    async def handler(self, ws):
        h = ws.request.headers
        conn = {"headers": {k.lower(): v for k, v in h.raw_items()}, "sizes": [], "nonzero": 0}
        self.connections.append(conn)
        await ws.send(json.dumps({"type": "connected", "message": "STT service ready", "timestamp": "t",
                                  "config": {"sample_rate": int(h["x-sample-rate"]), "chunk_size": 512}}))
        n = 0
        async for frame in ws:
            n += 1
            conn["sizes"].append(len(frame))
            conn["nonzero"] += any(frame)
            if self.error_after and n == self.error_after:
                await ws.send(json.dumps({"type": "error", "timestamp": "t", "message": "simulated hiccup"}))
            if self.drop_first_after and len(self.connections) == 1 and n == self.drop_first_after:
                await ws.close(1011, "simulated failure")
                return
            if n % self.fps == 0 and self.script:
                await ws.send(json.dumps({"type": "processing", "timestamp": "t"}))
                await ws.send(json.dumps({"type": "transcript", "timestamp": "t", "text": self.script.pop(0),
                                          "audio_duration_ms": 900, "segment_id": f"s{self.segment}",
                                          "segment_index": self.segment, "latency": 300}))
                self.segment += 1


def run_live(fake, pcm, rate=16000, pace_source=False, **kw):
    events, alerts = [], []

    async def main():
        async with serve(fake.handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            kw.setdefault("save_dir", None)
            session = LiveSession("test-key", "en-IN", rate, url=f"ws://127.0.0.1:{port}", pace=False,
                                  on_event=events.append, on_alert=lambda lvl, det: alerts.append(lvl),
                                  flush_seconds=0.2, drain_timeout=2.0, settle_seconds=0.1, **kw)
            return session, await session.run(file_frames(pcm, rate, pace=pace_source))

    session, summary = asyncio.run(main())
    return session, summary, events, alerts


def tone(frames: int) -> bytes:
    return bytes([1, 2]) * (FRAME_BYTES // 2) * frames


def test_protocol_headers_frames_alerts_and_ledger(isolated_budget):
    fake = FakeGnani()
    session, summary, events, alerts = run_live(fake, tone(60), pace_source=True)  # real cadence, ~1.9 s

    (conn,) = fake.connections
    h = conn["headers"]
    assert h["x-api-key-id"] == "test-key" and h["lang_code"] == "en-IN" and h["x-sample-rate"] == "16000"
    assert "OTP" in h["x-bias-list"].split(",") and h["x-bias-score"] == "1.0" and h["x-format"] == "verbatim"
    assert set(conn["sizes"]) == {FRAME_BYTES}

    assert alerts == ["medium", "high"]                       # each fires exactly once
    assert summary["level"] == "high" and summary["segments"] == 3
    tta = summary["time_to_alert"]
    assert 0 < tta["medium"] < tta["high"] <= summary["seconds_streamed"]
    assert [e.data["level"] for e in events if e.kind == "alert"] == ["medium", "high"]

    (row,) = [r for r in read_ledger(isolated_budget.ledger) if r["kind"] == "stt_stream"]
    assert row["audio_seconds"] == pytest.approx(summary["seconds_streamed"], abs=0.05)
    assert row["speech_seconds"] == 2.7 and row["sample_rate"] == 16000


def test_reconnects_before_the_session_cap_without_losing_audio(isolated_budget):
    fake = FakeGnani(script=[])
    session, summary, events, _ = run_live(fake, tone(50), reconnect_after=0.5)  # ~16 frames per session
    assert len(fake.connections) >= 3 and summary["connections"] == len(fake.connections)
    flush = int(0.2 / (FRAME_BYTES / 2 / 16000))
    assert sum(len(c["sizes"]) for c in fake.connections) == 50 + flush * len(fake.connections)
    assert len([r for r in read_ledger(isolated_budget.ledger) if r["kind"] == "stt_stream"]) == len(fake.connections)


def test_dropped_connection_is_reported_and_resumed(isolated_budget):
    fake = FakeGnani(drop_first_after=10)
    _, summary, events, alerts = run_live(fake, tone(80), pace_source=True)  # real cadence, ~2.6 s
    assert len(fake.connections) == 2 and summary["connections"] == 2
    assert any(e.kind == "error" and "Connection lost" in e.data["message"] for e in events)
    assert alerts == ["medium", "high"]  # detection carries on in the new session


def test_server_error_message_is_surfaced_and_session_continues(isolated_budget):
    fake = FakeGnani(error_after=3)
    _, summary, events, _ = run_live(fake, tone(60))
    assert [e.data["message"] for e in events if e.kind == "error"] == ["simulated hiccup"]
    assert summary["segments"] == 3 and len(fake.connections) == 1


def test_muted_session_sends_silence_while_the_warning_plays(isolated_budget):
    fake = FakeGnani(script=[])
    events = []

    async def main():
        async with serve(fake.handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            s = LiveSession("k", "en-IN", url=f"ws://127.0.0.1:{port}", pace=False, on_event=events.append,
                            flush_seconds=0.1, drain_timeout=1, settle_seconds=0.05)
            s.muted.set()
            await s.run(file_frames(tone(20), 16000, pace=False))

    asyncio.run(main())
    assert fake.connections[0]["nonzero"] == 0 and len(fake.connections[0]["sizes"]) > 20


def test_budget_guard_refuses_before_connecting(isolated_budget):
    data = json.loads(isolated_budget.rates.read_text(encoding="utf-8"))
    data["starting_credits"] = 10  # reserve 2; 300 s cap at 0.1/s = 30 credits -> refused
    isolated_budget.rates.write_text(json.dumps(data), encoding="utf-8")
    fake = FakeGnani()
    with pytest.raises(BudgetExceeded, match="reserve"):
        run_live(fake, tone(10))
    assert fake.connections == []


def test_max_seconds_caps_streaming(isolated_budget):
    fake = FakeGnani(script=[])
    _, summary, events, _ = run_live(fake, tone(200), max_seconds=1.0)
    assert summary["seconds_streamed"] < 1.0 + 0.2 + 0.1
    assert any("max-seconds" in e.data.get("message", "") for e in events if e.kind == "info")


def test_risk_tracker_jump_to_high_reports_once():
    t = RiskTracker()
    assert t.add("this is the cbi, arrest warrant, install anydesk and tell me the otp", 4.0) == "high"
    assert t.first_at == {"medium": 4.0, "high": 4.0}
    assert t.add("transfer money to a safe account", 6.0) is None


def test_frames_are_padded_and_wav_input_validated(tmp_path):
    frames = to_frames(b"\x01" * (FRAME_BYTES + 10))
    assert [len(f) for f in frames] == [FRAME_BYTES, FRAME_BYTES] and frames[1].endswith(b"\0")
    bad = tmp_path / "bad.wav"
    with wave.open(str(bad), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(22050)
        w.writeframes(b"\0\0" * 100)
    with pytest.raises(ValueError, match="22050"):
        read_wav_pcm(bad)


def test_alert_player_prepares_both_warnings_as_wav(tmp_path):
    from live import AlertPlayer
    from test_sentinel import FakeResp, make_client

    client, calls = make_client(tmp_path, lambda url, kw, n: FakeResp(content=b"RIFFwav"))
    player = AlertPlayer(client, "kn-IN")
    assert player.prepare() == [] and set(player.audio) == {"medium", "high"}
    assert {kw["json"]["audio_config"]["container"] for _, kw in calls} == {"wav"}
    assert all(kw["json"]["language"] == "kn-IN" for _, kw in calls)


@pytest.mark.parametrize("mute", [False, True])
def test_alert_player_mutes_only_when_asked(monkeypatch, mute):
    import sys, types
    from live import AlertPlayer

    seen = []
    session = LiveSession("k", "en-IN")
    fake_winsound = types.SimpleNamespace(SND_MEMORY=4, PlaySound=lambda audio, flags: seen.append(session.muted.is_set()))
    monkeypatch.setitem(sys.modules, "winsound", fake_winsound)
    monkeypatch.setattr("live.time.sleep", lambda s: None)
    player = AlertPlayer(client=None, lang="en-IN", session=session, mute_session=mute)
    player._play(b"wav")
    assert seen == [mute] and not session.muted.is_set()


def test_alerts_queue_without_blocking_the_caller(monkeypatch):
    import sys, threading, time, types
    from live import AlertPlayer

    gate, order = threading.Event(), []

    def play(audio, flags):
        order.append(audio)
        if audio == b"medium":
            gate.wait(2)       # the first warning is still playing

    monkeypatch.setitem(sys.modules, "winsound", types.SimpleNamespace(SND_MEMORY=4, PlaySound=play))
    player = AlertPlayer(client=None, lang="en-IN")
    player.audio = {"medium": b"medium", "high": b"high"}
    t0 = time.monotonic()
    player("medium", Detection(level="medium"))
    player("high", Detection(level="high"))
    assert time.monotonic() - t0 < 0.5          # the event loop is never held up
    gate.set()
    player.wait()
    assert order == [b"medium", b"high"]         # played in order, never over each other


def test_session_transcript_is_saved_locally(tmp_path, isolated_budget):
    fake = FakeGnani()
    _, summary, _, _ = run_live(fake, tone(60), save_dir=tmp_path / "sessions", source_name="kn_awareness_clean.wav")
    saved = json.loads(open(summary["saved_to"], encoding="utf-8").read())
    assert summary["saved_to"].endswith("_en-IN_kn_awareness_clean.json")
    assert [s["text"] for s in saved["segments"]] == SCRIPT and saved["segments"][1]["level"] == "medium"
    assert "audio" not in json.dumps(saved).replace("audio_ms", "")


HEARD_WARNING = ("warning this looks like a scam call hang up now do not share your otp pin or send any money "
                 "call the cyber crime helpline one nine three zero")   # real mic transcript, Phase 3


def test_own_warning_heard_by_the_mic_is_recognised():
    from live import is_own_warning
    session = LiveSession("k", "en-IN")
    assert is_own_warning(HEARD_WARNING, session.own_warnings)
    assert not is_own_warning("install anydesk and tell me the otp on your phone", session.own_warnings)
    assert not is_own_warning("hang up now", session.own_warnings)          # too short to judge
    kn = LiveSession("k", "kn-IN")
    assert is_own_warning("ಎಚ್ಚರ ಈ ಕರೆ ಅನುಮಾನಾಸ್ಪದವಾಗಿದೆ ಒಟಿಪಿ ಅಥವಾ ಹಣ ಕೊಡುವ ಮೊದಲು ಮನೆಯವರನ್ನು ಕೇಳಿ", kn.own_warnings)


def test_echo_of_the_medium_warning_does_not_escalate_to_high(isolated_budget):
    # Without the echo filter the warning's own words (OTP, money, cyber crime) would add up.
    fake = FakeGnani(script=["this is the cyber crime branch", "there is an arrest warrant against you",
                             "be careful this call is suspicious before sharing an otp or sending money ask your family"])
    _, summary, events, alerts = run_live(fake, tone(60), pace_source=True)
    assert alerts == ["medium"] and summary["level"] == "medium"
    assert [e.data["echo"] for e in events if e.kind == "transcript"] == [False, False, True]
