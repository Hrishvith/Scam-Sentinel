"""Protected calling line, end to end on localhost: two fake phones, a fake Gnani STT server,
a fake Timbre client. No network, no credits."""
import asyncio
import json

from aiohttp import WSMsgType
from aiohttp.test_utils import TestClient, TestServer
from websockets.asyncio.server import serve

from budget import read_ledger
from phone_relay import Relay
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


def run(body, tmp_path, script=SCRIPT):
    async def main():
        fake = FakeGnani(script=list(script), frames_per_segment=10)
        async with serve(fake.handler, "127.0.0.1", 0) as gnani:
            port = gnani.sockets[0].getsockname()[1]
            client, tts_calls = make_client(tmp_path, lambda url, kw, n: FakeResp(content=b"RIFF" + bytes(40)))
            relay = Relay("test-key", key=KEY, lang="en-IN", gnani_url=f"ws://127.0.0.1:{port}", client=client,
                          save_dir=None, pace=False, flush_seconds=0.1, drain_timeout=2, settle_seconds=0.1)
            async with TestClient(TestServer(relay.app())) as http:
                return await body(http, fake, tts_calls)
    return asyncio.run(main())


def test_wrong_key_is_refused_everywhere(tmp_path):
    async def body(http, fake, _):
        for path in ("/ws/call?role=caller&key=nope", "/ws/ops?key=nope", "/info?key=nope"):
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
