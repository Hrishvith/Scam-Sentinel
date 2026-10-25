"""Captures real Scam Sentinel screens in re-enacted states (for the promo video), at phone size.

Drives a hidden Edge through the DevTools protocol: opens each real page on the local server, puts it in the state
a re-enacted call would produce (e.g. the OTP STOP screen), and saves a screenshot to video/screens/.
No credits: no call is connected and no Gnani request is made. Keys and QR codes are hidden in the shots.

  python video/capture_screens.py
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "video" / "screens"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9333
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "video" / "build2"
KEY = (SCRATCH / "relay_key.txt").read_text(encoding="ascii").strip() if (SCRATCH / "relay_key.txt").exists() else ""
BASE = "http://localhost:8765"

# a fake call already in progress, the way the call page sets itself up after "Turn on protection"
IN_CALL = """
  applyWords(); show("incall"); window.Sentinel.inCall(true);
  $("riskcard").classList.remove("hidden"); setRisk("low", 0);
"""
CONNECTED = IN_CALL + """
  await onControl({type: "connected", guardians: 1}); clearInterval(timerId); $("timer").textContent = "0:%s";
"""
TRICKS = {"authority": "pretending to be police or an official", "threat": "threat of arrest or legal case",
          "secrecy": "asking you to keep it secret or stay on the line", "payment": "pushing you to transfer money"}


def tricks_js(ids):
    return "showTricks(%s);" % json.dumps([{"id": i, "label": TRICKS[i]} for i in ids])


ALERT_HIGH = {"type": "alert", "level": "high", "at": 21.0, "scam_label": "Fake family emergency",
              "message": "Warning! This looks like a scam call. Hang up now. Do not share your OTP, PIN or send any money.",
              "tip": "Police never ask for money to release anyone. Hang up and call your family member yourself.",
              "family_told": True, "caller_said": ["We have arrested your son in a serious case.", "Transfer five lakh rupees now."],
              "voice": "AI clone of a family member's voice (made with consent)"}

SHOTS = [
    # name, path, js to run after load, viewport (w, h, scale)
    ("home_en", "/?key={k}&lang=en", "", None),
    ("home_kn", "/?key={k}&lang=kn", "", None),
    ("home_hi", "/?key={k}&lang=hi", "", None),
    ("setup_en", "/?role=receiver&key={k}&lang=en", "", None),
    ("protection_on", "/?role=receiver&key={k}&lang=en", IN_CALL + 'await onControl({type: "waiting"});', None),
    ("call_safe", "/?role=receiver&key={k}&lang=en", CONNECTED % "07" + tricks_js([]) + 'setRisk("low", 1.0);', None),
    ("call_careful", "/?role=receiver&key={k}&lang=en", CONNECTED % "14" + tricks_js(["authority", "threat"]) +
     'setRisk("medium", 4.5); onAlert({type:"alert",level:"medium",at:12.4,scam_label:"Fake police / digital arrest",'
     'message:"Be careful! This call is suspicious. Before sharing an OTP or sending money, ask your family."});'
     '$("banner").classList.remove("show");', None),
    ("call_scam", "/?role=receiver&key={k}&lang=en",
     '$("cname").value = "Son"; $("cnum").value = "0000000000";' + CONNECTED % "21" +
     tricks_js(["authority", "threat", "secrecy", "payment"]) + "onAlert(%s);" % json.dumps(ALERT_HIGH), None),
    ("otp_stop", "/?role=receiver&key={k}&lang=en", CONNECTED % "33" + tricks_js(["authority", "threat", "payment"]) +
     'setRisk("high", 9); onGuard({type:"guard", message:"Stop! Don\'t say the numbers. Never tell anyone your OTP.", cut:true});', None),
    ("after_question", "/?role=receiver&key={k}&lang=en", CONNECTED % "40" +
     'seen.worst="high"; seen.label="Fake family emergency"; seen.labelEn="Fake family emergency"; seen.alerts=["medium at 12.4 s","high at 21.0 s"];'
     'seen.caller=["We have arrested your son in a serious case."]; end("Call ended"); window.scrollTo(0, 0);', None),
    ("after_yes", "/?role=receiver&key={k}&lang=en", CONNECTED % "40" +
     'seen.worst="high"; seen.label="Fake family emergency"; end("Call ended"); $("a-yes").click();'
     '$("after").scrollIntoView();', None),
    ("after_no", "/?role=receiver&key={k}&lang=en", CONNECTED % "40" +
     'seen.worst="high"; seen.label="Fake family emergency"; seen.labelEn="Fake family emergency"; seen.alerts=["high at 21.0 s"];'
     'seen.caller=["We have arrested your son in a serious case."]; end("Call ended"); $("a-no").click();'
     '$("a-note").textContent = report(); $("after").scrollIntoView();', None),
    ("listener_setup", "/?role=listener&key={k}&lang=en", "", None),
    ("sos", "/?key={k}&lang=en", "window.Sentinel.openHelp();", None),
    ("textsize_1", "/?key={k}&lang=en", 'document.querySelector("main").style.zoom = 1.15;', None),
    ("textsize_2", "/?key={k}&lang=en", 'document.querySelector("main").style.zoom = 1.3;', None),
    ("guardian_watch", "/guardian?key={k}&lang=en",
     '$("start").click(); await new Promise(r => setTimeout(r, 400));'
     'setStatus("On a call · protected", "var(--good)", "Language: Kannada · OTP guard on");'
     'add("info", "📞 10:42 · A call started. Scam Sentinel is listening for scam tricks.");', None),
    ("guardian_alarm", "/guardian?key={k}&lang=en",
     '$("num").value = "0000000000"; $("start").click(); await new Promise(r => setTimeout(r, 400));'
     'add("info", "📞 10:42 · A call started. Scam Sentinel is listening for scam tricks.");'
     'onAlert({level:"high", scam_label:"Fake family emergency", reasons:["pretending to be police or an official",'
     '"threat of arrest or legal case","pushing you to transfer money"], caller_said:["We have arrested your son in a serious case.",'
     '"Transfer five lakh rupees now."], tip:"Police never ask for money to release anyone. Hang up and call your family member yourself."});'
     'stopRing();', None),
    ("scams_grid", "/scams?key={k}&lang=en", "await new Promise(r => setTimeout(r, 600)); window.scrollTo(0, 520);", None),
    ("scams_open", "/scams?key={k}&lang=en",
     'await new Promise(r => setTimeout(r, 600)); document.querySelector(".scam .head").click();'
     'document.querySelector(".scam.open").scrollIntoView();', None),
    ("scams_scene", "/scams?key={k}&lang=en",
     'await new Promise(r => setTimeout(r, 600)); document.querySelector(".scam .head").click();'
     'const pl = document.querySelector(".scam.open .play"); pl.click(); await new Promise(r => setTimeout(r, 7000));'
     'document.querySelector(".scam.open .sim").scrollIntoView({block: "end"});', None),
    ("quiz_right", "/practice?key={k}&lang=en",
     'await new Promise(r => setTimeout(r, 500)); const it = items[order[at]]; answer(it.scam);'
     'await new Promise(r => setTimeout(r, 600));', None),
    ("quiz_score", "/practice?key={k}&lang=en",
     'await new Promise(r => setTimeout(r, 500)); for (let i = 0; i < order.length; i++) { const it = items[order[at]];'
     'await answer(i === 3 ? !it.scam : it.scam); $("next").click(); }', None),
    ("check_call", "/practice?key={k}&lang=en",
     'await new Promise(r => setTimeout(r, 500)); tab("check");'
     '$("text").value = "This is the police. We have arrested your son. Do not tell anyone. Transfer five lakh rupees now.";'
     'await runCheck(); window.scrollTo(0, 260);', None),
    ("operator", "/operator?key={k}", "OPERATOR", (1600, 1500, 1)),
]

# The operator view: hide the session key and replace the QR codes with harmless ones, then replay a short
# re-enacted call into its event handler so the transcript, risk and warnings show.
OPERATOR_JS = """
  await new Promise(r => setTimeout(r, 800));
  document.querySelectorAll(".link").forEach(e => e.textContent = "https://•••••.trycloudflare.com/?role=…&key=•••••");
  document.querySelectorAll("[id^=qr-]").forEach(e => { e.innerHTML = ""; new QRCode(e, {text: "https://example.invalid/scam-sentinel-demo", width: 150, height: 150}); });
  const ws = window.__ws; const send = (m) => ws.onmessage({data: JSON.stringify(m)});
  send({type: "peer", role: "receiver", joined: true}); send({type: "peer", role: "caller", joined: true});
  send({type: "guardians", count: 1}); send({type: "call", state: "connected", lang: "en-IN", guard: true});
  const lines = [[3.1, "Hello, this is Sub-Inspector Raju from the police station.", "low", 1.5],
                 [8.7, "We have arrested your son in a serious case.", "medium", 4.0],
                 [13.2, "Don't tell anyone about this.", "high", 6.0],
                 [18.9, "Transfer five lakh rupees now and we will release him.", "high", 12.0]];
  for (const [at, text, level, score] of lines) send({type: "transcript", at, text, level, score, echo: false});
  send({type: "alert", level: "medium", at: 8.7, scam_label: "Fake family emergency", message: "Be careful! This call is suspicious.",
        reasons: ["threat of arrest or legal case", "pretending to be police or an official"], family_told: true});
  send({type: "alert", level: "high", at: 13.2, scam_label: "Fake family emergency", message: "Warning! This looks like a scam call. Hang up now.",
        reasons: ["threat of arrest or legal case", "asking you to keep it secret", "pretending to be police or an official"], family_told: true,
        voice: "AI clone of a family member's voice (made with consent)"});
  send({type: "guard", at: 24.6, digits: 3});
  send({type: "done", seconds_streamed: 31.0, level: "high", time_to_alert: {medium: 8.7, high: 13.2}});
"""
WS_HOOK = """
  (() => { const W = window.WebSocket; window.WebSocket = function (...a) { const s = new W(...a); window.__ws = s; return s; };
           window.WebSocket.prototype = W.prototype; Object.assign(window.WebSocket, W); })();
"""


class Browser:
    def __init__(self):
        self.proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--remote-debugging-port={PORT}",
                                      f"--user-data-dir={ROOT / 'video' / 'build2' / 'cdp-profile'}", "--autoplay-policy=no-user-gesture-required",
                                      "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=2))
                page = next(p for p in pages if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        self.ws = connect(page["webSocketDebuggerUrl"], max_size=50_000_000)
        self.n = 0
        self.cmd("Page.enable"); self.cmd("Runtime.enable")

    def cmd(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def shot(self, name, url, js, size):
        w, h, scale = size or (412, 920, 2)
        lang = url.split("lang=")[1][:2] if "lang=" in url else "en"
        self.cmd("Page.navigate", url=BASE + "/icons/favicon.png")      # same site: set the remembered language first
        time.sleep(0.3)
        self.cmd("Runtime.evaluate", expression=f"localStorage.setItem('sentinel-lang','{lang}'); localStorage.setItem('sentinel-practice-lang','{lang}')")
        self.cmd("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=scale, mobile=size is None)
        self.cmd("Page.navigate", url=url)
        time.sleep(1.6)
        if js:
            code = OPERATOR_JS if js == "OPERATOR" else js
            r = self.cmd("Runtime.evaluate", expression=f"(async () => {{ {code} }})()", awaitPromise=True)
            if r.get("exceptionDetails"):
                print(f"  {name}: JS error {r['exceptionDetails'].get('exception', {}).get('description', '')[:200]}")
            time.sleep(0.9)
        png = base64.b64decode(self.cmd("Page.captureScreenshot", format="png")["data"])
        (OUT / f"{name}.png").write_bytes(png)
        # leave the page without a "leave site?" prompt
        self.cmd("Runtime.evaluate", expression="window.onbeforeunload = null; try { Sentinel.inCall(false) } catch (e) {}")
        print(f"  {name}")

    def close(self):
        self.ws.close(); self.proc.kill()


def main() -> int:
    if not KEY:
        sys.exit("No server key: start phone_relay.py and pass the folder holding relay_key.txt")
    OUT.mkdir(parents=True, exist_ok=True)
    b = Browser()
    try:
        b.cmd("Page.addScriptToEvaluateOnNewDocument", source=WS_HOOK)
        for name, path, js, size in SHOTS:
            b.shot(name, BASE + path.format(k=KEY), js, size)
    finally:
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
