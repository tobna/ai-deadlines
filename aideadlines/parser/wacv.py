import re
from copy import deepcopy

import requests
from bs4 import BeautifulSoup

from ..log_config import logger


def parse_wacv(year):
    url = f"https://wacv{year}.thecvf.com"

    submission_link = url + "/submissions"
    try:
        submissions = requests.get(submission_link)
    except requests.exceptions.ConnectionError:
        submissions = None
    if submissions is not None and submissions.status_code != 200:

        home = requests.get(url)
        home = BeautifulSoup(home.text, "html.parser")

        submission_link = None
        for link in home.find_all("a"):
            if link.get_text().lower().strip() in ["submissions", "submission"]:
                submission_link = link
                break

        if submission_link is None:
            return {}

        href = submission_link["href"]
        if href.startswith("https://"):
            submission_link = submission_link["href"]
        else:
            submission_link = url + submission_link["href"]

    data = {
        "id": f"wacv{year}",
        "title": "Winter Conference on Applications of Computer Vision",
        "shortname": f"WACV {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["CV"],
        "timeline": [{}, {}],
    }

    if submissions is not None:
        logger.info("try link", submission_link)
        submissions = requests.get(submission_link)
        submissions = BeautifulSoup(submissions.text, "html.parser")
        # print(submissions)

        for li in submissions.find_all("li"):
            txt = li.get_text().strip()
            # print(txt)
            if (
                txt.lower().startswith("paper submissions:")
                or txt.lower().startswith("submission:")
                or txt.lower().startswith("paper submission deadline:")
            ):
                round = 2 if "deadline" in data["timeline"][0] else 1

                data["timeline"][round - 1]["deadline"] = ":".join(txt.split(":")[1:]).split("(")[0].strip()

        if "deadline" not in data["timeline"][0]:
            return {}

    if "deadline" not in data["timeline"][0]:
        url = f"https://wacv.thecvf.com/Conferences/{year}/"
        data["website"] = url
        logger.info("try", url + "Dates")

        dates_site = requests.get(url + "Dates")
        dates_site = BeautifulSoup(dates_site.text, "html.parser")

        abstract_re = re.compile(r"Round (\d) .*Paper .*Registration.*")
        deadline_re = re.compile(r"Round (\d) .*Paper .*Submission.*")

        for row in dates_site.find_all("tr"):
            tds = row.find_all("td")
            for i, td in enumerate(tds):
                txt = td.get_text().strip()
                # print(txt)

                match = abstract_re.match(txt)
                if match:
                    data["timeline"][int(match.group(1)) - 1]["abstractDeadline"] = tds[i + 1].get_text().strip()
                match = deadline_re.match(txt)
                if match:
                    data["timeline"][int(match.group(1)) - 1]["deadline"] = tds[i + 1].get_text().strip()

    if "deadline" not in data["timeline"][0]:
        return {}

    rm_idx = []
    for idx in range(2):
        if "deadline" in data["timeline"][idx]:
            data["timeline"][idx]["note"] = f"Round {idx+1}"
        else:
            rm_idx.append(idx)
    for idx in sorted(rm_idx, reverse=True):
        data["timeline"].pop(idx)
    return data


if __name__ == "__main__":
    import os
    import sys

    src_folder = os.path.join(os.path.dirname(__file__), os.pardir)
    sys.path.append(src_folder)
    from utils import parse_all_times

    year = 2024
    data = {"s": 1}
    while len(data) > 0:
        data = parse_wacv(year)
        data = parse_all_times(data)
        print(year, data)
        year -= 1
