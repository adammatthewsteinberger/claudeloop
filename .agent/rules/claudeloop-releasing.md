# claudeloop-releasing (Antigravity mirror of `.claude/skills/claudeloop-releasing/SKILL.md`)


# claudeloop releasing

## Branch model

```
main         ← always releasable; vibey-gh promote opens a promotion PR here
  ▲ rebase merge (vibey-gh promote derives the version from content, not commits)
develop      ← integration; feature branches target this
  ▲ squash-merge (one conventional-commit-titled squash per feature)
feature/*    ← branch from develop, never from main
```

Never branch from `main`. Never target `main` with a feature PR.

## Conventional Commits (required, enforced by hook)

`<type>[optional scope]: <description>`. Hook installed via `pre-commit
install`. Types:

| Type | Use | Bump |
|---|---|---|
| `feat` | new feature | minor |
| `fix` | bug fix | patch |
| `feat!` / `fix!` / `BREAKING CHANGE:` | breaking change | major |
| `docs` `style` `refactor` `test` `build` `ci` `chore` | no functional change | none |
| `perf` | performance improvement | patch |

Scope in parentheses optional but strongly preferred.

## vibey-gh (release-please is retired)

`promote-to-main.yml` runs `vibey-gh promote`: compares `develop`/`main` by
content, derives the version, opens a promotion PR (rebase-merged) bumping
`pyproject.toml` and `CHANGELOG.md`. On merge, `release.yml` publishes
straight to PyPI (main) / TestPyPI (develop) via Trusted Publishing (OIDC),
gated by GitHub Environment approval — no `release: published` event, no
`publish-to-pypi.yml`.

See `docs/contributing/release-process.md`.
