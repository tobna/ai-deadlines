from datetime import datetime, timedelta
import os
import re
import dateparser
import yaml
import requests
from bs4 import BeautifulSoup

this_folder = os.path.dirname(__file__)


def make_conf_rank_function(online=False):
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
    h5_file = os.path.join(this_folder, os.pardir, "rank", "h5index.yaml")
    with open(h5_file, "r") as f:
        _short_to_h5 = yaml.safe_load(f)

    updated_h5s = False
    if online:
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
                    updated_h5s = True
                    print(f"INFO: updated h5 data for {short} -> {h5idx}")

    if updated_h5s:
        with open(h5_file, "w") as f:
            yaml.safe_dump(_short_to_h5)
    print(f"got {len(_short_to_h5)} conference h5 values", flush=True)

    def add_h5(conf):
        rdig_re = re.compile(r".*R\d$")
        conf_id = conf["id"][:-4]
        if rdig_re.match(conf_id):
            conf_id = conf_id[:-2]

        if conf_id in _short_to_h5:
            conf["h5Index"] = _short_to_h5[conf_id]
        return conf

    return add_h5


_allowed_rank_re = re.compile(r"[A-H]\*?$")


def _get_core_rank(shortname):
    shortname = shortname.lower().replace("threedv", "3dv")
    core_url = f"https://portal.core.edu.au/conf-ranks/?search={shortname}&by=all"
    core_res = requests.get(core_url)
    core_res = BeautifulSoup(core_res.text, "html.parser")

    for row in core_res.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 4:
            continue
        if tds[1].get_text().strip().lower() == shortname:
            rank = tds[3].get_text().strip()
            if _allowed_rank_re.match(rank):
                return rank

    return None


def make_core_rank_function(conference_groups, online=True, force_update=False):
    core_save_file = os.path.join(this_folder, os.pardir, "rank", "core.yaml")
    if os.path.isfile(core_save_file):
        with open(core_save_file, "r") as f:
            core_ranks = yaml.safe_load(f)
        if core_ranks is None:
            core_ranks = {}
    else:
        core_ranks = {}
        force_update = True

    last_update_file = os.path.join(this_folder, "data", ".last_core_update")
    if not os.path.isfile(last_update_file):
        force_update = True
    else:
        with open(last_update_file, "r") as f:
            last_update = dateparser.parse(f.read().strip())

        if last_update is None:
            force_update = True
        else:
            force_update = force_update or last_update + timedelta(days=1) < datetime.now()

    rdig_re = re.compile(r".*R\d$")
    conference_groups = {cfg[:-2] if rdig_re.match(cfg) else cfg for cfg in conference_groups}
    if force_update and online:
        print(f"Updating core ranks for {len(conference_groups)} conferences")

        for i, group in enumerate(conference_groups):
            rank = _get_core_rank(group)
            if rank is not None:
                core_ranks[group] = rank
                print(f"{i+1}/{len(conference_groups)}: {group} -> {rank}")

        with open(core_save_file, "w") as f:
            yaml.safe_dump(core_ranks, f)
        with open(last_update_file, "w") as f:
            f.write(datetime.now().isoformat())

    def add_core_rank(conf):
        rdig_re = re.compile(r".*R\d$")
        conf_id = conf["id"][:-4]
        if rdig_re.match(conf_id):
            conf_id = conf_id[:-2]

        if conf_id in core_ranks:
            conf["rating"] = core_ranks[conf_id]

        return conf

    return add_core_rank
