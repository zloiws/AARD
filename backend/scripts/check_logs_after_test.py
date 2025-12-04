"""
Check if model logs were saved to Digital Twin context after test
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.task import Task
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

def check_latest_task_logs():
    """Check logs in the latest task"""
    db = SessionLocal()
    
    try:
        # Get latest task (created in last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        task = db.query(Task).filter(
            Task.created_at >= one_hour_ago
        ).order_by(Task.created_at.desc()).first()
        
        if not task:
            print("❌ No tasks found in the last hour")
            return
        
        print(f"✅ Found task: {task.id}")
        print(f"   Description: {task.description[:60]}...")
        print(f"   Created: {task.created_at}")
        
        # Get context
        context = task.get_context()
        
        if not context:
            print("❌ No context found in task")
            return
        
        print(f"\n📋 Context keys: {list(context.keys())}")
        
        # Check model logs
        model_logs = context.get("model_logs", [])
        
        if not model_logs:
            print("\n❌ No model_logs found in Digital Twin context")
            print(f"   Available keys: {list(context.keys())}")
        else:
            print(f"\n✅ Found {len(model_logs)} model log entries!")
            print("\n📝 Log entries:")
            for i, log in enumerate(model_logs[:5], 1):  # Show first 5
                log_type = log.get("type", "unknown")
                model = log.get("model", "unknown")
                stage = log.get("stage", "none")
                timestamp = log.get("timestamp", "unknown")
                print(f"   {i}. [{log_type}] {model} (stage: {stage}) at {timestamp[:19]}")
                content_preview = str(log.get("content", ""))[:50]
                if content_preview:
                    print(f"      Content: {content_preview}...")
            if len(model_logs) > 5:
                print(f"   ... and {len(model_logs) - 5} more logs")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" CHECKING MODEL LOGS IN DIGITAL TWIN CONTEXT")
    print("=" * 70 + "\n")
    
    check_latest_task_logs()

