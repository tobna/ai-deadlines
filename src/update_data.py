import argparse
import datetime
import os
import re
import sys

import dateparser
import pytz
import requests
import yaml
from bs4 import BeautifulSoup

this_folder = os.path.dirname(__file__)
sys.path.append(this_folder)
sys.path.append(os.path.join(this_folder, "parser"))

from common_website import PARSER
from hf_list import get_hf_list
from ninoduarte_list import get_nino_list
from see_future import estimate_future_conferences
from wacv import parse_wacv
from ranking import make_core_rank_function, make_conf_rank_function

conference_folder = os.path.join(this_folder, os.pardir, "conferences")
_SOURCES = ["estimate", "ninoduarte-git", "hf-repo", "off-website", "manual"]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--historic", default=False, action=argparse.BooleanOptionalAction, help="Pull historic data aswell."
)
parser.add_argument(
    "--online", default=False, action=argparse.BooleanOptionalAction, help="Download data from the internet"
)
parser.add_argument("--write", default=True, action=argparse.BooleanOptionalAction, help="Write out results")
args = parser.parse_args()


def parse_all_times(conference):
    if "id" not in conference:
        assert len(conference) == 0, f"Strange conference: {conference}"
        return conference
    month_day_re = re.compile(r"[A-Z][a-z]* \d?\d$")
    year = int(conference["id"][-4:])
    conf_tz = None
    if "timezone" in conference:
        conf_tz = conference["timezone"]
        conf_tz = conf_tz.replace("Russia/Moscow", "GMT+3")
    for timekey in ["deadline", "conferenceStartDate", "conferenceEndDate", "abstractDeadline"]:
        if timekey in conference:
            timestr = str(conference[timekey])
            if month_day_re.match(timestr.strip()):
                timestr += f", {year}"

            timestr = timestr.replace("(Anywhere on Earth)", "AoE")
            timestr = timestr.replace("AoE", "UTC-12")
            parsed_time = dateparser.parse(timestr)
            if parsed_time is None:
                print("NONE:", timestr)
                continue
            if parsed_time.tzinfo is None and conf_tz is not None and timekey in ["deadline", "abstractDeadline"]:
                timestr = timestr + f" {conf_tz}"
                timestr = timestr.replace("(Anywhere on Earth)", "AoE")
                timestr = timestr.replace("AoE", "UTC-12")
                old_parsed_time = parsed_time
                parsed_time = dateparser.parse(timestr)
                if parsed_time is None:
                    parsed_time = old_parsed_time
            final_str = (
                parsed_time.astimezone(pytz.UTC).isoformat().replace("+00:00", "Z")
                if "deadline" in timekey.lower()
                else parsed_time.strftime("%Y-%m-%d")
            )
            conference[timekey] = final_str

    return conference


conferences = {}
for conf_file in os.listdir(conference_folder):
    with open(os.path.join(conference_folder, conf_file), "r") as f:
        file_confs = yaml.safe_load(f)
    file_confs = {key: parse_all_times(conf) for key, conf in file_confs.items()}
    conferences = {**file_confs, **conferences}


if args.online:
    all_parsers = PARSER + [parse_wacv]
    for conf_parser in all_parsers:
        current_year = datetime.datetime.now().year
        year = current_year + 2
        no_data_years = 0
        while no_data_years < 5 and (year >= current_year - 1 or args.historic):
            print(f"{conf_parser} {year}", end="\t")
            try:
                yearly_datas = conf_parser(year)
            except Exception as e:
                print(f"ERROR while parsing conference: {e}")
                continue
            if not isinstance(yearly_datas, list):
                yearly_datas = [yearly_datas]
            print("no data" if len(yearly_datas[0]) == 0 else "loaded data", flush=True)
            for yearly_data in yearly_datas:
                try:
                    yearly_data = parse_all_times(yearly_data)
                except Exception as e:
                    print(f"ERROR while parsing dates for conference {yearly_data['id']}: {e}")
                    continue
                if len(yearly_data) == 0:
                    no_data_years += 1
                else:
                    no_data_years = 0
                    id = yearly_data["id"]
                    if id not in conferences:
                        conferences[id] = yearly_data
                        conferences[id]["dataSrc"] = "off-website"
                        print(f"NEW CONFERENCE: {conferences[id]}")
                    elif _SOURCES.index(conferences[id]["dataSrc"]) <= _SOURCES.index("off-website"):
                        if conferences[id]["dataSrc"] == "estimate":
                            print(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
                        conferences[id] = {**conferences[id], **yearly_data}
                        conferences[id]["dataSrc"] = "off-website"
                    else:
                        conferences[id] = {**yearly_data, **conferences[id]}
            year -= 1

    print("load hf data", flush=True)
    try:
        hf_conferences = get_hf_list()
    except Exception as e:
        print(f"ERROR while parsing hf list: {e}")
        hf_conferences = []
    for hf_data in hf_conferences:
        hf_data = parse_all_times(hf_data)
        id = hf_data["id"]
        if id.startswith("wacv"):
            deadline = dateparser.parse(hf_data["deadline"])
            round = 1 if deadline.month <= 8 else 2
            id = id.replace("wacv", f"wacvR{round}")
            hf_data["id"] = id
            hf_data["note"] = f"Round {round}"
        if id not in conferences:
            conferences[id] = hf_data
            conferences[id]["dataSrc"] = "hf-repo"
            print(f"NEW CONFERENCE: {conferences[id]}")
        elif _SOURCES.index(conferences[id]["dataSrc"]) <= _SOURCES.index("hf-repo"):
            if conferences[id]["dataSrc"] == "estimate":
                print(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
            conferences[id] = {**conferences[id], **hf_data}
            conferences[id]["dataSrc"] = "hf-repo"
        else:
            conferences[id] = {**hf_data, **conferences[id]}

    print("load nino duarte data", flush=True)
    try:
        nino_confs = get_nino_list()
    except Exception as e:
        print(f"ERROR while parsing ninoduarte-git: {e}")
        nino_confs = []
    for nino_conf in nino_confs:
        nino_conf = parse_all_times(nino_conf)
        id = nino_conf["id"].replace("nips", "neurips")
        if id.startswith("wacv"):
            deadline = dateparser.parse(nino_conf["deadline"])
            round = 1 if deadline.month <= 8 else 2
            id = id.replace("wacv", f"wacvR{round}")
            nino_conf["id"] = id
            nino_conf["note"] = f"Round {round}"
        if id not in conferences:
            conferences[id] = nino_conf
            conferences[id]["dataSrc"] = "ninoduarte-git"
            print(f"NEW CONFERENCE: {conferences[id]}")
        elif _SOURCES.index(conferences[id]["dataSrc"]) < _SOURCES.index("ninoduarte-git"):
            if conferences[id]["dataSrc"] == "estimate":
                print(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
            conferences[id] = {**conferences[id], **nino_conf}
            conferences[id]["dataSrc"] = "ninoduarte-git"
        else:
            conferences[id] = {**nino_conf, **conferences[id]}


add_conf_rank = make_conf_rank_function(online=False)  # google doesn't allow scraping of h5 data right now

# save the data
conf_groups = {}
for key, val in conferences.items():
    group = key[:-4]
    if group not in conf_groups:
        conf_groups[group] = {}
    conf_groups[group][key] = val

add_core_rank = make_core_rank_function(conf_groups.keys(), online=args.online)

ends_wit_rd_re = re.compile(r".*R\d$")
print(conf_groups.keys())
for group, conferences in conf_groups.items():
    print(f"write out group {group}", flush=True)
    if group == "wacv":
        continue
    try:
        future_conferences = estimate_future_conferences(conferences)
        future_conferences = {key: parse_all_times(conf) for key, conf in future_conferences.items()}
    except Exception as e:
        print(f"ERROR estimating future conferences of group {group}: {e}")
        future_conferences = {}

    conferences = {**future_conferences, **conferences}
    conferences = {key: add_conf_rank(conf) for key, conf in conferences.items()}
    conferences = {key: add_core_rank(conf) for key, conf in conferences.items()}
    if args.write:
        with open(os.path.join(conference_folder, f"{group}.yaml"), "w") as f:
            yaml.safe_dump(conferences, f)

    else:
        print(conferences)
