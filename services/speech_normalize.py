import re

# Twilio phone_call STT often renders spoken digits as English words
# ("six zero six zero one"). We translate only unambiguous digit names so
# we don't misread regular words like "for" or "to" as digits.
_DIGIT_WORDS: dict[str, str] = {
    "zero": "0",
    "oh": "0",
    "naught": "0",
    "nought": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "niner": "9",
}

_WORD_RE = re.compile(r"[A-Za-z]+")
_FIVE_DIGIT_RE = re.compile(r"\d{5}")


def words_to_digits(text: str) -> str:
    """Replace spoken digit words inside ``text`` with numeric characters.

    Non-digit words and existing digits are preserved verbatim.
    """
    if not text:
        return ""
    return _WORD_RE.sub(lambda m: _DIGIT_WORDS.get(m.group(0).lower(), m.group(0)), text)


def extract_zip_code(text: str) -> str | None:
    """Pull a 5-digit US ZIP from a noisy speech transcript.

    Accepts both numeric ("60601") and spelled-out ("six zero six zero one")
    forms. Returns ``None`` if no 5-digit run can be assembled.
    """
    if not text:
        return None

    direct = "".join(ch for ch in text if ch.isdigit())
    match = _FIVE_DIGIT_RE.search(direct)
    if match:
        return match.group(0)

    normalized_digits = "".join(ch for ch in words_to_digits(text) if ch.isdigit())
    match = _FIVE_DIGIT_RE.search(normalized_digits)
    return match.group(0) if match else None
