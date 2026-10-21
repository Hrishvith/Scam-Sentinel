"""WAV helpers: split a call into <=25 s chunks, convert other formats if ffmpeg exists, add phone-line noise."""
from __future__ import annotations

import array
import io
import random
import shutil
import subprocess
import wave


def split_wav(audio: bytes, chunk_seconds: float = 25.0) -> list[tuple[float, bytes]]:
    """Split WAV audio into (start_second, wav_bytes) chunks. Non-WAV input is returned whole."""
    try:
        src = wave.open(io.BytesIO(audio))
    except (wave.Error, EOFError):
        return [(0.0, audio)]
    with src:
        rate, width, channels = src.getframerate(), src.getsampwidth(), src.getnchannels()
        per_chunk = max(1, int(rate * chunk_seconds))
        chunks, start = [], 0
        while True:
            frames = src.readframes(per_chunk)
            if not frames:
                break
            buf = io.BytesIO()
            with wave.open(buf, "wb") as out:
                out.setnchannels(channels), out.setsampwidth(width), out.setframerate(rate)
                out.writeframes(frames)
            chunks.append((start / rate, buf.getvalue()))
            start += per_chunk
    return chunks or [(0.0, audio)]


def ensure_wav(audio: bytes, filename: str = "") -> bytes:
    """Return WAV bytes. Other formats are converted with ffmpeg if available, else returned unchanged."""
    try:
        wave.open(io.BytesIO(audio)).close()
        return audio
    except (wave.Error, EOFError):
        pass
    if shutil.which("ffmpeg"):
        proc = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "16000",
                               "-f", "wav", "pipe:1"], input=audio, capture_output=True)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    return audio


def concat_wavs(parts: list[bytes], pause_seconds: float = 0.4) -> bytes:
    """Concatenate same-format WAVs with short silences between them."""
    out = io.BytesIO()
    writer = None
    for data in parts:
        with wave.open(io.BytesIO(data)) as w:
            if writer is None:
                writer = wave.open(out, "wb")
                writer.setnchannels(w.getnchannels()), writer.setsampwidth(w.getsampwidth())
                writer.setframerate(w.getframerate())
                silence = b"\x00" * int(w.getframerate() * pause_seconds) * w.getsampwidth() * w.getnchannels()
            writer.writeframes(w.readframes(w.getnframes()))
            writer.writeframes(silence)
    if writer is None:
        raise ValueError("No audio to concatenate")
    writer.close()
    return out.getvalue()


def split_on_pauses(wav: bytes, max_seconds: float = 12.0, min_pause: float = 0.4,
                    window: float = 0.05) -> list[tuple[float, bytes]]:
    """Split WAV audio at natural pauses into (start_second, wav_bytes) utterances.

    Prisma's REST endpoint (seen with kn-IN) can return only the first sentence of a longer
    clip, while one utterance per request comes back complete. Quiet is judged against the
    clip's own noise floor, so noisy lines still split at pauses. Segments with no speech are
    dropped (never billed); anything longer than `max_seconds` is cut evenly. Audio with no
    usable level contrast (or non-16-bit / multi-channel WAV) falls back to split_wav.
    """
    try:
        src = wave.open(io.BytesIO(wav))
    except (wave.Error, EOFError):
        return [(0.0, wav)]
    with src:
        channels, width, rate = src.getnchannels(), src.getsampwidth(), src.getframerate()
        if channels != 1 or width != 2:
            return split_wav(wav, max_seconds)
        samples = array.array("h", src.readframes(src.getnframes()))
    step = max(1, int(rate * window))
    rms = [(sum(s * s for s in samples[i:i + step]) / len(samples[i:i + step])) ** 0.5
           for i in range(0, len(samples), step)]
    ordered = sorted(rms)
    floor, loud = (ordered[len(ordered) // 10], ordered[int(len(ordered) * 0.9)]) if rms else (0, 0)
    if loud < 500:  # no speech-level contrast to work with
        return split_wav(wav, max_seconds)
    quiet = [level < floor + 0.1 * (loud - floor) for level in rms]

    need = max(1, round(min_pause / window))
    cuts, run_start = [0], None
    for i, q in enumerate(quiet + [False]):
        if q and run_start is None:
            run_start = i
        elif not q and run_start is not None:
            if i - run_start >= need:
                cuts.append((run_start + i) // 2)
            run_start = None
    cuts.append(len(rms))

    max_windows = max(1, int(max_seconds / window))
    out = []
    for a, b in zip(cuts, cuts[1:]):
        while a < b:
            end = min(b, a + max_windows)
            if sum(not q for q in quiet[a:end]) >= 3:  # at least ~0.15 s of speech
                buf = io.BytesIO()
                with wave.open(buf, "wb") as o:
                    o.setnchannels(1), o.setsampwidth(2), o.setframerate(rate)
                    o.writeframes(samples[a * step:end * step].tobytes())
                out.append((a * step / rate, buf.getvalue()))
            a = end
    return out or [(0.0, wav)]


def add_noise(wav: bytes, amplitude: int = 400, seed: int = 7) -> bytes:
    """Mix low-level white noise into 16-bit mono/stereo WAV to mimic a poor phone line."""
    rng = random.Random(seed)
    with wave.open(io.BytesIO(wav)) as w:
        params = (w.getnchannels(), w.getsampwidth(), w.getframerate())
        if params[1] != 2:
            raise ValueError("add_noise supports 16-bit audio only")
        samples = array.array("h", w.readframes(w.getnframes()))
    for i, s in enumerate(samples):
        samples[i] = max(-32768, min(32767, s + int(rng.gauss(0, amplitude))))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(params[0]), out.setsampwidth(params[1]), out.setframerate(params[2])
        out.writeframes(samples.tobytes())
    return buf.getvalue()
