import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_loader import load_datasets

actuals, forecasts = load_datasets()

print("Actual records:", len(actuals))
print("Forecast records:", len(forecasts))

print("First actual record:", actuals[0])
print("First forecast record:", forecasts[0])