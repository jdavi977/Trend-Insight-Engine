"""Tests for app.preprocessing.redact — PII scrubbing at the persist boundary.

Covers the regex layer (emails, phones, @handles) and the NER layer (person
names) in isolation, plus the spec §11 criterion-7 guarantee that a known
email never survives into the redacted text.
"""
from app.preprocessing.redact import (
    EMAIL_PLACEHOLDER,
    HANDLE_PLACEHOLDER,
    NAME_PLACEHOLDER,
    PHONE_PLACEHOLDER,
    redact,
)


# --- Regex layer: emails -----------------------------------------------------

def test_plain_email_is_removed():
    out = redact("Contact me at john@example.com please")
    assert "john@example.com" not in out
    assert EMAIL_PLACEHOLDER in out


def test_complex_email_is_removed():
    out = redact("ping jane.doe+tag@sub.example.co.uk thanks")
    assert "jane.doe+tag@sub.example.co.uk" not in out
    assert EMAIL_PLACEHOLDER in out


# --- Regex layer: phones -----------------------------------------------------

def test_us_phone_with_formatting_is_removed():
    out = redact("call me at (234) 567-8900 tomorrow")
    assert "567-8900" not in out
    assert PHONE_PLACEHOLDER in out


def test_international_phone_is_removed():
    out = redact("reach support on +44 20 7946 0958 any time")
    assert "7946 0958" not in out
    assert PHONE_PLACEHOLDER in out


def test_short_version_number_is_not_treated_as_phone():
    out = redact("crashes on version 2.0.0 every time")
    assert "2.0.0" in out
    assert PHONE_PLACEHOLDER not in out


# --- Regex layer: handles ----------------------------------------------------

def test_handle_is_removed():
    out = redact("shoutout to @john_doe for the fix")
    assert "@john_doe" not in out
    assert HANDLE_PLACEHOLDER in out


def test_email_local_part_is_not_treated_as_handle():
    out = redact("mail john@example.com here")
    assert HANDLE_PLACEHOLDER not in out
    assert EMAIL_PLACEHOLDER in out


# --- NER layer: person names -------------------------------------------------

def test_mixed_case_name_in_sentence_is_removed():
    out = redact("I told John Smith about the sync bug")
    assert "John Smith" not in out
    assert NAME_PLACEHOLDER in out


def test_lowercase_name_is_removed():
    out = redact("sarah keller said it crashes on launch")
    assert "sarah keller" not in out
    assert NAME_PLACEHOLDER in out


def test_company_name_is_not_treated_as_person():
    # False-positive guard: "Apple" is an ORG, not a PERSON.
    out = redact("Apple should fix the offline sync issue")
    assert "Apple" in out
    assert NAME_PLACEHOLDER not in out


# --- Composition & edge cases ------------------------------------------------

def test_spec_criterion_7_email_never_survives():
    out = redact("Reviewer John Doe wrote: email me at john@example.com")
    assert "john@example.com" not in out


def test_multiple_pii_types_in_one_string():
    out = redact("John Smith (@jsmith) — john@example.com / +1 (234) 567-8900")
    assert "John Smith" not in out
    assert "@jsmith" not in out
    assert "john@example.com" not in out
    assert "567-8900" not in out


def test_clean_text_is_unchanged():
    text = "the app crashes on launch and loses my notes"
    assert redact(text) == text


def test_empty_string_returns_empty():
    assert redact("") == ""
