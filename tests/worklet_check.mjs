// Runs web/pcm-worklet.js outside a browser with minimal stand-ins, and checks the audio maths.
import { readFileSync } from "node:fs";
const procs = {};
globalThis.sampleRate = Number(process.argv[2] || 48000);
globalThis.AudioWorkletProcessor = class { constructor() { this.port = { posted: [], postMessage(m) { this.posted.push(m); }, onmessage: null }; } };
globalThis.registerProcessor = (name, cls) => { procs[name] = cls; };
new Function(readFileSync(new URL("../web/pcm-worklet.js", import.meta.url), "utf8"))();

const SR = globalThis.sampleRate, HZ = 440, SECONDS = 1;
const cap = new procs.capture();
const total = SR * SECONDS;
for (let start = 0; start < total; start += 128) {          // browsers call process() with 128-sample blocks
  const block = new Float32Array(128).map((_, k) => 0.5 * Math.sin(2 * Math.PI * HZ * (start + k) / SR));
  cap.process([[block]], [[new Float32Array(128)]]);
}
const frames = cap.port.posted.map((b) => new Int16Array(b));
const net = Int16Array.from(frames.flatMap((f) => Array.from(f)));
function zeroCrossHz(xs, rate) { let c = 0; for (let i = 1; i < xs.length; i++) if ((xs[i - 1] < 0) !== (xs[i] < 0)) c++; return c / 2 / (xs.length / rate); }

const player = new procs.player();
const outBlocks = [];
let sent = 0, duckedPeak = 0;
const blocks = Math.floor(total / 128);
for (let i = 0; i < blocks; i++) {
  // the network delivers one 20 ms frame per 20 ms of playback, starting 3 frames ahead
  while (sent < frames.length && sent * 0.02 <= (i * 128) / SR + 0.06) player.port.onmessage({ data: frames[sent++].buffer });
  if (i === Math.floor(blocks / 2)) player.port.onmessage({ data: { gain: 0.25 } });   // a warning starts
  const o = new Float32Array(128);
  player.process([], [[o]]);
  if (i > blocks / 2 + 1 && i < blocks / 2 + 20) duckedPeak = Math.max(duckedPeak, ...o.map(Math.abs));
  outBlocks.push(...o);
}
const played = outBlocks.slice(Math.floor(SR * 0.1), Math.floor(SR * 0.45));   // before the warning
const ducked = [duckedPeak];

console.log(JSON.stringify({
  frames: frames.length, frame_bytes: frames[0].byteLength,
  net_seconds: net.length / 16000, net_hz: zeroCrossHz(net, 16000),
  net_peak: Math.max(...net.map(Math.abs)),
  played_hz: zeroCrossHz(played, SR), played_peak: Math.max(...played.map(Math.abs)),
  ducked_peak: Math.max(...ducked.map(Math.abs)),
}));
