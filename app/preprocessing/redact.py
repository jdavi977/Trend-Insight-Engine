"""PII redaction applied at the persist boundary.

Raw comment / review text is scrubbed of personally identifiable information
before it is written into ``quotes_json`` (spec §2, §11 criterion 7). Two
layers compose, in order:

1. **Regex** — emails, phone numbers, and ``@handles`` (deterministic,
   structured PII). Patterns live in :mod:`app.config.regex`.
2. **NER** — person names via spaCy ``en_core_web_sm`` (``PERSON`` entities
   only; organisations / products such as "Apple" are left intact).

``redact(text)`` is pure: it returns a scrubbed copy and has no side effects.
The spaCy model is loaded lazily and cached, so importing this module is cheap
and the model is only paid for on first use.
"""
from __future__ import annotations

import functools
import re

from app.config.regex import EMAIL_REGEX, HANDLE_REGEX, PHONE_CANDIDATE_REGEX

EMAIL_PLACEHOLDER = "[REDACTED_EMAIL]"
PHONE_PLACEHOLDER = "[REDACTED_PHONE]"
HANDLE_PLACEHOLDER = "[REDACTED_HANDLE]"
NAME_PLACEHOLDER = "[REDACTED_NAME]"

_SPACY_MODEL = "en_core_web_sm"
# A candidate digit run is treated as a phone number only if it carries at
# least this many digits — keeps "version 2.0.0" / "rated 5 stars" intact.
_MIN_PHONE_DIGITS = 7

_NON_DIGIT = re.compile(r"\D")


@functools.lru_cache(maxsize=1)
def _nlp():
    """Load and cache the spaCy pipeline (NER only; tagger/parser disabled)."""
    import spacy

    return spacy.load(
        _SPACY_MODEL,
        disable=["tagger", "parser", "lemmatizer", "attribute_ruler"],
    )


def _redact_phones(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        digit_count = len(_NON_DIGIT.sub("", match.group()))
        return PHONE_PLACEHOLDER if digit_count >= _MIN_PHONE_DIGITS else match.group()

    return PHONE_CANDIDATE_REGEX.sub(_replace, text)


def _redact_names(text: str) -> str:
    persons = [ent for ent in _nlp()(text).ents if ent.label_ == "PERSON"]
    if not persons:
        return text
    # Replace spans right-to-left so earlier char offsets stay valid.
    for ent in sorted(persons, key=lambda e: e.start_char, reverse=True):
        text = text[: ent.start_char] + NAME_PLACEHOLDER + text[ent.end_char :]
    return text


def redact(text: str) -> str:
    """Return ``text`` with emails, phones, ``@handles``, and person names removed.

    Layer order matters: emails are redacted before handles so an email's
    local-part ``@`` is not mistaken for a handle, and regex runs before NER so
    structured PII is gone before name detection.
    """
    if not text:
        return text

    text = EMAIL_REGEX.sub(EMAIL_PLACEHOLDER, text)
    text = _redact_phones(text)
    text = HANDLE_REGEX.sub(HANDLE_PLACEHOLDER, text)
    text = _redact_names(text)
    return text
