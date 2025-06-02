from datetime import datetime, timedelta

import dateparser


def estimate_future_conferences(conferences, end_in_years=2):
    deadlines = [conf["deadline"] for conf in conferences.values() if "deadline" in conf]
    if len(deadlines) < 2:
        return {}

    deadlines = [dateparser.parse(dl) for dl in deadlines]
    deadlines = sorted(deadlines, key=lambda x: x.year)
    deltas = []
    for d1, d2 in zip(deadlines[:-1], deadlines[1:]):
        delta = d2 - d1
        years = round(delta.days / 365)
        deltas.append(years)
    yearly_rythm = round(sum(deltas) / len(deltas))
    next_year = deadlines[-1].year + yearly_rythm
    last_conf = max(list(conferences.values()), key=lambda x: x["deadline"])
    last_deadline = dateparser.parse(last_conf["deadline"])
    last_start = dateparser.parse(last_conf["conferenceStartDate"])

    future_conferences = {}
    while next_year <= datetime.now().year + end_in_years:
        data = {
            "id": last_conf["id"][:-4] + str(next_year),
            "dataSrc": "estimate",
            "isApproximateDeadline": True,
            "shortname": last_conf["shortname"][:-4] + str(next_year),
            "tags": last_conf["tags"],
            "deadline": last_deadline + timedelta(days=365 * (next_year - last_start.year)),
            "conferenceStartDate": last_start + timedelta(days=365 * (next_year - last_start.year)),
            "conferenceEndDate": (
                last_start + timedelta(days=365 * (next_year - last_start.year) + 5)
            ),  # just assume 1 week
        }
        if "title" in last_conf:
            data["title"] = last_conf["title"]
        if "rating" in last_conf:
            data["rating"] = last_conf["rating"]
        if "h5Index" in last_conf:
            data["h5Index"] = last_conf["h5Index"]
        if "note" in last_conf:
            data["note"] = f"From {last_conf['shortname']}: {last_conf['note']}"
        if "abstractDeadline" in last_conf:
            data["abstractDeadline"] = dateparser.parse(last_conf["abstractDeadline"]) + timedelta(
                days=365 * (next_year - last_start.year)
            )
        if data["id"] not in conferences:
            future_conferences[data["id"]] = data
            print("estimate", data["id"])
        next_year += yearly_rythm

    return future_conferences
