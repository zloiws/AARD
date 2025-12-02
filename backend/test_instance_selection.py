"""Test instance selection logic"""
import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from app.core.ollama_client import get_ollama_client

async def test_instance_selection():
    client = get_ollama_client()
    
    print("=" * 60)
    print("TEST: Instance Selection Logic")
    print("=" * 60)
    
    print("\n1. Configured instances:")
    for i, inst in enumerate(client.instances, 1):
        print(f"   Instance {i}:")
        print(f"     URL: {inst.url}")
        print(f"     Model: {inst.model}")
        print(f"     Capabilities: {inst.capabilities}")
    
    print("\n2. Test 1: Select model with server URL (10.39.0.6)")
    print("   Request: server=10.39.0.6:11434/v1, model=gemma3:4b")
    try:
        response = await client.generate(
            prompt="Say 'test1'",
            model="gemma3:4b",
            server_url="http://10.39.0.6:11434/v1"
        )
        print(f"   ✓ Response model: {response.model}")
        print(f"   ✓ Response: {response.response[:50]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n3. Test 2: Select model with server URL (10.39.0.101)")
    print("   Request: server=10.39.0.101:11434/v1, model=qwen3-vl:8b")
    try:
        response = await client.generate(
            prompt="Say 'test2'",
            model="qwen3-vl:8b",
            server_url="http://10.39.0.101:11434/v1"
        )
        print(f"   ✓ Response model: {response.model}")
        print(f"   ✓ Response: {response.response[:50]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n4. Test 3: Auto-select (no server, no model)")
    print("   Request: task_type=general_chat")
    try:
        response = await client.generate(
            prompt="Say 'test3'",
            task_type="general_chat"
        )
        print(f"   ✓ Response model: {response.model}")
        print(f"   ✓ Response: {response.response[:50]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_instance_selection())

