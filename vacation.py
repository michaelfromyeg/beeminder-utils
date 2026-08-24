# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import json
import os
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

BEEMINDER_API = "https://www.beeminder.com/api/v1"

MAX_RETRIES = 3
RETRY_BACKOFF = 2

# Beeminder refuses road edits that make a goal easier before "today plus one week".
# That is the akrasia horizon, and it is the product working as intended, so a break
# can only ever be scheduled, never started today.
AKRASIA_HORIZON_DAYS = 7


def request_with_retry(req: urllib.request.Request) -> Any:
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                raise
            if attempt == MAX_RETRIES - 1:
                raise
            wait = RETRY_BACKOFF ** (attempt + 1)
            print(f"  retrying in {wait}s (HTTP {e.code})...")
            time.sleep(wait)
        except urllib.error.URLError:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = RETRY_BACKOFF ** (attempt + 1)
            print(f"  retrying in {wait}s (connection error)...")
            time.sleep(wait)


def api(method: str, path: str, data: dict[str, Any] | None = None) -> Any:
    url = f"{BEEMINDER_API}{path}"
    body = None
    if data:
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    return request_with_retry(req)


def earliest_break_start(today: date) -> date:
    return today + timedelta(days=AKRASIA_HORIZON_DAYS)


def insert_break(
    fullroad: list[list[Any]], start_ts: int, end_ts: int
) -> list[list[Any]]:
    """Road matrix for `fullroad` with a flat segment from `start_ts` to `end_ts`.

    Rows are [date, value, rate] with exactly one field null. History is emitted in
    value form so the past road is unchanged; everything from the break onwards is
    emitted in rate form, which resumes the original slopes and means the road's
    values never have to be interpolated here — Beeminder recomputes them.

    A kink falling inside the break window is swallowed by the flat segment.
    """
    rows: list[list[Any]] = [[t, v, None] for t, v, _ in fullroad if t < start_ts]
    rate_at_start = next((r for t, _, r in fullroad if t >= start_ts), fullroad[-1][2])
    rows.append([start_ts, None, rate_at_start])
    rows.append([end_ts, None, 0])
    rows.extend([t, None, r] for t, _, r in fullroad if t > end_ts)
    return rows


def day_start(day: date, tz_name: str) -> int:
    return int(
        datetime(day.year, day.month, day.day, tzinfo=ZoneInfo(tz_name)).timestamp()
    )


def main() -> None:
    token = os.environ["BEEMINDER_AUTH_TOKEN"]
    username = os.environ["BEEMINDER_USERNAME"]
    tz_name = os.environ.get("TZ_NAME", "America/Los_Angeles")
    slugs = [s.split(":")[0].strip() for s in os.environ["BEEMINDER_GOALS"].split(",")]
    days = int(os.environ.get("BREAK_DAYS", "7"))
    dry_run = os.environ.get("DRY_RUN", "1") == "1"

    today = datetime.now(ZoneInfo(tz_name)).date()
    earliest = earliest_break_start(today)
    start = (
        date.fromisoformat(os.environ["BREAK_START"])
        if os.environ.get("BREAK_START")
        else earliest
    )
    if start < earliest:
        raise SystemExit(
            f"break cannot start {start}: Beeminder refuses road edits that make a "
            f"goal easier before the akrasia horizon ({earliest}). "
            "schedule it later, or archive the goals in the Beeminder UI."
        )

    end = start + timedelta(days=days)
    start_ts, end_ts = day_start(start, tz_name), day_start(end, tz_name)
    print(f"break {start} to {end} ({days}d) for {', '.join(slugs)}")
    print("DRY RUN, nothing will be written\n" if dry_run else "")

    for slug in slugs:
        goal = api("GET", f"/users/{username}/goals/{slug}.json?auth_token={token}")
        roadall = insert_break(goal["fullroad"], start_ts, end_ts)
        print(
            f"{slug}: rate {goal['rate']}/{goal['runits']}, {len(goal['fullroad'])} "
            f"segments -> {len(roadall)}"
        )
        print(f"  {json.dumps(roadall)}")
        if not dry_run:
            api(
                "PUT",
                f"/users/{username}/goals/{slug}.json",
                {"auth_token": token, "roadall": roadall},
            )
            print("  written.")

    print("\ndone." if not dry_run else "\ndone (dry run).")


if __name__ == "__main__":
    main()
