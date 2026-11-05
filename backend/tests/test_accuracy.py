import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from accuracy import calculate_accuracy


def rows(pairs):
    return [{"forecast_generation": f, "actual_generation": a} for f, a in pairs]


def test_mae_rmse_and_positive_bias():
    result = calculate_accuracy(rows([(3, 1), (2, 4)]))
    assert result["mae"] == 2
    assert result["rmse"] == 2
    assert result["bias"] == 0


def test_positive_and_negative_bias():
    assert calculate_accuracy(rows([(5, 2)]))["bias"] == 3
    assert calculate_accuracy(rows([(2, 5)]))["bias"] == -3


def test_wape_and_zero_denominator():
    assert calculate_accuracy(rows([(3, 2), (6, 4)]))["wape"] == 50
    zero = calculate_accuracy(rows([(0, 0)]))
    assert zero["wape"] is None
    assert (zero["valid_interval_count"], zero["missing_interval_count"]) == (1, 0)
    assert (zero["mae"], zero["rmse"], zero["bias"]) == (0, 0, 0)


def test_missing_values_are_excluded_and_counted():
    result = calculate_accuracy(rows([(3, 2), (None, 1), (1, None)]))
    assert (result["valid_interval_count"], result["missing_interval_count"], result["total_interval_count"]) == (1, 2, 3)
    assert result["mae"] == 1


def test_empty_valid_dataset():
    result = calculate_accuracy(rows([(None, 0)]))
    assert result["valid_interval_count"] == 0
    assert result["mae"] is result["rmse"] is result["bias"] is result["wape"] is None
