"""Tests for aideadlines.parser.http — status and error handling, no real network."""

import requests

from aideadlines.parser import http


class FakeResponse:
    def __init__(self, status_code=200, text="", json_data=None, json_error=False):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("bad json")
        return self._json_data


class FakeSession:
    """Returns/raises queued outcomes in order; records how many GETs happened."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.headers = {}

    def get(self, url, timeout=None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _install(monkeypatch, outcomes):
    session = FakeSession(outcomes)
    monkeypatch.setattr(http, "_session", session)
    return session


class TestFetch:
    def test_returns_response_on_200(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(200, text="ok")])
        resp = http.fetch("http://x")
        assert resp is not None and resp.text == "ok"

    def test_error_status_returns_none_without_retrying(self, monkeypatch):
        session = _install(monkeypatch, [FakeResponse(503), FakeResponse(200, text="ok")])
        assert http.fetch("http://x") is None
        assert session.calls == 1  # the next hourly run is the retry

    def test_request_exception_returns_none(self, monkeypatch):
        session = _install(monkeypatch, [requests.ConnectionError("boom")])
        assert http.fetch("http://x") is None
        assert session.calls == 1


class TestTypedFetchers:
    def test_fetch_text_passes_through_none(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(500)])
        assert http.fetch_text("http://x") is None

    def test_fetch_json_parses(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(200, json_data={"a": 1})])
        assert http.fetch_json("http://x") == {"a": 1}

    def test_fetch_json_none_on_invalid(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(200, json_error=True)])
        assert http.fetch_json("http://x") is None

    def test_fetch_yaml_parses(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(200, text="a: 1\nb: 2")])
        assert http.fetch_yaml("http://x") == {"a": 1, "b": 2}

    def test_fetch_yaml_none_on_invalid(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(200, text="a: [unclosed")])
        assert http.fetch_yaml("http://x") is None

    def test_fetch_soup_parses_html(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(200, text="<table><tr><td>hi</td></tr></table>")])
        soup = http.fetch_soup("http://x")
        assert soup is not None and soup.find("td").get_text() == "hi"

    def test_fetch_soup_none_on_failure(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(500)])
        assert http.fetch_soup("http://x") is None
