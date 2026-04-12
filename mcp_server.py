# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp"]
# ///

import json
import os
import urllib.request
from mcp.server.fastmcp import FastMCP

BEEMINDER_API = "https://www.beeminder.com/api/v1"

mcp = FastMCP("beeminder")

USERNAME = os.environ.get("BEEMINDER_USERNAME", "")
TOKEN = os.environ.get("BEEMINDER_AUTH_TOKEN", "")


def api(method, path, data=None):
    url = f"{BEEMINDER_API}{path}"
    if "?" in url:
        url += f"&auth_token={TOKEN}"
    else:
        url += f"?auth_token={TOKEN}"
    body = None
    if data:
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def summarize_goal(g):
    return {
        "slug": g["slug"],
        "title": g.get("title", ""),
        "goal_type": g.get("goal_type"),
        "rate": g.get("rate"),
        "runits": g.get("runits"),
        "curval": g.get("curval"),
        "safebuf": g.get("safebuf"),
        "pledge": g.get("pledge"),
        "losedate": g.get("losedate"),
        "limsum": g.get("limsum"),
    }


@mcp.tool()
def list_goals() -> str:
    """List all goals with their current status."""
    goals = api("GET", f"/users/{USERNAME}/goals.json")
    return json.dumps([summarize_goal(g) for g in goals], indent=2)


@mcp.tool()
def get_goal(goal_slug: str) -> str:
    """Get full details for a specific goal."""
    goal = api("GET", f"/users/{USERNAME}/goals/{goal_slug}.json")
    return json.dumps(goal, indent=2)


@mcp.tool()
def get_datapoints(goal_slug: str, count: int = 10) -> str:
    """Get recent datapoints for a goal."""
    points = api(
        "GET",
        f"/users/{USERNAME}/goals/{goal_slug}/datapoints.json?sort=daystamp&count={count}",
    )
    return json.dumps(points, indent=2)


@mcp.tool()
def create_datapoint(
    goal_slug: str,
    value: float,
    comment: str = "",
    daystamp: str = "",
) -> str:
    """Add a datapoint to a goal. Daystamp format: YYYY-MM-DD (defaults to today)."""
    data = {"value": value, "auth_token": TOKEN}
    if comment:
        data["comment"] = comment
    if daystamp:
        data["daystamp"] = daystamp
    point = api(
        "POST",
        f"/users/{USERNAME}/goals/{goal_slug}/datapoints.json",
        data,
    )
    return json.dumps(point, indent=2)


@mcp.tool()
def ratchet_goal(goal_slug: str, max_safe_days: int = 1) -> str:
    """Ratchet a goal to reduce safety buffer to the given number of days."""
    data = {"auth_token": TOKEN, "newsafety": max_safe_days}
    if max_safe_days == 0:
        data["beemergency"] = True
    result = api(
        "POST",
        f"/users/{USERNAME}/goals/{goal_slug}/ratchet.json",
        data,
    )
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
