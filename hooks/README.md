# Git hooks (local, no cloud CI)

This repo gates quality with a local pre-commit hook instead of a CI service.

Enable it once after cloning:

```bash
git config core.hooksPath hooks
```

Then every `git commit` runs `python3 scripts/check.py` (contract + template +
wizard checks). Bypass a single commit with `git commit --no-verify`.

You can also run the checks any time: `python3 scripts/check.py`.
