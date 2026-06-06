# Generator Wizard (local GUI)

A no-install web form for creating a Cowork automation project folder — the
point-and-click alternative to running the `cowork-automation-generator` skill in
Cowork.

## Run

```bash
node wizard/server.mjs
# open http://localhost:4321
```

Requirements: Node 18+ and Python 3 (the wizard calls the scaffolder). No
`npm install`, no Convex.

## What it does

You fill in your field/role and pick surfaces (the in-Cowork skill is always
included; Local CLI is on by default; the BYOK webapp is optional). On submit it
runs `skills/cowork-automation-generator/scripts/scaffold.py` and creates
`projects/<your-field>/`.

It creates the folder with the **6 core tools**. For field-specific tools, open the
new folder in Cowork and run the `cowork-automation-generator` skill — Claude adds
and implements them, and operates the automation for you.

Env vars: `PORT` (default 4321), `PYTHON` (default `python3`).
