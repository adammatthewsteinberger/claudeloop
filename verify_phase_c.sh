#!/bin/bash
# Phase C verification script - run all quality gates

set -e  # Exit on first error

echo "=== Phase C Guardrails Verification ==="
echo

echo "1. Formatting with ruff..."
uv run ruff format src tests

echo "2. Linting with ruff..."
uv run ruff check --fix src tests

echo "3. Type checking with mypy..."
uv run mypy --strict src/claudeloop

echo "4. Testing domain layer (100% branch coverage required)..."
uv run pytest --cov=src/claudeloop/domain --cov-branch --cov-fail-under=100 -v

echo "5. Testing application layer (100% branch coverage required)..."
uv run pytest --cov=src/claudeloop/application --cov-branch --cov-fail-under=100 -v

echo "6. Testing infrastructure layer (100% branch coverage required)..."
uv run pytest --cov=src/claudeloop/infrastructure --cov-branch --cov-fail-under=100 -v

echo "7. Testing CLI layer (100% branch coverage required)..."
uv run pytest --cov=src/claudeloop/cli --cov-branch --cov-fail-under=100 -v

echo "8. Checking architecture constraints with lint-imports..."
uv run lint-imports

echo "9. Security scan with bandit..."
uv run bandit -r src/claudeloop

echo "10. Dependency vulnerability check with pip-audit..."
uv run pip-audit

echo "11. Stability check (running pytest 5 times)..."
for i in 1 2 3 4 5; do
    echo "  Run $i/5..."
    uv run pytest -q || { echo "FAILED on run $i"; exit 1; }
done

echo
echo "=== All gates passed! ==="
echo
echo "Next: Create commit with:"
echo "  git add -A"
echo "  git commit -m 'feat(cli): add --cwd and --wind-down-at guardrails"
echo ""
echo "- Add --cwd to resume, stop, wind-down, prompt, logs, status, unwind, watch"
echo "- Prevents incident where resume from wrong directory auto-committed to live checkout"
echo "- Add --wind-down-at for deadline-driven graceful hand-off"
echo "- Supports ISO8601 absolute timestamps and +duration relative specs"
echo "- Fix py3.10 TUI test flake with await pilot.pause() for widget mount"
echo ""
echo "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>'"
