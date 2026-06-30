"""Tests for aideadlines.merge — the source-priority merge logic extracted from update_data.

Pins the behavior the four inline blocks had: priority ordering (manual highest, estimate
lowest), the estimate-gets-replaced rule, the <= vs < asymmetry, WACV round tagging, and id
transforms.
"""

from aideadlines.merge import SOURCES, merge_one, merge_source, tag_wacv_round


def _conf(dataSrc=None, title="t", tags=("ML",), deadline="2025-01-01"):
    c = {"id": "x2025", "tags": list(tags), "timeline": [{"deadline": deadline}], "title": title}
    if dataSrc is not None:
        c["dataSrc"] = dataSrc
    return c


class TestPriorityOrder:
    def test_manual_is_highest_estimate_is_lowest(self):
        assert SOURCES[0] == "estimate"
        assert SOURCES[-1] == "manual"


class TestMergeOne:
    def test_new_conference_is_added_and_group_flagged(self):
        conferences, groups = {}, []
        merge_one(conferences, _conf(), "abc2025", "hf-repo", groups)
        assert conferences["abc2025"]["dataSrc"] == "hf-repo"
        assert groups == ["abc"]  # "abc2025"[:-4]

    def test_estimate_is_fully_replaced_and_reestimated(self):
        conferences = {"x2025": _conf(dataSrc="estimate", title="old")}
        groups = []
        merge_one(conferences, _conf(title="new"), "x2025", "hf-repo", groups)
        assert conferences["x2025"]["title"] == "new"
        assert conferences["x2025"]["dataSrc"] == "hf-repo"
        assert groups == ["x"]

    def test_higher_priority_overwrites_lower_via_master_merge(self):
        conferences = {"x2025": _conf(dataSrc="hf-repo", title="old", tags=["ML"])}
        groups = []
        merge_one(conferences, _conf(title="new", tags=["CV"]), "x2025", "manual", groups)
        assert conferences["x2025"]["title"] == "new"
        assert conferences["x2025"]["dataSrc"] == "manual"
        assert conferences["x2025"]["tags"] == ["CV", "ML"]  # union
        assert groups == []  # not new, not estimate -> no reestimate

    def test_lower_priority_does_not_overwrite_higher(self):
        conferences = {"x2025": _conf(dataSrc="manual", title="keep")}
        groups = []
        merge_one(conferences, _conf(title="ignored"), "x2025", "hf-repo", groups)
        assert conferences["x2025"]["title"] == "keep"
        assert conferences["x2025"]["dataSrc"] == "manual"

    def test_overwrite_equal_true_replaces_same_priority(self):
        conferences = {"x2025": _conf(dataSrc="hf-repo", title="old")}
        merge_one(conferences, _conf(title="new"), "x2025", "hf-repo", [], overwrite_equal=True)
        assert conferences["x2025"]["title"] == "new"

    def test_overwrite_equal_false_keeps_same_priority(self):
        conferences = {"x2025": _conf(dataSrc="ninoduarte-git", title="keep")}
        merge_one(conferences, _conf(title="ignored"), "x2025", "ninoduarte-git", [], overwrite_equal=False)
        assert conferences["x2025"]["title"] == "keep"


class TestTagWacvRound:
    def test_early_month_is_round_1(self):
        c = {"timeline": [{"deadline": "2025-03-01"}]}
        tag_wacv_round(c, "wacv2025")
        assert c["timeline"][0]["note"] == "Round 1"

    def test_late_month_is_round_2(self):
        c = {"timeline": [{"deadline": "2025-11-01"}]}
        tag_wacv_round(c, "wacv2025")
        assert c["timeline"][0]["note"] == "Round 2"

    def test_non_wacv_untouched(self):
        c = {"timeline": [{"deadline": "2025-03-01"}]}
        tag_wacv_round(c, "cvpr2025")
        assert "note" not in c["timeline"][0]

    def test_multi_deadline_untouched(self):
        c = {"timeline": [{"deadline": "2025-03-01"}, {"deadline": "2025-09-01"}]}
        tag_wacv_round(c, "wacv2025")
        assert "note" not in c["timeline"][0]


def test_merge_source_merges_each_item_by_its_id():
    conferences, groups = {}, []
    merge_source(
        conferences,
        [{"id": "neurips2025", "tags": ["ML"], "timeline": [{"deadline": "2025-01-01"}]}],
        "ninoduarte-git",
        groups,
        overwrite_equal=False,
    )
    assert "neurips2025" in conferences
    assert conferences["neurips2025"]["dataSrc"] == "ninoduarte-git"
