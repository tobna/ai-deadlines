import re

from ..log_config import logger
from .http import fetch_json, fetch_yaml

_tag_dict = {
    "machine-learning": "ML",
    "computer-vision": "CV",
    "natural-language-processing": "NLP",
    "human-computer-interaction": "HCI",
    "robotics": "RO",
    "data-mining": "DM",
    "signal-processing": "SP",
}

no_dig_re = re.compile(r"[a-zA-Z]*$")
hf_date_re = re.compile(r"([A-Z][a-z]+)[ ,]*(\d+) *[-|–] *([A-Z,a-z]*) *(\d+), *(\d+)$")

_HF_TREE = "https://api.github.com/repos/huggingface/ai-deadlines/git/trees/main?recursive=1"
_HF_RAW = "https://raw.githubusercontent.com/huggingface/ai-deadlines/refs/heads/main/"


def _build_timeline(conference):
    """Assemble our timeline (paper/abstract deadlines) from an HF conference entry."""
    timeline = []
    if conference.get("deadline") is not None:
        timeline = [{"deadline": conference["deadline"]}]
    if "deadlines" in conference:
        tl_obj = {}
        has_paper_type = any(dl["type"] == "paper" for dl in conference["deadlines"])
        for dl in conference["deadlines"]:
            if dl["date"] is None:
                continue
            if (
                not has_paper_type
                and dl["type"] == "submission"
                and ("label" not in dl or "paper" in dl["label"].lower())
            ):
                dl["type"] = "paper"
            if dl["type"] == "paper":
                if "deadline" in tl_obj:
                    timeline.append(tl_obj)
                    tl_obj = {}
                tl_obj["deadline"] = dl["date"]
                if "timezone" in dl:
                    tl_obj["deadline"] += f" {dl['timezone']}"
                if "label" in dl:
                    tl_obj["note"] = dl["label"]
            elif dl["type"] == "abstract" or dl["type"] == "registration":
                if "deadline" in tl_obj and "abstractDeadline" in tl_obj:
                    timeline.append(tl_obj)
                    tl_obj = {}
                tl_obj["abstractDeadline"] = dl["date"]
                if "timezone" in dl:
                    tl_obj["abstractDeadline"] += f" {dl['timezone']}"
        if "deadline" in tl_obj:
            timeline.append(tl_obj)
    return timeline


def conference_from_hf(conference):
    """Convert one HF conference entry to our schema, or None to skip it."""
    shortname = re.sub(r"[^a-zA-Z]", "", conference["title"])
    if no_dig_re.match(shortname):
        conf_id = shortname.lower() + str(conference["year"])
        shortname = shortname + " " + str(conference["year"])
    else:
        conf_id = shortname.lower()
    out_conf = {
        "id": conf_id,
        "title": conference["full_name"],
        "shortname": shortname,
        "isApproximateDeadline": False,
    }

    timeline = _build_timeline(conference)
    if len(timeline) == 0:
        logger.warning(f"no timeline for hf-conf: {out_conf}")
        return None
    out_conf["timeline"] = timeline

    if "venue" in conference:
        out_conf["location"] = conference["venue"]
    elif "country" in conference or "city" in conference:
        loc_str = []
        if "city" in conference:
            loc_str.append(conference["city"])
        if "country" in conference:
            loc_str.append(conference["country"])
        out_conf["location"] = ", ".join(loc_str)

    if "timezone" in conference:
        out_conf["timezone"] = conference["timezone"]
    if "link" in conference:
        out_conf["website"] = conference["link"]

    if conference.get("start") is not None:
        out_conf["conferenceStartDate"] = conference["start"]
        out_conf["conferenceEndDate"] = conference.get("end")
    else:
        date_str = (conference.get("date") or "").strip()
        match = hf_date_re.match(date_str)
        if not match:
            logger.info(f"INFO skipping hf entry {conf_id} with date '{date_str}'")
            return None
        month1, day1, month2, day2, year = match.groups()
        if month2 is None or len(month2) == 0:
            month2 = month1
        out_conf["conferenceStartDate"] = f"{month1} {day1}, {year}"
        out_conf["conferenceEndDate"] = f"{month2} {day2}, {year}"

    if conference.get("abstract_deadline") is not None:
        out_conf["timeline"][0]["abstractDeadline"] = conference["abstract_deadline"]

    out_conf["tags"] = [_tag_dict[tag] for tag in conference.get("tags", []) if tag in _tag_dict]
    return out_conf


def get_hf_list():
    tree = fetch_json(_HF_TREE)
    if tree is None or "tree" not in tree:
        logger.error("could not fetch hf ai-deadlines file tree")
        return []
    hf_paths = [
        f["path"]
        for f in tree["tree"]
        if f["path"].startswith("src/data/conferences/") and f["path"].endswith(".yml")
    ]

    out_data = []
    for hf_path in hf_paths:
        conferences = fetch_yaml(_HF_RAW + hf_path)
        if not conferences:
            continue
        for conference in conferences:
            try:
                out_conf = conference_from_hf(conference)
            except (KeyError, TypeError) as e:
                logger.warning(f"skipping hf conf in {hf_path}: {e}")
                continue
            if out_conf is not None:
                out_data.append(out_conf)
    return out_data


if __name__ == "__main__":
    data = get_hf_list()
    for conf in data:
        print(f"{conf['shortname']}: {conf}")
        for dl in conf["timeline"]:
            assert dl["deadline"] is not None
            if "abstractDeadline" in dl:
                assert dl["abstractDeadline"]
