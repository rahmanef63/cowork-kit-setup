# Trigger evals

`trigger-eval.json` — 20 realistic queries (10 should-trigger, 10 near-miss
should-NOT-trigger) used to tune the SKILL.md `description` so the skill fires on
the right requests and stays quiet on adjacent ones (one-off scripts, fixing an
existing app, building a single MCP server, image/slide generation, or just
explaining what Cowork is).

## Run the automated optimizer (optional)

Needs the `claude` CLI and an API key; runs ~5 iterations (≈300 model calls), so
do it as a background pass when you have time. From the **skill-creator** skill
directory:

```bash
python -m scripts.run_loop \
  --eval-set /abs/path/to/skills/cowork-automation-generator/evals/trigger-eval.json \
  --skill-path /abs/path/to/skills/cowork-automation-generator \
  --model <model-id-powering-your-session> \
  --max-iterations 5 --verbose
```

It splits the set into train/held-out test, measures the trigger rate per
description (3 reps/query), proposes improvements, and reports `best_description`
selected on the test split. Paste that into SKILL.md's frontmatter.
