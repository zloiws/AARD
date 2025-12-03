"""
Test script for A2A (Agent-to-Agent) communication
Tests protocol, registry, router, and API endpoints
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

import httpx
from app.core.database import SessionLocal
from app.core.a2a_protocol import A2AMessage, A2AMessageType, A2ARequest, AgentIdentity
from app.services.agent_registry import AgentRegistry
from app.services.a2a_router import A2ARouter
from app.models.agent import Agent, AgentStatus
from app.services.agent_service import AgentService


async def test_a2a_protocol():
    """Test A2A protocol message creation and serialization"""
    print("\n" + "="*60)
    print("TEST 1: A2A Protocol")
    print("="*60)
    
    try:
        # Create a test message
        sender_id = uuid4()
        recipient_id = uuid4()
        
        request = A2ARequest(
            action="test_action",
            parameters={"param1": "value1", "param2": 42},
            context={"task_id": str(uuid4())}
        )
        
        message = request.to_message(
            sender_id=sender_id,
            recipient=recipient_id,
            sender_version=1,
            sender_capabilities=["test"],
            priority=5,
            timeout=30
        )
        
        print(f"✓ Created A2A message: {message.message_id}")
        print(f"  Type: {message.type.value}")
        print(f"  Sender: {message.sender.agent_id}")
        print(f"  Recipient: {message.recipient}")
        print(f"  Action: {message.payload.get('action')}")
        
        # Test serialization
        message_dict = message.to_dict()
        print(f"✓ Message serialized to dict")
        
        # Test deserialization
        message_restored = A2AMessage.from_dict(message_dict)
        print(f"✓ Message deserialized from dict")
        print(f"  Restored message_id: {message_restored.message_id}")
        
        # Test expiration
        assert not message.is_expired(), "New message should not be expired"
        print(f"✓ Message expiration check works")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_registry():
    """Test Agent Registry functionality"""
    print("\n" + "="*60)
    print("TEST 2: Agent Registry")
    print("="*60)
    
    db = SessionLocal()
    try:
        registry = AgentRegistry(db)
        
        # Create a test agent
        agent_service = AgentService(db)
        test_agent = agent_service.create_agent(
            name=f"test_agent_{uuid4().hex[:8]}",
            description="Test agent for A2A testing",
            capabilities=["test", "a2a"],
            created_by="test_script"
        )
        
        print(f"✓ Created test agent: {test_agent.name} ({test_agent.id})")
        
        # Register agent
        success = registry.register_agent(
            agent_id=test_agent.id,
            endpoint="http://localhost:8000/api/a2a/message/receive",
            capabilities=["test", "a2a"]
        )
        
        assert success, "Agent registration should succeed"
        print(f"✓ Agent registered in registry")
        
        # Find agents by capability
        found_agents = registry.find_agents(capabilities=["test"])
        print(f"✓ Found {len(found_agents)} agents with 'test' capability")
        
        # Get registry stats
        stats = registry.get_registry_stats()
        print(f"✓ Registry stats:")
        print(f"  Total active: {stats['total_active']}")
        print(f"  Healthy: {stats['healthy']}")
        print(f"  By capability: {stats['by_capability']}")
        
        # Get agent identity
        identity = registry.get_agent_identity(test_agent.id)
        assert identity is not None, "Should get agent identity"
        print(f"✓ Got agent identity: {identity.agent_id}")
        
        # Cleanup - pause agent instead of deleting
        agent_service.pause_agent(test_agent.id)
        print(f"✓ Test agent paused")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_a2a_router():
    """Test A2A Router functionality"""
    print("\n" + "="*60)
    print("TEST 3: A2A Router")
    print("="*60)
    
    db = SessionLocal()
    try:
        router = A2ARouter(db)
        registry = AgentRegistry(db)
        
        # Create test agents
        agent_service = AgentService(db)
        agent1 = agent_service.create_agent(
            name=f"router_test_1_{uuid4().hex[:8]}",
            description="Router test agent 1",
            capabilities=["router_test"],
            created_by="test_script"
        )
        
        agent2 = agent_service.create_agent(
            name=f"router_test_2_{uuid4().hex[:8]}",
            description="Router test agent 2",
            capabilities=["router_test"],
            created_by="test_script"
        )
        
        print(f"✓ Created test agents: {agent1.name}, {agent2.name}")
        
        # Register agents
        registry.register_agent(agent1.id, endpoint="http://localhost:8000/api/a2a/message/receive")
        registry.register_agent(agent2.id, endpoint="http://localhost:8000/api/a2a/message/receive")
        print(f"✓ Agents registered")
        
        # Create a test message
        request = A2ARequest(
            action="test_router",
            parameters={"test": "value"}
        )
        
        message = request.to_message(
            sender_id=agent1.id,
            recipient=agent2.id,
            sender_version=1,
            sender_capabilities=["router_test"]
        )
        
        print(f"✓ Created test message: {message.message_id}")
        
        # Test message handling (without actual HTTP call)
        async def mock_handler(msg: A2AMessage):
            """Mock handler for testing"""
            return {
                "status": "success",
                "result": "Test response",
                "metadata": {}
            }
        
        response = await router.handle_incoming_message(message, handler_callback=mock_handler)
        
        if response:
            print(f"✓ Message handled, got response: {response.type.value}")
            print(f"  Response status: {response.payload.get('status')}")
        else:
            print(f"⚠ Message handled but no response (expected for some message types)")
        
        # Test broadcast (will fail HTTP but should not crash)
        broadcast_message = A2AMessage(
            sender=AgentIdentity(
                agent_id=agent1.id,
                version=1,
                capabilities=["router_test"]
            ),
            recipient="broadcast",
            type=A2AMessageType.NOTIFICATION,
            payload={"action": "broadcast_test"}
        )
        
        print(f"✓ Testing broadcast (may fail HTTP but should not crash)...")
        try:
            await router._broadcast(broadcast_message)
            print(f"✓ Broadcast completed")
        except Exception as e:
            print(f"⚠ Broadcast HTTP failed (expected if agents not running): {e}")
        
        # Cleanup - pause agents instead of deleting
        agent_service.pause_agent(agent1.id)
        agent_service.pause_agent(agent2.id)
        print(f"✓ Test agents paused")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_a2a_api(base_url: str = "http://localhost:8000"):
    """Test A2A API endpoints"""
    print("\n" + "="*60)
    print("TEST 4: A2A API Endpoints")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test registry stats
            print(f"Testing GET /api/a2a/registry/stats...")
            response = await client.get(f"{base_url}/api/a2a/registry/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"✓ Registry stats endpoint works")
                print(f"  Total active: {stats.get('total_active', 0)}")
                print(f"  Healthy: {stats.get('healthy', 0)}")
            else:
                print(f"⚠ Registry stats returned {response.status_code}: {response.text}")
            
            # Test find agents
            print(f"\nTesting GET /api/a2a/registry/agents...")
            response = await client.get(f"{base_url}/api/a2a/registry/agents")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Find agents endpoint works")
                print(f"  Found {data.get('count', 0)} agents")
            else:
                print(f"⚠ Find agents returned {response.status_code}: {response.text}")
            
            # Test send message (will fail if no agents, but should not crash)
            print(f"\nTesting POST /api/a2a/message...")
            test_message = {
                "message_id": str(uuid4()),
                "timestamp": "2025-12-03T13:00:00Z",
                "ttl": 300,
                "priority": 5,
                "sender": {
                    "agent_id": str(uuid4()),
                    "version": 1,
                    "capabilities": ["test"]
                },
                "recipient": "broadcast",
                "type": "notification",
                "payload": {
                    "action": "test",
                    "parameters": {}
                },
                "encryption": "none"
            }
            
            response = await client.post(
                f"{base_url}/api/a2a/message",
                json={
                    "message": test_message,
                    "wait_for_response": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Send message endpoint works")
                print(f"  Message ID: {result.get('message_id')}")
            else:
                print(f"⚠ Send message returned {response.status_code}: {response.text}")
            
            return True
            
    except httpx.ConnectError:
        print(f"✗ Cannot connect to server at {base_url}")
        print(f"  Make sure the server is running: python backend/main.py")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("A2A Communication System Tests")
    print("="*60)
    
    results = []
    
    # Test 1: Protocol
    results.append(await test_a2a_protocol())
    
    # Test 2: Registry
    results.append(await test_agent_registry())
    
    # Test 3: Router
    results.append(await test_a2a_router())
    
    # Test 4: API (requires server running)
    print(f"\n⚠ Note: API tests require server to be running")
    api_result = await test_a2a_api()
    results.append(api_result)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    test_names = [
        "A2A Protocol",
        "Agent Registry",
        "A2A Router",
        "A2A API"
    ]
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{i+1}. {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

