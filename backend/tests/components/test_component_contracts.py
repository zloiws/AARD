from pathlib import Path

import pytest


def _repo_root() -> Path:
    # backend/tests/components -> repo root
    return Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "prompt_name",
    [
        "interpretation.system",
        "semantic_validator.system",
        "routing.system",
        "planning.system",
        "execution_validator.system",
        "reflection.system",
    ],
)
def test_component_prompts_exist(prompt_name: str):
    p = _repo_root() / "prompts" / "components" / prompt_name
    assert p.exists(), f"Missing prompt file: {p}"
    assert p.read_text(encoding="utf-8").strip(), f"Empty prompt file: {p}"


def test_contract_models_importable():
    from app.components.contracts import (ExecutionValidationResult,
                                          PlanHypothesis, ReflectionRecord,
                                          RoutingDecision, StructuredIntent,
                                          ValidationResult)

    # Basic smoke validation
    intent = StructuredIntent(raw_input="hi", intent="hi")
    assert intent.raw_input == "hi"
    assert ValidationResult().status == "approved"
    assert RoutingDecision().route == "unknown"
    assert PlanHypothesis().confidence == 0.5
    assert ExecutionValidationResult().status == "approved"
    assert ReflectionRecord().category == "unknown"


@pytest.mark.asyncio
async def test_semantic_validator_smoke():
    from app.components.contracts import StructuredIntent
    from app.components.semantic_validator import SemanticValidator

    v = SemanticValidator()
    res = await v.validate_intent(StructuredIntent(raw_input="x", intent="x"))
    assert res.status == "approved"


