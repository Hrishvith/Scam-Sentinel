"""Live mode: stream a call to Gnani Prisma realtime STT and warn while it is still going on.

  python live.py --lang kn-IN                     # microphone, 16 kHz, stops after --max-seconds (300)
  python live.py --lang hi-IN --rate 8000         # mimic a phone line
  python live.py --lang kn-IN --file demo_calls/corpus/kn_scam_kyc_noisy.wav --play

SPENDS CREDITS: every second streamed (silence included) counts as realtime STT. --max-seconds
caps a session and the budget guard checks that cap before connecting.

Protocol (docs.gnani.ai/api/STT/stt-websocket.md): wss://api.vachana.ai/stt/v3/stream, config in
upgrade headers, raw s16le mono PCM in frames of exactly 1024 bytes at real-time cadence. The
server cuts utterances with its own VAD and replies with connected / processing / transcript /
error JSON messages. Sessions are capped at 15 minutes, so we reconnect at 14. There is no
documented end-of-stream message: we send a little silence so the last utterance is closed,
wait for its transcript, then close the socket.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sys
import threading
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Callable

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from alerts import HELPLINE, alert_text, top_reasons
from budget import Budget
from detector import Detection, detect_rules
from gnani_client import BudgetExceeded, GnaniClient, GnaniError
from pipeline import speak_alert
from tactics import BIAS_WORDS

WS_URL = os.getenv("GNANI_STT_WS_URL", "wss://api.vachana.ai/stt/v3/stream")
SESSIONS_DIR = Path(__file__).resolve().parent / "data" / "live_sessions"   # local only, gitignored
FRAME_BYTES = 1024                  # exactly 512 samples of s16le mono (docs)
RATES = (8000, 16000, 44100, 48000)
RECONNECT_AFTER_S = 14 * 60         # the server caps a session at 15 minutes
LEVELS = ["low", "medium", "high"]


def frame_seconds(rate: int) -> float:
    return FRAME_BYTES / 2 / rate


@dataclass
class LiveEvent:
    kind: str                        # info | connected | transcript | alert | error | done
    data: dict = field(default_factory=dict)


class RiskTracker:
    """Cumulative risk over everything heard so far; reports a level the first time it is reached."""

    def __init__(self) -> None:
        self.texts: list[str] = []
        self.det = Detection()
        self.first_at: dict[str, float] = {}   # level -> seconds of audio when it was first reached

    def add(self, text: str, at: float) -> str | None:
        if text.strip():
            self.texts.append(text.strip())
        self.det = detect_rules(" ".join(self.texts))
        new = None
        for level in ("medium", "high"):
            if LEVELS.index(self.det.level) >= LEVELS.index(level) and level not in self.first_at:
                self.first_at[level] = at
                new = level      # a jump straight to high reports high only
        return new


# ---- audio sources: async iterators of exact 1024-byte frames ------------------------------
def to_frames(pcm: bytes) -> list[bytes]:
    frames = [pcm[i:i + FRAME_BYTES] for i in range(0, len(pcm), FRAME_BYTES)]
    if frames and len(frames[-1]) < FRAME_BYTES:
        frames[-1] = frames[-1].ljust(FRAME_BYTES, b"\0")
    return frames


def read_wav_pcm(path: str) -> tuple[int, bytes]:
    with wave.open(str(path)) as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("Live mode needs a 16-bit mono WAV.")
        if w.getframerate() not in RATES:
            raise ValueError(f"Sample rate {w.getframerate()} not supported; use one of {RATES}.")
        return w.getframerate(), w.readframes(w.getnframes())


async def file_frames(pcm: bytes, rate: int, *, pace: bool = True) -> AsyncIterator[bytes]:
    """Frames of a recording, sent at real-time cadence (bursting degrades the server's VAD)."""
    start, dt = time.monotonic(), frame_seconds(rate)
    for i, frame in enumerate(to_frames(pcm)):
        if pace:
            delay = start + i * dt - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
        yield frame


async def mic_frames(rate: int, stop: threading.Event) -> AsyncIterator[bytes]:
    """Microphone frames until `stop` is set (real-time by nature)."""
    import sounddevice as sd

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[bytes] = asyncio.Queue()

    def callback(indata, frames, t, status):  # runs on the audio thread
        loop.call_soon_threadsafe(queue.put_nowait, bytes(indata))

    buf = b""
    with sd.RawInputStream(samplerate=rate, channels=1, dtype="int16", blocksize=FRAME_BYTES // 2,
                           callback=callback):
        while not stop.is_set():
            try:
                buf += await asyncio.wait_for(queue.get(), 0.5)
            except asyncio.TimeoutError:
                continue
            while len(buf) >= FRAME_BYTES:
                yield buf[:FRAME_BYTES]
                buf = buf[FRAME_BYTES:]


# ---- the streaming session -----------------------------------------------------------------
class LiveSession:
    def __init__(self, api_key: str, lang: str, rate: int = 16000, *,
                 on_event: Callable[[LiveEvent], None] = lambda e: None,
                 on_alert: Callable[[str, Detection], None] | None = None,
                 max_seconds: float = 300.0, url: str = WS_URL, reconnect_after: float = RECONNECT_AFTER_S,
                 bias_words: list[str] | None = BIAS_WORDS, budget: Budget | None = None,
                 stop: threading.Event | None = None, pace: bool = True,
                 flush_seconds: float = 1.2, drain_timeout: float = 6.0, settle_seconds: float = 0.8,
                 max_reconnects: int = 3, save_dir: Path | None = SESSIONS_DIR, source_name: str = "microphone"):
        if rate not in RATES:
            raise ValueError(f"rate must be one of {RATES}")
        self.api_key, self.lang, self.rate, self.url = api_key, lang, rate, url
        self.on_event, self.on_alert = on_event, on_alert
        self.max_seconds, self.reconnect_after, self.bias_words = max_seconds, reconnect_after, bias_words
        self.budget = budget or Budget()
        self.stop = stop or threading.Event()
        self.pace, self.flush_seconds, self.drain_timeout = pace, flush_seconds, drain_timeout
        self.settle_seconds = settle_seconds
        self.max_reconnects = max_reconnects
        self.save_dir, self.source_name = save_dir, source_name
        self.dt = frame_seconds(rate)
        self.muted = threading.Event()       # set while our own warning plays: send silence instead
        self.tracker = RiskTracker()
        self.sent_s = 0.0                     # audio seconds streamed (the billing unit we assume)
        self.segments: list[dict] = []
        self.connections = 0
        self._pending = 0
        self._last_msg = 0.0

    def headers(self) -> dict[str, str]:
        h = {"x-api-key-id": self.api_key, "lang_code": self.lang, "x-sample-rate": str(self.rate),
             "x-format": "verbatim"}
        if self.bias_words:
            h["x-bias-list"] = ",".join(self.bias_words[:100])
            h["x-bias-score"] = "1.0"
        return h

    def _emit(self, kind: str, **data) -> None:
        self.on_event(LiveEvent(kind, data))

    async def run(self, frames: AsyncIterator[bytes]) -> dict:
        est = self.budget.check("stt_stream", self.max_seconds)
        self._emit("info", message=est.line())
        if not est.ok:
            raise BudgetExceeded(f"Budget guard: {est.reason}.")
        it, failures, finished = frames.__aiter__(), 0, False
        while not finished:
            before = self.sent_s
            try:
                finished = await self._one_connection(it)
            except (ConnectionClosed, OSError, asyncio.TimeoutError, ConnectionError) as exc:
                failures = 0 if self.sent_s > before + 5 else failures + 1
                self._emit("error", message=f"Connection lost ({type(exc).__name__}: {exc}); reconnecting.")
                if failures > self.max_reconnects:
                    self._emit("error", message="Giving up after repeated connection failures.")
                    break
                await asyncio.sleep(min(2 ** failures, 8) if self.pace else 0)
        summary = self.summary()
        if self.save_dir and self.segments:
            summary["saved_to"] = str(self._save(summary))
        self._emit("done", **summary)
        return summary

    def _save(self, summary: dict) -> Path:
        """Keep what was heard (text only, never audio) so a surprising alert can be explained later."""
        self.save_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self.save_dir / f"{stamp}_{self.lang}_{Path(self.source_name).stem}.json"
        record = {"lang": self.lang, "source": self.source_name, "sample_rate": self.rate,
                  **{k: v for k, v in summary.items() if k not in ("transcript", "segments")},
                  "segments": self.segments}
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    async def _one_connection(self, it) -> bool:
        """Stream until the source ends (True) or it is time for a fresh session (False)."""
        self.connections += 1
        start_s, speech_ms, self._pending = self.sent_s, [0], 0
        try:
            async with connect(self.url, additional_headers=self.headers(), open_timeout=10,
                               max_size=2 ** 20) as ws:
                first = json.loads(await asyncio.wait_for(ws.recv(), 10))
                if first.get("type") != "connected":
                    raise ConnectionError(f"expected 'connected', got {first.get('type')}: "
                                          f"{first.get('message', '')}")
                self._emit("connected", session=self.connections, config=first.get("config", {}))
                receiver = asyncio.create_task(self._receive(ws, speech_ms))
                try:
                    finished = await self._send(ws, it, start_s, receiver)
                    await self._flush(ws, receiver)
                    if receiver.done() and not receiver.cancelled():
                        exc = receiver.exception()
                        if isinstance(exc, ConnectionClosed) and not isinstance(exc, ConnectionClosedOK):
                            raise exc            # dropped mid-flush: reconnect instead of ending quietly
                finally:
                    receiver.cancel()
                    with contextlib.suppress(asyncio.CancelledError, ConnectionClosed):
                        await receiver
                return finished
        finally:
            streamed = self.sent_s - start_s
            if streamed > 0:
                self.budget.record("stt_stream", streamed, language=self.lang, model="prisma-stt-v3-stream",
                                   cache_hit=False, speech_seconds=round(speech_ms[0] / 1000, 2),
                                   sample_rate=self.rate)

    async def _send(self, ws, it, start_s: float, receiver: asyncio.Task) -> bool:
        while True:
            if receiver.done():
                receiver.result()             # re-raise ConnectionClosed from the receiver
            if self.stop.is_set():
                return True
            if self.sent_s >= self.max_seconds:
                self._emit("info", message=f"Reached --max-seconds ({self.max_seconds:.0f} s); stopping.")
                return True
            if self.sent_s - start_s >= self.reconnect_after:
                self._emit("info", message="Opening a fresh session before the 15-minute cap.")
                return False
            try:
                frame = await it.__anext__()
            except StopAsyncIteration:
                return True
            if len(frame) != FRAME_BYTES:
                raise ValueError(f"frame of {len(frame)} bytes; the server needs exactly {FRAME_BYTES}")
            await ws.send(bytes(FRAME_BYTES) if self.muted.is_set() else frame)
            self.sent_s += self.dt

    async def _flush(self, ws, receiver: asyncio.Task) -> None:
        """Send a little silence so the server's VAD closes the last utterance, then wait for it."""
        silence = bytes(FRAME_BYTES)
        for _ in range(int(self.flush_seconds / self.dt)):
            if receiver.done():
                return
            await ws.send(silence)
            self.sent_s += self.dt
            if self.pace:
                await asyncio.sleep(self.dt)
        deadline = time.monotonic() + self.drain_timeout
        self._last_msg = max(self._last_msg, time.monotonic())  # give the server time to answer
        while time.monotonic() < deadline and not receiver.done():
            if self._pending == 0 and time.monotonic() - self._last_msg > self.settle_seconds:
                break
            await asyncio.sleep(0.05)

    async def _receive(self, ws, speech_ms: list[int]) -> None:
        async for raw in ws:
            if isinstance(raw, bytes):
                continue
            msg = json.loads(raw)
            self._last_msg = time.monotonic()
            kind = msg.get("type")
            if kind == "processing":
                self._pending += 1
            elif kind == "transcript":
                self._pending = max(0, self._pending - 1)
                speech_ms[0] += int(msg.get("audio_duration_ms") or 0)
                self._on_transcript(msg)
            elif kind == "error":
                self._emit("error", message=str(msg.get("message", "unknown error")))

    def _on_transcript(self, msg: dict) -> None:
        text, at = (msg.get("text") or "").strip(), round(self.sent_s, 2)
        new = self.tracker.add(text, at)
        det = self.tracker.det
        self.segments.append({"at": at, "text": text, "level": det.level, "score": round(det.score, 2),
                              "tactics": sorted(det.tactics), "latency_ms": msg.get("latency"),
                              "audio_ms": msg.get("audio_duration_ms")})
        self._emit("transcript", text=text, at=at, level=det.level, score=round(det.score, 2),
                   tactics=sorted(det.tactics), latency_ms=msg.get("latency"))
        if new:
            self._emit("alert", level=new, at=at, message=alert_text(self.lang, det),
                       reasons=top_reasons(self.lang, det))
            if self.on_alert:
                self.on_alert(new, det)

    def summary(self) -> dict:
        det = self.tracker.det
        return {"seconds_streamed": round(self.sent_s, 1), "connections": self.connections,
                "segments": len(self.segments), "level": det.level, "score": round(det.score, 2),
                "tactics": sorted(det.tactics), "time_to_alert": dict(self.tracker.first_at),
                "transcript": " ".join(self.tracker.texts)}


# ---- spoken warning --------------------------------------------------------------------------
class AlertPlayer:
    """Speaks the warning on the PC speakers. Both warnings are synthesized (and cached) up front,
    so an alert plays instantly.

    `mute_session`: only for a microphone on open speakers, where the mic would hear the warning
    itself. It also drops whatever the caller says meanwhile, so never use it for a file stream
    (no echo possible) or with headphones.
    """

    def __init__(self, client: GnaniClient, lang: str, session: LiveSession | None = None,
                 mute_session: bool = False):
        self.client, self.lang, self.session, self.mute_session = client, lang, session, mute_session
        self.audio: dict[str, bytes] = {}
        self._threads: list[threading.Thread] = []

    def prepare(self) -> list[str]:
        warnings = []
        for level in ("medium", "high"):
            audio, warn = speak_alert(self.client, alert_text(self.lang, Detection(level=level)), self.lang,
                                      container="wav", sample_rate=16000)
            if audio:
                self.audio[level] = audio
            if warn:
                warnings.append(warn)
        return warnings

    def __call__(self, level: str, det: Detection) -> None:
        # Called on the event loop: never block here. Each warning waits for the previous one in
        # its own thread, so warnings never talk over each other and streaming never stalls.
        if level in self.audio:
            prev = self._threads[-1] if self._threads else None
            thread = threading.Thread(target=self._play_after, args=(prev, self.audio[level]), daemon=True)
            self._threads.append(thread)
            thread.start()

    def _play_after(self, prev: threading.Thread | None, audio: bytes) -> None:
        if prev:
            prev.join()
        self._play(audio)

    def wait(self) -> None:
        """Block until every warning has finished playing (the CLI would otherwise cut it off)."""
        for t in self._threads:
            t.join()

    def _play(self, audio: bytes) -> None:
        import winsound

        mute = self.session if self.mute_session else None
        if mute:
            mute.muted.set()
        try:
            winsound.PlaySound(audio, winsound.SND_MEMORY)
        finally:
            if mute:
                time.sleep(0.3)
                mute.muted.clear()


# ---- command line --------------------------------------------------------------------------
def print_event(e: LiveEvent) -> None:
    d = e.data
    if e.kind == "transcript":
        bar = "#" * min(20, int(d["score"] * 2))
        print(f"[{d['at']:6.1f}s] {d['level']:<6} {d['score']:5.1f} |{bar:<20}| {d['text']}")
    elif e.kind == "alert":
        print(f"\n!!! {d['level'].upper()} RISK at {d['at']:.1f} s of audio: {d['message']}")
        for r in d["reasons"]:
            print(f"    - {r}")
        print()
    elif e.kind == "connected":
        print(f"connected (session {d['session']}, {d['config']})")
    elif e.kind in ("info", "error"):
        print(f"{e.kind}: {d['message']}", file=sys.stderr)
    elif e.kind == "done":
        print(f"\nDone: {d['seconds_streamed']} s streamed over {d['connections']} session(s), "
              f"{d['segments']} segments, final {d['level']} ({d['score']}).")
        for level, at in d["time_to_alert"].items():
            print(f"  time to {level} alert: {at:.1f} s")
        if d["level"] == "high":
            print(f"  Hang up and call {HELPLINE} (national cyber crime helpline).")
        if d.get("saved_to"):
            print(f"  transcript saved to {d['saved_to']}")


async def _main(args) -> None:
    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        raise SystemExit("Set GNANI_API_KEY (or put it in .env).")
    stop = threading.Event()
    rate = args.rate
    pcm = None
    if args.file:
        rate, pcm = read_wav_pcm(args.file)
    session = LiveSession(api_key, args.lang, rate, on_event=print_event, max_seconds=args.max_seconds,
                          stop=stop, source_name=args.file or "microphone")
    player = None
    if args.speak:
        player = AlertPlayer(GnaniClient(api_key), args.lang, session,
                             mute_session=pcm is None and not args.headphones)
        for w in player.prepare():
            print(w, file=sys.stderr)
        session.on_alert = player
    if pcm is not None:
        if args.play:
            import numpy as np
            import sounddevice as sd
            sd.play(np.frombuffer(pcm, dtype=np.int16), rate)
        source = file_frames(pcm, rate)
        print(f"Streaming {args.file} ({len(pcm) / 2 / rate:.1f} s, SIMULATED call). Ctrl+C to stop.")
    else:
        source = mic_frames(rate, stop)
        print(f"Listening on the microphone at {rate} Hz for up to {args.max_seconds:.0f} s. Ctrl+C to stop.")
    try:
        await session.run(source)
    except asyncio.CancelledError:
        stop.set()
    if player:
        await asyncio.to_thread(player.wait)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="kn-IN", help="kn-IN, hi-IN, en-IN (en-IN also covers Hinglish)")
    ap.add_argument("--rate", type=int, default=16000, choices=RATES, help="microphone sample rate")
    ap.add_argument("--file", help="stream a 16-bit mono WAV instead of the microphone")
    ap.add_argument("--play", action="store_true", help="play the --file aloud while streaming it")
    ap.add_argument("--max-seconds", type=float, default=300.0, help="hard cap on streamed audio")
    ap.add_argument("--no-speak", dest="speak", action="store_false", help="text alerts only (no TTS)")
    ap.add_argument("--headphones", action="store_true",
                    help="keep listening while the warning plays (no speaker echo to block)")
    args = ap.parse_args(argv)
    try:
        asyncio.run(_main(args))
    except KeyboardInterrupt:
        print("\nStopped.")
    except (GnaniError, ValueError) as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
