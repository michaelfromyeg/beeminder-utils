from unittest.mock import patch, call
from autoratchet import parse_goals_config, main


def test_parse_with_per_goal_buffer():
    result = parse_goals_config("duolingo:1,lifts:3,running2:4", default_buffer=1)
    assert result == {"duolingo": 1, "lifts": 3, "running2": 4}


def test_parse_with_default_buffer():
    result = parse_goals_config("duolingo,headspace", default_buffer=2)
    assert result == {"duolingo": 2, "headspace": 2}


def test_parse_mixed():
    result = parse_goals_config("duolingo:1,lifts:3,habits", default_buffer=1)
    assert result == {"duolingo": 1, "lifts": 3, "habits": 1}


def test_parse_empty_string():
    assert parse_goals_config("", default_buffer=1) == {}


def test_parse_whitespace():
    result = parse_goals_config(" duolingo : 2 , lifts : 3 ", default_buffer=1)
    assert result == {"duolingo": 2, "lifts": 3}


@patch("autoratchet.api")
def test_main_skips_within_limit(mock_api, monkeypatch):
    monkeypatch.setenv("BEEMINDER_AUTH_TOKEN", "tok")
    monkeypatch.setenv("BEEMINDER_USERNAME", "user")
    monkeypatch.setenv("BEEMINDER_GOALS", "lifts:3")

    mock_api.return_value = {"slug": "lifts", "safebuf": 2}

    main()

    # Only the GET call, no ratchet POST
    assert mock_api.call_count == 1
    assert mock_api.call_args_list[0] == call(
        "GET", "/users/user/goals/lifts.json?auth_token=tok"
    )


@patch("autoratchet.api")
def test_main_ratchets_when_over_limit(mock_api, monkeypatch):
    monkeypatch.setenv("BEEMINDER_AUTH_TOKEN", "tok")
    monkeypatch.setenv("BEEMINDER_USERNAME", "user")
    monkeypatch.setenv("BEEMINDER_GOALS", "lifts:3")

    mock_api.return_value = {"slug": "lifts", "safebuf": 6}

    main()

    assert mock_api.call_count == 2
    assert mock_api.call_args_list[1] == call(
        "POST",
        "/users/user/goals/lifts/ratchet.json",
        {"auth_token": "tok", "newsafety": 3},
    )


@patch("autoratchet.api")
def test_main_per_goal_buffers(mock_api, monkeypatch):
    monkeypatch.setenv("BEEMINDER_AUTH_TOKEN", "tok")
    monkeypatch.setenv("BEEMINDER_USERNAME", "user")
    monkeypatch.setenv("BEEMINDER_GOALS", "duolingo:1,lifts:3")

    mock_api.side_effect = [
        {"slug": "duolingo", "safebuf": 5},  # GET duolingo
        {"slug": "lifts", "safebuf": 2},  # GET lifts
        {},  # POST ratchet duolingo
    ]

    main()

    assert mock_api.call_count == 3
    # duolingo (safebuf 5 > 1) gets ratcheted
    assert mock_api.call_args_list[2] == call(
        "POST",
        "/users/user/goals/duolingo/ratchet.json",
        {"auth_token": "tok", "newsafety": 1},
    )
    # lifts (safebuf 2 <= 3) was not ratcheted — only 3 calls total
