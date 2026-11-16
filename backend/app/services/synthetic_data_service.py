"""
PrivShield Multi-Industry Synthetic Dataset Generator
Generates realistic, certified synthetic datasets for multi-industry evaluation:
1. Hospital Patient Records (Healthcare)
2. Bank Transactions (Finance)
3. University Student Records (Education)
4. Corporate Employee Records (Human Resources)
5. E-Commerce Customer Database (Online Retail)
Each dataset follows domain-specific schemas, realistic statistical distributions,
valid mathematical checksums (Luhn, Mod 97-10), and zero hardcoded column dependencies.
"""

from pathlib import Path
import random
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from backend.app.core.config import settings


def _generate_luhn_card(bin_prefix: str = "4123", length: int = 16, rng: Optional[random.Random] = None) -> str:
    r = rng or random
    digits = [int(c) for c in bin_prefix]
    needed = length - 1 - len(digits)
    digits.extend([r.randint(0, 9) for _ in range(needed)])
    # Calculate checksum digit
    chk = 0
    reverse_digits = digits[::-1]
    for idx, d in enumerate(reverse_digits):
        if idx % 2 == 0:
            doubled = d * 2
            chk += (doubled - 9) if doubled > 9 else doubled
        else:
            chk += d
    check_digit = (10 - (chk % 10)) % 10
    digits.append(check_digit)
    raw = "".join(str(d) for d in digits)
    return f"{raw[:4]} {raw[4:8]} {raw[8:12]} {raw[12:]}"


def _generate_valid_iban(country_code: str = "JO", bank_code: str = "ARAB", rng: Optional[random.Random] = None) -> str:
    r = rng or random
    account_digits = "".join(str(r.randint(0, 9)) for _ in range(22))
    b_code = (bank_code + "XXXX")[:4].upper()
    # Compute check digits: rearranged = b_code + account_digits + country_code + "00"
    rearranged = b_code + account_digits + country_code + "00"
    num_str = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    mod = int(num_str) % 97
    chk = 98 - mod
    chk_str = f"{chk:02d}"
    return f"{country_code}{chk_str}{b_code}{account_digits}"


FIRST_NAMES = [
    "Ahmad", "Omar", "Yousef", "Tareq", "Zaid", "Hamza", "Abdullah", "Khaled",
    "Rania", "Noor", "Huda", "Fatima", "Salma", "Layla", "Dina", "Yasmin",
    "James", "Emily", "Michael", "Sophia", "Daniel", "Emma", "David", "Olivia"
]

LAST_NAMES = [
    "Al-Majali", "Haddad", "Al-Zubi", "Al-Khatib", "Obeidat", "Al-Qudah",
    "Tarawneh", "Masri", "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller"
]

CITIES = ["Amman", "Zarqa", "Irbid", "Aqaba", "Salt", "Madaba", "Jerash", "Mafraq"]


def generate_hospital_dataset(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic Hospital Patient Records dataset."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    diagnoses = [
        ("I10", "Essential (Primary) Hypertension", "Antihypertensive therapy"),
        ("E11.9", "Type 2 Diabetes Mellitus without complications", "Metformin & Diet"),
        ("J45.0", "Predominantly Allergic Asthma", "Inhaled Corticosteroids"),
        ("K21.9", "Gastro-esophageal Reflux Disease", "Proton Pump Inhibitors"),
        ("M54.5", "Low Back Pain", "Physical Therapy & NSAIDs"),
        ("F32.9", "Major Depressive Disorder, Unspecified", "Psychotherapy & SSRIs"),
        ("C34.9", "Malignant Neoplasm of Bronchus/Lung", "Oncology Protocol Chemotherapy"),
        ("Z00.0", "General Medical Examination", "Routine Annual Screening"),
    ]

    rows = []
    base_charge = np_rng.lognormal(mean=7.5, sigma=0.8, size=n_rows)

    for i in range(n_rows):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        name = f"{first} {last}"
        diag_code, diag_desc, treatment = rng.choice(diagnoses)
        age = int(np_rng.integers(18, 88))
        gender = rng.choice(["M", "F"])
        city = rng.choice(CITIES)
        postal = f"{rng.randint(11100, 11999)}"
        charge = round(float(np.clip(base_charge[i], 120.0, 45000.0)), 2)
        lab_val = round(float(np_rng.normal(loc=110.0, scale=25.0)), 1)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        adm_date = f"2025-{month:02d}-{day:02d}"

        rows.append({
            "PatientID": f"PAT-{100000 + i}",
            "PatientName": name,
            "MRN": f"MRN-{8000000 + i}",
            "SSN": f"{rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}",
            "Phone": f"+962 7{rng.choice(['7', '8', '9'])} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "Email": f"{first.lower()}.{last.lower().replace('-', '')}{i}@hospital-patient.org",
            "StreetAddress": f"{rng.randint(12, 980)} Zahran St, {city}",
            "Age": age,
            "Gender": gender,
            "City": city,
            "PostalCode": postal,
            "AdmissionDate": adm_date,
            "DiagnosisCode": diag_code,
            "DiagnosisDescription": diag_desc,
            "Treatment": treatment,
            "LabResultNumeric": lab_val,
            "HospitalCharge": charge,
            "IsSynthetic": True,
        })
    return pd.DataFrame(rows)


def generate_bank_transactions_dataset(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic Bank Transactions dataset."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    amounts = np_rng.lognormal(mean=4.2, sigma=1.1, size=n_rows)
    balances = np_rng.lognormal(mean=7.8, sigma=1.2, size=n_rows)
    credit_scores = np_rng.normal(loc=680, scale=65, size=n_rows)

    rows = []
    for i in range(n_rows):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        name = f"{first} {last}"
        age = int(np_rng.integers(20, 75))
        city = rng.choice(CITIES)
        iban = _generate_valid_iban("JO", "ARAB", rng)
        card = _generate_luhn_card("4123", 16, rng)
        nat_id = f"{rng.randint(90, 99)}{rng.randint(10000000, 99999999)}"[:10]
        amt = round(float(np.clip(amounts[i], 5.0, 9500.0)), 2)
        bal = round(float(np.clip(balances[i], 50.0, 150000.0)), 2)
        cs = int(np.clip(credit_scores[i], 320, 850))
        loan_status = rng.choice(["Approved", "Current", "Fully Paid", "Under Review", "Defaulted"])
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        hour = rng.randint(0, 23)
        tx_date = f"2025-{month:02d}-{day:02d}T{hour:02d}:30:00"

        rows.append({
            "AccountID": f"ACC-{200000 + i}",
            "CustomerName": name,
            "NationalID": nat_id,
            "Email": f"{first.lower()}.{last.lower().replace('-', '')}{i}@bank-client.jo",
            "Phone": f"+962 7{rng.choice(['7', '8', '9'])} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "IBAN": iban,
            "CardNumber": card,
            "CustomerAge": age,
            "Gender": rng.choice(["M", "F"]),
            "BranchCity": city,
            "PostalCode": f"{rng.randint(11100, 11999)}",
            "TransactionDate": tx_date,
            "TransactionAmount": amt,
            "AccountBalance": bal,
            "CreditScore": cs,
            "LoanStatus": loan_status,
            "IsSynthetic": True,
        })
    return pd.DataFrame(rows)


def generate_university_students_dataset(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic University Student Records dataset."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    majors = [
        "Computer Science", "Software Engineering", "Data Science",
        "Electrical Engineering", "Civil Engineering", "Nursing",
        "Business Administration", "Accounting", "Finance", "Psychology"
    ]
    standings = ["Dean's List", "Good Standing", "Satisfactory", "Academic Warning", "Probation"]

    rows = []
    gpas = np_rng.normal(loc=3.15, scale=0.45, size=n_rows)
    aid_amounts = np_rng.uniform(0, 15000, size=n_rows)

    for i in range(n_rows):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        gpa = round(float(np.clip(gpas[i], 1.50, 4.00)), 2)
        aid = round(float(aid_amounts[i]), 2)
        standing = rng.choice(standings) if gpa >= 2.0 else "Probation"
        major = rng.choice(majors)
        enroll_yr = rng.choice([2021, 2022, 2023, 2024, 2025])
        age = int(np_rng.integers(18, 28))
        city = rng.choice(CITIES)

        rows.append({
            "StudentID": f"STU-{300000 + i}",
            "FullName": f"{first} {last}",
            "PersonalEmail": f"{first.lower()}.{last.lower().replace('-', '')}{i}@student-campus.edu",
            "CampusPhone": f"+962 7{rng.choice(['7', '8', '9'])} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "HomeAddress": f"{rng.randint(10, 450)} University Way, {city}",
            "Age": age,
            "Gender": rng.choice(["M", "F"]),
            "HomeCity": city,
            "HomeState": "Capital District",
            "EnrollmentYear": enroll_yr,
            "Major": major,
            "CumulativeGPA": gpa,
            "AcademicStanding": standing,
            "FinancialAidAmount": aid,
            "ScholarshipStatus": "Merit Scholarship" if gpa >= 3.75 else ("Need-Based Aid" if aid > 5000 else "None"),
            "IsSynthetic": True,
        })
    return pd.DataFrame(rows)


def generate_employee_records_dataset(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic Corporate Employee Records dataset."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    departments = [
        "Engineering & Technology", "Data & Analytics", "Finance & Accounting",
        "Human Resources", "Sales & Marketing", "Corporate Business"
    ]
    ed_levels = ["Bachelor's", "Master's", "Ph.D.", "Associate Degree", "High School"]

    rows = []
    salaries = np_rng.normal(loc=72000, scale=22000, size=n_rows)
    bonuses = np_rng.uniform(1000, 25000, size=n_rows)

    for i in range(n_rows):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        dept = rng.choice(departments)
        salary = round(float(np.clip(salaries[i], 32000.0, 210000.0)), 2)
        bonus = round(float(bonuses[i]), 2)
        rating = rng.choice(["Exceeds Expectations", "Meets Expectations", "Needs Improvement", "Outstanding"])
        hire_yr = rng.choice([2016, 2018, 2020, 2022, 2024, 2025])
        age = int(np_rng.integers(22, 64))
        city = rng.choice(CITIES)

        rows.append({
            "EmployeeID": f"EMP-{400000 + i}",
            "FullName": f"{first} {last}",
            "WorkEmail": f"{first.lower()}.{last.lower().replace('-', '')}{i}@enterprise-corp.com",
            "PersonalPhone": f"+962 7{rng.choice(['7', '8', '9'])} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "NationalID": f"{rng.randint(90, 99)}{rng.randint(10000000, 99999999)}"[:10],
            "ResidentialAddress": f"{rng.randint(1, 990)} Queen Rania St, {city}",
            "Age": age,
            "Gender": rng.choice(["M", "F"]),
            "OfficeLocation": city,
            "Department": dept,
            "HireYear": hire_yr,
            "EducationLevel": rng.choice(ed_levels),
            "BaseSalary": salary,
            "AnnualBonus": bonus,
            "PerformanceRating": rating,
            "DisciplinaryAction": rng.choice(["None", "None", "None", "Written Warning", "Verbal Warning"]),
            "IsSynthetic": True,
        })
    return pd.DataFrame(rows)


def generate_customer_database_dataset(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic E-Commerce Customer Database."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    age_groups = ["[18-24]", "[25-34]", "[35-44]", "[45-54]", "55+"]
    rows = []
    incomes = np_rng.normal(loc=58000, scale=18000, size=n_rows)
    limits = np_rng.uniform(1000, 25000, size=n_rows)
    ltvs = np_rng.lognormal(mean=6.5, sigma=0.9, size=n_rows)

    for i in range(n_rows):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        city = rng.choice(CITIES)
        income = round(float(np.clip(incomes[i], 18000.0, 180000.0)), 2)
        limit = round(float(np.clip(limits[i], 500.0, 50000.0)), 2)
        ltv = round(float(np.clip(ltvs[i], 50.0, 45000.0)), 2)
        churn = round(float(rng.uniform(0.01, 0.95)), 3)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        reg_date = f"2024-{month:02d}-{day:02d}"

        ip_addr = f"{rng.randint(11, 210)}.{rng.randint(1, 250)}.{rng.randint(1, 250)}.{rng.randint(1, 250)}"

        rows.append({
            "CustomerID": f"CUST-{500000 + i}",
            "FullName": f"{first} {last}",
            "Email": f"{first.lower()}.{last.lower().replace('-', '')}{i}@shop-retail.com",
            "PhoneNumber": f"+962 7{rng.choice(['7', '8', '9'])} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "BillingAddress": f"{rng.randint(5, 780)} Mecca St, {city}",
            "IPAddress": ip_addr,
            "AgeGroup": rng.choice(age_groups),
            "Gender": rng.choice(["M", "F"]),
            "City": city,
            "State": "Capital Governorate",
            "PostalCode": f"{rng.randint(11100, 11999)}",
            "RegistrationDate": reg_date,
            "AnnualIncome": income,
            "CreditLimit": limit,
            "LifetimeValue": ltv,
            "ChurnRiskScore": churn,
            "IsSynthetic": True,
        })
    return pd.DataFrame(rows)


def generate_government_dataset(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic Civil Registry and Public Sector dataset."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    marital_statuses = ["Married", "Single", "Divorced", "Widowed"]
    disability_options = ["None", "None", "None", "Partial", "Total"]
    pension_tiers = ["Tier 1", "Tier 2", "Tier 3", "None"]

    incomes = np_rng.normal(loc=48000, scale=16000, size=n_rows)
    benefits = np_rng.exponential(scale=350, size=n_rows)
    assessments = np_rng.normal(loc=95000, scale=35000, size=n_rows)

    rows = []
    for i in range(n_rows):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        city = rng.choice(CITIES)
        nat_id = f"{rng.randint(90, 99)}{rng.randint(10000000, 99999999)}"[:10]
        passport = f"P{rng.randint(10000000, 99999999)}"
        tax_id = f"TIN-{rng.randint(10000000, 99999999)}"
        phone = f"+962 7{rng.choice(['7', '8', '9'])} {rng.randint(100, 999)} {rng.randint(1000, 9999)}"
        age = int(np_rng.integers(18, 85))
        income = round(float(np.clip(incomes[i], 12000.0, 150000.0)), 2)
        benefit = round(float(np.clip(benefits[i], 0.0, 2500.0)), 2)
        assessment = round(float(np.clip(assessments[i], 20000.0, 450000.0)), 2)

        rows.append({
            "Citizen_Name": f"{first} {last}",
            "National_ID": nat_id,
            "Passport_Number": passport,
            "Tax_ID": tax_id,
            "Residential_Address": f"{rng.randint(1, 800)} Al-Dustour St, {city}",
            "Phone": phone,
            "Age": age,
            "Gender": rng.choice(["M", "F"]),
            "Municipality": city,
            "Postal_Code": f"{rng.randint(11100, 11999)}",
            "Marital_Status": rng.choice(marital_statuses),
            "Household_Size": int(rng.randint(1, 8)),
            "Taxable_Income": income,
            "Benefit_Amount": benefit,
            "Disability_Status": rng.choice(disability_options),
            "Property_Assessment": assessment,
            "Pension_Tier": rng.choice(pension_tiers),
            "IsSynthetic": True,
        })
    return pd.DataFrame(rows)


def generate_industry_dataset(industry: str, n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Dispatches dataset generation for specified industry name."""
    ind = industry.lower().strip()
    if ind in ("healthcare", "hospital", "patient"):
        return generate_hospital_dataset(n_rows, seed=seed)
    if ind in ("finance", "banking", "bank"):
        return generate_bank_transactions_dataset(n_rows, seed=seed)
    if ind in ("education", "university", "student"):
        return generate_university_students_dataset(n_rows, seed=seed)
    if ind in ("hr", "human_resources", "employee"):
        return generate_employee_records_dataset(n_rows, seed=seed)
    if ind in ("ecommerce", "e-commerce", "customer", "retail"):
        return generate_customer_database_dataset(n_rows, seed=seed)
    if ind in ("government", "public_sector", "civil_registry"):
        return generate_government_dataset(n_rows, seed=seed)
    # Default fallback
    return generate_hospital_dataset(n_rows, seed=seed)


def save_synthetic_datasets(target_dir: Optional[Path] = None, n_rows: int = 1000) -> Dict[str, Path]:
    """Generates and writes all synthetic benchmark CSV files to disk."""
    out_dir = target_dir or settings.DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "hospital_patient_records.csv": generate_hospital_dataset(n_rows),
        "bank_transactions.csv": generate_bank_transactions_dataset(n_rows),
        "university_student_records.csv": generate_university_students_dataset(n_rows),
        "employee_records.csv": generate_employee_records_dataset(n_rows),
        "customer_database.csv": generate_customer_database_dataset(n_rows),
        "government_records.csv": generate_government_dataset(n_rows),
    }

    saved_paths: Dict[str, Path] = {}
    for filename, df in datasets.items():
        path = out_dir / filename
        df.to_csv(path, index=False)
        saved_paths[filename] = path

    return saved_paths
