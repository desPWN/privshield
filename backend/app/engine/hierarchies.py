"""
PrivShield Generalization Hierarchies
Implements pluggable, multi-level Domain Generalization Hierarchies (DGH):
1. Pluggable numerical binning (equal width, quantile, custom edges).
2. Multi-level categorical trees (ICD-10 clinical, education majors, HR job titles, transaction categories).
3. Date and timestamp granularities (hour, day, month, quarter, year, wildcard).
4. Multi-level geographic taxonomies (City -> Governorate/State -> Region -> Country -> Wildcard).
Preserves backward compatibility for Jordanian geography and financial transaction tiers.
Exports apply_generalization and HierarchyRegistry.
"""

import math
import re
from typing import Any, Callable, Dict, List, Optional, Union
import numpy as np
import pandas as pd

# Multi-level Jordanian Geographic Taxonomy
CITY_TO_GOVERNORATE: Dict[str, str] = {
    "amman": "Capital Governorate",
    "عمان": "Capital Governorate",
    "zarqa": "Zarqa Governorate",
    "الزرقاء": "Zarqa Governorate",
    "salt": "Balqa Governorate",
    "السلط": "Balqa Governorate",
    "madaba": "Madaba Governorate",
    "مادبا": "Madaba Governorate",
    "irbid": "Irbid Governorate",
    "إربد": "Irbid Governorate",
    "jerash": "Jerash Governorate",
    "جرش": "Jerash Governorate",
    "ajloun": "Ajloun Governorate",
    "عجلون": "Ajloun Governorate",
    "mafraq": "Mafraq Governorate",
    "المفرق": "Mafraq Governorate",
    "aqaba": "Aqaba Governorate",
    "العقبة": "Aqaba Governorate",
    "karak": "Karak Governorate",
    "الكرك": "Karak Governorate",
    "tafilah": "Tafilah Governorate",
    "الطفيلة": "Tafilah Governorate",
    "maan": "Ma'an Governorate",
    "معان": "Ma'an Governorate"
}

GOVERNORATE_TO_REGION: Dict[str, str] = {
    "Capital Governorate": "Central Region",
    "Zarqa Governorate": "Central Region",
    "Balqa Governorate": "Central Region",
    "Madaba Governorate": "Central Region",
    "Irbid Governorate": "Northern Region",
    "Jerash Governorate": "Northern Region",
    "Ajloun Governorate": "Northern Region",
    "Mafraq Governorate": "Northern Region",
    "Aqaba Governorate": "Southern Region",
    "Karak Governorate": "Southern Region",
    "Tafilah Governorate": "Southern Region",
    "Ma'an Governorate": "Southern Region"
}

# Global Geographic Taxonomy
GLOBAL_CITY_TO_STATE: Dict[str, str] = {
    "new york": "New York",
    "chicago": "Illinois",
    "los angeles": "California",
    "san francisco": "California",
    "boston": "Massachusetts",
    "seattle": "Washington",
    "toronto": "Ontario",
    "london": "Greater London",
    "paris": "Île-de-France",
    "berlin": "Berlin",
    "tokyo": "Kanto",
    "sydney": "New South Wales"
}

STATE_TO_REGION: Dict[str, str] = {
    "New York": "East Coast",
    "Massachusetts": "East Coast",
    "Illinois": "Midwest",
    "California": "West Coast",
    "Washington": "West Coast",
    "Ontario": "Eastern Canada",
    "Greater London": "South East England",
    "Île-de-France": "Northern France",
    "Berlin": "Eastern Germany",
    "Kanto": "Eastern Japan",
    "New South Wales": "Eastern Australia"
}

# Healthcare Clinical Hierarchy (ICD-10 Chapter mappings)
ICD10_CHAPTER_MAP: Dict[str, str] = {
    "A": "Infectious & Parasitic Diseases",
    "B": "Infectious & Parasitic Diseases",
    "C": "Neoplasms (Cancers)",
    "D": "Neoplasms & Blood Diseases",
    "E": "Endocrine & Metabolic Diseases (Diabetes)",
    "F": "Mental & Behavioral Disorders",
    "G": "Nervous System Diseases",
    "H": "Eye & Ear Diseases",
    "I": "Circulatory System Diseases (Cardiovascular)",
    "J": "Respiratory System Diseases (Asthma/COPD)",
    "K": "Digestive System Diseases",
    "L": "Skin & Subcutaneous Diseases",
    "M": "Musculoskeletal Diseases (Arthritis)",
    "N": "Genitourinary System Diseases",
    "Z": "Health Status & Services (Checkups)"
}

# HR Job Titles Hierarchy
JOB_TITLE_TO_DEPT: Dict[str, str] = {
    "software engineer": "Engineering & Technology",
    "frontend developer": "Engineering & Technology",
    "backend developer": "Engineering & Technology",
    "data scientist": "Data & Analytics",
    "data analyst": "Data & Analytics",
    "registered nurse": "Clinical Care",
    "physician": "Clinical Care",
    "accountant": "Finance & Accounting",
    "financial analyst": "Finance & Accounting",
    "recruiter": "Human Resources",
    "hr coordinator": "Human Resources",
    "sales manager": "Sales & Marketing",
    "marketing specialist": "Sales & Marketing"
}

DEPT_TO_DIVISION: Dict[str, str] = {
    "Engineering & Technology": "Technical Operations",
    "Data & Analytics": "Technical Operations",
    "Clinical Care": "Medical Services",
    "Finance & Accounting": "Corporate Business",
    "Human Resources": "Corporate Business",
    "Sales & Marketing": "Corporate Business"
}

# Education Majors Hierarchy
MAJOR_TO_FIELD: Dict[str, str] = {
    "computer science": "Computing & Informatics",
    "software engineering": "Computing & Informatics",
    "data science": "Computing & Informatics",
    "electrical engineering": "Engineering",
    "mechanical engineering": "Engineering",
    "civil engineering": "Engineering",
    "nursing": "Health Sciences",
    "biology": "Life Sciences",
    "business administration": "Business & Economics",
    "accounting": "Business & Economics",
    "finance": "Business & Economics",
    "psychology": "Social Sciences"
}

FIELD_TO_DISCIPLINE: Dict[str, str] = {
    "Computing & Informatics": "STEM",
    "Engineering": "STEM",
    "Health Sciences": "Health & Medical",
    "Life Sciences": "STEM",
    "Business & Economics": "Business & Commerce",
    "Social Sciences": "Humanities & Social Sciences"
}


def generalize_city(val: Any, level: int = 1) -> str:
    """Generalize city according to administrative taxonomy."""
    if val is None or pd.isna(val):
        return "*"
    if level <= 0:
        return str(val).strip()
    if level >= 4:
        return "*"
    if level == 3:
        return "Jordan"

    clean = str(val).lower().strip()
    if clean in CITY_TO_GOVERNORATE:
        governorate = CITY_TO_GOVERNORATE[clean]
        if level == 1:
            return governorate
        if level == 2:
            return GOVERNORATE_TO_REGION.get(governorate, "Other Region")
        return "Jordan"

    if clean in GLOBAL_CITY_TO_STATE:
        state = GLOBAL_CITY_TO_STATE[clean]
        if level == 1:
            return f"{state} State"
        if level == 2:
            return STATE_TO_REGION.get(state, "Global Region")
        return "International"

    governorate = f"{str(val).title()} Governorate"
    if level == 1:
        return governorate
    if level == 2:
        return GOVERNORATE_TO_REGION.get(governorate, "Other Region")
    return "Jordan"


def generalize_age(val: Any, level: int = 1, bin_size: int = 10) -> str:
    """Generalize age into standardized demographic bins."""
    if val is None or pd.isna(val):
        return "*"
    try:
        age = float(val)
    except (ValueError, TypeError):
        return "*"

    if level <= 0:
        return str(int(round(age)))
    if level >= 3:
        return "*"

    if level == 1:
        if bin_size == 5:
            if age < 18:
                return "< 18"
            if age >= 65:
                return "65+"
            lower = int(age // 5 * 5)
            upper = lower + 4
            return f"[{lower}-{upper}]"
        else:
            if age < 18:
                return "< 18"
            if age < 25:
                return "[18-24]"
            if age >= 65:
                return "65+"
            lower = int(((age - 25) // 10 * 10) + 25)
            upper = lower + 9
            return f"[{lower}-{upper}]"

    if level == 2:
        if age < 30:
            return "Young Adult [18-29]"
        if age < 55:
            return "Adult [30-54]"
        return "Senior [55+]"

    return "*"


def generalize_amount(val: Any, level: int = 1, currency: str = "JOD") -> str:
    """Generalize financial transaction amount into standardized financial tiers."""
    if val is None or pd.isna(val):
        return "*"
    try:
        amt = float(val)
    except (ValueError, TypeError):
        return "*"

    if level <= 0:
        return f"{amt:.2f}"
    if level >= 3:
        return "*"

    if level == 1:
        if amt < 50:
            return f"[0 - 50] {currency}"
        if amt < 200:
            return f"[50 - 200] {currency}"
        if amt < 1000:
            return f"[200 - 1000] {currency}"
        if amt < 5000:
            return f"[1000 - 5000] {currency}"
        return f"[5000+] {currency}"

    if level == 2:
        if amt < 200:
            return f"Micro [< 200 {currency}]"
        if amt <= 1000:
            return f"Commercial [200 - 1000 {currency}]"
        return f"Wholesale [> 1000 {currency}]"

    return "*"


def generalize_timestamp(val: Any, level: int = 1, granularity: Optional[str] = None) -> str:
    """
    Generalize timestamp by truncating precision.
    Supports backward-compatible levels (0: Exact, 1: Hour, 2: Date, 3: Month, 4+: Wildcard)
    and optional explicit granularities: 'year', 'quarter', 'month', 'day', 'hour'.
    """
    if val is None or pd.isna(val):
        return "*"
    s = str(val).strip()

    iso_clean = s.replace(" ", "T")
    parts = iso_clean.split("T")
    date_part = parts[0]
    time_part = parts[1] if len(parts) > 1 else "00:00:00"

    # Handle explicit named granularity
    if granularity:
        g = granularity.lower().strip()
        if g in ("year", "yyyy"):
            return date_part[:4] if len(date_part) >= 4 else date_part
        if g == "quarter":
            month = int(date_part[5:7]) if len(date_part) >= 7 and date_part[5:7].isdigit() else 1
            q = (month - 1) // 3 + 1
            return f"{date_part[:4]}-Q{q}"
        if g in ("month", "year-month", "yyyy-mm"):
            return date_part[:7] if len(date_part) >= 7 else date_part
        if g in ("day", "date"):
            return date_part
        if g == "hour":
            hour = time_part[:2] if len(time_part) >= 2 else "00"
            return f"{date_part} {hour}:00"

    if level <= 0:
        return s
    if level >= 4:
        return "*"

    if level == 1:
        hour = time_part[:2] if len(time_part) >= 2 else "00"
        return f"{date_part} {hour}:00"

    if level == 2:
        return date_part

    if level == 3:
        return date_part[:7] if len(date_part) >= 7 else date_part

    return "*"


def generalize_category(val: Any, level: int = 1) -> str:
    """Generalize transaction categories into higher-level sectors."""
    if val is None or pd.isna(val):
        return "*"
    clean = str(val).lower().strip()
    if level <= 0:
        return str(val)
    if level >= 3:
        return "*"

    level1_map = {
        "shopping": "Retail & Living",
        "restaurant": "Food & Beverage",
        "dining": "Food & Beverage",
        "atm withdrawal": "Cash & Banking",
        "transfer": "Cash & Banking",
        "bills & utilities": "Household Services",
        "bills": "Household Services",
        "utilities": "Household Services",
        "healthcare": "Health & Education",
        "education": "Health & Education"
    }

    subsector = level1_map.get(clean, "Commercial Services")
    if level == 1:
        return subsector

    if subsector in ("Retail & Living", "Food & Beverage"):
        return "Consumer Discretionary"
    if subsector in ("Household Services", "Health & Education"):
        return "Essential Public Services"
    if subsector == "Cash & Banking":
        return "Financial Operations"

    return "General Commercial"


def generalize_medical_icd(val: Any, level: int = 1) -> str:
    """Generalize ICD-10 medical code: leaf -> 3-char block -> chapter description -> *."""
    if val is None or pd.isna(val):
        return "*"
    s = str(val).strip().upper()
    if level <= 0:
        return s
    if level >= 3 or len(s) == 0:
        return "*"
    if level == 1:
        # Truncate to 3-character category block (e.g., E11.9 -> E11)
        return s[:3]
    if level == 2:
        # Map initial letter to ICD-10 chapter
        initial = s[0]
        return ICD10_CHAPTER_MAP.get(initial, "General Medical Condition")
    return "*"


def generalize_job_title(val: Any, level: int = 1) -> str:
    """Generalize job title: role -> department -> division -> *."""
    if val is None or pd.isna(val):
        return "*"
    s = str(val).strip().lower()
    if level <= 0:
        return str(val)
    if level >= 3:
        return "*"
    dept = JOB_TITLE_TO_DEPT.get(s, "Professional Services")
    if level == 1:
        return dept
    if level == 2:
        return DEPT_TO_DIVISION.get(dept, "Corporate Operations")
    return "*"


def generalize_education_major(val: Any, level: int = 1) -> str:
    """Generalize educational major: major -> field -> discipline -> *."""
    if val is None or pd.isna(val):
        return "*"
    s = str(val).strip().lower()
    if level <= 0:
        return str(val)
    if level >= 3:
        return "*"
    field = MAJOR_TO_FIELD.get(s, "General Studies")
    if level == 1:
        return field
    if level == 2:
        return FIELD_TO_DISCIPLINE.get(field, "Academic Program")
    return "*"


# Pluggable Numerical Binning
def bin_numerical_equal_width(series: pd.Series, n_bins: int = 5, precision: int = 1) -> pd.Series:
    """Bins numeric series into equal-width intervals."""
    numeric_series = pd.to_numeric(series, errors="coerce")
    min_v = numeric_series.min()
    max_v = numeric_series.max()
    if pd.isna(min_v) or pd.isna(max_v) or min_v == max_v:
        return series.astype(str)
    bins = np.linspace(min_v, max_v, n_bins + 1)
    labels = [f"[{round(bins[i], precision)}-{round(bins[i+1], precision)}]" for i in range(n_bins)]
    return pd.cut(numeric_series, bins=bins, labels=labels, include_lowest=True).astype(str)


def bin_numerical_quantiles(series: pd.Series, n_quantiles: int = 4, precision: int = 1) -> pd.Series:
    """Bins numeric series into equal-frequency quantile intervals."""
    numeric_series = pd.to_numeric(series, errors="coerce")
    try:
        binned, bins = pd.qcut(numeric_series, q=n_quantiles, retbins=True, duplicates="drop")
        return binned.astype(str)
    except Exception:
        return bin_numerical_equal_width(series, n_bins=n_quantiles, precision=precision)


def bin_numerical_custom(val: Any, cutoffs: List[float], labels: Optional[List[str]] = None) -> str:
    """Bins single numeric value by custom cutoffs."""
    if val is None or pd.isna(val):
        return "*"
    try:
        v = float(val)
    except (ValueError, TypeError):
        return "*"
    for idx, c in enumerate(cutoffs):
        if v < c:
            if labels and idx < len(labels):
                return labels[idx]
            prev = cutoffs[idx - 1] if idx > 0 else 0
            return f"[{prev}-{c}]"
    if labels and len(labels) > len(cutoffs):
        return labels[-1]
    return f"[{cutoffs[-1]}+]"


class HierarchyRegistry:
    """Registry coordinating domain generalization hierarchies across attributes."""

    _custom_handlers: Dict[str, Callable[[Any, int], str]] = {}

    @classmethod
    def register(cls, pattern: str, handler: Callable[[Any, int], str]) -> None:
        cls._custom_handlers[pattern.lower()] = handler

    @classmethod
    def generalize_series(cls, col_name: str, series: pd.Series, level: int = 1) -> pd.Series:
        """Apply the appropriate generalization hierarchy to a pandas Series."""
        norm = re.sub(r"[_\-\s]+", "", col_name.lower())
        if level <= 0:
            return series

        # Check custom handlers
        for pat, fn in cls._custom_handlers.items():
            if pat in norm:
                return series.apply(lambda v: fn(v, level))

        if "city" in norm or "governorate" in norm or "town" in norm or "location" in norm or "state" in norm or "municipality" in norm:
            return series.apply(lambda v: generalize_city(v, level))
        if "age" in norm:
            return series.apply(lambda v: generalize_age(v, level))
        if "amount" in norm or "balance" in norm or "salary" in norm or "income" in norm or "charge" in norm:
            return series.apply(lambda v: generalize_amount(v, level))
        if "time" in norm or "date" in norm or "year" in norm:
            return series.apply(lambda v: generalize_timestamp(v, level))
        if "category" in norm or "merchant" in norm:
            return series.apply(lambda v: generalize_category(v, level))
        if "diagnosis" in norm or "icd" in norm:
            return series.apply(lambda v: generalize_medical_icd(v, level))
        if "job" in norm or "title" in norm or "position" in norm or "department" in norm or "dept" in norm:
            return series.apply(lambda v: generalize_job_title(v, level))
        if "major" in norm or "degree" in norm:
            return series.apply(lambda v: generalize_education_major(v, level))
        if "postal" in norm or "zip" in norm:
            return series.apply(lambda v: f"{str(v)[:3]}**" if (level == 1 and pd.notna(v) and len(str(v)) >= 3) else "*")

        # Default fallback for unmapped categorical attributes
        if level >= 2:
            return series.apply(lambda v: "*")
        return series


def apply_generalization(
    data: Union[pd.Series, Any],
    hierarchy_type: str,
    level: int = 1,
    **kwargs
) -> Any:
    """
    Applies generalization to either a pandas Series or single scalar value.
    """
    ht = hierarchy_type.lower().strip()
    if isinstance(data, pd.Series):
        if ht in ("equal_width", "equal_bins"):
            return bin_numerical_equal_width(data, n_bins=kwargs.get("n_bins", 5))
        if ht in ("quantile", "quantiles"):
            return bin_numerical_quantiles(data, n_quantiles=kwargs.get("n_quantiles", 4))
        return HierarchyRegistry.generalize_series(hierarchy_type, data, level=level)

    # Scalar value dispatch
    if ht in ("city", "location", "state", "municipality"):
        return generalize_city(data, level=level)
    if ht == "age":
        return generalize_age(data, level=level, bin_size=kwargs.get("bin_size", 10))
    if ht in ("amount", "balance", "salary", "charge"):
        return generalize_amount(data, level=level, currency=kwargs.get("currency", "JOD"))
    if ht in ("time", "date", "timestamp"):
        return generalize_timestamp(data, level=level, granularity=kwargs.get("granularity"))
    if ht in ("category", "merchant"):
        return generalize_category(data, level=level)
    if ht in ("icd", "diagnosis"):
        return generalize_medical_icd(data, level=level)
    if ht in ("job", "title", "department", "dept"):
        return generalize_job_title(data, level=level)
    if ht in ("major", "degree"):
        return generalize_education_major(data, level=level)
    if ht in ("postal", "postalcode", "zip", "postcode"):
        return f"{str(data)[:3]}**" if (level == 1 and data is not None and len(str(data)) >= 3) else "*"
    if level >= 2:
        return "*"
    return str(data)
