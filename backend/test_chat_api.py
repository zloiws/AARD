"""Test chat API"""
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

import requests

BASE_URL = "http://localhost:8000"

print("Testing Chat API...\n")

# Wait for server
time.sleep(2)

# Test list models
print("1. Testing GET /api/chat/models")
try:
    response = requests.get(f"{BASE_URL}/api/chat/models", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Models: {len(data.get('models', []))}")
        for model in data.get('models', []):
            print(f"     - {model.get('model')}: {model.get('capabilities')}")
        print("   ✓ Models endpoint OK\n")
    else:
        print(f"   ✗ Unexpected status: {response.status_code}\n")
except requests.exceptions.ConnectionError:
    print("   ✗ Connection failed - is the server running?\n")
except Exception as e:
    print(f"   ✗ Error: {e}\n")

# Test chat endpoint (if Ollama is available)
print("2. Testing POST /api/chat/")
print("   (This may fail if Ollama instances are not accessible)")
try:
    response = requests.post(
        f"{BASE_URL}/api/chat/",
        json={
            "message": "Say 'Hello' in one word.",
            "task_type": "general_chat",
            "temperature": 0.7
        },
        timeout=30
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Model: {data.get('model')}")
        print(f"   Task Type: {data.get('task_type')}")
        print(f"   Response: {data.get('response')[:100]}...")
        print(f"   Duration: {data.get('duration_ms')}ms")
        print("   ✓ Chat endpoint OK\n")
    else:
        print(f"   Response: {response.text}")
        print(f"   ✗ Unexpected status: {response.status_code}\n")
except requests.exceptions.ConnectionError:
    print("   ✗ Connection failed\n")
except requests.exceptions.Timeout:
    print("   ⚠ Request timed out (Ollama may be slow or unavailable)\n")
except Exception as e:
    print(f"   ⚠ Error: {e}\n")

print("Testing complete!")

