# Cowork Automation Generator

Name a field → **Claude** interviews you, then designs, builds, sets up, runs, and
fixes an automation kit for it. The user just talks; Claude does the technical
parts. Every kit lands in **`projects/<field>/`**, ready for Cowork.

New here? Read **[CARA-PAKAI.md](CARA-PAKAI.md)** (plain-language guide).

## In plain words

Cowork is Claude working directly on your computer. **cowork-setup turns that
generic Claude into a worker for your specific job.** Tell it what you do; it asks
a couple of questions, then builds a ready-made automation kit in
`projects/<field>/` and runs it. No coding. Optionally it adds a **local website**
(a CRUD dashboard for your data) and an **MCP server** so Claude can create/read/
update/delete that website's data straight from Cowork. Claude drafts; you approve
anything that gets sent or published.

## Two ways to use it

1. **Talk to Claude in Cowork** (main). Install the skill, say what you do. Claude
   interviews you and builds `projects/<field>/` — and operates it for you.
2. **Wizard GUI** (no Cowork). `node wizard/server.mjs`, fill the form → it creates
   `projects/<field>/`. Then open that folder in Cowork for the field-specific tools.

## What lands in `projects/<field>/`

- **In-Cowork ops skill** (`.cowork/skills/<field>-ops/`) — zero setup.
- **Local Python CLI** (default) — headless/scheduled runs; one Anthropic API key.
- **Local website** (`--web`, opt-in) — a Next.js CRUD dashboard over your data.
  Pure local files (`.data/` + `output/`). **No Convex, no account, no key.**
- **MCP server** (`--mcp`, opt-in) — Python; full CRUD over the same data, so Cowork
  can manage the website's content. Connect its bundled `.mcp.json`.

One datastore powers all of them (`.data/<table>.jsonl` + `output/`), and
`automation.config.json` is the single tool contract.

## Repo layout

```
cowork-setup/
├── .claude-plugin/plugin.json          # installs the generator as a plugin
├── skills/cowork-automation-generator/ # the generator (skill + references + scaffolder + templates: local/ web/ mcp/)
├── agents/automation-architect.md      # subagent that researches + designs a domain config
├── wizard/                             # zero-dep local GUI: form -> creates projects/<field>/
├── projects/                           # your generated kits land here (one per field)
├── scripts/                            # verify.py, check.py (local checks; no cloud CI)
├── hooks/                              # git pre-commit hook
└── cowork-automation-generator.skill   # packaged, installable bundle
```

## Wizard (GUI generator)

```bash
node wizard/server.mjs      # open http://localhost:4321
```

No `npm install`. Needs Node 18+ and Python 3. Fill the form → writes `projects/<field>/`.

## Advanced: run the scaffolder yourself

```bash
# default surfaces (in-Cowork skill + local CLI)
python3 skills/cowork-automation-generator/scripts/scaffold.py --domain "real estate"

# add the local website and the MCP CRUD server
python3 skills/cowork-automation-generator/scripts/scaffold.py --domain "real estate" --web --mcp
```

`--dry-run` previews; `--force` overwrites; `--surfaces cowork,cli,web,mcp` selects surfaces.

## Run a generated kit

```bash
# local CLI
cd projects/<field>/local && python -m venv .venv && source .venv/bin/activate
pip install -e . && cp .env.example .env   # add ANTHROPIC_API_KEY
automation doctor && automation run "Process the newest item in ./inbox"

# local website (if generated with --web) — no account, no keys
cd projects/<field>/web && npm install && npm run dev   # http://localhost:3000

# MCP server (if generated with --mcp) — let Cowork CRUD the website's data
pip install -r projects/<field>/mcp/requirements.txt
# then connect projects/<field>/mcp/.mcp.json in Cowork/Claude Code
```

## Develop

```bash
python3 scripts/verify.py     # JSON, py_compile, config<->CLI registry, web/mcp shape, scaffold dry-run
python3 scripts/check.py      # runs verify + wizard syntax (used by the pre-commit hook)
```

A local **git pre-commit hook** runs `check.py` automatically — enable once with
`git config core.hooksPath hooks` (no cloud CI). See `CONTRIBUTING.md`.

## Design principles

- **Claude operates, the user talks.** A working thing, set up and run — not files to wire up.
- **One datastore, many faces.** CLI, website, and MCP share `.data/`+`output/`; they stay in sync.
- **Deterministic work in tools, judgement in prompts.**
- **Guardrails before power.** Irreversible/external actions (send, pay, post, delete) stay human-approved; folder access scoped; secrets never in prompts.
- **Default light, scale on demand.** Cowork + CLI by default; website + MCP opt-in.

## FAQ

**Do I need to know how to code?**
No. Install the skill and tell Claude your field. Claude interviews you, builds the kit in `projects/`, runs it, and fixes errors itself. Guide: [CARA-PAKAI.md](CARA-PAKAI.md).

**What's the difference between the wizard and the skill?**
Same outcome (a `projects/<field>/` folder), two interfaces — the **skill** is Claude in Cowork (it also implements + runs everything); the **wizard** is a click-through form.

**Where do generated projects go?**
`projects/<field>/`. Gitignored by default (they're yours, not part of the template).

**What is the MCP server for?**
It lets Claude (in Cowork) do full CRUD — create/read/update/delete — on your project's data, which is the same data the local website shows. It's how "Claude controls the website" works. Connect `projects/<field>/mcp/.mcp.json` after `pip install -r mcp/requirements.txt`.

**Is there a database or account to set up?**
No. The website and MCP use plain local files (`.data/` + `output/`). No Convex, no signup, no API key for those. Only the CLI needs an Anthropic key.

**Do I need an Anthropic API key?**
In-Cowork: no. Local CLI: one `ANTHROPIC_API_KEY` (stored in `.env`). Website + MCP: no key (they're local data tools).

**`npm i` fails at the repo root.**
The root isn't a Node project. The wizard runs with `node wizard/server.mjs` (no install). npm only applies inside a generated `projects/<field>/web` if you added `--web`.

**Some generated tools say `TODO`.**
Domain-specific tools are scaffolded as stubs so the project validates immediately. Claude implements them in `projects/<field>/local/automation/tools.py`.

**Is my data safe?**
Everything is local files on your machine. The CLI key lives in `.env` (gitignored). `delete_record` is irreversible — Claude confirms before deleting.

**macOS or Windows?**
Both — Cowork runs on macOS and Windows.

**How do I update the generator?**
Re-install the latest `cowork-automation-generator.skill` (Settings → Skills) and pull the repo.
