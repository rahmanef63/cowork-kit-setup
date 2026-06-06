"""
automation/cli.py
=================
Command-line entry point. Subcommands:

    run "<task>"        one-shot task
    workflow <name>     run a named workflow from the config
    tools               list the configured tools
    doctor              check key, config, registry, and workspace

Global flags (on run / workflow): --engine {direct,agent}, --stream, --model.
The `direct` engine is the default and needs only the `anthropic` package.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .config import find_config, load_config, load_env, workspace_root
from .tools import REGISTRY, build_anthropic_tools, validate_registry


def _require_key() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    print(
        "ANTHROPIC_API_KEY is not set.\n"
        "  - copy local/.env.example to local/.env and add your key, or\n"
        "  - set it in your shell:\n"
        "      Windows (PowerShell):  $env:ANTHROPIC_API_KEY = 'sk-ant-...'\n"
        "      macOS/Linux:           export ANTHROPIC_API_KEY=sk-ant-...\n"
        "Create a key at https://console.anthropic.com/.",
        file=sys.stderr,
    )
    return False


def _load_or_report():
    try:
        return load_config()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return None


def _run_engine(task: str, config: dict, engine: str, model, stream: bool) -> str:
    if engine == "agent":
        from .agent_sdk_runner import run_agent

        # The agent engine streams its messages inline; --stream is implied.
        return run_agent(task, config, model=model)
    from .direct_runner import run_direct

    return run_direct(task, config, model=model, stream=stream)


def _streamed(args) -> bool:
    return bool(getattr(args, "stream", False)) or getattr(args, "engine", "") == "agent"


def _print_result(args, result: str) -> None:
    # In streaming/agent mode the body is already on screen; don't repeat it.
    if not _streamed(args) and result:
        print("\n" + result)


def cmd_run(args) -> int:
    config = _load_or_report()
    if config is None:
        return 2
    if not _require_key():
        return 2
    print(f"[engine: {args.engine} | model: {args.model or config.get('model')}]")
    result = _run_engine(args.task, config, args.engine, args.model, args.stream)
    _print_result(args, result)
    return 0


def cmd_workflow(args) -> int:
    config = _load_or_report()
    if config is None:
        return 2
    workflows = config.get("workflows", [])
    wf = next((w for w in workflows if w.get("name") == args.name), None)
    if wf is None:
        available = ", ".join(w.get("name", "?") for w in workflows) or "(none)"
        print(
            f"No workflow named '{args.name}'. Available: {available}", file=sys.stderr
        )
        return 2
    if not _require_key():
        return 2
    print(f"[workflow: {wf['name']} | engine: {args.engine}]")
    if wf.get("description"):
        print(wf["description"])
    result = _run_engine(
        wf.get("prompt", ""), config, args.engine, args.model, args.stream
    )
    _print_result(args, result)
    return 0


def cmd_tools(args) -> int:
    config = _load_or_report()
    if config is None:
        return 2
    tools = build_anthropic_tools(config)
    if not tools:
        print("No tools are defined in automation.config.json.")
        return 0
    print(f"{len(tools)} tool(s):\n")
    for t in tools:
        print(f"  {t['name']}")
        if t.get("description"):
            print(f"      {t['description']}")
    return 0


def cmd_doctor(args) -> int:
    ok = True

    key = os.environ.get("ANTHROPIC_API_KEY")
    print(f"ANTHROPIC_API_KEY : {'set' if key else 'MISSING'}")
    ok = ok and bool(key)

    config = None
    try:
        path = find_config()
        config = load_config()
        print(f"config            : OK  ({path})")
    except Exception as exc:
        print(f"config            : FAILED  - {exc}")
        ok = False

    if config is not None:
        try:
            validate_registry(config)
            print(
                "registry          : OK  "
                f"({len(REGISTRY)} handlers, {len(config.get('tools', []))} tools in config)"
            )
        except Exception as exc:
            print(f"registry          : FAILED  - {exc}")
            ok = False

    print(f"workspace         : {workspace_root()}")

    try:
        import anthropic  # noqa: F401

        print("engine 'direct'   : available (anthropic)")
    except Exception:
        print("engine 'direct'   : MISSING - pip install anthropic")
        ok = False

    try:
        import claude_agent_sdk  # noqa: F401

        print("engine 'agent'    : available (claude-agent-sdk)")
    except Exception:
        print(
            "engine 'agent'    : not installed (optional) - pip install claude-agent-sdk"
        )

    print()
    print("doctor: " + ("all good" if ok else "issues found (see above)"))
    return 0 if ok else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="automation",
        description="Run the automation defined by automation.config.json.",
    )
    parser.add_argument(
        "--version", action="version", version=f"automation-local {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # Shared engine flags for run / workflow.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--engine",
        choices=["direct", "agent"],
        default="direct",
        help="Execution engine (default: direct).",
    )
    common.add_argument(
        "--stream",
        action="store_true",
        help="Stream tokens as they arrive (direct engine).",
    )
    common.add_argument("--model", default=None, help="Override the model from config.")

    p_run = sub.add_parser("run", parents=[common], help="Run a one-shot task.")
    p_run.add_argument("task", help="The task instruction (quote it).")
    p_run.set_defaults(func=cmd_run)

    p_wf = sub.add_parser(
        "workflow", parents=[common], help="Run a named workflow from the config."
    )
    p_wf.add_argument("name", help="Workflow name (see automation.config.json).")
    p_wf.set_defaults(func=cmd_workflow)

    p_tools = sub.add_parser("tools", help="List the configured tools.")
    p_tools.set_defaults(func=cmd_tools)

    p_doctor = sub.add_parser(
        "doctor", help="Check key, config, registry, and workspace."
    )
    p_doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv=None) -> int:
    """CLI entry point. Returns a process exit code."""
    load_env()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
