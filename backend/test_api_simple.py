"""Simple API test"""
import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"

async def test():
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Test health
        print("1. Testing health...")
        r = await client.get(f"{BASE_URL}/health")
        print(f"   ✅ {r.status_code}: {r.json()}")
        
        # Test approvals
        print("\n2. Testing approvals...")
        r = await client.get(f"{BASE_URL}/api/approvals/")
        if r.status_code == 200:
            try:
                approvals = r.json()
                print(f"   ✅ {r.status_code}: {len(approvals)} pending")
            except Exception as e:
                print(f"   ⚠️ {r.status_code}: Response parsing error: {e}")
                print(f"   Response text: {r.text[:200]}")
        else:
            print(f"   ❌ {r.status_code}: {r.text[:200]}")
        
        # Test prompts - create
        print("\n3. Testing prompts - create...")
        r = await client.post(
            f"{BASE_URL}/api/prompts/",
            json={
                "name": "test_system_prompt",
                "prompt_text": "You are a helpful AI assistant.",
                "prompt_type": "system",
                "level": 1
            }
        )
        if r.status_code == 200:
            prompt = r.json()
            print(f"   ✅ Created prompt: {prompt['id']}")
            prompt_id = prompt['id']
        else:
            print(f"   ❌ {r.status_code}: {r.text}")
            return
        
        # Test prompts - get
        print("\n4. Testing prompts - get...")
        r = await client.get(f"{BASE_URL}/api/prompts/{prompt_id}")
        if r.status_code == 200:
            print(f"   ✅ Retrieved prompt: {r.json()['name']}")
        else:
            print(f"   ❌ {r.status_code}: {r.text}")
        
        # Test artifacts - create (this takes time)
        print("\n5. Testing artifacts - create (this may take 30-60 seconds)...")
        try:
            r = await client.post(
                f"{BASE_URL}/api/artifacts/",
                json={
                    "description": "Create a simple tool to add two numbers",
                    "artifact_type": "tool"
                },
                timeout=120.0
            )
            if r.status_code == 200:
                artifact = r.json()
                print(f"   ✅ Created artifact: {artifact['id']}")
                print(f"      Name: {artifact['name']}")
                print(f"      Status: {artifact['status']}")
                
                # Check approval was created
                r2 = await client.get(f"{BASE_URL}/api/approvals/")
                approvals = r2.json()
                print(f"   ✅ Approval request created: {len(approvals)} pending")
            else:
                print(f"   ❌ {r.status_code}: {r.text}")
        except Exception as e:
            print(f"   ⚠️ Error (may be timeout): {e}")
        
        print("\n✅ Basic API tests completed!")

if __name__ == "__main__":
    asyncio.run(test())

