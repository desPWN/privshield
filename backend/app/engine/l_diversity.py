"""
PrivShield L-Diversity Evaluator
Audits the diversity of designated sensitive attributes within each equivalence class.
Implements:
1. Distinct L-Diversity: Every class must contain at least L distinct sensitive values.
2. Entropy L-Diversity: Information entropy H(S|EC) >= log2(L).
3. Recursive (c, l)-Diversity: Most frequent value count r_1 < c * sum_{i=l}^m r_i.
Provides structured violation diagnostics for vulnerability mitigation.
"""

from collections import Counter, defaultdict
import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from backend.app.models.schemas import LDiversityAuditResult, LDiversityViolationDetail


def evaluate_distinct_l_diversity(
    df: pd.DataFrame,
    qi_columns: List[str],
    sensitive_column: str,
    target_l: int = 3
) -> LDiversityAuditResult:
    """
    Evaluates distinct L-diversity across all equivalence classes formed by qi_columns.
    Returns structured audit result detailing compliance and any violating groups.
    """
    if sensitive_column not in df.columns:
        raise KeyError(f"Sensitive column '{sensitive_column}' not found in DataFrame.")

    for col in qi_columns:
        if col not in df.columns:
            raise KeyError(f"Quasi-identifier column '{col}' not found in DataFrame.")

    if df.empty:
        return LDiversityAuditResult(
            target_l=target_l,
            sensitive_attribute=sensitive_column,
            satisfied=True,
            total_classes=0,
            violating_classes_count=0,
            violating_records_count=0,
            min_observed_distinct_values=0,
            violation_details=[]
        )

    # Group sensitive values by equivalence class QI signature
    ec_sensitive_map: Dict[tuple, List[Any]] = defaultdict(list)
    for _, row in df.iterrows():
        qi_tuple = tuple(str(row[col]) for col in qi_columns)
        ec_sensitive_map[qi_tuple].append(row[sensitive_column])

    total_classes = len(ec_sensitive_map)
    violating_classes: List[LDiversityViolationDetail] = []
    total_violating_records = 0
    min_diversity_observed = float("inf")

    for qi_tuple, sensitive_vals in ec_sensitive_map.items():
        clean_vals = [str(v) if pd.notna(v) else "[NULL]" for v in sensitive_vals]
        distinct_vals = list(set(clean_vals))
        div_count = len(distinct_vals)

        if div_count < min_diversity_observed:
            min_diversity_observed = div_count

        if div_count < target_l:
            total_violating_records += len(sensitive_vals)
            freq_dict = dict(Counter(clean_vals))
            violating_classes.append(LDiversityViolationDetail(
                qi_values=dict(zip(qi_columns, qi_tuple)),
                class_size=len(sensitive_vals),
                distinct_count=div_count,
                values_present=distinct_vals,
                frequency_breakdown=freq_dict
            ))

    satisfied = (len(violating_classes) == 0) and (total_classes > 0)
    actual_min = int(min_diversity_observed) if total_classes > 0 else 0

    return LDiversityAuditResult(
        target_l=target_l,
        sensitive_attribute=sensitive_column,
        satisfied=satisfied,
        total_classes=total_classes,
        violating_classes_count=len(violating_classes),
        violating_records_count=total_violating_records,
        min_observed_distinct_values=actual_min,
        violation_details=violating_classes
    )


def evaluate_entropy_l_diversity(
    df: pd.DataFrame,
    qi_columns: List[str],
    sensitive_column: str,
    target_l: int = 3
) -> LDiversityAuditResult:
    """
    Evaluates entropy L-diversity: H(S|EC) >= log2(L).
    """
    if sensitive_column not in df.columns:
        raise KeyError(f"Sensitive column '{sensitive_column}' not found in DataFrame.")

    for col in qi_columns:
        if col not in df.columns:
            raise KeyError(f"Quasi-identifier column '{col}' not found in DataFrame.")

    if df.empty:
        return LDiversityAuditResult(
            target_l=target_l,
            sensitive_attribute=sensitive_column,
            satisfied=True,
            total_classes=0,
            violating_classes_count=0,
            violating_records_count=0,
            min_observed_distinct_values=0,
            violation_details=[]
        )

    target_entropy = math.log2(target_l) if target_l > 1 else 0.0

    ec_sensitive_map: Dict[tuple, List[Any]] = defaultdict(list)
    for _, row in df.iterrows():
        qi_tuple = tuple(str(row[col]) for col in qi_columns)
        ec_sensitive_map[qi_tuple].append(row[sensitive_column])

    total_classes = len(ec_sensitive_map)
    violating_classes: List[LDiversityViolationDetail] = []
    total_violating_records = 0
    min_diversity_observed = float("inf")

    for qi_tuple, sensitive_vals in ec_sensitive_map.items():
        clean_vals = [str(v) if pd.notna(v) else "[NULL]" for v in sensitive_vals]
        freq_dict = dict(Counter(clean_vals))
        total_n = len(clean_vals)
        div_count = len(freq_dict)

        if div_count < min_diversity_observed:
            min_diversity_observed = div_count

        # Compute Shannon entropy
        entropy = 0.0
        for cnt in freq_dict.values():
            p = cnt / total_n
            if p > 0:
                entropy -= p * math.log2(p)

        if entropy < target_entropy - 1e-9:
            total_violating_records += total_n
            violating_classes.append(LDiversityViolationDetail(
                qi_values=dict(zip(qi_columns, qi_tuple)),
                class_size=total_n,
                distinct_count=div_count,
                values_present=list(freq_dict.keys()),
                frequency_breakdown=freq_dict
            ))

    satisfied = (len(violating_classes) == 0) and (total_classes > 0)
    actual_min = int(min_diversity_observed) if total_classes > 0 else 0

    return LDiversityAuditResult(
        target_l=target_l,
        sensitive_attribute=sensitive_column,
        satisfied=satisfied,
        total_classes=total_classes,
        violating_classes_count=len(violating_classes),
        violating_records_count=total_violating_records,
        min_observed_distinct_values=actual_min,
        violation_details=violating_classes
    )


def evaluate_recursive_l_diversity(
    df: pd.DataFrame,
    qi_columns: List[str],
    sensitive_column: str,
    c: float = 2.0,
    l: int = 3
) -> LDiversityAuditResult:
    """
    Evaluates recursive (c, l)-diversity: r_1 < c * sum_{i=l}^m r_i
    where r_1 >= r_2 >= ... >= r_m are the sorted value frequencies.
    """
    if sensitive_column not in df.columns:
        raise KeyError(f"Sensitive column '{sensitive_column}' not found in DataFrame.")

    for col in qi_columns:
        if col not in df.columns:
            raise KeyError(f"Quasi-identifier column '{col}' not found in DataFrame.")

    if df.empty:
        return LDiversityAuditResult(
            target_l=l,
            sensitive_attribute=sensitive_column,
            satisfied=True,
            total_classes=0,
            violating_classes_count=0,
            violating_records_count=0,
            min_observed_distinct_values=0,
            violation_details=[]
        )

    ec_sensitive_map: Dict[tuple, List[Any]] = defaultdict(list)
    for _, row in df.iterrows():
        qi_tuple = tuple(str(row[col]) for col in qi_columns)
        ec_sensitive_map[qi_tuple].append(row[sensitive_column])

    total_classes = len(ec_sensitive_map)
    violating_classes: List[LDiversityViolationDetail] = []
    total_violating_records = 0
    min_diversity_observed = float("inf")

    for qi_tuple, sensitive_vals in ec_sensitive_map.items():
        clean_vals = [str(v) if pd.notna(v) else "[NULL]" for v in sensitive_vals]
        freq_dict = dict(Counter(clean_vals))
        total_n = len(clean_vals)
        sorted_freqs = sorted(freq_dict.values(), reverse=True)
        m = len(sorted_freqs)

        if m < min_diversity_observed:
            min_diversity_observed = m

        r_1 = sorted_freqs[0]
        # sum from index l-1 to end (1-indexed l to m)
        tail_sum = sum(sorted_freqs[l - 1:]) if m >= l else 0

        is_violating = (m < l) or (r_1 >= c * tail_sum)

        if is_violating:
            total_violating_records += total_n
            violating_classes.append(LDiversityViolationDetail(
                qi_values=dict(zip(qi_columns, qi_tuple)),
                class_size=total_n,
                distinct_count=m,
                values_present=list(freq_dict.keys()),
                frequency_breakdown=freq_dict
            ))

    satisfied = (len(violating_classes) == 0) and (total_classes > 0)
    actual_min = int(min_diversity_observed) if total_classes > 0 else 0

    return LDiversityAuditResult(
        target_l=l,
        sensitive_attribute=sensitive_column,
        satisfied=satisfied,
        total_classes=total_classes,
        violating_classes_count=len(violating_classes),
        violating_records_count=total_violating_records,
        min_observed_distinct_values=actual_min,
        violation_details=violating_classes
    )


def evaluate_l_diversity(
    df: pd.DataFrame,
    qi_columns: List[str],
    sensitive_column: str,
    target_l: int = 3,
    mode: str = "distinct",
    c: float = 2.0
) -> LDiversityAuditResult:
    """Unified L-diversity evaluation dispatcher."""
    m = mode.lower().strip()
    if m == "entropy":
        return evaluate_entropy_l_diversity(df, qi_columns, sensitive_column, target_l=target_l)
    if m in ("recursive", "c_l"):
        return evaluate_recursive_l_diversity(df, qi_columns, sensitive_column, c=c, l=target_l)
    return evaluate_distinct_l_diversity(df, qi_columns, sensitive_column, target_l=target_l)
