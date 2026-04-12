# autoratchet

A GitHub Actions workflow that autoratchets [Beeminder](https://www.beeminder.com) goals. Runs daily and reduces safety buffer to a configured maximum, so you can't coast on banked progress.

Inspired by [this blog post](https://nickmartinovic.com/building-an-autoratchet-in-beeminder/).

## Setup

1. Add repo secrets (`Settings > Secrets > Actions`):
   - `BEEMINDER_AUTH_TOKEN` — from https://www.beeminder.com/api/v1/auth_token.json
   - `BEEMINDER_USERNAME`
2. Configure goals and buffer in `.github/workflows/autoratchet.yml`:
   - `BEEMINDER_GOALS` — comma-separated goal slugs (leave empty for all goals)
   - `MAX_BUFFER_DAYS` — max safety buffer before ratcheting (default: 1)
3. Adjust the cron schedule as needed (default: daily at 9am UTC)

## Manual trigger

```
gh workflow run autoratchet
```
