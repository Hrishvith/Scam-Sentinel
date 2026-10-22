"""Phase 5a: voice cloning, offline (fake Gnani client, synthetic tones; never a real voice)."""
import array
import json
import math

import pytest

import family_voice
from alerts import FAMILY_WARNINGS
from budget import cost, load_rates
from detector import Detection
from gnani_client import GnaniError
from live import AlertPlayer, LiveSession, is_own_warning
from test_phase2 import speechlike
from test_sentinel import FakeResp, make_client

EMB = {"embedding": "QUJD", "shape": [1, 768], "dtype": "torch.bfloat16"}


def vc_server(url, kw, n):
    if url.endswith("/voice-clone/embeddings"):
        return FakeResp(json_body={"success": True, "message": "Voice embeddings generated successfully",
                                   "data": {"voice_clone_embedding": EMB}})
    return FakeResp(content=b"RIFFcloned" if kw["json"].get("model") == "vachana-vc-v1" else b"RIFFstandard")


def test_enrolment_uploads_the_reference_once_and_caches_the_embedding(tmp_path):
    client, calls = make_client(tmp_path, vc_server)
    ref = speechlike([("s", 8.0)], rate=16000)
    assert client.voice_embedding(ref) == EMB
    assert client.voice_embedding(ref) == EMB                     # cached: no second upload
    (url, kw), = calls
    assert url.endswith("/api/v1/tts/voice-clone/embeddings") and "audio_file" in kw["files"]


@pytest.mark.parametrize("seconds", [3.0, 31.0])
def test_enrolment_rejects_references_outside_5_to_30_seconds(tmp_path, seconds):
    client, calls = make_client(tmp_path, vc_server)
    with pytest.raises(GnaniError, match="5-30"):
        client.voice_embedding(speechlike([("s", seconds)], rate=16000))
    assert calls == []


def test_cloned_speech_request_matches_the_docs(tmp_path):
    client, calls = make_client(tmp_path, vc_server)
    assert client.synthesize_cloned("Hi, it's me.", EMB) == b"RIFFcloned"
    body = calls[0][1]["json"]
    assert body["model"] == "vachana-vc-v1" and body["speaker_embedding"] == EMB
    assert "language" not in body and "voice" not in body          # the VC API takes neither
    assert body["audio_config"] == {"container": "wav", "sample_rate": 16000, "num_channels": 1,
                                    "encoding": "linear_pcm", "sample_width": 2}


def test_voice_clone_costs_are_estimated_until_measured():
    rates = load_rates()
    assert cost("tts_vc", 1000, rates) == pytest.approx(cost("tts", 1000, rates))
    assert cost("vc_embed", 20, rates) == pytest.approx(cost("stt", 20, rates))


def test_high_warning_uses_the_family_voice_and_medium_stays_standard(tmp_path):
    client, _ = make_client(tmp_path, vc_server)
    player = AlertPlayer(client, "kn-IN", family={"name": "Asha", **EMB})
    assert player.prepare() == [] and player.family_used
    assert player.audio == {"high": b"RIFFcloned", "medium": b"RIFFstandard"}


def test_family_voice_failure_falls_back_to_the_standard_warning(tmp_path):
    def server(url, kw, n):
        if kw["json"].get("model") == "vachana-vc-v1":
            return FakeResp(400, {"error": {"type": "INVALID_REQUEST_ERROR", "message": "bad embedding"}})
        return FakeResp(content=b"RIFFstandard")

    client, _ = make_client(tmp_path, server)
    player = AlertPlayer(client, "kn-IN", family={"name": "Asha", **EMB})
    warnings = player.prepare()
    assert player.audio["high"] == b"RIFFstandard" and not player.family_used
    assert "Family voice unavailable" in warnings[0]


@pytest.mark.parametrize("lang", ["kn-IN", "hi-IN", "en-IN"])
def test_echo_filter_knows_the_family_warning(lang):
    session = LiveSession("k", lang)
    heard = FAMILY_WARNINGS[lang.split("-")[0]].replace(".", "").replace(",", "").replace("।", "")
    assert is_own_warning(heard, session.own_warnings)


# ---- recording quality -----------------------------------------------------------------------
def samples(pattern, noise=0):
    import io, wave
    with wave.open(io.BytesIO(speechlike(pattern, rate=16000, noise=noise))) as w:
        return array.array("h", w.readframes(w.getnframes()))


def test_good_take_is_trimmed_and_accepted():
    trimmed, stats, problems = family_voice.check_reference(samples([("q", 2.0), ("s", 12.0), ("q", 3.0)]))
    assert problems == [] and 12 <= stats["seconds"] <= 13


@pytest.mark.parametrize("pattern,noise,problem", [
    ([("s", 3.0)], 0, "Too short"),
    ([("q", 1.0), ("s", 10.0), ("q", 1.0)], 3000, "background noise"),
])
def test_bad_takes_are_rejected_with_a_reason(pattern, noise, problem):
    _, _, problems = family_voice.check_reference(samples(pattern, noise=noise))
    assert any(problem in p for p in problems)


def test_quiet_take_is_rejected():
    quiet = array.array("h", (int(1000 * math.sin(2 * math.pi * 300 * i / 16000)) for i in range(16000 * 10)))
    _, _, problems = family_voice.check_reference(quiet)
    assert any("Too quiet" in p for p in problems)


def test_enrol_requires_explicit_consent(tmp_path, monkeypatch):
    monkeypatch.setattr(family_voice, "REFERENCE", tmp_path / "reference.wav")
    with pytest.raises(SystemExit, match="Only clone your own voice"):
        family_voice.main(["enroll", "--name", "Asha"])


def test_delete_removes_all_voice_data(tmp_path, monkeypatch):
    voice, cache = tmp_path / "voice", tmp_path / ".cache"
    voice.mkdir(), cache.mkdir()
    for p in (voice / "reference.wav", voice / "profile.json", cache / "vcemb-1.json", cache / "vctts-2.wav",
              cache / "tts-3.wav"):
        p.write_text("x")
    monkeypatch.setattr(family_voice, "VOICE_DIR", voice)
    monkeypatch.setattr(family_voice, "HERE", tmp_path)
    family_voice.main(["delete"])
    assert list(voice.iterdir()) == [] and [p.name for p in cache.iterdir()] == ["tts-3.wav"]
