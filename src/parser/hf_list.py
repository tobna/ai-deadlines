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


def get_hf_list():
    url = "https://raw.githubusercontent.com/huggingface/ai-deadlines/refs/heads/main/src/data/conferences.yml"
    data = requests.get(url).text
    try:
        data = yaml.safe_load(data)
    except yaml.YAMLError:
        return {}

    hf_date_re = re.compile(r"([A-Z][a-z]+)[ ,]*(\d+) *[-|–] *([A-Z,a-z]*) *(\d+), *(\d+)$")

    out_data = []
    for conference in data:
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
            "timeline": [{"deadline": conference["deadline"]}],
            "isApproximateDeadline": False,
        }

        if "venue" in conference:
            out_conf["location"] = conference["venue"]

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
