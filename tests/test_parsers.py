"""Unit tests for the pure parsing helpers (no network)."""

import os

import pytest
from bs4 import BeautifulSoup

from aideadlines.parser import common_website, openaccept
from aideadlines.parser.ccf_deadlines import conference_from_ccf, parse_ccf_date_range
from aideadlines.parser.common_website import extract_dates_from_soup
from aideadlines.parser.hf_list import conference_from_hf
from aideadlines.parser.ninoduarte_list import conference_from_nino, parse_past_conferences
from aideadlines.parser.openaccept import attach_rate, files_by_name, stats_from_metadata
from aideadlines.parser.wacv import _split_session_dates


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

    def test_digit_in_shortname_kept_and_3dv_matches_ccf_id(self):
        conference = {
            "title": "3DV",
            "full_name": "International Conference on 3D Vision",
            "year": 2027,
            "deadline": "2026-08-28",
            "start": "2027-04-06",
            "end": "2027-04-09",
            "tags": ["computer-vision"],
        }
        out = conference_from_hf(conference)
        assert out["id"] == "threedv2027"  # matches ccf_deadlines id so instances merge
        assert out["shortname"] == "3DV 2027"

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


# --------------------------------------------------------------------------- #
# common_website factory — pins the metadata of the deduplicated parsers so the
# config-driven factory can't silently drift from the 5 originals it replaced.
# Network is mocked; the live behavior is exercised separately, not in CI.
# --------------------------------------------------------------------------- #
_FAKE_DATES_HTML = """
<table>
  <tr><td>Paper Submission Deadline</td><td>March 1, 2025</td></tr>
  <tr><td>Main Conference Day</td><td>June 10, 2025</td></tr>
</table>
"""


def _website_parser(name):
    return {p.__name__: p for p in common_website.PARSER}[name]


@pytest.fixture
def fake_dates_page(monkeypatch):
    monkeypatch.setattr(
        common_website, "fetch_soup", lambda url, **kw: BeautifulSoup(_FAKE_DATES_HTML, "html.parser")
    )


@pytest.mark.parametrize(
    "name,year,cid,short,title,tag",
    [
        ("parse_cvpr", 2025, "cvpr2025", "CVPR 2025", "Computer Vision and Pattern Recognition Conference", "CV"),
        ("parse_neurips", 2025, "neurips2025", "NeurIPS 2025", "Neural Information Processing Systems", "ML"),
        ("parse_icml", 2025, "icml2025", "ICML 2025", "International Conference on Machine Learning", "ML"),
        ("parse_iccv", 2025, "iccv2025", "ICCV 2025", "International Conference on Computer Vision", "CV"),
        ("parse_eccv", 2024, "eccv2024", "ECCV 2024", "European Conference on Computer Vision", "CV"),
    ],
)
def test_website_factory_metadata(fake_dates_page, name, year, cid, short, title, tag):
    d = _website_parser(name)(year)
    assert d["id"] == cid
    assert d["shortname"] == short
    assert d["title"] == title
    assert d["tags"] == [tag]
    assert d["website"].startswith("https://")
    assert d["timeline"][0]["deadline"].strip() == "March 1, 2025"
    assert d["conferenceStartDate"].strip() == "June 10, 2025"


def test_iccv_skips_even_years():
    assert _website_parser("parse_iccv")(2024) == {}


def test_eccv_skips_odd_years():
    assert _website_parser("parse_eccv")(2025) == {}


def test_website_parser_returns_empty_without_deadline(monkeypatch):
    monkeypatch.setattr(
        common_website, "fetch_soup", lambda url, **kw: BeautifulSoup("<html></html>", "html.parser")
    )
    assert _website_parser("parse_cvpr")(2025) == {}


# --------------------------------------------------------------------------- #
# wacv — conference-session date splitting (from the thecvf 'Dates' table)
# --------------------------------------------------------------------------- #
class TestWacvSessionDates:
    def test_same_month_range_borrows_month_for_end(self):
        assert _split_session_dates("Jan 6th - 8th") == ("Jan 6th", "Jan 8th")

    def test_cross_month_range_keeps_both_months(self):
        assert _split_session_dates("Feb 28 - Mar 3") == ("Feb 28", "Mar 3")

    def test_en_dash_separator(self):
        assert _split_session_dates("Jan 6th – 8th") == ("Jan 6th", "Jan 8th")

    def test_no_range_returns_none(self):
        assert _split_session_dates("sometime in January") is None


# --------------------------------------------------------------------------- #
# openaccept
# --------------------------------------------------------------------------- #
class TestOpenAccept:
    def _metadata(self):
        return {
            "name": "ACL",
            "yearly_data": [
                {"year": 2025, "submitted": 8360, "accepted": 1699},
                {"year": 2024, "submitted": 4407, "accepted": 943},
                {"year": 2023, "submitted": 0, "accepted": 0},
                {"year": 2022, "submitted": 100, "accepted": 200},
            ],
            # Findings: must never be mistaken for the main track
            "second_track": "Findings",
            "second_track_yearly_data": [{"year": 2025, "submitted": 8360, "accepted": 1392}],
        }

    def test_only_the_main_track_with_sane_counts_is_read(self):
        assert stats_from_metadata(self._metadata()) == {2025: (8360, 1699), 2024: (4407, 943)}

    def test_missing_yearly_data_is_not_an_error(self):
        assert stats_from_metadata({"name": "ACL"}) == {}

    def test_files_are_keyed_by_lowercased_name_skipping_dotfiles(self):
        tree = {"tree": [
            {"path": "ai/NeurIPS.json"},
            {"path": "gm/ACM MM.json"},
            {"path": ".schema/conference-schema.jsons"},
            {"path": "README.md"},
        ]}
        assert files_by_name(tree) == {"neurips": "ai/NeurIPS.json", "acm mm": "gm/ACM MM.json"}

    def _stats(self):
        return {2025: (21575, 5290), 2023: (12343, 3218)}

    def test_exact_year_wins_and_carries_the_counts(self):
        assert attach_rate({"id": "neurips2023"}, self._stats()) == {
            "id": "neurips2023",
            "acceptanceRate": 26.07,
            "acceptanceRateYear": 2023,
            "acceptedPapers": 3218,
            "submittedPapers": 12343,
        }

    def test_upcoming_year_falls_back_to_the_latest_past_year(self):
        conf = attach_rate({"id": "neurips2027"}, self._stats())
        assert (conf["acceptanceRate"], conf["acceptanceRateYear"]) == (24.52, 2025)

    def test_a_later_year_is_never_used_for_an_older_conference(self):
        assert attach_rate({"id": "neurips2015"}, self._stats()) == {"id": "neurips2015"}

    def test_scraping_is_throttled_to_the_refresh_interval(self, tmp_path, monkeypatch):
        stamp = tmp_path / "stamp"
        monkeypatch.setattr(openaccept, "_STAMP_FILE", str(stamp))
        assert openaccept._due(), "never scraped"
        stamp.touch()
        assert not openaccept._due(), "just scraped"
        os.utime(stamp, (0, 0))
        assert openaccept._due(), "stale"
