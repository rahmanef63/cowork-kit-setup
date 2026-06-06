#!/usr/bin/env python3
"""
check.py — run every repo check locally (no cloud CI).

Run by hand:        python3 scripts/check.py
Run automatically:  via the git pre-commit hook (see hooks/pre-commit).

Wraps: verify.py (contract/template/scaffold), check_web.py (Convex wiring on the
template), and a `node --check` of the wizard (skipped if node isn't installed).
Exits non-zero if anything fails.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(desc: str, cmd: list[str]) -> bool:
    print(f"\n=== {desc} ===")
    return subprocess.run(cmd, cwd=ROOT).returncode == 0


def main() -> int:
    ok = True
    ok &= run("contract integrity (verify.py)", [sys.executable, "scripts/verify.py"])
    ok &= run(
        "webapp Convex wiring (template)",
        [sys.executable, "scripts/check_web.py",
         "skills/cowork-automation-generator/assets/templates/web"],
    )
    node = shutil.which("node")
    if node:
        ok &= run("wizard syntax", [node, "--check", "wizard/server.mjs"])
    else:
        print("\n=== wizard syntax ===\n  skipped (node not found)")
    print("\n" + ("ALL CHECKS PASSED ✓" if ok else "CHECKS FAILED ✗"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
