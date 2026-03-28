import re


def detect_language(text: str) -> str:
    """Detect if text is Chinese or English based on CJK character presence."""
    cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
    cjk_chars = len(cjk_pattern.findall(text))
    total_alpha = len(re.findall(r"[a-zA-Z]", text))

    if cjk_chars > total_alpha:
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
