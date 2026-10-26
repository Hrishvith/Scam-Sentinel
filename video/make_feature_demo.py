"""Scam Sentinel full feature demo: every feature in order, about 2.5 minutes, 16:9 (and 9:16 with --vertical).

Same renderer, narrator (Gnani Timbre), music and mastering as make_promo3.py; real app shots from the user's screen
recordings (Desktop\\vid) and screens captured from the site. New narration lines are cached after the first run.

  python video/make_feature_demo.py --dry-run | --stills | (build) [--vertical]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_promo3 as m                                                         # noqa: E402
from make_promo3 import AMBER, GREEN, RED, Media, Scene                         # noqa: E402

OUT = m.DESKTOP / "Scam Sentinel - full feature demo 16x9.mp4"
OUT_VERT = m.DESKTOP / "Scam Sentinel - full feature demo 9x16.mp4"

NEW_VO = {
    "intro": "Meet Scam Sentinel: a website that protects you during scam calls. Nothing to install. It works in Kannada, "
             "Hindi and English, and one tap changes the language of the whole site.",
    "gnani": "It is built on Gnani AI. Prisma turns the caller's speech into text while they talk, and Timbre speaks the "
             "warnings out loud.",
    "setup": "To protect a phone, follow three simple steps and tap Turn on protection. Calls through the Scam Sentinel "
             "line are now checked as they happen.",
    "normal2": "Phones don't let apps hear their own normal calls. So for a normal call, put it on speaker and let a second "
               "device listen.",
    "after": "When the call ends, it asks if you shared an OTP or sent money, then shows the next steps, and copies the "
             "call details for your complaint.",
    "scams": "The Real scams page explains six common Indian scams with news sources. Listen to each one explained, or "
             "hear a re-enacted call.",
    "practice": "In Practice, spot the scam in an eight-question quiz, or type what a caller said and check it. Practice is "
                "free and works offline.",
    "sos2": "Cheated? The red SOS button shows four steps: call 1930, call your bank, tell your family, and register a "
            "complaint at cybercrime.gov.in.",
    "easy": "Big buttons, high contrast, a text-size control and a Back button on every page make it easy for elders.",
    "operator": "For telecom operators, a dashboard shows the caller's side of the call, the risk, and every warning.",
    "honest": "It is a prototype and a decision aid, not a guarantee. When in doubt, hang up and call 1930.",
}
m.VO.update(NEW_VO)

PRISMA = (0, 0.0, "GNANI PRISMA", "listening", GREEN, 0.70)
SCENES = [
    Scene("hook", "", [], [Media("drawn")], layout="hook", pad=0.5),
    Scene("problem", "THE PROBLEM", ["The scam works", "*DURING* the call"], [], layout="stats",
          chips=["Source: Ministry of Home Affairs", "Source: Parliament reply, 2024", "Source: Karnataka Home Minister"]),
    Scene("intro", "MEET SCAM SENTINEL", ["A shield for", "*every call*"],
          [Media("clip", "A", 0.2, 2.4), Media("clip", "B", 0.3, 2.8), Media("clip", "G", 0.2, 2.6), Media("clip", "E", 0.2, 2.0)],
          layout="reveal", chips=["Opens in any phone browser · nothing to install", "Kannada · Hindi · English",
                                  "One tap changes the whole site"], pad=0.3),
    Scene("gnani", "BUILT ON GNANI AI", ["Gnani *Prisma*", "+ Gnani *Timbre*"],
          [Media("clip", "E", 8.0, 11.5), Media("clip", "A", 12.5, 16.0)],
          chips=["Prisma: live speech-to-text", "Timbre: spoken warnings + explanations", "Kannada · Hindi · English · Hinglish"],
          label=(PRISMA, (1, 0.0, "GNANI TIMBRE", "speaking", AMBER, 0.62)), pad=0.3),
    Scene("setup", "01 · TURN ON PROTECTION", ["Three steps,", "*one green button*"],
          [Media("clip", "F", 2.5, 6.5), Media("clip", "F", 8.0, 12.0)],
          chips=["3 simple steps", "Calls on the Scam Sentinel line", "Normal calls: see speaker mode"], pad=0.3),
    Scene("live", "02 · LIVE PROTECTION", ["Spots scam tricks", "*as they build up*"],
          [Media("clip", "E", 8.0, 15.8), Media("clip", "E", 36.95, 37.85)],   # "Likely scam" before the line naming the cloned voice scrolls in
          chips=["Spoken warning: only YOU hear it", "Caller's voice turns down", "Names the scam type",
                 "Understands Hinglish and mixed speech", "AI voice clone option, made with consent"], label=PRISMA),
    Scene("alert", "02 · THE REAL WARNING", ["It warns you", "*DURING* the call"], [Media("clip", "E", *m.ALERT, mask=True)],
          chips=["pretending to be police", "threat of arrest", "pushing you to transfer money"], chip_color=RED,
          note="AI voice clone, made with consent", pad=0.1,
          label=(0, 0.75, "GNANI TIMBRE", "speaking the warning", AMBER, 0.09)),
    Scene("otp", "03 · OTP GUARD", ["Reading out an OTP?", "*STOP.*"], [Media("screen", "otp_stop")],
          chips=["OTP Guard ON by default", "Your words are never shown or saved", "Digits are only counted"], chip_color=RED,
          pad=0.4),
    Scene("normal2", "04 · NORMAL CALLS", ["Normal call?", "*Speaker mode*"], [Media("clip", "E", 2.4, 7.6)],
          chips=["Put the call on speaker", "A second phone or laptop listens"],
          note="WHY A SECOND DEVICE? Phones don't let apps hear their own calls (Android privacy permissions).", pad=0.3),
    Scene("after", "05 · AFTER THE CALL", ["Clear", "*next steps*"],
          [Media("clip", "E", 29.7, 32.6), Media("screen", "after_yes")],
          chips=["Did you share an OTP or send money?", "Call 1930 · bank · Sanchar Saathi", "Copy the call details"], pad=0.3),
    Scene("guardian", "06 · FAMILY GUARDIAN", ["Family gets a", "*live alarm*"],
          [Media("screen", "guardian_watch"), Media("screen", "guardian_alarm")],
          chips=["Alerts on OTP-guard stops", "What-to-do steps for the family"], pad=0.8),
    Scene("scams", "07 · REAL SCAMS IN INDIA", ["Real scams,", "*explained*"],
          [Media("clip", "A", 7.5, 10.0), Media("clip", "A", 12.5, 15.5), Media("clip", "A", 40.0, 43.0), Media("clip", "B", 26.0, 30.0)],
          chips=["6 scam types, with news sources", "Listen to it explained", "Re-enacted calls · AI voices"], pad=0.3),
    Scene("practice", "08 · PRACTICE", ["Spot", "*the scam*"],
          [Media("clip", "C", 13.0, 18.0), Media("screen", "check_call"), Media("screen", "quiz_score")],
          chips=["8-question quiz", "Check a call by typing", "Practice is free and offline"], pad=0.3),
    Scene("sos2", "09 · SOS + COMPLAINT", ["Cheated?", "*One tap.*"],
          [Media("clip", "D", 25.5, 27.5), Media("clip", "D", 30.0, 32.8), Media("screen", "portal")],
          chips=["Call 1930", "Register a complaint at cybercrime.gov.in", "Call your bank · tell your family"], chip_color=RED,
          note="The complaint link opens the official National Cyber Crime Reporting Portal.", pad=0.4),
    Scene("easy", "10 · EASY FOR ELDERS", ["Big, clear,", "*simple*"],
          [Media("screen", "textsize_1"), Media("screen", "textsize_2"), Media("clip", "D", 5.0, 8.0)],
          chips=["Big buttons, high contrast", "Text size: three steps", "Back button + bottom bar on every page"], pad=0.4),
    Scene("operator", "11 · FOR TELECOM OPERATORS", ["Operator", "*dashboard*"], [Media("screen", "operator")], layout="operator",
          chips=["Only the caller's side is transcribed", "Risk and every warning, live"], pad=0.4),
    Scene("proof", "IN OUR TESTS", [], [Media("screen", "operator")], layout="results", lead=1.0, pad=1.2),
    Scene("honest", "", [], [], layout="statement", pad=0.6,
          line=[("A prototype and a *decision aid*,", 72), ("not a guarantee.", 72), ("When in doubt: hang up and call *1930*.", 56)]),
    Scene("close", "", [], [], layout="close", pad=2.0),
]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--stills", action="store_true")
    ap.add_argument("--vertical", action="store_true")
    a = ap.parse_args()
    m.WORK.mkdir(parents=True, exist_ok=True)
    chars = sum(len(x) for x in NEW_VO.values())
    print(f"new narration: {chars} characters, {sum(len(x.split()) for x in NEW_VO.values())} words")
    if a.dry_run:
        return 0
    v = m.make_voice()
    tl = m.timeline(v, SCENES, "feature")
    print(f"  length {tl.total:.1f} s  " + "  ".join(f"{s.key} {t1 - t0:.1f}" for t0, t1, s in tl.spans))
    audio = m.master(tl, v, "feature")
    jobs = [(m.layout(1920, 1080), OUT)] + ([(m.layout(1080, 1920), OUT_VERT)] if a.vertical else [])
    for L, out in jobs:
        if a.stills:
            times = [2.0] + [t0 + (t1 - t0) * f for t0, t1, s in tl.spans[1:] for f in (0.3, 0.8)]
            m.render(L, tl, None, audio, times, tag="feature" + ("V" if L.portrait else ""))
            continue
        m.render(L, tl, out, audio); print("  done:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
