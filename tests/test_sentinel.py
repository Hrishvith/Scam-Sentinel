import io
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import make_demo_call  # noqa: E402
from alerts import alert_text, top_reasons  # noqa: E402
from audio_utils import add_noise, concat_wavs, ensure_wav, split_wav  # noqa: E402
from detector import detect, detect_rules  # noqa: E402
from gnani_client import GnaniClient, GnaniError, fix_wav_sizes, wav_duration_seconds  # noqa: E402
from pipeline import analyze_call, analyze_texts, analyze_transcripts  # noqa: E402


def wav_bytes(seconds: float, rate: int = 8000, fills: tuple[int, ...] = (1,)) -> bytes:
    """Silent-ish WAV. `fills` gives each equal slice a distinct sample value so chunks hash differently."""
    buf = io.BytesIO()
    per = int(rate * seconds) // len(fills)
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        for f in fills:
            w.writeframes(bytes([f, 0]) * per)
    return buf.getvalue()


# ---- detector -------------------------------------------------------------
SCAMS = {
    "en": "This is the CBI. There is an arrest warrant against you. Do not tell anyone. "
          "Install AnyDesk and tell me your OTP, then transfer money to a safe account.",
    "hi": "मैं सीबीआई से बोल रहा हूँ। आपके खिलाफ़ गिरफ्तारी वारंट है। किसी को मत बताना। "
          "एनीडेस्क ऐप डाउनलोड करें और अपना ओटीपी बताएं।",
    "kn": "ನಾನು ಸಿಬಿಐ ಇಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ. ನಿಮ್ಮ ವಿರುದ್ಧ ಅರೆಸ್ಟ್ ವಾರೆಂಟ್ ಇದೆ. ಯಾರಿಗೂ ಹೇಳಬೇಡಿ. "
          "ಈಗಲೇ ಒಟಿಪಿ ಹೇಳಿ ಮತ್ತು ಸುರಕ್ಷಿತ ಖಾತೆಗೆ ಹಣ ಕಳುಹಿಸಿ.",
}


@pytest.mark.parametrize("lang", SCAMS)
def test_scam_scripts_are_high_risk_in_every_language(lang):
    det = detect_rules(SCAMS[lang])
    assert det.level == "high", det.to_dict()
    assert {"authority", "threat", "credentials"} <= det.tactics.keys()


@pytest.mark.parametrize("text", [
    "Hi, are we still meeting for lunch tomorrow?",
    "Your parcel will be delivered tomorrow between two and five.",
    "The police station is near the bus stand, you can ask there.",
    "ನಾಳೆ ಮನೆಗೆ ಬರುತ್ತೇನೆ, ಅಮ್ಮನಿಗೆ ಹೇಳಿ.",
    "कल शाम को मिलते हैं, खाना साथ में खाएँगे।",
    "I was spinning the wheel at the fair.",  # 'pin' must not match inside 'spinning'
])
def test_normal_conversation_stays_low(text):
    assert detect_rules(text).level == "low"


def test_awareness_message_not_flagged_high():
    det = detect_rules("Bank notice: never share your OTP or PIN with anyone, including bank staff.")
    assert det.level != "high"
    assert any("awareness" in n for n in det.notes)


def test_pressure_alone_is_not_enough():
    assert detect_rules("This is the police. Please come to the station.").level == "low"


def test_word_boundary_for_short_keywords():
    assert "credentials" not in detect_rules("spinning pinned pins").tactics


def test_llm_never_lowers_and_failures_fall_back(monkeypatch):
    monkeypatch.setenv("EVON_BASE_URL", "http://127.0.0.1:9")  # nothing listens
    det = detect(SCAMS["en"])
    assert det.level == "high" and det.source == "rules"


# ---- cumulative timeline --------------------------------------------------
def test_risk_escalates_over_the_call():
    texts = ["Hello, this is the police.", "There is an arrest warrant against you.",
             "Do not tell anyone and tell me your OTP now."]
    chunks, final = analyze_texts(texts)
    scores = [c.score for c in chunks]
    assert scores == sorted(scores) and scores[0] < scores[-1]
    assert chunks[0].level == "low" and chunks[-1].level == "high"
    assert "threat" in chunks[1].new_tactics and "threat" not in chunks[2].new_tactics


# ---- alerts ---------------------------------------------------------------
@pytest.mark.parametrize("lang", ["kn-IN", "hi-IN", "en-IN"])
def test_high_alert_mentions_helpline_digits(lang):
    det = detect_rules(SCAMS[lang[:2]])
    assert "1 9 3 0" in alert_text(lang, det)
    assert top_reasons(lang, det)


# ---- audio ----------------------------------------------------------------
def test_split_wav_into_25s_chunks():
    parts = split_wav(wav_bytes(60), 25)
    assert [round(s) for s, _ in parts] == [0, 25, 50]
    for _, data in parts:
        with wave.open(io.BytesIO(data)) as w:
            assert w.getnframes() / w.getframerate() <= 25.01


def test_non_wav_is_returned_whole_and_ensure_wav_keeps_wav():
    assert split_wav(b"not-a-wav") == [(0.0, b"not-a-wav")]
    wav = wav_bytes(1)
    assert ensure_wav(wav) == wav


def test_concat_and_noise_preserve_format():
    joined = concat_wavs([wav_bytes(1), wav_bytes(1)], pause_seconds=0.5)
    noisy = add_noise(joined)
    with wave.open(io.BytesIO(noisy)) as w:
        assert w.getframerate() == 8000 and w.getnframes() == int(8000 * 2.0 + 2 * 4000)
    assert noisy != joined


# ---- end to end with a fake Gnani client ---------------------------------
class FakeResp:
    def __init__(self, status=200, json_body=None, content=b""):
        self.status_code, self._json, self.content = status, json_body, content
        self.text = str(json_body)

    def json(self):
        return self._json


def make_client(tmp_path, handler):
    c = GnaniClient("test-key", cache_dir=tmp_path, backoff=0)
    calls = []

    def fake_post(url, **kw):
        calls.append((url, kw))
        return handler(url, kw, len(calls))

    c._session.post = fake_post
    return c, calls


def test_identical_chunks_hit_the_cache_instead_of_spending_credits(tmp_path):
    def handler(url, kw, n):
        return FakeResp(json_body={"success": True, "transcript": "hello"})

    client, calls = make_client(tmp_path, handler)
    analyze_call(wav_bytes(50), "en-IN", client, chunk_seconds=25)  # two byte-identical 25 s chunks
    assert len(calls) == 1 and client.stats["cache_hits"] == 1


def test_analyze_call_transcribes_each_chunk_with_word_boosting_then_speaks(tmp_path):
    transcripts = iter(["this is the police", "arrest warrant do not tell anyone", "tell me your OTP anydesk"])

    def handler(url, kw, n):
        if url.endswith("/stt/v3"):
            return FakeResp(json_body={"success": True, "transcript": next(transcripts)})
        return FakeResp(content=b"mp3alert")

    client, calls = make_client(tmp_path, handler)
    # 75 s of audio, three distinct 25 s slices -> three chunks, three STT calls
    res = analyze_call(wav_bytes(75, fills=(1, 2, 3)), "en-IN", client, chunk_seconds=25)

    stt = [kw for url, kw in calls if url.endswith("/stt/v3")]
    assert len(stt) == 3
    assert stt[0]["data"]["format"] == "verbatim" and stt[0]["data"]["bias_score"] == "1.0"
    assert "OTP" in stt[0]["data"]["bias_list"]
    assert res.final.level == "high" and res.alert_audio == b"mp3alert"
    assert [round(c.start) for c in res.chunks] == [0, 25, 50]


def test_low_risk_call_does_not_spend_tts_credits(tmp_path):
    def handler(url, kw, n):
        return FakeResp(json_body={"success": True, "transcript": "see you at lunch tomorrow"})

    client, calls = make_client(tmp_path, handler)
    res = analyze_call(wav_bytes(5), "en-IN", client)
    assert res.final.level == "low" and res.alert_audio is None
    assert all(url.endswith("/stt/v3") for url, _ in calls)


def test_failed_chunk_is_skipped_with_warning_and_all_failed_raises(tmp_path):
    def handler(url, kw, n):
        return FakeResp(403, {"error": {"type": "FORBIDDEN", "message": "no credits"}})

    client, _ = make_client(tmp_path, handler)
    with pytest.raises(GnaniError, match="No speech"):
        analyze_call(wav_bytes(5), "en-IN", client)


def test_alert_falls_back_to_v25_then_to_text(tmp_path):
    def handler(url, kw, n):
        body = kw.get("json")
        if body and body["model"] == "timbre-v3.0":
            return FakeResp(400, {"error": {"type": "INVALID_REQUEST_ERROR", "message": "nope"}})
        return FakeResp(content=b"v25audio")

    client, calls = make_client(tmp_path, handler)
    res = analyze_transcripts([SCAMS["en"]], "en-IN", client=client)
    assert res.alert_audio == b"v25audio" and not res.warnings
    assert [kw["json"]["model"] for _, kw in calls] == ["timbre-v3.0", "timbre-v2.5"]


def test_demo_call_generator_builds_noisy_8khz_wav(tmp_path, monkeypatch):
    def handler(url, kw, n):
        assert kw["json"]["audio_config"] == {"container": "wav", "sample_rate": 8000, "num_channels": 1,
                                              "encoding": "linear_pcm", "sample_width": 2}
        return FakeResp(content=wav_bytes(1))

    client, _ = make_client(tmp_path, handler)
    monkeypatch.setattr(make_demo_call, "GnaniClient", lambda: client)
    out = make_demo_call.build("en", out_dir=str(tmp_path / "calls"))
    with wave.open(str(out)) as w:
        assert w.getframerate() == 8000 and w.getnframes() > 8000 * 5


def test_streaming_wav_sizes_from_timbre_are_repaired(tmp_path):
    good = wav_bytes(2, rate=16000)
    streamed = good[:4] + b"\xff\xff\xff\xff" + good[8:40] + b"\xff\xff\xff\xff" + good[44:]
    client, _ = make_client(tmp_path, lambda url, kw, n: FakeResp(content=streamed))
    out = client.synthesize("hello", container="wav", sample_rate=16000)
    assert out == good and wav_duration_seconds(out) == 2.0
    assert client.synthesize("hello", container="wav", sample_rate=16000) == good  # cache hit too
    assert fix_wav_sizes(b"ID3mp3data") == b"ID3mp3data"
