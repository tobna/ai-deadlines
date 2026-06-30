import re

from ..log_config import logger
from .http import fetch_soup

_TITLE = "Winter Conference on Applications of Computer Vision"


def _submissions_soup(url):
    """Soup of the WACV submissions page, discovering its link from the homepage if needed."""
    soup = fetch_soup(url + "/submissions")
    if soup is not None:
        return soup
    home = fetch_soup(url)
    if home is None:
        return None
    for link in home.find_all("a"):
        if link.get_text().lower().strip() in ("submissions", "submission"):
            href = link.get("href", "")
            target = href if href.startswith("https://") else url + href
            logger.info(f"trying discovered WACV submissions link: {target}")
            return fetch_soup(target)
    return None


def _parse_submission_deadlines(soup, data):
    """Read 'Paper submission' <li> items into round 1/2 deadlines."""
    for li in soup.find_all("li"):
        txt = li.get_text().strip()
        if txt.lower().startswith(("paper submissions:", "submission:", "paper submission deadline:")):
            round_idx = 1 if "deadline" in data["timeline"][0] else 0
            data["timeline"][round_idx]["deadline"] = ":".join(txt.split(":")[1:]).split("(")[0].strip()


def _split_session_dates(date_text):
    """Split a 'Jan 6th - 8th' / 'Feb 28 - Mar 3' range into (start, end), or None.

    The end borrows the start's month when it omits one; the year is appended later by
    parse_all_times from the conference id.
    """
    sep = next((s for s in ("–", "—", "-") if s in date_text), None)
    if sep is None:
        return None
    start, end = (part.strip() for part in date_text.split(sep, 1))
    if not start or not end:
        return None
    if end[:1].isdigit():  # end omits the month -> borrow it from the start
        end = f"{start.split(' ')[0]} {end}"
    return start, end


def _parse_dates_fallback(year, data):
    """Fall back to the thecvf 'Dates' table, which labels each round explicitly."""
    url = f"https://wacv.thecvf.com/Conferences/{year}/"
    data["website"] = url
    logger.info(f"trying WACV dates fallback: {url}Dates")
    soup = fetch_soup(url + "Dates")
    if soup is None:
        return
    abstract_re = re.compile(r"Round (\d) .*Paper .*Registration.*")
    deadline_re = re.compile(r"Round (\d) .*Paper .*Submission.*")
    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        # The "Main Conference Session(s)" row carries the event dates in the next cell.
        if len(tds) >= 2 and "main conference" in tds[0].get_text().lower():
            session_dates = _split_session_dates(tds[1].get_text(" ", strip=True))
            if session_dates is not None:
                data["conferenceStartDate"], data["conferenceEndDate"] = session_dates
        for i, td in enumerate(tds):
            if i + 1 >= len(tds):
                continue
            txt = td.get_text().strip()
            match = abstract_re.match(txt)
            if match:
                data["timeline"][int(match.group(1)) - 1]["abstractDeadline"] = tds[i + 1].get_text().strip()
            match = deadline_re.match(txt)
            if match:
                data["timeline"][int(match.group(1)) - 1]["deadline"] = tds[i + 1].get_text().strip()


def parse_wacv(year):
    url = f"https://wacv{year}.thecvf.com"
    data = {
        "id": f"wacv{year}",
        "title": _TITLE,
        "shortname": f"WACV {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["CV"],
        "timeline": [{}, {}],
    }

    soup = _submissions_soup(url)
    if soup is not None:
        _parse_submission_deadlines(soup, data)

    if "deadline" not in data["timeline"][0]:
        _parse_dates_fallback(year, data)

    if "deadline" not in data["timeline"][0]:
        return {}

    rm_idx = []
    for idx in range(2):
        if "deadline" in data["timeline"][idx]:
            data["timeline"][idx]["note"] = f"Round {idx + 1}"
        else:
            rm_idx.append(idx)
    for idx in sorted(rm_idx, reverse=True):
        data["timeline"].pop(idx)
    return data
