# Noise benchmark: Scam Sentinel on noisy phone audio

**All calls are simulated**: scripts written for this project, spoken by Gnani Timbre (two voices,
8 kHz phone quality), with white noise added. No real calls, numbers or people.
20 calls (8 scam, 12 benign incl. bank awareness messages and delivery-OTP calls) x 3 noise levels, in Kannada, Hindi, English and Hinglish.

## Overall

| Noise | SNR | Speech-to-text char error | Scams caught (high) | False alarms (final) | False alarms (any point) | Median time to high alert |
|---|---|---|---|---|---|---|
| clean | 47 dB | 3.2% | 8/8 (100%) (8) | 0/12 (0%) | 0/12 (0%) | 16.9 s (78% into the call) |
| medium | 13 dB | 7.7% | 8/8 (100%) (8) | 0/12 (0%) | 1/12 (8%) | 16.9 s (77% into the call) |
| heavy | 5 dB | 17.7% | 7/8 (88%) (7) | 1/12 (8%) | 1/12 (8%) | 14.6 s (82% into the call) |

## By language

| Noise | Language | SNR | Char error | Scams caught | False alarms (any point) | Median time to high |
|---|---|---|---|---|---|---|
| clean | Kannada | 41 dB | 2.1% | 2/2 (100%) | 0/3 (0%) | 16.9 s |
| clean | Hindi | 48 dB | 1.0% | 2/2 (100%) | 0/3 (0%) | 15.9 s |
| clean | English | 46 dB | 0.4% | 2/2 (100%) | 0/3 (0%) | 16.3 s |
| clean | Hinglish | 47 dB | 9.3% | 2/2 (100%) | 0/3 (0%) | 15.9 s |
| medium | Kannada | 7 dB | 8.4% | 2/2 (100%) | 0/3 (0%) | 16.9 s |
| medium | Hindi | 14 dB | 3.5% | 2/2 (100%) | 0/3 (0%) | 15.8 s |
| medium | English | 12 dB | 5.5% | 2/2 (100%) | 1/3 (33%) | 16.2 s |
| medium | Hinglish | 13 dB | 13.1% | 2/2 (100%) | 0/3 (0%) | 15.9 s |
| heavy | Kannada | 0 dB | 25.3% | 1/2 (50%) | 1/3 (33%) | 24.9 s |
| heavy | Hindi | 6 dB | 8.2% | 2/2 (100%) | 0/3 (0%) | 15.8 s |
| heavy | English | 5 dB | 16.2% | 2/2 (100%) | 0/3 (0%) | 16.3 s |
| heavy | Hinglish | 5 dB | 21.1% | 2/2 (100%) | 0/3 (0%) | 14.5 s |

## Every miss and false alarm

- **FALSE ALARM** `en_benign_delivery` at medium noise (13 dB): final low (1.9), tactics: credentials,lure. Heard: "hello i am the delivery person from the courier company i am outside your building with your password oh great i will come down please tell me the delivery otp "
- **MISSED scam** `kn_scam_kyc` at heavy noise (0 dB): final low (2.5), tactics: threat. Heard: "ನಮಸ್ಕಾರ ಮೇಡಮ್ ನಾನು ನಿಮ್ಮ ಬ್ಯಾಂಕಿನ ಕೆ ಐಸಿ ವಿಭಾಗದಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ ಹೌದಾ ಏನು ವಿಷಯ ನಿಮ್ಮ ಕೆರೆನ್ಸಿ ಅವಧಿ ಮುಗಿದಿದೆ ಇಂದೇ ನಿಮ್ಮ ಖಾತೆ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ ಅಯ್ಯೋ ಈಗ ಏನು ಮಾಡ"
- **FALSE ALARM** `kn_awareness` at heavy noise (-2 dB): final high (6.5), tactics: authority,credentials. Heard: "ಇದು ನಿಮ್ಮ ಬ್ಯಾಂಕಿನಿಂದ ಒಂದು ಮುಖ್ಯ ಸೂಚನೆ ನಿಮ್ಮ ಒ ಟಿ ಪಿ ಪಿನ್ ಅಥವಾ ಪಾಸ್ವರ್ಡನ್ನು ಯಾರೊಂದಿಗೂ ಹಂಚಿಕೊಳ್ಳಬಹುದು ಬ್ಯಾಂಕ್ ಸಿಬಿಂದಿಯೊಂದಿಗೂ ಸಹ ಯಾರಾದರೂ ಕೇಳಿದರೆ ಸೈಬರ್ ಕ್ರೈಮ್ ಸಹಾಯ"

## Method

- Same path as the app: the call is split at pauses (one utterance per request), transcribed by Gnani
  Prisma (verbatim, word boosting), and the risk tracker replays it utterance by utterance.
- *Scams caught*: final risk medium or high. *False alarms (any point)*: a benign call that triggered
  an alert at any moment, which is what a user would actually hear in live mode.
- *Time to alert*: seconds of call audio until the utterance that crossed the threshold ended
  (Prisma's transcription latency, about 1-2 s live, comes on top).
- *SNR*: speech RMS (clean recording, speech windows only) over the added noise RMS.
- *Char error*: character-level edit distance against the script, spaces and punctuation ignored.

## Limits (read before quoting)

- Small: 8 scam and 12 benign calls. Percentages move in big steps; treat them as indicative.
- The detector was tuned on the clean and medium transcripts of these same scripts (Phase 2);
  only the heavy level is unseen. Real scam calls are longer and less scripted.
- Noise was added at a fixed level, not a fixed SNR: quieter voices (the Kannada ones) got a harsher
  test. Both heavy-noise failures are Kannada calls at about 0 dB, where speech recognition lost
  the OTP request in one and flipped "don't share" into "may share" in the other.
- White noise is a stand-in for phone-line noise; real calls add codecs, echo and background voices.
- Hinglish error rates are inflated by spelling: romanised Hindi has no standard spelling
  ("main" vs "mein"), so some "errors" are the same word written differently.
- In these scripts the OTP or payment request comes near the end, so the high alert also comes late;
  the medium alert is the earlier, gentler warning.
