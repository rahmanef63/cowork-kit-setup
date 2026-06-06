# Cowork Capabilities (Ground Truth)

This is the capability catalog the generator maps domain tasks onto. Every fact
here describes Claude Cowork as of mid-2026. When you scaffold an automation,
pick capabilities from this list — do not invent features. Lines marked
*(guidance)* are general best practice, not hard product facts.

## What Cowork is

Cowork is Anthropic's agentic mode inside the Claude desktop app (macOS and
Windows). It became generally available to paid subscribers on April 9, 2026;
before that, early access ran through higher tiers (Max, roughly $100–200/mo).
It is built on the same agent architecture as Claude Code, wrapped in the chat
UI so non-developers can use it. You give Claude a goal; it plans multi-step
work, executes it in a loop, and keeps you informed through a live progress/task
sidebar and an Artifacts pane that shows the files it reads and creates.

The capabilities below are the building blocks. The generator selects among them
per task (see `best-practice-framework.md`) and composes them into patterns (see
`automation-patterns.md`).

## 1. Files & sandbox

What it is: you grant Claude access to a local folder; within it, it can read,
edit, create, and delete files. Execution happens in a sandboxed Linux
environment with Python, Node, and common CLI tools preinstalled. With your
permission it can install more (e.g. LibreOffice for office conversion,
Ghostscript for PDF work).

- When to reach for it: any task whose inputs and outputs are files on disk — the
  default substrate for almost every automation.
- Strengths: batch file conversion, data crunching, report generation;
  deterministic, inspectable, no external dependency.
- Limits & gotchas: file delete is destructive, so scope the folder tightly;
  installed sandbox state does not reliably persist between sessions; large or
  binary files cost time. Put deletion behind an approval gate *(guidance)*.
- Example: "Convert every .docx in ./inbox to PDF and write them to ./output."

## 2. Skills

What it is: SKILL.md-based extensions that teach Claude a capability or format.
Anthropic ships office skills (docx, pptx, xlsx, pdf); you can author custom ones
with the skill-creator. Skills use progressive disclosure — they load only when
the task is relevant, so they do not bloat context.

- When to reach for it: producing or parsing Office/PDF documents natively, or
  packaging your own repeatable procedure.
- Strengths: native handling of docx/pptx/xlsx/pdf; reusable; cheap when idle
  (loads on demand only).
- Limits & gotchas: the xlsx skill struggles with non-columnar or merged-cell
  spreadsheets — keep tabular data clean and columnar. A skill is instructions,
  not a guarantee; validate the output.
- Example: "Generate a formatted .docx engagement letter from this intake record."

## 3. Plugins

What it is: bundles of skills + agents + hooks + MCP servers, described by a
`.claude-plugin/plugin.json` manifest. Plugins can be grouped into marketplaces
for distribution.

- When to reach for it: shipping a whole domain kit (several skills, an agent, a
  connector config) as one installable unit.
- Strengths: one-step install of a coherent toolset; versioned; shareable via a
  marketplace.
- Limits & gotchas: more moving parts than a single skill; keep the manifest
  minimal. The generated repo already ships a drop-in
  `.cowork/skills/<domain>-ops/SKILL.md`; a plugin is the next step up when you
  also bundle connectors and hooks.
- Example: "Install the 'accounting-ops' plugin so the firm gets its skills,
  agent, and connectors at once."

## 4. Connectors (MCP)

What it is: Model Context Protocol connectors link Claude to external services.
Hundreds exist, all Anthropic-reviewed. Two delivery forms: web connectors
(browser-based APIs) and desktop extensions (deeper local access). Inside Cowork
connectors also gain filesystem context — Claude can pull external data and save
it locally, or use local files as inputs to external actions.

- When to reach for it: any service that has a connector. This is the preferred
  path for external systems — fastest and most precise.
- Strengths: structured API access (no screenshot guessing); bidirectional with
  the local folder; reviewed for safety. Enterprise GA added role-based access
  controls, group spend limits, usage analytics, per-tool connector controls,
  and a Zoom MCP connector.
- Limits & gotchas: at the source's time, Gmail / Google Calendar / Google Drive
  connectors were still in development, so Google workflows often fell back to
  the Chrome extension. Some connectors are immature — verify the specific one
  before depending on it.
- Example: "Pull this week's closed deals from the CRM connector and save them as
  ./data/deals.jsonl."

## 5. Claude in Chrome

What it is: a browser extension. Claude can see pages, click, fill forms,
navigate tabs, and take screenshots. It has built-in familiarity with Gmail,
Google Docs, Slack, and GitHub.

- When to reach for it: web apps with no dedicated connector — especially Google
  workflows while those connectors mature.
- Strengths: works on any site; good for retrieval and light automation;
  understands common apps out of the box.
- Limits & gotchas: it operates through screenshot round-trips, so it is slow for
  click-heavy work; long web tasks can take many minutes. Great for read and
  light-write, poor for bulk clicking.
- Example: "Open Gmail, find this week's invoices, and save the attachments to
  ./inbox."

## 6. Computer use

What it is: a research-preview capability that lets Claude control desktop apps
via screenshots plus mouse and keyboard, for native apps with no MCP or web path.
Access is tiered: browsers are read-only via screenshot, terminals and IDEs are
click-only, everything else is full control.

- When to reach for it: only when there is no API, connector, or Chrome route to
  the app.
- Strengths: reaches native apps nothing else can; spans cross-app workflows.
- Limits & gotchas: the slowest path; research preview; tiering blocks some
  actions. Use as a last resort *(guidance: prefer connector → Chrome → computer
  use)*.
- Example: "Enter these figures into the desktop-only practice-management app."

## 7. Scheduled tasks

What it is: tasks that run automatically on a cron-like schedule, or once at a
future time.

- When to reach for it: anything recurring — daily briefings, weekly digests,
  periodic reminders — or a one-off deferred run.
- Strengths: unattended recurrence; pairs naturally with digest and reminder
  patterns.
- Limits & gotchas: a scheduled run is still an agent run with no one watching
  live, so keep its prompt deterministic and its actions reversible or gated
  *(guidance)*.
- Example: "Every weekday at 8am, build a digest of new ./inbox files and create
  tasks for action items."

## 8. Artifacts

What it is: persisted, self-contained HTML views. An artifact can pull fresh data
from connectors each time it is opened.

- When to reach for it: dashboards, trackers, and recurring reports that should
  stay live rather than be regenerated by hand.
- Strengths: self-contained; refreshes on open; a clean handoff surface for
  non-technical users.
- Limits & gotchas: it is a view, not a database — keep source-of-truth data in
  files and records, not embedded in the artifact.
- Example: "Build a matter-status dashboard artifact that reads
  ./data/matters.jsonl."

## 9. Subagents

What it is: delegation to parallel agents for fan-out, research, or verification.

- When to reach for it: work that parallelizes (research many sources at once) or
  benefits from an independent checker.
- Strengths: throughput on wide tasks; a separate verifier reduces single-pass
  errors.
- Limits & gotchas: more agents means more cost and coordination; reserve for
  genuinely parallel or verification-worthy work *(guidance)*.
- Example: "Research these 10 counterparties in parallel and return one
  synthesized brief."

## 10. Memory

What it is: file-based memory that persists facts across sessions.

- When to reach for it: anything the agent should remember between runs — client
  preferences, naming conventions, recurring context.
- Strengths: continuity without re-prompting; plain files you can inspect and
  edit.
- Limits & gotchas: it is persisted text — do not store secrets there; keep it
  scoped and curated *(guidance)*.
- Example: "Remember that this client bills in EUR and prefers Friday updates."

## Choosing the right path

For external systems, prefer the fastest correct route in this order:

1. Dedicated MCP connector if one exists — structured, precise, safest.
2. Else Claude in Chrome for web apps, accepting it is slow for click-heavy work.
3. Else computer use for native apps with no other route.

Quick mapping for the rest:

- Structured external data → connector.
- Web retrieval or light writes → Chrome.
- Native-only app → computer use.
- Produce or parse Office/PDF docs → skills.
- Recurring work → wrap any of the above in a scheduled task.
- Live status view → artifact.
- Wide or parallel work → subagents.
- Facts that outlive a session → memory.
- Files in, files out → stay in the Files & sandbox layer.

The rule across all of this: the fastest correct path wins.

## Research-preview caveats (honest)

- Chrome automation is slow because of screenshot round-trips; long click-heavy
  web tasks can take many minutes.
- Some connectors are immature; the Google connectors (Gmail / Calendar / Drive)
  were still in development at the source's time, with Chrome the common fallback.
- The xlsx skill parses complex spreadsheets (non-columnar, merged cells) poorly.
- Computer use is a research preview with tiered, sometimes-blocked actions.

Design around these: prefer connectors, keep spreadsheets columnar, gate
destructive or irreversible actions, and never put a critical, time-sensitive
path on the slowest route.
