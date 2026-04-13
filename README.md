# beeminder-utils

Automation and tooling for [Beeminder](https://www.beeminder.com).

Inspired by [this blog post](https://nickmartinovic.com/building-an-autoratchet-in-beeminder/).

## What it does

### GitHub Actions workflows

- **autoratchet** - runs daily and reduces safety buffer to a configured maximum per goal, so you can't coast on banked progress
- **habits** - syncs completed habits from a Notion database to a Beeminder goal

### MCP server

An [MCP](https://modelcontextprotocol.io/) server (`mcp_server.py`) that exposes Beeminder as tools for AI assistants like Claude Code. Supports:

- **list_goals** - overview of all goals with status, rates, and buffer
- **get_goal** - full details for a specific goal
- **get_datapoints** - recent data entries for a goal
- **create_datapoint** - add a new data entry (value, comment, date)
- **ratchet_goal** - reduce a goal's safety buffer

## Setup

### Workflows

1. Add repo secrets (`Settings > Secrets > Actions`):
   - `BEEMINDER_AUTH_TOKEN` - from https://www.beeminder.com/api/v1/auth_token.json
   - `BEEMINDER_USERNAME`
   - `NOTION_TOKEN` - from https://www.notion.so/my-integrations (for habits sync)
2. Configure in `.github/workflows/`:
   - `autoratchet.yml` - set `BEEMINDER_GOALS` and `MAX_BUFFER_DAYS`
   - `habits.yml` - set `NOTION_DATABASE_ID`, `BEEMINDER_HABITS_GOAL`, and `TZ_NAME`

`BEEMINDER_GOALS` supports per-goal buffer overrides: `"duolingo:1,lifts:3,running2:4,habits"`. Goals without a `:N` suffix use `MAX_BUFFER_DAYS` as the default. Use higher buffer for weekly goals so they keep scheduling flexibility (e.g., 3 days for 3x/week, 4 days for 2x/week).

### MCP server

1. Copy `.env.example` to `.env` and fill in `BEEMINDER_USERNAME` and `BEEMINDER_AUTH_TOKEN`.
2. Run `direnv allow` to auto-load env vars (or source `.env` manually).
3. The server is configured in `.mcp.json` and runs via `uv run mcp_server.py`.

## Development

```
make setup      # create venv, install deps for type checking
make test       # run tests
make typecheck  # run ty type checker
make lint       # run ruff linter
make format     # auto-format with ruff
make check      # lint + typecheck + format check
```

## Manual triggers

```
gh workflow run autoratchet
gh workflow run habits
```
