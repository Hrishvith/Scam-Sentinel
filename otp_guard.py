"""OTP guard: notices the PROTECTED person starting to read digits out after the caller asked for an
OTP or money, so the line can stop them ("Stop! Don't say the numbers") and cut their voice to the caller.

Privacy by design: the protected person's words are only counted for digits. They are never shown
to the operator or guardian, and the saved session keeps digit counts, not text.
"""
from __future__ import annotations

from typing import Callable

from alerts import GUARD_WARNINGS, HELPLINE, lang_key
from live import LiveSession, is_own_warning
from text_norm import normalize

# Digit words as Prisma writes them. Words that double as everyday words ("ಒಂದು" = "a", "दो" = "give",
# "एक" = "a") count too, which is why one sentence needs several digits before the guard fires.
# "to"-like words ("two" as ಟು / टू, "oh") are left out: Prisma writes English "to" the same way.
# REVIEW with native speakers.
DIGIT_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ಸೊನ್ನೆ", "ಒಂದು", "ಎರಡು", "ಮೂರು", "ನಾಲ್ಕು", "ಐದು", "ಆರು", "ಏಳು", "ಎಂಟು", "ಒಂಬತ್ತು",
    "ಝೀರೋ", "ಜೀರೋ", "ವನ್", "ತ್ರೀ", "ಫೋರ್", "ಫೈವ್", "ಸಿಕ್ಸ್", "ಸೆವೆನ್", "ಎಯ್ಟ್", "ನೈನ್",
    "शून्य", "एक", "दो", "तीन", "चार", "पांच", "पाँच", "छह", "छः", "छै", "सात", "आठ", "नौ",
    "ज़ीरो", "जीरो", "वन", "थ्री", "फोर", "फ़ाइव", "फाइव", "सिक्स", "सेवन", "एट", "नाइन",
    "ek", "teen", "char", "chaar", "paanch", "panch", "chhe", "saat", "aath", "nau",
}
ARMING_TACTICS = {"credentials", "otp_request", "payment"}


def spoken_digits(text: str) -> int:
    """How many digits a sentence contains, as numerals or digit words (the helpline number excluded)."""
    t = normalize(text).replace(HELPLINE, " ")
    numerals = sum(ch.isdigit() for ch in t)
    words = sum(w.strip(",.?!।") in DIGIT_WORDS for w in t.split())
    return numerals + words


class DigitWatch:
    """Fires when, after the caller asked for an OTP/PIN or money (`armed`), at least `min_digits` digits
    are spoken within `window` seconds. At most once per `cooldown` seconds."""

    def __init__(self, min_digits: int = 3, window: float = 10.0, cooldown: float = 6.0):
        self.min_digits, self.window, self.cooldown = min_digits, window, cooldown
        self.recent: list[tuple[float, int]] = []
        self.fired_at: float | None = None
        self.fired = 0

    def add(self, at: float, digits: int, armed: bool) -> int | None:
        """Digits heard in one sentence; returns how many were heard in the window when it fires."""
        if digits:
            self.recent = [(t, n) for t, n in self.recent if at - t <= self.window] + [(at, digits)]
        total = sum(n for _, n in self.recent)
        if armed and total >= self.min_digits and (self.fired_at is None or at - self.fired_at >= self.cooldown):
            self.fired_at, self.recent = at, []
            self.fired += 1
            return total
        return None


class GuardSession(LiveSession):
    """Prisma realtime on the protected person's microphone. Emits a "guard" event when, after the
    caller has asked for an OTP/PIN or money (`armed()`), at least `min_digits` digits are spoken
    within `window` seconds."""

    def __init__(self, *args, armed: Callable[[], bool], min_digits: int = 3, window: float = 10.0,
                 cooldown: float = 6.0, **kw):
        super().__init__(*args, **kw)
        self.armed = armed
        self.watch = DigitWatch(min_digits, window, cooldown)
        self.own_warnings.append(GUARD_WARNINGS[lang_key(self.lang)])   # its phone plays this too

    def _on_transcript(self, msg: dict) -> None:
        text, at = (msg.get("text") or "").strip(), round(self.sent_s, 2)
        echo = is_own_warning(text, self.own_warnings)
        digits = 0 if echo else spoken_digits(text)
        armed = bool(self.armed())
        self.segments.append({"at": at, "digits": digits, "armed": armed, "echo": echo})   # no words kept
        self._emit("heard", at=at, digits=digits, armed=armed, echo=echo)
        total = self.watch.add(at, digits, armed)
        if total:
            self._emit("guard", at=at, digits=total)

    def summary(self) -> dict:
        s = super().summary()
        s.pop("transcript", None)        # never keep the protected person's words
        s["guard_fired"] = self.watch.fired
        return s
