"""
automation/config.py
=====================
Locate and load the shared `automation.config.json` contract, and resolve the
workspace root. The config is the single source of truth shared by the Python
CLI and the webapp, so resolution is deliberately forgiving:

    explicit path  ->  AUTOMATION_CONFIG env  ->  search upward from cwd
                   ->  search upward from this package directory.

Also loads a local `.env` (when python-dotenv is installed).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_FILENAME = "automation.config.json"


def load_env() -> None:
    """Load environment variables from a nearby `.env` file if python-dotenv is
    available. Searches upward from the current working directory. No-op when the
    package is missing or no `.env` exists."""
    try:
        from dotenv import find_dotenv, load_dotenv
    except Exception:
        return
    path = find_dotenv(usecwd=True)
    if path:
        load_dotenv(path)


def workspace_root() -> Path:
    """The directory tools read from and write to. Override with
    AUTOMATION_WORKSPACE; defaults to the current working directory."""
    raw = os.environ.get("AUTOMATION_WORKSPACE") or os.getcwd()
    return Path(raw).expanduser().resolve()


def _search_upward(start: Path, filename: str) -> Path | None:
    start = start.resolve()
    for parent in (start, *start.parents):
        candidate = parent / filename
        if candidate.is_file():
            return candidate
    return None


def find_config(path: str | os.PathLike | None = None) -> Path:
    """Resolve the path to automation.config.json, raising FileNotFoundError with
    a clear message when it cannot be found."""
    if path:
        p = Path(path).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"Config not found at: {p}")
        return p.resolve()

    env = os.environ.get("AUTOMATION_CONFIG")
    if env:
        p = Path(env).expanduser()
        if not p.is_file():
            raise FileNotFoundError(
                f"AUTOMATION_CONFIG points to '{p}', which does not exist."
            )
        return p.resolve()

    found = _search_upward(Path.cwd(), CONFIG_FILENAME)
    if found:
        return found

    found = _search_upward(Path(__file__).parent, CONFIG_FILENAME)
    if found:
        return found

    raise FileNotFoundError(
        f"Could not locate '{CONFIG_FILENAME}'. Set AUTOMATION_CONFIG to its "
        f"path, or run from inside the automation repo. Searched upward from "
        f"'{Path.cwd()}' and '{Path(__file__).parent}'."
    )


def load_config(path: str | os.PathLike | None = None) -> dict:
    """Load and parse the config file into a dict."""
    cfg_path = find_config(path)
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"'{cfg_path}' is not valid JSON: {exc}") from exc
