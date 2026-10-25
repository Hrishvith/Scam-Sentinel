"""Builds the 60-second Scam Sentinel demo video (16:9, 1920x1080) in the style of a product walkthrough:
the phone recording on the left, a section tag + big headline + a checklist that ticks step by step on the right,
continuous Gnani Timbre narration (no gaps), small subtitles, and one steady layout so cuts feel like animation.

  python video/make_promo.py --dry-run    # narration size and cost; makes nothing
  python video/make_promo.py --preview    # still frames of every scene (free)
  python video/make_promo.py              # build (narration is cached after the first time)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLIPS = Path(r"C:\Users\Welcome\Desktop\vid")
OUT = Path(r"C:\Users\Welcome\Desktop\Scam Sentinel - 60s demo.mp4")
WORK = ROOT / "video" / "build"
W, H, FPS = 1920, 1080, 30
FONT, FONT_SB, FONT_B = (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\seguisb.ttf", r"C:\Windows\Fonts\segoeuib.ttf")
NAVY_TOP, NAVY_BOTTOM = (8, 22, 32), (5, 14, 22)
AMBER, GREEN, WHITE, SOFT, DIM = (247, 181, 56), (52, 211, 140), (255, 255, 255), (196, 210, 220), (128, 146, 158)
GAP = 0.06                                   # seconds between one sentence and the next

CLIP = {
    "A": "Record_2026-10-25-14-00-41_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
    "B": "Record_2026-10-25-14-06-08_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
    "C": "Record_2026-10-25-14-07-11_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
    "D": "Record_2026-10-25-14-08-47_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
    "E": "Record_2026-10-25-14-12-23_40deb401b9ffe8e1df2f1cc5ba480b12.mp4",
}


@dataclass
class Scene:
    name: str
    narration: str = ""                     # Gnani Timbre voice; "" when the recording's own sound plays
    subtitle: str = ""                      # defaults to the narration
    kind: str = "phone"                     # phone | hook | stat | end
    clip: str | None = None
    start: float = 0.0
    end: float = 0.0
    tag: str = ""
    headline: list[str] = field(default_factory=list)   # *word* = amber highlight
    items: list[str] = field(default_factory=list)      # checklist; the last one is the current step
    note: str = ""
    cards: list[tuple[str, str]] = field(default_factory=list)   # (big value, small label)
    clip_audio: bool = False


LIVE = ["Start listening", "Safe so far", "Scam? It warns out loud", "What to do next"]
SCENES = [
    Scene("01_hook", kind="hook", headline=["“We’ve arrested *your son.*", "Pay *₹5 lakh* now.”"],
          note="A real call my uncle got",
          narration="My uncle got this call. Police, they said. His son was arrested, and he had to pay five lakh rupees, right now."),
    Scene("02_problem", kind="stat", headline=["None of it was *true.*"],
          cards=[("₹22,845 crore", "lost to cyber fraud in India, 2024"), ("During the call", "is when the damage happens")],
          narration="None of it was true. But calls like this cost Indians twenty two thousand crore rupees last year, and nobody warns you during the call."),
    Scene("03_built", clip="B", start=0.3, end=3.0, tag="SCAM SENTINEL", headline=["A shield for", "*every call*"],
          items=["Kannada · Hindi · English"],
          narration="So I built Scam Sentinel, in Kannada, Hindi and English."),
    Scene("04_listen", clip="E", start=6.0, end=11.0, tag="01 · LIVE CALL", headline=["Put the call", "on *speaker*"],
          items=LIVE[:1], narration="Put any call on speaker and tap start."),
    Scene("05_safe", clip="E", start=11.0, end=16.0, tag="01 · LIVE CALL", headline=["Put the call", "on *speaker*"],
          items=LIVE[:2], narration="Gnani's speech recognition listens to every word, live."),
    Scene("06_warn", clip="E", start=16.7, end=22.6, tag="01 · LIVE CALL", headline=["It warns you", "*during* the call"],
          items=LIVE[:3], clip_audio=True, note="Spoken in an AI clone of my own voice, made with consent.",
          subtitle="“Hi, it’s me. This call is a scam. Please hang up right now.”"),
    Scene("07_after", clip="E", start=25.0, end=31.0, tag="01 · LIVE CALL", headline=["It warns you", "*during* the call"],
          items=LIVE, narration="When the call ends, it tells you exactly what to do next."),
    Scene("08_real", clip="A", start=37.0, end=45.0, tag="02 · REAL SCAMS", headline=["Real scams,", "*re-enacted*"],
          items=["Real Indian cases, with sources", "Two Gnani voices act it out"],
          narration="It also re-enacts real Indian scams in two Gnani voices, so families learn the tricks before the call comes."),
    Scene("09_practice", clip="C", start=13.0, end=18.0, tag="03 · PRACTICE", headline=["Spot the", "*scam*"],
          items=["Scam or safe? It explains why"], narration="A quick quiz trains the whole family."),
    Scene("10_help", clip="D", start=26.0, end=27.9, tag="04 · HELP", headline=["Cheated?", "*One tap.*"],
          items=["What to do, step by step"], narration="And if you were cheated, one tap shows what to do."),
    Scene("11_1930", clip="D", start=30.0, end=32.8, tag="04 · HELP", headline=["Cheated?", "*One tap.*"],
          items=["What to do, step by step", "Call 1930 · cyber crime helpline"],
          narration="Call one nine three zero, fast.", subtitle="Call 1930, fast."),
    Scene("12_end", kind="end", cards=[("24 / 24", "test scams caught"), ("0 / 36", "false alarms")],
          narration="Scam Sentinel. Twenty four out of twenty four test scams caught. Built on Gnani AI."),
]


# ---------------------------------------------------------------- drawing
def font(size: int, weight: str = "") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype({"b": FONT_B, "sb": FONT_SB}.get(weight, FONT), size)


_BG = None


def background() -> Image.Image:
    """Deep navy with a soft teal glow and a faint grid (the same on every scene, so cuts are seamless)."""
    global _BG
    if _BG is None:
        img = Image.new("RGB", (W, H))
        top, bot = Image.new("RGB", (1, H)), None
        for y in range(H):
            t = y / H
            top.putpixel((0, y), tuple(int(NAVY_TOP[i] * (1 - t) + NAVY_BOTTOM[i] * t) for i in range(3)))
        img = top.resize((W, H))
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse((-200, -500, 1100, 700), fill=90)
        ImageDraw.Draw(glow).ellipse((1300, 500, 2300, 1400), fill=50)
        glow = glow.filter(ImageFilter.GaussianBlur(220))
        img = Image.composite(Image.new("RGB", (W, H), (20, 110, 100)), img, glow)
        grid = ImageDraw.Draw(img, "RGBA")
        for x in range(0, W, 64):
            grid.line((x, 0, x, H), fill=(255, 255, 255, 7))
        for y in range(0, H, 64):
            grid.line((0, y, W, y), fill=(255, 255, 255, 7))
        _BG = img
    return _BG.copy()


def header(img: Image.Image) -> None:
    logo = Image.open(ROOT / "web/icons/icon-192.png").convert("RGBA").resize((52, 52))
    img.paste(logo, (64, 44), logo)
    ImageDraw.Draw(img).text((130, 46), "Scam Sentinel", font=font(34, "sb"), fill=WHITE)


def rich(d: ImageDraw.ImageDraw, xy, line: str, f, base=WHITE, hi=AMBER, center=False) -> None:
    plain = line.replace("*", "")
    x, y = xy
    if center:
        x = (W - d.textlength(plain, font=f)) / 2
    for part in re.split(r"(\*[^*]+\*)", line):
        if part:
            color, text = (hi, part.strip("*")) if part.startswith("*") else (base, part)
            d.text((x, y), text, font=f, fill=color)
            x += d.textlength(text, font=f)


def wrap(d, text: str, f, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= width:
            cur = trial
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def tick(d, x, y, r=17) -> None:
    d.ellipse((x, y, x + 2 * r, y + 2 * r), outline=GREEN, width=3)
    d.line((x + r * 0.55, y + r * 1.05, x + r * 0.9, y + r * 1.4, x + r * 1.5, y + r * 0.65), fill=GREEN, width=4, joint="curve")


def card(d, box, value, label, value_font, label_font) -> None:
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=22, fill=(255, 255, 255, 14), outline=(255, 255, 255, 40), width=2)
    d.text((x0 + 30, y0 + 22), value, font=value_font, fill=AMBER)
    for i, line in enumerate(wrap(d, label, label_font, x1 - x0 - 60)[:2]):
        d.text((x0 + 30, y0 + 26 + value_font.size + 14 + i * 34), line, font=label_font, fill=SOFT)


SCREEN = (330, 104, 330 + 405, 104 + 904)     # 720x1608 recording scaled to 405x904
RX = 900                                       # right column


def subtitle(d, text: str, center=False) -> None:
    if not text:
        return
    f = font(30)
    if center:
        lines = wrap(d, text, f, 1300)[:2]
        for i, line in enumerate(lines):
            d.text(((W - d.textlength(line, font=f)) / 2, 960 + i * 42), line, font=f, fill=SOFT)
    else:
        lines = wrap(d, text, f, W - RX - 90)[:3]
        y = 1012 - 42 * len(lines)
        for i, line in enumerate(lines):
            d.text((RX, y + i * 42), line, font=f, fill=SOFT)


def scene_image(s: Scene) -> tuple[Image.Image, Image.Image | None]:
    img = background()
    header(img)
    d = ImageDraw.Draw(img, "RGBA")
    if s.kind == "hook":
        f = font(108, "b")
        for i, line in enumerate(s.headline):
            rich(d, (0, 330 + i * 140), line, f, center=True)
        fn = font(36, "sb"); t = s.note.upper()
        tw = d.textlength(t, font=fn)
        d.rounded_rectangle(((W - tw) / 2 - 26, 230, (W + tw) / 2 + 26, 290), radius=30, outline=AMBER, width=2)
        d.text(((W - tw) / 2, 237), t, font=fn, fill=AMBER)
        subtitle(d, s.subtitle or s.narration, center=True)
        return img, None
    if s.kind == "stat":
        rich(d, (0, 250), s.headline[0], font(100, "b"), center=True)
        fv, fl = font(64, "b"), font(30)
        cw, gap = 560, 40
        x = (W - 2 * cw - gap) / 2
        for value, label in s.cards:
            card(d, (x, 470, x + cw, 690), value, label, fv, fl); x += cw + gap
        subtitle(d, s.subtitle or s.narration, center=True)
        return img, None
    if s.kind == "end":
        logo = Image.open(ROOT / "web/icons/icon-192.png").convert("RGBA").resize((120, 120))
        img.paste(logo, ((W - 120) // 2, 120), logo)
        rich(d, (0, 260), "*Scam Sentinel*", font(110, "b"), center=True)
        steps = [("1", "Listen", "to the call, live"), ("2", "Warn", "during the call"), ("3", "Learn", "real scams"), ("4", "Help", "one tap · 1930")]
        cw, gap = 330, 30
        x = (W - 4 * cw - 3 * gap) / 2
        for n, title, sub in steps:
            d.rounded_rectangle((x, 430, x + cw, 590), radius=22, fill=(255, 255, 255, 12), outline=(255, 255, 255, 40), width=2)
            d.ellipse((x + 26, 452, x + 70, 496), outline=AMBER, width=3)
            d.text((x + 40, 452), n, font=font(28, "b"), fill=AMBER)
            d.text((x + 26, 505), title, font=font(40, "b"), fill=WHITE)
            d.text((x + 26, 552), sub, font=font(26), fill=SOFT)
            x += cw + gap
        fv, fl = font(54, "b"), font(26)
        cw2 = 400
        x = (W - 2 * cw2 - 40) / 2
        for value, label in s.cards:
            card(d, (x, 625, x + cw2, 790), value, label, fv, fl); x += cw2 + 40
        t = "Kannada · Hindi · English   ·   Built on Gnani Prisma + Timbre"
        d.text(((W - d.textlength(t, font=font(32, "sb"))) / 2, 820), t, font=font(32, "sb"), fill=WHITE)
        t = "#GnaniAI   #GreatIndianAIInternshipChallenge"
        d.text(((W - d.textlength(t, font=font(32, "b"))) / 2, 872), t, font=font(32, "b"), fill=GREEN)
        t = "Prototype · re-enacted calls, AI voices · Real scam? Call 1930"
        d.text(((W - d.textlength(t, font=font(24))) / 2, 925), t, font=font(24), fill=DIM)
        return img, None
    # phone scene: bezel, tag, headline, checklist, subtitle
    x0, y0, x1, y1 = SCREEN
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((x0 - 10, y0 + 10, x1 + 30, y1 + 40), radius=70, fill=160)
    img.paste((0, 0, 0), (0, 0), shadow.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x0 - 16, y0 - 16, x1 + 16, y1 + 16), radius=62, fill=(14, 18, 22), outline=(90, 104, 116), width=3)
    if s.tag:
        ft = font(24, "sb"); tw = d.textlength(s.tag, font=ft)
        d.rounded_rectangle((RX, 210, RX + tw + 40, 258), radius=24, fill=(247, 181, 56, 30), outline=AMBER, width=2)
        d.text((RX + 20, 218), s.tag, font=ft, fill=AMBER)
    fh = font(92, "b")
    for i, line in enumerate(s.headline):
        rich(d, (RX, 280 + i * 112), line, fh)
    y = 540
    for i, item in enumerate(s.items):
        current = i == len(s.items) - 1
        fi = font(34, "sb" if current else "")
        if current:
            tw = d.textlength(item, font=fi)
            d.rounded_rectangle((RX - 14, y - 12, RX + tw + 80, y + 52), radius=16, fill=(247, 181, 56, 28), outline=AMBER, width=2)
            d.ellipse((RX + 6, y + 13, RX + 22, y + 29), fill=AMBER)
            d.text((RX + 46, y - 2), item, font=fi, fill=WHITE)
        else:
            tick(d, RX, y + 2)
            d.text((RX + 52, y - 2), item, font=fi, fill=SOFT)
        y += 76
    if s.note:
        d.text((RX, y + 6), s.note, font=font(26), fill=DIM)
    subtitle(d, s.subtitle or s.narration)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle(SCREEN, fill=255)
    ImageDraw.Draw(mask).rounded_rectangle(SCREEN, radius=48, fill=0)
    over = img.copy().convert("RGBA"); over.putalpha(mask)
    return img, over


# ---------------------------------------------------------------- media
FFMPEG = None


def ffmpeg() -> str:
    global FFMPEG
    if FFMPEG is None:
        import imageio_ffmpeg
        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    return FFMPEG


def run(args: list[str]) -> None:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:])


def duration(path: Path) -> float:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def voice(s: Scene, client) -> Path | None:
    if not s.narration:
        return None
    from pipeline import speak_alert
    audio, warn = speak_alert(client, s.narration, "en-IN")
    if audio is None:
        raise RuntimeError(warn)
    raw = WORK / f"{s.name}.mp3"; raw.write_bytes(audio)
    out = WORK / f"{s.name}_trim.wav"            # the voice files start and end with silence: trim both ends
    trim = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03"
    run(["-i", str(raw), "-af", f"{trim},areverse,{trim},areverse", "-ar", "48000", str(out)])
    return out


def build_scene(s: Scene, narr: Path | None) -> Path:
    """One scene, exactly as long as its sentence (+ a tiny gap): the recording speeds up or holds to fit."""
    img, over = scene_image(s)
    bg = WORK / f"{s.name}_bg.png"; img.save(bg)
    seg = (s.end - s.start) if s.clip else 0.0
    dur = (duration(narr) + GAP) if narr else max(seg, 2.0)
    out = WORK / f"{s.name}.mp4"
    args = ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(bg)]
    if s.clip:
        x0, y0, x1, y1 = SCREEN
        ovp = WORK / f"{s.name}_over.png"; over.save(ovp)
        speed = min(3.0, seg / dur) if seg > dur else 1.0
        args += ["-ss", f"{s.start}", "-t", f"{seg:.3f}", "-i", str(CLIPS / CLIP[s.clip]), "-loop", "1", "-t", f"{dur:.3f}", "-i", str(ovp)]
        vf = (f"[1:v]setpts=PTS/{speed:.4f},fps={FPS},scale={x1 - x0}:{y1 - y0},tpad=stop_mode=clone:stop_duration={dur:.3f},"
              f"trim=duration={dur:.3f},setpts=PTS-STARTPTS[ph];[0:v][ph]overlay={x0}:{y0}[a];[a][2:v]overlay=0:0,format=yuv420p[v]")
        ain = 3
    else:
        vf = "[0:v]format=yuv420p[v]"
        ain = 1
    if narr:
        args += ["-i", str(narr)]
        af = f"[{ain}:a]apad,atrim=duration={dur:.3f},aresample=48000,aformat=channel_layouts=stereo[au]"
    elif s.clip_audio:
        af = f"[1:a]volume=2.2,apad,atrim=duration={dur:.3f},afade=t=out:st={dur - 0.15:.3f}:d=0.15,aresample=48000,aformat=channel_layouts=stereo[au]"
    else:
        args += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        af = f"[{ain}:a]anull[au]"
    run([*args, "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[au]", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", str(out)])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    chars = sum(len(s.narration) for s in SCENES)
    from budget import load_rates
    print(f"narration: {chars} characters, about {chars * (load_rates().get('tts_credits_per_1k_chars') or 0) / 1000:.1f} credits "
          "if none of it is cached yet")
    if a.dry_run:
        return 0
    if a.preview:
        for s in SCENES:
            img, over = scene_image(s)
            if over is not None:
                img.paste((40, 54, 60), SCREEN); img.paste(over, (0, 0), over)
            img.save(WORK / f"preview_{s.name}.png")
        print("previews in", WORK)
        return 0
    from gnani_client import GnaniClient
    client = GnaniClient()
    parts, total = [], 0.0
    for s in SCENES:
        p = build_scene(s, voice(s, client))
        parts.append(p); total += duration(p)
        print(f"  {s.name:12} {duration(p):5.1f} s")
    listing = WORK / "list.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(OUT)])
    print(f"done: {OUT}  ({duration(OUT):.1f} s)  TTS calls: {client.stats['tts_calls']}, cache hits: {client.stats['cache_hits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
