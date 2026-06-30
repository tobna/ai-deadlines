"""Characterization tests for aideadlines.utils.

Locks current behavior of date/timezone parsing and the merge helpers before the
Phase 3 restructure.
"""

import datetime

import pytest

from aideadlines.utils import (
    _parse_timestr,
    join_conferences,
    parse_all_times,
    parse_stuff,
    unite_tags,
)


# --------------------------------------------------------------------------- #
# _parse_timestr
# --------------------------------------------------------------------------- #
class TestParseTimestr:
    def test_explicit_time_with_aoe_default(self):
        # 23:59 AoE (UTC-12) on Sep 5 == 11:59 UTC on Sep 6.
        assert _parse_timestr("Sep 5, 2025 23:59 AoE", with_time=True) == "2025-09-06T11:59:00Z"

    def test_date_only_strips_time(self):
        assert _parse_timestr("2025-09-05", with_time=False) == "2025-09-05"

    def test_missing_time_fills_end_of_day_then_shifts_aoe(self):
        # No explicit time -> filled to 23:59:59, then AoE shift -> next day 11:59:59 UTC.
        assert _parse_timestr("Sep 5 2025", with_time=True) == "2025-09-06T11:59:59Z"

    def test_unparseable_returns_none(self):
        assert _parse_timestr("not a date xyz", with_time=True) is None

    def test_named_timezone_replacement(self):
        # CET is mapped via TZ_REPLACE; this pins the *current* observed conversion.
        # (The exact UTC offset here is suspected buggy and may change in a later phase.)
        assert _parse_timestr("May 1, 2025 18:00 CET", with_time=True) == "2025-05-01T16:00:00Z"

    def test_datetime_input_passthrough(self):
        dt = datetime.datetime(2025, 3, 1, 10, 30, tzinfo=datetime.timezone.utc)
        assert _parse_timestr(dt, with_time=True) == "2025-03-01T10:30:00Z"

    def test_datetime_input_date_only(self):
        dt = datetime.datetime(2025, 3, 1, 10, 30)
        assert _parse_timestr(dt, with_time=False) == "2025-03-01"


# --------------------------------------------------------------------------- #
# parse_all_times
# --------------------------------------------------------------------------- #
class TestParseAllTimes:
    def test_appends_year_from_id(self):
        conf = {
            "id": "zzz2025",
            "timezone": "AoE",
            "conferenceStartDate": "Jun 1",
            "timeline": [{"deadline": "Jan 15, 23:59"}],
        }
        out = parse_all_times(conf)
        assert out["conferenceStartDate"] == "2025-06-01"
        assert out["timeline"][0]["deadline"] == "2025-01-16T11:59:00Z"

    def test_invalid_id_year_raises(self):
        with pytest.raises(ValueError):
            parse_all_times({"id": "noyear", "timeline": []})

    def test_empty_conference_is_noop(self):
        # parse_all_times asserts emptiness when 'id' is absent, then KeyErrors on timeline.
        with pytest.raises(KeyError):
            parse_all_times({})


# --------------------------------------------------------------------------- #
# join_conferences
# --------------------------------------------------------------------------- #
class TestJoinConferences:
    def test_master_overrides_slave_and_unions_tags(self):
        master = {"id": "x2025", "tags": ["ML"], "timeline": [{"deadline": "2025-01-01"}], "title": "M"}
        slave = {
            "id": "x2025",
            "tags": ["CV"],
            "timeline": [{"deadline": "2025-02-02"}],
            "title": "S",
            "website": "w",
        }
        out = join_conferences(master=master, slave=slave)
        assert out["title"] == "M"  # master wins
        assert out["tags"] == ["CV", "ML"]  # sorted union
        assert out["timeline"] == [{"deadline": "2025-01-01"}]  # master timeline
        assert out["website"] == "w"  # slave-only key preserved

    def test_tbd_master_timeline_falls_back_to_slave(self):
        master = {"id": "x", "tags": ["ML"], "timeline": [{"deadline": "tbd"}]}
        slave = {"id": "x", "tags": ["ML"], "timeline": [{"deadline": "2025-02-02"}]}
        out = join_conferences(master=master, slave=slave)
        assert out["timeline"] == [{"deadline": "2025-02-02"}]

    def test_empty_master_timeline_falls_back_to_slave(self):
        master = {"id": "x", "tags": [], "timeline": []}
        slave = {"id": "x", "tags": [], "timeline": [{"deadline": "2025-02-02"}]}
        out = join_conferences(master=master, slave=slave)
        assert out["timeline"] == [{"deadline": "2025-02-02"}]


# --------------------------------------------------------------------------- #
# unite_tags
# --------------------------------------------------------------------------- #
def test_unite_tags_shares_sorted_union_across_group():
    group = {
        "a2025": {"id": "a2025", "tags": ["ML", "CV"], "timeline": []},
        "a2024": {"id": "a2024", "tags": ["NLP"], "timeline": []},
    }
    out = unite_tags(group)
    assert out["a2025"]["tags"] == ["CV", "ML", "NLP"]
    assert out["a2024"]["tags"] == ["CV", "ML", "NLP"]


# --------------------------------------------------------------------------- #
# parse_stuff
# --------------------------------------------------------------------------- #
class TestParseStuff:
    def test_gmt_offset_sign_flip(self):
        confs = {"x2025": {"id": "x2025", "timezone": "GMT+2", "timeline": [{"deadline": "2025-01-01T00:00:00Z"}]}}
        out = parse_stuff(confs)
        assert out["x2025"]["timezone"] == "Etc/GMT-2"

    def test_identical_deadlines_merge_note_and_abstract(self):
        confs = {
            "x2025": {
                "id": "x2025",
                "timezone": "Etc/GMT-2",
                "timeline": [
                    {"deadline": "2025-01-01T00:00:00Z", "note": "a"},
                    {"deadline": "2025-01-01T00:00:00Z", "abstractDeadline": "2024-12-01"},
                ],
            }
        }
        out = parse_stuff(confs)
        timeline = out["x2025"]["timeline"]
        assert len(timeline) == 1
        assert timeline[0]["note"] == "a"
        assert timeline[0]["abstractDeadline"] == "2024-12-01"
