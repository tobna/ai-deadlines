import re
from copy import deepcopy
import requests
from bs4 import BeautifulSoup


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
    }

    if submissions is not None:
        print("try link", submission_link)
        submissions = requests.get(submission_link)
        submissions = BeautifulSoup(submissions.text, "html.parser")
        print(submissions)

        for li in submissions.find_all("li"):
            txt = li.get_text().strip()
            # print(txt)
            if (
                txt.lower().startswith("paper submissions:")
                or txt.lower().startswith("submission:")
                or txt.lower().startswith("paper submission deadline:")
            ):
                key = "deadline2" if "deadline1" in data else "deadline1"

                data[key] = txt.split(":")[1].strip()

        if "deadline1" not in data:
            return {}

    if "deadline1" not in data:
        url = f"https://wacv.thecvf.com/Conferences/{year}/"
        data["website"] = url
        print("try", url + "Dates")

        dates_site = requests.get(url + "Dates")
        dates_site = BeautifulSoup(dates_site.text, "html.parser")

        abstract_re = re.compile(r"Round (\d) .*Paper .*Registration.*")
        deadline_re = re.compile(r"Round (\d) .*Paper .*Submission.*")

        for row in dates_site.find_all("tr"):
            tds = row.find_all("td")
            for i, td in enumerate(tds):
                txt = td.get_text().strip()
                print(txt)

                match = abstract_re.match(txt)
                if match:
                    data[f"abstractDeadline{match.group(1)}"] = tds[i + 1].get_text().strip()
                match = deadline_re.match(txt)
                if match:
                    data[f"deadline{match.group(1)}"] = tds[i + 1].get_text().strip()

    if "deadline1" in data:
        data2 = deepcopy(data)
        data["deadline"] = data["deadline1"]
        data2["deadline"] = data2["deadline2"]
        data["note"] = "Round 1"
        data2["note"] = "Round 2"
        data["id"] = f"wacvR1{year}"
        data2["id"] = f"wacvR2{year}"
        if "abstractDeadline1" in data:
            data["abstractDeadline"] = data["abstractDeadline1"]
        if "abstractDeadline2" in data:
            data2["abstractDeadline"] = data["abstractDeadline2"]

        end_dig_re = re.compile(r".*\d$")
        for di in [data, data2]:
            for key in list(di.keys()):
                if end_dig_re.match(key):
                    di.pop(key)

        return [data, data2]

    return {}


if __name__ == "__main__":
    year = 2026
    data = {"s": 1}
    while len(data) > 0:
        data = parse_wacv(year)
        print(year, data)
        year -= 1
