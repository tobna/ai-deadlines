import argparse
import datetime
import os
import sys

import dateparser
import yaml

this_folder = os.path.dirname(__file__)
sys.path.append(this_folder)
sys.path.append(os.path.join(this_folder, "parser"))

from ccf_deadlines import get_ccf_list
from common_website import PARSER
from hf_list import get_hf_list
from ninoduarte_list import get_nino_list
from see_future import estimate_future_conferences
from wacv import parse_wacv

from ranking import make_conf_rank_function, make_core_rank_function
from utils import join_conferences, parse_all_times, unite_tags, _parse_timestr

conference_folder = os.path.join(this_folder, os.pardir, "conferences")
_SOURCES = ["estimate", "ccf-deadlines", "ninoduarte-git", "hf-repo", "off-website", "manual"]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--historic", default=False, action=argparse.BooleanOptionalAction, help="Pull historic data aswell."
)
parser.add_argument(
    "--online", default=False, action=argparse.BooleanOptionalAction, help="Download data from the internet"
)
parser.add_argument("--write", default=True, action=argparse.BooleanOptionalAction, help="Write out results")
parser.add_argument(
    "--reestimate", default=False, action=argparse.BooleanOptionalAction, help="Force reestimate all conferences"
)
args = parser.parse_args()


conferences = {}
for conf_file in os.listdir(conference_folder):
    with open(os.path.join(conference_folder, conf_file), "r") as f:
        file_confs = yaml.safe_load(f)
    file_confs = {key: parse_all_times(conf) for key, conf in file_confs.items()}
    # file_confs = {key: _update_to_multiple_deadlines(conf) for key, conf in file_confs.items()}
    conferences = {**file_confs, **conferences}

# join wacvR1 and wacvR2:
# r1s = [k for k in conferences.keys() if k.startswith("wacvR1")]
# r2s = [k for k in conferences.keys() if k.startswith("wacvR2")]
# for k1 in r1s:
#     conferences[k1.replace("R1", "")] = conferences.pop(k1)
# for k2 in r2s:
#     conferences[k2.replace("R2", "")]["timeline"].append(conferences.pop(k2)["timeline"][0])
#     print(conferences[k2.replace("R2", "")])

reestimate_future_for_groups = []
if args.online:
    all_parsers = PARSER + [parse_wacv]
    for conf_parser in all_parsers:
        current_year = datetime.datetime.now().year
        year = current_year + 2
        no_data_years = 0
        while no_data_years < 5 and (year >= current_year - 1 or args.historic):
            print(f"{conf_parser} {year}", end="\t")
            try:
                yearly_data = conf_parser(year)
            except Exception as e:
                print(f"ERROR while parsing conference: {e}")
                continue
            print("no data" if len(yearly_data) == 0 else "loaded data", flush=True)
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
                    reestimate_future_for_groups.append(id[:-4])
                elif _SOURCES.index(conferences[id]["dataSrc"]) <= _SOURCES.index("off-website"):
                    if conferences[id]["dataSrc"] == "estimate":
                        print(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
                        reestimate_future_for_groups.append(id[:-4])
                    conferences[id] = join_conferences(slave=conferences[id], master=yearly_data)
                    conferences[id]["dataSrc"] = "off-website"
                else:
                    conferences[id] = join_conferences(slave=yearly_data, master=conferences[id])
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
        if id.startswith("wacv") and len(hf_data["timeline"]) == 1:  # hf data only hase one deadline for WACV
            deadline = dateparser.parse(hf_data["timeline"][0]["deadline"])
            round = 1 if deadline.month <= 8 else 2
            hf_data["timeline"][0]["note"] = f"Round {round}"
        if id not in conferences:
            conferences[id] = hf_data
            conferences[id]["dataSrc"] = "hf-repo"
            print(f"NEW CONFERENCE: {conferences[id]}")
            reestimate_future_for_groups.append(id[:-4])
        elif _SOURCES.index(conferences[id]["dataSrc"]) <= _SOURCES.index("hf-repo"):
            if conferences[id]["dataSrc"] == "estimate":
                print(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
                reestimate_future_for_groups.append(id[:-4])
            conferences[id] = join_conferences(slave=conferences[id], master=hf_data)
            conferences[id]["dataSrc"] = "hf-repo"
        else:
            conferences[id] = join_conferences(slave=hf_data, master=conferences[id])

    print("load nino duarte data", flush=True)
    try:
        nino_confs = get_nino_list()
    except Exception as e:
        print(f"ERROR while parsing ninoduarte-git: {e}")
        nino_confs = []
    for nino_conf in nino_confs:
        nino_conf = parse_all_times(nino_conf)
        id = nino_conf["id"].replace("nips", "neurips")
        if id.startswith("wacv") and len(nino_conf["timeline"]) == 1:  # nino data only hase one deadline for WACV
            deadline = dateparser.parse(nino_conf["timeline"][0]["deadline"])
            round = 1 if deadline.month <= 8 else 2
            nino_conf["timeline"][0]["note"] = f"Round {round}"
        if id not in conferences:
            conferences[id] = nino_conf
            conferences[id]["dataSrc"] = "ninoduarte-git"
            print(f"NEW CONFERENCE: {conferences[id]}")
            reestimate_future_for_groups.append(id[:-4])
        elif _SOURCES.index(conferences[id]["dataSrc"]) < _SOURCES.index("ninoduarte-git"):
            if conferences[id]["dataSrc"] == "estimate":
                print(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
                reestimate_future_for_groups.append(id[:-4])
            conferences[id] = join_conferences(slave=conferences[id], master=nino_conf)
            conferences[id]["dataSrc"] = "ninoduarte-git"
        else:
            conferences[id] = join_conferences(slave=nino_conf, master=conferences[id])

    print(f"load ccf-deadlines")
    try:
        ccf_conferences = get_ccf_list()
        print(f"got {len(ccf_conferences)} ccf conferences")
    except Exception as e:
        print(f"ERROR while parsing ccf-deadlines: {e}")
        ccf_conferences = []
    for ccf_data in ccf_conferences:
        ccf_data = parse_all_times(ccf_data)
        id = ccf_data["id"]
        if id.startswith("wacv") and len(ccf_data["timeline"]) == 1:  # hf data only hase one deadline for WACV
            deadline = dateparser.parse(ccf_data["timeline"][0]["deadline"])
            round = 1 if deadline.month <= 8 else 2
            ccf_data["timeline"][0]["note"] = f"Round {round}"
        if id not in conferences:
            conferences[id] = ccf_data
            conferences[id]["dataSrc"] = "ccf-deadlines"
            print(f"NEW CONFERENCE: {conferences[id]}")
            reestimate_future_for_groups.append(id[:-4])
        elif _SOURCES.index(conferences[id]["dataSrc"]) <= _SOURCES.index("ccf-deadlines"):
            if conferences[id]["dataSrc"] == "estimate":
                print(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
                reestimate_future_for_groups.append(id[:-4])
            conferences[id] = join_conferences(slave=conferences[id], master=ccf_data)
            conferences[id]["dataSrc"] = "ccf-deadlines"
        else:
            conferences[id] = join_conferences(slave=ccf_data, master=conferences[id])


remove_ids = set()
for id, conf in conferences.items():
    none_deadlines = set()
    for i, deadline in enumerate(conf["timeline"]):
        if _parse_timestr(deadline["deadline"], with_time=True) is None:
            none_deadlines.add(i)
    if len(none_deadlines) == len(conf["timeline"]):
        remove_ids.add(id)
    else:
        for idx in sorted(list(none_deadlines), reverse=True):
            removed = conf["timeline"].pop(idx)
            print(f"WARNING: removed deadline {removed} from {conf['id']}")
for conf_id in remove_ids:
    removed = conferences.pop(conf_id)
    print(f"WARNING: removed conference {removed} due to no timeline")


reestimate_future_for_groups = set(reestimate_future_for_groups)

add_conf_rank = make_conf_rank_function(online=False)  # google doesn't allow scraping of h5 data right now

# save the data
conf_groups = {}
for key, val in conferences.items():
    group = key[:-4]
    if group not in conf_groups:
        conf_groups[group] = {}
    conf_groups[group][key] = val

add_core_rank = make_core_rank_function(conf_groups.keys(), online=args.online)


for group, conferences in conf_groups.items():
    print(f"write out group {group}", flush=True)
    if group in reestimate_future_for_groups or args.reestimate:
        conferences = {key: conf for key, conf in conferences.items() if not conf["isApproximateDeadline"]}
    try:
        future_conferences = estimate_future_conferences(conferences)
        future_conferences = {key: parse_all_times(conf) for key, conf in future_conferences.items()}
    except Exception as e:
        print(f"ERROR estimating future conferences of group {group}: {e}")
        if args.reestimate:
            raise e
        future_conferences = {}

    conferences = {**future_conferences, **conferences}
    conferences = {key: add_conf_rank(conf) for key, conf in conferences.items()}
    conferences = {key: add_core_rank(conf) for key, conf in conferences.items()}
    conferences = unite_tags(conferences)
    if args.write:
        with open(os.path.join(conference_folder, f"{group}.yaml"), "w") as f:
            yaml.safe_dump(conferences, f)

    else:
        print(conferences)
