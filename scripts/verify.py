#!/usr/bin/env python3
"""
verify.py — contract & template integrity checks (stdlib only, no deps).

Exits non-zero on any failure. Checks:
  1. Every *.json parses.
  2. For the template and each generated repo: the tool-handler set is identical
     across automation.config.json, the Python registry (when a `local/` surface
     exists), and the TS dispatcher (when a `web/` surface exists). Surfaces are
     optional — a repo may be Cowork-only, CLI-only, or include the webapp.
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
    return set(re.findall(r'["\']?(\w+)["\']?:\s*async\s*\(input', tools_ts.read_text("utf-8")))


def check_repo(label: str, repo: Path) -> None:
    global checks
    cfg_path = repo / "automation.config.json"
    if not cfg_path.is_file():
        return
    print(f"[{label}] {repo.relative_to(ROOT)}")
    cfg = json.loads(cfg_path.read_text("utf-8"))
    c = config_handlers(cfg)
    surfaces: list[str] = []

    local = repo / "local"
    if local.is_dir():
        surfaces.append("cli")
        for p in sorted(local.rglob("*.py")):
            checks += 1
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as exc:
                fail(f"py_compile {p.relative_to(ROOT)}: {exc.msg}")
        ok("python byte-compiles")
        checks += 1
        py = py_handlers(local / "automation/tools.py")
        if c == py:
            ok(f"config == python ({len(c)} handlers)")
        else:
            fail(f"config/python mismatch — config={sorted(c)} python={sorted(py)}")

    tools_ts = repo / "web/lib/tools.ts"
    if tools_ts.is_file():
        surfaces.append("web")
        checks += 1
        ts = ts_handlers(tools_ts)
        if c == ts:
            ok(f"config == typescript ({len(c)} handlers)")
        else:
            fail(f"config/ts mismatch — config={sorted(c)} ts={sorted(ts)}")

    ok(f"surfaces present: {', '.join(surfaces) or 'cowork-only'}")


def main() -> int:
    global checks
    print("== JSON validity ==")
    for j in sorted(ROOT.rglob("*.json")):
        if ("/node_modules/" in str(j) or "/_generated/" in str(j)
                or j.name.startswith("tsconfig")):  # tsconfig is JSONC, not strict JSON
            continue
        checks += 1
        try:
            json.loads(j.read_text("utf-8"))
        except Exception as exc:
            fail(f"invalid JSON {j.relative_to(ROOT)}: {exc}")
    ok("all JSON parses")

    print("== template & examples ==")
    check_repo("template", TEMPLATE)
    for label, sub in (("example", "examples"), ("project", "projects")):
        base = ROOT / sub
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if (d / "automation.config.json").is_file():
                    check_repo(label, d)

    print("== scaffolder dry-run (default + web) ==")
    for label, extra in (("default", []), ("with --web", ["--web"])):
        checks += 1
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(
                [sys.executable, str(SCAFFOLD), "--domain", "ci smoke test",
                 "--out", tmp + "/out", "--dry-run", *extra],
                capture_output=True, text=True,
            )
            if r.returncode == 0 and "DRY RUN" in r.stdout:
                ok(f"scaffold --dry-run {label}")
            else:
                fail(f"scaffold dry-run {label} failed: {r.stderr.strip() or r.stdout.strip()}")

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
