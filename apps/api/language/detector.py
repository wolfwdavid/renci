import re


def detect_language(text: str) -> str:
    """Detect if text is Chinese or English.

    Uses the language of the first substantive token — if the message
    starts with Latin words, treat as English; if it starts with CJK, treat
    as Chinese. This matches how bilingual speakers code-switch: the lead
    language is the intended language.
    """
    text = text.strip()
    if not text:
        return "en"

    # Check the first non-whitespace character
    for char in text:
        if char.isspace():
            continue
        if "\u4e00" <= char <= "\u9fff" or "\u3400" <= char <= "\u4dbf":
            return "zh"
        if char.isascii() and char.isalpha():
            return "en"

    # Fallback: count CJK vs English words
    cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
    cjk_chars = len(cjk_pattern.findall(text))
    english_words = len(re.findall(r"[a-zA-Z]+", text))

    if cjk_chars > english_words:
        return "zh"
    return "en"


def is_traditional_chinese(text: str) -> bool:
    """Rough check for Traditional vs Simplified Chinese.

    Traditional characters common in Cantonese-speaking communities
    tend to fall in certain Unicode ranges more frequently.
    """
    # Common traditional-only characters
    traditional_markers = set("這裡們會對說學點還過國開來時個問與從後對種樣讓經議發總處進選題關員認論達類際質")
    chars_in_text = set(text)
    overlap = chars_in_text & traditional_markers
    return len(overlap) > 0
