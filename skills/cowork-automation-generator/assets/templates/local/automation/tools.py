"""
automation/tools.py
===================
The shared tool registry: deterministic, offline-safe, pure-Python handlers that
both engines (direct + agent) dispatch through. Each handler takes a single dict
of arguments and returns ``{"content": "<string the model sees>"}``. Handlers
never raise into the agent loop -- they return friendly error strings instead.

The registry is keyed by the ``handler`` name in automation.config.json. Startup
validation (``validate_registry``) fails loudly if the config references a
handler that isn't implemented here, keeping config and code honest.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import workspace_root

# handler key -> callable(args: dict) -> {"content": str}
REGISTRY: dict[str, Callable[[dict], dict]] = {}


def register(name: str):
    """Decorator: add a handler to the registry under ``name``."""

    def deco(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        REGISTRY[name] = fn
        return fn

    return deco


# --------------------------------------------------------------------------- #
# Workspace + formatting helpers
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
    """A bare filename, stripped of any directory components."""
    return Path(str(name)).name


def _safe_table(table: str) -> str:
    """A flat, filesystem-safe table name (alnum, dash, underscore)."""
    cleaned = "".join(c for c in str(table) if c.isalnum() or c in ("-", "_"))
    return cleaned.strip("-_")


def _normalize_glob(pattern: str) -> str:
    # pathlib's "**" matches directories only; callers mean "everything under
    # here", so expand a trailing ** into **/* to actually reach the files.
    if pattern == "**":
        return "**/*"
    if pattern.endswith("/**"):
        return pattern + "/*"
    return pattern


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_args(value, limit: int = 80) -> str:
    """One-line, length-capped rendering of tool args for console logging."""
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        s = str(value)
    return s if len(s) <= limit else s[: limit - 3] + "..."


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
        return {
            "content": f"Error: '{path}' is outside the workspace; only files under {_ws()} can be read."
        }
    try:
        if not target.is_file():
            return {"content": f"Error: no file at '{path}' (looked in {_ws()})."}
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"content": f"Error reading '{path}': {exc}"}
    return {"content": text}


@register("list_workspace")
def list_workspace(args: dict) -> dict:
    """List files in the workspace, optionally filtered by a glob (default inbox/**)."""
    pattern = (args or {}).get("pattern") or "inbox/**"
    glob = _normalize_glob(str(pattern))
    ws = _ws()
    try:
        matches = sorted(_rel(p) for p in ws.glob(glob) if p.is_file())
    except Exception as exc:
        return {"content": f"Error listing files with pattern '{pattern}': {exc}"}
    if not matches:
        return {"content": f"No files matched '{pattern}' under {ws}."}
    return {"content": "\n".join(matches)}


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
    """Append a JSON object as one line to <workspace>/.data/<table>.jsonl."""
    table = (args or {}).get("table")
    data = (args or {}).get("data")
    if not table:
        return {"content": "Error: 'table' is required."}
    if not isinstance(data, dict):
        return {"content": "Error: 'data' must be an object of key/value pairs."}
    safe = _safe_table(table)
    if not safe:
        return {"content": f"Error: '{table}' is not a valid table name."}
    record = dict(data)
    record.setdefault("_saved_at", _now())
    path = _data_dir() / f"{safe}.jsonl"
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        return {"content": f"Error saving to '{safe}': {exc}"}
    return {"content": f"Saved 1 record to '{safe}' ({_rel(path)})."}


@register("lookup_record")
def lookup_record(args: dict) -> dict:
    """Return records in a table whose any field contains `query` (case-insensitive)."""
    table = (args or {}).get("table")
    query = (args or {}).get("query") or ""
    if not table:
        return {"content": "Error: 'table' is required."}
    safe = _safe_table(table)
    path = _data_dir() / f"{safe}.jsonl"
    if not path.is_file():
        return {"content": f"No records: table '{safe}' does not exist yet."}
    needle = str(query).strip().lower()
    matches: list = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not needle or _record_matches(rec, needle):
                    matches.append(rec)
    except Exception as exc:
        return {"content": f"Error reading '{safe}': {exc}"}
    if not matches:
        return {"content": f"No records in '{safe}' matched '{query}'."}
    body = json.dumps(matches, ensure_ascii=False, indent=2)
    return {"content": f"Found {len(matches)} record(s) in '{safe}':\n{body}"}


def _record_matches(rec, needle: str) -> bool:
    values = rec.values() if isinstance(rec, dict) else [rec]
    return any(needle in str(v).lower() for v in values)


@register("create_task")
def create_task(args: dict) -> dict:
    """Append a task record to <workspace>/.data/tasks.jsonl."""
    title = (args or {}).get("title")
    if not title:
        return {"content": "Error: 'title' is required."}
    record = {
        "title": str(title),
        "due": (args or {}).get("due"),
        "notes": (args or {}).get("notes"),
        "status": "open",
        "created_at": _now(),
    }
    path = _data_dir() / "tasks.jsonl"
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        return {"content": f"Error creating task: {exc}"}
    due = f" (due {record['due']})" if record["due"] else ""
    return {"content": f"Created task: {record['title']}{due}"}


# --------------------------------------------------------------------------- #
# Domain handlers (scaffold.py injects @register(...) stubs below this marker)
# --------------------------------------------------------------------------- #
# >>> SCAFFOLD:DOMAIN_TOOLS <<<


# --------------------------------------------------------------------------- #
# Config <-> registry glue (shared by both engines)
# --------------------------------------------------------------------------- #
def build_anthropic_tools(config: dict) -> list[dict]:
    """Map config.tools[*] -> the Anthropic `tools` array shape."""
    tools = []
    for spec in config.get("tools", []):
        tools.append(
            {
                "name": spec["name"],
                "description": spec.get("description", ""),
                "input_schema": spec.get("input_schema")
                or {"type": "object", "properties": {}},
            }
        )
    return tools


def name_to_handler(config: dict, tool_name: str) -> str | None:
    """Map a tool's public `name` -> its registry `handler` key (or None)."""
    for spec in config.get("tools", []):
        if spec.get("name") == tool_name:
            return spec.get("handler", tool_name)
    return None


def validate_registry(config: dict) -> None:
    """Raise ValueError listing any config tool whose handler is unregistered."""
    missing = []
    for spec in config.get("tools", []):
        handler = spec.get("handler", spec.get("name"))
        if handler not in REGISTRY:
            missing.append(
                f"  - tool '{spec.get('name')}' needs handler '{handler}' (not registered)"
            )
    if missing:
        raise ValueError(
            "Tool registry is missing handlers required by automation.config.json:\n"
            + "\n".join(missing)
            + f"\n\nRegistered handlers: {sorted(REGISTRY)}"
        )
