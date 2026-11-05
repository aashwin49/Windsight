from datetime import date
from pathlib import Path
import json
import os
import sys

# The API entry point lives in backend/app, while the shared modules and data
# files live one directory above it. Add that directory before importing them
# so `uvicorn main:app` works when launched from backend/app.
ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from accuracy import calculate_accuracy
from data_loader import load_json
from data_processor import aggregate_actuals_hourly
from forecast_selector import normalize_timestamp, select_latest_forecast, calculate_cutoff

PROCESSED = BACKEND_ROOT / "processed" / "january_2026_processed.json"
ACTUALS_PATH = BACKEND_ROOT / "raw" / "actual_generation.json"
FORECASTS_PATH = BACKEND_ROOT / "raw" / "forecast_generation.json"
app = FastAPI(title="Windsight API", version="1.0")
# Configure comma-separated browser origins with CORS_ORIGINS. Local development
# defaults remain useful when no deployment-specific value is supplied.
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def selected_data(delivery_date: date, cutoff_hour: int):
    if not PROCESSED.exists():
        raise HTTPException(503, "Processed dataset is unavailable")
    try:
        processed = load_json(PROCESSED)
        actual_raw = load_json(ACTUALS_PATH)
        forecasts = load_json(FORECASTS_PATH)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(503, f"Unable to load processed or source data: {exc}") from exc
    actual_date = [r for r in actual_raw if normalize_timestamp(r["startTime"]).date() == delivery_date]
    hourly_actuals = aggregate_actuals_hourly(actual_date)
    if not hourly_actuals:
        raise HTTPException(404, f"No data available for delivery date {delivery_date.isoformat()}")
    day_forecasts = [r for r in forecasts if normalize_timestamp(r["startTime"]).date() == delivery_date]
    rows = []
    for actual in hourly_actuals:
        start = actual["startTime"]
        chosen = select_latest_forecast(day_forecasts, start, cutoff_hour=cutoff_hour)
        forecast = chosen.get("generation") if chosen else None
        actual_value = actual["generation"] if actual.get("is_complete", True) else None
        error = forecast - actual_value if forecast is not None and actual_value is not None else None
        rows.append({"startTime": start, "forecast": forecast, "actual": actual_value, "error": error,
                     "forecast_generation": forecast, "actual_generation": actual_value,
                     "forecast_missing": forecast is None, "actual_missing": actual_value is None,
                     "actual_incomplete": not actual.get("is_complete", True),
                     "forecast_publish_time": chosen["publishTime"] if chosen else None,
                     "decision_cutoff": calculate_cutoff(start, cutoff_hour).isoformat()})
    # Validate date against the Phase 3 processed window, rather than silently serving arbitrary source-only data.
    if not any(normalize_timestamp(r["startTime"]).date() == delivery_date for r in processed):
        raise HTTPException(404, f"No processed data available for delivery date {delivery_date.isoformat()}")
    return rows, day_forecasts


@app.get("/api/dashboard")
def dashboard(delivery_date: date = Query(...), cutoff_hour: int = Query(12, ge=0, le=23)):
    rows, _ = selected_data(delivery_date, cutoff_hour)
    metrics = calculate_accuracy(rows)
    valid = [r for r in rows if r["error"] is not None]
    avg = lambda key: sum(r[key] for r in valid) / len(valid) if valid else None
    return {"selected_date": delivery_date.isoformat(), "decision_cutoff": f"{cutoff_hour:02d}:00 Europe/London",
            "forecast_generation_mw": avg("forecast"), "actual_generation_mw": avg("actual"),
            "forecast_error_mw": avg("error"), "wape_percent": metrics["wape"], **metrics,
            "missing_forecast_count": sum(r["forecast_missing"] for r in rows),
            "missing_actual_count": sum(r["actual_missing"] for r in rows)}


@app.get("/api/generation")
def generation(delivery_date: date = Query(...), cutoff_hour: int = Query(12, ge=0, le=23)):
    rows, _ = selected_data(delivery_date, cutoff_hour)
    return {"selected_date": delivery_date.isoformat(), "data": [{k: r[k] for k in ("startTime", "forecast", "actual", "error")} for r in rows]}


@app.get("/api/accuracy")
def accuracy(delivery_date: date = Query(...), cutoff_hour: int = Query(12, ge=0, le=23)):
    rows, _ = selected_data(delivery_date, cutoff_hour)
    return {"selected_date": delivery_date.isoformat(), **calculate_accuracy(rows)}


@app.get("/api/forecast-history")
def forecast_history(delivery_date: date = Query(...), cutoff_hour: int = Query(12, ge=0, le=23)):
    rows, forecasts = selected_data(delivery_date, cutoff_hour)
    selected = {r["startTime"]: r["forecast_publish_time"] for r in rows}
    history = []
    for row in forecasts:
        start = normalize_timestamp(row["startTime"])
        pub = normalize_timestamp(row["publishTime"])
        start_iso = start.isoformat().replace("+00:00", "Z")
        history.append({"startTime": start_iso, "publishTime": row["publishTime"], "forecast": row.get("generation"),
                        "selected": row.get("publishTime") == selected.get(start_iso) and selected.get(start_iso) is not None})
    history.sort(key=lambda r: (r["startTime"], r["publishTime"]))
    return {"selected_date": delivery_date.isoformat(), "decision_cutoff": f"{cutoff_hour:02d}:00 Europe/London", "data": history}
