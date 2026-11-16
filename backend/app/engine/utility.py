"""
FinGuard Data Utility Analytics Engine
Quantifies information preservation across 5 mathematical dimensions:
1. Record Retention Metric (U_rec, weight 0.25)
2. Numerical Distribution Fidelity (U_num, weight 0.25 via Kolmogorov-Smirnov test)
3. Categorical Distribution Fidelity (U_cat, weight 0.20 via Total Variation Distance)
4. Correlation Matrix Preservation (U_corr, weight 0.15 via MAE on Pearson correlations)
5. Attribute Granularity / Information Loss (U_gran, weight 0.15 via Normalized Certainty Penalty)
Computes the Composite Utility-Retention Score (CURS in [0, 100%]).
"""

from collections import Counter
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from backend.app.models.schemas import UtilityMetrics


def compute_ks_fidelity(orig_series: pd.Series, anon_series: pd.Series) -> float:
    """Compute 1 - Kolmogorov-Smirnov 2-sample test statistic."""
    clean_orig = orig_series.dropna().astype(float).values
    clean_anon = anon_series.dropna().astype(float).values

    if len(clean_orig) == 0 or len(clean_anon) == 0:
        return 0.0

    res = stats.ks_2samp(clean_orig, clean_anon)
    ks_stat = float(res.statistic)
    return float(np.clip(1.0 - ks_stat, 0.0, 1.0))


def compute_categorical_tvd(orig_series: pd.Series, anon_series: pd.Series) -> float:
    """Compute Total Variation Distance between original and anonymized categorical series."""
    clean_orig = orig_series.dropna().astype(str).tolist()
    clean_anon = anon_series.dropna().astype(str).tolist()

    if not clean_orig or not clean_anon:
        return 1.0

    n_orig = len(clean_orig)
    n_anon = len(clean_anon)

    orig_counts = Counter(clean_orig)
    anon_counts = Counter(clean_anon)
    all_cats = set(orig_counts.keys()).union(anon_counts.keys())

    sum_abs_diff = 0.0
    for cat in all_cats:
        p = orig_counts.get(cat, 0) / n_orig
        q = anon_counts.get(cat, 0) / n_anon
        sum_abs_diff += abs(p - q)

    tvd = 0.5 * sum_abs_diff
    return float(np.clip(tvd, 0.0, 1.0))


def compute_utility_metrics(
    original_df: pd.DataFrame,
    anonymized_df: pd.DataFrame,
    quasi_identifiers: Optional[List[str]] = None,
    generalization_levels: Optional[Dict[str, int]] = None,
    max_hierarchy_depth: int = 3
) -> UtilityMetrics:
    """
    Computes 5-component utility analysis and CURS between original and anonymized DataFrames.
    """
    n_orig = len(original_df)
    n_anon = len(anonymized_df)

    # Edge cases
    if n_orig == 0:
        return UtilityMetrics(
            record_retention=1.0,
            numerical_distribution_fidelity=1.0,
            categorical_distribution_fidelity=1.0,
            correlation_retention=1.0,
            granularity_retention=1.0,
            composite_utility_score=100.0,
            mean_relative_error={},
            std_relative_error={},
            suppressed_records=0,
            suppression_rate=0.0
        )

    suppressed_count = max(0, n_orig - n_anon)
    suppression_rate = suppressed_count / n_orig

    # If all records suppressed, utility is 0
    if n_anon == 0:
        return UtilityMetrics(
            record_retention=0.0,
            numerical_distribution_fidelity=0.0,
            categorical_distribution_fidelity=0.0,
            correlation_retention=0.0,
            granularity_retention=0.0,
            composite_utility_score=0.0,
            mean_relative_error={},
            std_relative_error={},
            suppressed_records=suppressed_count,
            suppression_rate=1.0
        )

    # 1. Record Retention Metric (U_rec)
    u_rec = float(n_anon / n_orig)

    # Common columns
    common_cols = [c for c in original_df.columns if c in anonymized_df.columns]

    # Identify numeric and categorical columns
    numeric_cols: List[str] = []
    categorical_cols: List[str] = []

    for c in common_cols:
        if pd.api.types.is_numeric_dtype(original_df[c]) and pd.api.types.is_numeric_dtype(anonymized_df[c]):
            # Avoid single-value identifiers or booleans
            if original_df[c].nunique() > 1:
                numeric_cols.append(c)
        else:
            if original_df[c].nunique() > 1:
                categorical_cols.append(c)

    # 2. Numerical Distribution Fidelity (U_num)
    mean_rel_err: Dict[str, float] = {}
    std_rel_err: Dict[str, float] = {}
    ks_scores: List[float] = []

    for col in numeric_cols:
        ks_fidelity = compute_ks_fidelity(original_df[col], anonymized_df[col])
        ks_scores.append(ks_fidelity)

        mu_orig = float(original_df[col].mean())
        mu_anon = float(anonymized_df[col].mean())
        std_orig = float(original_df[col].std())
        std_anon = float(anonymized_df[col].std())

        mean_err = abs(mu_anon - mu_orig) / (abs(mu_orig) + 1e-6)
        std_err = abs(std_anon - std_orig) / (abs(std_orig) + 1e-6)

        mean_rel_err[col] = round(float(mean_err), 4)
        std_rel_err[col] = round(float(std_err), 4)

    u_num = float(np.mean(ks_scores)) if ks_scores else 1.0

    # 3. Categorical Distribution Fidelity (U_cat)
    cat_scores: List[float] = []
    for col in categorical_cols:
        tvd = compute_categorical_tvd(original_df[col], anonymized_df[col])
        cat_scores.append(1.0 - tvd)

    u_cat = float(np.mean(cat_scores)) if cat_scores else 1.0

    # 4. Correlation Matrix Preservation (U_corr)
    if len(numeric_cols) >= 2:
        try:
            orig_corr = original_df[numeric_cols].corr(method="pearson").values
            anon_corr = anonymized_df[numeric_cols].corr(method="pearson").values

            # Replace any NaNs in correlation matrix with 0
            orig_corr = np.nan_to_num(orig_corr, nan=0.0)
            anon_corr = np.nan_to_num(anon_corr, nan=0.0)

            k = len(numeric_cols)
            # Off-diagonal elements
            triu_indices = np.triu_indices(k, k=1)
            mae_corr = float(np.mean(np.abs(orig_corr[triu_indices] - anon_corr[triu_indices])))
            u_corr = float(np.clip(1.0 - mae_corr, 0.0, 1.0))
        except Exception:
            u_corr = 1.0
    else:
        u_corr = 1.0

    # 5. Granularity / Information Loss (U_gran)
    # Using Normalized Certainty Penalty (NCP)
    if generalization_levels and quasi_identifiers:
        penalties: List[float] = []
        for col in quasi_identifiers:
            level = generalization_levels.get(col, 0)
            penalties.append(min(1.0, level / max(1, max_hierarchy_depth)))
        avg_penalty = float(np.mean(penalties)) if penalties else 0.0
        u_gran = float(np.clip(1.0 - avg_penalty, 0.0, 1.0))
    else:
        u_gran = 1.0

    # Composite Utility-Retention Score (CURS)
    # 0.25 * U_rec + 0.25 * U_num + 0.20 * U_cat + 0.15 * U_corr + 0.15 * U_gran
    curs_normalized = (
        0.25 * u_rec +
        0.25 * u_num +
        0.20 * u_cat +
        0.15 * u_corr +
        0.15 * u_gran
    )
    curs = float(np.clip(curs_normalized * 100.0, 0.0, 100.0))

    return UtilityMetrics(
        record_retention=round(u_rec, 4),
        numerical_distribution_fidelity=round(u_num, 4),
        categorical_distribution_fidelity=round(u_cat, 4),
        correlation_retention=round(u_corr, 4),
        granularity_retention=round(u_gran, 4),
        composite_utility_score=round(curs, 2),
        mean_relative_error=mean_rel_err,
        std_relative_error=std_rel_err,
        suppressed_records=suppressed_count,
        suppression_rate=round(suppression_rate, 4)
    )


def compute_summary_distribution_diffs(
    original_df: pd.DataFrame,
    anonymized_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Computes detailed summary distribution comparison between original and anonymized dataframes:
    mean, median, standard deviation relative errors, missing value differentials, and distribution distances.
    """
    common_cols = [c for c in original_df.columns if c in anonymized_df.columns]
    column_stats: Dict[str, Dict[str, Any]] = {}

    for c in common_cols:
        is_num = (
            pd.api.types.is_numeric_dtype(original_df[c])
            and pd.api.types.is_numeric_dtype(anonymized_df[c])
        )

        nulls_orig = int(original_df[c].isna().sum())
        nulls_anon = int(anonymized_df[c].isna().sum())

        if is_num and original_df[c].dropna().count() > 0 and anonymized_df[c].dropna().count() > 0:
            mu_orig = float(original_df[c].mean())
            mu_anon = float(anonymized_df[c].mean())
            med_orig = float(original_df[c].median())
            med_anon = float(anonymized_df[c].median())
            std_orig = float(original_df[c].std())
            std_anon = float(anonymized_df[c].std())

            mean_err = abs(mu_anon - mu_orig) / (abs(mu_orig) + 1e-6)
            med_err = abs(med_anon - med_orig) / (abs(med_orig) + 1e-6)
            std_err = abs(std_anon - std_orig) / (abs(std_orig) + 1e-6)
            ks_score = compute_ks_fidelity(original_df[c], anonymized_df[c])

            column_stats[c] = {
                "type": "numeric",
                "mean_original": round(mu_orig, 4),
                "mean_anonymized": round(mu_anon, 4),
                "mean_relative_error": round(float(mean_err), 4),
                "median_original": round(med_orig, 4),
                "median_anonymized": round(med_anon, 4),
                "median_relative_error": round(float(med_err), 4),
                "std_original": round(std_orig, 4),
                "std_anonymized": round(std_anon, 4),
                "std_relative_error": round(float(std_err), 4),
                "ks_fidelity": round(ks_score, 4),
                "null_count_original": nulls_orig,
                "null_count_anonymized": nulls_anon,
            }
        else:
            tvd = compute_categorical_tvd(original_df[c], anonymized_df[c])
            column_stats[c] = {
                "type": "categorical",
                "tvd_distance": round(tvd, 4),
                "distribution_fidelity": round(1.0 - tvd, 4),
                "null_count_original": nulls_orig,
                "null_count_anonymized": nulls_anon,
            }

    return {
        "record_count_original": len(original_df),
        "record_count_anonymized": len(anonymized_df),
        "suppression_impact_records": max(0, len(original_df) - len(anonymized_df)),
        "columns": column_stats
    }

