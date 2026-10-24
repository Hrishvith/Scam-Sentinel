// Shared by every phone page: one language for the whole site, a big-text button, the bottom bar
// (Home · Practice · Real scams · Help) and the "I was cheated" help screen. Made for people who
// are new to smartphones: big targets, few words, their own language. REVIEW kn/hi with native speakers.
(function () {
  const params = new URLSearchParams(location.search);
  const key = params.get("key") || "";
  const k = encodeURIComponent(key);

  function stored(name, value) {           // browser storage can be unavailable: never rely on it
    try { if (value === undefined) return localStorage.getItem(name); localStorage.setItem(name, value); } catch (_) { return null; }
  }
  function prefs() { try { return JSON.parse(stored("sentinel-prefs") || "{}"); } catch (_) { return {}; } }

  const WORDS = {
    en: { back: "Back", home: "Home", practice: "Practice", scams: "Real scams", help: "Help", bigger: "Text size",
          sosTitle: "Were you cheated?", sosSub: "Don't worry. Do these now, one by one. The first hour matters most.",
          s1: "📞 Call 1930: cyber crime helpline", s1n: "They can try to stop the money. Tell them what happened.",
          s2: "🏦 Call your bank", s2n: "Use the number on the back of your card. Ask them to block your card and UPI.",
          s3: "👪 Call {name}", s3n: "Tell your family now. It is not your fault.", s3x: "👪 Call your family",
          s4: "🌐 File a complaint online", s4n: "cybercrime.gov.in",
          calm: "Got a scary call right now? Just hang up. It is always OK to hang up: real police and real banks never mind.",
          close: "Close", pick: "Choose your language", now: "Ready to use", soon: "Coming soon",
          soonNote: "These languages need native speakers to check the words and voices first." },
    kn: { back: "ಹಿಂದೆ", home: "ಮುಖಪುಟ", practice: "ಅಭ್ಯಾಸ", scams: "ನಿಜವಾದ ಮೋಸಗಳು", help: "ಸಹಾಯ", bigger: "ಅಕ್ಷರದ ಗಾತ್ರ",
          sosTitle: "ನಿಮಗೆ ಮೋಸ ಆಯಿತೇ?", sosSub: "ಗಾಬರಿ ಬೇಡ. ಈಗಲೇ ಇವುಗಳನ್ನು ಒಂದೊಂದಾಗಿ ಮಾಡಿ. ಮೊದಲ ಒಂದು ಗಂಟೆ ಬಹಳ ಮುಖ್ಯ.",
          s1: "📞 1930 ಗೆ ಕರೆ ಮಾಡಿ: ಸೈಬರ್ ಅಪರಾಧ ಸಹಾಯವಾಣಿ", s1n: "ಅವರು ಹಣವನ್ನು ತಡೆಯಲು ಪ್ರಯತ್ನಿಸುತ್ತಾರೆ. ಏನಾಯಿತು ಎಂದು ಹೇಳಿ.",
          s2: "🏦 ನಿಮ್ಮ ಬ್ಯಾಂಕಿಗೆ ಕರೆ ಮಾಡಿ", s2n: "ಕಾರ್ಡ್ ಹಿಂದಿರುವ ಸಂಖ್ಯೆಗೆ ಕರೆ ಮಾಡಿ. ಕಾರ್ಡ್ ಮತ್ತು ಯುಪಿಐ ಬ್ಲಾಕ್ ಮಾಡಲು ಹೇಳಿ.",
          s3: "👪 {name} ಅವರಿಗೆ ಕರೆ ಮಾಡಿ", s3n: "ಈಗಲೇ ಮನೆಯವರಿಗೆ ತಿಳಿಸಿ. ಇದು ನಿಮ್ಮ ತಪ್ಪಲ್ಲ.", s3x: "👪 ಮನೆಯವರಿಗೆ ಕರೆ ಮಾಡಿ",
          s4: "🌐 ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ದೂರು ನೀಡಿ", s4n: "cybercrime.gov.in",
          calm: "ಈಗ ಹೆದರಿಸುವ ಕರೆ ಬಂದಿದೆಯೇ? ಕರೆ ಕಟ್ ಮಾಡಿ. ಕರೆ ಕಟ್ ಮಾಡುವುದು ಯಾವಾಗಲೂ ಸರಿ: ನಿಜವಾದ ಪೊಲೀಸರು, ಬ್ಯಾಂಕಿನವರು ಬೇಸರಿಸುವುದಿಲ್ಲ.",
          close: "ಮುಚ್ಚಿ", pick: "ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ", now: "ಈಗ ಬಳಸಬಹುದು", soon: "ಶೀಘ್ರದಲ್ಲೇ",
          soonNote: "ಈ ಭಾಷೆಗಳ ಪದಗಳು ಮತ್ತು ಧ್ವನಿಗಳನ್ನು ಮೊದಲು ಆ ಭಾಷೆಯವರು ಪರಿಶೀಲಿಸಬೇಕು." },
    hi: { back: "पीछे", home: "होम", practice: "अभ्यास", scams: "असली धोखे", help: "मदद", bigger: "अक्षर का आकार",
          sosTitle: "क्या आपके साथ धोखा हुआ?", sosSub: "घबराइए मत। अभी ये काम एक-एक करके करें। पहला एक घंटा सबसे ज़रूरी है।",
          s1: "📞 1930 पर कॉल करें: साइबर क्राइम हेल्पलाइन", s1n: "वे पैसे रोकने की कोशिश करते हैं। उन्हें बताएँ क्या हुआ।",
          s2: "🏦 अपने बैंक को कॉल करें", s2n: "कार्ड के पीछे लिखे नंबर पर कॉल करें। कार्ड और यूपीआई ब्लॉक करवाएँ।",
          s3: "👪 {name} को कॉल करें", s3n: "अभी घरवालों को बताएँ। इसमें आपकी गलती नहीं है।", s3x: "👪 घरवालों को कॉल करें",
          s4: "🌐 ऑनलाइन शिकायत करें", s4n: "cybercrime.gov.in",
          calm: "अभी डराने वाली कॉल आई है? बस कॉल काट दें। कॉल काटना हमेशा ठीक है: असली पुलिस और असली बैंक बुरा नहीं मानते।",
          close: "बंद करें", pick: "अपनी भाषा चुनें", now: "अभी इस्तेमाल करें", soon: "जल्द आ रहा है",
          soonNote: "इन भाषाओं के शब्द और आवाज़ें पहले उस भाषा के लोग जाँचेंगे।" },
  };
  const NAMES = { kn: "ಕನ್ನಡ", hi: "हिन्दी", en: "English" };
  const ENGLISH = { kn: "Kannada", hi: "Hindi", en: "English" };
  // Regional languages shown as "coming soon": the warnings, scam words and voices are not ready in them yet
  const SOON = [["தமிழ்", "Tamil"], ["తెలుగు", "Telugu"], ["മലയാളം", "Malayalam"], ["मराठी", "Marathi"],
                ["বাংলা", "Bengali"], ["ગુજરાતી", "Gujarati"], ["ਪੰਜਾਬੀ", "Punjabi"], ["ଓଡ଼ିଆ", "Odia"]];

  function getLang() {
    if (WORDS[params.get("lang")]) return params.get("lang");      // a shared link can open in a language: ?lang=kn
    const l = stored("sentinel-lang") || stored("sentinel-practice-lang") || (prefs().lang || "").split("-")[0];
    return WORDS[l] ? l : null;
  }
  function setLang(l) {
    if (!WORDS[l]) return;
    stored("sentinel-lang", l); stored("sentinel-practice-lang", l);
    if (params.has("lang")) { params.delete("lang"); history.replaceState(null, "", location.pathname + "?" + params); }
    const p = prefs(); p.lang = l + "-IN"; stored("sentinel-prefs", JSON.stringify(p));
    document.documentElement.lang = l;
    render();
    window.dispatchEvent(new CustomEvent("sentinel-lang", { detail: l }));
  }
  const w = () => WORDS[getLang() || "kn"];

  // ---- text size: three steps, remembered on this phone ----
  const SIZES = [1, 1.15, 1.3];
  // Only the page content grows: zooming <body> would also scale and shift the fixed bottom bar off the screen.
  function applySize() {
    const z = SIZES[Number(stored("sentinel-size") || 0)] || 1;
    document.querySelectorAll("main").forEach((m) => { m.style.zoom = z; });
  }
  function nextSize() { stored("sentinel-size", String((Number(stored("sentinel-size") || 0) + 1) % SIZES.length)); applySize(); }

  // ---- styles for the bar and the help screen ----
  const css = document.createElement("style");
  css.textContent = `
    /* room for the bottom bar under the last item on every page (pages lay out a full-height <main>) */
    main { padding-bottom: calc(110px + env(safe-area-inset-bottom)) !important; }
    body.sn-incall #sn-bar, body.sn-incall #sn-back, #sn-back.off { display:none; }
    header { flex-wrap:wrap; row-gap:8px; }
    #sn-back { width:auto !important; flex:none; margin:0 2px 0 0 !important; text-align:left; }
    #sn-back { display:inline-flex; align-items:center; gap:4px; min-height:46px; padding:0 14px 0 10px; margin-right:2px;
               border-radius:14px; border:2px solid rgba(255,255,255,.55); background:rgba(255,255,255,.16); color:#fff;
               font:inherit; font-size:17px; font-weight:800; cursor:pointer; }
    #sn-back .ar { font-size:22px; line-height:1; }
    body.sn-incall main { padding-bottom: 28px !important; }
    #sn-bar { position:fixed; left:0; right:0; bottom:0; z-index:9; background:#fff; border-top:2px solid #d3cdbf; box-shadow:0 -4px 16px -8px rgba(0,0,0,.25);
              display:grid; grid-template-columns:repeat(5,1fr);
              padding:6px max(4px, calc((100vw - 560px) / 2)) max(6px, env(safe-area-inset-bottom)); }
    #sn-bar a, #sn-bar button { display:flex; flex-direction:column; align-items:center; gap:3px; color:#424d4a; text-decoration:none;
              background:none; border:0; font:inherit; font-size:14px; font-weight:600; line-height:1.15; text-align:center; padding:6px 2px; border-radius:12px; cursor:pointer; min-height:60px; }
    #sn-bar .ic { font-size:24px; line-height:1; }
    #sn-bar .on { color:#0b5d4b; background:#e3efea; }
    #sn-bar .sos { color:#fff; background:#c0262d; font-weight:800; }
    #sn-help { display:none; position:fixed; inset:0; z-index:20; background:#f5f3ee; color:#17201e; overflow:auto;
               padding:max(18px, env(safe-area-inset-top)) 16px 30px; }
    #sn-help.show { display:block; }
    #sn-help .in { max-width:520px; margin:0 auto; }
    #sn-help h2 { font-size:28px; margin:6px 0 4px; } #sn-help .sub { color:#424d4a; font-size:18px; margin:0 0 14px; }
    #sn-help a.step { display:block; text-decoration:none; color:#17201e; border-radius:18px; padding:16px; margin:10px 0; background:#fff; border:2px solid #d3cdbf; }
    #sn-help a.step b { display:block; font-size:21px; } #sn-help a.step span { color:#424d4a; font-size:16px; }
    #sn-help a.step.first { background:#c0262d; border-color:#c0262d; color:#fff; } #sn-help a.step.first span { color:#fff; }
    #sn-help .num { display:inline-grid; place-items:center; width:32px; height:32px; border-radius:50%; background:#e3efea; color:#0b5d4b; margin-right:8px; font-weight:800; }
    #sn-help a.step.first .num { background:rgba(255,255,255,.25); color:#fff; }
    #sn-help .calm { background:#dff1e6; color:#0f5530; border-radius:16px; padding:14px; font-size:18px; margin-top:16px; font-weight:600; }
    #sn-help button.x { width:100%; margin-top:14px; padding:18px; border-radius:16px; border:2px solid #d3cdbf; background:#fff; color:#17201e; font:inherit; font-size:19px; font-weight:700; }
    #sn-lang { display:none; position:fixed; inset:0; z-index:21; background:#f5f3ee; color:#17201e; overflow:auto;
               padding:max(24px, env(safe-area-inset-top)) 18px 30px; text-align:center; }
    #sn-lang.show { display:block; }
    #sn-lang .in { max-width:460px; margin:0 auto; display:flex; flex-direction:column; gap:12px; }
    #sn-lang img { width:72px; height:72px; border-radius:18px; margin:0 auto 2px; }
    #sn-lang .q { font-size:20px; color:#424d4a; line-height:1.6; font-weight:700; }
    #sn-lang h3 { margin:12px 0 0; font-size:15px; text-transform:uppercase; letter-spacing:.06em; color:#424d4a; text-align:left; }
    #sn-lang button.lg { width:100%; margin:0; padding:16px 18px; font:inherit; color:#0b5d4b; background:#fff; border:3px solid #0b5d4b;
                         border-radius:20px; cursor:pointer; box-shadow:0 3px 12px -6px rgba(0,0,0,.3);
                         display:flex; align-items:center; justify-content:space-between; gap:10px; text-align:left; }
    #sn-lang button.lg b { font-size:28px; } #sn-lang button.lg small { font-size:16px; color:#424d4a; font-weight:600; }
    #sn-lang button.lg.on { background:#0b5d4b; color:#fff; } #sn-lang button.lg.on small { color:#e3efea; }
    #sn-lang .soon { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    #sn-lang .soon span { padding:12px 8px; border-radius:16px; border:2px dashed #c9c3b5; color:#56615e; background:#efece5; font-size:19px; font-weight:700; }
    #sn-lang .soon small { display:block; font-size:13px; font-weight:600; }
    #sn-lang .note { font-size:15px; color:#56615e; margin:0; }
    #sn-lang button.x { width:100%; margin-top:6px; padding:16px; border-radius:16px; border:2px solid #d3cdbf; background:#fff;
                        color:#17201e; font:inherit; font-size:19px; font-weight:700; cursor:pointer; }
    /* language bar: always visible under the header, one tap per language (no menus to find) */
    #sn-langstrip { margin:0 0 14px; padding:10px; background:#fff; border:2px solid #d3cdbf; border-radius:20px;
                    box-shadow:0 2px 10px -6px rgba(23,32,30,.3); }
    #sn-langstrip .lab { font-size:15px; font-weight:700; color:#424d4a; margin:0 4px 8px; }
    #sn-langstrip .row { display:grid; grid-template-columns:1fr 1fr 1fr auto; gap:8px; }
    #sn-langstrip button { width:auto !important; margin:0 !important; min-height:56px; padding:6px 8px; border-radius:14px; cursor:pointer;
                           font:inherit; font-size:21px; font-weight:800; color:#0b5d4b; background:#fff; border:2px solid #0b5d4b; }
    #sn-langstrip button.on { background:#0b5d4b; color:#fff; box-shadow:inset 0 0 0 3px #0b5d4b, 0 0 0 3px #bfe0d5; }
    #sn-langstrip button.more { font-size:16px; color:#424d4a; border-color:#d3cdbf; padding:6px 10px; }
    body.sn-incall #sn-langstrip { display:none; }
    header .pill { order:9; }
  `;
  document.head.append(css);

  function el(tag, attrs, text) { const e = document.createElement(tag); Object.assign(e, attrs || {}); if (text !== undefined) e.textContent = text; return e; }

  // ---- bottom bar ----
  const here = location.pathname.replace(/\/$/, "") || "/";
  const bar = el("nav", { id: "sn-bar", ariaLabel: "Scam Sentinel" });
  const items = [["home", "🏠", `/?key=${k}`, "/"], ["practice", "🎓", `/practice?key=${k}`, "/practice"],
                 ["scams", "📰", `/scams?key=${k}`, "/scams"]];
  // ---- Back button, first thing in the header ----
  const back = el("button", { id: "sn-back", type: "button" });
  let backHandler = null;           // a page can handle Back itself (e.g. setup screen -> role choice)
  back.onclick = () => {
    if (backHandler && backHandler()) return;
    const fromHere = document.referrer && new URL(document.referrer).origin === location.origin;
    if (fromHere && history.length > 1) history.back(); else location.href = `/?key=${k}`;
  };
  function setBack(handler, visible) { backHandler = handler || null; back.classList.toggle("off", visible === false); }

  function render() {
    const words = w();
    back.innerHTML = ""; back.append(el("span", { className: "ar" }, "←"), el("span", {}, words.back));
    bar.innerHTML = "";
    for (const [name, icon, href, path] of items) {
      const a = el("a", { href, className: here === path ? "on" : "" });
      a.append(el("span", { className: "ic" }, icon), el("span", {}, words[name]));
      bar.append(a);
    }
    const size = el("button", { type: "button", ariaLabel: words.bigger, onclick: nextSize });
    size.append(el("span", { className: "ic" }, "🔠"), el("span", {}, words.bigger));
    const sos = el("button", { type: "button", className: "sos", onclick: openHelp });
    sos.append(el("span", { className: "ic" }, "🆘"), el("span", {}, words.help));
    bar.append(size, sos);
    renderHelp();
    renderLangBtn();
  }

  // ---- "I was cheated" help screen ----
  const help = el("div", { id: "sn-help", role: "dialog" });
  function renderHelp() {
    const words = w(), p = prefs();
    const num = (p.cnum || "").replace(/[^0-9+]/g, "");
    help.innerHTML = "";
    const box = el("div", { className: "in" });
    box.append(el("h2", {}, "🆘 " + words.sosTitle), el("p", { className: "sub" }, words.sosSub));
    const steps = [["tel:1930", words.s1, words.s1n], ["", words.s2, words.s2n],
                   [num ? "tel:" + num : "", num ? words.s3.replace("{name}", p.cname || "") : words.s3x, words.s3n],
                   ["https://cybercrime.gov.in", words.s4, words.s4n]];
    steps.forEach(([href, title, note], i) => {
      const a = el("a", { className: "step" + (i === 0 ? " first" : "") });
      if (href) { a.href = href; if (href.startsWith("http")) { a.target = "_blank"; a.rel = "noopener"; } }
      const b = el("b"); b.append(el("span", { className: "num" }, String(i + 1)), document.createTextNode(title));
      a.append(b, el("span", {}, note));
      box.append(a);
    });
    box.append(el("div", { className: "calm" }, "💚 " + words.calm), el("button", { className: "x", type: "button", onclick: closeHelp }, words.close));
    help.append(box);
  }
  function openHelp() { renderHelp(); help.classList.add("show"); }
  function closeHelp() { help.classList.remove("show"); }

  // ---- first visit: choose the language before anything else ----
  const picker = el("div", { id: "sn-lang" });
  function askLang(done) {
    const current = getLang(), words = WORDS[current || "kn"];
    picker.innerHTML = "";
    const box = el("div", { className: "in" });
    box.append(el("img", { src: "/icons/icon-192.png", alt: "" }),
               el("div", { className: "q" }, current ? "🌐 " + words.pick : `${WORDS.kn.pick} · ${WORDS.hi.pick} · ${WORDS.en.pick}`),
               el("h3", {}, current ? words.now : `${WORDS.kn.now} · ${WORDS.en.now}`));
    for (const [code, name] of Object.entries(NAMES)) {
      const b = el("button", { type: "button", className: "lg" + (code === current ? " on" : ""),
                               onclick: () => { picker.classList.remove("show"); setLang(code); done && done(code); } });
      b.append(el("b", {}, name), el("small", {}, (code === current ? "✓ " : "") + ENGLISH[code]));
      box.append(b);
    }
    box.append(el("h3", {}, current ? words.soon : `${WORDS.kn.soon} · ${WORDS.en.soon}`));
    const soon = el("div", { className: "soon" });
    for (const [name, english] of SOON) { const c = el("span", {}, name); c.append(el("small", {}, english)); soon.append(c); }
    box.append(soon, el("p", { className: "note" }, (current ? words : WORDS.en).soonNote));
    if (current) box.append(el("button", { type: "button", className: "x", onclick: () => picker.classList.remove("show") }, words.close));
    picker.append(box);
    picker.classList.add("show");
    picker.scrollTop = 0;
  }

  // ---- language bar under the header of every page: the three languages are always one tap away ----
  const strip = el("section", { id: "sn-langstrip", ariaLabel: "Language" });
  function renderLangBtn() {
    const current = getLang() || "kn";
    strip.innerHTML = "";
    strip.append(el("div", { className: "lab" }, "🌐 ಭಾಷೆ · भाषा · Language"));
    const row = el("div", { className: "row" });
    for (const [code, name] of Object.entries(NAMES)) {
      row.append(el("button", { type: "button", className: code === current ? "on" : "", ariaPressed: String(code === current),
                                onclick: () => setLang(code) }, name));
    }
    row.append(el("button", { type: "button", className: "more", title: "More languages", onclick: () => askLang() }, "+"));
    strip.append(row);
  }

  function start() {
    document.body.append(bar, help, picker);
    document.querySelector("header")?.prepend(back);
    document.querySelector("header")?.after(strip);
    applySize();
    document.documentElement.lang = getLang() || "kn";
    render();
    if (!getLang() && document.body.dataset.askLang !== "no") askLang();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();

  // a page in the middle of a call hides the bar and asks before the phone's Back button leaves
  function inCall(on) {
    document.body.classList.toggle("sn-incall", on);
    window.onbeforeunload = on ? () => "" : null;
  }

  window.Sentinel = { getLang, setLang, words: w, openHelp, askLang, inCall, stored, setBack };
})();
