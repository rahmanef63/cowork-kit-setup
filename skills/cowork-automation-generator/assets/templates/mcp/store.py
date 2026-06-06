"""
mcp/store.py — pure-Python CRUD over the project's local datastore.
No third-party deps. Same on-disk format as the CLI and what the website reads:

  <workspace>/.data/<table>.jsonl   one JSON object per line, each with "id"
  <workspace>/output/<file>         documents / deliverables

Workspace = $AUTOMATION_WORKSPACE, else the project root (parent of this mcp/ dir).
This is what makes "Claude controls CRUD to the website": the MCP, the website,
and the CLI all read/write the same files.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


def workspace() -> Path:
    env = os.environ.get("AUTOMATION_WORKSPACE")
    return Path(env).resolve() if env else Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    d = workspace() / ".data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _output_dir() -> Path:
    d = workspace() / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _safe_table(table: str) -> str:
    return "".join(c for c in str(table) if c.isalnum() or c in ("-", "_")).strip("-_")


def _safe_name(name: str) -> str:
    return Path(str(name)).name


def _path(safe: str) -> Path:
    return _data_dir() / f"{safe}.jsonl"


def _read(safe: str) -> list[dict]:
    p = _path(safe)
    if not p.is_file():
        return []
    rows = []
    for line in p.read_text("utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def _write(safe: str, rows: list[dict]) -> None:
    _path(safe).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")


# --------------------------------------------------------------------------- #
# Records CRUD
# --------------------------------------------------------------------------- #
def list_tables() -> list[str]:
    return sorted(p.stem for p in _data_dir().glob("*.jsonl"))


def list_records(table: str, query: str = "") -> list[dict]:
    safe = _safe_table(table)
    needle = str(query or "").strip().lower()
    rows = _read(safe)
    if not needle:
        return rows
    return [r for r in rows if any(needle in str(v).lower() for v in r.values())]


def get_record(table: str, record_id: str) -> dict | None:
    for r in _read(_safe_table(table)):
        if r.get("id") == record_id:
            return r
    return None


def create_record(table: str, data: dict) -> dict:
    safe = _safe_table(table)
    if not safe:
        raise ValueError("invalid table name")
    if not isinstance(data, dict):
        raise ValueError("data must be an object")
    rows = _read(safe)
    rec = {"id": _new_id(), **data, "created_at": _now(), "updated_at": _now()}
    rows.append(rec)
    _write(safe, rows)
    return rec


def update_record(table: str, record_id: str, data: dict) -> dict | None:
    safe = _safe_table(table)
    rows = _read(safe)
    out = None
    for r in rows:
        if r.get("id") == record_id:
            r.update(data)
            r["id"] = record_id
            r["updated_at"] = _now()
            out = r
            break
    if out is not None:
        _write(safe, rows)
    return out


def delete_record(table: str, record_id: str) -> bool:
    safe = _safe_table(table)
    rows = _read(safe)
    kept = [r for r in rows if r.get("id") != record_id]
    if len(kept) == len(rows):
        return False
    _write(safe, kept)
    return True


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #
def list_documents() -> list[str]:
    out = _output_dir()
    return sorted(p.name for p in out.glob("*") if p.is_file())


def read_doc(name: str) -> str | None:
    p = _output_dir() / _safe_name(name)
    return p.read_text("utf-8", errors="replace") if p.is_file() else None


def write_doc(name: str, content: str) -> str:
    safe = _safe_name(name)
    if not safe:
        raise ValueError("invalid file name")
    (_output_dir() / safe).write_text(str(content), "utf-8")
    return f"output/{safe}"
