# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Conference Deadlines** — a community-maintained tracker of academic conference submission deadlines (AI, ML, NLP, CV). Live at https://aideadlines.nauen-it.de.

Data is stored as YAML files in `conferences/`, scraped/merged from multiple sources, validated, converted to JSON, and served as a static frontend.

## Common Commands

```bash
# Full update pipeline (pull, scrape, validate, convert, commit/push)
python3 update.py

# Scrape online sources and merge into conferences/ YAML files
python3 -m aideadlines.update_data --online

# Validate the conferences/*.yaml data (used as a gate before auto-commit)
python3 -m aideadlines.validate

# Convert YAML → JSON only (no scraping)
python3 -m aideadlines.data_to_json

# Build static website (copy files, gzip compress)
./make_website.sh

# Tests + lint (CI runs both)
pip install -r requirements-dev.txt
pytest
ruff check aideadlines/ tests/ update.py
```

The `update.py` script requires a `.gittkn` file (git token, gitignored) for auto-commit/push. The token is passed to git via a credential helper reading from the environment — it is never placed on a command line.

## Architecture

### Module map (`aideadlines/`)

- `update_data.py` — orchestrates scraping + merging; `main()` entry point.
- `data_to_json.py` — splits merged YAML into upcoming/archive JSON; `main()` entry point.
- `validate.py` — schema validation (`validate_conferences`); `main()` exits non-zero on problems.
- `merge.py` — source-priority merge logic (`SOURCES`, `merge_one`, `merge_source`, `tag_wacv_round`).
- `utils.py` — date/timezone parsing (`_parse_timestr`, `parse_all_times`, `normalize_timezone_for_js`), merge helpers (`join_conferences`, `unite_tags`, `parse_stuff`).
- `ranking.py` — CORE rating + Google Scholar h5-index lookups.
- `parser/http.py` — resilient HTTP layer used by all parsers (see below).
- `parser/*.py` — one module per source (see Data Pipeline).

The pipeline modules are **functions with `main()` guards** — importing them does not run the pipeline (important for tests and for the `aideadlines-update` console entry point in `setup.cfg`).

### Data Pipeline

`update_data.py:main()` runs:

1. `load_conferences()` — load all `conferences/*.yaml`, parsing timestamps.
2. With `--online`, `scrape_online()` fetches and merges each source in ascending priority:
   - Official conference websites (`parser/common_website.py`, `parser/wacv.py`)
   - Hugging Face AI deadlines repo (`parser/hf_list.py`)
   - Nino Duarte's deadlines repo (`parser/ninoduarte_list.py`, only with `--load-nino-data`)
   - CCF deadlines (`parser/ccf_deadlines.py`)
3. `normalize_nips()` — rename lingering `nips`/`NIPS` to `neurips`/`NeurIPS`.
4. `drop_empty_timelines()` — drop unparseable deadlines and conferences with none left.
5. `write_groups()` — group by conference family, estimate future instances (`parser/see_future.py`), attach CORE/h5 ranks (`ranking.py`), and write YAML back to `conferences/`.

`data_to_json.py:main()` then splits YAML into:
- `aideadlines/data/conferences.json` — upcoming deadlines
- `aideadlines/data/conferences_archive.json` — past deadlines

`update.py` chains these for the unattended run: pull → `update_data --online` → **`validate` (aborts the commit on failure)** → `data_to_json` → update README badge → commit/push.

### Source Priority (`dataSrc` field)

Merging is centralized in `merge.py`. Lower priority is silently overwritten by higher (see `SOURCES`):

`estimate` < `ninoduarte-git` < `ccf-deadlines` < `hf-repo` < `off-website` < `manual`

`manual` is the highest priority: hand-curated edits win over every scraper. `estimate` is the lowest: a guessed instance yields to any real data. (`ninoduarte-git` merges with strict `<`; the others with `<=`, via `merge_one(..., overwrite_equal=...)`.)

### Parser conventions

All parsers fetch through `parser/http.py`, never `requests.get` directly:

- `fetch` / `fetch_text` / `fetch_json` / `fetch_yaml` / `fetch_soup` use a pooled session with a **timeout**, **status checking**, and **bounded retries + backoff** on transient failures (429/5xx, connection errors). They return `None` on persistent failure.
- Callers treat `None` as "skip this file/record" and degrade gracefully rather than aborting the whole source.
- Per-record parsing is wrapped so one malformed conference is logged and skipped, not fatal.
- The shared "Dates"-table conferences (CVPR/ICCV/ECCV/NeurIPS/ICML) come from one config-driven factory in `common_website.py` (`_CONFIGS` + `_make_parser`); add a new one by appending to `_CONFIGS`. Table extraction lives in `extract_dates_from_soup` (pure, unit-tested).

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
- `aideadlines/index.html` — structure, filter controls, and a strict Content-Security-Policy.
- `aideadlines/scripts.js` — loads JSON, handles filtering/sorting/theming.
- `aideadlines/styles.tailwind.css` — Tailwind CSS
- `html/` — generated output directory (gitignored)

Conventions in `scripts.js`:
- Conference data is community-sourced, so **every value interpolated into `innerHTML` must go through `escapeHtml`**, and any URL used in an `href` through `safeHref` (http/https only).
- A **single global ticker** updates all visible countdowns once per second (do not create per-card intervals); filter inputs are debounced.

## Testing

`pytest` lives in `tests/` and runs with no network:
- Backend characterization tests (`test_utils.py`, `test_see_future.py`, `test_merge_priority.py`, `test_validate.py`) pin current behavior so refactors stay safe. (`data_to_json`'s timezone normalization is covered via `normalize_timezone_for_js` in `test_utils.py`.)
- `test_http.py` exercises retry/status/timeout via a monkeypatched session.
- `test_parsers.py` covers the pure parser helpers and the `common_website` factory metadata (mocked `fetch_soup`).

Live parser behavior is verified manually against real sites, not in CI. CI (`.github/workflows/ci.yml`) runs `ruff` + `pytest` and skips data-only auto-commits.

## Dependencies

Runtime (pinned in `requirements.txt`): `requests`, `beautifulsoup4`, `pytz`, `PyYAML`, `dateparser`, `python-dateutil`, `loguru`.
Dev (`requirements-dev.txt`): `pytest`, `ruff`.

Install: `pip install -r requirements-dev.txt` (or `pip install -e .` for runtime only).
