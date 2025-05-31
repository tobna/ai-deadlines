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


def make_conf_rank_function(online=False):
    if not online:
        return lambda conf: conf

    short_to_scholar_name = {
        "neurips": "Neural Information Processing Systems",
        "iclr": "International Conference on Learning Representations",
        "icml": "International Conference on Machine Learning",
        "aaai": "AAAI Conference on Artificial Intelligence",
        "ijcai": "International Joint Conference on Artificial Intelligence (IJCAI)",
        "aistats": "International Conference on Artificial Intelligence and Statistics",
        "cvpr": "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
        "iccv": "IEEE/CVF International Conference on Computer Vision",
        "eccv": "European Conference on Computer Vision",
        "wacv": "IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)",
        "icip": "IEEE International Conference on Image Processing (ICIP)",
        "bmvc": "British Machine Vision Conference (BMVC)",
        "icpr": "International Conference on Pattern Recognition",
        "icdar": "International Conference on Document Analysis and Recognition",
        "acl": "Meeting of the Association for Computational Linguistics (ACL)",
        "emnlp": "Conference on Empirical Methods in Natural Language Processing (EMNLP)",
        "naacl": (
            "Conference of the North American Chapter of the Association for Computational Linguistics: Human Language"
            " Technologies (HLT-NAACL)"
        ),
        "coling": "International Conference on Computational Linguistics (COLING)",
        "conll": "Conference on Computational Natural Language Learning (CoNLL)",
    }
    scholar_name_to_short = {val: key for key, val in short_to_scholar_name.items()}

    google_scholar_keywords = [
        "eng_artificialintelligence",
        "eng_computationallinguistics",
        "eng_computervisionpatternrecognition",
    ]
    google_scholar_base_url = "https://scholar.google.com/citations?view_op=top_venues&hl=en&vq="
    _short_to_h5 = {}

    for kw in google_scholar_keywords:
        rank_list = requests.get(google_scholar_base_url + kw)
        rank_list = BeautifulSoup(rank_list.text, "html.parser")

        for row in rank_list.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) != 4:
                continue

            if tds[1].get_text().strip() in scholar_name_to_short:
                short = scholar_name_to_short[tds[1].get_text().strip()]
                h5idx = int(tds[2].get_text().strip())
                _short_to_h5[short] = h5idx

    print(f"got {len(_short_to_h5)} conference h5 values", flush=True)

    def add_h5(conf):
        short = conf["id"][:-4]
        if short in _short_to_h5:
            conf["h5Index"] = _short_to_h5[short]
        return conf

    return add_h5


def get_core_rank(shortname):
    shortname = shortname.lower()
    core_url = f"https://portal.core.edu.au/conf-ranks/?search={shortname}&by=all"
    core_res = requests.get(core_url)
    core_res = BeautifulSoup(core_res.text, "html.parser")

    for row in core_res.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 4:
            continue
        if tds[1].get_text().strip().lower() == shortname:
            return tds[3].get_text().strip()

    return None


conferences = {}
for conf_file in os.listdir(conference_folder):
    with open(os.path.join(conference_folder, conf_file), "r") as f:
        file_confs = yaml.safe_load(f)
    # print(conf_file)
    file_confs = {key: parse_all_times(conf) for key, conf in file_confs.items()}
    conferences = {**file_confs, **conferences}


if args.online:
    all_parsers = PARSER + [parse_wacv]
    for conf_parser in PARSER:
        current_year = datetime.datetime.now().year
        year = current_year + 2
        no_data_years = 0
        while no_data_years < 5 and (year >= current_year - 1 or args.historic):
            print(f"{conf_parser} {year}", end="\t")
            yearly_datas = conf_parser(year)
            if not isinstance(yearly_datas, list):
                yearly_datas = [yearly_datas]
            print("no data" if len(yearly_datas[0]) == 0 else "loaded data", flush=True)
            for yearly_data in yearly_datas:
                yearly_data = parse_all_times(yearly_data)
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
    hf_conferences = get_hf_list()
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
    nino_confs = get_nino_list()
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


print(conferences.keys())

add_conf_rank = make_conf_rank_function(True)

# save the data
conf_groups = {}
for key, val in conferences.items():
    group = key[:-4]
    if group not in conf_groups:
        conf_groups[group] = {}
    conf_groups[group][key] = val

ends_wit_rd_re = re.compile(r".*R\d$")
print(conf_groups.keys())
for group, conferences in conf_groups.items():
    print(f"write out group {group}", flush=True)
    if group == "wacv":
        continue
    future_conferences = estimate_future_conferences(conferences)
    future_conferences = {key: parse_all_times(conf) for key, conf in future_conferences.items()}

    group_name = group[:-2] if ends_wit_rd_re.match(group) else group.replace("threedv", "3DV")
    group_rank = get_core_rank(group) if args.online else None
    conferences = {**future_conferences, **conferences}
    conferences = {key: add_conf_rank(conf) for key, conf in conferences.items()}
    if group_rank:
        print(group, group_rank)
        for conf in conferences.values():
            conf["rating"] = group_rank
    if args.write:
        with open(os.path.join(conference_folder, f"{group}.yaml"), "w") as f:
            yaml.safe_dump(conferences, f)

    else:
        print(conferences)
