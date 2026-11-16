"""
tests_e2e/run_e2e_tests.py - PrivShield Standalone E2E Test Suite Runner.
Executes multi-industry test tiers, verifies mathematical invariants, and outputs a formatted audit report.
Returns exit code 0 on 100% pass, or exit code 1 if any test fails.
"""

import argparse
import os
import sys
import time
import pytest


BANNER = r"""
================================================================================
  _____       _       _____ _     _      _     _ 
 |  __ \     (_)     / ____| |   (_)    | |   | |
 | |__) | __  _ _   _| (___ | |__  _  ___| | __| |
 |  ___/ '__|| \ \ / /\___ \| '_ \| |/ _ \ |/ _` |
 | |   | |   | |\ V / ____) | | | | |  __/ | (_| |
 |_|   |_|   |_| \_/ |_____/|_| |_|_|\___|_|\__,_|
  UNIVERSAL ENTERPRISE DATA PRIVACY & ANONYMIZATION PLATFORM
  Multi-Industry 4-Tier End-to-End Test Verification Runner
================================================================================
"""


def main():
    parser = argparse.ArgumentParser(description="PrivShield E2E Test Runner")
    parser.add_argument("--tier", type=str, choices=["1", "2", "3", "4", "5", "all", "full"], default="all",
                        help="Select test tier to run: 1 (Features), 2 (Boundaries), 3 (Combinations), 4 (Scenarios), 5 (Adversarial), all (Tiers 1-4), or full (Tiers 1-5)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose pytest output")
    parser.add_argument("-k", "--keyword", type=str, default="", help="Filter tests by keyword expression")
    args = parser.parse_args()

    tests_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(tests_dir, ".."))

    # Ensure paths are in sys.path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    backend_dir = os.path.join(project_root, "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    print(BANNER)
    print(f"[*] Workspace Root: {project_root}")
    print(f"[*] Test Root:      {tests_dir}")
    print(f"[*] Python Runtime: {sys.version.split()[0]} ({sys.platform})")
    print(f"[*] Target Tier:    {args.tier.upper()}")
    print("-" * 80)

    # Build pytest target list
    targets = []
    if args.tier in ("1", "all", "full"):
        targets.append(os.path.join(tests_dir, "tier1_features"))
    if args.tier in ("2", "all", "full"):
        targets.append(os.path.join(tests_dir, "tier2_boundaries"))
    if args.tier in ("3", "all", "full"):
        targets.append(os.path.join(tests_dir, "tier3_combinations"))
    if args.tier in ("4", "all", "full"):
        targets.append(os.path.join(tests_dir, "tier4_real_world"))
    if args.tier in ("5", "full"):
        targets.append(os.path.join(tests_dir, "tier5_adversarial"))

    pytest_args = ["-q"]
    if args.verbose:
        pytest_args = ["-v"]
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])

    pytest_args.extend(targets)

    start_time = time.time()
    exit_code = pytest.main(pytest_args)
    elapsed = time.time() - start_time

    print("-" * 80)
    if exit_code == 0:
        print(f"[+] SUCCESS: All targeted tests PASSED in {elapsed:.2f}s!")
        print(f"[+] All mathematical invariants (Strict K, Distinct L, T-Closeness, CURS, Formula Defense) satisfied.")
    else:
        print(f"[-] FAILURE: Test suite failed with exit code {exit_code} (elapsed: {elapsed:.2f}s).")
    print("=" * 80)

    sys.exit(int(exit_code))


if __name__ == "__main__":
    main()
