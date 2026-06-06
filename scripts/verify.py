#!/usr/bin/env python3
"""
verify.py — contract & template integrity checks (stdlib only, no deps).

Run locally or in CI. Exits non-zero on any failure. Checks:
  1. Every *.json in the repo parses.
  2. For the template and each generated example: the tool handler set is
     identical across automation.config.json, the Python registry (tools.py),
     and the TypeScript dispatcher (tools.ts) — the contract cannot drift.
  3. Every local Python file byte-compiles.
  4. The scaffolder runs (dry-run) for a fresh domain.
"""
from __future__ import annotations

import json
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = ROOT / "skills/cowork-automation-generator/scripts/scaffold.py"
TEMPLATE = ROOT / "skills/cowork-automation-generator/assets/templates"

failures: list[str] = []
checks = 0


def ok(msg: str) -> None:
    print(f"  ok   {msg}")


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL {msg}")


def config_handlers(cfg: dict) -> set[str]:
    return {t["handler"] for t in cfg.get("tools", [])}


def py_handlers(tools_py: Path) -> set[str]:
    return set(re.findall(r'@register\("(\w+)"\)', tools_py.read_text("utf-8")))


def ts_handlers(tools_ts: Path) -> set[str]:
    text = tools_ts.read_text("utf-8")
    return set(re.findall(r'["\']?(\w+)["\']?:\s*async\s*\(input', text))


def check_repo(label: str, repo: Path) -> None:
    global checks
    cfg_path = repo / "automation.config.json"
    tools_py = repo / "local/automation/tools.py"
    tools_ts = repo / "web/lib/tools.ts"
    if not cfg_path.is_file():
        return
    print(f"[{label}] {repo.relative_to(ROOT)}")
    cfg = json.loads(cfg_path.read_text("utf-8"))

    # py_compile every python file
    for p in sorted((repo / "local").rglob("*.py")):
        checks += 1
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as exc:
            fail(f"py_compile {p.relative_to(ROOT)}: {exc.msg}")
    ok("python byte-compiles")

    # cross-language consistency
    checks += 1
    c, py, ts = config_handlers(cfg), py_handlers(tools_py), ts_handlers(tools_ts)
    if c == py == ts:
        ok(f"handlers consistent across config/python/ts ({len(c)})")
    else:
        fail(
            f"handler mismatch — config={sorted(c)} python={sorted(py)} ts={sorted(ts)}"
        )


def main() -> int:
    global checks
    print("== JSON validity ==")
    for j in sorted(ROOT.rglob("*.json")):
        if "/node_modules/" in str(j) or "/_generated/" in str(j):
            continue
        checks += 1
        try:
            json.loads(j.read_text("utf-8"))
        except Exception as exc:
            fail(f"invalid JSON {j.relative_to(ROOT)}: {exc}")
    ok("all JSON parses")

    print("== template & examples ==")
    check_repo("template", TEMPLATE)
    examples = ROOT / "examples"
    if examples.is_dir():
        for d in sorted(examples.iterdir()):
            if (d / "automation.config.json").is_file():
                check_repo("example", d)

    print("== scaffolder dry-run ==")
    checks += 1
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(
            [sys.executable, str(SCAFFOLD), "--domain", "ci smoke test",
             "--out", tmp + "/out", "--dry-run"],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and "DRY RUN" in r.stdout:
            ok("scaffold --dry-run works")
        else:
            fail(f"scaffold dry-run failed: {r.stderr.strip() or r.stdout.strip()}")

    print()
    if failures:
        print(f"FAILED: {len(failures)} of {checks} checks")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASSED: {checks} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
