"""The markdown export agents read at /data/deadlines.md."""

from aideadlines.data_to_json import conferences_to_markdown

RECORDS = [
    {
        "shortname": "ZZZ 2027",
        "deadline": "2027-05-01T11:59:59Z",
        "isApproximateDeadline": True,
        "location": "Somewhere | Else",
        "tags": ["ML", "CV"],
    },
    {
        "shortname": "AAA 2026",
        "deadline": "2026-01-02T23:59:00Z",
        "abstractDeadline": "2025-12-25T23:59:00Z",
        "note": "Round 1",
        "conferenceStartDate": "2026-06-01",
        "conferenceEndDate": "2026-06-05",
        "website": "https://example.org/",
        "rating": "A*",
        "h5Index": 42,
    },
]


def test_rows_are_sorted_by_deadline_and_marked():
    lines = conferences_to_markdown(RECORDS).splitlines()
    rows = [line for line in lines if line.startswith("| ") and "---" not in line][1:]
    assert len(rows) == 2
    assert rows[0].startswith("| AAA 2026 |")
    assert "(est.)" not in rows[0]
    assert "(est.)" in rows[1]


def test_every_row_has_the_same_column_count_with_pipes_escaped():
    lines = conferences_to_markdown(RECORDS).splitlines()
    rows = [line for line in lines if line.startswith("| ")]
    assert all(row.count("|") - row.count("\\|") == 10 for row in rows)
    assert "Somewhere \\| Else" in lines[-1]
