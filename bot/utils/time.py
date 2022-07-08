from datetime import timedelta

import arrow


def next_time_occurence(hour: int, minute: int = 0, second: int = 0) -> arrow.Arrow:
    """Return an Arrow for the next occurence of the given time of day."""
    delta = time_until(hour, minute, second)
    return arrow.get() + delta


def time_until(hour: int, minute: int = 0, second: int = 0) -> timedelta:
    """Return the difference between now and the next occurence of the given time of day in UTC."""
    now = arrow.get()
    time_today = now.replace(hour=hour, minute=minute, second=second)
    delta = time_today - now
    return delta % timedelta(days=1)
