"""Test actual model generation"""
import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from app.core.ollama_client import get_ollama_client, TaskType
import httpx


async def test_direct_ollama_request():
    """Test direct request to Ollama"""
    print("=" * 60)
    print("TEST 1: Direct Ollama API Request")
    print("=" * 60)
    
    # Test Instance 1
    print("\n1. Testing Instance 1 (deepseek-r1)")
    base_url = "http://10.39.0.101:11434"
    model = "huihui_ai/deepseek-r1-abliterated:8b"
    
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
            payload = {
                "model": model,
                "prompt": "Say 'Hello' in one word.",
                "stream": False
            }
            
            print(f"   URL: {base_url}/api/generate")
            print(f"   Model: {model}")
            print(f"   Payload: {payload}")
            print("   Sending request...")
            
            response = await client.post("/api/generate", json=payload, timeout=60.0)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Success!")
                print(f"   Response: {data.get('response', 'N/A')}")
                print(f"   Done: {data.get('done', False)}")
                print(f"   Total duration: {data.get('total_duration', 0) / 1000000000:.2f}s")
                
                # Check if model is now loaded
                ps_response = await client.get("/api/ps", timeout=5.0)
                if ps_response.status_code == 200:
                    ps_data = ps_response.json()
                    loaded_models = ps_data.get("models", [])
                    print(f"\n   Models in GPU: {len(loaded_models)}")
                    for m in loaded_models:
                        print(f"      - {m.get('name')}")
            else:
                print(f"   ✗ Error: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
    
    except httpx.TimeoutException:
        print("   ✗ Timeout (60s)")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_ollama_client():
    """Test through Ollama client"""
    print("\n" + "=" * 60)
    print("TEST 2: Through Ollama Client")
    print("=" * 60)
    
    client = get_ollama_client()
    
    print("\n1. Testing generate() method")
    try:
        print("   Sending request to generate...")
        response = await client.generate(
            prompt="Say 'Hello' in one word.",
            task_type=TaskType.GENERAL_CHAT,
            temperature=0.7
        )
        
        print(f"   ✓ Success!")
        print(f"   Model: {response.model}")
        print(f"   Response: {response.response}")
        print(f"   Done: {response.done}")
        
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_chat_api():
    """Test through Chat API"""
    print("\n" + "=" * 60)
    print("TEST 3: Through Chat API")
    print("=" * 60)
    
    import requests
    
    try:
        print("   Sending POST /api/chat/...")
        response = requests.post(
            "http://localhost:8000/api/chat/",
            json={
                "message": "Say 'Hello' in one word.",
                "task_type": "general_chat",
                "temperature": 0.7
            },
            timeout=60
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Success!")
            print(f"   Model: {data.get('model')}")
            print(f"   Response: {data.get('response')}")
            print(f"   Duration: {data.get('duration_ms')}ms")
        else:
            print(f"   ✗ Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
    
    except requests.exceptions.Timeout:
        print("   ✗ Timeout (60s)")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def check_models_status():
    """Check which models are loaded in GPU"""
    print("\n" + "=" * 60)
    print("CHECK: Models in GPU")
    print("=" * 60)
    
    servers = [
        ("Server 1", "http://10.39.0.101:11434"),
        ("Server 2", "http://10.39.0.6:11434")
    ]
    
    for name, base_url in servers:
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
                response = await client.get("/api/ps", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    print(f"\n{name}: {len(models)} models loaded")
                    for m in models:
                        print(f"  - {m.get('name')} (size: {m.get('size_vram', 0) / 1024 / 1024 / 1024:.2f} GB)")
                else:
                    print(f"\n{name}: Error {response.status_code}")
        except Exception as e:
            print(f"\n{name}: Error - {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MODEL GENERATION DIAGNOSTICS")
    print("=" * 60)
    
    # Check initial state
    await check_models_status()
    
    # Test direct request
    await test_direct_ollama_request()
    
    # Check after direct request
    print("\n" + "-" * 60)
    print("After direct request:")
    await check_models_status()
    
    # Test through client
    await test_ollama_client()
    
    # Test through API
    await test_chat_api()
    
    # Final check
    print("\n" + "-" * 60)
    print("Final state:")
    await check_models_status()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

