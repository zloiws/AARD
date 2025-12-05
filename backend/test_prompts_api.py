"""Test prompt management API endpoints"""
import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"

def test_api_endpoints():
    """Test API endpoints"""
    print("=== Testing API Endpoints ===\n")
    
    # Test 1: List prompts
    print("1. GET /api/prompts/ - List prompts")
    try:
        response = requests.get(f"{BASE_URL}/api/prompts/")
        if response.status_code == 200:
            prompts = response.json()
            print(f"   ✓ Found {len(prompts)} prompts")
        else:
            print(f"   ✗ Status: {response.status_code}")
    except Exception as e:
        print(f"   ⚠ Server not running: {e}")
        return
    
    # Test 2: Create prompt
    print("\n2. POST /api/prompts/ - Create prompt")
    prompt_data = {
        "name": f"test_api_{uuid4().hex[:8]}",
        "prompt_text": "Test prompt from API",
        "prompt_type": "system",
        "level": 0
    }
    response = requests.post(f"{BASE_URL}/api/prompts/", json=prompt_data)
    if response.status_code == 200:
        prompt = response.json()
        prompt_id = prompt["id"]
        print(f"   ✓ Created prompt: {prompt['name']} (id: {prompt_id})")
    else:
        print(f"   ✗ Status: {response.status_code}, Error: {response.text}")
        return
    
    # Test 3: Get prompt
    print(f"\n3. GET /api/prompts/{prompt_id} - Get prompt")
    response = requests.get(f"{BASE_URL}/api/prompts/{prompt_id}")
    if response.status_code == 200:
        prompt = response.json()
        print(f"   ✓ Retrieved: {prompt['name']}")
    else:
        print(f"   ✗ Status: {response.status_code}")
    
    # Test 4: Update prompt
    print(f"\n4. PUT /api/prompts/{prompt_id} - Update prompt")
    update_data = {"prompt_text": "Updated prompt text from API"}
    response = requests.put(f"{BASE_URL}/api/prompts/{prompt_id}", json=update_data)
    if response.status_code == 200:
        prompt = response.json()
        print(f"   ✓ Updated: {prompt['prompt_text'][:50]}...")
    else:
        print(f"   ✗ Status: {response.status_code}")
    
    # Test 5: Create version
    print(f"\n5. POST /api/prompts/{prompt_id}/version - Create version")
    version_data = {"prompt_text": "Version 2 from API"}
    response = requests.post(f"{BASE_URL}/api/prompts/{prompt_id}/version", json=version_data)
    if response.status_code == 200:
        version = response.json()
        print(f"   ✓ Created version {version['version']}")
    else:
        print(f"   ✗ Status: {response.status_code}, Error: {response.text}")
    
    # Test 6: Get versions
    print(f"\n6. GET /api/prompts/{prompt_id}/versions - Get versions")
    response = requests.get(f"{BASE_URL}/api/prompts/{prompt_id}/versions")
    if response.status_code == 200:
        versions = response.json()
        print(f"   ✓ Found {len(versions)} versions")
    else:
        print(f"   ✗ Status: {response.status_code}")
    
    # Test 7: Get metrics
    print(f"\n7. GET /api/prompts/{prompt_id}/metrics - Get metrics")
    response = requests.get(f"{BASE_URL}/api/prompts/{prompt_id}/metrics")
    if response.status_code == 200:
        metrics = response.json()
        print(f"   ✓ Metrics: usage_count={metrics.get('usage_count', 0)}, "
              f"success_rate={metrics.get('success_rate')}, "
              f"avg_execution_time={metrics.get('avg_execution_time')}")
    else:
        print(f"   ✗ Status: {response.status_code}")
    
    # Test 8: Deprecate prompt
    print(f"\n8. POST /api/prompts/{prompt_id}/deprecate - Deprecate prompt")
    response = requests.post(f"{BASE_URL}/api/prompts/{prompt_id}/deprecate")
    if response.status_code == 200:
        prompt = response.json()
        print(f"   ✓ Deprecated: status={prompt['status']}")
    else:
        print(f"   ✗ Status: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("✓ API tests completed!")

if __name__ == "__main__":
    test_api_endpoints()

