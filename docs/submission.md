# Submission text (Great Indian AI Internship Challenge)

Copy each section into the form. Replace the `[brackets]`. Build details can be edited until the final
submission (deadline 11:59 PM IST, 10 Nov 2026).

## Project name
Scam Sentinel: a live voice scam-call shield for Indian languages

## Problem
Phone scams ("digital arrest", fake KYC, courier/customs, electricity disconnection) talk victims into
sharing an OTP, installing a remote-control app or transferring money, under time pressure and often in
the victim's own language. By the time a family member hears about it, the money is gone. Existing
protection (caller-ID spam labels, awareness messages) does not help **during** the call, and rarely in
Kannada or other regional languages.

## What it does
Scam Sentinel listens to a call in real time (Gnani Prisma realtime STT), tracks scam tactics as they
build up (authority, threat, urgency, secrecy, OTP/PIN, payment, remote access, lure), and the moment
the cumulative risk crosses *medium* and then *high* it speaks a calm warning in the listener's language
(Gnani Timbre TTS) with the 1930 helpline, optionally in a family member's own cloned voice. It understands Kannada, Hindi, English and code-mixed
Hinglish, including the way Prisma actually writes them ("ಒ ಟಿ ಪಿ", "any desk", "share maadbedi"), and it
does not panic at normal calls that mention an OTP (bank awareness messages, delivery hand-overs).

## Intended users
Elderly and first-time smartphone users, and their families; people who take calls mainly in Kannada,
Hindi or a regional language; and, as a next step, banks and telecom providers who could run it as an
opt-in, on-call safety layer.

## Gnani models / APIs used
- **Prisma speech-to-text, realtime WebSocket** (`wss://api.vachana.ai/stt/v3/stream`): live mode;
  `kn-IN`, `hi-IN`, `en-IN` (Hinglish); 8/16 kHz; word boosting (`x-bias-list`) on scam keywords.
- **Prisma speech-to-text, REST** (`/stt/v3`): uploaded calls and the benchmark; verbatim + `bias_list`.
- **Timbre text-to-speech** (`/api/v1/tts/inference`): spoken warnings with v3.0 voice Chetana (fallback
  v2.5), and the simulated test calls with v2.5 voices (Kavin, Saanvi, Deepak, Nalini, Pranav, Kaveri, Poorvi).
- **Voice cloning** (`/api/v1/tts/voice-clone/embeddings` + model `vachana-vc-v1`): optional "family
  voice" high-risk warning in an AI clone of a family member's own voice (the developer's own voice in the
  demo, with consent, labelled on screen). Verified in Kannada and English.
- Evon (open weights) is supported as an optional second opinion but was not used in the results.

## Results
- Live: on a simulated Kannada scam call, medium warning at 12.2 s and high warning at 19.7 s, before the
  OTP was given; on a live microphone test (English), high warning at 22.3 s while the "scammer" was speaking.
- Noise benchmark (20 simulated calls, 4 languages, 3 noise levels, full app path): scams flagged
  100% / 100% / 88% at 47 / 13 / 5 dB SNR; normal calls with a false alert 0% / 8% / 8%. Every miss is
  published with its transcript in `results/benchmark.md`.
- All test audio is simulated (Timbre voices); no real calls or personal data.

## Contribution
[Solo: "Built by [Your Name], solo: design, implementation, testing, benchmark and demo."]
[Team of two: "[Name 1]: ...; [Name 2]: ..."]

## Links
- Demo video post (LinkedIn): [link]
- Demo video post (X): [link]
- Code: [repo link]
