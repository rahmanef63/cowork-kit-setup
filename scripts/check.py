#!/usr/bin/env python3
"""check.py — run every repo check locally (no cloud CI).

Run by hand:        python3 scripts/check.py
Run automatically:  via the git pre-commit hook (hooks/pre-commit).
Wraps verify.py (contract/template/scaffold) and a node --check of the wizard.
"""
from __future__ import annotations
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(desc, cmd):
    print(f"\n=== {desc} ===")
    return subprocess.run(cmd, cwd=ROOT).returncode == 0


def main() -> int:
    ok = True
    ok &= run("contract integrity (verify.py)", [sys.executable, "scripts/verify.py"])
    node = shutil.which("node")
    if node:
        ok &= run("wizard syntax", [node, "--check", "wizard/server.mjs"])
    else:
        print("\n=== wizard syntax ===\n  skipped (node not found)")
    print("\n" + ("ALL CHECKS PASSED" if ok else "CHECKS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
