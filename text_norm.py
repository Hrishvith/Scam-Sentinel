"""Text normalisation shared by the detector, live mode and the benchmark."""
from __future__ import annotations

import re
import unicodedata

_KN_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize(text: str, keep_dots: bool = False) -> str:
    """NFC, lowercase, native digits -> ASCII, drop ZWNJ/ZWJ, collapse spaces."""
    t = unicodedata.normalize("NFC", text or "").lower()
    t = t.translate(_KN_DIGITS).translate(_DEV_DIGITS)
    t = t.replace("‌", "").replace("‍", "")
    if not keep_dots:
        t = t.replace(".", " ")
    return re.sub(r"\s+", " ", t).strip()
