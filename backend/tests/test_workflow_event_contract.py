from datetime import datetime, timezone
from app.models.workflow_event import WorkflowEvent


def test_workflow_event_to_dict_includes_executionevent_fields():
    ev = WorkflowEvent()
    ev.id = None
    ev.workflow_id = "wf-1"
    ev.event_type = "model_request"
    ev.event_source = "model"
    ev.stage = "interpretation"
    ev.status = "in_progress"
    ev.message = "test"
    ev.event_data = {"input_summary": "in", "output_summary": "out", "reason_code": "rc1"}
    ev.event_metadata = {"component_name": "InterpretationService"}
    ev.timestamp = datetime.now(timezone.utc)

    d = ev.to_dict()
    assert "input_summary" in d
    assert "output_summary" in d
    assert "reason_code" in d
    assert "component_name" in d
    assert d["input_summary"] == "in"
    assert d["output_summary"] == "out"
    assert d["reason_code"] == "rc1"
    assert d["component_name"] == "InterpretationService"


