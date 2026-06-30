import json
import os
from copy import deepcopy
from datetime import datetime

import dateparser
import pytz
import yaml

from .log_config import logger
from .utils import normalize_timezone_for_js

THIS_FOLDER = os.path.dirname(__file__)
CONFERENCE_FOLDER = os.path.join(THIS_FOLDER, os.pardir, "conferences")
DATA_FOLDER = os.path.join(THIS_FOLDER, "data")


def load_conferences():
    conferences = {}
    for conf_file in os.listdir(CONFERENCE_FOLDER):
        with open(os.path.join(CONFERENCE_FOLDER, conf_file), "r") as f:
            file_confs = yaml.safe_load(f)
        conferences = {**file_confs, **conferences}
    return conferences


def split_future_past(conferences):
    """Explode each conference's timeline into one record per deadline, partitioned by now."""
    future_conf, past_conf = {}, {}
    now = datetime.now().astimezone(pytz.UTC)
    for conf_id, conf in conferences.items():
        conf["timezone"] = normalize_timezone_for_js(conf.get("timezone", "AoE"))
        for i, dates in enumerate(conf["timeline"]):
            conf_cpy = deepcopy(conf)
            conf_cpy.pop("timeline")
            conf_cpy = {**conf_cpy, **dates}
            record_id = f"{conf_id}-{i + 1}"
            conf_cpy["id"] = record_id
            try:
                if dateparser.parse(conf_cpy["deadline"]) > now:
                    future_conf[record_id] = conf_cpy
                else:
                    past_conf[record_id] = conf_cpy
            except TypeError as e:
                logger.error(f"Type Error for conference {conf_cpy}: {e}")
    return future_conf, past_conf


def main():
    conferences = load_conferences()
    logger.info(f"managing {len(conferences)} conference instances")
    logger.info(sorted(list(conferences.keys())))

    future_conf, past_conf = split_future_past(conferences)
    logger.info(f"past: {sorted(list(past_conf.keys()))}")
    logger.info(f"future: {sorted(list(future_conf.keys()))}")

    with open(os.path.join(DATA_FOLDER, "conferences.json"), "w") as f:
        json.dump(list(future_conf.values()), f)
    with open(os.path.join(DATA_FOLDER, "conferences_archive.json"), "w") as f:
        json.dump(list(past_conf.values()), f)


if __name__ == "__main__":
    main()
