import re

ARABIC_CHAR_RANGE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")


def detect_language(text: str) -> str:
    """
    Detect if text is Arabic or English based on character presence.
    Returns 'ar' or 'en'.
    """
    text = text.strip()
    if not text:
        return "ar"
    arabic_chars = ARABIC_CHAR_RANGE.findall(text)
    total_chars = len([c for c in text if c.isalpha()])
    if total_chars == 0:
        return "ar"
    if len(arabic_chars) / total_chars >= 0.3:
        return "ar"
    return "en"


def resolve_response_language(message: str) -> str:
    """
    Source of truth for response language.
    Always resolve from the current incoming user message.
    """
    return detect_language(message)


def is_arabic(text: str) -> bool:
    return detect_language(text) == "ar"


def is_english(text: str) -> bool:
    return detect_language(text) == "en"
