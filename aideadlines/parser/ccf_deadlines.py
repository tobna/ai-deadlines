import os

from ..log_config import logger
from .http import fetch_json, fetch_yaml

load_conferences = ["AI", "CG/3dv"]

_CCF_TREE = "https://api.github.com/repos/ccfddl/ccf-deadlines/git/trees/main?recursive=1"
_CCF_RAW = "https://raw.githubusercontent.com/ccfddl/ccf-deadlines/refs/heads/main/"


def parse_ccf_date_range(date_str, fallback_year):
    """Parse a ccf-deadlines 'date' string into (start, end) 'D Mon YYYY' strings.

    Returns None for 'TBD'. Raises ValueError/AssertionError for shapes it can't handle.
    """
    if date_str == "TBD":
        return None
    parts = date_str.replace("-", " - ").replace("  ", " ").split(" ")
    if len(parts) == 3:
        month, days, year = parts
        start_month = end_month = month
        days = days.split("-")
        start_day, end_day = days if len(days) == 2 else (days[0], days[0])
    elif len(parts) == 5:
        if int(parts[-1]) >= 1900:
            month, start_day, dash, end_day, year = parts
            assert dash == "-", f"No '-', but '{dash}'"
            start_month = end_month = month
        else:
            start_month, start_day, dash, end_month, end_day = parts
            assert len(end_month) >= 3, f"Thought {end_month} was a month"
            year = str(fallback_year)
    elif len(parts) == 6:
        start_month, start_day, dash, end_month, end_day, year = parts
        assert dash == "-", f"No '-', but '{dash}'"
    else:
        raise ValueError(f"Can't parse dates str '{date_str}' yet")
    return f"{start_day} {start_month} {year}", f"{end_day} {end_month} {year}"


def conference_from_ccf(ccf_info, conf):
    """Build one conference record from a ccf-deadlines entry, or None to skip it."""
    data = {
        "shortname": ccf_info["title"] + " " + str(conf["year"]),
        "id": ccf_info["title"].lower().replace("3dv", "threedv") + str(conf["year"]),
        "isApproximateDeadline": False,
        "tags": [],
        "timeline": [],
    }
    if "link" in conf:
        data["website"] = conf["link"]
    if "description" in ccf_info:
        data["title"] = ccf_info["description"]

    if "date" in conf:
        # Historical behavior: a 'TBD' conference date drops the whole conference.
        if conf["date"] == "TBD":
            return None
        try:
            date_range = parse_ccf_date_range(conf["date"], conf["year"])
            if date_range is not None:
                data["conferenceStartDate"], data["conferenceEndDate"] = date_range
                logger.debug(f"added conf dates for {data['id']}")
        except Exception as e:
            logger.error(f"Error when trying to parse date '{conf['date']}': {e}")
    else:
        logger.warning(f"no conf dates for {data['id']}: {list(conf.keys())}")

    for dates in conf["timeline"]:
        if "deadline" not in dates or dates["deadline"] == "TBD":
            continue
        timeline = {"deadline": dates["deadline"]}
        if "comment" in dates:
            timeline["note"] = dates["comment"]
        if "abstract_deadline" in dates and dates["abstract_deadline"] != "TBD":
            timeline["abstractDeadline"] = dates["abstract_deadline"]
        data["timeline"].append(timeline)
    if len(data["timeline"]) == 0:
        return None
    return data


def _interesting_files(tree_paths, my_conferences):
    candidates = [p for p in tree_paths if p.startswith("conference") and p.endswith(".yml")]
    return [
        file
        for file in candidates
        if any(file.startswith(f"conference/{interest}") for interest in load_conferences)
        or any(file.endswith("/" + conf + ".yml") for conf in my_conferences)
    ]


def get_ccf_list():
    conf_folder = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "conferences")
    my_conferences = [path.split(".")[0] for path in os.listdir(conf_folder)]

    tree = fetch_json(_CCF_TREE)
    if tree is None or "tree" not in tree:
        logger.error("could not fetch ccf-deadlines file tree")
        return []
    ccf_files = _interesting_files([f["path"] for f in tree["tree"]], my_conferences)

    conf_list = []
    for i, file in enumerate(ccf_files):
        start_num_confs = len(conf_list)
        ccf_infos = fetch_yaml(_CCF_RAW + file)
        if ccf_infos is None:
            logger.warning(f"no answer for file {file} from ccf-deadlines")
            continue

        for ccf_info in ccf_infos:
            for conf in ccf_info["confs"]:
                try:
                    data = conference_from_ccf(ccf_info, conf)
                except Exception as e:
                    logger.warning(f"skipping ccf conf in {file}: {e}")
                    continue
                if data is not None:
                    conf_list.append(data)

        log = logger.info if len(conf_list) > start_num_confs else logger.warning
        log(f"{i}/{len(ccf_files)}\tgot {len(conf_list) - start_num_confs} conferences of {file} from ccf-deadlines")
    return conf_list


if __name__ == "__main__":
    data = get_ccf_list()
    for conf in data:
        logger.info(f"{conf['shortname']}: {conf}")
        for dl in conf["timeline"]:
            assert dl["deadline"] is not None
            if "abstractDeadline" in dl:
                assert dl["abstractDeadline"]
