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
