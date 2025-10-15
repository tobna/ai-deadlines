import json
import os
import requests
import yaml

load_conferences = ["AI", "CG/3dv"]


def get_ccf_list():
    conf_folder = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "conferences")
    my_conferences = [path.split(".")[0] for path in os.listdir(conf_folder)]
    ccf_files = requests.get("https://api.github.com/repos/ccfddl/ccf-deadlines/git/trees/main?recursive=1")

    ccf_files = json.loads(ccf_files.text)["tree"]
    ccf_files = [
        file["path"] for file in ccf_files if file["path"].startswith("conference") and file["path"].endswith(".yml")
    ]

    ccf_files = [
        file
        for file in ccf_files
        if any(file.startswith(f"conference/{intrest}") for intrest in load_conferences)
        or any(file.endswith("/" + conf + ".yml") for conf in my_conferences)
    ]

    conf_list = []
    for i, file in enumerate(ccf_files):
        print(f"{i}/{len(ccf_files)}\tget", file, "from ccf-deadlines", flush=True)
        ccf_infos = requests.get("https://raw.githubusercontent.com/ccfddl/ccf-deadlines/refs/heads/main/" + file)
        ccf_infos = yaml.safe_load(ccf_infos.text)
        if ccf_infos is None:
            print(f"WARNING: no answer for file {file} from ccf-deadlines")
            continue

        for ccf_info in ccf_infos:
            for conf in ccf_info["confs"]:
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
                    date_str = conf["date"]
                    try:
                        conf_date_data = date_str.replace("-", " - ").replace("  ", " ").split(" ")
                        if len(conf_date_data) == 3:
                            month, days, year = conf_date_data
                            start_month = end_month = month
                            start_day, end_day = days.split("-")
                        elif len(conf_date_data) == 5:
                            if int(conf_date_data[-1]) >= 1900:
                                month, start_day, dash, end_day, year = conf_date_data
                                assert dash == "-", f"No '-', but '{dash}'"
                                start_month = end_month = month
                            else:
                                start_month, start_day, dash, end_month, end_day = conf_date_data
                                assert len(end_month) >= 3, f"Thought {end_month} was a month"
                                year = str(conf["year"])

                        elif len(conf_date_data) == 6:
                            start_month, start_day, dash, end_month, end_day, year = conf_date_data
                            assert dash == "-", f"No '-', but '{dash}'"
                        else:
                            raise ValueError(f"Can't parse dates str '{date_str}' yet")
                        data["conferenceStartDate"] = f"{start_day} {start_month} {year}"
                        data["conferenceEndDate"] = f"{end_day} {end_month} {year}"
                        print(f"added conf dates for {data['id']}")
                    except Exception as e:
                        print(f"Error when trying to parse date '{date_str}': {e}")
                else:
                    print(f"no conf dates for {data['id']}: {list(conf.keys())}")

                for dates in conf["timeline"]:
                    if "deadline" not in dates:
                        continue
                    timeline = {"deadline": dates["deadline"]}
                    if "comment" in dates:
                        timeline["note"] = dates["comment"]
                    if "abstract_deadline" in dates:
                        timeline["abstractDeadline"] = dates["abstract_deadline"]
                    data["timeline"].append(timeline)
                if len(data["timeline"]) == 0:
                    continue
                conf_list.append(data)
    return conf_list


if __name__ == "__main__":
    data = get_ccf_list()
    print(data)
