"""Composition root — the only module permitted to know about every layer at
once. Wires concrete infrastructure adapters into application ports and hands
the assembled AutonomousRunner (or a lighter-weight use-case dependency) to
cli/. Nothing outside this file should import both a port name from
application/ports.py and its concrete infrastructure implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import click

from claudeloop.application.runner import AutonomousRunner
from claudeloop.application.usecases.doctor import DoctorEnvironment
from claudeloop.domain.budget import Budget
from claudeloop.domain.waiting import WaitPolicyConfig
from claudeloop.infrastructure.agent.catalog import SdkSessionCatalog
from claudeloop.infrastructure.agent.gateway import ClaudeAgentGateway, ClaudeCapacityProbe
from claudeloop.infrastructure.audit import JsonlAuditLog
from claudeloop.infrastructure.clock import AnyioSleeper, SystemClock
from claudeloop.infrastructure.config import RunnerConfig
from claudeloop.infrastructure.doctor_env import RealDoctorEnvironment
from claudeloop.infrastructure.progress import ConsoleProgressReporter


@dataclass(frozen=True, slots=True)
class RunnerContext:
    runner: AutonomousRunner
    gateway: ClaudeAgentGateway


def build_runner(
    *,
    cwd: Path,
    config: RunnerConfig,
    session_id: str | None = None,
    resume: str | None = None,
    continue_conversation: bool = False,
    log_file: Path | None = None,
) -> RunnerContext:
    gateway = ClaudeAgentGateway(
        cwd=str(cwd),
        session_id=session_id,
        resume=resume,
        continue_conversation=continue_conversation,
        max_turns=config.max_turns,
        max_budget_usd=config.max_dollars,
        retry_watchdog=config.retry_watchdog,
        model=config.model,
    )
    probe = ClaudeCapacityProbe(cwd=str(cwd))
    clock = SystemClock()
    sleeper = AnyioSleeper(clock)
    audit_path = Path(log_file) if log_file else cwd / "claudeloop.log.jsonl"
    audit_log = JsonlAuditLog(audit_path)
    progress = ConsoleProgressReporter()
    budget = Budget(
        max_turns=config.max_turns,
        max_dollars=config.max_dollars,
        max_attempts=config.max_attempts,
    )
    wait_policy = WaitPolicyConfig(
        credits_probe_interval=timedelta(seconds=config.credits_probe_interval_seconds),
        credits_probe_ceiling=timedelta(seconds=config.credits_probe_ceiling_seconds),
        window_probe_interval=timedelta(seconds=config.window_probe_interval_seconds),
        reset_grace=timedelta(seconds=config.reset_grace_seconds),
        max_wait=(
            timedelta(seconds=config.max_wait_seconds)
            if config.max_wait_seconds is not None
            else None
        ),
    )

    runner = AutonomousRunner(
        agent_gateway=gateway,
        capacity_probe=probe,
        clock=clock,
        sleeper=sleeper,
        audit_log=audit_log,
        progress=progress,
        budget=budget,
        wait_policy=wait_policy,
        done_marker=config.done_marker,
    )
    return RunnerContext(runner=runner, gateway=gateway)


def build_session_catalog() -> SdkSessionCatalog:
    return SdkSessionCatalog()


def build_doctor_environment() -> DoctorEnvironment:
    return RealDoctorEnvironment()


_CACHED_API_GROUP: click.Group | None = None


def build_api_click_group() -> click.Group:
    from claudeloop.infrastructure.api.binder import build_api_click_group as _build

    global _CACHED_API_GROUP
    if _CACHED_API_GROUP is None:
        _CACHED_API_GROUP = _build()
    return _CACHED_API_GROUP
