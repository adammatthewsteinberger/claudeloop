# Release process

Releases are automated by [`vibey-gh`](https://pypi.org/project/vibey-gh/)
(pinned to `1.47.0` in `pyproject.toml` and in every workflow that installs
it), and published to PyPI via
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC — no
long-lived API token stored anywhere). **release-please is not used.**
`.vibey-gh.toml` states this explicitly: "release-please has been retired:
two systems deriving versions and opening release pull requests against one
branch is a race, not redundancy."

## The automated loop

1. A feature PR merges into `develop` (squash-merged by `merge-train.yml`,
   which runs `vibey-gh merge-train` once the PR-automation gate on that PR's
   head has passed — see
   [development.md](development.md#the-branch-model-gitflow)).
2. `promote-to-main.yml` runs after a successful merge train (also on a
   Monday cron backstop, and via manual dispatch). It runs `vibey-gh
   promote`, which compares `develop` and `main` **by content** (not commit
   count), derives the next version, and opens or reuses a promotion PR
   against `main` — bumping `pyproject.toml`'s `[project].version` and
   `src/claudeloop/__init__.py`, and updating `CHANGELOG.md`.
3. **Merging that promotion PR is what cuts a release** — it's the human
   review gate, enforced by a branch ruleset that requires an approving
   review (`AUTOMERGE_TOKEN` is what lets the automation itself push the
   version bump and later complete the merge). The PR is merged by rebase,
   not a plain merge commit — `main`'s commits are rewritten copies with new
   SHAs, which is why `develop` can never fast-forward onto `main` and why a
   separate `realign` step exists (below).
4. `release.yml` runs on every push to `main` **and** `develop` — there is no
   separate `publish-to-pypi.yml` file. On `develop`, it stamps a unique dev
   version (`vibey-gh version --dev "$GITHUB_RUN_NUMBER" --apply`) and
   publishes straight to **TestPyPI**, then verifies the exact version
   installs and runs from there. On `main`, it reads the version already
   committed to `pyproject.toml` (set by the promotion in step 2/3) and
   publishes straight to **PyPI** — no `release: published` event, no
   separate tag-triggered workflow. Both the `testpypi` and `pypi` publish
   jobs are scoped to a GitHub Environment of the same name, which requires
   manual approval before the job runs — that approval is the second human
   gate, independent of the promotion-PR review.
5. After a successful `main` publish, `release.yml`'s `realign` job pushes
   `main` back onto `develop` (`vibey-gh realign`) when `AUTOMERGE_TOKEN` is
   configured, so the two branches don't drift apart. This is tidiness, not
   a gate — `vibey-gh promote` compares branches by content, so a divergent
   `develop` never blocks the next release.

Nothing in this loop requires the maintainer to hand-bump a version number,
hand-write a changelog entry, or hold a PyPI API token anywhere.

## One-time manual setup (already done for this repo, documented for forks)

1. **Create the GitHub repo** `adammatthewsteinberger/claudeloop`, push
   `main` and `develop`. Set **`develop` as the default branch** so the
   GitHub front door is the integration branch contributors PR into.
   `main` stays the always-releasable line that `vibey-gh promote` targets.
   Fill in the About box (description, website, topics) as documented in
   [documentation.md](documentation.md#github-about-box-not-stored-in-git);
   enable Discussions; leave the wiki off.
2. **PyPI → Account settings → Publishing → Add a new pending publisher:**

   | Field | Value |
   |---|---|
   | PyPI Project Name | `claudeloop` |
   | Owner | `adammatthewsteinberger` |
   | Repository name | `claudeloop` |
   | Workflow name | `release.yml` (the **filename** — this is load-bearing) |
   | Environment name | `pypi` |

3. **Create the GitHub environments `pypi` and `testpypi`** (repo Settings →
   Environments) with the maintainer as a required reviewer on `pypi`. This
   is what makes Trusted Publishing meaningfully stronger than a repo-scoped
   API token — per PyPI's own security model documentation, anyone with
   commit access can otherwise modify a publishing workflow, so the human
   approval gate on the environment is the actual control, not the OIDC
   exchange by itself.
4. **Protect `main`**: require CI (`ci.yml`) to pass, require an approving
   review, disallow force-pushes.
5. **Enable GitHub Pages**, source: GitHub Actions (for `release-surfaces.yml`,
   which branches ProperDocs and companion surfaces after a release).

A PyPI *pending* publisher reserves nothing — the project name isn't claimed
until the first real publish succeeds. The working title `autoclaude` was
rejected as too similar to existing packages, which is why this project
ships as `claudeloop`; claim it promptly with a real `0.1.0` rather than
deferring indefinitely.

## Doing a release dry run

Before the first real PyPI publish, validate the whole OIDC + build
pipeline against **TestPyPI**:

1. Repeat the pending-publisher setup above at `test.pypi.org` (a fully
   separate account and publisher registry from `pypi.org`), pointed at the
   `testpypi` environment.
2. Push to `develop` — every such push runs `release.yml`'s `testpypi` job
   automatically; there is no separate manual-dispatch path for this.
3. `release.yml`'s own `verify-testpypi` job already does the round-trip
   install-and-run check (`pip install --index-url
   https://test.pypi.org/simple/ claudeloop==<version>` in a fresh
   environment, then `claudeloop --version`) against the pushed dev build.
4. Only once that round-trips cleanly, proceed with a real promotion PR
   merge against `main` (step 2–3 of [the automated loop](#the-automated-loop)).

## What CI checks before any of this runs

Every gate in [development.md](development.md#running-the-quality-gates-locally)
runs in `ci.yml` on every push and PR to `main`/`develop`, across Python
3.10–3.13. `release.yml`'s publish jobs (`testpypi`, `pypi`) do not re-run
the test suite — they trust that nothing reaches `main`/`develop` (both
protected, CI-gated) without already having passed it. The `build` job
that precedes both publish jobs just builds the sdist and wheel with
`python -m build`, keeping the publish jobs themselves minimal (they hold
the OIDC token; the less they do, the smaller that surface is).

## Verifying a completed publish

- Attestations: `pypa/gh-action-pypi-publish` generates signed attestations
  automatically for Trusted Publishing flows (PEP 740) — visible on the
  PyPI project page under each release's files.
- `py.typed` shipped in the wheel: `unzip -l dist/*.whl | grep py.typed`.
- Metadata: `pypi.org/project/claudeloop/` should show the classifiers,
  keywords, and `[project.urls]` links configured in `pyproject.toml`.
