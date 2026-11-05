import math
from numbers import Real


def calculate_accuracy(records):
    total = len(records)
    valid = []
    for row in records:
        f, a = row.get("forecast_generation"), row.get("actual_generation")
        if (isinstance(f, Real) and not isinstance(f, bool) and math.isfinite(f)
                and isinstance(a, Real) and not isinstance(a, bool) and math.isfinite(a)):
            valid.append((float(f), float(a)))
    errors = [f - a for f, a in valid]
    n = len(valid)
    abs_error = sum(abs(e) for e in errors)
    return {
        "mae": abs_error / n if n else None,
        "rmse": math.sqrt(sum(e * e for e in errors) / n) if n else None,
        "bias": sum(errors) / n if n else None,
        "wape": abs_error / sum(abs(a) for _, a in valid) * 100 if valid and sum(abs(a) for _, a in valid) else None,
        "valid_interval_count": n,
        "missing_interval_count": total - n,
        "total_interval_count": total,
    }
