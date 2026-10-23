from datetime import datetime, time
from zoneinfo import ZoneInfo

from src.pipelines.daily_scheduler import next_run_time


def test_next_run_time_is_later_today():
    timezone = ZoneInfo("Asia/Kolkata")
    now = datetime(2026, 10, 22, 8, 0, tzinfo=timezone)

    result = next_run_time(now, time(9, 30), timezone)

    assert result == datetime(2026, 10, 22, 9, 30, tzinfo=timezone)


def test_next_run_time_moves_to_tomorrow_after_schedule():
    timezone = ZoneInfo("Asia/Kolkata")
    now = datetime(2026, 10, 22, 9, 30, tzinfo=timezone)

    result = next_run_time(now, time(9, 30), timezone)

    assert result == datetime(2026, 10, 23, 9, 30, tzinfo=timezone)
