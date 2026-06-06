# MCP server — control the website's data from Cowork

This MCP server exposes **full CRUD** (create/read/update/delete) over the
project's local datastore (`.data/*.jsonl` + `output/`). It's the same data the
website shows and the CLI uses — so connecting this in Cowork lets Claude manage
the website's content directly.

## Setup

```bash
pip install -r mcp/requirements.txt   # installs the `mcp` package
```

## Connect it

- **Claude Code / Cowork (project):** this folder ships `.mcp.json`, so opening the
  project picks up the `automation-data` server automatically (approve it once).
- **Manual / other clients:** run `python3 mcp/server.py` (stdio). On Windows use
  `python` if `python3` isn't on PATH.

## Tools

`list_tables`, `list_records(table, query?)`, `get_record(table, id)`,
`create_record(table, data)`, `update_record(table, id, data)`,
`delete_record(table, id)`, `list_documents`, `read_document(name)`,
`write_document(name, content)`.

`delete_record` is destructive — confirm before using. Data lives under the
project's `.data/` and `output/`; point a different project with
`AUTOMATION_WORKSPACE`.
