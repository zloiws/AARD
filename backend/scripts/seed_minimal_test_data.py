"""Seed minimal data for integration tests"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.models.agent import Agent
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer


def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Ensure there's an active server 10.39.0.6 and model with planning capability
    server = db.query(OllamaServer).filter(OllamaServer.url.ilike('%10.39.0.6%')).first()
    if not server:
        server = OllamaServer(
            id=uuid4(),
            name='ollama_10_39_0_6',
            url='http://10.39.0.6:11434/v1',
            is_active=True,
            is_default=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(server)
        db.commit()
    else:
        server.is_active = True
        db.commit()

    # Ensure a model exists and is active with planning capability
    model = db.query(OllamaModel).filter(
        OllamaModel.server_id == server.id
    ).first()
    if not model:
        model = OllamaModel(
            id=uuid4(),
            server_id=server.id,
            name='qwen3-coder-seed',
            model_name='qwen3-coder:seed',
            is_active=True,
            capabilities=['planning', 'reasoning'],
            details={
                'avg_quality_score': {'planning': 0.8},
                'avg_response_time': {'planning': 1.0}
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(model)
        db.commit()
    else:
        model.is_active = True
        model.capabilities = model.capabilities or []
        if 'planning' not in [c.lower() for c in model.capabilities]:
            model.capabilities = (model.capabilities or []) + ['planning']
        model.details = model.details or {}
        model.details.setdefault('avg_quality_score', {}).setdefault('planning', 0.8)
        model.details.setdefault('avg_response_time', {}).setdefault('planning', 1.0)
        db.commit()

    # Ensure PlannerAgent exists and is active
    planner = db.query(Agent).filter(Agent.name == 'PlannerAgent').first()
    if not planner:
        planner = Agent(
            id=uuid4(),
            name='PlannerAgent',
            description='Seeded Planner Agent',
            status='active',
            capabilities=['planning', 'reasoning'],
            created_at=datetime.now(timezone.utc)
        )
        db.add(planner)
        db.commit()
    else:
        planner.status = 'active'
        planner.capabilities = planner.capabilities or []
        if 'planning' not in [c.lower() for c in planner.capabilities]:
            planner.capabilities = (planner.capabilities or []) + ['planning']
        db.commit()

    print("Seed complete.")


if __name__ == '__main__':
    main()


