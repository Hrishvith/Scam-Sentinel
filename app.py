"""Scam Sentinel: listen to a call, spot scam tactics as they build up, and speak a warning.

Run:  streamlit run app.py
"""
import os

import streamlit as st

from alerts import HELPLINE, SITE, lang_key, top_reasons
from budget import Budget, load_rates
from gnani_client import GnaniClient, GnaniError
from live_ui import live_tab
from pipeline import analyze_call, analyze_transcripts

st.set_page_config(page_title="Scam Sentinel", page_icon="🛡️", layout="centered")

LANGS = {"ಕನ್ನಡ (Kannada)": "kn-IN", "हिन्दी (Hindi)": "hi-IN", "English / Hinglish": "en-IN"}
LEVEL_UI = {"low": ("🟢", "Low risk", st.success), "medium": ("🟠", "Suspicious", st.warning),
            "high": ("🔴", "Likely scam", st.error)}
SAMPLE = ("Hello, this is Inspector Rao from the cyber crime branch. A parcel in your name was caught by customs. "
          "There is an arrest warrant against you. Do not disconnect this call and do not tell anyone. "
          "Install AnyDesk right now and tell me the OTP on your phone.")

st.title("🛡️ Scam Sentinel")
st.caption("Voice scam-call shield · Gnani Prisma (listens) + Timbre (speaks the warning)")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gnani API key", value=os.getenv("GNANI_API_KEY", ""), type="password")
    lang = LANGS[st.selectbox("Language of the call", list(LANGS))]
    speak = st.toggle("Speak the warning", value=True)
    st.caption("Use simulated calls or recordings you have consent for. Audio is sent to Gnani for transcription.")
    _rates = load_rates()
    _spent, _ = Budget().totals()
    st.caption(f"Credits (estimate): {_rates['starting_credits'] - _spent:.0f} left, "
               f"{_rates['starting_credits'] * _rates['reserve_fraction']:.0f} held in reserve. "
               "Run usage_report.py for details.")

tab_live, tab_audio, tab_text = st.tabs(["🔴 Live", "🎧 Analyze a call", "📝 Paste a script (no credits)"])

with tab_live:
    live_tab(api_key, lang, speak)

analysis, error = None, None
try:
    with tab_audio:
        audio = st.audio_input("Record")
        upload = st.file_uploader("…or upload a recording", type=["wav", "mp3", "ogg", "flac", "m4a"])
        if (audio or upload) and st.button("Analyze call", type="primary"):
            src = audio or upload
            client = GnaniClient(api_key)
            with st.spinner("Listening to the call…"):
                analysis = analyze_call(src.getvalue(), lang, client, filename=src.name or "call.wav",
                                        speak=speak)
            st.caption(f"API calls this session: {client.stats}")
    with tab_text:
        script = st.text_area("Call transcript", value=SAMPLE, height=140)
        if st.button("Analyze script"):
            client = GnaniClient(api_key) if (api_key and speak) else None
            analysis = analyze_transcripts([s.strip() for s in script.split("\n") if s.strip()] or [script],
                                           lang, client=client, speak=speak)
except GnaniError as exc:
    error = str(exc)

if error:
    st.error(error)

if analysis:
    for w in analysis.warnings:
        st.warning(w)
    final = analysis.final
    icon, title, banner = LEVEL_UI[final.level]
    banner(f"{icon} **{title}** · score {final.score:.1f}")

    st.subheader("Spoken warning")
    st.write(analysis.alert_text)
    if analysis.alert_audio:
        st.audio(analysis.alert_audio, format="audio/mp3", autoplay=True)
    if final.level == "high":
        st.info(f"Hang up. Call **{HELPLINE}** (national cyber crime helpline) or report at {SITE}.")

    st.subheader("How the risk built up")
    st.line_chart({"risk score (cumulative)": [c.score for c in analysis.chunks]})

    st.subheader("Tactics detected")
    reasons = top_reasons(lang, final, limit=8)
    for r in reasons or ["None so far"]:
        st.write(f"• {r}")
    for note in final.notes:
        st.caption(note)

    with st.expander("Transcript by segment"):
        for c in analysis.chunks:
            tags = " ".join(f"`{t}`" for t in c.new_tactics)
            st.markdown(f"**{c.start:.0f}s** · {c.level} · {c.text or '(no speech)'} {tags}")
    st.caption("This is a decision aid, not a guarantee. If in doubt, hang up and call the organisation yourself.")
