"""Builds the 60-second Scam Sentinel demo video (4:5, 1080x1350) from the phone screen recordings.

Narration: a Gnani Timbre English voice (synthesized once, then served from the Gnani cache).
Layout per scene: brand header, the phone recording in a phone frame on the left, a section tag and a big
headline on the right, subtitles at the bottom. Scenes fade in and out and are joined with ffmpeg.

  python video/make_promo.py --dry-run    # what the narration would cost; makes nothing
  python video/make_promo.py              # build (narration spends ~1-2 credits the first time only)
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
W, H, FPS = 1080, 1350, 30
FONT = r"C:\Windows\Fonts\segoeui.ttf"
FONT_B = r"C:\Windows\Fonts\segoeuib.ttf"
FONT_INDIC = r"C:\Windows\Fonts\Nirmala.ttf"
FONT_INDIC_B = r"C:\Windows\Fonts\NirmalaB.ttf"
BG_TOP, BG_BOTTOM = (11, 72, 60), (6, 20, 18)
AMBER, GREEN, RED, WHITE, SOFT = (255, 196, 64), (64, 220, 150), (240, 80, 80), (255, 255, 255), (190, 214, 206)

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
    headline: list[str]              # lines; words in *stars* are highlighted
    narration: str = ""              # spoken by Gnani Timbre ("" = none)
    subtitle: str = ""               # defaults to the narration
    clip: str | None = None          # clip letter
    start: float = 0.0
    end: float = 0.0
    tag: str = ""
    note: str = ""                   # small line under the headline
    clip_audio: bool = False         # keep the recording's own sound (the spoken warning)
    card: bool = False               # full-screen text card (no phone)
    min_seconds: float = 2.5
    extra: dict = field(default_factory=dict)


SCENES = [
    Scene("01_hook", ["“This is the police.", "We’ve arrested *your son.*", "Pay *₹5 lakh.*”"], card=True,
          note="A call my uncle got. Names and numbers not shown.",
          narration="My uncle got a call. Police, they said. His son had been arrested, and he had to pay five lakh rupees."),
    Scene("02_lie", ["None of it", "was *true.*"], card=True,
          note="But nobody could warn him while the call was on.",
          narration="None of it was true. But nobody could warn him while the call was on."),
    Scene("03_built", ["So I built", "*Scam Sentinel*"], clip="B", start=0.3, end=3.0, tag="KANNADA · HINDI · ENGLISH",
          narration="So I built Scam Sentinel."),
    Scene("04_listen", ["It listens to", "the call, *live*"], clip="E", start=8.0, end=15.8, tag="01 · LIVE CALL ON SPEAKER",
          note="Gnani Prisma speech-to-text, in real time",
          narration="Put any call on speaker. Scam Sentinel listens live, with Gnani's speech recognition."),
    Scene("05_warn", ["It warns you", "*during* the call"], clip="E", start=16.0, end=23.0, tag="01 · LIVE CALL ON SPEAKER",
          note="Warning spoken in an AI clone of my own voice, made with consent.",
          subtitle="“Hi, it’s me. This call is a scam. Please hang up right now.”", clip_audio=True),
    Scene("06_real", ["Real scams,", "*re-enacted*"], clip="A", start=37.0, end=45.0, tag="02 · REAL SCAMS",
          note="Two Gnani voices act out the call. Every case has a news source.",
          narration="It also re-enacts real Indian scams in Gnani voices, so families learn the tricks."),
    Scene("07_practice", ["Spot the", "*scam*"], clip="C", start=13.0, end=18.0, tag="03 · PRACTICE",
          narration="Practise spotting them, in Kannada, Hindi or English."),
    Scene("08_help", ["Cheated?", "*One tap.*"], clip="D", start=26.0, end=27.9, tag="04 · HELP",
          narration="Cheated? One tap shows what to do."),
    Scene("09_1930", ["Call", "*1930*"], clip="D", start=30.0, end=32.8, tag="04 · HELP",
          note="India's cyber crime helpline",
          narration="Call one nine three zero, fast.", subtitle="Call 1930, fast."),
    Scene("10_end", [], card=True, narration="Scam Sentinel. Built on Gnani AI.", min_seconds=4.5,
          extra={"end": True}),
]


# ---------------------------------------------------------------- drawing
def font(size: int, bold: bool = False, indic: bool = False) -> ImageFont.FreeTypeFont:
    path = (FONT_INDIC_B if bold else FONT_INDIC) if indic else (FONT_B if bold else FONT)
    return ImageFont.truetype(path, size)


def background() -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        c = tuple(int(BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t) for i in range(3))
        for x in range(W):
            px[x, y] = c
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((-300, -400, 900, 600), fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    return Image.composite(Image.new("RGB", (W, H), (40, 160, 120)), img, glow)


def header(img: Image.Image) -> None:
    logo = Image.open(ROOT / "web/icons/icon-192.png").convert("RGBA").resize((64, 64))
    img.paste(logo, (60, 48), logo)
    ImageDraw.Draw(img).text((140, 50), "Scam Sentinel", font=font(40, True), fill=WHITE)


def rich_line(d: ImageDraw.ImageDraw, xy, line: str, f, base=WHITE, hi=AMBER) -> None:
    """Draws a line where *starred* words are highlighted."""
    x, y = xy
    for part in re.split(r"(\*[^*]+\*)", line):
        if not part:
            continue
        color, text = (hi, part.strip("*")) if part.startswith("*") else (base, part)
        d.text((x, y), text, font=f, fill=color)
        x += d.textlength(text, font=f)


def wrap(d, text: str, f, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= width:
            cur = trial
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def subtitles(img: Image.Image, text: str) -> None:
    if not text:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = font(34, True)
    lines = wrap(d, text, f, W - 160)[:3]
    h = 50 * len(lines) + 30
    y0 = H - 60 - h
    d.rounded_rectangle((60, y0, W - 60, y0 + h), radius=22, fill=(0, 0, 0, 150))
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=f)
        d.text(((W - tw) / 2, y0 + 15 + 50 * i), line, font=f, fill=WHITE)


PHONE = (64, 176, 64 + 424, 176 + 948)   # x0, y0, x1, y1 of the screen area (720x1608 scaled to 424x948)


def scene_image(s: Scene) -> tuple[Image.Image, Image.Image | None]:
    """The still parts of a scene, and (for phone scenes) a frame overlay that rounds the recording's corners."""
    img = background()
    header(img)
    d = ImageDraw.Draw(img, "RGBA")
    if s.extra.get("end"):
        logo = Image.open(ROOT / "web/icons/icon-192.png").convert("RGBA").resize((200, 200))
        img.paste(logo, ((W - 200) // 2, 230), logo)
        f = font(92, True); t = "Scam Sentinel"
        d.text(((W - d.textlength(t, font=f)) / 2, 460), t, font=f, fill=WHITE)
        f2 = font(44, True); t2 = "Warns you DURING a scam call"
        d.text(((W - d.textlength(t2, font=f2)) / 2, 590), t2, font=f2, fill=AMBER)
        chips, fx = ["Kannada", "Hindi", "English"], font(40, True)   # Pillow cannot shape Indic scripts
        widths = [d.textlength(c, font=fx) + 60 for c in chips]
        x = (W - sum(widths) - 24 * 2) / 2
        for c, cw in zip(chips, widths):
            d.rounded_rectangle((x, 690, x + cw, 760), radius=35, outline=GREEN, width=3)
            d.text((x + 30, 698), c, font=fx, fill=WHITE)
            x += cw + 24
        f3 = font(36); t3 = "Built on Gnani Prisma + Timbre"
        d.text(((W - d.textlength(t3, font=f3)) / 2, 820), t3, font=f3, fill=SOFT)
        f4 = font(34, True); t4 = "#GnaniAI  #GreatIndianAIInternshipChallenge"
        d.text(((W - d.textlength(t4, font=f4)) / 2, 900), t4, font=f4, fill=GREEN)
        f5 = font(28); t5 = "Prototype · re-enacted calls, AI voices · Real scam? Call 1930"
        d.text(((W - d.textlength(t5, font=f5)) / 2, 1000), t5, font=f5, fill=SOFT)
        subtitles(img, s.subtitle or s.narration)
        return img, None
    if s.card:
        f = font(86, True)
        y = 380 if len(s.headline) > 2 else 470
        for line in s.headline:
            plain = line.replace("*", "")
            rich_line(d, ((W - d.textlength(plain, font=f)) / 2, y), line, f)
            y += 110
        if s.note:
            fn = font(36)
            for line in wrap(d, s.note, fn, W - 200):
                d.text(((W - d.textlength(line, font=fn)) / 2, y + 40), line, font=fn, fill=SOFT); y += 50
        subtitles(img, s.subtitle or s.narration)
        return img, None
    # phone scene: frame + right column
    x0, y0, x1, y1 = PHONE
    d.rounded_rectangle((x0 - 14, y0 - 14, x1 + 14, y1 + 14), radius=64, fill=(8, 12, 11), outline=(70, 90, 84), width=3)
    rx = 545
    if s.tag:
        ft = font(24, True)
        tw = d.textlength(s.tag, font=ft)
        d.rounded_rectangle((rx, 330, rx + tw + 36, 378), radius=24, outline=AMBER, width=2)
        d.text((rx + 18, 338), s.tag, font=ft, fill=AMBER)
    fh = font(64, True)
    y = 410
    for line in s.headline:
        rich_line(d, (rx, y), line, fh)
        y += 84
    if s.note:
        fn = font(30)
        for line in wrap(d, s.note, fn, W - rx - 50):
            d.text((rx, y + 24), line, font=fn, fill=SOFT); y += 42
    subtitles(img, s.subtitle or s.narration)
    # overlay that paints the rounded corners of the screen over the recording
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle((x0, y0, x1, y1), fill=255)
    ImageDraw.Draw(mask).rounded_rectangle((x0, y0, x1, y1), radius=50, fill=0)
    over = img.copy().convert("RGBA")
    over.putalpha(mask)
    return img, over


# ---------------------------------------------------------------- audio
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


def narration(s: Scene, client) -> Path | None:
    if not s.narration:
        return None
    from pipeline import speak_alert
    out = WORK / f"{s.name}.mp3"
    audio, warn = speak_alert(client, s.narration, "en-IN")
    if audio is None:
        raise RuntimeError(warn)
    out.write_bytes(audio)
    return out


# ---------------------------------------------------------------- build
def build_scene(s: Scene, voice: Path | None) -> Path:
    img, over = scene_image(s)
    bg = WORK / f"{s.name}_bg.png"; img.save(bg)
    lead = 0.25
    seg = (s.end - s.start) if s.clip else 0
    dur = max(s.min_seconds, seg, (duration(voice) + lead + 0.45) if voice else 0)
    out = WORK / f"{s.name}.mp4"
    fade = f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.25:.2f}:d=0.25"
    args = ["-loop", "1", "-t", f"{dur:.2f}", "-i", str(bg)]
    if s.clip:
        x0, y0, x1, y1 = PHONE
        ovp = WORK / f"{s.name}_over.png"; over.save(ovp)
        args += ["-ss", f"{s.start}", "-t", f"{seg:.2f}", "-i", str(CLIPS / CLIP[s.clip]), "-loop", "1", "-t", f"{dur:.2f}", "-i", str(ovp)]
        vf = (f"[1:v]fps={FPS},scale={x1 - x0}:{y1 - y0},tpad=stop_mode=clone:stop_duration={dur:.2f},trim=duration={dur:.2f},setpts=PTS-STARTPTS[ph];"
              f"[0:v][ph]overlay={x0}:{y0}[a];[a][2:v]overlay=0:0,{fade},format=yuv420p[v]")
        audio_in = 3
    else:
        vf = f"[0:v]{fade},format=yuv420p[v]"
        audio_in = 1
    if voice:
        args += ["-i", str(voice)]
        af = f"[{audio_in}:a]adelay={int(lead * 1000)}|{int(lead * 1000)},apad,atrim=duration={dur:.2f},aresample=48000,aformat=channel_layouts=stereo[au]"
    elif s.clip_audio:
        af = f"[1:a]volume=2.2,apad,atrim=duration={dur:.2f},afade=t=out:st={dur - 0.3:.2f}:d=0.3,aresample=48000,aformat=channel_layouts=stereo[au]"
    else:
        args += ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
        af = f"[{audio_in}:a]anull[au]"
    run([*args, "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[au]", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-t", f"{dur:.2f}", str(out)])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    chars = sum(len(s.narration) for s in SCENES)
    from budget import load_rates
    print(f"narration: {chars} characters, about {chars * (load_rates().get('tts_credits_per_1k_chars') or 0) / 1000:.1f} credits "
          "the first time (cached after)")
    if args.dry_run:
        return 0
    from gnani_client import GnaniClient
    WORK.mkdir(parents=True, exist_ok=True)
    client = GnaniClient()
    parts = []
    for s in SCENES:
        voice = narration(s, client)
        parts.append(build_scene(s, voice))
        print(f"  {s.name:12} {duration(parts[-1]):5.1f} s")
    listing = WORK / "list.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(OUT)])
    print(f"done: {OUT}  ({duration(OUT):.1f} s)  TTS calls: {client.stats['tts_calls']}, cache hits: {client.stats['cache_hits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
