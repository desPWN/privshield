"""
tests_e2e/conftest.py - PrivShield E2E Testing Fixtures, Test Oracles & Validation Utilities.
Provides authoritative reference implementations, synthetic multi-industry data generators,
and mathematical assertion helpers for 4-tier testing.
"""

import os
import sys
import math
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple, Set, Optional

import numpy as np
import pandas as pd
import pytest

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(WORKSPACE_DIR, "backend")
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ==============================================================================
# AUTHORITATIVE REFERENCE ORACLES (MATHEMATICAL SPECIFICATION)
# ==============================================================================

def oracle_equivalence_classes(df: pd.DataFrame, qis: List[str]) -> Dict[Tuple, List[int]]:
    """Partitions DataFrame row indices into Equivalence Classes based on QIs."""
    ec_map = defaultdict(list)
    for idx, row in df.iterrows():
        key = tuple(row[col] for col in qis)
        ec_map[key].append(idx)
    return dict(ec_map)


def oracle_verify_strict_k(df: pd.DataFrame, qis: List[str], k: int) -> Tuple[bool, int, int]:
    """
    Evaluates strict K-anonymity invariant.
    Returns: (is_satisfied, min_class_size, num_classes)
    """
    if len(df) == 0:
        return True, 0, 0
    ec_map = oracle_equivalence_classes(df, qis)
    sizes = [len(indices) for indices in ec_map.values()]
    min_size = min(sizes) if sizes else 0
    return min_size >= k, min_size, len(sizes)


def oracle_verify_distinct_l(df: pd.DataFrame, qis: List[str], sensitive_col: str, l: int) -> Tuple[bool, int, List[Tuple]]:
    """
    Evaluates distinct L-diversity invariant.
    Returns: (is_satisfied, min_distinct_count, list_of_violating_classes)
    """
    if len(df) == 0:
        return True, 0, []
    ec_map = oracle_equivalence_classes(df, qis)
    violating = []
    min_distinct = float("inf")
    for key, indices in ec_map.items():
        sens_vals = set(df.loc[indices, sensitive_col].dropna().tolist())
        distinct_count = len(sens_vals)
        if distinct_count < min_distinct:
            min_distinct = distinct_count
        if distinct_count < l:
            violating.append(key)
    satisfied = len(violating) == 0
    return satisfied, (min_distinct if min_distinct != float("inf") else 0), violating


def oracle_verify_entropy_l(df: pd.DataFrame, qis: List[str], sensitive_col: str, l: int) -> Tuple[bool, float, List[Tuple]]:
    """Evaluates entropy L-diversity invariant: H(S) >= log(L) for each equivalence class."""
    if len(df) == 0:
        return True, 0.0, []
    ec_map = oracle_equivalence_classes(df, qis)
    target_entropy = math.log(l)
    violating = []
    min_observed_entropy = float("inf")
    for key, indices in ec_map.items():
        vals = df.loc[indices, sensitive_col].dropna().tolist()
        if not vals:
            continue
        counts = Counter(vals)
        total = len(vals)
        ent = -sum((c / total) * math.log(c / total) for c in counts.values())
        if ent < min_observed_entropy:
            min_observed_entropy = ent
        if ent < target_entropy - 1e-6:
            violating.append(key)
    satisfied = len(violating) == 0
    return satisfied, (min_observed_entropy if min_observed_entropy != float("inf") else 0.0), violating


def oracle_wasserstein_1d(class_vals: List[float], global_vals: List[float]) -> float:
    """Computes exact 1D Wasserstein-1 (EMD) distance on normalized continuous values."""
    if not class_vals or not global_vals:
        return 0.0
    min_val = min(global_vals)
    max_val = max(global_vals)
    val_range = max_val - min_val
    if val_range == 0:
        return 0.0

    unique_points = sorted(set(global_vals + class_vals))
    m = len(unique_points)
    if m <= 1:
        return 0.0

    n_class = len(class_vals)
    n_global = len(global_vals)
    sorted_class = sorted(class_vals)
    sorted_global = sorted(global_vals)

    emd = 0.0
    for i in range(m - 1):
        x_k = unique_points[i]
        x_next = unique_points[i + 1]
        dx = (x_next - x_k) / val_range

        cdf_class = bisect_right(sorted_class, x_k) / n_class
        cdf_global = bisect_right(sorted_global, x_k) / n_global
        emd += dx * abs(cdf_class - cdf_global)

    return min(1.0, max(0.0, emd))


def oracle_total_variation_distance(class_vals: List[Any], global_vals: List[Any]) -> float:
    """Computes Total Variation Distance (TVD) for categorical distributions."""
    if not class_vals or not global_vals:
        return 0.0
    n_class = len(class_vals)
    n_global = len(global_vals)
    class_counts = Counter(class_vals)
    global_counts = Counter(global_vals)
    all_categories = set(global_counts.keys()).union(class_counts.keys())

    sum_abs_diff = 0.0
    for cat in all_categories:
        p = class_counts.get(cat, 0) / n_class
        q = global_counts.get(cat, 0) / n_global
        sum_abs_diff += abs(p - q)

    return min(1.0, max(0.0, 0.5 * sum_abs_diff))


def oracle_sanitize_cell(val: Any) -> Any:
    """Neutralizes spreadsheet formula injection prefixes (=, +, -, @, \\t, \\r)."""
    if val is None:
        return val
    s = str(val)
    if not s:
        return s
    if s[0] in ("=", "+", "-", "@", "\t", "\r"):
        try:
            float(s)
            if s[0] in ("+", "-"):
                return s
        except ValueError:
            pass
        return "'" + s
    return s


# ==============================================================================
# ASSERTION HELPERS
# ==============================================================================

def assert_strict_k_anonymity(df: pd.DataFrame, qis: List[str], target_k: int):
    """Enforces that NO equivalence class in the dataset has size < target_k."""
    if len(df) == 0:
        return
    satisfied, min_size, num_classes = oracle_verify_strict_k(df, qis, target_k)
    assert satisfied, (
        f"Strict K-Anonymity violated! Target K={target_k}, but minimum class size is {min_size} "
        f"across {num_classes} equivalence classes."
    )


def assert_distinct_l_diversity(df: pd.DataFrame, qis: List[str], sensitive_attr: str, target_l: int):
    """Enforces that all equivalence classes contain at least target_l distinct values."""
    if len(df) == 0:
        return
    satisfied, min_div, violators = oracle_verify_distinct_l(df, qis, sensitive_attr, target_l)
    assert satisfied, (
        f"Distinct L-Diversity violated! Target L={target_l}, but minimum distinct values observed is {min_div}. "
        f"Violating classes count: {len(violators)}"
    )


def assert_t_closeness(df: pd.DataFrame, qis: List[str], sensitive_attr: str, t_threshold: float, is_numeric: bool = True):
    """Enforces that all equivalence classes have distribution distance <= t_threshold."""
    if len(df) == 0:
        return
    ec_map = oracle_equivalence_classes(df, qis)
    global_vals = df[sensitive_attr].dropna().tolist()
    for key, indices in ec_map.items():
        class_vals = df.loc[indices, sensitive_attr].dropna().tolist()
        if is_numeric:
            dist = oracle_wasserstein_1d(class_vals, global_vals)
        else:
            dist = oracle_total_variation_distance(class_vals, global_vals)
        assert dist <= t_threshold + 1e-6, (
            f"T-Closeness violated for EC {key}! Distance={dist:.4f} exceeds threshold T={t_threshold:.4f}"
        )


def assert_curs_in_bounds(curs: float):
    """Validates that Composite Utility-Retention Score is strictly in [0, 100%]."""
    assert isinstance(curs, (int, float)), f"CURS must be numeric, got {type(curs)}"
    assert 0.0 <= curs <= 100.0, f"CURS out of bounds: {curs} not in [0, 100]"


def assert_zero_raw_pii(content: str):
    """Asserts that no unmasked Jordanian National IDs, IBANs, or Card PANs exist in text."""
    nat_ids = re.findall(r"\b(?<!\d)\d{10}(?!\d)\b", content)
    suspicious_nat_ids = [
        nid for nid in nat_ids
        if not nid.startswith("0000") and not nid.endswith("0000")
    ]
    assert len(suspicious_nat_ids) == 0, f"Raw National ID leaked in output: {suspicious_nat_ids[:3]}"

    ibans = re.findall(r"\bJO\d{2}[A-Z0-9]{26}\b", content)
    assert len(ibans) == 0, f"Raw Jordanian IBAN leaked in output: {ibans[:3]}"

    cards = re.findall(r"\b(?:4[0-9]{15}|5[1-5][0-9]{14})\b", content)
    assert len(cards) == 0, f"Raw Credit Card PAN leaked in output: {cards[:3]}"


def assert_zero_raw_pii_extended(content: str):
    """Asserts no raw emails, cards, IBANs, or SSNs are present in output text."""
    emails = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", content)
    assert len(emails) == 0, f"Raw email leaked in output: {emails[:3]}"

    ssns = re.findall(r"\b\d{3}-\d{2}-\d{4}\b", content)
    assert len(ssns) == 0, f"Raw SSN leaked in output: {ssns[:3]}"

    cards = re.findall(r"\b(?:4[0-9]{15}|5[1-5][0-9]{14})\b", content)
    assert len(cards) == 0, f"Raw Card PAN leaked in output: {cards[:3]}"


def assert_formula_safe(csv_text: str):
    """Verifies that no cell in CSV content allows command execution without escaping."""
    for line_idx, line in enumerate(csv_text.splitlines()):
        cells = [c.strip().strip('"') for c in line.split(",")]
        for cell in cells:
            if cell.startswith(("=", "@", "\t", "\r")):
                assert cell.startswith("'"), (
                    f"Vulnerable formula injection detected at line {line_idx+1}: {cell}"
                )
            elif cell.startswith(("+", "-")):
                try:
                    float(cell)
                except ValueError:
                    assert cell.startswith("'"), (
                        f"Vulnerable formula injection with text prefix at line {line_idx+1}: {cell}"
                    )


# ==============================================================================
# PYTEST FIXTURES: MULTI-INDUSTRY SYNTHETIC DATASETS
# ==============================================================================

@pytest.fixture
def hospital_patient_df() -> pd.DataFrame:
    """Generates 120 realistic hospital patient records (Healthcare domain)."""
    np.random.seed(101)
    icd10_codes = ["E11.9", "I10", "J45.909", "M54.5", "K21.9", "F41.1"]
    treatments = ["Inpatient Surgery", "Outpatient Consultation", "Chemotherapy", "Physiotherapy", "Emergency Care"]
    names = ["Alice Smith", "Bob Jones", "Carol White", "David Brown", "Emma Davis", "Frank Miller", "Grace Wilson"]
    zip_codes = ["90210", "90211", "90212", "90213", "90214"]

    records = []
    for i in range(120):
        records.append({
            "MRN": f"MRN-{100000+i}",
            "Patient_Name": names[i % len(names)],
            "National_ID": f"NID{90000000+i}",
            "Age": 18 + (i % 65),
            "Gender": "M" if (i % 2 == 0) else "F",
            "Zip_Code": zip_codes[i % len(zip_codes)],
            "Admission_Date": f"2026-0{(i % 9) + 1:01d}-{(i % 28) + 1:02d}",
            "ICD10_Code": icd10_codes[i % len(icd10_codes)],
            "Treatment_Category": treatments[i % len(treatments)],
            "Total_Charges": round(float(np.random.lognormal(mean=7.5, sigma=0.8)), 2),
            "IsSynthetic": True
        })
    return pd.DataFrame(records)


@pytest.fixture
def bank_transactions_df() -> pd.DataFrame:
    """Generates 120 realistic bank transactions (Finance domain)."""
    np.random.seed(202)
    merchants = ["Apex Retail", "Metro Grocery", "Global Airways", "Cloud Services Inc", "Downtown Bistro"]
    cities = ["New York", "Chicago", "San Francisco", "Austin", "Boston"]
    loan_statuses = ["Current", "30-Days Late", "Paid Off", "Default"]

    records = []
    for i in range(120):
        records.append({
            "Transaction_ID": f"TXN-BNK-{10000+i}",
            "Customer_ID": f"CUST-{5000+i}",
            "IBAN": f"GB29NWBK601613319268{i:04d}",
            "Card_Number": f"411122223333{1000+i:04d}",
            "Email": f"client_{i}@finvault.org",
            "City": cities[i % len(cities)],
            "Age": 21 + (i % 50),
            "Gender": "M" if (i % 2 == 0) else "F",
            "Merchant": merchants[i % len(merchants)],
            "Transaction_Amount": round(float(np.random.lognormal(mean=4.5, sigma=1.0)), 2),
            "Loan_Status": loan_statuses[i % len(loan_statuses)],
            "Timestamp": f"2026-10-{(i % 28) + 1:02d} 11:30:00",
            "IsSynthetic": True
        })
    return pd.DataFrame(records)


@pytest.fixture
def university_students_df() -> pd.DataFrame:
    """Generates 120 realistic university student records (Education domain)."""
    np.random.seed(303)
    majors = ["Computer Science", "Mechanical Engineering", "Economics", "Biology", "Psychology"]
    standings = ["Good Standing", "Academic Probation", "Dean's List", "Honors"]
    states = ["CA", "NY", "TX", "WA", "IL"]
    names = ["Sophia Taylor", "Liam Anderson", "Olivia Thomas", "Noah Jackson", "Ava White"]

    records = []
    for i in range(120):
        records.append({
            "StudentID": f"STU-{70000+i}",
            "Student_Name": names[i % len(names)],
            "SSN": f"900-{10+i%80:02d}-{1000+i:04d}",
            "Birth_Date": f"{1998 + (i % 7)}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "Gender": "F" if (i % 2 == 0) else "M",
            "State": states[i % len(states)],
            "Major": majors[i % len(majors)],
            "GPA": round(float(np.clip(np.random.normal(3.3, 0.4), 1.5, 4.0)), 2),
            "Academic_Standing": standings[i % len(standings)],
            "Credits_Completed": 15 + (i % 105),
            "IsSynthetic": True
        })
    return pd.DataFrame(records)


@pytest.fixture
def employee_records_df() -> pd.DataFrame:
    """Generates 120 realistic employee HR records (Human Resources domain)."""
    np.random.seed(404)
    departments = ["Engineering", "Sales", "Human Resources", "Finance", "Legal"]
    titles = ["Software Engineer", "Account Executive", "HR Generalist", "Financial Analyst", "Legal Counsel"]
    offices = ["Seattle", "Austin", "New York", "Chicago", "Denver"]
    names = ["Lucas Martin", "Mia Garcia", "Ethan Rodriguez", "Harper Martinez", "Benjamin Lee"]

    records = []
    for i in range(120):
        records.append({
            "EmployeeID": f"EMP-{4000+i}",
            "Full_Name": names[i % len(names)],
            "SSN": f"123-{(i%90)+10:02d}-{1000+i:04d}",
            "Department": departments[i % len(departments)],
            "Job_Title": titles[i % len(titles)],
            "Age": 22 + (i % 45),
            "Office_Location": offices[i % len(offices)],
            "Salary": 60000 + ((i % 12) * 5000),
            "Performance_Rating": (i % 5) + 1,
            "Tenure_Years": (i % 15) + 1,
            "IsSynthetic": True
        })
    return pd.DataFrame(records)


@pytest.fixture
def customer_database_df() -> pd.DataFrame:
    """Generates 120 realistic customer records (E-commerce / Customer Databases domain)."""
    np.random.seed(505)
    cities = ["Los Angeles", "Houston", "Miami", "Phoenix", "Philadelphia"]
    streets = ["Oak Street", "Maple Avenue", "Pine Road", "Cedar Lane", "Elm Boulevard"]
    names = ["Alexander Clark", "Charlotte Lewis", "Daniel Hall", "Amelia Allen", "Henry Young"]

    records = []
    for i in range(120):
        records.append({
            "CustomerID": f"CUST-ID-{8000+i}",
            "Customer_Name": names[i % len(names)],
            "Email": f"shopper_{i}@customerhub.io",
            "Phone": f"+1-555-{(i%800)+100:03d}-{1000+i:04d}",
            "IP_Address": f"192.168.{(i % 250) + 1}.{(i % 200) + 1}",
            "Residential_Address": f"{100 + i} {streets[i % len(streets)]}",
            "City": cities[i % len(cities)],
            "Age": 19 + (i % 55),
            "Annual_Income": round(float(np.random.uniform(30000, 140000)), 2),
            "Purchase_Frequency": (i % 20) + 1,
            "IsSynthetic": True
        })
    return pd.DataFrame(records)


@pytest.fixture
def synthetic_jordanian_df() -> pd.DataFrame:
    """Generates a realistic 120-row Jordanian financial transaction dataset for backward compatibility."""
    np.random.seed(42)
    cities = ["Amman", "Zarqa", "Irbid", "Aqaba", "Salt", "Madaba"]
    merchants = ["Carrefour Amman", "City Mall Zain", "Irbid Mall Co", "Aqaba Port DutyFree", "Jordan Telecom"]
    categories = ["Shopping", "Groceries", "Utilities", "Dining", "Transfer"]
    names = [
        "Ahmad Al-Majali", "Fatima Al-Zoubi", "Omar Tarawneh", "Rania Al-Abdullah",
        "Tariq Kasasbeh", "Hala Al-Fayez", "Zaid Al-Husseini", "Noor Haddad"
    ]

    records = []
    for i in range(120):
        c_idx = i % len(cities)
        city = cities[c_idx]
        age = 20 + (i % 55)
        nat_id = f"99{i:08d}"
        iban = f"JO94ARAB{1000+i:04d}00000000{i:010d}"
        card = f"411122223333{1000+i:04d}"
        email = f"user_{i}@bank-jordan.jo"
        phone = f"079{1000000+i:07d}"
        amount = round(float(np.random.lognormal(mean=4.0, sigma=1.0)), 2)
        category = categories[i % len(categories)]
        merchant = merchants[i % len(merchants)]
        timestamp = f"2026-11-{(i % 28) + 1:02d} 14:{i % 60:02d}:00"

        records.append({
            "Transaction_ID": f"TXN-{10000+i}",
            "Customer_Name": names[i % len(names)],
            "National_ID": nat_id,
            "IBAN": iban,
            "Card_Number": card,
            "Email": email,
            "Phone": phone,
            "City": city,
            "Age": age,
            "Gender": "M" if (i % 2 == 0) else "F",
            "Merchant": merchant,
            "Category": category,
            "Transaction_Amount": amount,
            "Timestamp": timestamp,
            "Currency": "JOD",
            "IsSynthetic": True
        })
    return pd.DataFrame(records)


@pytest.fixture
def empty_df() -> pd.DataFrame:
    """Returns an empty DataFrame with standard columns."""
    return pd.DataFrame(columns=[
        "Transaction_ID", "Customer_Name", "National_ID", "IBAN", "City",
        "Age", "Category", "Transaction_Amount", "Sensitive_Val"
    ])


@pytest.fixture
def single_record_df() -> pd.DataFrame:
    """Returns a single-record DataFrame."""
    return pd.DataFrame([{
        "ID": "REC-001",
        "Name": "Sample User",
        "Email": "user@sample.org",
        "SSN": "123-45-6789",
        "City": "Boston",
        "Age": 30,
        "Gender": "F",
        "Sensitive_Val": "Diagnosis_A"
    }])


@pytest.fixture
def uniform_qis_df() -> pd.DataFrame:
    """All 50 records share the exact same Quasi-Identifiers."""
    records = []
    categories = ["Cardiology", "Neurology", "Oncology", "Pediatrics", "Orthopedics"]
    for i in range(50):
        records.append({
            "Record_ID": f"REC-{i}",
            "Name": f"Person {i}",
            "City": "Metropolis",
            "Age": 40,
            "Gender": "M",
            "Category": categories[i % len(categories)],
            "Score": 100.0 + (i * 2.5)
        })
    return pd.DataFrame(records)


@pytest.fixture
def all_unique_qis_df() -> pd.DataFrame:
    """Every record has completely unique Quasi-Identifiers."""
    records = []
    for i in range(25):
        records.append({
            "Record_ID": f"REC-{i}",
            "Name": f"Person {i}",
            "City": f"City_{i}",
            "Age": 20 + i,
            "Gender": "M" if i % 2 == 0 else "F",
            "Postal_Code": f"021{i:02d}",
            "Category": "General",
            "Score": 50.0 + i
        })
    return pd.DataFrame(records)


@pytest.fixture
def formula_injection_df() -> pd.DataFrame:
    """Contains malicious CSV formula injection payloads."""
    return pd.DataFrame([
        {"Customer_Name": "=cmd|' /C calc'!A0", "City": "Boston", "Note": "+1234567", "Amount": 150.0},
        {"Customer_Name": "@SUM(1+1)*cmd|' /C calc'!A0", "City": "Austin", "Note": "-2+3*4", "Amount": 200.0},
        {"Customer_Name": "\tcalc.exe", "City": "Seattle", "Note": "\rtest_payload", "Amount": 50.0},
        {"Customer_Name": "=2+5", "City": "Denver", "Note": "@alert('xss')", "Amount": -75.50},
        {"Customer_Name": "Safe Name", "City": "Boston", "Note": "Regular memo", "Amount": 12.00}
    ])
