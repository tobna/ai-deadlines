import argparse
import datetime
import os
import traceback

import yaml

from .log_config import logger
from .merge import merge_one, merge_source
from .parser.ccf_deadlines import get_ccf_list
from .parser.common_website import PARSER
from .parser.hf_list import get_hf_list
from .parser.ninoduarte_list import get_nino_list
from .parser.see_future import estimate_future_conferences
from .parser.wacv import parse_wacv
from .ranking import make_conf_rank_function, make_core_rank_function
from .utils import _parse_timestr, join_conferences, parse_all_times, parse_stuff, unite_tags

THIS_FOLDER = os.path.dirname(__file__)
CONFERENCE_FOLDER = os.path.join(THIS_FOLDER, os.pardir, "conferences")


def parse_args():
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
    parser.add_argument(
        "--load-nino-data", default=False, action=argparse.BooleanOptionalAction, help="Load data from ninoduartes github"
    )
    return parser.parse_args()


def load_conferences():
    """Load every conferences/*.yaml file, parsing all timestamps."""
    conferences = {}
    for conf_file in os.listdir(CONFERENCE_FOLDER):
        with open(os.path.join(CONFERENCE_FOLDER, conf_file), "r") as f:
            file_confs = yaml.safe_load(f)
        file_confs = {key: parse_all_times(conf) for key, conf in file_confs.items()}
        conferences = {**file_confs, **conferences}
    return conferences


def scrape_official_websites(conferences, args, reestimate_groups):
    """Walk each official-website parser backwards through years, merging what it finds."""
    for conf_parser in PARSER + [parse_wacv]:
        current_year = datetime.datetime.now().year
        year = current_year + 2
        no_data_years = 0
        while no_data_years < 5 and (year >= current_year - 1 or args.historic):
            logger.info(f"{conf_parser} {year}")
            try:
                yearly_data = conf_parser(year)
            except Exception as e:
                logger.warning(f"Error while parsing conference: {e}")
                year -= 1
                continue
            logger.info("no data" if len(yearly_data) == 0 else "loaded data")
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
                merge_one(conferences, yearly_data, yearly_data["id"], "off-website", reestimate_groups)
            year -= 1


def _safe_fetch(label, fetch):
    """Run a source fetcher, returning [] (and logging) on failure or empty result."""
    try:
        items = fetch()
    except Exception as e:
        logger.error(f"ERROR while parsing {label}: {e}\n{traceback.format_exc()}")
        items = []
    if len(items) == 0:
        logger.error(f"ERROR no {label} conferences found")
    return items


def scrape_online(conferences, args, reestimate_groups):
    """Fetch and merge every online source in ascending priority order."""
    scrape_official_websites(conferences, args, reestimate_groups)

    logger.info("load hf data")
    hf_conferences = _safe_fetch("hf-repo", get_hf_list)
    merge_source(conferences, [parse_all_times(c) for c in hf_conferences], "hf-repo", reestimate_groups)

    if args.load_nino_data:
        logger.info("load nino duarte data")
        nino_confs = _safe_fetch("ninoduarte-git", get_nino_list)
        merge_source(
            conferences,
            [parse_all_times(c) for c in nino_confs],
            "ninoduarte-git",
            reestimate_groups,
            overwrite_equal=False,
            id_transform=lambda i: i.replace("nips", "neurips"),
        )
    else:
        logger.info("skipping ninoduarte-git (not that reliable)")

    logger.info("load ccf-deadlines")
    ccf_conferences = _safe_fetch("ccf-deadlines", get_ccf_list)
    logger.info(f"got {len(ccf_conferences)} ccf conferences")
    merge_source(conferences, [parse_all_times(c) for c in ccf_conferences], "ccf-deadlines", reestimate_groups)


def normalize_nips(conferences):
    """Rename any lingering nips/NIPS ids and shortnames to neurips/NeurIPS, merging dupes."""
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
    return conferences


def drop_empty_timelines(conferences):
    """Drop unparseable deadlines, and any conference left with no valid deadline at all."""
    remove_ids = set()
    for id, conf in conferences.items():
        none_deadlines = {i for i, dl in enumerate(conf["timeline"]) if _parse_timestr(dl["deadline"], with_time=True) is None}
        if len(none_deadlines) == len(conf["timeline"]):
            remove_ids.add(id)
        else:
            for idx in sorted(none_deadlines, reverse=True):
                removed = conf["timeline"].pop(idx)
                logger.warning(f"WARNING: removed deadline {removed} from {conf['id']}")
    for conf_id in remove_ids:
        removed = conferences.pop(conf_id)
        logger.warning(f"WARNING: removed conference {removed} due to no timeline")
    return conferences


def write_groups(conferences, reestimate_groups, args):
    """Group by conference family, estimate future instances, attach ranks, and write YAML."""
    reestimate_groups = set(reestimate_groups)
    add_conf_rank = make_conf_rank_function(online=False)  # google doesn't allow scraping of h5 data right now

    conf_groups = {}
    for key, val in conferences.items():
        conf_groups.setdefault(key[:-4], {})[key] = val

    add_core_rank = make_core_rank_function(conf_groups.keys(), online=args.online)

    if not args.reestimate:
        logger.info(f"Will reestimate futures for: {reestimate_groups}")
    for group, group_confs in conf_groups.items():
        logger.info(f"write out group {group}: {list(group_confs.keys())}")
        if group in reestimate_groups or args.reestimate:
            group_confs = {key: conf for key, conf in group_confs.items() if not conf["isApproximateDeadline"]}
        try:
            future_conferences = estimate_future_conferences(group_confs)
            future_conferences = {key: parse_all_times(conf) for key, conf in future_conferences.items()}
        except Exception as e:
            logger.error(f"ERROR estimating future conferences of group {group}: {e}")
            if args.reestimate:
                raise e
            future_conferences = {}

        group_confs = {**future_conferences, **group_confs}
        group_confs = {key: add_conf_rank(conf) for key, conf in group_confs.items()}
        group_confs = {key: add_core_rank(conf) for key, conf in group_confs.items()}
        group_confs = unite_tags(group_confs)
        group_confs = parse_stuff(group_confs)
        if args.write:
            with open(os.path.join(CONFERENCE_FOLDER, f"{group}.yaml"), "w") as f:
                yaml.safe_dump(group_confs, f)
        else:
            logger.info(group_confs)


def main():
    args = parse_args()
    conferences = load_conferences()
    reestimate_groups = []
    if args.online:
        scrape_online(conferences, args, reestimate_groups)
    normalize_nips(conferences)
    drop_empty_timelines(conferences)
    write_groups(conferences, reestimate_groups, args)


if __name__ == "__main__":
    main()
