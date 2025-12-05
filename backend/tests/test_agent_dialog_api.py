"""
API tests for agent dialogs endpoints
"""
import pytest
from uuid import uuid4, UUID
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes.agent_dialogs import router
from app.models.agent import Agent, AgentStatus
from app.models.agent_conversation import ConversationStatus, MessageRole
from app.services.agent_service import AgentService
from app.core.database import SessionLocal


@pytest.fixture
def client(db):
    """Create test client"""
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def test_agents(db):
    """Create test agents"""
    agent_service = AgentService(db)
    agent1 = agent_service.create_agent(
        name=f"Test Agent 1 {uuid4()}",
        capabilities=["planning"]
    )
    agent1.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent1)
    
    agent2 = agent_service.create_agent(
        name=f"Test Agent 2 {uuid4()}",
        capabilities=["code_generation"]
    )
    agent2.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent2)
    
    return agent1, agent2


def test_create_conversation(client, db, test_agents):
    """Test creating a conversation via API"""
    agent1, agent2 = test_agents
    
    response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test conversation goal",
            "title": "Test Conversation"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["goal"] == "Test conversation goal"
    # title is optional and may not be in response
    if "title" in data:
        assert data["title"] == "Test Conversation"
    assert len(data["participants"]) == 2
    assert data["status"] == ConversationStatus.INITIATED.value


def test_create_conversation_insufficient_participants(client, db, test_agents):
    """Test creating conversation with less than 2 participants"""
    agent1, _ = test_agents
    
    response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id)],
            "goal": "Test"
        }
    )
    
    # Pydantic validation returns 422, service validation returns 400
    assert response.status_code in [400, 422]


def test_get_conversation(client, db, test_agents):
    """Test getting a conversation by ID"""
    agent1, agent2 = test_agents
    
    # Create conversation
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal"
        }
    )
    assert create_response.status_code == 201
    conversation_id = create_response.json()["id"]
    
    # Get conversation
    response = client.get(f"/api/agent-dialogs/{conversation_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conversation_id
    assert data["goal"] == "Test goal"


def test_get_conversation_not_found(client, db):
    """Test getting non-existent conversation"""
    fake_id = str(uuid4())
    response = client.get(f"/api/agent-dialogs/{fake_id}")
    
    assert response.status_code == 404


def test_list_conversations(client, db, test_agents):
    """Test listing conversations"""
    agent1, agent2 = test_agents
    
    # Create multiple conversations
    for i in range(3):
        client.post(
            "/api/agent-dialogs/",
            json={
                "participant_ids": [str(agent1.id), str(agent2.id)],
                "goal": f"Test goal {i}"
            }
        )
    
    # List all conversations
    response = client.get("/api/agent-dialogs/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_list_conversations_by_task(client, db, test_agents):
    """Test listing conversations filtered by task_id"""
    from app.models.task import Task, TaskStatus
    
    agent1, agent2 = test_agents
    
    # Create task
    task = Task(
        description="Test task",
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create conversation linked to task
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal",
            "task_id": str(task.id)
        }
    )
    assert create_response.status_code == 201
    
    # List conversations by task
    response = client.get(f"/api/agent-dialogs/?task_id={task.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["task_id"] == str(task.id)


def test_add_message(client, db, test_agents):
    """Test adding a message to conversation"""
    agent1, agent2 = test_agents
    
    # Create conversation
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal"
        }
    )
    conversation_id = create_response.json()["id"]
    
    # Add message
    response = client.post(
        f"/api/agent-dialogs/{conversation_id}/message",
        json={
            "agent_id": str(agent1.id),
            "content": "Test message content"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Test message content"
    assert data["agent_id"] == str(agent1.id)
    assert "timestamp" in data


def test_add_message_non_participant(client, db, test_agents):
    """Test adding message by non-participant agent"""
    agent1, agent2 = test_agents
    
    # Create third agent
    agent_service = AgentService(db)
    agent3 = agent_service.create_agent(
        name=f"Test Agent 3 {uuid4()}",
        capabilities=["analysis"]
    )
    db.commit()
    db.refresh(agent3)
    
    # Create conversation with agent1 and agent2
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal"
        }
    )
    conversation_id = create_response.json()["id"]
    
    # Try to add message as agent3 (not a participant)
    response = client.post(
        f"/api/agent-dialogs/{conversation_id}/message",
        json={
            "agent_id": str(agent3.id),
            "content": "Test message"
        }
    )
    
    assert response.status_code == 400


def test_send_message_to_participants(client, db, test_agents):
    """Test sending message with A2A notifications"""
    agent1, agent2 = test_agents
    
    # Create conversation
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal"
        }
    )
    conversation_id = create_response.json()["id"]
    
    # Send message
    response = client.post(
        f"/api/agent-dialogs/{conversation_id}/send-message",
        json={
            "sender_agent_id": str(agent1.id),
            "content": "Hello from agent 1"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Hello from agent 1"
    assert data["agent_id"] == str(agent1.id)


def test_update_context(client, db, test_agents):
    """Test updating conversation context"""
    agent1, agent2 = test_agents
    
    # Create conversation
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal"
        }
    )
    conversation_id = create_response.json()["id"]
    
    # Update context
    response = client.put(
        f"/api/agent-dialogs/{conversation_id}/context",
        json={
            "updates": {
                "key1": "value1",
                "key2": {"nested": "value"}
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["key1"] == "value1"
    assert data["key2"]["nested"] == "value"


def test_complete_conversation(client, db, test_agents):
    """Test completing a conversation"""
    agent1, agent2 = test_agents
    
    # Create conversation
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal"
        }
    )
    conversation_id = create_response.json()["id"]
    
    # Complete conversation
    response = client.post(
        f"/api/agent-dialogs/{conversation_id}/complete?success=true",
        json={
            "result": {"final_decision": "Agreed"}
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ConversationStatus.COMPLETED.value
    assert data.get("completed_at") is not None


def test_pause_resume_conversation(client, db, test_agents):
    """Test pausing and resuming a conversation"""
    agent1, agent2 = test_agents
    
    # Create conversation
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal"
        }
    )
    conversation_id = create_response.json()["id"]
    
    # Pause conversation
    pause_response = client.post(f"/api/agent-dialogs/{conversation_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == ConversationStatus.PAUSED.value
    
    # Resume conversation
    resume_response = client.post(f"/api/agent-dialogs/{conversation_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == ConversationStatus.ACTIVE.value


def test_get_messages(client, db, test_agents):
    """Test getting all messages in a conversation"""
    agent1, agent2 = test_agents
    
    # Create conversation
    create_response = client.post(
        "/api/agent-dialogs/",
        json={
            "participant_ids": [str(agent1.id), str(agent2.id)],
            "goal": "Test goal"
        }
    )
    conversation_id = create_response.json()["id"]
    
    # Add multiple messages
    for i in range(3):
        client.post(
            f"/api/agent-dialogs/{conversation_id}/message",
            json={
                "agent_id": str(agent1.id if i % 2 == 0 else agent2.id),
                "content": f"Message {i}"
            }
        )
    
    # Get messages
    response = client.get(f"/api/agent-dialogs/{conversation_id}/messages")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert all("content" in msg for msg in data)
    assert all("agent_id" in msg for msg in data)

