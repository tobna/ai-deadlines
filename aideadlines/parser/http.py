"""Resilient HTTP helpers shared by the parsers.

Every parser used to fetch URLs with a bare ``requests.get(...).text``/``.json()`` — no
timeout (a slow host could hang the whole pipeline), no status check (an error page would be
parsed as data), and no retry. These helpers add a pooled session, a timeout, status
checking, and bounded retries with backoff for transient failures, returning ``None`` on
persistent failure so callers can skip a source or record instead of crashing.
"""

import time

import requests
import yaml
from bs4 import BeautifulSoup

from ..log_config import logger

DEFAULT_TIMEOUT = 20
DEFAULT_RETRIES = 3
BACKOFF_SECONDS = 1.0
_RETRY_STATUS = {429, 500, 502, 503, 504}
_USER_AGENT = "aideadlines-bot (+https://aideadlines.nauen-it.de)"

_session = requests.Session()
_session.headers.update({"User-Agent": _USER_AGENT})


def fetch(url, *, timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES, backoff=BACKOFF_SECONDS):
    """GET ``url``, retrying transient failures. Returns a 200 Response, or ``None``."""
    for attempt in range(1, retries + 1):
        try:
            response = _session.get(url, timeout=timeout)
        except requests.RequestException as e:
            logger.warning(f"GET {url} failed (attempt {attempt}/{retries}): {e}")
        else:
            if response.status_code == 200:
                return response
            if response.status_code in _RETRY_STATUS:
                logger.warning(f"GET {url} -> {response.status_code} (attempt {attempt}/{retries})")
            else:
                logger.warning(f"GET {url} -> {response.status_code}; giving up")
                return None
        if attempt < retries:
            time.sleep(backoff * attempt)
    logger.error(f"GET {url} failed after {retries} attempts")
    return None


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
