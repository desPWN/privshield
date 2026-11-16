"""
FinGuard T-Closeness Evaluator
Measures the distance between the local sensitive attribute distribution within each
equivalence class and the global dataset distribution.
Implements:
1. Continuous attributes: 1D Earth Mover's Distance (Wasserstein-1) via step integration
   on normalized empirical Cumulative Distribution Functions (ECDFs).
2. Categorical attributes: Total Variation Distance (TVD = 0.5 * sum |p - q|).
"""

from bisect import bisect_right
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from backend.app.models.schemas import TClosenessAuditResult, TClosenessViolationDetail


def compute_continuous_wasserstein_distance(
    class_values: List[float],
    global_values: List[float]
) -> float:
    """
    Computes exact 1D Wasserstein-1 (Earth Mover's Distance) between class and global
    continuous values normalized to [0, 1].
    """
    if not class_values or not global_values:
        return 0.0

    min_val = float(min(global_values))
    max_val = float(max(global_values))
    val_range = max_val - min_val

    if val_range <= 1e-12:
        return 0.0

    # Sorted evaluation points across union
    all_points = sorted(set(global_values + class_values))
    m = len(all_points)
    if m <= 1:
        return 0.0

    sorted_class = sorted(class_values)
    sorted_global = sorted(global_values)
    n_class = len(class_values)
    n_global = len(global_values)

    emd = 0.0
    for i in range(m - 1):
        x_k = all_points[i]
        x_next = all_points[i + 1]
        dx = (x_next - x_k) / val_range

        # ECDF values at x_k
        cdf_class = bisect_right(sorted_class, x_k) / n_class
        cdf_global = bisect_right(sorted_global, x_k) / n_global

        emd += dx * abs(cdf_class - cdf_global)

    return float(np.clip(emd, 0.0, 1.0))


def compute_categorical_tvd(
    class_values: List[Any],
    global_values: List[Any]
) -> float:
    """
    Computes Total Variation Distance (TVD) for categorical attribute distributions:
    TVD = 0.5 * sum_{c} |p(c) - q(c)|
    """
    if not class_values or not global_values:
        return 0.0

    n_class = len(class_values)
    n_global = len(global_values)

    class_counts = Counter(class_values)
    global_counts = Counter(global_values)
    all_categories = set(global_counts.keys()).union(class_counts.keys())

    sum_abs_diff = 0.0
    for cat in all_categories:
        p_c = class_counts.get(cat, 0) / n_class
        q_c = global_counts.get(cat, 0) / n_global
        sum_abs_diff += abs(p_c - q_c)

    tvd = 0.5 * sum_abs_diff
    return float(np.clip(tvd, 0.0, 1.0))


def evaluate_t_closeness(
    df: pd.DataFrame,
    qi_columns: List[str],
    sensitive_column: str,
    target_t: float = 0.20,
    force_numeric: Optional[bool] = None
) -> TClosenessAuditResult:
    """
    Evaluates T-closeness for each equivalence class formed by qi_columns against the
    global distribution of sensitive_column.
    """
    if sensitive_column not in df.columns:
        raise KeyError(f"Sensitive column '{sensitive_column}' not found in DataFrame.")

    for col in qi_columns:
        if col not in df.columns:
            raise KeyError(f"Quasi-identifier column '{col}' not found in DataFrame.")

    if df.empty:
        return TClosenessAuditResult(
            target_t=target_t,
            sensitive_attribute=sensitive_column,
            attribute_type="numeric" if force_numeric else "categorical",
            satisfied=True,
            total_classes=0,
            violating_classes_count=0,
            violating_records_count=0,
            max_observed_distance=0.0,
            average_distance=0.0,
            violation_details=[]
        )

    # Determine attribute type
    if force_numeric is not None:
        is_numeric = force_numeric
    else:
        is_numeric = pd.api.types.is_numeric_dtype(df[sensitive_column])

    # Extract global distribution values
    if is_numeric:
        clean_global = df[sensitive_column].dropna().astype(float).tolist()
    else:
        clean_global = [str(v) if pd.notna(v) else "[NULL]" for v in df[sensitive_column]]

    # Group records by Equivalence Class
    ec_sensitive_map: Dict[tuple, List[Any]] = defaultdict(list)
    for _, row in df.iterrows():
        qi_tuple = tuple(str(row[col]) for col in qi_columns)
        val = row[sensitive_column]
        if is_numeric:
            if pd.notna(val):
                ec_sensitive_map[qi_tuple].append(float(val))
        else:
            ec_sensitive_map[qi_tuple].append(str(val) if pd.notna(val) else "[NULL]")

    total_classes = len(ec_sensitive_map)
    violating_details: List[TClosenessViolationDetail] = []
    distances: List[float] = []
    total_violating_records = 0

    for c_id, (qi_tuple, class_vals) in enumerate(ec_sensitive_map.items(), start=1):
        if not class_vals:
            dist = 0.0
        elif is_numeric:
            dist = compute_continuous_wasserstein_distance(class_vals, clean_global)
        else:
            dist = compute_categorical_tvd(class_vals, clean_global)

        dist = round(dist, 4)
        distances.append(dist)
        is_viol = dist > target_t

        if is_viol:
            total_violating_records += len(class_vals)

        violating_details.append(TClosenessViolationDetail(
            class_id=c_id,
            qi_values=dict(zip(qi_columns, qi_tuple)),
            class_size=len(class_vals),
            distance=dist,
            threshold_t=target_t,
            is_violation=is_viol
        ))

    violating_classes_count = sum(1 for d in violating_details if d.is_violation)
    satisfied = (violating_classes_count == 0) and (total_classes > 0)
    max_dist = max(distances) if distances else 0.0
    avg_dist = float(sum(distances) / len(distances)) if distances else 0.0

    return TClosenessAuditResult(
        target_t=target_t,
        sensitive_attribute=sensitive_column,
        attribute_type="numeric" if is_numeric else "categorical",
        satisfied=satisfied,
        total_classes=total_classes,
        violating_classes_count=violating_classes_count,
        violating_records_count=total_violating_records,
        max_observed_distance=round(max_dist, 4),
        average_distance=round(avg_dist, 4),
        violation_details=violating_details
    )
