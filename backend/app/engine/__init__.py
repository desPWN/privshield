"""
PrivShield Privacy Engine Core Package
Exports mathematical algorithms and evaluation pipelines for:
- Discovery of sensitive multi-industry data (heuristics, regex, ISO 7064 Mod 97-10, Luhn)
- Data masking and format-preserving tokenization
- Domain generalization hierarchies (pluggable numeric, categorical, date/time, geography)
- Strict K-Anonymity with deterministic violation suppression
- Distinct, Entropy, and Recursive L-Diversity
- T-Closeness via 1D Wasserstein EMD and Total Variation Distance
- Multi-scenario privacy risk modeling (Prosecutor, Journalist, Marketer, Linkage, NCP)
- 5-component statistical utility analytics (CURS) and distribution differences
"""

from backend.app.engine.discovery import (
    calculate_shannon_entropy,
    calculate_uniqueness_ratio,
    detect_sensitive_attributes,
    discover_column,
    discover_dataset,
    score_regex_and_checksum,
    validate_iban_mod97,
    validate_luhn,
)
from backend.app.engine.hierarchies import (
    HierarchyRegistry,
    apply_generalization,
    bin_numerical_custom,
    bin_numerical_equal_width,
    bin_numerical_quantiles,
    generalize_age,
    generalize_amount,
    generalize_category,
    generalize_city,
    generalize_education_major,
    generalize_job_title,
    generalize_medical_icd,
    generalize_timestamp,
)
from backend.app.engine.k_anonymity import (
    enforce_strict_k_anonymity,
    partition_equivalence_classes,
)
from backend.app.engine.l_diversity import (
    evaluate_distinct_l_diversity,
    evaluate_entropy_l_diversity,
    evaluate_l_diversity,
    evaluate_recursive_l_diversity,
)
from backend.app.engine.masking import (
    apply_masking,
    apply_masking_rule,
    mask_address,
    mask_card_number,
    mask_email,
    mask_full,
    mask_hash,
    mask_iban,
    mask_ip_address,
    mask_national_id,
    mask_partial,
    mask_passport,
    mask_phone,
    mask_salted_token,
    mask_ssn,
    tokenize_format_preserving,
)
from backend.app.engine.risk import (
    compute_ncp,
    compute_privacy_risk_metrics,
)
from backend.app.engine.t_closeness import (
    compute_categorical_tvd,
    compute_continuous_wasserstein_distance,
    evaluate_t_closeness,
)
from backend.app.engine.utility import (
    compute_categorical_tvd as compute_utility_tvd,
    compute_ks_fidelity,
    compute_summary_distribution_diffs,
    compute_utility_metrics,
)

__all__ = [
    "discover_column",
    "discover_dataset",
    "detect_sensitive_attributes",
    "validate_iban_mod97",
    "validate_luhn",
    "calculate_shannon_entropy",
    "calculate_uniqueness_ratio",
    "score_regex_and_checksum",
    "apply_masking",
    "apply_masking_rule",
    "mask_email",
    "mask_phone",
    "mask_national_id",
    "mask_ssn",
    "mask_passport",
    "mask_iban",
    "mask_card_number",
    "mask_ip_address",
    "mask_address",
    "mask_full",
    "mask_partial",
    "mask_hash",
    "mask_salted_token",
    "tokenize_format_preserving",
    "generalize_city",
    "generalize_age",
    "generalize_amount",
    "generalize_timestamp",
    "generalize_category",
    "generalize_medical_icd",
    "generalize_job_title",
    "generalize_education_major",
    "bin_numerical_equal_width",
    "bin_numerical_quantiles",
    "bin_numerical_custom",
    "apply_generalization",
    "HierarchyRegistry",
    "partition_equivalence_classes",
    "enforce_strict_k_anonymity",
    "evaluate_distinct_l_diversity",
    "evaluate_entropy_l_diversity",
    "evaluate_recursive_l_diversity",
    "evaluate_l_diversity",
    "evaluate_t_closeness",
    "compute_continuous_wasserstein_distance",
    "compute_categorical_tvd",
    "compute_privacy_risk_metrics",
    "compute_ncp",
    "compute_utility_metrics",
    "compute_ks_fidelity",
    "compute_summary_distribution_diffs",
]
