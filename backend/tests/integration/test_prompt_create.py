"""Test prompt creation"""
import asyncio
import json

import httpx

BASE_URL = "http://localhost:8000"

async def test():
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("Testing prompt creation...")
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/prompts/",
                json={
                    "name": "test_system_prompt",
                    "prompt_text": "You are a helpful AI assistant.",
                    "prompt_type": "system",
                    "level": 1
                }
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                prompt = response.json()
                print(f"✅ Created prompt: {prompt['id']}")
                print(f"   Name: {prompt['name']}")
                print(f"   Type: {prompt['prompt_type']}")
                print(f"   Status: {prompt['status']}")
            else:
                print(f"❌ Error: {response.text}")
                try:
                    error_detail = response.json()
                    print(f"   Detail: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())

