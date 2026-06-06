"""
automation/direct_runner.py
===========================
The dependable default engine: a transparent, manual tool-use loop built only on
the ``anthropic`` SDK (no agent framework required). It sends the task, executes
any tool calls through the shared REGISTRY, feeds the results back, and repeats
until the model stops asking for tools. Supports token streaming via --stream.
"""
from __future__ import annotations

from .tools import (
    REGISTRY,
    build_anthropic_tools,
    compact_args,
    name_to_handler,
)

DEFAULT_MAX_TOKENS = 2048
MAX_TURNS = 16  # safety stop to avoid runaway tool loops


def _dispatch(config: dict, tool_name: str, tool_input: dict) -> str:
    """Run one tool call through the registry, never raising."""
    handler_key = name_to_handler(config, tool_name)
    fn = REGISTRY.get(handler_key) if handler_key else None
    if fn is None:
        return f"Error: no handler registered for tool '{tool_name}'."
    try:
        out = fn(tool_input or {})
    except Exception as exc:  # handlers shouldn't raise, but stay safe
        return f"Error in tool '{tool_name}': {exc}"
    return str(out.get("content", "")) if isinstance(out, dict) else str(out)


def _stream_once(client, kwargs):
    """Stream one assistant turn to stdout; return (text, content_blocks, stop_reason)."""
    printed = []
    with client.messages.stream(**kwargs) as stream:
        for chunk in stream.text_stream:
            print(chunk, end="", flush=True)
            printed.append(chunk)
        final = stream.get_final_message()
    print()  # newline after the streamed text
    return "".join(printed), final.content, final.stop_reason


def run_direct(
    task: str, config: dict, model: str | None = None, stream: bool = False
) -> str:
    """Run `task` to completion and return the final assistant text."""
    # Imported here so a missing/misconfigured SDK surfaces as a clean error
    # rather than breaking `import` of the whole CLI.
    from anthropic import Anthropic

    client = Anthropic()  # reads ANTHROPIC_API_KEY
    model = model or config.get("model")
    tools = build_anthropic_tools(config)
    system = config.get("systemPrompt", "")
    messages: list[dict] = [{"role": "user", "content": task}]

    for _ in range(MAX_TURNS):
        kwargs = {"model": model, "max_tokens": DEFAULT_MAX_TOKENS, "messages": messages}
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        if stream:
            text, content, stop_reason = _stream_once(client, kwargs)
        else:
            resp = client.messages.create(**kwargs)
            content = resp.content
            stop_reason = resp.stop_reason
            text = "".join(
                b.text for b in content if getattr(b, "type", None) == "text"
            )

        if stop_reason != "tool_use":
            return text.strip()

        # Echo the assistant turn back, run the requested tools, return results.
        messages.append({"role": "assistant", "content": content})
        results = []
        for block in content:
            if getattr(block, "type", None) == "tool_use":
                print(f"  -> tool: {block.name}({compact_args(block.input)})")
                result_text = _dispatch(config, block.name, block.input)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    }
                )
        messages.append({"role": "user", "content": results})

    return (
        "Stopped: reached the maximum number of tool-use turns "
        f"({MAX_TURNS}) without a final answer."
    )
