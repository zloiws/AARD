"""
Tests for PromptAssignment creation and basic retrieval/resolution filters
"""
import pytest
from uuid import uuid4

from app.core.execution_context import ExecutionContext
from app.services.prompt_service import PromptService
from app.models.prompt import Prompt, PromptType


def test_create_prompt_assignment(db):
    """Create a prompt and assign it with component_role/stage/scope"""
    context = ExecutionContext.from_db_session(db)
    svc = PromptService(db)

    # Create a prompt
    prompt = svc.create_prompt(
        name="test-assignment-prompt",
        prompt_text="System: do X",
        prompt_type=PromptType.SYSTEM,
        level=0,
        created_by="test"
    )

    # Assign prompt with required fields
    assignment = svc.assign_prompt_to_model_or_server(
        prompt_id=prompt.id,
        model_id=None,
        server_id=None,
        task_type="planning",
        component_role="planning",
        stage="planning",
        scope="global",
        agent_id=None,
        experiment_id=None,
        created_by="test"
    )

    assert assignment is not None
    assert assignment.component_role == "planning"
    assert assignment.stage == "planning"
    assert assignment.scope == "global"
    assert str(assignment.prompt_id) == str(prompt.id)


def test_list_assignments_filters(db):
    """Ensure listing assignments by component_role and scope works"""
    context = ExecutionContext.from_db_session(db)
    svc = PromptService(db)

    # Create base prompt
    p = svc.create_prompt(
        name="filter-prompt",
        prompt_text="Filter test",
        prompt_type=PromptType.SYSTEM,
        level=0,
        created_by="test"
    )

    # Create assignments with different scopes and roles
    a_global = svc.assign_prompt_to_model_or_server(
        prompt_id=p.id,
        component_role="interpretation",
        stage="interpretation",
        scope="global",
        created_by="test"
    )

    a_agent = svc.assign_prompt_to_model_or_server(
        prompt_id=p.id,
        component_role="interpretation",
        stage="interpretation",
        scope="agent",
        agent_id=uuid4(),
        created_by="test"
    )

    # Query by component_role
    results = svc.list_assignments(component_role="interpretation")
    assert any(r.id == a_global.id for r in results)
    assert any(r.id == a_agent.id for r in results)

    # Query by scope
    globals_only = svc.list_assignments(component_role="interpretation", scope="global")
    assert any(r.id == a_global.id for r in globals_only)
    assert all(r.scope == "global" for r in globals_only)


