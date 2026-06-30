"""Lightweight schema validation for the conference data.

Run before the auto-commit (see update.py) so a malformed scrape can't silently land in the
repository. ``validate_conferences`` is pure and unit-tested; ``main`` exits non-zero when
any problem is found.
"""

import os
import sys

import dateparser
import yaml

from .log_config import logger

THIS_FOLDER = os.path.dirname(__file__)
CONFERENCE_FOLDER = os.path.join(THIS_FOLDER, os.pardir, "conferences")

REQUIRED_KEYS = ("id", "timeline")


def validate_conferences(conferences):
    """Return a list of human-readable problems; an empty list means the data is valid."""
    errors = []
    for key, conf in conferences.items():
        if not isinstance(conf, dict):
            errors.append(f"{key}: not a mapping")
            continue
        for req in REQUIRED_KEYS:
            if req not in conf:
                errors.append(f"{key}: missing required key '{req}'")
        if not conf.get("shortname") and not conf.get("title"):
            errors.append(f"{key}: needs a shortname or title")
        timeline = conf.get("timeline")
        if not isinstance(timeline, list) or len(timeline) == 0:
            errors.append(f"{key}: timeline must be a non-empty list")
            continue
        for i, entry in enumerate(timeline):
            if "deadline" not in entry:
                errors.append(f"{key}: timeline[{i}] missing 'deadline'")
            elif dateparser.parse(str(entry["deadline"])) is None:
                errors.append(f"{key}: timeline[{i}] has unparseable deadline {entry['deadline']!r}")
    return errors


def load_conferences():
    conferences = {}
    for conf_file in os.listdir(CONFERENCE_FOLDER):
        with open(os.path.join(CONFERENCE_FOLDER, conf_file)) as f:
            conferences.update(yaml.safe_load(f) or {})
    return conferences


def main():
    errors = validate_conferences(load_conferences())
    if errors:
        for e in errors:
            logger.error(f"VALIDATION: {e}")
        logger.error(f"conference validation failed with {len(errors)} problem(s)")
        sys.exit(1)
    logger.info("conference validation passed")


if __name__ == "__main__":
    main()
