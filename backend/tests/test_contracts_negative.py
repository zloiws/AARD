import json


def test_create_prompt_invalid_type(client):
    # invalid prompt_type should return 422
    payload = {
        "name": "invalid-type-prompt",
        "prompt_text": "text",
        "prompt_type": "invalid_type",
        "level": 0
    }
    r = client.post("/api/prompts/", json=payload)
    assert r.status_code == 422


def test_assign_requires_auth(client):
    # create prompt (allowed without auth)
    payload = {
        "name": "auth-required-prompt",
        "prompt_text": "text",
        "prompt_type": "system",
        "level": 0
    }
    r = client.post("/api/prompts/", json=payload)
    assert r.status_code == 200
    pid = r.json()["id"]

    # attempt to assign without auth override -> should be 401
    assign_payload = {
        "component_role": "execution",
        "stage": "execution",
        "scope": "global"
    }
    r2 = client.post(f"/api/prompts/{pid}/assign", json=assign_payload)
    assert r2.status_code == 401


def test_assign_invalid_uuid_fields_return_422(client):
    # override auth for creation/assignment
    from types import SimpleNamespace

    from app.core.auth import get_current_user_required
    client.app.dependency_overrides[get_current_user_required] = lambda: SimpleNamespace(username="t", role="admin")

    payload = {
        "name": "uuid-format-prompt",
        "prompt_text": "text",
        "prompt_type": "system",
        "level": 0
    }
    r = client.post("/api/prompts/", json=payload)
    assert r.status_code == 200
    pid = r.json()["id"]

    # experiment_id invalid format
    assign_payload = {
        "component_role": "execution",
        "stage": "execution",
        "scope": "experiment",
        "experiment_id": "not-a-uuid"
    }
    r2 = client.post(f"/api/prompts/{pid}/assign", json=assign_payload)
    assert r2.status_code == 422

    # model_id invalid format
    assign_payload2 = {
        "component_role": "execution",
        "stage": "execution",
        "scope": "global",
        "model_id": "123"
    }
    r3 = client.post(f"/api/prompts/{pid}/assign", json=assign_payload2)
    assert r3.status_code == 422

    client.app.dependency_overrides.pop(get_current_user_required, None)


def test_events_recent_invalid_limit_returns_422(client):
    r = client.get("/api/events/recent?limit=0")
    assert r.status_code == 422


def test_delete_assignment_requires_auth(client):
    # create prompt and assignment with auth, then attempt delete without auth
    from types import SimpleNamespace

    from app.core.auth import get_current_user_required
    client.app.dependency_overrides[get_current_user_required] = lambda: SimpleNamespace(username="t", role="admin")

    payload = {
        "name": "delete-auth-prompt",
        "prompt_text": "text",
        "prompt_type": "system",
        "level": 0
    }
    r = client.post("/api/prompts/", json=payload)
    pid = r.json()["id"]
    assign_payload = {"component_role": "execution", "stage": "execution", "scope": "global"}
    r2 = client.post(f"/api/prompts/{pid}/assign", json=assign_payload)
    assert r2.status_code == 200
    aid = r2.json()["id"]

    # remove auth override -> unauthenticated delete should be 401
    client.app.dependency_overrides.pop(get_current_user_required, None)
    r3 = client.delete(f"/api/prompts/assignments/{aid}")
    assert r3.status_code == 401


