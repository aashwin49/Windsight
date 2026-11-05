import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from data_processor import aggregate_actuals_hourly

# Load actual generation data
with (BACKEND_DIR / "raw" / "actual_generation.json").open("r", encoding="utf-8") as file:
    actual_records = json.load(file)

# Aggregate half-hourly records into hourly records
hourly_records = aggregate_actuals_hourly(actual_records)

# Print results
print("Original records:", len(actual_records))
print("Hourly records:", len(hourly_records))

complete = sum(1 for r in hourly_records if r["is_complete"])
incomplete = len(hourly_records) - complete

print("Complete hours:", complete)
print("Incomplete hours:", incomplete)

print("\nFirst 5 hourly records:")
for record in hourly_records[:5]:
    print(record)
