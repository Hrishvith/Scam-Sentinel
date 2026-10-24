"""Protected calling line: a real call between two phones, with Scam Sentinel sitting in the network.

This is the operator-side design in miniature. Two smartphones open the calling page (any browser,
over the internet); their call audio flows through this server, which is exactly where a telecom
network sits. The server listens to the CALLER's side with Gnani Prisma realtime STT, scores scam
tactics as they build up, and sends the Gnani Timbre warning (or the family-voice warning) into the
RECEIVER's ear only, mid-call. The caller never hears it.

  python phone_relay.py --tunnel             # public https link via cloudflared + QR codes
  python phone_relay.py --tunnel --prewarm   # also prepare every warning up front (instant first call)

The protected person chooses on their phone: the language (Kannada, Hindi, English), whether the
high-risk warning comes in the family voice (needs a profile from family_voice.py; always labelled),
and the OTP guard: if they start reading digits out after the caller asked for an OTP or money, their
phone says "Stop! Don't say the numbers" and the line stops sending their voice to the caller.

Speakerphone listener (/?role=listener): for a REAL mobile call. Any laptop, tablet or spare phone placed
next to a phone call on speaker listens through its own microphone and warns out loud during the call
(both voices are heard, so the OTP guard there can only warn, not cut anyone off).

A family guardian can open a third page (/guardian) on their own phone: it rings when a call to the
protected person turns into a likely scam, names the kind of scam, and offers to call them.

Then open http://localhost:8765/operator?key=... on the laptop (printed at start) and scan the QR
codes. SPENDS CREDITS while a call is connected: ~0.44 credits per minute for the caller's side, and
the same again for the protected person's side when the OTP guard is on.

Use it for simulated scam calls (scripted, played by you and a friend), never to record real people
without their knowledge. In production the telecom network would carry the call instead of the internet.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

from aiohttp import WSMsgType, web

from alerts import GUARD_WARNINGS, HELPLINE, lang_key, scam_label, scam_tip, top_reasons, tricks
from budget import Budget
from detector import Detection, detect_rules
from family_voice import load_profile
from gnani_client import BudgetExceeded, GnaniClient
from live import FRAME_BYTES, SESSIONS_DIR, WS_URL, AlertPlayer, LiveEvent, LiveSession
from otp_guard import ARMING_TACTICS, DigitWatch, GuardSession, spoken_digits

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
RATE = 16000                      # browsers send 16 kHz mono s16le, 20 ms per message
ROLES = ("caller", "receiver", "listener")   # listener: a device next to a real call on speaker
LANGS = {"kn-IN": "ಕನ್ನಡ", "hi-IN": "हिन्दी", "en-IN": "English"}


class Call:
    """The one call the relay carries at a time (one call = bounded credit spend)."""

    def __init__(self) -> None:
        self.peers: dict[str, web.WebSocketResponse] = {}
        self.caller_audio: asyncio.Queue[bytes | None] = asyncio.Queue()
        self.task: asyncio.Task | None = None
        self.session: LiveSession | None = None
        self.connected_at: float | None = None
        self.ended = False
        self.lang = "kn-IN"                        # chosen by the protected person when they join
        self.use_family = False
        self.use_guard = False                     # OTP guard: also listen to the protected person
        self.receiver_audio: asyncio.Queue[bytes | None] = asyncio.Queue()
        self.guard_task: asyncio.Task | None = None
        self.receiver_muted = False                # set by the guard: their voice no longer reaches the caller
        self.caller_lines: list[str] = []          # last few things the caller said (for the guardian)
        self.digit_watch: DigitWatch | None = None # speakerphone listener: the OTP guard on the mixed audio

    def protected(self) -> web.WebSocketResponse | None:
        """The phone that gets the warnings: the receiver, or the speakerphone listener."""
        # not `a or b`: an aiohttp response is a mapping and an empty one is falsy
        receiver = self.peers.get("receiver")
        return receiver if receiver is not None else self.peers.get("listener")


class Relay:
    def __init__(self, api_key: str, *, key: str, lang: str = "kn-IN", max_seconds: float = 300.0,
                 family: dict | None = None, gnani_url: str = WS_URL, client: GnaniClient | None = None,
                 save_dir: Path | None = SESSIONS_DIR, public_url: str | None = None, pace: bool = True,
                 guard: bool = True, **session_opts):
        self.api_key, self.key, self.lang, self.max_seconds = api_key, key, lang, max_seconds
        self.guard = guard                         # offer the OTP guard on the protected phone
        self.family, self.gnani_url, self.save_dir, self.pace = family, gnani_url, save_dir, pace
        self.client = client or GnaniClient(api_key)
        self.public_url = public_url
        self.session_opts = session_opts           # e.g. faster flush timings in tests
        self.call = Call()
        self.ops: set[web.WebSocketResponse] = set()
        self.guardians: set[web.WebSocketResponse] = set()   # family phones watching over the receiver
        self.history: list[dict] = []           # events of the current/last call, for late operator tabs

    # ---- web app ----------------------------------------------------------------------------
    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/", self.page("call.html"))
        app.router.add_get("/operator", self.page("operator.html"))
        app.router.add_get("/guardian", self.page("guardian.html"))
        app.router.add_get("/practice", self.page("practice.html"))
        app.router.add_get("/practice.json", self.page("practice.json", "application/json"))
        app.router.add_get("/scams", self.page("scams.html"))
        app.router.add_get("/scams.json", self.page("scams.json", "application/json"))
        app.router.add_post("/api/check", self.check)
        app.router.add_get("/pcm-worklet.js", self.page("pcm-worklet.js", "application/javascript"))
        app.router.add_get("/manifest.webmanifest", self.manifest)
        app.router.add_static("/icons", WEB / "icons")
        (WEB / "audio").mkdir(exist_ok=True)
        app.router.add_static("/audio", WEB / "audio")        # saved Timbre explanations (free to play)
        app.router.add_get("/info", self.info)
        app.router.add_get("/ws/call", self.call_ws)
        app.router.add_get("/ws/ops", self.ops_ws)
        app.router.add_get("/ws/guardian", self.guardian_ws)
        return app

    def page(self, name: str, content_type: str = "text/html"):
        async def handler(request: web.Request) -> web.Response:
            return web.Response(body=(WEB / name).read_bytes(), content_type=content_type, charset="utf-8",
                                headers={"Cache-Control": "no-store"})
        return handler

    def authorised(self, request: web.Request) -> bool:
        return secrets.compare_digest(request.query.get("key", ""), self.key)

    async def manifest(self, request: web.Request) -> web.Response:
        """Lets a phone add the page to its home screen as an app that opens straight into its role."""
        if not self.authorised(request):
            raise web.HTTPForbidden(text="bad key")
        app = request.query.get("app", "receiver")
        if app not in ("receiver", "listener", "guardian"):
            raise web.HTTPBadRequest(text="app must be receiver, listener or guardian")
        start = f"/guardian?key={self.key}" if app == "guardian" else f"/?role={app}&key={self.key}"
        name = "Family guardian" if app == "guardian" else "Scam Sentinel"
        icons = [{"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                 {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
                 {"src": "/icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]
        body = {"name": name, "short_name": name, "start_url": start, "scope": "/", "id": f"/{app}",
                "display": "standalone", "orientation": "portrait",
                "background_color": "#0b1416", "theme_color": "#0b1416", "icons": icons}
        return web.Response(text=json.dumps(body), content_type="application/manifest+json",
                            headers={"Cache-Control": "no-store"})

    async def check(self, request: web.Request) -> web.Response:
        """Practice page: score typed words with the offline rule detector. Free: no Gnani call, nothing saved."""
        if not self.authorised(request):
            raise web.HTTPForbidden(text="bad key")
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise web.HTTPBadRequest(text="send JSON: {text, lang}")
        text, lang = str(body.get("text", ""))[:2000], str(body.get("lang", "en-IN"))
        lang = lang if lang in LANGS else "en-IN"
        det = detect_rules(text)
        return web.json_response({"level": det.level, "score": round(det.score, 1), "scam_type": det.scam_type,
                                  "scam_label": scam_label(lang, det.scam_type) if det.tactics else None,
                                  "tip": scam_tip(lang, det.scam_type) if det.level != "low" else None,
                                  "tricks": tricks(lang, det.tactics)})

    async def info(self, request: web.Request) -> web.Response:
        if not self.authorised(request):
            raise web.HTTPForbidden(text="bad key")
        return web.json_response({"public_url": self.public_url, "lang": self.lang, "langs": LANGS,
                                  "family": self.family["name"] if self.family else None,
                                  "max_seconds": self.max_seconds, "guard": self.guard})

    # ---- call websocket ---------------------------------------------------------------------
    async def call_ws(self, request: web.Request) -> web.WebSocketResponse:
        if not self.authorised(request):
            raise web.HTTPForbidden(text="bad key")
        role = request.query.get("role")
        if role not in ROLES:
            raise web.HTTPBadRequest(text="role must be caller, receiver or listener")
        lang = request.query.get("lang", self.lang)
        if role in ("receiver", "listener") and lang not in LANGS:
            raise web.HTTPBadRequest(text=f"lang must be one of {', '.join(LANGS)}")
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=4 * 1024 * 1024)
        await ws.prepare(request)
        call = self.call
        busy = (f"Someone is already connected as the {role}." if role in call.peers else
                "The line is busy with another call." if call.peers and (role == "listener" or "listener" in call.peers)
                else None)
        if busy:
            await ws.send_json({"type": "error", "message": busy})
            await ws.close()
            return ws
        call.peers[role] = ws
        if role in ("receiver", "listener"):
            call.lang = lang
            call.use_family = request.query.get("family") == "1" and self.family is not None
            call.use_guard = request.query.get("guard") == "1" and self.guard
        await self.broadcast_ops({"type": "peer", "role": role, "joined": True})
        await ws.send_json({"type": "waiting", "role": role})
        if len(call.peers) == 2 or role == "listener":
            await self.start(call)
        other = "receiver" if role == "caller" else "caller"
        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    peer = call.peers.get(other)
                    blocked = role == "receiver" and call.receiver_muted
                    if peer is not None and not peer.closed and call.connected_at and not blocked:
                        await peer.send_bytes(msg.data)              # the call itself
                    if role in ("caller", "listener") and call.connected_at:
                        call.caller_audio.put_nowait(msg.data)       # the network's ear on the caller
                    elif role == "receiver" and call.connected_at and call.use_guard:
                        call.receiver_audio.put_nowait(msg.data)     # only counted for digits
                elif msg.type == WSMsgType.TEXT:
                    kind = json.loads(msg.data).get("type")
                    if kind == "hangup":
                        break
                    if kind == "unmute" and role == "receiver" and call.receiver_muted:
                        call.receiver_muted = False                  # their choice: the caller hears them again
                        await self.broadcast_ops({"type": "unmuted"})
                        await self.broadcast(self.guardians, {"type": "unmuted"})
        finally:
            await self.hangup(call, role)
        return ws

    async def start(self, call: Call) -> None:
        call.connected_at = time.monotonic()
        self.history = []
        loop = asyncio.get_running_loop()

        def on_event(e: LiveEvent) -> None:   # LiveSession runs on this loop: schedule the sends
            loop.create_task(self.forward(call, e))

        session = LiveSession(self.api_key, call.lang, RATE, on_event=on_event, max_seconds=self.max_seconds,
                              url=self.gnani_url, save_dir=self.save_dir, source_name="phone-relay",
                              pace=self.pace, **self.session_opts)
        call.session = session
        player = AlertPlayer(self.client, call.lang, session, family=self.family if call.use_family else None,
                             guard=call.use_guard)
        problems = await asyncio.to_thread(player.prepare)   # cached after the first call: instant
        warnings = {lvl: base64.b64encode(a).decode() for lvl, a in player.audio.items()}
        for role, ws in call.peers.items():
            await ws.send_json({"type": "connected", "role": role, "lang": call.lang,
                                "max_seconds": self.max_seconds, "guard": call.use_guard,
                                "guardians": len(self.guardians)})
        receiver = call.protected()
        if receiver is not None:
            await receiver.send_json({"type": "warnings", "audio": warnings, "helpline": HELPLINE})
        for p in problems:
            await self.broadcast_ops({"type": "info", "message": p})
        state = {"type": "call", "state": "connected", "lang": call.lang, "guard": call.use_guard,
                 "family": self.family["name"] if player.family_used else None}
        await self.broadcast_ops(state)
        await self.broadcast(self.guardians, state)
        call.task = asyncio.create_task(self.listen(call, session, call.caller_audio))
        if call.use_guard and "listener" in call.peers:
            call.digit_watch = DigitWatch()        # one microphone hears both people: count digits in it
        elif call.use_guard:
            def on_guard(e: LiveEvent) -> None:
                loop.create_task(self.forward_guard(call, e))

            guard = GuardSession(self.api_key, call.lang, RATE, on_event=on_guard, max_seconds=self.max_seconds,
                                 url=self.gnani_url, save_dir=self.save_dir, source_name="phone-relay-receiver",
                                 pace=self.pace, armed=lambda: bool(session.tracker.det.tactics.keys() & ARMING_TACTICS),
                                 **self.session_opts)
            call.guard_task = asyncio.create_task(self.listen(call, guard, call.receiver_audio, main=False))

    async def listen(self, call: Call, session: LiveSession, source: asyncio.Queue, main: bool = True) -> None:
        try:
            summary = await session.run(self.frames(source))
        except BudgetExceeded as exc:
            await self.broadcast_ops({"type": "error", "message": str(exc)})
            if main:
                for ws in list(call.peers.values()):
                    await self.safe_send(ws, {"type": "error", "message": "Protection unavailable (credit limit)."})
            return
        if main and summary["seconds_streamed"] >= self.max_seconds:
            for ws in list(call.peers.values()):
                await self.safe_send(ws, {"type": "ended", "reason": "time limit"})
                await ws.close()

    async def frames(self, source: asyncio.Queue):
        """Phone audio re-cut into the exact 1024-byte frames Prisma needs."""
        buf = b""
        while True:
            chunk = await source.get()
            if chunk is None:
                return
            buf += chunk
            while len(buf) >= FRAME_BYTES:
                yield buf[:FRAME_BYTES]
                buf = buf[FRAME_BYTES:]

    async def forward(self, call: Call, e: LiveEvent) -> None:
        msg = {"type": e.kind, **e.data}
        if e.kind == "transcript" and not e.data.get("echo") and e.data["text"]:
            call.caller_lines = (call.caller_lines + [e.data["text"]])[-3:]
            if call.digit_watch:
                armed = bool(set(e.data["tactics"]) & ARMING_TACTICS)
                total = call.digit_watch.add(e.data["at"], spoken_digits(e.data["text"]), armed)
                if total:
                    await self.forward_guard(call, LiveEvent("guard", {"at": e.data["at"], "digits": total}))
        if e.kind == "alert":
            msg["family_told"] = bool(self.guardians)
            msg["tip"] = scam_tip(call.lang, e.data.get("scam_type"))
            msg["scam_label_en"] = scam_label("en-IN", e.data.get("scam_type"))
            msg["caller_said"] = call.caller_lines
            await self.broadcast(self.guardians, {
                "type": "alert", "level": e.data["level"], "at": e.data["at"], "lang": call.lang,
                "scam_type": e.data.get("scam_type"), "scam_label": scam_label("en-IN", e.data.get("scam_type")),
                "reasons": top_reasons("en-IN", Detection(tactics={t: [] for t in e.data.get("tactics", [])})),
                "tip": scam_tip("en-IN", e.data.get("scam_type")), "caller_said": call.caller_lines})
        elif e.kind == "done":
            await self.broadcast(self.guardians, {"type": "done", "level": e.data["level"],
                                                  "seconds": e.data["seconds_streamed"]})
        self.history.append(msg)
        await self.broadcast_ops(msg)
        receiver = call.protected()
        if receiver is None:
            return
        if e.kind == "alert":                 # only the protected person hears and sees the warning
            await self.safe_send(receiver, msg)
        elif e.kind == "transcript" and not e.data.get("echo"):
            await self.safe_send(receiver, {"type": "risk", "level": e.data["level"], "score": e.data["score"],
                                            "tricks": tricks(call.lang, e.data.get("tactics", []))})

    async def forward_guard(self, call: Call, e: LiveEvent) -> None:
        """Events from the OTP guard. The protected person's words are never forwarded, only digit counts."""
        if e.kind in ("heard", "guard"):
            msg = {"type": e.kind, **e.data}
        elif e.kind in ("info", "error"):
            msg = {"type": e.kind, "message": "OTP guard: " + e.data["message"]}
        elif e.kind == "done":
            msg = {"type": "guard_done", "fired": e.data.get("guard_fired", 0),
                   "seconds_streamed": e.data["seconds_streamed"]}
        else:
            return
        if e.kind == "guard":
            call.receiver_muted = True        # the caller stops hearing them at once (relayed calls)
            msg["cut"] = "receiver" in call.peers
            await self.broadcast(self.guardians, msg)
            receiver = call.protected()
            if receiver is not None:
                await self.safe_send(receiver, {**msg, "message": GUARD_WARNINGS[lang_key(call.lang)]})
        self.history.append(msg)
        await self.broadcast_ops(msg)

    async def hangup(self, call: Call, role: str) -> None:
        if call.peers.pop(role, None) is None:
            return
        await self.broadcast_ops({"type": "peer", "role": role, "joined": False})
        for ws in list(call.peers.values()):
            await self.safe_send(ws, {"type": "ended", "reason": f"the {role} hung up"})
            await ws.close()
        if call.connected_at and not call.ended:
            call.ended = True
            call.caller_audio.put_nowait(None)             # let the sessions flush and finish
            call.receiver_audio.put_nowait(None)
            for task in (call.task, call.guard_task):
                if task:
                    try:
                        await asyncio.wait_for(asyncio.shield(task), 15)
                    except asyncio.TimeoutError:
                        task.cancel()
            await self.broadcast_ops({"type": "call", "state": "ended"})
            await self.broadcast(self.guardians, {"type": "call", "state": "ended"})
        if not call.peers:
            self.call = Call()

    # ---- operator dashboard -------------------------------------------------------------------
    async def ops_ws(self, request: web.Request) -> web.WebSocketResponse:
        if not self.authorised(request):
            raise web.HTTPForbidden(text="bad key")
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        self.ops.add(ws)
        for role in self.call.peers:
            await ws.send_json({"type": "peer", "role": role, "joined": True})
        for msg in self.history:
            await ws.send_json(msg)
        try:
            async for _ in ws:
                pass
        finally:
            self.ops.discard(ws)
        return ws

    async def broadcast_ops(self, msg: dict) -> None:
        await self.broadcast(self.ops, msg)

    async def broadcast(self, group: set[web.WebSocketResponse], msg: dict) -> None:
        for ws in list(group):
            await self.safe_send(ws, msg)

    # ---- family guardian ----------------------------------------------------------------------
    async def guardian_ws(self, request: web.Request) -> web.WebSocketResponse:
        """A family member's phone: told when a call to the protected person turns into a likely scam."""
        if not self.authorised(request):
            raise web.HTTPForbidden(text="bad key")
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        self.guardians.add(ws)
        call = self.call
        live = call.connected_at is not None and not call.ended
        await ws.send_json({"type": "call", "state": "connected" if live else "idle", "lang": call.lang,
                            "guard": call.use_guard})
        await self.guardians_changed()
        try:
            async for _ in ws:
                pass
        finally:
            self.guardians.discard(ws)
            await self.guardians_changed()
        return ws

    async def guardians_changed(self) -> None:
        msg = {"type": "guardians", "count": len(self.guardians)}
        await self.broadcast_ops(msg)
        receiver = self.call.protected()
        if receiver is not None:
            await self.safe_send(receiver, msg)

    @staticmethod
    async def safe_send(ws: web.WebSocketResponse, msg: dict) -> None:
        if not ws.closed:
            try:
                await ws.send_json(msg)
            except (ConnectionResetError, RuntimeError):
                pass


# ---- public link via cloudflared ---------------------------------------------------------------
def find_cloudflared() -> str | None:
    for candidate in (os.getenv("CLOUDFLARED"), shutil.which("cloudflared"),
                      str(Path.home() / "Desktop" / "cloudflared.exe")):
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def start_tunnel(port: int, timeout: float = 40.0) -> tuple[subprocess.Popen, str]:
    """A temporary https://*.trycloudflare.com address for this laptop (phones need https for the mic)."""
    exe = find_cloudflared()
    if not exe:
        raise SystemExit("cloudflared not found: set CLOUDFLARED to its path, or run without --tunnel.")
    proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace")
    deadline = time.monotonic() + timeout
    for line in proc.stdout:
        found = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if found:
            return proc, found.group(0)
        if time.monotonic() > deadline:
            break
    proc.kill()
    raise SystemExit("cloudflared did not give a public address in time; check the internet connection.")


def prewarm(client: GnaniClient, family: dict | None, guard: bool = True) -> None:
    """Synthesize (and cache) every warning the phones could need; later calls cost nothing for TTS."""
    for lang in LANGS:
        for fam in ([None, family] if family else [None]):
            player = AlertPlayer(client, lang, family=fam, guard=guard)
            for problem in player.prepare():
                print(problem)
            print(f"warnings ready: {lang}{' + family voice' if player.family_used else ''}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="kn-IN", choices=list(LANGS), help="default language on the phone page")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--max-seconds", type=float, default=300.0, help="longest protected call (credit cap)")
    ap.add_argument("--no-family", action="store_true", help="hide the family-voice option even if a profile exists")
    ap.add_argument("--prewarm", action="store_true",
                    help="synthesize every warning (3 languages, standard + family) now, so calls start instantly")
    ap.add_argument("--tunnel", action="store_true", help="public https link via cloudflared (for phones)")
    ap.add_argument("--no-guard", action="store_true",
                    help="do not offer the OTP guard (halves the listening cost of a call)")
    args = ap.parse_args(argv)

    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        raise SystemExit("Set GNANI_API_KEY (or put it in .env).")
    family = None if args.no_family else load_profile()
    if args.prewarm:
        prewarm(GnaniClient(api_key), family, guard=not args.no_guard)
    est = Budget().check("stt_stream", args.max_seconds * (1 if args.no_guard else 2))   # both sides
    print(est.line())
    if not est.ok:
        raise SystemExit(est.reason)

    key = secrets.token_urlsafe(9)
    tunnel, public = (start_tunnel(args.port) if args.tunnel else (None, None))
    relay = Relay(api_key, key=key, lang=args.lang, max_seconds=args.max_seconds, family=family, public_url=public,
                  guard=not args.no_guard)
    base = public or f"http://localhost:{args.port}"
    print(f"\nOperator dashboard (open on this laptop): http://localhost:{args.port}/operator?key={key}")
    print(f"Receiver phone (protected): {base}/?role=receiver&key={key}")
    print(f"Caller phone (simulated scammer): {base}/?role=caller&key={key}")
    print(f"Family guardian's phone: {base}/guardian?key={key}")
    print(f"Speakerphone listener (real calls; on this laptop): http://localhost:{args.port}/?role=listener&key={key}")
    if not public:
        print("(No --tunnel: phones cannot reach localhost and need https for the microphone.)")
    print("Ctrl+C to stop.\n")
    try:
        web.run_app(relay.app(), host="127.0.0.1", port=args.port, print=None)
    finally:
        if tunnel:
            tunnel.terminate()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
