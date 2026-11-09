"""Protected calling line, end to end on localhost: two fake phones, a fake Gnani STT server,
a fake Timbre client. No network, no credits."""
import asyncio
import base64
import json
import time

from aiohttp import WSMsgType
from aiohttp.test_utils import TestClient, TestServer
from websockets.asyncio.server import serve

import phone_relay
from alerts import FAMILY_WARNINGS
from budget import read_ledger
from phone_relay import PublicQuota, Relay
from test_live import FakeGnani
from test_sentinel import FakeResp, make_client

KEY = "secret-key"
SCRIPT = ["this is the cyber crime branch", "there is an arrest warrant against you",
          "do not tell anyone install anydesk and tell me the otp"]


def frame(n: int) -> bytes:
    """20 ms of 16 kHz s16le, distinguishable per frame."""
    return bytes([n % 251, 1]) * 320


async def receive_until(ws, kind, timeout=5.0):
    """JSON messages until one of type `kind` arrives; binary (call audio) collected separately."""
    seen, audio = [], []

    async def loop():
        while True:
            msg = await ws.receive()
            if msg.type == WSMsgType.BINARY:
                audio.append(msg.data)
                continue
            if msg.type != WSMsgType.TEXT:
                return
            m = json.loads(msg.data)
            seen.append(m)
            if m["type"] == kind:
                return

    await asyncio.wait_for(loop(), timeout)
    return seen, audio


async def next_audio(ws, timeout=3.0):
    msg = await asyncio.wait_for(ws.receive(), timeout)
    while msg.type == WSMsgType.TEXT:
        msg = await asyncio.wait_for(ws.receive(), timeout)
    return msg.data


async def drain(ws):
    out = []
    try:
        while True:
            msg = await asyncio.wait_for(ws.receive(), 0.3)
            if msg.type == WSMsgType.TEXT:
                out.append(json.loads(msg.data))
            elif msg.type != WSMsgType.BINARY:
                return out
    except asyncio.TimeoutError:
        return out


def tts_server(url, kw, n):
    cloned = kw["json"].get("model") == "vachana-vc-v1"
    return FakeResp(content=(b"RIFFcloned" if cloned else b"RIFFstandard") + bytes(40))


def run(body, tmp_path, script=SCRIPT, family=None, public=None):
    async def main():
        fake = FakeGnani(script=list(script), frames_per_segment=10)
        async with serve(fake.handler, "127.0.0.1", 0) as gnani:
            port = gnani.sockets[0].getsockname()[1]
            client, tts_calls = make_client(tmp_path, tts_server)
            relay = Relay("test-key", key=KEY, lang="en-IN", gnani_url=f"ws://127.0.0.1:{port}", client=client,
                          family=family, save_dir=None, pace=False, flush_seconds=0.1, drain_timeout=2,
                          settle_seconds=0.1, public=public)
            async with TestClient(TestServer(relay.app())) as http:
                return await body(http, fake, tts_calls)
    return asyncio.run(main())


# ---- public demo: no key, one-device speakerphone listener only, within a daily credit limit ----------------

def test_public_quota_reserves_settles_and_resets_each_day():
    now = [1_800_000_000.0]
    q = PublicQuota(daily_credits=2.0, max_seconds=100, rate=0.01, per_ip_seconds=300, clock=lambda: now[0])
    held, why = q.reserve("1.1.1.1")
    assert held == 1.0 and why is None and q.left() == 1.0          # the longest session is held up front
    assert q.reserve("1.1.1.1")[1].startswith("Please wait")          # one free call per visitor every 5 minutes
    q.settle(held, 30)                                                # only 30 s were really streamed
    assert abs(q.left() - 1.7) < 1e-9
    assert q.reserve("2.2.2.2")[1] is None and q.reserve("3.3.3.3")[1].startswith("Today's free")   # 1.7 - 1.0 < 1.0
    now[0] += 24 * 3600                                               # next day in India: a fresh limit
    assert q.left() == 2.0 and q.reserve("1.1.1.1")[1] is None
    assert not PublicQuota(0, 120, 0.007).enabled


def test_one_network_waits_a_minute_and_a_half_between_public_sessions():
    now = [1_800_000_000.0]
    q = PublicQuota(daily_credits=7.0, max_seconds=120, rate=0.0073, clock=lambda: now[0])
    assert q.reserve("1.1.1.1")[1] is None
    now[0] += 60
    assert q.reserve("1.1.1.1")[1].startswith("Please wait about 30 seconds")
    now[0] += 30
    assert q.reserve("1.1.1.1")[1] is None


def test_without_public_demo_no_key_means_no_live_call(tmp_path):
    async def body(http, fake, _):
        assert (await http.get("/info")).status == 403
        assert (await http.get("/ws/call?role=listener")).status == 403
        assert fake.connections == []
    run(body, tmp_path)


def test_public_demo_allows_only_the_listener_and_counts_credits(tmp_path):
    quota = PublicQuota(daily_credits=5.0, max_seconds=60, rate=0.01)
    async def body(http, fake, _):
        info = await (await http.get("/info")).json()
        assert info["public"] is True and info["roles"] == ["listener"] and info["max_seconds"] == 60
        for role in ("receiver", "caller"):                           # never pair strangers in a two-phone call
            assert (await http.get(f"/ws/call?role={role}")).status == 403
        assert (await http.get("/ws/guardian")).status == 403 and (await http.get("/ws/ops")).status == 403
        ws = await http.ws_connect("/ws/call?role=listener&lang=en-IN")
        seen, _ = await receive_until(ws, "connected")
        assert seen[-1]["max_seconds"] == 60                         # the shorter public cap
        assert abs(quota.left() - 4.4) < 1e-9                         # 60 s x 0.01 held while the call runs
        for i in range(30):
            await ws.send_bytes(frame(i))
        await ws.send_json({"type": "hangup"}); await ws.close()
        for _ in range(100):
            if quota.left() > 4.4:
                break
            await asyncio.sleep(0.05)
        assert 4.4 < quota.left() <= 5.0                              # settled with the seconds really streamed
    run(body, tmp_path, public=quota)


def test_a_connection_lost_during_start_up_frees_the_line_and_the_credits(tmp_path, monkeypatch):
    real_prepare = phone_relay.AlertPlayer.prepare

    def slow_prepare(self):
        time.sleep(0.5)                                               # the warnings being made, on a fresh server
        return real_prepare(self)

    monkeypatch.setattr(phone_relay.AlertPlayer, "prepare", slow_prepare)
    quota = PublicQuota(daily_credits=5.0, max_seconds=60, rate=0.01, per_ip_seconds=0)
    async def body(http, fake, _):
        ws = await http.ws_connect("/ws/call?role=listener&lang=en-IN")
        await receive_until(ws, "waiting")
        ws._response.connection.transport.abort()                     # tab killed or network lost: no goodbye
        await asyncio.sleep(1.0)
        assert quota.left() == 5.0                                    # nothing was streamed, nothing is charged
        monkeypatch.setattr(phone_relay.AlertPlayer, "prepare", real_prepare)
        next_visitor = await http.ws_connect("/ws/call?role=listener&lang=en-IN")
        seen, _ = await receive_until(next_visitor, "connected")      # not "Someone is already connected"
        assert all(m["type"] != "error" for m in seen)
        await next_visitor.send_json({"type": "hangup"}); await next_visitor.close()
    run(body, tmp_path, public=quota)


def test_the_protected_phone_is_told_when_speech_recognition_stops(tmp_path):
    """Audit P0: a speech-service failure must never leave the phone looking protected."""
    async def main():
        client, _ = make_client(tmp_path, tts_server)
        relay = Relay("test-key", key=KEY, lang="en-IN", gnani_url="ws://127.0.0.1:9", client=client,  # nothing listens
                      save_dir=None, pace=False, flush_seconds=0.1, drain_timeout=1, settle_seconds=0.1)
        async with TestClient(TestServer(relay.app())) as http:
            guardian = await http.ws_connect(f"/ws/guardian?key={KEY}")
            listener = await http.ws_connect(f"/ws/call?role=listener&lang=en-IN&key={KEY}")
            await receive_until(listener, "connected")
            for i in range(40):
                await listener.send_bytes(frame(i))
            seen, _ = await receive_until(listener, "protection", timeout=10)
            assert seen[-1]["state"] == "paused"                          # first failed connection
            states = [seen[-1]["state"]]
            while states[-1] != "off":
                more, _ = await receive_until(listener, "protection", timeout=15)
                states.append(more[-1]["state"])
            assert states == ["paused", "off"]                            # gave up: said so, never "on"
            family = await drain(guardian)
            assert any(m["type"] == "protection" and m["state"] == "off" for m in family)
            await listener.close()
    asyncio.run(main())


def test_a_public_visitors_call_is_never_written_to_disk(tmp_path):
    saved = tmp_path / "sessions"
    async def main():
        fake = FakeGnani(script=list(SCRIPT), frames_per_segment=10)
        async with serve(fake.handler, "127.0.0.1", 0) as gnani:
            port = gnani.sockets[0].getsockname()[1]
            client, _ = make_client(tmp_path, tts_server)
            relay = Relay("test-key", key=KEY, lang="en-IN", gnani_url=f"ws://127.0.0.1:{port}", client=client,
                          save_dir=saved, pace=False, flush_seconds=0.1, drain_timeout=2, settle_seconds=0.1,
                          public=PublicQuota(daily_credits=5.0, max_seconds=60, rate=0.01))
            async with TestClient(TestServer(relay.app())) as http:
                ws = await http.ws_connect("/ws/call?role=listener&lang=en-IN")
                await receive_until(ws, "connected")
                for i in range(60):
                    await ws.send_bytes(frame(i))
                await receive_until(ws, "alert", timeout=10)               # it really heard the scam
                await ws.send_json({"type": "hangup"}); await ws.close()
                await asyncio.sleep(0.5)
    asyncio.run(main())
    assert not saved.exists() or not any(saved.iterdir())


def test_the_key_holder_takes_the_line_from_a_public_session(tmp_path):
    async def body(http, fake, _):
        public = await http.ws_connect("/ws/call?role=listener&lang=en-IN")
        await receive_until(public, "connected")
        mine = await http.ws_connect(f"/ws/call?role=listener&lang=en-IN&key={KEY}")
        seen, _ = await receive_until(public, "ended")
        assert "needed for a live demo" in seen[-1]["reason"]
        seen, _ = await receive_until(mine, "connected")             # the private demo gets the line
        await mine.close()
    run(body, tmp_path, public=PublicQuota(daily_credits=5.0, max_seconds=60, rate=0.01))


def test_wrong_key_is_refused_everywhere(tmp_path):
    async def body(http, fake, _):
        for path in ("/ws/call?role=caller&key=nope", "/ws/ops?key=nope", "/info?key=nope",
                     "/info?key=%EF%BB%BFnope", "/info?key=%E0%B2%95"):          # hidden BOM, Kannada letter: 403, not 500
            assert (await http.get(path)).status == 403
        assert fake.connections == []
    run(body, tmp_path)


def test_pages_are_served(tmp_path):
    async def body(http, fake, _):
        assert "Scam Sentinel protected line" in await (await http.get("/")).text()
        assert "operator view" in await (await http.get("/operator")).text()
        worklet = await http.get("/pcm-worklet.js")
        assert worklet.content_type == "application/javascript" and "registerProcessor" in await worklet.text()
        info = await (await http.get(f"/info?key={KEY}")).json()
        assert info["lang"] == "en-IN" and info["family"] is None
    run(body, tmp_path)


def test_every_page_has_security_headers_and_private_pages_stay_out_of_search(tmp_path):
    async def body(http, fake, _):
        for path in ("/", "/practice", "/scams", "/theme.css", "/robots.txt", "/info"):   # /info: a 403 too
            res = await http.get(path)
            assert res.headers["X-Content-Type-Options"] == "nosniff", path
            assert res.headers["Referrer-Policy"] == "no-referrer", path     # the private ?key= never leaks
            assert "frame-ancestors 'none'" in res.headers["Content-Security-Policy"], path
        robots = await (await http.get("/robots.txt")).text()
        assert "Disallow: /operator" in robots and "Disallow: /guardian" in robots and "Sitemap:" in robots
        sitemap = await (await http.get("/sitemap.xml")).text()
        assert "/practice</loc>" in sitemap and "operator" not in sitemap
        home = await (await http.get("/")).text()
        assert '<meta name="description"' in home and 'property="og:title"' in home
        assert 'content="noindex' in await (await http.get("/operator")).text()
    run(body, tmp_path)


def test_audio_waiting_for_speech_recognition_is_bounded():
    q = asyncio.Queue(3)
    for i in range(5):
        phone_relay.offer(q, bytes([i]))
    phone_relay.offer(q, None)                                        # the end-of-call marker always gets in
    assert [q.get_nowait() for _ in range(3)] == [bytes([3]), bytes([4]), None]


def test_phones_can_install_it_as_an_app(tmp_path):
    async def body(http, fake, _):
        assert (await http.get("/manifest.webmanifest?app=receiver&key=nope")).status == 403
        assert (await http.get(f"/manifest.webmanifest?app=caller&key={KEY}")).status == 400
        man = await (await http.get(f"/manifest.webmanifest?app=receiver&key={KEY}")).json(content_type=None)
        assert man["start_url"] == f"/?role=receiver&key={KEY}" and man["display"] == "standalone"
        guardian = await (await http.get(f"/manifest.webmanifest?app=guardian&key={KEY}")).json(content_type=None)
        assert guardian["start_url"] == f"/guardian?key={KEY}" and guardian["name"] == "Family guardian"
        for icon in man["icons"]:
            res = await http.get(icon["src"])
            assert res.status == 200 and res.content_type == "image/png"
    run(body, tmp_path)


def test_call_is_relayed_both_ways_and_only_the_receiver_is_warned(tmp_path, isolated_budget):
    async def body(http, fake, tts_calls):
        ops = await http.ws_connect(f"/ws/ops?key={KEY}")
        receiver = await http.ws_connect(f"/ws/call?role=receiver&key={KEY}")
        caller = await http.ws_connect(f"/ws/call?role=caller&key={KEY}")
        r_msgs, _ = await receive_until(receiver, "warnings")          # connected, then the warning audio
        assert {m["type"] for m in r_msgs} >= {"waiting", "connected", "warnings"}
        assert set(r_msgs[-1]["audio"]) == {"medium", "high"}
        await receive_until(caller, "connected")

        await receiver.send_bytes(frame(999))                            # receiver -> caller
        assert await next_audio(caller) == frame(999)

        for n in range(60):                                              # caller speaks for 1.2 s
            await caller.send_bytes(frame(n))
            await asyncio.sleep(0.005)
        heard, alerts = [], []
        while not any(a["level"] == "high" for a in alerts):
            msgs, audio = await receive_until(receiver, "alert", timeout=10)
            heard += audio
            alerts += [m for m in msgs if m["type"] == "alert"]
        assert heard[:3] == [frame(0), frame(1), frame(2)]               # the call itself reaches the receiver
        assert [a["level"] for a in alerts] == ["medium", "high"]
        assert set(fake.connections[0]["sizes"]) == {1024}               # re-cut into Prisma's frame size
        assert fake.connections[0]["headers"]["lang_code"] == "en-IN"

        await caller.send_str(json.dumps({"type": "hangup"}))
        msgs, _ = await receive_until(receiver, "ended")
        assert "caller hung up" in msgs[-1]["reason"]
        ops_msgs, _ = await receive_until(ops, "done", timeout=10)
        kinds = {m["type"] for m in ops_msgs}
        assert {"transcript", "alert", "done"} <= kinds
        done = next(m for m in ops_msgs if m["type"] == "done")
        assert done["level"] == "high" and set(done["time_to_alert"]) == {"medium", "high"}

        caller_msgs = await drain(caller)
        assert not any(m.get("type") in ("alert", "warnings", "risk") for m in caller_msgs)   # caller is never warned
        await asyncio.sleep(0.2)
        rows = [r for r in read_ledger(isolated_budget.ledger) if r["kind"] == "stt_stream"]
        assert len(rows) == 1 and rows[0]["model"] == "prisma-stt-v3-stream"
    run(body, tmp_path)


def test_a_second_phone_cannot_take_an_occupied_role(tmp_path):
    async def body(http, fake, _):
        first = await http.ws_connect(f"/ws/call?role=receiver&key={KEY}")
        await receive_until(first, "waiting")
        second = await http.ws_connect(f"/ws/call?role=receiver&key={KEY}")
        msgs, _ = await receive_until(second, "error")
        assert "already connected" in msgs[-1]["message"] and fake.connections == []
    run(body, tmp_path)


FAMILY = {"name": "Asha", "embedding": "QUJD", "shape": [1, 768], "dtype": "torch.bfloat16"}


async def connect_and_speak(http, receiver_query):
    receiver = await http.ws_connect(f"/ws/call?role=receiver&key={KEY}{receiver_query}")
    caller = await http.ws_connect(f"/ws/call?role=caller&key={KEY}")
    msgs, _ = await receive_until(receiver, "warnings")
    await receive_until(caller, "connected")
    for n in range(60):
        await caller.send_bytes(frame(n))
        await asyncio.sleep(0.005)
    alerts = []
    while not any(a["level"] == "high" for a in alerts):
        more, _ = await receive_until(receiver, "alert", timeout=10)
        alerts += [m for m in more if m["type"] == "alert"]
    return receiver, caller, msgs, alerts


def test_the_protected_person_chooses_hindi_and_the_family_voice(tmp_path):
    async def body(http, fake, _):
        info = await (await http.get(f"/info?key={KEY}")).json()
        assert info["family"] == "Asha" and set(info["langs"]) == {"kn-IN", "hi-IN", "en-IN"}
        receiver, caller, msgs, alerts = await connect_and_speak(http, "&lang=hi-IN&family=1")
        connected = next(m for m in msgs if m["type"] == "connected")
        assert connected["lang"] == "hi-IN" and fake.connections[0]["headers"]["lang_code"] == "hi-IN"
        audio = next(m for m in msgs if m["type"] == "warnings")["audio"]
        assert base64.b64decode(audio["high"]).startswith(b"RIFFcloned")        # family voice for "high"
        assert base64.b64decode(audio["medium"]).startswith(b"RIFFstandard")
        high = next(a for a in alerts if a["level"] == "high")
        assert high["voice"] == "AI clone of Asha's voice (made with consent)"
        assert high["message"] == FAMILY_WARNINGS["hi"]
        await caller.send_str(json.dumps({"type": "hangup"}))
    run(body, tmp_path, family=FAMILY)


def test_family_voice_is_off_unless_the_receiver_asks(tmp_path):
    async def body(http, fake, _):
        receiver, caller, msgs, alerts = await connect_and_speak(http, "&lang=kn-IN")
        audio = next(m for m in msgs if m["type"] == "warnings")["audio"]
        assert base64.b64decode(audio["high"]).startswith(b"RIFFstandard")
        assert all(a.get("voice") is None for a in alerts)
        await caller.send_str(json.dumps({"type": "hangup"}))
    run(body, tmp_path, family=FAMILY)


def test_family_voice_request_without_a_profile_falls_back(tmp_path):
    async def body(http, fake, _):
        info = await (await http.get(f"/info?key={KEY}")).json()
        assert info["family"] is None
        receiver, caller, msgs, alerts = await connect_and_speak(http, "&lang=en-IN&family=1")
        assert all(a.get("voice") is None for a in alerts)
        await caller.send_str(json.dumps({"type": "hangup"}))
    run(body, tmp_path)


def test_unknown_language_is_rejected(tmp_path):
    async def body(http, fake, _):
        assert (await http.get(f"/ws/call?role=receiver&key={KEY}&lang=ta-IN")).status == 400
    run(body, tmp_path)
