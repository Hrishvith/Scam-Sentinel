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


@pytest.mark.parametrize("scam", DATA["scams"], ids=lambda s: s["id"])
def test_every_scam_is_written_in_every_language(scam):
    for lang in LANGS:
        assert scam["title"][lang] and len(scam["do"][lang]) == len(scam["do"]["en"]) and scam["lines"][lang]


@pytest.mark.parametrize("scam", DATA["scams"], ids=lambda s: s["id"])
@pytest.mark.parametrize("lang", LANGS)
def test_the_re_enacted_call_is_caught_and_named(scam, lang):
    lines = scam["lines"][lang]
    assert detect_rules(lines[0]).level == "low"                 # it starts innocent...
    det = detect_rules(" ".join(lines))
    assert det.level != "low"                                    # ...and is flagged by the end
    assert det.scam_type == NAMED.get(scam["id"], scam["id"])


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


def test_scams_page_is_served(tmp_path):
    async def body(http, fake, _):
        assert "Real scams" in await (await http.get("/scams")).text()
        assert (await (await http.get("/scams.json")).json(content_type=None))["scams"]
    run(body, tmp_path)
