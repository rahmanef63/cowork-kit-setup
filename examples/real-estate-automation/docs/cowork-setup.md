# Using Real Estate Agency inside Cowork

Cowork is the fastest way to *run* these automations interactively.

## 1. Give Cowork the folder
Put this repo (or just your working files) in a folder and grant Cowork access to
it. The agent reads from `./inbox` and writes deliverables to `./output`.

## 2. Install the drop-in skill
This repo ships a Cowork skill at `.cowork/skills/real-estate-ops/SKILL.md`.
Copy that folder into your Cowork/Claude skills directory so Claude loads the
domain workflows automatically.

## 3. Connect suggested connectors (MCP)
Enable these in Cowork → Settings → Connectors:
  - gmail
  - google-calendar
  - google-drive

If a connector for your tool isn't available yet, Cowork can fall back to the
Chrome extension for web tasks (slower, screenshot-based).

## 4. Schedule the recurring work
Create scheduled tasks for:
  - `0 8 * * 1` → weekly-lead-followup: Monday morning: surface leads needing follow-up and draft reminders.
  - `0 7 * * *` → daily-viewing-digest: Each morning: summarize today's scheduled viewings with prep notes.

## 5. Guardrails
Keep external/irreversible actions human-approved. Review the agent's plan in the
progress sidebar before letting it act on anything that leaves your machine.
