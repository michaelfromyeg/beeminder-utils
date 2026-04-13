import json
from unittest.mock import patch

from mcp_server import (
    summarize_goal,
    list_goals,
    get_goal,
    get_datapoints,
    create_datapoint,
    ratchet_goal,
)

SAMPLE_GOAL = {
    "slug": "lifts",
    "title": "Lift weights",
    "goal_type": "hustler",
    "rate": 0.43,
    "runits": "d",
    "curval": 11,
    "safebuf": 3,
    "pledge": 5.0,
    "losedate": 1776063599,
    "limsum": "+1 in 3 days",
    "extra_field": "should be excluded",
}


def test_summarize_goal():
    result = summarize_goal(SAMPLE_GOAL)
    assert result["slug"] == "lifts"
    assert result["safebuf"] == 3
    assert "extra_field" not in result


@patch("mcp_server.api")
def test_list_goals(mock_api):
    mock_api.return_value = [SAMPLE_GOAL]
    result = json.loads(list_goals())
    assert len(result) == 1
    assert result[0]["slug"] == "lifts"
    assert "extra_field" not in result[0]


@patch("mcp_server.api")
def test_get_goal(mock_api):
    mock_api.return_value = SAMPLE_GOAL
    result = json.loads(get_goal("lifts"))
    assert result["slug"] == "lifts"
    mock_api.assert_called_once()
    assert "/goals/lifts.json" in mock_api.call_args[0][1]


@patch("mcp_server.api")
def test_get_datapoints(mock_api):
    points = [{"value": 1, "daystamp": "20260411"}]
    mock_api.return_value = points
    result = json.loads(get_datapoints("lifts", count=5))
    assert len(result) == 1
    assert "count=5" in mock_api.call_args[0][1]


@patch("mcp_server.api")
def test_create_datapoint(mock_api):
    mock_api.return_value = {"id": "abc", "value": 1.0, "status": "created"}
    result = json.loads(
        create_datapoint("lifts", 1.0, comment="test", daystamp="2026-04-12")
    )
    assert result["status"] == "created"
    call_data = mock_api.call_args[0][2]
    assert call_data["value"] == 1.0
    assert call_data["comment"] == "test"
    assert call_data["daystamp"] == "2026-04-12"


@patch("mcp_server.api")
def test_ratchet_goal(mock_api):
    mock_api.return_value = {"slug": "lifts"}
    result = json.loads(ratchet_goal("lifts", max_safe_days=3))
    assert result["slug"] == "lifts"
    call_data = mock_api.call_args[0][2]
    assert call_data["newsafety"] == 3
    assert "beemergency" not in call_data


@patch("mcp_server.api")
def test_ratchet_goal_beemergency(mock_api):
    mock_api.return_value = {"slug": "lifts"}
    ratchet_goal("lifts", max_safe_days=0)
    call_data = mock_api.call_args[0][2]
    assert call_data["newsafety"] == 0
    assert call_data["beemergency"] is True
