import sys
import json
import math
from datetime import timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import backend.app.main as main
from forecast_selector import calculate_cutoff, normalize_timestamp

client = TestClient(main.app)
PARAMS = {"delivery_date": "2026-01-15", "cutoff_hour": 12}


def test_all_endpoints_use_real_data():
    dashboard = client.get("/api/dashboard", params=PARAMS)
    assert dashboard.status_code == 200
    assert dashboard.json()["valid_interval_count"] == 24
    generation = client.get("/api/generation", params=PARAMS).json()["data"]
    assert len(generation) == 24 and set(generation[0]) == {"startTime", "forecast", "actual", "error"}
    accuracy = client.get("/api/accuracy", params=PARAMS).json()
    assert accuracy["mae"] == dashboard.json()["mae"]
    history = client.get("/api/forecast-history", params=PARAMS).json()["data"]
    assert history and any(item["selected"] for item in history)
    assert all(item["publishTime"] <= "2026-01-14T12:00:00Z" for item in history if item["selected"])


def test_api_series_matches_processed_january_rows_and_independent_metrics():
    processed = json.loads(main.PROCESSED.read_text())
    expected = [row for row in processed if row["startTime"].startswith("2026-01-15")]
    response = client.get("/api/generation", params=PARAMS)
    assert response.status_code == 200
    series = response.json()["data"]
    assert [row["startTime"] for row in series] == [row["startTime"] for row in expected]
    for result, source in zip(series, expected):
        assert result["forecast"] == source["forecast_generation"]
        assert result["actual"] == source["actual_generation"]
        assert result["error"] == source["error"]
        if result["forecast"] is None or result["actual"] is None:
            assert result["error"] is None
        else:
            assert result["error"] == result["forecast"] - result["actual"]

    pairs = [(row["forecast"], row["actual"]) for row in series if row["forecast"] is not None and row["actual"] is not None]
    errors = [forecast - actual for forecast, actual in pairs]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error**2 for error in errors) / len(errors))
    bias = sum(errors) / len(errors)
    wape = sum(abs(error) for error in errors) / sum(abs(actual) for _, actual in pairs) * 100
    metrics = client.get("/api/accuracy", params=PARAMS).json()
    assert metrics["mae"] == mae
    assert metrics["rmse"] == rmse
    assert metrics["bias"] == bias
    assert metrics["wape"] == wape
    assert metrics["valid_interval_count"] == len(pairs)
    assert metrics["missing_interval_count"] == len(series) - len(pairs)
    assert metrics["total_interval_count"] == len(series)


def test_forecast_history_selection_matches_series_per_delivery_interval():
    rows = client.get("/api/generation", params=PARAMS).json()["data"]
    history = client.get("/api/forecast-history", params=PARAMS).json()["data"]
    assert all(row["startTime"].startswith("2026-01-15") for row in rows)
    assert all(item["startTime"].startswith("2026-01-15") for item in history)
    by_delivery = {}
    for item in history:
        by_delivery.setdefault(item["startTime"], []).append(item)
    for row in rows:
        revisions = by_delivery[row["startTime"]]
        selected = [item for item in revisions if item["selected"]]
        assert len(selected) == 1
        selected_row = selected[0]
        assert selected_row["forecast"] == row["forecast"]
        cutoff = calculate_cutoff(row["startTime"], PARAMS["cutoff_hour"]).astimezone(timezone.utc)
        selected_time = normalize_timestamp(selected_row["publishTime"])
        assert selected_time <= cutoff
        eligible = [item for item in revisions if normalize_timestamp(item["publishTime"]) <= cutoff]
        assert selected_time == max(normalize_timestamp(item["publishTime"]) for item in eligible)


def test_no_eligible_forecast_is_null_and_not_selected():
    params = {"delivery_date": "2026-01-15", "cutoff_hour": 0}
    rows = client.get("/api/generation", params=params).json()["data"]
    history = client.get("/api/forecast-history", params=params).json()["data"]
    no_forecast_times = {row["startTime"] for row in rows if row["forecast"] is None}
    assert no_forecast_times
    assert all(row["error"] is None for row in rows if row["forecast"] is None)
    assert not any(item["selected"] for item in history if item["startTime"] in no_forecast_times)


def test_invalid_query_parameters():
    assert client.get("/api/dashboard", params={"delivery_date": "bad"}).status_code == 422
    assert client.get("/api/dashboard", params={**PARAMS, "cutoff_hour": 24}).status_code == 422
    assert client.get("/api/dashboard").status_code == 422


def test_date_without_processed_data_is_404():
    assert client.get("/api/accuracy", params={"delivery_date": "2026-02-01"}).status_code == 404


def test_cutoff_changes_selected_forecast_and_excludes_later_publications():
    early = client.get("/api/forecast-history", params={**PARAMS, "cutoff_hour": 0}).json()["data"]
    noon = client.get("/api/forecast-history", params=PARAMS).json()["data"]
    assert any(row["selected"] for row in early)
    assert any(row["selected"] for row in noon)
    early_selected = next(row for row in early if row["selected"] and row["startTime"] == "2026-01-15T12:00:00Z")
    noon_selected = next(row for row in noon if row["selected"] and row["startTime"] == "2026-01-15T12:00:00Z")
    assert early_selected["publishTime"] == "2026-01-13T22:30:00Z"
    assert noon_selected["publishTime"] == "2026-01-14T11:30:00Z"
    assert all(not row["selected"] for row in noon if row["startTime"] == "2026-01-15T12:00:00Z" and row["publishTime"] > "2026-01-14T12:00:00Z")


def test_missing_processed_file_returns_service_error(monkeypatch):
    monkeypatch.setattr(main, "PROCESSED", Path("/does/not/exist.json"))
    assert client.get("/api/dashboard", params=PARAMS).status_code == 503
