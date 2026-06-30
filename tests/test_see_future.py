"""Characterization tests for aideadlines.parser.see_future.estimate_future_conferences."""

from aideadlines.parser.see_future import estimate_future_conferences


def test_too_few_deadlines_returns_empty(real_conf_pair):
    single = {"abc2024": real_conf_pair["abc2024"]}
    assert estimate_future_conferences(single) == {}


def test_estimates_annual_rhythm(real_conf_pair, clone):
    fut = estimate_future_conferences(clone(real_conf_pair), end_in_years=2, max_approximations=2)
    assert sorted(fut.keys()) == ["abc2025", "abc2026"]


def test_estimated_metadata_propagates(real_conf_pair, clone):
    fut = estimate_future_conferences(clone(real_conf_pair), end_in_years=2, max_approximations=2)
    est = fut["abc2025"]
    assert est["isApproximateDeadline"] is True
    assert est["dataSrc"] == "estimate"
    assert est["shortname"] == "ABC2025"
    assert est["rating"] == "A"
    assert est["h5Index"] == 42
    assert est["title"] == "ABC Conference"


def test_max_approximations_caps_count(real_conf_pair, clone):
    fut = estimate_future_conferences(clone(real_conf_pair), end_in_years=10, max_approximations=1)
    assert list(fut.keys()) == ["abc2025"]


def test_deadline_shift_current_leap_year_drift(real_conf_pair, clone):
    # KNOWN BUG (Phase 3 target): timedelta(days=365) ignores leap years, so the 2024-01-15
    # deadline drifts one day to 2025-01-14. This pins current behavior; update to
    # 2025-01-15 once the calendar-aware shift lands.
    fut = estimate_future_conferences(clone(real_conf_pair), end_in_years=2, max_approximations=2)
    dl = fut["abc2025"]["timeline"][0]["deadline"]
    assert dl.year == 2025 and dl.month == 1 and dl.day == 14
