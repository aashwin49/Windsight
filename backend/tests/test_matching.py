import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_processor import match_forecasts_with_actuals

forecasts = [
    {
        "startTime": "2026-01-15T12:00:00Z",
        "generation": 11000
    },
    {
        "startTime": "2026-01-15T13:00:00Z",
        "generation": 12000
    }
]

actuals = [
    {
        "startTime": "2026-01-15T12:00:00Z",
        "generation": 10000,
        "is_complete": True
    },
    {
        "startTime": "2026-01-15T13:00:00Z",
        "generation": 12500,
        "is_complete": True
    },
    {
        "startTime": "2026-01-15T14:00:00Z",
        "generation": 9000,
        "is_complete": False
    }
]

result = match_forecasts_with_actuals(forecasts, actuals)

for record in result:
    print(record)
