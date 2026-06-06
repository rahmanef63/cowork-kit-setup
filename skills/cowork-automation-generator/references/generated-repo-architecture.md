# Generated Repo Architecture (Canonical Contract)

Every generated project (`projects/<slug>/`) follows this. All surfaces share ONE
local datastore; `automation.config.json` is the tool contract. No external
database, no API keys for data (only the optional CLI needs an Anthropic key).

## 1. Single source of truth: `automation.config.json`

Repo root of the generated project. Shape:

```jsonc
{
  "domain": "real-estate",            // kebab-case slug
  "displayName": "Real Estate Agency",
  "description": "...",
  "version": "0.1.0",
  "model": "claude-opus-4-8",
  "systemPrompt": "You are an automation agent for ...",
  "coworkCapabilities": ["files", "web", "connectors", "scheduled"],
  "suggestedConnectors": ["gmail", "google-calendar"],
  "bestPractices": [ { "title": "...", "detail": "..." } ],
  "tools": [
    {
      "name": "draft_listing",        // snake_case; the Anthropic tool name
      "handler": "draft_listing",     // snake_case; key into the CLI registry
      "description": "When to use it + what it does. Write it for the model.",
      "input_schema": { "type": "object", "properties": { ... }, "required": [ ... ] }
    }
  ],
  "workflows": [
    { "name": "weekly-lead-followup", "description": "...", "prompt": "...", "schedule": "0 8 * * 1" }
  ]
}
```

Rules: tool `name`/`handler` are snake_case (`^[a-z][a-z0-9_]*$`); `input_schema`
is plain JSON Schema; every tool needs a handler in the CLI registry (startup
validation enforces this).

## 2. Shared local datastore (the heart)

All surfaces read/write the same files under the project root (or
`$AUTOMATION_WORKSPACE`):

```
<project>/.data/<table>.jsonl   one JSON object per line; each has id, fields, created_at, updated_at
<project>/output/<file>         documents / deliverables
<project>/inbox/                source files the agent reads (CLI workspace)
```

Records are id-addressable, enabling full CRUD. "tasks" is just a table. This
shared store is what lets the CLI, the website, and the MCP server interoperate.

## 3. Eight core tools (full CRUD)

Always present, implemented in the CLI registry (`local/automation/tools.py`):

- `read_document(path)`, `list_workspace(pattern?)`, `write_deliverable(filename, content)`
- `save_record(table, data)` → create (returns id)
- `lookup_record(table, query?)` → read (returns records incl. ids)
- `update_record(table, id, data)` → update (merge)
- `delete_record(table, id)` → delete (irreversible; confirm first)
- `create_task(title, due?, notes?)` → create a row in the "tasks" table

Domain tools (3–6) are added per field; new handlers get stubs injected into the
CLI registry for implementation.

## 4. Surfaces

### cowork (always) — `.cowork/skills/<slug>-ops/SKILL.md`
A drop-in Cowork skill. Inside Cowork, Claude uses its native file tools on the
project folder following this guidance. Zero setup.

### cli (default) — `local/`
Python package + console script `automation`:
- `automation run "<task>"`, `workflow <name>`, `tools`, `doctor`
- engines: `--engine direct` (Anthropic SDK loop) or `--engine agent` (Claude Agent
  SDK + in-process MCP). Reads `ANTHROPIC_API_KEY` from `.env`. Dispatches the
  config's tools through the shared registry over the datastore.

### web (opt-in `--web`) — `web/`
A **local-filesystem Next.js** CRUD dashboard. App-Router API routes use Node `fs`
to read/write the SAME `.data/`+`output/` (resolved as `../` from `web/`, or
`$AUTOMATION_WORKSPACE`). No Convex, no account, no API key. Shows records per
table + documents; create/edit/delete in the browser.

### mcp (opt-in `--mcp`) — `mcp/`
A **Python FastMCP** server (stdio) exposing full CRUD over the same datastore:
`list_tables`, `list_records`, `get_record`, `create_record`, `update_record`,
`delete_record`, `list_documents`, `read_document`, `write_document`. Ships a
`.mcp.json` so Cowork/Claude Code can connect it (named `<slug>-data`). This is how
Claude controls the website's data from Cowork. `pip install -r mcp/requirements.txt`.
Pure stdlib store logic in `mcp/store.py` (no deps); `server.py` wraps it.

The website *shows* the data; the MCP *lets Claude change* it; both share `.data/`.

## 5. Layout produced by the scaffolder

```
projects/<slug>/
├── automation.config.json        # the contract
├── README.md  docs/              # quickstart + best-practices + cowork-setup
├── .cowork/skills/<slug>-ops/    # drop-in Cowork skill (always)
├── local/                        # Python CLI (if cli)
│   └── automation/{config,tools,direct_runner,agent_sdk_runner,cli}.py
├── web/                          # local-fs Next.js CRUD site (if web)
│   ├── app/  lib/store.ts  package.json
└── mcp/                          # Python FastMCP CRUD server (if mcp)
    ├── server.py  store.py  .mcp.json  requirements.txt
```

Default surfaces: `cowork,cli`. Add `--web` and/or `--mcp`. Everything stays
consistent because there is one contract and one datastore.
