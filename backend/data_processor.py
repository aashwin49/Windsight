from collections import defaultdict
from datetime import datetime, timezone
from select_forecasts import normalize_timestamp


def aggregate_actuals_hourly(records):
    """
    Aggregate half-hourly actual wind generation into hourly averages.

    generation is measured in average MW, so the hourly value is
    the average of the two half-hourly MW readings.
    """
    hourly_groups = defaultdict(list)

    by_timestamp = {}
    for record in records:
        start_time = normalize_timestamp(record["startTime"])
        key = start_time
        existing = by_timestamp.get(key)
        if existing is not None:
            if existing != record:
                raise ValueError(f"Conflicting actual records at {record['startTime']}")
            continue
        by_timestamp[key] = record

        # Both 12:00 and 12:30 belong to the 12:00 hourly period.
        hour_start = start_time.replace(minute=0, second=0, microsecond=0)

        hourly_groups[hour_start].append(record["generation"])

    hourly_actuals = []

    for hour_start, values in sorted(hourly_groups.items()):
        valid_values = [value for value in values if value is not None]

        # An hourly period must contain both half-hourly readings.
        if len(values) != 2 or len(valid_values) != 2:
            generation = None
            is_complete = False
        else:
            generation = sum(valid_values) / 2
            is_complete = True

        hourly_actuals.append({
            "startTime": hour_start.isoformat().replace("+00:00", "Z"),
            "generation": generation,
            "is_complete": is_complete,
            "source_records": len(values)
        })

    return hourly_actuals


def match_forecasts_with_actuals(forecasts, actuals):
    """
    Match hourly forecasts with hourly actual generation.
    Error = Forecast - Actual.
    """

    # Detect duplicate timestamps
    check_duplicate_timestamps(forecasts, "forecasts")
    check_duplicate_timestamps(actuals, "actuals")

    # Create lookup dictionaries
    forecast_lookup = {normalize_timestamp(record["startTime"]): record for record in forecasts}
    actual_lookup = {normalize_timestamp(record["startTime"]): record for record in actuals}

    # Combine all delivery timestamps
    all_times = sorted(
        set(forecast_lookup) | set(actual_lookup)
    )

    matched_records = []

    for start_time in all_times:

        forecast = forecast_lookup.get(start_time)
        actual = actual_lookup.get(start_time)

        forecast_generation = (
            forecast.get("generation")
            if forecast is not None else None
        )

        actual_generation = (
            actual.get("generation")
            if actual is not None else None
        )

        # Check whether hourly actual data is complete
        actual_incomplete = (
            actual is not None
            and not actual.get("is_complete", True)
        )

        forecast_missing = (
            forecast is None or forecast_generation is None
        )

        actual_missing = (
            actual is None
            or actual_generation is None
            or actual_incomplete
        )

        # Calculate error only when both values are valid
        if not forecast_missing and not actual_missing:
            error = forecast_generation - actual_generation
        else:
            error = None

        matched_records.append({
            "startTime": start_time.isoformat().replace("+00:00", "Z"),
            "forecast_generation": forecast_generation,
            "actual_generation": actual_generation,
            "error": error,
            "forecast_missing": forecast_missing,
            "actual_missing": actual_missing,
            "actual_incomplete": actual_incomplete
        })

    return matched_records


def check_duplicate_timestamps(records, dataset_name):
    """
    Identify duplicate startTime values in a dataset.
    Raise an error if duplicates are found.
    """

    seen = {}
    duplicates = set()

    for record in records:
        start_time = normalize_timestamp(record["startTime"])
        if start_time in seen:
            if seen[start_time] != record:
                duplicates.add(start_time.isoformat())
        else:
            seen[start_time] = record

    if duplicates:
        raise ValueError(
            f"Duplicate timestamps found in {dataset_name}: "
            f"{sorted(duplicates)}"
        )

    return True
