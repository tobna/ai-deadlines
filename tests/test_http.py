"""Tests for aideadlines.parser.http — retry/timeout/status behavior, no real network."""

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
    monkeypatch.setattr(http.time, "sleep", lambda _s: None)  # don't actually wait
    return session


class TestFetch:
    def test_returns_response_on_200(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(200, text="ok")])
        resp = http.fetch("http://x")
        assert resp is not None and resp.text == "ok"

    def test_retries_transient_then_succeeds(self, monkeypatch):
        session = _install(monkeypatch, [FakeResponse(503), FakeResponse(200, text="ok")])
        resp = http.fetch("http://x", retries=3)
        assert resp is not None and resp.text == "ok"
        assert session.calls == 2

    def test_gives_up_after_retries_on_persistent_5xx(self, monkeypatch):
        session = _install(monkeypatch, [FakeResponse(503)] * 3)
        assert http.fetch("http://x", retries=3) is None
        assert session.calls == 3

    def test_non_retry_status_returns_none_immediately(self, monkeypatch):
        session = _install(monkeypatch, [FakeResponse(404)])
        assert http.fetch("http://x", retries=3) is None
        assert session.calls == 1  # 404 is not retried

    def test_retries_on_request_exception(self, monkeypatch):
        session = _install(monkeypatch, [requests.ConnectionError("boom"), FakeResponse(200, text="ok")])
        resp = http.fetch("http://x", retries=3)
        assert resp is not None and resp.text == "ok"
        assert session.calls == 2


class TestTypedFetchers:
    def test_fetch_text_passes_through_none(self, monkeypatch):
        _install(monkeypatch, [FakeResponse(500)] * 3)
        assert http.fetch_text("http://x", retries=3) is None

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
        _install(monkeypatch, [FakeResponse(500)] * 3)
        assert http.fetch_soup("http://x", retries=3) is None
