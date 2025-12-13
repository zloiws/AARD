#!/usr/bin/env python3
from __future__ import annotations
import os, asyncio, json

os.environ.setdefault("PYTHONPATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.services.planning_service import PlanningService

async def main():
    db = SessionLocal()
    try:
        svc = PlanningService(db)
        task_description = """Create a complete e-commerce application with:
        1. User authentication and authorization
        2. Product catalog with categories
        3. Shopping cart functionality
        4. Order processing
        5. Payment integration
        6. Admin dashboard
        7. Email notifications
        8. Search functionality"""
        plan = await svc.generate_plan(task_description=task_description, context=None)
        print("Plan created id:", plan.id)
        print("Plan steps count:", len(plan.steps) if plan.steps else 0)
        # Inspect task context traces
        from app.models.task import Task
        task = db.query(Task).filter(Task.id == plan.task_id).first()
        if task:
            ctx = task.get_context()
            print("Context plan.steps_count:", ctx.get("plan", {}).get("steps_count"))
            print("Planning trace last entries:")
            for e in (ctx.get("planning_trace", []) or [])[-10:]:
                print(json.dumps(e, ensure_ascii=False))
        else:
            print("Task not found for plan")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())


