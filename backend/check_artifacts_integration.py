#!/usr/bin/env python3
"""Check if artifacts are created in planning integration"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.planning_service import PlanningService
from app.models.task import Task
import asyncio

async def check_artifacts():
    """Check artifact creation in planning"""
    db = SessionLocal()
    try:
        ps = PlanningService(db)

        # Create a plan for a task that should generate artifacts
        plan = await ps.generate_plan('Create a tool for data processing and implement a REST API')
        task = db.query(Task).filter(Task.id == plan.task_id).first()
        context = task.get_context()

        print('Task context artifacts:')
        artifacts = context.get('artifacts', [])
        print(f'Number of artifacts: {len(artifacts)}')
        for i, art in enumerate(artifacts, 1):
            art_type = art.get('type', 'unknown')
            art_name = art.get('name', 'unnamed')
            art_desc = art.get('description', 'no desc')
            print(f'{i}. {art_type}: {art_name} - {art_desc}')

        print('\nPlan steps:')
        for i, step in enumerate(plan.steps or [], 1):
            step_desc = step.get('description', 'no desc')
            print(f'{i}. {step_desc}')

        return len(artifacts) > 0

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(check_artifacts())
    print(f'\nArtifacts created: {success}')
    sys.exit(0 if success else 1)
