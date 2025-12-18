from uuid import uuid4

def create_prompt(svc, name, text="x", prompt_type="system"):
    p = svc.create_prompt(name=name, prompt_text=text, prompt_type=prompt_type, level=0, created_by="test")
    return p


def test_prompt_runtime_selector_precedence(db):
    from app.services.prompt_service import PromptService
    from app.services.prompt_runtime_selector import PromptRuntimeSelector
    from app.models.prompt_assignment import PromptAssignment
    from uuid import UUID

    svc = PromptService(db)
    selector = PromptRuntimeSelector(db)

    component_role = "interpretation"

    # create disk-canonical prompt (acts as fallback)
    disk = create_prompt(svc, name=component_role, text="disk-prompt", prompt_type="system")

    # create global prompt and assignment
    global_p = create_prompt(svc, name="global-prompt", text="global", prompt_type="system")
    assign_global = PromptAssignment(
        prompt_id=global_p.id,
        component_role=component_role,
        stage=component_role,
        scope="global",
        created_by="test"
    )
    db.add(assign_global)
    db.commit()

    # resolve -> should pick global
    resolved = selector.resolve(component_role=component_role)
    assert resolved["source"] == "global"
    assert resolved["prompt_text"] == "global"

    # create agent assignment
    agent_id = uuid4()
    agent_p = create_prompt(svc, name="agent-prompt", text="agent", prompt_type="system")
    assign_agent = PromptAssignment(
        prompt_id=agent_p.id,
        component_role=component_role,
        stage=component_role,
        scope="agent",
        agent_id=agent_id,
        created_by="test"
    )
    db.add(assign_agent)
    db.commit()

    # resolve with agent_id -> should pick agent
    resolved = selector.resolve(component_role=component_role, agent_id=agent_id)
    assert resolved["source"] == "agent"
    assert resolved["prompt_text"] == "agent"

    # create experiment assignment
    experiment_id = uuid4()
    exp_p = create_prompt(svc, name="exp-prompt", text="experiment", prompt_type="system")
    assign_exp = PromptAssignment(
        prompt_id=exp_p.id,
        component_role=component_role,
        stage=component_role,
        scope="experiment",
        experiment_id=experiment_id,
        created_by="test"
    )
    db.add(assign_exp)
    db.commit()

    # resolve with experiment context metadata -> should pick experiment
    resolved = selector.resolve(component_role=component_role, context_metadata={"experiment_id": str(experiment_id)})
    assert resolved["source"] == "experiment"
    assert resolved["prompt_text"] == "experiment"

    # cleanup created assignments
    db.query(PromptAssignment).filter(PromptAssignment.component_role == component_role).delete()
    db.commit()


