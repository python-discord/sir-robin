from datetime import timedelta

import arrow


def time_until(hour: int, minute: int = 0, second: int = 0) -> timedelta:
    """Return the difference between now and the next occurence of the given time of day in UTC."""
    now = arrow.get()
    time_today = now.replace(hour=hour, minute=minute, second=second)
    delta = time_today - now
    return delta % timedelta(days=1)
