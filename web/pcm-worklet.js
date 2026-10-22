// Audio worklets for the protected calling line.
// capture: microphone (any device rate) -> 16 kHz mono s16le, posted in 20 ms (640-byte) messages.
// player:  16 kHz s16le frames from the network -> device rate, with a small jitter buffer and a gain
//          the page lowers while a warning plays.
const NET_RATE = 16000;
const FRAME = 320; // samples per 20 ms

class Capture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.step = sampleRate / NET_RATE; // input samples per output sample
    this.pos = 0;                      // fractional read position into the current block
    this.out = new Int16Array(FRAME);
    this.n = 0;
  }
  process(inputs, outputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    while (this.pos < ch.length) {
      const i = Math.floor(this.pos);
      const f = this.pos - i;
      const a = ch[i];
      const b = i + 1 < ch.length ? ch[i + 1] : ch[i];
      let s = a + (b - a) * f;
      s = Math.max(-1, Math.min(1, s));
      this.out[this.n++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      if (this.n === FRAME) {
        this.port.postMessage(this.out.buffer.slice(0));
        this.n = 0;
      }
      this.pos += this.step;
    }
    this.pos -= ch.length;
    return true;
  }
}

class Player extends AudioWorkletProcessor {
  constructor() {
    super();
    this.step = NET_RATE / sampleRate; // network samples per output sample
    this.queue = [];
    this.cur = null;
    this.pos = 0;
    this.gain = 1;
    this.primed = false;               // wait for 3 frames (60 ms) before playing: absorbs jitter
    this.port.onmessage = (e) => {
      if (e.data && e.data.gain !== undefined) { this.gain = e.data.gain; return; }
      this.queue.push(new Int16Array(e.data));
      if (this.queue.length > 30) this.queue.splice(0, this.queue.length - 10); // drop lag, stay live
    };
  }
  process(inputs, outputs) {
    const out = outputs[0][0];
    for (let k = 0; k < out.length; k++) {
      if (!this.cur) {
        if (!this.primed && this.queue.length < 3) { out[k] = 0; continue; }
        this.primed = true;
        this.cur = this.queue.shift() || null;
        if (!this.cur) { this.primed = false; out[k] = 0; continue; } // underrun: re-prime
      }
      const i = Math.floor(this.pos);
      const f = this.pos - i;
      const a = this.cur[i];
      const b = i + 1 < this.cur.length ? this.cur[i + 1] : a;
      out[k] = ((a + (b - a) * f) / 32768) * this.gain;
      this.pos += this.step;
      if (this.pos >= this.cur.length) { this.pos -= this.cur.length; this.cur = null; }
    }
    return true;
  }
}

registerProcessor("capture", Capture);
registerProcessor("player", Player);
