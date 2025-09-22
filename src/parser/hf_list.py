import json
import re

import requests
import yaml

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


def get_hf_list():
    conferences_list = "https://api.github.com/repos/huggingface/ai-deadlines/git/trees/main?recursive=1"
    data = requests.get(conferences_list).text
    hf_list = json.loads(data)["tree"]
    hf_list = [
        file["path"]
        for file in hf_list
        if file["path"].startswith("src/data/conferences/") and file["path"].endswith(".yml")
    ]

    out_data = []
    for hf_path in hf_list:
        url = "https://raw.githubusercontent.com/huggingface/ai-deadlines/refs/heads/main/" + hf_path
        data = requests.get(url).text
        try:
            conferences = yaml.safe_load(data)
        except yaml.YAMLError:
            continue

        for conference in conferences:
            shortname = conference["title"].replace(" ", "")
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

            timeline = []
            if "deadline" in conference:
                timeline = [{"deadline": conference["deadline"]}]
            if "deadlines" in conference:
                for dl in conference["deadlines"]:
                    if dl["type"] != "submission":
                        continue
                    tl_obj = {"deadline": dl["date"]}
                    if "label" in dl:
                        tl_obj["note"] = dl["label"]
                    timeline.append(tl_obj)
            if len(timeline) == 0:
                print(f"WARNING: no timeline for hf-conf: {out_conf}")
                continue
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

            if "start" in conference:
                out_conf["conferenceStartDate"] = conference["start"]
                out_conf["conferenceEndDate"] = conference["end"]
            else:  # -
                date_str = conference["date"].strip()
                match = hf_date_re.match(date_str)
                if not match:
                    print(f"INFO skipping hf entry {conf_id} with date '{date_str}'")
                    continue
                month1, day1, month2, day2, year = match.groups()
                if month2 is None or len(month2) == 0:
                    month2 = month1
                out_conf["conferenceStartDate"] = f"{month1} {day1}, {year}"
                out_conf["conferenceEndDate"] = f"{month2} {day2}, {year}"

            if "abstract_deadline" in conference:
                out_conf["timeline"][0]["abstractDeadline"] = conference["abstract_deadline"]

            out_conf["tags"] = [_tag_dict[tag] for tag in conference["tags"] if tag in _tag_dict.keys()]
            out_data.append(out_conf)
    return out_data


if __name__ == "__main__":
    data = get_hf_list()
    print(data)
