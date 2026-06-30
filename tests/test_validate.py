"""Tests for aideadlines.validate.validate_conferences."""

from aideadlines.validate import validate_conferences


def test_valid_conference_has_no_errors():
    conferences = {
        "abc2025": {
            "id": "abc2025",
            "shortname": "ABC2025",
            "timeline": [{"deadline": "2025-01-15T23:59:59Z"}],
        }
    }
    assert validate_conferences(conferences) == []


def test_missing_timeline_is_flagged():
    errors = validate_conferences({"abc2025": {"id": "abc2025", "title": "ABC"}})
    assert any("timeline" in e for e in errors)


def test_empty_timeline_is_flagged():
    errors = validate_conferences({"abc2025": {"id": "abc2025", "title": "ABC", "timeline": []}})
    assert any("non-empty" in e for e in errors)


def test_missing_deadline_in_entry_is_flagged():
    errors = validate_conferences(
        {"abc2025": {"id": "abc2025", "title": "ABC", "timeline": [{"note": "no deadline"}]}}
    )
    assert any("missing 'deadline'" in e for e in errors)


def test_unparseable_deadline_is_flagged():
    errors = validate_conferences(
        {"abc2025": {"id": "abc2025", "title": "ABC", "timeline": [{"deadline": "not a date"}]}}
    )
    assert any("unparseable" in e for e in errors)


def test_missing_name_is_flagged():
    errors = validate_conferences(
        {"abc2025": {"id": "abc2025", "timeline": [{"deadline": "2025-01-15"}]}}
    )
    assert any("shortname or title" in e for e in errors)
