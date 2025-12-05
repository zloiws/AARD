"""
Tests for AgentConversation model
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime

from app.models.agent_conversation import (
    AgentConversation,
    ConversationStatus,
    MessageRole
)
from app.models.agent import Agent, AgentStatus
from app.models.task import Task, TaskStatus


def test_agent_conversation_creation(db):
    """Test creating an agent conversation"""
    # Create test agents
    agent1 = Agent(
        name=f"Agent 1 {uuid4()}",
        status=AgentStatus.ACTIVE.value,
        capabilities=["planning", "reasoning"]
    )
    agent2 = Agent(
        name=f"Agent 2 {uuid4()}",
        status=AgentStatus.ACTIVE.value,
        capabilities=["code_generation"]
    )
    
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    # Create conversation
    conversation = AgentConversation(
        title="Test Conversation",
        description="A test conversation between agents",
        participants=[str(agent1.id), str(agent2.id)],
        messages=[],
        goal="Solve a complex problem together",
        status=ConversationStatus.INITIATED.value
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    assert conversation.id is not None
    assert conversation.title == "Test Conversation"
    assert conversation.description == "A test conversation between agents"
    assert len(conversation.get_participants()) == 2
    assert conversation.goal == "Solve a complex problem together"
    assert conversation.status == ConversationStatus.INITIATED.value
    assert conversation.messages == []


def test_agent_conversation_add_message(db):
    """Test adding messages to a conversation"""
    # Create test agent
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Create conversation
    conversation = AgentConversation(
        participants=[str(agent.id)],
        messages=[],
        status=ConversationStatus.INITIATED.value
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Add message
    message = conversation.add_message(
        agent_id=agent.id,
        content="Hello, this is a test message",
        role=MessageRole.AGENT
    )
    
    db.commit()
    db.refresh(conversation)
    
    assert message is not None
    assert message["content"] == "Hello, this is a test message"
    assert message["role"] == MessageRole.AGENT.value
    assert message["agent_id"] == str(agent.id)
    assert "id" in message
    assert "timestamp" in message
    
    # Check that status changed to active
    assert conversation.status == ConversationStatus.ACTIVE.value
    
    # Check messages
    messages = conversation.get_messages()
    assert len(messages) == 1
    assert messages[0]["content"] == "Hello, this is a test message"


def test_agent_conversation_multiple_messages(db):
    """Test adding multiple messages to a conversation"""
    # Create test agents
    agent1 = Agent(
        name=f"Agent 1 {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    agent2 = Agent(
        name=f"Agent 2 {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    # Create conversation
    conversation = AgentConversation(
        participants=[str(agent1.id), str(agent2.id)],
        messages=[],
        status=ConversationStatus.INITIATED.value
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Add messages from both agents
    conversation.add_message(agent1.id, "Message 1 from agent 1", MessageRole.AGENT)
    conversation.add_message(agent2.id, "Message 2 from agent 2", MessageRole.AGENT)
    conversation.add_message(agent1.id, "Message 3 from agent 1", MessageRole.AGENT)
    
    db.commit()
    db.refresh(conversation)
    
    messages = conversation.get_messages()
    assert len(messages) == 3
    assert messages[0]["content"] == "Message 1 from agent 1"
    assert messages[1]["content"] == "Message 2 from agent 2"
    assert messages[2]["content"] == "Message 3 from agent 1"


def test_agent_conversation_participants(db):
    """Test participant management"""
    # Create test agents
    agent1 = Agent(
        name=f"Agent 1 {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    agent2 = Agent(
        name=f"Agent 2 {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    agent3 = Agent(
        name=f"Agent 3 {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    
    db.add(agent1)
    db.add(agent2)
    db.add(agent3)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    db.refresh(agent3)
    
    # Create conversation with 2 participants
    conversation = AgentConversation(
        participants=[str(agent1.id), str(agent2.id)],
        messages=[]
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Check participants
    participants = conversation.get_participants()
    assert len(participants) == 2
    assert agent1.id in participants
    assert agent2.id in participants
    assert agent3.id not in participants
    
    # Check is_participant
    assert conversation.is_participant(agent1.id) is True
    assert conversation.is_participant(agent2.id) is True
    assert conversation.is_participant(agent3.id) is False


def test_agent_conversation_context(db):
    """Test conversation context management"""
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    conversation = AgentConversation(
        participants=[str(agent.id)],
        messages=[],
        context={"initial": "data"}
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Get context
    context = conversation.get_context()
    assert context == {"initial": "data"}
    
    # Update context
    conversation.update_context({"new": "value", "number": 42})
    db.commit()
    db.refresh(conversation)
    
    context = conversation.get_context()
    assert context["initial"] == "data"
    assert context["new"] == "value"
    assert context["number"] == 42


def test_agent_conversation_complete(db):
    """Test completing a conversation"""
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    conversation = AgentConversation(
        participants=[str(agent.id)],
        messages=[],
        status=ConversationStatus.ACTIVE.value
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Complete successfully
    conversation.complete(success=True)
    db.commit()
    db.refresh(conversation)
    
    assert conversation.status == ConversationStatus.COMPLETED.value
    assert conversation.completed_at is not None
    
    # Test failure
    conversation2 = AgentConversation(
        participants=[str(agent.id)],
        messages=[],
        status=ConversationStatus.ACTIVE.value
    )
    db.add(conversation2)
    db.commit()
    db.refresh(conversation2)
    
    conversation2.complete(success=False)
    db.commit()
    db.refresh(conversation2)
    
    assert conversation2.status == ConversationStatus.FAILED.value
    assert conversation2.completed_at is not None


def test_agent_conversation_task_relationship(db):
    """Test conversation relationship with task"""
    # Create task
    task = Task(
        description="Test task for conversation",
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create agent
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Create conversation linked to task
    conversation = AgentConversation(
        participants=[str(agent.id)],
        messages=[],
        task_id=task.id
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    assert conversation.task_id == task.id
    assert conversation.task is not None
    assert conversation.task.id == task.id


def test_agent_conversation_to_dict(db):
    """Test converting conversation to dictionary"""
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    conversation = AgentConversation(
        title="Test Conversation",
        description="Test description",
        participants=[str(agent.id)],
        messages=[],
        goal="Test goal",
        context={"test": "data"},
        status=ConversationStatus.ACTIVE.value
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Add a message
    conversation.add_message(agent.id, "Test message", MessageRole.AGENT)
    db.commit()
    db.refresh(conversation)
    
    # Convert to dict
    conv_dict = conversation.to_dict()
    
    assert conv_dict["id"] == str(conversation.id)
    assert conv_dict["title"] == "Test Conversation"
    assert conv_dict["description"] == "Test description"
    assert conv_dict["goal"] == "Test goal"
    assert conv_dict["status"] == ConversationStatus.ACTIVE.value
    assert len(conv_dict["participants"]) == 1
    assert len(conv_dict["messages"]) == 1
    assert conv_dict["context"] == {"test": "data"}
    assert "created_at" in conv_dict
    assert "updated_at" in conv_dict


def test_agent_conversation_default_values(db):
    """Test default values for conversation"""
    agent = Agent(
        name=f"Test Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    conversation = AgentConversation(
        participants=[str(agent.id)]
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    assert conversation.status == ConversationStatus.INITIATED.value
    assert conversation.messages == []
    assert conversation.context is None or conversation.context == {}
    assert conversation.goal is None
    assert conversation.title is None
    assert conversation.description is None
    assert conversation.task_id is None
    assert conversation.completed_at is None

