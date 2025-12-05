"""
Script to import benchmark tasks from JSON files
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.services.benchmark_service import BenchmarkService

def main():
    """Import benchmark tasks from data/benchmarks directory"""
    print("=" * 70)
    print(" Importing Benchmark Tasks")
    print("=" * 70 + "\n")
    
    db = SessionLocal()
    try:
        service = BenchmarkService(db)
        
        # Get benchmarks directory
        benchmarks_dir = backend_dir / "data" / "benchmarks"
        
        if not benchmarks_dir.exists():
            print(f"❌ Directory {benchmarks_dir} does not exist!")
            print("   Creating directory...")
            benchmarks_dir.mkdir(parents=True, exist_ok=True)
            print(f"   Please add JSON files with benchmark tasks to {benchmarks_dir}")
            return
        
        print(f"Loading tasks from: {benchmarks_dir}\n")
        
        # Import tasks
        stats = service.import_tasks_from_directory(benchmarks_dir)
        
        print("\n" + "=" * 70)
        print(" Import Statistics")
        print("=" * 70)
        print(f"Total tasks found: {stats['total']}")
        print(f"✅ Imported: {stats['imported']}")
        print(f"⏭️  Skipped (already exist): {stats['skipped']}")
        print(f"❌ Errors: {stats['errors']}")
        
        # Show counts by type
        print("\n" + "=" * 70)
        print(" Tasks by Type")
        print("=" * 70)
        counts = service.get_task_count_by_type()
        for task_type, count in counts.items():
            print(f"  {task_type}: {count}")
        
        print("\n✅ Import completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

