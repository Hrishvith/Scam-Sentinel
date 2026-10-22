"""Protected calling line: a real call between two phones, with Scam Sentinel sitting in the network.

This is the operator-side design in miniature. Two smartphones open the calling page (any browser,
over the internet); their call audio flows through this server, which is exactly where a telecom
network sits. The server listens to the CALLER's side with Gnani Prisma realtime STT, scores scam
tactics as they build up, and sends the Gnani Timbre warning (or the family-voice warning) into the
RECEIVER's ear only, mid-call. The caller never hears it.

  python phone_relay.py --lang kn-IN --tunnel             # public https link via cloudflared + QR codes
  python phone_relay.py --lang kn-IN --family-voice       # high warning in your cloned voice (labelled)

Then open http://localhost:8765/operator?key=... on the laptop (printed at start) and scan the two QR
codes with two phones. SPENDS CREDITS while a call is connected (~0.44 credits per minute).

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

from alerts import HELPLINE
from budget import Budget
from family_voice import load_profile
from gnani_client import BudgetExceeded, GnaniClient
from live import FRAME_BYTES, SESSIONS_DIR, WS_URL, AlertPlayer, LiveEvent, LiveSession

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
RATE = 16000                      # browsers send 16 kHz mono s16le, 20 ms per message
ROLES = ("caller", "receiver")


class Call:
    """The one call the relay carries at a time (one call = bounded credit spend)."""

    def __init__(self) -> None:
        self.peers: dict[str, web.WebSocketResponse] = {}
        self.caller_audio: asyncio.Queue[bytes | None] = asyncio.Queue()
        self.task: asyncio.Task | None = None
        self.session: LiveSession | None = None
        self.connected_at: float | None = None
        self.ended = False


class Relay:
    def __init__(self, api_key: str, *, key: str, lang: str = "kn-IN", max_seconds: float = 300.0,
                 family: dict | None = None, gnani_url: str = WS_URL, client: GnaniClient | None = None,
                 save_dir: Path | None = SESSIONS_DIR, public_url: str | None = None, pace: bool = True,
                 **session_opts):
        self.api_key, self.key, self.lang, self.max_seconds = api_key, key, lang, max_seconds
        self.family, self.gnani_url, self.save_dir, self.pace = family, gnani_url, save_dir, pace
        self.client = client or GnaniClient(api_key)
        self.public_url = public_url
        self.session_opts = session_opts           # e.g. faster flush timings in tests
        self.call = Call()
        self.ops: set[web.WebSocketResponse] = set()
        self.history: list[dict] = []           # events of the current/last call, for late operator tabs

    # ---- web app ----------------------------------------------------------------------------
    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/", self.page("call.html"))
        app.router.add_get("/operator", self.page("operator.html"))
        app.router.add_get("/pcm-worklet.js", self.page("pcm-worklet.js", "application/javascript"))
        app.router.add_get("/info", self.info)
        app.router.add_get("/ws/call", self.call_ws)
        app.router.add_get("/ws/ops", self.ops_ws)
        return app

    def page(self, name: str, content_type: str = "text/html"):
        async def handler(request: web.Request) -> web.Response:
            return web.Response(body=(WEB / name).read_bytes(), content_type=content_type, charset="utf-8",
                                headers={"Cache-Control": "no-store"})
        return handler

    def authorised(self, request: web.Request) -> bool:
        return secrets.compare_digest(request.query.get("key", ""), self.key)

    async def info(self, request: web.Request) -> web.Response:
        if not self.authorised(request):
            raise web.HTTPForbidden(text="bad key")
        return web.json_response({"public_url": self.public_url, "lang": self.lang,
                                  "family": self.family["name"] if self.family else None,
                                  "max_seconds": self.max_seconds})

    # ---- call websocket ---------------------------------------------------------------------
    async def call_ws(self, request: web.Request) -> web.WebSocketResponse:
        if not self.authorised(request):
            raise web.HTTPForbidden(text="bad key")
        role = request.query.get("role")
        if role not in ROLES:
            raise web.HTTPBadRequest(text="role must be caller or receiver")
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=4 * 1024 * 1024)
        await ws.prepare(request)
        call = self.call
        if role in call.peers:
            await ws.send_json({"type": "error", "message": f"Someone is already connected as the {role}."})
            await ws.close()
            return ws
        call.peers[role] = ws
        await self.broadcast_ops({"type": "peer", "role": role, "joined": True})
        await ws.send_json({"type": "waiting", "role": role})
        if len(call.peers) == 2:
            await self.start(call)
        other = "receiver" if role == "caller" else "caller"
        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    peer = call.peers.get(other)
                    if peer is not None and not peer.closed and call.connected_at:
                        await peer.send_bytes(msg.data)              # the call itself
                    if role == "caller" and call.connected_at:
                        call.caller_audio.put_nowait(msg.data)       # the network's ear on the caller
                elif msg.type == WSMsgType.TEXT and json.loads(msg.data).get("type") == "hangup":
                    break
        finally:
            await self.hangup(call, role)
        return ws

    async def start(self, call: Call) -> None:
        call.connected_at = time.monotonic()
        self.history = []
        loop = asyncio.get_running_loop()

        def on_event(e: LiveEvent) -> None:   # LiveSession runs on this loop: schedule the sends
            loop.create_task(self.forward(call, e))

        session = LiveSession(self.api_key, self.lang, RATE, on_event=on_event, max_seconds=self.max_seconds,
                              url=self.gnani_url, save_dir=self.save_dir, source_name="phone-relay",
                              pace=self.pace, **self.session_opts)
        call.session = session
        player = AlertPlayer(self.client, self.lang, session, family=self.family)
        problems = await asyncio.to_thread(player.prepare)   # cached after the first call: instant
        warnings = {lvl: base64.b64encode(a).decode() for lvl, a in player.audio.items()}
        for role, ws in call.peers.items():
            await ws.send_json({"type": "connected", "role": role, "lang": self.lang,
                                "max_seconds": self.max_seconds})
        receiver = call.peers.get("receiver")
        if receiver is not None:
            await receiver.send_json({"type": "warnings", "audio": warnings, "helpline": HELPLINE})
        for p in problems:
            await self.broadcast_ops({"type": "info", "message": p})
        await self.broadcast_ops({"type": "call", "state": "connected", "lang": self.lang,
                                  "family": self.family["name"] if player.family_used else None})
        call.task = asyncio.create_task(self.listen(call, session))

    async def listen(self, call: Call, session: LiveSession) -> None:
        try:
            summary = await session.run(self.frames(call))
        except BudgetExceeded as exc:
            await self.broadcast_ops({"type": "error", "message": str(exc)})
            for ws in list(call.peers.values()):
                await self.safe_send(ws, {"type": "error", "message": "Protection unavailable (credit limit)."})
            return
        if summary["seconds_streamed"] >= self.max_seconds:
            for ws in list(call.peers.values()):
                await self.safe_send(ws, {"type": "ended", "reason": "time limit"})
                await ws.close()

    async def frames(self, call: Call):
        """Caller audio re-cut into the exact 1024-byte frames Prisma needs."""
        buf = b""
        while True:
            chunk = await call.caller_audio.get()
            if chunk is None:
                return
            buf += chunk
            while len(buf) >= FRAME_BYTES:
                yield buf[:FRAME_BYTES]
                buf = buf[FRAME_BYTES:]

    async def forward(self, call: Call, e: LiveEvent) -> None:
        msg = {"type": e.kind, **e.data}
        self.history.append(msg)
        await self.broadcast_ops(msg)
        receiver = call.peers.get("receiver")
        if receiver is None:
            return
        if e.kind == "alert":                 # only the protected person hears and sees the warning
            await self.safe_send(receiver, msg)
        elif e.kind == "transcript" and not e.data.get("echo"):
            await self.safe_send(receiver, {"type": "risk", "level": e.data["level"], "score": e.data["score"]})

    async def hangup(self, call: Call, role: str) -> None:
        if call.peers.pop(role, None) is None:
            return
        await self.broadcast_ops({"type": "peer", "role": role, "joined": False})
        for ws in list(call.peers.values()):
            await self.safe_send(ws, {"type": "ended", "reason": f"the {role} hung up"})
            await ws.close()
        if call.connected_at and not call.ended:
            call.ended = True
            call.caller_audio.put_nowait(None)             # let the session flush and finish
            if call.task:
                try:
                    await asyncio.wait_for(asyncio.shield(call.task), 15)
                except asyncio.TimeoutError:
                    call.task.cancel()
            await self.broadcast_ops({"type": "call", "state": "ended"})
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
        for ws in list(self.ops):
            await self.safe_send(ws, msg)

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


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="kn-IN", help="the protected person's language: kn-IN, hi-IN, en-IN")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--max-seconds", type=float, default=300.0, help="longest protected call (credit cap)")
    ap.add_argument("--family-voice", action="store_true", help="high warning in your cloned voice (labelled)")
    ap.add_argument("--tunnel", action="store_true", help="public https link via cloudflared (for phones)")
    args = ap.parse_args(argv)

    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        raise SystemExit("Set GNANI_API_KEY (or put it in .env).")
    family = load_profile() if args.family_voice else None
    if args.family_voice and not family:
        raise SystemExit("No voice profile: run family_voice.py record and enroll first.")
    est = Budget().check("stt_stream", args.max_seconds)
    print(est.line())
    if not est.ok:
        raise SystemExit(est.reason)

    key = secrets.token_urlsafe(9)
    tunnel, public = (start_tunnel(args.port) if args.tunnel else (None, None))
    relay = Relay(api_key, key=key, lang=args.lang, max_seconds=args.max_seconds, family=family, public_url=public)
    base = public or f"http://localhost:{args.port}"
    print(f"\nOperator dashboard (open on this laptop): http://localhost:{args.port}/operator?key={key}")
    print(f"Receiver phone (protected): {base}/?role=receiver&key={key}")
    print(f"Caller phone (simulated scammer): {base}/?role=caller&key={key}")
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
