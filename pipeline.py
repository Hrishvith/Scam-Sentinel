"""Call audio -> Prisma STT (chunked) -> cumulative scam risk -> spoken Timbre alert."""
from __future__ import annotations

from dataclasses import dataclass, field

from alerts import alert_text
from audio_utils import ensure_wav, split_wav
from detector import Detection, detect
from gnani_client import BudgetExceeded, GnaniClient, GnaniError
from tactics import BIAS_WORDS

ALERT_VOICES = [("timbre-v3.0", "Chetana"), ("timbre-v2.5", {"kn-IN": "Saanvi", "hi-IN": "Nalini",
                                                            "en-IN": "Kaveri"})]


@dataclass
class ChunkResult:
    index: int
    start: float
    text: str
    score: float          # cumulative score after this chunk
    level: str
    new_tactics: list[str]


@dataclass
class CallAnalysis:
    chunks: list[ChunkResult]
    final: Detection
    transcript: str
    alert_text: str
    alert_audio: bytes | None = None
    warnings: list[str] = field(default_factory=list)


def analyze_texts(texts: list[str], starts: list[float] | None = None) -> tuple[list[ChunkResult], Detection]:
    """Cumulative analysis: each point is the risk of everything heard so far (shows escalation)."""
    starts = starts or [0.0] * len(texts)
    seen: set[str] = set()
    results: list[ChunkResult] = []
    det = Detection()
    for i, text in enumerate(texts):
        det = detect(" ".join(texts[: i + 1]), use_llm=False)  # LLM only runs once, on the full call
        new = [t for t in det.tactics if t not in seen]
        seen.update(det.tactics)
        results.append(ChunkResult(i, starts[i], text, det.score, det.level, new))
    return results, det


def speak_alert(client: GnaniClient, text: str, lang: str) -> tuple[bytes | None, str | None]:
    """Try Timbre v3.0 first, fall back to v2.5 (Timbre is beta)."""
    last = None
    for model, voice in ALERT_VOICES:
        voice_name = voice if isinstance(voice, str) else voice.get(lang, "Kaveri")
        try:
            return client.synthesize(text, language=lang, voice=voice_name, model=model), None
        except BudgetExceeded as exc:
            return None, f"Spoken alert skipped, showing text only ({exc})"
        except GnaniError as exc:
            last = str(exc)
    return None, f"Spoken alert unavailable, showing text only ({last})"


def analyze_transcripts(texts: list[str], lang: str, client: GnaniClient | None = None,
                        speak: bool = True) -> CallAnalysis:
    """Same as analyze_call but from text (no STT credits). Useful for testing and the 'paste a script' mode."""
    chunks, _ = analyze_texts(texts)
    full = " ".join(texts)
    final = detect(full)  # may add the optional Evon second opinion
    return _finish(chunks, final, full, lang, client, speak)


def analyze_call(audio: bytes, lang: str, client: GnaniClient, *, filename: str = "call.wav",
                 chunk_seconds: float = 25.0, speak: bool = True) -> CallAnalysis:
    wav = ensure_wav(audio, filename)
    parts = split_wav(wav, chunk_seconds)
    texts, starts, warnings = [], [], []
    for start, data in parts:
        try:
            # verbatim + word boosting: favours the scam keywords that matter, not currency formatting
            text = client.transcribe(data, lang, filename="chunk.wav", itn=False, bias_words=BIAS_WORDS)
        except BudgetExceeded:
            raise  # stop at once; the remaining chunks would be refused too
        except GnaniError as exc:
            warnings.append(f"Chunk at {start:.0f}s skipped: {exc}")
            text = ""
        texts.append(text)
        starts.append(start)
    if not any(texts):
        raise GnaniError("No speech could be transcribed. Try a clearer or shorter recording.")

    chunks, _ = analyze_texts(texts, starts)
    full = " ".join(t for t in texts if t)
    final = detect(full)
    result = _finish(chunks, final, full, lang, client, speak)
    result.warnings = warnings + result.warnings
    return result


def _finish(chunks, final, full, lang, client, speak) -> CallAnalysis:
    text = alert_text(lang, final)
    res = CallAnalysis(chunks, final, full, text)
    if speak and client is not None and final.level != "low":
        res.alert_audio, warn = speak_alert(client, text, lang)
        if warn:
            res.warnings.append(warn)
    return res
