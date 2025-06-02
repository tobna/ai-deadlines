import json
import dateparser
import requests


def get_nino_list():
    nino_list = requests.get(
        "https://raw.githubusercontent.com/NunoDuarte/NunoDuarte.github.io/refs/heads/master/deadlines/static/data/conferences.json"
    )
    if nino_list.status_code == 200:
        nino_list = json.loads(nino_list.text)
    else:
        nino_list = []

    past_confs = requests.get(
        "https://github.com/NunoDuarte/NunoDuarte.github.io/raw/refs/heads/master/deadlines/static/data/past_conferences.txt"
    )
    if past_confs.status_code == 200:
        past_confs = past_confs.text.strip()  # it's missing the '[' ']' and has a trailing comma
        if past_confs.endswith(","):
            past_confs = past_confs[:-1]
        if not past_confs.startswith("["):
            past_confs = "[" + past_confs + "]"
        nino_list += json.loads(past_confs)

    out_list = []
    for conf in nino_list:
        year = dateparser.parse(conf["date_start"]).year
        data = {
            "id": conf["id"] + str(year),
            "deadline": conf["deadline"],
            "isApproximateDeadline": False,
            "location": conf["location"],
            "shortname": conf["name"],
            "tags": [conf["type"]],
            "timezone": conf["timezone"],
            "website": conf["link"],
            "conferenceStartDate": conf["date_start"],
            "conferenceEndDate": conf["date_end"],
        }
        out_list.append(data)
    return out_list


if __name__ == "__main__":
    data = get_nino_list()
    print(data)
