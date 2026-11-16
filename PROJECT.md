# Project: PrivShield — Universal Enterprise Data Anonymization Platform

## Architecture
PrivShield is an industry-independent, general-purpose enterprise privacy engineering and data anonymization platform. It provides mathematical anonymization guarantees (Strict K-anonymity, Distinct/Entropy/Recursive L-diversity, Continuous/Categorical T-closeness), multi-tier sensitive attribute auto-discovery, dual processing modes (Reversible Pseudonymization with encrypted recovery vs. Irreversible Anonymization with pre-export evaluation gateways), universal data utility quantification, and an Apple-inspired dark cybersecurity SaaS user interface.

### System Components
1. **Universal Detection & Profiling Engine (`backend/app/engine/discovery.py`)**:
   - 4-tier detection: Semantic taxonomy keywords, high-precision regexes & check-digit algorithms (Luhn, ISO 7064 Mod 97-10, RFC 5322, IPv4/v6, E.164, SSN, Passports), domain dictionaries (ICD-10, global locations, job titles, education degrees), and statistical Shannon entropy / uniqueness ratio analysis.
   - Classification into Direct Identifiers, Quasi-identifiers, Sensitive Attributes, and Insensitive fields with confidence metrics.
   - Dynamic user overrides with SQLite persistence.
   - Pre-built industry profiles: Healthcare, Finance, Education, Government, HR, E-commerce, and Custom (`backend/app/services/profile_service.py`).
2. **Universal Anonymization Engine (`backend/app/engine/`)**:
   - Expanded masking: email, phone, card, IBAN, national ID/SSN, IP address, residential address, custom mask formats (`masking.py`).
   - Format-preserving & cryptographic tokenization (`masking.py`, `encryption_service.py`).
   - Pluggable generalization hierarchies: numerical binning, multi-level categorical trees, date/timestamp granularities, geographic hierarchies (`hierarchies.py`).
   - Strict K-Anonymity guaranteeing zero equivalence classes smaller than $K$ ($\min(|EC_j|) \ge K$, $K=2 \dots 10$) with deterministic suppression (`k_anonymity.py`).
   - L-Diversity: Distinct, entropy-based, and recursive diversity with homogeneity violation reporting (`l_diversity.py`).
   - T-Closeness: Continuous 1D Wasserstein-1 Earth Mover's Distance and categorical Total Variation Distance ($0.5 \sum |p - q|$) (`t_closeness.py`).
3. **Dual Processing Modes & Cryptographic Vault (`backend/app/services/`)**:
   - **Mode 1 (Reversible Pseudonymization)**: AES-256-GCM authenticated dataset encryption at rest (`storage/raw/{dataset_id}.enc`), Fernet token encryption, relational SQLite `token_mappings` vault, authorized single-token lookup and full dataset reconstruction with admin passkey verification, and immutable audit logs (`recovery.py`, `recovery_service.py`).
   - **Mode 2 (Irreversible Anonymization)**: Permanent transformation without recovery keys or mappings, enforcing a mandatory privacy verification evaluation gateway prior to sanitized export.
4. **Universal Privacy & Utility Evaluation (`backend/app/engine/`)**:
   - Privacy risk models: Prosecutor Risk ($1 / \min|EC|$), Journalist Risk, Marketer Risk, Linkage attack simulation, and Normalized Certainty Penalty (NCP) (`risk.py`).
   - Utility analytics: Numerical & categorical distribution shifts, mean/median/std dev relative error, Pearson/Spearman correlation matrix preservation, and the 5-component Composite Utility-Retention Score (CURS) (`utility.py`).
5. **Backend Service & Export Layer (`backend/app/`)**:
   - FastAPI REST API with SQLite WAL persistence (`privshield.db`).
   - Safe local storage isolation (`storage/raw/` vs `storage/anonymized/`), path traversal guards, temp file cleanup, and redacting logging filter removing all continuous and spaced PII.
   - Sanitized exports (CSV with formula injection neutralization for `=`, `+`, `-`, `@`, `\t`, `\r`, XLSX via OpenPyXL, and JSON).
   - Publication-grade ReportLab PDF privacy evaluation report with dynamic NumberedCanvas, industry badges, K/L/T verification scorecards, and zero raw PII (`pdf_service.py`).
6. **Multi-Industry Synthetic Datasets (`backend/app/services/synthetic_data_service.py`)**:
   - Dedicated generators for 5 realistic 1,000-record datasets: Hospital patient records, Bank transactions, University student records, Employee records, and Customer databases.
7. **Apple-Inspired Dark Cybersecurity SaaS Frontend (`frontend/`)**:
   - Palette: Deep charcoal surfaces (`#090B10` canvas, `#0D1017` sidebar, `#11151E` panels, `#171D28` elevated surfaces, `#8B9CF7` indigo accent, `#36C995` emerald, `#E9AE57` amber, `#F16B78` rose), 1px hairline borders (`rgba(255, 255, 255, 0.07)`), refined typography with tabular numerals (`tabular-nums`), zero AI slop or neon glow shadows.
   - Application shell: Persistent compact sidebar navigating across 8 dedicated workspace views:
     1. Privacy Overview
     2. Dataset Management
     3. Data Discovery
     4. Anonymization Studio (professional 3-panel workspace)
     5. Privacy Analysis
     6. Utility Analysis
     7. Secure Recovery Center
     8. Reports & Settings
   - Enterprise Data Table with compact rows, sorting, pagination, filtering, column visibility, and raw PII masking safeguards.
8. **Dual-Track E2E Testing Suite (`tests_e2e/`)**:
   - Independent 4-tier requirement-driven opaque-box test suite validating multi-industry ingestion, detection, K/L/T math, dual modes, recovery, exports, and PDF reports without hardcoded column names.

---

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone. No feature is left unassigned.
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Multi-Industry Synthetic Datasets & Generator | 5 realistic 1,000-record datasets (Hospital, Bank, University, Employee, Customer) with synthetic certification | M1 | Survey (Exp 1, 2) |
| 2 | Universal Sensitive Attribute Detection Engine | 4-tier detection (taxonomy, regex/checksums, domain dictionaries, entropy) classifying Direct IDs, Quasi-IDs, Sensitive Attributes | M1 | Survey (Exp 1, 2) |
| 3 | Dynamic & Persistent User Classification Overrides | Dynamic override of column classifications with SQLite persistence | M1, M2 | Survey (Exp 1, 2) |
| 4 | Pre-Built Industry Profiles | 7 pre-built profiles (Healthcare, Finance, Education, Government, HR, E-commerce, Custom) with customizable rules | M1, M2 | Survey (Exp 2) |
| 5 | Universal Data Masking & Tokenization | Trailing-digit preserving masking (email, phone, card, IBAN, SSN, IP, address), format-preserving & cryptographic tokenization | M1 | Survey (Exp 1) |
| 6 | Pluggable Generalization Hierarchies | Numerical bins, multi-level categorical groupings, date/time granularities, geographic hierarchies | M1 | Survey (Exp 1) |
| 7 | Strict K-Anonymity Engine | Equivalence class partitioning; Invariant: min(EC) >= K (K=2..10), zero violating classes | M1 | Survey (Exp 1) |
| 8 | Distinct, Entropy & Recursive L-Diversity | Evaluates distinct sensitive attributes per equivalence class, isolates homogeneity attacks, flags violations | M1 | Survey (Exp 1) |
| 9 | Continuous EMD & Categorical TVD T-Closeness | 1D Earth Mover's Distance (Wasserstein-1) for continuous distributions, Total Variation Distance for categorical | M1 | Survey (Exp 1) |
| 10 | Universal Privacy Risk Metrics | Prosecutor risk (1/min|EC|), Journalist risk, Marketer risk, Linkage attack simulation, Normalized Certainty Penalty (NCP) | M1 | Survey (Exp 1) |
| 11 | Universal Data Utility Analytics & CURS | Distribution shifts, mean/median/std dev error, correlation preservation, suppression impact, 5-component CURS | M1 | Survey (Exp 1) |
| 12 | At-Rest Cryptographic Storage & EncryptionService | AES-256-GCM authenticated file encryption at rest (`storage/raw/{id}.enc`), Fernet token encryption | M1, M2 | Survey (Exp 1, 2) |
| 13 | SQLite Database Persistence & Migrations | SQLite schema for datasets, token_mappings, industry_profiles, anonymization_runs, audit_logs | M1, M2 | Survey (Exp 2) |
| 14 | Reversible Pseudonymization Mode & Recovery Service | Mode 1: Encrypted vault storage, encrypted token mappings, authorized record recovery, full dataset restore, audit logging | M1, M2 | Survey (Exp 1, 2) |
| 15 | Irreversible Anonymization & Pre-Export Gateway | Mode 2: Permanent transformation, zero recovery mappings, strict pre-export privacy evaluation verification | M1, M2 | Survey (Exp 1) |
| 16 | Multi-Format Sanitized Export with Formula Guard | Sanitized CSV (neutralizing =, +, -, @, \t, \r), XLSX, and JSON exports | M2 | Survey (Exp 2) |
| 17 | PrivShield ReportLab PDF Privacy Report | Executive privacy evaluation PDF report, NumberedCanvas, vector tables, multi-industry badges, scorecards, zero raw PII | M2 | Survey (Exp 2) |
| 18 | Apple Design System & Antislop Dark UI Tokens | #090B10 canvas, #0D1017 sidebar, #11151E panels, #171D28 elevated, hairline borders, tabular numerals, zero AI slop | M3 | Survey (Exp 3) |
| 19 | Application Shell & 8 Dedicated Workspace Views | Overview, Datasets, Discovery, Studio, Privacy Analysis, Utility Analysis, Secure Recovery Center, Reports & Settings | M3 | Survey (Exp 3) |
| 20 | Professional 3-Panel Anonymization Studio | Left columns rail, center transformation config with mode toggle, right pre-flight verification & live diff preview | M3 | Survey (Exp 3) |
| 21 | Enterprise Data Table with PII Masking Safeguards | Compact rows, sorting, pagination, filtering, column visibility, right-aligned tabular numbers, masked display with toggle | M3 | Survey (Exp 3) |
| 22 | Recharts Multi-Industry Privacy & Utility Visualizations | Risk distribution, equivalence class histograms, L-diversity breakdown, T-closeness curves, CURS radar chart | M3 | Survey (Exp 3) |
| 23 | Multi-Industry Opaque-Box E2E Test Suite | 4-tier test suite validating multi-industry datasets (Hospital, Bank, University, Employee, Customer) with zero hardcoded column names | E2E Track | Survey (Exp 1, 2) |
| 24 | Adversarial Hardening (Tier 5) | White-box stress testing, boundary condition attacks, zero false compliance verification | M4 (Phase 2) | Survey (Exp 1) |
| 25 | Dual-Viewport Responsive Layout Verification | Responsive layout verification at 1920x1080 and 1366x768 without horizontal overflow or clipping | M3, M4 | Survey (Exp 3) |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Requirement-driven multi-industry opaque-box test suite (Tiers 1-4) publishing TEST_READY.md | none | DONE |
| M1 | Universal Backend Engine, Detection, Cryptography & Dual Modes | Multi-tier detection, universal masking, pluggable hierarchies, strict K/L/T math, risk/utility models, EncryptionService (AES-256-GCM + Fernet), SQLite migrations, ProfileService, SyntheticDataGenerator | none | DONE |
| M2 | FastAPI Service Layer, Recovery Endpoints, Profiles & PDF Rebranding | /api/profiles, /api/recovery/*, demo loading endpoints, pre-export privacy verification gateway, PrivShield ReportLab PDF generator | M1 | DONE |
| M3 | Frontend Apple Design System, Shell & 8 Dedicated Workspace Views | Apple dark tokens, component primitives, Sidebar & TopNav, 8 dedicated views (Overview, Datasets, Discovery, 3-panel Studio, Privacy, Utility, Recovery, Reports/Settings), Enterprise DataTable | M2 | DONE |
| M4 | Final E2E 100% Pass, Adversarial Hardening & Viewport Verification | Phase 1: Pass 100% of E2E tests (Tiers 1-4); Phase 2: Tier 5 adversarial coverage hardening; Dual-viewport validation (1920x1080, 1366x768) | M3, E2E (TEST_READY.md) | DONE |

---

## Interface Contracts

### 1. Detection Engine ↔ API Service
- Input: `df: pd.DataFrame`
- Output: `List[ColumnProfile]`
```python
class ColumnProfile(BaseModel):
    column_name: str
    detected_type: Literal["direct_identifier", "quasi_identifier", "sensitive_attribute", "insensitive"]
    specific_type: str  # e.g., "national_id", "ssn", "iban", "email", "phone", "icd10", "salary", "gpa"
    confidence: float   # 0.0 to 1.0
    explanation: str
    sample_values_masked: List[str]
    unique_count: int
    null_count: int
```

### 2. Anonymization Engine ↔ API Service
- Input: `df: pd.DataFrame`, `config: AnonymizationConfig`:
```python
class AnonymizationConfig(BaseModel):
    processing_mode: Literal["reversible_pseudonymization", "irreversible_anonymization"] = "irreversible_anonymization"
    quasi_identifiers: List[str]
    sensitive_attributes: List[str]
    k_metric: int = 5                  # 2 to 10
    l_metric: Optional[int] = None      # 2 to 5
    t_metric: Optional[float] = None    # 0.05 to 0.50
    suppression_strategy: Literal["record", "cell"] = "record"
    max_suppression_pct: float = 0.50
    masking_rules: Dict[str, str] = {}
    generalization_levels: Dict[str, int] = {}
```
- Output: `AnonymizationResult`:
```python
class AnonymizationResult(BaseModel):
    anonymized_df: pd.DataFrame
    processing_mode: str
    is_reversible: bool
    token_mapping_count: int
    k_satisfied: bool                  # strictly True ONLY if min(EC) >= k
    achieved_k: int
    total_records: int
    retained_records: int
    suppressed_records: int
    suppression_rate: float
    num_equivalence_classes: int
    min_equivalence_class_size: int
    avg_equivalence_class_size: float
    l_diversity_results: Dict[str, Any]
    t_closeness_results: Dict[str, Any]
    privacy_risk: PrivacyRiskMetrics
    utility_metrics: UtilityMetrics
```

### 3. Secure Recovery Engine ↔ API Service
- Input: Token lookup (`token: str`, `passkey: str`) or dataset restore (`dataset_id: str`, `passkey: str`)
- Output: Single decrypted value or restored CSV stream, with audit event recorded in `audit_logs`.

### 4. Backend ↔ Frontend API Contract
- `POST /api/datasets/upload` -> returns `{ dataset_id: str, row_count: int, columns: List[str], preview: List[Dict], is_encrypted: bool }`
- `GET /api/datasets/{id}/discover` -> returns `{ dataset_id: str, profiles: List[ColumnProfile] }`
- `POST /api/datasets/{id}/overrides` -> update classification overrides
- `GET /api/profiles` -> returns list of 7 pre-built industry profiles
- `POST /api/datasets/load-industry-demo/{industry}` -> loads one of 5 synthetic demo datasets
- `POST /api/datasets/{id}/anonymize` -> executes anonymization (mode 1 or mode 2), returns summary metrics & run_id
- `GET /api/runs/{run_id}/analytics` -> returns full privacy risk & utility analytics (for Recharts)
- `GET /api/runs/{run_id}/diff?page=1&size=50` -> returns paginated original vs anonymized comparative records
- `GET /api/runs/{run_id}/export/{format}` -> downloads sanitized CSV, XLSX, or JSON (requires pre-export validation if Mode 2)
- `GET /api/runs/{run_id}/report/pdf` -> downloads executive ReportLab PDF report
- `POST /api/recovery/lookup-token` -> reverse single token (auth required)
- `POST /api/recovery/restore-dataset` -> restore full raw dataset from encrypted vault (auth required)
- `GET /api/recovery/audit-logs` -> list immutable recovery actions

---

## Code Layout
```
c:\Users\elias\Desktop\dsww\
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── logging_filter.py
│   │   ├── engine/
│   │   │   ├── discovery.py
│   │   │   ├── masking.py
│   │   │   ├── hierarchies.py
│   │   │   ├── k_anonymity.py
│   │   │   ├── l_diversity.py
│   │   │   ├── t_closeness.py
│   │   │   ├── risk.py
│   │   │   └── utility.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   ├── db/
│   │   │   └── database.py
│   │   ├── services/
│   │   │   ├── dataset_service.py
│   │   │   ├── anonymization_service.py
│   │   │   ├── encryption_service.py
│   │   │   ├── profile_service.py
│   │   │   ├── recovery_service.py
│   │   │   ├── synthetic_data_service.py
│   │   │   ├── export_service.py
│   │   │   └── pdf_service.py
│   │   └── api/
│   │       ├── router.py
│   │       └── routes/
│   │           ├── datasets.py
│   │           ├── discovery.py
│   │           ├── anonymization.py
│   │           ├── analytics.py
│   │           ├── diff.py
│   │           ├── export.py
│   │           ├── profiles.py
│   │           └── recovery.py
│   ├── data/
│   │   └── jordan_financial_transactions.csv
│   ├── storage/
│   │   ├── raw/
│   │   └── anonymized/
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── types/
│       ├── api/
│       ├── components/
│       │   ├── common/
│       │   ├── layout/
│       │   ├── overview/
│       │   ├── datasets/
│       │   ├── discovery/
│       │   ├── studio/
│       │   ├── privacy/
│       │   ├── utility/
│       │   ├── recovery/
│       │   └── reports/
│       └── hooks/
└── tests_e2e/
    ├── conftest.py
    ├── run_e2e_tests.py
    ├── tier1_features/
    ├── tier2_boundaries/
    ├── tier3_combinations/
    └── tier4_real_world/
```
