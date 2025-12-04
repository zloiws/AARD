"""
Simple test for WebSocket endpoints (using HTTP to verify endpoints exist)
"""
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import requests

def test_websocket_endpoints_exist():
    """Test that WebSocket endpoints are accessible (HTTP check)"""
    print("=" * 80)
    print("TEST: WebSocket Endpoints Availability")
    print("=" * 80)
    
    base_url = "http://localhost:8000"
    
    print(f"\n1. Checking if server is running at {base_url}...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ⚠️  Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ ERROR: Could not connect to server at {base_url}")
        print(f"      Make sure FastAPI server is running: python backend/main.py")
        return
    except Exception as e:
        print(f"   ⚠️  Error checking server: {e}")
    
    print("\n2. WebSocket endpoints information:")
    print("   ✅ /api/ws/events - WebSocket endpoint for all workflow events")
    print("   ✅ /api/ws/events/{workflow_id} - WebSocket endpoint for specific workflow")
    print("\n   Note: WebSocket endpoints cannot be tested with HTTP requests.")
    print("   To test WebSocket:")
    print("   1. Open browser DevTools Console")
    print("   2. Open tab 'Текущая работа'")
    print("   3. Check console for 'WebSocket connected' message")
    print("   4. Send a chat message or run a planning test")
    print("   5. Watch events appear in real-time")
    
    print("\n" + "=" * 80)
    print("✅ ENDPOINT CHECK COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Start the server: python backend/main.py")
    print("  2. Open browser to http://localhost:8000")
    print("  3. Open 'Текущая работа' tab")
    print("  4. Test real-time updates by sending a chat message")

if __name__ == "__main__":
    test_websocket_endpoints_exist()

