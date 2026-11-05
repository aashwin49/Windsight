import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forecast_selector import calculate_cutoff, select_latest_forecast


DELIVERY = "2026-01-15T12:00:00Z"


def item(publish, generation=1):
    return {"startTime": DELIVERY, "publishTime": publish, "generation": generation}


def test_selects_latest_eligible_forecast():
    records = [item("2026-01-14T10:00:00Z"), item("2026-01-14T11:30:00Z", 2), item("2026-01-14T15:30:00Z", 3)]
    assert select_latest_forecast(records, DELIVERY)["generation"] == 2


def test_excludes_forecast_after_cutoff():
    assert select_latest_forecast([item("2026-01-14T12:01:00Z")], DELIVERY) is None


def test_forecast_published_exactly_at_cutoff_is_eligible():
    eligible = item("2026-01-14T12:00:00Z", generation=42)
    assert select_latest_forecast([eligible], DELIVERY) == eligible


def test_selects_one_eligible_forecast():
    assert select_latest_forecast([item("2026-01-14T11:00:00Z")], DELIVERY) == item("2026-01-14T11:00:00Z")


def test_returns_none_when_no_eligible_forecast():
    assert select_latest_forecast([], DELIVERY) is None


def test_conflicting_same_publication_raises():
    with pytest.raises(ValueError, match="Conflicting forecasts"):
        select_latest_forecast([item("2026-01-14T11:00:00Z", 1), item("2026-01-14T11:00:00Z", 2)], DELIVERY)


def test_exact_duplicates_do_not_change_selection():
    record = item("2026-01-14T11:00:00Z")
    assert select_latest_forecast([record, record.copy()], DELIVERY) == record


def test_configurable_cutoff_and_utc_equivalence():
    record = item("2026-01-14T13:00:00+01:00")
    assert select_latest_forecast([record], DELIVERY, decision_cutoff="2026-01-14T12:00:00Z") == record


def test_cutoff_uses_london_local_time_with_dst():
    # In summer London noon is 11:00 UTC.
    assert calculate_cutoff("2026-07-15T12:00:00Z").isoformat() == "2026-07-14T12:00:00+01:00"
