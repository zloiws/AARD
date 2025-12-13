#!/usr/bin/env python3
import asyncio
import os
from pathlib import Path
import sys

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.services.planning_service import PlanningService

async def run():
    db = SessionLocal()
    try:
        ps = PlanningService(db)
        plan = await ps.generate_plan(task_description="Write a function to calculate factorial", context=None)
        from app.models.task import Task
        task = db.query(Task).filter(Task.id == plan.task_id).first()
        print("Plan id:", plan.id)
        print("Task id:", plan.task_id)
        ctx = task.get_context()
        print("Context keys:", list(ctx.keys()) if isinstance(ctx, dict) else None)
        print("Context:", ctx)
    finally:
        db.close()

if __name__ == '__main__':
    asyncio.run(run())


