"""Official-website parsers for the explainable-AI venues (xAI, AIES, EXPLAINS).

No list source carries these, so each is read from its own yearly site. Every parser returns
``{}`` unless the page it read is really for the requested year: xAI publishes next year's
page early with the old dates copied in, and INSTICC serves the current edition for any
unknown year.
"""

import re

from .http import fetch_soup

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# "February 8, 2026" / "March, 15th, 2024" / "April 20" (no year) / "1st of February, 2026"
_DATE_RE = re.compile(
    rf"(?:(?P<m1>{_MONTHS}),?\s+(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?"
    rf"|(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s+of\s+(?P<m2>{_MONTHS}))(?:,?\s*(?P<y>\d{{4}}))?",
    re.I,
)
# "17-19 July, 2024, Malta, Valletta" / "28 - 30 October, 2026, Angers, France"
# -> first day, last day, month, year, rest. ponytail: same-month ranges only.
_DAY_FIRST_RANGE_RE = re.compile(
    rf"(\d{{1,2}})\s*-\s*(\d{{1,2}})(?:st|nd|rd|th)?,?\s+({_MONTHS}),?\s*(\d{{4}})(.*)", re.I | re.S
)
# "October 12-14, 2026" -> month, first day, last day, year
_MONTH_FIRST_RANGE_RE = re.compile(rf"({_MONTHS}) (\d{{1,2}})\s*[-–]\s*(\d{{1,2}}),? (\d{{4}})", re.I)


def _fmt(match, default_year):
    """A ``_DATE_RE`` match as 'Month D, YYYY', filling in a missing year."""
    month = (match["m1"] or match["m2"]).capitalize()
    return f"{month} {int(match['d1'] or match['d2'])}, {match['y'] or default_year}"


def _date_after(label_re, text, year):
    """The date right after ``label_re`` in ``text``, or None."""
    label = re.search(label_re + r"\s*", text, re.I)
    match = label and _DATE_RE.match(text, label.end())
    return _fmt(match, year) if match else None


def _venue_from_range(match):
    """Start/end dates and location from a ``_DAY_FIRST_RANGE_RE`` match."""
    start, end, month, year, rest = match.groups()
    month = month.capitalize()
    return {
        "conferenceStartDate": f"{month} {int(start)}, {year}",
        "conferenceEndDate": f"{month} {int(end)}, {year}",
        "location": rest.strip(" ,-\n").split("\n")[0].strip(),
    }


def extract_xai_timeline(soup, year):
    """The main-track deadlines from an xAI 'important-dates' page, or None.

    Extended deadlines are appended to the cell (the old ones struck out), so the last date
    in a cell is the current one.
    """
    entry = {}
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = cells[0].get_text(" ", strip=True).lower()
        dates = list(_DATE_RE.finditer(cells[1].get_text(" ", strip=True)))
        if not dates:
            continue
        if label.startswith("authors/title"):
            entry["abstractDeadline"] = _fmt(dates[-1], year)
        elif "article upload deadline" in label:
            # ponytail: the main-track table comes first; late-breaking/DC tables follow it
            entry["deadline"] = _fmt(dates[-1], year)
            return entry
    return None


def parse_xai(year):
    url = f"https://xaiworldconference.com/{year}/"
    home = fetch_soup(url)
    banner = home and home.find("div", class_="banner-desc")
    match = banner and _DAY_FIRST_RANGE_RE.search(banner.get_text("\n"))
    if not match or int(match[4]) != year:  # "dates/location to be announced"
        return {}
    dates_page = fetch_soup(url + "important-dates/")
    entry = dates_page and extract_xai_timeline(dates_page, year)
    # ponytail: every edition so far had its deadline in the conference year; a stale copied-over
    # date fails this check, a real December deadline would too (the estimate covers that year)
    if not entry or not entry["deadline"].endswith(str(year)):
        return {}
    return {
        "id": f"xai{year}",
        "title": "World Conference on Explainable Artificial Intelligence",
        "shortname": f"xAI {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["ML", "XAI"],
        "timeline": [entry],
        **_venue_from_range(match),
    }


def extract_aies_dates(home, cfp, year):
    """Deadlines, dates and location from the AIES homepage and call for papers, or None."""
    text = cfp.get_text(" ", strip=True)
    deadline = _date_after(r"Submission deadline:", text, year)
    if deadline is None or not deadline.endswith(str(year)):
        return None
    entry = {"deadline": deadline}
    abstract = _date_after(r"Abstract Registration Deadline:", text, year)
    if abstract is not None:
        entry["abstractDeadline"] = abstract
    data = {"timeline": [entry]}

    # The hero slider: [..., "Malmo Live", "Malmo, Sweden", "October 12-14, 2026", ...]
    captions = home.find_all(class_="tp-caption")
    for i, caption in enumerate(captions):
        match = _MONTH_FIRST_RANGE_RE.fullmatch(caption.get_text(" ", strip=True))
        if match and int(match[4]) == year:
            month = match[1].capitalize()
            data["conferenceStartDate"] = f"{month} {match[2]}, {year}"
            data["conferenceEndDate"] = f"{month} {match[3]}, {year}"
            if i > 0:  # "Malmo Live<br>Malmo, Sweden"
                data["location"] = captions[i - 1].get_text(", ", strip=True)
            break
    return data


def parse_aies(year):
    url = f"https://www.aies-conference.com/{year}/"
    home = fetch_soup(url)
    cfp = home and fetch_soup(url + "call-for-papers/")
    data = cfp and extract_aies_dates(home, cfp, year)
    if not data:
        return {}
    return {
        "id": f"aies{year}",
        "title": "AAAI/ACM Conference on AI, Ethics, and Society",
        "shortname": f"AIES {year}",
        "isApproximateDeadline": False,
        "website": url,
        "tags": ["XAI"],
        **data,
    }


def extract_insticc_dates(soup, year):
    """Deadlines, dates and location from an INSTICC 'ImportantDates.aspx' page, or None."""
    location = soup.find("meta", attrs={"name": "location"})
    match = location and _DAY_FIRST_RANGE_RE.search(location.get("content", ""))
    if not match or int(match[4]) != year:
        return None
    timeline = []
    stages = [("lblRPaperSubDates", "Regular Papers"), ("lblPPaperSubDates", "Position / Regular Papers (2nd stage)")]
    for span_id, note in stages:
        span = soup.find("span", id=re.compile(span_id + "$"))
        date = span and _DATE_RE.match(span.get_text(strip=True))
        if date:
            timeline.append({"deadline": _fmt(date, year), "note": note})
    if not timeline:
        return None
    return {"timeline": timeline, **_venue_from_range(match)}


def parse_explains(year):
    url = f"https://explains.scitevents.org/ImportantDates.aspx?y={year}"
    soup = fetch_soup(url)
    data = soup and extract_insticc_dates(soup, year)
    if not data:
        return {}
    return {
        "id": f"explains{year}",
        "title": "International Conference on Explainable AI for Neural and Symbolic Methods",
        "shortname": f"EXPLAINS {year}",
        "isApproximateDeadline": False,
        "website": f"https://explains.scitevents.org/?y={year}",
        "tags": ["ML", "XAI"],
        **data,
    }


PARSER = [parse_xai, parse_aies, parse_explains]
