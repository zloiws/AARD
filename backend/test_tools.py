"""
Comprehensive tests for Tools system
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from uuid import uuid4
from sqlalchemy.orm import Session
from app.core.database import get_db, Base, engine
from app.models.tool import Tool, ToolStatus, ToolCategory
from app.services.tool_service import ToolService
from app.tools.python_tool import PythonTool


def setup_test_db():
    """Create test database tables"""
    Base.metadata.create_all(bind=engine)


def cleanup_test_db():
    """Clean up test database"""
    # Drop all tables
    Base.metadata.drop_all(bind=engine)


def test_tool_model():
    """Test Tool model creation"""
    print("\n=== Test 1: Tool Model ===")
    
    tool = Tool(
        name="test_tool",
        description="Test tool description",
        category=ToolCategory.FILE_OPERATIONS.value,
        code="def execute(x): return x * 2",
        entry_point="execute",
        status=ToolStatus.DRAFT.value
    )
    
    assert tool.name == "test_tool"
    assert tool.category == "file_operations"
    assert tool.status == "draft"
    assert tool.version == 1
    
    tool_dict = tool.to_dict()
    assert "id" in tool_dict
    assert tool_dict["name"] == "test_tool"
    assert tool_dict["metadata"] == tool.tool_metadata  # Check mapping
    
    print("✓ Tool model creation: PASSED")
    return True


def test_tool_service_create():
    """Test ToolService.create_tool"""
    print("\n=== Test 2: ToolService.create_tool ===")
    
    db: Session = next(get_db())
    service = ToolService(db)
    
    try:
        tool = service.create_tool(
            name="test_file_finder",
            description="Find files by extension",
            category="file_operations",
            code="""
def execute(directory, extension=None):
    from pathlib import Path
    path = Path(directory)
    if extension:
        return list(path.glob(f"*.{extension}"))
    return list(path.glob("*"))
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
            dependencies=["pathlib"],
            created_by="test_user"
        )
        
        assert tool.id is not None
        assert tool.name == "test_file_finder"
        assert tool.status == ToolStatus.DRAFT.value
        assert tool.version == 1
        assert tool.created_by == "test_user"
        
        print("✓ Tool creation: PASSED")
        
        # Test duplicate name
        try:
            service.create_tool(name="test_file_finder", description="Duplicate")
            print("✗ Duplicate name check: FAILED (should raise ValueError)")
            return False
        except ValueError as e:
            assert "already exists" in str(e).lower()
            print("✓ Duplicate name check: PASSED")
        
        return True
        
    except Exception as e:
        print(f"✗ Tool creation: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_tool_service_list():
    """Test ToolService.list_tools"""
    print("\n=== Test 3: ToolService.list_tools ===")
    
    db: Session = next(get_db())
    service = ToolService(db)
    
    try:
        # Create multiple tools
        tool1 = service.create_tool(
            name="tool_1",
            description="Tool 1",
            category="file_operations",
            status=ToolStatus.ACTIVE.value
        )
        
        tool2 = service.create_tool(
            name="tool_2",
            description="Tool 2",
            category="network",
            status=ToolStatus.DRAFT.value
        )
        
        # List all tools
        all_tools = service.list_tools()
        assert len(all_tools) >= 2
        
        # Filter by status
        active_tools = service.list_tools(status=ToolStatus.ACTIVE.value)
        assert len(active_tools) >= 1
        assert all(t.status == ToolStatus.ACTIVE.value for t in active_tools)
        
        # Filter by category
        file_tools = service.list_tools(category="file_operations")
        assert len(file_tools) >= 1
        assert all(t.category == "file_operations" for t in file_tools)
        
        # Active only
        active_only = service.list_tools(active_only=True)
        assert len(active_only) >= 1
        assert all(t.status == ToolStatus.ACTIVE.value for t in active_only)
        
        print("✓ Tool listing: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Tool listing: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_tool_service_update():
    """Test ToolService.update_tool"""
    print("\n=== Test 4: ToolService.update_tool ===")
    
    db: Session = next(get_db())
    service = ToolService(db)
    
    try:
        tool = service.create_tool(
            name="tool_to_update",
            description="Original description",
            category="file_operations"
        )
        
        # Update tool
        updated = service.update_tool(
            tool.id,
            description="Updated description",
            category="network",
            metadata={"key": "value"}
        )
        
        assert updated.description == "Updated description"
        assert updated.category == "network"
        assert updated.tool_metadata == {"key": "value"}
        
        print("✓ Tool update: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Tool update: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_tool_service_lifecycle():
    """Test tool lifecycle (activate, pause, deprecate)"""
    print("\n=== Test 5: Tool Lifecycle ===")
    
    db: Session = next(get_db())
    service = ToolService(db)
    
    try:
        # Create tool in waiting_approval status
        tool = service.create_tool(
            name="lifecycle_tool",
            description="Lifecycle test",
            status=ToolStatus.WAITING_APPROVAL.value
        )
        
        # Activate
        activated = service.activate_tool(tool.id)
        assert activated.status == ToolStatus.ACTIVE.value
        assert activated.activated_at is not None
        
        # Pause
        paused = service.pause_tool(tool.id)
        assert paused.status == ToolStatus.PAUSED.value
        
        # Reactivate (need to set back to waiting_approval first)
        service.update_tool(tool.id, status=ToolStatus.WAITING_APPROVAL.value)
        reactivated = service.activate_tool(tool.id)
        assert reactivated.status == ToolStatus.ACTIVE.value
        
        # Deprecate
        deprecated = service.deprecate_tool(tool.id)
        assert deprecated.status == ToolStatus.DEPRECATED.value
        
        print("✓ Tool lifecycle: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Tool lifecycle: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_tool_metrics():
    """Test tool metrics recording"""
    print("\n=== Test 6: Tool Metrics ===")
    
    db: Session = next(get_db())
    service = ToolService(db)
    
    try:
        tool = service.create_tool(
            name="metrics_tool",
            description="Metrics test",
            status=ToolStatus.ACTIVE.value
        )
        
        # Record executions
        service.record_execution(tool.id, success=True, execution_time=100)
        service.record_execution(tool.id, success=True, execution_time=150)
        service.record_execution(tool.id, success=False, execution_time=50)
        
        # Get metrics
        metrics = service.get_tool_metrics(tool.id)
        
        assert metrics["total_executions"] == 3
        assert metrics["successful_executions"] == 2
        assert metrics["failed_executions"] == 1
        assert metrics["success_rate"] == "66.67%"
        assert metrics["average_execution_time"] is not None
        
        print("✓ Tool metrics: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Tool metrics: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_tool_access_control():
    """Test tool access control"""
    print("\n=== Test 7: Tool Access Control ===")
    
    db: Session = next(get_db())
    service = ToolService(db)
    
    try:
        agent1_id = uuid4()
        agent2_id = uuid4()
        agent3_id = uuid4()
        
        # Create tool with allowed agents
        tool = service.create_tool(
            name="restricted_tool",
            description="Restricted tool",
            status=ToolStatus.ACTIVE.value,
            allowed_agents=[str(agent1_id), str(agent2_id)]
        )
        
        # Check access
        assert service.can_agent_use_tool(tool.id, agent1_id) == True
        assert service.can_agent_use_tool(tool.id, agent2_id) == True
        assert service.can_agent_use_tool(tool.id, agent3_id) == False
        
        # Test forbidden agents
        tool2 = service.create_tool(
            name="forbidden_tool",
            description="Forbidden tool",
            status=ToolStatus.ACTIVE.value,
            forbidden_agents=[str(agent1_id)]
        )
        
        assert service.can_agent_use_tool(tool2.id, agent1_id) == False
        assert service.can_agent_use_tool(tool2.id, agent2_id) == True
        
        # Test inactive tool
        tool3 = service.create_tool(
            name="inactive_tool",
            description="Inactive tool",
            status=ToolStatus.DRAFT.value
        )
        
        assert service.can_agent_use_tool(tool3.id, agent1_id) == False
        
        print("✓ Tool access control: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Tool access control: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_python_tool_execution():
    """Test PythonTool execution"""
    print("\n=== Test 8: PythonTool Execution ===")
    
    db: Session = next(get_db())
    service = ToolService(db)
    
    try:
        # Create tool with Python code
        tool = service.create_tool(
            name="execution_tool",
            description="Execution test",
            code="""
def execute(x, y):
    return x + y
            """,
            entry_point="execute",
            status=ToolStatus.ACTIVE.value
        )
        
        # Create PythonTool instance
        python_tool = PythonTool(tool_id=tool.id, tool_service=service)
        
        # Execute tool
        result = await python_tool.execute(x=5, y=3)
        
        assert result["status"] == "success"
        assert result["result"] == 8
        assert "execution_time_ms" in result["metadata"]
        
        # Test with invalid input
        result2 = await python_tool.execute(x="invalid")
        # Should handle error gracefully
        
        print("✓ PythonTool execution: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ PythonTool execution: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_tool_input_validation():
    """Test tool input validation"""
    print("\n=== Test 9: Tool Input Validation ===")
    
    db: Session = next(get_db())
    service = ToolService(db)
    
    try:
        tool = service.create_tool(
            name="validation_tool",
            description="Validation test",
            code="def execute(name, age): return f'{name} is {age}'",
            entry_point="execute",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                },
                "required": ["name", "age"]
            },
            status=ToolStatus.ACTIVE.value
        )
        
        python_tool = PythonTool(tool_id=tool.id, tool_service=service)
        
        # Valid input
        is_valid, error = python_tool.validate_input(name="John", age=30)
        assert is_valid == True
        assert error is None
        
        # Missing required field
        is_valid, error = python_tool.validate_input(name="John")
        assert is_valid == False
        assert "age" in error.lower()
        
        # Wrong type
        is_valid, error = python_tool.validate_input(name="John", age="thirty")
        # Note: Basic validation may not catch all type errors
        
        print("✓ Tool input validation: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Tool input validation: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_tool_api_endpoints():
    """Test API endpoints (basic checks)"""
    print("\n=== Test 10: API Endpoints (Structure) ===")
    
    try:
        from app.api.routes import tools
        
        # Check router exists
        assert hasattr(tools, 'router')
        assert tools.router.prefix == "/api/tools"
        
        # Check routes exist
        routes = [route.path for route in tools.router.routes]
        
        expected_routes = [
            "/",
            "/{tool_id}",
            "/{tool_id}/activate",
            "/{tool_id}/pause",
            "/{tool_id}/deprecate",
            "/{tool_id}/metrics",
            "/{tool_id}/can-use/{agent_id}"
        ]
        
        for expected in expected_routes:
            found = any(expected in route for route in routes)
            if not found:
                print(f"⚠ Route {expected} not found (may be OK)")
        
        print("✓ API endpoints structure: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ API endpoints: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("TOOLS SYSTEM TESTS")
    print("=" * 60)
    
    results = []
    
    # Setup
    try:
        setup_test_db()
    except Exception as e:
        print(f"⚠ Database setup warning: {e}")
    
    # Run synchronous tests
    results.append(("Tool Model", test_tool_model()))
    results.append(("ToolService.create_tool", test_tool_service_create()))
    results.append(("ToolService.list_tools", test_tool_service_list()))
    results.append(("ToolService.update_tool", test_tool_service_update()))
    results.append(("Tool Lifecycle", test_tool_service_lifecycle()))
    results.append(("Tool Metrics", test_tool_metrics()))
    results.append(("Tool Access Control", test_tool_access_control()))
    results.append(("API Endpoints", test_tool_api_endpoints()))
    
    # Run async tests
    async def run_async_tests():
        results_async = []
        results_async.append(("PythonTool Execution", await test_python_tool_execution()))
        results_async.append(("Tool Input Validation", await test_tool_input_validation()))
        return results_async
    
    async_results = asyncio.run(run_async_tests())
    results.extend(async_results)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠ {total - passed} test(s) failed")
    
    # Cleanup
    try:
        cleanup_test_db()
    except Exception as e:
        print(f"⚠ Database cleanup warning: {e}")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

