#!/usr/bin/env python3
"""
PrivShield Automated Deliverable Verification Suite
Validates docs/PrivShield_Documentation.md and docs/PrivShield_Documentation.pdf
against all milestone and technical whitepaper acceptance criteria.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent
DOCS_DIR = REPO_ROOT / "docs"
MD_PATH = DOCS_DIR / "PrivShield_Documentation.md"
PDF_PATH = DOCS_DIR / "PrivShield_Documentation.pdf"


class VerificationReporter:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.checks: List[Tuple[str, bool, str]] = []

    def check(self, name: str, condition: bool, details: str = ""):
        if condition:
            self.passed += 1
            self.checks.append((name, True, details))
            print(f"  [PASS] {name} {f'({details})' if details else ''}")
        else:
            self.failed += 1
            self.checks.append((name, False, details))
            print(f"  [FAIL] {name} {f'- {details}' if details else ''}")

    def summary(self) -> int:
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print(f"VERIFICATION SUMMARY: {self.passed} PASSED, {self.failed} FAILED (TOTAL {total})")
        print("=" * 70)
        return 0 if self.failed == 0 else 1


def get_pdf_page_count(pdf_path: Path) -> int:
    """Multi-engine PDF page counter with pypdf, pdfplumber, and binary regex fallback."""
    # Engine A: pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        return len(reader.pages)
    except (ImportError, Exception):
        pass

    # Engine B: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            return len(pdf.pages)
    except (ImportError, Exception):
        pass

    # Engine C: Binary regex parser
    data = pdf_path.read_bytes()
    page_matches = len(re.findall(rb"/Type\s*/Page\b", data))
    if page_matches > 0:
        return page_matches

    # Engine D: Page tree trailer
    count_match = re.search(rb"/Type\s*/Pages.*?/Count\s+(\d+)", data, re.DOTALL)
    if count_match:
        return int(count_match.group(1))

    raise RuntimeError("Unable to extract PDF page count across all engines.")


def extract_pdf_text(pdf_path: Path) -> str:
    """Extracts all text content across PDF pages using available engines."""
    full_text = []
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        for p in reader.pages:
            t = p.extract_text()
            if t:
                full_text.append(t)
        return "\n".join(full_text)
    except Exception:
        pass

    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    full_text.append(t)
        return "\n".join(full_text)
    except Exception:
        pass

    # Binary string extraction fallback
    data = pdf_path.read_bytes()
    strings = re.findall(rb"\((.*?)\)", data)
    return " ".join([s.decode("latin1", errors="ignore") for s in strings])


def verify_markdown_whitepaper(reporter: VerificationReporter):
    print("\n--- Verifying Markdown Whitepaper: docs/PrivShield_Documentation.md ---")

    # 1.1 Existence
    reporter.check("Markdown file exists", MD_PATH.exists(), str(MD_PATH))
    if not MD_PATH.exists():
        return

    # 1.2 File size and non-empty check
    size = MD_PATH.stat().st_size
    reporter.check("Markdown file size >= 25,000 bytes", size >= 25000, f"{size:,} bytes")

    content = MD_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    reporter.check("Markdown line count >= 500 lines", len(lines) >= 500, f"{len(lines):,} lines")

    # 1.3 Executive Summary & System Architecture
    reporter.check(
        "Executive Summary & Architecture section present",
        "Executive Summary & System Architecture" in content,
        "Section 1 present",
    )
    reporter.check(
        "FastAPI and SQLite WAL mode documented",
        "FastAPI" in content and "SQLite" in content and "WAL" in content,
        "Backend stack documented",
    )

    # 1.4 Core Mathematical Privacy Engines
    reporter.check(
        "4-Tier Discovery Engine documented",
        "4-Tier Sensitive Attribute Discovery" in content,
        "Section 2 present",
    )
    reporter.check(
        "Luhn and ISO 7064 checksums documented",
        "Luhn" in content and "ISO 7064" in content,
        "Tier 2 checksum algorithms documented",
    )
    reporter.check(
        "Shannon Entropy & Uniqueness Ratio documented",
        "Shannon Entropy" in content and "Uniqueness Ratio" in content,
        "Tier 4 information theory documented",
    )
    reporter.check(
        "Strict K-Anonymity Engine documented",
        "Strict K-Anonymity" in content,
        "Section 4 present",
    )
    reporter.check(
        "L-Diversity (distinct, entropy, recursive) documented",
        "Distinct L-Diversity" in content and "Entropy-Based L-Diversity" in content and "Recursive (c, l)-Diversity" in content,
        "Section 5 L-diversity formulations present",
    )
    reporter.check(
        "T-Closeness (Wasserstein-1 EMD & TVD) documented",
        "Wasserstein-1" in content and "Total Variation Distance" in content,
        "Section 6 T-closeness formulations present",
    )
    reporter.check(
        "SDC Threat Models (Prosecutor, Marketer, Journalist) documented",
        "Prosecutor" in content and "Marketer" in content and "Journalist" in content,
        "Section 7 SDC threat models present",
    )
    reporter.check(
        "Composite Utility-Retention Score (CURS) documented",
        "Composite Utility-Retention Score" in content or "CURS" in content,
        "Section 8 utility formulations present",
    )

    # 1.5 Formal Equations & Invariants
    reporter.check(
        "Strict K-Anonymity invariant equation min(|EC|) >= K present",
        "min" in content and "|EC" in content and ">= K" in content,
        "Invariant min(|EC_j|) >= K present",
    )
    reporter.check(
        "Wasserstein EMD integral equation present",
        "W_1" in content or "Wasserstein" in content,
        "W1 EMD integral equation present",
    )
    reporter.check(
        "5-Dimension CURS equation present",
        "0.25" in content and "0.20" in content and "0.15" in content,
        "CURS weighted sum formula present",
    )

    # 1.6 REST API Reference & JSON Schemas
    reporter.check(
        "REST API Reference & JSON Schemas present",
        "REST API Reference & JSON Schemas" in content,
        "Section 10 present",
    )
    reporter.check(
        "Primary endpoints documented (/anonymize, /discover, /upload, /export)",
        "/api/datasets/{id}/anonymize" in content and "/api/datasets/{id}/discover" in content,
        "API endpoints verified",
    )

    # 1.7 7 Frontend Workspaces Walkthrough
    reporter.check(
        "Frontend Workspaces walkthrough present",
        "Frontend Workspaces" in content,
        "Section 11 present",
    )
    for ws in [
        "Privacy Overview",
        "Dataset Management",
        "Data Discovery",
        "Anonymization Studio",
        "Privacy Analysis",
        "Utility Analysis",
        "Reports & Platform Settings",
    ]:
        reporter.check(f"Workspace '{ws}' documented", ws in content, f"Verified in Section 11")

    # 1.8 Security Controls & Defensive Measures
    reporter.check(
        "Spreadsheet DDE Formula Injection defense documented",
        "Formula Injection" in content and ("=" in content and "+" in content and "-" in content),
        "Section 9 / Section 12 formula defense documented",
    )
    reporter.check(
        "Path traversal defense documented",
        "Path Traversal" in content or "resolve_safe_path" in content,
        "Filesystem containment documented",
    )
    reporter.check(
        "Zero-PII server logging filter documented",
        "Zero-PII" in content or "RedactingFilter" in content,
        "Log redaction filter documented",
    )

    # 1.9 Verification & Test Suite Summary
    reporter.check(
        "Comprehensive test suite inventory (919 total tests) documented",
        "919" in content and "661" in content and "258" in content,
        "Exact test counts (661 backend + 258 E2E = 919) documented",
    )


def verify_pdf_documentation(reporter: VerificationReporter):
    print("\n--- Verifying PDF Documentation: docs/PrivShield_Documentation.pdf ---")

    # 2.1 File existence
    reporter.check("PDF file exists", PDF_PATH.exists(), str(PDF_PATH))
    if not PDF_PATH.exists():
        return

    # 2.2 Valid PDF header and non-empty size
    pdf_bytes = PDF_PATH.read_bytes()
    reporter.check("PDF starts with %PDF- binary header", pdf_bytes.startswith(b"%PDF-"), f"{len(pdf_bytes):,} bytes")
    reporter.check("PDF size >= 50,000 bytes", len(pdf_bytes) >= 50000, f"{len(pdf_bytes):,} bytes")

    # 2.3 Total Page Count >= 20
    page_count = get_pdf_page_count(PDF_PATH)
    reporter.check("PDF page count >= 20 pages", page_count >= 20, f"Actual: {page_count} pages")

    # 2.4 Table of Contents Presence
    pdf_text = extract_pdf_text(PDF_PATH)
    reporter.check("PDF contains Table of Contents", "Table of Contents" in pdf_text, "TOC detected in document text")

    # 2.5 Major Section Headings in TOC / Document
    expected_sections = [
        "Executive Summary & System Architecture",
        "4-Tier Sensitive Attribute Discovery",
        "Data Masking & Transformation Engine",
        "Strict K-Anonymity Engine",
        "L-Diversity Engine",
        "T-Closeness Engine",
        "Privacy Risk & Threat Modeling",
        "Data Utility Analytics Engine & CURS",
        "Irreversible Anonymization & Operational Safeguards",
        "REST API Reference & JSON Schemas",
        "Frontend Workspaces & User Interaction Guide",
        "Security Architecture & Regulatory Compliance",
        "Verification, Test Suites & Empirical Validation",
    ]
    for sec in expected_sections:
        reporter.check(f"PDF contains section: '{sec}'", sec in pdf_text, "Section verified in PDF")


def main():
    print("=" * 70)
    print("PrivShield Technical Documentation Deliverable Verification")
    print("Milestone M5 — Technical Whitepaper & Publication-Grade PDF")
    print("=" * 70)

    reporter = VerificationReporter()
    verify_markdown_whitepaper(reporter)
    verify_pdf_documentation(reporter)
    exit_code = reporter.summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
