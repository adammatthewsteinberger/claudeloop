---
name: claudeloop-releasing
description: Explains the gitflow branch model (feature/* -> develop -> main), Conventional Commits requirements and types, and how vibey-gh automates promotion, versioning, changelog generation, and PyPI Trusted Publishing (OIDC) via release.yml. Use this whenever creating a branch, writing a commit message, opening a PR, asking about versioning, releases, or publishing to PyPI, or when a commit-msg hook rejects a commit. Make sure to consult this before writing any commit message in this repo — the commit-msg git hook enforces Conventional Commits and will reject anything that doesn't match, and getting the branch target or merge strategy wrong breaks the automated release pipeline downstream.
---

# claudeloop releasing — gitflow + Conventional Commits + vibey-gh + Trusted Publishing


> **Codex skill mirror** of `.claude/skills/claudeloop-releasing/SKILL.md`. When this guidance changes, update Claude skill, Cursor rule, and `.agents/skills/` in the same PR.

## Branch model

```
main         ← always releasable; vibey-gh promote opens a promotion PR here
  ▲ rebase merge (vibey-gh promote derives the version from develop-vs-main content)
develop      ← integration branch; feature branches target this
  ▲ squash-merge (one conventional-commit-titled squash per feature, via merge-train.yml)
feature/*    ← your work — branch from develop, never from main
```

**Never branch from `main` directly, never target `main` with a feature
PR.** Feature work is `git checkout -b feature/<short-description> develop`,
PR into `develop`. `develop` → `main` happens via a promotion PR that
`promote-to-main.yml` opens by running `vibey-gh promote`, merged by rebase
(not a squash, not a plain merge commit).

## Conventional Commits — required, enforced by a git hook

Every commit message: `<type>[optional scope]: <description>`. The
`commit-msg` hook (installed by `pre-commit install`) rejects anything else
in `--strict` mode. Types and what each triggers on release:

| Type | Use for | Bump |
|---|---|---|
| `feat` | new feature | minor |
| `fix` | bug fix | patch |
| `feat!` / `fix!` / `BREAKING CHANGE:` footer | breaking change | major |
| `docs` `style` `refactor` `test` `build` `ci` `chore` | no functional/patch/minor change | none |
| `perf` | performance improvement | patch |
| `revert` | reverts a prior commit | depends |

```
feat(domain): add CreditsExhausted as a distinct capacity state
fix(waiting): clamp exponential backoff before constructing timedelta
```

Scope in parentheses is optional but strongly preferred — it makes the
`vibey-gh`-generated changelog dramatically more scannable. If a commit is
rejected: your editor still has what you typed; fix the first line and
commit again.

## vibey-gh promote — versioning and changelog, one human gate

**release-please is not used in this repo** — `.vibey-gh.toml` states it was
retired ("two systems deriving versions and opening release pull requests
against one branch is a race, not redundancy"). `promote-to-main.yml` runs
`vibey-gh promote` after a successful merge train (plus a Monday cron
backstop and manual dispatch). It compares `develop` and `main` **by
content**, derives the next version, and opens or reuses a single promotion
PR bumping `pyproject.toml`'s `[project].version` and `CHANGELOG.md`.
**Merging that PR is the release** — that merge (by rebase) is the human
review gate; nothing else about versioning needs to happen by hand.

## Publishing — PyPI Trusted Publishing (OIDC), no stored token

`release.yml` runs on every push to `main` **and** `develop` — there is no
separate `publish-to-pypi.yml` file and no `release: published` trigger. On
`develop` it stamps a unique dev version (`vibey-gh version --dev
"$GITHUB_RUN_NUMBER" --apply`) and publishes to **TestPyPI**; on `main` it
reads the version the promotion PR already committed and publishes to
**PyPI**. Both publish jobs are scoped to a GitHub Environment of the same
name (`testpypi` / `pypi`) requiring manual approval — a second human gate —
with `permissions: id-token: write` and nothing else, publishing via
`pypa/gh-action-pypi-publish`. There is no PyPI API token anywhere in this
repository's secrets — do not add one; it would disable the OIDC flow for
no benefit.

**The workflow filename `release.yml` is load-bearing** — PyPI's
pending-publisher configuration matches on it exactly. Do not rename that
file without also updating the PyPI project's Trusted Publisher
configuration to match.

## Full reference

`docs/contributing/release-process.md` (the complete manual setup steps and
verification checklist), `docs/contributing/development.md#the-branch-model-gitflow`,
`CONTRIBUTING.md`.
