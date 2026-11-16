"""
FinGuard Strict K-Anonymity Engine
Partitions dataset into Equivalence Classes based on user-selected Quasi-Identifiers,
applies hierarchical generalization, and deterministically resolves all violations
via outlier suppression so that NO retained equivalence class has size < K.

HARD RULE: Never claims K satisfaction unless every single retained equivalence class
strictly contains at least K records.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from backend.app.models.schemas import EquivalenceClassSummary
from backend.app.engine.hierarchies import HierarchyRegistry


def partition_equivalence_classes(
    df: pd.DataFrame,
    qi_columns: List[str]
) -> Dict[Tuple[Any, ...], List[int]]:
    """
    Partition dataframe row indices into equivalence classes based on quasi-identifier tuple.
    Returns mapping from qi_tuple to list of original row indices.
    """
    ec_map: Dict[Tuple[Any, ...], List[int]] = defaultdict(list)
    if df.empty or not qi_columns:
        return ec_map

    # Ensure all qi_columns exist in df
    for col in qi_columns:
        if col not in df.columns:
            raise KeyError(f"Quasi-identifier column '{col}' not found in DataFrame.")

    # Iterate rows and group indices
    for idx, row in df.iterrows():
        qi_tuple = tuple(str(row[col]) for col in qi_columns)
        ec_map[qi_tuple].append(idx)

    return ec_map


def enforce_strict_k_anonymity(
    df: pd.DataFrame,
    qi_columns: List[str],
    target_k: int = 5,
    generalization_levels: Optional[Dict[str, int]] = None,
    suppression_strategy: str = "record",
    max_suppression_pct: float = 0.50
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Executes strict K-anonymity on the provided dataframe.
    Guarantees:
      min(|EC_j|) >= target_k for all j in remaining equivalence classes.
      If total records < target_k, suppresses 100% of records.
    """
    if target_k < 2:
        raise ValueError(f"target_k must be >= 2, got {target_k}")

    total_records = len(df)
    if total_records == 0:
        return df.copy(), {
            "k_satisfied": True,
            "achieved_k": 0,
            "total_records": 0,
            "retained_records": 0,
            "suppressed_records": 0,
            "suppression_rate": 0.0,
            "num_equivalence_classes": 0,
            "min_equivalence_class_size": 0,
            "avg_equivalence_class_size": 0.0,
            "violating_classes_count": 0,
            "equivalence_classes": []
        }

    # If no quasi-identifiers are defined, no K-anonymity partitioning applies.
    # All records are retained intact without suppression.
    if not qi_columns:
        return df.copy(), {
            "k_satisfied": True,
            "achieved_k": total_records,
            "total_records": total_records,
            "retained_records": total_records,
            "suppressed_records": 0,
            "suppression_rate": 0.0,
            "num_equivalence_classes": 1 if total_records > 0 else 0,
            "min_equivalence_class_size": total_records,
            "avg_equivalence_class_size": float(total_records),
            "violating_classes_count": 0,
            "equivalence_classes": []
        }

    # If dataset has fewer records than target_k, no class can ever satisfy K.
    # Strict invariant requires suppressing all records to prevent privacy leakage.
    if total_records < target_k:
        empty_df = df.iloc[0:0].copy()
        return empty_df, {
            "k_satisfied": True,  # Vacuously satisfied because 0 classes remain with size < K
            "achieved_k": 0,
            "total_records": total_records,
            "retained_records": 0,
            "suppressed_records": total_records,
            "suppression_rate": 1.0,
            "num_equivalence_classes": 0,
            "min_equivalence_class_size": 0,
            "avg_equivalence_class_size": 0.0,
            "violating_classes_count": 1,
            "equivalence_classes": []
        }

    # Step 1: Apply domain generalization hierarchies to QI attributes
    transformed_df = df.reset_index(drop=True)
    if generalization_levels:
        for col, level in generalization_levels.items():
            if col in transformed_df.columns and level > 0:
                transformed_df[col] = HierarchyRegistry.generalize_series(
                    col, transformed_df[col], level=level
                )

    # Step 2: Group records into Equivalence Classes
    ec_map = partition_equivalence_classes(transformed_df, qi_columns)

    # Step 3: Classify compliant vs violating equivalence classes
    compliant_indices: List[int] = []
    violating_indices: List[int] = []
    violating_classes_info: List[Dict[str, Any]] = []

    for qi_tuple, member_indices in ec_map.items():
        if len(member_indices) >= target_k:
            compliant_indices.extend(member_indices)
        else:
            violating_indices.extend(member_indices)
            violating_classes_info.append({
                "qi_values": dict(zip(qi_columns, qi_tuple)),
                "size": len(member_indices),
                "record_indices": member_indices
            })

    # Step 4: Resolve violations deterministically
    suppressed_count = len(violating_indices)

    if suppression_strategy == "cell":
        # Keep compliant records intact
        retained_records = transformed_df.loc[compliant_indices].copy()

        # Mask QI values of violating records with wildcard '*'
        if violating_indices:
            masked_violators = transformed_df.loc[violating_indices].copy()
            for col in qi_columns:
                masked_violators[col] = "*"

            # If the wildcard group meets target_k, it forms a valid equivalence class
            if len(masked_violators) >= target_k:
                anonymized_df = pd.concat([retained_records, masked_violators], axis=0)
                suppressed_count = 0
            else:
                # Even wildcard class is smaller than K -> must record-suppress
                anonymized_df = retained_records
                suppressed_count = len(violating_indices)
        else:
            anonymized_df = retained_records
    else:
        # Standard record suppression: drop violating rows
        anonymized_df = transformed_df.loc[compliant_indices].copy()

    # Re-index output cleanly
    anonymized_df = anonymized_df.reset_index(drop=True)

    # Step 5: Verify strict invariant on the final output
    final_ec_map = partition_equivalence_classes(anonymized_df, qi_columns)
    final_class_sizes = [len(members) for members in final_ec_map.values()]

    if final_class_sizes:
        actual_min_k = min(final_class_sizes)
        # HARD RULE ASSERTION
        if actual_min_k < target_k:
            raise AssertionError(
                f"INVARIANT VIOLATION: Equivalence class with size {actual_min_k} < target {target_k}"
            )
        k_satisfied = True
        avg_size = float(sum(final_class_sizes) / len(final_class_sizes))
        achieved_k = actual_min_k
    else:
        actual_min_k = 0
        avg_size = 0.0
        achieved_k = 0
        k_satisfied = (total_records == 0 or total_records < target_k or suppressed_count == total_records)

    # Build equivalence class summaries for UI / analytics
    ec_summaries: List[EquivalenceClassSummary] = []
    for c_id, (qi_tuple, member_indices) in enumerate(final_ec_map.items(), start=1):
        ec_summaries.append(EquivalenceClassSummary(
            class_id=c_id,
            qi_values=dict(zip(qi_columns, qi_tuple)),
            size=len(member_indices),
            is_k_satisfied=len(member_indices) >= target_k,
            record_indices=member_indices
        ))

    retained_count = len(anonymized_df)
    suppression_rate = (suppressed_count / total_records) if total_records > 0 else 0.0

    metrics = {
        "k_satisfied": k_satisfied,
        "achieved_k": achieved_k,
        "target_k": target_k,
        "total_records": total_records,
        "retained_records": retained_count,
        "suppressed_records": suppressed_count,
        "suppression_rate": round(suppression_rate, 4),
        "num_equivalence_classes": len(final_ec_map),
        "min_equivalence_class_size": actual_min_k,
        "avg_equivalence_class_size": round(avg_size, 2),
        "violating_classes_count": len(violating_classes_info),
        "equivalence_classes": ec_summaries
    }

    return anonymized_df, metrics
