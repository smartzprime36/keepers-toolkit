"""Run every test suite in the toolkit. Offline; synthetic data only.

    python3 run_tests.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [("journal", "test_journal"), ("txreader", "test_tx_parse"),
          ("walletview", "test_render_board")]


def main():
    failed = []
    for folder, module in SUITES:
        print(f"=== {folder}/{module} ===")
        r = subprocess.run(
            [sys.executable, "-m", "unittest", module, "-v"],
            cwd=os.path.join(HERE, folder))
        if r.returncode != 0:
            failed.append(folder)
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("all suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
