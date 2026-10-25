"""Scam Sentinel promo (about 65 s), rendered frame by frame: 16:9 (1920x1080) and 9:16 (1080x1920).

Follows the brief in Desktop\\link.txt, with three honest changes agreed with the user: the trust scene shows measured
results (not "free / offline / nothing saved"), the clone is "a family member's voice, made with consent", and there
are no faces (a ringing phone instead). Voice: Gnani Timbre (narration + the scammer line, cached after the first run);
the spoken warning is the real recording. Music and sound effects are synthesized here (no third-party audio).

  python video/make_promo2.py --dry-run     # narration size and cost
  python video/make_promo2.py --stills      # a few still frames per format (free once the voice is cached)
  python video/make_promo2.py               # build both videos on the Desktop
"""
from __future__ import annotations

import argparse
import math
import random
import re
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CLIPS = Path(r"C:\Users\Welcome\Desktop\vid")
DESKTOP = Path(r"C:\Users\Welcome\Desktop")
WORK = ROOT / "video" / "build2"
FPS, SR = 30, 48000
TEAL, GREEN, RED, AMBER = (11, 43, 42), (31, 163, 122), (198, 40, 40), (247, 181, 56)
WHITE, SOFT, DIM, INK = (255, 255, 255), (200, 222, 216), (130, 160, 152), (6, 22, 21)
F_REG, F_SB, F_B = r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\seguisb.ttf", r"C:\Windows\Fonts\segoeuib.ttf"
CLIP = {"A": "Record_2026-10-25-14-00-41_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
        "B": "Record_2026-10-25-14-06-08_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
        "C": "Record_2026-10-25-14-07-11_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
        "D": "Record_2026-10-25-14-08-47_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
        "E": "Record_2026-10-25-14-12-23_40deb401b9ffe8e1df2f1cc5ba480b12.mp4"}

VO = {  # narration, Gnani Timbre (en-IN)
    "problem": "None of it was true. In 2024, Indians lost twenty-two thousand crore rupees to cyber fraud. "
               "And scammers don't wait. They strike during the call, when fear is highest.",
    "reveal": "Meet Scam Sentinel. A shield for every call.",
    "demo": "Put the call on speaker. Scam Sentinel listens, and the moment it hears a scam, it warns you out loud, "
            "in a family member's voice. An AI clone, made with consent.",
    "learn": "It speaks your language: Kannada, Hindi, English. It re-enacts real scams from real news, so you learn "
             "the tricks before they reach you. And a quick quiz trains you to spot them.",
    "sos": "Already cheated? One tap shows exactly what to do, step by step. Because the first hour matters most.",
    "trust": "It warns during the call, in three languages, and it caught every one of our twenty-four test scams.",
    "close": "Scam Sentinel. Hang up on fear, not on your family.",
}
SCAMMER = "We've arrested your son. Pay five lakh rupees now."
WARNING_LINE = "“It’s me. This call is a scam. Please hang up right now.”"
SUBS = {"problem": "None of it was true. In 2024, Indians lost ₹22,845 crore to cyber fraud. And scammers don't wait. "
                   "They strike during the call, when fear is highest.",
        "trust": "It warns during the call, in three languages, and it caught every one of our 24 test scams."}


# ---------------------------------------------------------------- helpers
def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args: list[str]) -> None:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:])


def read_wav(path: Path) -> np.ndarray:
    tmp = WORK / (path.stem + "_48k.wav")
    run(["-i", str(path), "-ac", "1", "-ar", str(SR), "-sample_fmt", "s16", str(tmp)])
    with wave.open(str(tmp)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def trim(x: np.ndarray, thr: float = 0.01) -> np.ndarray:
    idx = np.where(np.abs(x) > thr)[0]
    return x[max(0, idx[0] - 480): idx[-1] + 2400] if len(idx) else x


_FONTS: dict = {}


def font(size: int, w: str = "") -> ImageFont.FreeTypeFont:
    key = (size, w)
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype({"b": F_B, "sb": F_SB}.get(w, F_REG), size)
    return _FONTS[key]


def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def wrap(d, text, f, width):
    lines, cur = [], ""
    for wd in text.split():
        trial = (cur + " " + wd).strip()
        if d.textlength(trial, font=f) <= width:
            cur = trial
        else:
            lines.append(cur); cur = wd
    return lines + ([cur] if cur else [])


# ---------------------------------------------------------------- audio
def make_voice() -> dict[str, np.ndarray]:
    from gnani_client import GnaniClient
    from pipeline import speak_alert
    client = GnaniClient()
    out = {}
    for key, text in VO.items():
        audio, warn = speak_alert(client, text, "en-IN")
        if audio is None:
            raise RuntimeError(warn)
        p = WORK / f"vo_{key}.mp3"; p.write_bytes(audio)
        fast = WORK / f"vo_{key}_fast.wav"
        run(["-i", str(p), "-af", "atempo=1.05", "-ac", "1", "-ar", str(SR), str(fast)])
        out[key] = trim(read_wav(fast))
    raw = client.synthesize(SCAMMER, language="en-IN", voice="Pranav", model="timbre-v2.5")
    p = WORK / "scammer.mp3"; p.write_bytes(raw)
    phone = WORK / "scammer_phone.wav"           # sounds like a phone line
    run(["-i", str(p), "-af", "highpass=f=320,lowpass=f=3200,acompressor=threshold=-18dB:ratio=4,volume=1.6",
         "-ac", "1", "-ar", str(SR), str(phone)])
    out["scammer"] = trim(read_wav(phone))
    clip = WORK / "warning.wav"
    run(["-ss", "16.7", "-t", "5.9", "-i", str(CLIPS / CLIP["E"]), "-vn", "-ac", "1", "-ar", str(SR), str(clip)])
    out["warning"] = read_wav(clip) * 2.0
    print(f"  Gnani: {client.stats['tts_calls']} new, {client.stats['cache_hits']} from cache")
    return out


def tone(f, dur, amp=0.3):
    t = np.arange(int(dur * SR)) / SR
    return amp * np.sin(2 * np.pi * f * t)


def env(n, a=0.01, r=0.1):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def sfx_ring():
    out = []
    for _ in range(2):
        b = (tone(440, 0.42, 0.12) + tone(480, 0.42, 0.12)); b *= env(len(b), 0.01, 0.05)
        out += [b, np.zeros(int(0.22 * SR))]
    return np.concatenate(out)


def sfx_heart():
    def thump(amp):
        t = np.arange(int(0.16 * SR)) / SR
        return amp * np.sin(2 * np.pi * 52 * t) * np.exp(-t * 28)
    return np.concatenate([thump(0.55), np.zeros(int(0.14 * SR)), thump(0.4)])


def sfx_whoosh(dur=0.45):
    n = int(dur * SR); noise = np.random.default_rng(1).standard_normal(n)
    k = np.linspace(2, 40, n).astype(int)                    # low-pass that opens up: a sweep
    out = np.array([noise[max(0, i - k[i]):i + 1].mean() for i in range(n)])
    return 0.5 * out * np.sin(np.linspace(0, np.pi, n)) ** 2


def sfx_tick():
    t = np.arange(int(0.05 * SR)) / SR
    return 0.22 * np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 90)


def sfx_alarm():
    return np.concatenate([tone(f, 0.16, 0.18) * env(int(0.16 * SR), 0.005, 0.03) for f in (880, 660, 880, 660)])


def music(total, dip_at, end_at):
    """Soft pad that builds: Am - F - C - G, a silent beat before the reveal, a warm C chord to finish."""
    t = np.arange(int(total * SR)) / SR
    chords = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (130.8, 196.0, 261.6), (196.0, 246.9, 293.7)]
    out = np.zeros_like(t)
    seg = 2.4
    for i, start in enumerate(np.arange(0, total, seg)):
        ch = (130.8, 196.0, 261.6, 329.6) if start >= end_at else chords[i % 4]
        s, e = int(start * SR), min(len(t), int((start + seg + 0.6) * SR))
        tt = t[s:e] - start
        part = sum(np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) for f in ch)
        part *= np.minimum(1, tt / 0.8) * np.exp(-np.maximum(0, tt - seg) * 6)
        out[s:e] += part
    build = 0.35 + 0.65 * np.clip(t / total, 0, 1)                      # grows over the video
    out *= 0.018 * build
    lo, hi = int((dip_at - 0.7) * SR), int(dip_at * SR)                  # the quiet beat
    out[lo:hi] *= np.linspace(1, 0, hi - lo)
    out[hi:hi + int(0.9 * SR)] *= np.linspace(0, 1, min(int(0.9 * SR), len(out) - hi))
    out[-int(1.2 * SR):] *= np.linspace(1, 0, int(1.2 * SR))
    return out


# ---------------------------------------------------------------- timeline
@dataclass
class Shot:
    kind: str
    t0: float
    t1: float
    clip: str | None = None
    c0: float = 0.0
    c1: float = 0.0
    data: dict = field(default_factory=dict)


@dataclass
class Plan:
    shots: list[Shot]
    subs: list[tuple[float, float, str]]
    sounds: list[tuple[float, str]]
    voice: list[tuple[float, str]]
    total: float
    reveal_at: float
    close_at: float


def split_sub(t0, t1, text):
    """Splits a narration into sentence-sized subtitles, timed by length."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    total = sum(len(p) for p in parts); out, t = [], t0
    for p in parts:
        d = (t1 - t0) * len(p) / total
        out.append((t, t + d, p)); t += d
    return out


def plan(v: dict[str, np.ndarray]) -> Plan:
    dur = {k: len(a) / SR for k, a in v.items()}
    shots, subs, sounds, voice = [], [], [], []
    t = 0.0
    # 1 hook
    s_at = 1.45
    hook_end = s_at + dur["scammer"] + 0.9
    shots.append(Shot("hook", 0, hook_end, data={"talk": (s_at, s_at + dur["scammer"])}))
    sounds += [(0.0, "ring"), (s_at - 0.1, "heart"), (s_at + 0.95, "heart"), (s_at + 1.9, "heart"), (s_at + 2.85, "heart")]
    voice.append((s_at, "scammer")); subs.append((s_at, s_at + dur["scammer"], "“" + SCAMMER + "”"))
    t = hook_end + 0.15
    # 2 problem
    d = dur["problem"] + 0.2
    shots.append(Shot("problem", t, t + d)); voice.append((t, "problem"))
    subs += split_sub(t, t + dur["problem"], SUBS["problem"]); sounds.append((t - 0.05, "whoosh"))
    for f in (0.22, 0.52, 0.74):
        sounds.append((t + d * f, "tick"))
    t += d
    # 3 reveal (a quiet beat first)
    reveal_at = t
    d = 0.6 + dur["reveal"] + 0.3
    shots.append(Shot("reveal", t, t + d)); voice.append((t + 0.6, "reveal"))
    subs += split_sub(t + 0.6, t + 0.6 + dur["reveal"], VO["reveal"]); sounds.append((t + 0.55, "whoosh"))
    t += d
    # 4 demo: listen -> safe -> warning (the real recording)
    d = dur["demo"] + 0.1
    shots.append(Shot("demo_listen", t, t + d * 0.42, "E", 4.2, 7.6))
    shots.append(Shot("demo_safe", t + d * 0.42, t + d, "E", 8.0, 15.6))
    voice.append((t, "demo")); subs += split_sub(t, t + dur["demo"], VO["demo"]); sounds.append((t - 0.05, "whoosh"))
    t += d
    w = dur["warning"]
    shots.append(Shot("demo_warn", t, t + w, "E", 16.7, 16.7 + w))
    voice.append((t, "warning")); subs.append((t + 0.2, t + w, WARNING_LINE)); sounds.append((t, "alarm"))
    for f in (0.25, 0.42, 0.59):
        sounds.append((t + w * f, "tick"))
    t += w
    # 5 learn: language -> real scams -> quiz
    d = dur["learn"] + 0.15
    shots += [Shot("learn_lang", t, t + d * 0.3, "A", 0.3, 3.4), Shot("learn_real", t + d * 0.3, t + d * 0.7, "A", 37.0, 42.5),
              Shot("learn_quiz", t + d * 0.7, t + d, "C", 14.8, 17.6)]
    voice.append((t, "learn")); subs += split_sub(t, t + dur["learn"], VO["learn"])
    sounds += [(t - 0.05, "whoosh"), (t + d * 0.3 - 0.05, "whoosh"), (t + d * 0.7 - 0.05, "whoosh")]
    t += d
    # 6 SOS
    d = dur["sos"] + 0.3
    shots.append(Shot("sos", t, t + d, "D", 26.0, 27.3)); voice.append((t, "sos"))
    subs += split_sub(t, t + dur["sos"], VO["sos"]); sounds.append((t - 0.05, "whoosh"))
    for f in (0.15, 0.32, 0.49, 0.66):
        sounds.append((t + d * f, "tick"))
    t += d
    # 7 trust
    d = dur["trust"] + 0.25
    shots.append(Shot("trust", t, t + d)); voice.append((t, "trust"))
    subs += split_sub(t, t + dur["trust"], SUBS["trust"]); sounds.append((t - 0.05, "whoosh"))
    for f in (0.05, 0.3, 0.55):
        sounds.append((t + d * f, "tick"))
    t += d
    # 8 close
    close_at = t
    d = dur["close"] + 1.3
    shots.append(Shot("close", t, t + d)); voice.append((t + 0.2, "close"))
    subs += split_sub(t + 0.2, t + 0.2 + dur["close"], VO["close"]); sounds.append((t - 0.05, "whoosh"))
    t += d
    return Plan(shots, subs, sounds, voice, t, reveal_at, close_at)


def mix(p: Plan, v: dict[str, np.ndarray]) -> Path:
    n = int((p.total + 0.5) * SR); out = np.zeros(n, dtype=np.float32)

    def put(at, x, gain=1.0):
        s = int(at * SR); e = min(n, s + len(x))
        if s < n:
            out[s:e] += gain * x[:e - s]
    voice_mask = np.zeros(n, dtype=bool)
    for at, key in p.voice:
        put(at, v[key]); voice_mask[int(at * SR): int(at * SR) + len(v[key])] = True
    fx = {"ring": sfx_ring(), "heart": sfx_heart(), "whoosh": sfx_whoosh(), "tick": sfx_tick(), "alarm": sfx_alarm()}
    for at, key in p.sounds:
        put(at, fx[key], 0.9)
    m = music(p.total + 0.5, p.reveal_at, p.close_at)[:n]
    hook = int(p.shots[0].t1 * SR)
    m[:hook] = 0                                                # silence under the hook: ring, voice, heartbeat only
    duck = np.where(voice_mask, 0.45, 1.0)
    duck = np.convolve(duck, np.ones(4800) / 4800, mode="same")   # smooth ducking under the voice
    out += m * duck
    out = np.clip(out / max(1.0, np.abs(out).max() / 0.95), -1, 1)
    path = WORK / "mix.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    return path


# ---------------------------------------------------------------- layout
class Layout:
    def __init__(self, w, h):
        self.W, self.H = w, h
        self.portrait = h > w
        if self.portrait:
            self.screen = (350, 870, 350 + 380, 870 + 849)
            self.tx, self.ty, self.tw = 80, 190, w - 160
            self.sub_y = 1772
        else:
            self.screen = (300, 130, 300 + 405, 130 + 904)
            self.tx, self.ty, self.tw = 880, 230, w - 880 - 80
            self.sub_y = 948
        self.bg = self._bg()

    def _bg(self):
        W, H = self.W, self.H
        col = Image.new("RGB", (1, H))
        for y in range(H):
            k = y / H
            col.putpixel((0, y), tuple(int(TEAL[i] * (1 - k) + INK[i] * k) for i in range(3)))
        img = col.resize((W, H))
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse((-W * 0.2, -H * 0.4, W * 0.6, H * 0.6), fill=110)
        glow = glow.filter(ImageFilter.GaussianBlur(max(W, H) // 8))
        img = Image.composite(Image.new("RGB", (W, H), (24, 120, 98)), img, glow)
        g = ImageDraw.Draw(img, "RGBA")
        for x in range(0, W, 64):
            g.line((x, 0, x, H), fill=(255, 255, 255, 6))
        for y in range(0, H, 64):
            g.line((0, y, W, y), fill=(255, 255, 255, 6))
        return img


_IMG: dict = {}


def asset(name, size):
    key = (name, size)
    if key not in _IMG:
        path = {"logo": ROOT / "web/icons/icon-512.png", "kn": WORK.parent / "build/word_kn_mask.png",
                "hi": WORK.parent / "build/word_hi_mask.png"}[name]
        im = Image.open(path)
        im = im.convert("RGBA") if name == "logo" else im.convert("L")
        r = size / im.height
        _IMG[key] = im.resize((max(1, int(im.width * r)), size), Image.LANCZOS)
    return _IMG[key]


def text_layer(text, f, color):
    """A line of text where *word* is amber, on its own transparent layer (for fades and slides)."""
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    plain = text.replace("*", "")
    w = int(d0.textlength(plain, font=f)) + 8
    h = int(f.size * 1.35)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 0
    for part in re.split(r"(\*[^*]+\*)", text):
        if part:
            c, tx = (AMBER, part.strip("*")) if part.startswith("*") else (color, part)
            d.text((x, 0), tx, font=f, fill=c); x += d.textlength(tx, font=f)
    return im


_TL: dict = {}


def put_text(img, xy, text, size, w="b", color=WHITE, alpha=1.0, center=False):
    key = (text, size, w, color)
    if key not in _TL:
        _TL[key] = text_layer(text, font(size, w), color)
    layer = _TL[key]
    if alpha < 1:
        layer = layer.copy(); layer.putalpha(layer.getchannel("A").point(lambda a: int(a * alpha)))
    x, y = xy
    if center:
        x = (img.width - layer.width) // 2
    img.alpha_composite(layer, (int(x), int(y)))
    return layer.width


def kinetic(img, L, lines, t, start, size, y=None, center=False):
    """Headline lines fade in and slide up, one after another."""
    y = L.ty + 70 if y is None else y
    for i, line in enumerate(lines):
        k = ease((t - start - i * 0.12) / 0.35)
        if k > 0:
            put_text(img, (L.tx, y + (1 - k) * 34), line, size, alpha=k, center=center)
        y += int(size * 1.18)
    return y


def chip(img, x, y, label, color=GREEN, t=1.0, size=30, fill=None):
    k = ease(t / 0.25)
    if k <= 0:
        return 0
    f = font(size, "sb"); d = ImageDraw.Draw(img, "RGBA")
    tw = d.textlength(label, font=f); w, h = tw + 44, size + 26
    s = 0.7 + 0.3 * k
    layer = Image.new("RGBA", (int(w) + 4, int(h) + 4), (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
    dl.rounded_rectangle((1, 1, w, h), radius=h // 2, fill=fill or color + (40,), outline=color + (255,), width=3)
    dl.text((22, 10), label, font=f, fill=WHITE)
    layer = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))))
    layer.putalpha(layer.getchannel("A").point(lambda a: int(a * k)))
    img.alpha_composite(layer, (int(x + (1 - s) * w / 2), int(y + (1 - s) * h / 2)))
    return w


def lang_chips(img, x, y, size, center_w=None):
    """ಕನ್ನಡ · हिन्दी · English chips (Indic words are pre-shaped images)."""
    items = [("kn", None), ("hi", None), (None, "English")]
    d = ImageDraw.Draw(img, "RGBA"); f = font(size, "sb"); h = size + 30
    widths = []
    for k, label in items:
        widths.append((asset(k, size).width if k else d.textlength(label, font=f)) + 50)
    total = sum(widths) + 20 * 2
    if center_w is not None:
        x = (center_w - total) // 2
    for (k, label), w in zip(items, widths):
        layer = Image.new("RGBA", (int(w) + 4, int(h) + 4), (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
        dl.rounded_rectangle((1, 1, w, h), radius=h // 2, fill=GREEN + (55,), outline=GREEN + (255,), width=3)
        if k:
            layer.paste(WHITE + (255,), (25, 15), asset(k, size))
        else:
            dl.text((25, 8), label, font=f, fill=WHITE)
        img.alpha_composite(layer, (int(x), int(y)))
        x += w + 20


def subtitle(img, L, text, column=False):
    """Burned-in subtitle; in landscape phone scenes it sits under the right-hand column, clear of the phone."""
    if not text:
        return
    d = ImageDraw.Draw(img); f = font(34 if L.portrait else 32, "sb")
    left, width = (L.tx, L.tw) if (column and not L.portrait) else (80, L.W - 160)
    lines = wrap(d, text, f, width)[:2]
    lh = 48
    y = L.sub_y + (70 - lh * len(lines)) // 2
    for i, line in enumerate(lines):
        tw = int(d.textlength(line, font=f)); x = left + (width - tw) // 2
        layer = Image.new("RGBA", (tw + 32, 46), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((0, 0, tw + 31, 45), radius=10, fill=(0, 0, 0, 160))
        ImageDraw.Draw(layer).text((16, 2), line, font=f, fill=WHITE)
        img.alpha_composite(layer, (x - 16, y + i * lh - 2))


def header(img, L):
    logo = asset("logo", 54); img.alpha_composite(logo, (60, 44))
    ImageDraw.Draw(img).text((128, 48), "Scam Sentinel", font=font(34, "sb"), fill=WHITE)


def tag(img, L, label, y=None):
    f = font(26, "sb"); y = L.ty if y is None else y
    tw = int(ImageDraw.Draw(img).textlength(label, font=f))
    layer = Image.new("RGBA", (tw + 44, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.rounded_rectangle((1, 1, tw + 41, 49), radius=24, fill=AMBER + (40,), outline=AMBER + (255,), width=2)
    d.text((21, 9), label, font=f, fill=AMBER)
    img.alpha_composite(layer, (L.tx, y))


# ---------------------------------------------------------------- phone
class ClipReader:
    """Streams the frames of one clip segment at 30 fps, already scaled to the phone screen."""

    def __init__(self, clip, c0, c1, size):
        self.size, self.idx, self.frame = size, -1, None
        self.proc = subprocess.Popen([ffmpeg(), "-hide_banner", "-loglevel", "error", "-ss", f"{c0}", "-t", f"{c1 - c0}",
                                      "-i", str(CLIPS / CLIP[clip]), "-vf", f"fps={FPS},scale={size[0]}:{size[1]}",
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def get(self, i):
        n = self.size[0] * self.size[1] * 3
        while self.idx < i:
            buf = self.proc.stdout.read(n)
            if len(buf) < n:
                break                                            # past the end: keep the last frame
            self.frame = Image.frombytes("RGB", self.size, buf); self.idx += 1
        return self.frame

    def close(self):
        self.proc.kill()


def phone(img, L, frame, zoom=1.0, shake=(0, 0), red=0.0):
    x0, y0, x1, y1 = L.screen
    w, h = x1 - x0, y1 - y0
    pad = 18
    W2, H2 = int((w + 2 * pad) * zoom), int((h + 2 * pad) * zoom)
    cx, cy = (x0 + x1) // 2 + shake[0], (y0 + y1) // 2 + shake[1]
    body = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(body)
    d.rounded_rectangle((0, 0, w + 2 * pad - 1, h + 2 * pad - 1), radius=64, fill=(12, 16, 18), outline=(96, 116, 112), width=3)
    if frame is not None:
        mask = Image.new("L", (w, h), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=46, fill=255)
        body.paste(frame, (pad, pad), mask)
    if red > 0:
        glow = Image.new("RGBA", body.size, RED + (0,)); ImageDraw.Draw(glow).rounded_rectangle(
            (0, 0, body.width - 1, body.height - 1), radius=64, outline=RED + (int(255 * red),), width=10)
        body.alpha_composite(glow)
    if zoom != 1.0:
        body = body.resize((W2, H2), Image.BILINEAR)
    shadow = Image.new("RGBA", (body.width + 80, body.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((40, 60, body.width + 40, body.height + 60), radius=70, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    img.alpha_composite(shadow, (cx - body.width // 2 - 40, cy - body.height // 2 - 40))
    img.alpha_composite(body, (cx - body.width // 2, cy - body.height // 2))


def incoming_call(L, t, talk):
    """A generic incoming-call screen (drawn, not the app): dark, a pulsing ring, 'Unknown caller'."""
    x0, y0, x1, y1 = L.screen; w, h = x1 - x0, y1 - y0
    im = Image.new("RGB", (w, h), (14, 16, 20)); d = ImageDraw.Draw(im, "RGBA")
    cx, cy = w // 2, int(h * 0.36)
    for i in range(3):
        r = 70 + ((t * 70 + i * 40) % 120)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, int(110 * (1 - (r - 70) / 120))), width=3)
    d.ellipse((cx - 64, cy - 64, cx + 64, cy + 64), fill=(60, 66, 74))
    d.text((cx - 28, cy - 40), "?", font=font(70, "b"), fill=(190, 196, 204))
    for txt, size, yy, col in (("Unknown caller", 40, cy + 110, WHITE), ("+91 ••••• •••••", 28, cy + 165, (160, 166, 176)),
                               ("Incoming call…" if t < talk[0] else "00:0%d" % min(9, int(t - talk[0])), 26, cy + 210, (160, 166, 176))):
        tw = d.textlength(txt, font=font(size, "sb")); d.text(((w - tw) / 2, yy), txt, font=font(size, "sb"), fill=col)
    for bx, col in ((w * 0.28, (198, 40, 40)), (w * 0.72, (31, 163, 122))):
        d.ellipse((bx - 46, h * 0.82 - 46, bx + 46, h * 0.82 + 46), fill=col)
    return im


# ---------------------------------------------------------------- scenes
def draw(L: Layout, p: Plan, t: float, readers: dict) -> Image.Image:
    shot = next((s for s in p.shots if s.t0 <= t < s.t1), None)
    if shot is None:
        return Image.new("RGB", (L.W, L.H), (0, 0, 0)) if t < p.total - 0.05 else Image.new("RGB", (L.W, L.H), (0, 0, 0))
    lt = t - shot.t0; dur = shot.t1 - shot.t0
    img = (Image.new("RGBA", (L.W, L.H), (0, 0, 0, 255)) if shot.kind == "hook" else L.bg.convert("RGBA"))
    W, H = L.W, L.H
    if shot.kind != "hook":
        header(img, L)
    frame = None
    if shot.clip:
        r = readers.get(id(shot))
        if r is None:
            for k in list(readers):
                readers.pop(k).close()
            pw, ph = L.screen[2] - L.screen[0], L.screen[3] - L.screen[1]
            r = readers[id(shot)] = ClipReader(shot.clip, shot.c0, shot.c1, (pw, ph))
        speed = max(1.0, (shot.c1 - shot.c0) / dur)
        frame = r.get(int(lt * FPS * speed))
    zoom = 1.0 + 0.04 * (lt / dur)

    if shot.kind == "hook":
        talk = shot.data["talk"]
        talking = talk[0] <= t <= talk[1]
        shake = (random.Random(int(t * 30)).randint(-5, 5), random.Random(int(t * 31)).randint(-5, 5)) if talking else (0, 0)
        beat = max(0.0, math.sin(t * 7.4)) ** 6 if t > talk[0] - 0.2 else 0
        vign = Image.new("RGBA", (W, H), (120, 10, 10, int(70 * beat))); img.alpha_composite(vign)
        phone(img, L, incoming_call(L, t, talk), zoom=1.0 + 0.06 * ease(t / dur), shake=shake)
        if t > talk[0] + 0.8:
            k = ease((t - talk[0] - 0.8) / 0.4)
            y = (L.screen[1] - 130) if L.portrait else 120
            if L.portrait:
                put_text(img, (0, 120), "A real call.", 64, alpha=k, center=True)
                put_text(img, (0, 205), "Someone's *uncle* got it.", 64, alpha=k, center=True)
            else:
                put_text(img, (L.tx, 380), "A real call.", 76, alpha=k)
                put_text(img, (L.tx, 480), "Someone's *uncle*", 76, alpha=k)
                put_text(img, (L.tx, 580), "got it.", 76, alpha=k)
    elif shot.kind == "problem":
        c = W // 2
        if lt < dur * 0.22 + 0.4:
            k = ease(lt / 0.4) * (1 - ease((lt - dur * 0.22) / 0.4))
            put_text(img, (0, H * 0.38), "None of it was *true.*", 110 if not L.portrait else 84, alpha=k, center=True)
        else:
            def counter(y, start, value, unit, label, fmt="{:,}"):
                k = ease((lt - start) / 1.2)
                if lt < start:
                    return
                num = int(value * k)
                s = "₹" + fmt.format(num) + unit if unit else fmt.format(num)
                put_text(img, (0, y), s, 120 if not L.portrait else 100, color=AMBER, alpha=min(1, (lt - start) / 0.3), center=True)
                put_text(img, (0, y + (150 if not L.portrait else 125)), label, 40 if not L.portrait else 38, "sb", SOFT,
                         alpha=min(1, (lt - start) / 0.3), center=True)
            if lt < dur * 0.74:
                base = H * (0.22 if not L.portrait else 0.25)
                counter(base, dur * 0.22, 22845, " crore", "lost to cyber fraud in India, 2024")
                counter(base + (290 if not L.portrait else 330), dur * 0.52, 1935, " crore", "lost to ‘digital arrest’ scams")
            else:
                k = ease((lt - dur * 0.74) / 0.4)
                cy = H * 0.3
                d = ImageDraw.Draw(img, "RGBA")
                d.ellipse((c - 36, cy - 36, c + 36, cy + 36), fill=RED + (int(255 * k),))
                d.polygon(((c - 30, cy + 18), (c + 30, cy + 18), (c, cy + 80)), fill=RED + (int(255 * k),))
                d.ellipse((c - 14, cy - 14, c + 14, cy + 14), fill=WHITE + (int(255 * k),))
                put_text(img, (0, cy + 110), "Karnataka", 56, "b", WHITE, alpha=k, center=True)
                put_text(img, (0, cy + 190), "641 cases · ₹109 crore", 78, "b", AMBER, alpha=k, center=True)
            if lt > dur * 0.62:
                k = ease((lt - dur * 0.62) / 0.4)
                put_text(img, (0, H * (0.74 if not L.portrait else 0.72)), "Fraud happens *DURING* the call.",
                         64 if not L.portrait else 56, alpha=k, center=True)
    elif shot.kind == "reveal":
        k = ease((lt - 0.7) / 0.6)
        if k > 0:
            size = 260 if not L.portrait else 300
            logo = asset("logo", size).copy()
            glow = Image.new("RGBA", (size + 200, size + 200), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse((40, 40, size + 160, size + 160), fill=GREEN + (int(150 * k * (0.75 + 0.25 * math.sin(lt * 4))),))
            glow = glow.filter(ImageFilter.GaussianBlur(40))
            ly = int(H * (0.16 if not L.portrait else 0.22))
            img.alpha_composite(glow, ((W - glow.width) // 2, ly - 100))
            logo.putalpha(logo.getchannel("A").point(lambda a: int(a * k)))
            img.alpha_composite(logo, ((W - size) // 2, ly))
            put_text(img, (0, ly + size + 40), "Scam Sentinel", 120 if not L.portrait else 110, alpha=ease((lt - 1.0) / 0.5), center=True)
            put_text(img, (0, ly + size + 200), "A shield for *every call*", 56 if not L.portrait else 54, "sb", SOFT,
                     alpha=ease((lt - 1.4) / 0.5), center=True)
            if lt > 1.9:
                lang_chips(img, 0, ly + size + 300, 44, center_w=W)
    elif shot.kind.startswith("demo"):
        warn = shot.kind == "demo_warn"
        red = max(0.0, 1 - lt / 0.6) if warn else 0
        phone(img, L, frame, zoom=zoom, red=(0.6 + 0.4 * math.sin(lt * 8)) if warn else 0)
        tag(img, L, "LIVE PROTECTION · CALL ON SPEAKER")
        lines = ["It warns you", "*DURING* the call"] if warn else ["Put the call", "on *speaker*"]
        y = kinetic(img, L, lines, lt, 0.05, 92 if not L.portrait else 80)
        if warn:
            labels = ["pretending to be police", "threat of arrest", "pushing you to transfer money"]
            for i, lab in enumerate(labels):
                chip(img, L.tx, y + 16 + i * (70 if L.portrait else 76), lab, RED, t=lt - dur * (0.25 + 0.17 * i), size=30)
            ImageDraw.Draw(img).text((L.tx, y + 16 + 3 * (70 if L.portrait else 76) + 6), "AI voice clone of a family member · made with consent",
                                     font=font(26, "sb"), fill=AMBER)
            if red > 0:
                img.alpha_composite(Image.new("RGBA", (W, H), RED + (int(150 * red),)))
        else:
            label = "Listening · Safe so far" if shot.kind == "demo_safe" else "Tap “Start listening”"
            chip(img, L.tx, y + 20, label, GREEN, t=lt, size=32)
    elif shot.kind.startswith("learn"):
        phone(img, L, frame, zoom=zoom)
        tagl, lines = {"learn_lang": ("YOUR LANGUAGE", ["It speaks", "*your language*"]),
                       "learn_real": ("REAL SCAMS · REAL NEWS", ["Real scams.", "*Re-enacted.*"]),
                       "learn_quiz": ("PRACTICE", ["*Practise*", "spotting them"])}[shot.kind]
        tag(img, L, tagl)
        y = kinetic(img, L, lines, lt, 0.05, 92 if not L.portrait else 80)
        if shot.kind == "learn_lang" and lt > 0.4:
            lang_chips(img, L.tx, y + 20, 38)
        if shot.kind == "learn_real":
            chip(img, L.tx, y + 20, "Two Gnani voices act it out", GREEN, t=lt - 0.3, size=30)
        if shot.kind == "learn_quiz":
            chip(img, L.tx, y + 20, "Right! Scam or safe, explained", GREEN, t=lt - 0.3, size=30)
    elif shot.kind == "sos":
        phone(img, L, frame, zoom=zoom)
        tag(img, L, "SOS · ONE TAP")
        y = kinetic(img, L, ["Cheated?", "*One tap.*"], lt, 0.05, 92 if not L.portrait else 80)
        steps = ["Call 1930", "Call your bank", "Call your family", "File at cybercrime.gov.in"]
        for i, s in enumerate(steps):
            k = ease((lt - dur * (0.15 + 0.17 * i)) / 0.3)
            if k > 0:
                d = ImageDraw.Draw(img, "RGBA"); yy = y + 20 + i * 74 + (1 - k) * 20
                col = RED if i == 0 else GREEN
                d.ellipse((L.tx, yy, L.tx + 50, yy + 50), fill=col + (int(255 * k),))
                d.text((L.tx + 17, yy + 4), str(i + 1), font=font(32, "b"), fill=WHITE + (int(255 * k),))
                d.text((L.tx + 68, yy + 2), s, font=font(36, "sb"), fill=WHITE + (int(255 * k),))
    elif shot.kind == "trust":
        cards = [("Warns", "DURING the call"), (None, "3 languages"), ("24 / 24", "test scams caught · 0 false alarms")]
        cw, chh = (520, 300) if not L.portrait else (860, 260)
        for i, (big, small) in enumerate(cards):
            k = ease((lt - dur * (0.05 + 0.25 * i)) / 0.3)
            if k <= 0:
                continue
            if not L.portrait:
                x = (W - 3 * cw - 2 * 40) // 2 + i * (cw + 40); y = int(H * 0.3)
            else:
                x = (W - cw) // 2; y = 330 + i * (chh + 40)
            layer = Image.new("RGBA", (cw, chh), (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
            dl.rounded_rectangle((0, 0, cw - 1, chh - 1), radius=28, fill=(255, 255, 255, 18), outline=GREEN, width=3)
            if big:
                tw = dl.textlength(big, font=font(84, "b")); dl.text(((cw - tw) / 2, 50), big, font=font(84, "b"), fill=AMBER)
            else:
                tmp = Image.new("RGBA", (cw, 120), (0, 0, 0, 0)); lang_chips(tmp, 0, 30, 34, center_w=cw)
                layer.alpha_composite(tmp, (0, 40))
            for j, line in enumerate(wrap(dl, small, font(34, "sb"), cw - 60)[:2]):
                tw = dl.textlength(line, font=font(34, "sb")); dl.text(((cw - tw) / 2, 175 + j * 44), line, font=font(34, "sb"), fill=SOFT)
            s = 0.8 + 0.2 * k
            layer = layer.resize((int(cw * s), int(chh * s))); layer.putalpha(layer.getchannel("A").point(lambda a: int(a * k)))
            img.alpha_composite(layer, (int(x + cw * (1 - s) / 2), int(y + chh * (1 - s) / 2)))
    elif shot.kind == "close":
        size = 200 if not L.portrait else 240
        ly = int(H * (0.12 if not L.portrait else 0.2))
        img.alpha_composite(asset("logo", size), ((W - size) // 2, ly))
        put_text(img, (0, ly + size + 30), "Scam Sentinel", 110 if not L.portrait else 104, center=True)
        tagline = "Hang up on fear, not on your family."
        n = int(len(tagline) * ease((lt - 0.4) / 1.6))
        if n:
            put_text(img, (0, ly + size + 180), tagline[:n], 60 if not L.portrait else 50, "sb", AMBER, center=True)
        k = ease((lt - 1.4) / 0.5)
        if k > 0:
            base = ly + size + (300 if not L.portrait else 300)
            put_text(img, (0, base), "Built on Gnani Prisma + Timbre · Demo link in the comments", 34 if not L.portrait else 30, "sb", WHITE, k, True)
            put_text(img, (0, base + 60), "#GnaniAI  #GreatIndianAIInternshipChallenge", 36 if not L.portrait else 32, "b", GREEN, k, True)
            put_text(img, (0, base + 120), "Prototype · re-enacted calls · AI voices · Real scam? Call 1930", 26, "", DIM, k, True)
        fade = max(0.0, (lt - (dur - 0.6)) / 0.6)
        if fade > 0:
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
    sub = next((s for s in p.subs if s[0] <= t < s[1] + 0.15), None)
    if sub and t < p.total - 0.8:
        subtitle(img, L, sub[2], column=shot.clip is not None)
    if shot.kind == "hook" and t > shot.t1 - 0.12:              # hard cut to silence and black
        return Image.new("RGB", (W, H), (0, 0, 0))
    return img.convert("RGB")


def render(L: Layout, p: Plan, out: Path, audio: Path, frames: list[float] | None = None) -> None:
    if frames is not None:                                     # stills
        readers = {}
        for t in frames:
            draw(L, p, t, readers).save(WORK / f"still_{'v' if L.portrait else 'h'}_{t:05.1f}.png")
        for r in readers.values():
            r.close()
        return
    enc = subprocess.Popen([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{L.W}x{L.H}", "-r", str(FPS), "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    readers: dict = {}
    n = int(p.total * FPS)
    for i in range(n):
        enc.stdin.write(draw(L, p, i / FPS, readers).tobytes())
        if i % 300 == 0:
            print(f"    {L.W}x{L.H}: {i / FPS:5.1f} / {p.total:.1f} s")
    for r in readers.values():
        r.close()
    enc.stdin.close(); enc.wait()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    chars = sum(len(x) for x in VO.values()) + len(SCAMMER)
    from budget import load_rates
    print(f"voice: {chars} characters, about {chars * (load_rates().get('tts_credits_per_1k_chars') or 0) / 1000:.1f} credits if not cached")
    if a.dry_run:
        return 0
    v = make_voice()
    p = plan(v)
    print(f"  length {p.total:.1f} s")
    audio = mix(p, v)
    layouts = [Layout(1920, 1080), Layout(1080, 1920)]
    if a.stills:
        times = [2.5, 5.0] + [s.t0 + (s.t1 - s.t0) * 0.75 for s in p.shots[1:]]
        for L in layouts:
            render(L, p, None, audio, times)
        print("stills in", WORK)
        return 0
    outs = [DESKTOP / "Scam Sentinel - promo 16x9.mp4", DESKTOP / "Scam Sentinel - promo 9x16.mp4"]
    for L, out in zip(layouts, outs):
        render(L, p, out, audio)
        print("  done:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
