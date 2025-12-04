"""
Clear database and automatically restore Ollama servers
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import clear database function
from scripts.clear_database import clear_database
from scripts.restore_servers import restore_servers

if __name__ == "__main__":
    print("=" * 70)
    print(" Database Clear and Server Restoration")
    print("=" * 70 + "\n")
    
    # Clear database
    if clear_database():
        print("\n" + "=" * 70)
        print(" Automatically restoring servers...")
        print("=" * 70 + "\n")
        
        # Restore servers
        restore_servers()
        
        print("\n✅ Database cleared and servers restored successfully!")
    else:
        print("\n❌ Failed to clear database")
        sys.exit(1)

