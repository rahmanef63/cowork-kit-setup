---
name: cowork-automation-generator
description: >-
  Generate a complete, runnable automation repo for ANY field or industry, tuned for Claude Cowork. From one field name it derives field-specific best practices and scaffolds a project under projects/<field>/ usable several ways — a drop-in Cowork skill, a local Python CLI (Anthropic SDK + Claude Agent SDK engines), a local-filesystem Next.js CRUD website, and a bundled MCP server so Cowork can create/read/update/delete the website's data — all sharing one tool contract and datastore. Use whenever someone wants to set up, bootstrap, or generate Cowork/Claude automations for a business, role, or field, or wants an agent-project scaffold with tool-calling, a local web dashboard, or an MCP server for CRUD control. Examples: 'set up Cowork for my law firm', 'generate automations for a real estate agency', 'best practices for Cowork in accounting', 'buatkan otomasi cowork untuk bidang X', 'bikin generator automation per industri', 'scaffold an agent repo with tools and an MCP CRUD server'. Trigger even if they don't say 'Cowork' or name this skill. Do NOT use for one-off scripts, fixing an existing app, generating images or slides, or merely explaining what Cowork is.
argument-hint: [field or domain name, e.g. "real estate"]
allowed-tools: Read, Write, Edit, Bash, WebSearch, Glob
---

# Cowork Automation Generator

The user names a field; **you** interview them, then design, build, set up, run, and
fix the automation. Assume the user is non-technical: they never open a terminal,
read an error, or run a command. You do all of that and report back plainly.

Everything you generate goes into **`projects/<slug>/`** — one folder per field,
Cowork-ready. All surfaces share one local datastore: `.data/<table>.jsonl` +
`output/`.

## Surfaces

- **In-Cowork ops skill** (always) — `.cowork/skills/<slug>-ops/` plus the work you
  do right here in Cowork. Zero setup. The default.
- **Local Python CLI** (default) — headless/scheduled runs; one Anthropic API key.
- **Local website** (`--web`, opt-in) — a Next.js CRUD dashboard over the same
  `.data/`+`output/` via Node `fs`. **No Convex, no account, no API key.**
- **MCP server** (`--mcp`, opt-in) — a Python MCP server exposing full CRUD over
  the datastore, so Cowork/Claude can create/read/update/delete the **website's
  data** directly. This replaced the old BYOK approach.

Pair `--web` + `--mcp` for "a website whose data Claude controls."

Golden rule: don't hand the user commands or make them debug. Run things yourself
via Bash; only ask for what you can't supply (their Anthropic API key for the CLI).

## When you're invoked — interview the user

Short, friendly interview, one or two questions at a time:

1. What do they do? (field/role)
2. What eats the most time each week? (1–3 painful recurring tasks)
3. What tools/apps do they live in? (connectors) — optional
4. Do they want a local website and/or the MCP CRUD server? (default: Cowork + CLI)

If terse ("set up cowork for my clinic"), ask just Q2, then go.

## Step 1 — Ground yourself (read the references)

- `references/cowork-capabilities.md`, `references/best-practice-framework.md`,
  `references/automation-patterns.md`, `references/generated-repo-architecture.md`
  (the exact `automation.config.json` + datastore contract — match it).

For an unfamiliar field, run a focused `WebSearch` (2–3 queries). Keep it light.

## Step 2 — Design the `automation.config.json`

Decompose recurring work → classify by frequency × structure × stakes → map to a
Cowork capability + pattern → tools/workflows → guardrails. Match the contract:

- Keep the eight core tools (`read_document`, `list_workspace`, `write_deliverable`,
  `save_record`, `lookup_record`, `update_record`, `delete_record`, `create_task`) —
  these give full CRUD over the shared datastore.
- Add 3–6 genuinely field-specific domain tools (snake_case, real JSON Schema).
- Add 2–4 workflows; cron-schedule the truly recurring ones.
- Fill `systemPrompt`, `bestPractices` (3–5 actionable), `suggestedConnectors`.

Write to `/tmp/<slug>-design.json`, confirm it parses. For a richer pass, delegate
to the **automation-architect** subagent.

## Step 3 — Scaffold into projects/ (you run this)

```bash
python3 <skill_dir>/scripts/scaffold.py --config /tmp/<slug>-design.json --out projects/<slug>
```

Add `--web` for the local website and `--mcp` for the MCP server. Default surfaces
are Cowork + CLI. `--dry-run` previews, `--force` overwrites. (Without a design,
`--domain "<field>"` makes a minimal core-tools scaffold.)

## Step 4 — Implement the domain tools, then OPERATE it

1. **Fill the stubs.** Replace each `TODO` domain handler in
   `projects/<slug>/local/automation/tools.py` with a real, deterministic impl.
2. **In Cowork:** do the work now — read `./inbox`, write `./output`, keep records
   (full CRUD), follow workflows — and install the `<slug>-ops` skill so it repeats.
3. **Local CLI:** set up via Bash — venv, `pip install -e .`, write `.env` after
   asking for their `ANTHROPIC_API_KEY` once, `automation doctor`, then a real run.
4. **Website (if `--web`):** `cd web && npm install && npm run dev` → http://localhost:3000.
   It's pure local-fs (no account/keys). Confirm it shows the project's records/documents.
5. **MCP (if `--mcp`):** `pip install -r mcp/requirements.txt`, then connect the
   bundled `mcp/.mcp.json` in Cowork/Claude Code. Now Claude can CRUD the website's
   data. `delete_record` is destructive — confirm with the user before deleting.

Never make a non-technical user run these. If you can't execute a step (e.g. no
API key), explain the single missing piece plainly and continue once provided.

## Step 5 — Verify and hand off

- `python3 -m py_compile projects/<slug>/local/automation/*.py` (and `mcp/*.py` if built).
- `automation doctor` / `automation tools` to confirm wiring.
- Tell the user plainly what it does now, the first workflow you'd switch on, offer
  to schedule it, and point at `projects/<slug>/README.md`.

## Design principles

- **Claude operates, the user talks.** Deliver a working thing, set up and run.
- **One datastore, many faces.** CLI, website, and MCP all read/write the same
  `.data/`+`output/`, so they stay in sync. `automation.config.json` is the contract.
- **Deterministic work in tools, judgement in prompts.**
- **Guardrails before power.** Irreversible/external actions (send, pay, post,
  delete) stay human-approved; folder access scoped; secrets never in prompts.
- **Default light, scale on demand.** Cowork + CLI by default; website + MCP opt-in.

## Notes

- Local CLI defaults to the `direct` engine (plain `anthropic`); `--engine agent`
  adds the Claude Agent SDK. Same tool registry either way.
- The website is **local-fs only** (no Convex, no keys). The **MCP server** is how
  Claude controls that website's data from Cowork — they share `.data/`+`output/`.
- A separate **root wizard** (`wizard/server.mjs`) is a GUI that *creates* project
  folders; don't confuse it with a project's `web/` (which *shows* one project's data).
- Re-package this generator as a `.skill` by zipping `cowork-automation-generator/`.
