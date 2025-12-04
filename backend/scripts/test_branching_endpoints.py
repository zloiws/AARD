"""
Test branching visualization API endpoints
"""
import sys
import requests
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

BASE_URL = "http://localhost:8000"


def print_separator(title: str):
    """Print test separator"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


def test_endpoints():
    """Test API endpoints"""
    print_separator("Testing Branching Visualization API Endpoints")
    
    # Test 1: Check if server is running
    print("📝 Test 1: Checking if server is running...")
    try:
        response = requests.get(f"{BASE_URL}/api", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the server first.")
        print("   Run: cd backend && python main.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Get active tasks
    print("\n📝 Test 2: Testing /api/current-work/tasks endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/current-work/tasks", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Active tasks endpoint working")
            print(f"   Total active tasks: {data.get('total', 0)}")
            if data.get('tasks'):
                print(f"   Sample task: {data['tasks'][0].get('description', 'N/A')[:50]}...")
                print(f"   Status: {data['tasks'][0].get('status', 'N/A')}")
                print(f"   Progress: {data['tasks'][0].get('progress_percent', 0)}%")
        else:
            print(f"⚠️ Endpoint returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Get latest summaries
    print("\n📝 Test 3: Testing /api/model-logs/summaries/latest endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/model-logs/summaries/latest?limit=5", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Summary endpoint working")
            print(f"   Total summaries: {data.get('total', 0)}")
            if data.get('summaries'):
                summary = data['summaries'][0]
                print(f"   Sample task: {summary.get('task_description', 'N/A')[:50]}...")
                print(f"   Status: {summary.get('status', 'N/A')}")
                print(f"   Plans: {len(summary.get('plans', []))}")
                print(f"   Replanning history: {len(summary.get('replanning_history', []))}")
        else:
            print(f"⚠️ Endpoint returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(" ✅ Endpoint tests completed!")
    print("=" * 70 + "\n")
    print("💡 Note: To see full functionality, create some tasks with plans first.")
    
    return True


if __name__ == "__main__":
    success = test_endpoints()
    sys.exit(0 if success else 1)

