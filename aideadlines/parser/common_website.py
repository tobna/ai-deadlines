import re

from .http import fetch_soup


def _cell_after(tds, i):
    """Text of the cell after index ``i``, or None when ``i`` is the last cell."""
    return tds[i + 1].get_text() if i + 1 < len(tds) else None


def parse_common_website_format(data, url):
    if "timeline" not in data:
        data["timeline"] = [{}]
    website = fetch_soup(url)
    if website is None:
        return data
    return extract_dates_from_soup(data, website)


def extract_dates_from_soup(data, website):
    """Pull deadlines and conference dates out of an already-fetched 'Dates' page soup."""
    if "timeline" not in data:
        data["timeline"] = [{}]

    for table in website.find_all("table"):
        main_conference_data = True
        for row in table.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 1:
                main_conference_data = (
                    "main conference" in tds[0].get_text().lower()
                    or "paper submission" in tds[0].get_text().lower()
                )
            for i, td in enumerate(tds):
                lower = td.get_text().lower()
                if (
                    all(word in lower for word in ["abstract", "submission", "deadline"])
                    or all(word in lower for word in ["paper", "registration", "deadline"])
                ) and main_conference_data:
                    nxt = _cell_after(tds, i)
                    if nxt is not None:
                        data["timeline"][0]["abstractDeadline"] = nxt
                elif all(word in lower for word in ["submission", "deadline"]) and main_conference_data:
                    nxt = _cell_after(tds, i)
                    if nxt is not None:
                        data["timeline"][0]["deadline"] = nxt
                elif "main conference day" in lower:
                    nxt = _cell_after(tds, i)
                    if nxt is not None:
                        if "conferenceStartDate" not in data:
                            data["conferenceStartDate"] = nxt
                        data["conferenceEndDate"] = nxt
                elif "main conference" in lower and not any(
                    word in lower for word in ["submission", "decision", "paper", "notification", "deadline"]
                ):
                    date = _cell_after(tds, i)
                    if date is None:
                        continue
                    month = date.split(" ")[0]
                    if month.endswith(","):
                        month = month[:-1]
                    days = date[len(month) + 1:]
                    days = days.split(",") if "," in days else days.split("-")
                    if len(days) >= 2:
                        data["conferenceStartDate"] = f"{month} {days[0].strip()}"
                        data["conferenceEndDate"] = f"{month} {days[1].strip()}"

            header = row.find_next("th")
            if header and ("conference sessions" in header.get_text().lower()):
                td = row.find_next("td")
                if td is not None:
                    dates = td.get_text().replace("\xa0", " ").split("through")
                    if len(dates) >= 2:
                        data["conferenceStartDate"] = dates[0].strip()
                        data["conferenceEndDate"] = dates[1].strip()

    date_sessions = website.find_all("div", {"class": "date-sessions-table"})
    if len(date_sessions) > 0:
        date_re = re.compile(r"(.*) (\d\d) - (\d\d): (.*)")
        for p in date_sessions[0].find_all("p"):
            match = date_re.match(p.get_text())
            if match and "conference" in match.group(4).lower():
                data["conferenceStartDate"] = f"{match.group(1)} {match.group(2)}"
                data["conferenceEndDate"] = f"{match.group(1)} {match.group(3)}"
    return data


def _every_year(year):
    return True


def _even_years(year):
    return year % 2 == 0


def _odd_years(year):
    return year % 2 == 1


# One factory drives the conferences that share the neurips.cc / thecvf.com "Dates" table
# layout, replacing five near-identical hand-written parsers.
_CONFIGS = [
    dict(id="eccv", title="European Conference on Computer Vision", short="ECCV",
         url="https://eccv.ecva.net/Conferences/{year}/", tags=["CV"], year_filter=_even_years),
    dict(id="cvpr", title="Computer Vision and Pattern Recognition Conference", short="CVPR",
         url="https://cvpr.thecvf.com/Conferences/{year}/", tags=["CV"], year_filter=_every_year),
    dict(id="iccv", title="International Conference on Computer Vision", short="ICCV",
         url="https://iccv.thecvf.com/Conferences/{year}/", tags=["CV"], year_filter=_odd_years),
    dict(id="neurips", title="Neural Information Processing Systems", short="NeurIPS",
         url="https://neurips.cc/Conferences/{year}/", tags=["ML"], year_filter=_every_year),
    dict(id="icml", title="International Conference on Machine Learning", short="ICML",
         url="https://icml.cc/Conferences/{year}/", tags=["ML"], year_filter=_every_year),
]


def _make_parser(config):
    def parse(year):
        if not config["year_filter"](year):
            return {}
        url = config["url"].format(year=year)
        data = {
            "id": f"{config['id']}{year}",
            "title": config["title"],
            "shortname": f"{config['short']} {year}",
            "isApproximateDeadline": False,
            "website": url,
            "tags": list(config["tags"]),
        }
        data = parse_common_website_format(data, url + "Dates")
        if "deadline" not in data["timeline"][0] or "conferenceStartDate" not in data:
            return {}
        return data

    parse.__name__ = f"parse_{config['id']}"
    return parse


PARSER = [_make_parser(config) for config in _CONFIGS]
