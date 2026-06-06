"""
automation/agent_sdk_runner.py
==============================
The richer engine: runs the same tools through the Claude Agent SDK's in-process
MCP server and full agent loop. The SDK is imported lazily so the CLI (and the
default ``direct`` engine) keep working even when ``claude-agent-sdk`` isn't
installed. Exposes an async runner plus a synchronous wrapper.
"""
from __future__ import annotations

import asyncio

from .tools import REGISTRY, compact_args, validate_registry


async def run_agent_async(task: str, config: dict, model: str | None = None) -> str:
    """Run `task` through the Agent SDK and return the final assistant text."""
    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            create_sdk_mcp_server,
            query,
            tool,
        )
    except ImportError as exc:
        raise RuntimeError(
            "The 'agent' engine needs the 'claude-agent-sdk' package (plus the "
            "Claude Code CLI it drives). Install it with "
            "`pip install claude-agent-sdk`, or use `--engine direct`."
        ) from exc

    validate_registry(config)

    # Wrap each registry handler as an SDK tool. The `_fn=fn` default-argument
    # binding captures the correct handler per iteration -- without it, every
    # generated tool would close over the loop's final `fn` (late-binding bug).
    sdk_tools = []
    for spec in config.get("tools", []):
        fn = REGISTRY.get(spec.get("handler", spec["name"]))
        if fn is None:
            continue
        schema = spec.get("input_schema") or {"type": "object", "properties": {}}

        @tool(spec["name"], spec.get("description", ""), schema)
        async def _sdk_tool(args, _fn=fn):
            try:
                out = _fn(args or {})
                text = (
                    str(out.get("content", "")) if isinstance(out, dict) else str(out)
                )
            except Exception as exc:  # stay safe inside the agent loop
                text = f"Error: {exc}"
            return {"content": [{"type": "text", "text": text}]}

        sdk_tools.append(_sdk_tool)

    # In-process MCP server. The dict key ("automation") forms the tool
    # namespace the model sees: mcp__automation__<tool>.
    server = create_sdk_mcp_server(name="automation", version="0.1.0", tools=sdk_tools)
    options = ClaudeAgentOptions(
        mcp_servers={"automation": server},
        allowed_tools=[
            f"mcp__automation__{spec['name']}" for spec in config.get("tools", [])
        ],
        system_prompt=config.get("systemPrompt", ""),
        model=model or config.get("model"),
        # Auto-approve tool calls for unattended runs (no interactive prompts).
        permission_mode="bypassPermissions",
    )

    final_parts: list[str] = []
    final_result: str | None = None
    async for message in query(prompt=task, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, end="", flush=True)
                    final_parts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    # Tools are namespaced (mcp__automation__x); show the bare name.
                    name = block.name.split("__")[-1]
                    print(f"\n  -> tool: {name}({compact_args(block.input)})")
        elif isinstance(message, ResultMessage):
            final_result = message.result

    print()
    if final_result:
        return final_result.strip()
    return "".join(final_parts).strip()


def run_agent(task: str, config: dict, model: str | None = None) -> str:
    """Synchronous wrapper around :func:`run_agent_async`."""
    return asyncio.run(run_agent_async(task, config, model=model))
