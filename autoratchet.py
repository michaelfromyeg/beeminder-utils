# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import json
import os
import time
import urllib.error
import urllib.request

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


def api(method, path, data=None):
    url = f"{BEEMINDER_API}{path}"
    body = None
    if data:
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    return request_with_retry(req)


def main():
    token = os.environ["BEEMINDER_AUTH_TOKEN"]
    username = os.environ["BEEMINDER_USERNAME"]
    max_buffer = int(os.environ.get("MAX_BUFFER_DAYS", "1"))
    goals_filter = os.environ.get("BEEMINDER_GOALS", "")
    goal_slugs = [s.strip() for s in goals_filter.split(",") if s.strip()]

    if goal_slugs:
        goals = [
            api("GET", f"/users/{username}/goals/{slug}.json?auth_token={token}")
            for slug in goal_slugs
        ]
    else:
        goals = api("GET", f"/users/{username}/goals.json?auth_token={token}")

    for goal in goals:
        slug = goal["slug"]
        safebuf = goal.get("safebuf", 0)

        if safebuf <= max_buffer:
            print(f"{slug}: safebuf={safebuf}, within limit. skipping.")
            continue

        print(f"{slug}: safebuf={safebuf}, ratcheting to {max_buffer}.")
        data = {"auth_token": token, "newsafety": max_buffer}
        if max_buffer == 0:
            data["beemergency"] = True
        api("POST", f"/users/{username}/goals/{slug}/ratchet.json", data)

    print("done.")


if __name__ == "__main__":
    main()
