import dateparser
from copy import deepcopy
import pytz
import re
import datetime


def _parse_timestr(timestr, with_time, conf_tz=None):
    if isinstance(timestr, str):
        timestr = timestr.replace("(Anywhere on Earth)", "AoE")
        timestr = timestr.replace("AoE", "UTC-12")
        timestr = timestr.replace("Pacific Time", "PT")
        parsed_time = dateparser.parse(timestr)
        if parsed_time is None:
            print("NONE:", timestr)
            return None
    else:
        assert isinstance(timestr, datetime.datetime), f"timestr has to be str or datetime, but got {type(timestr)}"
        parsed_time = timestr
        timestr = timestr.isoformat()
    if not with_time:
        return parsed_time.strftime("%Y-%m-%d")
    if parsed_time.tzinfo is None and conf_tz is not None:
        timestr = timestr + f" {conf_tz}"
        timestr = timestr.replace("(Anywhere on Earth)", "AoE")
        timestr = timestr.replace("AoE", "UTC-12")
        old_parsed_time = parsed_time
        parsed_time = dateparser.parse(timestr)
        if parsed_time is None:
            parsed_time = old_parsed_time
    return parsed_time.astimezone(pytz.UTC).isoformat().replace("+00:00", "Z")


# month_day_re = re.compile(r"[A-Z][a-z]* \d?\d$")
month_day_re = re.compile(r"^[A-Z,a-z, ]*\d?\d[a-z]*$")
month_day_time_re = re.compile(r"^([A-Z,a-z, ,\,]*\d?\d[a-z]*)(,? *\d\d:\d\d[A-Z,a-z, ]*)$")
month_strs = [datetime.datetime.strptime(f"2024-{mnth:02d}-10", "%Y-%m-%d").strftime("%b") for mnth in range(1, 13)]


def parse_all_times(conference):
    if "id" not in conference:
        assert len(conference) == 0, f"Strange conference: {conference}"
        return conference
    year = int(conference["id"][-4:])
    conf_tz = None
    if "timezone" in conference:
        conf_tz = conference["timezone"]
        conf_tz = conf_tz.replace("Russia/Moscow", "GMT+3")
    for timekey in ["conferenceStartDate", "conferenceEndDate"]:
        if timekey in conference:
            timestr = str(conference[timekey])
            if month_day_re.match(timestr.strip()):
                timestr += f", {year}"
            if " the " in timestr and not any(mnth in timestr for mnth in month_strs):
                print(f"WATCH OUT: {timestr} ->", end="\t")
                if "End" in timekey:
                    timestr = timestr.replace(
                        " the ", " " + month_strs[int(conference["conferenceStartDate"].split("-")[1]) - 1] + " "
                    )
                print(timestr)

            timestr = _parse_timestr(timestr, with_time=False, conf_tz=conf_tz)
            if timestr:
                conference[timekey] = timestr
    for dates in conference["timeline"]:
        for key in dates.keys():
            if "deadline" in key.lower():
                timestr = dates[key]
                if month_day_time_re.match(timestr):
                    print(f"adding year to '{timestr}' -> ", end="\t")
                    start, end = month_day_time_re.match(timestr).groups()
                    timestr = f"{start} {year}{end}"
                    print(timestr)
                timestr = _parse_timestr(timestr, with_time=True, conf_tz=conf_tz)
                if timestr:
                    dates[key] = timestr

    return conference


def _update_to_multiple_deadlines(conf):
    timeline = [{"deadline": conf.pop("deadline")}]
    if "abstractDeadline" in conf:
        timeline[0]["abstractDeadline"] = conf.pop("abstractDeadline")
    if "note" in conf:
        timeline[0]["note"] = conf.pop("note")
    conf["timeline"] = timeline
    return conf


def join_conferences(master, slave):
    out = deepcopy(slave)
    for key, val in master.items():
        if key == "tags":
            all_tags = set(master[key]).union(set(slave[key]))
            val = sorted(list(all_tags))
        out[key] = val
    return out
