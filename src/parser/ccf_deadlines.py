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

                for dates in conf["timeline"]:
                    if not "deadline" in dates:
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
