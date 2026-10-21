# Scam Sentinel 🛡️

A voice scam-call shield for the Great Indian AI Internship Challenge. It listens to a call, shows how scam tactics build up over time, and speaks a calm warning in the listener's language (Kannada, Hindi, English/Hinglish).

```
call audio -> split into 25 s chunks -> Prisma STT (verbatim + word boosting)
           -> tactic detector (cumulative risk per chunk; optional Evon second opinion)
           -> Timbre spoken warning (v3.0 "Chetana", falls back to v2.5)
```

## How Gnani is used

| Gnani piece | Role here |
|---|---|
| **Prisma** STT (`kn-IN`, `hi-IN`, `en-IN` for Hinglish) | Transcribes noisy phone audio. Runs in `verbatim` mode with **word boosting** (`bias_list`) on scam keywords like OTP, CBI, warrant, AnyDesk. |
| **Timbre** TTS | Speaks the warning. v3.0 voices speak all 10 languages; falls back to v2.5 if needed. Also generates the simulated demo call at 8 kHz. |
| **Evon** (optional) | Second opinion on the whole call via any OpenAI-compatible server. Never lowers the rule-based level. |

## Run

```bash
pip install -r requirements.txt
export GNANI_API_KEY=your-key        # from app.gnani.ai
streamlit run app.py
```

Tests (no API calls, no credits): `python -m pytest -q`

## Make a demo call (simulated)

```bash
python make_demo_call.py en     # or hi / kn  -> demo_calls/call_en.wav
```

Two Timbre voices play a scripted "digital arrest" scam at 8 kHz with line noise added. **Say "simulated" in your post.** Never use a real person's voice or a real scam call.

## Credits

Everything is cached in `.cache/` by content hash. Low-risk calls skip TTS entirely. The "paste a script" tab uses no credits. A 60 s call is about three STT calls.

## Limits to state honestly

- Rule-based tactics are tuned for scripted scams; real Prisma transcripts may spell words differently. Run a few real (consented or simulated) calls and add the spellings you see to `tactics.py`.
- Short keywords like "police" or "OTP" appear in normal speech too, so one tactic alone stays low risk and it takes combinations to reach high.
- This is a decision aid, not a guarantee. India's cyber crime helpline is **1930**; report at cybercrime.gov.in.
- Have a native speaker review the Kannada and Hindi warning text in `alerts.py`.
