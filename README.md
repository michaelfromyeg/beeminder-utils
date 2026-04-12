# beeminder-utils

GitHub Actions workflows for [Beeminder](https://www.beeminder.com) automation.

Inspired by [this blog post](https://nickmartinovic.com/building-an-autoratchet-in-beeminder/).

## What it does

- **autoratchet** - runs daily and reduces safety buffer to a configured maximum, so you can't coast on banked progress
- **habits** - syncs completed habits from a Notion database to a Beeminder goal

## Setup

1. Add repo secrets (`Settings > Secrets > Actions`):
   - `BEEMINDER_AUTH_TOKEN` - from https://www.beeminder.com/api/v1/auth_token.json
   - `BEEMINDER_USERNAME`
   - `NOTION_TOKEN` - from https://www.notion.so/my-integrations (for habits sync)
2. Configure in `.github/workflows/`:
   - `autoratchet.yml` - set `BEEMINDER_GOALS` and `MAX_BUFFER_DAYS`
   - `habits.yml` - set `NOTION_DATABASE_ID`, `BEEMINDER_HABITS_GOAL`, and `TZ_NAME`

## Manual triggers

```
gh workflow run autoratchet
gh workflow run habits
```
