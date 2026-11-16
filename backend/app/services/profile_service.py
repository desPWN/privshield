"""
PrivShield Industry Profiles Service
Provides pre-built industry dataset profiles:
1. Healthcare (HIPAA Safe Harbor / Expert Determination)
2. Finance (PCI-DSS / CBJ / GDPR)
3. Education (FERPA)
4. Government (Civil Registry / Public Sector)
5. Human Resources (Corporate Payroll & Staffing)
6. E-Commerce (Online Retail & Customer Analytics)
7. Custom (Freeform User Configuration)
Enables suggested classification and anonymization presets for diverse domains.
"""

from typing import Any, Dict, List, Optional
import json

from backend.app.models.schemas import IndustryProfile
from backend.app.db.database import DatabaseRepository

PREBUILT_PROFILES: List[Dict[str, Any]] = [
    {
        "id": "healthcare",
        "name": "Healthcare Patient Privacy (HIPAA Safe Harbor)",
        "industry": "healthcare",
        "description": "Designed for hospital clinical datasets, patient records, and health insurers. Strictly protects direct patient identifiers and enforces K=5, L=3 on diagnoses, and T=0.15 on charges.",
        "icon": "HeartPulse",
        "suggested_rules": {
            "k_metric": 5,
            "l_metric": 3,
            "t_metric": 0.15,
            "max_suppression_pct": 0.15,
            "suppression_strategy": "record",
            "masking_rules": {
                "Patient_Name": "mask_full",
                "PatientName": "mask_full",
                "MRN": "token",
                "SSN": "mask_ssn",
                "Phone": "mask_phone",
                "Email": "mask_email",
                "StreetAddress": "mask_address",
                "Address": "mask_address",
            },
            "generalization_levels": {
                "Age": 1,
                "City": 1,
                "PostalCode": 1,
                "Postal_Code": 1,
                "AdmissionDate": 1,
            },
            "direct_identifiers": ["PatientID", "Patient_Name", "PatientName", "MRN", "SSN", "Phone", "Email", "StreetAddress", "Address"],
            "quasi_identifiers": ["Age", "Gender", "City", "PostalCode", "Postal_Code", "AdmissionDate"],
            "sensitive_attributes": ["DiagnosisCode", "DiagnosisDescription", "Treatment", "LabResultNumeric", "HospitalCharge", "Medication", "Billing_Amount"],
        },
        "is_built_in": 1,
    },
    {
        "id": "finance",
        "name": "Banking & Financial Services (PCI-DSS / CBJ)",
        "industry": "finance",
        "description": "Tailored for retail banks, credit card processors, and fintechs. Enforces strict K=5, L=3, and T=0.15 with trailing digit masking for cards, IBANs, and national IDs.",
        "icon": "Landmark",
        "suggested_rules": {
            "k_metric": 5,
            "l_metric": 3,
            "t_metric": 0.15,
            "max_suppression_pct": 0.10,
            "suppression_strategy": "record",
            "masking_rules": {
                "Customer_Name": "mask_full",
                "CustomerName": "mask_full",
                "NationalID": "mask_national_id",
                "National_ID": "mask_national_id",
                "IBAN": "mask_iban",
                "CardNumber": "mask_card",
                "Card_Number": "mask_card",
                "Email": "mask_email",
                "Phone": "mask_phone",
            },
            "generalization_levels": {
                "City": 1,
                "BranchCity": 1,
                "CustomerAge": 1,
                "Customer_Age": 1,
                "Age": 1,
                "TransactionAmount": 1,
                "TransactionDate": 1,
                "Timestamp": 1,
            },
            "direct_identifiers": ["AccountID", "Customer_Name", "CustomerName", "NationalID", "National_ID", "Email", "Phone", "IBAN", "CardNumber", "Card_Number"],
            "quasi_identifiers": ["CustomerAge", "Customer_Age", "Age", "Gender", "BranchCity", "City", "PostalCode", "TransactionDate", "Timestamp"],
            "sensitive_attributes": ["TransactionAmount", "AccountBalance", "CreditScore", "LoanStatus", "Annual_Income"],
        },
        "is_built_in": 1,
    },
    {
        "id": "education",
        "name": "Higher Education & Student Records (FERPA)",
        "industry": "education",
        "description": "Configured for universities, colleges, and examination boards. Masks student identifiers while protecting GPA and disciplinary history with K=4 and L=2.",
        "icon": "GraduationCap",
        "suggested_rules": {
            "k_metric": 4,
            "l_metric": 2,
            "t_metric": 0.20,
            "max_suppression_pct": 0.15,
            "suppression_strategy": "record",
            "masking_rules": {
                "FullName": "mask_full",
                "Student_Name": "mask_full",
                "StudentID": "token",
                "Student_ID": "token",
                "PersonalEmail": "mask_email",
                "Personal_Email": "mask_email",
                "CampusPhone": "mask_phone",
                "HomeAddress": "mask_address",
            },
            "generalization_levels": {
                "Age": 1,
                "HomeCity": 1,
                "HomeState": 1,
                "EnrollmentYear": 1,
                "Major": 1,
            },
            "direct_identifiers": ["StudentID", "Student_ID", "FullName", "Student_Name", "PersonalEmail", "Personal_Email", "CampusPhone", "HomeAddress"],
            "quasi_identifiers": ["Age", "Gender", "HomeCity", "HomeState", "EnrollmentYear", "Major"],
            "sensitive_attributes": ["CumulativeGPA", "AcademicStanding", "FinancialAidAmount", "ScholarshipStatus", "DisciplinaryRecord"],
        },
        "is_built_in": 1,
    },
    {
        "id": "government",
        "name": "Civil Registry & Public Sector (GDPR / National)",
        "industry": "government",
        "description": "Designed for government agencies, tax authorities, and social security registries. Strictly redacts identity tokens while auditing income distributions with K=5, L=3.",
        "icon": "Building2",
        "suggested_rules": {
            "k_metric": 5,
            "l_metric": 3,
            "t_metric": 0.15,
            "max_suppression_pct": 0.10,
            "suppression_strategy": "record",
            "masking_rules": {
                "Citizen_Name": "mask_full",
                "National_ID": "mask_national_id",
                "Passport_Number": "mask_passport",
                "Tax_ID": "mask_hash",
                "Residential_Address": "mask_address",
                "Phone": "mask_phone",
            },
            "generalization_levels": {
                "Municipality": 1,
                "Age": 1,
                "Taxable_Income": 1,
            },
            "direct_identifiers": ["Citizen_Name", "National_ID", "Passport_Number", "Tax_ID", "Residential_Address", "Phone"],
            "quasi_identifiers": ["Age", "Gender", "Municipality", "Postal_Code", "Marital_Status", "Household_Size"],
            "sensitive_attributes": ["Taxable_Income", "Benefit_Amount", "Disability_Status", "Property_Assessment", "Pension_Tier"],
        },
        "is_built_in": 1,
    },
    {
        "id": "hr",
        "name": "Corporate Human Resources & Payroll",
        "industry": "hr",
        "description": "Formulated for corporate HR and payroll departments. Protects compensation, bonuses, and performance reviews with K=4 and L=2.",
        "icon": "Users",
        "suggested_rules": {
            "k_metric": 4,
            "l_metric": 2,
            "t_metric": 0.20,
            "max_suppression_pct": 0.15,
            "suppression_strategy": "record",
            "masking_rules": {
                "FullName": "mask_full",
                "Employee_Name": "mask_full",
                "EmployeeID": "token",
                "Employee_ID": "token",
                "WorkEmail": "mask_email",
                "Corporate_Email": "mask_email",
                "PersonalPhone": "mask_phone",
                "NationalID": "mask_national_id",
                "SSN_TaxID": "mask_ssn",
                "ResidentialAddress": "mask_address",
            },
            "generalization_levels": {
                "Department": 1,
                "OfficeLocation": 1,
                "HireYear": 1,
                "Age": 1,
                "BaseSalary": 1,
            },
            "direct_identifiers": ["EmployeeID", "Employee_ID", "FullName", "Employee_Name", "WorkEmail", "Corporate_Email", "PersonalPhone", "NationalID", "SSN_TaxID", "ResidentialAddress"],
            "quasi_identifiers": ["Age", "Gender", "OfficeLocation", "Department", "HireYear", "EducationLevel"],
            "sensitive_attributes": ["BaseSalary", "AnnualBonus", "PerformanceRating", "DisciplinaryAction", "Sick_Leave_Days"],
        },
        "is_built_in": 1,
    },
    {
        "id": "ecommerce",
        "name": "E-Commerce & Retail Customer Analytics",
        "industry": "ecommerce",
        "description": "Engineered for online merchants and marketplaces. Masks buyer contact details and billing info while preserving purchasing insights with K=3, L=2, T=0.25.",
        "icon": "ShoppingCart",
        "suggested_rules": {
            "k_metric": 3,
            "l_metric": 2,
            "t_metric": 0.25,
            "max_suppression_pct": 0.20,
            "suppression_strategy": "record",
            "masking_rules": {
                "FullName": "mask_full",
                "Customer_Name": "mask_full",
                "CustomerID": "token",
                "Customer_ID": "token",
                "Email": "mask_email",
                "PhoneNumber": "mask_phone",
                "BillingAddress": "mask_address",
                "Shipping_Address": "mask_address",
                "IPAddress": "mask_ip",
            },
            "generalization_levels": {
                "City": 1,
                "State": 1,
                "RegistrationDate": 1,
                "AgeGroup": 1,
            },
            "direct_identifiers": ["CustomerID", "Customer_ID", "FullName", "Customer_Name", "Email", "PhoneNumber", "BillingAddress", "Shipping_Address", "IPAddress"],
            "quasi_identifiers": ["AgeGroup", "Gender", "City", "State", "PostalCode", "RegistrationDate"],
            "sensitive_attributes": ["AnnualIncome", "CreditLimit", "LifetimeValue", "ChurnRiskScore", "Order_Total"],
        },
        "is_built_in": 1,
    },
    {
        "id": "custom",
        "name": "Custom Universal Privacy Profile",
        "industry": "custom",
        "description": "Blank-slate customizable profile for arbitrary structured datasets, scientific research, and domain-specific regulatory regimes.",
        "icon": "Sliders",
        "suggested_rules": {
            "k_metric": 3,
            "l_metric": None,
            "t_metric": None,
            "max_suppression_pct": 0.20,
            "suppression_strategy": "record",
            "masking_rules": {},
            "generalization_levels": {},
            "direct_identifiers": [],
            "quasi_identifiers": [],
            "sensitive_attributes": [],
        },
        "is_built_in": 1,
    },
]


class ProfileService:
    @classmethod
    def seed_prebuilt_profiles(cls) -> None:
        """Seeds built-in industry profiles into the SQLite persistence layer."""
        for p in PREBUILT_PROFILES:
            DatabaseRepository.upsert_industry_profile(p)

    @classmethod
    def list_profiles(cls) -> List[IndustryProfile]:
        """Returns all industry profiles from database, falling back to in-memory list."""
        cls.seed_prebuilt_profiles()
        db_rows = DatabaseRepository.list_industry_profiles()
        if db_rows:
            return [
                IndustryProfile(
                    id=r["id"],
                    name=r["name"],
                    industry=r["industry"],
                    description=r["description"],
                    icon=r["icon"],
                    suggested_rules=r.get("suggested_rules", {}),
                    is_built_in=bool(r.get("is_built_in", 1)),
                )
                for r in db_rows
            ]
        return [
            IndustryProfile(
                id=p["id"],
                name=p["name"],
                industry=p["industry"],
                description=p["description"],
                icon=p["icon"],
                suggested_rules=p["suggested_rules"],
                is_built_in=bool(p.get("is_built_in", 1)),
            )
            for p in PREBUILT_PROFILES
        ]

    @classmethod
    def get_profile(cls, profile_id: str) -> Optional[IndustryProfile]:
        """Retrieves a single industry profile by ID."""
        cls.seed_prebuilt_profiles()
        db_row = DatabaseRepository.get_industry_profile(profile_id)
        if db_row:
            return IndustryProfile(
                id=db_row["id"],
                name=db_row["name"],
                industry=db_row["industry"],
                description=db_row["description"],
                icon=db_row["icon"],
                suggested_rules=db_row.get("suggested_rules", {}),
                is_built_in=bool(db_row.get("is_built_in", 1)),
            )
        for p in PREBUILT_PROFILES:
            if p["id"] == profile_id:
                return IndustryProfile(
                    id=p["id"],
                    name=p["name"],
                    industry=p["industry"],
                    description=p["description"],
                    icon=p["icon"],
                    suggested_rules=p["suggested_rules"],
                    is_built_in=bool(p.get("is_built_in", 1)),
                )
        return None

    @classmethod
    def apply_profile_to_dataset(cls, profile_id: str, columns: List[str]) -> Dict[str, Any]:
        """
        Matches dataset columns against profile's suggested direct IDs, quasi IDs,
        and sensitive attributes, returning configured anonymization parameters.
        """
        profile = cls.get_profile(profile_id)
        if not profile:
            profile = cls.get_profile("custom")

        rules = profile.suggested_rules if profile else {}
        clean_cols = {c.lower().replace("_", ""): c for c in columns}

        matched_masking: Dict[str, str] = {}
        for candidate, rule in rules.get("masking_rules", {}).items():
            norm_cand = candidate.lower().replace("_", "")
            if norm_cand in clean_cols:
                matched_masking[clean_cols[norm_cand]] = rule

        matched_gen: Dict[str, int] = {}
        for candidate, level in rules.get("generalization_levels", {}).items():
            norm_cand = candidate.lower().replace("_", "")
            if norm_cand in clean_cols:
                matched_gen[clean_cols[norm_cand]] = level

        matched_qi: List[str] = []
        for candidate in rules.get("quasi_identifiers", []):
            norm_cand = candidate.lower().replace("_", "")
            if norm_cand in clean_cols and clean_cols[norm_cand] not in matched_qi:
                matched_qi.append(clean_cols[norm_cand])

        matched_sa: List[str] = []
        for candidate in rules.get("sensitive_attributes", []):
            norm_cand = candidate.lower().replace("_", "")
            if norm_cand in clean_cols and clean_cols[norm_cand] not in matched_sa:
                matched_sa.append(clean_cols[norm_cand])

        return {
            "profile_id": profile.id if profile else "custom",
            "k_metric": rules.get("k_metric", 3),
            "l_metric": rules.get("l_metric"),
            "t_metric": rules.get("t_metric"),
            "suppression_strategy": rules.get("suppression_strategy", "record"),
            "max_suppression_pct": rules.get("max_suppression_pct", 0.20),
            "masking_rules": matched_masking,
            "generalization_levels": matched_gen,
            "quasi_identifiers": matched_qi,
            "sensitive_attributes": matched_sa,
        }
