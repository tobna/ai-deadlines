"""Tests for the pipeline steps in aideadlines.update_data (no network)."""

import argparse
from types import SimpleNamespace

import pytest

from aideadlines import update_data


def test_historic_scrape_stops_after_five_empty_years(monkeypatch):
    calls = []

    def no_data(year):
        calls.append(year)
        return {}

    def broken(year):
        calls.append(year)
        raise ValueError("site changed")

    monkeypatch.setattr(update_data, "PARSER", [no_data])
    monkeypatch.setattr(update_data, "parse_wacv", broken)
    monkeypatch.setattr(update_data, "XAI_PARSER", [])
    update_data.scrape_official_websites({}, argparse.Namespace(historic=True))
    assert len(calls) == 10  # five empty years per parser, then the next one


@pytest.mark.parametrize(
    "abstract,deadline,flagged",
    [
        ("2099-01-20T11:59:59Z", "2099-01-27T11:59:59Z", False),  # a week before: fine
        ("2098-01-20T11:59:59Z", "2099-01-27T11:59:59Z", True),  # a year before (the ICML 2026 typo)
        ("2099-03-01T11:59:59Z", "2099-01-27T11:59:59Z", True),  # after the paper deadline
        ("2010-03-01T11:59:59Z", "2010-01-27T11:59:59Z", False),  # past: left to the archive
    ],
)
def test_implausible_abstract_of_an_upcoming_deadline_is_an_error(monkeypatch, abstract, deadline, flagged):
    errors = []
    monkeypatch.setattr(update_data, "logger", SimpleNamespace(error=errors.append))
    conf = {"id": "x2099", "timeline": [{"deadline": deadline, "abstractDeadline": abstract}]}
    update_data.flag_implausible_abstracts({"x2099": conf})
    assert bool(errors) is flagged
    assert conf["timeline"][0]["abstractDeadline"] == abstract  # never dropped
