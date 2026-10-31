"""HTTP helpers shared by the parsers: a pooled session, a timeout, and a status check.

A bare ``requests.get`` has no timeout (a slow host could hang the whole pipeline) and parses
an error page as data. These helpers return ``None`` on any failure so callers can skip a
source or record instead of crashing. There are deliberately no retries: the pipeline runs
every hour, a failed source keeps its stored data until then, and in practice every retried
URL was a host that never answers (each retry only added another timeout).
"""

import requests
import yaml
from bs4 import BeautifulSoup

from ..log_config import logger

DEFAULT_TIMEOUT = 20
_USER_AGENT = "aideadlines-bot (+https://aideadlines.nauen-it.de)"

_session = requests.Session()
_session.headers.update({"User-Agent": _USER_AGENT})


def fetch(url, *, timeout=DEFAULT_TIMEOUT):
    """GET ``url`` once. Returns a 200 Response, or ``None`` (logged) on any failure."""
    try:
        response = _session.get(url, timeout=timeout)
    except requests.RequestException as e:
        logger.warning(f"GET {url} failed: {e}")
        return None
    if response.status_code != 200:
        logger.warning(f"GET {url} -> {response.status_code}")
        return None
    return response


def fetch_text(url, **kwargs):
    response = fetch(url, **kwargs)
    return response.text if response is not None else None


def fetch_json(url, **kwargs):
    response = fetch(url, **kwargs)
    if response is None:
        return None
    try:
        return response.json()
    except ValueError as e:
        logger.warning(f"GET {url}: invalid JSON: {e}")
        return None


def fetch_yaml(url, **kwargs):
    text = fetch_text(url, **kwargs)
    if text is None:
        return None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        logger.warning(f"GET {url}: invalid YAML: {e}")
        return None


def fetch_soup(url, parser="html.parser", **kwargs):
    text = fetch_text(url, **kwargs)
    return BeautifulSoup(text, parser) if text is not None else None
