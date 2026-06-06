# Automation Patterns (Composable Building Blocks)

These are the reusable shapes of work the generator composes into a domain kit.
Each pattern pins a recurring task shape to Cowork capabilities (from
`cowork-capabilities.md`) and to the shared tool primitives every generated repo
exposes. Compose patterns; do not reinvent them. The framework selects patterns
in Step 3 (`best-practice-framework.md`).

Shared tool primitives referenced below:

- `read_document(path)` — read a file's full text.
- `list_workspace(pattern)` — discover input files by glob.
- `write_deliverable(filename, content)` — write a finished file to ./output.
- `save_record(table, data)` — append a structured record to a JSONL datastore.
- `lookup_record(table, query)` — search saved records.
- `create_task(title, due?, notes?)` — create a follow-up task.

## Inbox / Document Triage

- Intent: sort incoming items (files, emails, messages) into categories and route
  each to the right next step.
- Trigger: new items land in ./inbox, or a scheduled inbox check.
- Capability/tools: Files & sandbox; optionally connector or Chrome for email.
  Primitives: `list_workspace`, `read_document`, `save_record`, `create_task`.
- Local vs web: local-first (folder); use Chrome/connector when the source is a
  web inbox.
- Guardrail: classify and log only — do not auto-reply or delete; route anything
  actionable to a task.
- Flow: `list_workspace("inbox/*")` → for each `read_document` → classify →
  `save_record("triage", …)` → if actionable `create_task`.

## Document Generation (report / letter / brief)

- Intent: turn structured inputs into a finished document.
- Trigger: on request, or after a record or workflow completes.
- Capability/tools: Skills (docx/pptx/pdf) + Files. Primitives: `read_document` /
  `lookup_record` → `write_deliverable`.
- Local vs web: either; in-Cowork for interactive drafting, local CLI for batch.
- Guardrail: client-facing output is assist-level — human review before it is sent.
- Flow: gather inputs (`lookup_record` / `read_document`) → draft →
  `write_deliverable("letter.docx", …)` → hand to a human.

## Research & Synthesis (web → doc)

- Intent: gather from multiple web sources and synthesize one cited document.
- Trigger: a research question, or a recurring brief.
- Capability/tools: Chrome or connectors for retrieval; Subagents for parallel
  fan-out plus a verifier. Primitives: `write_deliverable`.
- Local vs web: retrieval is web (Chrome/connector); output is local.
- Guardrail: cite sources; add a verification pass for high-stakes claims; Chrome
  is slow, so budget time.
- Flow: fan out subagents over sources → each returns notes → verifier checks →
  synthesize → `write_deliverable("brief.md", …)`.

## Structured Data Extraction (files → records)

- Intent: pull fields out of documents into structured records.
- Trigger: new source docs (invoices, forms, PDFs) arrive.
- Capability/tools: Files + pdf skill; sandbox for parsing. Primitives:
  `list_workspace`, `read_document`, `save_record`.
- Local vs web: local-first; schedulable.
- Guardrail: keep records columnar (avoid xlsx merged-cell traps); validate
  required fields; flag low-confidence extractions instead of guessing.
- Flow: `list_workspace` → `read_document` → extract → validate →
  `save_record("invoices", …)`.

## Lightweight CRM / Record Logging

- Intent: maintain simple structured records (leads, clients, transactions)
  without a database.
- Trigger: any event worth remembering — new lead, status change.
- Capability/tools: Files (JSONL datastore) + Memory for preferences. Primitives:
  `save_record`, `lookup_record`.
- Local vs web: either; the JSONL store is the shared substrate.
- Guardrail: append-only where possible; one logical table per entity; no secrets
  in records.
- Flow: `lookup_record("leads", q)` to dedupe → `save_record("leads", …)` →
  optionally `create_task` for follow-up.

## Scheduled Digest / Briefing

- Intent: produce a recurring summary (daily/weekly) unattended.
- Trigger: a cron schedule.
- Capability/tools: Scheduled tasks + Files (+ connector/Chrome for fresh data).
  Primitives: `list_workspace`, `read_document`, `write_deliverable`, `create_task`.
- Local vs web: local CLI (schedulable) is the natural home.
- Guardrail: a scheduled run is unwatched — keep its actions read/produce only and
  gate anything external.
- Flow: [cron] → gather new inputs → summarize →
  `write_deliverable("digest-<date>.md", …)` → `create_task` for action items.

## Reminder / Follow-up Creation

- Intent: surface things a human must do later.
- Trigger: during any workflow when an action item appears, or a scheduled sweep
  of due dates.
- Capability/tools: Files/records + Scheduled tasks. Primitives: `create_task`,
  `lookup_record`.
- Local vs web: either.
- Guardrail: create tasks; do not take the follow-up action automatically if it
  is external.
- Flow: detect obligation → `create_task(title, due, notes)`; [scheduled]
  `lookup_record` due-soon → `create_task` or roll into a digest.

## Web Form / Portal Filling (Chrome)

- Intent: enter data into a web app or portal that has no connector.
- Trigger: a batch of records ready to submit.
- Capability/tools: Claude in Chrome. Primitives: `lookup_record` /
  `read_document` for the source data.
- Local vs web: web (Chrome).
- Guardrail: Chrome is slow for click-heavy work; the final submit on anything
  consequential is approval-gated; verify each entry by screenshot.
- Flow: `lookup_record` → open portal in Chrome → fill fields → pause for
  approval → submit → `save_record("submissions", …)`.

## Approval-Gated External Action

- Intent: wrap any irreversible/external action (send, pay, file, publish,
  delete) in a human checkpoint.
- Trigger: a workflow reaches an external side effect.
- Capability/tools: whatever performs the action (connector/Chrome/computer use)
  plus an explicit confirm step. Primitives: `create_task` (log the pending
  action), `save_record` (audit trail).
- Local vs web: either; the gate is the point.
- Guardrail: this IS the guardrail — never auto-execute; present a clear
  summary/diff and wait for an explicit yes.
- Flow: prepare action → summarize what will happen (`write_deliverable` if
  useful) → request approval → on yes: execute → `save_record("audit", …)`.

## Dashboard / Tracker Artifact

- Intent: a live view of status that refreshes on open.
- Trigger: the user wants an at-a-glance tracker.
- Capability/tools: Artifacts (self-contained HTML, can pull from connectors) +
  records as source. Primitives: `lookup_record` (data source).
- Local vs web: the artifact lives in Cowork; it reads local records or connector
  data.
- Guardrail: an artifact is a view — keep the source of truth in records/files,
  not embedded in the HTML.
- Flow: `lookup_record("matters")` → render HTML artifact → user opens →
  artifact re-pulls fresh data.

## Batch File Conversion

- Intent: convert many files between formats.
- Trigger: a folder of inputs needs reformatting.
- Capability/tools: Files & sandbox (install LibreOffice/Ghostscript with
  permission). Primitives: `list_workspace`, `write_deliverable`.
- Local vs web: local (sandbox).
- Guardrail: write to ./output, never overwrite originals; confirm count-in
  equals count-out.
- Flow: `list_workspace("inbox/*.docx")` → for each convert in sandbox →
  `write_deliverable("<name>.pdf", …)` → report N converted.

## Composing patterns

Most domain workflows are two to four of these chained. Examples:

- Triage → Extraction → Record Logging → Scheduled Digest.
- Research & Synthesis → Document Generation → Approval-Gated send.
- Batch File Conversion → Document Generation → Dashboard Artifact.

Quick reference — pattern to primary primitives and capability:

| Pattern | Primary primitives | Primary capability |
|---|---|---|
| Inbox / Document Triage | list_workspace, read_document, save_record, create_task | Files (+ Chrome/connector) |
| Document Generation | read_document/lookup_record, write_deliverable | Skills + Files |
| Research & Synthesis | write_deliverable | Chrome/connector + Subagents |
| Structured Data Extraction | list_workspace, read_document, save_record | Files + pdf skill |
| CRM / Record Logging | save_record, lookup_record | Files + Memory |
| Scheduled Digest / Briefing | list_workspace, read_document, write_deliverable, create_task | Scheduled tasks + Files |
| Reminder / Follow-up | create_task, lookup_record | Scheduled tasks + Files |
| Web Form / Portal Filling | lookup_record, read_document | Chrome |
| Approval-Gated External Action | create_task, save_record | any actor + confirm step |
| Dashboard / Tracker Artifact | lookup_record | Artifacts + records |
| Batch File Conversion | list_workspace, write_deliverable | Files & sandbox |
