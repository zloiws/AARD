"""
Tests for AgentDialogService
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime

from app.services.agent_dialog_service import AgentDialogService
from app.models.agent_conversation import AgentConversation, ConversationStatus, MessageRole
from app.models.agent import Agent, AgentStatus
from app.models.task import Task, TaskStatus


def test_create_conversation(db):
    """Test creating a conversation"""
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
    service = AgentDialogService(db)
    conversation = service.create_conversation(
        participant_ids=[agent1.id, agent2.id],
        goal="Test goal",
        title="Test Conversation"
    )
    
    assert conversation.id is not None
    assert conversation.goal == "Test goal"
    assert conversation.title == "Test Conversation"
    assert len(conversation.get_participants()) == 2
    assert conversation.status == ConversationStatus.INITIATED.value


def test_create_conversation_insufficient_participants(db):
    """Test that conversation requires at least 2 participants"""
    agent = Agent(
        name=f"Agent {uuid4()}",
        status=AgentStatus.ACTIVE.value
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    service = AgentDialogService(db)
    
    with pytest.raises(ValueError, match="at least 2 participants"):
        service.create_conversation(participant_ids=[agent.id])


def test_create_conversation_invalid_agent(db):
    """Test creating conversation with invalid agent ID"""
    service = AgentDialogService(db)
    
    invalid_id = uuid4()
    
    with pytest.raises(ValueError, match="not found or not active"):
        service.create_conversation(participant_ids=[invalid_id, uuid4()])


def test_get_conversation(db):
    """Test getting conversation by ID"""
    # Create agents and conversation
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    service = AgentDialogService(db)
    conversation = service.create_conversation(
        participant_ids=[agent1.id, agent2.id]
    )
    
    # Get conversation
    retrieved = service.get_conversation(conversation.id)
    assert retrieved is not None
    assert retrieved.id == conversation.id


def test_add_message(db):
    """Test adding message to conversation"""
    # Create agents and conversation
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    service = AgentDialogService(db)
    conversation = service.create_conversation(
        participant_ids=[agent1.id, agent2.id]
    )
    
    # Add message
    message = service.add_message(
        conversation_id=conversation.id,
        agent_id=agent1.id,
        content="Hello, this is a test message",
        role=MessageRole.AGENT
    )
    
    assert message is not None
    assert message["content"] == "Hello, this is a test message"
    assert message["agent_id"] == str(agent1.id)
    assert message["role"] == MessageRole.AGENT.value
    
    # Verify conversation status changed to active
    db.refresh(conversation)
    assert conversation.status == ConversationStatus.ACTIVE.value


def test_add_message_non_participant(db):
    """Test that non-participant cannot add message"""
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent3 = Agent(name=f"Agent 3 {uuid4()}", status=AgentStatus.ACTIVE.value)
    
    db.add(agent1)
    db.add(agent2)
    db.add(agent3)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    db.refresh(agent3)
    
    service = AgentDialogService(db)
    conversation = service.create_conversation(
        participant_ids=[agent1.id, agent2.id]
    )
    
    # Try to add message from non-participant
    with pytest.raises(ValueError, match="not a participant"):
        service.add_message(
            conversation_id=conversation.id,
            agent_id=agent3.id,
            content="This should fail"
        )


def test_update_context(db):
    """Test updating conversation context"""
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    service = AgentDialogService(db)
    conversation = service.create_conversation(
        participant_ids=[agent1.id, agent2.id],
        initial_context={"initial": "data"}
    )
    
    # Update context
    context = service.update_context(
        conversation_id=conversation.id,
        updates={"new": "value", "number": 42}
    )
    
    assert context["initial"] == "data"
    assert context["new"] == "value"
    assert context["number"] == 42


def test_is_conversation_complete(db):
    """Test checking if conversation is complete"""
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    service = AgentDialogService(db)
    conversation = service.create_conversation(
        participant_ids=[agent1.id, agent2.id]
    )
    
    # Not complete initially
    assert service.is_conversation_complete(conversation.id) is False
    
    # Check with max_messages condition
    assert service.is_conversation_complete(
        conversation.id,
        check_conditions={"max_messages": 5}
    ) is False
    
    # Add messages to reach limit
    for i in range(5):
        service.add_message(
            conversation_id=conversation.id,
            agent_id=agent1.id if i % 2 == 0 else agent2.id,
            content=f"Message {i}"
        )
    
    # Refresh conversation to get updated message count
    db.refresh(conversation)
    
    # Now should be complete (5 messages >= 5 max_messages)
    assert service.is_conversation_complete(
        conversation.id,
        check_conditions={"max_messages": 5}
    ) is True


def test_complete_conversation(db):
    """Test completing a conversation"""
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    service = AgentDialogService(db)
    conversation = service.create_conversation(
        participant_ids=[agent1.id, agent2.id]
    )
    
    # Complete successfully
    completed = service.complete_conversation(
        conversation_id=conversation.id,
        success=True,
        result={"outcome": "success"}
    )
    
    assert completed.status == ConversationStatus.COMPLETED.value
    assert completed.completed_at is not None
    
    # Check result in context
    context = completed.get_context()
    assert "result" in context
    assert context["result"]["outcome"] == "success"


def test_pause_and_resume_conversation(db):
    """Test pausing and resuming a conversation"""
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    service = AgentDialogService(db)
    conversation = service.create_conversation(
        participant_ids=[agent1.id, agent2.id]
    )
    
    # Add a message to make it active
    service.add_message(
        conversation_id=conversation.id,
        agent_id=agent1.id,
        content="Test message"
    )
    
    # Pause
    paused = service.pause_conversation(conversation.id)
    assert paused.status == ConversationStatus.PAUSED.value
    
    # Resume
    resumed = service.resume_conversation(conversation.id)
    assert resumed.status == ConversationStatus.ACTIVE.value


def test_get_conversations_by_task(db):
    """Test getting conversations by task"""
    # Create task
    task = Task(
        description="Test task",
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create agents
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    db.add(agent1)
    db.add(agent2)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    
    service = AgentDialogService(db)
    
    # Create conversations
    conv1 = service.create_conversation(
        participant_ids=[agent1.id, agent2.id],
        task_id=task.id
    )
    conv2 = service.create_conversation(
        participant_ids=[agent1.id, agent2.id],
        task_id=task.id
    )
    
    # Get conversations by task
    conversations = service.get_conversations_by_task(task.id)
    assert len(conversations) == 2
    assert conv1.id in {c.id for c in conversations}
    assert conv2.id in {c.id for c in conversations}


def test_get_conversations_by_agent(db):
    """Test getting conversations by agent"""
    agent1 = Agent(name=f"Agent 1 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent2 = Agent(name=f"Agent 2 {uuid4()}", status=AgentStatus.ACTIVE.value)
    agent3 = Agent(name=f"Agent 3 {uuid4()}", status=AgentStatus.ACTIVE.value)
    
    db.add(agent1)
    db.add(agent2)
    db.add(agent3)
    db.commit()
    db.refresh(agent1)
    db.refresh(agent2)
    db.refresh(agent3)
    
    service = AgentDialogService(db)
    
    # Create conversations
    conv1 = service.create_conversation(participant_ids=[agent1.id, agent2.id])
    conv2 = service.create_conversation(participant_ids=[agent1.id, agent3.id])
    conv3 = service.create_conversation(participant_ids=[agent2.id, agent3.id])
    
    # Get conversations for agent1
    conversations = service.get_conversations_by_agent(agent1.id)
    assert len(conversations) == 2
    assert conv1.id in {c.id for c in conversations}
    assert conv2.id in {c.id for c in conversations}
    assert conv3.id not in {c.id for c in conversations}

