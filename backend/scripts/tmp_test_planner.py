from app.core.database import SessionLocal
from app.core.execution_context import ExecutionContext
from app.services.planning_service import PlanningService
import traceback

def main():
    try:
        db = SessionLocal()
        ctx = ExecutionContext.from_db_session(db)
        ps = PlanningService(ctx)
        pa = None
        try:
            pa = ps._get_planner_agent()
            print('planner_agent:', pa)
        except Exception:
            print('error while creating planner_agent via execution_context')
            traceback.print_exc()
        try:
            ps2 = PlanningService(db)
            pa2 = ps2._get_planner_agent()
            print('planner_agent with raw db:', pa2)
        except Exception:
            print('error while creating planner_agent via raw db')
            traceback.print_exc()
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    main()


