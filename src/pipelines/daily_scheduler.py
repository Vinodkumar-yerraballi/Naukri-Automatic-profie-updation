import logging
import time
from datetime import datetime, time as time_of_day, timedelta
from zoneinfo import ZoneInfo


def next_run_time(
    now: datetime,
    run_at: time_of_day,
    timezone: ZoneInfo,
) -> datetime:
    """Return the next scheduled local time, strictly after ``now``."""
    local_now = now.astimezone(timezone)
    next_run = local_now.replace(
        hour=run_at.hour,
        minute=run_at.minute,
        second=0,
        microsecond=0,
    )
    if next_run <= local_now:
        next_run += timedelta(days=1)
    return next_run


def run_daily(task, run_at: str, timezone_name: str) -> None:
    """Run a task every day at an HH:MM time in the named timezone."""
    try:
        scheduled_time = time_of_day.fromisoformat(run_at)
    except ValueError as error:
        raise ValueError("Schedule time must use HH:MM format.") from error
    timezone = ZoneInfo(timezone_name)

    while True:
        scheduled_run = next_run_time(
            datetime.now(timezone), scheduled_time, timezone
        )
        delay = max(0.0, (scheduled_run - datetime.now(timezone)).total_seconds())
        print(
            f"Next job and resume-draft run: "
            f"{scheduled_run.isoformat(timespec='minutes')}"
        )
        time.sleep(delay)
        try:
            task()
        except Exception:
            logging.exception("Scheduled job and resume-draft run failed.")
