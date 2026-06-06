# Contributing

This repo is a **generator**: it turns a field name into an automation repo. Two
layers — the generator (`skills/`, `agents/`, `scripts/`) and what it emits
(`examples/`). Keep both honest with the checks below.

## The contract

`automation.config.json` is the single source of truth. The Python registry
(`local/automation/tools.py`) and the TypeScript dispatcher (`web/lib/tools.ts`)
must implement the **same tool handlers** by name. CI fails if they drift.

## Add / change a domain

```bash
# full design (recommended): hand the scaffolder a config Claude designed
python3 skills/cowork-automation-generator/scripts/scaffold.py --config design.json --out ./out

# minimal: core tools + tuned metadata from just a name
python3 skills/cowork-automation-generator/scripts/scaffold.py --domain "your field" --out ./out
```

Domain tools whose `handler` isn't one of the six core handlers get a stub
injected into both languages (look for `TODO`). Implement the body in both
`local/automation/tools.py` and `web/lib/tools.ts` — keep the tool `name` identical.

## Add a core tool (shipped in every generated repo)

1. Add the spec to the template `assets/templates/automation.config.json`.
2. Implement it in `assets/templates/local/automation/tools.py` (`@register("name")`).
3. Implement it in `assets/templates/web/lib/tools.ts` (add to the `handlers` map).
4. Keep the `name`/`handler` identical across all three.

## Before you push

```bash
python3 scripts/verify.py                                  # JSON, py_compile, config<->py<->ts, scaffold dry-run
python3 scripts/check_web.py skills/cowork-automation-generator/assets/templates/web   # Convex wiring resolves
```

Or run everything at once: `python3 scripts/check.py`. A local **git pre-commit hook**
runs it automatically on each commit — enable once per clone:

```bash
git config core.hooksPath hooks
```

This repo uses a local hook, not a cloud CI service. Bypass once with `git commit --no-verify`.

## Conventions

- Tool `name` and `handler`: `snake_case` (`^[a-z][a-z0-9_]*$`).
- `input_schema`: plain JSON Schema (`type: object`) — drops straight into both SDKs.
- Deterministic work in tools; judgement in the system prompt.
- Gate irreversible/external actions behind human approval. Webapp stays BYOK.
