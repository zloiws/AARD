"""
PlanLifecycle — explicit plan state machine.

This module centralizes allowed transitions for `Plan.status` so that:
- behavior is observable (single source of truth)
- transitions are attributable (errors point to lifecycle rules)
- transitions are reversible (no hidden implicit auto-transitions)

Plan.status values are stored as lowercase strings in DB (see `app.models.plan.Plan.status`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class TransitionResult:
    allowed: bool
    reason: Optional[str] = None


PLAN_STATES: Set[str] = {"draft", "approved", "executing", "completed", "failed", "cancelled"}


ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "draft": {"approved", "cancelled"},
    "approved": {"executing", "cancelled"},
    "executing": {"completed", "failed", "cancelled"},
    # terminal-ish states
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


def validate_transition(current: str, target: str) -> TransitionResult:
    current = (current or "").lower()
    target = (target or "").lower()

    if current not in PLAN_STATES:
        return TransitionResult(False, f"unknown_current_state:{current}")
    if target not in PLAN_STATES:
        return TransitionResult(False, f"unknown_target_state:{target}")
    if target == current:
        return TransitionResult(True, "no_op")
    if target in ALLOWED_TRANSITIONS.get(current, set()):
        return TransitionResult(True)
    return TransitionResult(False, f"disallowed_transition:{current}->{target}")


def allowed_targets(current: str) -> List[str]:
    current = (current or "").lower()
    return sorted(ALLOWED_TRANSITIONS.get(current, set()))


