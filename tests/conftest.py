"""Shared fixtures and helpers for the backend test suite.

These are characterization tests: they pin the *current* observed behavior of the
pipeline so that the Phase 3 restructure can be verified behavior-preserving. Where a
locked value reflects a known bug (e.g. the leap-year drift in see_future), the test
carries a comment saying so; that value is expected to change when the bug is fixed, at
which point the test is updated deliberately rather than by accident.
"""

from copy import deepcopy

import pytest


@pytest.fixture
def real_conf_pair():
    """Two real (non-approximate) annual instances of one conference group."""
    return {
        "abc2023": {
            "id": "abc2023",
            "shortname": "ABC2023",
            "isApproximateDeadline": False,
            "tags": ["ML"],
            "conferenceStartDate": "2023-06-01",
            "timeline": [{"deadline": "2023-01-15"}],
            "title": "ABC Conference",
            "rating": "A",
            "h5Index": 42,
        },
        "abc2024": {
            "id": "abc2024",
            "shortname": "ABC2024",
            "isApproximateDeadline": False,
            "tags": ["ML"],
            "conferenceStartDate": "2024-06-01",
            "timeline": [{"deadline": "2024-01-15"}],
            "title": "ABC Conference",
            "rating": "A",
            "h5Index": 42,
        },
    }


@pytest.fixture
def clone():
    """Return a deepcopy helper so tests never mutate fixtures in place."""
    return deepcopy
