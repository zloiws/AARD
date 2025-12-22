from uuid import uuid4


def create_prompt(svc, name, text="x", prompt_type="system"):
    p = svc.create_prompt(name=name, prompt_text=text, prompt_type=prompt_type, level=0, created_by="test")
    return p


def test_experiment_over_agent_precedence(db):
    from app.models.prompt_assignment import PromptAssignment
    from app.services.prompt_runtime_selector import PromptRuntimeSelector
    from app.services.prompt_service import PromptService

    svc = PromptService(db)
    selector = PromptRuntimeSelector(db)
    role = "routing"

    # global
    gp = create_prompt(svc, "global1", "g")
    db.add(PromptAssignment(prompt_id=gp.id, component_role=role, stage=role, scope="global", created_by="test"))
    db.commit()

    # agent
    agent_id = uuid4()
    ap = create_prompt(svc, "agent1", "agent")
    db.add(PromptAssignment(prompt_id=ap.id, component_role=role, stage=role, scope="agent", agent_id=agent_id, created_by="test"))
    db.commit()

    # experiment
    exp_id = uuid4()
    ep = create_prompt(svc, "exp1", "exp")
    db.add(PromptAssignment(prompt_id=ep.id, component_role=role, stage=role, scope="experiment", experiment_id=exp_id, created_by="test"))
    db.commit()

    # resolve with both agent and experiment -> experiment wins
    resolved = selector.resolve(component_role=role, agent_id=agent_id, context_metadata={"experiment_id": str(exp_id)})
    assert resolved["source"] == "experiment"
    assert resolved["prompt_text"] == "exp"


def test_model_server_filtering(db):
    from uuid import uuid4

    from app.models.prompt_assignment import PromptAssignment
    from app.services.prompt_runtime_selector import PromptRuntimeSelector
    from app.services.prompt_service import PromptService

    svc = PromptService(db)
    selector = PromptRuntimeSelector(db)
    role = "execution"

    # global generic
    gp = create_prompt(svc, "g1", "generic")
    db.add(PromptAssignment(prompt_id=gp.id, component_role=role, stage=role, scope="global", created_by="test"))
    db.commit()

    # model-specific (create corresponding OllamaModel to satisfy FK)
    model_id = uuid4()
    from app.models.ollama_model import OllamaModel
    from app.models.ollama_server import OllamaServer
    server = OllamaServer(name="test-server", url="http://localhost:11434", is_active=False)
    db.add(server)
    db.commit()
    db.add(OllamaModel(id=model_id, model_name="test-model", name="test-model-display", server_id=server.id))
    db.commit()
    mp = create_prompt(svc, "m1", "model-specific")
    db.add(PromptAssignment(prompt_id=mp.id, component_role=role, stage=role, scope="global", model_id=model_id, created_by="test"))
    db.commit()

    # when model_id provided -> should pick model-specific
    resolved = selector.resolve(component_role=role, model_id=model_id)
    assert resolved["source"] == "global"
    assert resolved["prompt_text"] == "model-specific"

    # without model_id -> picks generic global
    resolved2 = selector.resolve(component_role=role)
    assert resolved2["prompt_text"] == "generic"


def test_invalid_experiment_id_handling_returns_fallback(db):
    from app.services.prompt_runtime_selector import PromptRuntimeSelector
    from app.services.prompt_service import PromptService

    svc = PromptService(db)
    selector = PromptRuntimeSelector(db)
    role = "analysis"

    # disk canonical (name == role)
    dp = create_prompt(svc, name=role, text="disk")

    # call with invalid experiment id string -> should not raise, fallback to disk
    resolved = selector.resolve(component_role=role, context_metadata={"experiment_id": "not-a-uuid"})
    assert resolved["source"] == "disk"
    assert resolved["prompt_text"] == "disk"


def test_no_component_role_returns_none(db):
    from app.services.prompt_runtime_selector import PromptRuntimeSelector
    selector = PromptRuntimeSelector(db)
    # component_role that doesn't exist and no disk prompt
    resolved = selector.resolve(component_role="nonexistent_role")
    assert resolved["prompt_text"] is None
    assert resolved["source"] is None


