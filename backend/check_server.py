"""Quick server check"""
import sys

import httpx

try:
    response = httpx.get("http://localhost:8000/health", timeout=2.0)
    print(f"✅ Server is running: {response.status_code}")
    print(f"   Response: {response.json()}")
    sys.exit(0)
except httpx.ConnectError:
    print("❌ Server is not running")
    print("   Start it with: python backend/main.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

