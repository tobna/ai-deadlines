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
    if dateparser.parse(conf["deadline"]) > datetime.now().astimezone(pytz.UTC):
        future_conf[id] = conf
    else:
        past_conf[id] = conf

with open(os.path.join(this_folder, "data", "conferences.json"), "w") as f:
    json.dump(list(future_conf.values()), f)
with open(os.path.join(this_folder, "data", "conferences_archive.json"), "w") as f:
    json.dump(list(past_conf.values()), f)
