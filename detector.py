"""Scam-tactic detection and risk scoring.

Rule-based by default (free, offline, explainable). If EVON_BASE_URL is set, an
OpenAI-compatible LLM (e.g. Gnani Evon served with vLLM) is asked for a second
opinion and the higher risk level wins.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

import requests

from tactics import DELIVERY_PHRASES, ESCALATION, SAFETY_PHRASES, TACTICS
from taxonomy import normalize

LEVELS = ["low", "medium", "high"]
MEDIUM_AT, HIGH_AT = 3.5, 6.0
_PRIVATE = {"authority", "threat"}          # "someone official is pressuring me"
_DANGEROUS_ASK = {"credentials", "payment", "remote_access"}  # "...and wants something harmful"


def _compile(keyword: str) -> re.Pattern:
    if keyword.startswith("re:"):
        return re.compile(keyword[3:])
    if keyword.isascii():
        kw = re.escape(normalize(keyword))
        return re.compile(rf"(?<![a-z0-9]){kw}(?![a-z0-9])")
    # Kannada/Hindi: Prisma splits words unpredictably ("ಒ ಟಿ ಪಿ", "ಡೌನ್ ಲೋಡ್"), so spaces are optional.
    chars = normalize(keyword).replace(" ", "")
    return re.compile(r"\s?".join(map(re.escape, chars)))


_PATTERNS = {name: [(kw, _compile(kw)) for kw in spec["keywords"]] for name, spec in TACTICS.items()}
_SAFETY = [_compile(p) for p in SAFETY_PHRASES]
_DELIVERY = [_compile(p) for p in DELIVERY_PHRASES]


@dataclass
class Detection:
    score: float = 0.0
    level: str = "low"
    tactics: dict[str, list[str]] = field(default_factory=dict)  # tactic -> matched evidence
    notes: list[str] = field(default_factory=list)
    source: str = "rules"

    def to_dict(self) -> dict:
        return {"score": round(self.score, 2), "level": self.level, "tactics": self.tactics,
                "notes": self.notes, "source": self.source}


def level_for(score: float) -> str:
    return "high" if score >= HIGH_AT else "medium" if score >= MEDIUM_AT else "low"


def detect_rules(text: str) -> Detection:
    plain = normalize(text)
    found: dict[str, list[str]] = {}
    for name, pats in _PATTERNS.items():
        hits = [kw for kw, rx in pats if rx.search(plain)]
        if hits:
            found[name] = hits

    notes: list[str] = []
    weights = {name: TACTICS[name]["weight"] for name in found}
    # An OTP mention is only discounted when nothing else escalates (scammers also say "don't share").
    context = None
    if "credentials" in weights and not found.keys() & ESCALATION:
        if any(rx.search(plain) for rx in _SAFETY):
            context = "Sounds like an awareness message (\"never share\"), so OTP/PIN weight was reduced."
        elif any(rx.search(plain) for rx in _DELIVERY):
            context = "Sounds like a delivery hand-over OTP, so OTP weight was reduced."
    if context:
        weights["credentials"] *= 0.3
        notes.append(context)

    score = sum(weights.values())
    if not context and found.keys() & _PRIVATE and found.keys() & _DANGEROUS_ASK:
        score += 2.0
        notes.append("Official-sounding pressure combined with a request for OTP, money or app access.")
    if "secrecy" in found and found.keys() & _DANGEROUS_ASK:
        score += 1.0
        notes.append("Told to keep it secret while being asked for something sensitive.")
    return Detection(score=score, level=level_for(score), tactics=found, notes=notes)


_SYSTEM = (
    "You analyse a phone-call transcript (Kannada, Hindi, English or mixed) for scam tactics common in India "
    "(digital arrest, fake KYC, courier/customs, OTP theft, remote-access apps). Reply with ONE JSON object only: "
    "{\"risk\": \"low\"|\"medium\"|\"high\", \"reason\": <one short English sentence>}. "
    "Awareness messages that warn people NOT to share OTPs are low risk."
)


def assess_llm(text: str, *, base_url: str, model: str, api_key: str | None = None,
               timeout: int = 30) -> dict | None:
    """Second opinion from an OpenAI-compatible endpoint. None on any failure."""
    try:
        resp = requests.post(
            base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            json={"model": model, "temperature": 0, "max_tokens": 300,
                  "messages": [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": text}]},
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(re.findall(r"\{[^{}]*\}", content, flags=re.S)[-1])
        if data.get("risk") in LEVELS:
            return {"risk": data["risk"], "reason": str(data.get("reason", ""))[:300]}
    except Exception:
        pass
    return None


def detect(text: str, use_llm: bool | None = None) -> Detection:
    det = detect_rules(text)
    base_url = os.getenv("EVON_BASE_URL")
    if use_llm is None:
        use_llm = bool(base_url)
    if not (use_llm and base_url and text.strip()):
        return det

    opinion = assess_llm(text, base_url=base_url, model=os.getenv("EVON_MODEL", "gnani-evon-v3.3"),
                         api_key=os.getenv("EVON_API_KEY"))
    if opinion is None:
        return det
    det.source = "rules+llm"
    det.notes.append(f"LLM view ({opinion['risk']}): {opinion['reason']}")
    if LEVELS.index(opinion["risk"]) > LEVELS.index(det.level):
        det.level = opinion["risk"]
    return det
