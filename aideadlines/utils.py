import dateparser
from .log_config import logger
from copy import deepcopy
import pytz
import re
import datetime

TZ_REPLACE = {
    # US timezone abbreviations
    "Pacific Time": "PST",
    "PT": "PST",
    "Eastern Time": "EST",
    "ET": "EST",
    "Central Time": "UTC-6",  # not "CST", which is China below
    "CT": "UTC-6",
    "Mountain Time": "MST",
    # Named timezone regions
    "Russia/Moscow": "GMT+3",
    "Europe/London": "GMT+0",
    "Europe/Paris": "GMT+1",
    "Europe/Berlin": "GMT+1",
    "Europe/Rome": "GMT+1",
    "Europe/Madrid": "GMT+1",
    "Europe/Amsterdam": "GMT+1",
    "Europe/Zurich": "GMT+1",
    "Europe/Vienna": "GMT+1",
    "Asia/Tokyo": "GMT+9",
    "Asia/Shanghai": "GMT+8",
    "Asia/Singapore": "GMT+8",
    "Asia/Seoul": "GMT+9",
    "Asia/Hong_Kong": "GMT+8",
    "Asia/Kolkata": "GMT+5:30",
    "Australia/Sydney": "GMT+11",
    "Australia/Melbourne": "GMT+11",
    "Pacific/Honolulu": "UTC-10",
    # European timezone abbreviations
    "CET": "GMT+1",
    "CEST": "GMT+2",
    "EET": "GMT+2",
    "EEST": "GMT+3",
    # Asian timezone abbreviations
    "JST": "GMT+9",
    "KST": "GMT+9",
    "CST": "GMT+8",
    "China Standard Time": "GMT+8",
    "IST": "GMT+5:30",
    # Australian timezone abbreviations
    "AEST": "GMT+10",
    "AEDT": "GMT+11",
    "AWST": "GMT+8",
    # Other common formats
    "(Anywhere on Earth)": "AoE",
    "Anywhere on Earth": "AoE",
    "AoE": "UTC-12",
}
# Whole words only, so the "ET" inside "CET" stays put. Applied in order, so "AoE" -> "UTC-12" chains.
_TZ_PATTERNS = [(re.compile(rf"(?<!\w){re.escape(name)}(?!\w)"), tz) for name, tz in TZ_REPLACE.items()]


def _replace_tz_names(text):
    """Swap the zone names dateparser misreads or doesn't know for UTC offsets."""
    for pattern, tz in _TZ_PATTERNS:
        text = pattern.sub(tz, text)
    return text


def _localize(naive, conf_tz):
    """``naive`` as wall time in the conference timezone, or None if that zone is unknown."""
    try:  # IANA names ("America/Los_Angeles", "Etc/GMT-2", "CET"), with daylight saving time
        return pytz.timezone(conf_tz).localize(naive)
    except pytz.UnknownTimeZoneError:  # "AoE", "UTC-12", "PST": dateparser reads the offset
        aware = dateparser.parse(f"{naive.isoformat()} {_replace_tz_names(conf_tz)}")
    if aware is None or aware.tzinfo is None:
        logger.error(f"ERROR unknown conference timezone '{conf_tz}'")
        return None
    return aware


def _parse_timestr(timestr, with_time, conf_tz=None):
    if conf_tz is None:
        conf_tz = "AoE"
    if isinstance(timestr, str):
        has_explicit_time = bool(re.search(r"\d+:\d+", timestr))
        timestr = _replace_tz_names(timestr)
        logger.debug(f"replaced to {timestr}")
        parsed_time = dateparser.parse(timestr)
        if parsed_time is None:
            logger.error(f"NONE: '{timestr}'")
            return None
    else:
        assert isinstance(timestr, datetime.datetime), f"timestr has to be str or datetime, but got {type(timestr)}"
        parsed_time = timestr
        has_explicit_time = True
    if not with_time:
        return parsed_time.strftime("%Y-%m-%d")
    if not has_explicit_time:
        parsed_time = parsed_time.replace(hour=23, minute=59, second=59)
    if parsed_time.tzinfo is None:  # no zone in the string: it is the conference's
        parsed_time = _localize(parsed_time, conf_tz)
        if parsed_time is None:
            return None
    return parsed_time.astimezone(pytz.UTC).isoformat().replace("+00:00", "Z")


month_day_re = re.compile(r"^[A-Z,a-z, ]*\d?\d[a-z]*$")
month_day_time_re = re.compile(r"^([A-Z,a-z, ,\,]*\d?\d[a-z]*)(,? *\d\d:\d\d[A-Z,a-z, ]*)$")
month_strs = [datetime.datetime.strptime(f"2024-{mnth:02d}-10", "%Y-%m-%d").strftime("%b") for mnth in range(1, 13)]


def parse_all_times(conference):
    if "id" not in conference:
        assert len(conference) == 0, f"Strange conference: {conference}"
    try:
        year = int(conference["id"][-4:])
    except ValueError as e:
        logger.info(conference)
        raise e
    conf_tz = conference.get("timezone", "AoE")
    for timekey in ["conferenceStartDate", "conferenceEndDate"]:
        if timekey in conference:
            timestr = str(conference[timekey])
            if month_day_re.match(timestr.strip()):
                timestr += f", {year}"
            if " the " in timestr and not any(mnth in timestr for mnth in month_strs):
                old_time_str = timestr
                if "End" in timekey:
                    timestr = timestr.replace(
                        " the ", " " + month_strs[int(conference["conferenceStartDate"].split("-")[1]) - 1] + " "
                    )
                logger.info(f"WATCH OUT: {old_time_str} -> {timestr}")

            timestr = _parse_timestr(timestr, with_time=False, conf_tz=conf_tz)
            if timestr:
                conference[timekey] = timestr
    for dates in conference["timeline"]:
        for key in dates.keys():
            if "deadline" in key.lower():
                timestr = dates[key]
                if isinstance(timestr, str) and month_day_time_re.match(timestr):
                    old_time_str = timestr
                    start, end = month_day_time_re.match(timestr).groups()
                    timestr = f"{start} {year}{end}"
                    logger.info(f"adding year to '{old_time_str}' -> '{timestr}'")
                timestr = _parse_timestr(timestr, with_time=True, conf_tz=conf_tz)
                if timestr:
                    dates[key] = timestr

    return conference


def join_conferences(master, slave):
    out = deepcopy(slave)
    for key, val in master.items():
        if key == "tags":
            all_tags = set(master[key]).union(set(slave[key]))
            val = sorted(list(all_tags))
        if key == "timeline":
            if (len(val) == 0 or val[0]["deadline"].lower() == "tbd") and len(out[key]) > 0:
                logger.info(f"taking slave timeline: {out[key]} instead of master timeline {val}")
                continue
        out[key] = val
    return out


def unite_tags(conf_group):
    tags = set()
    for conf in conf_group.values():
        if "tags" in conf:
            tags = tags.union(conf["tags"])
    tags = sorted(list(tags))
    for conf in conf_group.values():
        conf["tags"] = tags
    return conf_group


def normalize_timezone_for_js(js_tz):
    """Normalize a conference timezone string to an IANA 'Etc/GMT±N' zone the frontend uses.

    Handles 'UTC±N' offsets (note the POSIX sign flip in 'Etc/GMT') plus the named cases
    AoE (UTC−12) and Russia/Moscow.
    """
    old_tz = js_tz
    if "UTC" in js_tz:
        char = "+" if "+" in js_tz else ("-" if "-" in js_tz else None)
        if char is not None:
            offset = int(js_tz.split(char)[-1])
            js_tz = f"Etc/GMT{'+' if char == '-' else '-'}{offset}"
    js_tz = js_tz.replace("AoE", "Etc/GMT+12").replace("Russia/Moscow", "Etc/GMT+3")
    if old_tz != js_tz:
        logger.debug(f"Parsing timezone for json: {old_tz} -> {js_tz}")
    return js_tz


def parse_stuff(conferences):
    # parse GMT timezone strings for use with js
    for conf in conferences.values():
        if "timezone" in conf:
            if conf["timezone"].startswith("GMT"):
                offset = int(conf["timezone"][3:])
                conf["timezone"] = f"Etc/GMT{-offset:+}"

    # join deadlines that are the exact same
    for conf in conferences.values():
        deadline_dates = {dl["deadline"] for dl in conf["timeline"]}
        timeline = [dict(deadline=dl) for dl in sorted(deadline_dates)]
        for tldl in timeline:
            for cnfdl in conf["timeline"]:
                if tldl["deadline"] == cnfdl["deadline"]:
                    for key in ["abstractDeadline", "note"]:
                        if key in cnfdl and key not in tldl:
                            tldl[key] = cnfdl[key].strip()
        conf["timeline"] = timeline

    return conferences
