#!/usr/bin/env python3
"""Test artifact auto-generation"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.planning_service import PlanningService

def test_artifact_generation():
    """Test the new artifact auto-generation functionality"""
    db = SessionLocal()
    try:
        ps = PlanningService(db)

        # Test steps that should generate artifacts
        test_steps = [
            {'step_id': 'step_1', 'description': 'Create a tool for data processing', 'type': 'implementation'},
            {'step_id': 'step_2', 'description': 'Implement a REST API endpoint', 'type': 'api_creation'},
            {'step_id': 'step_3', 'description': 'Design an agent for task automation', 'type': 'agent_creation'}
        ]

        task_desc = 'Build a data processing system'
        existing_artifacts = []

        generated = ps._auto_generate_artifacts_from_steps(test_steps, task_desc, existing_artifacts)

        print('Generated artifacts:')
        for art in generated:
            print(f'  - {art["type"]}: {art["name"]} - {art["description"]}')

        print(f'Generated {len(generated)} artifacts')

        return len(generated) > 0

    except Exception as e:
        print(f'Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_artifact_generation()
    sys.exit(0 if success else 1)
