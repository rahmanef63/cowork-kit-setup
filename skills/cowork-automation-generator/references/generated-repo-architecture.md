# Generated Repo Architecture (Canonical Contract)

This is the spec that every generated automation repo follows. The local Python
runtime and the Next.js + Convex webapp are two front-ends over **one shared
contract**: `automation.config.json`. Implement against this document exactly so
the two languages stay in lockstep.

## 1. Single source of truth: `automation.config.json`

Lives at the repo root. Both runtimes read it. The scaffolder generates it per
domain. Shape:

```jsonc
{
  "domain": "real-estate",                // kebab-case slug
  "displayName": "Real Estate Agency",
  "description": "One-line description of the operation being automated.",
  "version": "0.1.0",
  "model": "claude-opus-4-8",            // default model for both runtimes
  "systemPrompt": "You are an automation agent for ...",
  "coworkCapabilities": ["files", "web", "connectors", "scheduled"],
  "suggestedConnectors": ["gmail", "google-calendar"],   // MCP connectors to enable in Cowork
  "bestPractices": [                       // domain-tuned guidance (shown in README + docs/)
    { "title": "...", "detail": "..." }
  ],
  "tools": [
    {
      "name": "draft_listing",            // snake_case; becomes the Anthropic tool name
      "description": "When to use it + what it does. Write it for the model.",
      "handler": "draft_listing",         // key into the language registry
      "input_schema": {                    // JSON Schema (Anthropic `input_schema`)
        "type": "object",
        "properties": {
          "address": { "type": "string", "description": "Property address" },
          "features": { "type": "array", "items": { "type": "string" } }
        },
        "required": ["address"]
      }
    }
  ],
  "workflows": [                           // higher-level recipes (used by CLI subcommands + scheduled tasks)
    {
      "name": "weekly-lead-followup",
      "description": "...",
      "prompt": "Natural-language instruction the agent runs for this workflow.",
      "schedule": "0 8 * * 1"             // optional cron; null if on-demand
    }
  ]
}
```

Rules:
- Tool `name` and `handler` are snake_case and identical across Python and TS.
- `input_schema` is plain JSON Schema so it drops straight into the Anthropic
  `tools` array in both languages — no translation.
- Every tool listed MUST have a handler registered in BOTH `local/automation/tools.py`
  and `web/lib/tools.ts`. Startup validation fails loudly if one is missing — this
  is what keeps the two languages honest.

## 2. The tool registry pattern (both languages, mirrored)

Python (`local/automation/tools.py`):

```python
REGISTRY: dict[str, Callable[[dict], dict]] = {}

def register(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco

@register("draft_listing")
def draft_listing(args: dict) -> dict:
    # returns {"content": "<string the model sees as tool_result>"}
    ...
```

TypeScript (`web/lib/tools.ts`):

```ts
export type ToolHandler = (args: Record<string, unknown>) => Promise<string> | string;
export const registry: Record<string, ToolHandler> = {
  draft_listing: async (args) => { /* return string */ },
};
```

Both expose a `buildAnthropicTools(config)` helper that maps
`config.tools[*]` → `{ name, description, input_schema }`.

A `validateRegistry(config)` function asserts every `config.tools[*].handler`
exists in the registry and throws listing any gaps. Call it at startup.

## 3. Local runtime — two interchangeable engines

Same tools, same config, two ways to run the loop. CLI flag `--engine` picks one.

### 3a. `agent_sdk_runner.py` — Claude Agent SDK (`claude-agent-sdk`)
Full agent loop, can also load Cowork skills/MCP. Wrap each registry function as
an Agent SDK tool and expose them through an in-process MCP server.

```python
from claude_agent_sdk import query, tool, create_sdk_mcp_server, ClaudeAgentOptions

def build_sdk_tools(config):
    sdk_tools = []
    for spec in config["tools"]:
        fn = REGISTRY[spec["handler"]]
        @tool(spec["name"], spec["description"], spec["input_schema"])
        async def _t(args, _fn=fn):
            out = _fn(args)
            return {"content": [{"type": "text", "text": out["content"]}]}
        sdk_tools.append(_t)
    return sdk_tools

server = create_sdk_mcp_server(name="automation", version="0.1.0", tools=build_sdk_tools(config))
options = ClaudeAgentOptions(
    mcp_servers=[server],
    allowed_tools=[f"mcp__automation__{t['name']}" for t in config["tools"]],
    system_prompt=config["systemPrompt"],
)
# await query(prompt=..., options=options); async for message in ...:
```
Note: Agent SDK namespaces tools as `mcp__<server>__<tool>`. API key via `ANTHROPIC_API_KEY`.

### 3b. `direct_runner.py` — Anthropic SDK (`anthropic`), manual loop
Lighter, fully transparent, no agent framework. Canonical loop:

```python
from anthropic import Anthropic
client = Anthropic()  # ANTHROPIC_API_KEY
tools = build_anthropic_tools(config)
messages = [{"role": "user", "content": prompt}]
while True:
    resp = client.messages.create(model=config["model"], max_tokens=2048, tools=tools, messages=messages)
    if resp.stop_reason != "tool_use":
        return "".join(b.text for b in resp.content if b.type == "text")
    messages.append({"role": "assistant", "content": resp.content})
    results = []
    for b in resp.content:
        if b.type == "tool_use":
            out = REGISTRY[name_to_handler(config, b.name)](b.input)
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out["content"]})
    messages.append({"role": "user", "content": results})
```
A `--stream` flag uses `client.messages.stream(...)` for token output.

### 3c. `cli.py`
`run "<task>"` (one-shot), `workflow <name>` (runs a config workflow), `tools`
(lists tools), `doctor` (validates config + registry + env). `--engine agent|direct`,
`--stream`, `--model`. Uses argparse, no heavy deps.

## 4. Webapp runtime — Next.js + Convex + BYOK

The webapp is the same agent, but the **user supplies their own Anthropic API key**
(BYOK) in the browser. Never ship a server key.

- `web/lib/tools.ts` — the TS mirror of the registry (same tool names/handlers).
- `web/convex/schema.ts` — tables: `apiKeys` (per-session BYOK key), `runs`,
  `messages` (for streaming via DB polling).
- `web/convex/agent.ts` — a Convex **action** running the same tool loop with
  `new Anthropic({ apiKey })`. Because Convex `action()` cannot stream over HTTP,
  stream by writing assistant deltas into the `messages` table; the client
  subscribes with `useQuery` (live). An `http.ts` `httpAction` variant with
  `ReadableStream` is included as an alternative for true SSE.
- `web/convex/keys.ts` — store/clear the BYOK key. Document plainly that for a
  real deployment the key should be encrypted at rest / kept session-scoped; for
  the template it is stored per session and never logged.
- `web/app/page.tsx` — key entry, task box, live transcript, tool-call display.

BYOK flow: user pastes key → stored in Convex keyed by an anonymous session id →
action reads it at request time → calls Anthropic → streams deltas into `messages`
→ UI renders live → key can be cleared.

## 5. Repo layout produced by the scaffolder

```
<domain>-automation/
├── automation.config.json        # the contract (generated per domain)
├── README.md                     # quickstart for BOTH modes + best practices
├── docs/
│   ├── best-practices.md         # domain-tuned Cowork best practices
│   └── cowork-setup.md           # how to wire this up inside Cowork (skill + connectors + schedule)
├── local/                        # Python CLI (both engines)
│   ├── pyproject.toml
│   ├── .env.example
│   └── automation/{__init__,config,tools,runners...}.py
├── web/                          # Next.js + Convex + BYOK
│   ├── package.json
│   ├── convex/{schema,agent,keys,http}.ts
│   ├── lib/tools.ts
│   └── app/{page,layout}.tsx
└── .cowork/                      # optional: drop-in Cowork skill for this domain
    └── skills/<domain>-ops/SKILL.md
```

The `.cowork/skills/<domain>-ops/SKILL.md` makes the generated repo itself usable
**inside Cowork** — closing the loop: Cowork generates an automation repo whose
automations can also be invoked from Cowork.
