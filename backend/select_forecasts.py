
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


UK_TIMEZONE = ZoneInfo("Europe/London")


def normalize_timestamp(value):
    """Parse an ISO timestamp and return an aware UTC datetime."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UK_TIMEZONE)
    return parsed.astimezone(timezone.utc)


def calculate_cutoff(delivery_time, cutoff_hour=12):
    """
    Calculate the decision cutoff:
    noon UK local time on the day before delivery.
    """

    delivery_datetime = normalize_timestamp(delivery_time).astimezone(UK_TIMEZONE)

    previous_day = delivery_datetime.date() - timedelta(days=1)

    cutoff = datetime(
        previous_day.year,
        previous_day.month,
        previous_day.day,
        cutoff_hour,
        0,
        tzinfo=UK_TIMEZONE
    )

    return cutoff


def select_latest_forecast(forecasts, delivery_time, cutoff_hour=12, decision_cutoff=None):
    """
    Select the latest forecast published at or before
    the decision cutoff.
    """

    cutoff = (normalize_timestamp(decision_cutoff) if decision_cutoff is not None
              else calculate_cutoff(delivery_time, cutoff_hour).astimezone(timezone.utc))
    delivery_utc = normalize_timestamp(delivery_time)

    by_publish = {}
    seen_records = set()

    for record in forecasts:

        if normalize_timestamp(record["startTime"]) != delivery_utc:
            continue
        publish_time = normalize_timestamp(record["publishTime"])
        if publish_time <= cutoff:
            identity = (publish_time, record.get("generation"))
            # Exact duplicate records do not affect selection.
            frozen = tuple(sorted(record.items()))
            if frozen in seen_records:
                continue
            seen_records.add(frozen)
            previous = by_publish.get(publish_time)
            if previous is not None and previous.get("generation") != record.get("generation"):
                raise ValueError(
                    "Conflicting forecasts for startTime "
                    f"{delivery_time} at publishTime {record['publishTime']}"
                )
            by_publish[publish_time] = record

    if not by_publish:
        return None
    return by_publish[max(by_publish)]
