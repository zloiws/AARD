"""Test API endpoints for evolution system"""
import asyncio
import json
from typing import Any, Dict

import httpx

BASE_URL = "http://localhost:8000"

async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ Health check: {response.status_code} - {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            print("   Make sure server is running: python backend/main.py")
            return False

async def test_approvals_api():
    """Test approvals API"""
    print("\n" + "=" * 60)
    print("Testing Approvals API")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Get pending approvals
        try:
            response = await client.get(f"{BASE_URL}/api/approvals/")
            if response.status_code == 200:
                approvals = response.json()
                print(f"✅ GET /api/approvals/ - Found {len(approvals)} pending approvals")
                return True
            else:
                print(f"❌ GET /api/approvals/ - Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ GET /api/approvals/ - Error: {e}")
            return False

async def test_artifacts_api():
    """Test artifacts API"""
    print("\n" + "=" * 60)
    print("Testing Artifacts API")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # List artifacts
        try:
            response = await client.get(f"{BASE_URL}/api/artifacts/")
            if response.status_code == 200:
                artifacts = response.json()
                print(f"✅ GET /api/artifacts/ - Found {len(artifacts)} artifacts")
            else:
                print(f"❌ GET /api/artifacts/ - Status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ GET /api/artifacts/ - Error: {e}")
            return False
        
        # Create artifact (this will take time as it uses LLM)
        print("\n📝 Creating a test artifact (this may take 30-60 seconds)...")
        try:
            create_request = {
                "description": "Create a simple tool to calculate the sum of two numbers",
                "artifact_type": "tool"
            }
            response = await client.post(
                f"{BASE_URL}/api/artifacts/",
                json=create_request,
                timeout=120.0
            )
            if response.status_code == 200:
                artifact = response.json()
                print(f"✅ POST /api/artifacts/ - Created artifact: {artifact['id']}")
                print(f"   Name: {artifact['name']}")
                print(f"   Status: {artifact['status']}")
                print(f"   Security rating: {artifact.get('security_rating', 'N/A')}")
                
                # Check if approval request was created
                approval_response = await client.get(f"{BASE_URL}/api/approvals/")
                if approval_response.status_code == 200:
                    approvals = approval_response.json()
                    print(f"✅ Approval request created automatically: {len(approvals)} pending")
                
                return artifact['id']
            else:
                print(f"❌ POST /api/artifacts/ - Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except httpx.TimeoutException:
            print("⚠️ Request timed out (LLM generation takes time)")
            return None
        except Exception as e:
            print(f"❌ POST /api/artifacts/ - Error: {e}")
            import traceback
            traceback.print_exc()
            return None

async def test_prompts_api():
    """Test prompts API"""
    print("\n" + "=" * 60)
    print("Testing Prompts API")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # List prompts
        try:
            response = await client.get(f"{BASE_URL}/api/prompts/")
            if response.status_code == 200:
                prompts = response.json()
                print(f"✅ GET /api/prompts/ - Found {len(prompts)} prompts")
            else:
                print(f"❌ GET /api/prompts/ - Status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ GET /api/prompts/ - Error: {e}")
            return False
        
        # Create prompt
        try:
            create_request = {
                "name": "test_system_prompt",
                "prompt_text": "You are a helpful AI assistant.",
                "prompt_type": "system",
                "level": 1
            }
            response = await client.post(f"{BASE_URL}/api/prompts/", json=create_request)
            if response.status_code == 200:
                prompt = response.json()
                print(f"✅ POST /api/prompts/ - Created prompt: {prompt['id']}")
                print(f"   Name: {prompt['name']}")
                print(f"   Type: {prompt['prompt_type']}")
                return prompt['id']
            else:
                print(f"❌ POST /api/prompts/ - Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ POST /api/prompts/ - Error: {e}")
            return None

async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 Evolution System API Tests")
    print("=" * 60)
    
    # Test health first
    if not await test_health():
        print("\n⚠️ Server is not running. Please start it first:")
        print("   cd backend")
        print("   python main.py")
        return
    
    # Run tests
    approvals_ok = await test_approvals_api()
    artifact_id = await test_artifacts_api()
    prompt_id = await test_prompts_api()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Approvals API: {'✅ PASS' if approvals_ok else '❌ FAIL'}")
    print(f"Artifacts API: {'✅ PASS' if artifact_id else '❌ FAIL'}")
    print(f"Prompts API: {'✅ PASS' if prompt_id else '❌ FAIL'}")
    
    if approvals_ok and artifact_id and prompt_id:
        print("\n🎉 All API tests passed!")
        print(f"\n📋 Created resources:")
        print(f"   - Artifact ID: {artifact_id}")
        print(f"   - Prompt ID: {prompt_id}")
        print(f"\n💡 Next steps:")
        print(f"   1. Check approval queue: GET /api/approvals/")
        print(f"   2. Approve artifact: POST /api/approvals/{{id}}/approve")
        print(f"   3. View artifact details: GET /api/artifacts/{artifact_id}")
    else:
        print("\n⚠️ Some tests failed. Check errors above.")

if __name__ == "__main__":
    asyncio.run(main())

