#!/usr/bin/env python3
"""
verify.py — contract & template integrity checks (stdlib only, no deps).

Exits non-zero on any failure. Per template/project:
  - every *.json parses (tsconfig/_generated/node_modules skipped)
  - if local/ : Python byte-compiles AND config tool handlers == the CLI registry
  - if mcp/   : Python byte-compiles AND the FastMCP server is present
  - if web/   : package.json parses and carries no Convex/Anthropic deps (it's local-fs)
  - the scaffolder dry-runs (default and --web --mcp)
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


def ok(m): print(f"  ok   {m}")
def fail(m): failures.append(m); print(f"  FAIL {m}")


def config_handlers(cfg): return {t["handler"] for t in cfg.get("tools", [])}
def py_handlers(p): return set(re.findall(r'@register\("(\w+)"\)', p.read_text("utf-8")))


def compile_dir(d: Path, label: str):
    global checks
    bad = False
    for p in sorted(d.rglob("*.py")):
        checks += 1
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as exc:
            fail(f"py_compile {p.relative_to(ROOT)}: {exc.msg}"); bad = True
    if not bad:
        ok(f"{label} python byte-compiles")


def check_repo(label: str, repo: Path) -> None:
    global checks
    cfg_path = repo / "automation.config.json"
    if not cfg_path.is_file():
        return
    print(f"[{label}] {repo.relative_to(ROOT)}")
    cfg = json.loads(cfg_path.read_text("utf-8"))
    c = config_handlers(cfg)
    surfaces = []

    local = repo / "local"
    if local.is_dir():
        surfaces.append("cli")
        compile_dir(local, "cli")
        checks += 1
        py = py_handlers(local / "automation/tools.py")
        if c == py:
            ok(f"config == CLI registry ({len(c)} handlers)")
        else:
            fail(f"config/CLI mismatch — config={sorted(c)} cli={sorted(py)}")

    mcp = repo / "mcp"
    if mcp.is_dir():
        surfaces.append("mcp")
        compile_dir(mcp, "mcp")
        checks += 1
        srv = (mcp / "server.py").read_text("utf-8") if (mcp / "server.py").is_file() else ""
        ok("mcp FastMCP server present") if "FastMCP(" in srv else fail("mcp server.py missing FastMCP")

    web = repo / "web"
    if web.is_dir():
        surfaces.append("web")
        checks += 1
        pkg_path = web / "package.json"
        try:
            pkg = json.dumps(json.loads(pkg_path.read_text("utf-8")))
            if "convex" in pkg or "@anthropic" in pkg:
                fail("web/package.json still references convex/anthropic (should be local-fs)")
            else:
                ok("web is local-fs (no convex/anthropic deps)")
        except Exception as exc:
            fail(f"web/package.json invalid: {exc}")

    ok(f"surfaces present: {', '.join(surfaces) or 'cowork-only'}")


def main() -> int:
    global checks
    print("== JSON validity ==")
    for j in sorted(ROOT.rglob("*.json")):
        s = str(j)
        if "/node_modules/" in s or "/_generated/" in s or j.name.startswith("tsconfig"):
            continue
        checks += 1
        try:
            json.loads(j.read_text("utf-8"))
        except Exception as exc:
            fail(f"invalid JSON {j.relative_to(ROOT)}: {exc}")
    ok("all JSON parses")

    print("== template & projects ==")
    check_repo("template", TEMPLATE)
    for sub in ("examples", "projects"):
        base = ROOT / sub
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if (d / "automation.config.json").is_file():
                    check_repo(sub.rstrip("s"), d)

    print("== scaffolder dry-run ==")
    for label, extra in (("default", []), ("--web --mcp", ["--web", "--mcp"])):
        checks += 1
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, str(SCAFFOLD), "--domain", "ci smoke",
                                "--out", tmp + "/o", "--dry-run", *extra], capture_output=True, text=True)
            ok(f"scaffold --dry-run {label}") if (r.returncode == 0 and "DRY RUN" in r.stdout) \
                else fail(f"scaffold dry-run {label}: {r.stderr.strip() or r.stdout.strip()}")

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
