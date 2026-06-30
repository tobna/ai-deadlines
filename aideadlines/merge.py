"""Merge conference records from multiple sources, honoring source priority.

This consolidates logic that was previously copy-pasted four times (once per source) in
``update_data.py``. Keeping it here, importable and side-effect-free at import time, is also
what makes it testable (see ``tests/test_merge_priority.py``).
"""

import dateparser

from .log_config import logger
from .utils import join_conferences

# Lower index = lower priority. A source overwrites another only when the existing source
# is at the same-or-lower priority. ``manual`` is highest: hand-curated edits win over every
# scraper. ``estimate`` is lowest: a guessed instance yields to any real data.
SOURCES = ["estimate", "ninoduarte-git", "ccf-deadlines", "hf-repo", "off-website", "manual"]


def tag_wacv_round(conf, conf_id):
    """WACV feeds often carry a single undated round; label it Round 1/2 by deadline month.

    Mutates ``conf`` in place. No-op for non-WACV ids or multi-deadline timelines.
    """
    if conf_id.startswith("wacv") and len(conf["timeline"]) == 1:
        deadline = dateparser.parse(conf["timeline"][0]["deadline"])
        if deadline is None:
            logger.warning(f"Failed to parse deadline for WACV conference {conf_id}")
            rnd = 2
        else:
            rnd = 1 if deadline.month <= 8 else 2
        conf["timeline"][0]["note"] = f"Round {rnd}"


def merge_one(conferences, new_conf, conf_id, src_name, reestimate_groups, overwrite_equal=True):
    """Merge a single conference record into ``conferences`` by source priority.

    Mutates ``conferences`` and appends affected group prefixes to ``reestimate_groups``,
    matching the original inline merge behavior.

    ``overwrite_equal`` selects ``<=`` (a same-priority source overwrites) vs ``<`` (it does
    not) — the historical asymmetry where ninoduarte-git used ``<`` and the others ``<=``.
    """
    if conf_id not in conferences:
        conferences[conf_id] = new_conf
        conferences[conf_id]["dataSrc"] = src_name
        logger.success(f"NEW CONFERENCE: {conferences[conf_id]}")
        reestimate_groups.append(conf_id[:-4])
        return

    existing_priority = SOURCES.index(conferences[conf_id]["dataSrc"])
    new_priority = SOURCES.index(src_name)
    new_takes_precedence = existing_priority <= new_priority if overwrite_equal else existing_priority < new_priority

    if new_takes_precedence:
        if conferences[conf_id]["dataSrc"] == "estimate":
            logger.success(f"FIRST DATA FOR CONFERENCE: {conferences[conf_id]}")
            reestimate_groups.append(conf_id[:-4])
            conferences[conf_id] = new_conf
        else:
            conferences[conf_id] = join_conferences(slave=conferences[conf_id], master=new_conf)
        conferences[conf_id]["dataSrc"] = src_name
    else:
        conferences[conf_id] = join_conferences(slave=new_conf, master=conferences[conf_id])


def merge_source(conferences, items, src_name, reestimate_groups, overwrite_equal=True, id_transform=None):
    """Merge every record in ``items`` from one source into ``conferences``.

    ``id_transform`` optionally rewrites each record's id (e.g. ``nips`` -> ``neurips`` for
    the ninoduarte feed). WACV round tagging is applied before merging.
    """
    for item in items:
        conf_id = item["id"] if id_transform is None else id_transform(item["id"])
        tag_wacv_round(item, conf_id)
        merge_one(conferences, item, conf_id, src_name, reestimate_groups, overwrite_equal=overwrite_equal)
