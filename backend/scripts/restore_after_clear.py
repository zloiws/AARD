"""
Restore database after clearing
This script restores:
1. All tables (if missing)
2. Ollama servers from .env
3. Initial prompts (optional)
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.core.database import SessionLocal, Base, engine
from app.models import *  # Import all models
from sqlalchemy import inspect
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def restore_tables():
    """Restore all tables if missing"""
    print("=" * 70)
    print(" Restoring Database Tables")
    print("=" * 70 + "\n")
    
    try:
        # Check existing tables
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        # Expected tables from models
        expected_tables = set(Base.metadata.tables.keys())
        
        missing_tables = expected_tables - existing_tables
        
        if missing_tables:
            print(f"Found {len(missing_tables)} missing tables")
            print("Creating missing tables...\n")
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            
            # Verify
            inspector = inspect(engine)
            new_tables = set(inspector.get_table_names())
            created = new_tables - existing_tables
            
            print(f"✅ Created {len(created)} tables:")
            for table in sorted(created):
                if table != 'alembic_version':
                    print(f"   ✓ {table}")
        else:
            print("✅ All tables exist")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error restoring tables: {e}")
        import traceback
        traceback.print_exc()
        return False


def restore_servers():
    """Restore Ollama servers from .env"""
    print("=" * 70)
    print(" Restoring Ollama Servers")
    print("=" * 70 + "\n")
    
    try:
        from scripts.restore_servers import restore_servers
        return restore_servers()
    except Exception as e:
        print(f"❌ Error restoring servers: {e}")
        import traceback
        traceback.print_exc()
        return False


def restore_initial_prompts():
    """Restore initial prompts for PlanningService"""
    print("=" * 70)
    print(" Restoring Initial Prompts")
    print("=" * 70 + "\n")
    
    db = SessionLocal()
    try:
        from app.services.prompt_service import PromptService
        from app.models.prompt import PromptType
        
        service = PromptService(db)
        
        # Check if prompts already exist
        existing = service.list_prompts(prompt_type=PromptType.SYSTEM, limit=10)
        if existing:
            print(f"Found {len(existing)} existing prompts. Skipping creation.")
            return True
        
        print("Creating initial prompts...\n")
        
        # Task analysis prompt
        analysis_prompt = service.get_active_prompt("task_analysis", PromptType.SYSTEM, level=0)
        if not analysis_prompt:
            analysis_prompt = service.create_prompt(
                name="task_analysis",
                prompt_text="""You are an expert at task analysis and strategic planning.
Analyze the task and create a strategy that includes:
1. approach: General approach to solving the task
2. assumptions: List of assumptions made
3. constraints: List of constraints and limitations
4. success_criteria: List of criteria for successful completion

Return a JSON object with these fields. Only return valid JSON, no additional text.""",
                prompt_type=PromptType.SYSTEM,
                level=0,
                created_by="system"
            )
            print(f"✅ Created: {analysis_prompt.name}")
        else:
            print(f"⏭️  Already exists: {analysis_prompt.name}")
        
        # Task decomposition prompt
        decomposition_prompt = service.get_active_prompt("task_decomposition", PromptType.SYSTEM, level=0)
        if not decomposition_prompt:
            decomposition_prompt = service.create_prompt(
                name="task_decomposition",
                prompt_text="""You are an expert at breaking down complex tasks into executable steps.
Create a detailed plan with steps. Each step should have:
- step_id: unique identifier (e.g., "step_1", "step_2")
- description: clear description of what to do
- type: one of "action", "decision", "validation", "approval"
- inputs: what inputs are needed (object)
- expected_outputs: what outputs are expected (object)
- timeout: timeout in seconds (integer)
- retry_policy: {max_attempts: 3, delay: 10}
- dependencies: list of step_ids that must complete first (array)
- approval_required: boolean
- risk_level: "low", "medium", or "high"
- function_call: (optional) if step requires code execution, include function call in format:
  {
    "function": "code_execution_tool",
    "parameters": {
      "code": "python code here",
      "language": "python"
    }
  }

IMPORTANT: For steps that require code execution, use function_call instead of generating code directly.
This ensures safe execution in a sandboxed environment.

Return a JSON array of steps. Only return valid JSON, no additional text.""",
                prompt_type=PromptType.SYSTEM,
                level=0,
                created_by="system"
            )
            print(f"✅ Created: {decomposition_prompt.name}")
        else:
            print(f"⏭️  Already exists: {decomposition_prompt.name}")
        
        # Replan prompt
        replan_prompt = service.get_active_prompt("task_replan", PromptType.SYSTEM, level=0)
        if not replan_prompt:
            replan_prompt = service.create_prompt(
                name="task_replan",
                prompt_text="""You are an expert at replanning tasks when execution fails or requirements change.
Analyze the current situation and create a new plan.

Context:
- Original task: {original_task}
- Current status: {current_status}
- Issues encountered: {issues}
- Completed steps: {completed_steps}

Create a new plan that:
1. Addresses the issues encountered
2. Builds on completed steps
3. Adjusts approach based on new information
4. Maintains consistency with original goals

Return a JSON object with:
- revised_approach: Updated approach
- new_steps: Array of new/adjusted steps
- removed_steps: Array of step_ids to remove
- modified_steps: Array of step_ids to modify with new details
- reasoning: Explanation of changes

Only return valid JSON, no additional text.""",
                prompt_type=PromptType.SYSTEM,
                level=0,
                created_by="system"
            )
            print(f"✅ Created: {replan_prompt.name}")
        else:
            print(f"⏭️  Already exists: {replan_prompt.name}")
        
        print("\n✅ Initial prompts restored!")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error restoring prompts: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Main restoration function"""
    print("=" * 70)
    print(" Database Restoration After Clear")
    print("=" * 70 + "\n")
    
    success = True
    
    # Step 1: Restore tables
    if not restore_tables():
        success = False
    
    # Step 2: Restore servers
    if not restore_servers():
        success = False
    
    # Step 3: Restore initial prompts
    if not restore_initial_prompts():
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print(" ✅ Database restoration completed successfully!")
    else:
        print(" ⚠️  Database restoration completed with warnings")
    print("=" * 70 + "\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

