import os
import re
from datetime import datetime, timedelta

import dateparser
import requests
import yaml
from bs4 import BeautifulSoup

from .log_config import logger

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
    core_res = requests.get(core_url)
    core_res = BeautifulSoup(core_res.text, "html.parser")

    for row in core_res.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 4:
            continue
        if tds[1].get_text().strip().lower() == shortname:
            rank = tds[3].get_text().strip()
            if _allowed_rank_re.match(rank):
                return rank

    return None


def make_core_rank_function(conference_groups, online=True, force_update=False):
    core_save_file = os.path.join(this_folder, os.pardir, "rank", "core.yaml")
    if os.path.isfile(core_save_file):
        with open(core_save_file, "r") as f:
            core_ranks = yaml.safe_load(f)
        if core_ranks is None:
            core_ranks = {}
    else:
        core_ranks = {}
        force_update = True

    last_update_file = os.path.join(this_folder, "data", ".last_core_update")
    if not os.path.isfile(last_update_file):
        force_update = True
    else:
        with open(last_update_file, "r") as f:
            last_update = dateparser.parse(f.read().strip())

        if last_update is None:
            force_update = True
        else:
            force_update = force_update or last_update + timedelta(days=1) < datetime.now()

    if force_update and online:
        logger.info(f"Updating core ranks for {len(conference_groups)} conferences")

        for i, group in enumerate(conference_groups):
            rank = _get_core_rank(group)
            if rank is not None:
                core_ranks[group] = rank
                logger.info(f"{i+1}/{len(conference_groups)}: {group} -> {rank}")

        with open(core_save_file, "w") as f:
            yaml.safe_dump(core_ranks, f)
        with open(last_update_file, "w") as f:
            f.write(datetime.now().isoformat())

    def add_core_rank(conf):
        conf_id = conf["id"][:-4]

        if conf_id in core_ranks:
            conf["rating"] = core_ranks[conf_id]

        return conf

    return add_core_rank
