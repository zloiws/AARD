"""
Diagnostic script to reproduce procedural-memory matching used by tests.
Creates an agent, saves a procedural AgentMemory, then calls PlanningService._apply_procedural_memory_patterns
and prints diagnostics to stdout.
Run from project root: python -u backend/scripts/diag_procedural_pattern.py
"""
import asyncio
from uuid import uuid4
import json

from app.core.database import SessionLocal, Base, engine
from app.models.agent import Agent
from app.models.agent_memory import MemoryType, AgentMemory
from app.services.memory_service import MemoryService
from app.services.planning_service import PlanningService
from datetime import datetime, timezone


def main():
    print("DIAG: starting procedural pattern diagnostic")
    # ensure tables exist (safe to call)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("DIAG: create_all error:", e)

    db = SessionLocal()
    try:
        # create agent
        agent = Agent(id=uuid4(), name=f"DiagAgent {uuid4()}", description="diag", system_prompt="You are diag")
        db.add(agent)
        db.commit()
        db.refresh(agent)
        print("DIAG: created agent", agent.id)

        # create procedural memory via MemoryService
        mem_svc = MemoryService(db)
        content = {
            "pattern_type": "planning_strategy",
            "task_pattern": "test task",
            "success_rate": 0.9,
            "strategy": {
                "approach": "test approach",
                "steps_template": [{"step_id": "1", "description": "Pattern step 1"}]
            }
        }
        mem = mem_svc.save_memory(
            agent_id=agent.id,
            memory_type=MemoryType.PROCEDURAL.value,
            content=content,
            summary=None,
            importance=0.8,
        )
        print("DIAG: saved procedural memory id=", mem.id)

        # show raw AgentMemory rows
        rows = db.query(AgentMemory).filter(AgentMemory.agent_id == agent.id).all()
        print("DIAG: agent_memory_count=", len(rows))
        for i, r in enumerate(rows):
            print(f"DIAG: row[{i}] id={r.id} type={r.memory_type} summary={r.summary} content={json.dumps(r.content)}")

        # call planning_service selector
        planning = PlanningService(db)
        res = asyncio.run(planning._apply_procedural_memory_patterns(task_description="test task for pattern matching", agent_id=agent.id))
        print("DIAG: _apply_procedural_memory_patterns result:", res)

    finally:
        try:
            db.close()
        except:
            pass


if __name__ == "__main__":
    main()


