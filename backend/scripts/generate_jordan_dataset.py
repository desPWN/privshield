"""
FinGuard Jordanian Financial Synthetic Dataset Generator
Procedurally generates realistic, mathematically sound synthetic financial transactions
situated in the Jordanian banking sector with genuine checksums (ISO 7064 Mod 97-10 IBAN,
Luhn payment card numbers, 10-digit National IDs) and log-normal transaction amounts.
"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd


def calculate_iban_check_digits(country_code: str, bank_code: str, account_number: str) -> str:
    """Calculate ISO 7064 Mod 97-10 check digits for an IBAN."""
    rearranged = bank_code.upper() + account_number + country_code.upper() + "00"
    numeric_string = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    remainder = int(numeric_string) % 97
    check_digits = 98 - remainder
    return f"{check_digits:02d}"


def generate_luhn_card_number(bin_prefix: str = "4123") -> str:
    """Generate a 16-digit payment card number satisfying the Luhn (Mod 10) checksum."""
    body_length = 15 - len(bin_prefix)
    random_body = "".join(str(random.randint(0, 9)) for _ in range(body_length))
    partial_number = bin_prefix + random_body

    checksum = 0
    reverse_digits = [int(c) for c in reversed(partial_number)]
    for idx, d in enumerate(reverse_digits):
        if idx % 2 == 0:  # In 0-indexed reverse, position 0 corresponds to penultimate digit in 16-digit card
            doubled = d * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += d

    check_digit = (10 - (checksum % 10)) % 10
    card_raw = partial_number + str(check_digit)
    return f"{card_raw[0:4]} {card_raw[4:8]} {card_raw[8:12]} {card_raw[12:16]}"


def generate_dataset(num_records: int = 2500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic Jordanian financial transactions dataset."""
    random.seed(seed)
    np.random.seed(seed)

    first_names_m = [
        "Ahmad", "Mohammad", "Omar", "Tariq", "Zaid", "Khaled", "Yazan",
        "Hamza", "Abdullah", "Fadi", "Mustafa", "Bilal", "Sami", "Hussein", "Raed"
    ]
    first_names_f = [
        "Rania", "Nour", "Hiba", "Layla", "Farah", "Dana", "Yasmin",
        "Reem", "Salma", "Zein", "Tala", "Mariam", "Dina", "Hala", "Lina"
    ]
    family_names = [
        "Al-Majali", "Al-Zubi", "Haddad", "Al-Tarawneh", "Qudah", "Al-Adwan",
        "Shamali", "Khoury", "Al-Nsour", "Al-Khatib", "Al-Fayez", "Hijazi",
        "Dajani", "Naber", "Al-Husseini", "Obeidat", "Al-Momani"
    ]

    cities_weights = {
        "Amman": 0.48,
        "Zarqa": 0.18,
        "Irbid": 0.14,
        "Aqaba": 0.06,
        "Salt": 0.05,
        "Madaba": 0.04,
        "Jerash": 0.03,
        "Mafraq": 0.02
    }
    cities = list(cities_weights.keys())
    c_weights = list(cities_weights.values())

    postal_codes = {
        "Amman": "11181",
        "Zarqa": "13110",
        "Irbid": "21110",
        "Aqaba": "77110",
        "Salt": "19110",
        "Madaba": "17110",
        "Jerash": "26110",
        "Mafraq": "25110"
    }

    merchants_by_category = {
        "Shopping": [
            "City Mall Amman", "Abdali Boulevard", "Sameh Mall", "Taj Mall",
            "Zara Amman", "Carrefour Amman", "Mecca Mall"
        ],
        "Bills & Utilities": [
            "Jordan Telecom (Orange)", "Zain Jordan HQ", "Umniah Telecom",
            "Miyahuna Water", "JEPCO Electricity"
        ],
        "Restaurant": [
            "Hashem Restaurant", "Abu Jbara", "Wild Jordan Cafe",
            "Suffra Amman", "Firefly Burgers", "Shams El Balad"
        ],
        "ATM Withdrawal": [
            "Arab Bank ATM - Shmeisani", "Housing Bank ATM - Abdali",
            "Etihad Bank ATM - Sweifieh", "Bank of Jordan ATM - 7th Circle"
        ],
        "Transfer": [
            "CliQ Instant Transfer", "Western Union Amman", "Internal Account Transfer",
            "Arab Bank CliQ Service"
        ],
        "Healthcare": [
            "Al-Khalidi Hospital", "Jordan Hospital Pharmacy", "Abdali Medical Center",
            "Farah Hospital"
        ],
        "Education": [
            "University of Jordan Registration", "German Jordanian Univ Tuition",
            "Amman Baccalaureate School"
        ]
    }

    categories = list(merchants_by_category.keys())
    cat_weights = [0.28, 0.20, 0.18, 0.12, 0.11, 0.06, 0.05]

    bank_codes = [
        ("ARAB", "Arab Bank"),
        ("HABB", "Housing Bank"),
        ("UBSI", "Etihad Bank"),
        ("JCBU", "Jordan Commercial Bank"),
        ("BJOR", "Bank of Jordan"),
        ("AJIB", "Arab Jordan Investment Bank")
    ]

    card_bins = ["4123", "5200", "4580", "5105", "4029"]
    email_domains = ["gmail.com", "yahoo.com", "orange.jo", "umniah.jo", "outlook.com"]

    records = []
    base_date = datetime(2025, 1, 1, 8, 0, 0)

    for i in range(1, num_records + 1):
        gender = "M" if random.random() < 0.52 else "F"
        fname = random.choice(first_names_m if gender == "M" else first_names_f)
        lname = random.choice(family_names)
        full_name = f"{fname} {lname}"

        age = int(np.clip(np.random.normal(38, 14), 18, 78))
        birth_year = 2026 - age
        nat_prefix = str(birth_year)[2:] if birth_year >= 1930 else "99"
        national_id = f"{nat_prefix}{random.randint(10000000, 99999999)}"

        clean_fname = fname.lower()
        clean_lname = lname.lower().replace("-", "").replace("al", "")
        email = f"{clean_fname}.{clean_lname}{random.randint(10, 99)}@{random.choice(email_domains)}"

        phone_prefix = random.choice(["79", "78", "77"])
        phone = f"+962 {phone_prefix} {random.randint(100, 999)} {random.randint(1000, 9999)}"

        # 30-char Jordanian IBAN with valid ISO 7064 Mod 97-10 check digits
        # Format: JO + 2 check digits + 4 bank code + 22 numeric account chars
        bank_code, _ = random.choice(bank_codes)
        account_core = f"{random.randint(10**21, (10**22) - 1)}"
        check_digits = calculate_iban_check_digits("JO", bank_code, account_core)
        iban = f"JO{check_digits}{bank_code}{account_core}"

        # 16-digit card number with valid Luhn checksum
        card_num = generate_luhn_card_number(random.choice(card_bins))

        city = random.choices(cities, weights=c_weights)[0]
        postal = postal_codes[city]

        category = random.choices(categories, weights=cat_weights)[0]
        merchant = random.choice(merchants_by_category[category])
        channel = random.choices(
            ["POS", "ATM", "Online", "Mobile App", "Branch"],
            weights=[0.45, 0.15, 0.22, 0.13, 0.05]
        )[0]

        # Log-normal transaction amount (Jordanian Dinars - JOD)
        raw_amount = float(np.random.lognormal(mean=3.2, sigma=1.1))
        amount = round(float(np.clip(raw_amount, 0.50, 5000.00)), 2)

        # Account balance (liquidity)
        balance = round(float(np.clip(np.random.lognormal(mean=7.6, sigma=1.2), 15.00, 85000.00)), 2)

        time_offset = timedelta(
            days=random.randint(0, 420),
            hours=int(np.clip(np.random.normal(14, 4), 0, 23)),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        timestamp = (base_date + time_offset).isoformat()

        risk_score = int(np.clip(np.random.exponential(scale=18), 1, 99))
        loan_status = random.choices(
            ["No Active Loan", "Good Standing", "Delinquent", "Closed"],
            weights=[0.60, 0.28, 0.04, 0.08]
        )[0]

        records.append({
            "CustomerID": f"JO-CUST-{10000 + i}",
            "FullName": full_name,
            "NationalID": national_id,
            "Email": email,
            "Phone": phone,
            "IBAN": iban,
            "CardNumber": card_num,
            "Age": age,
            "Gender": gender,
            "City": city,
            "PostalCode": postal,
            "Timestamp": timestamp,
            "Merchant": merchant,
            "Channel": channel,
            "TransactionAmount": amount,
            "AccountBalance": balance,
            "TransactionCategory": category,
            "RiskScore": risk_score,
            "LoanStatus": loan_status,
            "IsSynthetic": True
        })

    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Jordanian financial dataset.")
    parser.add_argument("--records", type=int, default=2500, help="Number of records to generate")
    parser.add_argument("--output", type=str, default="backend/data/jordan_financial_transactions.csv", help="Output file path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_dataset(num_records=args.records, seed=args.seed)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} synthetic records to {output_path}")


if __name__ == "__main__":
    main()
