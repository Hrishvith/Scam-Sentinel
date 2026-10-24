"""Real scams page: every case is sourced, every re-enacted call is caught and named, the page is served."""
import json
import sys
from pathlib import Path

import pytest

from detector import detect_rules
from test_phone_relay import KEY, run

DATA = json.loads((Path(__file__).resolve().parents[1] / "web" / "scams.json").read_text(encoding="utf-8"))
LANGS = ("en", "kn", "hi")
NAMED = {"electricity": "remote_access"}          # page topics that are not a detector scam type of their own


def test_every_case_and_figure_links_to_its_source():
    for item in DATA["stats"] + [c for s in DATA["scams"] for c in s["cases"]]:
        assert item["source"].startswith("https://") and item["by"]
    assert all(s["cases"] for s in DATA["scams"])


def scammer_lines(scam, lang):
    """What the scammer says before Scam Sentinel's warning cuts in (the part the detector hears)."""
    scene = scam["scene"][lang]
    return [text for who, text in scene[:scene.index(["W", ""])] if who == "S"]


@pytest.mark.parametrize("scam", DATA["scams"], ids=lambda s: s["id"])
def test_every_scam_is_written_in_every_language(scam):
    for lang in LANGS:
        assert scam["title"][lang] and len(scam["do"][lang]) == len(scam["do"]["en"]) and scam["scene"][lang]


@pytest.mark.parametrize("scam", DATA["scams"], ids=lambda s: s["id"])
@pytest.mark.parametrize("lang", LANGS)
def test_the_re_enacted_call_is_caught_and_named_before_the_warning(scam, lang):
    lines = scammer_lines(scam, lang)
    assert detect_rules(lines[0]).level == "low"                 # it starts innocent...
    det = detect_rules(" ".join(lines))
    assert det.level != "low"                                    # ...and is flagged when the warning plays
    assert det.scam_type == NAMED.get(scam["id"], scam["id"])


@pytest.mark.parametrize("scam", DATA["scams"], ids=lambda s: s["id"])
@pytest.mark.parametrize("lang", LANGS)
def test_each_scene_is_a_conversation_that_ends_with_hanging_up(scam, lang):
    scene = scam["scene"][lang]
    assert [who for who, _ in scene].count("W") == 1 and scene[-1][0] == "V"     # warning, then they hang up
    assert {"S", "V"} <= {who for who, _ in scene} and all(text for who, text in scene if who != "W")


@pytest.mark.parametrize("scam", DATA["scams"], ids=lambda s: s["id"])
def test_every_scam_has_a_short_spoken_explanation(scam):
    for lang in LANGS:
        text = scam["spoken"][lang]
        assert 150 < len(text) < 400                              # ~20 s of speech, ~1 credit each
        assert "1930" not in text                                 # spaced, so TTS reads it digit by digit


def test_audio_is_made_once_and_only_with_yes(tmp_path, monkeypatch, capsys):
    import make_scam_audio as m
    monkeypatch.setattr(m, "OUT", tmp_path)
    calls = []
    monkeypatch.setattr(m, "speak_alert", lambda client, text, lang: (calls.append(lang) or b"ID3fake", None))
    monkeypatch.setattr(m, "GnaniClient", lambda: type("C", (), {"stats": {"tts_calls": len(calls), "cache_hits": 0}})())
    monkeypatch.setattr(sys, "argv", ["make_scam_audio.py", "--lang", "kn"])
    m.main()
    assert calls == [] and "credits" in capsys.readouterr().out    # dry run: nothing spent
    monkeypatch.setattr(sys, "argv", ["make_scam_audio.py", "--lang", "kn", "--yes"])
    m.main()
    assert calls == ["kn-IN"] * len(DATA["scams"])
    index = json.loads((tmp_path / "index.json").read_text())["files"]
    assert set(index) == {f"{s['id']}-kn" for s in DATA["scams"]}
    m.main()                                                      # files exist now: nothing more to make
    assert len(calls) == len(DATA["scams"])


def test_scene_audio_uses_two_voices_and_the_real_warning_and_costs_only_once(tmp_path, monkeypatch, capsys):
    import make_scene_audio as m
    from gnani_client import CacheMiss
    monkeypatch.setattr(m, "OUT", tmp_path)
    made = []

    class Fake:
        def __init__(self, offline=False):
            self.offline, self.stats = offline, {"tts_calls": 0, "cache_hits": 0}

        def synthesize(self, text, *, language, voice, model):
            if self.offline:
                raise CacheMiss("tts", len(text))
            made.append((voice, text))
            return b"ID3"
    monkeypatch.setattr(m, "GnaniClient", Fake)
    monkeypatch.setattr(sys, "argv", ["make_scene_audio.py", "--lang", "kn"])
    m.main()
    assert made == [] and "credits" in capsys.readouterr().out            # dry run spends nothing
    monkeypatch.setattr(sys, "argv", ["make_scene_audio.py", "--lang", "kn", "--yes"])
    m.main()
    voices = {v for v, _ in made}
    assert {"Kavin", "Saanvi"} <= voices                                  # scammer and the person called
    warnings = [t for v, t in made if v not in ("Kavin", "Saanvi")]
    assert len(warnings) == len(DATA["scams"]) and all(t.startswith("ಎಚ್ಚರ") for t in warnings)
    scenes = json.loads((tmp_path / "index.json").read_text())["scenes"]
    assert set(scenes) == {f"{s['id']}-kn" for s in DATA["scams"]}       # only complete scenes are listed
    before = len(made)
    m.main()                                                              # all saved: nothing more to make
    assert len(made) == before


def test_every_phone_page_loads_the_shared_help_bar_first(tmp_path):
    async def body(http, fake, _):
        js = await http.get("/common.js")
        assert js.content_type == "application/javascript" and "tel:1930" in await js.text()
        for path in ("/", "/practice", "/scams", "/guardian"):
            html = await (await http.get(path)).text()
            assert html.index('<script src="/common.js">') < html.index("<body")   # before the page's own script
    run(body, tmp_path)


def test_scams_page_is_served(tmp_path):
    async def body(http, fake, _):
        assert "Real scams" in await (await http.get("/scams")).text()
        assert (await (await http.get("/scams.json")).json(content_type=None))["scams"]
    run(body, tmp_path)
