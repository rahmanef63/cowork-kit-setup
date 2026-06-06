#!/usr/bin/env python3
"""
scaffold.py — materialize a Cowork automation repo from a domain config.
============================================================================
This is the deterministic half of the cowork-automation-generator skill. The
*design* (which domain tools, workflows, best practices) is done by Claude using
the references/ docs; this script turns that design into a working monorepo:

    local/  -> Python CLI (direct + Agent SDK engines)
    web/    -> Next.js + Convex + BYOK webapp
    automation.config.json  -> the shared contract both runtimes read
    docs/, README.md, .cowork/skills/<domain>-ops/SKILL.md

Two modes:
  1. Full design (recommended): pass a complete config produced by Claude.
       python scaffold.py --config design.json --out ./acme-automation
  2. Minimal: just a domain name; you get the 6 core tools + tuned metadata.
       python scaffold.py --domain "real estate" --out ./real-estate-automation

Domain tools whose handler is not one of the six core handlers get a valid stub
injected into BOTH languages (at the SCAFFOLD:DOMAIN_TOOLS markers) so the repo's
`doctor`/validation passes out of the box and you only fill in the body.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES = SCRIPT_DIR.parent / "assets" / "templates"

CORE_HANDLERS = {
    "read_document",
    "list_workspace",
    "write_deliverable",
    "save_record",
    "lookup_record",
    "create_task",
}

IDENT_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PY_MARKER = "# >>> SCAFFOLD:DOMAIN_TOOLS <<<"
TS_MARKER = "// >>> SCAFFOLD:DOMAIN_TOOLS <<<"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower())
    return s.strip("-") or "automation"


def titlecase(text: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[-_\s]+", str(text)) if w)


def die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


# --------------------------------------------------------------------------- #
# Config construction + validation
# --------------------------------------------------------------------------- #
def load_template_config() -> dict:
    return json.loads((TEMPLATES / "automation.config.json").read_text("utf-8"))


def build_minimal_config(domain: str, display: str | None, description: str | None) -> dict:
    cfg = load_template_config()
    slug = slugify(domain)
    name = display or titlecase(domain)
    cfg["domain"] = slug
    cfg["displayName"] = name
    cfg["description"] = description or f"Automation kit for {name.lower()} operations."
    cfg["systemPrompt"] = (
        f"You are a meticulous operations agent for a {name.lower()} team. "
        "You complete multi-step tasks end to end with the available tools: read "
        "source files, produce deliverables, keep simple records, and create "
        "follow-up tasks. Prefer doing the work over describing it. State any "
        "assumptions you make. Write outputs to ./output and confirm what you produced."
    )
    return cfg


def validate_config(cfg: dict) -> None:
    for key in ("domain", "displayName", "model", "systemPrompt", "tools"):
        if not cfg.get(key):
            die(f"config is missing required key: {key!r}")
    seen: set[str] = set()
    for i, spec in enumerate(cfg.get("tools", [])):
        for k in ("name", "handler", "input_schema"):
            if k not in spec:
                die(f"tools[{i}] is missing {k!r}")
        name, handler = spec["name"], spec["handler"]
        if not IDENT_RE.match(name):
            die(f"tool name {name!r} must be snake_case (^[a-z][a-z0-9_]*$)")
        if not IDENT_RE.match(handler):
            die(f"tool handler {handler!r} must be snake_case (^[a-z][a-z0-9_]*$)")
        if name in seen:
            die(f"duplicate tool name {name!r}")
        seen.add(name)
        schema = spec["input_schema"]
        if not isinstance(schema, dict) or schema.get("type") != "object":
            die(f"tools[{i}].input_schema must be a JSON Schema object (type: object)")


def domain_handlers(cfg: dict) -> list[str]:
    """Unique handlers not covered by the core registry, in first-seen order."""
    out: list[str] = []
    for spec in cfg["tools"]:
        h = spec["handler"]
        if h not in CORE_HANDLERS and h not in out:
            out.append(h)
    return out


# --------------------------------------------------------------------------- #
# Domain-tool stub injection
# --------------------------------------------------------------------------- #
def py_stub(handler: str, tool_name: str) -> str:
    return (
        f'@register("{handler}")\n'
        f"def {handler}(args: dict) -> dict:\n"
        f'    """TODO: implement domain tool \'{tool_name}\'. Auto-generated stub."""\n'
        f'    return {{"content": "TODO: implement \'{handler}\'. Received args: "\n'
        f"                       + compact_args(args, 400)}}\n"
    )


def ts_stub_block(handlers: list[dict]) -> str:
    lines = ["Object.assign(handlers, {"]
    for h in handlers:
        lines.append(f'  "{h["handler"]}": async (input, _ctx) => {{')
        lines.append(f'    // TODO: implement domain tool "{h["name"]}".')
        lines.append(
            f'    return `TODO: implement "{h["handler"]}". Received: ${{JSON.stringify(input)}}`;'
        )
        lines.append("  },")
    lines.append("});")
    return "\n".join(lines)


def inject_python(out: Path, cfg: dict, handlers: list[str]) -> None:
    path = out / "local" / "automation" / "tools.py"
    text = path.read_text("utf-8")
    if PY_MARKER not in text:
        die(f"python marker not found in {path} (template drift?)")
    if handlers:
        name_by_handler = {s["handler"]: s["name"] for s in cfg["tools"]}
        stubs = "\n\n".join(py_stub(h, name_by_handler[h]) for h in handlers)
        replacement = f"{PY_MARKER}\n{stubs}"
    else:
        replacement = f"{PY_MARKER}\n# (no domain-specific tools)"
    path.write_text(text.replace(PY_MARKER, replacement), "utf-8")


def inject_typescript(out: Path, cfg: dict, handlers: list[str]) -> None:
    path = out / "web" / "lib" / "tools.ts"
    text = path.read_text("utf-8")
    if TS_MARKER not in text:
        die(f"typescript marker not found in {path} (template drift?)")
    if handlers:
        specs = [s for s in cfg["tools"] if s["handler"] in handlers]
        # de-dup by handler, preserve order
        seen, uniq = set(), []
        for s in specs:
            if s["handler"] not in seen:
                seen.add(s["handler"])
                uniq.append(s)
        block = ts_stub_block(uniq)
        replacement = f"{TS_MARKER}\n{block}"
    else:
        replacement = f"{TS_MARKER}\n// (no domain-specific tools)"
    path.write_text(text.replace(TS_MARKER, replacement), "utf-8")


# --------------------------------------------------------------------------- #
# Doc rendering
# --------------------------------------------------------------------------- #
def tools_table(cfg: dict) -> str:
    rows = ["| Tool | Purpose |", "| --- | --- |"]
    for s in cfg["tools"]:
        desc = s["description"].split(". ")[0].strip().rstrip(".")
        rows.append(f"| `{s['name']}` | {desc} |")
    return "\n".join(rows)


def workflows_list(cfg: dict) -> str:
    wfs = cfg.get("workflows", [])
    if not wfs:
        return "_No workflows defined yet._"
    out = []
    for w in wfs:
        sched = f" — scheduled `{w['schedule']}`" if w.get("schedule") else " — on-demand"
        out.append(f"- **{w['name']}**{sched}: {w['description']}")
    return "\n".join(out)


def best_practices_block(cfg: dict) -> str:
    bps = cfg.get("bestPractices", [])
    if not bps:
        return "_No domain best practices captured yet._"
    return "\n".join(f"- **{b['title']}** — {b['detail']}" for b in bps)


def render_readme(cfg: dict) -> str:
    name = cfg["displayName"]
    connectors = ", ".join(cfg.get("suggestedConnectors", [])) or "none suggested"
    return f"""# {name} — Automation Kit

{cfg['description']}

Generated by the **cowork-automation-generator**. One repo, three ways to run the
same automations: inside **Cowork**, from a **local Python CLI**, or via a
**Next.js + Convex webapp** where each user brings their own Anthropic API key (BYOK).

## What it automates

{tools_table(cfg)}

### Workflows
{workflows_list(cfg)}

## Best practices for this field
{best_practices_block(cfg)}

Suggested Cowork connectors: {connectors}.

## Run it locally (Python CLI)

```bash
cd local
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e .
cp .env.example .env        # add your ANTHROPIC_API_KEY
automation doctor           # checks key, config, and tool registry
automation run "Summarize everything in ./inbox and list follow-ups"
automation workflow {cfg.get('workflows', [{'name': 'process-inbox'}])[0]['name']}
```

Pick the engine with `--engine direct` (default; plain Anthropic SDK loop) or
`--engine agent` (Claude Agent SDK). Add `--stream` to stream tokens.

## Run it as a webapp (Next.js + Convex, BYOK)

```bash
cd web
npm install
npx convex dev        # creates convex/_generated and sets NEXT_PUBLIC_CONVEX_URL
npm run dev           # http://localhost:3000
```

Open the app, paste your Anthropic API key (stored per session in Convex, never
logged), type a task, and watch the agent work with a live transcript. See
`web/README.md` for the streaming details and the production security note.

## Use it inside Cowork

Copy `.cowork/skills/{cfg['domain']}-ops` into your Cowork skills folder (or this
whole repo into a folder you grant Cowork access to). See `docs/cowork-setup.md`.

## How it fits together

`automation.config.json` is the single source of truth — tool names, schemas,
system prompt, and workflows. The Python registry (`local/automation/tools.py`)
and the TypeScript dispatcher (`web/lib/tools.ts`) both implement the same tool
handlers, so behavior stays consistent across every surface. Domain-specific
tools were stubbed for you to implement (look for `TODO` in those two files).
"""


def render_best_practices_doc(cfg: dict) -> str:
    return f"""# Best Practices — {cfg['displayName']}

These are tuned for this field. They follow the generator's framework:
decompose recurring work, match each task to the right Cowork capability, choose
a deployment surface, and add guardrails.

## Field-specific guidance
{best_practices_block(cfg)}

## Universal checklist (applies to every automation here)
- Scope folder access: point Cowork (or the CLI workspace) at one working folder, not your whole drive.
- Keep deterministic steps in tools; keep judgement in the prompt.
- Gate irreversible or external actions (sending, paying, posting) behind explicit human approval.
- Never paste secrets/keys into prompts. The webapp uses BYOK; the CLI reads the key from `.env`.
- Add a verification step for anything high-stakes (re-read the output, check figures).
- Schedule the recurring parts ({workflows_list(cfg)}).
- Start with one high-frequency, low-stakes workflow; expand once it's trusted.
- Remember the research-preview limits: Chrome automation is slow; complex spreadsheets parse poorly.
"""


def render_cowork_setup_doc(cfg: dict) -> str:
    connectors = cfg.get("suggestedConnectors", [])
    conn_lines = "\n".join(f"  - {c}" for c in connectors) or "  - (none suggested)"
    sched = [w for w in cfg.get("workflows", []) if w.get("schedule")]
    sched_lines = (
        "\n".join(f"  - `{w['schedule']}` → {w['name']}: {w['description']}" for w in sched)
        or "  - (no scheduled workflows; all on-demand)"
    )
    return f"""# Using {cfg['displayName']} inside Cowork

Cowork is the fastest way to *run* these automations interactively.

## 1. Give Cowork the folder
Put this repo (or just your working files) in a folder and grant Cowork access to
it. The agent reads from `./inbox` and writes deliverables to `./output`.

## 2. Install the drop-in skill
This repo ships a Cowork skill at `.cowork/skills/{cfg['domain']}-ops/SKILL.md`.
Copy that folder into your Cowork/Claude skills directory so Claude loads the
domain workflows automatically.

## 3. Connect suggested connectors (MCP)
Enable these in Cowork → Settings → Connectors:
{conn_lines}

If a connector for your tool isn't available yet, Cowork can fall back to the
Chrome extension for web tasks (slower, screenshot-based).

## 4. Schedule the recurring work
Create scheduled tasks for:
{sched_lines}

## 5. Guardrails
Keep external/irreversible actions human-approved. Review the agent's plan in the
progress sidebar before letting it act on anything that leaves your machine.
"""


def render_cowork_skill(cfg: dict) -> str:
    name = cfg["displayName"]
    wf_lines = "\n".join(
        f"- **/{w['name']}** — {w['description']}\n  Prompt: {w['prompt']}"
        for w in cfg.get("workflows", [])
    ) or "- (define workflows in automation.config.json)"
    tool_lines = "\n".join(f"- `{s['name']}`: {s['description']}" for s in cfg["tools"])
    desc = (
        f"{name} operations automation. Use whenever the user works on {name.lower()} "
        f"tasks — intake, drafting, records, follow-ups, reporting — or names this domain. "
        f"Reads ./inbox, writes ./output, keeps records in ./.data."
    )
    return f"""---
name: {cfg['domain']}-ops
description: {desc}
---

# {name} Operations

You automate {name.lower()} knowledge work. Prefer doing the work with tools over
describing it. Write deliverables to `./output`; log structured data with records;
create tasks for human follow-ups. State assumptions when a request is ambiguous.

## System role
{cfg['systemPrompt']}

## Available tools
{tool_lines}

## Workflows
{wf_lines}

## Guardrails
- Gate any irreversible or external action (send, pay, post) behind explicit approval.
- Keep folder access scoped; never echo secrets.
- Verify high-stakes outputs before finishing.
"""


# --------------------------------------------------------------------------- #
# Main scaffold routine
# --------------------------------------------------------------------------- #
def copy_template(out: Path, force: bool) -> None:
    if out.exists() and any(out.iterdir()) and not force:
        die(f"output dir {out} is not empty (use --force to overwrite)")
    for sub in ("local", "web"):
        shutil.copytree(TEMPLATES / sub, out / sub, dirs_exist_ok=force)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")


def scaffold(cfg: dict, out: Path, force: bool, dry_run: bool) -> dict:
    validate_config(cfg)
    handlers = domain_handlers(cfg)
    slug = cfg["domain"]
    plan = {
        "out": str(out),
        "domain": slug,
        "tools": [t["name"] for t in cfg["tools"]],
        "domain_handlers_stubbed": handlers,
        "workflows": [w["name"] for w in cfg.get("workflows", [])],
    }
    if dry_run:
        return plan

    copy_template(out, force)
    cfg_text = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    write_text(out / "automation.config.json", cfg_text)
    write_text(out / "web" / "automation.config.json", cfg_text)
    inject_python(out, cfg, handlers)
    inject_typescript(out, cfg, handlers)
    write_text(out / "README.md", render_readme(cfg))
    write_text(out / "docs" / "best-practices.md", render_best_practices_doc(cfg))
    write_text(out / "docs" / "cowork-setup.md", render_cowork_setup_doc(cfg))
    write_text(
        out / ".cowork" / "skills" / f"{slug}-ops" / "SKILL.md",
        render_cowork_skill(cfg),
    )
    # seed an empty inbox so list_workspace has somewhere to look
    write_text(
        out / "local" / "inbox" / "README.txt",
        "Drop source files here. The agent reads ./inbox and writes ./output.\n",
    )
    return plan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a Cowork automation repo.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--config", help="Path to a full automation.config.json design.")
    src.add_argument("--domain", help="Field name for a minimal scaffold, e.g. 'real estate'.")
    ap.add_argument("--display", help="Display name (minimal mode).")
    ap.add_argument("--description", help="One-line description (minimal mode).")
    ap.add_argument("--out", help="Output directory. Default: ./<domain>-automation")
    ap.add_argument("--force", action="store_true", help="Overwrite a non-empty output dir.")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan; write nothing.")
    args = ap.parse_args(argv)

    if args.config:
        cfg = json.loads(Path(args.config).read_text("utf-8"))
    else:
        cfg = build_minimal_config(args.domain, args.display, args.description)

    out = Path(args.out) if args.out else Path(f"{cfg['domain']}-automation")
    out = out.resolve()

    plan = scaffold(cfg, out, args.force, args.dry_run)

    if args.dry_run:
        print("DRY RUN — would generate:")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    print(f"Scaffolded {cfg['displayName']} -> {out}")
    print(f"  tools: {', '.join(plan['tools'])}")
    if plan["domain_handlers_stubbed"]:
        print(f"  stubbed domain handlers (implement the TODOs): {', '.join(plan['domain_handlers_stubbed'])}")
    print(f"  workflows: {', '.join(plan['workflows']) or '(none)'}")
    print("Next: cd local && pip install -e . && automation doctor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
