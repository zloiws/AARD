import json
from uuid import UUID

def test_prompt_assign_and_unassign_api(client):
    # Create a prompt
    payload = {
        "name": "api-test-prompt",
        "prompt_text": "System: do X",
        "prompt_type": "system",
        "level": 0
    }
    r = client.post("/api/prompts/", json=payload)
    assert r.status_code == 200
    prompt = r.json()
    prompt_id = prompt["id"]

    # Assign prompt
    assign_payload = {
        "model_id": None,
        "server_id": None,
        "task_type": "planning",
        "component_role": "planning",
        "stage": "planning",
        "scope": "global"
    }
    r = client.post(f"/api/prompts/{prompt_id}/assign", json=assign_payload)
    assert r.status_code == 200
    assignment = r.json()
    assignment_id = assignment["id"]

    # List assignments for prompt
    r = client.get(f"/api/prompts/{prompt_id}/assignments")
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list) and len(arr) >= 1

    # Delete assignment
    r = client.delete(f"/api/prompts/assignments/{assignment_id}")
    assert r.status_code == 204

    # Confirm deletion
    r = client.get(f"/api/prompts/{prompt_id}/assignments")
    assert r.status_code == 200
    arr = r.json()
    ids = [a["id"] for a in arr]
    assert str(assignment_id) not in ids


