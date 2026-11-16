"""
FinGuard Pydantic Data Models & Schemas
Defines core domain entities, API contracts, discovery profiles,
anonymization configurations, risk estimates, and utility metrics.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class SensitivityCategory(str, Enum):
    DIRECT_IDENTIFIER = "direct_identifier"
    QUASI_IDENTIFIER = "quasi_identifier"
    SENSITIVE_ATTRIBUTE = "sensitive_attribute"
    INSENSITIVE = "insensitive"


class PiiType(str, Enum):
    CUSTOMER_NAME = "customer_name"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    NATIONAL_ID = "national_id"
    ACCOUNT_NUMBER = "account_number"
    IBAN = "iban"
    CARD_NUMBER = "card_number"
    ADDRESS = "address"
    AGE = "age"
    GENDER = "gender"
    CITY = "city"
    POSTAL_CODE = "postal_code"
    TIMESTAMP = "timestamp"
    MERCHANT = "merchant"
    LOCATION = "location"
    AMOUNT = "amount"
    BALANCE = "balance"
    CATEGORY = "category"
    INCOME = "income"
    LOAN_INFO = "loan_info"
    SSN = "ssn"
    PASSPORT = "passport"
    IP_ADDRESS = "ip_address"
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    GPA = "gpa"
    STUDENT_ID = "student_id"
    EMPLOYEE_ID = "employee_id"
    JOB_TITLE = "job_title"
    DEPARTMENT = "department"
    TAX_ID = "tax_id"
    UNKNOWN = "unknown"


class ColumnProfile(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    column_name: str
    detected_type: Literal["direct_identifier", "quasi_identifier", "sensitive_attribute", "insensitive"]
    specific_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    sample_values_masked: List[str]
    unique_count: int
    null_count: int
    is_overridden: bool = False
    user_category: Optional[Literal["direct_identifier", "quasi_identifier", "sensitive_attribute", "insensitive"]] = None


class ColumnOverrideItem(BaseModel):
    column_name: str
    user_category: Literal["direct_identifier", "quasi_identifier", "sensitive_attribute", "insensitive"]
    specific_type: Optional[str] = None
    notes: Optional[str] = None


class ColumnOverrideRequest(BaseModel):
    overrides: List[ColumnOverrideItem]


class AnonymizationConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    processing_mode: Literal["reversible_pseudonymization", "irreversible_anonymization"] = "irreversible_anonymization"
    quasi_identifiers: List[str] = Field(default_factory=list)
    sensitive_attributes: List[str] = Field(default_factory=list)
    k_metric: int = Field(default=5, ge=2, le=10)
    l_metric: Optional[int] = Field(default=None, ge=2, le=10)
    t_metric: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    suppression_strategy: Literal["record", "cell"] = "record"
    max_suppression_pct: float = Field(default=0.50, ge=0.0, le=1.0)
    masking_rules: Dict[str, str] = Field(default_factory=dict)
    generalization_levels: Dict[str, int] = Field(default_factory=dict)


class EquivalenceClassSummary(BaseModel):
    class_id: int
    qi_values: Dict[str, Any]
    size: int
    is_k_satisfied: bool
    record_indices: List[int] = Field(default_factory=list)


class LDiversityViolationDetail(BaseModel):
    qi_values: Dict[str, Any]
    class_size: int
    distinct_count: int
    values_present: List[Any]
    frequency_breakdown: Dict[str, int]


class LDiversityAuditResult(BaseModel):
    target_l: int
    sensitive_attribute: str
    satisfied: bool
    total_classes: int
    violating_classes_count: int
    violating_records_count: int
    min_observed_distinct_values: int
    violation_details: List[LDiversityViolationDetail] = Field(default_factory=list)


class TClosenessViolationDetail(BaseModel):
    class_id: int
    qi_values: Dict[str, Any]
    class_size: int
    distance: float
    threshold_t: float
    is_violation: bool


class TClosenessAuditResult(BaseModel):
    target_t: float
    sensitive_attribute: str
    attribute_type: Literal["numeric", "categorical"]
    satisfied: bool
    total_classes: int
    violating_classes_count: int
    violating_records_count: int
    max_observed_distance: float
    average_distance: float
    violation_details: List[TClosenessViolationDetail] = Field(default_factory=list)


class PrivacyRiskMetrics(BaseModel):
    prosecutor_risk: float
    journalist_risk: float
    marketer_risk: float
    average_risk: float
    transaction_linkage_risk: float
    smallest_class_size: int
    largest_class_size: int
    average_class_size: float
    k_achieved: int


class UtilityMetrics(BaseModel):
    record_retention: float
    numerical_distribution_fidelity: float
    categorical_distribution_fidelity: float
    correlation_retention: float
    granularity_retention: float
    composite_utility_score: float
    mean_relative_error: Dict[str, float] = Field(default_factory=dict)
    std_relative_error: Dict[str, float] = Field(default_factory=dict)
    suppressed_records: int
    suppression_rate: float


class AnonymizationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    anonymized_df: Any = None
    processing_mode: str = "irreversible_anonymization"
    is_reversible: bool = False
    token_mapping_count: int = 0
    k_satisfied: bool
    achieved_k: int
    total_records: int
    retained_records: int
    suppressed_records: int
    suppression_rate: float
    num_equivalence_classes: int
    min_equivalence_class_size: int
    avg_equivalence_class_size: float
    l_diversity_results: Dict[str, Any] = Field(default_factory=dict)
    t_closeness_results: Dict[str, Any] = Field(default_factory=dict)
    privacy_risk: PrivacyRiskMetrics
    utility_metrics: UtilityMetrics


class IndustryProfile(BaseModel):
    id: str
    name: str
    industry: str
    description: str
    icon: str
    suggested_rules: Dict[str, Any] = Field(default_factory=dict)
    is_built_in: bool = True


class TokenLookupRequest(BaseModel):
    token: str
    passkey: str
    run_id: Optional[str] = None
    column_name: Optional[str] = None
    justification: Optional[str] = "Authorized de-pseudonymization investigation"


class TokenLookupResponse(BaseModel):
    found: bool
    original_value: Optional[str] = None
    column_name: Optional[str] = None
    run_id: Optional[str] = None
    token: str


class DatasetRestoreRequest(BaseModel):
    dataset_id: str
    passkey: str
    actor: Optional[str] = "admin"
    justification: Optional[str] = "Statutory data recovery request"


class RecoveryAuditLogItem(BaseModel):
    id: int
    dataset_id: str
    run_id: Optional[str] = None
    actor: str
    ip_address: str
    action: str
    token_queried: Optional[str] = None
    records_recovered: int
    justification: str
    timestamp: str

