# Configuration reference (planned)

!!! note "Roadmap"
    This page describes the configuration surface `domain/` already models
    (`Budget`, `WaitPolicyConfig`) and the CLI will expose once M2/M3 land.
    See [`../architecture/domain-model.md`](../architecture/domain-model.md)
    for the underlying types.

| Setting | Flag | Env var | Default | Backed by |
|---|---|---|---|---|
| Max turns per run | `--max-turns` | `AUTOCLAUDE_MAX_TURNS` | unset (unbounded) | `domain.budget.Budget.max_turns` |
| Max dollars per run | `--max-dollars` | `AUTOCLAUDE_MAX_DOLLARS` | unset (unbounded) | `domain.budget.Budget.max_dollars` |
| Max attempts per run | `--max-attempts` | `AUTOCLAUDE_MAX_ATTEMPTS` | unset (unbounded) | `domain.budget.Budget.max_attempts` |
| Max total wait time | `--max-wait` | `AUTOCLAUDE_MAX_WAIT` | unset (unbounded) | `domain.waiting.WaitPolicyConfig.max_wait` |
| Credits probe interval | `--credits-probe-interval` | `AUTOCLAUDE_CREDITS_PROBE_INTERVAL` | 120s | `WaitPolicyConfig.credits_probe_interval` |
| Credits probe ceiling | `--credits-probe-ceiling` | `AUTOCLAUDE_CREDITS_PROBE_CEILING` | 600s | `WaitPolicyConfig.credits_probe_ceiling` |
| Window probe interval | `--window-probe-interval` | `AUTOCLAUDE_WINDOW_PROBE_INTERVAL` | 600s | `WaitPolicyConfig.window_probe_interval` |
| Reset-time grace period | `--reset-grace` | `AUTOCLAUDE_RESET_GRACE` | 60s | `WaitPolicyConfig.reset_grace` |
| Done-marker fallback string | `--done-marker` | `AUTOCLAUDE_DONE_MARKER` | `AUTOCLAUDE_TASK_FULLY_COMPLETE` | `domain.completion.DEFAULT_DONE_MARKER` |
| Log level | `-v` / `-vv` / `--log-level` | `AUTOCLAUDE_LOG_LEVEL` | `INFO` | structlog config |
| Log file | `--log-file` | `AUTOCLAUDE_LOG_FILE` | `./autoclaude.log` | `infrastructure/logging.py` |
| Use Claude Code's built-in retry watchdog instead of probing | `--retry-watchdog` | `AUTOCLAUDE_RETRY_WATCHDOG` | off | see [ADR 0005](../architecture/decisions/0005-retry-watchdog-off-by-default.md) |

Every numeric setting above corresponds directly to a field on
`WaitPolicyConfig` or `Budget` in `src/autoclaude/domain/`, both of which
validate their own values in `__post_init__` (e.g. a negative or zero
interval raises `ValueError` immediately, rather than producing a wait
policy that silently never probes). See `tests/domain/test_waiting.py` and
`tests/domain/test_budget.py` for the exact validated boundaries.
