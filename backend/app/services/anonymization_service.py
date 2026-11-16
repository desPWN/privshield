"""
FinGuard Anonymization Service
Coordinates the end-to-end de-identification pipeline:
- Direct identifier masking
- Generalization hierarchies
- Strict K-Anonymity with deterministic suppression
- Distinct L-Diversity and T-Closeness audits
- Privacy risk and CURS data utility retention scoring
- Physical storage isolation in storage/anonymized/{run_id}.csv
- Side-by-side comparative diff generation
"""

import json
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.security import resolve_safe_path, validate_uuid_id
from backend.app.db.database import DatabaseRepository
from backend.app.engine.hierarchies import HierarchyRegistry
from backend.app.engine.k_anonymity import (
    enforce_strict_k_anonymity,
    partition_equivalence_classes,
)
from backend.app.engine.l_diversity import evaluate_distinct_l_diversity
from backend.app.engine.masking import apply_masking_rule
from backend.app.engine.risk import compute_privacy_risk_metrics
from backend.app.engine.t_closeness import evaluate_t_closeness
from backend.app.engine.utility import compute_utility_metrics
from backend.app.models.schemas import (
    AnonymizationConfig,
    AnonymizationResult,
    PrivacyRiskMetrics,
    UtilityMetrics,
)
from backend.app.services.dataset_service import DatasetService


def _to_json_safe(val: Any) -> Any:
    """Converts numpy and pandas scalars to native Python primitives for JSON encoding."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        return float(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    return str(val) if not isinstance(val, (int, float, str, list, dict)) else val


class AnonymizationService:
    @classmethod
    def execute_anonymization(
        cls,
        dataset_id: str,
        config: AnonymizationConfig,
    ) -> Dict[str, Any]:
        """
        Executes full anonymization pipeline according to AnonymizationConfig.
        Saves output in storage/anonymized/{run_id}.csv and records run in SQLite.
        """
        start_time = time.perf_counter()
        clean_dataset_id = validate_uuid_id(dataset_id)

        dataset_meta = DatabaseRepository.get_dataset(clean_dataset_id)
        if not dataset_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{dataset_id}' not found.",
            )

        orig_df = DatasetService.get_dataset_df(clean_dataset_id)
        total_input_records = len(orig_df)

        # Validate Quasi-Identifiers
        for qi in config.quasi_identifiers:
            if qi not in orig_df.columns:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Quasi-identifier '{qi}' does not exist in dataset columns.",
                )

        working_df = orig_df.copy()

        # Retrieve effective classification roles (respecting user overrides)
        profiles = DatasetService.get_dataset_profiles(clean_dataset_id)
        effective_roles = {
            p.column_name: (p.user_category or p.detected_type) for p in profiles
        }

        # Step 1: Apply Direct Identifier Masking Rules
        for col, rule in config.masking_rules.items():
            if col in working_df.columns:
                role = effective_roles.get(col)
                # Never mask columns classified or overridden as insensitive
                if role == "insensitive":
                    continue
                working_df[col] = working_df[col].apply(
                    lambda v: apply_masking_rule(v, rule)
                )

        # Step 2: Apply Generalization Hierarchies to Quasi-Identifiers
        for col, level in config.generalization_levels.items():
            if col in working_df.columns and level > 0:
                working_df[col] = HierarchyRegistry.generalize_series(
                    col, working_df[col], level=level
                )

        # Step 3: Strict K-Anonymity Partitioning & Deterministic Suppression
        anon_df, k_metrics = enforce_strict_k_anonymity(
            df=working_df,
            qi_columns=config.quasi_identifiers,
            target_k=config.k_metric,
            generalization_levels=None,  # Already applied above
            suppression_strategy=config.suppression_strategy,
            max_suppression_pct=config.max_suppression_pct,
        )

        retained_records = len(anon_df)
        suppressed_records = total_input_records - retained_records
        suppression_rate = (
            suppressed_records / total_input_records
            if total_input_records > 0
            else 0.0
        )

        # Budget verification
        k_satisfied = k_metrics.get("k_satisfied", False)
        if (
            suppression_rate > config.max_suppression_pct
            and config.max_suppression_pct < 1.0
        ):
            k_satisfied = False

        achieved_k = k_metrics.get("achieved_k", 0)

        # Step 4: Distinct L-Diversity Evaluation
        l_diversity_results: Dict[str, Any] = {}
        achieved_l: Optional[int] = None
        for sens_attr in config.sensitive_attributes:
            if sens_attr in anon_df.columns:
                target_l = config.l_metric or 2
                l_res = evaluate_distinct_l_diversity(
                    df=anon_df,
                    qi_columns=config.quasi_identifiers,
                    sensitive_column=sens_attr,
                    target_l=target_l,
                )
                l_diversity_results[sens_attr] = l_res.model_dump()
                if achieved_l is None or l_res.min_observed_distinct_values < achieved_l:
                    achieved_l = l_res.min_observed_distinct_values

        # Step 5: T-Closeness Evaluation
        t_closeness_results: Dict[str, Any] = {}
        achieved_t: Optional[float] = None
        for sens_attr in config.sensitive_attributes:
            if sens_attr in anon_df.columns:
                target_t = config.t_metric or 0.20
                t_res = evaluate_t_closeness(
                    df=anon_df,
                    qi_columns=config.quasi_identifiers,
                    sensitive_column=sens_attr,
                    target_t=target_t,
                )
                t_closeness_results[sens_attr] = t_res.model_dump()
                if achieved_t is None or t_res.max_observed_distance > achieved_t:
                    achieved_t = t_res.max_observed_distance

        # Step 6: Multi-scenario Privacy Risk Metrics
        ec_map = partition_equivalence_classes(anon_df, config.quasi_identifiers)
        ec_sizes = [len(members) for members in ec_map.values()]
        risk_metrics: PrivacyRiskMetrics = compute_privacy_risk_metrics(
            ec_sizes, total_input_records=retained_records
        )

        # Step 7: 5-Component Statistical Utility (CURS)
        utility_metrics: UtilityMetrics = compute_utility_metrics(
            original_df=orig_df,
            anonymized_df=anon_df,
            quasi_identifiers=config.quasi_identifiers,
            generalization_levels=config.generalization_levels,
        )

        # Step 8: Storage Isolation
        run_id = str(uuid.uuid4())
        anon_storage_path = resolve_safe_path(
            settings.ANONYMIZED_STORAGE_DIR, f"{run_id}.csv"
        )
        anon_df.to_csv(anon_storage_path, index=False)

        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Record Equivalence Class Summaries for Frontend Visualizations
        ec_histogram = [
            {"size": sz, "count": ec_sizes.count(sz)} for sz in sorted(set(ec_sizes))
        ]

        full_metrics = {
            "run_id": run_id,
            "dataset_id": clean_dataset_id,
            "dataset_name": dataset_meta["name"],
            "k_satisfied": k_satisfied,
            "achieved_k": achieved_k,
            "target_k": config.k_metric,
            "achieved_l": achieved_l,
            "target_l": config.l_metric,
            "achieved_t": round(achieved_t, 4) if achieved_t is not None else None,
            "target_t": config.t_metric,
            "total_records": total_input_records,
            "retained_records": retained_records,
            "suppressed_records": suppressed_records,
            "suppression_rate": round(suppression_rate, 4),
            "num_equivalence_classes": len(ec_sizes),
            "min_equivalence_class_size": min(ec_sizes) if ec_sizes else 0,
            "avg_equivalence_class_size": round(float(np.mean(ec_sizes)), 2)
            if ec_sizes
            else 0.0,
            "max_equivalence_class_size": max(ec_sizes) if ec_sizes else 0,
            "ec_histogram": ec_histogram,
            "l_diversity_results": l_diversity_results,
            "t_closeness_results": t_closeness_results,
            "privacy_risk": risk_metrics.model_dump(),
            "utility_metrics": utility_metrics.model_dump(),
            "config": config.model_dump(),
            "execution_time_ms": execution_time_ms,
        }

        # Step 9: Database Persistence
        run_record = {
            "id": run_id,
            "dataset_id": clean_dataset_id,
            "config_json": json.dumps(config.model_dump()),
            "anonymized_storage_path": str(anon_storage_path),
            "status": "completed",
            "records_input": total_input_records,
            "records_retained": retained_records,
            "records_suppressed": suppressed_records,
            "suppression_rate": round(suppression_rate, 4),
            "achieved_k": achieved_k,
            "achieved_l": achieved_l,
            "achieved_t": round(achieved_t, 4) if achieved_t is not None else None,
            "utility_retention_score": round(
                utility_metrics.composite_utility_score, 2
            ),
            "metrics_json": json.dumps(full_metrics),
            "execution_time_ms": execution_time_ms,
            "error_message": None,
        }
        DatabaseRepository.create_anonymization_run(run_record)

        DatabaseRepository.log_audit(
            action="anonymize_dataset",
            dataset_id=clean_dataset_id,
            run_id=run_id,
            details={
                "k_target": config.k_metric,
                "achieved_k": achieved_k,
                "curs": round(utility_metrics.composite_utility_score, 2),
                "retained": retained_records,
            },
        )

        return full_metrics

    @classmethod
    def get_run(cls, run_id: str) -> Dict[str, Any]:
        """Retrieves anonymization run record from SQLite."""
        clean_id = validate_uuid_id(run_id)
        run = DatabaseRepository.get_anonymization_run(clean_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anonymization run '{run_id}' not found.",
            )
        return run

    @classmethod
    def get_run_df(cls, run_id: str) -> pd.DataFrame:
        """Loads anonymized DataFrame from physical storage."""
        clean_id = validate_uuid_id(run_id)
        anon_path = resolve_safe_path(
            settings.ANONYMIZED_STORAGE_DIR, f"{clean_id}.csv"
        )
        if not anon_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anonymized dataset storage file for run '{run_id}' not found.",
            )
        return pd.read_csv(anon_path)

    @classmethod
    def get_run_analytics(cls, run_id: str) -> Dict[str, Any]:
        """Returns detailed privacy and utility analytics metrics for visual dashboard."""
        run = cls.get_run(run_id)
        metrics = run.get("metrics") or {}
        return metrics

    @classmethod
    def get_run_diff(
        cls,
        run_id: str,
        page: int = 1,
        size: int = 50,
    ) -> Dict[str, Any]:
        """
        Generates paginated side-by-side comparative diff between
        original and anonymized records, flagging transformed, masked,
        and suppressed entries.
        """
        run = cls.get_run(run_id)
        dataset_id = run["dataset_id"]
        orig_df = DatasetService.get_dataset_df(dataset_id)
        anon_df = cls.get_run_df(run_id)

        config = run.get("config") or {}
        qis = set(config.get("quasi_identifiers", []))
        masked_cols = set(config.get("masking_rules", {}).keys())
        gen_cols = set(config.get("generalization_levels", {}).keys())

        total_original_records = len(orig_df)
        total_pages = max(1, math.ceil(total_original_records / size))
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * size
        end_idx = min(total_original_records, start_idx + size)

        # Slice original records for the requested page
        page_orig = orig_df.iloc[start_idx:end_idx]

        diff_rows: List[Dict[str, Any]] = []

        # Map rows in anon_df
        # If anon_df has retained rows, we align by positional or equivalence class
        anon_len = len(anon_df)

        for rel_idx, (orig_idx, orig_row) in enumerate(page_orig.iterrows()):
            abs_idx = start_idx + rel_idx
            is_retained = abs_idx < anon_len

            cell_diffs: Dict[str, Dict[str, Any]] = {}
            if is_retained:
                anon_row = anon_df.iloc[abs_idx]
                row_status = "retained"
            else:
                anon_row = None
                row_status = "suppressed"

            for col in orig_df.columns:
                orig_val = _to_json_safe(orig_row[col])

                if not is_retained:
                    cell_diffs[col] = {
                        "original": orig_val,
                        "anonymized": "[SUPPRESSED]",
                        "change_type": "suppressed",
                    }
                else:
                    raw_anon = anon_row[col] if col in anon_row else None
                    anon_val = _to_json_safe(raw_anon)

                    if col in masked_cols:
                        change_type = "masked"
                    elif col in gen_cols:
                        change_type = "generalized"
                    elif str(orig_val) != str(anon_val):
                        change_type = "modified"
                    else:
                        change_type = "unchanged"

                    cell_diffs[col] = {
                        "original": orig_val,
                        "anonymized": anon_val,
                        "change_type": change_type,
                    }

            diff_rows.append(
                {
                    "row_index": abs_idx,
                    "status": row_status,
                    "cells": cell_diffs,
                }
            )

        return {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "page": page,
            "size": size,
            "total_records": total_original_records,
            "total_pages": total_pages,
            "retained_records": anon_len,
            "suppressed_records": total_original_records - anon_len,
            "columns": list(orig_df.columns),
            "rows": diff_rows,
            "diff": diff_rows,
        }
