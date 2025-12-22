"""Test chat with specific model selection"""
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

BASE_URL = "http://localhost:8000"

print("Testing Chat with Model Selection\n")

# Test 1: Auto-select model
print("1. Testing auto-select (no model specified)")
try:
    response = requests.post(
        f"{BASE_URL}/api/chat/",
        json={
            "message": "Say 'test' in one word",
            "task_type": "general_chat"
        },
        timeout=30
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Model: {data.get('model')}")
        print(f"   ✓ Response: {data.get('response')}")
        print(f"   ✓ Duration: {data.get('duration_ms')}ms")
    else:
        print(f"   ✗ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Specific model
print("\n2. Testing with specific model")
try:
    response = requests.post(
        f"{BASE_URL}/api/chat/",
        json={
            "message": "Say 'test' in one word",
            "model": "huihui_ai/deepseek-r1-abliterated:8b",
            "task_type": "general_chat"
        },
        timeout=30
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Model: {data.get('model')}")
        print(f"   ✓ Response: {data.get('response')}")
        print(f"   ✓ Duration: {data.get('duration_ms')}ms")
    else:
        print(f"   ✗ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: Model from second server
print("\n3. Testing with model from second server")
try:
    response = requests.post(
        f"{BASE_URL}/api/chat/",
        json={
            "message": "Say 'test' in one word",
            "model": "qwen3-coder:30b-a3b-q4_K_M",
            "task_type": "code_generation"
        },
        timeout=60  # Longer timeout for first load
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Model: {data.get('model')}")
        print(f"   ✓ Response: {data.get('response')}")
        print(f"   ✓ Duration: {data.get('duration_ms')}ms")
    else:
        print(f"   ✗ Error: {response.text[:200]}")
except requests.exceptions.Timeout:
    print("   ⚠ Timeout (60s) - модель может загружаться в GPU")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n✓ Testing complete!")

