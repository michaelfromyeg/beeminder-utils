# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# beeminder-utils

Beeminder automation: two standalone scripts run as scheduled GitHub Actions, plus an MCP server for interactive use.

## Commands

```
make setup      # create .venv, install mcp (for typecheck only)
make test       # uv run --with pytest --with mcp pytest -v
make lint       # ruff check
make format     # ruff format
make typecheck  # ty check
make check      # lint + typecheck + format --check
make run        # uv run autoratchet.py (needs env vars set)
```

Run a single test: `uv run --with pytest --with mcp pytest test_autoratchet.py::test_parse_mixed -v`

Trigger workflows manually: `gh workflow run autoratchet` / `gh workflow run habits`

## Architecture

Three entry points, each a standalone `uv run` script with inline PEP 723 metadata (`# /// script`) — no shared package, no requirements file:

- `autoratchet.py` — for each configured goal, reads `safebuf` and ratchets down to the goal's max-buffer if over. Scheduled daily.
- `habits.py` — counts Notion DB rows due today with Status=Complete, posts the count as one datapoint to a Beeminder goal. Scheduled hourly (so a run always lands near midnight PT regardless of DST, and intraday completions sync within the hour). Autoratchet runs once daily and ratchets the `habits` goal, so it must run *after* a habits run — the hourly cadence guarantees this.
- `mcp_server.py` — FastMCP server exposing list/get goals, datapoints, and ratchet as tools. Configured in `.mcp.json` via `uv run`.

`.github/workflows/keepalive.yml` has no script: GitHub disables a repo's scheduled workflows after 60 days with no pushes and never re-enables them, so it runs twice a month to push an empty commit when the repo has been quiet for 45+ days and to re-enable anything already disabled. Without it the schedules silently stop (this is how `habits` went dark for 9 days in Aug 2026).

Each script reimplements its own Beeminder `api()` helper and (for the two workflow scripts) an identical `request_with_retry` (3 retries with exponential backoff on 5xx/429/connection errors). This duplication is intentional — keeping each script self-contained so `uv run <file>.py` works with zero project setup. If you change retry or API-call behavior, update all copies.

Beeminder auth is via `?auth_token=` query param (GET) or `auth_token` in the JSON body (POST). `ratchet.json` with `newsafety=0` also requires `beemergency: true`.

`habits.py` sends a stable `requestid` (`habits-<daystamp>`) so re-running the same day overwrites rather than duplicates the datapoint — the sync is idempotent.

## Config

`BEEMINDER_GOALS` (autoratchet) is a comma list with optional per-goal buffer overrides: `"duolingo:1,lifts:3,running2:4,habits"`. Entries without `:N` fall back to `MAX_BUFFER_DAYS`. Higher buffers suit lower-frequency goals (e.g. 4 for a 2x/week goal) to preserve scheduling flexibility. Live values live in `.github/workflows/autoratchet.yml`; this is the source of truth for which goals are managed.

Env vars: `BEEMINDER_USERNAME`, `BEEMINDER_AUTH_TOKEN` (all); `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `BEEMINDER_HABITS_GOAL`, `TZ_NAME` (habits). Workflows read these from repo secrets/workflow env; local runs use `.env` auto-loaded by `direnv` (run `direnv allow` after cloning).

## Conventions

- Python 3.12+, managed by `uv`. No dependencies beyond stdlib except `mcp` (server only).
- Tests mock the `api()` function and assert on exact call args (method, path, body) — match that style when adding tests.
