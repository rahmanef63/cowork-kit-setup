---
name: cowork-automation-generator
description: >-
  Generate a complete, runnable automation repo for ANY field or industry, tuned for Claude Cowork. From one domain name it derives field-specific best practices and scaffolds a single repo runnable three ways — a drop-in Cowork skill, a local Python CLI (Anthropic SDK + Claude Agent SDK engines), and a Next.js + Convex webapp with BYOK — all sharing one tool contract. Use whenever someone wants to set up, bootstrap, or generate Cowork/Claude automations for a business, role, or field, or wants an agent-project scaffold with tool-calling plus a BYOK web UI. Examples: 'set up Cowork for my law firm', 'generate automations for a real estate agency', 'best practices for Cowork in accounting', 'buatkan otomasi cowork untuk bidang X', 'bikin generator automation per industri', 'scaffold an agent repo with tools and a byok webapp'. Trigger even if they don't say 'Cowork' or name this skill. Do NOT use for one-off scripts, fixing an existing app, building a single MCP server, generating images or slides, or merely explaining what Cowork is.
argument-hint: [field or domain name, e.g. "real estate"]
allowed-tools: Read, Write, Edit, Bash, WebSearch, Glob
---

# Cowork Automation Generator

The user names a field; **you** interview them, then design, build, set up, run, and
fix the automation. Assume the user is non-technical: they never open a terminal,
read an error, or run a command. You do all of that and report back plainly.

Everything you generate goes into **`projects/<slug>/`** inside their repo — one
folder per field, ready to use in Cowork.

## Surfaces

- **In-Cowork ops skill** (always) — `projects/<slug>/.cowork/skills/<slug>-ops/`
  plus the work you do right here in Cowork. Zero setup. The default.
- **Local Python CLI** (default) — headless/scheduled runs; one Anthropic API key.
- **Per-project webapp (Next.js + Convex + BYOK)** — **opt-in.** A shareable web
  app that runs the automation in the browser. Needs a Convex account; build it
  only when the user explicitly wants something shareable. Pass `--web`.

There is also a **root wizard** (`wizard/server.mjs`) — a no-install web form the
user can run themselves (`node wizard/server.mjs`) to create a `projects/<slug>/`
without Cowork. It only scaffolds the core tools; when they open the folder in
Cowork, you take over and flesh it out. You don't run the wizard — it's the user's
GUI alternative to talking to you.

Golden rule: don't hand the user commands or make them debug. Run things yourself
via Bash; only ask for what you can't supply (their Anthropic API key; a Convex
login if they opted into the webapp).

## When you're invoked — interview the user

Run a short, friendly interview. Ask one or two questions at a time, not a wall.
You're after enough to design well:

1. What do they do? (field/role)
2. What eats the most time each week? (the 1–3 most painful recurring tasks)
3. What tools/apps do they live in? (informs connectors) — optional
4. Do they want a local CLI too, and/or a shareable web app? (default: Cowork + CLI)

If they were terse ("set up cowork for my clinic"), ask just question 2, then go.
Don't quiz them on engines or stacks.

## Step 1 — Ground yourself (read the references)

- `references/cowork-capabilities.md` — what Cowork can do, and its limits.
- `references/best-practice-framework.md` — the method to derive best practices. Follow it.
- `references/automation-patterns.md` — patterns you compose into tools + workflows.
- `references/generated-repo-architecture.md` — the exact `automation.config.json` contract.

For an unfamiliar field, run a focused `WebSearch` (2–3 queries) on how that
field's teams spend their day. Keep it light.

## Step 2 — Design the `automation.config.json`

Decompose the recurring work → classify by frequency × structure × stakes → map
each task to a Cowork capability + a pattern → choose tools/workflows → add
guardrails. Match `generated-repo-architecture.md`:

- Keep the six core tools (`read_document`, `list_workspace`, `write_deliverable`,
  `save_record`, `lookup_record`, `create_task`).
- Add 3–6 genuinely field-specific domain tools (snake_case, real JSON Schema).
- Add 2–4 workflows; cron-schedule the truly recurring ones.
- Fill `systemPrompt`, `bestPractices` (3–5 actionable), `suggestedConnectors`.

Write it to `/tmp/<slug>-design.json` and confirm it parses. For a richer pass,
delegate to the **automation-architect** subagent.

## Step 3 — Scaffold into projects/ (you run this)

```bash
python3 <skill_dir>/scripts/scaffold.py --config /tmp/<slug>-design.json --out projects/<slug>
```

`<skill_dir>` = `${CLAUDE_SKILL_DIR}` when available. Add `--web` only if they want
a shareable web app. Default surfaces are Cowork + CLI. `--dry-run` previews,
`--force` overwrites. (Without a hand-built design, `--domain "<field>"` makes a
minimal core-tools scaffold.)

## Step 4 — Implement the domain tools, then OPERATE it

1. **Fill the stubs.** Replace each `TODO` domain handler with a real, deterministic
   implementation in `projects/<slug>/local/automation/tools.py` (and
   `web/lib/tools.ts` if web). Keep behavior identical across languages.
2. **In Cowork:** do the requested work now — read their `./inbox`, write to
   `./output`, follow the workflows — and install the `<slug>-ops` skill so it repeats.
3. **Local CLI:** set it up via Bash — venv, `pip install -e .`, write `.env` after
   asking for their `ANTHROPIC_API_KEY` once, `automation doctor`, then a real run.
   Summarize results; don't paste raw logs.
4. **Webapp (only if opted in):** `npm install`; then `npx convex dev --once` to push
   schema + functions (a generic "Server Error" means the schema/index wasn't
   pushed); then `npm run dev`. Fix issues yourself. The one thing you can't do is
   create/log into a Convex account — guide that in one plain sentence.

Never make a non-technical user run these. If you can't execute a step (no key, no
Convex login), explain the single missing piece plainly and continue once provided.

## Step 5 — Verify and hand off

- `python3 -m py_compile projects/<slug>/local/automation/*.py` (if CLI built).
- `automation doctor` / `automation tools` to confirm wiring.
- One real run if a key is available.
- Tell the user plainly what it does now, the first workflow you'd switch on, offer
  to schedule it, and point at `projects/<slug>/README.md`.

## Design principles

- **Claude operates, the user talks.** Deliver a working thing, set up and run.
- **Output lives in `projects/`.** One folder per field, Cowork-ready.
- **One contract, many surfaces.** `automation.config.json` keeps them consistent.
- **Deterministic work in tools, judgement in prompts.**
- **Guardrails before power.** Irreversible/external actions human-approved; folder
  access scoped; secrets never in prompts; webapp is BYOK.
- **Default light, scale on demand.** Cowork + CLI by default; webapp opt-in.

## Notes

- Local CLI defaults to the `direct` engine (plain `anthropic`); `--engine agent`
  adds the Claude Agent SDK. Same tool registry either way.
- Two web things, don't confuse them: the **root wizard** (`wizard/`) is a GUI that
  *creates* project folders; the **per-project webapp** (`projects/<slug>/web/`) is a
  BYOK app that *runs* a project's automation.
- Re-package this generator as a `.skill` by zipping the `cowork-automation-generator/`
  directory with a `.skill` extension.
