"""Detailed tests for Ollama connection"""
import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

import httpx
from app.core.config import get_settings
from app.core.ollama_client import get_ollama_client


async def test_direct_connection():
    """Test direct connection to Ollama instances"""
    print("=" * 60)
    print("TEST 1: Direct Connection to Ollama Instances")
    print("=" * 60)
    
    settings = get_settings()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test Instance 1
        print(f"\n1. Testing Instance 1:")
        print(f"   URL: {settings.ollama_url_1}")
        print(f"   Model: {settings.ollama_model_1}")
        
        try:
            # Try different endpoints
            endpoints = [
                "/api/tags",
                "/api/version",
                "/api/ps",  # List running models
            ]
            
            for endpoint in endpoints:
                try:
                    url = settings.ollama_url_1.replace("/v1", "") + endpoint
                    print(f"\n   Testing endpoint: {url}")
                    response = await client.get(url, timeout=5.0)
                    print(f"   Status: {response.status_code}")
                    if response.status_code == 200:
                        print(f"   ✓ Success!")
                        try:
                            data = response.json()
                            print(f"   Response (first 200 chars): {str(data)[:200]}")
                        except:
                            print(f"   Response (text): {response.text[:200]}")
                    else:
                        print(f"   ✗ Error: {response.status_code}")
                        print(f"   Response: {response.text[:200]}")
                except httpx.ConnectError as e:
                    print(f"   ✗ Connection Error: {e}")
                except httpx.TimeoutException:
                    print(f"   ✗ Timeout")
                except Exception as e:
                    print(f"   ✗ Error: {type(e).__name__}: {e}")
        
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        
        # Test Instance 2
        print(f"\n2. Testing Instance 2:")
        print(f"   URL: {settings.ollama_url_2}")
        print(f"   Model: {settings.ollama_model_2}")
        
        try:
            for endpoint in endpoints:
                try:
                    url = settings.ollama_url_2.replace("/v1", "") + endpoint
                    print(f"\n   Testing endpoint: {url}")
                    response = await client.get(url, timeout=5.0)
                    print(f"   Status: {response.status_code}")
                    if response.status_code == 200:
                        print(f"   ✓ Success!")
                        try:
                            data = response.json()
                            print(f"   Response (first 200 chars): {str(data)[:200]}")
                        except:
                            print(f"   Response (text): {response.text[:200]}")
                    else:
                        print(f"   ✗ Error: {response.status_code}")
                        print(f"   Response: {response.text[:200]}")
                except httpx.ConnectError as e:
                    print(f"   ✗ Connection Error: {e}")
                except httpx.TimeoutException:
                    print(f"   ✗ Timeout")
                except Exception as e:
                    print(f"   ✗ Error: {type(e).__name__}: {e}")
        
        except Exception as e:
            print(f"   ✗ Failed: {e}")


async def test_health_check():
    """Test health check method"""
    print("\n" + "=" * 60)
    print("TEST 2: Health Check Method")
    print("=" * 60)
    
    client = get_ollama_client()
    
    for i, instance in enumerate(client.instances, 1):
        print(f"\n{i}. Testing instance: {instance.model}")
        print(f"   URL: {instance.url}")
        
        try:
            health = await client.health_check(instance)
            print(f"   Health check result: {'✓ Available' if health else '✗ Unavailable'}")
            
            if not health:
                # Try to diagnose
                print(f"   Diagnosing...")
                async with httpx.AsyncClient(timeout=5.0) as http_client:
                    # Try base URL without /v1
                    base_url = instance.url.replace("/v1", "")
                    try:
                        response = await http_client.get(f"{base_url}/api/tags", timeout=5.0)
                        print(f"   Direct GET /api/tags: {response.status_code}")
                    except Exception as e:
                        print(f"   Direct GET failed: {type(e).__name__}: {e}")
        except Exception as e:
            print(f"   ✗ Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()


async def test_ollama_client_methods():
    """Test Ollama client internal methods"""
    print("\n" + "=" * 60)
    print("TEST 3: Ollama Client Internal Methods")
    print("=" * 60)
    
    client = get_ollama_client()
    
    print(f"\n1. Client instances:")
    for i, instance in enumerate(client.instances, 1):
        print(f"   {i}. {instance.model}")
        print(f"      URL: {instance.url}")
        print(f"      Capabilities: {instance.capabilities}")
        print(f"      Max concurrent: {instance.max_concurrent}")
    
    print(f"\n2. Testing _get_client method:")
    for instance in client.instances:
        try:
            http_client = await client._get_client(instance)
            print(f"   {instance.model}: Client created")
            print(f"      Base URL: {http_client.base_url}")
        except Exception as e:
            print(f"   {instance.model}: ✗ Error: {e}")


async def test_generate_endpoint():
    """Test if generate endpoint works"""
    print("\n" + "=" * 60)
    print("TEST 4: Generate Endpoint (if available)")
    print("=" * 60)
    
    settings = get_settings()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try to generate with Instance 1
        print(f"\n1. Trying to generate with Instance 1:")
        try:
            # Use /api/generate endpoint
            base_url = settings.ollama_url_1.replace("/v1", "")
            url = f"{base_url}/api/generate"
            
            payload = {
                "model": settings.ollama_model_1,
                "prompt": "Say 'test'",
                "stream": False
            }
            
            print(f"   URL: {url}")
            print(f"   Payload: {payload}")
            
            response = await client.post(url, json=payload, timeout=30.0)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Success!")
                print(f"   Response: {data.get('response', 'N/A')[:100]}")
            else:
                print(f"   ✗ Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
        
        except httpx.ConnectError as e:
            print(f"   ✗ Connection Error: Can't connect to {settings.ollama_url_1}")
            print(f"   Details: {e}")
        except httpx.TimeoutException:
            print(f"   ✗ Timeout (30s)")
        except Exception as e:
            print(f"   ✗ Error: {type(e).__name__}: {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("OLLAMA CONNECTION DIAGNOSTICS")
    print("=" * 60)
    
    # Show configuration
    print("\nConfiguration:")
    settings = get_settings()
    print(f"  Instance 1: {settings.ollama_url_1} / {settings.ollama_model_1}")
    print(f"  Instance 2: {settings.ollama_url_2} / {settings.ollama_model_2}")
    
    await test_direct_connection()
    await test_health_check()
    await test_ollama_client_methods()
    await test_generate_endpoint()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

