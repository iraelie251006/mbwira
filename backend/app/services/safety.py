"""
Safety layer — detect crisis signals before AND after the LLM responds.

Two checks:
1. Keyword pre-filter on user input (fast, deterministic, always runs)
2. Post-filter on LLM output for the [ESCALATE: ...] tag

This is defense-in-depth: the keyword filter catches obvious signals even if the
LLM misses them, and the tag is there for cases the keyword filter can't see.
"""
import re
from dataclasses import dataclass

# Keywords are lowercase; we lowercase the input before checking.
# This list is intentionally short and high-precision. Add more cautiously —
# every false positive triggers a real human's time.

SUICIDAL_KEYWORDS_EN = [
    "kill myself", "suicide", "end my life", "want to die", "don't want to live",
    "hurt myself", "self harm", "self-harm", "cut myself", "take my life",
]
SUICIDAL_KEYWORDS_RW = [
    "kwiyahura", "kwiyica", "sinshaka kubaho", "kurangiza ubuzima bwanjye",
    "kwihungabanya", "kwikomeretsa",
]

GBV_KEYWORDS_EN = [
    "raped", "rape", "forced me", "abused me", "he hit me", "she hit me",
    "beat me", "sexually assaulted", "touched me without",
]
GBV_KEYWORDS_RW = [
    "yanfashe ku ngufu", "yamfashe ku ngufu", "gufata ku ngufu",
    "ihohoterwa", "yankubise", "yankoreye nabi",
]

MEDICAL_EMERGENCY_EN = [
    "bleeding a lot", "heavy bleeding", "can't stop bleeding",
    "took pills to abort", "unconscious", "can't breathe",
    "overdose", "poisoned myself",
]
MEDICAL_EMERGENCY_RW = [
    "amaraso menshi", "sinshobora guhagarika amaraso",
    "nafashe imiti kugira ngo ndagure inda", "sinyumva",
]

CHILD_SAFEGUARDING_PATTERNS = [
    r"\bi(?:\s|')m\s+1[0-7]\b",
    r"\bndi\s+w'?imyaka\s+1[0-7]\b",
]


@dataclass
class SafetySignal:
    triggered: bool
    reason: str | None = None
    matched_text: str | None = None


def check_user_message(text: str) -> SafetySignal:
    """Keyword scan on incoming user messages."""
    if not text:
        return SafetySignal(False)
    t = text.lower()

    for kw in SUICIDAL_KEYWORDS_EN + SUICIDAL_KEYWORDS_RW:
        if kw in t:
            return SafetySignal(True, "suicidal_ideation", kw)

    for kw in GBV_KEYWORDS_EN + GBV_KEYWORDS_RW:
        if kw in t:
            return SafetySignal(True, "gender_based_violance", kw)

    for kw in MEDICAL_EMERGENCY_EN + MEDICAL_EMERGENCY_RW:
        if kw in t:
            return SafetySignal(True, "medical_emergency", kw)

    for pattern in CHILD_SAFEGUARDING_PATTERNS:
        m = re.search(pattern, t)
        if m:
            return SafetySignal(True, "child_safeguarding_age", m.group(0))

    return SafetySignal(False)


ESCALATE_TAG_RE = re.compile(r"\[ESCALATE:\s*(\w+)\]", re.IGNORECASE)


def extract_escalation_from_response(text: str) -> tuple[str | None, str]:
    """
    Look for [ESCALATE: reason] in LLM output. Return (reason, cleaned_text).
    """
    m = ESCALATE_TAG_RE.search(text)
    if not m:
        return None, text
    reason = m.group(1).lower()
    cleaned = ESCALATE_TAG_RE.sub("", text).strip()
    return reason, cleaned


def safety_response_text(reason: str, lang: str = "rw") -> str:
    """Fallback safety text attached whenever escalation triggers."""
    if reason == "suicidal_ideation":
        if lang == "rw":
            return (
                "\n\nUri wa ngombwa. Hamagara 114 nonaha — bafasha ku buntu, mu ibanga. "
                "Umujyanama azaguhamagara mu masaha 24."
            )
        return (
            "\n\nYou matter. Please call 114 now — free and confidential. "
            "A counselor will also reach out within 24 hours."
        )
    if reason == "gender_based_violance":
        if lang == "rw":
            return (
                "\n\nUri mu mutekano wo gushaka ubufasha. Hamagara Isange 3029 "
                "cyangwa Polisi 112. Nta cyaha gifite."
            )
        return (
            "\n\nIt is safe to seek help. Call Isange 3029 or Police 112. "
            "This is not your fault."
        )
    if reason == "medical_emergency":
        if lang == "rw":
            return "\n\nJya ku kigo nderabuzima NONAHA cyangwa hamagara 114."
        return "\n\nGo to a health center NOW or call 114."
    if reason == "child_safeguarding":
        if lang == "rw":
            return (
                "\n\nNiba uri munsi y'imyaka 18 kandi umuntu mukuru akagukoraho, "
                "hamagara Isange 3029 cyangwa uvugishe umujyanama w'ubuzima."
            )
        return (
            "\n\nIf you're under 18 and an adult is touching you, call Isange 3029 "
            "or speak to a Community Health Worker."
        )
    return ""
