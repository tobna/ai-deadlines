import re
import requests
from bs4 import BeautifulSoup


def parse_common_website_format(data, url):
    if "timeline" not in data:
        data["timeline"] = [{}]
    website = requests.get(url)
    # print(website)
    website = BeautifulSoup(website.text, "html.parser")
    # print(website)
    tables = website.find_all("table")
    for table in tables:
        main_conference_data = True
        for row in table.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 1:
                main_conference_data = (
                    "main conference" in tds[0].get_text().lower() or "paper submission" in tds[0].get_text().lower()
                )
                # print(tds[0].get_text().strip(), main_conference_data)
            for i, td in enumerate(tds):
                txt = td.get_text()
                if (
                    all(word in txt.lower() for word in ["abstract", "submission", "deadline"])
                    or all(word in txt.lower() for word in ["paper", "registration", "deadline"])
                ) and main_conference_data:
                    # print("abstract ->", txt)
                    data["timeline"][0]["abstractDeadline"] = tds[i + 1].get_text()
                elif all(word in txt.lower() for word in ["submission", "deadline"]) and main_conference_data:
                    # print("deadline ->", txt)
                    data["timeline"][0]["deadline"] = tds[i + 1].get_text()

                elif "main conference day" in txt.lower():
                    # print("conference ->", tds[i + 1].get_text())
                    if "conferenceStartDate" not in data:
                        data["conferenceStartDate"] = tds[i + 1].get_text()
                    data["conferenceEndDate"] = tds[i + 1].get_text()

                elif "main conference" in txt.lower() and not any(
                    word in txt.lower() for word in ["submission", "decision", "paper", "notification", "deadline"]
                ):
                    # print("conference ->", txt.strip(), end=" ")
                    # print(tds[i + 1].get_text())
                    date = tds[i + 1].get_text()
                    month = date.split(" ")[0]
                    if month.endswith(","):
                        month = month[:-1]
                    days = date[len(month) + 1 :]
                    if "," in days:
                        days = days.split(",")
                    else:
                        days = days.split("-")
                    data["conferenceStartDate"] = f"{month} {days[0].strip()}"
                    data["conferenceEndDate"] = f"{month} {days[1].strip()}"

            header = row.find_next("th")
            if header and ("conference sessions" in header.get_text().lower()):
                td = row.find_next("td")
                dates = td.get_text().replace("\xa0", " ")
                # print("conference ->", txt, dates)
                dates = dates.split("through")
                data["conferenceStartDate"] = dates[0].strip()
                data["conferenceEndDate"] = dates[1].strip()

    date_sessions = website.find_all("div", {"class": "date-sessions-table"})
    if len(date_sessions) > 0:
        date_sessions = date_sessions[0]
        ps = date_sessions.find_all("p")
        date_re = re.compile(r"(.*) (\d\d) - (\d\d): (.*)")
        for p in ps:
            match = date_re.match(p.get_text())
            if match:
                desc = match.group(4)
                if "conference" in desc.lower():
                    data["conferenceStartDate"] = f"{match.group(1)} {match.group(2)}"
                    data["conferenceEndDate"] = f"{match.group(1)} {match.group(3)}"
    return data


def parse_neurips_data(year: int):
    url = f"https://neurips.cc/Conferences/{year}/"

    data = {
        "id": f"neurips{year}",
        "title": "Neural Information Processing Systems",
        "shortname": f"NeurIPS {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["ML"],
    }

    data = parse_common_website_format(data, url + "Dates")

    if "deadline" not in data["timeline"][0] or "conferenceStartDate" not in data:
        return {}
    return data


def parse_iccv(year):
    if year % 2 != 1:
        return {}
    url = f"https://iccv.thecvf.com/Conferences/{year}/"

    data = {
        "id": f"iccv{year}",
        "title": "International Conference on Computer Vision",
        "shortname": f"ICCV {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["CV"],
    }

    data = parse_common_website_format(data, url + "Dates")

    if "deadline" not in data["timeline"][0] or "conferenceStartDate" not in data:
        return {}

    return data


def parse_cvpr(year):
    url = f"https://cvpr.thecvf.com/Conferences/{year}/"

    data = {
        "id": f"cvpr{year}",
        "title": "Computer Vision and Pattern Recognition Conference",
        "shortname": f"CVPR {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["CV"],
    }

    data = parse_common_website_format(data, url + "Dates")

    if "deadline" not in data["timeline"][0] or "conferenceStartDate" not in data:
        return {}

    return data


def parse_eccv(year):
    if year % 2 != 0:
        return {}
    url = f"https://eccv.ecva.net/Conferences/{year}/"

    data = {
        "id": f"eccv{year}",
        "title": "European Conference on Computer Vision",
        "shortname": f"ECCV {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["CV"],
    }

    data = parse_common_website_format(data, url + "Dates")

    if "deadline" not in data["timeline"][0] or "conferenceStartDate" not in data:
        return {}

    return data


def parse_icml(year):
    url = f"https://icml.cc/Conferences/{year}/"

    data = {
        "id": f"icml{year}",
        "title": "International Conference on Machine Learning",
        "shortname": f"ICML {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["ML"],
    }

    data = parse_common_website_format(data, url + "Dates")

    if "deadline" not in data["timeline"][0] or "conferenceStartDate" not in data:
        return {}

    return data


PARSER = [parse_eccv, parse_cvpr, parse_iccv, parse_neurips_data, parse_icml]

if __name__ == "__main__":
    import sys
    import os

    src_folder = os.path.join(os.path.dirname(__file__), os.pardir)
    sys.path.append(src_folder)
    from ..utils import parse_all_times

    year = 2025
    data = {"test": 1}
    while len(data) > 0:
        data = parse_neurips_data(year)
        data = parse_all_times(data)
        print(year, data)
        year -= 1
