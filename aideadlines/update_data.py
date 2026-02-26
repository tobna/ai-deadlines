import argparse
import datetime
import os
import sys
import traceback
from .log_config import logger
import dateparser
import yaml

this_folder = os.path.dirname(__file__)

sys.path.append(os.path.join(this_folder, "parser"))

from .parser.ccf_deadlines import get_ccf_list
from .parser.common_website import PARSER
from .parser.hf_list import get_hf_list
from .parser.ninoduarte_list import get_nino_list
from .parser.see_future import estimate_future_conferences
from .parser.wacv import parse_wacv

from .ranking import make_conf_rank_function, make_core_rank_function
from .utils import (
    _parse_timestr,
    join_conferences,
    parse_all_times,
    parse_stuff,
    unite_tags,
)

conference_folder = os.path.join(this_folder, os.pardir, "conferences")
_SOURCES = ["estimate", "ninoduarte-git", "ccf-deadlines", "hf-repo", "off-website", "manual"]


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
#     logger.info(conferences[k2.replace("R2", "")])

reestimate_future_for_groups = []
if args.online:
    all_parsers = PARSER + [parse_wacv]
    for conf_parser in all_parsers:
        current_year = datetime.datetime.now().year
        year = current_year + 2
        no_data_years = 0
        while no_data_years < 5 and (year >= current_year - 1 or args.historic):
            logger.info(f"{conf_parser} {year}", end="\t")
            try:
                yearly_data = conf_parser(year)
            except Exception as e:
                logger.warning(f"Error while parsing conference: {e}")
                year -= 1
                continue
            logger.info("no data" if len(yearly_data) == 0 else "loaded data", flush=True)
            try:
                yearly_data = parse_all_times(yearly_data)
            except Exception as e:
                logger.warning(
                    f"Error while parsing dates for conference {conf_parser} {year} (data={yearly_data}): {e}"
                )
                year -= 1
                continue
            if len(yearly_data) == 0:
                no_data_years += 1
            else:
                no_data_years = 0
                id = yearly_data["id"]
                if id not in conferences:
                    conferences[id] = yearly_data
                    conferences[id]["dataSrc"] = "off-website"
                    logger.success(f"NEW CONFERENCE: {conferences[id]}")
                    reestimate_future_for_groups.append(id[:-4])
                elif _SOURCES.index(conferences[id]["dataSrc"]) <= _SOURCES.index("off-website"):
                    if conferences[id]["dataSrc"] == "estimate":
                        logger.success(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
                        reestimate_future_for_groups.append(id[:-4])
                        conferences[id] = yearly_data
                    else:
                        conferences[id] = join_conferences(slave=conferences[id], master=yearly_data)
                    conferences[id]["dataSrc"] = "off-website"
                else:
                    conferences[id] = join_conferences(slave=yearly_data, master=conferences[id])
            year -= 1

    logger.info("load hf data", flush=True)
    try:
        hf_conferences = get_hf_list()
    except Exception as e:
        trace = traceback.format_exc()
        logger.error(f"while parsing hf list: {e}\n{trace}")
        # write_error(f"Failed parsing hf conferences: {e}\n{trace}")
        hf_conferences = []
    if len(hf_conferences) == 0:
        logger.error("no hf conferences found")
        # write_error("No hf conferences found")
    for hf_data in hf_conferences:
        hf_data = parse_all_times(hf_data)
        id = hf_data["id"]
        if id.startswith("wacv") and len(hf_data["timeline"]) == 1:  # hf data only hase one deadline for WACV
            deadline = dateparser.parse(hf_data["timeline"][0]["deadline"])
            if deadline is None:
                logger.warning("Failed to parse deadline for HF conference {}".format(id))
                round = 2
            else:
                round = 1 if deadline.month <= 8 else 2
            hf_data["timeline"][0]["note"] = f"Round {round}"
        if id not in conferences:
            conferences[id] = hf_data
            conferences[id]["dataSrc"] = "hf-repo"
            logger.success(f"NEW CONFERENCE: {conferences[id]}")
            reestimate_future_for_groups.append(id[:-4])
        elif _SOURCES.index(conferences[id]["dataSrc"]) <= _SOURCES.index("hf-repo"):
            if conferences[id]["dataSrc"] == "estimate":
                logger.success(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
                reestimate_future_for_groups.append(id[:-4])
                conferences[id] = hf_data
            else:
                conferences[id] = join_conferences(slave=conferences[id], master=hf_data)
            conferences[id]["dataSrc"] = "hf-repo"
        else:
            conferences[id] = join_conferences(slave=hf_data, master=conferences[id])

    logger.info("load nino duarte data", flush=True)
    try:
        nino_confs = get_nino_list()
    except Exception as e:
        logger.error(f"ERROR while parsing ninoduarte-git: {e}")
        # write_error(f"Failed parsing ninoduarte-git: {e}")
        nino_confs = []
    if len(nino_confs) == 0:
        logger.error("ERROR no ninoduarte-git conferences found")
        # write_error("No ninoduarte-git conferences found")
    for nino_conf in nino_confs:
        nino_conf = parse_all_times(nino_conf)
        id = nino_conf["id"].replace("nips", "neurips")
        if id.startswith("wacv") and len(nino_conf["timeline"]) == 1:  # nino data only hase one deadline for WACV
            deadline = dateparser.parse(nino_conf["timeline"][0]["deadline"])
            if deadline is None:
                logger.warning("Failed to parse deadline for NINO conference {}".format(id))
                round = 2
            else:
                round = 1 if deadline.month <= 8 else 2
            nino_conf["timeline"][0]["note"] = f"Round {round}"
        if id not in conferences:
            conferences[id] = nino_conf
            conferences[id]["dataSrc"] = "ninoduarte-git"
            logger.success(f"NEW CONFERENCE: {conferences[id]}")
            reestimate_future_for_groups.append(id[:-4])
        elif _SOURCES.index(conferences[id]["dataSrc"]) < _SOURCES.index("ninoduarte-git"):
            if conferences[id]["dataSrc"] == "estimate":
                logger.success(f"FIRST DATA FOR CONFERENCE: {conferences[id]}")
                reestimate_future_for_groups.append(id[:-4])
                conferences[id] = nino_conf
            else:
                conferences[id] = join_conferences(slave=conferences[id], master=nino_conf)
            conferences[id]["dataSrc"] = "ninoduarte-git"
        else:
            conferences[id] = join_conferences(slave=nino_conf, master=conferences[id])

    logger.info("load ccf-deadlines")
    try:
        ccf_conferences = get_ccf_list()
        logger.info(f"got {len(ccf_conferences)} ccf conferences")
    except Exception as e:
        logger.error(f"ERROR while parsing ccf-deadlines: {e}")
        # write_error(f"Failed loading ccf-deadlines conferences: {e}")
        ccf_conferences = []
    if len(ccf_conferences) == 0:
        logger.error("ERROR no ccf-conferences gotten")
        # write_error("No ccf-conferences found")
    for ccf_data in ccf_conferences:
        ccf_data = parse_all_times(ccf_data)
        id = ccf_data["id"]
        if id.startswith("wacv") and len(ccf_data["timeline"]) == 1:  # hf data only hase one deadline for WACV
            deadline = dateparser.parse(ccf_data["timeline"][0]["deadline"])
            if deadline is None:
                logger.warning(f"Failed to parse deadline for CCF conference {id}")
                round = 2
            else:
                round = 1 if deadline.month <= 8 else 2
            ccf_data["timeline"][0]["note"] = f"Round {round}"
        if id not in conferences:
            conferences[id] = ccf_data
            conferences[id]["dataSrc"] = "ccf-deadlines"
            logger.success(f"NEW CONFERENCE: {conferences[id]}")
            reestimate_future_for_groups.append(id[:-4])
        elif _SOURCES.index(conferences[id]["dataSrc"]) <= _SOURCES.index("ccf-deadlines"):
            if conferences[id]["dataSrc"] == "estimate":
                logger.success(f"FIRST DATA FOR CONFERENCE: {conferences[id]} => {ccf_data}")
                reestimate_future_for_groups.append(id[:-4])
                conferences[id] = ccf_data
            else:
                conferences[id] = join_conferences(slave=conferences[id], master=ccf_data)
            conferences[id]["dataSrc"] = "ccf-deadlines"
        else:
            conferences[id] = join_conferences(slave=ccf_data, master=conferences[id])


# nips => neurips
nips_confs = {key: conf for key, conf in conferences.items() if "nips" in key or "nips" in conf["id"]}
for key, conf in nips_confs.items():
    old_key = key
    key = key.replace("nips", "neurips")
    if old_key != key:
        conferences.pop(old_key)
    conf["id"] = conf["id"].replace("nips", "neurips")
    conf["shortname"] = conf["shortname"].replace("NIPS", "NeurIPS")
    if key in conferences:
        conferences[key] = join_conferences(slave=conf, master=conferences[key])
    else:
        conferences[key] = conf
    logger.info(f"nips => neurips for {key}: {conf}")

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
            logger.warning(f"WARNING: removed deadline {removed} from {conf['id']}")
for conf_id in remove_ids:
    removed = conferences.pop(conf_id)
    logger.warning(f"WARNING: removed conference {removed} due to no timeline")


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


if not args.reestimate:
    logger.info(f"Will reestimate futures for: {reestimate_future_for_groups}")
for group, conferences in conf_groups.items():
    logger.info(f"write out group {group}: {list(conferences.keys())}", flush=True)
    if group in reestimate_future_for_groups or args.reestimate:
        conferences = {key: conf for key, conf in conferences.items() if not conf["isApproximateDeadline"]}
    try:
        future_conferences = estimate_future_conferences(conferences)
        future_conferences = {key: parse_all_times(conf) for key, conf in future_conferences.items()}
    except Exception as e:
        logger.error(f"ERROR estimating future conferences of group {group}: {e}")
        # write_error(f"Failed estimating future_conferences of group {group}: {e}")
        if args.reestimate:
            raise e
        future_conferences = {}

    conferences = {**future_conferences, **conferences}
    conferences = {key: add_conf_rank(conf) for key, conf in conferences.items()}
    conferences = {key: add_core_rank(conf) for key, conf in conferences.items()}
    conferences = unite_tags(conferences)
    conferences = parse_stuff(conferences)
    if args.write:
        with open(os.path.join(conference_folder, f"{group}.yaml"), "w") as f:
            yaml.safe_dump(conferences, f)

    else:
        logger.info(conferences)
