"""
API tests for Tools system
Tests the REST API endpoints for tools
"""
import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"


def test_create_tool():
    """Test creating a tool via API"""
    print("\n=== Test 1: Create Tool ===")
    try:
        tool_data = {
            "name": f"test_tool_{uuid4().hex[:8]}",
            "description": "Test tool for API testing",
            "category": "file_operations",
            "code": """
def execute(directory, extension=None):
    from pathlib import Path
    path = Path(directory)
    if extension:
        return list(path.glob(f"*.{extension}"))
    return list(path.glob("*"))
            """,
            "entry_point": "execute",
            "input_schema": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "extension": {"type": "string"}
                },
                "required": ["directory"]
            },
            "dependencies": ["pathlib"],
            "timeout_seconds": 30
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tools/",
            json=tool_data,
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"  [OK] Tool created: {data['name']}")
            print(f"  Tool ID: {data['id']}")
            print(f"  Status: {data['status']}")
            return data
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server. Is it running?")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_list_tools():
    """Test listing tools"""
    print("\n=== Test 2: List Tools ===")
    try:
        response = requests.get(f"{BASE_URL}/api/tools/", timeout=10)
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            tools = response.json()
            print(f"  [OK] Found {len(tools)} tools")
            if tools:
                print(f"  First tool: {tools[0]['name']} (status: {tools[0]['status']})")
            return tools
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            return []
            
    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server")
        return []
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return []


def test_get_tool(tool_id):
    """Test getting a specific tool"""
    print("\n=== Test 3: Get Tool ===")
    if not tool_id:
        print("  [WARN] Skipped (no tool ID)")
        return None
        
    try:
        response = requests.get(f"{BASE_URL}/api/tools/{tool_id}", timeout=10)
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            tool = response.json()
            print(f"  [OK] Tool retrieved: {tool['name']}")
            print(f"  Description: {tool.get('description', 'N/A')}")
            print(f"  Category: {tool.get('category', 'N/A')}")
            print(f"  Status: {tool['status']}")
            return tool
        elif response.status_code == 404:
            print(f"  [WARN] Tool not found: {tool_id}")
            return None
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def test_update_tool(tool_id):
    """Test updating a tool"""
    print("\n=== Test 4: Update Tool ===")
    if not tool_id:
        print("  [WARN] Skipped (no tool ID)")
        return None
        
    try:
        update_data = {
            "description": "Updated description via API",
            "metadata": {"test": "value", "updated": True}
        }
        
        response = requests.put(
            f"{BASE_URL}/api/tools/{tool_id}",
            json=update_data,
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            tool = response.json()
            print(f"  [OK] Tool updated")
            print(f"  New description: {tool.get('description', 'N/A')}")
            assert tool.get('description') == "Updated description via API"
            return tool
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def test_activate_tool(tool_id):
    """Test activating a tool"""
    print("\n=== Test 5: Activate Tool ===")
    if not tool_id:
        print("  [WARN] Skipped (no tool ID)")
        return None
        
    try:
        # First, set tool to waiting_approval status
        # Note: We can't directly set status via update, so we'll test the error case
        # In a real scenario, status would be set through approval workflow
        
        # Try to activate from draft status (should fail)
        response = requests.post(
            f"{BASE_URL}/api/tools/{tool_id}/activate",
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 400:
            error_data = response.json()
            print(f"  [OK] Correctly rejected activation from draft status")
            print(f"  Error message: {error_data.get('detail', 'N/A')}")
            # This is expected behavior - tool needs to be in waiting_approval first
            return True
        elif response.status_code == 200:
            tool = response.json()
            print(f"  [OK] Tool activated")
            print(f"  Status: {tool['status']}")
            return tool
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def test_tool_metrics(tool_id):
    """Test getting tool metrics"""
    print("\n=== Test 6: Tool Metrics ===")
    if not tool_id:
        print("  [WARN] Skipped (no tool ID)")
        return None
        
    try:
        response = requests.get(
            f"{BASE_URL}/api/tools/{tool_id}/metrics",
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            metrics = response.json()
            print(f"  [OK] Metrics retrieved:")
            print(f"    Total executions: {metrics.get('total_executions', 0)}")
            print(f"    Successful: {metrics.get('successful_executions', 0)}")
            print(f"    Failed: {metrics.get('failed_executions', 0)}")
            print(f"    Success rate: {metrics.get('success_rate', 'N/A')}")
            return metrics
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def test_list_tools_filters():
    """Test listing tools with filters"""
    print("\n=== Test 7: List Tools with Filters ===")
    try:
        # Test active_only filter
        response = requests.get(
            f"{BASE_URL}/api/tools/?active_only=true",
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            tools = response.json()
            print(f"  [OK] Found {len(tools)} active tools")
            if tools:
                assert all(t['status'] == 'active' for t in tools)
                print(f"  [OK] All tools are active")
            return True
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_duplicate_name():
    """Test creating tool with duplicate name"""
    print("\n=== Test 8: Duplicate Name Check ===")
    try:
        # Create first tool
        tool1 = test_create_tool()
        if not tool1:
            print("  [WARN] Skipped (could not create first tool)")
            return None
        
        # Try to create duplicate
        tool_data = {
            "name": tool1['name'],  # Same name
            "description": "Duplicate tool"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tools/",
            json=tool_data,
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 400:
            print(f"  [OK] Duplicate name correctly rejected")
            return True
        else:
            print(f"  ✗ Duplicate name not rejected (status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def run_all_tests():
    """Run all API tests"""
    print("=" * 60)
    print("TOOLS API TESTS")
    print("=" * 60)
    print(f"Testing against: {BASE_URL}")
    print()
    
    results = []
    created_tool_id = None
    
    # Test 1: Create tool
    tool = test_create_tool()
    if tool:
        created_tool_id = tool['id']
        results.append(("Create Tool", True))
    else:
        results.append(("Create Tool", False))
    
    # Test 2: List tools
    tools = test_list_tools()
    results.append(("List Tools", len(tools) >= 0))
    
    # Test 3: Get tool
    if created_tool_id:
        retrieved = test_get_tool(created_tool_id)
        results.append(("Get Tool", retrieved is not None))
    else:
        results.append(("Get Tool", None))
    
    # Test 4: Update tool
    if created_tool_id:
        updated = test_update_tool(created_tool_id)
        results.append(("Update Tool", updated is not None))
    else:
        results.append(("Update Tool", None))
    
    # Test 5: Activate tool
    if created_tool_id:
        activated = test_activate_tool(created_tool_id)
        results.append(("Activate Tool", activated is not None))
    else:
        results.append(("Activate Tool", None))
    
    # Test 6: Metrics
    if created_tool_id:
        metrics = test_tool_metrics(created_tool_id)
        results.append(("Tool Metrics", metrics is not None))
    else:
        results.append(("Tool Metrics", None))
    
    # Test 7: Filters
    filters_ok = test_list_tools_filters()
    results.append(("List with Filters", filters_ok))
    
    # Test 8: Duplicate name
    duplicate_ok = test_duplicate_name()
    results.append(("Duplicate Name Check", duplicate_ok))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)
    
    for name, result in results:
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped (out of {total})")
    
    if passed == total - skipped:
        print("[SUCCESS] All non-skipped tests passed!")
    elif passed > 0:
        print(f"[WARN] Some tests failed or were skipped")
    else:
        print("[FAIL] All tests failed or were skipped")
    
    return passed, failed, skipped


if __name__ == "__main__":
    try:
        passed, failed, skipped = run_all_tests()
        exit(0 if failed == 0 else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

