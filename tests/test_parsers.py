"""Unit tests for the pure parsing helpers (no network)."""

import pytest
from bs4 import BeautifulSoup

from aideadlines.parser.ccf_deadlines import conference_from_ccf, parse_ccf_date_range
from aideadlines.parser.common_website import extract_dates_from_soup
from aideadlines.parser.hf_list import conference_from_hf
from aideadlines.parser.ninoduarte_list import conference_from_nino, parse_past_conferences


# --------------------------------------------------------------------------- #
# ccf_deadlines
# --------------------------------------------------------------------------- #
class TestCcfDateRange:
    def test_tbd_returns_none(self):
        assert parse_ccf_date_range("TBD", 2025) is None

    def test_single_month_day_range(self):
        # The trailing comma on the end day is a known quirk dateparser tolerates downstream.
        assert parse_ccf_date_range("June 1-5, 2025", 2025) == ("1 June 2025", "5, June 2025")

    def test_cross_month_range(self):
        assert parse_ccf_date_range("June 30 - July 4, 2025", 2025) == ("30 June 2025", "4, July 2025")

    def test_single_day(self):
        assert parse_ccf_date_range("June 5 2025", 2025) == ("5 June 2025", "5 June 2025")

    def test_unparseable_raises(self):
        with pytest.raises(ValueError):
            parse_ccf_date_range("a b c d", 2025)


class TestConferenceFromCcf:
    def _info(self):
        return {"title": "CVPR", "description": "Computer Vision and Pattern Recognition"}

    def test_tbd_date_drops_conference(self):
        conf = {"year": 2025, "date": "TBD", "timeline": [{"deadline": "2024-11-01"}]}
        assert conference_from_ccf(self._info(), conf) is None

    def test_empty_timeline_returns_none(self):
        conf = {"year": 2025, "timeline": [{"deadline": "TBD"}]}
        assert conference_from_ccf(self._info(), conf) is None

    def test_valid_conference_built(self):
        conf = {
            "year": 2025,
            "link": "https://cvpr.org",
            "date": "June 1-5, 2025",
            "timeline": [{"deadline": "2024-11-01", "comment": "paper"}],
        }
        out = conference_from_ccf(self._info(), conf)
        assert out["id"] == "cvpr2025"
        assert out["website"] == "https://cvpr.org"
        assert out["conferenceStartDate"] == "1 June 2025"
        assert out["timeline"] == [{"deadline": "2024-11-01", "note": "paper"}]

    def test_3dv_id_is_rewritten(self):
        info = {"title": "3DV"}
        conf = {"year": 2025, "timeline": [{"deadline": "2024-11-01"}]}
        assert conference_from_ccf(info, conf)["id"] == "threedv2025"


# --------------------------------------------------------------------------- #
# hf_list
# --------------------------------------------------------------------------- #
class TestConferenceFromHf:
    def test_basic_conference(self):
        conference = {
            "title": "CVPR",
            "full_name": "Computer Vision and Pattern Recognition",
            "year": 2025,
            "deadline": "2024-11-01",
            "start": "2025-06-01",
            "end": "2025-06-05",
            "tags": ["computer-vision", "unknown-tag"],
        }
        out = conference_from_hf(conference)
        assert out["id"] == "cvpr2025"
        assert out["tags"] == ["CV"]  # unknown tag dropped
        assert out["timeline"] == [{"deadline": "2024-11-01"}]
        assert out["conferenceStartDate"] == "2025-06-01"

    def test_missing_tags_does_not_crash(self):
        conference = {
            "title": "ABC",
            "full_name": "A B C",
            "year": 2025,
            "deadline": "2024-11-01",
            "start": "2025-06-01",
            "end": "2025-06-05",
        }
        assert conference_from_hf(conference)["tags"] == []

    def test_no_timeline_returns_none(self):
        conference = {"title": "ABC", "full_name": "A B C", "year": 2025, "start": "2025-06-01", "end": "2025-06-05"}
        assert conference_from_hf(conference) is None

    def test_date_string_fallback_when_no_start(self):
        conference = {
            "title": "ABC",
            "full_name": "A B C",
            "year": 2025,
            "deadline": "2024-11-01",
            "date": "June 1 - 5, 2025",
            "tags": [],
        }
        out = conference_from_hf(conference)
        assert out["conferenceStartDate"] == "June 1, 2025"
        assert out["conferenceEndDate"] == "June 5, 2025"

    def test_unparseable_date_string_returns_none(self):
        conference = {
            "title": "ABC",
            "full_name": "A B C",
            "year": 2025,
            "deadline": "2024-11-01",
            "date": "next spring",
            "tags": [],
        }
        assert conference_from_hf(conference) is None


# --------------------------------------------------------------------------- #
# ninoduarte_list
# --------------------------------------------------------------------------- #
class TestNino:
    def test_parse_past_conferences_adds_brackets_and_trims_comma(self):
        raw = '{"id": "a"},\n{"id": "b"},'
        assert parse_past_conferences(raw) == [{"id": "a"}, {"id": "b"}]

    def test_parse_past_conferences_invalid_returns_empty(self):
        assert parse_past_conferences("{not valid json") == []

    def test_conference_from_nino_valid(self):
        conf = {
            "id": "cvpr",
            "name": "CVPR",
            "deadline": "2024-11-01",
            "location": "Seattle",
            "type": "CV",
            "timezone": "AoE",
            "link": "https://cvpr.org",
            "date_start": "2025-06-01",
            "date_end": "2025-06-05",
        }
        out = conference_from_nino(conf)
        assert out["id"] == "cvpr2025"
        assert out["timeline"] == [{"deadline": "2024-11-01"}]

    def test_conference_from_nino_unparseable_start_returns_none(self):
        conf = {
            "id": "cvpr",
            "name": "CVPR",
            "deadline": "2024-11-01",
            "location": "Seattle",
            "type": "CV",
            "timezone": "AoE",
            "link": "https://cvpr.org",
            "date_start": "not a date",
            "date_end": "also not",
        }
        assert conference_from_nino(conf) is None


# --------------------------------------------------------------------------- #
# common_website
# --------------------------------------------------------------------------- #
def test_extract_dates_from_soup_reads_deadline_table():
    html = """
    <table>
      <tr><td>Main Conference</td></tr>
      <tr><td>Paper Submission Deadline</td><td>March 1, 2025</td></tr>
      <tr><td>Abstract Submission Deadline</td><td>Feb 22, 2025</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    data = extract_dates_from_soup({"timeline": [{}]}, soup)
    assert data["timeline"][0]["deadline"].strip() == "March 1, 2025"
    assert data["timeline"][0]["abstractDeadline"].strip() == "Feb 22, 2025"


def test_extract_dates_from_soup_handles_missing_next_cell():
    # A deadline label with no following cell must not raise (was a tds[i+1] IndexError risk).
    html = "<table><tr><td>Paper Submission Deadline</td></tr></table>"
    soup = BeautifulSoup(html, "html.parser")
    data = extract_dates_from_soup({"timeline": [{}]}, soup)
    assert "deadline" not in data["timeline"][0]
