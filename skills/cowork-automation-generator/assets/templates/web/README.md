# Automation Data — local CRUD dashboard

A small **local** Next.js website for browsing and editing the project's on-disk
datastore. It reads and writes the **same files** the Python CLI produces and the
MCP server controls, so this is the "website" whose data Claude manages through the
MCP.

There is **no database service and no API keys** — no external backend at all.
Every API route uses Node's `fs` to read and write plain files under the project
root.

## What it edits

```
<workspace>/.data/<table>.jsonl   one JSON object per line (records)
<workspace>/output/<file>         documents / deliverables
```

Each record is
`{ "id": "...", ...your fields, "created_at": "...", "updated_at": "..." }`,
where `id` is a 12-character hex string and the timestamps are ISO-8601 — the same
shape the CLI (`local/automation/tools.py`) and the MCP server (`mcp/store.py`)
write. `tasks` is just another table.

## Run it

```bash
cd web
npm install
npm run dev      # http://localhost:3000
```

`next dev` runs from `web/`, so the **workspace is the parent of `web/`** (the
project root). The dashboard immediately sees whatever the CLI or the MCP server
have already written there.

Scripts: `dev`, `build`, `start`, `lint`.

## How it shares data with the CLI and the MCP server

All three surfaces point at the same `.data/` and `output/` folders:

| Surface      | Reads/writes                                           |
| ------------ | ------------------------------------------------------ |
| This website | `app/api/**` route handlers → `lib/store.ts` (Node fs) |
| Python CLI   | `local/automation/tools.py`                            |
| MCP server   | `mcp/store.py` (the tools Claude calls in Cowork)      |

Create a lead in the UI and it shows up in the CLI and to Claude via the MCP; have
Claude add a row through the MCP and it appears here on the next refresh. One
source of truth on disk.

## Point it at another project

By default the workspace is the parent of `web/`. To target a different project,
copy `.env.local.example` to `.env.local` and set:

```
AUTOMATION_WORKSPACE=/absolute/path/to/another/project
```

When set, the dashboard uses `<that>/.data` and `<that>/output`.

## API routes

| Method + path                      | Action                          |
| ---------------------------------- | ------------------------------- |
| `GET  /api/tables`                 | list record tables              |
| `GET  /api/records/[table]?q=`     | list / search records           |
| `POST /api/records/[table]`        | create a record (body = fields) |
| `PUT  /api/records/[table]/[id]`   | update (merge) a record         |
| `DELETE /api/records/[table]/[id]` | delete a record                 |
| `GET  /api/documents`              | list documents in `output/`     |
| `GET  /api/documents/[name]`       | read one document (plain text)  |

All run on the Node.js runtime (`export const runtime = "nodejs"`) because they
touch the filesystem. The fs code lives only in `lib/store.ts` and these route
handlers — never in a client component.

## Before you ship this

This template is built for **local use**. It has no authentication and only light
input validation (table/file-name sanitizing and JSON-object checks). For anything
beyond your own machine, add:

- real authentication and authorization,
- strict per-table schema validation,
- rate limiting and audit logging,
- and a review of what lives under `.data/` and `output/` before exposing it.
