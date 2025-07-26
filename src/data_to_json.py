from copy import deepcopy
import json
import pytz
import dateparser
from datetime import datetime
import os
import sys

import yaml

this_folder = os.path.dirname(__file__)
sys.path.append(this_folder)

conference_folder = os.path.join(this_folder, os.pardir, "conferences")

conferences = {}
for conf_file in os.listdir(conference_folder):
    with open(os.path.join(conference_folder, conf_file), "r") as f:
        file_confs = yaml.safe_load(f)
    conferences = {**file_confs, **conferences}
print(f"managing {len(conferences)} conference instances")
print(sorted(list(conferences.keys())))

future_conf = {}
past_conf = {}

for id, conf in conferences.items():
    if "timezone" in conf:
        conf["timezone"] = (
            conf["timezone"]
            .replace("AoE", "Etc/GMT+12")
            .replace("UTC-", "Etc/GMT-")
            .replace("UTC+", "Etc/GMT+")
            .replace("Russia/Moscow", "Etc/GMT+3")
        )
    for i, dates in enumerate(conf["timeline"]):
        conf_cpy = deepcopy(conf)
        conf_cpy.pop("timeline")
        conf_cpy = {**conf_cpy, **dates}
        conf_cpy["id"] = f"{id}-{i+1}"
        try:
            if dateparser.parse(conf_cpy["deadline"]) > datetime.now().astimezone(pytz.UTC):
                future_conf[f"{id}-{i+1}"] = conf_cpy
            else:
                past_conf[f"{id}-{i+1}"] = conf_cpy
        except TypeError as e:
            print(f"Type Error for conference {conf_cpy}: {e}")

print("past:", sorted(list(past_conf.keys())))
print("future:", sorted(list(future_conf.keys())))

with open(os.path.join(this_folder, "data", "conferences.json"), "w") as f:
    json.dump(list(future_conf.values()), f)
with open(os.path.join(this_folder, "data", "conferences_archive.json"), "w") as f:
    json.dump(list(past_conf.values()), f)
