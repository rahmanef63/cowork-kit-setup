# Local automation CLI

A small Python CLI that runs the automation described by the repo's
`automation.config.json` (one level up from this folder). Same config, same
tools, two interchangeable engines:

- **direct** (default) - a transparent manual tool-use loop on the `anthropic`
  SDK. Minimal deps, fully predictable, works even if the Agent SDK isn't installed.
- **agent** - the same tools run through the **Claude Agent SDK** in-process MCP
  server and full agent loop.

## Install

From this `local/` directory:

```bash
pip install -e .
# or, with uv:
uv pip install -e .
```

This installs an `automation` command. No install needed? Run it as a module:
`python -m automation.cli <command>`.

## Configure

```bash
cp .env.example .env      # then edit .env
# .env needs: ANTHROPIC_API_KEY=sk-ant-...
```

`AUTOMATION_WORKSPACE` (optional) sets the folder the agent reads from and writes
to; it defaults to the current working directory.

## Use

```bash
automation doctor                       # check key, config, registry, workspace
automation tools                        # list the configured tools
automation run "Summarize inbox/*.md"   # one-shot task
automation workflow process-inbox       # run a named workflow from the config
```

Flags (on `run` / `workflow`):

- `--engine direct|agent` (default `direct`)
- `--stream` stream tokens as they arrive (direct engine)
- `--model <id>` override the model from config

```bash
automation run "Draft a reply to the latest inbox note" --stream
automation run "Process today's inbox" --engine agent
```

## Workspace layout

The tools operate inside the workspace root (`AUTOMATION_WORKSPACE`, or the cwd):

```
<workspace>/
├── inbox/      # put input documents here   (read_document, list_workspace)
├── output/     # deliverables are written here   (write_deliverable)
└── .data/      # JSONL datastore: <table>.jsonl + tasks.jsonl
                #   (save_record, lookup_record, create_task)
```

`output/` and `.data/` are created automatically on first write.

## Engines: which to use?

- **direct** is the dependable default - exactly the tools in the config, a
  visible loop, and only the `anthropic` package required.
- **agent** adds the Claude Agent SDK loop (and can tap Cowork skills / MCP). It
  needs `claude-agent-sdk` (and the Claude Code CLI it drives) installed; if it
  isn't, the CLI tells you and `direct` keeps working.
