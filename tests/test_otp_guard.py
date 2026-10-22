"""OTP guard, family guardian and scam types. Relay tests use fake phones and a fake Gnani: no credits."""
import asyncio
import json

import pytest
from aiohttp.test_utils import TestClient, TestServer
from websockets.asyncio.server import serve

from detector import detect_rules
from otp_guard import spoken_digits
from phone_relay import Relay
from test_live import FakeGnani
from test_phone_relay import KEY, SCRIPT, drain, frame, next_audio, receive_until, tts_server
from test_sentinel import make_client


@pytest.mark.parametrize("text, n", [
    ("4 7 2 9 1 8", 6), ("472918", 6), ("four seven two nine", 4),
    ("ಫೋರ್ ಸೆವೆನ್ ಟು ನೈನ್", 3),                       # ಟು is also "to", so it is not counted
    ("ನಾಲ್ಕು ಏಳು ಎರಡು ಒಂಬತ್ತು", 4), ("चार सात नौ", 3), ("char saat nau ek", 4),
    ("೪೭೨೯", 4), ("I will call 1930 now", 0), ("ನಿಮ್ಮ ಮೊಬೈಲಿಗೆ ಒಂದು ಒಟಿಪಿ ಬಂದಿದೆ", 1), ("ok thank you", 0),
])
def test_spoken_digits(text, n):
    assert spoken_digits(text) == n


@pytest.mark.parametrize("text, kind", [
    # From two-phone test calls
    ("ನಾನು ಸಬ್ ಇನ್ಸ್ಪೆಕ್ಟರ್ ರಾಜು ಮಾತಾಡ್ತಾ ಇದ್ದೀನಿ ನಿಮ್ಮ ಮಗ ನಮ್ಮ ಕಸ್ಟಡಿಯಲ್ಲಿದ್ದಾನೆ "
     "ನೀವು ಬೇಗ ನಮಗೆ ಐದು ಲಕ್ಷ ರೂಪಾಯಿ ಟ್ರಾನ್ಸ್ಫರ್ ಮಾಡೋದಲ್ಲಿ ನಾವು ನಿಮ್ಮ ಮಗನನ್ನು ಬಿಟ್ಟುಕೊಡ್ತೀವಿ", "family_emergency"),
    ("मैं आर बी आई से बात कर रहा हूँ अगर आपको केवाईसी बैंक का केवाईसी अपडेट करना है तो हम एक ओटीपी शेयर कर रहे हैं",
     "kyc_bank"),
    ("This is the cyber crime branch. There is an arrest warrant against you. Tell me the OTP.", "digital_arrest"),
    ("Your FedEx parcel has drugs. Pay the customs fee by UPI now.", "courier"),
    ("Please install AnyDesk so I can fix your account.", "remote_access"),
    ("Sir an OTP has come to your phone, can you tell me the number?", "otp_theft"),
])
def test_scam_type_is_named(text, kind):
    assert detect_rules(text).scam_type == kind


def test_no_tactics_no_scam_type():
    assert detect_rules("Hello, are you coming for dinner tonight?").scam_type is None


# ---- relay: OTP guard + family guardian ----------------------------------------------------------
RECEIVER_BYTE = 0xEE


def receiver_frame() -> bytes:
    return bytes([RECEIVER_BYTE, 1]) * 320


class SplitGnani(FakeGnani):
    """One fake server for both streams: the first audio frame tells which phone a connection carries."""

    def __init__(self, caller_script, receiver_script, frames_per_segment=10):
        super().__init__(script=[], frames_per_segment=frames_per_segment)
        self.scripts = {"caller": list(caller_script), "receiver": list(receiver_script)}

    async def handler(self, ws):
        conn = {"sizes": [], "side": None}
        self.connections.append(conn)
        await ws.send(json.dumps({"type": "connected", "timestamp": "t", "config": {}}))
        n = 0
        async for data in ws:
            n += 1
            conn["sizes"].append(len(data))
            if conn["side"] is None:
                conn["side"] = "receiver" if data[0] == RECEIVER_BYTE else "caller"
            script = self.scripts[conn["side"]]
            if n % self.fps == 0 and script:
                await ws.send(json.dumps({"type": "processing", "timestamp": "t"}))
                await ws.send(json.dumps({"type": "transcript", "timestamp": "t", "text": script.pop(0),
                                          "audio_duration_ms": 900, "latency": 100}))


def run_split(body, tmp_path, caller_script, receiver_script):
    async def main():
        fake = SplitGnani(caller_script, receiver_script)
        async with serve(fake.handler, "127.0.0.1", 0) as gnani:
            port = gnani.sockets[0].getsockname()[1]
            client, _ = make_client(tmp_path, tts_server)
            relay = Relay("test-key", key=KEY, lang="en-IN", gnani_url=f"ws://127.0.0.1:{port}", client=client,
                          save_dir=None, pace=False, flush_seconds=0.1, drain_timeout=2, settle_seconds=0.1)
            async with TestClient(TestServer(relay.app())) as http:
                return await body(http, fake)
    return asyncio.run(main())


async def speak(ws, frames):
    for f in frames:
        await ws.send_bytes(f)
        await asyncio.sleep(0.005)


def test_guardian_is_told_the_scam_type_and_the_otp_guard_stops_the_readout(tmp_path):
    async def body(http, fake):
        assert "Family guardian" in await (await http.get("/guardian")).text()
        ops = await http.ws_connect(f"/ws/ops?key={KEY}")
        guardian = await http.ws_connect(f"/ws/guardian?key={KEY}")
        await receive_until(guardian, "call")                                   # idle
        receiver = await http.ws_connect(f"/ws/call?role=receiver&key={KEY}&lang=en-IN&guard=1")
        caller = await http.ws_connect(f"/ws/call?role=caller&key={KEY}")
        msgs, _ = await receive_until(receiver, "warnings")
        connected = next(m for m in msgs if m["type"] == "connected")
        assert connected["guard"] is True and connected["guardians"] == 1
        assert set(msgs[-1]["audio"]) == {"medium", "high", "guard"}           # "Stop!" audio prepared
        await receive_until(caller, "connected")

        await speak(caller, [frame(n) for n in range(60)])                     # the scammer asks for the OTP
        alerts = []
        while not any(a["level"] == "high" for a in alerts):
            more, _ = await receive_until(receiver, "alert", timeout=10)
            alerts += [m for m in more if m["type"] == "alert"]
        high = next(a for a in alerts if a["level"] == "high")
        assert high["family_told"] is True and high["scam_label"] == "Fake police / digital arrest"

        g_msgs = []
        while not any(m["type"] == "alert" and m["level"] == "high" for m in g_msgs):
            more, _ = await receive_until(guardian, "alert", timeout=10)
            g_msgs += more
        g_high = next(m for m in g_msgs if m["type"] == "alert" and m["level"] == "high")
        assert g_high["scam_label"] == "Fake police / digital arrest"
        assert "asking for OTP, PIN or passwords" in g_high["reasons"] and g_high["caller_said"]

        await speak(receiver, [receiver_frame()] * 20)                         # ...and they start reading it out
        r_msgs, _ = await receive_until(receiver, "guard", timeout=10)
        assert r_msgs[-1]["message"] == "Stop! Don't say the numbers. Never tell anyone your OTP."
        await receive_until(guardian, "guard")
        await drain(caller)

        await receiver.send_bytes(receiver_frame())                             # their voice is now blocked
        with pytest.raises(asyncio.TimeoutError):
            await next_audio(caller, timeout=0.5)
        await receiver.send_str(json.dumps({"type": "unmute"}))                # their choice to undo it
        await asyncio.sleep(0.1)
        await receiver.send_bytes(receiver_frame())
        assert await next_audio(caller) == receiver_frame()

        await caller.send_str(json.dumps({"type": "hangup"}))
        ops_msgs, _ = await receive_until(ops, "guard_done", timeout=15)
        heard = [m for m in ops_msgs if m["type"] == "heard"]
        assert heard and all("text" not in m for m in heard)                    # their words never leave the server
        assert any(m["type"] == "guard" for m in ops_msgs)
        assert {c["side"] for c in fake.connections} == {"caller", "receiver"}
    run_split(body, tmp_path, SCRIPT, ["four seven nine one eight"])


def test_digits_before_any_otp_request_do_not_trigger_the_guard(tmp_path):
    async def body(http, fake):
        receiver = await http.ws_connect(f"/ws/call?role=receiver&key={KEY}&lang=en-IN&guard=1")
        caller = await http.ws_connect(f"/ws/call?role=caller&key={KEY}")
        await receive_until(receiver, "warnings")
        await speak(receiver, [receiver_frame()] * 20)        # "my flat is 4 2 1": nobody asked for an OTP
        await asyncio.sleep(0.5)
        await caller.send_str(json.dumps({"type": "hangup"}))
        msgs = await drain(receiver)
        assert not any(m.get("type") == "guard" for m in msgs)
        assert any(c["side"] == "receiver" for c in fake.connections)
    run_split(body, tmp_path, ["hello how are you"], ["my flat number is 4 2 1"])


def test_speakerphone_listener_warns_during_a_real_call_and_tells_the_guardian(tmp_path):
    """One device next to a phone call on speaker: one stream hears both people."""
    async def body(http, fake, _):
        guardian = await http.ws_connect(f"/ws/guardian?key={KEY}")
        await receive_until(guardian, "call")
        listener = await http.ws_connect(f"/ws/call?role=listener&key={KEY}&lang=en-IN&guard=1")
        msgs, _ = await receive_until(listener, "warnings")                    # starts alone, at once
        assert set(msgs[-1]["audio"]) == {"medium", "high", "guard"}
        busy = await http.ws_connect(f"/ws/call?role=caller&key={KEY}")
        b_msgs, _ = await receive_until(busy, "error")
        assert "busy" in b_msgs[-1]["message"]

        await speak(listener, [frame(n) for n in range(80)])
        got, alerts = [], []
        while not any(m["type"] == "guard" for m in got):
            more, _ = await receive_until(listener, "guard", timeout=10)
            got += more
        alerts = [m for m in got if m["type"] == "alert"]
        assert [a["level"] for a in alerts] == ["medium", "high"]
        high = alerts[-1]
        assert high["scam_label_en"] == "Fake police / digital arrest" and high["caller_said"]
        guard = next(m for m in got if m["type"] == "guard")
        assert guard["cut"] is False                                            # nothing to cut on a speakerphone
        g_msgs, _ = await receive_until(guardian, "guard", timeout=10)
        assert any(m["type"] == "alert" and m["level"] == "high" for m in g_msgs)
        await listener.send_str(json.dumps({"type": "hangup"}))
        assert len(fake.connections) == 1                                       # one stream: ~0.44 credits/min
    from test_phone_relay import run
    run(body, tmp_path, script=SCRIPT + ["four seven nine one"])


def test_guard_is_off_unless_the_protected_person_asks(tmp_path):
    async def body(http, fake):
        receiver = await http.ws_connect(f"/ws/call?role=receiver&key={KEY}&lang=en-IN")
        caller = await http.ws_connect(f"/ws/call?role=caller&key={KEY}")
        msgs, _ = await receive_until(receiver, "warnings")
        assert set(msgs[-1]["audio"]) == {"medium", "high"}
        await speak(receiver, [receiver_frame()] * 20)
        await asyncio.sleep(0.3)
        await caller.send_str(json.dumps({"type": "hangup"}))
        await asyncio.sleep(0.3)
        assert all(c["side"] != "receiver" for c in fake.connections)          # no second stream, no cost
    run_split(body, tmp_path, ["hello"], ["one two three"])
