from datetime import datetime, timedelta
from ..log_config import logger

import json
import os
import dateparser
import yaml


def estimate_future_conferences(conferences, end_in_years=2, max_approximations=2):
    conferences = {key: conf for key, conf in conferences.items() if "conferenceStartDate" in conf}
    real_conferences = {key: conf for key, conf in conferences.items() if not conf["isApproximateDeadline"]}
    deadlines = [conf["timeline"][0]["deadline"] for conf in real_conferences.values()]
    if len(deadlines) < 2:
        logger.info(f"too few past deadlines for future estimation of {list(conferences.keys())}")
        return {}

    deadlines = [dateparser.parse(dl) if isinstance(dl, str) else dl for dl in deadlines]
    deadlines = sorted(deadlines, key=lambda x: x.year)
    deltas = []
    for d1, d2 in zip(deadlines[:-1], deadlines[1:]):
        delta = d2 - d1
        years = round(delta.days / 365)
        deltas.append(years)
    yearly_rythm = max([round(sum(deltas) / len(deltas)), 1])
    last_conf = max(list(real_conferences.values()), key=lambda x: x["conferenceStartDate"])
    last_start = dateparser.parse(last_conf["conferenceStartDate"])
    next_year = last_start.year + yearly_rythm

    future_conferences = {}
    while (
        next_year <= datetime.now().year + end_in_years
        and next_year <= last_start.year + max_approximations * yearly_rythm
    ):
        data = {
            "id": last_conf["id"][:-4] + str(next_year),
            "dataSrc": "estimate",
            "isApproximateDeadline": True,
            "shortname": last_conf["shortname"][:-4] + str(next_year),
            "tags": last_conf["tags"],
            "timeline": [],
            "conferenceStartDate": last_start + timedelta(days=365 * (next_year - last_start.year)),
            "conferenceEndDate": (
                last_start + timedelta(days=365 * (next_year - last_start.year) + 5)
            ),  # just assume 1 week
        }
        for dates in last_conf["timeline"]:
            next_timeline = {}
            for key in dates:
                if "deadline" in key.lower():
                    old_date = dates[key]
                    if isinstance(old_date, str):
                        old_date = dateparser.parse(old_date)
                    next_timeline[key] = old_date + timedelta(days=365 * (next_year - last_start.year))
                elif key == "note":
                    next_timeline[key] = f"From {last_conf['shortname']}: {dates[key]}"
                else:
                    raise ValueError(f"weird key in timeline: {key}")
            data["timeline"].append(next_timeline)

        if "title" in last_conf:
            data["title"] = last_conf["title"]
        if "rating" in last_conf:
            data["rating"] = last_conf["rating"]
        if "h5Index" in last_conf:
            data["h5Index"] = last_conf["h5Index"]
        if data["id"] not in conferences:
            future_conferences[data["id"]] = data
            logger.info("estimated %s" % data["id"])
        else:
            logger.debug(f"{data['id']} already in conferences")
        next_year += yearly_rythm

    return future_conferences


if __name__ == "__main__":
    this_folder = os.path.dirname(__file__)
    with open(os.path.join(this_folder, os.pardir, os.pardir, "conferences", "wacv.yaml")) as f:
        wacvs = yaml.safe_load(f)
    for conf in wacvs.values():
        for dates in conf["timeline"]:
            for key in dates:
                if "deadline" in key:
                    dates[key] = dateparser.parse(dates[key])
    logger.info(wacvs)
    logger.info(f"Keys: {wacvs.keys()}")
    future = estimate_future_conferences(wacvs, end_in_years=4, max_approximations=4)
    logger.info("Future:\n")
    for key, conf in future.items():
        print(key, ":", conf)
