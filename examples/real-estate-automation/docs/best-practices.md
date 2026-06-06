# Best Practices — Real Estate Agency

Tuned for this field. They follow the generator's framework: decompose recurring
work, match each task to the right Cowork capability, choose a deployment surface,
add guardrails.

## Field-specific guidance
- **Speed-to-lead wins deals** — Automate lead intake so a qualified summary and a drafted first reply exist within minutes of an inquiry landing in ./inbox. The agent drafts; you approve and send.
- **One source of truth for leads and listings** — Log every lead, listing, and viewing with save_record instead of scattered spreadsheets. lookup_record recalls history before any follow-up so nothing is double-worked or dropped.
- **Never auto-send or auto-publish** — Client emails, listing copy, and price guidance are drafted to ./output for human review. Publishing to portals (MLS, Zillow) stays manual or human-approved — those are irreversible, public actions.
- **Verify the comps before quoting a price** — comparable_analysis computes guidance from the comps you supply; always sanity-check the inputs and the range before sharing a number with a seller.
- **Calendar via connector, portals via Chrome** — Use the Google Calendar connector for viewings and Gmail for client mail. For MLS/portal lookups, the Chrome extension works but is slow (screenshot-based) — prefer pasting facts into ./inbox when you can.

## Universal checklist
- Scope folder access: point Cowork (or the CLI workspace) at one working folder.
- Keep deterministic steps in tools; keep judgement in the prompt.
- Gate irreversible/external actions (sending, paying, posting) behind human approval.
- Never paste secrets/keys into prompts. The webapp uses BYOK; the CLI reads `.env`.
- Add a verification step for anything high-stakes.
- Schedule the recurring parts (- **new-lead-intake** — on-demand: Process a new inquiry: qualify it, log it, draft a fast first reply, and create a follow-up task.
- **listing-package** — on-demand: Build a full listing package from a property fact sheet: listing sheet plus a pricing memo from comps.
- **weekly-lead-followup** — scheduled `0 8 * * 1`: Monday morning: surface leads needing follow-up and draft reminders.
- **daily-viewing-digest** — scheduled `0 7 * * *`: Each morning: summarize today's scheduled viewings with prep notes.).
- Start with one high-frequency, low-stakes workflow; expand once it's trusted.
- Research-preview limits: Chrome automation is slow; complex spreadsheets parse poorly.
