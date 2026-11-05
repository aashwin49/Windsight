import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_processor import (
    check_duplicate_timestamps,
    match_forecasts_with_actuals
)

forecasts = [
    {"startTime": "2026-01-15T12:00:00Z", "generation": 11000},
    {"startTime": "2026-01-15T12:00:00Z", "generation": 11500}
]

actuals = [
    {"startTime": "2026-01-15T12:00:00Z", "generation": 10000}
]

try:
    match_forecasts_with_actuals(forecasts, actuals)
except ValueError as error:
    print("Duplicate detection successful:")
    print(error)
