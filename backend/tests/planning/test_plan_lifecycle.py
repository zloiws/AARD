import pytest


def test_plan_lifecycle_validate_transition():
    from app.planning.lifecycle import allowed_targets, validate_transition

    assert validate_transition("draft", "approved").allowed
    assert not validate_transition("draft", "executing").allowed
    assert "approved" in allowed_targets("draft")


@pytest.mark.integration
def test_execute_requires_approved(client, db):
    # Create minimal Task + Plan in DB and verify /execute rejects until approved.
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.models.plan import Plan
    from app.models.task import Task

    task = Task(description="test task", status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)

    plan = Plan(
        task_id=task.id,
        version=1,
        goal="test",
        strategy={},
        steps=[{"type": "noop", "description": "no-op"}],
        alternatives=[],
        status="draft",
        current_step=0,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # Should fail because plan is draft
    r = client.post(f"/api/plans/{plan.id}/execute")
    assert r.status_code == 400

    # Approve
    r2 = client.post(f"/api/plans/{plan.id}/approve")
    assert r2.status_code == 200

    # Execution may still fail for other reasons in this environment, but it must pass lifecycle gate.
    r3 = client.post(f"/api/plans/{plan.id}/execute")
    assert r3.status_code in (200, 400)
    if r3.status_code == 400:
        # Ensure it's not the lifecycle rejection anymore
        assert "must be approved" not in (r3.json().get("detail") or "").lower()


