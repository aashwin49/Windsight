"""Build the January 2026 hourly forecast/actual dataset."""
import json
from datetime import datetime, timezone
from pathlib import Path

from data_loader import load_datasets
from data_processor import aggregate_actuals_hourly, match_forecasts_with_actuals
from forecast_selector import normalize_timestamp, select_latest_forecast


def process_january_2026(cutoff_hour=12):
    actuals, forecasts = load_datasets()
    jan_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feb_start = datetime(2026, 2, 1, tzinfo=timezone.utc)
    in_january = lambda r: jan_start <= normalize_timestamp(r["startTime"]) < feb_start
    january_actuals = [r for r in actuals if in_january(r)]
    january_forecasts = [r for r in forecasts if in_january(r)]

    hourly_actuals = aggregate_actuals_hourly(january_actuals)
    selected = []
    metadata = {}
    for actual in hourly_actuals:
        start = actual["startTime"]
        chosen = select_latest_forecast(january_forecasts, start, cutoff_hour=cutoff_hour)
        if chosen is not None:
            selected.append({"startTime": start, "generation": chosen.get("generation")})
            cutoff = select_cutoff(start, cutoff_hour)
            metadata[normalize_timestamp(start)] = {
                "decision_cutoff": cutoff,
                "forecast_publish_time": chosen["publishTime"],
            }

    output = match_forecasts_with_actuals(selected, hourly_actuals)
    for record in output:
        record.update(metadata.get(normalize_timestamp(record["startTime"]), {}))
    out_path = Path(__file__).resolve().parent / "processed" / "january_2026_processed.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return {
        "original_actual_count": len(actuals),
        "original_forecast_count": len(forecasts),
        "january_actual_source_count": len(january_actuals),
        "january_forecast_source_count": len(january_forecasts),
        "hourly_actual_count": len(hourly_actuals),
        "selected_forecast_count": len(selected),
        "missing_forecast_count": sum(r["forecast_missing"] for r in output),
        "missing_or_incomplete_actual_count": sum(r["actual_missing"] for r in output),
        "incomplete_actual_count": sum(r["actual_incomplete"] for r in output),
        "final_matched_record_count": len(output),
        "duplicate_actual_records_ignored": len(january_actuals) - len({normalize_timestamp(r["startTime"]) for r in january_actuals}),
        "export": str(out_path),
    }


def select_cutoff(delivery_time, cutoff_hour):
    from forecast_selector import calculate_cutoff
    return calculate_cutoff(delivery_time, cutoff_hour).isoformat()


if __name__ == "__main__":
    print(json.dumps(process_january_2026(), indent=2))
