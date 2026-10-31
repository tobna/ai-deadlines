import os
import random
import re

import yaml

from .log_config import logger
from .merge import ID_ALIASES
from .parser.http import fetch_soup

this_folder = os.path.dirname(__file__)


def make_conf_rank_function():
    # Google Scholar blocks scraping, so h5 values are read from the committed YAML only.
    h5_file = os.path.join(this_folder, os.pardir, "rank", "h5index.yaml")
    with open(h5_file, "r") as f:
        _short_to_h5 = yaml.safe_load(f)
    logger.info(f"got {len(_short_to_h5)} conference h5 values", flush=True)

    def add_h5(conf):
        conf_id = conf["id"][:-4]
        if conf_id in _short_to_h5:
            conf["h5Index"] = _short_to_h5[conf_id]
        return conf

    return add_h5


_allowed_rank_re = re.compile(r"[A-H]\*?$")


def _get_core_rank(shortname):
    shortname = shortname.lower().replace("threedv", "3dv")
    core_url = f"https://portal.core.edu.au/conf-ranks/?search={shortname}&by=all"
    core_res = fetch_soup(core_url)
    if core_res is None:  # unreachable, or blocking us (403)
        raise ConnectionError(f"CORE portal did not answer {core_url}")

    for row in core_res.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 4:
            continue
        if tds[1].get_text().strip().lower() == shortname:
            rank = tds[3].get_text().strip()
            if _allowed_rank_re.match(rank):
                return rank

    return None


def _core_search_names(group):
    """CORE may list a group under a spelling we fold away (``rulemlrr`` -> ``ruleml+rr``)."""
    return [group] + [alias for alias, canonical in ID_ALIASES.items() if canonical == group]


def _lookup_core_rank(group):
    for name in _core_search_names(group):
        rank = _get_core_rank(name)
        if rank is not None:
            return rank
    return None


def make_core_rank_function(conference_groups, online=True):
    """Rank lookup from ``rank/core.yaml``; online, first refresh one random group's rank from CORE.

    The CORE portal answers 403 to a burst of requests, and its rankings change only every few
    years, so each run asks about a single group picked at random: with hourly runs every group
    is rechecked every few days on average, with no state to keep.
    """
    core_save_file = os.path.join(this_folder, os.pardir, "rank", "core.yaml")
    core_ranks = {}
    if os.path.isfile(core_save_file):
        with open(core_save_file) as f:
            core_ranks = yaml.safe_load(f) or {}

    if online and conference_groups:
        group = random.choice(list(conference_groups))
        try:
            rank = _lookup_core_rank(group)
        except ConnectionError as e:
            logger.error(f"ERROR looking up the CORE rank of {group}, keeping the stored one: {e}")
        else:
            logger.info(f"CORE rank of {group}: {rank}")
            if rank is not None and core_ranks.get(group) != rank:
                core_ranks[group] = rank
                with open(core_save_file, "w") as f:
                    yaml.safe_dump(core_ranks, f)

    def add_core_rank(conf):
        conf_id = conf["id"][:-4]

        if conf_id in core_ranks:
            conf["rating"] = core_ranks[conf_id]

        return conf

    return add_core_rank
