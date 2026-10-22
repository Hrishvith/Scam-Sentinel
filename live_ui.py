"""Streamlit "Live" tab: runs a LiveSession in a background thread and shows it as it happens.

The microphone (or the simulated call being played) is on the machine running Streamlit,
which is the laptop in a local demo. Events reach the page through a queue that a fragment
drains every half second.
"""
from __future__ import annotations

import asyncio
import queue
import threading
from pathlib import Path

import streamlit as st

from alerts import HELPLINE
from budget import Budget
from corpus import LANGS as CORPUS_LANGS
from family_voice import load_profile
from gnani_client import GnaniClient
from live import RATES, AlertPlayer, LiveEvent, LiveSession, file_frames, mic_frames, read_wav_pcm

HERE = Path(__file__).resolve().parent
SIMULATED = HERE / "demo_calls" / "corpus"
LEVEL_UI = {"low": ("🟢", "Low risk"), "medium": ("🟠", "Suspicious"), "high": ("🔴", "Likely scam")}


def file_language(path: Path, default: str) -> str:
    """A simulated call's own STT language (from its kn_/hi_/en_/hl_ prefix), else `default`."""
    return CORPUS_LANGS.get(path.stem.split("_")[0], {}).get("stt", default)


class LiveRunner:
    def __init__(self, api_key: str, lang: str, *, rate: int, max_seconds: float, speak: bool,
                 wav_path: Path | None = None, play: bool = False, headphones: bool = False,
                 family: dict | None = None):
        self.api_key, self.lang, self.rate, self.max_seconds = api_key, lang, rate, max_seconds
        self.speak, self.wav_path, self.play, self.headphones = speak, wav_path, play, headphones
        self.family = family
        self.events: queue.Queue[LiveEvent] = queue.Queue()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=lambda: asyncio.run(self._run()), daemon=True)

    def start(self) -> None:
        self.thread.start()

    async def _run(self) -> None:
        try:
            rate, pcm = read_wav_pcm(self.wav_path) if self.wav_path else (self.rate, None)
            session = LiveSession(self.api_key, self.lang, rate, on_event=self.events.put,
                                  max_seconds=self.max_seconds, stop=self.stop,
                                  source_name=self.wav_path.name if self.wav_path else "microphone")
            if self.speak:
                player = AlertPlayer(GnaniClient(self.api_key), self.lang, session,
                                     mute_session=pcm is None and not self.headphones, family=self.family)
                for warning in player.prepare():
                    self.events.put(LiveEvent("error", {"message": warning}))
                session.on_alert = player
            if pcm is not None:
                if self.play:
                    import numpy as np
                    import sounddevice as sd
                    sd.play(np.frombuffer(pcm, dtype=np.int16), rate)
                source = file_frames(pcm, rate)
            else:
                source = mic_frames(rate, self.stop)
            await session.run(source)
        except Exception as exc:  # surface everything on the page; never die silently in a thread
            self.events.put(LiveEvent("error", {"message": f"{type(exc).__name__}: {exc}"}))
            self.events.put(LiveEvent("done", {}))


def _drain(state: dict) -> None:
    runner: LiveRunner = state["runner"]
    while True:
        try:
            e = runner.events.get_nowait()
        except queue.Empty:
            return
        if e.kind == "transcript":
            state["lines"].append(e.data)
            state["level"], state["score"] = e.data["level"], e.data["score"]
        elif e.kind == "alert":
            state["alerts"].append(e.data)
        elif e.kind == "error":
            state["errors"].append(e.data["message"])
        elif e.kind == "connected":
            state["status"] = "listening"
        elif e.kind == "done":
            state["status"], state["summary"] = "finished", e.data


@st.fragment(run_every=0.5)
def _panel() -> None:
    state = st.session_state.get("live")
    if not state:
        return
    _drain(state)
    icon, title = LEVEL_UI[state["level"]]
    st.markdown(f"### {icon} {title} · score {state['score']:.1f}  \n*{state['status']}*")
    st.progress(min(1.0, state["score"] / 10))
    for a in state["alerts"]:
        box = st.error if a["level"] == "high" else st.warning
        label = f"  \n🧬 *Spoken in an {a['voice']}.*" if a.get("voice") else ""
        box(f"**{a['level'].upper()} at {a['at']:.1f} s** · {a['message']}  \n" + " · ".join(a["reasons"]) + label)
    for msg in state["errors"]:
        st.caption(f"⚠️ {msg}")
    for line in state["lines"][-12:]:
        if line.get("echo"):
            st.caption(f"{line['at']:5.1f}s · 🔈 our own warning, heard by the mic (ignored): {line['text']}")
        else:
            st.markdown(f"`{line['at']:5.1f}s` {LEVEL_UI[line['level']][0]} {line['text']}")
    if state["summary"]:
        s = state["summary"]
        if "seconds_streamed" in s:
            tta = ", ".join(f"{lvl} after {at:.1f} s" for lvl, at in s["time_to_alert"].items()) or "no alert"
            st.success(f"Done: {s['seconds_streamed']} s streamed, {s['segments']} segments. Time to alert: {tta}.")
            if s["level"] == "high":
                st.info(f"Hang up. Call **{HELPLINE}** (national cyber crime helpline).")


def live_tab(api_key: str, lang: str, speak: bool) -> None:
    st.caption("Streams audio to Gnani Prisma in real time and warns mid-call. Billed per second streamed.")
    files = sorted(SIMULATED.glob("*.wav")) if SIMULATED.is_dir() else []
    source = st.radio("Source", ["Microphone"] + (["Simulated call (file)"] if files else []), horizontal=True)
    wav_path, play, rate, headphones = None, False, 16000, False
    if source == "Microphone":
        rate = st.selectbox("Sample rate", RATES[:2], format_func=lambda r: f"{r} Hz" + (" (phone line)" if r == 8000 else ""))
        headphones = st.checkbox("I'm using headphones", value=False,
                                 help="On speakers the mic would hear the warning itself, so listening pauses "
                                      "while it plays. With headphones it keeps listening.")
    else:
        wav_path = st.selectbox("Simulated call", files, format_func=lambda p: p.stem)
        play = st.checkbox("Play it aloud while streaming", value=True)
        # Use the recording's own language: Kannada STT on an English file writes English in
        # Kannada script, which is a different (and misleading) test.
        lang = file_language(wav_path, lang)
        st.caption(f"Language for this file: **{lang}** (from its name; overrides the sidebar).")
    max_seconds = st.slider("Stop after (seconds)", 15, 300, 60, step=15)
    profile = load_profile() if speak else None
    family = None
    if profile and st.checkbox(f"🧬 Speak the high-risk warning in {profile['name']}'s voice",
                               help="An AI clone of their own voice, made with their consent (family_voice.py)."):
        family = profile
        st.caption(f"Labelled on screen as an AI clone of {profile['name']}'s voice.")

    est = Budget().check("stt_stream", max_seconds)
    st.caption(f"Up to {max_seconds} s streamed ≈ {est.credits or 0:.2f} credits at most.")

    state = st.session_state.get("live")
    running = bool(state) and state["runner"].thread.is_alive()
    c1, c2 = st.columns(2)
    if c1.button("▶ Start", type="primary", disabled=running or not api_key or not est.ok):
        runner = LiveRunner(api_key, lang, rate=rate, max_seconds=max_seconds, speak=speak,
                            wav_path=wav_path, play=play, headphones=headphones, family=family)
        st.session_state.live = {"runner": runner, "lines": [], "alerts": [], "errors": [], "level": "low",
                                 "score": 0.0, "status": "connecting…", "summary": None}
        runner.start()
    if c2.button("■ Stop", disabled=not running):
        state["runner"].stop.set()
    if not est.ok:
        st.error(est.reason)
    _panel()
