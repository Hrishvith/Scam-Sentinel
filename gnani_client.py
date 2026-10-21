"""Thin, credit-aware wrapper around Gnani Prisma (STT) and Timbre (TTS) REST APIs.

Endpoints (from docs.gnani.ai):
  STT  POST https://api.vachana.ai/stt/v3                multipart: audio_file, language_code, format
  TTS  POST https://api.vachana.ai/api/v1/tts/inference  JSON, returns binary audio
Auth: X-API-Key-ID header.

Results are cached on disk by content hash so reruns and demo takes never burn
programme credits twice.
"""
from __future__ import annotations

import hashlib
import io
import os
import sys
import time
import wave
from pathlib import Path

import requests

from budget import Budget


def _load_dotenv(path: Path = Path(__file__).with_name(".env")) -> None:
    """Load KEY=VALUE lines from .env into os.environ (real env vars win)."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

BASE_URL = os.getenv("GNANI_BASE_URL", "https://api.vachana.ai")
STT_PATH = "/stt/v3"
TTS_PATH = "/api/v1/tts/inference"
MAX_STT_SECONDS = 60  # REST limit; ideal <= 30
RETRY_STATUS = {429, 500, 503}


class GnaniError(RuntimeError):
    """Any failure talking to the Gnani API (message is safe to show in the UI)."""


class BudgetExceeded(GnaniError):
    """The budget guard refused a call (rate unmeasured, or it would dip into the reserve)."""


def wav_duration_seconds(audio: bytes) -> float | None:
    """Duration of a WAV payload, or None if it isn't a readable WAV."""
    try:
        with wave.open(io.BytesIO(audio)) as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError):
        return None


class GnaniClient:
    def __init__(self, api_key: str | None = None, *, timeout: int = 60, max_retries: int = 3,
                 backoff: float = 1.0, cache_dir: str | Path | None = None, use_cache: bool = True,
                 budget: Budget | None = None):
        self.api_key = api_key or os.getenv("GNANI_API_KEY")
        if not self.api_key:
            raise GnaniError("No API key. Set GNANI_API_KEY or paste it in the sidebar.")
        self.timeout, self.max_retries, self.backoff = timeout, max_retries, backoff
        self.use_cache = use_cache
        self.cache_dir = Path(cache_dir or os.getenv("GNANI_CACHE_DIR", ".cache"))
        self._session = requests.Session()
        self.stats = {"stt_calls": 0, "tts_calls": 0, "cache_hits": 0}
        self.budget = budget or Budget()

    # -- internals ---------------------------------------------------------
    def _guard(self, kind: str, units: float) -> None:
        """Print the cost estimate and refuse calls the budget does not allow."""
        est = self.budget.check(kind, units)
        print(est.line(), file=sys.stderr)
        if not est.ok:
            raise BudgetExceeded(f"Budget guard: {est.reason}.")

    def _cache_file(self, kind: str, *parts: bytes | str, ext: str) -> Path:
        h = hashlib.sha256()
        for p in parts:
            h.update(p if isinstance(p, bytes) else p.encode("utf-8"))
            h.update(b"\x00")
        return self.cache_dir / f"{kind}-{h.hexdigest()[:32]}.{ext}"

    @staticmethod
    def _error_message(resp: requests.Response) -> str:
        try:
            err = resp.json().get("error", {})
            return f"{err.get('type', 'ERROR')}: {err.get('message', resp.text[:200])}"
        except Exception:
            return resp.text[:200] or f"HTTP {resp.status_code}"

    def _post(self, path: str, **kwargs) -> requests.Response:
        url = BASE_URL + path
        headers = {"X-API-Key-ID": self.api_key, **kwargs.pop("headers", {})}
        last = ""
        for attempt in range(self.max_retries):
            try:
                resp = self._session.post(url, headers=headers, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                last = str(exc)
            else:
                if resp.status_code == 200:
                    return resp
                last = f"HTTP {resp.status_code} {self._error_message(resp)}"
                if resp.status_code not in RETRY_STATUS:
                    hint = " (check API key / remaining credits)" if resp.status_code == 403 else ""
                    raise GnaniError(last + hint)
            time.sleep(self.backoff * (2 ** attempt))
        raise GnaniError(f"Gnani API unavailable after {self.max_retries} tries: {last}")

    # -- public API --------------------------------------------------------
    def transcribe(self, audio: bytes, language_code: str = "kn-IN", *, filename: str = "audio.wav",
                   itn: bool = True, bias_words: list[str] | None = None) -> str:
        """Prisma speech-to-text.

        itn=True  -> format=transcribe (numbers/currency written as digits).
        itn=False -> format=verbatim; this is the mode where word boosting (bias_words) applies.
        """
        dur = wav_duration_seconds(audio)
        if dur is not None and dur > MAX_STT_SECONDS:
            raise GnaniError(f"Audio is {dur:.0f}s; the REST endpoint accepts at most {MAX_STT_SECONDS}s.")

        fmt = "transcribe" if itn else "verbatim"
        data = {"language_code": language_code, "format": fmt}
        if bias_words and not itn:
            data["bias_list"] = ",".join(bias_words[:100])
            data["bias_score"] = "1.0"

        # Non-WAV duration is unknown locally: budget for the 60 s maximum.
        seconds = dur if dur is not None else float(MAX_STT_SECONDS)
        log = dict(language=language_code, model="prisma-stt-v3", units_estimated=dur is None)

        cache = self._cache_file("stt", audio, language_code, fmt, data.get("bias_list", ""), ext="txt")
        if self.use_cache and cache.exists():
            self.stats["cache_hits"] += 1
            self.budget.record("stt", seconds, cache_hit=True, **log)
            return cache.read_text(encoding="utf-8")

        self._guard("stt", seconds)
        resp = self._post(STT_PATH, files={"audio_file": (filename, audio)}, data=data)
        self.stats["stt_calls"] += 1
        body = resp.json()
        self.budget.record("stt", seconds, cache_hit=False, request_id=body.get("request_id"), **log)
        if not body.get("success", True) or "transcript" not in body:
            raise GnaniError(f"Unexpected STT response: {str(body)[:200]}")
        text = body["transcript"].strip()
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache.write_text(text, encoding="utf-8")
        return text

    def synthesize(self, text: str, *, language: str = "kn-IN", voice: str = "Saanvi",
                   model: str = "timbre-v2.5", speed: float = 1.0,
                   container: str = "mp3", sample_rate: int = 24000) -> bytes:
        """Timbre text-to-speech. container='mp3' (browser playback) or 'wav' (e.g. 8000 Hz telephony)."""
        if not text.strip():
            raise GnaniError("Nothing to synthesize.")
        if container not in {"mp3", "wav"}:
            raise GnaniError("container must be 'mp3' or 'wav'.")
        cache = self._cache_file("tts", text, language, voice, model, str(speed), container,
                                 str(sample_rate), ext=container)
        log = dict(language=language, model=model)
        if self.use_cache and cache.exists():
            self.stats["cache_hits"] += 1
            self.budget.record("tts", len(text), cache_hit=True, **log)
            return cache.read_bytes()

        self._guard("tts", len(text))
        audio_config = {"container": container, "sample_rate": sample_rate, "num_channels": 1}
        if container == "mp3":
            audio_config["bitrate"] = "64k"
        else:
            audio_config.update({"encoding": "linear_pcm", "sample_width": 2})
        payload = {"text": text, "voice": voice, "model": model, "language": language,
                   "speed": speed, "audio_config": audio_config}
        resp = self._post(TTS_PATH, json=payload)
        self.stats["tts_calls"] += 1
        self.budget.record("tts", len(text), cache_hit=False, **log)
        audio = resp.content
        if not audio:
            raise GnaniError("TTS returned empty audio.")
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(audio)
        return audio
