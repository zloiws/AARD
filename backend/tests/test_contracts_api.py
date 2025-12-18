import json
from uuid import uuid4

def test_execution_event_contract(client, db):
    from app.models.workflow_event import WorkflowEvent
    # create an event with required fields and extended contract fields
    ev = WorkflowEvent(
        workflow_id="wf-test-1",
        event_type="model_request",
        event_source="model",
        stage="execution",
        message="Invoking model",
        component_role="execution",
        prompt_id=None,
        prompt_version="v1",
        decision_source="human",
    )
    db.add(ev)
    db.commit()

    r = client.get("/api/events/recent")
    assert r.status_code == 200
    body = r.json()
    assert "events" in body and isinstance(body["events"], list)
    items = body["events"]
    # find our event
    found = [e for e in items if e.get("workflow_id") == "wf-test-1"]
    assert len(found) == 1
    e = found[0]
    # contract fields present
    assert "component_role" in e
    assert "decision_source" in e
    assert "prompt_id" in e
    assert "prompt_version" in e
    # types
    assert e["decision_source"] == "human"


def test_prompt_assignment_contract_api(client):
    # Override auth to allow assign endpoint
    from types import SimpleNamespace
    from app.core.auth import get_current_user_required
    client.app.dependency_overrides[get_current_user_required] = lambda: SimpleNamespace(username="tester", role="admin")

    # create prompt
    payload = {
        "name": "contract-test-prompt",
        "prompt_text": "System directive",
        "prompt_type": "system",
        "level": 0
    }
    r = client.post("/api/prompts/", json=payload)
    assert r.status_code == 200
    prompt = r.json()
    pid = prompt["id"]

    # assign with extended fields
    assign_payload = {
        "model_id": None,
        "server_id": None,
        "task_type": "execution",
        "component_role": "execution",
        "stage": "execution",
        "scope": "global",
        "agent_id": None,
        "experiment_id": None
    }
    r2 = client.post(f"/api/prompts/{pid}/assign", json=assign_payload)
    assert r2.status_code == 200
    assign = r2.json()
    # contract fields returned
    for key in ["component_role", "stage", "scope", "prompt_id", "id"]:
        assert key in assign

    # list assignments via endpoint and check keys exist
    r3 = client.get(f"/api/prompts/{pid}/assignments")
    assert r3.status_code == 200
    arr = r3.json()
    assert isinstance(arr, list) and len(arr) >= 1
    a = arr[0]
    assert "component_role" in a and "stage" in a and "scope" in a

    # cleanup override
    client.app.dependency_overrides.pop(get_current_user_required, None)


