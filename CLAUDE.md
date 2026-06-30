# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Conference Deadlines** — a community-maintained tracker of academic conference submission deadlines (AI, ML, NLP, CV). Live at https://aideadlines.nauen-it.de.

Data is stored as YAML files in `conferences/`, scraped/merged from multiple sources, converted to JSON, and served as a static frontend.

## Common Commands

```bash
# Full update pipeline (scrape, merge, convert, commit/push)
python3 update.py

# Scrape online sources and merge into conferences/ YAML files
python3 -m aideadlines.update_data --online

# Convert YAML → JSON only (no scraping)
python3 -m aideadlines.data_to_json

# Build static website (copy files, gzip compress)
./make_website.sh
```

The `update.py` script requires a `.gittkn` file (git token, excluded from repo) for auto-commit/push.

## Architecture

### Data Pipeline

`update_data.py` orchestrates the full flow:

1. Load all `conferences/*.yaml` files
2. Optionally fetch from online sources (`--online` flag):
   - Official conference websites (via `parser/common_website.py`)
   - Hugging Face AI deadlines GitHub repo (`parser/hf_list.py`)
   - Nino Duarte's deadlines repo (`parser/ninoduarte_list.py`)
   - CCF deadlines (`parser/ccf_deadlines.py`)
3. Merge by `dataSrc` priority (lower priority is overwritten by higher)
4. Estimate future instances from historical patterns (`parser/see_future.py`)
5. Fetch rankings: CORE ratings (`rank/core.yaml`) and Google Scholar h5-index (`rank/h5index.yaml`)
6. Write updated YAML back to `conferences/`

`data_to_json.py` then splits YAML into:
- `aideadlines/data/conferences.json` — upcoming deadlines
- `aideadlines/data/conferences_archive.json` — past deadlines

### Source Priority (`dataSrc` field)

Lower priority is silently overwritten by higher priority sources (see `SOURCES` in
`aideadlines/merge.py`):
`estimate` < `ninoduarte-git` < `ccf-deadlines` < `hf-repo` < `off-website` < `manual`

`manual` is the highest priority: hand-curated edits win over every scraper. `estimate` is
the lowest: a guessed instance yields to any real data.

### Conference YAML Schema

Key fields in each `conferences/<id>.yaml`:
- `id`, `shortname`, `title`, `website`, `location`
- `conferenceStartDate`, `conferenceEndDate`
- `timeline`: list of `{deadline, abstractDeadline?, note?}` entries
- `tags`: from `[DM, ML, NLP, CV, HCI, RO, SP]`
- `dataSrc`: source identifier (controls merge priority)
- `isApproximateDeadline`: true for estimated entries
- `h5Index`, `rating`: auto-populated from ranking files
- `timezone`: deadline timezone (default AoE)

### Frontend

Single-page static app — no backend:
- `aideadlines/index.html` — structure and filter controls
- `aideadlines/scripts.js` — loads JSON, handles filtering/sorting/theming
- `aideadlines/styles.tailwind.css` — Tailwind CSS
- `html/` — generated output directory (gitignored)

## Dependencies

Python: `requests`, `pyyaml`, `dateparser`, `loguru`, `beautifulsoup4`, `pytz`

Install: `pip install -r requirements.txt` or `pip install -e .`
