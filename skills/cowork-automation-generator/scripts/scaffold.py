#!/usr/bin/env python3
"""
scaffold.py — materialize a Cowork automation repo from a domain config.
============================================================================
Claude designs the domain (tools, workflows, best practices); this turns that
design into a project under projects/<slug>/.

Surfaces (opt-in via --surfaces, default "cli,cowork"):
  cowork  -> .cowork/skills/<slug>-ops/  zero-setup, runs inside Cowork  [always on]
  cli     -> local/   Python CLI (direct + Agent SDK engines)
  web     -> web/     local-fs Next.js CRUD website (no Convex, no keys)
  mcp     -> mcp/     Python MCP server: full CRUD over the local datastore,
                      so Cowork can control the website's data

Usage:
  python scaffold.py --domain "real estate"                       # cli + cowork
  python scaffold.py --config design.json --web --mcp --out projects/x
  python scaffold.py --domain legal --surfaces cowork             # cowork only
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES = SCRIPT_DIR.parent / "assets" / "templates"

CORE_HANDLERS = {
    "read_document", "list_workspace", "write_deliverable",
    "save_record", "lookup_record", "update_record", "delete_record", "create_task",
}
VALID_SURFACES = {"cowork", "cli", "web", "mcp"}

IDENT_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PY_MARKER = "# >>> SCAFFOLD:DOMAIN_TOOLS <<<"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower())
    return s.strip("-") or "automation"


def titlecase(text: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[-_\s]+", str(text)) if w)


def die(msg: str):
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


# --------------------------------------------------------------------------- #
# Config construction + validation
# --------------------------------------------------------------------------- #
def load_template_config() -> dict:
    return json.loads((TEMPLATES / "automation.config.json").read_text("utf-8"))


def build_minimal_config(domain: str, display: str | None, description: str | None) -> dict:
    cfg = load_template_config()
    name = display or titlecase(domain)
    cfg["domain"] = slugify(domain)
    cfg["displayName"] = name
    cfg["description"] = description or f"Automation kit for {name.lower()} operations."
    cfg["systemPrompt"] = (
        f"You are a meticulous operations agent for a {name.lower()} team. "
        "You complete multi-step tasks end to end with the available tools: read "
        "source files, produce deliverables, keep simple records (full CRUD), and "
        "create follow-up tasks. Prefer doing the work over describing it. State any "
        "assumptions. Write outputs to ./output and confirm what you produced."
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
        if not IDENT_RE.match(spec["name"]):
            die(f"tool name {spec['name']!r} must be snake_case")
        if not IDENT_RE.match(spec["handler"]):
            die(f"tool handler {spec['handler']!r} must be snake_case")
        if spec["name"] in seen:
            die(f"duplicate tool name {spec['name']!r}")
        seen.add(spec["name"])
        if not isinstance(spec["input_schema"], dict) or spec["input_schema"].get("type") != "object":
            die(f"tools[{i}].input_schema must be a JSON Schema object (type: object)")


def domain_handlers(cfg: dict) -> list[str]:
    out: list[str] = []
    for spec in cfg["tools"]:
        h = spec["handler"]
        if h not in CORE_HANDLERS and h not in out:
            out.append(h)
    return out


# --------------------------------------------------------------------------- #
# Domain-tool stub injection (Python CLI registry only)
# --------------------------------------------------------------------------- #
def py_stub(handler: str, tool_name: str) -> str:
    return (
        f'@register("{handler}")\n'
        f"def {handler}(args: dict) -> dict:\n"
        f'    """TODO: implement domain tool \'{tool_name}\'. Auto-generated stub."""\n'
        f'    return {{"content": "TODO: implement \'{handler}\'. Received args: "\n'
        f"                       + compact_args(args, 400)}}\n"
    )


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


def rename_mcp(out: Path, slug: str) -> None:
    """Make the MCP server name unique per project so connectors don't collide."""
    py = out / "mcp" / "server.py"
    if py.is_file():
        py.write_text(py.read_text("utf-8").replace('FastMCP("automation_mcp")', f'FastMCP("{slug.replace("-", "_")}_mcp")'), "utf-8")
    cfg = out / "mcp" / ".mcp.json"
    if cfg.is_file():
        cfg.write_text(cfg.read_text("utf-8").replace('"automation-data"', f'"{slug}-data"'), "utf-8")


# --------------------------------------------------------------------------- #
# Doc rendering
# --------------------------------------------------------------------------- #
def tools_table(cfg: dict) -> str:
    rows = ["| Tool | Purpose |", "| --- | --- |"]
    for s in cfg["tools"]:
        rows.append(f"| `{s['name']}` | {s['description'].split('. ')[0].strip().rstrip('.')} |")
    return "\n".join(rows)


def workflows_list(cfg: dict) -> str:
    wfs = cfg.get("workflows", [])
    if not wfs:
        return "_No workflows defined yet._"
    return "\n".join(
        f"- **{w['name']}**{(' — scheduled `' + w['schedule'] + '`') if w.get('schedule') else ' — on-demand'}: {w['description']}"
        for w in wfs
    )


def best_practices_block(cfg: dict) -> str:
    bps = cfg.get("bestPractices", [])
    return "\n".join(f"- **{b['title']}** — {b['detail']}" for b in bps) or "_No domain best practices captured yet._"


def render_readme(cfg: dict, surfaces: set[str]) -> str:
    name, slug = cfg["displayName"], cfg["domain"]
    connectors = ", ".join(cfg.get("suggestedConnectors", [])) or "none suggested"
    p = [
        f"# {name} — Automation Kit\n",
        f"{cfg['description']}\n",
        "Generated by the **cowork-automation-generator**. Easiest way to use it: let "
        "Claude (in Cowork) run it for you — no terminal needed.\n",
        "## What it automates\n",
        tools_table(cfg),
        "\n### Workflows",
        workflows_list(cfg),
        "\n## Best practices for this field",
        best_practices_block(cfg),
        f"\nSuggested Cowork connectors: {connectors}.\n",
        "## Easiest: use it inside Cowork (no setup)\n",
        f"This repo ships a drop-in Cowork skill at `.cowork/skills/{slug}-ops/`. Keep this "
        "folder somewhere Cowork can access and ask Claude to do the work — it reads "
        "`./inbox`, writes `./output`, keeps records in `./.data`. See `docs/cowork-setup.md`. Ready-to-use prompts: `docs/prompts.md`.\n",
    ]
    if "cli" in surfaces:
        p.append(
            "## Local CLI (Python)\n\n```bash\ncd local\npython -m venv .venv && source .venv/bin/activate"
            "   # Windows: .venv\\Scripts\\activate\npip install -e .\ncp .env.example .env"
            "        # add ANTHROPIC_API_KEY\nautomation doctor\nautomation run \"Summarize ./inbox\"\n```\n\n"
            "Full CRUD on records: `save_record`, `lookup_record`, `update_record`, `delete_record`."
        )
    if "web" in surfaces:
        p.append(
            "## Website (local CRUD, no account)\n\n```bash\ncd web\nnpm install\nnpm run dev"
            "        # http://localhost:3000\n```\n\n"
            "A local dashboard over the SAME data (`../.data` + `../output`) — no Convex, no keys. "
            "Create/edit/delete records and view documents in the browser."
        )
    if "mcp" in surfaces:
        p.append(
            "## MCP server (let Cowork control the website's data)\n\n```bash\npip install -r mcp/requirements.txt\n```\n\n"
            f"Connect the bundled `mcp/.mcp.json` (`{slug}-data`) in Cowork/Claude Code. Claude then has "
            "full CRUD (`list_records`, `create_record`, `update_record`, `delete_record`, documents…) over "
            "the exact data the website shows."
        )
    if "web" in surfaces and "mcp" in surfaces:
        p.append("The website and the MCP share one datastore — edit in the browser or have Claude do it via the MCP; both stay in sync.")
    if "web" not in surfaces:
        p.append(f"## Want a website?\n\nAdd it: `scaffold.py --domain \"{slug}\" --web --mcp --out . --force`")
    p.append(
        "\n## How it fits together\n\n`automation.config.json` is the single source of truth (tool names, "
        "schemas, system prompt, workflows). The CLI registry and the MCP server share the `.data/` + "
        "`output/` datastore, and the website reads/writes the same files."
        + (" Domain tools were stubbed for you to implement (look for `TODO` in `local/automation/tools.py`)." if "cli" in surfaces else "")
    )
    return "\n".join(p) + "\n"


def render_best_practices_doc(cfg: dict) -> str:
    return (
        f"# Best Practices — {cfg['displayName']}\n\n"
        "Tuned for this field: decompose recurring work, match each task to the right Cowork "
        "capability, choose a surface, add guardrails.\n\n"
        f"## Field-specific guidance\n{best_practices_block(cfg)}\n\n"
        "## Universal checklist\n"
        "- Scope folder access to one working folder.\n"
        "- Keep deterministic steps in tools; judgement in the prompt.\n"
        "- Gate irreversible/external actions (send, pay, post, delete) behind human approval.\n"
        "- Never paste secrets into prompts. CLI key in `.env`; the website + MCP are local (no keys).\n"
        "- Verify high-stakes outputs.\n"
        f"- Schedule the recurring parts ({workflows_list(cfg)}).\n"
        "- Start with one high-frequency, low-stakes workflow; expand once trusted.\n"
    )


def render_cowork_setup_doc(cfg: dict) -> str:
    connectors = cfg.get("suggestedConnectors", [])
    conn = "\n".join(f"  - {c}" for c in connectors) or "  - (none suggested)"
    sched = [w for w in cfg.get("workflows", []) if w.get("schedule")]
    sl = "\n".join(f"  - `{w['schedule']}` -> {w['name']}: {w['description']}" for w in sched) or "  - (none; all on-demand)"
    return (
        f"# Using {cfg['displayName']} inside Cowork\n\n"
        "Fastest way to run these automations — no install, no terminal.\n\n"
        "## 1. Give Cowork the folder\nPut this folder where Cowork can access it. The agent reads "
        "`./inbox` and writes `./output`; records live in `./.data`.\n\n"
        f"## 2. Install the drop-in skill\nCopy `.cowork/skills/{cfg['domain']}-ops/` into your Cowork/Claude "
        "skills directory.\n\n"
        f"## 3. Connect suggested connectors (MCP)\n{conn}\n\n"
        "## 4. (Optional) Connect the data MCP\nIf you generated the `mcp/` surface, connect `mcp/.mcp.json` so "
        "Claude can CRUD the website's data directly.\n\n"
        f"## 5. Schedule recurring work\n{sl}\n\n"
        "## 6. Guardrails\nKeep external/irreversible actions human-approved; review the plan before acting.\n"
    )


def render_prompts_doc(cfg: dict) -> str:
    name = cfg["displayName"]
    wfs = cfg.get("workflows", [])
    wf_lines = "\n".join(f"### {w['name']}\n> {w['prompt']}\n" for w in wfs) or "_No workflows defined yet._\n"
    domain = [s for s in cfg["tools"] if s["handler"] not in CORE_HANDLERS]
    dom_lines = "\n".join(
        f"- **{s['name']}** — {s['description'].split('. ')[0].rstrip('.')}\n  > Use {s['name']} for [...]."
        for s in domain
    ) or "_(none yet — ask Claude to add field-specific tools, then they'll appear here on re-generate)_"
    first = wfs[0]["name"] if wfs else "process-inbox"
    return f"""# Prompts — {name}

Copy-paste these into **Cowork** (or run via the CLI). Replace the [bracketed] bits.
Claude does the work; you approve anything sent, published, or deleted.

Start simple: *"Read ./inbox and tell me what needs doing."*

## Run a workflow

{wf_lines}
## Everyday asks (core tools — full CRUD)

- > Read everything in `./inbox` and summarize it with action items.
- > Draft a [document / letter / report] about [topic] and save it to `./output`.
- > Save a new record in **[table]**: [field1]=[..], [field2]=[..].
- > Find "[query]" in **[table]** and show me the matches (with ids).
- > Update record [id] in **[table]**: set [field] to [value].
- > Delete record [id] from **[table]**.   _(Claude confirms first)_
- > Create a task: [what] due [when].

## Field-specific asks

{dom_lines}

## Run it headless (CLI)

```bash
automation run "Process the newest item in ./inbox"
automation workflow {first}
```

## With the MCP server connected (in Cowork)

Once `mcp/.mcp.json` is connected, just ask Claude:
- > Add a [thing] to **[table]** with [details].
- > Change [record] status to [value].
- > List everything in **[table]**.

The local website (`web/`) shows the same data live.

## Scheduling (recurring)

- > Every Monday 8am, run **{first}** and send me the summary.
- > Each morning, digest new `./inbox` items and create tasks for follow-ups.

## Tips

- Be specific: names, dates, amounts, file names.
- One outcome per prompt; let Claude plan the steps.
- Say "draft, don't send" for anything external.
- This folder is the workspace: `./inbox` (inputs), `./output` (deliverables), `./.data` (records).
"""


def render_cowork_skill(cfg: dict) -> str:
    name = cfg["displayName"]
    wf = "\n".join(f"- **/{w['name']}** — {w['description']}\n  Prompt: {w['prompt']}" for w in cfg.get("workflows", [])) or "- (define workflows in automation.config.json)"
    tl = "\n".join(f"- `{s['name']}`: {s['description']}" for s in cfg["tools"])
    desc = (f"{name} operations automation. Use whenever the user works on {name.lower()} tasks — intake, "
            f"drafting, records, follow-ups, reporting — or names this domain. Reads ./inbox, writes ./output, "
            f"keeps records in ./.data.")
    return (
        f"---\nname: {cfg['domain']}-ops\ndescription: {desc}\n---\n\n"
        f"# {name} Operations\n\n"
        f"You automate {name.lower()} knowledge work. Prefer doing the work with tools over describing it. "
        "Write deliverables to `./output`; keep structured data with the record tools (full CRUD); create "
        "tasks for human follow-ups. State assumptions when a request is ambiguous.\n\n"
        f"## System role\n{cfg['systemPrompt']}\n\n## Available tools\n{tl}\n\n## Workflows\n{wf}\n\n"
        "## Guardrails\n- Gate any irreversible/external action (send, pay, post, delete) behind explicit approval.\n"
        "- Keep folder access scoped; never echo secrets.\n- Verify high-stakes outputs before finishing.\n"
    )


# --------------------------------------------------------------------------- #
# Main scaffold routine
# --------------------------------------------------------------------------- #
def copy_template(out: Path, force: bool, surfaces: set[str]) -> None:
    if out.exists() and any(out.iterdir()) and not force:
        die(f"output dir {out} is not empty (use --force to overwrite)")
    mapping = {"cli": "local", "web": "web", "mcp": "mcp"}
    for surf, sub in mapping.items():
        if surf in surfaces:
            shutil.copytree(TEMPLATES / sub, out / sub, dirs_exist_ok=force)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")


def scaffold(cfg: dict, out: Path, force: bool, dry_run: bool, surfaces: set[str]) -> dict:
    validate_config(cfg)
    handlers = domain_handlers(cfg)
    slug = cfg["domain"]
    plan = {
        "out": str(out), "domain": slug, "surfaces": sorted(surfaces),
        "tools": [t["name"] for t in cfg["tools"]],
        "domain_handlers_stubbed": handlers,
        "workflows": [w["name"] for w in cfg.get("workflows", [])],
    }
    if dry_run:
        return plan

    copy_template(out, force, surfaces)
    write_text(out / "automation.config.json", json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    write_text(out / "README.md", render_readme(cfg, surfaces))
    write_text(out / "docs" / "best-practices.md", render_best_practices_doc(cfg))
    write_text(out / "docs" / "cowork-setup.md", render_cowork_setup_doc(cfg))
    write_text(out / "docs" / "prompts.md", render_prompts_doc(cfg))
    write_text(out / ".cowork" / "skills" / f"{slug}-ops" / "SKILL.md", render_cowork_skill(cfg))

    if "cli" in surfaces:
        inject_python(out, cfg, handlers)
        write_text(out / "local" / "inbox" / "README.txt",
                   "Drop source files here. The agent reads ./inbox and writes ./output.\n")
    if "mcp" in surfaces:
        rename_mcp(out, slug)
    return plan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a Cowork automation repo.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--config", help="Path to a full automation.config.json design.")
    src.add_argument("--domain", help="Field name for a minimal scaffold, e.g. 'real estate'.")
    ap.add_argument("--display", help="Display name (minimal mode).")
    ap.add_argument("--description", help="One-line description (minimal mode).")
    ap.add_argument("--out", help="Output directory. Default: projects/<slug>")
    ap.add_argument("--surfaces", default="cli,cowork",
                    help="Comma list of: cowork, cli, web, mcp. Default 'cli,cowork'.")
    ap.add_argument("--web", action="store_true", help="Add the local website surface.")
    ap.add_argument("--mcp", action="store_true", help="Add the MCP server surface (CRUD over the data).")
    ap.add_argument("--force", action="store_true", help="Overwrite a non-empty output dir.")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan; write nothing.")
    args = ap.parse_args(argv)

    cfg = json.loads(Path(args.config).read_text("utf-8")) if args.config \
        else build_minimal_config(args.domain, args.display, args.description)

    surfaces = {s.strip() for s in args.surfaces.split(",") if s.strip()}
    if args.web:
        surfaces.add("web")
    if args.mcp:
        surfaces.add("mcp")
    surfaces.add("cowork")
    bad = surfaces - VALID_SURFACES
    if bad:
        die(f"unknown surfaces {sorted(bad)} (valid: {sorted(VALID_SURFACES)})")

    out = (Path(args.out) if args.out else Path("projects") / cfg["domain"]).resolve()
    plan = scaffold(cfg, out, args.force, args.dry_run, surfaces)

    if args.dry_run:
        print("DRY RUN — would generate:")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    print(f"Scaffolded {cfg['displayName']} -> {out}")
    print(f"  surfaces: {', '.join(plan['surfaces'])}")
    print(f"  tools: {', '.join(plan['tools'])}")
    if plan["domain_handlers_stubbed"]:
        print(f"  stubbed domain handlers (implement the TODOs): {', '.join(plan['domain_handlers_stubbed'])}")
    print(f"  workflows: {', '.join(plan['workflows']) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
