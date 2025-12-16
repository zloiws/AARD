"""
Contract models for prompt-centric components.

These contracts are intentionally minimal: they aim to make I/O observable and testable
without forcing a big refactor of existing services.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class StructuredIntent(BaseModel):
    raw_input: str = Field(..., description="Original user input")
    intent: Optional[str] = Field(default=None, description="Best-effort interpreted intent text")
    requires_clarification: bool = Field(default=False)
    clarification_questions: List[str] = Field(default_factory=list)
    can_proceed: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    status: Literal["approved", "clarification_required", "rejected"] = "approved"
    reason: Optional[str] = None
    clarification_questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    route: Literal["simple_chat", "planning", "execution", "unknown"] = "unknown"
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanHypothesis(BaseModel):
    name: str = "plan_hypothesis"
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionValidationResult(BaseModel):
    status: Literal["approved", "rejected"] = "approved"
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReflectionRecord(BaseModel):
    category: Literal["success", "partial_success", "semantic_mismatch", "execution_failure", "unknown"] = "unknown"
    summary: Optional[str] = None
    suggested_improvements: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


