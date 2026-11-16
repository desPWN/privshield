# PrivShield End-to-End Testing Infrastructure

## 1. Overview & Architecture

PrivShield is an industry-independent enterprise data anonymization and privacy engineering platform. This document formalizes the End-to-End (E2E) testing infrastructure, architectural principles, multi-industry testing methodology, feature inventory coverage matrix, and verification commands.

The testing suite enforces a requirement-driven, opaque-box methodology. Tests evaluate public interface contracts, mathematical privacy guarantees (Strict K-Anonymity, Distinct/Entropy/Recursive L-Diversity, Continuous EMD and Categorical TVD T-Closeness), risk estimators, statistical utility retention scores (CURS), cryptographic vaults, and sanitized exports without hardcoding column names or relying on private implementation details.

```
tests_e2e/
├── conftest.py                     # Global fixtures, multi-industry generators, mathematical oracles
├── run_e2e_tests.py                # Standalone runner with tier selection and formatted reporting
├── test_contracts.py               # Interface contract adapters and specification fallbacks
├── tier1_features/                 # Tier 1: Functional coverage across all 25 platform features (137 tests)
│   ├── test_f01_synthetic_datasets.py
│   ├── test_f02_detection_engine.py
│   ├── test_f03_user_overrides.py
│   ├── test_f04_industry_profiles.py
│   ├── test_f05_masking_tokenization.py
│   ├── test_f06_generalization_hierarchies.py
│   ├── test_f07_strict_k_anonymity.py
│   ├── test_f08_l_diversity.py
│   ├── test_f09_t_closeness.py
│   ├── test_f10_risk_metrics.py
│   ├── test_f11_utility_curs.py
│   ├── test_f12_cryptographic_storage.py
│   ├── test_f13_database_persistence.py
│   ├── test_f14_reversible_pseudonymization.py
│   ├── test_f15_irreversible_anonymization.py
│   ├── test_f16_sanitized_export.py
│   ├── test_f17_pdf_report.py
│   ├── test_f18_apple_design_tokens.py
│   ├── test_f19_workspace_views.py
│   ├── test_f20_anonymization_studio.py
│   ├── test_f21_enterprise_datatable.py
│   ├── test_f22_recharts_visualizations.py
│   ├── test_f23_multi_industry_e2e_suite.py
│   ├── test_f24_adversarial_hardening.py
│   └── test_f25_viewport_responsiveness.py
├── tier2_boundaries/               # Tier 2: Boundary, corner & pathological stress testing (41 tests)
│   ├── test_b01_empty_and_single_record.py
│   ├── test_b02_identical_and_unique_qis.py
│   ├── test_b03_impossible_k_and_l.py
│   ├── test_b04_t_closeness_extremes.py
│   ├── test_b05_extreme_values_and_outliers.py
│   ├── test_b06_special_characters_and_types.py
│   ├── test_b07_formula_injection_attacks.py
│   └── test_b08_recovery_passkey_boundaries.py
├── tier3_combinations/             # Tier 3: Cross-feature combinations and lifecycle pipelines (15 tests)
│   ├── test_c01_masking_generalization_k_pipeline.py
│   ├── test_c02_k_l_t_joint_satisfaction.py
│   ├── test_c03_suppression_and_utility_tradeoffs.py
│   ├── test_c04_end_to_end_lifecycle.py
│   ├── test_c05_reversible_pseudonymization_recovery_pipeline.py
│   └── test_c06_dual_mode_divergence.py
├── tier4_real_world/               # Tier 4: Real-world multi-industry scenario suites (5 tests)
│   ├── test_s01_hospital_patient_records.py
│   ├── test_s02_bank_transactions.py
│   ├── test_s03_university_student_records.py
│   ├── test_s04_employee_records.py
│   └── test_s05_customer_databases.py
└── tier5_adversarial/              # Tier 5: White-box stress testing and security hardening (60 tests)
    ├── test_whitebox_engine_stress.py
    └── test_whitebox_security_stress.py
```

---

## 2. 4-Tier Multi-Industry Testing Methodology

The test suite organizes platform verification into four progressive tiers, with an auxiliary white-box hardening tier:

### 2.1 Tier 1: Functional Feature Coverage (137 Tests)
Covers all 25 features identified in `PROJECT.md`. Every feature has dedicated tests verifying interface contracts, input parameter validation, edge-case rejection, and expected outputs. Each feature module contains at least 5 independent test cases (averaging 5.5 tests per feature).

### 2.2 Tier 2: Boundary, Corner & Pathological Cases (41 Tests)
Stresses mathematical limits and pathological data conditions to guarantee that algorithms never fail silently, enter infinite loops, or divide by zero:
- **Degenerate Sample Sizes ($N=0, N=1$)**: Empty datasets return zeroed metrics without crashing; single-record datasets enforce $K \ge 2$ via suppression without false compliance.
- **Monolithic vs. Singleton Class Distributions**: All-identical quasi-identifiers collapse to 1 class of size $N$; all-unique quasi-identifiers suppress 100% of rows unless generalized.
- **Impossible Parameter Constraints**: Enforces $N < K$ suppression and detects $L > K$ mathematical impossibilities.
- **Distribution Distance Extremes ($T=0.0, T=1.0$)**: Verifies exact distribution matches and maximum distance bounds.
- **Numeric Extremes & Outliers**: High-magnitude amounts, negative balances, and near-zero variance data.
- **Unicode & Special Character Sets**: Arabic script, Asian glyphs, mixed datatypes, and nulls/NaNs.
- **Formula Injection Defense**: Escapes spreadsheet formulas starting with `=`, `+`, `-`, `@`, `\t`, `\r` while preserving valid numeric signs.
- **Cryptographic Passkey Boundaries**: Empty, wrong, and whitespace passkeys rejected by the secure recovery engine.

### 2.3 Tier 3: Cross-Feature Combinations & Pipelines (15 Tests)
Validates interactions between independent platform capabilities:
- **Masking + Generalization + Strict K**: Ensures masked direct IDs do not split equivalence classes and generalization properly clusters records.
- **$(K, L, T)$ Triplet Verification**: Confirms simultaneous satisfaction across all three privacy dimensions and tests independent failure isolation.
- **Privacy vs. Utility Monotonicity**: Verifies that tightening privacy thresholds ($K \uparrow, T \downarrow$) monotonically increases record suppression and decreases risk.
- **End-to-End Lifecycle**: Raw upload $\rightarrow$ Auto-discovery $\rightarrow$ Custom overrides $\rightarrow$ Dual-mode configuration $\rightarrow$ Anonymization $\rightarrow$ Utility scoring $\rightarrow$ Sanitized export $\rightarrow$ PDF audit report.
- **Reversible Recovery Pipeline**: Round-trip encryption, token vault storage, single-record lookup, and complete dataset reconstruction.
- **Dual Mode Divergence**: Proves that Mode 1 preserves reversible vaults while Mode 2 permanently destroys recovery state and enforces pre-export gateways.

### 2.4 Tier 4: Real-World Multi-Industry Scenarios (5 Tests)
Validates complete, industry-specific anonymization workflows on 5 distinct domain datasets with zero hardcoded column dependencies:
1. **Hospital Patient Records (Healthcare)**: MRN and National ID tokenization, Age/Zip generalization, ICD-10 clinical diversity, charges distribution preservation, and HIPAA-compliant PDF export.
2. **Bank Transactions (Finance)**: IBAN and Card PAN masking, City/Age clustering, continuous EMD T-closeness on amounts, and formula-safe CSV/XLSX exports.
3. **University Student Records (Education)**: Student ID and SSN tokenization, Birth date/Major generalization, GPA distribution preservation, Academic Standing L-diversity, and FERPA-ready JSON export.
4. **Employee Records (Human Resources)**: Employee ID and SSN masking, Department/Office clustering, compensation and performance rating privacy, and executive audit reporting.
5. **Customer Databases (E-Commerce / Retail)**: Customer ID, Email, Phone, IP address, and Street masking, demographic generalization, Annual Income T-closeness, and GDPR/CCPA release.

---

## 3. Complete 25-Feature Inventory Coverage Matrix

| # | Feature Name | Test Module | Tests | Milestone | Verified Contracts & Invariants |
|---|--------------|-------------|:-----:|:---------:|---------------------------------|
| **F01** | Multi-Industry Synthetic Datasets & Generator | `test_f01_synthetic_datasets.py` | 6 | M1 | Verifies 5 industry schemas (Hospital, Bank, University, Employee, Customer), synthetic indicators, reproducible seeding, and minimum volume constraints. |
| **F02** | Universal Sensitive Attribute Detection Engine | `test_f02_detection_engine.py` | 6 | M1 | 4-tier detection (taxonomy, regexes/checksums, dictionaries, entropy) categorizing Direct IDs, Quasi-IDs, Sensitive Attributes, and Insensitive fields with confidence metrics. |
| **F03** | Dynamic & Persistent User Classification Overrides | `test_f03_user_overrides.py` | 5 | M1, M2 | Custom user overrides take precedence over automatic detection; validates schema persistence, revert capabilities, and multi-column reclassifications. |
| **F04** | Pre-Built Industry Profiles | `test_f04_industry_profiles.py` | 6 | M1, M2 | Validates 7 standard profiles (Healthcare, Finance, Education, Government, HR, E-commerce, Custom) with suggested rules and user parameter overrides. |
| **F05** | Universal Data Masking & Tokenization | `test_f05_masking_tokenization.py` | 6 | M1 | Validates trailing-digit masking for email, phone, card PAN, IBAN, SSN, IP, residential address, and format-preserving tokenization (FPT). |
| **F06** | Pluggable Generalization Hierarchies | `test_f06_generalization_hierarchies.py` | 6 | M1 | Evaluates numerical binning, multi-level categorical trees, timestamp granularities, Level 0 identity, multi-column generalization, and wildcard suppression. |
| **F07** | Strict K-Anonymity Engine | `test_f07_strict_k_anonymity.py` | 9 | M1 | Guarantees $\min(\|EC_j\|) \ge K$ for $K \in [2, 10]$; confirms achieved $K$ equals minimum class size; rejects false compliance; enforces suppression limits. |
| **F08** | Distinct, Entropy & Recursive L-Diversity | `test_f08_l_diversity.py` | 7 | M1 | Isolates homogeneity attacks; validates distinct counts $\ge L$; verifies Shannon entropy threshold $H(S) \ge \ln(L)$; reports offending classes. |
| **F09** | Continuous EMD & Categorical TVD T-Closeness | `test_f09_t_closeness.py` | 5 | M1 | 1D Wasserstein-1 Earth Mover's Distance on normalized continuous ECDFs; Total Variation Distance ($0.5 \sum \|p - q\|$) on categorical distributions; bounds in $[0, 1]$. |
| **F10** | Universal Privacy Risk Metrics | `test_f10_risk_metrics.py` | 5 | M1 | Calculates Prosecutor Risk ($1 / \min\|EC\| \le 1/K$), Journalist Risk, Marketer Risk, Linkage simulation, and Normalized Certainty Penalty (NCP). |
| **F11** | Universal Data Utility Analytics & CURS | `test_f11_utility_curs.py` | 5 | M1 | Computes 5-component CURS ($U_{rec}, U_{num}, U_{cat}, U_{corr}, U_{gran}$); Kolmogorov-Smirnov distance; variance and correlation matrix preservation; bounds in $[0, 100\%]$. |
| **F12** | At-Rest Cryptographic Storage & EncryptionService | `test_f12_cryptographic_storage.py` | 5 | M1, M2 | Authenticated AES-256-GCM dataset encryption at rest (`storage/raw/{id}.enc`); Fernet token encryption; tamper detection via authentication tags. |
| **F13** | SQLite Database Persistence & Migrations | `test_f13_database_persistence.py` | 5 | M1, M2 | Verifies SQLite WAL relational schemas: datasets, token_mappings, industry_profiles, anonymization_runs, and append-only audit_logs. |
| **F14** | Reversible Pseudonymization Mode & Recovery Service | `test_f14_reversible_pseudonymization.py` | 5 | M1, M2 | Mode 1 operations: encrypted vault storage, encrypted token mappings, authorized single-token lookup, full dataset restore, and immutable audit logging. |
| **F15** | Irreversible Anonymization & Pre-Export Gateway | `test_f15_irreversible_anonymization.py` | 5 | M1, M2 | Mode 2 operations: permanent value transformation, zero recovery mappings, pre-export verification gateway, and rejection of uncertified datasets. |
| **F16** | Multi-Format Sanitized Export with Formula Guard | `test_f16_sanitized_export.py` | 6 | M1, M2 | Sanitized CSV neutralizing spreadsheet formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`); OpenPyXL XLSX binary integrity; JSON structured array export. |
| **F17** | PrivShield ReportLab PDF Privacy Report | `test_f17_pdf_report.py` | 5 | M2 | Two-pass NumberedCanvas PDF generation; vector scorecard tables; multi-industry badges; zero raw PII leakage; graceful handling of suppressed sets. |
| **F18** | Apple Design System & Antislop Dark UI Tokens | `test_f18_apple_design_tokens.py` | 5 | M3 | Validates charcoal palette tokens (`#090B10`, `#0D1017`, `#11151E`, `#171D28`), hairline borders, tabular numerals, typography scale, and absence of AI slop. |
| **F19** | Application Shell & 8 Dedicated Workspace Views | `test_f19_workspace_views.py` | 5 | M3 | Navigation routing across all 8 workspace views: Overview, Datasets, Discovery, Studio, Privacy, Utility, Recovery, Reports/Settings. |
| **F20** | Professional 3-Panel Anonymization Studio | `test_f20_anonymization_studio.py` | 5 | M3 | Three-panel layout contracts: column selection rail, center transformation & mode configuration, right live diff preview and pre-flight verification. |
| **F21** | Enterprise Data Table with PII Masking Safeguards | `test_f21_enterprise_datatable.py` | 5 | M3 | Data table features: compact row padding, sorting, pagination, filtering, column visibility, and raw PII masking with reveal toggles. |
| **F22** | Recharts Multi-Industry Privacy & Utility Visualizations | `test_f22_recharts_visualizations.py` | 5 | M3 | Analytics payload structures for Recharts: risk distribution, equivalence class histograms, L-diversity breakdown, T-closeness curves, CURS radar metrics. |
| **F23** | Multi-Industry Opaque-Box E2E Test Suite | `test_f23_multi_industry_e2e_suite.py` | 5 | E2E | Verifies test harness execution across all 5 synthetic industry datasets, dynamic schema ingestion, and invariant enforcement without hardcoded column names. |
| **F24** | Adversarial Hardening (Tier 5) | `test_f24_adversarial_hardening.py` | 5 | M4 | Verifies the existence and execution of white-box stress tests, hostile payloads, fuzzing matrices, and path traversal guards. |
| **F25** | Dual-Viewport Responsive Layout Verification | `test_f25_viewport_responsiveness.py` | 5 | M3, M4 | Viewport contracts for desktop (1920x1080) and laptop (1366x768): prevents horizontal body scrolling, preserves table containment, and maintains readability. |

---

## 4. Strict Algorithmic Invariants & Verification Oracles

The test suite validates implementations against authoritative mathematical oracles defined in `tests_e2e/conftest.py`:

### 4.1 Strict K-Anonymity Invariant
Every unsuppressed equivalence class $EC_j$ partitioned by quasi-identifiers $Q$ must satisfy:
$$\min_{j} |EC_j| \ge K \quad \text{for } K \in \{2, \dots, 10\}$$
Any dataset containing even a single equivalence class with size $< K$ fails certification.

### 4.2 Distinct & Entropy L-Diversity Bounds
For each equivalence class $EC_j$ and sensitive attribute $S$:
$$\text{Distinct: } |\{s \in S \mid s \in EC_j\}| \ge L \quad (L \le K)$$
$$\text{Entropy: } H(S_j) = -\sum_{s \in S_j} p(s) \ln p(s) \ge \ln(L)$$
Classes failing these thresholds are flagged as vulnerable to homogeneity or background knowledge attacks.

### 4.3 T-Closeness Distance Bounds
Continuous attributes are evaluated via 1D Wasserstein-1 Earth Mover's Distance over normalized Empirical Cumulative Distribution Functions (ECDFs):
$$W_1(P_j, Q) = \int_0^1 |F_j(x) - F(x)| \, dx \le T \quad (W_1 \in [0.0, 1.0])$$
Categorical attributes are evaluated via Total Variation Distance:
$$TVD(P_j, Q) = \frac{1}{2} \sum_{c \in C} |p_j(c) - q(c)| \le T \quad (TVD \in [0.0, 1.0])$$

### 4.4 Composite Utility-Retention Score (CURS)
Utility preservation is measured on a $[0, 100\%]$ scale across 5 weighted dimensions:
$$CURS = 100 \times \left(0.25 \, U_{rec} + 0.25 \, U_{num} + 0.20 \, U_{cat} + 0.15 \, U_{corr} + 0.15 \, U_{gran}\right)$$
- $U_{rec}$: Record retention rate ($1 - \text{suppression\_rate}$)
- $U_{num}$: Numerical distribution preservation via two-sample Kolmogorov-Smirnov statistics ($1 - KS$)
- $U_{cat}$: Categorical distribution retention ($1 - TVD$)
- $U_{corr}$: Correlation matrix preservation ($1 - \text{mean\_abs\_corr\_diff}$)
- $U_{gran}$: Granularity retention penalty ($1 - NCP_{avg}$)

### 4.5 Zero Hardcoded Column Dependencies
Tests dynamically resolve column roles via `detect_sensitive_attributes()` or `ColumnProfile` metadata. Test assertions operate generically across datasets from healthcare, finance, education, human resources, and retail without expecting predefined column headers.

### 4.6 Formula Injection Neutralization
Export serializers inspect every string value. Any cell beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` is escaped with a prepended single quote (`'`), preventing remote code execution when opened in Microsoft Excel or Google Sheets. Legitimate signed numbers (e.g. `-142.50`) remain numeric.

### 4.7 Zero Raw PII Leakage
Sanitized outputs (CSVs, XLSX workbooks, JSON feeds, PDF reports, and log streams) are scanned with regex oracles. Any appearance of unmasked email addresses, raw credit card PANs, IBANs, or national identification numbers triggers immediate test failure.

---

## 5. Test Execution Commands

### 5.1 Standalone Test Runner
Execute the unified PrivShield test runner:
```bash
# Run all 4 primary test tiers (198 tests)
python tests_e2e/run_e2e_tests.py

# Run specific tiers
python tests_e2e/run_e2e_tests.py --tier=1    # Tier 1: Functional Feature Coverage (137 tests)
python tests_e2e/run_e2e_tests.py --tier=2    # Tier 2: Boundary & Corner Cases (41 tests)
python tests_e2e/run_e2e_tests.py --tier=3    # Tier 3: Cross-Feature Combinations (15 tests)
python tests_e2e/run_e2e_tests.py --tier=4    # Tier 4: Real-World Scenarios (5 tests)
python tests_e2e/run_e2e_tests.py --tier=5    # Tier 5: White-Box Adversarial Hardening (60 tests)

# Run full test suite including Tier 5 (258 tests)
python tests_e2e/run_e2e_tests.py --tier=full

# Verbose output with keyword filtering
python tests_e2e/run_e2e_tests.py --tier=1 -v -k "k_anonymity"
```

### 5.2 Pytest Direct Execution
```bash
# Execute entire test directory (258 tests)
pytest tests_e2e/

# Execute individual tiers
pytest tests_e2e/tier1_features/ -v
pytest tests_e2e/tier2_boundaries/ -v
pytest tests_e2e/tier3_combinations/ -v
pytest tests_e2e/tier4_real_world/ -v
pytest tests_e2e/tier5_adversarial/ -v
```
