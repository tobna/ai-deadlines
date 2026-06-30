# Code Quality Overhaul — Plan

Branch: `code-quality-overhaul`

Goal: lock current behavior with tests, then fix the concrete security/perf/correctness
bugs, then fully restructure the backend pipeline, then clean up repo hygiene and docs.

## Decisions (confirmed with owner)

1. **Source priority:** `manual` is the **highest** priority source (hand-edits override
   all scrapers). The code (`_SOURCES`) is correct; **`CLAUDE.md` is wrong** and will be
   fixed to match.
2. **Test scope:** **Python backend only**, using `pytest`. No JS test toolchain.
   Frontend fixes are verified manually (and by reasoning), not by automated tests.
3. **Refactor appetite:** **Full restructure** of the backend pipeline, sequenced
   tests-first so behavior is pinned before anything moves.

## Sequencing principle

Tests → bugfixes → restructure → hygiene. Each phase stays green before the next starts.
The pipeline auto-commits to `main`, so behavior-preserving changes must be backed by tests.

---

## Phase 1 — Tests first (safety net)

Set up `pytest` (add to dev deps, create `tests/`, a `conftest.py` with fixtures and
frozen "now" where needed). Pin behavior of the pure/normalizable logic **before** touching it.

- `tests/test_utils.py`
  - `_parse_timestr`: explicit-time vs date-only, AoE default, timezone-name replacement
    (`TZ_REPLACE`), `None` on unparseable, datetime passthrough, `23:59:59` fill when no time.
  - `parse_all_times`: year-appending regexes (`month_day_re`, `month_day_time_re`),
    `" the "` start-month substitution, timeline deadline parsing.
  - `join_conferences`: master-over-slave field override, tag union, `tbd`/empty timeline
    falling back to slave.
  - `unite_tags`, `parse_stuff`: tag uniting, GMT→`Etc/GMT` sign flip, identical-deadline
    de-duplication and note/abstract merge.
- `tests/test_see_future.py`
  - `estimate_future_conferences`: too-few-deadlines short-circuit, yearly-rhythm
    inference, number of approximations capped by `max_approximations`/`end_in_years`,
    field propagation (title/rating/h5Index), id/shortname year rewrite.
- `tests/test_merge_priority.py`
  - Extract the duplicated merge logic mentally first; test that a higher-priority source
    overrides a lower one, lower never overrides higher, `estimate` is always replaced,
    and the `manual = highest` rule holds. (This test guards the Phase 3 dedup.)
- `tests/test_data_to_json.py`
  - Timezone normalization (`AoE`→`Etc/GMT+12`, `UTC+N` handling), splitting a timeline
    into per-deadline records, future/past partition around a fixed `now`.

Acceptance: `pytest` green, covering the functions above. This is the checkpoint the user
asked to start from.

---

## Phase 2 — Concrete bug fixes (behavior-changing, intentional)

### Frontend
- **[Security] Stored XSS in `createConferenceCard`.** All interpolated conference fields
  (`title`, `shortname`, `location`, `note`) are injected into `innerHTML` unescaped, and
  `website` goes into an `href` unchecked. Add an `escapeHtml()` helper, escape every
  interpolated field, and validate `website` is `http(s):` before using it (drop/disable
  otherwise). Add a restrictive CSP `<meta>` as defense-in-depth.
- **[Perf] One `setInterval` per card.** Replace ~100 per-card 1s timers (each rewriting
  `innerHTML`) with a single global ticker that updates text nodes of visible cards.
- **[Perf] Full rebuild on every keystroke.** Debounce the name-filter input; avoid
  rebuilding the tag-filter buttons inside every render pass.

### Backend
- **[Bug] `for…else` in the nino block** logs "skipping ninoduarte-git" after the loop has
  already processed everything. Remove the misattached `else`.
- **[Bug] Broken console entry point.** `setup.cfg` points at `aideadlines.update_data:main`
  which doesn't exist. Provide a real `main()` (created in Phase 3) or fix the reference.
- **[Security] `os.system(f"git push https://tobna:{token}@…")`** leaks the token to the
  process list and uses shell interpolation. Switch to `subprocess` with the credential
  passed via env / git credential helper, not the command line.
- **[Bug] `logger.info(..., end=…, flush=…)`** — leftover `print` kwargs loguru ignores.
  Remove them.

---

## Phase 3 — Full backend restructure (behavior-preserving, tests stay green)

- Convert `update_data.py` and `data_to_json.py` from top-level scripts into modules with
  functions and `if __name__ == "__main__"` / `main()` entry points (also fixes the broken
  console script).
- **Dedupe the merge logic.** The off-website / hf / nino / ccf blocks are the same ~25-line
  block four times; the WACV round-detection block is duplicated four times. Extract:
  - `merge_source(conferences, new_items, src_name, reestimate_groups)`
  - `tag_wacv_round(conf)`
  Phase 1's `test_merge_priority.py` guards this.
- Remove dead `sys.path.append` hacks (proper relative imports already exist).
- Centralize timezone normalization (shared between `utils.py` and `data_to_json.py`)
  in one place instead of two divergent copies.
- Replace leap-year-ignoring `timedelta(days=365*n)` in `see_future.py` with a
  calendar-aware year shift (e.g. `relativedelta`) — guarded by the see_future tests.

---

## Phase 4 — Repo hygiene, reproducibility, docs

- **Pin dependencies** in `requirements.txt`/`setup.cfg` (especially `dateparser`, whose
  parsing changes across releases). Add a `requirements-dev.txt` (or extras) with `pytest`.
- **Remove `error.log`** from the repo and add it to `.gitignore`.
- Fix `setup.cfg` placeholders (`author = Your Name`, `you@example.com`).
- Fix typos in the API: `parse_stuff`, param `conferneces` (→ `conferences`) — done as a
  rename guarded by tests.
- **Add CI** (GitHub Actions): run `pytest` + `ruff` on push/PR. (`.ruff_cache` exists, so
  ruff is already in use locally — wire it into CI.)
- Add a **schema-validation step** before the auto-commit in `update.py`, so a malformed
  scrape can't silently land in `main`.
- **Fix `CLAUDE.md`** source-priority order to match code (`manual` highest).

---

## Out of scope (unless requested)

- Migrating the frontend to a framework/bundler — staying vanilla static is correct here.
- Rewriting the scrapers' parsing strategy.
- JS automated tests (owner chose Python-only).

## Verification per phase

- Phase 1/3/4 backend: `pytest` green.
- Phase 2 frontend: manual check — load the page, confirm XSS payloads in a test YAML render
  inert, countdowns still tick, filtering/debounce work, no console errors.
