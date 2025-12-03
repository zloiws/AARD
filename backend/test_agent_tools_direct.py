"""
Direct integration test for Agents and Tools
Tests the integration using Python code directly
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from uuid import uuid4
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.models.agent import Agent, AgentStatus
from app.models.tool import Tool, ToolStatus
from app.services.agent_service import AgentService
from app.services.tool_service import ToolService
from app.agents.simple_agent import SimpleAgent


def setup_test_data():
    """Setup test data"""
    print("\n=== Setting up test data ===")
    
    db: Session = SessionLocal()
    
    try:
        # Create tool
        tool_service = ToolService(db)
        tool = tool_service.create_tool(
            name=f"test_file_finder_{uuid4().hex[:8]}",
            description="Test tool for finding files",
            category="file_operations",
            code="""
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
            entry_point="execute",
            input_schema={
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "extension": {"type": "string"}
                },
                "required": ["directory"]
            },
            created_by="test"
        )
        
        # Activate tool
        tool.status = ToolStatus.WAITING_APPROVAL.value
        db.commit()
        tool = tool_service.activate_tool(tool.id)
        
        print(f"  [OK] Tool created and activated: {tool.name}")
        print(f"  Tool ID: {tool.id}")
        
        # Create agent
        agent_service = AgentService(db)
        agent = agent_service.create_agent(
            name=f"test_file_agent_{uuid4().hex[:8]}",
            description="Test agent for file operations",
            system_prompt="You are a file operations assistant.",
            capabilities=["file_operations"],
            created_by="test"
        )
        
        # Activate agent
        agent.status = AgentStatus.WAITING_APPROVAL.value
        db.commit()
        agent = agent_service.activate_agent(agent.id)
        
        print(f"  [OK] Agent created and activated: {agent.name}")
        print(f"  Agent ID: {agent.id}")
        
        # Configure tool access
        tool_service.update_tool(
            tool.id,
            allowed_agents=[str(agent.id)]
        )
        
        print(f"  [OK] Tool access configured for agent")
        
        return tool, agent, db
        
    except Exception as e:
        print(f"  [FAIL] Error setting up test data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None, None, None
    finally:
        pass  # Don't close db yet, we'll use it in tests


async def test_agent_get_available_tools(agent, tool, db):
    """Test agent getting available tools"""
    print("\n=== Test 1: Agent Get Available Tools ===")
    
    try:
        agent_service = AgentService(db)
        agent_instance = SimpleAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db
        )
        
        # Get available tools
        tools = agent_instance.get_available_tools()
        
        print(f"  [OK] Found {len(tools)} available tools")
        
        # Check if our tool is in the list
        tool_names = [t['name'] for t in tools]
        if tool.name in tool_names:
            print(f"  [OK] Test tool '{tool.name}' is available")
            return True
        else:
            print(f"  [WARN] Test tool '{tool.name}' not found in available tools")
            print(f"  Available tools: {tool_names}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_get_tool_by_name(agent, tool, db):
    """Test agent getting tool by name"""
    print("\n=== Test 2: Agent Get Tool By Name ===")
    
    try:
        agent_service = AgentService(db)
        agent_instance = SimpleAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db
        )
        
        # Get tool by name
        tool_info = agent_instance.get_tool_by_name(tool.name)
        
        if tool_info:
            print(f"  [OK] Tool found: {tool_info['name']}")
            print(f"  Description: {tool_info.get('description', 'N/A')}")
            return True
        else:
            print(f"  [FAIL] Tool not found or not accessible")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_use_tool(agent, tool, db):
    """Test agent using a tool"""
    print("\n=== Test 3: Agent Use Tool ===")
    
    try:
        agent_service = AgentService(db)
        agent_instance = SimpleAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db
        )
        
        # Use tool
        result = await agent_instance.use_tool(
            tool_name=tool.name,
            directory="/tmp",
            extension="py"
        )
        
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        
        if result['status'] == 'success':
            print(f"  [OK] Tool executed successfully")
            print(f"  Result: {result.get('result', {})}")
            return True
        else:
            print(f"  [FAIL] Tool execution failed: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_list_tools_by_category(agent, tool, db):
    """Test agent listing tools by category"""
    print("\n=== Test 4: Agent List Tools By Category ===")
    
    try:
        agent_service = AgentService(db)
        agent_instance = SimpleAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db
        )
        
        # Get tools by category
        categorized = agent_instance.list_tools_by_category()
        
        print(f"  [OK] Found {len(categorized)} categories")
        for category, tools in categorized.items():
            print(f"    {category}: {len(tools)} tools")
            if category == "file_operations":
                tool_names = [t['name'] for t in tools]
                if tool.name in tool_names:
                    print(f"  [OK] Test tool found in file_operations category")
                    return True
        
        print(f"  [WARN] Test tool not found in categorized list")
        return False
        
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_execute_with_tool(agent, tool, db):
    """Test agent executing a task with tool"""
    print("\n=== Test 5: Agent Execute With Tool ===")
    
    try:
        agent_service = AgentService(db)
        agent_instance = SimpleAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db
        )
        
        # Execute task with tool
        result = await agent_instance.execute(
            task_description="Find all Python files",
            tool_name=tool.name,
            tool_params={"directory": "/tmp", "extension": "py"}
        )
        
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        
        if result['status'] == 'success':
            print(f"  [OK] Task executed successfully with tool")
            if 'tool_used' in result.get('metadata', {}):
                print(f"  Tool used: {result['metadata']['tool_used']}")
            return True
        else:
            print(f"  [FAIL] Task execution failed: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("AGENT-TOOLS DIRECT INTEGRATION TESTS")
    print("=" * 60)
    
    # Setup test data
    tool, agent, db = setup_test_data()
    
    if not tool or not agent:
        print("\n[FAIL] Failed to setup test data")
        return False
    
    results = []
    
    # Run tests
    results.append(("Get Available Tools", await test_agent_get_available_tools(agent, tool, db)))
    results.append(("Get Tool By Name", await test_agent_get_tool_by_name(agent, tool, db)))
    results.append(("Use Tool", await test_agent_use_tool(agent, tool, db)))
    results.append(("List Tools By Category", await test_agent_list_tools_by_category(agent, tool, db)))
    results.append(("Execute With Tool", await test_agent_execute_with_tool(agent, tool, db)))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed!")
    else:
        print(f"[WARN] {total - passed} test(s) failed")
    
    # Cleanup
    if db:
        try:
            db.close()
        except:
            pass
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

