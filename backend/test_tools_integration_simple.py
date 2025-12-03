"""
Simple integration test - tests tools functionality
(Agents require migration to be applied first)
"""
import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from uuid import uuid4
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.tool import Tool, ToolStatus
from app.services.tool_service import ToolService
from app.tools.python_tool import PythonTool


async def test_tool_execution():
    """Test tool execution directly"""
    print("=" * 60)
    print("TOOLS INTEGRATION TEST")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # Create and activate tool
        tool_service = ToolService(db)
        tool = tool_service.create_tool(
            name=f"test_calculator_{uuid4().hex[:8]}",
            description="Simple calculator tool",
            category="custom",
            code="""
def execute(operation, a, b):
    if operation == "add":
        return a + b
    elif operation == "multiply":
        return a * b
    elif operation == "subtract":
        return a - b
    else:
        return None
            """,
            entry_point="execute",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["operation", "a", "b"]
            },
            created_by="test"
        )
        
        # Activate tool
        tool.status = ToolStatus.WAITING_APPROVAL.value
        db.commit()
        tool = tool_service.activate_tool(tool.id)
        
        print(f"\n[OK] Tool created and activated: {tool.name}")
        print(f"Tool ID: {tool.id}")
        
        # Create PythonTool instance
        python_tool = PythonTool(tool_id=tool.id, tool_service=tool_service)
        
        # Test 1: Execute tool
        print("\n=== Test 1: Execute Tool ===")
        result = await python_tool.execute(operation="add", a=5, b=3)
        print(f"  Status: {result['status']}")
        print(f"  Result: {result.get('result', {})}")
        
        if result['status'] == 'success' and result.get('result') == 8:
            print("  [OK] Tool executed correctly: 5 + 3 = 8")
            test1 = True
        else:
            print("  [FAIL] Tool execution failed or incorrect result")
            test1 = False
        
        # Test 2: Execute with different operation
        print("\n=== Test 2: Execute Tool (multiply) ===")
        result2 = await python_tool.execute(operation="multiply", a=4, b=7)
        print(f"  Status: {result2['status']}")
        print(f"  Result: {result2.get('result', {})}")
        
        if result2['status'] == 'success' and result2.get('result') == 28:
            print("  [OK] Tool executed correctly: 4 * 7 = 28")
            test2 = True
        else:
            print("  [FAIL] Tool execution failed or incorrect result")
            test2 = False
        
        # Test 3: Check metrics
        print("\n=== Test 3: Check Tool Metrics ===")
        metrics = tool_service.get_tool_metrics(tool.id)
        print(f"  Total executions: {metrics['total_executions']}")
        print(f"  Successful: {metrics['successful_executions']}")
        print(f"  Failed: {metrics['failed_executions']}")
        
        if metrics['total_executions'] >= 2:
            print("  [OK] Metrics recorded correctly")
            test3 = True
        else:
            print("  [FAIL] Metrics not recorded")
            test3 = False
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"[{'PASS' if test1 else 'FAIL'}]: Execute Tool (add)")
        print(f"[{'PASS' if test2 else 'FAIL'}]: Execute Tool (multiply)")
        print(f"[{'PASS' if test3 else 'FAIL'}]: Check Metrics")
        
        passed = sum([test1, test2, test3])
        print(f"\nTotal: {passed}/3 tests passed")
        
        if passed == 3:
            print("[SUCCESS] All tests passed!")
            print("\nNote: To test agent-tools integration, apply migration:")
            print("  alembic upgrade head")
            return True
        else:
            print(f"[WARN] {3 - passed} test(s) failed")
            return False
            
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    try:
        success = asyncio.run(test_tool_execution())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

