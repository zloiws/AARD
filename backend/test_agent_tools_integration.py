"""
Integration tests for Agents and Tools
Tests the integration between agents and tools
"""
import asyncio
import sys
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_create_tool():
    """Create a test tool"""
    print("\n=== Test 1: Create Tool ===")
    try:
        tool_data = {
            "name": "test_file_finder",
            "description": "Test tool for finding files",
            "category": "file_operations",
            "code": """
def execute(directory, extension=None):
    # Simulate file finding
    files = []
    if extension:
        files.append(f"test.{extension}")
    else:
        files.append("test.txt")
        files.append("test.py")
    return {"files": files, "count": len(files)}
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
            "status": "waiting_approval"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tools/",
            json=tool_data,
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 201:
            tool = response.json()
            print(f"  [OK] Tool created: {tool['name']}")
            print(f"  Tool ID: {tool['id']}")
            return tool
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return None


def test_activate_tool(tool_id):
    """Activate a tool"""
    print("\n=== Test 2: Activate Tool ===")
    if not tool_id:
        print("  [WARN] Skipped (no tool ID)")
        return None
        
    try:
        # First set to waiting_approval (if not already)
        update_response = requests.put(
            f"{BASE_URL}/api/tools/{tool_id}",
            json={"status": "waiting_approval"},
            timeout=10
        )
        
        # Now activate
        response = requests.post(
            f"{BASE_URL}/api/tools/{tool_id}/activate",
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            tool = response.json()
            print(f"  [OK] Tool activated: {tool['status']}")
            return tool
        else:
            print(f"  [WARN] Activation may require approval workflow")
            print(f"  Response: {response.json()}")
            return None
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return None


def test_create_agent():
    """Create a test agent"""
    print("\n=== Test 3: Create Agent ===")
    try:
        agent_data = {
            "name": "test_file_agent",
            "description": "Test agent for file operations",
            "system_prompt": "You are a file operations assistant.",
            "capabilities": ["file_operations"],
            "status": "waiting_approval"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/agents/",
            json=agent_data,
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 201:
            agent = response.json()
            print(f"  [OK] Agent created: {agent['name']}")
            print(f"  Agent ID: {agent['id']}")
            return agent
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return None


def test_activate_agent(agent_id):
    """Activate an agent"""
    print("\n=== Test 4: Activate Agent ===")
    if not agent_id:
        print("  [WARN] Skipped (no agent ID)")
        return None
        
    try:
        # First set to waiting_approval (if not already)
        update_response = requests.put(
            f"{BASE_URL}/api/agents/{agent_id}",
            json={"status": "waiting_approval"},
            timeout=10
        )
        
        # Now activate
        response = requests.post(
            f"{BASE_URL}/api/agents/{agent_id}/activate",
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            agent = response.json()
            print(f"  [OK] Agent activated: {agent['status']}")
            return agent
        else:
            print(f"  [WARN] Activation may require approval workflow")
            print(f"  Response: {response.json()}")
            return None
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return None


def test_configure_tool_access(tool_id, agent_id):
    """Configure tool access for agent"""
    print("\n=== Test 5: Configure Tool Access ===")
    if not tool_id or not agent_id:
        print("  [WARN] Skipped (missing IDs)")
        return False
        
    try:
        # Allow agent to use tool
        response = requests.put(
            f"{BASE_URL}/api/tools/{tool_id}",
            json={
                "allowed_agents": [str(agent_id)]
            },
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            tool = response.json()
            print(f"  [OK] Tool access configured")
            print(f"  Allowed agents: {tool.get('allowed_agents', [])}")
            return True
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_check_tool_access(tool_id, agent_id):
    """Check if agent can use tool"""
    print("\n=== Test 6: Check Tool Access ===")
    if not tool_id or not agent_id:
        print("  [WARN] Skipped (missing IDs)")
        return False
        
    try:
        response = requests.get(
            f"{BASE_URL}/api/tools/{tool_id}/can-use/{agent_id}",
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            can_use = data.get("can_use", False)
            print(f"  [OK] Agent can use tool: {can_use}")
            return can_use
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_list_available_tools(agent_id):
    """Test listing tools available to agent"""
    print("\n=== Test 7: List Available Tools (via API) ===")
    if not agent_id:
        print("  [WARN] Skipped (no agent ID)")
        return False
        
    try:
        # Get all active tools
        response = requests.get(
            f"{BASE_URL}/api/tools/?active_only=true",
            timeout=10
        )
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            tools = response.json()
            print(f"  [OK] Found {len(tools)} active tools")
            
            # Check access for each tool
            accessible = []
            for tool in tools:
                access_response = requests.get(
                    f"{BASE_URL}/api/tools/{tool['id']}/can-use/{agent_id}",
                    timeout=10
                )
                if access_response.status_code == 200:
                    access_data = access_response.json()
                    if access_data.get("can_use"):
                        accessible.append(tool['name'])
            
            print(f"  [OK] Agent can access {len(accessible)} tools: {', '.join(accessible)}")
            return True
        else:
            print(f"  [FAIL] Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_agent_tool_integration_summary():
    """Print integration summary"""
    print("\n=== Integration Summary ===")
    print("""
To test the full integration programmatically, you would need to:

1. Create agent and tool instances in Python:
   ```python
   from app.agents.simple_agent import SimpleAgent
   from app.services.agent_service import AgentService
   from app.services.tool_service import ToolService
   from app.core.database import SessionLocal
   
   db = SessionLocal()
   agent_service = AgentService(db)
   tool_service = ToolService(db)
   
   # Get agent and tool
   agent_data = agent_service.get_agent_by_name("test_file_agent")
   tool_data = tool_service.get_tool_by_name("test_file_finder")
   
   # Create agent instance
   agent = SimpleAgent(
       agent_id=agent_data.id,
       agent_service=agent_service,
       db_session=db
   )
   
   # Use tool
   result = await agent.use_tool("test_file_finder", directory="/tmp", extension="py")
   print(result)
   ```

2. Or use the API endpoints to execute agent tasks with tools.
    """)


def run_all_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("AGENT-TOOLS INTEGRATION TESTS")
    print("=" * 60)
    print(f"Testing against: {BASE_URL}")
    print()
    
    results = []
    tool_id = None
    agent_id = None
    
    # Test 1: Create tool
    tool = test_create_tool()
    if tool:
        tool_id = tool['id']
        results.append(("Create Tool", True))
    else:
        results.append(("Create Tool", False))
    
    # Test 2: Activate tool
    if tool_id:
        activated = test_activate_tool(tool_id)
        results.append(("Activate Tool", activated is not None))
    else:
        results.append(("Activate Tool", None))
    
    # Test 3: Create agent
    agent = test_create_agent()
    if agent:
        agent_id = agent['id']
        results.append(("Create Agent", True))
    else:
        results.append(("Create Agent", False))
    
    # Test 4: Activate agent
    if agent_id:
        activated = test_activate_agent(agent_id)
        results.append(("Activate Agent", activated is not None))
    else:
        results.append(("Activate Agent", None))
    
    # Test 5: Configure tool access
    if tool_id and agent_id:
        configured = test_configure_tool_access(tool_id, agent_id)
        results.append(("Configure Tool Access", configured))
    else:
        results.append(("Configure Tool Access", None))
    
    # Test 6: Check tool access
    if tool_id and agent_id:
        can_use = test_check_tool_access(tool_id, agent_id)
        results.append(("Check Tool Access", can_use))
    else:
        results.append(("Check Tool Access", None))
    
    # Test 7: List available tools
    if agent_id:
        listed = test_list_available_tools(agent_id)
        results.append(("List Available Tools", listed))
    else:
        results.append(("List Available Tools", None))
    
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
        print("[WARN] Some tests failed or were skipped")
    else:
        print("[FAIL] All tests failed or were skipped")
    
    # Integration summary
    test_agent_tool_integration_summary()
    
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

