"""Acceptance rates from openaccept.org (community-curated, CC BY-SA 4.0).

The site itself is a small volunteer project that rate-limits scrapers, but everything behind
it is published as one schema-checked JSON file per conference in the metadata repository —
so we read that instead and leave their server alone. Same tree-then-raw pattern as
``ccf_deadlines``/``hf_list``.

Unlike the deadline parsers this doesn't merge: rates are attached in ``write_groups`` the
same way CORE ratings are. When the fetch fails — or when the throttle below says the data is
still fresh — nothing is attached, and the values already in ``conferences/*.yaml`` are simply
written back unchanged.
"""

import os
import time
from urllib.parse import quote

from ..log_config import logger
from .http import fetch_json

_OA_TREE = "https://api.github.com/repos/OpenAccept/openaccept-metadata/git/trees/master?recursive=1"
_OA_RAW = "https://raw.githubusercontent.com/OpenAccept/openaccept-metadata/refs/heads/master/"

# conference groups whose openaccept file name differs from our id
ALIASES = {"acmmm": "acm mm"}

# Acceptance rates change a couple of times a year, so refresh at most this often. Longer than a
# day, so the daily pipeline run doesn't ask every time.
REFRESH_HOURS = 30
_STAMP_FILE = os.path.join(os.path.dirname(__file__), os.pardir, "data", ".last_openaccept_update")


def _due():
    """True if the rates in ``conferences/*.yaml`` are older than ``REFRESH_HOURS``."""
    # ponytail: the stamp file's mtime is the timestamp; nothing to write out and re-parse.
    try:
        return time.time() - os.path.getmtime(_STAMP_FILE) > REFRESH_HOURS * 3600
    except OSError:
        return True


def files_by_name(tree):
    """Lower-cased conference name -> metadata file path (`ai/NeurIPS.json` -> `neurips`)."""
    return {
        os.path.basename(item["path"])[: -len(".json")].lower(): item["path"]
        for item in tree.get("tree", [])
        if item["path"].endswith(".json") and not item["path"].startswith(".")
    }


def stats_from_metadata(data):
    """{year: (submitted, accepted)} from a metadata file's main track.

    ``second_track_yearly_data`` (ACL Findings and friends) lives under its own key, so taking
    ``yearly_data`` is exactly the main research track.
    """
    stats = {}
    for entry in data.get("yearly_data", []):
        year, submitted, accepted = entry.get("year"), entry.get("submitted"), entry.get("accepted")
        # community-edited: skip anything that isn't a sane accepted-out-of-submitted count
        if year and submitted and accepted and accepted <= submitted:
            stats[year] = (submitted, accepted)
    return stats


def get_acceptance_stats(groups):
    """{group: {year: (submitted, accepted)}} for the conference groups openaccept.org covers.

    Empty when the last scrape is still fresh — the caller then leaves the stored rates alone.
    """
    if not _due():
        logger.info(f"skipping openaccept metadata (fetched less than {REFRESH_HOURS}h ago)")
        return {}

    tree = fetch_json(_OA_TREE)
    files = files_by_name(tree) if tree is not None else {}
    if not files:
        logger.error("ERROR no openaccept metadata files found")
        return {}

    stats = {}
    for group in groups:
        path = files.get(ALIASES.get(group, group))
        if path is None:
            continue
        data = fetch_json(_OA_RAW + quote(path))
        if data is None:
            continue
        group_stats = stats_from_metadata(data)
        if group_stats:
            stats[group] = group_stats
    if stats:  # only start the clock on a fetch that actually worked
        open(_STAMP_FILE, "w").close()
    logger.info(f"got acceptance rates for {len(stats)} conference groups")
    return stats


def attach_rate(conf, year_stats):
    """Set the conference's own year's acceptance rate, else the most recent earlier one.

    The raw counts ride along so the frontend can show "5290 of 21575" rather than only a
    percentage the reader has to take on faith.
    """
    year = int(conf["id"][-4:])
    source_year = year if year in year_stats else max((y for y in year_stats if y < year), default=None)
    if source_year is not None:
        submitted, accepted = year_stats[source_year]
        conf["acceptanceRate"] = round(100 * accepted / submitted, 2)
        conf["acceptanceRateYear"] = source_year
        conf["acceptedPapers"] = accepted
        conf["submittedPapers"] = submitted
    return conf
