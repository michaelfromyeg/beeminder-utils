from unittest.mock import call, patch

import pytest

from habits import count_complete, fetch_rows_due, main


def row(status):
    """A Notion query result row, with only the properties habits.py reads."""
    return {"properties": {"Status": {"status": {"name": status} if status else None}}}


def test_count_complete_counts_complete_rows():
    rows = [row("Complete"), row("To-do"), row("Complete")]
    assert count_complete(rows) == 2


def test_count_complete_ignores_skipped():
    # Skipped sits in Notion's "complete" status group but is not a completed habit
    rows = [row("Complete"), row("Skipped"), row("Skipped")]
    assert count_complete(rows) == 1


def test_count_complete_ignores_empty_status():
    rows = [row("Complete"), row(None)]
    assert count_complete(rows) == 1


@patch("habits.notion_query")
def test_fetch_rows_due_filters_on_the_given_day(mock_query):
    mock_query.return_value = {"results": [row("Complete")], "has_more": False}

    fetch_rows_due("db123", "tok", "2026-08-23")

    assert mock_query.call_args_list == [
        call(
            "db123",
            "tok",
            {"filter": {"property": "Due", "date": {"equals": "2026-08-23"}}},
        )
    ]


@patch("habits.notion_query")
def test_fetch_rows_due_follows_pagination(mock_query):
    mock_query.side_effect = [
        {"results": [row("Complete")], "has_more": True, "next_cursor": "cur1"},
        {"results": [row("To-do"), row("Complete")], "has_more": False},
    ]

    rows = fetch_rows_due("db123", "tok", "2026-08-23")

    assert len(rows) == 3
    assert mock_query.call_args_list[1] == call(
        "db123",
        "tok",
        {
            "filter": {"property": "Due", "date": {"equals": "2026-08-23"}},
            "start_cursor": "cur1",
        },
    )


@patch("habits.beeminder_post_datapoint")
@patch("habits.notion_query")
@patch("habits.current_day")
def test_main_posts_the_completed_count(mock_day, mock_query, mock_post, monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "ntok")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db123")
    monkeypatch.setenv("BEEMINDER_AUTH_TOKEN", "btok")
    monkeypatch.setenv("BEEMINDER_USERNAME", "user")
    mock_day.return_value = "2026-08-23"
    mock_query.return_value = {
        "results": [row("Complete"), row("Complete"), row("To-do"), row("Skipped")],
        "has_more": False,
    }

    main()

    assert mock_post.call_args_list == [call("user", "habits", "btok", 2, "2026-08-23")]


@patch("habits.beeminder_post_datapoint")
@patch("habits.notion_query")
@patch("habits.current_day")
def test_main_refuses_to_post_when_no_rows_are_due(
    mock_day, mock_query, mock_post, monkeypatch
):
    # A revoked NOTION_TOKEN returns 200 with zero rows; posting that 0 would derail
    # the goal, so the run must fail loudly instead
    monkeypatch.setenv("NOTION_TOKEN", "revoked")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db123")
    monkeypatch.setenv("BEEMINDER_AUTH_TOKEN", "btok")
    monkeypatch.setenv("BEEMINDER_USERNAME", "user")
    mock_day.return_value = "2026-08-23"
    mock_query.return_value = {"results": [], "has_more": False}

    with pytest.raises(SystemExit, match="refusing to post 0"):
        main()

    assert mock_post.call_count == 0


@patch("habits.beeminder_post_datapoint")
@patch("habits.notion_query")
@patch("habits.current_day")
def test_main_posts_zero_when_rows_are_due_but_none_complete(
    mock_day, mock_query, mock_post, monkeypatch
):
    monkeypatch.setenv("NOTION_TOKEN", "ntok")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db123")
    monkeypatch.setenv("BEEMINDER_AUTH_TOKEN", "btok")
    monkeypatch.setenv("BEEMINDER_USERNAME", "user")
    mock_day.return_value = "2026-08-23"
    mock_query.return_value = {
        "results": [row("To-do"), row("Missed")],
        "has_more": False,
    }

    main()

    assert mock_post.call_args_list == [call("user", "habits", "btok", 0, "2026-08-23")]


@patch("habits.beeminder_post_datapoint")
@patch("habits.notion_query")
@patch("habits.current_day")
def test_main_honours_the_habits_goal_override(
    mock_day, mock_query, mock_post, monkeypatch
):
    monkeypatch.setenv("NOTION_TOKEN", "ntok")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db123")
    monkeypatch.setenv("BEEMINDER_AUTH_TOKEN", "btok")
    monkeypatch.setenv("BEEMINDER_USERNAME", "user")
    monkeypatch.setenv("BEEMINDER_HABITS_GOAL", "habits2")
    mock_day.return_value = "2026-08-23"
    mock_query.return_value = {"results": [row("Complete")], "has_more": False}

    main()

    assert mock_post.call_args_list == [
        call("user", "habits2", "btok", 1, "2026-08-23")
    ]
