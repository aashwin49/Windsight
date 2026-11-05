
import json
from pathlib import Path


def load_json(file_path):
    """
    Load records from a JSON file.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Expected a JSON list of records")

    return records


def load_datasets():
    """
    Load raw actual and forecast generation datasets.
    """

    backend_dir = Path(__file__).resolve().parent
    raw_dir = backend_dir / "raw"

    actuals = load_json(raw_dir / "actual_generation.json")
    forecasts = load_json(raw_dir / "forecast_generation.json")

    return actuals, forecasts
