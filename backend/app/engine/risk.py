"""
FinGuard Privacy Risk Estimation Engine
Computes multi-scenario re-identification and linkage risk metrics:
1. Prosecutor Risk (1 / min|EC|): Worst-case targeted individual re-identification.
2. Journalist Risk: Probability of at least one privacy breach across all classes.
3. Marketer Risk (M / N): Expected bulk re-identification rate across the entire dataset.
4. Average Re-identification Risk: Expected individual risk for a randomly sampled record.
5. Transaction Linkage Risk Index (TLRI): Multi-transaction velocity and trajectory correlation.
"""

import math
from typing import Dict, List, Optional
import numpy as np

from backend.app.models.schemas import PrivacyRiskMetrics


def compute_privacy_risk_metrics(
    ec_sizes: List[int],
    total_input_records: int,
    qi_trajectory_uniqueness: Optional[float] = None
) -> PrivacyRiskMetrics:
    """
    Computes standard Statistical Disclosure Control (SDC) risk metrics from equivalence class sizes.
    """
    if not ec_sizes or total_input_records == 0:
        return PrivacyRiskMetrics(
            prosecutor_risk=0.0,
            journalist_risk=0.0,
            marketer_risk=0.0,
            average_risk=0.0,
            transaction_linkage_risk=0.0,
            smallest_class_size=0,
            largest_class_size=0,
            average_class_size=0.0,
            k_achieved=0
        )

    num_classes = len(ec_sizes)
    retained_records = sum(ec_sizes)
    min_size = min(ec_sizes)
    max_size = max(ec_sizes)
    avg_size = retained_records / num_classes if num_classes > 0 else 0.0

    # 1. Prosecutor Risk: 1 / min(|EC|)
    prosecutor_risk = 1.0 / min_size if min_size > 0 else 0.0

    # 2. Marketer Risk & Average Risk: M / N_retained
    marketer_risk = (num_classes / retained_records) if retained_records > 0 else 0.0
    average_risk = marketer_risk

    # 3. Journalist Risk: Probability of at least one re-identification breach
    # Formula: 1 - prod_{j=1}^M (1 - 1/|EC_j|)^|EC_j|
    # For numerical stability, compute via log: log(prod) = sum [ |EC_j| * log(1 - 1/|EC_j|) ]
    log_safe_prob = 0.0
    has_singleton = False
    for sz in ec_sizes:
        if sz <= 1:
            has_singleton = True
            break
        # Probability that none of the sz individuals are re-identified
        prob_none = (1.0 - (1.0 / sz)) ** sz
        log_safe_prob += math.log(max(prob_none, 1e-15))

    if has_singleton:
        journalist_risk = 1.0
    else:
        journalist_risk = float(np.clip(1.0 - math.exp(log_safe_prob), 0.0, 1.0))

    # 4. Transaction Linkage Risk Index
    if qi_trajectory_uniqueness is not None:
        transaction_linkage_risk = float(np.clip(qi_trajectory_uniqueness, 0.0, 1.0))
    else:
        # Derived from equivalence class granularity and prosecutor risk
        transaction_linkage_risk = float(np.clip((0.6 * prosecutor_risk) + (0.4 * marketer_risk), 0.0, 1.0))

    return PrivacyRiskMetrics(
        prosecutor_risk=round(float(prosecutor_risk), 4),
        journalist_risk=round(float(journalist_risk), 4),
        marketer_risk=round(float(marketer_risk), 4),
        average_risk=round(float(average_risk), 4),
        transaction_linkage_risk=round(float(transaction_linkage_risk), 4),
        smallest_class_size=int(min_size),
        largest_class_size=int(max_size),
        average_class_size=round(float(avg_size), 2),
        k_achieved=int(min_size)
    )


def compute_ncp(
    generalization_levels: Dict[str, int],
    max_depths: Optional[Dict[str, int]] = None,
    default_max_depth: int = 3
) -> float:
    """
    Computes Normalized Certainty Penalty (NCP) across generalized quasi-identifiers.
    NCP = (1 / |QI|) * sum_{i in QI} (level_i / max_depth_i)
    """
    if not generalization_levels:
        return 0.0
    penalties = []
    for col, level in generalization_levels.items():
        max_d = (max_depths or {}).get(col, default_max_depth)
        penalties.append(min(1.0, max(0.0, level / max(1, max_d))))
    return float(np.mean(penalties)) if penalties else 0.0

