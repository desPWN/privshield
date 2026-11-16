# PrivShield — Enterprise Data Anonymization & Privacy Engineering Platform

PrivShield is an industry-independent enterprise privacy engineering and data anonymization platform. It provides mathematically certified privacy guarantees (Strict K-Anonymity, L-Diversity, T-Closeness), 4-tier automated sensitive attribute discovery, dual processing modes (Reversible AES-256-GCM Pseudonymization vs. Irreversible Anonymization), universal statistical utility quantification (CURS), and an Apple-inspired dark cybersecurity SaaS interface.

---

## Key Capabilities

* **4-Tier Sensitive Attribute Discovery:** Automatically classifies incoming data columns into *Direct Identifiers*, *Quasi-Identifiers*, *Sensitive Attributes*, or *Insensitive Fields* using regex syntax, mathematical check digits (Luhn, ISO 7064 Mod 97-10 for IBAN), domain dictionaries, and Shannon entropy.
* **Strict K-Anonymity ($\min(|EC_j|) \ge K$):** Enforces mathematical equivalence-class boundaries with deterministic cell/record suppression, guaranteeing zero singling-out violations.
* **Multi-Attribute L-Diversity & T-Closeness:** Protects against attribute disclosure and homogeneity attacks using distinct attribute entropy and Earth Mover's Distance (Wasserstein-1 metric).
* **Dual Protection Modes:**
  * **Mode 1 (Reversible Pseudonymization):** Cryptographic token vaulting backed by AES-256-GCM authenticated dataset encryption and Fernet symmetric tokens with admin passkey verification.
  * **Mode 2 (Irreversible Anonymization):** Permanent de-identification with cell suppression, generalization hierarchies, and pre-export privacy evaluation gateways.
* **5-Dimension Utility Quantification (CURS):** Measures analytical data quality retention across record retention, numerical fidelity, categorical fidelity, correlation matrix preservation, and granularity retention.
* **Export & Regulatory Compliance:** Generates formula-injection sanitized CSVs, XLSX spreadsheets, and publication-grade executive PDF compliance certifications.

---

## Tech Stack

* **Backend:** Python 3.10+, FastAPI, Uvicorn, Pandas, NumPy, SciPy, Scikit-learn, ReportLab, OpenPyXL, SQLite (WAL mode).
* **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons.

---

## Prerequisites

Before setting up PrivShield, make sure your machine has:
1. **Python 3.10 or higher** ([python.org](https://www.python.org/downloads/)) — *Be sure to check "Add Python to PATH" during installation.*
2. **Node.js 18 or higher** ([nodejs.org](https://nodejs.org/))
3. **Git** ([git-scm.com](https://git-scm.com/))

---

## Quick Start (Windows 1-Click)

If you are on Windows, you can get everything running in two clicks without typing commands:

1. **Initial Setup:** Double-click **`setup.bat`**  
   *(Installs all Python dependencies and npm packages automatically).*
2. **Launch Application:** Double-click **`start.bat`**  
   *(Starts both the FastAPI backend and Vite frontend, then opens your browser automatically).*

---

## Manual Installation & Run Guide

If you prefer using the terminal (macOS, Linux, or Windows PowerShell):

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/privshield.git
cd privshield
```

### 2. Backend Setup
Create and activate an optional virtual environment, then install dependencies:
```bash
# Optional: Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install Python requirements
pip install -r backend/requirements.txt
```

Start the FastAPI backend server:
```bash
python run_backend.py
```
> The backend server will start at: **`http://127.0.0.1:8000`**  
> Interactive OpenAPI documentation is available at: **`http://127.0.0.1:8000/docs`**

---

### 3. Frontend Setup
In a **new terminal window**, navigate to the `frontend` directory:
```bash
cd frontend

# Install npm packages
npm install

# Start the Vite development server
npm run dev
```
> The frontend application will start at: **`http://localhost:5173`**

Open your browser and navigate to **`http://localhost:5173`**.

---

## Verification & Testing Suite

PrivShield includes an extensive test suite covering unit math, API contracts, adversarial privacy attacks, and publication deliverables:

```bash
# Run all backend unit & adversarial tests (661 tests)
pytest backend/tests/

# Run the end-to-end multi-industry integration test suite (258 tests)
pytest tests_e2e/

# Run the publication-grade technical documentation & PDF verifier (48 checks)
python verify_documentation.py

# Verify frontend production build compilation
cd frontend && npm run build
```

---

## Project Structure

```
dsww/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # REST API endpoints (datasets, anonymization, recovery, export)
│   │   ├── core/              # Config, security sanitization, PII logging filters
│   │   ├── db/                # SQLite WAL repository & audit logging
│   │   ├── engine/            # K-Anonymity, L-Diversity, T-Closeness, Discovery, Utility (CURS)
│   │   ├── models/            # Pydantic schemas and domain models
│   │   └── services/          # Dataset ingestion, encryption vault, PDF generator, recovery
│   ├── storage/               # Isolated storage for raw encryptions, anonymized outputs, reports
│   ├── tests/                 # 661 unit, service layer, and adversarial tests
│   └── requirements.txt       # Python package dependencies
├── frontend/
│   ├── src/
│   │   ├── components/        # Reusable UI primitives, modals, data tables
│   │   ├── views/             # 8 workspace views (Studio, Discovery, Analysis, Recovery, etc.)
│   │   ├── types/             # TypeScript domain interfaces
│   │   └── services/          # Typed API client bridge
│   ├── package.json           # Node.js dependencies
│   └── vite.config.ts         # Vite build configuration
├── docs/                      # Technical whitepaper & 28-page certified PDF report
├── scripts/                   # Verification and PDF generation utilities
├── setup.bat                  # 1-click Windows dependency installer
├── start.bat                  # 1-click Windows application launcher
├── run_backend.py             # Backend launcher script
└── README.md                  # Project documentation
```

---

## License

This project is licensed under the MIT License.
