# 60-second demo storyboard

Goal: in one minute, show a scam call being caught **while it is happening**, in Kannada, with a spoken
warning, then prove it holds up on noisy lines. Aim at the *Demo Day Drop* award: one clear story, no
jargon, captions on (many people watch muted).

**Rules for the video:** say and caption **"simulated call"**; no real phone numbers, names, account
numbers or recordings; no API key on screen (keep the sidebar key field masked or crop it). Record the
screen at 1080p with system audio.

| Time | On screen | Audio / caption |
|---|---|---|
| 0:00-0:05 | Black card: "Every day, people in India lose savings to calls like this." then "This call is **simulated**." | Caption only |
| 0:05-0:10 | App, 🔴 Live tab. Source: *Simulated call*, `kn_scam_kyc_noisy`, "Play it aloud" on. Click **▶ Start** | Caption: "Scam Sentinel listens to the call, live, using Gnani Prisma" |
| 0:10-0:22 | The call plays. Kannada lines appear one by one in the transcript; risk bar starts to rise | Call audio. Caption, small: English gloss of each line ("I'm calling from your bank's KYC department...") |
| 0:22-0:28 | 🟠 at 12.2 s: "Your account will be blocked today". Orange warning box appears | **Spoken Kannada warning (Timbre)** plays over the call. Caption: "Mid-call warning, in the caller's language" |
| 0:28-0:36 | Caller asks for the OTP; 🔴 **Likely scam**, red box with reasons, helpline 1930, label "🧬 AI clone of Hrishvith C's voice" | **The high warning in YOUR cloned voice**: "ಹಲೋ, ಇದು ನಾನು. ಈ ಕರೆ ಮೋಸದ ಕರೆ…" Caption: "...and the final warning comes in a voice they trust: mine (AI clone of my own voice, with consent)" |
| 0:36-0:44 | Quick cut: same thing in Hindi or Hinglish (pick `hl_scam_arrest_noisy`), sped up 2x | Caption: "Kannada · Hindi · English · Hinglish" |
| 0:44-0:54 | `results/benchmark.png` full screen, zoom on the right panel | Caption: "Tested on noisy phone audio: 100% of scams flagged at 13 dB SNR, 88% at 5 dB. 20 simulated calls, 4 languages." |
| 0:54-0:60 | End card: "Scam Sentinel · built on Gnani Prisma + Timbre · #GnaniAI #GreatIndianAIInternshipChallenge". Small: "Decision aid. Cyber crime helpline 1930" | Caption only |

**Family voice:** tick "🧬 Speak the high-risk warning in Hrishvith C's voice" in the Live tab before
Start. Keep the on-screen clone label visible in the video (honesty rule: no misleading demos).

**Before recording:** restart the app (`run.ps1`), run the call once first so the warnings are cached
(they then play instantly), close other apps (memory), and do two takes. Each take costs about 0.15
credits.

**Optional second take (more personal):** you on camera reading the English scam lines into the mic,
the warning cutting in at "tell me the OTP". Use headphones so the warning is not re-recorded.
