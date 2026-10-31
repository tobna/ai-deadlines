# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Conference Deadlines** — a community-maintained tracker of academic conference submission deadlines (AI, ML, NLP, CV). Live at https://aideadlines.nauen-it.de.

Data is stored as YAML files in `conferences/`, scraped/merged from multiple sources, validated, converted to JSON, and served as a static frontend.

## Common Commands

```bash
# Install everything (runtime + dev group) into .venv from uv.lock
uv sync

# Full update pipeline (pull, scrape, validate, convert, commit/push)
uv run update.py

# Scrape online sources and merge into conferences/ YAML files
uv run python -m aideadlines.update_data --online

# Validate the conferences/*.yaml data (used as a gate before auto-commit)
uv run python -m aideadlines.validate

# Convert YAML → JSON only (no scraping)
uv run python -m aideadlines.data_to_json

# Build static website (runs update.py, copies files, gzip compress) — the server's hourly job
uv run ./make_website.sh

# Tests + lint (CI runs both)
uv run pytest
uv run ruff check aideadlines/ tests/ update.py
```

`make_website.sh` and `update.py` call plain `python3`; under `uv run` that is the project's venv.

The `update.py` script requires a `.gittkn` file (git token, gitignored) for auto-commit/push. The token is passed to git via a credential helper reading from the environment — it is never placed on a command line.

## Architecture

### Module map (`aideadlines/`)

- `update_data.py` — orchestrates scraping + merging; `main()` entry point.
- `data_to_json.py` — splits merged YAML into upcoming/archive JSON; `main()` entry point.
- `validate.py` — schema validation (`validate_conferences`); `main()` exits non-zero on problems.
- `merge.py` — source-priority merge logic (`SOURCES`, `merge_one`, `merge_source`, `tag_wacv_round`), the id blocklist/aliases (see below), and `load_conference_files`, the one `conferences/*.yaml` loader used by the pipeline, the validator and the JSON export.
- `utils.py` — date/timezone parsing (`_parse_timestr`, `parse_all_times`, `normalize_timezone_for_js`), merge helpers (`join_conferences`, `unite_tags`, `parse_stuff`). Zone names in a deadline string are swapped for offsets via `TZ_REPLACE` (whole words only); a conference `timezone` that pytz knows (IANA, `CET`) is applied with DST, anything else (`AoE`, `UTC-12`, `PST`) via dateparser, and an unknown one is an ERROR, never the server clock.
- `ranking.py` — CORE rating + Google Scholar h5-index lookups.
- `parser/xai.py` — the XAI venues' own sites (xAI, AIES, EXPLAINS), see below.
- `parser/openaccept.py` — acceptance rates from the openaccept.org metadata repo (not a deadline source, see below).
- `parser/http.py` — resilient HTTP layer used by all parsers (see below).
- `parser/*.py` — one module per source (see Data Pipeline).

The pipeline modules are **functions with `main()` guards** — importing them does not run the pipeline (important for tests).

### Data Pipeline

`update_data.py:main()` runs:

1. `load_conferences()` — load all `conferences/*.yaml`, parsing timestamps.
2. With `--online`, `scrape_online()` fetches and merges each source in ascending priority:
   - Official conference websites (`parser/common_website.py`, `parser/wacv.py`, `parser/xai.py`)
   - Hugging Face AI deadlines repo (`parser/hf_list.py`)
   - Nino Duarte's deadlines repo (`parser/ninoduarte_list.py`, only with `--load-nino-data`)
   - CCF deadlines (`parser/ccf_deadlines.py`): the whole `AI` category plus the single files listed in `load_conferences` (`CG/3dv`, `SC/satml`), and any file named like an existing `conferences/<id>.yaml`
3. `normalize_nips()` — rename lingering `nips`/`NIPS` to `neurips`/`NeurIPS`.
4. `drop_empty_timelines()` — drop unparseable deadlines and conferences with none left; `flag_implausible_abstracts()` logs an ERROR (red status, nothing dropped) for an upcoming deadline whose abstract is after it or more than 90 days before, since either date can be the wrong one — fix such a record with `dataSrc: manual`.
5. `write_groups()` — group by conference family, estimate future instances (`parser/see_future.py`; every `dataSrc: estimate` entry is dropped and rebuilt from the real instances on each run, so a corrected source year fixes its estimates too), attach CORE/h5 ranks (`ranking.py`) and acceptance rates (`parser/openaccept.py`), and write YAML back to `conferences/`.

`data_to_json.py:main()` then splits YAML into:
- `aideadlines/data/conferences.json` — upcoming deadlines
- `aideadlines/data/conferences_archive.json` — past deadlines
- `aideadlines/data/deadlines.md` — upcoming deadlines as one markdown table (`conferences_to_markdown`), for LLM agents that fetch a URL and can't run the page's JavaScript

All three are generated and gitignored; `make_website.sh` copies them into `html/data/`.

`update.py` chains these for the unattended run: pull → `update_data --online` → **`validate` (aborts the commit on failure)** → `data_to_json` → update README badge → commit/push. Every step except the commit (which exits 1 when nothing changed) is checked: a failure prints a red `ERROR: <step> failed` line and the final `=== PIPELINE FAILED: … failed step(s): <steps> ===` names it (both end up in `status.html`).

### Source Priority (`dataSrc` field)

Merging is centralized in `merge.py`. Lower priority is silently overwritten by higher (see `SOURCES`):

`estimate` < `ninoduarte-git` < `ccf-deadlines` < `hf-repo` < `off-website` < `manual`

`manual` is the highest priority: hand-curated edits win over every scraper. `estimate` is the lowest: a guessed instance yields to any real data. (`ninoduarte-git` merges with strict `<`; the others with `<=`, via `merge_one(..., overwrite_equal=...)`.)

### Blocklist and id aliases (`merge.py`)

`BLOCKED_GROUPS` / `BLOCKED_DOMAINS` drop predatory or stray entries (SAI Conference venues such as
CVC, single workshop ids like `cvpr_ws`) and `ID_ALIASES` folds a source's alternate spelling into
the canonical group (`ieee cec` -> `cec`, `ruleml+rr` -> `rulemlrr`). Both are applied in
`merge_source` (every list source) and in `load_conference_files` (stale YAML, so also in validation
and the JSON export), so a blocked or aliased
conference cannot come back through the daily run. To block a new venue add its domain or group id
there; to merge duplicate groups add the alias — `ranking.py` searches CORE under the canonical id
and every alias spelling, so the rating follows automatically on the next online refresh (never
hand-edit `rank/core.yaml`).

### Acceptance rates (`parser/openaccept.py`)

Not a deadline source, so it doesn't take part in the `dataSrc` merge — rates are attached in
`write_groups` the way CORE ratings are.

The data comes from **[OpenAccept/openaccept-metadata](https://github.com/OpenAccept/openaccept-metadata)**,
not from openaccept.org: the site is a small volunteer project that answers 429 to a scraper
walking its ~31 conference pages, while the repo publishes the same numbers as one
schema-checked JSON per conference. Same tree-then-raw pattern as `ccf_deadlines`/`hf_list`.
Files are keyed by lower-cased basename (`ai/NeurIPS.json` -> `neurips`), `ALIASES` maps the few
group ids that differ, and paths are `quote`d (`gm/ACM MM.json` has a space). `yearly_data` is the
main research track — Findings and other second tracks live under `second_track_yearly_data`, so
they're ignored for free.

There is deliberately **no cache file** — `conferences/*.yaml` already holds the last known rates,
so on a failed fetch nothing is attached and they are written back unchanged. The only state is a
gitignored `aideadlines/data/.last_openaccept_update` stamp whose *mtime* throttles the fetch to
once per `REFRESH_HOURS` (30, deliberately longer than the daily pipeline run). It is only touched
after a fetch that returned data, so a failure retries on the next run.

A conference with no rate for its own year gets the most recent *earlier* year's, tagged with
`acceptanceRateYear` — never a later year, so past instances aren't backdated. The raw
`acceptedPapers`/`submittedPapers` counts ride along: the card pill shows only `~25%`, and the
tooltip spells out `Acceptance rate 2025: 24.52% (5,290 of 21,575 papers). Source: openaccept.org`.

### Parser conventions

All parsers, and the CORE lookup in `ranking.py`, fetch through `parser/http.py`, never `requests.get` directly (CORE: an unreachable portal aborts the refresh with an ERROR and keeps `rank/core.yaml`):

- `fetch` / `fetch_text` / `fetch_json` / `fetch_yaml` / `fetch_soup` use a pooled session with a **timeout** and **status checking**, and make **one attempt** (no retries: the next hourly run is the retry, and the stored data stays until then). They return `None` on any failure (error status, timeout, connection error).
- Callers treat `None` as "skip this file/record" and degrade gracefully rather than aborting the whole source.
- Per-record parsing is wrapped so one malformed conference is logged and skipped, not fatal.
- `parser/xai.py` reads xAI (`xaiworldconference.com/<year>/`), AIES (`aies-conference.com/<year>/`) and EXPLAINS
  (INSTICC's `ImportantDates.aspx?y=<year>`, whose span ids are the same on every INSTICC/SCITEPRESS conference).
  Each parser **rejects a page that isn't for the requested year**: xAI puts next year's page up early with the
  old deadlines copied in, and INSTICC redirects an unknown year to the current edition.
- The shared "Dates"-table conferences (CVPR/ICCV/ECCV/NeurIPS/ICML) come from one config-driven factory in `common_website.py` (`_CONFIGS` + `_make_parser`); add a new one by appending to `_CONFIGS`. Table extraction lives in `extract_dates_from_soup` (pure, unit-tested).

### Conference YAML Schema

Key fields in each `conferences/<id>.yaml`:
- `id`, `shortname`, `title`, `website`, `location`
- `conferenceStartDate`, `conferenceEndDate`
- `timeline`: list of `{deadline, abstractDeadline?, note?}` entries
- `tags`: from `[DM, ML, NLP, CV, HCI, RO, SP, XAI]`. Tags are united across a group and kept on every merge, so a
  tag no source provides (FAccT's/SaTML's `XAI`) is added once to the YAML and sticks. The frontend builds its tag
  filter from the data, so a new tag needs no frontend change (but keep `llms.txt` in sync).
- `dataSrc`: source identifier (controls merge priority)
- `isApproximateDeadline`: true for estimated entries
- `h5Index`, `rating`: auto-populated from ranking files
- `acceptanceRate`, `acceptanceRateYear`, `acceptedPapers`, `submittedPapers`: auto-populated from openaccept.org
- `timezone`: deadline timezone (default AoE)

### Frontend

Single-page static app — no backend:
- `aideadlines/index.html` — structure, filter controls, and a strict Content-Security-Policy.
- `aideadlines/scripts.js` — loads JSON, handles filtering/sorting/theming.
- `aideadlines/styles.css` — hand-written stylesheet, served as is (no build step)
- `html/` — generated output directory (gitignored)
- `nginx.conf` — site config of the `website` container (`nginx:latest`, mounted over `/etc/nginx/conf.d/default.conf` in the docker-stacks compose file): serves `.md` as `text/markdown`, text as UTF-8, and the `.gz` files `make_website.sh` writes via `gzip_static`. nginx reads it at start, so restart the container after a change.
- `aideadlines/sitemap.xml` — template; `make_website.sh` stamps `<lastmod>` with the build date on the way into `html/`, so the daily rebuild never shows up as a git change.

Agent/LLM access (the page renders client-side, so fetching the HTML yields nothing):
- `aideadlines/llms.txt` — served at `/llms.txt`, the [llms.txt](https://llmstxt.org) entry point: links the data files and documents the JSON schema and field semantics. Static; keep it in sync when the schema changes.
- `index.html` carries an HTML comment plus `<link rel="alternate">` tags pointing at `/data/deadlines.md` and `/data/conferences.json`.
  Agent fetchers strip `<head>` and comments, so the pointer that actually reaches them is in the body: `<main id="conferenceGrid">`
  starts with an `.agent-note` addressed to LLMs (scripts.js replaces it with the cards), and the footer links the agent files.

Conventions in `scripts.js`:
- Conference data is community-sourced, so **every value interpolated into `innerHTML` must go through `escapeHtml`**, and any URL used in an `href` through `safeHref` (http/https only).
- A **single global ticker** updates all visible countdowns once per second (do not create per-card intervals); filter inputs are debounced.

## Testing

`pytest` lives in `tests/` and runs with no network:
- Backend characterization tests (`test_utils.py`, `test_see_future.py`, `test_merge_priority.py`, `test_validate.py`) pin current behavior so refactors stay safe. (`data_to_json`'s timezone normalization is covered via `normalize_timezone_for_js` in `test_utils.py`.)
- `test_http.py` exercises status/error handling (one attempt, `None` on failure) via a monkeypatched session.
- `test_parsers.py` covers the pure parser helpers, the `common_website` factory metadata and the `xai` year guards (mocked `fetch_soup`).
- `test_deadlines_md.py` pins the markdown export's sorting, `(est.)` marking and pipe escaping.
- `test_update_data.py` covers pipeline steps (the `--historic` loop ends, implausible abstract deadlines are flagged); `test_update_pipeline.py` runs `update.py`'s `main` with every subprocess replaced (a failed push fails the run).

Live parser behavior is verified manually against real sites, not in CI. CI (`.github/workflows/ci.yml`) runs `uv sync --locked`, `ruff` and `pytest` on Python 3.13 and skips data-only auto-commits.

## Dependencies

Managed with uv: `pyproject.toml` holds lower bounds (`>=MAJOR.MINOR`), `uv.lock` pins every package including transitive ones. Add or change one with `uv add <pkg>` (dev tools: `uv add --dev`), upgrade deliberately with `uv lock --upgrade`, and commit `uv.lock`. The project has no build system, so uv installs only the dependencies and the code runs from the repo.

Runtime: `requests`, `beautifulsoup4`, `pytz`, `PyYAML`, `dateparser`, `python-dateutil`, `loguru`. Dev group: `pytest`, `ruff`. `requires-python = ">=3.13"`, the server's Python.

Server: the `updater` service in `docker-stacks/ai-deadlines.yaml` (outside this repo) runs the stock `ghcr.io/astral-sh/uv:python3.13-alpine` image and calls `uv run --frozen ./make_website.sh` every hour, so a changed `uv.lock` is installed on the next run without rebuilding an image. `--frozen` matters: the run must never rewrite `uv.lock`, because `update.py` commits with `git add .`.
