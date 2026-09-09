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


MD_HEADER = """# AI Conference Deadlines — upcoming

Upcoming submission deadlines for AI/ML/NLP/CV conferences, sorted by deadline.
All times are UTC (`Z`); most conferences use AoE (UTC-12), see the `timezone` field in the JSON.
Deadlines marked `(est.)` are estimated from previous years, not confirmed by the organizers.

Machine-readable: <https://aideadlines.nauen-it.de/data/conferences.json> (same records, plus
`timezone`, `location`, `tags`, `dataSrc`), past deadlines:
<https://aideadlines.nauen-it.de/data/conferences_archive.json>.
Source and corrections: <https://github.com/tobna/ai-deadlines>

| Conference | Deadline (UTC) | Abstract | Dates | Location | Tags | CORE | h5 | Website |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""


def _cell(value):
    """Render one table cell: empty for missing, pipes escaped so the row stays a row."""
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def conferences_to_markdown(records):
    """Render deadline records (as written to conferences.json) as a markdown table."""
    # ponytail: string sort works because every deadline is ISO-8601 UTC; parse if that ever changes.
    rows = []
    for conf in sorted(records, key=lambda c: str(c.get("deadline", ""))):
        deadline = _cell(conf.get("deadline"))
        if conf.get("isApproximateDeadline"):
            deadline += " (est.)"
        website = _cell(conf.get("website"))
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(conf.get("shortname")),
                    deadline,
                    _cell(conf.get("abstractDeadline")),
                    f"{_cell(conf.get('conferenceStartDate'))} – {_cell(conf.get('conferenceEndDate'))}".strip(" –"),
                    _cell(conf.get("location")),
                    _cell(conf.get("tags")),
                    _cell(conf.get("rating")),
                    _cell(conf.get("h5Index")),
                    f"<{website}>" if website else "",
                ]
            )
            + " |"
        )
    return MD_HEADER + "\n".join(rows) + "\n"


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
    with open(os.path.join(DATA_FOLDER, "deadlines.md"), "w") as f:
        f.write(conferences_to_markdown(list(future_conf.values())))


if __name__ == "__main__":
    main()
