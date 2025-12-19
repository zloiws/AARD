"""Test new features"""
import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

import requests

BASE_URL = "http://localhost:8000"

async def test_models_api():
    """Test models API"""
    print("=" * 60)
    print("TESTING MODELS API")
    print("=" * 60)
    
    # Test list servers
    print("\n1. Testing GET /api/models/servers")
    try:
        response = requests.get(f"{BASE_URL}/api/models/servers", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            servers = data.get("servers", [])
            print(f"   ✓ Found {len(servers)} servers")
            for server in servers:
                print(f"      - {server.get('url')}: {len(server.get('models', []))} models, available: {server.get('available')}")
        else:
            print(f"   ✗ Error: {response.status_code}")
            print(f"   {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test get models from specific server
    print("\n2. Testing GET /api/models/server/models")
    try:
        # Use first configured server
        server_url = "http://10.39.0.101:11434/v1"
        response = requests.get(f"{BASE_URL}/api/models/server/models?server_url={server_url}", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"   ✓ Found {len(models)} models on server")
            for model in models[:3]:  # Show first 3
                print(f"      - {model.get('name')} ({model.get('size', 0) / 1024 / 1024 / 1024:.2f} GB)")
        else:
            print(f"   ✗ Error: {response.status_code}")
            print(f"   {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def test_chat_session():
    """Test chat session"""
    print("\n" + "=" * 60)
    print("TESTING CHAT SESSION")
    print("=" * 60)
    
    # Test create session
    print("\n1. Testing POST /api/chat/session")
    try:
        response = requests.post(f"{BASE_URL}/api/chat/session", json={"title": "Test session"}, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            print(f"   ✓ Session created: {session_id}")
            
            # Test get session
            print("\n2. Testing GET /api/chat/session/{session_id}")
            response = requests.get(f"{BASE_URL}/api/chat/session/{session_id}", timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Session retrieved: {len(data.get('messages', []))} messages")
            else:
                print(f"   ✗ Error: {response.status_code}")
        else:
            print(f"   ✗ Error: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


if __name__ == "__main__":
    print("\nTesting new features...\n")
    
    # Test models API
    asyncio.run(test_models_api())
    
    # Test chat session
    test_chat_session()
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)

