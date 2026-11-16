"""
PrivShield Sensitive Data Discovery Engine
Implements a 4-tier hybrid classification pipeline:
1. Column-name heuristic matching (taxonomy tokens across Healthcare, Finance, Education, HR, Government, E-commerce)
2. High-precision regular expression & checksum validation (ISO 7064 Mod 97-10, Luhn, RFC 5322, IPv4/v6, E.164, SSN, Passport)
3. Physical data-type and cardinality profiling
4. Statistical distribution analysis (uniqueness ratio, Shannon entropy)
Returns confidence scores, human-readable explanations, and masked sample previews.
Supports dynamic user overrides and exports detect_sensitive_attributes and discover_dataset.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

from backend.app.models.schemas import ColumnProfile, PiiType, SensitivityCategory
from backend.app.engine.masking import (
    mask_card_number,
    mask_email,
    mask_iban,
    mask_national_id,
    mask_partial,
    mask_phone,
)

# Regex Patterns
REGEX_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
REGEX_JORDAN_PHONE = re.compile(r"^(?:\+962|00962|0)?\s?7[789][\s\d]{7,10}$")
REGEX_GLOBAL_PHONE = re.compile(r"^\+?[1-9]\d{1,3}[\s\-]?(?:\(\d{1,4}\)[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}$")
REGEX_JORDAN_NATIONAL_ID = re.compile(r"^\d{10}$")
REGEX_US_SSN = re.compile(r"^\d{3}-\d{2}-\d{4}$")
REGEX_PASSPORT = re.compile(r"^[A-Z]{1,2}[0-9]{6,9}$")
REGEX_IPV4 = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
REGEX_IPV6 = re.compile(r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$")
REGEX_JORDAN_IBAN = re.compile(r"^JO\d{2}[A-Z]{4}\d{22}$", re.IGNORECASE)
REGEX_GLOBAL_IBAN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$", re.IGNORECASE)
REGEX_POSTAL_CODE = re.compile(r"^\d{5}(?:-\d{4})?$")
REGEX_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}:\d{2})?")
REGEX_CUST_ID = re.compile(r"^(?:JO\-)?CUST\-\d+$", re.IGNORECASE)
REGEX_ICD10 = re.compile(r"^[A-Z][0-9]{2}(?:\.[0-9]{1,4})?$", re.IGNORECASE)
REGEX_MRN = re.compile(r"^(?:MRN\-)?\d{6,10}$", re.IGNORECASE)
REGEX_EMP_ID = re.compile(r"^(?:EMP\-)?\d{4,8}$", re.IGNORECASE)
REGEX_STU_ID = re.compile(r"^(?:STU\-)?\d{6,10}$", re.IGNORECASE)

# Reference dictionaries
JORDANIAN_CITIES: Set[str] = {
    "amman", "zarqa", "irbid", "aqaba", "salt", "madaba",
    "jerash", "ajloun", "mafraq", "karak", "tafilah", "maan",
    "عمان", "الزرقاء", "إربد", "العقبة", "السلط", "مادبا",
    "جرش", "عجلون", "المفرق", "الكرك", "الطفيلة", "معان"
}

GLOBAL_CITIES: Set[str] = {
    "london", "new york", "paris", "berlin", "tokyo", "sydney",
    "toronto", "chicago", "los angeles", "boston", "seattle", "san francisco",
    "dubai", "riyadh", "cairo", "beirut", "doha", "manama", "kuwait city",
    "mumbai", "singapore", "hong kong", "zurich", "geneva", "amsterdam", "madrid"
}

GENDER_VALUES: Set[str] = {
    "m", "f", "male", "female", "other", "unknown", "non-binary", "ذكر", "أنثى"
}

TRANSACTION_CATEGORIES: Set[str] = {
    "shopping", "bills & utilities", "bills", "utilities", "restaurant",
    "atm withdrawal", "atm", "transfer", "healthcare", "education",
    "dining", "groceries", "salary", "investment", "credit card", "debit card",
    "cash", "paypal", "wire transfer"
}

GLOBAL_JOB_TITLES: Set[str] = {
    "software engineer", "nurse", "physician", "doctor", "accountant",
    "data analyst", "product manager", "project manager", "consultant",
    "professor", "teacher", "researcher", "sales manager", "director"
}

GLOBAL_DEPARTMENTS: Set[str] = {
    "engineering", "sales", "marketing", "finance", "human resources", "hr",
    "operations", "cardiology", "neurology", "pediatrics", "oncology",
    "computer science", "mathematics", "biology", "business", "legal"
}

TAXONOMY_KEYWORDS: Dict[PiiType, List[str]] = {
    PiiType.CUSTOMER_NAME: [
        "fullname", "full_name", "name", "cust_name", "customer_name",
        "client_name", "holder_name", "first_name", "last_name",
        "patient_name", "patientname", "student_name", "studentname",
        "employee_name", "employeename", "citizen_name", "worker_name"
    ],
    PiiType.EMAIL: [
        "email", "e_mail", "mail_addr", "cust_email", "contact_email",
        "personal_email", "work_email", "student_email", "corporate_email"
    ],
    PiiType.PHONE_NUMBER: [
        "phone", "mobile", "tel", "cell", "contact_no", "phone_number",
        "msisdn", "cust_mobile_no", "personal_phone", "campus_phone"
    ],
    PiiType.NATIONAL_ID: [
        "nationalid", "national_id", "ssn", "nat_id", "id_number",
        "civil_id", "personal_id", "al_raqam_al_watani", "c_nat_ident"
    ],
    PiiType.SSN: [
        "ssn", "social_security", "social_security_number", "ssn_taxid", "ssn_nationalid"
    ],
    PiiType.PASSPORT: [
        "passport", "passport_no", "passport_number", "passport_id"
    ],
    PiiType.ACCOUNT_NUMBER: [
        "customerid", "customer_id", "custid", "cust_id", "account",
        "account_no", "acc_num", "acct_id", "bank_account", "account_number",
        "patientid", "patient_id", "mrn", "medical_record_number",
        "studentid", "student_id", "employeeid", "employee_id"
    ],
    PiiType.STUDENT_ID: [
        "studentid", "student_id", "student_no", "matriculation_no"
    ],
    PiiType.EMPLOYEE_ID: [
        "employeeid", "employee_id", "staff_id", "emp_id", "worker_id"
    ],
    PiiType.IBAN: ["iban", "iban_code", "bank_iban", "cust_iban", "x_iban_code"],
    PiiType.CARD_NUMBER: [
        "card", "card_no", "cardnumber", "card_number", "pan",
        "credit_card", "debit_card", "cc_num"
    ],
    PiiType.ADDRESS: [
        "address", "street", "residence", "home_addr", "billing_address",
        "shipping_address", "residential_address", "home_address",
        "street_address", "streetaddress"
    ],
    PiiType.IP_ADDRESS: [
        "ip_address", "ip", "client_ip", "ipaddress", "host_ip", "ipv4", "ipv6"
    ],
    PiiType.TAX_ID: [
        "tax_id", "tin", "ein", "taxpayer_id"
    ],
    PiiType.AGE: [
        "age", "cust_age", "patient_age", "years_old", "dob",
        "birth_date", "birthdate", "customer_age", "age_group", "agegroup",
        "household_size", "householdsize"
    ],
    PiiType.GENDER: ["gender", "sex", "cust_gender", "patient_gender", "marital_status", "maritalstatus"],
    PiiType.CITY: [
        "city", "town", "governorate", "municipality", "province",
        "home_city", "branch_city", "shipping_city", "office_location"
    ],
    PiiType.POSTAL_CODE: [
        "zip", "postal", "postalcode", "postal_code", "zip_code", "postcode"
    ],
    PiiType.TIMESTAMP: [
        "timestamp", "date", "tx_date", "time", "created_at", "trans_time",
        "datetime", "transaction_timestamp", "transaction_date", "admission_date",
        "hire_date", "hire_year", "order_date", "enrollment_year", "registration_date"
    ],
    PiiType.MERCHANT: ["merchant", "merchant_name", "vendor", "store", "payee", "shop"],
    PiiType.LOCATION: ["location", "geo", "branch", "branch_location", "coordinates", "state", "home_state", "homestate"],
    PiiType.DEPARTMENT: [
        "department", "dept", "division", "faculty", "major", "major_program", "education_level", "educationlevel"
    ],
    PiiType.JOB_TITLE: [
        "job_title", "job", "title", "position", "role", "occupation"
    ],
    PiiType.AMOUNT: [
        "amount", "amt", "tr_amt", "tx_amt", "trans_amt", "tx_amount",
        "trans_amount", "transactionamount", "transaction_amount",
        "jod_amount", "total", "price", "charge", "hospital_charge",
        "hospitalcharge", "order_total", "billing_amount", "cost",
        "benefit_amount", "benefitamount", "property_assessment", "propertyassessment"
    ],
    PiiType.BALANCE: [
        "balance", "account_balance", "acc_balance", "curr_balance"
    ],
    PiiType.CATEGORY: [
        "category", "transactioncategory", "tx_category", "trans_type", "type", "mcc", "payment_method"
    ],
    PiiType.INCOME: [
        "income", "salary", "base_salary", "annual_income", "monthly_income",
        "earnings", "wage", "annual_bonus", "bonus", "taxable_income", "lifetime_value", "total_spend",
        "pension_tier", "pensiontier"
    ],
    PiiType.LOAN_INFO: [
        "loan", "loan_status", "loanstatus", "loan_amount", "credit_score",
        "creditscore", "debt", "risk_score", "riskscore", "credit_limit",
        "financial_aid_amount", "financial_aid", "churn_risk_score", "churnriskscore"
    ],
    PiiType.DIAGNOSIS: [
        "diagnosis", "diagnosis_code", "diagnosiscode", "diagnosis_description",
        "diagnosisdescription", "condition", "icd", "icd10", "disease",
        "treatment", "disability_status"
    ],
    PiiType.MEDICATION: ["medication", "prescription", "drug", "rx"],
    PiiType.GPA: [
        "gpa", "cumulative_gpa", "cumulativegpa", "grade",
        "academic_standing", "academicstanding", "scholarship_status", "scholarshipstatus",
        "disciplinary_record", "disciplinaryrecord", "disciplinary_action", "disciplinaryaction",
        "performance_rating", "performancerating", "sick_leave_days", "sickleavedays"
    ]
}

PII_TO_CATEGORY: Dict[PiiType, SensitivityCategory] = {
    PiiType.CUSTOMER_NAME: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.EMAIL: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.PHONE_NUMBER: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.NATIONAL_ID: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.ACCOUNT_NUMBER: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.IBAN: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.CARD_NUMBER: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.ADDRESS: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.SSN: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.PASSPORT: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.IP_ADDRESS: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.STUDENT_ID: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.EMPLOYEE_ID: SensitivityCategory.DIRECT_IDENTIFIER,
    PiiType.TAX_ID: SensitivityCategory.DIRECT_IDENTIFIER,

    PiiType.AGE: SensitivityCategory.QUASI_IDENTIFIER,
    PiiType.GENDER: SensitivityCategory.QUASI_IDENTIFIER,
    PiiType.CITY: SensitivityCategory.QUASI_IDENTIFIER,
    PiiType.POSTAL_CODE: SensitivityCategory.QUASI_IDENTIFIER,
    PiiType.TIMESTAMP: SensitivityCategory.QUASI_IDENTIFIER,
    PiiType.MERCHANT: SensitivityCategory.QUASI_IDENTIFIER,
    PiiType.LOCATION: SensitivityCategory.QUASI_IDENTIFIER,
    PiiType.DEPARTMENT: SensitivityCategory.QUASI_IDENTIFIER,
    PiiType.JOB_TITLE: SensitivityCategory.QUASI_IDENTIFIER,

    PiiType.AMOUNT: SensitivityCategory.SENSITIVE_ATTRIBUTE,
    PiiType.BALANCE: SensitivityCategory.SENSITIVE_ATTRIBUTE,
    PiiType.CATEGORY: SensitivityCategory.SENSITIVE_ATTRIBUTE,
    PiiType.INCOME: SensitivityCategory.SENSITIVE_ATTRIBUTE,
    PiiType.LOAN_INFO: SensitivityCategory.SENSITIVE_ATTRIBUTE,
    PiiType.DIAGNOSIS: SensitivityCategory.SENSITIVE_ATTRIBUTE,
    PiiType.MEDICATION: SensitivityCategory.SENSITIVE_ATTRIBUTE,
    PiiType.GPA: SensitivityCategory.SENSITIVE_ATTRIBUTE,

    PiiType.UNKNOWN: SensitivityCategory.INSENSITIVE
}


def validate_iban_mod97(iban_str: str) -> bool:
    """Validate IBAN using ISO 7064 Mod 97-10 checksum."""
    clean = re.sub(r"\s+", "", str(iban_str)).upper()
    if len(clean) < 15 or len(clean) > 34:
        return False
    if not clean[:2].isalpha():
        return False
    rearranged = clean[4:] + clean[:4]
    numeric_string = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    try:
        return int(numeric_string) % 97 == 1
    except ValueError:
        return False


def validate_luhn(card_str: str) -> bool:
    """Validate payment card PAN using Luhn algorithm (Mod 10)."""
    digits = [int(c) for c in str(card_str) if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for idx, d in enumerate(reverse_digits):
        if idx % 2 == 1:
            doubled = d * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def calculate_shannon_entropy(series: pd.Series) -> float:
    """Calculate base-2 Shannon entropy in bits for discrete values."""
    clean = series.dropna().astype(str)
    if len(clean) == 0:
        return 0.0
    probabilities = clean.value_counts(normalize=True).values
    pos_probs = probabilities[probabilities > 0]
    if len(pos_probs) <= 1:
        return 0.0
    entropy = -float(np.sum(pos_probs * np.log2(pos_probs)))
    return max(0.0, entropy)


def calculate_uniqueness_ratio(series: pd.Series) -> float:
    """Calculate the ratio of distinct values to total non-null values."""
    clean = series.dropna()
    if len(clean) == 0:
        return 0.0
    return float(clean.nunique() / len(clean))


def normalize_column_name(col: str) -> str:
    """Normalize column header for heuristic matching."""
    return re.sub(r"[_\-\s]+", "", str(col).lower().strip())


def score_column_name(col_name: str, pii_type: PiiType) -> float:
    """Compute heuristic name score for a candidate PII type."""
    norm_col = normalize_column_name(col_name)
    keywords = TAXONOMY_KEYWORDS.get(pii_type, [])

    for kw in keywords:
        norm_kw = normalize_column_name(kw)
        if norm_col == norm_kw:
            return 1.0
        if norm_kw in norm_col or norm_col in norm_kw:
            return 0.85

    return 0.0


def score_regex_and_checksum(series: pd.Series, pii_type: PiiType) -> Tuple[float, str]:
    """Audit column values against regex and mathematical checksums."""
    sample = series.dropna().astype(str)
    if len(sample) == 0:
        return 0.0, "Empty column"

    sample_size = min(len(sample), 100)
    test_rows = sample.iloc[:sample_size].tolist()

    if pii_type == PiiType.IBAN:
        matches = [
            s for s in test_rows
            if REGEX_JORDAN_IBAN.match(re.sub(r"\s+", "", s)) or REGEX_GLOBAL_IBAN.match(re.sub(r"\s+", "", s))
        ]
        ratio = len(matches) / sample_size
        if ratio >= 0.80:
            valid_checksums = sum(1 for s in matches if validate_iban_mod97(s))
            chk_ratio = valid_checksums / len(matches) if matches else 0
            if chk_ratio >= 0.80:
                pct = int(chk_ratio * 100)
                return 1.0, f"Matched IBAN format with ISO 7064 Mod 97-10 checksum verified on {pct}% of samples"
            return 0.75, "Matched IBAN structure with partial checksum match"
        return 0.0, "No IBAN match"

    if pii_type == PiiType.CARD_NUMBER:
        if pd.api.types.is_float_dtype(series):
            return 0.0, "Float column cannot be card number"
        clean_digits = [re.sub(r"\D", "", s) for s in test_rows]
        matches = [d for d in clean_digits if 13 <= len(d) <= 19]
        ratio = len(matches) / sample_size
        if ratio >= 0.75:
            luhn_valid = sum(1 for d in matches if validate_luhn(d))
            luhn_ratio = luhn_valid / len(matches) if matches else 0
            if luhn_ratio >= 0.80:
                pct = int(luhn_ratio * 100)
                return 1.0, f"Passed Luhn (Mod 10) payment card checksum on {pct}% of samples"
            return 0.65, "Matches 16-digit card length"
        return 0.0, "No card number match"

    if pii_type == PiiType.NATIONAL_ID:
        clean_digits = [re.sub(r"\D", "", s).zfill(10) for s in test_rows if 8 <= len(re.sub(r"\D", "", s)) <= 10]
        matches = [d for d in clean_digits if len(d) == 10 and REGEX_JORDAN_NATIONAL_ID.match(d)]
        ratio = len(matches) / sample_size
        if ratio >= 0.80:
            return 0.95, f"Matched 10-digit National ID format on {ratio * 100:.0f}% of sample rows"
        return 0.0, "No National ID match"

    if pii_type == PiiType.SSN:
        matches = [s for s in test_rows if REGEX_US_SSN.match(s.strip())]
        ratio = len(matches) / sample_size
        if ratio >= 0.70:
            return 0.95, f"Matched US SSN format on {ratio * 100:.0f}% of sample rows"
        return 0.0, "No SSN match"

    if pii_type == PiiType.PASSPORT:
        matches = [s for s in test_rows if REGEX_PASSPORT.match(s.strip())]
        ratio = len(matches) / sample_size
        if ratio >= 0.70:
            return 0.95, f"Matched Passport format on {ratio * 100:.0f}% of sample rows"
        return 0.0, "No passport match"

    if pii_type == PiiType.IP_ADDRESS:
        matches = [s for s in test_rows if REGEX_IPV4.match(s.strip()) or REGEX_IPV6.match(s.strip())]
        ratio = len(matches) / sample_size
        if ratio >= 0.70:
            return 0.95, f"Matched IPv4/IPv6 format on {ratio * 100:.0f}% of sample rows"
        return 0.0, "No IP address match"

    if pii_type == PiiType.ACCOUNT_NUMBER:
        matches = [s for s in test_rows if REGEX_CUST_ID.match(s.strip()) or REGEX_MRN.match(s.strip()) or REGEX_EMP_ID.match(s.strip()) or REGEX_STU_ID.match(s.strip())]
        ratio = len(matches) / sample_size
        if ratio >= 0.70:
            return 0.95, f"Matched Account Identifier pattern on {ratio * 100:.0f}% of samples"
        return 0.0, "No account number match"

    if pii_type == PiiType.PHONE_NUMBER:
        matches = [s for s in test_rows if REGEX_JORDAN_PHONE.match(s) or REGEX_GLOBAL_PHONE.match(re.sub(r"[\s\-\(\)]", "", s))]
        ratio = len(matches) / sample_size
        if ratio >= 0.70:
            return 0.90, f"Matched mobile/international phone format on {ratio * 100:.0f}% of sample rows"
        return 0.0, "No phone match"

    if pii_type == PiiType.EMAIL:
        matches = [s for s in test_rows if REGEX_EMAIL.match(s.strip())]
        ratio = len(matches) / sample_size
        if ratio >= 0.70:
            return 0.95, f"Matched RFC 5322 email syntax on {ratio * 100:.0f}% of sample rows"
        return 0.0, "No email match"

    if pii_type == PiiType.POSTAL_CODE:
        matches = [s for s in test_rows if REGEX_POSTAL_CODE.match(s.strip())]
        ratio = len(matches) / sample_size
        if ratio >= 0.80:
            return 0.85, f"Matched postal code pattern on {ratio * 100:.0f}% of samples"
        return 0.0, "No postal code match"

    if pii_type == PiiType.TIMESTAMP:
        matches = [s for s in test_rows if REGEX_DATE_ISO.match(s.strip())]
        ratio = len(matches) / sample_size
        if ratio >= 0.75:
            return 0.90, f"Matched ISO-8601 date/timestamp format on {ratio * 100:.0f}% of sample rows"
        return 0.0, "No timestamp match"

    if pii_type == PiiType.CITY:
        matches = [s for s in test_rows if s.lower().strip() in JORDANIAN_CITIES or s.lower().strip() in GLOBAL_CITIES]
        ratio = len(matches) / sample_size
        if ratio >= 0.60:
            return 0.95, f"Matched cities taxonomy on {ratio * 100:.0f}% of samples"
        return 0.0, "No city match"

    if pii_type == PiiType.GENDER:
        matches = [s for s in test_rows if s.lower().strip() in GENDER_VALUES]
        ratio = len(matches) / sample_size
        if ratio >= 0.85:
            return 0.95, f"Matched standard gender tokens on {ratio * 100:.0f}% of samples"
        return 0.0, "No gender match"

    if pii_type == PiiType.CATEGORY:
        matches = [s for s in test_rows if s.lower().strip() in TRANSACTION_CATEGORIES]
        ratio = len(matches) / sample_size
        if ratio >= 0.60:
            return 0.85, f"Matched category taxonomy on {ratio * 100:.0f}% of samples"
        return 0.0, "No category match"

    if pii_type == PiiType.DIAGNOSIS:
        matches = [s for s in test_rows if REGEX_ICD10.match(s.strip())]
        ratio = len(matches) / sample_size
        if ratio >= 0.60:
            return 0.95, f"Matched ICD-10 medical diagnostic format on {ratio * 100:.0f}% of samples"
        return 0.0, "No diagnosis match"

    return 0.0, ""


def mask_preview_values(series: pd.Series, specific_type: str, n_samples: int = 5) -> List[str]:
    """Generate masked preview representations of sample values."""
    sample_raw = series.dropna().iloc[:n_samples].tolist()
    masked: List[str] = []
    st = str(specific_type).lower().strip()

    for val in sample_raw:
        if st in ("email", "mail"):
            masked.append(mask_email(val))
        elif st in ("phone_number", "phone", "mobile", "cust_mobile_no"):
            masked.append(mask_phone(val))
        elif st in ("national_id", "c_nat_ident"):
            masked.append(mask_national_id(val))
        elif st in ("ssn", "social_security"):
            masked.append(mask_partial(val, preserve_prefix=0, preserve_suffix=4))
        elif st in ("iban", "bank_iban", "x_iban_code"):
            masked.append(mask_iban(val))
        elif st in ("card_number", "pan", "credit_card", "card"):
            masked.append(mask_card_number(val, format_style="dots"))
        elif st in ("ip_address", "ip"):
            s = str(val).strip()
            parts = s.split(".")
            if len(parts) == 4:
                masked.append(f"{parts[0]}.{parts[1]}.***.***")
            else:
                masked.append("[IP REDACTED]")
        elif st in ("passport", "passport_number"):
            s = str(val).strip()
            masked.append(mask_partial(s, preserve_prefix=2, preserve_suffix=2))
        elif st in ("customer_name", "fullname", "name", "patient_name", "student_name", "employee_name"):
            parts = str(val).split()
            if len(parts) >= 2:
                masked.append(f"{parts[0][0]}*** {parts[-1][0]}***")
            else:
                masked.append(f"{str(val)[:2]}***")
        elif st in ("address", "residential_address", "street"):
            s = str(val).strip()
            masked.append(f"*** {s.split(',')[-1].strip()}" if ',' in s else "*** Street")
        else:
            masked.append(str(val))

    return masked


def discover_column(col_name: str, series: pd.Series, overrides: Optional[Dict[str, str]] = None) -> ColumnProfile:
    """Analyze a single dataframe column and produce its classification profile."""
    unique_count = int(series.nunique(dropna=True))
    null_count = int(series.isna().sum())
    uniqueness = calculate_uniqueness_ratio(series)
    entropy = calculate_shannon_entropy(series)
    norm_col = normalize_column_name(col_name)

    # Check for direct override
    if overrides and col_name in overrides:
        user_cat = overrides[col_name]
        return ColumnProfile(
            column_name=col_name,
            detected_type=user_cat,  # type: ignore
            specific_type=col_name.lower(),
            confidence=1.0,
            explanation=f"User classification override to '{user_cat}'",
            sample_values_masked=mask_preview_values(series, col_name.lower()),
            unique_count=unique_count,
            null_count=null_count,
            is_overridden=True,
            user_category=user_cat  # type: ignore
        )

    # Candidate evaluation across all PII types
    best_candidate: PiiType = PiiType.UNKNOWN
    best_confidence = 0.0
    best_explanation = "No sensitive pattern or keyword detected"

    for pii_type in PiiType:
        if pii_type == PiiType.UNKNOWN:
            continue

        s_name = score_column_name(col_name, pii_type)
        s_regex, regex_expl = score_regex_and_checksum(series, pii_type)

        # Statistical score
        s_stats = 0.0
        expected_cat = PII_TO_CATEGORY.get(pii_type, SensitivityCategory.INSENSITIVE)
        if expected_cat == SensitivityCategory.DIRECT_IDENTIFIER:
            if uniqueness > 0.85 and entropy > 3.0:
                s_stats = 0.90
        elif expected_cat == SensitivityCategory.QUASI_IDENTIFIER:
            if 1 < unique_count < 150:
                s_stats = 0.80
        elif expected_cat == SensitivityCategory.SENSITIVE_ATTRIBUTE:
            if pd.api.types.is_numeric_dtype(series):
                s_stats = 0.85

        # Dtype score
        s_dtype = 0.5
        if pii_type in (PiiType.AMOUNT, PiiType.BALANCE, PiiType.INCOME, PiiType.AGE, PiiType.GPA):
            if pd.api.types.is_numeric_dtype(series):
                s_dtype = 1.0
            else:
                s_dtype = 0.0

        if s_regex >= 0.80:
            confidence = min(1.0, (0.50 * s_regex) + (0.30 * s_name) + (0.15 * s_stats) + (0.05 * s_dtype))
            explanation = regex_expl
            if s_name > 0:
                explanation += f"; column name matches '{pii_type.value}' taxonomy"
        elif s_name >= 0.80:
            confidence = min(1.0, (0.35 * s_regex) + (0.45 * s_name) + (0.15 * s_stats) + (0.05 * s_dtype))
            explanation = f"Column name '{col_name}' matched taxonomy keyword for '{pii_type.value}'"
            if s_regex > 0:
                explanation += f"; {regex_expl}"
        else:
            confidence = min(1.0, (0.40 * s_regex) + (0.30 * s_name) + (0.20 * s_stats) + (0.10 * s_dtype))
            explanation = regex_expl or f"Statistical distribution (uniqueness={uniqueness:.2f}, entropy={entropy:.1f} bits)"

        if confidence > best_confidence:
            best_confidence = confidence
            best_candidate = pii_type
            best_explanation = explanation

    if best_confidence < 0.40:
        detected_category = SensitivityCategory.INSENSITIVE
        specific_str = "general"
        best_explanation = f"Generic operational field (uniqueness: {uniqueness:.2f}, distinct: {unique_count})"
    else:
        detected_category = PII_TO_CATEGORY.get(best_candidate, SensitivityCategory.INSENSITIVE)
        specific_str = best_candidate.value

    # Edge cases for synthetic flags or ID counters
    if norm_col in ("issynthetic", "synthetic", "record_id", "row_id", "id") and best_candidate == PiiType.UNKNOWN:
        detected_category = SensitivityCategory.INSENSITIVE
        specific_str = "flag" if "synthetic" in norm_col else "identifier"
        best_explanation = "Operational record identifier or synthetic certification flag"
        best_confidence = 0.95

    masked_samples = mask_preview_values(series, specific_str)

    return ColumnProfile(
        column_name=col_name,
        detected_type=detected_category.value,  # type: ignore
        specific_type=specific_str,
        confidence=round(best_confidence, 2),
        explanation=best_explanation,
        sample_values_masked=masked_samples,
        unique_count=unique_count,
        null_count=null_count,
        is_overridden=False,
        user_category=None
    )


def discover_dataset(df: pd.DataFrame, overrides: Optional[Dict[str, str]] = None) -> List[ColumnProfile]:
    """Execute sensitive data discovery across all columns of a dataframe."""
    profiles: List[ColumnProfile] = []
    for col in df.columns:
        profile = discover_column(str(col), df[col], overrides=overrides)
        profiles.append(profile)
    return profiles


def detect_sensitive_attributes(df: pd.DataFrame, overrides: Optional[Dict[str, str]] = None) -> List[ColumnProfile]:
    """Alias for discover_dataset for universal backward-compatibility."""
    return discover_dataset(df, overrides=overrides)
