# Best-Practice Framework (Deriving Automations for Any Field)

The generator's job is to turn "automate my <field>" into a concrete, safe
automation kit. This document is the method — a repeatable way to derive best
practices for ANY field, even one neither the user nor this skill has seen
before. Do not lean on memorized domain knowledge; run the field through this
framework. It pulls capabilities from `cowork-capabilities.md` and patterns from
`automation-patterns.md`, and targets the three runtimes the generated repo
already supports (in-Cowork skill, local Python CLI, local website, MCP CRUD server).

## Step 1 — Decompose the field into recurring knowledge work

List the tasks that repeat in the field. A useful default spine covers: intake,
research, drafting, review, reporting, follow-up, scheduling, and
compliance/records. Walk each one: what triggers it, what goes in, what comes
out, who touches it. Aim for roughly 8–15 concrete tasks, named in the field's
own vocabulary rather than generic terms.

## Step 2 — Classify each task by frequency × structure × stakes

Score every task on three axes:

- Frequency — how often: daily / weekly / ad hoc.
- Structure — how repeatable the steps are: rote / semi-structured / judgement-heavy.
- Stakes — cost of a wrong or irreversible action: low / medium / high (money
  moved, filings, client-facing, legal exposure).

Turn the scores into a disposition:

- Automate fully — high frequency, high structure, low stakes.
- Assist (draft for a human) — structured but client-facing or judgement-flavored.
- Human-in-loop / approval gate — anything high-stakes or with an irreversible,
  external side effect.

When in doubt, downgrade one level toward human oversight.

## Step 3 — Map each task to a capability and a pattern

Pull the capability from `cowork-capabilities.md` and the pattern from
`automation-patterns.md`. Typical mappings:

- Files → Document Generation, Batch File Conversion, Structured Data Extraction.
- Connector or Chrome → Research & Synthesis, Web Form Filling, Inbox Triage.
- Scheduled task → Scheduled Digest, Reminder/Follow-up.
- Artifact → Dashboard/Tracker.
- Records (`save_record` / `lookup_record`) → Lightweight CRM/Record Logging.

Apply the path rule from doc 1: connector before Chrome before computer use.

## Step 4 — Decide the deployment surface per task

Three surfaces, matching the generated repo:

- In-Cowork skill — the user runs it conversationally inside Cowork (the drop-in
  `.cowork/skills/<domain>-ops`). Best for interactive, folder-centric work.
- Local CLI (Python) — scriptable, schedulable, runs the same tools headless.
  Best for recurring or batch jobs and anything you would cron.
- Website (local) — Next.js over local files; pair with the MCP server so Claude does CRUD. Best when
  non-local users need a shared UI.

Most tasks land in-Cowork plus local CLI; reserve the webapp for multi-user or
hosted needs. All three share one `automation.config.json` contract, so a task
defined once is available on every surface.

## Step 5 — Add guardrails

This layer is non-negotiable:

- Approval gates on every irreversible or external action (send, file, pay,
  delete, publish). The Approval-Gated External Action pattern exists for exactly
  this.
- Scoped folders — point Cowork at one working folder (e.g. ./inbox + ./output),
  never the whole drive.
- No secrets in prompts or memory — keys come from the environment
  (`ANTHROPIC_API_KEY`); the website and MCP are local-only (no keys).
- Validation/verification — confirm outputs (was the file written? is the record
  shape right? do totals reconcile?). Use a verifier subagent for high-stakes
  synthesis.
- Determinism where possible — file I/O, records, and task creation live in tools
  (predictable); judgement and synthesis stay in the prompt.

## Step 6 — Sequence the rollout

Start with one high-frequency, low-stakes win to build trust — typically the
daily inbox digest. Prove it works, then expand toward assist-level tasks, and
only wire up high-stakes tasks (behind approval gates) once the basics are
reliable. Ship the smallest useful automation first.

## Worked example: a small accounting practice

Step 1 decomposes the practice into recurring work: client intake, receipt and
invoice extraction, transaction categorization, reconciliation, statement
drafting, tax-filing submission, monthly client updates, and deadline tracking.

Steps 2–4 classify and map each task:

| Task | Freq | Structure | Stakes | Disposition | Capability | Pattern | Deployment |
|---|---|---|---|---|---|---|---|
| Intake doc collection | per client | semi | low | Assist | Chrome/connector + files | Inbox/Document Triage | In-Cowork |
| Receipt/invoice extraction | daily | rote | low | Automate | files + pdf skill | Structured Data Extraction | Local CLI (scheduled) |
| Transaction categorization | daily | semi | med | Assist | files + records | CRM/Record Logging | Local CLI |
| Reconciliation | monthly | semi | high | Human-in-loop | files | Extraction + validation | In-Cowork |
| Statement drafting | monthly | structured | med | Assist | xlsx/docx skills | Document Generation | In-Cowork |
| Tax-filing submission | quarterly | structured | high | Approval gate | Chrome/connector | Approval-Gated External Action | In-Cowork (gated) |
| Monthly client update | monthly | structured | med | Assist | skills + scheduled | Scheduled Digest/Briefing | Local CLI (scheduled) |
| Deadline reminders | ongoing | rote | med | Automate | scheduled + create_task | Reminder/Follow-up Creation | Local CLI (scheduled) |
| Practice dashboard | ongoing | rote | low | Automate | artifact + records | Dashboard/Tracker Artifact | In-Cowork artifact |

The resulting best-practice statements for this field:

1. Never let the agent submit a tax filing or move money — those are
   approval-gated. The agent prepares; a human submits.
2. Keep ledgers and extracted records columnar (JSONL/CSV). The xlsx skill
   mis-parses merged-cell workbooks, so normalize before any analysis.
3. Reconcile with a verification step — have the agent re-add totals and flag any
   line it could not match rather than silently balancing.
4. Schedule extraction and reminders (daily/weekly); keep judgement work
   (categorization edge cases, statement narrative) at assist level with human
   review.
5. Scope Cowork to a per-client folder; store client billing and preferences in
   memory, never credentials.

## Reusable best-practices checklist

Drop this into any generated repo's `docs/best-practices.md`:

- [ ] Cowork is pointed at one scoped working folder, not the whole drive.
- [ ] Every irreversible/external action (send, pay, file, delete, publish) is
      behind an approval gate.
- [ ] Secrets live in env (`ANTHROPIC_API_KEY`) — never in
      prompts, configs, or memory.
- [ ] Deterministic work (file I/O, records, tasks) is in tools; judgement is in
      the prompt.
- [ ] Outputs are validated (file exists, record shape, totals reconcile) before
      a run counts as done.
- [ ] Tabular data is columnar before any xlsx step.
- [ ] Recurring work is a scheduled workflow, not a manual prompt.
- [ ] External access uses the fastest correct path: connector → Chrome →
      computer use.
- [ ] High-stakes synthesis gets a verification pass (re-read or verifier
      subagent).
- [ ] Rollout starts with one high-frequency, low-stakes automation.

## Research-preview limits to respect

Carry the honest caveats from doc 1 into every plan: Chrome is slow for
click-heavy tasks; some connectors (including Google) are immature; complex
spreadsheets parse poorly; computer use is preview-tier and partly blocked.
Design around them — keep no critical, time-sensitive path on the slowest route,
and always keep a human gate on the expensive mistakes.
