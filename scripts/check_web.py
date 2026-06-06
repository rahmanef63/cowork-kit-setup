#!/usr/bin/env python3
"""Static check of the generated webapp's Convex wiring (no toolchain needed).
Verifies every internal.<mod>.<fn> / api.<mod>.<fn> reference resolves to a
function defined in convex/<mod>.ts, and that the public/internal kind matches."""
import re, sys
from pathlib import Path

web = Path(sys.argv[1] if len(sys.argv) > 1 else
           "examples/real-estate-automation/web")
convex = web / "convex"
DEF = re.compile(r'export const (\w+)\s*=\s*(internalQuery|internalMutation|internalAction|query|mutation|action|httpAction)\b')
REF = re.compile(r'\b(internal|api)\.(\w+)\.(\w+)')

defined = {}   # module -> {name: kind}
for f in convex.glob("*.ts"):
    mod = f.stem
    for name, kind in DEF.findall(f.read_text("utf-8")):
        defined.setdefault(mod, {})[name] = kind

problems = []
refs = 0
for f in list(convex.glob("*.ts")) + list((web / "lib").glob("*.ts")) + list((web / "app").glob("*.tsx")):
    for kind, mod, name in REF.findall(f.read_text("utf-8")):
        refs += 1
        decl = defined.get(mod, {}).get(name)
        if decl is None:
            problems.append(f"{f.name}: {kind}.{mod}.{name} -> no such export in convex/{mod}.ts")
            continue
        is_internal_decl = decl.startswith("internal")
        if kind == "internal" and not is_internal_decl:
            problems.append(f"{f.name}: internal.{mod}.{name} but {name} is public ({decl})")
        if kind == "api" and is_internal_decl:
            problems.append(f"{f.name}: api.{mod}.{name} but {name} is internal ({decl})")

print("defined functions:")
for mod in sorted(defined):
    print(f"  {mod}: " + ", ".join(f"{n}({k})" for n, k in sorted(defined[mod].items())))
print(f"\nchecked {refs} references")
if problems:
    print(f"FAIL: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("PASS: all Convex references resolve with correct public/internal kind")
