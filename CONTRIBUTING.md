# Contributing

## Branch / PR
- Use feature branches.
- Keep PRs focused (one concern per PR).
- Include test evidence in PR description.

## Commit style
- `feat: ...` for new features
- `fix: ...` for bug fixes
- `docs: ...` for documentation
- `test: ...` for tests
- `chore: ...` for maintenance

## Local quality gate
Run before opening PR:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests -v
```

## Lore and Blueprint discipline
- Keep Canon constraints in sync with implementation.
- If schema changes, update both `schemas/` and `examples/`.
- Document breaking changes in `docs/execution-prep.md`.
