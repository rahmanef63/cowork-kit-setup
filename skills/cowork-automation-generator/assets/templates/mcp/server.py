"""
mcp/server.py — MCP server (FastMCP, stdio) exposing full CRUD over the project's
local datastore. Connect it in Cowork/Claude Code so Claude can create/read/update/
delete the same records and documents the website shows.

Run:        python3 mcp/server.py         (or via the bundled .mcp.json)
Requires:   pip install -r mcp/requirements.txt   (the `mcp` package)
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

import store

mcp = FastMCP("automation_mcp")

RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
WR = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
DEL = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}


@mcp.tool(name="list_tables", annotations={"title": "List tables", **RO})
def list_tables() -> str:
    """List the record tables that exist in the datastore."""
    return json.dumps(store.list_tables())


@mcp.tool(name="list_records", annotations={"title": "List/search records", **RO})
def list_records(table: str, query: str = "") -> str:
    """List records in a table. `query` is an optional case-insensitive substring filter over any field."""
    return json.dumps(store.list_records(table, query), ensure_ascii=False, indent=2)


@mcp.tool(name="get_record", annotations={"title": "Get a record", **RO})
def get_record(table: str, id: str) -> str:
    """Get one record by id from a table."""
    rec = store.get_record(table, id)
    return json.dumps(rec, ensure_ascii=False, indent=2) if rec else f"No record '{id}' in '{table}'."


@mcp.tool(name="create_record", annotations={"title": "Create a record", **WR})
def create_record(table: str, data: dict) -> str:
    """Create a record in a table. Returns the created record (with its new id)."""
    try:
        return json.dumps(store.create_record(table, data), ensure_ascii=False)
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool(name="update_record", annotations={"title": "Update a record", **WR})
def update_record(table: str, id: str, data: dict) -> str:
    """Update (merge) fields of a record by id. Returns the updated record, or a not-found message."""
    rec = store.update_record(table, id, data)
    return json.dumps(rec, ensure_ascii=False) if rec else f"No record '{id}' in '{table}'."


@mcp.tool(name="delete_record", annotations={"title": "Delete a record", **DEL})
def delete_record(table: str, id: str) -> str:
    """Delete a record by id. Irreversible — confirm with the user first."""
    return f"Deleted '{id}' from '{table}'." if store.delete_record(table, id) else f"No record '{id}' in '{table}'."


@mcp.tool(name="list_documents", annotations={"title": "List documents", **RO})
def list_documents() -> str:
    """List document/deliverable files in the project's output folder."""
    return json.dumps(store.list_documents())


@mcp.tool(name="read_document", annotations={"title": "Read a document", **RO})
def read_document(name: str) -> str:
    """Read a document/deliverable by file name."""
    doc = store.read_doc(name)
    return doc if doc is not None else f"No document named '{name}'."


@mcp.tool(name="write_document", annotations={"title": "Write a document", **WR})
def write_document(name: str, content: str) -> str:
    """Create or overwrite a document/deliverable. Returns its path."""
    try:
        return f"Wrote {store.write_doc(name, content)}."
    except Exception as exc:
        return f"Error: {exc}"


if __name__ == "__main__":
    mcp.run()
