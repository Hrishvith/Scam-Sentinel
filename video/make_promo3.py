"""Scam Sentinel promo + feature explainer (brief in Desktop\\link.txt, 25 Oct 2026): about 68 s, 16:9 and 9:16.

Visuals: real app screens (the user's screen recordings and screens captured from the real site in re-enacted states by
capture_screens.py) inside a phone frame, kinetic headlines, 2-5 feature chips per scene, a progress dot bar.
Audio, mastered: narration -16 LUFS integrated / -1.5 dBTP (high-pass 80 Hz, de-esser, light compression, loudnorm);
music about -28 LUFS, ducked 13 dB under the voice and raised only in the opening and the last 4 s; effects kept
10 dB below the voice; a limiter at -1 dBTP. Narration: Gnani Timbre (cached after the first run).

  python video/make_promo3.py --dry-run | --stills | (build)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_promo2 as base                                                     # noqa: E402
from make_promo2 import (AMBER, CLIP, CLIPS, DIM, FPS, GREEN, RED, SOFT, SR, WHITE, ClipReader, Layout, asset, chip,  # noqa: E402
                         ease, ffmpeg, font, header, incoming_call, lang_chips, phone, put_text, read_wav, run, sfx_alarm,
                         sfx_heart, sfx_ring, sfx_tick, sfx_whoosh, tag, trim, wrap)

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "video" / "screens"
WORK = ROOT / "video" / "build3"
base.WORK = ROOT / "video" / "build2"            # where make_promo2 keeps its word images and cached voice files
DESKTOP = Path(r"C:\Users\Welcome\Desktop")
OUTS = [DESKTOP / "Scam Sentinel - explainer 16x9.mp4", DESKTOP / "Scam Sentinel - explainer 9x16.mp4"]
TEMPO = 1.07
MUSIC = ROOT / "video" / "music" / "Inspired.mp3"
MUSIC_CREDIT = "Music: “Inspired” by Kevin MacLeod (incompetech.com) · CC BY 4.0"
# the user's other recordings (base.CLIP already has A-E)
CLIP.update({"F": "Record_2026-10-25-14-13-20_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
             "G": "Record_2026-10-25-15-55-54_40deb401b9ffe8e1df2f1cc5ba480b12.mp4"})
ALERT = (16.7, 20.7)          # clip E: the real red alarm and its spoken warning

SCAMMER = "We've arrested your son. Pay five lakh rupees now."
VO = {
    "problem": "None of it was true. Indians lost twenty-two thousand crore rupees to cyber fraud in 2024. And it happens during the call.",
    "reveal": "Meet Scam Sentinel. A website, nothing to install, in Kannada, Hindi and English.",
    "live": "Turn on protection and it spots scam tricks as they build up: fake police, threats, secrecy, OTP and money pressure. "
            "The shield goes safe, careful, scam, and warns you out loud.",
    "otp": "Start reading out an OTP? It says stop, and cuts your voice off the line.",
    "normal": "For a normal call, use speaker mode on a second device. Afterwards, it guides every next step.",
    "guardian": "Family can watch as guardians, and get a live alarm.",
    "learn": "Learn real Indian scams, hear them re-enacted, and practise spotting them with a quiz.",
    "sos": "Cheated? One tap shows exactly what to do.",
    "proof": "In our tests, twenty-four of twenty-four scam calls were caught, and none of thirty-six normal calls flagged.",
    "close": "Scam Sentinel. Hang up on fear, not on your family.",
}
SUBS = {"problem": "None of it was true. Indians lost ₹22,845 crore to cyber fraud in 2024. And it happens during the call.",
        "proof": "In our tests, 24 of 24 scam calls were caught, and none of 36 normal calls flagged."}


@dataclass
class Media:
    kind: str                    # screen | clip | drawn
    name: str = ""
    c0: float = 0.0
    c1: float = 0.0


@dataclass
class Scene:
    key: str                     # narration key ("hook" uses the scammer line)
    tag: str
    headline: list[str]
    media: list[Media]
    chips: list[str] = field(default_factory=list)
    chip_color: tuple = GREEN
    note: str = ""
    layout: str = "phone"        # phone | stats | reveal | laptop | close | hook
    pad: float = 0.25


SCENES = [
    Scene("hook", "", [], [Media("drawn")], layout="hook", pad=0.9),
    Scene("problem", "THE PROBLEM", ["The scam works", "*DURING* the call"], [], layout="stats",
          chips=["Source: Ministry of Home Affairs", "Source: Parliament reply, 2024", "Source: Karnataka Home Minister"]),
    Scene("reveal", "SCAM SENTINEL", ["A shield for", "*every call*"],
          [Media("clip", "B", 0.3, 2.8), Media("clip", "G", 0.2, 2.6), Media("clip", "E", 0.2, 2.6)], layout="reveal",
          chips=["Opens in any phone browser", "Add to home screen", "One tap changes the whole site", "Built on Gnani AI: Prisma + Timbre"]),
    Scene("live", "01 · LIVE PROTECTION", ["Spots scam tricks", "*as they build up*"],
          [Media("clip", "F", 0.5, 9.0), Media("clip", "E", 8.0, 15.8)],
          chips=["Spoken warning — only YOU hear it", "Caller's voice turns down", "Names the scam type",
                 "Understands Hinglish and mixed speech", "Optional family-member voice clone (made with consent)"]),
    Scene("alert", "01 · THE REAL WARNING", ["It warns you", "*DURING* the call"], [Media("clip", "E", *ALERT)],
          chips=["pretending to be police", "threat of arrest", "pushing you to transfer money"], chip_color=RED,
          note="Spoken in an AI clone of a family member's voice · made with consent", pad=0.1),
    Scene("otp", "02 · OTP GUARD", ["Reading out an OTP?", "*STOP.*"], [Media("screen", "otp_stop")],
          chips=["OTP Guard ON by default", "Your words are never shown or saved", "Digits are only counted"], chip_color=RED),
    Scene("normal", "03 · NORMAL CALLS + AFTER", ["Speaker mode,", "then *next steps*"],
          [Media("clip", "E", 3.6, 7.6), Media("clip", "E", 25.0, 31.0)],
          chips=["Speaker mode for normal calls", "Ready-made complaint text"],
          note="WHY A SECOND DEVICE? Phones don't let apps hear their own calls (Android privacy permissions). "
               "So today, Scam Sentinel listens from a second device on speaker."),
    Scene("guardian", "04 · FAMILY GUARDIAN", ["Family gets a", "*live alarm*"],
          [Media("screen", "guardian_watch"), Media("screen", "guardian_alarm")],
          chips=["Alerts on OTP-guard stops", "What-to-do steps for the family"]),
    Scene("learn", "05 · LEARN + PRACTISE", ["Real scams,", "*re-enacted*"],
          [Media("clip", "A", 37.0, 43.0), Media("clip", "B", 22.0, 30.0), Media("clip", "C", 13.0, 18.0)],
          chips=["6 real scam types", "8-question quiz", "Check a call by typing", "Practice is free and offline"]),
    # the complaint step opens the official portal (cropped above its banner, so no officials' photos are shown)
    Scene("sos", "06 · SOS + COMPLAINT", ["Cheated?", "*One tap.*"],
          [Media("clip", "D", 26.0, 27.3), Media("clip", "D", 30.0, 32.8), Media("screen", "portal")],
          chips=["Call 1930", "Register a complaint at cybercrime.gov.in", "Big buttons + text-size control"], chip_color=RED,
          note="The complaint link opens the official National Cyber Crime Reporting Portal.", pad=1.7),
    Scene("proof", "07 · OPERATOR VIEW + PROOF", ["Tested, and", "*it works*"], [Media("screen", "operator")], layout="laptop",
          chips=["Operator / telecom view", "Only the caller's side is transcribed"]),
    Scene("close", "", [], [], layout="close", pad=1.1),
]


# ---------------------------------------------------------------- audio
def loudnorm(src: Path, dst: Path, target: float, tp: float = -1.5, pre: str = "") -> None:
    """Loudness to `target` LUFS with ONE fixed gain, then a fast peak limiter for the few peaks above `tp`.
    (ffmpeg's loudnorm fell back to its "dynamic" mode here, and its gain-riding made the voice wobble.)"""
    chain = (pre + "," if pre else "") + "loudnorm=print_format=json"
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(src), "-af", chain, "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    gain = target - float(m["input_i"])
    print(f"    {dst.name}: {float(m['input_i']):.1f} LUFS, gain {gain:+.1f} dB, peaks to limit {float(m['input_tp']) + gain - tp:+.1f} dB")
    second = ((pre + ",") if pre else "") + f"volume={gain:.2f}dB,alimiter=limit={10 ** (tp / 20):.4f}:attack=5:release=100:asc=1:level=false"
    run(["-i", str(src), "-af", second, "-ar", str(SR), "-ac", "1", str(dst)])


def lufs(path: Path) -> float:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def write(path: Path, x: np.ndarray) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    return path


def make_voice() -> dict[str, np.ndarray]:
    from gnani_client import GnaniClient
    from pipeline import speak_alert
    client = GnaniClient(); out = {}
    for key, text in VO.items():
        audio, warn = speak_alert(client, text, "en-IN")
        if audio is None:
            raise RuntimeError(warn)
        p = WORK / f"vo_{key}.mp3"; p.write_bytes(audio)
        f = WORK / f"vo_{key}_t.wav"
        run(["-i", str(p), "-af", f"aresample={SR},rubberband=tempo={TEMPO}:pitchq=quality:window=standard", "-ac", "1", "-ar", str(SR), str(f)])
        out[key] = trim(read_wav(f))
    raw = client.synthesize(SCAMMER, language="en-IN", voice="Pranav", model="timbre-v2.5")
    p = WORK / "scammer.mp3"; p.write_bytes(raw)
    ph = WORK / "scammer_phone.wav"           # phone-call sound, still easy to understand
    run(["-i", str(p), "-af", "highpass=f=300,lowpass=f=3400,acompressor=threshold=-20dB:ratio=3", "-ac", "1", "-ar", str(SR), str(ph)])
    out["hook"] = trim(read_wav(ph))
    al = WORK / "alert.wav"
    run(["-ss", str(ALERT[0]), "-t", str(ALERT[1] - ALERT[0]), "-i", str(CLIPS / CLIP["E"]), "-vn",
         "-af", "afade=t=out:st=%.2f:d=0.25" % (ALERT[1] - ALERT[0] - 0.25), "-ac", "1", "-ar", str(SR), str(al)])
    out["alert"] = read_wav(al)
    print(f"  Gnani: {client.stats['tts_calls']} new, {client.stats['cache_hits']} from cache")
    return out


@dataclass
class Timeline:
    spans: list[tuple[float, float, Scene]]
    voice_at: dict[str, float]
    subs: list[tuple[float, float, str]]
    sounds: list[tuple[float, str]]
    total: float


def split_sub(t0, t1, text):
    parts = [p.strip() for p in re.split(r"(?<=[.!?:])\s+", text) if p.strip()]
    n = sum(len(p) for p in parts); out, t = [], t0
    for p in parts:
        d = (t1 - t0) * len(p) / n; out.append((t, t + d, p)); t += d
    return out


def timeline(v: dict[str, np.ndarray]) -> Timeline:
    spans, voice_at, subs, sounds = [], {}, [], []
    t = 0.0
    for s in SCENES:
        lead = 1.45 if s.key == "hook" else (0.15 if s.key == "reveal" else 0.0)
        d = lead + len(v[s.key]) / SR + s.pad
        spans.append((t, t + d, s)); voice_at[s.key] = t + lead
        text = ("“" + SCAMMER + "”" if s.key == "hook" else
                "“Hi, it's me. This call is a scam. Please hang up right now.”" if s.key == "alert" else SUBS.get(s.key, VO[s.key]))
        subs += split_sub(t + lead, t + lead + len(v[s.key]) / SR, text)
        if s.key == "hook":
            sounds += [(0.0, "ring")] + [(lead - 0.1 + i * 0.95, "heart") for i in range(4)]
        else:
            sounds.append((t - 0.08, "whoosh"))
        if s.key == "alert":
            sounds.append((t - 0.05, "alarm"))
        t += d
    return Timeline(spans, voice_at, subs, sounds, t)


def chip_time(s: Scene, i: int, d: float) -> float:
    return d * (0.18 + 0.62 * i / max(1, len(s.chips)))


def master(tl: Timeline, v: dict[str, np.ndarray]) -> Path:
    n = int((tl.total + 0.3) * SR)
    voice = np.zeros(n, np.float32)
    for key, at in tl.voice_at.items():
        s = int(at * SR); x = v[key][: n - s]; voice[s:s + len(x)] += x
    voice *= 0.5 / max(1e-6, np.abs(voice).max())        # -6 dBFS headroom, so nothing clips before mastering
    vraw = write(WORK / "bus_voice_raw.wav", voice)
    vbus = WORK / "bus_voice.wav"
    loudnorm(vraw, vbus, -16.0, -1.0, "highpass=f=80,deesser=i=0.4,acompressor=threshold=-21dB:ratio=2.5:attack=8:release=120:makeup=2")
    voice = read_wav(vbus)[:n]; voice = np.pad(voice, (0, n - len(voice)))
    active = np.convolve((np.abs(voice) > 0.02).astype(np.float32), np.ones(int(0.25 * SR)), "same") > 0
    duck = np.where(active, 10 ** (-13 / 20), 1.0)
    duck = np.convolve(duck, np.ones(int(0.12 * SR)) / int(0.12 * SR), "same")
    lift = np.ones(n)
    first, last = int(tl.spans[0][1] * SR), int((tl.total - 4.0) * SR)
    lift[last:] = 10 ** (4 / 20)
    # "Inspired" by Kevin MacLeod (incompetech.com), CC BY 4.0. Starts after the hook; placed so the track's own
    # ending (it resolves and fades at about 4:32-4:40) lands on the end of the video.
    start = tl.spans[0][1]
    length = tl.total + 0.3 - start
    offset = max(0.0, 280.0 - length)
    mraw = WORK / "bus_music_raw.wav"
    run(["-ss", f"{offset:.2f}", "-t", f"{length:.2f}", "-i", str(MUSIC), "-af", "afade=t=in:st=0:d=1.2",
         "-ac", "1", "-ar", str(SR), str(mraw)])
    placed = np.zeros(n, np.float32); m = read_wav(mraw); m *= 0.5 / max(1e-6, np.abs(m).max()); s0 = int(start * SR)
    placed[s0:s0 + len(m)] = m[: n - s0]
    mpl = write(WORK / "bus_music_placed.wav", placed)
    mbus = WORK / "bus_music.wav"; loudnorm(mpl, mbus, -28.0, -6.0)
    music = read_wav(mbus)[:n]; music = np.pad(music, (0, n - len(music)))
    music *= duck * lift
    fx = {"ring": sfx_ring(), "heart": sfx_heart(), "whoosh": sfx_whoosh(), "tick": sfx_tick(), "alarm": sfx_alarm()}
    sfx = np.zeros(n, np.float32)
    for at, key in tl.sounds:
        s = max(0, int(at * SR)); x = fx[key][: n - s]; sfx[s:s + len(x)] += x
    vpeak = np.percentile(np.abs(voice[active]), 99) if active.any() else 0.5
    sfx *= (vpeak * 10 ** (-10 / 20)) / max(1e-6, np.abs(sfx).max())          # 10 dB under the voice
    sfx = np.where(active, sfx * 0.7, sfx)                                       # and a little lower while it speaks
    mix = write(WORK / "mix_raw.wav", voice + music + sfx)
    final = WORK / "mix.wav"
    run(["-i", str(mix), "-af", "alimiter=limit=0.89:level=false", "-ar", str(SR), "-ac", "1", str(final)])
    print(f"  loudness: voice {lufs(vbus):.1f} LUFS, music {lufs(mbus):.1f} LUFS (before ducking), mix {lufs(final):.1f} LUFS")
    return final


# ---------------------------------------------------------------- pictures
_SCR: dict = {}


def screen_img(name: str, size: tuple[int, int]) -> Image.Image:
    key = (name, size)
    if key not in _SCR:
        im = Image.open(SCREENS / f"{name}.png").convert("RGB")
        w, h = size; r = max(w / im.width, h / im.height)
        im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
        _SCR[key] = im.crop((0, 0, w, h))
    return _SCR[key]


def dots(img, L, i, n):
    d = ImageDraw.Draw(img, "RGBA"); r = 7; gap = 26
    x0 = (L.W - (n - 1) * gap) // 2; y = L.H - 26
    for k in range(n):
        x = x0 + k * gap
        if k == i:
            d.rounded_rectangle((x - 16, y - r, x + 16, y + r), radius=r, fill=AMBER + (255,))
        else:
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 120 if k < i else 50))


def subtitle(img, L, text, column):
    if not text:
        return
    d = ImageDraw.Draw(img); f = font(34 if L.portrait else 31, "sb")
    left, width = (L.tx, L.tw) if (column and not L.portrait) else (80, L.W - 160)
    lines = wrap(d, text, f, width)[:2]; lh = 46
    y = (L.H - 150 - lh * len(lines)) if L.portrait else (L.H - 74 - lh * len(lines))
    for k, line in enumerate(lines):
        tw = int(d.textlength(line, font=f)); x = left + (width - tw) // 2
        layer = Image.new("RGBA", (tw + 32, 44), (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
        dl.rounded_rectangle((0, 0, tw + 31, 43), radius=10, fill=(0, 0, 0, 165)); dl.text((16, 1), line, font=f, fill=WHITE)
        img.alpha_composite(layer, (x - 16, y + k * lh))


def chips_block(img, L, s: Scene, lt, d, y):
    fsize = 26 if L.portrait else 27
    x = L.tx; row_h = fsize + 40
    for i, label in enumerate(s.chips):
        w = ImageDraw.Draw(img).textlength(label, font=font(fsize, "sb")) + 44
        if x + w > L.tx + L.tw:
            x = L.tx; y += row_h
        chip(img, x, y, label, s.chip_color, t=lt - chip_time(s, i, d), size=fsize)
        x += w + 14
    return y + row_h


def kinetic(img, L, lines, lt, size, y):
    for i, line in enumerate(lines):
        k = ease((lt - 0.05 - i * 0.12) / 0.35)
        if k > 0:
            put_text(img, (L.tx, y + (1 - k) * 30), line, size, alpha=k)
        y += int(size * 1.16)
    return y


def media_frame(L, s: Scene, lt, d, readers, size):
    if not s.media:
        return None, 0
    n = len(s.media); idx = min(n - 1, int(lt / (d / n))); m = s.media[idx]
    local = lt - idx * d / n
    if m.kind == "screen":
        return screen_img(m.name, size), local
    if m.kind == "clip":
        r = readers.get((id(s), idx))
        if r is None:
            for k in list(readers):
                readers.pop(k).close()
            r = readers[(id(s), idx)] = ClipReader(m.name, m.c0, m.c1, size)
        speed = max(1.0, (m.c1 - m.c0) / (d / n))
        return r.get(int(local * FPS * speed)), local
    return None, local


def laptop(img, L, shot, k):
    """The operator dashboard in a simple laptop frame."""
    if L.portrait:
        w = 940; x = (L.W - w) // 2; y = 780
    else:
        w = 760; x = 90; y = 210
    h = int(w * shot.height / shot.width)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x - 18, y - 18, x + w + 18, y + h + 18), radius=22, fill=(16, 20, 22, 255), outline=(96, 116, 112, 255), width=3)
    d.polygon(((x - 70, y + h + 18), (x + w + 70, y + h + 18), (x + w + 40, y + h + 44), (x - 40, y + h + 44)), fill=(70, 84, 82, 255))
    im = shot.resize((w, h), Image.LANCZOS)
    s = 1 + 0.04 * k
    im = im.resize((int(w * s), int(h * s))).crop((int(w * (s - 1) / 2), 0, int(w * (s - 1) / 2) + w, h))
    img.paste(im, (x, y))


def draw(L: Layout, tl: Timeline, t: float, readers: dict) -> Image.Image:
    span = next((sp for sp in tl.spans if sp[0] <= t < sp[1]), tl.spans[-1])
    t0, t1, s = span; lt, d = t - t0, t1 - t0
    i = tl.spans.index(span)
    if s.layout == "hook":
        img = Image.new("RGBA", (L.W, L.H), (0, 0, 0, 255))
        talk = (tl.voice_at["hook"], tl.voice_at["hook"] + (d - 1.45 - s.pad))
        talking = talk[0] <= t <= talk[1]
        import random
        shake = (random.Random(int(t * 30)).randint(-5, 5), random.Random(int(t * 31)).randint(-5, 5)) if talking else (0, 0)
        beat = max(0.0, math.sin(t * 7.4)) ** 6 if t > talk[0] - 0.2 else 0
        img.alpha_composite(Image.new("RGBA", (L.W, L.H), (120, 10, 10, int(70 * beat))))
        phone(img, L, incoming_call(L, t, talk), zoom=1.0 + 0.06 * ease(lt / d), shake=shake)
        if t > talk[0] + 0.6:
            k = ease((t - talk[0] - 0.6) / 0.4)
            if L.portrait:
                put_text(img, (0, 130), "A real kind of call.", 66, alpha=k, center=True)
                put_text(img, (0, 220), "*Re-enacted.*", 66, alpha=k, center=True)
                put_text(img, (0, 320), "Prototype · re-enacted calls", 30, "sb", SOFT, k, True)
            else:
                put_text(img, (L.tx, 400), "A real kind of call.", 76, alpha=k)
                put_text(img, (L.tx, 500), "*Re-enacted.*", 76, alpha=k)
                put_text(img, (L.tx, 610), "Prototype · re-enacted calls", 32, "sb", SOFT, k)
        if t > t1 - 0.1:
            return Image.new("RGB", (L.W, L.H), (0, 0, 0))
    else:
        img = L.bg.convert("RGBA"); header(img, L)
        frame, local = media_frame(L, s, lt, d, readers, (L.screen[2] - L.screen[0], L.screen[3] - L.screen[1]))
        size = 84 if not L.portrait else 74
        if s.layout == "phone":
            phone(img, L, frame, zoom=1.0 + 0.035 * min(1, local / 2.5))
            tag(img, L, s.tag)
            y = kinetic(img, L, s.headline, lt, size, L.ty + 66)
            y = chips_block(img, L, s, lt, d, y + 18)
            if s.note:
                dn = ImageDraw.Draw(img, "RGBA"); fn = font(28 if L.portrait else 27, "sb")
                lines = wrap(dn, s.note, fn, L.tw - 40)
                box = Image.new("RGBA", (L.tw, 24 + 40 * len(lines)), (0, 0, 0, 0)); db = ImageDraw.Draw(box)
                db.rounded_rectangle((0, 0, L.tw - 1, box.height - 1), radius=16, fill=AMBER + (34,), outline=AMBER + (255,), width=2)
                for j, line in enumerate(lines):
                    db.text((20, 12 + 40 * j), line, font=fn, fill=WHITE if j or not line.startswith("WHY") else AMBER)
                k = ease((lt - 0.4) / 0.4)
                box.putalpha(box.getchannel("A").point(lambda a: int(a * k)))
                img.alpha_composite(box, (L.tx, int(y + 10)))
            if s.key == "alert":                                      # the red scam moment
                k = 1 - ease(lt / 0.6)
                if k > 0:
                    img.alpha_composite(Image.new("RGBA", (L.W, L.H), RED + (int(120 * k),)))
        elif s.layout == "stats":
            c = L.W // 2
            top = 230 if not L.portrait else 260
            put_text(img, (0, top - 120), "None of it was *true.*", 70 if not L.portrait else 66, alpha=ease(lt / 0.4), center=True)
            stats = [("₹", 22845, " crore", "lost to cyber fraud, 2024", 0), ("₹", 1935, " crore", "lost to ‘digital arrest’", 1),
                     ("", 641, " cases · ₹109 crore", "‘digital arrest’ in Karnataka", 2)]
            for pre, val, unit, label, j in stats:
                st = d * (0.12 + 0.22 * j)
                if lt < st:
                    continue
                k = ease((lt - st) / 1.0)
                txt = f"{pre}{int(val * k):,}{unit}"
                if L.portrait:
                    y = top + 40 + j * 330
                    put_text(img, (0, y), txt, 88, color=AMBER, alpha=min(1, (lt - st) / 0.3), center=True)
                    put_text(img, (0, y + 110), label, 38, "sb", WHITE, min(1, (lt - st) / 0.3), True)
                    chip(img, c - 260, y + 170, s.chips[j], GREEN, t=lt - st - 0.3, size=24)
                else:
                    x = 120 + j * 580; y = top + 70
                    put_text(img, (x, y), txt, 70 if j < 2 else 56, color=AMBER, alpha=min(1, (lt - st) / 0.3))
                    put_text(img, (x, y + 100), label, 34, "sb", WHITE, min(1, (lt - st) / 0.3))
                    chip(img, x, y + 160, s.chips[j], GREEN, t=lt - st - 0.3, size=24)
            if lt > d * 0.7:
                k = ease((lt - d * 0.7) / 0.4)
                put_text(img, (0, (L.H * 0.7) if not L.portrait else 1420), "The scam works *DURING* the call.",
                         62 if not L.portrait else 54, alpha=k, center=True)
        elif s.layout == "reveal":
            if lt < 1.4:                                               # the shield glows first
                k = ease(lt / 0.6); sz = 240 if not L.portrait else 300
                glow = Image.new("RGBA", (sz + 220, sz + 220), (0, 0, 0, 0))
                ImageDraw.Draw(glow).ellipse((50, 50, sz + 170, sz + 170), fill=GREEN + (int(160 * k),))
                glow = glow.filter(ImageFilter.GaussianBlur(44))
                ly = (L.H - sz) // 2 - 80
                img.alpha_composite(glow, ((L.W - glow.width) // 2, ly - 110))
                logo = asset("logo", sz).copy(); logo.putalpha(logo.getchannel("A").point(lambda a: int(a * k)))
                img.alpha_composite(logo, ((L.W - sz) // 2, ly))
                put_text(img, (0, ly + sz + 30), "Scam Sentinel", 110 if not L.portrait else 100, alpha=ease((lt - 0.4) / 0.4), center=True)
            else:
                lt2 = lt - 1.4; d2 = d - 1.4
                frame, local = media_frame(L, s, lt2, d2, readers, (L.screen[2] - L.screen[0], L.screen[3] - L.screen[1]))
                phone(img, L, frame, zoom=1.0 + 0.03 * min(1, local / 2))
                tag(img, L, s.tag)
                y = kinetic(img, L, s.headline, lt2, size, L.ty + 66)
                lang_chips(img, L.tx, y + 10, 30 if L.portrait else 34); y += 76 if L.portrait else 84
                chips_block(img, L, s, lt2, d2, y + 16)
        elif s.layout == "laptop":
            split = d * 0.55
            if lt < split:
                laptop(img, L, Image.open(SCREENS / "operator.png").convert("RGB"), lt / split)
                tag(img, L, s.tag)
                y = kinetic(img, L, ["Operator /", "*telecom view*"], lt, size, L.ty + 66)
                chips_block(img, L, s, lt, d, y + 18)
            else:
                k = ease((lt - split) / 0.4)
                cards = [("24 / 24", "test scam calls caught"), ("0 / 36", "normal calls flagged"), ("4", "languages incl. Hinglish")]
                cw, ch = (500, 260) if not L.portrait else (820, 230)
                for j, (big, small) in enumerate(cards):
                    kk = ease((lt - split - j * 0.25) / 0.3)
                    if kk <= 0:
                        continue
                    x = ((L.W - 3 * cw - 80) // 2 + j * (cw + 40)) if not L.portrait else (L.W - cw) // 2
                    y = int(L.H * 0.3) if not L.portrait else 420 + j * (ch + 40)
                    layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
                    dl.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=26, fill=(255, 255, 255, 20), outline=GREEN, width=3)
                    fb = font(96, "b"); tw = dl.textlength(big, font=fb); dl.text(((cw - tw) / 2, 30), big, font=fb, fill=AMBER)
                    fs = font(34, "sb"); tw = dl.textlength(small, font=fs); dl.text(((cw - tw) / 2, 168), small, font=fs, fill=WHITE)
                    layer.putalpha(layer.getchannel("A").point(lambda a: int(a * kk)))
                    img.alpha_composite(layer, (x, y))
                put_text(img, (0, (L.H * 0.17) if not L.portrait else 250), "In our tests", 60, alpha=k, center=True)
        elif s.layout == "close":
            sz = 170 if not L.portrait else 220
            ly = int(L.H * (0.1 if not L.portrait else 0.16))
            img.alpha_composite(asset("logo", sz), ((L.W - sz) // 2, ly))
            put_text(img, (0, ly + sz + 20), "Scam Sentinel", 104 if not L.portrait else 96, center=True)
            tagline = "Hang up on fear, not on your family."
            nch = int(len(tagline) * ease((lt - 0.3) / 1.4))
            if nch:
                put_text(img, (0, ly + sz + 160), tagline[:nch], 56 if not L.portrait else 48, "sb", AMBER, center=True)
            k = ease((lt - 1.2) / 0.5)
            if k > 0:
                y = ly + sz + (260 if not L.portrait else 250)
                rows = [("More languages coming: Tamil · Telugu · Malayalam · Marathi · Bengali · Gujarati · Punjabi · Odia", 28, "sb", SOFT),
                        ("Try it: demo link in the comments  ·  Always call 1930 · cybercrime.gov.in", 32, "sb", WHITE),
                        ("#GnaniAI   #GreatIndianAIInternshipChallenge", 34, "b", GREEN),
                        ("Prototype · re-enacted calls · AI voices · a decision aid, not a guarantee", 26, "", DIM),
                        (MUSIC_CREDIT, 24, "", DIM)]
                for text, sz2, wgt, col in rows:
                    if L.portrait and len(text) > 60:
                        for part in wrap(ImageDraw.Draw(img), text, font(sz2 - 2, wgt), L.W - 140):
                            put_text(img, (0, y), part, sz2 - 2, wgt, col, k, True); y += sz2 + 14
                    else:
                        put_text(img, (0, y), text, sz2, wgt, col, k, True); y += sz2 + 26
            fade = max(0.0, (lt - (d - 0.7)) / 0.7)
            if fade > 0:
                img.alpha_composite(Image.new("RGBA", (L.W, L.H), (0, 0, 0, int(255 * fade))))
    sub = next((x for x in tl.subs if x[0] <= t < x[1] + 0.12), None)
    if sub and t < tl.total - 0.7:
        subtitle(img, L, sub[2], column=s.layout in ("phone", "laptop", "hook") or (s.layout == "reveal" and lt >= 1.4))
    if s.layout != "hook" and t < tl.total - 0.7:
        dots(img, L, i, len(tl.spans))
    return img.convert("RGB")


def render(L, tl, out: Path, audio: Path, stills=None):
    readers: dict = {}
    if stills is not None:
        for t in stills:
            draw(L, tl, t, readers).save(WORK / f"still_{'v' if L.portrait else 'h'}_{t:05.1f}.png")
        for r in readers.values():
            r.close()
        return
    enc = subprocess.Popen([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{L.W}x{L.H}", "-r", str(FPS), "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-ac", "2", "-shortest", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    for f in range(int(tl.total * FPS)):
        enc.stdin.write(draw(L, tl, f / FPS, readers).tobytes())
        if f % 300 == 0:
            print(f"    {L.W}x{L.H}: {f / FPS:5.1f} / {tl.total:.1f} s")
    for r in readers.values():
        r.close()
    enc.stdin.close(); enc.wait()


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    chars = sum(len(x) for x in VO.values())
    from budget import load_rates
    print(f"narration: {chars} characters, about {chars * (load_rates().get('tts_credits_per_1k_chars') or 0) / 1000:.1f} credits if not cached "
          f"({sum(len(x.split()) for x in VO.values()) + len(SCAMMER.split())} words)")
    if a.dry_run:
        return 0
    v = make_voice(); tl = timeline(v)
    print(f"  length {tl.total:.1f} s")
    audio = master(tl, v)
    layouts = [Layout(1920, 1080), Layout(1080, 1920)]
    for L in layouts:                                  # this brief's layout: a little more room for chips
        if L.portrait:
            L.screen = (340, 730, 340 + 400, 730 + 893); L.ty = 180
        else:
            L.screen = (300, 130, 300 + 405, 130 + 904)
    if a.stills:
        times = [3.5] + [(t0 + t1) / 2 for t0, t1, s in tl.spans[1:]] + [tl.spans[3][0] + (tl.spans[3][1] - tl.spans[3][0]) * 0.9]
        for L in layouts:
            render(L, tl, None, audio, times)
        return 0
    for L, out in zip(layouts, OUTS):
        render(L, tl, out, audio); print("  done:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
