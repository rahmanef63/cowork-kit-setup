---
name: cowork-automation-generator
description: >-
  Generate a complete, runnable automation repo for ANY field or industry, tuned for Claude Cowork. From one domain name it derives field-specific best practices and scaffolds a single repo runnable three ways — a drop-in Cowork skill, a local Python CLI (Anthropic SDK + Claude Agent SDK engines), and a Next.js + Convex webapp with BYOK — all sharing one tool contract. Use whenever someone wants to set up, bootstrap, or generate Cowork/Claude automations for a business, role, or field, or wants an agent-project scaffold with tool-calling plus a BYOK web UI. Examples: 'set up Cowork for my law firm', 'generate automations for a real estate agency', 'best practices for Cowork in accounting', 'buatkan otomasi cowork untuk bidang X', 'bikin generator automation per industri', 'scaffold an agent repo with tools and a byok webapp'. Trigger even if they don't say 'Cowork' or name this skill. Do NOT use for one-off scripts, fixing an existing app, building a single MCP server, generating images or slides, or merely explaining what Cowork is.
argument-hint: [field or domain name, e.g. "real estate"]
allowed-tools: Read, Write, Edit, Bash, WebSearch, Glob
---

# Cowork Automation Generator

The user names a field; **you** design, build, set up, run, and fix the automation
for them. Assume the user is non-technical: they should never have to open a
terminal, read an error, or run a command. You do all of that with your tools and
report back in plain language.

## Default surfaces (what to build)

- **In-Cowork ops skill** (always) — a drop-in `.cowork/skills/<domain>-ops/`
  skill plus the work done right here in Cowork. Zero setup. This is the default.
- **Local Python CLI** (default) — for headless/scheduled runs. Needs only one
  Anthropic API key.
- **Webapp (Next.js + Convex + BYOK)** — **opt-in only.** It needs a Convex
  account, so build it *only when the user explicitly asks for a shareable web
  app.* Pass `--web` to the scaffolder then.

Golden rule: don't hand the user a wall of commands or make them debug. Run things
yourself via Bash, and only ask them for the one thing you truly can't supply
(their Anthropic API key, or a Convex login if they opted into the webapp).

## When you're invoked

Get the field from the argument or their description. If it's vague ("my
business"), ask **one** plain question: their industry + the single most painful
recurring task. Don't quiz them about surfaces, engines, or stacks — default to
the Cowork skill + local CLI. Mention the webapp only if they ask for something
shareable/multi-user.

## Step 1 — Ground yourself (read the references)

- `references/cowork-capabilities.md` — what Cowork can do, and its limits.
- `references/best-practice-framework.md` — the method to derive best practices for any field. Follow it.
- `references/automation-patterns.md` — reusable patterns you compose into tools + workflows.
- `references/generated-repo-architecture.md` — the exact `automation.config.json` contract. Your design must match it.

For a field you don't know cold, run a focused `WebSearch` (2–3 queries) on how
that field's teams actually spend their day. Keep it light.

## Step 2 — Design the `automation.config.json`

Apply the framework: decompose the recurring work → classify by frequency ×
structure × stakes → map each task to a Cowork capability + an automation pattern
→ choose tools/workflows → add guardrails. Produce a config that matches
`generated-repo-architecture.md`:

- Keep the six core tools (`read_document`, `list_workspace`, `write_deliverable`,
  `save_record`, `lookup_record`, `create_task`).
- Add 3–6 genuinely field-specific domain tools (snake_case `name`/`handler`,
  real JSON Schema). New handlers get stubs you'll implement.
- Add 2–4 workflows; cron-schedule the truly recurring ones.
- Fill `systemPrompt`, `bestPractices` (3–5 actionable), `suggestedConnectors`.

Write it to `/tmp/<domain>-design.json` and confirm it parses. For a richer pass,
delegate to the **automation-architect** subagent (`agents/automation-architect.md`).

## Step 3 — Scaffold (you run this, not the user)

Default surfaces (Cowork skill + CLI), output into the user's working folder:

```bash
python3 <skill_dir>/scripts/scaffold.py --config /tmp/<domain>-design.json --out <user_folder>
```

`<skill_dir>` = `${CLAUDE_SKILL_DIR}` when available. Quick path without a design:
`scaffold.py --domain "real estate" --out ./real-estate-automation`. Add `--web`
**only if** the user wants a shareable web app. `--dry-run` previews, `--force` overwrites.

The scaffolder writes `automation.config.json`, the `.cowork/skills/<domain>-ops/`
skill, `docs/`, and the `README.md`; for `cli` it writes `local/` and injects
Python stubs; for `web` it writes `web/` and injects TS stubs. It keeps tool
names identical across surfaces.

## Step 4 — Implement the domain tools, then OPERATE it for the user

This is what makes it "they don't need to know anything." Do it yourself.

1. **Fill the stubs.** Replace each `TODO` domain handler with a real, deterministic
   implementation in `local/automation/tools.py` (and `web/lib/tools.ts` if web).
   Keep behavior identical across languages.
2. **In Cowork (the zero-setup path):** just do the requested work now — read their
   `./inbox`, produce deliverables to `./output`, follow the workflows — using your
   own tools. Install the `<domain>-ops` skill so it's repeatable.
3. **Local CLI:** set it up via Bash for them — create a venv, `pip install -e .`,
   write `.env` after asking for their `ANTHROPIC_API_KEY` once, run
   `automation doctor`, then a real `automation run "<their task>"` or
   `automation workflow <name>`. Summarize what it produced; don't paste raw logs.
4. **Webapp (only if opted in):** `npm install`; then **`npx convex dev --once`**
   to push schema + functions (this is what makes `keyStatus` and other queries
   work — a generic "Server Error" almost always means the schema/index wasn't
   pushed); then `npm run dev`. Read the convex output yourself and fix issues.
   The one thing you can't do for them is create/log into a Convex account — guide
   that in one plain sentence, do everything else.

Never make a non-technical user run these. If you're in an environment where you
can't execute a step (no key, no Convex login), explain the single missing piece
in plain words and offer to continue once they provide it.

## Step 5 — Verify and hand off

- `python3 -m py_compile <out>/local/automation/*.py` (if CLI built).
- `automation doctor` / `automation tools` to confirm wiring.
- One real run if a key is available.
- Tell the user plainly: what the automation does now, which first workflow you'd
  switch on, and offer to schedule it. Point them at `README.md`.

## Design principles (why this shape)

- **Claude operates, the user talks.** The deliverable isn't just files — it's a
  working thing you set up and run. Optimize for a user who knows nothing technical.
- **One contract, many surfaces.** `automation.config.json` is the single source of
  truth so every surface stays consistent.
- **Deterministic work in tools, judgement in prompts.** Tools are predictable
  functions; the model supplies reasoning.
- **Guardrails before power.** Irreversible/external actions stay human-approved.
  Folder access scoped. Secrets never in prompts. Webapp is BYOK.
- **Default light, scale on demand.** Cowork skill + CLI by default; webapp only
  when a shareable app is genuinely wanted.

## Notes

- Local CLI defaults to the `direct` engine (plain `anthropic`); `--engine agent`
  adds the Claude Agent SDK. Same tool registry either way.
- The webapp is BYOK — never ship a server-side key. Keys live per session in Convex.
- To re-package this generator as an installable `.skill`, zip the
  `cowork-automation-generator/` directory with a `.skill` extension.
