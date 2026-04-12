# beeminder-utils

Beeminder automation: GitHub Actions workflows + an MCP server.

## Structure

- `mcp_server.py` - MCP server exposing Beeminder API tools (list/get goals, datapoints, ratchet)
- `.mcp.json` - MCP server config for Claude Code (uses `uv run`)
- `.github/workflows/autoratchet.yml` - daily autoratchet workflow
- `.github/workflows/habits.yml` - Notion-to-Beeminder habits sync workflow
- `.env.example` - required env vars template

## Running

- MCP server: `uv run mcp_server.py` (needs `BEEMINDER_USERNAME` and `BEEMINDER_AUTH_TOKEN` in env)
- Workflows run on schedule via GitHub Actions or manually with `gh workflow run`
- Uses `direnv` to auto-load `.env` — run `direnv allow` after cloning

## Dependencies

- Python 3.12+, managed via `uv`
- MCP server uses inline script metadata (`# /// script`) for deps — no requirements file needed
- `direnv` for environment variable management
