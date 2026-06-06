---
name: cowork-automation-generator
description: >-
  Generate a complete, runnable automation repo for ANY field or industry, tuned for Claude Cowork. From one domain name it derives field-specific best practices and scaffolds a single repo runnable three ways — a drop-in Cowork skill, a local Python CLI (Anthropic SDK + Claude Agent SDK engines), and a Next.js + Convex webapp with BYOK — all sharing one tool contract. Use whenever someone wants to set up, bootstrap, or generate Cowork/Claude automations for a business, role, or field, or wants an agent-project scaffold with tool-calling plus a BYOK web UI. Examples: 'set up Cowork for my law firm', 'generate automations for a real estate agency', 'best practices for Cowork in accounting', 'buatkan otomasi cowork untuk bidang X', 'bikin generator automation per industri', 'scaffold an agent repo with tools and a byok webapp'. Trigger even if they don't say 'Cowork' or name this skill. Do NOT use for one-off scripts, fixing an existing app, building a single MCP server, generating images or slides, or merely explaining what Cowork is.
argument-hint: [field or domain name, e.g. "real estate"]
allowed-tools: Read, Write, Edit, Bash, WebSearch, Glob
---

# Cowork Automation Generator

Turn a single field name into a working automation repo that gets the most out of
Claude Cowork. The output repo runs three ways from one shared contract:

- **Inside Cowork** — a drop-in skill (`.cowork/skills/<domain>-ops/`).
- **Local Python CLI** — tool-calling agent with two engines (Anthropic SDK direct + Claude Agent SDK).
- **Webapp** — Next.js + Convex where each user brings their own Anthropic key (BYOK).

Your job when this skill runs: **design** the automation for the user's field,
then **scaffold** it with `scripts/scaffold.py`. Design is judgement (you, using
the reference docs); scaffolding is deterministic (the script).

## When you're invoked

The user gives a field (the argument) or describes their work. If the field is
vague ("my business"), ask one quick question to pin down the industry and their
single most painful recurring task — that one answer shapes the whole design.

## Step 1 — Ground yourself (read the references)

Read these before designing. They are the source of truth:

- `references/cowork-capabilities.md` — what Cowork can actually do, and its limits.
- `references/best-practice-framework.md` — the repeatable method to derive best practices for any field. Follow it.
- `references/automation-patterns.md` — the reusable patterns you compose into tools + workflows.
- `references/generated-repo-architecture.md` — the exact `automation.config.json` contract the scaffolder consumes. Your design output must match this schema.

For a field you don't know cold, do a focused `WebSearch` (2–3 queries) on how
that field's teams actually spend their day and where the repetitive document /
research / follow-up work lives. Keep it light; the framework matters more than trivia.

## Step 2 — Design the `automation.config.json`

Apply the framework: decompose the field's recurring knowledge work → classify by
frequency × structure × stakes → map each task to a Cowork capability and an
automation pattern → choose tools/workflows → add guardrails.

Produce a config object that matches `generated-repo-architecture.md` exactly:

- Keep the **six core tools** (`read_document`, `list_workspace`, `write_deliverable`,
  `save_record`, `lookup_record`, `create_task`) — they cover most office work.
- Add **3–6 domain tools** that capture this field's specific actions. Use
  snake_case `name` and `handler`. New handlers (not core) get a stub injected into
  both languages for the user to implement — so design tools that are genuinely
  field-specific and worth implementing, not restatements of the core ones.
- Write each tool `description` *for the model*: when to use it and what it does.
- Add **2–4 workflows** (the recurring recipes). Give the genuinely-recurring ones
  a cron `schedule`; leave the rest `null`.
- Fill `systemPrompt`, `bestPractices` (3–5, field-specific, actionable),
  `suggestedConnectors`, and `coworkCapabilities`.

Write the design to a temp file, e.g. `/tmp/<domain>-design.json`. Validate it
reads as JSON before scaffolding.

For a richer design pass (or when the user wants options), delegate to the
**automation-architect** subagent (`agents/automation-architect.md`) — it
researches the field and returns a complete config. Otherwise design inline.

## Step 3 — Scaffold the repo

Run the scaffolder with your design. Default output is the user's working folder
so they can see and use it immediately.

```bash
python3 <skill_dir>/scripts/scaffold.py --config /tmp/<domain>-design.json --out <output_dir>
```

`<skill_dir>` is this skill's directory (`${CLAUDE_SKILL_DIR}` when available).
Quick path without a hand-built design (core tools + tuned metadata only):

```bash
python3 <skill_dir>/scripts/scaffold.py --domain "real estate" --out ./real-estate-automation
```

Use `--dry-run` first if you want to preview the plan, `--force` to overwrite.

The scaffolder copies the `local/` and `web/` templates, writes
`automation.config.json` to the root and into `web/`, injects valid stub handlers
for every domain tool into both `tools.py` and `tools.ts` (so validation passes),
and renders `README.md`, `docs/`, and the drop-in Cowork skill.

## Step 4 — Verify and hand off

- `python3 -m py_compile <out>/local/automation/*.py` to confirm the injected
  Python parses.
- Run `<out>/local` `automation doctor` if a key is available, or just confirm
  `automation tools` lists the expected tools.
- Tell the user: what field was targeted, which domain tools were stubbed (the
  `TODO`s they implement), the three ways to run it, and the single first workflow
  you'd switch on. Point them at `README.md`.

## Design principles (why this shape)

- **One contract, many surfaces.** `automation.config.json` is the single source
  of truth so the CLI and the webapp never drift. Design once; it works everywhere.
- **Deterministic work in tools, judgement in prompts.** Tools are predictable
  functions (file I/O, records, domain actions); the model supplies reasoning.
  This keeps runs reproducible and cheap.
- **Guardrails before power.** Anything irreversible or external (sending, paying,
  posting) stays human-approved. Folder access stays scoped. Secrets never go in prompts.
- **Honest about the preview.** Cowork's Chrome automation is slow and some
  connectors are immature; prefer connectors/MCP, then Chrome, then computer use.

## Notes

- The generated repo's local CLI defaults to the `direct` engine (plain Anthropic
  SDK) so it runs with just the `anthropic` package; `--engine agent` adds the
  Claude Agent SDK. Both dispatch the same tool registry.
- The webapp is BYOK by design — never ship a server-side Anthropic key. Keys are
  stored per session in Convex and used at request time.
- To package this generator as an installable `.skill`, zip the
  `cowork-automation-generator/` directory with a `.skill` extension.
