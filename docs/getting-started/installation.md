# Installation

## Requirements

- Python 3.10 or newer (CI tests 3.10–3.13).
- macOS or Linux (Unix-based systems only — see
  [`../index.md`](../index.md) for why Windows isn't a target).
- The [Claude Code CLI](https://code.claude.com) installed and authenticated
  (`claude auth login`, or an `ANTHROPIC_API_KEY` in the environment) — this
  package drives it, it doesn't replace it.

## From PyPI (once published)

```bash
pipx install autoclaude
```

[`pipx`](https://pipx.pypa.io) is recommended over a bare `pip install` for
CLI tools — it isolates the install into its own virtual environment so
`autoclaude`'s dependencies never collide with anything else on your system.
A plain

```bash
pip install autoclaude
```

works too, inside whatever virtual environment you're already using.

## From source (for development)

```bash
git clone https://github.com/adammatthewsteinberger/autoclaude.git
cd autoclaude
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
pre-commit install
```

See [`../contributing/development.md`](../contributing/development.md) for
the full contributor setup, including how to run every quality gate locally.

## Verifying the install

```bash
autoclaude --version
autoclaude --help
```

If `autoclaude` isn't on your `PATH` after a `pipx install`, run
`pipx ensurepath` and open a new shell.

## Project status

`autoclaude` is pre-1.0 and under active development. The domain core
(milestone M1) is complete and tested; the CLI, the agent runner, and the
generated REST surface (M2–M5) are still being built. See
[`../plans/architecture-and-roadmap.md`](../plans/architecture-and-roadmap.md)
for the roadmap.
