import json

import dateparser

from ..log_config import logger
from .http import fetch_json, fetch_text

_NINO_JSON = (
    "https://raw.githubusercontent.com/NunoDuarte/NunoDuarte.github.io/"
    "refs/heads/master/deadlines/static/data/conferences.json"
)
_NINO_PAST = (
    "https://github.com/NunoDuarte/NunoDuarte.github.io/raw/"
    "refs/heads/master/deadlines/static/data/past_conferences.txt"
)


def parse_past_conferences(raw):
    """The past-conferences file is JSON objects missing the wrapping [] and has a trailing comma."""
    raw = raw.strip()
    if raw.endswith(","):
        raw = raw[:-1]
    if not raw.startswith("["):
        raw = "[" + raw + "]"
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"could not parse ninoduarte past_conferences: {e}")
        return []


def conference_from_nino(conf):
    """Convert one ninoduarte record to our schema, or None if its start date won't parse."""
    start = dateparser.parse(conf["date_start"])
    if start is None:
        logger.warning(f"skipping ninoduarte conf with unparseable date_start: {conf.get('id')}")
        return None
    return {
        "id": conf["id"] + str(start.year),
        "timeline": [{"deadline": conf["deadline"]}],
        "isApproximateDeadline": False,
        "location": conf["location"],
        "shortname": conf["name"],
        "tags": [conf["type"]],
        "timezone": conf["timezone"],
        "website": conf["link"],
        "conferenceStartDate": conf["date_start"],
        "conferenceEndDate": conf["date_end"],
    }


def get_nino_list():
    nino_list = fetch_json(_NINO_JSON) or []

    past_raw = fetch_text(_NINO_PAST)
    if past_raw:
        nino_list += parse_past_conferences(past_raw)

    out_list = []
    for conf in nino_list:
        try:
            data = conference_from_nino(conf)
        except KeyError as e:
            logger.warning(f"skipping ninoduarte conf missing key {e}: {conf.get('id', conf)}")
            continue
        if data is not None:
            out_list.append(data)
    return out_list


if __name__ == "__main__":
    print(get_nino_list())
