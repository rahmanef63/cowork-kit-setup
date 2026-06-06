# Using Real Estate Agency inside Cowork

Cowork is the fastest way to run these automations — no install, no terminal.

## 1. Give Cowork the folder
Put this repo (or just your working files) in a folder and grant Cowork access.
The agent reads from `./inbox` and writes deliverables to `./output`.

## 2. Install the drop-in skill
Copy `.cowork/skills/real-estate-ops/` into your Cowork/Claude skills directory
so Claude loads the domain workflows automatically.

## 3. Connect suggested connectors (MCP)
Enable these in Cowork → Settings → Connectors:
  - gmail
  - google-calendar
  - google-drive

## 4. Schedule the recurring work
Create scheduled tasks for:
  - `0 8 * * 1` → weekly-lead-followup: Monday morning: surface leads needing follow-up and draft reminders.
  - `0 7 * * *` → daily-viewing-digest: Each morning: summarize today's scheduled viewings with prep notes.

## 5. Guardrails
Keep external/irreversible actions human-approved. Review the plan in the progress
sidebar before letting the agent act on anything that leaves your machine.
