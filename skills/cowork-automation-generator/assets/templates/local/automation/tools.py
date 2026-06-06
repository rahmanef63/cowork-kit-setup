"""
automation/tools.py
===================
Shared tool registry: deterministic, offline-safe, pure-Python handlers that both
CLI engines dispatch through. Each handler takes a single dict and returns
``{"content": "<string the model sees>"}``. Handlers never raise into the loop.

The local datastore is shared by the CLI, the MCP server, and the website:
  <workspace>/.data/<table>.jsonl   one JSON object per line, each with an "id"
  <workspace>/output/<file>         deliverables / documents
This is the source of truth for full CRUD (create/read/update/delete).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import workspace_root

REGISTRY: dict[str, Callable[[dict], dict]] = {}


def register(name: str):
    def deco(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        REGISTRY[name] = fn
        return fn
    return deco


# --------------------------------------------------------------------------- #
# Workspace + datastore helpers
# --------------------------------------------------------------------------- #
def _ws() -> Path:
    return workspace_root()


def _output_dir() -> Path:
    d = _ws() / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _data_dir() -> Path:
    d = _ws() / ".data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _within_ws(p: Path) -> bool:
    try:
        p.resolve().relative_to(_ws())
        return True
    except ValueError:
        return False


def _rel(p: Path) -> str:
    return str(p.relative_to(_ws())) if _within_ws(p) else str(p)


def _safe_name(name: str) -> str:
    return Path(str(name)).name


def _safe_table(table: str) -> str:
    cleaned = "".join(c for c in str(table) if c.isalnum() or c in ("-", "_"))
    return cleaned.strip("-_")


def _normalize_glob(pattern: str) -> str:
    if pattern == "**":
        return "**/*"
    if pattern.endswith("/**"):
        return pattern + "/*"
    return pattern


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _table_path(safe: str) -> Path:
    return _data_dir() / f"{safe}.jsonl"


def _read_table(safe: str) -> list[dict]:
    path = _table_path(safe)
    if not path.is_file():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _write_table(safe: str, rows: list[dict]) -> None:
    path = _table_path(safe)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _append_row(safe: str, row: dict) -> None:
    with open(_table_path(safe), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def compact_args(value, limit: int = 80) -> str:
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        s = str(value)
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _record_matches(rec, needle: str) -> bool:
    values = rec.values() if isinstance(rec, dict) else [rec]
    return any(needle in str(v).lower() for v in values)


# --------------------------------------------------------------------------- #
# Handlers (keyed by the `handler` field in automation.config.json)
# --------------------------------------------------------------------------- #
@register("read_document")
def read_document(args: dict) -> dict:
    """Read a file's text from the workspace."""
    path = (args or {}).get("path")
    if not path:
        return {"content": "Error: 'path' is required."}
    target = (_ws() / str(path)).resolve()
    if not _within_ws(target):
        return {"content": f"Error: '{path}' is outside the workspace."}
    try:
        if not target.is_file():
            return {"content": f"Error: no file at '{path}'."}
        return {"content": target.read_text(encoding="utf-8", errors="replace")}
    except Exception as exc:
        return {"content": f"Error reading '{path}': {exc}"}


@register("list_workspace")
def list_workspace(args: dict) -> dict:
    """List files in the workspace (default inbox/**)."""
    pattern = (args or {}).get("pattern") or "inbox/**"
    glob = _normalize_glob(str(pattern))
    ws = _ws()
    try:
        matches = sorted(_rel(p) for p in ws.glob(glob) if p.is_file())
    except Exception as exc:
        return {"content": f"Error listing '{pattern}': {exc}"}
    return {"content": "\n".join(matches) if matches else f"No files matched '{pattern}'."}


@register("write_deliverable")
def write_deliverable(args: dict) -> dict:
    """Write a finished deliverable into <workspace>/output/."""
    filename = (args or {}).get("filename")
    content = (args or {}).get("content")
    if not filename:
        return {"content": "Error: 'filename' is required."}
    if content is None:
        return {"content": "Error: 'content' is required."}
    name = _safe_name(filename)
    if not name:
        return {"content": f"Error: '{filename}' is not a valid file name."}
    out = _output_dir() / name
    body = str(content)
    try:
        out.write_text(body, encoding="utf-8")
    except Exception as exc:
        return {"content": f"Error writing '{name}': {exc}"}
    return {"content": f"Wrote {len(body)} characters to {_rel(out)}."}


@register("save_record")
def save_record(args: dict) -> dict:
    """Create a record in a table. Returns the new record id."""
    table = (args or {}).get("table")
    data = (args or {}).get("data")
    if not table:
        return {"content": "Error: 'table' is required."}
    if not isinstance(data, dict):
        return {"content": "Error: 'data' must be an object of key/value pairs."}
    safe = _safe_table(table)
    if not safe:
        return {"content": f"Error: '{table}' is not a valid table name."}
    rid = _new_id()
    record = {"id": rid, **data, "created_at": _now(), "updated_at": _now()}
    try:
        _append_row(safe, record)
    except Exception as exc:
        return {"content": f"Error saving to '{safe}': {exc}"}
    return {"content": f"Created record {rid} in '{safe}'."}


@register("lookup_record")
def lookup_record(args: dict) -> dict:
    """Read records in a table; optional case-insensitive substring filter. Includes ids."""
    table = (args or {}).get("table")
    query = (args or {}).get("query") or ""
    if not table:
        return {"content": "Error: 'table' is required."}
    safe = _safe_table(table)
    if not _table_path(safe).is_file():
        return {"content": f"No records: table '{safe}' does not exist yet."}
    needle = str(query).strip().lower()
    try:
        rows = [r for r in _read_table(safe) if not needle or _record_matches(r, needle)]
    except Exception as exc:
        return {"content": f"Error reading '{safe}': {exc}"}
    if not rows:
        return {"content": f"No records in '{safe}' matched '{query}'."}
    body = json.dumps(rows, ensure_ascii=False, indent=2)
    return {"content": f"Found {len(rows)} record(s) in '{safe}':\n{body}"}


@register("update_record")
def update_record(args: dict) -> dict:
    """Update fields of an existing record by id (merge). Use lookup_record to find the id."""
    table = (args or {}).get("table")
    rid = (args or {}).get("id")
    data = (args or {}).get("data")
    if not table or not rid:
        return {"content": "Error: 'table' and 'id' are required."}
    if not isinstance(data, dict):
        return {"content": "Error: 'data' must be an object of fields to update."}
    safe = _safe_table(table)
    rows = _read_table(safe)
    found = False
    for r in rows:
        if r.get("id") == rid:
            r.update(data)
            r["id"] = rid
            r["updated_at"] = _now()
            found = True
            break
    if not found:
        return {"content": f"No record with id '{rid}' in '{safe}'."}
    try:
        _write_table(safe, rows)
    except Exception as exc:
        return {"content": f"Error updating '{safe}': {exc}"}
    return {"content": f"Updated record {rid} in '{safe}'."}


@register("delete_record")
def delete_record(args: dict) -> dict:
    """Delete a record by id. Irreversible — confirm with the user before calling."""
    table = (args or {}).get("table")
    rid = (args or {}).get("id")
    if not table or not rid:
        return {"content": "Error: 'table' and 'id' are required."}
    safe = _safe_table(table)
    rows = _read_table(safe)
    kept = [r for r in rows if r.get("id") != rid]
    if len(kept) == len(rows):
        return {"content": f"No record with id '{rid}' in '{safe}'."}
    try:
        _write_table(safe, kept)
    except Exception as exc:
        return {"content": f"Error deleting from '{safe}': {exc}"}
    return {"content": f"Deleted record {rid} from '{safe}'."}


@register("create_task")
def create_task(args: dict) -> dict:
    """Create a follow-up task (stored in the 'tasks' table) with an optional due date."""
    title = (args or {}).get("title")
    if not title:
        return {"content": "Error: 'title' is required."}
    rid = _new_id()
    record = {
        "id": rid,
        "title": str(title),
        "due": (args or {}).get("due"),
        "notes": (args or {}).get("notes"),
        "status": "open",
        "created_at": _now(),
        "updated_at": _now(),
    }
    try:
        _append_row("tasks", record)
    except Exception as exc:
        return {"content": f"Error creating task: {exc}"}
    due = f" (due {record['due']})" if record["due"] else ""
    return {"content": f"Created task {rid}: {record['title']}{due}"}


# --------------------------------------------------------------------------- #
# Domain handlers (scaffold.py injects @register(...) stubs below this marker)
# --------------------------------------------------------------------------- #
# >>> SCAFFOLD:DOMAIN_TOOLS <<<


# --------------------------------------------------------------------------- #
# Config <-> registry glue (shared by both engines)
# --------------------------------------------------------------------------- #
def build_anthropic_tools(config: dict) -> list[dict]:
    tools = []
    for spec in config.get("tools", []):
        tools.append({
            "name": spec["name"],
            "description": spec.get("description", ""),
            "input_schema": spec.get("input_schema") or {"type": "object", "properties": {}},
        })
    return tools


def name_to_handler(config: dict, tool_name: str) -> str | None:
    for spec in config.get("tools", []):
        if spec.get("name") == tool_name:
            return spec.get("handler", tool_name)
    return None


def validate_registry(config: dict) -> None:
    missing = []
    for spec in config.get("tools", []):
        handler = spec.get("handler", spec.get("name"))
        if handler not in REGISTRY:
            missing.append(f"  - tool '{spec.get('name')}' needs handler '{handler}' (not registered)")
    if missing:
        raise ValueError(
            "Tool registry is missing handlers required by automation.config.json:\n"
            + "\n".join(missing)
            + f"\n\nRegistered handlers: {sorted(REGISTRY)}"
        )
