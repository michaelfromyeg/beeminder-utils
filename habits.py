# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import json
import os
import time
import urllib.error
import urllib.request
from datetime import date

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

    today = date.today().isoformat()

    print(f"querying notion for {today}...")
    result = notion_query(
        notion_db,
        notion_token,
        {
            "filter": {
                "and": [
                    {"property": "Due", "date": {"equals": today}},
                    {"property": "Status", "status": {"equals": "Complete"}},
                ]
            }
        },
    )

    count = len(result["results"])
    print(f"{today}: {count} habits completed.")

    beeminder_post_datapoint(bm_username, bm_goal, bm_token, count, today)
    print(f"posted {count} to beeminder/{bm_goal}.")


if __name__ == "__main__":
    main()
