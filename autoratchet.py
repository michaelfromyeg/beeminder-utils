# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import json
import os
import urllib.request

BEEMINDER_API = "https://www.beeminder.com/api/v1"


def api(method, path, data=None):
    url = f"{BEEMINDER_API}{path}"
    body = None
    if data:
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


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
