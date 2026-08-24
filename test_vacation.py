from datetime import date

import pytest

from vacation import earliest_break_start, insert_break

# Fixed timestamps standing in for road dates, one day apart
DAY = 86400
JAN01 = 1767254400
JAN08 = JAN01 + 7 * DAY
JAN15 = JAN01 + 14 * DAY
JAN22 = JAN01 + 21 * DAY


def test_earliest_break_start_is_a_week_out():
    assert earliest_break_start(date(2026, 8, 23)) == date(2026, 8, 30)


def test_insert_break_flattens_the_window():
    fullroad = [[JAN01, 100.0, 0.0], [JAN22, 121.0, 1.0]]

    roadall = insert_break(fullroad, JAN08, JAN15)

    assert roadall == [
        [JAN01, 100.0, None],
        [JAN08, None, 1.0],
        [JAN15, None, 0],
        [JAN22, None, 1.0],
    ]


def test_insert_break_keeps_history_in_value_form():
    # Past rows carry their values so the road behind us is provably unchanged
    fullroad = [[JAN01, 100.0, 0.0], [JAN08, 107.0, 1.0], [JAN22, 121.0, 1.0]]

    roadall = insert_break(fullroad, JAN15, JAN22)

    assert roadall[0] == [JAN01, 100.0, None]
    assert roadall[1] == [JAN08, 107.0, None]


def test_insert_break_uses_the_rate_of_the_segment_it_starts_in():
    # The break starts inside the 2.5/day segment, so the road must run at 2.5 up to it
    fullroad = [[JAN01, 100.0, 0.0], [JAN15, 135.0, 2.5], [JAN22, 142.0, 1.0]]

    roadall = insert_break(fullroad, JAN08, JAN15)

    assert roadall[1] == [JAN08, None, 2.5]


def test_insert_break_swallows_a_kink_inside_the_window():
    fullroad = [[JAN01, 100.0, 0.0], [JAN15, 114.0, 1.0], [JAN22, 128.0, 2.0]]

    roadall = insert_break(fullroad, JAN08, JAN22)

    assert roadall == [
        [JAN01, 100.0, None],
        [JAN08, None, 1.0],
        [JAN22, None, 0],
    ]


def test_insert_break_past_the_end_of_the_road_extends_at_the_final_rate():
    fullroad = [[JAN01, 100.0, 0.0], [JAN08, 107.0, 1.0]]

    roadall = insert_break(fullroad, JAN15, JAN22)

    assert roadall == [
        [JAN01, 100.0, None],
        [JAN08, 107.0, None],
        [JAN15, None, 1.0],
        [JAN22, None, 0],
    ]


def test_insert_break_rows_have_exactly_one_null_each():
    fullroad = [[JAN01, 100.0, 0.0], [JAN15, 114.0, 1.0], [JAN22, 128.0, 2.0]]

    roadall = insert_break(fullroad, JAN08, JAN15)

    for row in roadall:
        assert sum(1 for field in row if field is None) == 1


def test_main_refuses_a_break_inside_the_akrasia_horizon(monkeypatch, capsys):
    monkeypatch.setenv("BEEMINDER_AUTH_TOKEN", "tok")
    monkeypatch.setenv("BEEMINDER_USERNAME", "user")
    monkeypatch.setenv("BEEMINDER_GOALS", "duolingo:0")
    monkeypatch.setenv("BREAK_START", "2020-01-01")
    from vacation import main

    with pytest.raises(SystemExit, match="akrasia horizon"):
        main()
