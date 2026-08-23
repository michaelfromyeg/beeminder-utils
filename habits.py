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
from zoneinfo import ZoneInfo

NOTION_API = "https://api.notion.com/v1"
BEEMINDER_API = "https://www.beeminder.com/api/v1"

MAX_RETRIES = 3
RETRY_BACKOFF = 2


def request_with_retry(req):
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


def notion_query(database_id, token, filter_body):
    url = f"{NOTION_API}/databases/{database_id}/query"
    body = json.dumps(filter_body).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", "2022-06-28")
    req.add_header("Content-Type", "application/json")
    return request_with_retry(req)


def current_day(tz_name):
    return datetime.now(ZoneInfo(tz_name)).date().isoformat()


def fetch_rows_due(database_id, token, day):
    """Every habit row due on `day`, following Notion's pagination."""
    rows = []
    cursor = None
    while True:
        body = {"filter": {"property": "Due", "date": {"equals": day}}}
        if cursor:
            body["start_cursor"] = cursor
        result = notion_query(database_id, token, body)
        rows.extend(result["results"])
        if not result.get("has_more"):
            return rows
        cursor = result["next_cursor"]


def count_complete(rows):
    """Rows whose Status is exactly Complete. Skipped shares Notion's "complete"
    status group but is not a completed habit, so it must not count."""
    return sum(
        1
        for row in rows
        if (row["properties"]["Status"].get("status") or {}).get("name") == "Complete"
    )


def beeminder_post_datapoint(username, goal, token, value, daystamp):
    url = f"{BEEMINDER_API}/users/{username}/goals/{goal}/datapoints.json"
    body = json.dumps(
        {
            "auth_token": token,
            "value": value,
            "daystamp": daystamp,
            "requestid": f"habits-{daystamp}",
        }
    ).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    return request_with_retry(req)


def main():
    notion_token = os.environ["NOTION_TOKEN"]
    notion_db = os.environ["NOTION_DATABASE_ID"]
    bm_token = os.environ["BEEMINDER_AUTH_TOKEN"]
    bm_username = os.environ["BEEMINDER_USERNAME"]
    bm_goal = os.environ.get("BEEMINDER_HABITS_GOAL", "habits")

    today = current_day(os.environ.get("TZ_NAME", "America/Los_Angeles"))

    print(f"querying notion for {today}...")
    rows = fetch_rows_due(notion_db, notion_token, today)

    # A revoked or wrong NOTION_TOKEN still returns 200 with zero rows, which is
    # indistinguishable from a real 0 once it reaches Beeminder — that is how this
    # sync posted 0 every hour for months without ever failing a workflow run. The
    # tracker always has rows due, so no rows means broken access, not a zero day.
    if not rows:
        raise SystemExit(
            f"no habit rows due {today}; refusing to post 0. "
            "check NOTION_TOKEN's access to the database."
        )

    count = count_complete(rows)
    print(f"{today}: {count}/{len(rows)} habits completed.")

    beeminder_post_datapoint(bm_username, bm_goal, bm_token, count, today)
    print(f"posted {count} to beeminder/{bm_goal}.")


if __name__ == "__main__":
    main()
