"""Tests for the pipeline steps in aideadlines.update_data (no network)."""

import argparse

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
