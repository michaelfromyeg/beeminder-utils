# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

BEEMINDER_API = "https://www.beeminder.com/api/v1"

MAX_RETRIES = 3
RETRY_BACKOFF = 2


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


def parse_goals_config(goals_str: str, default_buffer: int) -> dict[str, int]:
    """Parse goals config like 'duolingo:1,lifts:3,running2' into {slug: max_buffer}."""
    config: dict[str, int] = {}
    for entry in goals_str.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            slug, buf = entry.split(":", 1)
            config[slug.strip()] = int(buf.strip())
        else:
            config[entry] = default_buffer
    return config


def local_hour(tz_name: str) -> int:
    return datetime.now(ZoneInfo(tz_name)).hour


def main() -> None:
    # Cron is UTC, so a fixed daily UTC time drifts across the local midnight twice a
    # year: "5 7 * * *" was 00:05 PDT but 23:05 PST, i.e. it would have ratcheted the
    # *previous* day. Instead the workflow fires hourly and only the first hour of the
    # local day does the work, which is DST-proof and survives a move to another zone
    # (set TZ_NAME). Ratcheting later in the day would be worse than useless: work
    # already logged that morning earns a day of buffer, and a same-day ratchet to 0
    # would take it away and demand the work twice.
    tz_name = os.environ.get("TZ_NAME", "America/Los_Angeles")
    if os.environ.get("FORCE") != "1":
        hour = local_hour(tz_name)
        if hour != 0:
            print(f"{hour:02d}:xx in {tz_name}, not the start of the day. skipping.")
            return

    token = os.environ["BEEMINDER_AUTH_TOKEN"]
    username = os.environ["BEEMINDER_USERNAME"]
    max_buffer = int(os.environ.get("MAX_BUFFER_DAYS", "1"))
    goals_config = parse_goals_config(os.environ.get("BEEMINDER_GOALS", ""), max_buffer)

    if goals_config:
        goals = [
            (
                api(
                    "GET",
                    f"/users/{username}/goals/{slug}.json?auth_token={token}",
                ),
                buf,
            )
            for slug, buf in goals_config.items()
        ]
    else:
        goals = [
            (g, max_buffer)
            for g in api("GET", f"/users/{username}/goals.json?auth_token={token}")
        ]

    for goal, goal_max_buffer in goals:
        slug = goal["slug"]
        safebuf = goal.get("safebuf", 0)

        if safebuf <= goal_max_buffer:
            print(
                f"{slug}: safebuf={safebuf}, within limit ({goal_max_buffer}). skipping."
            )
            continue

        print(f"{slug}: safebuf={safebuf}, ratcheting to {goal_max_buffer}.")
        data = {"auth_token": token, "newsafety": goal_max_buffer}
        if goal_max_buffer == 0:
            data["beemergency"] = True
        api("POST", f"/users/{username}/goals/{slug}/ratchet.json", data)

    print("done.")


if __name__ == "__main__":
    main()
